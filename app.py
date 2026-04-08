"""FastAPI web server for Global M2 money supply visualization."""
from pathlib import Path
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "output" / "m2_global.csv"
CSV_PATH_FALLBACK = BASE_DIR / "output" / "m2_money_supply.csv"

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
    if CSV_PATH.exists():
        df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    elif CSV_PATH_FALLBACK.exists():
        # Backward compat: wrap legacy US-only CSV in the new schema
        df = pd.read_csv(CSV_PATH_FALLBACK, parse_dates=["date"])
        df = df.rename(columns={"m2_billions_usd": "value"})
        df["country_code"] = "US"
        df["series_id"] = "M2SL"
    else:
        return JSONResponse(content={"error": "No data file found. Run scraper.py first."}, status_code=404)

    df = df.sort_values(["country_code", "date"])
    df["yoy_pct"] = df.groupby("country_code")["value"].pct_change(12) * 100
    df = df.dropna(subset=["yoy_pct"])

    countries = []
    for code, group in df.groupby("country_code"):
        series_id = group["series_id"].iloc[0] if "series_id" in group.columns else code
        data = list(zip(
            group["date"].dt.strftime("%Y-%m-%d").tolist(),
            group["yoy_pct"].round(2).tolist(),
        ))
        countries.append({
            "code": code,
            "name": COUNTRY_NAMES.get(code, code),
            "series_id": series_id,
            "data": data,
        })

    return JSONResponse(content={"mode": "yoy_pct_change", "countries": countries})
