"""Anomaly-detector comparison harness (Isolation Forest vs. One-Class SVM
vs. Local Outlier Factor).

Per external review feedback: "develop a POC for anomaly detection and
evaluate suitable models" - the current Isolation Forest was never
compared against alternatives.

Evaluation methodology is deliberately DIFFERENT from
compare_algorithms.py's classifier comparison, because anomaly detectors
are unsupervised - trained ONLY on baseline (unfaulted) data, never shown
a labeled fault example during training:

- Trained on baseline data only, using the exact same feature set as the
  currently shipped Isolation Forest (ISOLATION_FOREST_CONFIG).
- Every grid config is evaluated and reported - none is auto-selected.
  For a single-threshold anomaly detector, FPR and detection rate move in
  the SAME direction as contamination/nu changes, so a selection rule
  based on FPR alone has a trivial optimum (always the smallest grid
  value) and provides no real signal - it would just reproduce the exact
  contamination=0.01 detection-collapse problem this project already
  found and fixed once for the shipped Isolation Forest. The actual
  choice is a deliberate human call, same as the original 0.01->0.03
  retuning was.
- Detection rate is reported PER INDIVIDUAL FAULT FILE, never as one
  blended average - MODEL_ACCEPTANCE_CRITERIA.md explicitly requires this.
- Undercharge is excluded from the fault sweep, matching the existing
  Isolation Forest's own deliberate scope decision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from sklearn.ensemble import IsolationForest  # noqa: E402
from sklearn.neighbors import LocalOutlierFactor  # noqa: E402
from sklearn.svm import OneClassSVM  # noqa: E402

from src.features.build_features import build_feature_table  # noqa: E402
from src.models.model_registry import ISOLATION_FOREST_CONFIG, SIMULATED_FAULTS  # noqa: E402

FEATURE_COLS = [f"{col}_residual" for col in ISOLATION_FOREST_CONFIG["feature_cols"]]
FEATURE_COLS.append("RTU_TOT_CAPA_ewma30_segmented_residual")

HELD_OUT_FRACTION = 0.2  # last 20% of baseline (by time) held out for FPR testing
FPR_USABLE_CEILING = 0.05  # per MODEL_ACCEPTANCE_CRITERIA.md
FPR_CAVEAT_CEILING = 0.10  # per MODEL_ACCEPTANCE_CRITERIA.md


def _resolve_path(relative_path: str) -> str:
    return str(ML_ROOT / relative_path)


def _build_candidates() -> dict:
    return {
        "isolation_forest": {
            "build": lambda p: IsolationForest(random_state=42, n_estimators=100, **p),
            "grid": [{"contamination": c} for c in (0.01, 0.02, 0.03, 0.05)],
        },
        "one_class_svm": {
            "build": lambda p: OneClassSVM(kernel="rbf", **p),
            "grid": [{"nu": n} for n in (0.01, 0.03, 0.05)],
        },
        "local_outlier_factor": {
            "build": lambda p: LocalOutlierFactor(novelty=True, **p),
            "grid": [
                {"contamination": c, "n_neighbors": k} for c in (0.01, 0.03, 0.05) for k in (20, 35)
            ],
        },
    }


def load_baseline_and_faults():
    """Same all-faults file set the currently shipped Isolation Forest
    trains alongside (undercharge deliberately excluded, matching that
    existing scope decision)."""
    all_fault_paths: dict[str, str] = {}
    for config in SIMULATED_FAULTS.values():
        all_fault_paths.update(config.fault_paths)

    table, _ = build_feature_table(
        baseline_path=_resolve_path("data/raw/RTU_sim_baseline.csv"),
        fault_paths={label: _resolve_path(path) for label, path in all_fault_paths.items()},
        pressure_temp_cols=ISOLATION_FOREST_CONFIG["feature_cols"],
        return_weather_models=True,
    )
    return table


def _tier(fpr: float) -> str:
    if fpr <= FPR_USABLE_CEILING:
        return "Usable"
    if fpr <= FPR_CAVEAT_CEILING:
        return "Usable with caveat"
    return "Not production-usable"


def run_comparison() -> dict:
    """Evaluates EVERY grid config per algorithm - does NOT auto-select a
    "best" one. See module docstring for why.
    """
    table = load_baseline_and_faults()
    baseline = table[table["label"] == 0].reset_index(drop=True)
    faults = table[table["label"] == 1].reset_index(drop=True)

    split_idx = int(len(baseline) * (1 - HELD_OUT_FRACTION))
    train_baseline = baseline.iloc[:split_idx]
    held_out_baseline = baseline.iloc[split_idx:]

    print(f"Baseline: {len(train_baseline)} train rows, {len(held_out_baseline)} held-out rows")
    print(f"Fault rows across full sweep: {len(faults)}, {faults['source_file'].nunique()} files")

    results: dict = {}
    for algo_name, algo_config in _build_candidates().items():
        configs_evaluated = []
        for params in algo_config["grid"]:
            model = algo_config["build"](params)
            model.fit(train_baseline[FEATURE_COLS])
            preds = model.predict(held_out_baseline[FEATURE_COLS])
            fpr = float((preds == -1).mean())

            detection_by_file = {}
            for file_label, group in faults.groupby("source_file"):
                fault_preds = model.predict(group[FEATURE_COLS])
                detection_by_file[file_label] = {
                    "n_rows": len(group),
                    "detection_rate": float((fault_preds == -1).mean()),
                }

            configs_evaluated.append(
                {
                    "params": params,
                    "held_out_baseline_fpr": fpr,
                    "fpr_tier": _tier(fpr),
                    "detection_by_file": detection_by_file,
                }
            )
            print(f"{algo_name} {params}: FPR {fpr:.4f} ({_tier(fpr)})")

        results[algo_name] = {"configs": configs_evaluated}

    return results


def print_summary(results: dict) -> None:
    sample_files = [
        "suctionpipe09bar",
        "evapfouling50",
        "liquidpipe10bar",
        "evapfouling30",
        "condfouling30",
        "overcharge15",
    ]
    for algo_name, res in results.items():
        print("\n=== " + algo_name + " ===")
        for cfg in res["configs"]:
            params = cfg["params"]
            fpr = cfg["held_out_baseline_fpr"]
            tier = cfg["fpr_tier"]
            print("\n  " + str(params) + ": FPR " + format(fpr, ".4f") + " (" + tier + ")")
            for file_label in sample_files:
                d = cfg["detection_by_file"].get(file_label)
                if d:
                    rate = d["detection_rate"]
                    print("    " + file_label.ljust(20) + " detection=" + format(rate, ".3f"))


if __name__ == "__main__":
    results = run_comparison()
    output_path = ML_ROOT / "MODEL_COMPARISON_ANOMALY_RESULTS.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print("\nSaved to " + str(output_path))
    print_summary(results)
