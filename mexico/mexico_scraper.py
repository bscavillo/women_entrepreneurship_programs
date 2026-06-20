"""
mexico_scraper.py

Builds a state-year panel dataset (2014-2024) for Mexico.

Data Source
===========
ENOE / ENOE N — Encuesta Nacional de Ocupación y Empleo
  INEGI's National Survey of Occupation and Employment (quarterly).
  Provides: labor force, employed, unemployed by sex and state (32 entities).
  Also provides industry sector (SCIAN) and employment position (employer /
  self-employed / employee) for the professional services proxy.

  URL patterns (publicly downloadable, no authentication required):
    Old ENOE  (2014 Q1 – 2020 Q1):
      https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos/
        {YEAR}trim{Q}_csv.zip
    ETOE      (2020 Q2, telephone survey during COVID-19):
      https://www.inegi.org.mx/contenidos/investigacion/etoe/microdatos/
        etoe_2020_{MES}_csv.zip  (mes = "mayo", "junio", "agosto")
    ENOE N    (2020 Q3 – 2022 Q4, "Nueva Edición"):
      https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos/
        enoe_n_{YEAR}_trim{Q}_csv.zip
    ENOE      (2023 Q1 – present, post-ENOE-N classic survey):
      https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos/
        enoe_{YEAR}_trim{Q}_csv.zip
      (Note: when ENOE N ended after 2022, INEGI dropped the '_n' but KEPT the
       underscore-delimited format — NOT the pre-2020 bare '{YEAR}trim{Q}'.)

  Inside each ZIP, the SDEM (sociodemographic) table is the primary source.
  File names follow the pattern SDEM{Q}{2-digit-year}.csv (e.g. SDEM114.csv
  for Q1 2014).  The scraper searches the ZIP adaptively for SDEM* files.

Key SDEM Variables (all pre-coded by INEGI before public release)
===================================================================
  ent        : Entity (state) code, 01–32
  sex        : Sex  1=Male  2=Female
  clase1     : Labor force status  1=Economically active (PEA)  2=Inactive
  clase2     : Employment status   1=Employed  2=Open unemployed
                                   3=Available (not searching)  4=N/A
  scian      : SCIAN sector grouping into 21 categories (NOT a 4-digit code).
               Code 12 = "Servicios profesionales, científicos y técnicos",
               the exact equivalent of US NAICS 54.  Present (and identically
               coded) across all ENOE/ENOE-N years 2014–present.
  pos_ocu    : Position in occupation
                 1 = Subordinate paid worker (trabajador subordinado y remunerado)
                 2 = Employer / patrón   (owns business with paid employees)
                 3 = Self-employed / cuenta propia  (no paid employees)
                 4 = Unpaid worker (trabajador sin pago)
                 5 = Unspecified
  fac_tri    : Quarterly expansion factor (sampling weight; sum → population)
               May also appear as FAC or fac in some years.

Analysis Universe (applied before any tabulation)
=================================================
  Per INEGI, the precoded labor variables and fac_tri weight are valid only for:
    R_DEF == 0 (complete interview), C_RES in {1, 3} (usual resident),
    age (eda) 15–98.  These filters reproduce INEGI's published totals.

PSTS Sector Proxy
=================
  scian == 12  →  "Servicios profesionales, científicos y técnicos"
                  (exact equivalent of US NAICS 54).
  This is consistent across the old ENOE, ETOE, and ENOE N / current ENOE.

PSTS Self-Employed (SelfEmployedPSTS)
=====================================
  Sum of expansion-weighted individuals in the PSTS sector with
  pos_ocu ∈ {2 (employer / patrón), 3 (own-account / cuenta propia)} — i.e. the
  TOTAL self-employed in PSTS.  This matches the Canadian StatCan "Self-employed"
  class (which also spans both with-paid-help and own-account workers), enabling a
  like-for-like Canada–Mexico comparison.
  The employer vs own-account split is NOT exported: only the all-PSTS total is
  used in the analysis, so `SelfEmployedPSTS` denotes the TOTAL (not the
  own-account subset).
  Note: Unlike the US ABS/ASE which counts employer-owned *firms*, ENOE counts
  *persons* who own or operate a business — a different unit than the US series.

2020 Special Treatment
======================
  Q1 : Regular ENOE (standard methodology).
  Q2 : ETOE (Encuesta Telefónica de Ocupación y Empleo), phone-based COVID
       substitute.  Variable names differ slightly; scraper attempts adaptive
       mapping.  If no compatible SDEM is found, Q2 is skipped for 2020.
  Q3–Q4: ENOE N (Nueva Edición, new sample design).
  Annual 2020 figures are the mean of available quarters (min 1, max 4).

Output
======
  data/mexico/aggregatedData.csv   — long panel (1 row per State x Year x Sex),
                                     mirroring the Canadian StatCan layout
                                     (State, Year, Sex, LaborForce,
                                      UnemploymentRate, Employed, Unemployed,
                                      SelfEmployedPSTS)
  data/mexico/data_validation_report.md
  data/mexico/scraper.log
"""

