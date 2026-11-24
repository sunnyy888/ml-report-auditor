# ML Report Auditor 🔍

HW4 4D as a tool. `audit.py` reads a model write-up (free text plus a confusion matrix) and flags the problems a careful reviewer would catch. It uses only the standard library.

| Check | What it does |
|---|---|
| **Matrix** | Recomputes accuracy, precision, recall, F1 and specificity from TP/FP/FN/TN and flags every reported number that doesn't match (tolerance 0.005). Also flags precision reported without recall. |
| **Baseline** | Compares accuracy with always predicting the majority class, and downgrades the flag if the report already acknowledges the baseline. |
| **Leakage** | Flags features that only exist after the prediction moment. It parses statements like "prediction 72 hours before departure" and "check-in opens 24 hours before departure", in the report or a `--context` file. Also flags names that encode the outcome (`refund_issued`, `collections_status`, `days_until…`) and history counts that need a cutoff date. |
| **Split** | Flags random row splits when the same people repeat (group leakage), and random splits on time-ordered data. |
| **Claims** | Flags causal language drawn from a predictive model ("causes", "drives", "would cut … by", "if we remove…"); hedged statements are skipped. Also flags "ready to ship" when recall or the lift over baseline is weak. |

Findings are ranked HIGH, MEDIUM or LOW, each with the quoted evidence and a concrete fix.

## Usage

```
python3 audit.py examples/hw4_4d.md --context examples/hw4_4d.context.md            # markdown to stdout
python3 audit.py examples/returns.md --format html --out audits/returns.html        # also: --format json
```

The exit code is 1 when there are HIGH findings, so it can gate a CI pipeline.

## Example: the HW4 4D report

The agent's write-up, verbatim: [`examples/hw4_4d.md`](examples/hw4_4d.md). It's audited with two timing facts from the assignment: the prediction is made 72 h before departure, and check-in opens at 24 h. Result in [`audits/hw4_4d.md`](audits/hw4_4d.md):

| # | Severity | Finding |
|---|---|---|
| 1 | HIGH | Causal claim: "bag fees cause no-shows; dropping the bag fee would cut no-shows by a third" |
| 2 | HIGH | `checked_in_online` isn't available 72 h out (check-in opens at 24 h) |
| 3 | HIGH | Random split by booking while frequent flyers make up 38% of bookings |
| 4 | HIGH | Precision reported as 0.82; the matrix gives 184/244 = **0.754** |
| 5 | HIGH | Precision without recall: recall is **0.46** |
| 6 | MEDIUM | 93.1% accuracy against a 90.0% majority baseline |
| 7 | MEDIUM | "Ready to ship" with recall 0.46 |
| 8 | LOW | "Past no-show count" must be computed only from before the booking date |

These cover all three rubric problems (leakage, matrix, claim) and more.

## Five more reports with planted errors

| Report | Planted problems | Caught |
|---|---|---|
| `loan_default.md` | wrong accuracy (91.0% vs 92.6%), `collections_status`, random split over 2019–2023, causal rate claim | 4/4 |
| `churn.md` | 95.2% accuracy vs a 95.0% baseline, `logins_next_month`, random split of monthly snapshots, "deploy now" | 4/4 |
| `readmission.md` | wrong recall and F1, `follow_up_visit_attended` (visits happen 7 days after discharge), "longer stays lead to…" | 4/4 |
| `returns.md` | wrong F1, `refund_issued`, random split with 40% repeat customers, "free shipping drives returns" | 4/4 |
| `fraud.md` | **none:** a clean control report | 0 HIGH / 0 MEDIUM flags |

## Tests

```
python3 test_audit.py
```

There are 18 checks:
- **Parsing:** thousands separators vs list commas, table-format matrices, "93% accurate", feature lists and timing facts.
- **Metrics:** the HW4 metrics are recomputed exactly.
- **Planted problems:** every planted problem in all six reports is caught (**24/24**), with no false alarms where the expectations forbid them.
- **HW4 4D:** leakage, matrix and claim are all HIGH.
- **Output:** markdown and HTML render, and the CLI exit codes are right.

**Known limits:** it's a heuristic reader. It needs a confusion matrix in a recognizable form, and timing comparisons need the prediction moment and the field timing stated in words. It flags anything suspicious for a human to judge rather than claiming certainty.
