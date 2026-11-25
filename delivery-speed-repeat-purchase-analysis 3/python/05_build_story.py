"""
Step 5. Build the data story (story/The-First-Delivery-Decides.html and .pdf).

Every number in the story is filled in from the analysis outputs, so the article
always matches the data. Run from the project folder (after steps 1 to 4):
    python3 python/05_build_story.py
"""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
STORY = ROOT / "story"

cust = pd.read_csv(ROOT / "data/clean/fact_customers.csv")
study = cust[cust.in_study == 1]
speed = pd.read_csv(OUT / "return_rate_by_delivery_speed.csv")
odds = pd.read_csv(OUT / "logistic_regression_odds_ratios.csv")
q05 = pd.read_csv(OUT / "query_results/q05_review_by_delivery_speed.csv")
q07 = pd.read_csv(OUT / "query_results/q07_region_scorecard.csv")
curve = pd.read_csv(OUT / "return_curve_by_delivery_speed.csv")
window = pd.read_csv(OUT / "second_purchase_window.csv")
gate = pd.read_csv(OUT / "loyalty_gate.csv")
sizing = pd.read_csv(OUT / "opportunity_sizing.csv").iloc[0]

names = ["Within\n7 days", "8 to 14\ndays", "15 to 21\ndays", "22 to 30\ndays", "More than\n30 days"]
data = {
    "speed": [{"name": n, "short": n, "value": r.rate_pct, "low": r.low_pct, "high": r.high_pct,
               "customers": int(r.customers), "returned": int(r.returned)} for n, r in zip(names, speed.itertuples())],
    "reviews": [{"name": n, "value": r.pct_1_or_2_stars, "avg": r.avg_review, "customers": int(r.customers)}
                for n, r in zip(names, q05.itertuples())],
    "odds": [],
    "region": [{"region": r.region, "customers": int(r.customers), "days": r.avg_delivery_days,
                "late": r.pct_late, "rate": r.return_rate_pct} for r in q07.itertuples()],
    "curve": {"days": curve.day.tolist(), "fast": curve["Within 7 days"].tolist(),
              "mid": curve["8 to 21 days"].tolist(), "slow": curve["More than 21 days"].tolist()},
    "window": [{"period": r.period, "short": f"{r.start_day + 1 if r.start_day else 0} to\n{r.start_day + 30}",
                "tiny": f"{r.start_day + 1 if r.start_day else 0}-\n{r.start_day + 30}",
                "chance": r.chance_of_returning_pct, "cum": r.cumulative_returned_pct} for r in window.itertuples()],
    "gate": gate.within_180_days_pct.tolist(),
    "gate_n": gate.customers.astype(int).tolist(),
}
label = {"weeks_to_deliver": "Each extra week to deliver", "is_late": "Delivered after the promised date"}
for r in odds[odds.factor.isin(label)].itertuples():
    data["odds"].append({"name": label[r.factor], "model": r.model.split(". ", 1)[1],
                         "or": r.odds_ratio, "low": r.ci_low, "high": r.ci_high, "p": r.p_value})

wk = odds[(odds.model.str.startswith("B")) & (odds.factor == "weeks_to_deliver")].iloc[0]
base = window.loc[window.start_day >= 90, "chance_of_returning_pct"].mean()
returners = cust[cust.returned == 1]
third_gap = returners.loc[returners.made_third_purchase == 1, "days_second_to_third"].median()
survival_n = gate.customers[0]

fill = {
    "customers": f"{len(cust):,}",
    "study": f"{len(study):,}",
    "rate": f"{study.returned_within_180.mean() * 100:.2f}",
    "extra_spend": f"{sizing.extra_spend_per_returner_brl:,.0f}",
    "over30": f"{int(speed.customers.iloc[4]):,}",
    "r1": f"{speed.rate_pct.iloc[0]:.2f}",
    "r5": f"{speed.rate_pct.iloc[4]:.2f}",
    "ratio": f"{speed.rate_pct.iloc[0] / speed.rate_pct.iloc[4]:.1f}",
    "early8": f"{(study.days_vs_promise <= -8).mean() * 100:.0f}",
    "week_pct": f"{(1 - wk.odds_ratio) * 100:.0f}",
    "reviewed": f"{int(q05.customers.sum()):,}",
    "low1": f"{q05.pct_1_or_2_stars.iloc[0]:.1f}",
    "low5": f"{q05.pct_1_or_2_stars.iloc[4]:.0f}",
    "survival_n": f"{survival_n:,}",
    "median_return": f"{returners.days_to_return.median():.0f}",
    "w1x": f"{window.chance_of_returning_pct[0] / base:.1f}",
    "w2x": f"{window.chance_of_returning_pct[1] / base:.1f}",
    "base": f"{base:.2f}",
    "g1": f"{gate.within_180_days_pct[0]:.1f}",
    "g2": f"{gate.within_180_days_pct[1]:.1f}",
    "gx": f"{gate.within_180_days_pct[1] / gate.within_180_days_pct[0]:.1f}",
    "gate_n": f"{gate.customers[1]:,}",
    "third_gap": f"{third_gap:.0f}",
    "extra_returners": f"{int(sizing.extra_returners_if_slow_matched_8_to_14_days)}",
    "extra_pct": f"{sizing.increase_in_returning_customers_pct:.0f}",
}

html = (STORY / "story_template.html").read_text()
for k, v in fill.items():
    html = html.replace("{{" + k + "}}", v)
assert "{{" not in html, "a placeholder was not filled"
html = html.replace("/*DATA*/null", json.dumps(data))
out = STORY / "The-First-Delivery-Decides.html"
out.write_text(html)
print(f"Saved {out}")

# PDF version (needs Playwright with Chromium installed)
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(out.resolve().as_uri(), wait_until="networkidle")
        page.emulate_media(color_scheme="light")
        page.evaluate("document.documentElement.setAttribute('data-theme','light'); renderAll();")
        page.wait_for_timeout(800)
        page.pdf(path=str(STORY / "The-First-Delivery-Decides.pdf"), format="Letter", print_background=True,
                 margin={"top": "0.5in", "bottom": "0.6in", "left": "0.4in", "right": "0.4in"})
        browser.close()
    print("Saved PDF")
except Exception as e:
    print(f"PDF skipped: {e}")
