"""One-off script: ingest Experimental-dataset fault data into
telemetry-service, for end-to-end ml-service testing.

Different from ingest_test_data.py: Experimental files have a different
schema (OCCU_MOD, RTU_OA_DMPR_DM, etc.), real 2020-2022 dates (not the
Simulated dataset's 2018 sim-clock), and a documented "NAN" sentinel
string for missing sensor readings during unoccupied hours - skip rows
where a required column's value is literally "NAN" rather than trying to
convert it, matching the na_values=["NAN"] treatment established in the
EDA (ml/notebooks/07-10).

Run with: python ingest_experimental_test_data.py
"""

import csv
import json
import urllib.request
from datetime import datetime, timedelta

INGESTION_URL = "http://localhost:8002/telemetry/bulk"
API_KEY = "PASTE_YOUR_INGESTION_KEY_HERE"
ASSET_ID = "PASTE_YOUR_ASSET_ID_HERE"
CSV_PATH = "ml/data/raw/experimental/Inc_Eco_SP_-4_Winter_2022.csv"
TIME_OFFSET_DAYS = 2100  # push well clear of both the Simulated dataset's
# 2018 dates and their shifted variants used so far

COLUMNS_TO_INGEST = ["RTU_OA_DMPR_DM", "RTU_OA_TEMP", "OCCU_MOD"]

readings = []
skipped_nan = 0
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for row in reader:
        if row.get("OCCU_MOD") not in ("1", "1.0"):
            continue

        if any(row.get(col) == "NAN" for col in COLUMNS_TO_INGEST):
            skipped_nan += 1
            continue

        original_dt = datetime.strptime(row["Datetime"], "%Y-%m-%d %H:%M:%S")
        shifted_dt = original_dt + timedelta(days=TIME_OFFSET_DAYS)
        recorded_at = shifted_dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
        for col in COLUMNS_TO_INGEST:
            readings.append(
                {
                    "asset_id": ASSET_ID,
                    "external_key": col,
                    "value": float(row[col]),
                    "recorded_at": recorded_at,
                }
            )

print(
    f"Prepared {len(readings)} readings ({len(COLUMNS_TO_INGEST)} columns), skipped {skipped_nan} NAN rows"
)

payload = json.dumps({"readings": readings}).encode("utf-8")
req = urllib.request.Request(
    INGESTION_URL,
    data=payload,
    method="POST",
    headers={"Content-Type": "application/json", "X-Ingestion-Key": API_KEY},
)

with urllib.request.urlopen(req) as response:
    result = json.loads(response.read())
    print(result)
