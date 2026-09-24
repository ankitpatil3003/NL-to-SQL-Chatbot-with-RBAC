# Security & Access Control Model

## Overview

Not all users should see the same data. The chat assistant must enforce role-based access control so that each user only sees the data they are authorized to access. The `users` table defines each user's role, territory/region assignment, and pricing access.

## Roles

There are three roles, each with different data visibility:

### Exec

Executives have **global, unrestricted access** to all data across all territories and regions.

- **Data scope**: All organizations, all sales, all territories
- **WAC pricing**: Visible (`can_view_wac = 1`)
- **Use case**: C-suite, VP of Sales, Head of Commercial Analytics

### Director (Director of Sales)

Directors see data for **all territories within their assigned region**.

- **Data scope**: Organizations and sales within the director's assigned region
- **WAC pricing**: Hidden (`can_view_wac = 0`) — Directors cannot see pricing data
- **Use case**: Regional sales leadership — oversees multiple RAMs and territories within a region

### RAM (Regional Account Manager)

RAMs see data **only for their assigned territory**.

- **Data scope**: Organizations and sales within the RAM's assigned territory
- **WAC pricing**: Hidden (`can_view_wac = 0`)
- **Use case**: Field sales rep — manages accounts within a single territory

## Access Rules

### Row-Level Security — Territory / Region Filtering

When a user asks a question, the SQL query must be scoped to only the data they are authorized to see:

| Role | Scope |
|------|-------|
| Exec | All data — no restrictions |
| Director | Only data within their assigned region |
| RAM | Only data within their assigned territory |

This applies to organizations, sales, and any derived metrics. A user should never see data outside their scope.

### Column-Level Security — WAC Restriction

The `wac` column in the `sales` table contains wholesale acquisition cost (pricing data). This is sensitive and must be restricted:

| Role | WAC access |
|------|-----------|
| Exec | Full access — can see WAC values, run revenue queries |
| Director | **No access** — WAC must be excluded from results. Revenue queries should return unit-based metrics instead |
| RAM | **No access** — WAC must be excluded from results. Revenue queries should be blocked or return unit-based metrics (pack_units, equivalents) instead |

**When a RAM asks a revenue question** (e.g., "What are my total sales in dollars?"), the assistant should either:
- Respond that pricing data is not available for their access level, or
- Offer an alternative: "I can show you sales volume in units instead. Would you like that?"

**What this means for SQL generation:**
- For Exec: queries can SELECT and aggregate `wac`
- For Director/RAM: queries must **never** include `wac` in SELECT, WHERE, ORDER BY, or any aggregation. Use `pack_units` or `total_mg` for volume-based analysis instead.

### Market Data Access

Market data (`data_source = 'market_data'`) follows the same territory/region scoping rules. A RAM can see market data for their territory, a Director for their region.

### Product and ZIP Reference Tables

The `products` and `zip_territory` tables are reference data with no access restrictions. All users can see all rows in these tables.

## User Identification

The chat interface must identify the logged-in user (by `user_id` or `email`) and apply the appropriate access rules on every query. How you implement authentication (session, JWT, simple login, etc.) is up to you, but the access control must be enforced.

## Test Scenarios

Consider these scenarios when building your access control:

1. **RAM asks "What are our total sales?"** → Should see only their territory's volume in units (not dollars)
2. **Director asks "What are our total sales?"** → Should see their region's volume in units (not dollars — no WAC access)
3. **Exec asks "What are our total sales?"** → Should see company-wide sales with full pricing
4. **RAM asks "Show me market share for Zenovax"** → Should see market share for their territory only
5. **RAM asks "Compare all territories"** → Should be denied or shown only their own territory
6. **Director asks "Compare territories in my region"** → Should see all territories within their region
