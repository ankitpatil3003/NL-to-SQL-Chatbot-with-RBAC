# Organization Hierarchy

## Overview

Healthcare organizations are structured in a three-level hierarchy:

```
Grandparent (Health System / IDN)
  └── Parent (Hospital / Clinic Group)
        └── Facility (Individual Site)
```

## Hierarchy Levels

### Grandparent (`org_type = 'Grandparent'`)
The top-level entity — typically an Integrated Delivery Network (IDN) or health system. This is the primary level for account analytics and ranking.

**Examples:** Memorial Health System, Great Lakes Health Alliance, Lone Star Cancer Centers

**Key fields:**
- `org_id` — unique identifier
- `org_name` — system name
- `org_archetype` — typically 'IDN'
- `gpo_name` — the Group Purchasing Organization this system is affiliated with

### Parent (`org_type = 'Parent'`)
An intermediate grouping — usually a hospital or clinic group within a health system.

**Key fields:**
- `parent_org_id` — not used (this IS the parent level)
- `grandparent_org_id` → links to the grandparent's `org_id`
- `grandparent_org_name` → the grandparent's name

### Facility (`org_type = 'Facility'`)
The individual site where drugs are administered — a specific infusion center, clinic, or pharmacy.

**Key fields:**
- `parent_org_id` → links to the parent's `org_id`
- `parent_org_name` → the parent's name
- `grandparent_org_id` → links to the grandparent's `org_id`
- `grandparent_org_name` → the grandparent's name

## Joining Sales to Hierarchy

The `sales` table records transactions at the **facility** level via `sales.org_id`. To roll up sales to the parent or grandparent level:

```sql
-- Sales by grandparent account
SELECT
    COALESCE(o.grandparent_org_name, o.org_name) AS account_name,
    SUM(s.wac) AS revenue
FROM sales s
JOIN organizations o ON s.org_id = o.org_id
WHERE s.data_source = 'distributor' AND s.brand_flag = 1
GROUP BY account_name
ORDER BY revenue DESC
```

**Important:** Use `COALESCE(o.grandparent_org_name, o.org_name)` because standalone facilities (without a parent/grandparent) have NULL hierarchy fields. The COALESCE falls back to the facility's own name.

## Standalone Facilities

Some organizations operate independently without a parent hierarchy. These have:
- `org_type = 'Facility'`
- `parent_org_id = NULL`
- `grandparent_org_id = NULL`

When aggregating at the grandparent level, treat these as their own top-level account.

## GPO Affiliation

Group Purchasing Organizations (GPOs) negotiate drug pricing for their member health systems. The `gpo_name` field on the organization record indicates the primary GPO affiliation.

Common GPOs in this dataset:
- **Onmark** — large community oncology GPO
- **ION** — integrated oncology network
- **Unity** — multi-specialty GPO
- **VitalSource** — specialty pharmacy GPO

GPO affiliation is relevant for understanding purchasing channels and contract pricing.

## 340B Program

Organizations with `is_340b = 1` participate in the federal 340B Drug Pricing Program, which provides discounted drug pricing to eligible healthcare entities. These are typically safety-net hospitals or federally qualified health centers.

When analyzing sales:
- 340B and non-340B volumes are often reported separately
- Market share calculations may exclude or separately break out 340B volume
