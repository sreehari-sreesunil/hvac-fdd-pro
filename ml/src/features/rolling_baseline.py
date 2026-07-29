"""Per-asset rolling baseline / adaptive thresholds.

Genuinely different mechanism from every other model in this project:
not a pre-trained classifier evaluated once against historical data, but
a live statistical computation that continuously adapts as a SPECIFIC
asset's own telemetry history accumulates. Two units of the same type can
have different "normal" operating ranges (install conditions, location,
calibration drift) - this catches "this specific unit just started
drifting from ITS OWN recent normal," independent of whether any
fault-specific classifier fires at all.

"Adaptive" means the baseline itself continuously shifts as new data
arrives (a rolling window), not a fixed threshold computed once and
frozen - unlike the trained classifiers/gatekeeper, this needs no
training phase at all.
"""

from __future__ import annotations

import pandas as pd


def compute_rolling_baseline(
    series: pd.Series,
    window: int,
    min_periods: int | None = None,
) -> tuple[pd.Series, pd.Series]:
    """Rolling mean and standard deviation over a trailing window.

    Args:
        series: Time-ordered readings for one asset+metric.
        window: Number of trailing readings to include.
        min_periods: Minimum readings required before producing a value
            (defaults to `window` - no baseline until the window fills,
            rather than an unstable early-window estimate).

    Returns:
        (rolling_mean, rolling_std) - both same length as `series`, with
        leading NaNs until `min_periods` is reached.
    """
    if min_periods is None:
        min_periods = window
    rolling = series.rolling(window=window, min_periods=min_periods)
    return rolling.mean(), rolling.std()


def flag_deviations(
    series: pd.Series,
    window: int,
    k_std: float = 3.0,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Flag readings that deviate more than k_std standard deviations from
    the rolling baseline AT THE TIME of that reading (the baseline for row
    i uses only rows before i, via pandas' rolling - never a future value,
    matching this project's standing discipline against any form of
    look-ahead).

    Returns a DataFrame with columns: value, rolling_mean, rolling_std,
    z_score, is_deviation.
    """
    rolling_mean, rolling_std = compute_rolling_baseline(series, window, min_periods)
    z_score = (series - rolling_mean) / rolling_std
    is_deviation = z_score.abs() > k_std

    return pd.DataFrame(
        {
            "value": series,
            "rolling_mean": rolling_mean,
            "rolling_std": rolling_std,
            "z_score": z_score,
            "is_deviation": is_deviation.fillna(False),
        }
    )
