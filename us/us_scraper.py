"""
us_scraper.py

Builds a state-year panel dataset (2014-2023) for the United States.

Data Sources
============
1. ACS 1-Year Estimates, Table B23001
   "SEX BY AGE BY EMPLOYMENT STATUS FOR THE CIVILIAN NONINSTITUTIONAL
   POPULATION 16 YEARS AND OVER"
   API: https://api.census.gov/data/{year}/acs/acs1
   Provides: civilian labor force, employed, unemployed — by sex, by state, annually.
   Coverage: 2014-2019, 2021-2023 (standard). 2020 standard release was suspended
             by Census due to COVID-19. 2024-2025 not yet published as of June 2026.

2. Annual Survey of Entrepreneurs – Company Summary (ase/csa)
   API: https://api.census.gov/data/{year}/ase/csa
   Provides: employer-firm counts by sex of majority owner, by NAICS, by state.
   NAICS 54 = "Professional, Scientific, and Technical Services" — used as the
   PSTS-sector proxy following the women's entrepreneurship literature.
   SEX codes: "003" = male-owned (>50% male), "002" = female-owned (>50% female)
   (same coding convention as ABS, confirmed via SEX_TTL attribute in the ASE API).
   Coverage: reference years 2014-2016 (ASE ran 2014-2016 before ABS replaced it).
   Industry coded under NAICS2012 for all three ASE years.

3. Annual Business Survey – Company Summary (abscs)
   API: https://api.census.gov/data/{year}/abscs
   Provides: employer-firm counts by sex of majority owner, by NAICS, by state.
   NAICS 54 = "Professional, Scientific, and Technical Services" — used as the
   PSTS-sector proxy following the women's entrepreneurship literature.
   SEX codes: "003" = male-owned (>50% male), "002" = female-owned (>50% female)
   (counter-intuitive ordering verified via SEX_LABEL attribute in the ABS API).
   Coverage: reference years 2017-2023 (ABS began 2017; 2024+ not yet released).
   Together with ASE (2014-2016), this gives an unbroken annual series 2014-2023.

Disclosure Suppression (FIRMPDEMP_F)
====================================
  Both ASE and ABS withhold small/low-quality cells: the API returns FIRMPDEMP=0
  together with a flag in FIRMPDEMP_F (almost always "S" = "estimate did not meet
  publication standards"). That 0 is a placeholder, NOT a count of zero employer
  firms. To avoid recording a misleading zero, every flagged cell is set to NaN
  (see _suppress_flagged). In the 2014-2023 NAICS-54 state panel this affects 30
  male/female cells, all in the ABS years (2018-2023), mostly female-owned in
  small states. They are NaN in the output and documented in the validation
  report; the analysis notebook drops them from the log-rate model.

PSTS Measure — Cross-Country Comparability (IMPORTANT)
======================================================
  BusinessOwnersPSTS (in the female/male rows of the long-format output) is an
  EMPLOYER-FIRM count (FIRMPDEMP: firms
  with at least one paid employee), classified by majority-owner sex. This is a
  fundamentally different construct from the self-employed-PERSONS counts used
  for Canada (StatCan LFS "Self-employed" in PSTS) and Mexico (ENOE persons with
  pos_ocu in {employer, own-account}). Specifically, the US series:
    - counts FIRMS, not persons;
    - includes ONLY employer firms (with paid employees) — it excludes
      own-account / non-employer businesses, which dominate self-employment;
    - is attributed by majority-owner sex, not the individual's own sex.
  It therefore CANNOT be relabeled as "self-employed persons" to match the other
  countries. The column name is deliberately kept as BusinessOwnersPSTS (NOT
  renamed to the standardized Self_Employed used for Mexico/Canada) so the
  differing construct stays visible in the schema.

  Why not source US self-employed PERSONS directly? A comparable
  state x sex x PSTS-industry self-employed-persons series is not reliably
  available from the US statistical agencies. The only microdata crossing
  class-of-worker x detailed-industry x sex x state is ACS PUMS, where the
  female-PSTS-self-employed cell is so small per state-year that estimates are
  dominated by sampling error and frequent suppression. Obtaining the same
  information the other national statistics offices (INEGI, StatCan) publish
  directly is thus prohibitively difficult and unreliable, so the ABS/ASE
  employer-firm proxy is retained by design and flagged here and in the
  validation report.

B23001 Table Structure (verified against Census variables API)
==============================================================
Male header: var 002
  Young age groups (16-64): 10 groups × 7 sub-vars each (starts at var 003)
    sub-var offsets: +0 total | +1 in_LF | +2 armed | +3 civilian_LF | +4 employed | +5 unemployed | +6 not_in_LF
    civilian_LF = group_start + 3
  Old age groups (65+): 3 groups × 5 sub-vars (starts at var 073)
    sub-var offsets: +0 total | +1 in_LF | +2 employed | +3 unemployed | +4 not_in_LF
    (no Armed Forces / Civilian split for 65+; in_LF ≡ civilian_LF for these groups)
    civilian_LF = group_start + 1

Female header: var 088 (= 002 + 1 + 10×7 + 3×5 = 002+86)
  Young groups: 10 groups × 7 vars (starts at var 089), same offsets as male
  Old groups: 3 groups × 5 vars (starts at var 159), same offsets as male

Output
======
  data/us/aggregatedData.csv         — long panel (1 row per State x Year x Sex),
                                       mirroring the Canadian StatCan layout
                                       (State, Year, Sex, LaborForce,
                                        UnemploymentRate, Employed, Unemployed,
                                        BusinessOwnersPSTS)
  data/us/data_validation_report.md  — validation checks and known data-gap notes
  data/us/scraper.log                — full API call log
"""

