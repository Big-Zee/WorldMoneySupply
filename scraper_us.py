"""Standalone US M2 money supply fetcher (FRED M2SL series).

Auto-detects incremental vs full fetch:
- If output/US_m2_money_supply.csv exists: fetches from last known date onwards and merges.
- If no CSV found: full historical fetch.

Designed to run as an Azure Function or standalone script.
"""
import logging
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

import job_logger

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "M2SL"
COUNTRY_CODE = "US"
OUTPUT_PATH = Path("output/US_m2_money_supply.csv")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_observations(api_key: str, observation_start: str | None = None) -> list[dict]:
    """Fetch M2SL observations from FRED. Pass observation_start (YYYY-MM-DD) for incremental."""
    params = {"series_id": SERIES_ID, "api_key": api_key, "file_type": "json"}
    if observation_start:
        params["observation_start"] = observation_start
    response = requests.get(FRED_API_URL, params=params, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"FRED API returned HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json()["observations"]


def build_dataframe(observations: list[dict]) -> pd.DataFrame:
    """Convert FRED observations to the standard per-country CSV schema."""
    df = pd.DataFrame(observations)[["date", "value"]]
    df = df[df["value"] != "."].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)
    df["country_code"] = COUNTRY_CODE
    df["series_id"] = SERIES_ID
    return df[["date", "country_code", "series_id", "value"]].sort_values("date").reset_index(drop=True)


def load_existing() -> pd.DataFrame | None:
    """Return existing CSV as DataFrame, or None if it doesn't exist."""
    if OUTPUT_PATH.exists():
        return pd.read_csv(OUTPUT_PATH, parse_dates=["date"])
    return None


def main() -> None:
    load_dotenv()
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        logger.error(
            "No FRED API key found. Set FRED_API_KEY env var or add it to .env file.\n"
            "Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        sys.exit(1)

    start = time.time()
    try:
        existing = load_existing()
        observation_start = None
        if existing is not None:
            last_date = existing["date"].max()
            observation_start = last_date.strftime("%Y-%m-%d")
            logger.info("Existing data found (%d rows). Incremental fetch from %s.", len(existing), observation_start)
        else:
            logger.info("No existing data found. Performing full fetch.")

        observations = fetch_observations(api_key, observation_start)
        if not observations:
            logger.info("No new observations returned by FRED.")
            latest_date = existing["date"].max().strftime("%Y-%m-%d") if existing is not None else None
            job_logger.log("US", "success", 0, latest_date, time.time() - start)
            return

        new_df = build_dataframe(observations)
        logger.info("Fetched %d new observations (latest: %s).", len(new_df), new_df["date"].max().date())

        if existing is not None:
            combined = (
                pd.concat([existing, new_df])
                .drop_duplicates(subset=["date"])
                .sort_values("date")
                .reset_index(drop=True)
            )
            rows_added = len(combined) - len(existing)
        else:
            combined = new_df
            rows_added = len(combined)

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(OUTPUT_PATH, index=False, date_format="%Y-%m-%d")
        latest_date = combined["date"].max().strftime("%Y-%m-%d")
        logger.info("Saved %d rows to %s (latest: %s).", len(combined), OUTPUT_PATH, latest_date)
        job_logger.log("US", "success", rows_added, latest_date, time.time() - start)

    except Exception as exc:
        job_logger.log("US", "error", 0, None, time.time() - start, str(exc))
        raise


if __name__ == "__main__":
    main()
