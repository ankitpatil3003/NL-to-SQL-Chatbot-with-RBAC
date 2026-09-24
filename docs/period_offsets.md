# Period Offsets — Time Filtering Guide

## Why Offsets Instead of Dates

The `sales` table includes pre-computed period offset columns that make time-based filtering simpler and more reliable than date arithmetic. **Always prefer offset columns over date math.**

Offsets are relative to the current data refresh date (not `CURRENT_DATE`), which accounts for data pipeline lag. The data is typically 1 business day behind.

## Offset Columns

### `wk_offset` — Week Offset
- `0` = the current (most recent) week
- `1` = last week
- `2` = two weeks ago
- Up to `155` for ~3 years of history

### `mo_offset` — Month Offset
- `0` = current month
- `1` = last month (most recently completed full month)
- `2` = two months ago
- Up to `35` for ~3 years of history

## Common Time Windows

| Business Term | Filter |
|---|---|
| Current week | `wk_offset = 0` |
| Last 4 weeks / R30D | `wk_offset <= 3` |
| Last month | `mo_offset = 1` |
| Last 3 months (R3M) | `mo_offset IN (0, 1, 2)` |
| Prior 3 months (R6M / comparison period) | `mo_offset IN (3, 4, 5)` |
| Last quarter | `mo_offset IN (1, 2, 3)` |
| Year to date | Depends on current month; use `period_qtr` for quarterly grouping |

## Period Label Columns

These columns provide human-readable labels for grouping:

- `period_wk` — format `YYYY-WNN` (e.g., `2026-W38`)
- `period_mo` — format `YYYY-MM` (e.g., `2026-09`)
- `period_qtr` — format `YYYY-QN` (e.g., `2026-Q3`)

Use these for GROUP BY when showing trends over time.

## Date Columns

Raw date columns are available for reference but should be secondary to offsets:

- `transaction_date` — the actual transaction date (YYYY-MM-DD)
- `week_ending_date` — the Saturday ending the transaction's week (YYYY-MM-DD)

## Examples

**"Sales this month":**
```sql
SELECT drug_name, SUM(wac) as revenue
FROM sales
WHERE data_source = 'distributor' AND brand_flag = 1 AND mo_offset = 0
GROUP BY drug_name
```

**"Monthly trend for the last 6 months":**
```sql
SELECT period_mo, drug_name, SUM(wac) as revenue
FROM sales
WHERE data_source = 'distributor' AND brand_flag = 1 AND mo_offset BETWEEN 0 AND 5
GROUP BY period_mo, drug_name
ORDER BY period_mo
```

**"Compare this quarter vs last quarter":**
```sql
SELECT period_qtr, SUM(wac) as revenue
FROM sales
WHERE data_source = 'distributor' AND brand_flag = 1 AND period_qtr IN ('2026-Q3', '2026-Q2')
GROUP BY period_qtr
```
