"""ML report auditor: read a model write-up (text + confusion matrix) and flag problems.

Checks
  1. Matrix   recompute accuracy, precision, recall, F1, specificity from the confusion matrix; flag any
              reported number that doesn't match, and flag precision reported without recall
  2. Baseline compare accuracy with always predicting the majority class
  3. Leakage  features available only after the prediction moment (timing from the report or a context file),
              features whose names suggest post-outcome information, and history counts that need a cutoff
  4. Split    random row splits when the same entities repeat, or when the data has a time order
  5. Claims   causal language ("causes", "would cut ... by", "drives") drawn from a predictive model,
              and "ready to ship" claims with weak recall

Usage
  python audit.py REPORT.md [--context CONTEXT.md] [--format md|json|html] [--out FILE]
Standard library only.
"""
import argparse
import html
import json
import re
import sys

NUM = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"   # 3,540 or 0.82; a comma must be a thousands separator
SEV_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def num(s):
    return float(s.replace(",", ""))


# ------------------------------------------------------------------ parsing
def parse_matrix(text):
    """Find TP/FP/FN/TN in 'TP 184, FP 60 ...', 'TP = 184', or a 2x2 actual/predicted table."""
    vals = {}
    for k in ("TP", "FP", "FN", "TN"):
        m = re.search(r"\b" + k + r"\b\s*[:=]?\s*" + NUM, text)
        if m:
            vals[k] = int(num(m.group(1)))
    if len(vals) == 4:
        return vals
    # table: rows "actual yes | a | b" / "actual no | c | d" with predicted yes first
    rows = re.findall(r"actual[_ ]?(yes|no|positive|negative|1|0)[^\d\n]*" + NUM + r"[^\d\n]+" + NUM, text, re.I)
    if len(rows) >= 2:
        get = {r[0].lower(): (int(num(r[1])), int(num(r[2]))) for r in rows}
        pos = get.get("yes") or get.get("positive") or get.get("1")
        neg = get.get("no") or get.get("negative") or get.get("0")
        if pos and neg:
            return {"TP": pos[0], "FN": pos[1], "FP": neg[0], "TN": neg[1]}
    return None


def parse_claims(text):
    """Reported metrics as proportions: accuracy, precision, recall, f1, specificity, auc."""
    names = {"accuracy": r"accura(?:cy|te)", "precision": r"precision", "recall": r"recall|sensitivity|true positive rate",
             "f1": r"f1(?:[- ]score)?", "specificity": r"specificity", "auc": r"\bauc\b|roc[- ]auc"}
    out = {}
    for key, pat in names.items():
        for m in re.finditer(r"(?:" + pat + r")\s*(?:of|is|was|=|:|at|\()?\s*" + NUM + r"\s*(%)?", text, re.I):
            v = num(m.group(1))
            if m.group(2) or v > 1:
                v /= 100
            out.setdefault(key, []).append((v, m.group(0).strip()))
        for m in re.finditer(NUM + r"\s*(%)?\s*(?:" + pat + r")", text, re.I):     # "93% accurate"
            v = num(m.group(1))
            if m.group(2) or v > 1:
                v /= 100
            if 0 < v <= 1:
                out.setdefault(key, []).append((v, m.group(0).strip()))
    return out


def parse_features(text):
    """Comma list after 'Features:' or a bulleted list under a Features heading. Returns [(name, note)]."""
    feats = []
    m = re.search(r"features?\s*(?:used)?\s*:\s*([^\n]+?)(?:\.\s|\.$|\n)", text, re.I)
    if m and "," in m.group(1):
        for part in re.split(r",\s*(?:and\s+)?|\s+and\s+", m.group(1)):
            part = part.strip(" .")
            if part:
                nm = re.match(r"([^()]+?)\s*(?:\((.*)\))?$", part)
                feats.append((nm.group(1).strip(), (nm.group(2) or "").strip()))
    sec = re.search(r"#+\s*features?[^\n]*\n((?:\s*[-*]\s+[^\n]+\n?)+)", text, re.I)
    if sec:
        for line in re.findall(r"[-*]\s+([^\n]+)", sec.group(1)):
            nm = re.match(r"`?([\w .\-]+?)`?\s*(?:[:—-]\s*(.*)|\((.*)\))?$", line.strip())
            if nm:
                feats.append((nm.group(1).strip(), (nm.group(2) or nm.group(3) or "").strip()))
    seen, out = set(), []
    for n, note in feats:
        if n.lower() not in seen:
            seen.add(n.lower())
            out.append((n, note))
    return out


