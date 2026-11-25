# Tableau Build Guide: The First Delivery Decides

**Time needed:** about 60 to 90 minutes. **What you need:** Tableau Public on your Mac and the three files in `dashboard/tableau-data/`.

This is the same as Part 5 of the Step-by-Step Guide, saved on its own so you can keep it open next to Tableau.


You will build 6 charts and 3 number tiles, then combine them into one dashboard with filters. If a step does not look the same on your screen, look for the same words nearby: Tableau moves buttons between versions.

## Step 1. Install Tableau Public

You already have Tableau Public from your first project. If not:

1. Go to public.tableau.com and sign in as victoria.okorie.
2. Click Create, then Download the App. Install it like any Mac app.
3. Open Tableau Public from Applications.

## Step 2. Connect to the main data file

1. On the start screen, under Connect, click **Text file**.
2. Go to your project folder, then dashboard, then tableau-data.
3. Choose **customers_study_group.csv** and click Open.
4. Check the preview at the bottom: you should see 52,542 rows (shown at the top right of the preview).
5. Tableau tidies the column names: returned_within_180 becomes **Returned Within 180**, delivery_days becomes **Delivery Days**, and so on. This guide uses the tidy names.
6. Click **Sheet 1** at the bottom left.

## Step 3. Create 3 calculated fields

For each one:

1. Click **Analysis** in the top menu, then **Create Calculated Field**.
2. Type the name.
3. Delete anything in the formula box and type the formula exactly.
4. Check that it says "The calculation is valid" at the bottom.
5. Click **OK**.

**Field 1. Name:** `Return Rate`

```
SUM([Returned Within 180]) / COUNT([Returned Within 180])
```

Then: right-click Return Rate in the Data pane, click Default Properties, then Number Format, then Percentage, set 2 decimal places, click OK.

**Field 2. Name:** `Low Review Share`

```
SUM(IF [Review Score] <= 2 THEN 1 ELSE 0 END) / COUNT([Review Score])
```

Set it to Percentage with 0 decimal places, the same way.

**Field 3. Name:** `Speed Colour`

```
IF [Delivery Days] <= 14 THEN "Fast: 14 days or less"
ELSEIF [Delivery Days] <= 30 THEN "Slow: 15 to 30 days"
ELSE "Very slow: more than 30 days"
END
```

## Step 4. Chart 1: return rate by delivery speed

1. Drag **Delivery Speed Band** onto **Columns**.
2. Drag **Return Rate** onto **Rows**. Bars appear.
3. Drag **Speed Colour** onto **Color** on the Marks card.
4. Click Color, then Edit Colors. Set Fast to blue, Slow to light grey, Very slow to red. Click OK.
5. Drag **Return Rate** onto **Label** on the Marks card.
6. Hover over a bar to see the tooltip. To add the number of customers: right-click in the Data pane on the empty space, choose Create Calculated Field, name it `Customers`, type `COUNT([Returned Within 180])`, click OK, then drag **Customers** onto **Tooltip**.
7. Double-click the title and type: `The slower the first delivery, the fewer customers come back`.
8. Right-click the **Sheet 1** tab, choose Rename, type `Speed`.

## Step 5. Chart 2: bad reviews by delivery speed

1. Right-click the **Speed** tab and choose **Duplicate**.
2. Drag **Return Rate** off the Rows shelf (drop it on the grey area).
3. Drag **Low Review Share** onto **Rows**.
4. Drag **Return Rate** off the Label box on the Marks card, and drag **Low Review Share** onto **Label**.
5. Title: `After a month of waiting, most customers leave a 1 or 2 star review`.
6. Rename the tab `Reviews`.

## Step 6. Chart 3: return rate by region

1. Duplicate the **Speed** tab.
2. Drag **Delivery Speed Band** off Columns. Drag **Region** onto Columns.
3. Drag **Speed Colour** off Color.
4. Drag **Delivery Days** onto **Tooltip**. Right-click it on the Marks card, choose Measure, then Average.
5. Click the sort icon on the vertical axis so the highest return rate is on the left.
6. Title: `Return rate by region of Brazil`. Rename the tab `Region`.

## Step 7. Chart 4: late against the promise

1. Duplicate the **Speed** tab.
2. Drag **Delivery Speed Band** off Columns. Drag **Is Late** onto Columns.
3. If Is Late shows as a measure (green), right-click it on Columns and choose **Dimension**.
4. Right-click **Is Late** in the Data pane, choose Aliases, and type `On time or early` for 0 and `Late` for 1. Click OK.
5. Drag **Speed Colour** off Color.
6. Title: `Late or not, the return rates overlap once waiting time is known`. Rename the tab `Promise`.

## Step 8. Add the second data file and build Chart 5: the second purchase window