import os
import time
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

# ── Environment & paths ────────────────────────────────────────────────────────

load_dotenv()
CENSUS_API_KEY = os.getenv("CENSUS_API_KEY")
if not CENSUS_API_KEY:
    raise ValueError("CENSUS_API_KEY not found in .env file")

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "us"
OUT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(OUT_DIR / "scraper.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

BASE_URL = "https://api.census.gov/data"

FIPS_TO_STATE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "11": "DC", "12": "FL",
    "13": "GA", "15": "HI", "16": "ID", "17": "IL", "18": "IN",
    "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME",
    "24": "MD", "25": "MA", "26": "MI", "27": "MN", "28": "MS",
    "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI",
    "45": "SC", "46": "SD", "47": "TN", "48": "TX", "49": "UT",
    "50": "VT", "51": "VA", "53": "WA", "54": "WV", "55": "WI",
    "56": "WY",
}

ALL_YEARS = list(range(2014, 2024))
ACS_YEARS = list(range(2014, 2024))
ASE_YEARS = list(range(2014, 2017))
ABS_YEARS = list(range(2017, 2024))
ABS_PSTS_NAICS = "54"
# ABS switched from NAICS2017 to NAICS2022 as the industry variable starting with 2022 data.
ABS_NAICS_VAR = {y: ("NAICS2022" if y >= 2022 else "NAICS2017") for y in ABS_YEARS}

# ── B23001 variable lists (derived from verified Census table structure) ───────

_MALE_YOUNG_STARTS = [3 + i * 7 for i in range(10)]
_MALE_OLD_STARTS = [73, 78, 83]

_FEMALE_YOUNG_STARTS = [89 + i * 7 for i in range(10)]
_FEMALE_OLD_STARTS = [159, 164, 169]

def _build_vars(young_starts, old_starts):
    """Return (clf_vars, emp_vars, une_vars) for one sex section of B23001."""
    clf, emp, une = [], [], []
    for s in young_starts:
        clf.append(f"B23001_{s + 3:03d}E")
        emp.append(f"B23001_{s + 4:03d}E")
        une.append(f"B23001_{s + 5:03d}E")
    for s in old_starts:
        clf.append(f"B23001_{s + 1:03d}E")
        emp.append(f"B23001_{s + 2:03d}E")
        une.append(f"B23001_{s + 3:03d}E")
    return clf, emp, une


MALE_CLF_VARS,   MALE_EMP_VARS,   MALE_UNE_VARS   = _build_vars(_MALE_YOUNG_STARTS,   _MALE_OLD_STARTS)
FEMALE_CLF_VARS, FEMALE_EMP_VARS, FEMALE_UNE_VARS = _build_vars(_FEMALE_YOUNG_STARTS, _FEMALE_OLD_STARTS)

# ── Census API helper ──────────────────────────────────────────────────────────