UNIT_H = {"minute": 1 / 60, "hour": 1, "h": 1, "day": 24, "week": 168, "month": 720}


def hours(n, unit):
    u = unit.lower().rstrip("s")
    return num(n) * UNIT_H.get(u, UNIT_H.get(u[:4], 1))


def parse_timing(text):
    """Prediction moment and availability facts, as hours before (+) or after (-) the reference event."""
    pred = None
    m = re.search(r"predict\w*[^.\n]{0,40}?(?:made|run|generated|scored|issued)?\s*" + NUM + r"\s*(hours?|h|days?|weeks?)\s+before\s+(\w+)", text, re.I)
    if m:
        pred = {"hours_before": hours(m.group(1), m.group(2)), "event": m.group(3).lower(), "text": m.group(0)}
    else:
        m = re.search(r"predict\w*[^.\n]{0,40}?\bat\s+(?:the\s+)?(?:time\s+of\s+)?(booking|application|checkout|discharge|signup|sign-up|authorization|order|filing|enrollment)", text, re.I)
        if m:
            pred = {"moment": m.group(1).lower(), "text": m.group(0)}
    facts = []
    for m in re.finditer(r"([^.\n]{0,80}?)\b(opens?|available|recorded|happens?|occurs?|starts?|captured|known|filled in|logged|takes? place)\s+(?:only\s+)?" + NUM + r"\s*(hours?|h|days?|weeks?)\s+(before|after)\s+(\w+)", text, re.I):
        hb = hours(m.group(3), m.group(4)) * (1 if m.group(5).lower() == "before" else -1)
        facts.append({"subject": m.group(1).strip(), "hours_before": hb, "event": m.group(6).lower(), "text": m.group(0).strip()})
    for m in re.finditer(r"([^.\n]{0,80}?)\b(?:recorded|known|filled in|captured|happens?|takes place|assigned|logged)\s+(?:only\s+)?(at|after|during)\s+(check-in|arrival|departure|discharge|delivery|the end|cancellation|closing)", text, re.I):
        facts.append({"subject": m.group(1).strip(), "after_event": m.group(3).lower(), "text": m.group(0).strip()})
    return pred, facts


def tokens(s):
    s = re.sub(r"[_\-]", " ", s.lower())
    toks = set(re.findall(r"[a-z]+", s))
    # light normalization: check-in / checked in / checkin
    if {"checked", "in"} <= toks or "checkin" in toks or {"check", "in"} <= toks:
        toks |= {"checkin"}
    return {t.rstrip("s") for t in toks if len(t) > 2 or t == "in"} - {"the", "and", "for", "online", "are", "was", "only", "this"}


# ------------------------------------------------------------------ checks
POST_HINTS = {
    "checked_in": "check-in status is only known close to departure", "check_in": "check-in status is only known close to departure",
    "boarding": "boarding happens at departure", "refund": "refunds follow the outcome", "chargeback": "chargebacks are filed after fraud",
    "collection": "loans go to collections because they default", "cancel": "cancellation fields are set when the outcome happens",
    "status": "status fields are usually updated as the outcome unfolds", "outcome": "outcome fields encode the label",
    "final": "'final' values are known only at the end", "return": "returns happen after delivery", "exit": "exit events happen when someone leaves",
    "after": "the name says it is measured after something", "post_": "post-event measurement", "future": "future information",
    "next_": "next-period information", "days_until": "time-until-event encodes the label", "lifetime": "lifetime totals include the future",
    "follow_up": "follow-ups happen after the prediction", "followup": "follow-ups happen after the prediction", "complaint": "complaints follow bad outcomes",
    "dispute": "disputes follow the outcome", "denied": "denial is the decision being predicted", "scanned": "scans happen during the event",
    "assigned_room": "rooms are assigned at check-in", "resolution": "resolutions come after the event", "attended": "attendance is observed later",
}
HISTORY_HINTS = ("past", "previous", "prior", "history", "historical", "count", "last")
STRONG = ("refund", "chargeback", "collection", "boarding", "days_until", "exit", "outcome", "denied", "scanned", "reservation_status")
CAUSAL = [r"\bcaus(?:e|es|ed|ing)\b", r"\bleads? to\b", r"\bdrives?\b", r"\bresults? in\b", r"\bbecause of\b",
          r"\bwould (?:cut|reduce|increase|raise|lower|decrease|eliminate|boost|improve)\b", r"\bif we (?:drop|remove|change|cut|raise|lower|stop|add)\b",
          r"\b(?:the )?(?:effect|impact) of\b", r"\bresponsible for\b", r"\bmakes? (?:customers|people|passengers|users|patients)\b"]
