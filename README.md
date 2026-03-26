# WorldMoneySupply

Fetches the M2 money supply historical series (USA, monthly, billions USD) from the
[FRED API](https://fred.stlouisfed.org/series/M2SL) and writes it to a CSV file.

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

Output is written to `output/m2_money_supply.csv`.

Optional flags:

```
--api-key KEY       FRED API key (overrides env var / .env)
--output-dir DIR    Directory to write CSV (default: output)
```

## Verify

```bash
python -c "import pandas as pd; df=pd.read_csv('output/m2_money_supply.csv'); print(df.info()); print(df.tail(3))"
```

Expected: 780+ rows, dates from ~1959-01-01 to within ~60 days of today, values in the thousands (billions USD), no NaNs.

## Web UI

An interactive chart is available via the FastAPI server:

```bash
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` — features scroll-wheel zoom, range slider, series toggle, and reset zoom.