import io
import logging
import os
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import requests

try:
    from dbfread import DBF as _DBF
    _HAS_DBFREAD = True
except ImportError:
    _HAS_DBFREAD = False
    _DBF = None

# ── Paths & logging ────────────────────────────────────────────────────────────

# Data lives in <repo-root>/data/mexico, while this scraper sits in
# <repo-root>/mexico. Resolve OUT_DIR relative to this file so the scraper writes
# to the same data folder no matter which working directory it is launched from.
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "mexico"
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

# ── State code → name mapping (INEGI entity codes 01–32) ──────────────────────

ENT_TO_STATE = {
    "01": "Aguascalientes",
    "02": "Baja California",
    "03": "Baja California Sur",
    "04": "Campeche",
    "05": "Coahuila de Zaragoza",
    "06": "Colima",
    "07": "Chiapas",
    "08": "Chihuahua",
    "09": "Ciudad de México",
    "10": "Durango",
    "11": "Guanajuato",
    "12": "Guerrero",
    "13": "Hidalgo",
    "14": "Jalisco",
    "15": "México",
    "16": "Michoacán de Ocampo",
    "17": "Morelos",
    "18": "Nayarit",
    "19": "Nuevo León",
    "20": "Oaxaca",
    "21": "Puebla",
    "22": "Querétaro",
    "23": "Quintana Roo",
    "24": "San Luis Potosí",
    "25": "Sinaloa",
    "26": "Sonora",
    "27": "Tabasco",
    "28": "Tamaulipas",
    "29": "Tlaxcala",
    "30": "Veracruz de Ignacio de la Llave",
    "31": "Yucatán",
    "32": "Zacatecas",
}

ALL_STATES = sorted(ENT_TO_STATE.values())
ALL_YEARS  = list(range(2014, 2025))   # 2014–2024

# ── URL builders ───────────────────────────────────────────────────────────────

BASE = "https://www.inegi.org.mx/contenidos/programas/enoe/15ymas/microdatos"
BASE_ETOE = "https://www.inegi.org.mx/contenidos/investigacion/etoe/microdatos"

# ETOE was released per-month; we average the three months to stand in for Q2.
ETOE_MONTHS = ["mayo", "junio", "agosto"]


def _enoe_url(year: int, quarter: int) -> str:
    """URL for old ENOE (2014 Q1 – 2020 Q1) CSV zip."""
    return f"{BASE}/{year}trim{quarter}_csv.zip"


def _enoe_n_url(year: int, quarter: int) -> str:
    """URL for ENOE N (2020 Q3 – 2022 Q4) CSV zip."""
    return f"{BASE}/enoe_n_{year}_trim{quarter}_csv.zip"


