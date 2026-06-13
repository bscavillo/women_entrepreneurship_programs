# Data Validation Report

## 1. Sample Size and Panel Structure

| Metric | Value |
|--------|-------|
| Total rows | 612 |
| Unique states | 51 (50 states + DC) |
| Years covered | 2014–2025 (12 years) |
| Expected rows (51 × 12) | 612 |
| Panel balanced | Yes |

## 2. Coverage Completeness

- **Missing state-year rows:** 0
- **Duplicate state-year rows:** 0

**ACS labor-force variables** — available for 9 of 12 years.
Missing years: [2020, 2024, 2025] (see Section 9).

**Business ownership variables (PSTS / NAICS 54)** — state coverage by year:

| Year | Source | States with male data | States with female data |
|------|--------|-----------------------|------------------------|
| 2014 | ASE | 51 | 51 |
| 2015 | ASE | 51 | 51 |
| 2016 | ASE | 51 | 51 |
| 2017 | ABS | 51 | 51 |
| 2018 | ABS | 50 | 45 |
| 2019 | ABS | 48 | 45 |
| 2020 | ABS | 49 | 47 |
| 2021 | ABS | 49 | 47 |
| 2022 | ABS | 51 | 50 |
| 2023 | ABS | 50 | 51 |
| 2024 | — | 0 | 0 |
| 2025 | — | 0 | 0 |

## 3. Missing Values by Column

| Column | Missing (n) | Missing (%) | Cause |
|--------|-------------|-------------|-------|
| male_employed | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| female_employed | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| male_unemployed | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| female_unemployed | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| male_labor_force | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| female_labor_force | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| male_unemployment_rate | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| female_unemployment_rate | 153 | 25.0% | 2020 COVID ACS gap; 2024–2025 not yet released |
| male_business_owners_psts | 111 | 18.1% | 2024–2025 ABS not released (102) + 9 suppression flags |
| female_business_owners_psts | 123 | 20.1% | 2024–2025 ABS not released (102) + 21 suppression flags |

## 4. Data Integrity Checks

| Check | Count | Result |
|-------|-------|--------|
| Negative values in any numeric column | 0 | **PASS** |
| Male: unemployed > labor_force | 0 | **PASS** |
| Male: employed > labor_force | 0 | **PASS** |
| Female: unemployed > labor_force | 0 | **PASS** |
| Female: employed > labor_force | 0 | **PASS** |
| Male: |labor_force − (employed + unemployed)| > 1 | 0 | **PASS** |
| Female: |labor_force − (employed + unemployed)| > 1 | 0 | **PASS** |
| Male: stored rate ≠ unemployed / labor_force (tol 1e-6) | 0 | **PASS** |
| Female: stored rate ≠ unemployed / labor_force (tol 1e-6) | 0 | **PASS** |
| Duplicate state-year rows | 0 | **PASS** |
| Zero values in male_business_owners_psts after suppression fix | 0 | **PASS** |
| Zero values in female_business_owners_psts after suppression fix | 0 | **PASS** |

## 5. Summary Statistics (non-missing observations)

| Variable | n | min | p25 | median | mean | p75 | max | std |
|----------|---|-----|-----|--------|------|-----|-----|-----|
| male_employed | 459 | 152796 | 395598 | 1037050 | 1607134 | 1902516 | 10268688 | 1834442 |
| female_employed | 459 | 128582 | 352943 | 966511 | 1453963 | 1767120 | 8852741 | 1600739 |
| male_unemployed | 459 | 4168 | 20299 | 59587 | 93383 | 109373 | 885118 | 119219 |
| female_unemployed | 459 | 3795 | 16372 | 51106 | 81805 | 96264 | 796213 | 105756 |
| male_labor_force | 459 | 158181 | 419334 | 1103775 | 1700517 | 1989413 | 10809726 | 1948769 |
| female_labor_force | 459 | 133615 | 371754 | 1022143 | 1535768 | 1850798 | 9358980 | 1702074 |
| male_unemployment_rate | 459 | 0.0205 | 0.0417 | 0.0510 | 0.0527 | 0.0622 | 0.0989 | 0.0152 |
| female_unemployment_rate | 459 | 0.0192 | 0.0381 | 0.0477 | 0.0493 | 0.0581 | 0.0984 | 0.0149 |
| male_business_owners_psts | 501 | 780 | 2524 | 6295 | 10634 | 13289 | 79662 | 13528 |
| female_business_owners_psts | 489 | 173 | 878 | 1970 | 3963 | 4844 | 33484 | 5347 |

## 6. Unemployment Rates by Year (cross-state mean)

