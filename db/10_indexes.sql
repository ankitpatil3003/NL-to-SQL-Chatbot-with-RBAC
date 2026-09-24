-- Indexes for the query shapes the assistant generates. Additive only; base tables unchanged.
-- Each index was kept only if EXPLAIN ANALYZE on the full 2M-row dataset showed the planner using
-- it and the query getting faster (numbers in the commit that introduced this file). Rejected:
-- a plain sales(org_id) index made territory/region-scoped queries 1.6-2.8x SLOWER (nested loop
-- fetched ~52 rows per facility and discarded 50), and sales(ndc) was never chosen.

-- RBAC scoping path: zip_territory (territory/region) -> organizations.zip -> sales.org_id.
CREATE INDEX IF NOT EXISTS ix_zip_territory_name ON zip_territory (territory_name);
CREATE INDEX IF NOT EXISTS ix_zip_region_name ON zip_territory (region_name);
CREATE INDEX IF NOT EXISTS ix_orgs_zip ON organizations (zip);

-- Per-facility lookups that also carry the near-universal filters (paid demand = distributor +
-- brand_flag = 1, offset-based time windows), so they're applied inside the index instead of
-- after fetching every sale. Leading org_id also serves single-account drill-downs.
CREATE INDEX IF NOT EXISTS ix_sales_org_source_brand_mo ON sales (org_id, data_source, brand_flag, mo_offset);

-- Company-wide time-window questions ("revenue last month", "R3M volume").
CREATE INDEX IF NOT EXISTS ix_sales_source_brand_mo ON sales (data_source, brand_flag, mo_offset);
