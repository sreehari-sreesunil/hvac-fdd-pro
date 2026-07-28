"""One-off script: ingest a chunk of real fault data into telemetry-service,
for end-to-end ml-service testing.

Each call should use a growing TIME_OFFSET_DAYS so timestamps never
collide with a previous model's test data (all Simulated-dataset fault
files share the identical underlying 2018 timestamps).

START_ROW matters: GET /telemetry only returns the most recent 500 rows
per metric, so START_ROW + NUM_ROWS - 500 to START_ROW + NUM_ROWS is the
actual window the live pipeline will see. Pick a START_ROW confirmed (via
a direct check of the raw CSV) to contain real stage-2 compressor
operation in that trailing window - otherwise the model will correctly,
honestly refuse to score (no fault of the pipeline, just an unlucky
data window for testing).

Run with: python ingest_test_data.py
"""

import csv
import json
import urllib.request
from datetime import datetime, timedelta

INGESTION_URL = "http://localhost:8002/telemetry/bulk"
API_KEY = "PASTE_YOUR_INGESTION_KEY_HERE"
ASSET_ID = "PASTE_YOUR_ASSET_ID_HERE"
CSV_PATH = "ml/data/raw/RTU_sim_evapfouling40.csv"
TIME_OFFSET_DAYS = 4000  # deliberately larger than the current max (2027-12-07) so this becomes the newest ingestion across ALL required metrics, unifying the overlap window
START_ROW = 40000
NUM_ROWS = 2000  # wider window than usual - no way to pre-verify stage-2 presence without the raw CSV, so cast a wider net

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

readings = []
with open(CSV_PATH) as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < START_ROW:
            continue
        if i >= START_ROW + NUM_ROWS:
            break
        original_dt = datetime.strptime(row["Datetime"], "%Y-%m-%d %H:%M:%S")
        shifted_dt = original_dt + timedelta(days=TIME_OFFSET_DAYS)
        recorded_at = shifted_dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
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

print(
    f"Prepared {len(readings)} readings from rows {START_ROW}-{START_ROW+NUM_ROWS} x {len(COLUMNS_TO_INGEST)} columns"
)
print(f"Shifted by {TIME_OFFSET_DAYS} days")

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