HEDGES = r"\b(?:associated with|correlat\w*|predict\w*|linked to|not causal|does not (?:imply|prove|show)|cannot conclude)\b"


def finding(sev, area, title, evidence, fix, detail=""):
    return {"severity": sev, "area": area, "title": title, "evidence": evidence, "fix": fix, "detail": detail}


def metrics_from(cm):
    tp, fp, fn, tn = cm["TP"], cm["FP"], cm["FN"], cm["TN"]
    n = tp + fp + fn + tn
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return {"n": n, "positives": tp + fn, "accuracy": (tp + tn) / n, "precision": prec, "recall": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else float("nan"), "specificity": tn / (tn + fp) if tn + fp else float("nan"),
            "baseline": max(tp + fn, fp + tn) / n, "majority": "positive" if tp + fn > fp + tn else "negative"}


def audit(text, context=""):
    full = text + "\n" + context
    out = {"findings": [], "matrix": None, "metrics": None, "claims": {}, "features": [], "timing": {}}
    F = out["findings"]
    cm = parse_matrix(text)
    claims = parse_claims(text)
    out["claims"] = {k: [c[0] for c in v] for k, v in claims.items()}
    # ---- 1/2. matrix and baseline
    if not cm:
        F.append(finding("MEDIUM", "Matrix", "No confusion matrix found", "", "Report TP, FP, FN and TN on the test set so every metric can be checked."))
    else:
        m = metrics_from(cm)
        out["matrix"], out["metrics"] = cm, m
        for key in ("accuracy", "precision", "recall", "f1", "specificity"):
            for v, quote in claims.get(key, []):
                if abs(v - m[key]) > 0.0051:
                    F.append(finding("HIGH", "Matrix", f"Reported {key} doesn't match the confusion matrix", quote,
                                     f"Recompute from the matrix: {key} = {m[key]:.3f}, not {v:.3f}.", f"reported {v:.3f} vs {m[key]:.3f}"))
        if "precision" in claims and "recall" not in claims:
            F.append(finding("HIGH" if m["recall"] < 0.6 else "MEDIUM", "Matrix", "Precision reported without recall",
                             claims["precision"][0][1], f"Report recall too: {cm['TP']}/{cm['TP'] + cm['FN']} = {m['recall']:.3f}. "
                             f"The model misses {1 - m['recall']:.0%} of actual positives."))
        acc_claim = claims.get("accuracy", [(m["accuracy"], "")])[0]
        gap = m["accuracy"] - m["baseline"]
        acknowledged = re.search(r"baseline|majority|always[- ](?:predict|legit|no|negative)|naive", text, re.I)
        if "accuracy" in claims and gap < 0.05:
            F.append(finding("LOW" if acknowledged else "HIGH" if gap < 0.02 else "MEDIUM", "Baseline", "Accuracy barely beats always predicting the majority class",
                             acc_claim[1], f"Always predicting '{m['majority']}' scores {m['baseline']:.1%}; the model adds only {100 * gap:.1f} points. "
                             "Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.",
                             f"accuracy {m['accuracy']:.3f} vs baseline {m['baseline']:.3f}"))
        elif "accuracy" in claims and not re.search(r"baseline|majority|naive|always predict", text, re.I) and m["baseline"] > 0.7:
            F.append(finding("LOW", "Baseline", "No baseline given for an imbalanced problem", acc_claim[1],
                             f"State the majority-class baseline ({m['baseline']:.1%}) next to accuracy."))
        ship = re.search(r"[^.\n]*\b(?:ready to (?:ship|deploy|launch)|production[- ]ready|deploy (?:it|now)|good to go)\b[^.\n]*", text, re.I)
        if ship and (m["recall"] < 0.6 or gap < 0.05):
            F.append(finding("MEDIUM", "Claim", "'Ready to ship' isn't supported by the metrics", ship.group(0).strip(),
                             f"With recall {m['recall']:.2f} and {100 * gap:.1f} points over the baseline, decide on business cost first (e.g. a cutoff that minimizes cost)."))
    # ---- 3. leakage
    feats = parse_features(text)
    out["features"] = [f[0] for f in feats]
    pred, facts = parse_timing(full)
    out["timing"] = {"prediction": pred, "facts": facts}
    flagged = set()
    for name, note in feats:
        ftoks, lname = tokens(name + " " + note), name.lower().replace(" ", "_")
        # timing facts that mention this feature's key words
        for f in facts:
            stoks = tokens(f["subject"])
            if not (ftoks & stoks - {"in", "passenger", "customer"}):
                continue
            later = ("after_event" in f) \
                or (pred and "hours_before" in pred and "hours_before" in f and f["event"] == pred["event"] and f["hours_before"] < pred["hours_before"]) \
                or (pred and "moment" in pred and "hours_before" in f and f["hours_before"] < 0 and f["event"].startswith(pred["moment"][:6]))
            if later:
                when = f"{f['hours_before']:g} h before {f['event']}" if "hours_before" in f else f"at {f['after_event']}"
                at = f"{pred['hours_before']:g} h before {pred['event']}" if pred and "hours_before" in pred else (pred or {}).get("moment", "prediction time")
                F.append(finding("HIGH", "Leakage", f"'{name}' isn't available when the prediction is made",
                                 f"{f['text']} / prediction: {(pred or {}).get('text', 'see report')}",
                                 f"Drop '{name}' or replace it with its value as of the prediction moment ({at}); it only exists {when}."))
                flagged.add(name)
                break
        if name in flagged:
            continue
        hint = next((why for key, why in POST_HINTS.items() if key in lname), None)
        strong = any(k in lname for k in STRONG)
        if hint and not any(h in lname for h in ("past_", "prior_", "previous_")):
            F.append(finding("HIGH" if strong else "MEDIUM", "Leakage", f"'{name}' {'leaks' if strong else 'may leak'} post-prediction information", name,
                             f"Check when '{name}' is recorded ({hint}). Keep it only if it's known at the prediction moment."))
            flagged.add(name)
        elif set(re.split(r"[^a-z]+", name.lower())) & set(HISTORY_HINTS):
            F.append(finding("LOW", "Leakage", f"History feature '{name}' needs a cutoff date", name,
                             f"Compute '{name}' only from events before the prediction moment (not as of today), or it leaks the label."))
    # ---- 4. split
    split = re.search(r"[^.\n]*\brandom(?:ly)?\b[^.\n]*\bsplit\b[^.\n]*|[^.\n]*\bsplit\b[^.\n]*\brandom(?:ly)?\b[^.\n]*", text, re.I)
    if split:
        repeat = re.search(r"[^.\n]*\b(?:frequent|repeat(?:ed)?|returning|same (?:customer|passenger|patient|user|borrower)s?|multiple (?:bookings|orders|visits|loans)|loyal)\b[^.\n]*", text, re.I)
        if repeat:
            F.append(finding("HIGH", "Leakage", "Random row split while the same people appear many times", f"{split.group(0).strip()} / {repeat.group(0).strip()}",
                             "Split by person (group split) or by time, so no one appears in both train and test; re-score on the clean split."))
        elif re.search(r"\b(?:20\d\d|years?|months?|over time|daily|weekly|season|history)\b", text, re.I):
            F.append(finding("MEDIUM", "Split", "Random split on data with a time order", split.group(0).strip(),
                             "Use a time-based split (train on the past, test on the future) to mimic deployment."))
    # ---- 5. causal claims
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if re.search(HEDGES, sent, re.I) and not re.search(r"\bwould (?:cut|reduce|increase)\b", sent, re.I):
            continue
        hits = [p for p in CAUSAL if re.search(p, sent, re.I)]
        if hits:
            strong = bool(re.search(r"importance|model|shap|coefficient|feature", sent, re.I)) or bool(re.search(r"\bwould\b|\bif we\b", sent, re.I))
            F.append(finding("HIGH" if strong else "MEDIUM", "Claim", "Causal claim from a predictive model", sent.strip(),
                             "Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare)."))
    F.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["area"]))
    return out


