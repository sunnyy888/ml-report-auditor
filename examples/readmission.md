# 30-day readmission model

Prediction is made at discharge. Follow-up visits take place 7 days after discharge.

## Features
- length_of_stay
- prior_admissions_count: admissions in the 12 months before this stay
- age
- follow_up_visit_attended: whether the patient attended the follow-up visit
- discharge_medications

## Test results
TP 410, FP 390, FN 190, TN 9,010 (10,000 discharges, held out by discharge date: train 2021-2022, test 2023).
Accuracy 94.2%, precision 0.51, recall 0.82, F1 0.63.

Longer stays lead to more readmissions.
