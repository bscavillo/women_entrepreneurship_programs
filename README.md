# Women Entrepreneurship Programs — Cross-Country DiD/DDD

This project scrapes US and Mexico state-level labor panels and estimates the effect of
Canada's **Women Entrepreneurship Strategy (WES, 2018)** on women's self-employment in
**PSTS** (Professional, Scientific & Technical Services), with **Mexico as the control**.
Canadian data and the original DiD are in the [`WESEffectsDiD`](WESEffectsDiD/) submodule.

Author: Benedict Scavillo

## Data

Data is formatted as (`State × Year × Sex`): `LaborForce`, `UnemploymentRate`, `Employed`, `Unemployed`,
and a PSTS self-employment column. All data was pulled on the **2026-06-18**.

| Country | Source | Coverage | PSTS column |
|---------|--------|----------|-------------|
| US | Census — [ACS 1-year B23001](https://data.census.gov/table/ACSDT1Y2023.B23001); [ASE](https://www.census.gov/programs-surveys/ase.html) / [ABS](https://www.census.gov/programs-surveys/abs.html) NAICS 54 | 51 states, 2014–2023 (2020 ACS NaN) | `BusinessOwnersPSTS` |
| Mexico | INEGI [ENOE](https://www.inegi.org.mx/programas/enoe/15ymas/#microdatos) microdata (+ [ETOE](https://www.inegi.org.mx/investigacion/etoe/#microdatos) 2020 Q2), quarterly → annual | 32 states, 2014–2024 | `SelfEmployedPSTS` |
| Canada | StatCan [14-10-0027-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410002701) + [14-10-0327-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410032701) (submodule) | provinces | `Self_Employed` |

US `BusinessOwnersPSTS` counts **employer firms** (`FIRMPDEMP`), not self-employed persons —
not comparable to Canada/Mexico (see report). Missing cells are `NaN`.

## Calculations

Outcome: `log(self-employed PSTS / labor force)` by unit × year × gender; unemployment as control.

Parallel trends are checked first via pre-2018 event-study plots (in each `results/` folder) to validate the control. A DiD then compares the treated (Canada) and control panels around the 2018 WES, and a DDD adds the gender dimension so the WES effect is isolated as the female × Canada × post interaction, netting out gender- and country-specific shocks.

## Setup

```bash
git clone --recurse-submodules <repo>
pip install -r requirements.txt
echo "CENSUS_API_KEY=your_key" > .env   # free key: https://api.census.gov/data/key_signup.html
python us/us_scraper.py
python mexico/mexico_scraper.py
```