def _enoe_new_url(year: int, quarter: int) -> str:
    """URL for current ENOE (2023 Q1 – present) CSV zip.

    When ENOE N (Nueva Edición) ended after 2022, INEGI dropped the '_n' from
    the filename but kept the underscore-delimited format, e.g.
    enoe_2023_trim1_csv.zip — NOT the pre-2020 bare '2023trim1_csv.zip'.
    """
    return f"{BASE}/enoe_{year}_trim{quarter}_csv.zip"


def _etoe_url(month: str) -> str:
    """URL for ETOE 2020 CSV zip (month = 'mayo'/'junio'/'agosto')."""
    return f"{BASE_ETOE}/etoe_2020_{month}_csv.zip"


# ── Download & ZIP helpers ─────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (research scraper)"})


def _download_bytes(url: str, timeout: int = 300, retries: int = 3) -> bytes | None:
    """
    Download URL to bytes; return None if not found or if the response is too
    small to be a valid ZIP (< 512 bytes = redirect page / not-found stub).

    Retries on ANY transient network error (read/connect timeout, dropped
    connection, chunked-encoding error).  A "Read timed out" surfaces as a
    ConnectionError, not a Timeout, so we retry on the RequestException base
    class rather than Timeout alone.  The large 2023+ files (~40 MB) are the
    most timeout-prone, hence the generous default timeout.
    """
    for attempt in range(retries + 1):
        try:
            log.info("  GET %s", url)
            r = SESSION.get(url, timeout=timeout)
            if r.status_code == 404:
                log.info("    → 404 not found")
                return None
            r.raise_for_status()
            if len(r.content) < 512:
                log.info("    → %d bytes (too small, treating as not found)", len(r.content))
                return None
            log.info("    → %.1f MB", len(r.content) / 1e6)
            return r.content
        except requests.exceptions.RequestException as exc:
            # Transient: timeouts, dropped connections, incomplete reads.
            if attempt < retries:
                wait = 5 * (attempt + 1)   # linear backoff: 5s, 10s, 15s
                log.warning("    → %s (attempt %d/%d, retrying in %ds)",
                            exc, attempt + 1, retries + 1, wait)
                time.sleep(wait)
            else:
                log.warning("    → %s (failed after %d attempts)", exc, attempt + 1)
                return None
        except Exception as exc:
            log.warning("    → %s", exc)
            return None


def _find_csv_in_zip(zf: zipfile.ZipFile, prefix: str) -> pd.DataFrame | None:
    """
    Find the first CSV file whose base name starts with PREFIX (e.g. 'SDEM').
    Falls back to DBF if no CSV found and dbfread is available.
    """
    flat_names = {n.upper().split("/")[-1]: n for n in zf.namelist()}
    csv_candidates = [
        orig for upper, orig in flat_names.items()
        if prefix.upper() in upper and upper.endswith(".CSV")
    ]
    if csv_candidates:
        name = csv_candidates[0]
        log.info("    Reading CSV %s", name)
        raw = zf.read(name)
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                return pd.read_csv(io.BytesIO(raw), low_memory=False, encoding=enc)
            except UnicodeDecodeError:
                continue
            except Exception as exc:
                log.warning("    CSV read error for %s (%s): %s", name, enc, exc)
                break
        log.warning("    Could not decode %s with any encoding", name)

    # Fallback: try DBF
    return _find_dbf_in_zip(zf, prefix)


def _find_dbf_in_zip(zf: zipfile.ZipFile, prefix: str) -> pd.DataFrame | None:
    """Extract a DBF file from the ZIP to a temp file, read via dbfread."""
    if not _HAS_DBFREAD:
        log.warning("    dbfread not installed — cannot read DBF files")
        return None
    flat_names = {n.upper().split("/")[-1]: n for n in zf.namelist()}
    dbf_candidates = [
        orig for upper, orig in flat_names.items()
        if prefix.upper() in upper and upper.endswith(".DBF")
    ]
    if not dbf_candidates:
        log.warning("    No %s*.csv or *.dbf found in ZIP (files: %s)",
                    prefix, list(flat_names.keys())[:15])
        return None
    name = dbf_candidates[0]
    log.info("    Reading DBF %s", name)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".dbf")
    try:
        with os.fdopen(tmp_fd, "wb") as tmp_f:
            tmp_f.write(zf.read(name))
        table = _DBF(tmp_path, load=True, encoding="latin-1")
        return pd.DataFrame(iter(table))
    except Exception as exc:
        log.warning("    DBF read error for %s: %s", name, exc)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ── Column-name resolver (case-insensitive, tolerates ENOE/ETOE/ENOE-N diffs) ─

