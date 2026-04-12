## Customer Cohort Analysis for HVAC Products

This code creates a chart that shows how customers behave over time for 4 main home heating/cooling products. 

It’s a **cohort analysis** — one of the best ways to understand if things are getting better, worse, or staying the same.

France HVAC Sales Team sells boilers, stoves, air conditioners, and heat pumps.

- Every week, new people request a quote (`first_quote_date`).
- The code groups these people by the week they first asked for a quote → this is called a **cohort**.
- Then it tracks two important things for each weekly group:

| Metric | Description |
|--------|-------------|
| **Conversion Rate** | What % of people who requested a quote actually bought the product? |
| **Decision Days** | On average, how many days did it take them to decide and buy? |

It does this separately for each of the 4 products:

- Boiler (gas)
- Stove
- Air Conditioner (AC)
- Heat Pump

#### Step-by-Step: What the Code Does

#### 1. Prepares the Data

  - Takes only the 4 main products (ignores everything else)
  - Creates a `cohort_week` column: which week did this person first ask for a quote?
  - Counts how many quotes came in that week (total)
  - Counts how many actually converted into a sale (converted)
  - Calculates the average number of days to buy (`avg_decision_days`)

#### 2. Calculates Conversion Rate

    conversion_rate = (converted / total) × 100 → shown as a percentage

#### 3. Smooths the Lines (Rolling Average)

  - Raw weekly numbers are often very noisy (up and down every week)
  - So it creates a **4-week rolling average** — this makes the trend much easier to see

#### 4. Handles Recent Data Carefully

  - The last 12 weeks are marked as **"incomplete"** because people who quoted very recently haven’t had enough time to buy yet
  - These recent weeks are shown with dashed lines and a light orange shaded area with a warning ⚠

#### 5. Creates the Plot (The Picture)
Makes two charts stacked vertically (one on top of the other):

  - **Top chart:** Conversion Rate over time (with % on the y-axis)
  - **Bottom chart:** Average days to decide/buy over time

For each product it draws:

  - Light dots = actual weekly data (a bit transparent)
  - Thick solid line = smoothed 4-week average (for older, reliable data)
  - Thin dashed line = smoothed 4-week average (for the most recent, incomplete weeks)

#### 6. Product Colors

| Product | Color |
|---------|-------|
| Boiler | `steelblue` |
| Stove | `tomato` (red-orange) |
| AC | `mediumseagreen` |
| Heat Pump | `darkorange` |

#### 7. Finishing Touches
- Adds titles, labels, legend, grid
- Rotates the date labels
- Saves the final image as `cohort_curves_by_segment.png`
- Shows the plot on screen

### What Story Does This Chart Tell?

We can look at the chart and immediately see things like:

- Is the conversion rate for Heat Pumps going up or down over the past year?
- Are people deciding faster or slower to buy Boilers lately?
- How does the Stove compare to the Air Conditioner?
- Is the most recent data (dashed lines) looking promising or worrying?

This kind of chart is useful for **business people, product managers, or marketing teams** to spot trends early.

### Summary

> The code takes our customer quote and purchase data, groups people by the week they first contacted sales team, calculates 
> how well each of the four main products is converting and how fast people are buying, smooths out the noise, separates
> old reliable data from very recent data, and draws two clean, professional line charts (one for conversion %, one for
