"""Train and save final, deployable models per ml/src/models/model_registry.py.

This script trains each model on the FULL available historical data for that
fault (not a train/test split - the split-based evaluation already happened
in the corresponding EDA/modeling notebooks; this script produces the actual
artifact to be used for inference, and should use all available real signal).

Each model is saved via joblib alongside a JSON metadata sidecar recording
the exact feature list (in order - inference must reproduce this exactly),
the model's registry status/notes, and training provenance. This metadata is
what a future ml-service or inference script must read before ever calling
.predict() on a loaded model - never assume a feature order.

Run from the ml/ directory: `poetry run python src/models/train_final_models.py`
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from xgboost import XGBClassifier

ML_ROOT = Path(__file__).resolve().parents[2]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from src.features.build_experimental_features import build_experimental_feature_table  # noqa: E402
from src.features.build_features import build_feature_table  # noqa: E402
from src.models.model_registry import (  # noqa: E402
    EXPERIMENTAL_FAULTS,
    ISOLATION_FOREST_CONFIG,
    SIMULATED_FAULTS,
)

MODELS_DIR = ML_ROOT / "models"


def _resolve_path(relative_path: str) -> str:
    """Resolve a registry-relative data path against ML_ROOT."""
    return str(ML_ROOT / relative_path)


def _save_model(
    model, name: str, feature_cols: list[str], status: str, notes: str, extra: dict | None = None
) -> None:
    """Save a fitted model and its metadata sidecar to MODELS_DIR."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / f"{name}.joblib"
    joblib.dump(model, model_path)

    metadata = {
        "name": name,
        "feature_cols": feature_cols,
        "status": status,
        "notes": notes,
        "sklearn_version": sklearn.__version__,
        "trained_at_utc": datetime.now(UTC).isoformat(),
    }
    if extra:
        metadata.update(extra)

    metadata_path = MODELS_DIR / f"{name}.metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"Saved {model_path.name} + {metadata_path.name}")


def train_simulated_fault_models() -> None:
    """Train and save one binary classifier per SIMULATED_FAULTS entry."""
    for fault_name, config in SIMULATED_FAULTS.items():
        table, weather_models = build_feature_table(
            baseline_path=_resolve_path(config.baseline_path),
            fault_paths={label: _resolve_path(path) for label, path in config.fault_paths.items()},
            pressure_temp_cols=config.pressure_temp_cols,
            return_weather_models=True,
        )

        residual_cols = [f"{col}_residual" for col in config.pressure_temp_cols]
        capacity_residual_col = "RTU_TOT_CAPA_ewma30_segmented_residual"
        if config.include_capacity:
            residual_cols.append(capacity_residual_col)

        if config.algorithm == "xgboost":
            model = XGBClassifier(eval_metric="logloss", random_state=42, **config.algorithm_params)
        else:
            model = RandomForestClassifier(
                n_estimators=100, max_depth=5, random_state=42, **config.algorithm_params
            )
        model.fit(table[residual_cols], table["label"])

        required_raw_metrics = list(config.pressure_temp_cols) + ["RTU_STG_STA", "RTU_OA_TEMP"]
        if config.include_capacity:
            required_raw_metrics.append("RTU_TOT_CAPA")

        _save_model(
            model,
            name=f"simulated_{fault_name}",
            feature_cols=residual_cols,
            status=config.status,
            notes=config.notes,
            extra={
                "dataset": "simulated",
                "algorithm": config.algorithm,
                "training_rows": len(table),
                "weather_regression_models": weather_models,
                "required_raw_metrics": required_raw_metrics,
            },
        )


