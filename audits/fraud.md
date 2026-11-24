# Audit: fraud.md

**0 high, 0 medium, 3 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 1,640 · FP 1,360 · FN 360 · TN 196,640 (n = 200,000, 2,000 positives = 1.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.991 | 0.991 |
| precision | 0.547 | 0.547 |
| recall | 0.820 | 0.820 |
| f1 | 0.656 | 0.656 |
| specificity | 0.993 | – |
| majority-class baseline | 0.990 | |

## Findings

### 1. [LOW] Baseline: Accuracy barely beats always predicting the majority class

> Accuracy 99.1%

**Fix:** Always predicting 'negative' scores 99.0%; the model adds only 0.1 points. Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.

### 2. [LOW] Leakage: History feature 'transactions_last_hour' needs a cutoff date

> transactions_last_hour

**Fix:** Compute 'transactions_last_hour' only from events before the prediction moment (not as of today), or it leaks the label.

### 3. [LOW] Leakage: History feature 'distance_from_previous_km' needs a cutoff date

> distance_from_previous_km

**Fix:** Compute 'distance_from_previous_km' only from events before the prediction moment (not as of today), or it leaks the label.
