"""FastAPI web server for M2 money supply visualization."""
from pathlib import Path
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

BASE_DIR = Path(__file__).parent
CSV_PATH = BASE_DIR / "output" / "m2_money_supply.csv"

app = FastAPI(title="M2 Money Supply Monitor")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/data")
async def get_data():
    df = pd.read_csv(CSV_PATH)
    records = list(zip(df["date"].tolist(), df["m2_billions_usd"].round(1).tolist()))
    return JSONResponse(content={"series": "M2SL", "unit": "billions_usd", "data": records})
