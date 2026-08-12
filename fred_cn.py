"""China M2 fetcher: FRED history (through 2019-08) + manual PBOC supplement.

FRED series MYAGM2CNM189N stopped being updated after 2019-08.
Data from 2019-09 onwards is manually collected from the People's Bank of China
and stored in data/CN_m2_money_supply_from2019-09.csv.
  - 2026 data sourced from:
    https://www.pbc.gov.cn/diaochatongjisi/attachDir/2026/07/2026071515594282024.htm

Both sources are merged into output/CN_m2_money_supply.csv; manual data wins
on any overlapping dates. Re-run whenever new months are appended to the manual file.
"""
import argparse
import logging
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

import job_logger

FRED_API_URL  = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID     = "MYAGM2CNM189N"
COUNTRY_CODE  = "CN"
MANUAL_SERIES = "PBOC_M2"
OUTPUT_DIR    = Path("output")
MANUAL_CSV    = Path("data/CN_m2_money_supply_from2019-09.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_fred(api_key: str) -> pd.DataFrame:
    params = {"series_id": SERIES_ID, "api_key": api_key, "file_type": "json"}
    r = requests.get(FRED_API_URL, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"FRED returned HTTP {r.status_code}: {r.text[:200]}")
    obs = r.json()["observations"]
    df = pd.DataFrame(obs)[["date", "value"]]
    df = df[df["value"] != "."].copy()
    df["date"]         = pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp()
    df["value"]        = df["value"].astype(float)
    df["country_code"] = COUNTRY_CODE
    df["series_id"]    = SERIES_ID
    return df[["date", "country_code", "series_id", "value"]]


def load_manual() -> pd.DataFrame:
    df = pd.read_csv(MANUAL_CSV, parse_dates=["date"])
    df["date"]         = df["date"].dt.to_period("M").dt.to_timestamp()
    df["series_id"]    = MANUAL_SERIES
    df["country_code"] = COUNTRY_CODE
    return df[["date", "country_code", "series_id", "value"]]


def merge(fred: pd.DataFrame, manual: pd.DataFrame) -> pd.DataFrame:
    """Concatenate FRED (lower priority) then manual (higher priority).
    On duplicate dates, manual data wins via keep='last'."""
    combined = pd.concat([fred, manual], ignore_index=True)
    combined = combined.sort_values("date")
    combined = combined.drop_duplicates(subset="date", keep="last")
    return combined.reset_index(drop=True)


def save_csv(df: pd.DataFrame) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    out = OUTPUT_DIR / "CN_m2_money_supply.csv"
    df.to_csv(out, index=False, date_format="%Y-%m-%d")
    return out


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Build CN M2 CSV from FRED + manual PBOC data.")
    parser.add_argument("--api-key", default=os.getenv("FRED_API_KEY"))
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("FRED API key required (--api-key flag or FRED_API_KEY env var)")

    t0 = time.time()
    try:
        fred   = fetch_fred(args.api_key)
        manual = load_manual()
        df     = merge(fred, manual)
        path   = save_csv(df)
        logger.info(
            "Wrote %d rows to %s (FRED: %d, manual: %d, latest: %s)",
            len(df), path, len(fred), len(manual),
            df["date"].max().strftime("%Y-%m-%d"),
        )
        job_logger.log(
            scraper="CN",
            status="success",
            rows_added=len(df),
            latest_date=df["date"].max().strftime("%Y-%m-%d"),
            duration_seconds=round(time.time() - t0, 1),
        )
    except Exception as exc:
        logger.error("Failed: %s", exc)
        job_logger.log(
            scraper="CN",
            status="error",
            rows_added=0,
            latest_date=None,
            duration_seconds=round(time.time() - t0, 1),
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    main()
