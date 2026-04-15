# WorldMoneySupply

Fetches broad M2 money supply data for **11 countries** and visualizes them as
**year-over-year % change** on a single interactive chart. Most countries are
sourced from the [FRED API](https://fred.stlouisfed.org/); Euro Area data comes
directly from the [ECB REST API](https://data-api.ecb.europa.eu/) (no API key required).

## Countries

| Code | Name           | Source | Series ID                              |
|------|----------------|--------|----------------------------------------|
| US   | United States  | FRED   | M2SL                                   |
| EZ   | Euro Area      | ECB    | BSI.M.U2.Y.V.M20.X.1.U2.2300.Z01.E    |
| JP   | Japan          | FRED   | MABMM301JPM189S                        |
| GB   | United Kingdom | FRED   | MABMM301GBM189S                        |
| CA   | Canada         | FRED   | MABMM301CAM189S                        |
| AU   | Australia      | FRED   | MABMM301AUM189S                        |
| KR   | South Korea    | FRED   | MABMM301KRM189S                        |
| ZA   | South Africa   | FRED   | MABMM301ZAM189S                        |
| NO   | Norway         | FRED   | MABMM301NOM189S                        |
| CZ   | Czech Republic | FRED   | MABMM301CZM189S                        |
| HU   | Hungary        | FRED   | MABMM301HUM189S                        |

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
--api-key KEY          FRED API key (overrides env var / .env)
--output-dir DIR       Directory to write CSV (default: output)
--countries US,EZ,JP   Fetch only the specified country codes (default: all 11)
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

Expected: 11 per-country files, 8 000+ rows total, dates from ~1959 onward.

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
