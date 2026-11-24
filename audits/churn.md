# Audit: churn.md

**1 high, 3 medium, 2 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 120 · FP 80 · FN 1,080 · TN 22,720 (n = 24,000, 1,200 positives = 5.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.952 | 0.952 |
| precision | 0.600 | – |
| recall | 0.100 | – |
| f1 | 0.171 | – |
| specificity | 0.996 | – |
| majority-class baseline | 0.950 | |

## Findings

### 1. [HIGH] Baseline: Accuracy barely beats always predicting the majority class

> 95.2% accurate

**Fix:** Always predicting 'negative' scores 95.0%; the model adds only 0.2 points. Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.

### 2. [MEDIUM] Claim: 'Ready to ship' isn't supported by the metrics

> Recommendation: deploy now

**Fix:** With recall 0.10 and 0.2 points over the baseline, decide on business cost first (e.g. a cutoff that minimizes cost).

### 3. [MEDIUM] Leakage: 'logins_next_month' may leak post-prediction information

> logins_next_month

**Fix:** Check when 'logins_next_month' is recorded (next-period information). Keep it only if it's known at the prediction moment.

### 4. [MEDIUM] Split: Random split on data with a time order

> Data: 2 years of monthly snapshots, 120,000 subscriber-months, randomly split 80/20

**Fix:** Use a time-based split (train on the past, test on the future) to mimic deployment.

### 5. [LOW] Leakage: History feature 'support_tickets_last_90d' needs a cutoff date

> support_tickets_last_90d

**Fix:** Compute 'support_tickets_last_90d' only from events before the prediction moment (not as of today), or it leaks the label.

### 6. [LOW] Leakage: History feature 'payment_failures_last_6m' needs a cutoff date

> payment_failures_last_6m

**Fix:** Compute 'payment_failures_last_6m' only from events before the prediction moment (not as of today), or it leaks the label.
