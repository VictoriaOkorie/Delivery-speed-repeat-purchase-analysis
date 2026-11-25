"""
Step 1. Clean the Olist Brazilian e-commerce data.

Does a slow first delivery stop a customer from coming back?
This script turns 8 raw tables into 4 tidy tables that answer that question.

Run from the project folder:
    python3 python/01_clean_data.py

Outputs (data/clean/):
    fact_orders.csv          one row per order, with delivery and review details
    fact_customers.csv       one row per customer, built from their first order
    dim_state.csv            Brazilian state code, name and region
    dim_category.csv         product category in Portuguese and English
    cleaning_log.txt         every decision and how many rows it touched
"""
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEAN = ROOT / "data" / "clean"
CLEAN.mkdir(parents=True, exist_ok=True)

log = []
def note(msg):
    print(msg)
    log.append(msg)

# The data stops in late August 2018 (September and October hold only 20 stray orders).
# Every follow-up window is measured up to this date.
DATA_END = pd.Timestamp("2018-09-01")
WINDOW_DAYS = 180   # how long we watch each customer after their first delivery

# ---------------------------------------------------------------- 1. Load
dates = ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"]
orders = pd.read_csv(RAW / "olist_orders_dataset.csv", parse_dates=dates)
customers = pd.read_csv(RAW / "olist_customers_dataset.csv")
items = pd.read_csv(RAW / "olist_order_items_dataset.csv")
payments = pd.read_csv(RAW / "olist_order_payments_dataset.csv")
reviews = pd.read_csv(RAW / "olist_order_reviews_dataset.csv",
                      parse_dates=["review_creation_date", "review_answer_timestamp"])
products = pd.read_csv(RAW / "olist_products_dataset.csv")
sellers = pd.read_csv(RAW / "olist_sellers_dataset.csv")
translate = pd.read_csv(RAW / "product_category_name_translation.csv")

note(f"Loaded {len(orders):,} orders, {len(items):,} order items, {len(reviews):,} reviews, "
     f"{customers.customer_unique_id.nunique():,} unique customers.")

# ---------------------------------------------------------------- 2. The customer identifier trap
# customer_id changes with every order. customer_unique_id is the real person.
# Using customer_id would make every customer look like a one-time buyer.
orders = orders.merge(customers, on="customer_id", how="left")
note(f"customer_id has {customers.customer_id.nunique():,} values but there are only "
     f"{customers.customer_unique_id.nunique():,} real people (customer_unique_id). "
     "All repeat purchase logic uses customer_unique_id.")

# ---------------------------------------------------------------- 3. Trim to the reliable date range
before = len(orders)
orders = orders[orders.order_purchase_timestamp < DATA_END].copy()
note(f"Removed {before - len(orders):,} orders placed after {DATA_END.date()} (the data trails off).")

# ---------------------------------------------------------------- 4. Order-level facts
# Basket value, freight and item count
basket = items.groupby("order_id").agg(
    order_value=("price", "sum"),
    freight_value=("freight_value", "sum"),
    item_count=("order_item_id", "count"),
    seller_id=("seller_id", "first"),
    product_id=("product_id", "first"),
).reset_index()

# Main category = category of the first item, translated into English
products = products.merge(translate, on="product_category_name", how="left")
products["category"] = (products["product_category_name_english"]
                        .fillna(products["product_category_name"])
                        .fillna("unknown")
                        .str.replace("_", " "))
basket = basket.merge(products[["product_id", "category"]], on="product_id", how="left")
basket = basket.merge(sellers[["seller_id", "seller_state"]], on="seller_id", how="left")

# Main payment type = the payment with the largest value
pay = (payments.sort_values("payment_value", ascending=False)
       .drop_duplicates("order_id")[["order_id", "payment_type", "payment_installments"]])
pay["payment_type"] = pay["payment_type"].replace({"boleto": "bank slip (boleto)",
                                                    "credit_card": "credit card",
                                                    "debit_card": "debit card",
                                                    "not_defined": "unknown"})

# Reviews: 547 orders have more than one review; keep the most recent answer
dupes = reviews.order_id.duplicated(keep=False).sum()
reviews = reviews.sort_values("review_answer_timestamp").drop_duplicates("order_id", keep="last")
reviews["has_comment"] = reviews["review_comment_message"].notna().astype(int)
note(f"{dupes:,} review rows belonged to orders with more than one review; kept the latest per order.")

orders = (orders.merge(basket, on="order_id", how="left")
                .merge(pay, on="order_id", how="left")
                .merge(reviews[["order_id", "review_score", "has_comment", "review_creation_date"]],
                       on="order_id", how="left"))

