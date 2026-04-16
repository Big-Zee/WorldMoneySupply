import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = "https://www.stat-search.boj.or.jp/api/v1/getDataCode"

# Replace with actual series codes found in BOJDiscoverSeries output
# Example codes for M2 (monthly, seasonally adjusted / original)
M2_CODES = [
    "MAM1NAM2M2MO",  # M2 outstanding (example — verify from metadata)
]

params = {
    "format":    "json",
    "lang":      "en",
    "db":        "MD02",
    "code":      ",".join(M2_CODES),  # comma-separated, same frequency only
    "startDate": "197001",            # earliest available BOJ MD02 data
    "endDate":   datetime.now().strftime("%Y%m"),
}

resp = requests.get(BASE, params=params, headers={"Accept-Encoding": "gzip"})
resp.raise_for_status()
result = resp.json()

if result["STATUS"] != 200:
    raise ValueError(f"API error {result['STATUS']}: {result['MESSAGE']}")

rows = []
for series in result["RESULTSET"]:
    series_id = series["SERIES_CODE"]
    dates     = series["VALUES"]["SURVEY_DATES"]
    values    = series["VALUES"]["VALUES"]
    print(f"\n{series['NAME_OF_TIME_SERIES']}")
    for d, v in zip(dates, values):
        print(f"  {d}: {v}")
        if v not in ("-", "", None):
            rows.append({"date": d, "series_id": series_id, "value": float(v)})

df = pd.DataFrame(rows)
df["date"]         = pd.to_datetime(df["date"], format="%Y%m")
df["country_code"] = "JP"
df["value"]        = df["value"].astype(float)
df = df[["date", "country_code", "series_id", "value"]].sort_values("date").reset_index(drop=True)

out_dir = Path("output")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "JP_m2_money_supply.csv"
df.to_csv(out_path, index=False, date_format="%Y-%m-%d")
print(f"\nSaved {len(df)} rows to {out_path}")