| Year | Male u-rate | Female u-rate | Observations |
|------|-------------|---------------|--------------|
| 2014 | 0.0694 | 0.0651 | 51 |
| 2015 | 0.0612 | 0.0569 | 51 |
| 2016 | 0.0573 | 0.0527 | 51 |
| 2017 | 0.0525 | 0.0487 | 51 |
| 2018 | 0.0494 | 0.0454 | 51 |
| 2019 | 0.0459 | 0.0417 | 51 |
| 2020 | n/a | n/a | 0 |
| 2021 | 0.0585 | 0.0551 | 51 |
| 2022 | 0.0405 | 0.0388 | 51 |
| 2023 | 0.0398 | 0.0391 | 51 |
| 2024 | n/a | n/a | 0 |
| 2025 | n/a | n/a | 0 |

## 7. PSTS Business Ownership by Year (mean across non-suppressed states)

| Year | Source | States (male) | Mean male firms | States (female) | Mean female firms |
|------|--------|--------------|-----------------|----------------|-------------------|
| 2014 | ASE | 51 | 10118 | 51 | 3276 |
| 2015 | ASE | 51 | 10201 | 51 | 3402 |
| 2016 | ASE | 51 | 10364 | 51 | 3516 |
| 2017 | ABS | 51 | 10417 | 51 | 3673 |
| 2018 | ABS | 50 | 10655 | 45 | 4052 |
| 2019 | ABS | 48 | 11032 | 45 | 4242 |
| 2020 | ABS | 49 | 10882 | 47 | 4402 |
| 2021 | ABS | 49 | 11043 | 47 | 4354 |
| 2022 | ABS | 51 | 10700 | 50 | 4399 |
| 2023 | ABS | 50 | 10986 | 51 | 4434 |
| 2024 | — | 0 | n/a | 0 | n/a |
| 2025 | — | 0 | n/a | 0 | n/a |

## 8. Census Suppression Flags (resolved to NaN)

The Census Bureau withholds employer-firm counts where publication would disclose data for individual companies (flag D) or where the estimate does not meet publication standards (flag S). The ABS/ASE API returns these cells as 0 in the FIRMPDEMP field. All 30 such observations have been replaced with NaN in the cleaned dataset.

**Male suppression (9 obs):** IN 2021, ME 2019, ND 2021, NH 2020, RI 2020, SD 2019, WV 2019, WV 2023, WY 2018.

**Female suppression (21 obs):** AK 2019, AL 2019, CO 2018, DC 2018, DC 2021, DE 2019, DE 2022, HI 2020, HI 2021, ME 2019, MN 2021, NE 2018, NE 2019, NH 2020, RI 2018, RI 2020, RI 2021, TN 2018, WA 2019, WV 2018, WV 2020.

Suppression is more prevalent for female-owned firms (21 vs 9), consistent with smaller cell sizes in states where female PSTS ownership is concentrated in few firms. Consecutive-year suppression (HI 2020–2021; NE 2018–2019; RI 2020–2021) indicates persistent disclosure concerns, not data-collection failures.

## 9. Known Data Limitations

### ACS 1-year 2020

Census suspended the standard ACS 1-year release due to COVID-19 data-collection disruption. All 51 state rows for 2020 have NaN for every labor-force column. The 2020 experimental estimates (released separately by Census) are not used here because they carry much wider margins of error and are not directly comparable with the standard 1-year series.

### ACS 1-year 2024–2025

Not yet published as of June 2026. ACS 1-year estimates are released approximately 9 months after the reference year. These rows exist in the panel skeleton but carry NaN for all labor-force columns.

### Business ownership series: ASE → ABS break (2016/2017)

2014–2016 data come from the Annual Survey of Entrepreneurs (ASE, ase/csa, NAICS2012). 2017–2021 data come from the Annual Business Survey (ABS, abscs, NAICS2017). 2022–2023 data come from ABS with NAICS2022 coding. The NAICS 54 boundary (Professional, Scientific, and Technical Services) is stable across all three classifications, making the series substantively comparable. However, the ASE and ABS differ in sampling frame, weighting, and imputation, which may introduce a small level break at the 2016/2017 seam. Any econometric model should include a post-2016 indicator or test for a break.

### Business ownership 2024–2025

ABS 2024+ data are not yet available via the Census API as of June 2026. Typical publication lag is 18–24 months after the reference year.

### FIRMPDEMP: employer firms only

FIRMPDEMP counts only employer firms with paid employees. Non-employer businesses (self-employed with no payroll) — which account for a large share of female-owned PSTS activity — are excluded. This systematically understates female entrepreneurship relative to a broader measure.

### Majority-ownership threshold

ABS/ASE classify a firm as female-owned only if >50% female-owned (SEX code 002). Equally male/female co-owned firms (SEX code 004) are excluded from both the male and female counts. This undercounts partnership-based entrepreneurship, which disproportionately affects female owners.