# Delivery measures
day = 86400
orders["delivery_days"] = (orders.order_delivered_customer_date - orders.order_purchase_timestamp).dt.total_seconds() / day
orders["promised_days"] = (orders.order_estimated_delivery_date - orders.order_purchase_timestamp.dt.normalize()).dt.days
# Positive = late, negative = early. Compared by calendar date because the promise is a date, not a time.
orders["days_vs_promise"] = (orders.order_delivered_customer_date.dt.normalize() - orders.order_estimated_delivery_date).dt.days
orders["is_late"] = (orders["days_vs_promise"] > 0).astype("Int64")
orders.loc[orders.order_delivered_customer_date.isna(), "is_late"] = pd.NA

# Data errors: a delivery time of zero or below is impossible
bad = (orders.delivery_days <= 0).sum()
note(f"{bad} orders had a delivery date on or before the purchase date; delivery fields set to missing.")
orders.loc[orders.delivery_days <= 0, ["delivery_days", "days_vs_promise", "is_late"]] = np.nan

def speed_band(d):
    if pd.isna(d): return None
    if d <= 7: return "1. Within 7 days"
    if d <= 14: return "2. 8 to 14 days"
    if d <= 21: return "3. 15 to 21 days"
    if d <= 30: return "4. 22 to 30 days"
    return "5. More than 30 days"
orders["delivery_speed_band"] = orders.delivery_days.apply(speed_band)

def promise_band(v):
    if pd.isna(v): return None
    if v <= -15: return "1. 15 or more days early"
    if v <= -8: return "2. 8 to 14 days early"
    if v <= 0: return "3. 0 to 7 days early"
    if v <= 7: return "4. 1 to 7 days late"
    return "5. More than 7 days late"
orders["promise_band"] = orders.days_vs_promise.apply(promise_band)

orders["same_state"] = (orders.seller_state == orders.customer_state).astype("Int64")
orders["freight_share"] = orders.freight_value / (orders.order_value + orders.freight_value)

# Order sequence for each real customer
orders = orders.sort_values(["customer_unique_id", "order_purchase_timestamp"])
orders["order_number"] = orders.groupby("customer_unique_id").cumcount() + 1
orders["counts_as_purchase"] = (~orders.order_status.isin(["canceled", "unavailable"])).astype(int)

# ---------------------------------------------------------------- 5. Customer-level table
first = orders[orders.order_number == 1].copy()
note(f"{len(first):,} customers in total.")

# Repeat purchases that could have been influenced by the first delivery:
# a later, non-cancelled order placed AFTER the first order arrived.
later = orders[(orders.order_number > 1) & (orders.counts_as_purchase == 1)][
    ["customer_unique_id", "order_purchase_timestamp", "order_value"]]
pairs = first[["customer_unique_id", "order_purchase_timestamp", "order_delivered_customer_date"]].merge(
    later, on="customer_unique_id", suffixes=("_first", ""))
pairs["before_delivery"] = (pairs.order_delivered_customer_date.isna() |
                            (pairs.order_purchase_timestamp <= pairs.order_delivered_customer_date))
note(f"{pairs.before_delivery.sum():,} later orders were placed before the first order arrived "
     "(mostly same-day split baskets). They are not counted as returns, because the delivery "
     "experience could not have influenced them.")
after = pairs[~pairs.before_delivery].copy()
after["days_after_delivery"] = (after.order_purchase_timestamp - after.order_delivered_customer_date).dt.total_seconds() / day
after["days_after_first_purchase"] = (after.order_purchase_timestamp - after.order_purchase_timestamp_first).dt.total_seconds() / day
after = after.sort_values(["customer_unique_id", "order_purchase_timestamp"])
after["return_number"] = after.groupby("customer_unique_id").cumcount() + 1

second = after[after.return_number == 1].set_index("customer_unique_id")
third = after[after.return_number == 2].set_index("customer_unique_id")

first = first.set_index("customer_unique_id")
first["returned"] = first.index.isin(second.index).astype(int)
first["days_to_return"] = second["days_after_delivery"]
first["days_first_to_second_purchase"] = second["days_after_first_purchase"]
first["second_order_value"] = second["order_value"]
first["made_third_purchase"] = first.index.isin(third.index).astype(int)
first["days_second_to_third"] = (third["order_purchase_timestamp"] - second["order_purchase_timestamp"]).dt.total_seconds() / day

totals = orders[orders.counts_as_purchase == 1].groupby("customer_unique_id").agg(
    total_orders=("order_id", "count"), total_spend=("order_value", "sum"))
first = first.join(totals)
first["total_orders"] = first["total_orders"].fillna(0).astype(int)
first["total_spend"] = first["total_spend"].fillna(0)

