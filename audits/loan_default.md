# Audit: loan_default.md

**3 high, 2 medium, 1 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 610 · FP 290 · FN 640 · TN 10,960 (n = 12,500, 1,250 positives = 10.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.926 | 0.910 |
| precision | 0.678 | 0.680 |
| recall | 0.488 | 0.490 |
| f1 | 0.567 | – |
| specificity | 0.974 | – |
| majority-class baseline | 0.900 | |

## Findings

### 1. [HIGH] Claim: Causal claim from a predictive model

> ## Takeaways
Higher interest rates cause defaults, so lowering rates for risky applicants would reduce losses.

**Fix:** Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare).

### 2. [HIGH] Leakage: 'collections_status' leaks post-prediction information

> collections_status

**Fix:** Check when 'collections_status' is recorded (loans go to collections because they default). Keep it only if it's known at the prediction moment.

### 3. [HIGH] Matrix: Reported accuracy doesn't match the confusion matrix

> Accuracy is 91.0%

**Fix:** Recompute from the matrix: accuracy = 0.926, not 0.910.

### 4. [MEDIUM] Baseline: Accuracy barely beats always predicting the majority class

> Accuracy is 91.0%

**Fix:** Always predicting 'negative' scores 90.0%; the model adds only 2.6 points. Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.

### 5. [MEDIUM] Split: Random split on data with a time order

> Data: 50,000 loans issued 2019-2023, with a random 75/25 split

**Fix:** Use a time-based split (train on the past, test on the future) to mimic deployment.

### 6. [LOW] Leakage: History feature 'months_since_last_delinquency' needs a cutoff date

> months_since_last_delinquency

**Fix:** Compute 'months_since_last_delinquency' only from events before the prediction moment (not as of today), or it leaks the label.