def _col(df: pd.DataFrame, *candidates: str) -> str | None:
    """Return the first candidate found as a column (case-insensitive)."""
    upper = {c.upper(): c for c in df.columns}
    for cand in candidates:
        if cand.upper() in upper:
            return upper[cand.upper()]
    return None


# ── Single-quarter processor ───────────────────────────────────────────────────

def _process_sdem(sdem: pd.DataFrame, label: str) -> pd.DataFrame | None:
    """
    Given an SDEM DataFrame, return a summary DataFrame with columns:
      ent, sex, n_labor_force, n_employed, n_unemployed,
      n_psts_workers, n_psts_employers, n_psts_self_employed
    All n_* are expansion-weighted population estimates (sum of fac_tri).
    Returns None if required columns are missing.
    """
    sdem = sdem.copy()   # avoid SettingWithCopyWarning on temp columns

    # ── Resolve column names ──────────────────────────────────────────────────
    c_ent    = _col(sdem, "ent", "ENT", "Ent")
    c_sex    = _col(sdem, "sex", "SEX", "Sex")
    c_cl1    = _col(sdem, "clase1", "CLASE1")
    c_cl2    = _col(sdem, "clase2", "CLASE2")
    c_fac    = _col(sdem, "fac_tri", "FAC_TRI", "fac", "FAC", "factor", "FACTOR")
    c_scian  = _col(sdem, "scian", "SCIAN")
    c_pos    = _col(sdem, "pos_ocu", "POS_OCU")
    # Universe-filter columns (INEGI: R_DEF=00, C_RES in {1,3}, age 15-98)
    c_rdef   = _col(sdem, "r_def", "R_DEF")
    c_cres   = _col(sdem, "c_res", "C_RES")
    c_eda    = _col(sdem, "eda", "EDA", "edad", "EDAD")

    required = {"ent": c_ent, "sex": c_sex, "clase1": c_cl1,
                "clase2": c_cl2, "fac": c_fac}
    missing = [k for k, v in required.items() if v is None]
    if missing:
        log.warning("  [%s] Missing required columns: %s  (available: %s)",
                    label, missing, list(sdem.columns)[:20])
        return None

    # ── Cast & clean ─────────────────────────────────────────────────────────
    for col in [c_ent, c_sex, c_cl1, c_cl2, c_fac]:
        sdem[col] = pd.to_numeric(sdem[col], errors="coerce")
    sdem = sdem.dropna(subset=[c_ent, c_sex, c_cl1, c_fac])

    # ── Apply INEGI analysis universe ─────────────────────────────────────────
    # The precoded labor variables (clase1/clase2/pos_ocu/scian) and the fac_tri
    # weight are only valid for: complete interviews (R_DEF=00), de-jure/usual
    # residents (C_RES in {1,3}), aged 15-98.  Filtering here matches INEGI's
    # own published totals.
    if c_rdef is not None:
        rdef_num = pd.to_numeric(sdem[c_rdef], errors="coerce")
        sdem = sdem[rdef_num == 0]
    if c_cres is not None:
        cres_num = pd.to_numeric(sdem[c_cres], errors="coerce")
        sdem = sdem[cres_num.isin([1, 3])]
    if c_eda is not None:
        eda_num = pd.to_numeric(sdem[c_eda], errors="coerce")
        sdem = sdem[(eda_num >= 15) & (eda_num <= 98)]

    # Normalise entity code to zero-padded 2-char string
    sdem["_ent"] = sdem[c_ent].astype(int).astype(str).str.zfill(2)
    sdem = sdem[sdem["_ent"].isin(ENT_TO_STATE)]

    # ── Labor force & employment ──────────────────────────────────────────────
    in_pea      = sdem[c_cl1] == 1
    is_employed = in_pea & (sdem[c_cl2] == 1)
    is_unemp    = in_pea & (sdem[c_cl2] == 2)

    # ── PSTS sector filter ────────────────────────────────────────────────────
    # ENOE/ENOE-N variable `scian` is a 21-category SCIAN sector grouping.
    # Code 12 = "Servicios profesionales, científicos y técnicos" — the exact
    # equivalent of US NAICS 54.  (Not rama_est2==8, which is the broader
    # professional+financial+real-estate+corporate+admin bundle, SCIAN 52-56.)
    if c_scian is not None:
        scian_num = pd.to_numeric(sdem[c_scian], errors="coerce")
        in_psts = (scian_num == 12)
        log.info("  [%s] scian==12 filter applied (SCIAN 54, exact PSTS)", label)
    else:
        in_psts = pd.Series(False, index=sdem.index)
        log.warning("  [%s] scian column not found; PSTS counts will be 0", label)

    # ── Employment position in PSTS ───────────────────────────────────────────
    if c_pos is not None:
        # pos_ocu: 2=Empleadores (employer), 3=Trabajadores por cuenta propia
        # (self-employed).  (1=subordinate paid, 4=unpaid, 5=unspecified.)
        pos_num = pd.to_numeric(sdem[c_pos], errors="coerce")
        is_employer = is_employed & in_psts & (pos_num == 2)
        is_self_emp = is_employed & in_psts & (pos_num == 3)
    else:
        is_employer = pd.Series(False, index=sdem.index)
        is_self_emp = pd.Series(False, index=sdem.index)
        log.warning("  [%s] pos_ocu not found; employer/self-emp counts = 0", label)

    # ── Group by state × sex and sum weights ──────────────────────────────────
    sdem["_sex"] = sdem[c_sex].astype(int)

    rows = []
    for ent in sdem["_ent"].unique():
        mask_ent = sdem["_ent"] == ent
        for sex_val in (1, 2):
            mask = mask_ent & (sdem["_sex"] == sex_val)
            w = sdem.loc[mask, c_fac]

            def wsum(condition):
                return float(sdem.loc[mask & condition, c_fac].sum())

            rows.append({
                "ent": ent,
                "sex": sex_val,
                # Labour force (PEA) = employed + open-unemployed (working OR
                # actively seeking).  NOT the working-age population (`w.sum()`,
                # which would also include the economically inactive).
                "n_labor_force":      wsum(is_employed | is_unemp),
                "n_employed":         wsum(is_employed),
                "n_unemployed":       wsum(is_unemp),
                "n_psts_workers":     wsum(is_employed & in_psts),
                "n_psts_employers":   wsum(is_employer),
                "n_psts_self_employed": wsum(is_self_emp),
            })

    return pd.DataFrame(rows)


