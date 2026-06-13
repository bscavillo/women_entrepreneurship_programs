# Data Validation Report — Mexico

## Shape

| Metric | Value |
|--------|-------|
| Rows | 352 |
| Unique states | 32 |
| Unique years | 11 |
| Quarterly files processed | 43 |

## Missing State-Year Combinations

- Count: **0**

## Duplicate Rows

- Count: **0**

## Missing Values by Column

| Column | Missing (n) | Missing (%) |
|--------|------------|-------------|
| state | 0 | 0.0% |
| year | 0 | 0.0% |
| male_employed | 0 | 0.0% |
| female_employed | 0 | 0.0% |
| male_unemployed | 0 | 0.0% |
| female_unemployed | 0 | 0.0% |
| male_labor_force | 0 | 0.0% |
| female_labor_force | 0 | 0.0% |
| male_unemployment_rate | 0 | 0.0% |
| female_unemployment_rate | 0 | 0.0% |
| male_business_owners_psts | 0 | 0.0% |
| female_business_owners_psts | 0 | 0.0% |
| male_psts_employers | 0 | 0.0% |
| female_psts_employers | 0 | 0.0% |
| male_psts_self_employed | 0 | 0.0% |
| female_psts_self_employed | 0 | 0.0% |
| male_psts_workers | 0 | 0.0% |
| female_psts_workers | 0 | 0.0% |

## Rate Consistency

- **Male**: 0 inconsistent rows
- **Female**: 0 inconsistent rows

## Known Methodological Notes

### PSTS sector definition (scian == 12)

The ENOE/ENOE-N variable `scian` groups economic activity into 21 SCIAN sectors. Code 12 = 'Servicios profesionales, científicos y técnicos', the exact equivalent of US NAICS 54. The coding is identical across the old ENOE (2014–2020 Q1), ENOE N (2020 Q3–2022) and current ENOE (2023+), so the PSTS series is comparable across the whole panel.

### Analysis universe

All tabulations apply INEGI's standard universe before weighting: R_DEF=0 (complete interview), C_RES in {1,3} (usual resident), age 15–98. This reproduces INEGI's published labor-force totals.

### ETOE 2020 Q2 (May/June/August)

Telephone substitute during COVID-19. The CSV files are no longer served; the DBF releases contain only a household roster (no employment variables or expansion weight), so 2020 Q2 could not be incorporated. The 2020 annual figure is the mean of Q1, Q3 and Q4.

### Survey-design breaks

Two methodological breaks exist: old ENOE → ENOE N (2020 Q3, new sample design after the COVID interruption) and ENOE N → current ENOE (2023). Core concepts (clase1/clase2/pos_ocu/scian) are defined consistently across all three, but small level shifts around 2020 should be expected.

### Business owners (male/female_business_owners_psts)

Counts ENOE-expanded persons who are employers (patrones, pos_ocu=2) or self-employed (cuenta propia, pos_ocu=3) in the PSTS sector. Unit is persons, not firms (unlike US ABS/ASE firm counts).

