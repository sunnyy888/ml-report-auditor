# Audit: returns.md

**4 high, 1 medium, 2 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 9,000 · FP 3,000 · FN 6,000 · TN 42,000 (n = 60,000, 15,000 positives = 25.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.850 | 0.850 |
| precision | 0.750 | 0.750 |
| recall | 0.600 | 0.600 |
| f1 | 0.667 | 0.720 |
| specificity | 0.933 | – |
| majority-class baseline | 0.750 | |

## Findings

### 1. [HIGH] Claim: Causal claim from a predictive model

> If we remove free shipping, returns would decrease by 20%.

**Fix:** Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare).

### 2. [HIGH] Leakage: 'refund_issued' leaks post-prediction information

> refund_issued

**Fix:** Check when 'refund_issued' is recorded (refunds follow the outcome). Keep it only if it's known at the prediction moment.

### 3. [HIGH] Leakage: Random row split while the same people appear many times

> Data: 300,000 orders, random split; 40% of orders come from repeat customers / Data: 300,000 orders, random split; 40% of orders come from repeat customers

**Fix:** Split by person (group split) or by time, so no one appears in both train and test; re-score on the clean split.

### 4. [HIGH] Matrix: Reported f1 doesn't match the confusion matrix

> F1 0.72

**Fix:** Recompute from the matrix: f1 = 0.667, not 0.720.

### 5. [MEDIUM] Claim: Causal claim from a predictive model

> Free shipping drives returns.

**Fix:** Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare).

### 6. [LOW] Baseline: No baseline given for an imbalanced problem

> Accuracy 85%

**Fix:** State the majority-class baseline (75.0%) next to accuracy.

### 7. [LOW] Leakage: History feature 'customer_past_return_rate' needs a cutoff date

> customer_past_return_rate

**Fix:** Compute 'customer_past_return_rate' only from events before the prediction moment (not as of today), or it leaks the label.
