# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch M2 data for all countries except Japan (requires FRED API key)
python scraper.py

# Fetch M2 data for specific countries
python scraper.py --countries US,EZ,GB

# Fetch Japan M2 data from Bank of Japan (no API key required)
python BOJDownloadSeries.py

# Discover available BOJ series (saves output/boj_md02_series.csv)
python BOJDiscoverSeries.py

# Start the web UI
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

## FRED API Key

Required for `scraper.py`. Supply via `.env` file (`FRED_API_KEY=your_key`), environment variable, or `--api-key` flag. Not needed for BOJ scripts or `app.py`.

## Architecture

The project has two data collection paths that both write to `output/`:

**FRED/ECB path (`scraper.py`)** — fetches 10 countries. Euro Area (EZ) is overridden to use the ECB REST API instead of FRED (see `ECB_OVERRIDES` dict). All other countries use FRED. Output: `output/{CODE}_m2_money_supply.csv` per country + `output/m2_global.csv` (combined).

**BOJ path (`BOJDownloadSeries.py`)** — fetches Japan only from the Bank of Japan MD02 database. Writes `output/JP_m2_money_supply.csv` in the same schema. `BOJDiscoverSeries.py` is a helper to browse available series and find the right series code.

**CSV schema** (all files): `date, country_code, series_id, value` — dates as `YYYY-MM-01`, values as float in native currency units.

**Web UI (`app.py`)** — FastAPI server that reads `output/*_m2_money_supply.csv` at request time (no caching). `load_data()` globs all per-country files; falls back to `m2_global.csv` then a legacy US-only file. `/api/data` computes YoY % change via `pct_change(12)` on monthly data and returns both raw values and YoY series per country. The chart is rendered client-side by ECharts in `templates/index.html`.

**Adding a new country** — add an entry to `COUNTRIES` in `scraper.py` with its FRED series ID. If the source is not FRED, add an override in `ECB_OVERRIDES` (or create a dedicated script like `BOJDownloadSeries.py`) and add the country code to `COUNTRY_NAMES` in `app.py`.
