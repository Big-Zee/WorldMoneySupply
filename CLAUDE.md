# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git Operations

The git repository root is `WorldMoneySupply/`. Always run git commands from there (this directory).

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

# Fetch CZ M2 data from Czech National Bank (FRED stopped Nov 2023)
python cnb_cz.py

# Build CN M2 CSV from FRED history + manual PBOC data (re-run after adding rows to data/CN_m2_money_supply_from2019-09.csv)
python fred_cn.py

# Discover available BOJ series (saves output/boj_md02_series.csv)
python BOJDiscoverSeries.py

# Start the web UI
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

## FRED API Key

Required for `scraper.py`. Supply via `.env` file (`FRED_API_KEY=your_key`), environment variable, or `--api-key` flag. Not needed for BOJ scripts or `app.py`.

## Architecture

Three data collection paths all write to `output/`:

**FRED/ECB path (`scraper.py`)** — fetches 9 countries (US, EZ, GB, CA, AU, KR, ZA, NO, HU). Euro Area (EZ) is overridden to use the ECB REST API instead of FRED (see `ECB_OVERRIDES` dict). All others use FRED. Output: `output/{CODE}_m2_money_supply.csv` per country + `output/m2_global.csv` (combined).

**BOJ path (`BOJDownloadSeries.py`)** — fetches Japan only from the Bank of Japan MD02 database. Writes `output/JP_m2_money_supply.csv` in the same schema. `BOJDiscoverSeries.py` is a helper to browse available series.

**CNB path (`cnb_cz.py`)** — fetches Czech Republic from the Czech National Bank. FRED stopped publishing CZ after 2023-11. The script merges three sources in priority order: existing CSV (FRED history pre-2002) → `data/CZ_ARAD_SMV5M106.csv` (CNB/ARAD static export 2002-2026) → live CNB rolling feed (latest 13 months). CNB values are in millions of CZK and are multiplied by 1,000,000 to match the raw-CZK convention used by FRED data.

**CN path (`fred_cn.py`)** — builds the China M2 CSV from two sources merged by priority: FRED series `MYAGM2CNM189N` (history through 2019-08; FRED stopped updating after that) and `data/CN_m2_money_supply_from2019-09.csv` (manually collected PBOC data from 2019-09 onwards; 2026 data from https://www.pbc.gov.cn/diaochatongjisi/attachDir/2026/07/2026071515594282024.htm). Manual data wins on any overlapping dates. Re-run whenever new months are appended to the manual file.

**CSV schema** (all files): `date, country_code, series_id, value` — dates as `YYYY-MM-01`, values as float in native currency units.

**Web UI (`app.py`)** — FastAPI server that reads `output/*_m2_money_supply.csv` at request time (no caching). `load_data()` globs all per-country files; falls back to `m2_global.csv` then a legacy US-only file. `/api/data` computes YoY % change via `pct_change(12)` on monthly data and returns both raw values and YoY series per country. The chart is rendered client-side by ECharts in `templates/index.html`.

**Adding a new country** — if FRED has the series: add an entry to `COUNTRIES` in `scraper.py` and the country code to `COUNTRY_NAMES` in `app.py`. If the source is not FRED, create a dedicated script (see `BOJDownloadSeries.py` or `cnb_cz.py` as patterns) and add to `COUNTRY_NAMES` in `app.py`.

## Changelog

Always update `CHANGELOG.md` before committing any code change.

- New entries go at the **top** of the file, under `## [Unreleased]`
- Use subsections: `### Added`, `### Changed`, `### Fixed`, `### Removed`
- One bullet per logical change, plain English (no implementation detail or file paths)
- When a version is released/tagged, rename `[Unreleased]` to the release date `[YYYY-MM-DD]` and add a fresh `## [Unreleased]` above it
