# Data Validation Report

## Shape

This dataset is in **long format** (one row per State x Year x Sex), mirroring the Canadian StatCan reference layout.

| Metric | Value |
|--------|-------|
| Rows | 1020 |
| Unique states | 51 |
| Unique years | 10 |
| Sex categories | Male, Female |

Coverage is **2014–2023**. No rows are emitted for 2024–2025: neither source (ACS 1-year, ABS) has published those reference years as of June 2026, so rather than carry all-NaN rows the years are omitted from the panel entirely.

## Missing State-Year-Sex Combinations

- Count: **0**

## Duplicate Rows

- Count: **0**

## Missing Values by Column

| Column | Missing (n) | Missing (%) |
|--------|------------|-------------|
| State | 0 | 0.0% |
| Year | 0 | 0.0% |
| Sex | 0 | 0.0% |
| LaborForce | 102 | 10.0% |
| UnemploymentRate | 102 | 10.0% |
| Employed | 102 | 10.0% |
| Unemployed | 102 | 10.0% |
| BusinessOwnersPSTS | 0 | 0.0% |

The only remaining missing values are the four labor-force columns for **2020** (one State × Sex grid, 102 rows): the standard 2020 ACS 1-year was suspended, but ABS still publishes 2020 PSTS business owners, so those rows are retained with PSTS present and labor force NaN.

## Unemployment Rate Consistency

UnemploymentRate is derived as 100 x Unemployed / LaborForce and rounded to the nearest tenth. Check below confirms stored rate matches that formula (tolerance 0.05 pp, i.e. half the rounding step).

- Inconsistent rows: **0**

## Known Data Availability Gaps

### ACS 1-year 2020

Census suspended the standard 2020 ACS 1-year release due to COVID-19 data-collection disruption. These rows contain NaN for all labor-force columns.

### 2024–2025 omitted from the panel

Neither source has published these reference years as of June 2026 (ACS 1-year is released ~9 months after the reference year; ABS lags 18–24 months). Because every column would be NaN, no rows are emitted for 2024–2025 — the panel ends at 2023.

### ASE/ABS PSTS 2014–2023

Business ownership by sex is drawn from two consecutive Census surveys: the Annual Survey of Entrepreneurs (ASE, ase/csa) for 2014-2016, and the Annual Business Survey (ABS, abscs) for 2017-2023. Both use FIRMPDEMP (employer firms with paid employees) and identical SEX coding. ASE uses NAICS2012; ABS uses NAICS2017 (2017-2021) and NAICS2022 (2022-2023). The NAICS 54 industry boundary is stable across all three classifications.

### PSTS measure is employer FIRMS, not self-employed persons (cross-country caveat)

BusinessOwnersPSTS is FIRMPDEMP — employer firms (with paid employees) by majority-owner sex — NOT a count of self-employed persons. It is therefore NOT directly comparable to Canada's StatCan 'Self-employed' persons in PSTS (Self_Employed) or Mexico's ENOE self-employed persons, and it excludes own-account / non-employer businesses. The column deliberately keeps the name BusinessOwnersPSTS (rather than the standardized Self_Employed used for Mexico/Canada) to flag this different construct. A comparable US self-employed-PERSONS series by state x sex x PSTS industry is not reliably available: the only such microdata (ACS PUMS) yields female-PSTS cells too small to be reliable (heavy sampling error and suppression), so obtaining the information INEGI/StatCan publish directly is prohibitively difficult. The employer-firm proxy is retained by design.

