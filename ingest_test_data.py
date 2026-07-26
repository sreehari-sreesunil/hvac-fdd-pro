"""One-off script: ingest a chunk of real condfouling50.csv data into
telemetry-service, for end-to-end ml-service testing.

Run with: python ingest_test_data.py
"""

import csv
import json
import urllib.request

INGESTION_URL = "http://localhost:8002/telemetry/bulk"
API_KEY = "PASTE_YOUR_INGESTION_KEY_HERE"
ASSET_ID = "a5d67b00-4500-4692-9a0e-d1bdf79e89ce"
CSV_PATH = "ml/data/raw/RTU_sim_condfouling50.csv"

COLUMNS_TO_INGEST = [
    "RTU_REFG_COND_PRES",
    "RTU_REFG_COND_TEMP",
    "RTU_TOT_CAPA",
    "RTU_STG_STA",
    "RTU_OA_TEMP",
]
NUM_ROWS = 1200  # enough history for segmented EWMA to warm up, per earlier live-feature testing

readings = []
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= NUM_ROWS:
            break
        # original timestamps are 2018 - fine for a historical test buffer, no conversion needed
        recorded_at = row["Datetime"].replace(" ", "T") + "Z"
        for col in COLUMNS_TO_INGEST:
            readings.append(
                {
                    "asset_id": ASSET_ID,
                    "external_key": col,
                    "value": float(row[col]),
                    "recorded_at": recorded_at,
                }
            )

print(f"Prepared {len(readings)} readings from {NUM_ROWS} rows x {len(COLUMNS_TO_INGEST)} columns")

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
