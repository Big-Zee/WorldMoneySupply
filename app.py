"""FastAPI web server for Global M2 money supply visualization."""
import json
from pathlib import Path
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "output" / "m2_global.csv"
CSV_PATH_FALLBACK = BASE_DIR / "output" / "m2_money_supply.csv"
OUTPUT_DIR = BASE_DIR / "output"


def load_data() -> pd.DataFrame | None:
    """Load all per-country CSVs; fall back to m2_global.csv or legacy US-only file."""
    per_country = sorted(OUTPUT_DIR.glob("*_m2_money_supply.csv"))
    if per_country:
        return pd.concat(
            [pd.read_csv(p, parse_dates=["date"]) for p in per_country],
            ignore_index=True,
        )
    if CSV_PATH.exists():
        return pd.read_csv(CSV_PATH, parse_dates=["date"])
    if CSV_PATH_FALLBACK.exists():
        df = pd.read_csv(CSV_PATH_FALLBACK, parse_dates=["date"])
        df = df.rename(columns={"m2_billions_usd": "value"})
        df["country_code"] = "US"
        df["series_id"] = "M2SL"
        return df
    return None

COUNTRY_NAMES = {
    "US": "United States",
    "EZ": "Euro Area",
    "JP": "Japan",
    "GB": "United Kingdom",
    "CA": "Canada",
    "AU": "Australia",
    "KR": "South Korea",
    "ZA": "South Africa",
    "NO": "Norway",
    "CZ": "Czech Republic",
    "HU": "Hungary",
}

app = FastAPI(title="Global M2 Monitor")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/data")
async def get_data():
    raw_df = load_data()
    if raw_df is None:
        return JSONResponse(
            content={"error": "No data file found. Run scraper.py first."}, status_code=404
        )

    raw_df = raw_df.sort_values(["country_code", "date"])
    df = raw_df.copy()
    df["yoy_pct"] = df.groupby("country_code")["value"].pct_change(12) * 100
    df = df.dropna(subset=["yoy_pct"])

    countries = []
    for code, group in df.groupby("country_code"):
        series_id = group["series_id"].iloc[0] if "series_id" in group.columns else code
        data = list(zip(
            group["date"].dt.strftime("%Y-%m-%d").tolist(),
            group["yoy_pct"].round(2).tolist(),
        ))
        raw_grp = raw_df[raw_df["country_code"] == code].dropna(subset=["value"])
        raw_data = [
            [row["date"].strftime("%Y-%m-%d"), round(float(row["value"]), 2)]
            for _, row in raw_grp[["date", "value"]].iterrows()
        ]
        countries.append({
            "code": code,
            "name": COUNTRY_NAMES.get(code, code),
            "series_id": series_id,
            "data": data,
            "raw": raw_data,
        })

    return JSONResponse(content={"mode": "yoy_pct_change", "countries": countries})


@app.get("/api/scraper-status")
async def scraper_status():
    path = BASE_DIR / "output" / "job_status.json"
    if not path.exists():
        return JSONResponse(content={"scrapers": []})
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return JSONResponse(content={"scrapers": []})
    seen: set[str] = set()
    latest: list[dict] = []
    for entry in reversed(entries):
        if entry["scraper"] not in seen:
            seen.add(entry["scraper"])
            latest.append(entry)
    return JSONResponse(content={"scrapers": latest})