# ── Quarter fetcher ────────────────────────────────────────────────────────────

def _fetch_quarter(year: int, quarter: int) -> pd.DataFrame | None:
    """
    Download and process one ENOE quarter.  Returns summary DataFrame or None.
    Tries old-ENOE URL first (2014-2020 Q1), then ENOE-N URL (2020 Q3+).
    """
    label = f"{year} Q{quarter}"

    # Determine which URL(s) to try.
    # ENOE N ran 2020 Q3 – 2022 Q4; from 2023 Q1 the survey returned to the
    # classic ENOE name and URL scheme (without the enoe_n_ prefix).
    if year < 2020 or (year == 2020 and quarter == 1):
        urls = [_enoe_url(year, quarter)]
    elif year == 2020 and quarter == 2:
        # ETOE: not a standard quarterly file — handled separately
        return None
    elif year == 2020 and quarter in (3, 4):
        urls = [_enoe_n_url(year, quarter), _enoe_url(year, quarter)]
    elif year in (2021, 2022):
        urls = [_enoe_n_url(year, quarter)]
    else:
        # 2023+ : ENOE N ended; survey uses enoe_{year}_trim{q} naming.
        # Try that first, then the pre-2020 bare and the enoe_n_ patterns as
        # fallbacks for robustness.
        urls = [
            _enoe_new_url(year, quarter),
            _enoe_url(year, quarter),
            _enoe_n_url(year, quarter),
        ]

    for url in urls:
        data = _download_bytes(url)
        if data is None:
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                sdem = _find_csv_in_zip(zf, "SDEM")
        except zipfile.BadZipFile:
            log.warning("  [%s] Bad ZIP at %s", label, url)
            continue
        if sdem is None:
            continue
        result = _process_sdem(sdem, label)
        if result is not None:
            return result

    log.warning("  [%s] No usable data found", label)
    return None


