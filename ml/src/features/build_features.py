"""Feature engineering: build labeled, weather-residualized feature tables for
fault classification.

Derived from ml/notebooks/11_model_undercharge_template.ipynb: raw physical
signals (pressures, temperatures, capacity) carry real fault signal, but also
carry substantial weather-driven variance (RTU_OA_TEMP explained 77-99% of
several features' baseline-condition variance). That variance is comparable in
magnitude to some faults' true effect size, and materially degrades forward-
in-time model generalization if left unaddressed. Residualizing each feature
against a baseline-fit linear regression on outdoor temperature removes most
of this nuisance variance while preserving the fault-driven component.

Known limitation, carried over from the template notebook: weather-
residualization measurably improves near-term generalization but does not
fully resolve degradation in farther-future evaluation folds. Report both
random-split and time-series-split metrics for any model built on these
features - do not rely on random-split metrics alone.
"""

from pathlib import Path

import pandas as pd
from sklearn.linear_model import LinearRegression

from src.features.filtering import stage2_only
from src.features.smoothing import add_segmented_ewma


def build_feature_table(
    baseline_path: str | Path,
    fault_paths: dict[str, str | Path],
    weather_col: str = "RTU_OA_TEMP",
    capacity_col: str = "RTU_TOT_CAPA",
    pressure_temp_cols: tuple[str, ...] = (
        "RTU_REFG_SUCT_PRES",
        "RTU_REFG_SUCT_TEMP",
        "RTU_REFG_DISC_PRES",
    ),
    stage_col: str = "RTU_STG_STA",
    ewma_span: int = 30,
    return_weather_models: bool = False,
) -> pd.DataFrame | tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    """Build a labeled, stage-2-filtered, weather-residualized feature table.

    Loads a baseline file and one or more fault-severity files, applies
    stage-2 compressor filtering, segmented-EWMA-smooths the capacity
    column, then residualizes capacity and the pressure/temperature columns
    against a baseline-fit linear regression on outdoor air temperature.
    Residualizing removes weather-driven nuisance variance that can rival
    or exceed some faults' true effect size (see module docstring).

    Args:
        baseline_path: Path to the unfaulted baseline CSV.
        fault_paths: Mapping of label -> path, one entry per fault-severity
            CSV to include (e.g. {"undercharge10": "...", "undercharge15": "..."}).
            All severities are pooled under label=1; this function does not
            yet support multi-class (per-severity) labeling.
        weather_col: Column used as the weather-residualization predictor.
        capacity_col: Raw capacity column to smooth and residualize.
        pressure_temp_cols: Additional raw columns to residualize against
            weather. Chosen per-fault in the template notebook based on EDA;
            callers should pass the columns relevant to the fault being built.
        stage_col: Compressor stage column, passed to stage2_only().
        ewma_span: Span for segmented EWMA smoothing, passed to
            add_segmented_ewma(). Not validated as a universal default -
            see ml/notebooks/02_eda_overcharge.ipynb for why this needs
            per-fault/per-feature validation, not blind reuse.
        return_weather_models: If True, also return the fitted weather-
            regression coefficients (slope/intercept per residualized
            column). Needed at training time so these coefficients can be
            PERSISTED and reused identically at inference time - live,
            unlabeled data has no "baseline rows" to refit against, so the
            regression must be fit once (here, on known-labeled training
            data) and then only ever applied, never refit, in production.
            Default False preserves the original single-return-value
            behavior for existing callers.

    Returns:
        If return_weather_models is False (default): a single concatenated,
        sorted-by-Datetime DataFrame with columns: Datetime, one
        `<col>_residual` per residualized column, label (0=baseline, 1=any
        fault), and source_file (which input file each row came from).

        If return_weather_models is True: a tuple (table, weather_models)
        where weather_models maps each residualized column name to
        {"slope": float, "intercept": float} from the baseline-fit
        LinearRegression against weather_col.
    """
    files = {"baseline": baseline_path, **fault_paths}
    dfs = {label: pd.read_csv(path) for label, path in files.items()}

    for df in dfs.values():
        df["Datetime"] = pd.to_datetime(df["Datetime"])

    capacity_smoothed_col = f"{capacity_col}_ewma{ewma_span}_segmented"
    cols_to_residualize = list(pressure_temp_cols) + [capacity_smoothed_col]

    labeled_dfs = []
    for label, df in dfs.items():
        # Segmented EWMA must run on the FULL, unfiltered series first, so its
        # run-segmentation logic sees real off/stage1/stage2 transitions and
        # real time gaps between separate stage-2 operating sessions - this
        # matches notebook 01's original, validated approach. Filtering to
        # stage-2 rows BEFORE smoothing (the previous, buggy order) leaves
        # every remaining row in the same state bucket, so there are no real
        # transitions left to segment by - the smoothing then silently
        # blends together what were actually separate stage-2 sessions,
        # exactly the cross-contamination segmented EWMA was built to avoid.
        smoothed = add_segmented_ewma(
            df,
            value_col=capacity_col,
            state_col=stage_col,
            span=ewma_span,
            output_col=capacity_smoothed_col,
        )
        filtered = stage2_only(smoothed, stage_col=stage_col)
        subset = filtered[["Datetime", weather_col] + cols_to_residualize].copy()
        subset["label"] = 0 if label == "baseline" else 1
        subset["source_file"] = label
        labeled_dfs.append(subset)

    table = pd.concat(labeled_dfs, ignore_index=True).sort_values("Datetime").reset_index(drop=True)

    baseline_rows = table[table["label"] == 0]
    weather_models: dict[str, dict[str, float]] = {}
    for col in cols_to_residualize:
        weather_model = LinearRegression()
        weather_model.fit(baseline_rows[[weather_col]], baseline_rows[col])
        predicted = weather_model.predict(table[[weather_col]])
        table[f"{col}_residual"] = table[col] - predicted
        weather_models[col] = {
            "slope": float(weather_model.coef_[0]),
            "intercept": float(weather_model.intercept_),
            "weather_col": weather_col,
        }

    residual_cols = [f"{col}_residual" for col in cols_to_residualize]
    result = table[["Datetime", "label", "source_file"] + residual_cols]

    if return_weather_models:
        return result, weather_models
    return result