def census_get(year: int, dataset: str, variables: list,
               geo: str = "state:*", predicates: dict = None) -> pd.DataFrame:
    """
    GET https://api.census.gov/data/{year}/{dataset}
    variables  : list of variable names (Census API limit: 50 per call)
    geo        : geography predicate string
    predicates : extra filter key-value pairs added to query string
    Returns a DataFrame; raises requests.HTTPError on non-2xx response.
    """
    url = f"{BASE_URL}/{year}/{dataset}"
    query = {
        "get": ",".join(variables),
        "for": geo,
        "key": CENSUS_API_KEY,
    }
    if predicates:
        query.update(predicates)

    log.info("GET %s  vars=%d  geo=%s  filters=%s", url, len(variables), geo, predicates)

    resp = requests.get(url, params=query, timeout=90)
    resp.raise_for_status()

    data = resp.json()
    if len(data) < 2:
        raise ValueError(f"Empty response: year={year} dataset={dataset}")

    return pd.DataFrame(data[1:], columns=data[0])


def _suppress_flagged(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Set FIRMPDEMP to NaN wherever the Census disclosure flag FIRMPDEMP_F is set.

    The ABS/ASE API returns a value of 0 for cells it withholds — most commonly
    flag "S" ("estimate did not meet publication standards"), but also "D"
    (disclosure), "N"/"X" (not available/applicable). That 0 is a placeholder,
    NOT a count of zero employer firms, so recording it would be misleading.
    Per the project's academic-transparency rule (missing is better than
    misleading) we convert every flagged cell to NaN and log how many. See
    data/us/data_validation_report.md. If FIRMPDEMP_F is absent the frame is
    returned unchanged.
    """
    if "FIRMPDEMP_F" not in df.columns:
        return df
    flagged = df["FIRMPDEMP_F"].notna() & (df["FIRMPDEMP_F"].astype(str).str.strip() != "")
    n = int(flagged.sum())
    if n:
        df.loc[flagged, "FIRMPDEMP"] = np.nan
        log.info("%s: %d suppressed PSTS cell(s) (FIRMPDEMP_F set) → NaN", label, n)
    return df

# ── ACS: labor force by sex ────────────────────────────────────────────────────

def fetch_acs_year(year: int):
    """
    Fetch state-level civilian LF / employed / unemployed by sex for one year.
    Makes two API calls (male vars, female vars — each 13 variables).
    Returns a DataFrame or None on failure.

    Note on 2020: Census did not publish standard ACS 1-year for 2020 (COVID-19
    disruption). We attempt the standard endpoint; a 404 is expected and logged.
    """
    dataset = "acs/acs1"
    male_vars   = MALE_CLF_VARS   + MALE_EMP_VARS   + MALE_UNE_VARS
    female_vars = FEMALE_CLF_VARS + FEMALE_EMP_VARS + FEMALE_UNE_VARS

    try:
        df_m = census_get(year, dataset, male_vars)
        time.sleep(0.3)
        df_f = census_get(year, dataset, female_vars)
        time.sleep(0.3)
    except requests.HTTPError as e:
        log.warning("ACS %d: HTTP %s — skipping", year, e.response.status_code)
        return None
    except Exception as e:
        log.warning("ACS %d: %s — skipping", year, e)
        return None

    for df, clf, emp, une in [
        (df_m, MALE_CLF_VARS,   MALE_EMP_VARS,   MALE_UNE_VARS),
        (df_f, FEMALE_CLF_VARS, FEMALE_EMP_VARS, FEMALE_UNE_VARS),
    ]:
        for col in clf + emp + une:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    prefix = {"m": ("male", df_m, MALE_CLF_VARS, MALE_EMP_VARS, MALE_UNE_VARS),
              "f": ("female", df_f, FEMALE_CLF_VARS, FEMALE_EMP_VARS, FEMALE_UNE_VARS)}

    results = {}
    for sex, df, clf, emp, une in prefix.values():
        df[f"{sex}_labor_force"] = df[clf].sum(axis=1)
        df[f"{sex}_employed"]    = df[emp].sum(axis=1)
        df[f"{sex}_unemployed"]  = df[une].sum(axis=1)
        results[sex] = df[["state", f"{sex}_labor_force", f"{sex}_employed", f"{sex}_unemployed"]]

    merged = results["male"].merge(results["female"], on="state")
    merged["year"]  = year
    merged["state"] = merged["state"].map(FIPS_TO_STATE)
    return merged.dropna(subset=["state"])

# ── ASE: business ownership by sex (PSTS / NAICS 54), 2014-2016 ───────────────

def fetch_ase_year(year: int):
    """
    Fetch employer-firm counts by sex of owner for NAICS 54 (PSTS) at state level
    using the Annual Survey of Entrepreneurs Company Summary (ase/csa).
    Covers 2014-2016 (ASE predecessor to ABS; all three years use NAICS2012).
    SEX codes follow the same convention as ABS:
      "001"=Total | "002"=Female-owned (>50%) | "003"=Male-owned (>50%)
    Returns DataFrame or None on failure.
    """
    try:
        df = census_get(
            year, "ase/csa",
            variables=["FIRMPDEMP", "FIRMPDEMP_F", "SEX"],
            predicates={"NAICS2012": ABS_PSTS_NAICS},
        )
        time.sleep(0.3)
    except requests.HTTPError as e:
        log.warning("ASE %d: HTTP %s — skipping", year, e.response.status_code)
        return None
    except Exception as e:
        log.warning("ASE %d: %s — skipping", year, e)
        return None

    df["FIRMPDEMP"] = pd.to_numeric(df["FIRMPDEMP"], errors="coerce")
    df = _suppress_flagged(df, f"ASE {year}")
    df["state_abbr"] = df["state"].map(FIPS_TO_STATE)
    df = df.dropna(subset=["state_abbr"])

    male_df   = (df[df["SEX"] == "003"][["state_abbr", "FIRMPDEMP"]]
                 .rename(columns={"state_abbr": "state",
                                  "FIRMPDEMP": "male_business_owners_psts"}))
    female_df = (df[df["SEX"] == "002"][["state_abbr", "FIRMPDEMP"]]
                 .rename(columns={"state_abbr": "state",
                                  "FIRMPDEMP": "female_business_owners_psts"}))

    if male_df.empty and female_df.empty:
        log.warning("ASE %d: no male/female SEX rows found — skipping", year)
        return None

    result = male_df.merge(female_df, on="state", how="outer")
    result["year"] = year
    return result


# ── ABS: business ownership by sex (PSTS / NAICS 54), 2017-2023 ───────────────

def fetch_abs_year(year: int):
    """
    Fetch employer-firm counts by sex of owner for NAICS 54 (PSTS) at state level.
    Uses FIRMPDEMP (number of employer firms with paid employees).
    # ABS SEX codes verified via SEX_LABEL attribute:
    #   "001"=Total | "002"=Female-owned (>50%) | "003"=Male-owned (>50%) | "004"=Equally male/female
    # Counter-intuitive ordering: 002=Female, 003=Male (confirmed empirically).
    Returns DataFrame or None on failure.
    """
    naics_var = ABS_NAICS_VAR[year]
    try:
        df = census_get(
            year, "abscs",
            variables=["FIRMPDEMP", "FIRMPDEMP_F", "SEX"],
            predicates={naics_var: ABS_PSTS_NAICS},
        )
        time.sleep(0.3)
    except requests.HTTPError as e:
        log.warning("ABS %d: HTTP %s — skipping", year, e.response.status_code)
        return None
    except Exception as e:
        log.warning("ABS %d: %s — skipping", year, e)
        return None

    df["FIRMPDEMP"] = pd.to_numeric(df["FIRMPDEMP"], errors="coerce")
    df = _suppress_flagged(df, f"ABS {year}")
    df["state_abbr"] = df["state"].map(FIPS_TO_STATE)
    df = df.dropna(subset=["state_abbr"])

    male_df   = (df[df["SEX"] == "003"][["state_abbr", "FIRMPDEMP"]]
                 .rename(columns={"state_abbr": "state",
                                  "FIRMPDEMP": "male_business_owners_psts"}))
    female_df = (df[df["SEX"] == "002"][["state_abbr", "FIRMPDEMP"]]
                 .rename(columns={"state_abbr": "state",
                                  "FIRMPDEMP": "female_business_owners_psts"}))

    if male_df.empty and female_df.empty:
        log.warning("ABS %d: no male/female SEX rows found — skipping", year)
        return None

    result = male_df.merge(female_df, on="state", how="outer")
    result["year"] = year
    return result

# ── Panel assembly ─────────────────────────────────────────────────────────────

def build_panel() -> pd.DataFrame:
    log.info("=== Fetching ACS 1-year labor force data (B23001) ===")
    acs_frames = []
    for year in ACS_YEARS:
        log.info("  ACS year %d", year)
        df = fetch_acs_year(year)
        if df is not None:
            acs_frames.append(df)
            log.info("    → %d state rows", len(df))
        else:
            log.info("    → skipped/unavailable")

    log.info("=== Fetching ASE business ownership data (NAICS 54 / PSTS, 2014-2016) ===")
    ase_frames = []
    for year in ASE_YEARS:
        log.info("  ASE year %d", year)
        df = fetch_ase_year(year)
        if df is not None:
            ase_frames.append(df)
            log.info("    → %d state rows", len(df))
        else:
            log.info("    → skipped/unavailable")

    log.info("=== Fetching ABS business ownership data (NAICS 54 / PSTS, 2017-2023) ===")
    abs_frames = []
    for year in ABS_YEARS:
        log.info("  ABS year %d", year)
        df = fetch_abs_year(year)
        if df is not None:
            abs_frames.append(df)
            log.info("    → %d state rows", len(df))
        else:
            log.info("    → skipped/unavailable")

    states = sorted(FIPS_TO_STATE.values())
    panel = pd.DataFrame(
        [(s, y) for s in states for y in ALL_YEARS],
        columns=["state", "year"],
    )

    if acs_frames:
        acs_df = pd.concat(acs_frames, ignore_index=True)
        panel = panel.merge(acs_df, on=["state", "year"], how="left")
    else:
        for col in ["male_employed", "female_employed", "male_unemployed",
                    "female_unemployed", "male_labor_force", "female_labor_force"]:
            panel[col] = np.nan

    biz_frames = ase_frames + abs_frames
    if biz_frames:
        biz_df = pd.concat(biz_frames, ignore_index=True)
        panel = panel.merge(biz_df, on=["state", "year"], how="left")
    else:
        panel["male_business_owners_psts"]   = np.nan
        panel["female_business_owners_psts"] = np.nan

    cols = [
        "state", "year",
        "male_employed", "female_employed",
        "male_unemployed", "female_unemployed",
        "male_labor_force", "female_labor_force",
        "male_business_owners_psts", "female_business_owners_psts",
    ]
    for c in cols:
        if c not in panel.columns:
            panel[c] = np.nan

    return panel[cols].sort_values(["state", "year"]).reset_index(drop=True)


def to_long(panel: pd.DataFrame) -> pd.DataFrame:
    """Reshape the internal wide panel into the long (one row per State-Year-Sex)
    layout that mirrors the Canadian StatCan dataset (Province, Year, Sex, ...).

    Conventions matched to the Canadian reference data:
      - one row per State x Year x Sex, Sex in {"Male", "Female"};
      - counts (LaborForce, Employed, Unemployed) as raw persons;
      - UnemploymentRate as a percentage rounded to the nearest tenth
        (derived as Unemployed / LaborForce; the ACS does not publish a
        state x sex unemployment rate directly — see validation report).
    The PSTS column keeps the US-specific name BusinessOwnersPSTS (employer
    FIRMS, not self-employed persons) to flag the different construct.
    """
    frames = []
    for sex_label, p in (("Male", "male"), ("Female", "female")):
        rate = (panel[f"{p}_unemployed"] / panel[f"{p}_labor_force"] * 100).round(1)
        frames.append(pd.DataFrame({
            "State": panel["state"],
            "Year": panel["year"],
            "Sex": sex_label,
            "LaborForce": panel[f"{p}_labor_force"],
            "UnemploymentRate": rate,
            "Employed": panel[f"{p}_employed"],
            "Unemployed": panel[f"{p}_unemployed"],
            "BusinessOwnersPSTS": panel[f"{p}_business_owners_psts"],
        }))

    long = pd.concat(frames, ignore_index=True)
    long["Sex"] = pd.Categorical(long["Sex"], categories=["Male", "Female"], ordered=True)
    # Employer-firm counts are integers; use a nullable integer dtype so the
    # disclosure-suppressed cells (NaN) render as empty without forcing the whole
    # column to float (e.g. 943 rather than 943.0).
    long["BusinessOwnersPSTS"] = long["BusinessOwnersPSTS"].astype("Int64")
    return long.sort_values(["State", "Year", "Sex"]).reset_index(drop=True)

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting US state-year panel build (2014-2023)")
    panel = build_panel()
    long = to_long(panel)

    out = OUT_DIR / "aggregatedData.csv"
    long.to_csv(out, index=False)
    log.info("Saved %d rows → %s", len(long), out)

    log.info("Done.")
