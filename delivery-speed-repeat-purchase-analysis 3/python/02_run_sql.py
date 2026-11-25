"""
Step 2. Build the SQLite database and run every Structured Query Language query.

Run from the project folder:
    python3 python/02_run_sql.py
"""
from pathlib import Path
import sqlite3
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "structured-query-language"
CLEAN = ROOT / "data" / "clean"
OUT = ROOT / "outputs" / "query_results"
OUT.mkdir(parents=True, exist_ok=True)

db = SQL / "olist_retention.db"
db.unlink(missing_ok=True)
con = sqlite3.connect(db)
con.executescript((SQL / "01_create_tables.sql").read_text())

for table in ["dim_state", "dim_category", "fact_orders", "fact_customers"]:
    df = pd.read_csv(CLEAN / f"{table}.csv")
    df.to_sql(table, con, if_exists="append", index=False)
    print(f"Loaded {table}: {len(df):,} rows")

text = (SQL / "02_analysis_queries.sql").read_text()
for block in text.split("-- name: ")[1:]:
    name, query = block.split("\n", 1)
    name = name.strip()
    result = pd.read_sql_query(query, con)
    result.to_csv(OUT / f"{name}.csv", index=False)
    print(f"\n=== {name} ===\n{result.to_string(index=False)}")

con.close()
