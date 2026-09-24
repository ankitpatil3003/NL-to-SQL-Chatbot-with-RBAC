# Data Source Guide

The `sales` table contains data from three distinct sources, identified by the `data_source` column. Understanding which source to use is critical for generating correct queries.

## `distributor`

**What it is:** NovaPharma's own shipment data from distribution partners. This is the primary source for NovaPharma's paid demand — actual units sold and shipped to healthcare facilities.

**When to use:**
- Any question about NovaPharma's own sales, revenue, or demand
- "How much did we sell?" or "What are our sales?"
- Paid demand analysis
- Account-level revenue calculations
- The `wac` column contains the dollar amount for distributor transactions

**Key filters:**
- Always filter `brand_flag = 1` when looking at NovaPharma product sales
- `brand_flag = 0` rows should not appear for this source in practice

**Examples:**
- "Total Zenovax sales last month" → `data_source = 'distributor' AND drug_name = 'ZENOVAX'`
- "Revenue by account" → `SUM(wac) WHERE data_source = 'distributor' AND brand_flag = 1`

## `hub_dispense`

**What it is:** Free drug dispensed through NovaPharma's patient assistance hub. These are not paid transactions — the drug is provided at no cost to qualifying patients.

**When to use:**
- Questions specifically about free drug or patient assistance programs (PAP)
- Total volume analysis that includes both paid and free drug
- The `wac` column is always 0 for hub dispense transactions

**Key distinction:**
- Hub dispense volume is **excluded** from paid demand and revenue calculations by default
- Only include hub_dispense when the user explicitly asks about "total volume including free drug" or "PAP volume"

**Examples:**
- "How much free drug did we provide?" → `data_source = 'hub_dispense'`
- "Total volume including free drug" → `data_source IN ('distributor', 'hub_dispense')`

## `market_data`

**What it is:** Third-party market research data. Captures estimated total market volume across all manufacturers for each therapeutic area. Includes both branded and generic products from all competitors.

**When to use:**
- Market share calculations (this provides the denominator)
- Competitive analysis — what competitors are selling
- Total market size / market potential analysis
- The `brand_flag` column distinguishes NovaPharma products (1) from competitors (0) within market data

**Key filters:**
- For market share denominators, use ALL `market_data` rows for the relevant therapeutic area
- For competitor-only analysis, filter `brand_flag = 0` within market_data
- `wac` values in market data are estimated, not actual transaction prices

**Examples:**
- "Total docetaxel market size" → `data_source = 'market_data' AND drug_name IN (all docetaxel products)`
- "Market share for Zenovax" → NovaPharma distributor equivalents / market_data total equivalents

## Common Mistakes to Avoid

1. **Mixing sources in ratios**: Never divide distributor volume by distributor volume for "market share." Market share always uses `distributor` in the numerator and `market_data` in the denominator.

2. **Including hub_dispense in revenue**: Hub transactions have `wac = 0`. Including them inflates unit counts without adding revenue, skewing per-unit metrics.

3. **Forgetting brand_flag**: When summing "our sales," always filter `brand_flag = 1` to ensure only NovaPharma products are counted.

4. **Using market_data for revenue**: Market data WAC values are estimates. For actual revenue, always use the `distributor` source.
