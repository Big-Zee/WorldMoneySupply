"""M2 Money Supply fetcher via FRED API (series M2SL)."""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
SERIES_ID = "M2SL"
DEFAULT_OUTPUT_DIR = "output"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_m2_data(api_key: str) -> list[dict]:
    """Fetch M2 observations from FRED API. Returns list of observation dicts."""
    params = {
        "series_id": SERIES_ID,
        "api_key": api_key,
        "file_type": "json",
    }
    response = requests.get(FRED_API_URL, params=params, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"FRED API returned HTTP {response.status_code}: {response.text[:200]}"
        )
    return response.json()["observations"]


def build_dataframe(observations: list[dict]) -> pd.DataFrame:
    """Convert FRED observations to a clean DataFrame."""
    df = pd.DataFrame(observations)[["date", "value"]]
    df = df[df["value"] != "."].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)
    df = df.rename(columns={"value": "m2_billions_usd"})
    df = df.sort_values("date").reset_index(drop=True)
    return df


def save_csv(df: pd.DataFrame, output_dir: str) -> Path:
    """Write DataFrame to CSV and return the output path."""
    out_path = Path(output_dir) / "m2_money_supply.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, date_format="%Y-%m-%d")
    logger.info("Saved %d rows to %s", len(df), out_path)
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch M2 money supply data from FRED.")
    parser.add_argument("--api-key", help="FRED API key (overrides FRED_API_KEY env var)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    args = parser.parse_args()

    load_dotenv()

    api_key = args.api_key or os.environ.get("FRED_API_KEY")
    if not api_key:
        logger.error(
            "No FRED API key found. Provide one via:\n"
            "  --api-key YOUR_KEY\n"
            "  FRED_API_KEY env var\n"
            "  .env file with FRED_API_KEY=your_key\n"
            "Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html"
        )
        sys.exit(1)

    try:
        logger.info("Fetching M2 data from FRED (series: %s)...", SERIES_ID)
        observations = fetch_m2_data(api_key)
        logger.info("Retrieved %d raw observations", len(observations))

        df = build_dataframe(observations)
        logger.info("Built DataFrame with %d valid rows (date range: %s to %s)",
                    len(df), df["date"].min().date(), df["date"].max().date())

        save_csv(df, args.output_dir)
    except Exception as exc:
        logger.error("Failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
