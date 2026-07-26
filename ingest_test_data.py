"""One-off script: ingest a chunk of real fault data into telemetry-service,
for end-to-end ml-service testing.

Run with: python ingest_test_data.py
"""

import csv
import json
import urllib.request

INGESTION_URL = "http://localhost:8002/telemetry/bulk"
API_KEY = "PASTE_YOUR_INGESTION_KEY_HERE"
ASSET_ID = "PASTE_YOUR_ASSET_ID_HERE"
CSV_PATH = "ml/data/raw/RTU_sim_suctionpipe09bar.csv"

COLUMNS_TO_INGEST = [
    "RTU_REFG_SUCT_PRES",
    "RTU_REFG_SUCT_TEMP",
    "RTU_REFG_DISC_PRES",
    "RTU_REFG_COND_PRES",
    "RTU_REFG_COND_TEMP",
    "RTU_SA_TEMP",
    "RTU_TOT_CAPA",
    "RTU_STG_STA",
    "RTU_OA_TEMP",
]
NUM_ROWS = 1200

readings = []
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i >= NUM_ROWS:
            break
        recorded_at = row["Datetime"].replace(" ", "T") + "Z"
        for col in COLUMNS_TO_INGEST:
            if col in row:
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
