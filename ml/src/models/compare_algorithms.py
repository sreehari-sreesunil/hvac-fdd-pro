"""Multi-algorithm comparison harness for Simulated-dataset fault classifiers.

Built per an external reviewer's recommendation: "compare models using a
standard evaluation framework and select the best-performing model," rather
than defaulting to Random Forest without ever testing whether it's actually
the best choice per fault.

Evaluation methodology matches every other classifier metric in this
project: 5-fold TimeSeriesSplit, never a random split (see
ml/MODEL_ACCEPTANCE_CRITERIA.md). Hyperparameters are chosen via a NESTED
search - for each outer TimeSeriesSplit fold, an inner TimeSeriesSplit-based
GridSearchCV selects hyperparameters using ONLY that fold's training
portion, before that fold's test portion is ever touched. This avoids
picking hyperparameters using the same data they're evaluated against.

Scope boundary, deliberate: this harness uses the SAME feature set already
locked in per fault in model_registry.py (including existing capacity-
ablation decisions) - it varies only the algorithm and its hyperparameters,
not the feature engineering. Re-testing feature choices per algorithm is a
separate, larger piece of work, not assumed here.

Results are written to MODEL_COMPARISON_RESULTS.json - a raw comparison
record, not a final decision. Promoting a winning algorithm into
model_registry.py/train_final_models.py/FINAL_MODEL_METRICS.md is a
deliberate, separate step after reviewing these results against
ml/MODEL_ACCEPTANCE_CRITERIA.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ML_ROOT = Path(__file__).resolve().parents[2]
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from src.features.build_features import build_feature_table  # noqa: E402
from src.models.model_registry import SIMULATED_FAULTS  # noqa: E402

try:
    from xgboost import XGBClassifier

    _HAS_XGBOOST = True
except ImportError:
    _HAS_XGBOOST = False


def _resolve_path(relative_path: str) -> str:
    return str(Path(__file__).resolve().parents[2] / relative_path)


def _build_candidates() -> dict[str, tuple[Pipeline, dict]]:
    """Candidate algorithms + a deliberately narrow hyperparameter grid per
    algorithm, kept small so the nested search below finishes in minutes,
    not hours, on a solo-developer machine.

    class_weight="balanced" is used for Random Forest and Logistic
    Regression here - this is a deliberate change from the currently
    shipped Random Forest config (which does not set it). Worth knowing
    going in: this comparison is not "apples to apples" against the exact
    deployed model, it's testing whether a better-regularized version of
    each algorithm improves things further.
    """
    candidates: dict[str, tuple[Pipeline, dict]] = {
        "logistic_regression": (
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "clf",
                        LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42),
                    ),
                ]
            ),
            {"clf__C": [0.1, 1.0, 10.0]},
        ),
        "random_forest": (
            Pipeline([("clf", RandomForestClassifier(class_weight="balanced", random_state=42))]),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [3, 5, 8],
            },
        ),
        "mlp": (
            Pipeline(
                [
                    ("scaler", StandardScaler()),
                    (
                        "clf",
                        MLPClassifier(max_iter=1000, early_stopping=True, random_state=42),
                    ),
                ]
            ),
            {
                "clf__hidden_layer_sizes": [(64, 32)],
                "clf__alpha": [0.001],
            },
        ),
    }
    if _HAS_XGBOOST:
        candidates["xgboost"] = (
            Pipeline([("clf", XGBClassifier(eval_metric="logloss", random_state=42))]),
            {
                "clf__n_estimators": [100, 200],
                "clf__max_depth": [3, 5],
                "clf__learning_rate": [0.05, 0.1],
            },
        )
    return candidates


def _acceptance_tier(recalls: list[float], precisions: list[float]) -> str:
    """Apply ml/MODEL_ACCEPTANCE_CRITERIA.md's numeric tiers. Mirrors that
    document exactly - if the criteria change, update both places together.
    """
    min_recall, min_precision = min(recalls), min(precisions)
    if min_recall >= 0.90 and min_precision >= 0.75:
        return "Usable"
    if min_recall >= 0.65 and min_precision >= 0.60:
        return "Usable with caveat"
    return "Not production-usable"


def compare_algorithms_for_fault(fault_name: str) -> dict:
    """Run every candidate algorithm through an identical 5-fold
    TimeSeriesSplit for one fault, with nested hyperparameter search per
    fold. Returns a structured result dict, one entry per algorithm.
    """
    config = SIMULATED_FAULTS[fault_name]
    table, _ = build_feature_table(
        baseline_path=_resolve_path(config.baseline_path),
        fault_paths={label: _resolve_path(path) for label, path in config.fault_paths.items()},
        pressure_temp_cols=config.pressure_temp_cols,
        return_weather_models=True,
    )

    residual_cols = [f"{col}_residual" for col in config.pressure_temp_cols]
    if config.include_capacity:
        residual_cols.append("RTU_TOT_CAPA_ewma30_segmented_residual")

    X = table[residual_cols].reset_index(drop=True)
    y = table["label"].reset_index(drop=True)

    outer_cv = TimeSeriesSplit(n_splits=5)
    results: dict[str, dict] = {}

    for algo_name, (pipeline, param_grid) in _build_candidates().items():
        fold_records = []
        for train_idx, test_idx in outer_cv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

            # Inner search: pick hyperparameters using ONLY this fold's
            # training portion. The test portion is untouched until predict().
            inner_cv = TimeSeriesSplit(n_splits=3)
            search = GridSearchCV(
                pipeline, param_grid, cv=inner_cv, scoring="f1", n_jobs=-1, verbose=1
            )
            search.fit(X_train, y_train)

            y_pred = search.predict(X_test)
            fold_records.append(
                {
                    "n_train": len(train_idx),
                    "n_test": len(test_idx),
                    "n_positive_train": int(y_train.sum()),
                    "n_positive_test": int(y_test.sum()),
                    "recall": float(recall_score(y_test, y_pred, zero_division=0)),
                    "precision": float(precision_score(y_test, y_pred, zero_division=0)),
                    "best_params": search.best_params_,
                }
            )

        recalls = [f["recall"] for f in fold_records]
        precisions = [f["precision"] for f in fold_records]
        results[algo_name] = {
            "folds": fold_records,
            "recall_range": [min(recalls), max(recalls)],
            "precision_range": [min(precisions), max(precisions)],
            "acceptance_tier": _acceptance_tier(recalls, precisions),
        }

    return results


def run_full_comparison() -> dict:
    """Run the comparison for every fault currently in SIMULATED_FAULTS.

    Note: undercharge is intentionally NOT included here, since it isn't
    in SIMULATED_FAULTS (excluded from the registry per its own
    Not-production-usable status). Re-testing undercharge against these
    other algorithms is a real, separate, worthwhile follow-up - Random
    Forest failing doesn't prove every algorithm fails the same way - but
    it needs its own explicit config, not assumed here.
    """
    all_results = {}
    for fault_name in SIMULATED_FAULTS:
        print(f"Comparing algorithms for: {fault_name}")
        all_results[fault_name] = compare_algorithms_for_fault(fault_name)
    return all_results


def print_summary(all_results: dict) -> None:
    """Quick console summary: winning tier per algorithm per fault."""
    for fault_name, fault_results in all_results.items():
        print(f"\n{fault_name}:")
        for algo_name, algo_result in fault_results.items():
            r_lo, r_hi = algo_result["recall_range"]
            p_lo, p_hi = algo_result["precision_range"]
            tier = algo_result["acceptance_tier"]
            print(
                f"  {algo_name:20s} recall {r_lo:.2f}-{r_hi:.2f}  "
                f"precision {p_lo:.2f}-{p_hi:.2f}  -> {tier}"
            )


if __name__ == "__main__":
    all_results = run_full_comparison()
    output_path = Path(__file__).resolve().parents[2] / "MODEL_COMPARISON_RESULTS.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nSaved raw results to {output_path}")
    print_summary(all_results)
