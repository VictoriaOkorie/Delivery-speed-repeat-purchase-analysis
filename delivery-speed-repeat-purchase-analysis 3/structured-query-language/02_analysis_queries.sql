-- Step 2b. Analysis queries (SQLite)
-- Each query starts with a "-- name:" line. python/02_run_sql.py runs them in order
-- and saves each result to outputs/query_results/<name>.csv
--
-- Trick used throughout: returned_within_180 is 1 or 0, so AVG() of it is the return rate.
-- The main comparison group is in_study = 1: customers whose first order was delivered
-- and who could be watched for a full 180 days afterwards.


-- name: q01_overall_kpis
-- The headline numbers for the whole business.
SELECT
    (SELECT COUNT(*) FROM fact_customers)                                        AS customers,
    (SELECT COUNT(*) FROM fact_orders)                                           AS orders,
    ROUND((SELECT AVG(total_orders > 1) * 100 FROM fact_customers), 2)          AS pct_customers_with_2_plus_orders,
    (SELECT COUNT(*) FROM fact_customers WHERE in_study = 1)                     AS study_customers,
    ROUND((SELECT AVG(returned_within_180) * 100 FROM fact_customers WHERE in_study = 1), 2) AS return_rate_180_pct,
    ROUND((SELECT AVG(delivery_days) FROM fact_customers WHERE in_study = 1), 1) AS avg_first_delivery_days,
    ROUND((SELECT AVG(is_late) * 100 FROM fact_customers WHERE in_study = 1), 1) AS pct_first_orders_late,
    ROUND((SELECT AVG(review_score) FROM fact_customers WHERE in_study = 1), 2)  AS avg_first_review;


-- name: q02_return_by_delivery_speed
-- The core question: does a faster first delivery bring customers back?
SELECT
    delivery_speed_band,
    COUNT(*)                                  AS customers,
    SUM(returned_within_180)                  AS returned,
    ROUND(AVG(returned_within_180) * 100, 2)  AS return_rate_pct,
    ROUND(AVG(review_score), 2)               AS avg_review,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_customers_pct
FROM fact_customers
WHERE in_study = 1
GROUP BY delivery_speed_band
ORDER BY delivery_speed_band;


-- name: q03_return_late_vs_on_time
-- Did breaking the delivery promise matter?
SELECT
    CASE is_late WHEN 1 THEN 'Late' ELSE 'On time or early' END AS first_delivery,
    COUNT(*)                                  AS customers,
    SUM(returned_within_180)                  AS returned,
    ROUND(AVG(returned_within_180) * 100, 2)  AS return_rate_pct,
    ROUND(AVG(review_score), 2)               AS avg_review,
    ROUND(AVG(review_score <= 2) * 100, 1)    AS pct_reviews_1_or_2_stars
FROM fact_customers
WHERE in_study = 1
GROUP BY is_late;


-- name: q04_return_by_promise_gap
-- How early or late against the promised date.
SELECT
    promise_band,
    COUNT(*)                                  AS customers,
    ROUND(AVG(returned_within_180) * 100, 2)  AS return_rate_pct,
    ROUND(AVG(review_score), 2)               AS avg_review,
    ROUND(AVG(delivery_days), 1)              AS avg_delivery_days
FROM fact_customers
WHERE in_study = 1
GROUP BY promise_band
ORDER BY promise_band;


-- name: q05_review_by_delivery_speed
-- The mechanism: slow delivery shows up in the review first. Uses all delivered first orders.
SELECT
    delivery_speed_band,
    COUNT(*)                                  AS customers,
    ROUND(AVG(review_score), 2)               AS avg_review,
    ROUND(AVG(review_score = 5) * 100, 1)     AS pct_5_stars,
    ROUND(AVG(review_score <= 2) * 100, 1)    AS pct_1_or_2_stars
FROM fact_customers
WHERE order_status = 'delivered' AND delivery_days IS NOT NULL AND review_score IS NOT NULL
GROUP BY delivery_speed_band
ORDER BY delivery_speed_band;


-- name: q06_return_by_review_score
SELECT
    review_score,
    COUNT(*)                                  AS customers,
    ROUND(AVG(returned_within_180) * 100, 2)  AS return_rate_pct
FROM fact_customers
WHERE in_study = 1 AND review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;


-- name: q07_region_scorecard
-- JOIN to the state lookup table, then roll up by region.
SELECT
    s.region,
    COUNT(*)                                       AS customers,
    ROUND(AVG(c.delivery_days), 1)                 AS avg_delivery_days,
    ROUND(AVG(c.is_late) * 100, 1)                 AS pct_late,
    ROUND(AVG(c.returned_within_180) * 100, 2)     AS return_rate_pct
