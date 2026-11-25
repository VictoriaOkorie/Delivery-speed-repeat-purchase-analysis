"""
Step 4. Build the Excel dashboard (dashboard/Delivery-and-Repeat-Purchase-Dashboard.xlsx).

Every number on the Summary and Delivery Speed sheets is a live COUNTIFS or AVERAGEIFS
formula over the Data sheet, so anyone can click a cell and see how it was calculated.

Run from the project folder (after steps 1 to 3):
    python3 python/04_build_excel_dashboard.py
"""
from pathlib import Path
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
DASH = ROOT / "dashboard"
DASH.mkdir(exist_ok=True)

cust = pd.read_csv(ROOT / "data/clean/fact_customers.csv")
states = pd.read_csv(ROOT / "data/clean/dim_state.csv")
cust = cust.merge(states[["state_code", "region"]], left_on="customer_state", right_on="state_code", how="left")
study = cust[cust.in_study == 1].copy()
window = pd.read_csv(OUT / "second_purchase_window.csv")
gate = pd.read_csv(OUT / "loyalty_gate.csv")

INK, MUTED, BLUE, RED, LINE, PALE = "0B0B0B", "52514E", "2A78D6", "E34948", "D6D5CF", "F3F2EE"
H1 = Font(name="Calibri", size=20, bold=True, color=INK)
H2 = Font(name="Calibri", size=13, bold=True, color=INK)
NOTE = Font(name="Calibri", size=10, italic=True, color=MUTED)
HEAD = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
HEAD_FILL = PatternFill("solid", fgColor=BLUE)
TILE_FILL = PatternFill("solid", fgColor=PALE)
BIG = Font(name="Calibri", size=24, bold=True, color=BLUE)
LABEL = Font(name="Calibri", size=10, color=MUTED)
INPUT_FILL = PatternFill("solid", fgColor="FFF4CC")
thin = Border(bottom=Side(style="thin", color=LINE))

wb = Workbook()

# ------------------------------------------------------------------ Data sheet
data = wb.active
data.title = "Data"
cols = ["first_order_id", "first_purchase_month", "region", "customer_state", "category", "order_value",
        "delivery_days", "delivery_speed_band", "is_late", "days_vs_promise", "review_score",
        "returned_within_180", "days_to_return", "made_third_purchase", "total_orders", "total_spend"]
d = study[cols].copy()
d["delivery_days"] = d.delivery_days.round(1)
data.append(cols)
for row in d.itertuples(index=False):
    data.append([None if (isinstance(v, float) and pd.isna(v)) else v for v in row])
for c in data[1]:
    c.font = HEAD; c.fill = HEAD_FILL
data.freeze_panes = "A2"
for i, w in enumerate([34, 12, 13, 8, 26, 11, 11, 20, 8, 10, 9, 12, 11, 12, 10, 11], 1):
    data.column_dimensions[get_column_letter(i)].width = w
N = len(d) + 1
rng = lambda col: f"Data!${col}$2:${col}${N}"
BAND, LATE, RET, DAYS, REV, REG = rng("H"), rng("I"), rng("L"), rng("G"), rng("K"), rng("C")
SPEND = rng("P")

# ------------------------------------------------------------------ Summary sheet
s = wb.create_sheet("Summary", 0)
s.sheet_view.showGridLines = False
for col, w in zip("ABCDEFGH", [2, 22, 4, 22, 4, 22, 4, 22]):
    s.column_dimensions[col].width = w
s["B2"] = "The First Delivery Decides"; s["B2"].font = H1
s["B3"] = "Does a slow first delivery stop customers coming back? Olist Brazilian e-commerce, 2016 to 2018."
s["B3"].font = NOTE
s["B4"] = "Study group: customers whose first order was delivered and who were watched for 180 days afterwards."
s["B4"].font = NOTE

tiles = [
    ("B", "Customers in study", f"=COUNT({RET})", "#,##0"),
    ("D", "Returned within 180 days", f"=AVERAGE({RET})", "0.00%"),
    ("F", "Average days to deliver", f"=AVERAGE({DAYS})", "0.0"),
    ("H", "First orders delivered late", f"=AVERAGE({LATE})", "0.0%"),
]
for col, label, formula, fmt in tiles:
    s[f"{col}6"] = label; s[f"{col}6"].font = LABEL
    s[f"{col}7"] = formula; s[f"{col}7"].font = BIG; s[f"{col}7"].number_format = fmt
    for r in (6, 7, 8):
        s[f"{col}{r}"].fill = TILE_FILL
    s[f"{col}6"].alignment = s[f"{col}7"].alignment = Alignment(horizontal="left", indent=1)