# ------------------------------------------------------------------ output
def to_markdown(res, name="report"):
    F, m = res["findings"], res["metrics"]
    counts = {s: sum(f["severity"] == s for f in F) for s in SEV_ORDER}
    L = [f"# Audit: {name}", "", f"**{counts['HIGH']} high, {counts['MEDIUM']} medium, {counts['LOW']} low** severity findings.", ""]
    if m:
        cm = res["matrix"]
        L += ["## Metrics recomputed from the confusion matrix", "",
              f"TP {cm['TP']:,} · FP {cm['FP']:,} · FN {cm['FN']:,} · TN {cm['TN']:,} (n = {m['n']:,}, {m['positives']:,} positives = {m['positives'] / m['n']:.1%})", "",
              "| Metric | Recomputed | Reported |", "|---|---|---|"]
        for k in ("accuracy", "precision", "recall", "f1", "specificity"):
            rep = res["claims"].get(k)
            L.append(f"| {k} | {m[k]:.3f} | {', '.join(f'{v:.3f}' for v in rep) if rep else '–'} |")
        L += [f"| majority-class baseline | {m['baseline']:.3f} | |", ""]
    L += ["## Findings", ""]
    if not F:
        L.append("No problems found.")
    for i, f in enumerate(F, 1):
        L += [f"### {i}. [{f['severity']}] {f['area']}: {f['title']}", ""]
        if f["evidence"]:
            L.append(f"> {f['evidence']}")
            L.append("")
        L += [f"**Fix:** {f['fix']}", ""]
    return "\n".join(L)


