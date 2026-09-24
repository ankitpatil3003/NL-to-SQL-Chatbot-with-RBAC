# Metric Definitions

This document defines the key business metrics used by the NovaPharma commercial analytics team. These formulas should be used whenever a user asks about these metrics.

## Market Share

Market share measures NovaPharma's branded product volume as a proportion of the total market volume for the same therapeutic area.

**Formula:**
```
Market Share = NovaPharma Equivalents / Total Market Equivalents
```

- **Numerator**: Sum of equivalents from `data_source = 'distributor'` where `brand_flag = 1` (NovaPharma branded products only)
- **Denominator**: Sum of equivalents from `data_source = 'market_data'` (includes all competitors and NovaPharma volume as reported by the market data provider)
- Market share is always expressed as a decimal between 0 and 1 (multiply by 100 for percentage)
- If the denominator is 0, market share is NULL (not 0)

**Important**: The `distributor` and `market_data` sources measure volume independently. The distributor source is NovaPharma's own shipment data; the market data source is third-party reported total market volume. They should never be mixed in a single ratio calculation.

## Equivalents

Equivalents convert raw `pack_units` into a standardized dosing unit so that different package sizes of the same drug can be compared.

**Formula:**
```
Equivalents = pack_units × unit_conversion_factor
```

The `unit_conversion_factor` is found in the `products` table. For example:
- ZENOVAX 80MG vial: `unit_conversion_factor = 1.0` → 1 pack = 1 equivalent
- ZENOVAX 20MG vial: `unit_conversion_factor = 0.25` → 4 packs = 1 equivalent
- CARBOTREL 150MG vial: `unit_conversion_factor = 0.333` → ~3 packs = 1 equivalent

Alternatively, equivalents can be calculated from milligrams:
```
Equivalents = total_mg / mg_equivalent
```

## Rolling Period Metrics

### R3M (Rolling 3 Months)
Sales or equivalents for the most recent 3 months: `mo_offset IN (0, 1, 2)` (current month plus the two prior months).

### R6M (Rolling 6 Months, Prior Period)
The 3-month window preceding R3M: `mo_offset IN (3, 4, 5)`.

### R3M vs R6M Trend
```
Trend = R3M Market Share - R6M Market Share
```
A positive trend means market share is growing; negative means declining. Often weighted by volume:
```
Weighted Trend = (R3M Share - R6M Share) × (R3M Volume + R6M Volume)
```
This ensures that large accounts with modest share changes rank above small accounts with volatile shares.

## Revenue Metrics

### Gross Revenue (WAC)
WAC (Wholesale Acquisition Cost) is the list price revenue. Found directly in the `sales.wac` column.
```
Gross Revenue = SUM(wac) WHERE data_source = 'distributor' AND brand_flag = 1
```

### Paid Demand
Paid demand refers exclusively to `data_source = 'distributor'` transactions. This is actual purchased volume.
- Excludes `hub_dispense` (free drug / patient assistance program)
- Excludes `market_data` (third-party reported, not direct sales)

## Account-Level Aggregation

Metrics are typically aggregated at the **grandparent** organization level (`grandparent_org_name` in the `organizations` table). This represents the top-level health system or IDN.

When a user asks about "accounts" or "top accounts" without specifying a level, default to grandparent-level aggregation.

For facilities without a grandparent, use the facility's own `org_name`.
