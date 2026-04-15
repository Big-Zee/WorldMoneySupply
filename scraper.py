"""M2 Money Supply fetcher — multi-country.

FRED is used for most countries. Euro Area (EZ) is sourced directly from the
ECB public REST API (no API key required), which is updated monthly and current
through early 2026.
"""
import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
ECB_API_URL = "https://data-api.ecb.europa.eu/service/data"

# Countries fetched from ECB instead of FRED (no API key required)
ECB_OVERRIDES = {
    "EZ": {
        "series_key": "BSI/M.U2.Y.V.M20.X.1.U2.2300.Z01.E",
        "series_id":  "BSI.M.U2.Y.V.M20.X.1.U2.2300.Z01.E",
        "unit_multiplier": 1 / 1000,  # ECB reports millions of EUR; convert to billions
    },
}

DEFAULT_OUTPUT_DIR = "output"

COUNTRIES = {
    "US": {"name": "United States",  "series_id": "M2SL"},
    "EZ": {"name": "Euro Area",       "series_id": "MABMM301EZM189S"},
    "JP": {"name": "Japan",           "series_id": "MABMM301JPM189S"},
    "GB": {"name": "United Kingdom",  "series_id": "MABMM301GBM189S"},
    "CA": {"name": "Canada",          "series_id": "MABMM301CAM189S"},
    "AU": {"name": "Australia",       "series_id": "MABMM301AUM189S"},
    "KR": {"name": "South Korea",     "series_id": "MABMM301KRM189S"},
    "ZA": {"name": "South Africa",    "series_id": "MABMM301ZAM189S"},
    "NO": {"name": "Norway",          "series_id": "MABMM301NOM189S"},
    "CZ": {"name": "Czech Republic",  "series_id": "MABMM301CZM189S"},
    "HU": {"name": "Hungary",         "series_id": "MABMM301HUM189S"},
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_series(api_key: str, series_id: str) -> list[dict]:
    """Fetch observations for a FRED series. Returns list of observation dicts."""
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
    }
    response = requests.get(FRED_API_URL, params=params, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"FRED API returned HTTP {response.status_code} for {series_id}: {response.text[:200]}"
        )
    return response.json()["observations"]


def build_dataframe(observations: list[dict], country_code: str, series_id: str) -> pd.DataFrame:
    """Convert FRED observations to a clean DataFrame with country/series columns."""
    df = pd.DataFrame(observations)[["date", "value"]]
    df = df[df["value"] != "."].copy()
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)
    df["country_code"] = country_code
    df["series_id"] = series_id
    df = df[["date", "country_code", "series_id", "value"]]
    df = df.sort_values("date").reset_index(drop=True)
    return df


def fetch_ecb_series(
    series_key: str, country_code: str, series_id: str, unit_multiplier: float = 1.0
) -> pd.DataFrame:
    """Fetch observations from ECB SDMX REST API. Returns same schema as build_dataframe()."""
    from io import StringIO
    url = f"{ECB_API_URL}/{series_key}"
    response = requests.get(url, params={"format": "csvdata", "detail": "dataonly"}, timeout=30)
    if response.status_code != 200:
        raise RuntimeError(
            f"ECB API returned HTTP {response.status_code} for {series_key}: {response.text[:200]}"
        )
    df = pd.read_csv(StringIO(response.text))
    df = df[["TIME_PERIOD", "OBS_VALUE"]].rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "value"})
    df = df.dropna(subset=["value"])
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float) * unit_multiplier
    df["country_code"] = country_code
    df["series_id"] = series_id
    return df[["date", "country_code", "series_id", "value"]].sort_values("date").reset_index(drop=True)


def save_csv(df: pd.DataFrame, output_dir: str) -> None:
    """Write one CSV per country and a combined m2_global.csv."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for code, group in df.groupby("country_code"):
        path = out_dir / f"{code}_m2_money_supply.csv"
        group.to_csv(path, index=False, date_format="%Y-%m-%d")
        logger.info("Saved %d rows to %s", len(group), path)

    global_path = out_dir / "m2_global.csv"
    df.to_csv(global_path, index=False, date_format="%Y-%m-%d")
    logger.info("Saved %d rows (combined) to %s", len(df), global_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch M2 money supply data from FRED.")
    parser.add_argument("--api-key", help="FRED API key (overrides FRED_API_KEY env var)")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "--countries",
        help="Comma-separated country codes to fetch (default: all). E.g. US,EZ,JP",
    )
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

    if args.countries:
        requested = [c.strip().upper() for c in args.countries.split(",")]
        unknown = [c for c in requested if c not in COUNTRIES]
        if unknown:
            logger.error("Unknown country codes: %s. Valid codes: %s", unknown, list(COUNTRIES))
            sys.exit(1)
        selected = {c: COUNTRIES[c] for c in requested}
    else:
        selected = COUNTRIES

    frames: list[pd.DataFrame] = []
    for code, meta in selected.items():
        try:
            if code in ECB_OVERRIDES:
                ecb = ECB_OVERRIDES[code]
                logger.info("Fetching %s (%s) from ECB...", meta["name"], code)
                df = fetch_ecb_series(
                    ecb["series_key"], code, ecb["series_id"], ecb["unit_multiplier"]
                )
            else:
                series_id = meta["series_id"]
                logger.info("Fetching %s (%s, series: %s)...", meta["name"], code, series_id)
                observations = fetch_series(api_key, series_id)
                df = build_dataframe(observations, code, series_id)
            logger.info(
                "  %s: %d rows, %s to %s",
                code, len(df), df["date"].min().date(), df["date"].max().date(),
            )
            frames.append(df)
        except Exception as exc:
            logger.error("Failed to fetch %s: %s", code, exc)

    if not frames:
        logger.error("No data fetched. Exiting.")
        sys.exit(1)

    combined = pd.concat(frames, ignore_index=True)
    save_csv(combined, args.output_dir)


if __name__ == "__main__":
    main()