def to_html(res, name="report"):
    md = to_markdown(res, name)
    body = []
    for line in md.split("\n"):
        e = html.escape(line)
        e = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", e)
        if line.startswith("### "):
            sev = re.search(r"\[(HIGH|MEDIUM|LOW)\]", line).group(1).lower()
            body.append(f'<h3 class="{sev}">{e[4:]}</h3>')
        elif line.startswith("## "):
            body.append(f"<h2>{e[3:]}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{e[2:]}</h1>")
        elif line.startswith("&gt; "):
            body.append(f"<blockquote>{e[5:]}</blockquote>")
        elif line.startswith("|") and not set(line) <= set("|-"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            body.append("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells) + "</tr>")
        elif line.strip() and not set(line) <= set("|-"):
            body.append(f"<p>{e}</p>")
    out = "\n".join(body)
    out = re.sub(r"((?:<tr>.*?</tr>\n?)+)", r"<table>\1</table>", out)
    css = ("body{font:15px/1.5 -apple-system,Segoe UI,sans-serif;max-width:820px;margin:24px auto;padding:0 16px;color:#1d1f24}"
           "h3{padding:6px 10px;border-radius:6px;font-size:15px} .high{background:#fde8e6} .medium{background:#fff4d6} .low{background:#eef2f6}"
           "blockquote{margin:6px 0;padding:6px 12px;border-left:3px solid #ccc;color:#555} table{border-collapse:collapse}"
           "td{border-bottom:1px solid #e5e5e5;padding:4px 10px}")
    return f"<!doctype html><meta charset='utf-8'><title>Audit: {html.escape(name)}</title><style>{css}</style>{out}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report")
    ap.add_argument("--context", help="optional file with facts about timing (e.g. when each field is recorded)")
    ap.add_argument("--format", choices=["md", "json", "html"], default="md")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    text = open(a.report).read()
    ctx = open(a.context).read() if a.context else ""
    res = audit(text, ctx)
    name = a.report.rsplit("/", 1)[-1]
    s = json.dumps(res, indent=1, default=str) if a.format == "json" else to_html(res, name) if a.format == "html" else to_markdown(res, name)
    (open(a.out, "w").write(s) if a.out else sys.stdout.write(s + "\n"))
    return 1 if any(f["severity"] == "HIGH" for f in res["findings"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
