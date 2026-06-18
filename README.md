# Women Entrepreneurship Programs — Cross-Country DiD/DDD

BA thesis. Scrapes US and Mexico state-level labor panels and estimates the effect of
Canada's **Women Entrepreneurship Strategy (WES, 2018)** on women's self-employment in
**PSTS** (Professional, Scientific & Technical Services), with **Mexico as the control**.
Canadian data and the original DiD are in the [`WESEffectsDiD`](WESEffectsDiD/) submodule.

Author: Benedict Scavillo

## Data

Per-country panels live in `<country>_data/` (`aggregatedData.csv` + validation report + log),
long format (`State × Year × Sex`): `LaborForce`, `UnemploymentRate`, `Employed`, `Unemployed`,
and a PSTS self-employment column. Both pulled **2026-06-18**.

| Country | Source | Coverage | PSTS column |
|---------|--------|----------|-------------|
| US | Census API — ACS 1-year B23001; ASE/ABS NAICS 54 — [scraper](us/us_scraper.py) | 51 states, 2014–2025 | `BusinessOwnersPSTS` |
| Mexico | INEGI ENOE microdata, quarterly → annual — [scraper](mexico/mexico_scraper.py) | 32 states, 2014–2024 | `SelfEmployedPSTS` |
| Canada | StatCan 14-10-0027-01 + 14-10-0327-01 (submodule) | provinces | `Self_Employed` |

US `BusinessOwnersPSTS` counts **employer firms** (`FIRMPDEMP`), not self-employed persons —
not comparable to Canada/Mexico (see report). Missing cells are `NaN`, never interpolated.

## Calculations

Outcome: `log(self-employed PSTS / labor force)` by unit × year × gender; unemployment as control.

- Pre-trends / control DiD — [mexico/main_mexico.ipynb](mexico/main_mexico.ipynb), [us/main_us.ipynb](us/main_us.ipynb) → `*/results/`
- Triple-difference (Canada vs Mexico, 2014–2024) — [main_DDD.ipynb](main_DDD.ipynb) → [ddd_results/](ddd_results/):

  ```
  log_rate ~ female + female:Post + female:canada + canada:Post
             + female:canada:Post + unemp + C(geo) + C(year)
  ```
  WES effect = the triple interaction `female:canada:Post`.

## Setup

```bash
git clone --recurse-submodules <repo>
pip install -r requirements.txt
echo "CENSUS_API_KEY=your_key" > .env   # free key: https://api.census.gov/data/key_signup.html
python us/us_scraper.py
python mexico/mexico_scraper.py
```
