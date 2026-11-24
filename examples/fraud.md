# Card fraud model

Scores are produced at authorization time. Training data: transactions from January to September; test data: October to December (time-based split, no overlap).

## Features
- amount: authorization amount
- merchant_category: from the authorization request
- transactions_last_hour: velocity over the prior hour
- distance_from_previous_km: distance from the previous transaction

## Test results (200,000 transactions)
TP 1,640, FP 1,360, FN 360, TN 196,640.
Accuracy 99.1% (the always-legitimate baseline is 99.0%), precision 0.547, recall 0.82, F1 0.656.

High velocity is associated with fraud; this is a predictive pattern, not a causal claim. We recommend a cost-based cutoff before launch.
