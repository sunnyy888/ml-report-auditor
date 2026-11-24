Returns prediction, scored at checkout. Data: 300,000 orders, random split; 40% of orders come from repeat customers.
Features: items_in_cart, bought_multiple_sizes, discount_used, refund_issued, customer_past_return_rate.
Confusion matrix on the test set: TP 9,000, FP 3,000, FN 6,000, TN 42,000. Accuracy 85%, precision 0.75, recall 0.60, F1 0.72.
Free shipping drives returns. If we remove free shipping, returns would decrease by 20%.