def _fetch_etoe_q2() -> pd.DataFrame | None:
    """
    Attempt to download ETOE 2020 month files and return an averaged summary
    to stand in for 2020 Q2.
    """
    monthly_frames = []
    for month in ETOE_MONTHS:
        # Try CSV first, then DBF (ETOE was released primarily as DBF with
        # a cpv2020 infix; CSV may not exist at all).
        urls_to_try = [
            _etoe_url(month),
            f"{BASE_ETOE}/etoe_2020_{month}_cpv2020_dbf.zip",
        ]
        sdem = None
        for url in urls_to_try:
            data = _download_bytes(url)
            if data is None:
                continue
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    sdem = _find_csv_in_zip(zf, "SDEM")
                    if sdem is None:
                        sdem = _find_csv_in_zip(zf, "ETOE")
            except zipfile.BadZipFile:
                log.warning("  [ETOE %s] Bad ZIP at %s", month, url)
                continue
            if sdem is not None:
                break   # found usable data, stop trying URLs

        if sdem is None:
            log.warning("  [ETOE %s] Not available from any URL", month)
            continue
        result = _process_sdem(sdem, f"ETOE 2020 {month}")
        if result is not None:
            monthly_frames.append(result)
        time.sleep(0.5)

    if not monthly_frames:
        return None

    # Average the monthly estimates (treating months as equal-weight sub-periods)
    combined = pd.concat(monthly_frames)
    avg = (combined
           .groupby(["ent", "sex"])
           [["n_labor_force", "n_employed", "n_unemployed",
             "n_psts_workers", "n_psts_employers", "n_psts_self_employed"]]
           .mean()
           .reset_index())
    return avg


# ── Annual aggregation ─────────────────────────────────────────────────────────

