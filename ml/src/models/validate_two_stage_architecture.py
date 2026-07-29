"""Validates the two-stage architecture (gatekeeper -> classifier) against
running all classifiers directly, per external review feedback: "validate
a two-stage architecture" and "compare the proposed architecture with a
direct classification approach."

This has never been tested. Every classifier has only ever been evaluated
in isolation (its own fault vs. baseline) - never as part of a system
running alongside the other four. Two real questions this answers that
no prior evaluation has:

1. COMPOUNDING FALSE POSITIVES: even if each classifier individually has
   a low false-positive rate, running 5 independent classifiers together
   means the chance that AT LEAST ONE fires on genuinely normal data can
   compound (a classic multiple-comparisons problem). Does gating with
   the anomaly-detection gatekeeper first reduce this system-level false
   alarm rate?

2. GATING RISK: the gatekeeper isn't perfect either. If it fails to flag
   a genuine but weak-signal fault, the two-stage approach would
   incorrectly suppress a classifier that would have fired correctly on
   its own. Does this actually happen, and how often?

A third, secondary diagnostic: cross-fault misfires - does e.g.
condenser_fouling's classifier ever fire on evaporator_fouling data it
was never trained to recognize?

Efficiency note: builds ONE shared feature table (the union of every
classifier's required residual columns, computed in a single pass over
all 21 fault files + baseline), rather than one pass per classifier -
avoids 6x redundant CSV reads and guarantees every classifier scores the
exact same rows in the exact same order, eliminating any alignment risk.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib

ML_ROOT = Path(__file__).resolve().parents[2]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from src.features.build_features import build_feature_table  # noqa: E402
from src.models.model_registry import ANOMALY_GATEKEEPER_CONFIG, SIMULATED_FAULTS  # noqa: E402

MODELS_DIR = ML_ROOT / "models"


def _resolve_path(relative_path: str) -> str:
    return str(ML_ROOT / relative_path)


def _all_fault_paths() -> dict[str, str]:
    all_paths: dict[str, str] = {}
    for config in SIMULATED_FAULTS.values():
        all_paths.update(config.fault_paths)
    return all_paths


def build_shared_table():
    """One pass over all 21 fault files + baseline, residualizing the
    UNION of every classifier's required pressure/temp columns plus the
    gatekeeper's."""
    union_cols: list[str] = []
    for config in SIMULATED_FAULTS.values():
        for col in config.pressure_temp_cols:
            if col not in union_cols:
                union_cols.append(col)
    for col in ANOMALY_GATEKEEPER_CONFIG["feature_cols"]:
        if col not in union_cols:
            union_cols.append(col)

    print(f"Building shared table with residualized columns: {union_cols}")
    table = build_feature_table(
        baseline_path=_resolve_path("data/raw/RTU_sim_baseline.csv"),
        fault_paths={label: _resolve_path(path) for label, path in _all_fault_paths().items()},
        pressure_temp_cols=tuple(union_cols),
    )
    print(
        f"Shared table: {len(table)} rows, {table['source_file'].nunique()} fault files + baseline"
    )
    return table


def score_all_models(table) -> dict:
    """Score every classifier and the gatekeeper against the SAME shared
    table - each just selects its own required residual columns."""
    scores: dict[str, dict] = {}

    for fault_name, config in SIMULATED_FAULTS.items():
        model_name = f"simulated_{fault_name}"
        model = joblib.load(MODELS_DIR / f"{model_name}.joblib")
        residual_cols = [f"{col}_residual" for col in config.pressure_temp_cols]
        if config.include_capacity:
            residual_cols.append("RTU_TOT_CAPA_ewma30_segmented_residual")
        X = table[residual_cols]
        scores[fault_name] = {
            "predicted": model.predict(X),
            "probability": model.predict_proba(X)[:, 1],
        }
        print(f"Scored classifier: {fault_name}")

    gatekeeper = joblib.load(MODELS_DIR / "simulated_anomaly_gatekeeper.joblib")
    gk_cols = [f"{col}_residual" for col in ANOMALY_GATEKEEPER_CONFIG["feature_cols"]]
    gk_cols.append("RTU_TOT_CAPA_ewma30_segmented_residual")
    gk_preds = gatekeeper.predict(table[gk_cols])
    scores["_gatekeeper"] = {"is_anomaly": gk_preds == -1}
    print("Scored gatekeeper")

    return scores


