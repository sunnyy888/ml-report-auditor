# Loan default model (v2)

We predict at application time whether a personal loan will default within 24 months. Data: 50,000 loans issued 2019-2023, with a random 75/25 split.

## Features
- credit_score: bureau score pulled at application
- annual_income: stated on the application
- loan_amount: requested amount
- collections_status: current status in the collections system
- months_since_last_delinquency: from the bureau report

## Results (12,500 test loans)
TP = 610, FP = 290, FN = 640, TN = 10,960.
Accuracy is 91.0%, precision 0.68 and recall 0.49.

## Takeaways
Higher interest rates cause defaults, so lowering rates for risky applicants would reduce losses.