FROM fact_customers AS c
JOIN dim_state AS s ON s.state_code = c.customer_state
WHERE c.in_study = 1
GROUP BY s.region
ORDER BY avg_delivery_days;


-- name: q08_second_purchase_window
-- When do returning customers come back? 30-day buckets after the first delivery,
-- with a running total (window function) to show how fast the window closes.
WITH returners AS (
    SELECT
        CASE
            WHEN days_to_return <= 30  THEN '01. 0 to 30 days'
            WHEN days_to_return <= 60  THEN '02. 31 to 60 days'
            WHEN days_to_return <= 90  THEN '03. 61 to 90 days'
            WHEN days_to_return <= 120 THEN '04. 91 to 120 days'
            WHEN days_to_return <= 180 THEN '05. 121 to 180 days'
            WHEN days_to_return <= 270 THEN '06. 181 to 270 days'
            WHEN days_to_return <= 365 THEN '07. 271 to 365 days'
            ELSE '08. More than 365 days'
        END AS days_after_first_delivery
    FROM fact_customers
    WHERE returned = 1 AND days_observed >= 365   -- only customers we could watch for a full year
)
SELECT
    days_after_first_delivery,
    COUNT(*) AS returning_customers,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_pct,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY days_after_first_delivery)
          / SUM(COUNT(*)) OVER (), 1)                  AS cumulative_share_pct
FROM returners
GROUP BY days_after_first_delivery
ORDER BY days_after_first_delivery;


-- name: q09_third_purchase_by_return_speed
-- Loyalty: do customers who come back quickly go on to buy a third time?
SELECT
    CASE
        WHEN days_to_return <= 30 THEN '1. Returned within 30 days'
        WHEN days_to_return <= 90 THEN '2. Returned in 31 to 90 days'
        ELSE '3. Returned after 90 days'
    END AS second_purchase_timing,
    COUNT(*)                                   AS returning_customers,
    SUM(made_third_purchase)                   AS made_third_purchase,
    ROUND(AVG(made_third_purchase) * 100, 1)   AS third_purchase_rate_pct
FROM fact_customers
WHERE returned = 1
GROUP BY second_purchase_timing
ORDER BY second_purchase_timing;


-- name: q10_customer_value
-- What a returning customer is worth compared with a one-time buyer.
SELECT
    CASE WHEN returned = 1 THEN 'Returned' ELSE 'One order only' END AS customer_type,
    COUNT(*)                         AS customers,
    ROUND(AVG(total_orders), 2)      AS avg_orders,
    ROUND(AVG(total_spend), 2)       AS avg_total_spend_brl,
    ROUND(SUM(total_spend), 0)       AS total_spend_brl,
    ROUND(100.0 * SUM(total_spend) / SUM(SUM(total_spend)) OVER (), 1) AS share_of_revenue_pct
FROM fact_customers
WHERE in_study = 1
GROUP BY customer_type;


-- name: q11_categories_ranked
-- Which first-purchase categories bring people back? HAVING keeps groups big enough to trust.
SELECT
    c.category,
    d.category_id,
    COUNT(*)                                       AS customers,
    ROUND(AVG(c.returned_within_180) * 100, 2)     AS return_rate_pct,
    ROUND(AVG(c.delivery_days), 1)                 AS avg_delivery_days,
    RANK() OVER (ORDER BY AVG(c.returned_within_180) DESC) AS return_rank
FROM fact_customers AS c
LEFT JOIN dim_category AS d ON d.category = c.category
WHERE c.in_study = 1
GROUP BY c.category, d.category_id
HAVING COUNT(*) >= 1000
ORDER BY return_rank;


-- name: q12_data_quality_checks
-- Prove the cleaning worked. Every value here should be 0.
SELECT 'Duplicate customers' AS check_name,
       COUNT(*) - COUNT(DISTINCT customer_unique_id) AS problems FROM fact_customers
UNION ALL
SELECT 'Duplicate orders', COUNT(*) - COUNT(DISTINCT order_id) FROM fact_orders
UNION ALL
SELECT 'Study customers with missing outcome', COUNT(*) FROM fact_customers
       WHERE in_study = 1 AND returned_within_180 IS NULL
UNION ALL
SELECT 'Negative delivery times', COUNT(*) FROM fact_orders WHERE delivery_days <= 0
UNION ALL
SELECT 'Customer states missing from lookup', COUNT(*) FROM fact_customers c
       LEFT JOIN dim_state s ON s.state_code = c.customer_state WHERE s.state_code IS NULL
UNION ALL
SELECT 'Returns dated before first delivery', COUNT(*) FROM fact_customers WHERE days_to_return < 0;