def analyze(table, scores: dict) -> dict:
    source_files = table["source_file"].reset_index(drop=True)
    is_baseline = (source_files == "baseline").to_numpy()
    is_anomaly = scores["_gatekeeper"]["is_anomaly"]

    classifier_names = [k for k in scores if k != "_gatekeeper"]
    any_classifier_fires_direct = None
    for name in classifier_names:
        fires = scores[name]["predicted"] == 1
        any_classifier_fires_direct = (
            fires if any_classifier_fires_direct is None else (any_classifier_fires_direct | fires)
        )
    any_classifier_fires_two_stage = any_classifier_fires_direct & is_anomaly

    result = {
        "n_rows_total": len(table),
        "n_rows_baseline": int(is_baseline.sum()),
        "system_fpr": {
            "direct": float(any_classifier_fires_direct[is_baseline].mean()),
            "two_stage": float(any_classifier_fires_two_stage[is_baseline].mean()),
        },
        "per_fault_file": {},
        "cross_fault_misfires": {},
    }

    for file_label in sorted(source_files.unique()):
        if file_label == "baseline":
            continue
        mask = (source_files == file_label).to_numpy()
        n_rows = int(mask.sum())

        true_fault = None
        for fault_name, config in SIMULATED_FAULTS.items():
            if file_label in config.fault_paths:
                true_fault = fault_name
                break

        direct_detected = float(any_classifier_fires_direct[mask].mean())
        two_stage_detected = float(any_classifier_fires_two_stage[mask].mean())
        gatekeeper_flagged = float(is_anomaly[mask].mean())

        result["per_fault_file"][file_label] = {
            "n_rows": n_rows,
            "true_fault": true_fault,
            "direct_system_detection_rate": direct_detected,
            "two_stage_system_detection_rate": two_stage_detected,
            "gatekeeper_flag_rate": gatekeeper_flagged,
            "gating_missed_rate": max(0.0, direct_detected - two_stage_detected),
        }

        misfires = {}
        for name in classifier_names:
            if name == true_fault:
                continue
            fire_rate = float((scores[name]["predicted"][mask] == 1).mean())
            if fire_rate > 0.05:
                misfires[name] = fire_rate
        if misfires:
            result["cross_fault_misfires"][file_label] = misfires

    return result


if __name__ == "__main__":
    table = build_shared_table()
    scores = score_all_models(table)
    result = analyze(table, scores)

    output_path = ML_ROOT / "TWO_STAGE_VALIDATION_RESULTS.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"\nSaved to {output_path}")

    print(
        f"\n=== System-level false-positive rate on baseline ({result['n_rows_baseline']} rows) ==="
    )
    print(f"Direct (no gating):  {result['system_fpr']['direct']:.4f}")
    print(f"Two-stage (gated):   {result['system_fpr']['two_stage']:.4f}")

    print("\n=== Per-fault-file detection: direct vs. two-stage (gating risk) ===")
    for file_label, d in sorted(
        result["per_fault_file"].items(), key=lambda kv: kv[1]["gating_missed_rate"], reverse=True
    ):
        print(
            f"  {file_label:20s} true={d['true_fault']:25s} "
            f"direct={d['direct_system_detection_rate']:.3f}  "
            f"two_stage={d['two_stage_system_detection_rate']:.3f}  "
            f"gating_missed={d['gating_missed_rate']:.3f}"
        )

    if result["cross_fault_misfires"]:
        print("\n=== Cross-fault misfires (>5% fire rate on a DIFFERENT fault's data) ===")
        for file_label, misfires in result["cross_fault_misfires"].items():
            print(f"  {file_label}: {misfires}")
