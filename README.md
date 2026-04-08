# WorldMoneySupply

Fetches broad M2 money supply data for **11 countries** from the
[FRED API](https://fred.stlouisfed.org/) and visualizes them as
**year-over-year % change** on a single interactive chart.

## Countries

| Code | Name           | FRED Series ID         |
|------|----------------|------------------------|
| US   | United States  | M2SL                   |
| EZ   | Euro Area      | MABMM301EZM189S        |
| JP   | Japan          | MABMM301JPM189S        |
| GB   | United Kingdom | MABMM301GBM189S        |
| CA   | Canada         | MABMM301CAM189S        |
| AU   | Australia      | MABMM301AUM189S        |
| KR   | South Korea    | MABMM301KRM189S        |
| ZA   | South Africa   | MABMM301ZAM189S        |
| NO   | Norway         | MABMM301NOM189S        |
| CZ   | Czech Republic | MABMM301CZM189S        |
| HU   | Hungary        | MABMM301HUM189S        |

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

Output is written to `output/m2_global.csv` (all 11 countries, ~8 000+ rows).
`output/m2_money_supply.csv` (US-only) is also kept for backward compatibility.

Optional flags:

```
--api-key KEY          FRED API key (overrides env var / .env)
--output-dir DIR       Directory to write CSV (default: output)
--countries US,EZ,JP   Fetch only the specified country codes (default: all 11)
```

## Verify

```bash
python -c "
import pandas as pd
df = pd.read_csv('output/m2_global.csv')
print(df.info())
print('Countries:', sorted(df['country_code'].unique()))
print(df.groupby('country_code')['date'].agg(['min','max','count']))
"
```

Expected: 8 000+ rows, 11 unique `country_code` values, dates from ~1959 onward.

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
