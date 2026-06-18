# Data Validation Report — Mexico

## Shape

This dataset is in **long format** (one row per State x Year x Sex), mirroring the Canadian StatCan reference layout.

| Metric | Value |
|--------|-------|
| Rows | 704 |
| Unique states | 32 |
| Unique years | 11 |
| Sex categories | Male, Female |
| Quarterly files expected | 44 |
| Quarterly files processed | 43 |

## Missing Quarters

- Count: **1** of 44
- Missing: 2020 Q2
- Note: 2020 Q2 is the ETOE telephone survey (COVID-19 substitute). Its public release carries no `fac` expansion weight, so it cannot be tabulated; the 2020 annual figure is the mean of Q1, Q3 and Q4.

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
| LaborForce | 0 | 0.0% |
| UnemploymentRate | 0 | 0.0% |
| Employed | 0 | 0.0% |
| Unemployed | 0 | 0.0% |
| SelfEmployedPSTS | 0 | 0.0% |

## Rate Consistency

UnemploymentRate is derived as 100 x Unemployed / LaborForce and rounded to the nearest tenth. Check below confirms stored rate matches that formula (tolerance 0.05 pp, i.e. half the rounding step).

- Inconsistent rows: **0**

## Known Methodological Notes

### PSTS sector definition (scian == 12)

The ENOE/ENOE-N variable `scian` groups economic activity into 21 SCIAN sectors. Code 12 = 'Servicios profesionales, científicos y técnicos', the exact equivalent of US NAICS 54. The coding is identical across the old ENOE (2014–2020 Q1), ENOE N (2020 Q3–2022) and current ENOE (2023+), so the PSTS series is comparable across the whole panel.

### Analysis universe

All tabulations apply INEGI's standard universe before weighting: R_DEF=0 (complete interview), C_RES in {1,3} (usual resident), age 15–98. This reproduces INEGI's published labor-force totals.

### ETOE 2020 Q2 (May/June/August)

Telephone substitute during COVID-19. The CSV files are no longer served; the DBF releases contain only a household roster (no employment variables or expansion weight), so 2020 Q2 could not be incorporated. The 2020 annual figure is the mean of Q1, Q3 and Q4.

### Survey-design breaks

Two methodological breaks exist: old ENOE → ENOE N (2020 Q3, new sample design after the COVID interruption) and ENOE N → current ENOE (2023). Core concepts (clase1/clase2/pos_ocu/scian) are defined consistently across all three, but small level shifts around 2020 should be expected.

### PSTS self-employed (SelfEmployedPSTS)

Counts ENOE-expanded persons who are employers (patrones, pos_ocu=2) OR own-account workers (cuenta propia, pos_ocu=3) in the PSTS sector — i.e. the TOTAL self-employed in PSTS. Unit is persons, not firms (unlike the US BusinessOwnersPSTS firm counts). This total matches the Canadian StatCan 'Self-employed' class (which also includes both groups), enabling a like-for-like comparison. Only the total is exported (as SelfEmployedPSTS); the employer/own-account split is computed internally just to form the total. The analysis tests the all-PSTS total only.

### Long format (mirrors Canadian StatCan layout)

Output is one row per State x Year x Sex (Sex in {Male, Female}), matching the Canadian reference dataset. Counts (LaborForce, Employed, Unemployed, SelfEmployedPSTS) are raw ENOE-expanded persons; UnemploymentRate is a percentage rounded to the nearest tenth, derived as 100 x Unemployed / LaborForce (ENOE does not publish a state x sex annual rate directly at this aggregation).

