Churn model write-up. We predict on the 1st of each month which subscribers will cancel that month. Data: 2 years of monthly snapshots, 120,000 subscriber-months, randomly split 80/20.
Features: tenure_months, plan_price, support_tickets_last_90d, logins_next_month, payment_failures_last_6m.
Test set: TP 120, FP 80, FN 1,080, TN 22,720. The model is 95.2% accurate.
Recommendation: deploy now.
