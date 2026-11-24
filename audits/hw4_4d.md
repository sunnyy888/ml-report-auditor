# Audit: hw4_4d.md

**5 high, 2 medium, 1 low** severity findings.

## Metrics recomputed from the confusion matrix

TP 184 · FP 60 · FN 216 · TN 3,540 (n = 4,000, 400 positives = 10.0%)

| Metric | Recomputed | Reported |
|---|---|---|
| accuracy | 0.931 | 0.931, 0.930 |
| precision | 0.754 | 0.820 |
| recall | 0.460 | – |
| f1 | 0.571 | – |
| specificity | 0.983 | – |
| majority-class baseline | 0.900 | |

## Findings

### 1. [HIGH] Claim: Causal claim from a predictive model

> Feature importance shows that bag fees cause no-shows; dropping the bag fee would cut no-shows by a third.

**Fix:** Restate it as an association. To learn the effect of a change, run a randomized experiment (e.g. change it for a random group and compare).

### 2. [HIGH] Leakage: 'checked_in_online' isn't available when the prediction is made

> Online check-in opens 24 hours before departure / prediction: prediction 72 hours before departure

**Fix:** Drop 'checked_in_online' or replace it with its value as of the prediction moment (72 h before departure); it only exists 24 h before departure.

### 3. [HIGH] Leakage: Random row split while the same people appear many times

> Data: all 20,000 labeled bookings, random 80/20 split by booking (16,000 train, 4,000 test) / Frequent flyers (5 or more bookings) make up 38% of all bookings

**Fix:** Split by person (group split) or by time, so no one appears in both train and test; re-score on the clean split.

### 4. [HIGH] Matrix: Reported precision doesn't match the confusion matrix

> Precision 0.82

**Fix:** Recompute from the matrix: precision = 0.754, not 0.820.

### 5. [HIGH] Matrix: Precision reported without recall

> Precision 0.82

**Fix:** Report recall too: 184/400 = 0.460. The model misses 54% of actual positives.

### 6. [MEDIUM] Baseline: Accuracy barely beats always predicting the majority class

> Accuracy 93.1%

**Fix:** Always predicting 'negative' scores 90.0%; the model adds only 3.1 points. Lead with recall/precision (or cost), not accuracy, when classes are imbalanced.

### 7. [MEDIUM] Claim: 'Ready to ship' isn't supported by the metrics

> Summary: the model is 93% accurate and ready to ship

**Fix:** With recall 0.46 and 3.1 points over the baseline, decide on business cost first (e.g. a cutoff that minimizes cost).

### 8. [LOW] Leakage: History feature 'passenger's past no-show count' needs a cutoff date

> passenger's past no-show count

**Fix:** Compute 'passenger's past no-show count' only from events before the prediction moment (not as of today), or it leaks the label.
