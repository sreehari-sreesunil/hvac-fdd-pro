"""End-to-end test: fetch real telemetry from telemetry-service, assemble a
live buffer, and run inference via ml/src/models/inference.py.

Run with: python test_ml_pipeline.py
"""

import json
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent / "ml"))
from src.models.inference import predict  # noqa: E402

TELEMETRY_URL = "http://localhost:8002/telemetry"
TOKEN = "PASTE_YOUR_CURRENT_TOKEN_HERE"
ASSET_ID = "a5d67b00-4500-4692-9a0e-d1bdf79e89ce"

METRICS = {
    "RTU_REFG_COND_PRES": "d20d5482-933c-4788-b053-d3cc9b2c8d1b",
    "RTU_REFG_COND_TEMP": "1ee2f9ca-3ba3-45b5-b0fa-7b07e90c9f93",
    "RTU_TOT_CAPA": "ebdc37a7-079c-4d22-8dc3-3e512178a7cb",
    "RTU_STG_STA": "e369c652-c666-4abf-86a0-f1178332f3e8",
    "RTU_OA_TEMP": "fb2d57ef-8328-42c5-bf3c-65283e09bb16",
}


def fetch_metric(metric_name: str, metric_id: str) -> pd.DataFrame:
    url = f"{TELEMETRY_URL}?asset_id={ASSET_ID}&metric_definition_id={metric_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read())
    df = pd.DataFrame(data)[["recorded_at", "value"]].rename(columns={"value": metric_name})
    df["recorded_at"] = pd.to_datetime(df["recorded_at"])
    return df.sort_values("recorded_at")


print("Fetching all 5 metrics from telemetry-service...")
dfs = [fetch_metric(name, mid) for name, mid in METRICS.items()]

buffer = dfs[0]
for df in dfs[1:]:
    buffer = buffer.merge(df, on="recorded_at", how="inner")

buffer = (
    buffer.rename(columns={"recorded_at": "Datetime"})
    .sort_values("Datetime")
    .reset_index(drop=True)
)
print(f"Assembled buffer shape: {buffer.shape}")
print(buffer.head())
print(buffer.tail())

result = predict("simulated_condenser_fouling", buffer, Path("ml/models"))
print("\n=== Prediction result ===")
print(f"predicted_label: {result['predicted_label']}")
print(f"fault_probability: {result['fault_probability']:.3f}")
print(f"confidence: {result['confidence']}")
print(f"status: {result['status']}")