def build_panel() -> pd.DataFrame:
    quarterly_frames = []   # list of (year, quarter, df)

    for year in ALL_YEARS:
        log.info("=== Year %d ===", year)
        for quarter in (1, 2, 3, 4):
            log.info("  Fetching %d Q%d", year, quarter)

            if year == 2020 and quarter == 2:
                df = _fetch_etoe_q2()
                if df is not None:
                    quarterly_frames.append((year, quarter, df))
            else:
                df = _fetch_quarter(year, quarter)
                if df is not None:
                    quarterly_frames.append((year, quarter, df))
            time.sleep(0.5)

    if not quarterly_frames:
        raise RuntimeError("No quarterly data was retrieved — check network / URLs.")

    # ── Build annual averages ─────────────────────────────────────────────────
    # Tag each frame with its year and average across quarters within each year.
    tagged = []
    for year, _q, df in quarterly_frames:
        df = df.copy()
        df["year"] = year
        tagged.append(df)

    all_q = pd.concat(tagged, ignore_index=True)
    numeric_cols = ["n_labor_force", "n_employed", "n_unemployed",
                    "n_psts_workers", "n_psts_employers", "n_psts_self_employed"]
    annual = (all_q
              .groupby(["ent", "sex", "year"])[numeric_cols]
              .mean()
              .reset_index())

    # ── Pivot sex → separate male / female columns ────────────────────────────
    male   = annual[annual["sex"] == 1].copy().drop(columns="sex")
    female = annual[annual["sex"] == 2].copy().drop(columns="sex")

    rename_m = {c: f"male_{c[2:]}"   for c in numeric_cols}
    rename_f = {c: f"female_{c[2:]}" for c in numeric_cols}
    male   = male.rename(columns=rename_m)
    female = female.rename(columns=rename_f)

    merged = male.merge(female, on=["ent", "year"], how="outer")

    # ── Map entity code → state name ──────────────────────────────────────────
    merged["state"] = merged["ent"].map(ENT_TO_STATE)
    merged = merged.dropna(subset=["state"])

    # ── PSTS self-employed (TOTAL) = employers (patrón) + own-account (cuenta propia)
    # This total is the measure used in the analysis ("all PSTS") and matches the
    # Canadian StatCan "Self-employed" class, which likewise includes both
    # self-employed-with-paid-help and own-account workers.  The employer /
    # own-account split is computed here only to form the total; it is NOT exported
    # (we test only the all-PSTS total).  `*_psts_self_employed` in the output
    # therefore denotes the TOTAL self-employed in PSTS — NOT the own-account subset.
    merged["male_psts_self_employed_total"]   = (
        merged["male_psts_employers"] + merged["male_psts_self_employed"])
    merged["female_psts_self_employed_total"] = (
        merged["female_psts_employers"] + merged["female_psts_self_employed"])

    # ── Build full skeleton (state × year) and merge ──────────────────────────
    skeleton = pd.DataFrame(
        [(s, y) for s in ALL_STATES for y in ALL_YEARS],
        columns=["state", "year"],
    )
    panel = skeleton.merge(merged, on=["state", "year"], how="left")

    final_cols = [
        "state", "year",
        "male_employed", "female_employed",
        "male_unemployed", "female_unemployed",
        "male_labor_force", "female_labor_force",
        # PSTS self-employed = TOTAL (employers + own-account); see note above.
        # The employer/own-account breakdown is intentionally not exported.
        "male_psts_self_employed_total", "female_psts_self_employed_total",
    ]
    for c in final_cols:
        if c not in panel.columns:
            panel[c] = np.nan

    out_panel = (
        panel[final_cols].sort_values(["state", "year"]).reset_index(drop=True)
        .rename(columns={
            "male_psts_self_employed_total":   "male_psts_self_employed",
            "female_psts_self_employed_total": "female_psts_self_employed",
        })
    )
    return (
        out_panel,
        sorted((y, q) for y, q, _ in quarterly_frames),
    )


def to_long(panel: pd.DataFrame) -> pd.DataFrame:
    """Reshape the internal wide panel into the long (one row per State-Year-Sex)
    layout that mirrors the Canadian StatCan reference dataset.

    Conventions matched to the Canadian reference data:
      - one row per State x Year x Sex, Sex in {"Male", "Female"};
      - counts (LaborForce, Employed, Unemployed, SelfEmployedPSTS) as raw
        ENOE-expanded persons;
      - UnemploymentRate as a percentage rounded to the nearest tenth, derived
        as 100 x Unemployed / LaborForce (ENOE does not publish a state x sex
        annual rate directly at this aggregation — see validation report).
    SelfEmployedPSTS is the TOTAL self-employed PERSONS in PSTS (employers +
    own-account), matching the Canadian StatCan "Self-employed" class.
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
            "SelfEmployedPSTS": panel[f"{p}_psts_self_employed"],
        }))

    long = pd.concat(frames, ignore_index=True)
    long["Sex"] = pd.Categorical(long["Sex"], categories=["Male", "Female"], ordered=True)
    return long.sort_values(["State", "Year", "Sex"]).reset_index(drop=True)

# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("Starting Mexico state-year panel build (2014–2024)")
    panel, processed_quarters = build_panel()
    long = to_long(panel)

    out = OUT_DIR / "aggregatedData.csv"
    long.to_csv(out, index=False)
    log.info("Saved %d rows → %s", len(long), out)

    log.info("Done.")
