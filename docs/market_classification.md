# Product Market Classification

## Overview

Each product in the `products` table is classified into a therapeutic market hierarchy that determines which drugs compete with each other for market share analysis.

## Market Hierarchy

```
specialty (top level)
  └── market_category (therapeutic area)
        └── market_subcategory (specific drug class)
```

### Specialty
- **Oncology** — cancer treatment drugs
- **Urology** — urological treatment drugs (primarily prostate cancer)

### Market Categories and Subcategories

#### Oncology Markets

| market_category | market_subcategory | NovaPharma Brand | Key Competitors |
|---|---|---|---|
| Taxanes | Docetaxel | ZENOVAX | TAXOTERE, DOCETAXEL GENERIC |
| Taxanes | Paclitaxel | — | ABRAXANE |
| Platinum Compounds | Carboplatin | CARBOTREL | PARAPLATIN, CARBOPLATIN GENERIC |
| Platinum Compounds | Cisplatin | — | CISPLATIN GENERIC |
| Platinum Compounds | Oxaliplatin | — | OXALIPLATIN GENERIC |
| Antimetabolites | Gemcitabine | GEMTARA | GEMZAR, GEMCITABINE GENERIC |
| Antimetabolites | Pemetrexed | PAXELIUM | ALIMTA, PEMETREXED GENERIC |
| Antiemetics | Palonosetron | ONCOSETRON | ALOXI, PALONOSETRON GENERIC |
| Alkylating Agents | Cyclophosphamide | CYCLONOVA | CYTOXAN, CYCLOPHOSPHAMIDE GENERIC |
| Immunotherapy | PD-1 Inhibitors | — | KEYTRUDA, OPDIVO |
| Angiogenesis Inhibitors | VEGF Inhibitors | — | AVASTIN, BEVACIZUMAB BIOSIMILAR |
| Anthracyclines | Doxorubicin | — | DOXORUBICIN GENERIC |
| Topoisomerase Inhibitors | Irinotecan | — | IRINOTECAN GENERIC |
| EGFR Inhibitors | Cetuximab | — | ERBITUX |

#### Urology Markets

| market_category | market_subcategory | NovaPharma Brand | Key Competitors |
|---|---|---|---|
| GnRH Agonists | Leuprolide | LUPREX DEPOT | LUPRON DEPOT, ELIGARD |
| GnRH Antagonists | Degarelix | — | FIRMAGON |
| Antiandrogens | Enzalutamide | — | XTANDI |
| CYP17 Inhibitors | Abiraterone | — | ZYTIGA |

## Using Market Classification for Queries

### Market Share by Drug
To calculate market share for a specific NovaPharma product, match on `market_subcategory`:

```sql
-- Market share for ZENOVAX in the Docetaxel market
-- Numerator: NovaPharma distributor volume
SELECT SUM(s.pack_units * p.unit_conversion_factor) as nova_equivalents
FROM sales s
JOIN products p ON s.ndc = p.ndc
WHERE s.data_source = 'distributor'
  AND s.brand_flag = 1
  AND p.market_subcategory = 'Docetaxel'

-- Denominator: Total market volume
SELECT SUM(s.pack_units * p.unit_conversion_factor) as market_equivalents
FROM sales s
JOIN products p ON s.ndc = p.ndc
WHERE s.data_source = 'market_data'
  AND p.market_subcategory = 'Docetaxel'
```

### Market Size by Category
For broader market analysis, group by `market_category`:

```sql
SELECT p.market_category, SUM(s.pack_units * p.unit_conversion_factor) as total_equivalents
FROM sales s
JOIN products p ON s.ndc = p.ndc
WHERE s.data_source = 'market_data'
GROUP BY p.market_category
```

## NovaPharma Product Portfolio

NovaPharma has 7 branded products (identified by `brand_flag = 1` in the products table):

| Brand Name | Generic Name | Specialty | Strength |
|---|---|---|---|
| ZENOVAX | docetaxel | Oncology | 80MG, 20MG |
| CARBOTREL | carboplatin | Oncology | 450MG, 150MG |
| GEMTARA | gemcitabine | Oncology | 1000MG, 200MG |
| PAXELIUM | pemetrexed | Oncology | 500MG, 100MG |
| ONCOSETRON | palonosetron | Oncology | 0.25MG |
| CYCLONOVA | cyclophosphamide | Oncology | 1G, 500MG |
| LUPREX DEPOT | leuprolide | Urology | 22.5MG, 7.5MG |

The `brand_flag` field on both `products` and `sales` tables identifies NovaPharma products (1) vs. competitor products (0).
