"""CZ M2 updater — merges three sources into CZ_m2_money_supply.csv.

Sources (highest priority last, wins on dedup):
  1. Existing CSV (FRED history 1991-2001, kept as-is for pre-2002 data)
  2. data/CZ_ARAD_SMV5M106.csv  — CNB/ARAD static export 2002-2026 (bootstrap)
  3. Live CNB URL               — rolling 13-month window, for ongoing updates

ARAD and CNB live both report in millions of CZK; values are multiplied
by 1_000_000 to match the raw-CZK unit convention used by the FRED data.
"""
import logging
import re
import time
from pathlib import Path

import pandas as pd
import requests

import job_logger

CNB_URL = (
    "https://www.cnb.cz/export/sites/cnb/en/statistics/money_and_banking_stat"
    "/national_stat_data/download/mp_en.txt"
)
ARAD_PATH   = Path(__file__).parent / "data" / "CZ_ARAD_SMV5M106.csv"
OUTPUT_PATH = Path("output/CZ_m2_money_supply.csv")
SERIES_ID_CNB = "CNB_M2"
COUNTRY_CODE  = "CZ"
M2_LABEL      = "(1.7) m2"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_eu_number(s: str) -> float:
    """'7.261.008,9' or '6854868,0' → float (European thousands/decimal separators)."""
    return float(s.strip().replace(".", "").replace(",", "."))


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>|&nbsp;", "", s).strip()


def load_existing() -> pd.DataFrame | None:
    if OUTPUT_PATH.exists():
        df = pd.read_csv(OUTPUT_PATH, parse_dates=["date"])
        logger.info("Loaded %d existing rows (up to %s).", len(df), df["date"].max().date())
        return df
    return None


def load_arad() -> pd.DataFrame | None:
    """Parse the ARAD semicolon-delimited file (2002-01 → present, millions CZK)."""
    if not ARAD_PATH.exists():
        logger.info("ARAD file not found at %s — skipping.", ARAD_PATH)
        return None
    rows = []
    with ARAD_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("Period"):
                continue
            parts = line.rstrip(";").split(";")
            if len(parts) < 2:
                continue
            date_str, val_str = parts[0], parts[1]
            if not val_str:
                continue
            try:
                date = pd.Timestamp(date_str).replace(day=1)
                value = _parse_eu_number(val_str) * 1_000_000
                rows.append({
                    "date": date,
                    "country_code": COUNTRY_CODE,
                    "series_id": SERIES_ID_CNB,
                    "value": value,
                })
            except (ValueError, TypeError):
                continue
    if not rows:
        return None
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    logger.info("Parsed %d rows from ARAD (up to %s).", len(df), df["date"].max().date())
    return df


def fetch_cnb_live() -> pd.DataFrame:
    """Fetch rolling 13-month window from CNB (millions CZK) → standard-schema DataFrame.

    The file is delivered as a single line with no newline separators.
    Header dates are at the start; rows are separated by their label tokens.
    """
    resp = requests.get(CNB_URL, timeout=30)
    resp.raise_for_status()
    content = resp.text

    # Header: leading pipe-separated YYYY/MM dates before the first HTML tag
    header_end = content.find("<")
    if header_end == -1:
        raise ValueError("Unexpected CNB response format (no HTML tags found)")
    header_part = content[:header_end]
    dates = [t.strip() for t in header_part.split("|") if t.strip() and "/" in t]
    if not dates:
        raise ValueError("No date columns found in CNB header")

    # M2 row (1.7): extract the pipe-delimited values that follow the label
    m2_match = re.search(
        r"\(1\.7\)[^|]*\|([^(]+)",
        _strip_html(content),
        re.IGNORECASE,
    )
    if not m2_match:
        raise ValueError("Could not find M2 (1.7) row in CNB response")

    raw_values = [v.strip() for v in m2_match.group(1).split("|")]

    rows = []
    for date_str, val_str in zip(dates, raw_values):
        val_str = val_str.strip()
        if not val_str or val_str == "-":
            continue
        try:
            year, month = date_str.split("/")
            rows.append({
                "date": pd.Timestamp(f"{year}-{month}-01"),
                "country_code": COUNTRY_CODE,
                "series_id": SERIES_ID_CNB,
                "value": _parse_eu_number(val_str) * 1_000_000,
            })
        except (ValueError, TypeError):
            continue

    if not rows:
        raise ValueError("No M2 data parsed from CNB live response")

    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    logger.info("Fetched %d rows from CNB live (latest: %s).", len(df), df["date"].max().date())
    return df


def main() -> None:
    start = time.time()
    try:
        frames = []

        existing = load_existing()
        if existing is not None:
            frames.append(existing)

        arad = load_arad()
        if arad is not None:
            frames.append(arad)

        cnb = fetch_cnb_live()
        frames.append(cnb)

        # Frames are appended in priority order: FRED, ARAD, CNB live.
        # Stable sort on date preserves concat order for equal dates (FRED first, CNB last),
        # so keep="last" retains CNB live > ARAD > FRED for any overlapping date.
        combined = (
            pd.concat(frames)
            .sort_values("date", kind="stable")
            .drop_duplicates(subset=["date"], keep="last")
            .reset_index(drop=True)
        )

        rows_before = len(existing) if existing is not None else 0
        rows_added  = len(combined) - rows_before

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(OUTPUT_PATH, index=False, date_format="%Y-%m-%d")
        latest_date = combined["date"].max().strftime("%Y-%m-%d")
        logger.info(
            "Saved %d rows to %s (+%d new). Latest: %s.",
            len(combined), OUTPUT_PATH, rows_added, latest_date,
        )
        job_logger.log(COUNTRY_CODE, "success", rows_added, latest_date, time.time() - start)

    except Exception as exc:
        job_logger.log(COUNTRY_CODE, "error", 0, None, time.time() - start, str(exc))
        raise


if __name__ == "__main__":
    main()