1. Click the **Data** menu, then **New Data Source**, then **Text file**.
2. Open **second_purchase_window.csv** from the same tableau-data folder.
3. Click **Sheet** at the bottom (the new sheet icon) to start a fresh worksheet.
4. In the Data pane, make sure the new data source is selected at the top.
5. Drag **Period** onto **Columns**.
6. Drag **Chance Of Returning Pct** onto **Rows**.
7. Sort by time: right-click **Period** on Columns, choose Sort, choose **Field**, pick **Start Day**, **Ascending**, aggregation **Sum**. Close the box.
8. Drag **Chance Of Returning Pct** onto **Label**.
9. Colour the window: click Analysis, Create Calculated Field, name `Window`, formula: `IF [Start Day] < 60 THEN "First 60 days" ELSE "Later" END`. Click OK. Drag **Window** onto Color. Set First 60 days to blue and Later to light grey.
10. Title: `The second purchase window: the first 60 days after delivery`. Rename the tab `Window`.

## Step 9. Chart 6: the return curves

1. Data menu, New Data Source, Text file, open **return_curve_by_delivery_speed.csv**.
2. Start a new worksheet.
3. Drag **Day** onto **Columns**. Right-click it and choose **Dimension**, then right-click again and choose **Continuous**.
4. Drag **Returned So Far Pct** onto **Rows**. A line appears.
5. Drag **First Delivery** onto **Color**. Three lines appear.
6. Set the colours: Within 7 days blue, 8 to 21 days grey, More than 21 days red.
7. Title: `Fast first deliveries keep earning repeat customers`. Rename the tab `Curves`.

## Step 10. Three number tiles

Make each on a new worksheet using the **customers_study_group** data source (select it at the top of the Data pane).

1. **Tile "Customers":** drag **Customers** onto **Text** on the Marks card. Rename the tab `Tile Customers`.
2. **Tile "Return rate":** drag **Return Rate** onto **Text**. Rename the tab `Tile Return`.
3. **Tile "Days to deliver":** drag **Delivery Days** onto **Text**, right-click it on the Marks card, choose Measure, then Average. Rename the tab `Tile Days`.
4. On each tile: click **Text** on the Marks card, click the three dots, make the number size 28 and bold, and type a label above it (for example `Customers studied`). Click OK.

## Step 11. Build the dashboard

1. Click the **New Dashboard** icon at the bottom (the grid icon).
2. Under Size on the left, choose **Fixed size**, then **1200 by 1000**.
3. Drag a **Text** object (bottom left, under Objects) to the top. Type: `The First Delivery Decides` in size 22 bold, and below it: `Delivery speed and repeat purchase, 52,542 Olist customers, Brazil 2016 to 2018`.
4. Drag the 3 tiles across the top, side by side, under the title.
5. Drag **Speed** and **Reviews** into the next row, side by side.
6. Drag **Window** and **Curves** into the next row.
7. Drag **Region** and **Promise** into the bottom row.
8. Close any repeated colour legends: click the legend, then the small X. Keep one for Speed Colour.
9. Drag a Text object to the very bottom and paste the 5 recommendations from the README (section "What a growth team should do").
10. Rename the dashboard tab `Delivery Dashboard`.

## Step 12. Add filters

1. Click the **Speed** chart on the dashboard so it has a grey border.
2. Click the small down arrow on the border, choose **Filters**, then **Region**.
3. On the new filter, click its down arrow, choose **Single Value (dropdown)**.
4. Click the down arrow again, choose **Apply to Worksheets**, then **All Using This Data Source**.
5. Repeat for **Category**.
6. Drag both filters into a row under the title.

Note: these filters change the charts built from customers_study_group.csv. The Window and Curves charts come from separate summary files, so they stay the same. Write `Timing charts show all customers` under them.

## Step 13. Check your numbers

With no filters selected, these must match:

1. Customers studied: **52,542**
2. Return rate: **1.83%**
3. Within 7 days: **2.07%**. More than 30 days: **1.10%**
4. Reviews of 1 or 2 stars after more than 30 days: **59%** (the README and story say 63% because they count all 92,628 reviewed first orders; Tableau uses only the 52,542 customers in the 180-day study group, so 59% is correct here)
5. Days 0 to 30 window bar: **0.54**

If one is different, check the formula of that calculated field, letter by letter.

## Step 14. Publish

1. Click **File**, then **Save to Tableau Public As**.
2. Name it `Delivery Speed and Repeat Purchase`.
3. When the web page opens, copy the address. That is your dashboard link.
4. On the web page, click Edit Details and paste this description: `Growth analytics portfolio project. How first-delivery speed affects whether 52,542 e-commerce customers buy again, and when to send win-back offers.`
5. Take a screenshot: press Command, Shift and 4, and drag a box around the dashboard. Rename it dashboard-screenshot.png.