# Follow-up time available after the first delivery (for survival analysis)
first["days_observed"] = (DATA_END - first.order_delivered_customer_date).dt.total_seconds() / day

# The fair comparison group: first order delivered, and at least 180 days of follow-up
first["in_study"] = ((first.order_status == "delivered") &
                     first.delivery_days.notna() &
                     (first.days_observed >= WINDOW_DAYS)).astype(int)
first["returned_within_180"] = ((first.returned == 1) & (first.days_to_return <= WINDOW_DAYS)).astype(int)
first.loc[first.in_study == 0, "returned_within_180"] = np.nan

delivered_ok = (first.order_status == "delivered") & first.delivery_days.notna()
n_not_delivered = (~delivered_ok).sum()
n_short = (delivered_ok & (first.days_observed < WINDOW_DAYS)).sum()
note(f"Study group: {first.in_study.sum():,} customers. Left out {n_not_delivered:,} whose first order "
     f"was never delivered (or has no delivery date) and {n_short:,} delivered too recently to watch for {WINDOW_DAYS} days.")
note(f"Within the study group, {first.loc[first.in_study==1,'returned_within_180'].sum():,.0f} customers "
     f"returned within {WINDOW_DAYS} days ({first.loc[first.in_study==1,'returned_within_180'].mean():.2%}).")

first["first_purchase_month"] = first.order_purchase_timestamp.dt.to_period("M").astype(str)
first = first.reset_index()

# ---------------------------------------------------------------- 6. Lookup tables
states = pd.DataFrame([
    ("AC","Acre","North"),("AL","Alagoas","Northeast"),("AM","Amazonas","North"),("AP","Amapá","North"),
    ("BA","Bahia","Northeast"),("CE","Ceará","Northeast"),("DF","Federal District","Central-West"),
    ("ES","Espírito Santo","Southeast"),("GO","Goiás","Central-West"),("MA","Maranhão","Northeast"),
    ("MG","Minas Gerais","Southeast"),("MS","Mato Grosso do Sul","Central-West"),("MT","Mato Grosso","Central-West"),
    ("PA","Pará","North"),("PB","Paraíba","Northeast"),("PE","Pernambuco","Northeast"),("PI","Piauí","Northeast"),
    ("PR","Paraná","South"),("RJ","Rio de Janeiro","Southeast"),("RN","Rio Grande do Norte","Northeast"),
    ("RO","Rondônia","North"),("RR","Roraima","North"),("RS","Rio Grande do Sul","South"),
    ("SC","Santa Catarina","South"),("SE","Sergipe","Northeast"),("SP","São Paulo","Southeast"),
    ("TO","Tocantins","North")], columns=["state_code", "state_name", "region"])
cats = products[["category"]].drop_duplicates().sort_values("category").reset_index(drop=True)
cats.insert(0, "category_id", range(1, len(cats) + 1))

# ---------------------------------------------------------------- 7. Save
order_cols = ["order_id", "customer_unique_id", "order_number", "order_status", "counts_as_purchase",
              "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date",
              "delivery_days", "promised_days", "days_vs_promise", "is_late", "delivery_speed_band",
              "promise_band", "order_value", "freight_value", "freight_share", "item_count", "category",
              "customer_state", "seller_state", "same_state", "payment_type", "payment_installments",
              "review_score", "has_comment"]
orders[order_cols].to_csv(CLEAN / "fact_orders.csv", index=False, float_format="%.2f")

cust_cols = ["customer_unique_id", "order_id", "order_purchase_timestamp", "first_purchase_month",
             "order_status", "customer_state", "seller_state", "same_state", "category",
             "order_value", "freight_value", "freight_share", "item_count", "payment_type",
             "payment_installments", "delivery_days", "promised_days", "days_vs_promise", "is_late",
             "delivery_speed_band", "promise_band", "review_score", "has_comment",
             "in_study", "returned_within_180", "returned", "days_to_return",
             "days_first_to_second_purchase", "second_order_value", "made_third_purchase",
             "days_second_to_third", "total_orders", "total_spend", "days_observed"]
first = first.rename(columns={"order_id": "first_order_id"})
cust_cols[1] = "first_order_id"
first[cust_cols].to_csv(CLEAN / "fact_customers.csv", index=False, float_format="%.2f")
states.to_csv(CLEAN / "dim_state.csv", index=False)
cats.to_csv(CLEAN / "dim_category.csv", index=False)

note(f"Saved fact_orders ({len(orders):,} rows), fact_customers ({len(first):,} rows), "
     f"dim_state ({len(states)} rows), dim_category ({len(cats)} rows).")
(CLEAN / "cleaning_log.txt").write_text("\n".join(log) + "\n")
