# Audit: readmission.md

**4 high, 1 medium, 1 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 410 · FP 390 · FN 190 · TN 9,010 (n = 10,000, 600 positives = 6.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.942 | 0.942 |
| precision | 0.512 | 0.510 |
| recall | 0.683 | 0.820 |
| f1 | 0.586 | 0.630 |
| specificity | 0.959 | – |
| majority-class baseline | 0.940 | |

## Findings

### 1. [HIGH] Baseline: Accuracy barely beats always predicting the majority class

> Accuracy 94.2%

**Fix:** Always predicting 'negative' scores 94.0%; the model adds only 0.2 points. Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.

### 2. [HIGH] Leakage: 'follow_up_visit_attended' isn't available when the prediction is made

> Follow-up visits take place 7 days after discharge / prediction: Prediction is made at discharge

**Fix:** Drop 'follow_up_visit_attended' or replace it with its value as of the prediction moment (discharge); it only exists -168 h before discharge.

### 3. [HIGH] Matrix: Reported recall doesn't match the confusion matrix

> recall 0.82

**Fix:** Recompute from the matrix: recall = 0.683, not 0.820.

### 4. [HIGH] Matrix: Reported f1 doesn't match the confusion matrix

> F1 0.63

**Fix:** Recompute from the matrix: f1 = 0.586, not 0.630.

### 5. [MEDIUM] Claim: Causal claim from a predictive model

> Longer stays lead to more readmissions.

**Fix:** Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare).

### 6. [LOW] Leakage: History feature 'prior_admissions_count' needs a cutoff date

> prior_admissions_count

**Fix:** Compute 'prior_admissions_count' only from events before the prediction moment (not as of today), or it leaks the label.
