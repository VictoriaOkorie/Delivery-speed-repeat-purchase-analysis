-- Step 2a. Database design for the delivery and repeat purchase project (SQLite)
--
-- A star schema: two fact tables and two lookup (dimension) tables.
--   fact_customers  one row per real customer, described by their FIRST order
--   fact_orders     one row per order
--   dim_state       Brazilian state code -> state name and region
--   dim_category    product category -> category number
--
-- The tables are filled by python/02_run_sql.py from the cleaned CSV files.

DROP TABLE IF EXISTS fact_customers;
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS dim_state;
DROP TABLE IF EXISTS dim_category;

CREATE TABLE dim_state (
    state_code  TEXT PRIMARY KEY,
    state_name  TEXT NOT NULL,
    region      TEXT NOT NULL
);

CREATE TABLE dim_category (
    category_id INTEGER PRIMARY KEY,
    category    TEXT UNIQUE NOT NULL
);

CREATE TABLE fact_orders (
    order_id                      TEXT PRIMARY KEY,
    customer_unique_id            TEXT NOT NULL,
    order_number                  INTEGER,      -- 1 = the customer's first order
    order_status                  TEXT,
    counts_as_purchase            INTEGER,      -- 0 if cancelled or unavailable
    order_purchase_timestamp      TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    delivery_days                 REAL,         -- purchase to doorstep
    promised_days                 INTEGER,      -- purchase to promised date
    days_vs_promise               INTEGER,      -- positive = late, negative = early
    is_late                       INTEGER,
    delivery_speed_band           TEXT,
    promise_band                  TEXT,
    order_value                   REAL,
    freight_value                 REAL,
    freight_share                 REAL,
    item_count                    INTEGER,
    category                      TEXT REFERENCES dim_category(category),
    customer_state                TEXT REFERENCES dim_state(state_code),
    seller_state                  TEXT REFERENCES dim_state(state_code),
    same_state                    INTEGER,
    payment_type                  TEXT,
    payment_installments          INTEGER,
    review_score                  INTEGER,
    has_comment                   INTEGER
);

CREATE TABLE fact_customers (
    customer_unique_id            TEXT PRIMARY KEY,
    first_order_id                TEXT REFERENCES fact_orders(order_id),
    order_purchase_timestamp      TEXT,
    first_purchase_month          TEXT,
    order_status                  TEXT,
    customer_state                TEXT REFERENCES dim_state(state_code),
    seller_state                  TEXT,
    same_state                    INTEGER,
    category                      TEXT REFERENCES dim_category(category),
    order_value                   REAL,
    freight_value                 REAL,
    freight_share                 REAL,
    item_count                    INTEGER,
    payment_type                  TEXT,
    payment_installments          INTEGER,
    delivery_days                 REAL,
    promised_days                 INTEGER,
    days_vs_promise               INTEGER,
    is_late                       INTEGER,
    delivery_speed_band           TEXT,
    promise_band                  TEXT,
    review_score                  INTEGER,
    has_comment                   INTEGER,
    in_study                      INTEGER,      -- 1 = delivered and watched for 180 days
    returned_within_180           INTEGER,      -- the main outcome
    returned                      INTEGER,      -- returned at any point in the data
    days_to_return                REAL,         -- first delivery to second purchase
    days_first_to_second_purchase REAL,
    second_order_value            REAL,
    made_third_purchase           INTEGER,
    days_second_to_third          REAL,
    total_orders                  INTEGER,
    total_spend                   REAL,
    days_observed                 REAL
);

CREATE INDEX idx_cust_study ON fact_customers(in_study);
CREATE INDEX idx_orders_customer ON fact_orders(customer_unique_id);
