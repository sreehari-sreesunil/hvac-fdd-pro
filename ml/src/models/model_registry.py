"""Model registry: single source of truth for which fault models are
finalized for training/saving, their feature configuration, and why.

Every entry here traces back to a real, documented decision in
ml/MODEL_RESULTS_LOG.md and ml/FINAL_MODEL_METRICS.md - this file does not
introduce new judgment calls, it encodes decisions already made and
justified elsewhere. If a fault's status changes (e.g. undercharge's root
cause gets resolved), update the log/metrics files first, then this
registry, in that order.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SimulatedFaultConfig:
    """Configuration for one Simulated-dataset binary fault classifier."""

    name: str
    baseline_path: str
    fault_paths: dict[str, str]
    pressure_temp_cols: tuple[str, ...]
    include_capacity: bool
    status: str  # must match a status label from FINAL_MODEL_METRICS.md
    notes: str
    algorithm: str = "random_forest"  # "random_forest" or "xgboost" - see MODEL_COMPARISON_LOG.md
    algorithm_params: dict = field(
        default_factory=dict
    )  # hyperparameter overrides for the chosen algorithm


@dataclass(frozen=True)
class ExperimentalFaultConfig:
    """Configuration for one Experimental-dataset cross-season fault model."""

    name: str
    train_seasons: tuple[str, ...]
    feature_cols: tuple[str, ...]
    use_weather_residual: bool
    status: str
    notes: str


# ---------------------------------------------------------------------------
# Simulated dataset - only faults with status "Usable" or "Usable with caveat"
# in FINAL_MODEL_METRICS.md are included here. Undercharge is deliberately
# excluded: status "Not production-usable", root cause unresolved.
# ---------------------------------------------------------------------------

SIMULATED_FAULTS: dict[str, SimulatedFaultConfig] = {
    "overcharge": SimulatedFaultConfig(
        name="overcharge",
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={
            "overcharge10": "data/raw/RTU_sim_overcharge10.csv",
            "overcharge15": "data/raw/RTU_sim_overcharge15.csv",
            "overcharge20": "data/raw/RTU_sim_overcharge20.csv",
        },
        pressure_temp_cols=("RTU_REFG_SUCT_PRES", "RTU_REFG_SUCT_TEMP", "RTU_REFG_DISC_PRES"),
        include_capacity=False,  # notebook 02: capacity never established as a strong signal here
        status="Usable",
        notes="Stable across TimeSeriesSplit folds (0.97-1.00). See notebook 12.",
    ),
    "condenser_fouling": SimulatedFaultConfig(
        name="condenser_fouling",
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={
            "condfouling10": "data/raw/RTU_sim_condfouling10.csv",
            "condfouling20": "data/raw/RTU_sim_condfouling20.csv",
            "condfouling30": "data/raw/RTU_sim_condfouling30.csv",
            "condfouling40": "data/raw/RTU_sim_condfouling40.csv",
            "condfouling50": "data/raw/RTU_sim_condfouling50.csv",
        },
        pressure_temp_cols=("RTU_REFG_COND_PRES", "RTU_REFG_COND_TEMP"),
        include_capacity=True,  # weak signal but included per notebook 13; kept for consistency
        status="Usable",
        notes="Strongest, most stable result of all 6 faults. See notebook 13.",
    ),
    "evaporator_fouling": SimulatedFaultConfig(
        name="evaporator_fouling",
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={
            "evapfouling10": "data/raw/RTU_sim_evapfouling10.csv",
            "evapfouling20": "data/raw/RTU_sim_evapfouling20.csv",
            "evapfouling30": "data/raw/RTU_sim_evapfouling30.csv",
            "evapfouling40": "data/raw/RTU_sim_evapfouling40.csv",
            "evapfouling50": "data/raw/RTU_sim_evapfouling50.csv",
        },
        pressure_temp_cols=("RTU_REFG_SUCT_PRES", "RTU_REFG_SUCT_TEMP", "RTU_SA_TEMP"),
        include_capacity=False,  # notebook 17 ablation test: CONFIRMED capacity causes degradation here
        status="Usable",  # UPDATED - see MODEL_COMPARISON_LOG.md: XGBoost resolves the RF recall floor
        algorithm="xgboost",
        algorithm_params={"n_estimators": 200, "max_depth": 5, "learning_rate": 0.1},
        notes=(
            "SWITCHED to XGBoost per MODEL_COMPARISON_LOG.md - Random Forest had a documented "
            "TimeSeriesSplit recall floor (0.76->0.41). XGBoost achieves stable ~0.95 recall in "
            "every fold, crossing into 'Usable'. Hyperparameters chosen via nested TimeSeriesSplit "
            "GridSearchCV (see compare_algorithms.py), consistent across all 5 outer folds. "
            "Capacity still excluded per notebook 17's original ablation finding - that decision "
            "was about feature engineering, not algorithm, and was not retested here."
        ),
    ),
    "liquidline_restriction": SimulatedFaultConfig(
        name="liquidline_restriction",
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={
            "liquidpipe01bar": "data/raw/RTU_sim_liquidpipe01bar.csv",
            "liquidpipe04bar": "data/raw/RTU_sim_liquidpipe04bar.csv",
            "liquidpipe08bar": "data/raw/RTU_sim_liquidpipe08bar.csv",
            "liquidpipe10bar": "data/raw/RTU_sim_liquidpipe10bar.csv",
        },
        pressure_temp_cols=("RTU_REFG_SUCT_PRES", "RTU_REFG_SUCT_TEMP", "RTU_REFG_DISC_PRES"),
        include_capacity=True,  # notebook 15: stable even with capacity included, unlike evap/suction
        status="Usable",
        notes="Stable despite this fault's threshold-shaped severity response. See notebook 15.",
    ),
    "suctionline_restriction": SimulatedFaultConfig(
        name="suctionline_restriction",
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={
            "suctionpipe01bar": "data/raw/RTU_sim_suctionpipe01bar.csv",
            "suctionpipe03bar": "data/raw/RTU_sim_suctionpipe03bar.csv",
            "suctionpipe06bar": "data/raw/RTU_sim_suctionpipe06bar.csv",
            "suctionpipe09bar": "data/raw/RTU_sim_suctionpipe09bar.csv",
        },
        pressure_temp_cols=("RTU_REFG_SUCT_PRES", "RTU_REFG_SUCT_TEMP"),
        include_capacity=False,  # notebook 17 ablation test: CONFIRMED, same as evaporator fouling
        status="Usable with caveat",
        notes=(
            "Capacity deliberately excluded - notebook 17's ablation test confirmed removing it "
            "stabilizes TimeSeriesSplit recall (0.87->0.43 becomes 0.96-0.99 stable), at a real "
            "precision cost (~1.00 -> consistent 0.63)."
        ),
    ),
}

# Undercharge intentionally has NO entry here. See ml/FINAL_MODEL_METRICS.md:
# "Not production-usable" - root cause partially isolated, not resolved. Do not
# add an entry until that status changes.

ISOLATION_FOREST_CONFIG = {
    "feature_cols": ("RTU_REFG_SUCT_PRES", "RTU_REFG_SUCT_TEMP"),
    "capacity_col": "RTU_TOT_CAPA",
    "contamination": 0.03,  # RE-tuned in notebook 26 after the capacity-feature bug fix
    # (build_features.py order-of-operations fix) revealed contamination=0.01 was
    # miscalibrated against the corrected feature - severe detection regression on
    # moderate-tier faults (e.g. evapfouling40: 0.99998->0.404), missed by an
    # insufficient 2-file spot check in notebook 25. contamination=0.03 restores
    # near-original detection across the full 24-file sweep, at a real, disclosed
    # FPR cost (7.6% vs the previous, now-invalidated 2.9%).
    "status": "Usable with caveat",
    "notes": (
        "7.6% false-positive rate on held-out later baseline (contamination=0.03, "
        "re-tuned after the capacity-feature bug fix - see notebook 26 and "
        "MODEL_RESULTS_LOG.md's 'Isolation Forest contamination re-tuning' entry). "
        "Detection rate forms an honest gradient matching EDA effect sizes - "
        "near-perfect for strong faults, weak for faults already flagged as "
        "low-severity/weak-signal in EDA. Verified across the FULL 24-file sweep, "
        "not a partial spot check."
    ),
}

# ---------------------------------------------------------------------------
# Experimental dataset - only faults/directions with status "Usable" or
# "Usable with caveat" are included. Biased SAT sensor (not production-usable)
# and econ-setpoint-too-high (not modeled - data availability gap) are
# deliberately excluded.
# ---------------------------------------------------------------------------

EXPERIMENTAL_FAULTS: dict[str, ExperimentalFaultConfig] = {
    "oa_damper_stuck": ExperimentalFaultConfig(
        name="oa_damper_stuck",
        train_seasons=("Winter_2022", "Spring_2021"),
        feature_cols=("RTU_OA_DMPR_DM", "RTU_OA_TEMP"),
        use_weather_residual=True,  # notebook 19: raw features collapse cross-season (0.11 recall)
        status="Usable with caveat",
        notes=(
            "OA_TEMP-residualized damper position used, not raw - notebook 19 found this "
            "partially mitigates cross-season collapse (recall 0.11->0.34), at a real precision "
            "cost (1.00->0.42). Real, unresolved tradeoff - not a clean fix."
        ),
    ),
    "econ_setpoint_too_low": ExperimentalFaultConfig(
        name="econ_setpoint_too_low",
        train_seasons=("Winter_2022",),
        feature_cols=("RTU_OA_DMPR_DM", "RTU_OA_TEMP"),
        use_weather_residual=False,  # notebook 21: raw features used, moderate result achieved as-is
        status="Usable with caveat",
        notes=(
            "Only the 6C/8C (too-low) severities - see notebook 21 for why the 12C/14C "
            "(too-high) direction has NO entry here (data-availability gap, not modeled). "
            "Moderate result: baseline recall 0.40, precision 0.87, trained on Winter_2022."
        ),
    ),
}