tiles2 = [
    ("B", "Return rate: delivered within 7 days", f'=AVERAGEIFS({RET},{BAND},"1. Within 7 days")', "0.00%"),
    ("D", "Return rate: more than 30 days", f'=AVERAGEIFS({RET},{BAND},"5. More than 30 days")', "0.00%"),
    ("F", "Chance of a third order after a second", gate.within_180_days_pct[1] / 100, "0.0%"),
    ("H", "Extra spend per returning customer (reais)",
     f'=AVERAGEIFS({SPEND},{rng("O")},">1")-AVERAGEIFS({SPEND},{rng("O")},1)', "#,##0.00"),
]
for col, label, formula, fmt in tiles2:
    s[f"{col}10"] = label; s[f"{col}10"].font = LABEL
    s[f"{col}11"] = formula; s[f"{col}11"].font = BIG; s[f"{col}11"].number_format = fmt
    for r in (10, 11, 12):
        s[f"{col}{r}"].fill = TILE_FILL
    s[f"{col}10"].alignment = Alignment(horizontal="left", indent=1, wrap_text=True)
    s[f"{col}11"].alignment = Alignment(horizontal="left", indent=1)
s.row_dimensions[10].height = 30

s["B14"] = "What the data says"; s["B14"].font = H2
findings = [
    "1. Customers whose first order arrived within 7 days came back at almost twice the rate of those who waited more than 30 days.",
    "2. Each extra week of waiting cuts the odds of a return by about 11%, after controlling for region, price, product, payment and season.",
    "3. Missing the promised date did not matter on its own once waiting time was known. Customers react to the wait, not the estimate.",
    "4. The second purchase window is the first 60 days after delivery: the chance of returning is highest then and flattens after day 90.",
    "5. Once a customer buys a second time, a third order becomes about 4.7 times as likely. The second order is the gate to loyalty.",
]
for i, f in enumerate(findings):
    s[f"B{15 + i}"] = f
    s[f"B{15 + i}"].font = Font(name="Calibri", size=11, color=INK)
s["B21"] = "Note: the 'third order' tile uses a survival estimate from the Python notebook (outputs/loyalty_gate.csv)."
s["B21"].font = NOTE

# ------------------------------------------------------------------ Delivery speed sheet
sp = wb.create_sheet("Delivery Speed", 1)
sp.sheet_view.showGridLines = False
sp["A1"] = "Return rate by days to deliver the first order"; sp["A1"].font = H2
heads = ["Delivery speed", "Customers", "Returned", "Return rate", "Average review", "Late against promise"]
sp.append([]); sp.append(heads)
for c in sp[3]:
    c.font = HEAD; c.fill = HEAD_FILL; c.alignment = Alignment(horizontal="center", wrap_text=True)
bands = ["1. Within 7 days", "2. 8 to 14 days", "3. 15 to 21 days", "4. 22 to 30 days", "5. More than 30 days"]
for i, b in enumerate(bands):
    r = 4 + i
    sp[f"A{r}"] = b
    sp[f"B{r}"] = f'=COUNTIFS({BAND},A{r})'
    sp[f"C{r}"] = f'=COUNTIFS({BAND},A{r},{RET},1)'
    sp[f"D{r}"] = f"=C{r}/B{r}"; sp[f"D{r}"].number_format = "0.00%"
    sp[f"E{r}"] = f'=AVERAGEIFS({REV},{BAND},A{r})'; sp[f"E{r}"].number_format = "0.00"
    sp[f"F{r}"] = f'=AVERAGEIFS({LATE},{BAND},A{r})'; sp[f"F{r}"].number_format = "0.0%"
    sp[f"B{r}"].number_format = sp[f"C{r}"].number_format = "#,##0"
    for c in sp[r]:
        c.border = thin
for col, w in zip("ABCDEF", [24, 12, 11, 12, 14, 18]):
    sp.column_dimensions[col].width = w

sp["A11"] = "Late against the promised date"; sp["A11"].font = H2
sp.append([]); sp["A12"], sp["B12"], sp["C12"], sp["D12"] = "First delivery", "Customers", "Returned", "Return rate"
for c in sp[12][:4]:
    c.font = HEAD; c.fill = HEAD_FILL
for r, (label, v) in enumerate([("On time or early", 0), ("Late", 1)], start=13):
    sp[f"A{r}"] = label
    sp[f"B{r}"] = f"=COUNTIFS({LATE},{v})"; sp[f"B{r}"].number_format = "#,##0"
    sp[f"C{r}"] = f"=COUNTIFS({LATE},{v},{RET},1)"
    sp[f"D{r}"] = f"=C{r}/B{r}"; sp[f"D{r}"].number_format = "0.00%"