def train_isolation_forest() -> None:
    """Train and save the Isolation Forest gatekeeper on baseline-only data
    from every Simulated fault type's file set (matches notebook 18)."""
    all_fault_paths: dict[str, str] = {}
    for config in SIMULATED_FAULTS.values():
        all_fault_paths.update(config.fault_paths)
    # Undercharge is excluded from SIMULATED_FAULTS but its files are still
    # useful baseline-adjacent context; deliberately NOT added here - the
    # Isolation Forest should reflect the same fault scope as the registry.

    table, weather_models = build_feature_table(
        baseline_path=_resolve_path("data/raw/RTU_sim_baseline.csv"),
        fault_paths={label: _resolve_path(path) for label, path in all_fault_paths.items()},
        pressure_temp_cols=ISOLATION_FOREST_CONFIG["feature_cols"],
        return_weather_models=True,
    )

    feature_cols = [f"{col}_residual" for col in ISOLATION_FOREST_CONFIG["feature_cols"]]
    feature_cols.append("RTU_TOT_CAPA_ewma30_segmented_residual")

    baseline_only = table[table["label"] == 0]
    model = IsolationForest(
        contamination=ISOLATION_FOREST_CONFIG["contamination"],
        random_state=42,
        n_estimators=100,
    )
    model.fit(baseline_only[feature_cols])

    _save_model(
        model,
        name="simulated_isolation_forest",
        feature_cols=feature_cols,
        status=ISOLATION_FOREST_CONFIG["status"],
        notes=ISOLATION_FOREST_CONFIG["notes"],
        extra={
            "dataset": "simulated",
            "training_rows": len(baseline_only),
            "contamination": ISOLATION_FOREST_CONFIG["contamination"],
            "weather_regression_models": weather_models,
            "required_raw_metrics": list(ISOLATION_FOREST_CONFIG["feature_cols"])
            + ["RTU_TOT_CAPA", "RTU_STG_STA", "RTU_OA_TEMP"],
        },
    )


def train_experimental_fault_models() -> None:
    """Train and save one cross-season model per EXPERIMENTAL_FAULTS entry."""
    for fault_name, config in EXPERIMENTAL_FAULTS.items():
        season_tables = []
        for season in config.train_seasons:
            baseline_path = _resolve_path(f"data/raw/experimental/ERTU_{season}.csv")
            if fault_name == "oa_damper_stuck":
                fault_paths = {
                    f"damper_005_{season}": _resolve_path(
                        f"data/raw/experimental/OA_damper_stuck_005_{season}.csv"
                    ),
                    f"damper_010_{season}": _resolve_path(
                        f"data/raw/experimental/OA_damper_stuck_010_{season}.csv"
                    ),
                    f"damper_050_{season}": _resolve_path(
                        f"data/raw/experimental/OA_damper_stuck_050_{season}.csv"
                    ),
                    f"damper_100_{season}": _resolve_path(
                        f"data/raw/experimental/OA_damper_stuck_100_{season}.csv"
                    ),
                }
            elif fault_name == "econ_setpoint_too_low":
                fault_paths = {
                    f"econ_neg4_{season}": _resolve_path(
                        f"data/raw/experimental/Inc_Eco_SP_-4_{season}.csv"
                    ),
                    f"econ_neg2_{season}": _resolve_path(
                        f"data/raw/experimental/Inc_Eco_SP_-2_{season}.csv"
                    ),
                }
            else:
                raise ValueError(
                    f"No file-path mapping defined for '{fault_name}' - add one before training."
                )

            season_tables.append(
                build_experimental_feature_table(
                    baseline_path=baseline_path,
                    fault_paths=fault_paths,
                    feature_cols=config.feature_cols,
                )
            )

        table = pd.concat(season_tables, ignore_index=True)
        feature_cols = list(config.feature_cols)

        if config.use_weather_residual:
            from sklearn.linear_model import LinearRegression

            baseline_rows = table[table["label"] == 0]
            weather_col = "RTU_OA_TEMP"
            target_col = [c for c in config.feature_cols if c != weather_col][0]

            weather_model = LinearRegression()
            weather_model.fit(baseline_rows[[weather_col]], baseline_rows[target_col])
            table[f"{target_col}_residual"] = table[target_col] - weather_model.predict(
                table[[weather_col]]
            )
            feature_cols = [f"{target_col}_residual"]

        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(table[feature_cols], table["label"])

        extra = {
            "dataset": "experimental",
            "training_rows": len(table),
            "train_seasons": list(config.train_seasons),
        }
        extra["required_raw_metrics"] = list(config.feature_cols) + ["OCCU_MOD"]
        if config.use_weather_residual:
            extra["weather_regression_models"] = {
                target_col: {
                    "slope": float(weather_model.coef_[0]),
                    "intercept": float(weather_model.intercept_),
                    "weather_col": weather_col,
                }
            }

        _save_model(
            model,
            name=f"experimental_{fault_name}",
            feature_cols=feature_cols,
            status=config.status,
            notes=config.notes,
            extra=extra,
        )


if __name__ == "__main__":
    print("Training Simulated-dataset fault classifiers...")
    train_simulated_fault_models()

    print("\nTraining Isolation Forest anomaly detector...")
    train_isolation_forest()

    print("\nTraining Experimental-dataset fault models...")
    train_experimental_fault_models()

    print(f"\nAll models saved to {MODELS_DIR}")
