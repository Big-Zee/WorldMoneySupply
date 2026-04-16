import requests
import pandas as pd
from pathlib import Path

# Fetch metadata for MD02 (Money Stock) to see available series
url = "https://www.stat-search.boj.or.jp/api/v1/getMetadata"
params = {
    "format": "json",
    "lang":   "en",
    "db":     "MD02",
}

resp = requests.get(url, params=params)
resp.raise_for_status()
data = resp.json()

# Print series names and codes to find the M2 ones you need
for series in data["RESULTSET"]:
    print(f"{series['SERIES_CODE']:30} {series['NAME_OF_TIME_SERIES']}")

# Save all metadata to CSV
df = pd.DataFrame(data["RESULTSET"])
out_dir = Path("output")
out_dir.mkdir(parents=True, exist_ok=True)
out_path = out_dir / "boj_md02_series.csv"
df.to_csv(out_path, index=False)
print(f"\nSaved {len(df)} series to {out_path}")