sp["A17"] = "By region"; sp["A17"].font = H2
sp["A18"], sp["B18"], sp["C18"], sp["D18"] = "Region", "Customers", "Average days to deliver", "Return rate"
for c in sp[18][:4]:
    c.font = HEAD; c.fill = HEAD_FILL; c.alignment = Alignment(wrap_text=True)
for r, reg in enumerate(["Southeast", "South", "Central-West", "Northeast", "North"], start=19):
    sp[f"A{r}"] = reg
    sp[f"B{r}"] = f'=COUNTIFS({REG},A{r})'; sp[f"B{r}"].number_format = "#,##0"
    sp[f"C{r}"] = f'=AVERAGEIFS({DAYS},{REG},A{r})'; sp[f"C{r}"].number_format = "0.0"
    sp[f"D{r}"] = f'=AVERAGEIFS({RET},{REG},A{r})'; sp[f"D{r}"].number_format = "0.00%"

ch = BarChart(); ch.type = "col"; ch.style = 10
ch.title = "Return rate within 180 days, by days to deliver"
ch.add_data(Reference(sp, min_col=4, min_row=3, max_row=8), titles_from_data=True)
ch.set_categories(Reference(sp, min_col=1, min_row=4, max_row=8))
ch.legend = None; ch.y_axis.numFmt = "0.0%"; ch.y_axis.majorGridlines = None
ch.series[0].graphicalProperties.solidFill = BLUE
ch.series[0].graphicalProperties.line.noFill = True
ch.dataLabels = DataLabelList(); ch.dataLabels.showVal = True
ch.height, ch.width = 8, 16
sp.add_chart(ch, "H3")

# ------------------------------------------------------------------ Second purchase window sheet
w = wb.create_sheet("Second Purchase Window", 2)
w.sheet_view.showGridLines = False
w["A1"] = "When do customers come back? Chance of a second order in each 30-day period after delivery"; w["A1"].font = H2
w["A2"] = "Kaplan-Meier survival estimate on 93,185 delivered customers (from the Python notebook, outputs/second_purchase_window.csv)."
w["A2"].font = NOTE
w.append([]); w.append(["Period after delivery", "Chance of returning in this period", "Returned so far (cumulative)"])
for c in w[4]:
    c.font = HEAD; c.fill = HEAD_FILL; c.alignment = Alignment(wrap_text=True)
for i, row in window.iterrows():
    r = 5 + i
    w[f"A{r}"] = row.period
    w[f"B{r}"] = row.chance_of_returning_pct / 100; w[f"B{r}"].number_format = "0.00%"
    w[f"C{r}"] = row.cumulative_returned_pct / 100; w[f"C{r}"].number_format = "0.00%"
for col, wd in zip("ABC", [20, 18, 18]):
    w.column_dimensions[col].width = wd
w.row_dimensions[4].height = 32
ch = BarChart(); ch.type = "col"; ch.style = 10
ch.title = "Chance of a second order, by 30-day period after delivery"
ch.add_data(Reference(w, min_col=2, min_row=4, max_row=16), titles_from_data=True)
ch.set_categories(Reference(w, min_col=1, min_row=5, max_row=16))
ch.legend = None; ch.y_axis.numFmt = "0.0%"; ch.y_axis.majorGridlines = None
ch.series[0].graphicalProperties.solidFill = BLUE
ch.height, ch.width = 8, 18
w.add_chart(ch, "E4")
w["A19"] = "Recommendation"; w["A19"].font = H2
recs = ["Days 3 to 10: thank-you and how-to-use message (no discount). Ask for the review.",
        "Days 14 to 30: first personalised offer, based on the first purchase category. This is the period with the highest chance of return.",
        "Days 45 to 60: second reminder with a stronger incentive for customers who have not returned.",
        "After day 90: move to low-cost newsletter only. The chance of return is low and flat from here.",
        "After a second order: a third-order nudge around 50 days later (the median gap between second and third orders)."]
for i, t in enumerate(recs):
    w[f"A{20 + i}"] = t

