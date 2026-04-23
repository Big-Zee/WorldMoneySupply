# WorldMoneySupply

Fetches broad M2 money supply data for **11 countries** and visualizes them as
**year-over-year % change** on a single interactive chart. Most countries are
sourced from the [FRED API](https://fred.stlouisfed.org/); Euro Area data comes
directly from the [ECB REST API](https://data-api.ecb.europa.eu/) (no API key required);
Japan data comes directly from the [Bank of Japan API](https://www.stat-search.boj.or.jp/) (no API key required).

## Countries

| Code | Name           | Source | Series ID                              | Script                  |
|------|----------------|--------|----------------------------------------|-------------------------|
| US   | United States  | FRED   | M2SL                                   | scraper.py              |
| EZ   | Euro Area      | ECB    | BSI.M.U2.Y.V.M20.X.1.U2.2300.Z01.E    | scraper.py              |
| JP   | Japan          | BOJ    | MAM1NAM2M2MO                           | BOJDownloadSeries.py    |
| GB   | United Kingdom | FRED   | MABMM301GBM189S                        | scraper.py              |
| CA   | Canada         | FRED   | MABMM301CAM189S                        | scraper.py              |
| AU   | Australia      | FRED   | MABMM301AUM189S                        | scraper.py              |
| KR   | South Korea    | FRED   | MABMM301KRM189S                        | scraper.py              |
| ZA   | South Africa   | FRED   | MABMM301ZAM189S                        | scraper.py              |
| NO   | Norway         | FRED   | MABMM301NOM189S                        | scraper.py              |
| CZ   | Czech Republic | FRED   | MABMM301CZM189S                        | scraper.py              |
| HU   | Hungary        | FRED   | MABMM301HUM189S                        | scraper.py              |

## API Key Setup

1. Get a free key at: <https://fred.stlouisfed.org/docs/api/api_key.html>
2. Supply it in one of three ways:
   - **`.env` file** (recommended): create `.env` in this directory with `FRED_API_KEY=your_key_here`
   - **Environment variable**: `export FRED_API_KEY=your_key_here`
   - **CLI flag**: `python scraper.py --api-key your_key_here`

## Install

```bash
pip install -r requirements.txt
```

## Run

### All countries except Japan

```bash
python scraper.py
```

Each country is written to its own file: `output/{CODE}_m2_money_supply.csv`
(e.g. `US_m2_money_supply.csv`, `EZ_m2_money_supply.csv`). A combined
`output/m2_global.csv` is also written as a convenience artifact.

Partial runs are safe — fetching `--countries EZ` only touches `EZ_m2_money_supply.csv`
and `m2_global.csv`; all other per-country files are left intact.

Optional flags:

```
--api-key KEY        FRED API key (overrides env var / .env)
--output-dir DIR     Directory to write CSV (default: output)
--countries US,EZ    Fetch only the specified country codes (default: all except JP)
```

### Japan (BOJ)

Japan is fetched separately from the Bank of Japan API (no API key required):

```bash
python BOJDownloadSeries.py
```

Writes to `output/JP_m2_money_supply.csv` in the same schema as all other country files.

Use `BOJDiscoverSeries.py` to browse available BOJ MD02 series and update the
`M2_CODES` list in `BOJDownloadSeries.py` if the series code needs to change:

```bash
python BOJDiscoverSeries.py          # prints + saves output/boj_md02_series.csv
```

## Verify

```bash
python -c "
import pandas as pd, glob
files = sorted(glob.glob('output/*_m2_money_supply.csv'))
print('Per-country files:', [f.split('/')[-1] for f in files])
df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
print(df.info())
print('Countries:', sorted(df['country_code'].unique()))
print(df.groupby('country_code')['date'].agg(['min','max','count']))
"
```

Expected: 11 per-country files, 8 000+ rows total, dates from ~1959 onward (JP from ~1970).

## Web UI

An interactive chart is available via the FastAPI server:

```bash
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` — features:
- 11 colored lines showing YoY % change per country
- Per-country toggle checkboxes + Select All / Deselect All
- Scroll-wheel zoom, range slider, double-click to reset zoom
- Tooltip showing all country values for a given date

## Architecture

### Local / development

```
Data Sources                Scripts                  Output
────────────────────────    ─────────────────────    ──────────────────────────────
FRED API (US, GB, CA…)  ──► scraper.py        ──┐
ECB  API (EZ)           ──► scraper.py        ──┤► output/{CODE}_m2_money_supply.csv
BOJ  API (JP)           ──► BOJDownloadSeries ──┤► output/m2_global.csv (combined)
FRED API (US only)      ──► scraper_us.py     ──┘► output/job_status.json (audit log)
                                                            │
                                                            ▼
                                                     app.py (FastAPI)
                                                     ├── GET /api/data
                                                     └── GET /api/scraper-status
                                                            │
                                                            ▼
                                                  templates/index.html
                                                  (ECharts dashboard)
```

`scraper_us.py` is a self-contained incremental fetcher: if `output/US_m2_money_supply.csv`
exists it fetches only from the last known date onward; otherwise it performs a full
historical fetch. Every scraper run appends a result entry to `job_status.json` which
the dashboard health panel reads via `/api/scraper-status`.

### Azure (planned)

```
Resource Group: m2-supply-monitor
│
├── Storage Account: m2supplystorage
│   ├── Blob container: m2-data/
│   │   ├── US_m2_money_supply.csv
│   │   ├── JP_m2_money_supply.csv
│   │   └── …
│   └── Table: ScraperJobStatus
│       (PartitionKey=scraper, RowKey=timestamp, status, rows_added, …)
│
├── Function App: m2-supply-monitor-func    (Consumption plan — free tier)
│   ├── scraper_us   Timer Trigger  (monthly)
│   ├── scraper_all  Timer Trigger  (monthly)
│   ├── scraper_jp   Timer Trigger  (monthly)
│   ├── api_data     HTTP  Trigger  GET /api/data
│   └── api_status   HTTP  Trigger  GET /api/scraper-status
│
└── Static Web App: m2-supply-monitor-web   (Free tier)
    └── index.html + ECharts  →  calls Function App HTTP endpoints
```

GitHub Actions deploys on push to `main` using a Service Principal scoped to this
Resource Group — GitHub identity and Azure identity remain independent.
When `AZURE_STORAGE_CONNECTION_STRING` is set, `job_logger.py` writes audit entries
to Table Storage in addition to the local `job_status.json`.
