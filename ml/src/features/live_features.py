"""Live feature engineering: reproduce a saved model's exact feature
transformation on a rolling buffer of recent, unlabeled raw readings.

This is the production counterpart to build_features.py /
build_experimental_features.py, which operate on static, fully-labeled
historical CSVs. Live telemetry has neither: no fixed file to load, and no
label telling us which rows are "baseline" to fit a weather regression
against. Every model's weather-regression coefficients were fit ONCE during
training (see train_final_models.py) and persisted in its metadata sidecar
- this module only ever APPLIES those saved coefficients, never refits them.

A "buffer" is a pandas DataFrame of recent raw readings for ONE asset,
sorted ascending by Datetime, containing at minimum the columns needed to
reproduce that model's feature_cols. How much history the buffer needs to
contain depends on the model: Simulated-dataset models need enough history
for add_segmented_ewma() to have a meaningful run length (the EDA never
validated span=30 as a universal default - see
ml/notebooks/02_eda_overcharge.ipynb - so a buffer of at least the model's
ewma_span worth of same-state minutes is a reasonable minimum, not a
guarantee of a "warmed up" smoothed value).
"""

import pandas as pd

from src.features.filtering import stage2_only
from src.features.smoothing import add_segmented_ewma


def _apply_saved_residual(raw_value: float, weather_value: float, coefs: dict[str, float]) -> float:
    """Apply a SAVED (never refit) weather regression to one raw value."""
    predicted = coefs["slope"] * weather_value + coefs["intercept"]
    return raw_value - predicted


def build_live_simulated_features(
    buffer: pd.DataFrame,
    metadata: dict,
    capacity_col: str = "RTU_TOT_CAPA",
    stage_col: str = "RTU_STG_STA",
    ewma_span: int = 30,
) -> pd.Series:
    """Build the feature vector a Simulated-dataset model expects, from a
    live buffer of recent raw readings for one asset.

    Args:
        buffer: Recent raw readings, sorted ascending by Datetime. Must
            contain stage_col, the weather column referenced in the model's
            saved regressions, and every raw column implied by
            metadata["feature_cols"].
        metadata: The model's loaded metadata.json content - must include
            "feature_cols" and "weather_regression_models" (see
            train_final_models.py).
        capacity_col, stage_col, ewma_span: Must match what the model was
            TRAINED with (see build_feature_table()'s defaults, unchanged
            across every Simulated-dataset model in this project so far).

    Returns:
        A pandas Series indexed by metadata["feature_cols"], ready to pass
        (as a single-row DataFrame) to model.predict()/.predict_proba().

    Raises:
        ValueError: if the buffer has no stage-2 rows at all (the asset is
            not currently in stage-2 operation, per this project's
            established stage2_only() filtering convention) - the caller
            should treat this as "cannot currently score this asset",
            not silently score on stale or off-state data.
    """
    smoothed_col = f"{capacity_col}_ewma{ewma_span}_segmented"
    needs_capacity = f"{smoothed_col}_residual" in metadata["feature_cols"]

    if needs_capacity:
        # Segmented EWMA needs the buffer's full history BEFORE stage
        # filtering - the segmentation logic depends on state transitions
        # across the whole buffer, per
        # ml/src/features/smoothing.py's add_segmented_ewma(). Only run
        # this when the model actually uses the smoothed-capacity-residual
        # feature - models with include_capacity=False (see
        # model_registry.py, e.g. evaporator_fouling, suctionline_restriction,
        # per notebook 17's ablation-tested fix) never fetch raw capacity
        # into the buffer at all, so calling this unconditionally would
        # KeyError on a column that was never fetched. Found via a real
        # end-to-end test against suctionline_restriction, not assumed.
        working_buffer = add_segmented_ewma(
            buffer,
            value_col=capacity_col,
            state_col=stage_col,
            span=ewma_span,
            output_col=smoothed_col,
        )
    else:
        working_buffer = buffer

    stage2_rows = stage2_only(working_buffer, stage_col=stage_col)
    if stage2_rows.empty:
        raise ValueError(
            "No stage-2 rows in buffer - cannot score this asset right now (not currently in stage-2 operation)."
        )
    latest = stage2_rows.iloc[-1]

    weather_models = metadata["weather_regression_models"]
    features = {}
    for feature_col in metadata["feature_cols"]:
        raw_col = feature_col.removesuffix("_residual")
        coefs = weather_models[raw_col]
        features[feature_col] = _apply_saved_residual(
            raw_value=latest[raw_col],
            weather_value=latest[coefs["weather_col"]],
            coefs=coefs,
        )

    return pd.Series(features)


def build_live_experimental_features(
    buffer: pd.DataFrame,
    metadata: dict,
    occu_mod_col: str = "OCCU_MOD",
) -> pd.Series:
    """Build the feature vector an Experimental-dataset model expects, from
    a live buffer of recent raw readings for one asset.

    No stage-2 filtering or EWMA smoothing applies here (this dataset has no
    RTU_STG_STA column - see ml/src/features/build_experimental_features.py).
    Weather-residualization is only applied for models whose metadata
    includes "weather_regression_models" - the econ_setpoint_too_low model
    uses raw features directly (see model_registry.py).

    Args:
        buffer: Recent raw readings, sorted ascending by Datetime.
        metadata: The model's loaded metadata.json content.
        occu_mod_col: Occupancy-mode indicator column. If absent from the
            buffer, the whole buffer is used unfiltered (callers passing
            already-occupied-filtered data can omit this column).

    Returns:
        A pandas Series indexed by metadata["feature_cols"].

    Raises:
        ValueError: if occu_mod_col is present but no occupied rows exist
            in the buffer.
    """
    if occu_mod_col in buffer.columns:
        occupied = buffer[buffer[occu_mod_col] == 1]
        if occupied.empty:
            raise ValueError("No occupied-mode rows in buffer - cannot score this asset right now.")
    else:
        occupied = buffer

    latest = occupied.iloc[-1]
    weather_models = metadata.get("weather_regression_models", {})

    features = {}
    for feature_col in metadata["feature_cols"]:
        if feature_col in weather_models:
            coefs = weather_models[feature_col]
            features[feature_col] = _apply_saved_residual(
                raw_value=latest[feature_col],
                weather_value=latest[coefs["weather_col"]],
                coefs=coefs,
            )
        elif feature_col.endswith("_residual"):
            raw_col = feature_col.removesuffix("_residual")
            coefs = weather_models[raw_col]
            features[feature_col] = _apply_saved_residual(
                raw_value=latest[raw_col],
                weather_value=latest[coefs["weather_col"]],
                coefs=coefs,
            )
        else:
            features[feature_col] = latest[feature_col]

    return pd.Series(features)


def build_live_features(buffer: pd.DataFrame, metadata: dict) -> pd.Series:
    """Dispatch to the correct live-feature builder based on the model's
    saved "dataset" field. See build_live_simulated_features() and
    build_live_experimental_features() for details."""
    dataset = metadata.get("dataset")
    if dataset == "simulated":
        return build_live_simulated_features(buffer, metadata)
    if dataset == "experimental":
        return build_live_experimental_features(buffer, metadata)
    raise ValueError(
        f"Unknown dataset type in metadata: {dataset!r} - expected 'simulated' or 'experimental'."
    )