# ------------------------------------------------------------------ What-if planner
p = wb.create_sheet("What-If Planner", 3)
p.sheet_view.showGridLines = False
p.column_dimensions["A"].width = 62; p.column_dimensions["B"].width = 16
p["A1"] = "What-if planner: faster first deliveries"; p["A1"].font = H2
p["A2"] = "Change the yellow cells. Rates are pulled live from the Delivery Speed sheet. This is an estimate based on observed differences, not a guarantee."
p["A2"].font = NOTE
rows = [
    ("New customers per month", 5000, "#,##0", True),
    ("Share of first deliveries that take more than 14 days", "=SUM('Delivery Speed'!B6:B8)/SUM('Delivery Speed'!B4:B8)", "0.0%", True),
    ("Share of those slow deliveries you can speed up to 8 to 14 days", 0.5, "0%", True),
    ("Return rate for 8 to 14 day deliveries", "='Delivery Speed'!D5", "0.00%", False),
    ("Average return rate for deliveries over 14 days",
     "=SUM('Delivery Speed'!C6:C8)/SUM('Delivery Speed'!B6:B8)", "0.00%", False),
    ("Extra returning customers per month", "=B4*B5*B6*(B7-B8)", "#,##0.0", False),
    ("Extra spend per returning customer (reais)", "=Summary!H11", "#,##0.00", True),
    ("Extra revenue per year (reais)", "=B9*B10*12", "#,##0", False),
]
for i, (label, val, fmt, editable) in enumerate(rows, start=4):
    p[f"A{i}"] = label
    p[f"B{i}"] = val; p[f"B{i}"].number_format = fmt
    if editable:
        p[f"B{i}"].fill = INPUT_FILL
    p[f"A{i}"].border = p[f"B{i}"].border = thin
p["B11"].font = Font(bold=True, size=13, color=BLUE)

p["A13"] = "What-if planner: a win-back campaign in the second purchase window"; p["A13"].font = H2
p["A14"] = ("The lift is YOUR assumption: this data has no campaign in it. Test it with a holdout group "
            "(send the offer to most customers, hold back a random 10%) before trusting it.")
p["A14"].font = NOTE
rows2 = [
    ("Share of customers who return within 60 days of delivery today", window.cumulative_returned_pct[1] / 100, "0.00%", False),
    ("Assumed relative lift from the campaign (for example 20% more returns)", 0.2, "0%", True),
    ("Extra second orders per month", "=B4*B15*B16", "#,##0.0", False),
    ("Chance a second-order customer places a third order within 180 days", gate.within_180_days_pct[1] / 100, "0.0%", False),
    ("Extra third orders per month that follow", "=B17*B18", "#,##0.00", False),
    ("Extra revenue per year from the campaign (reais)", "=B17*B10*12", "#,##0", False),
]
for i, (label, val, fmt, editable) in enumerate(rows2, start=15):
    p[f"A{i}"] = label
    p[f"B{i}"] = val; p[f"B{i}"].number_format = fmt
    if editable:
        p[f"B{i}"].fill = INPUT_FILL
    p[f"A{i}"].border = p[f"B{i}"].border = thin
p["B20"].font = Font(bold=True, size=13, color=BLUE)
p["A22"] = ("Reading it honestly: on a marketplace where about 2% of customers return, faster delivery and better timing each add a "
            "modest number of repeat customers. The value is that both are cheap to change and they compound.")
p["A22"].font = NOTE
p["A22"].alignment = Alignment(wrap_text=True); p.row_dimensions[22].height = 45

# ------------------------------------------------------------------ About
a = wb.create_sheet("About")
a.column_dimensions["A"].width = 120
lines = [
    ("About this dashboard", H2),
    ("Data: Olist Brazilian e-commerce public dataset, 99,441 orders from 96,096 customers, September 2016 to August 2018.", None),
    ("Study group: 52,542 customers whose first order was delivered and who could be watched for 180 days afterwards.", None),
    ("Outcome: placed a new (not cancelled) order after the first order arrived and within 180 days.", None),
    ("Orders placed before the first order arrived (mostly same-day split baskets) do not count as returns.", None),
    ("Values are in Brazilian reais. Full method: README.md and python/03_analysis.ipynb. Built by Victoria Okorie.", None),
]
for i, (t, f) in enumerate(lines, start=1):
    a[f"A{i}"] = t
    if f:
        a[f"A{i}"].font = f

# ------------------------------------------------------------------ Files for Tableau Public
TAB = DASH / "tableau-data"
TAB.mkdir(exist_ok=True)
t = d.copy()
for c in ["returned_within_180", "is_late", "days_vs_promise", "review_score", "made_third_purchase"]:
    t[c] = t[c].astype("Int64")
t.drop(columns=["first_order_id"]).to_csv(TAB / "customers_study_group.csv", index=False)
window.to_csv(TAB / "second_purchase_window.csv", index=False)
pd.read_csv(OUT / "return_curve_by_delivery_speed.csv").melt(
    id_vars="day", var_name="first_delivery", value_name="returned_so_far_pct").to_csv(
    TAB / "return_curve_by_delivery_speed.csv", index=False)
print(f"Saved Tableau files in {TAB}")

path = DASH / "Delivery-and-Repeat-Purchase-Dashboard.xlsx"
wb.save(path)
print(f"Saved {path}")
