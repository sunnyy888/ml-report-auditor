"""Tests for audit.py. Run: python3 test_audit.py"""
import json
import os

import audit as A

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, "examples")
ok = []


def check(name, cond, detail=""):
    ok.append(bool(cond))
    print("%s  %s%s" % ("PASS" if cond else "FAIL", name, (": " + detail) if detail else ""))


# 1. parsing units
check("numbers: thousands separators vs list commas", A.parse_matrix("TP 184, FP 60, FN 216, TN 3,540") == {"TP": 184, "FP": 60, "FN": 216, "TN": 3540})
check("matrix from an actual/predicted table", A.parse_matrix("actual_yes | 30 | 10\nactual_no | 5 | 955") == {"TP": 30, "FN": 10, "FP": 5, "TN": 955})
c = {k: [v for v, _ in vs] for k, vs in A.parse_claims("Accuracy 93.1%. Precision 0.82, recall 0.46. The model is 93% accurate.").items()}
check("claims: percents, proportions, and '93% accurate'", [round(v, 3) for v in c["accuracy"]] == [0.931, 0.93] and c["precision"] == [0.82] and c["recall"] == [0.46], str({k: v for k, v in c.items()}))
check("claims: a list comma is not a thousands separator", [v for v, _ in A.parse_claims("precision 0.51, recall 0.82, F1 0.63")["recall"]] == [0.82])
f = [n for n, _ in A.parse_features("Features: fare class, days booked ahead, checked_in_online, bag fee paid.")]
check("features from a comma list", f == ["fare class", "days booked ahead", "checked_in_online", "bag fee paid"], str(f))
pred, facts = A.parse_timing("The prediction is made 72 hours before departure. Online check-in opens 24 hours before departure.")
check("timing: prediction moment and availability fact", pred["hours_before"] == 72 and facts[0]["hours_before"] == 24)
m = A.metrics_from({"TP": 184, "FP": 60, "FN": 216, "TN": 3540})
check("metrics recomputed (HW4 4D): accuracy .931, precision .754, recall .46, baseline .90",
      abs(m["accuracy"] - 0.931) < 1e-9 and abs(m["precision"] - 184 / 244) < 1e-12 and abs(m["recall"] - 0.46) < 1e-12 and m["baseline"] == 0.9)

# 2. planted errors in every example report are caught, and nothing extra fires where it shouldn't
exp = json.load(open(os.path.join(EX, "expected.json")))
caught = planted = 0
for fname, spec in exp.items():
    text = open(os.path.join(EX, fname)).read()
    ctx = open(os.path.join(EX, spec["context"])).read() if spec.get("context") else ""
    res = A.audit(text, ctx)
    blob = [(f["severity"], f["area"], (f["title"] + " " + f["evidence"] + " " + f["fix"]).lower()) for f in res["findings"]]
    missing = [m for m in spec["must"] if not any(s == m[0] and a == m[1] and m[2].lower() in t for s, a, t in blob)]
    planted += len(spec["must"])
    caught += len(spec["must"]) - len(missing)
    bad = [w for w in spec.get("must_not", []) if any(w.lower() in (a.lower() + " " + t) for s, a, t in blob if s in ("HIGH", "MEDIUM"))]
    highs = sum(s == "HIGH" for s, _, _ in blob)
    ok_high = highs <= spec.get("max_high", 99)
    check(f"{fname}: all planted problems caught, no false alarms", not missing and not bad and ok_high,
          f"{len(spec['must']) - len(missing)}/{len(spec['must'])} caught" + (f"; missing {missing}" if missing else "") + (f"; false alarm on {bad}" if bad else "") + ("" if ok_high else f"; {highs} HIGH on a clean report"))
check("overall recall on planted problems = 100%", caught == planted, f"{caught}/{planted}")

# 3. HW4 4D: the three rubric problems (leakage, matrix, claim) are all HIGH
res = A.audit(open(os.path.join(EX, "hw4_4d.md")).read(), open(os.path.join(EX, "hw4_4d.context.md")).read())
areas = {f["area"] for f in res["findings"] if f["severity"] == "HIGH"}
check("HW4 4D: leakage, matrix and claim problems all flagged HIGH", {"Leakage", "Matrix", "Claim"} <= areas, ", ".join(sorted(areas)))

# 4. outputs: markdown and HTML render, CLI exit code signals HIGH findings
md, html = A.to_markdown(res, "hw4_4d.md"), A.to_html(res, "hw4_4d.md")
check("markdown report has the recomputed table and numbered findings", "| precision | 0.754 | 0.820 |" in md and "### 1. [HIGH]" in md)
check("HTML report renders with severity styles", html.startswith("<!doctype html>") and 'class="high"' in html and "<table>" in html)
check("CLI exits 1 when HIGH findings exist, 0 for the clean report",
      A.main([os.path.join(EX, "hw4_4d.md"), "--out", os.devnull]) == 1 and A.main([os.path.join(EX, "fraud.md"), "--out", os.devnull]) == 0)
print("\n%d/%d PASS" % (sum(ok), len(ok)))
raise SystemExit(0 if all(ok) else 1)
