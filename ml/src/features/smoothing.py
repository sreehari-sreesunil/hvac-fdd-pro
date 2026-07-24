"""Feature engineering: rolling/EWMA smoothing that respects operating-state
transitions.

Derived from EDA in ml/notebooks/01_eda_undercharge.ipynb (Step 6c):
naively applying EWMA across an entire time series blends genuinely
different compressor operating states together, which manufactures noise
rather than removing it. Segmenting by contiguous same-state runs first
fixes this - confirmed empirically: effect size improved from 1.44 (raw)
to 1.59 (segmented EWMA), vs. 0.33 (naive, un-segmented EWMA making
things actively worse).
"""

import pandas as pd


def add_segmented_ewma(
    df: pd.DataFrame,
    value_col: str,
    state_col: str,
    span: int = 30,
    state_bins: tuple[float, ...] = (-0.01, 0.3, 1.01),
    output_col: str | None = None,
) -> pd.DataFrame:
    """Add an EWMA-smoothed column that resets whenever `state_col` changes
    operating bucket, instead of smoothing blindly across the whole series.

    Args:
        df: Input dataframe, must contain value_col and state_col.
        value_col: Column to smooth (e.g. "RTU_TOT_CAPA").
        state_col: Column defining operating state (e.g. "RTU_STG_STA").
        span: EWMA span - see pandas .ewm(span=...) docs. Default 30
            matches the value validated in the undercharge EDA notebook
            for 1-minute-sampled RTU data; revisit if sampling rate or
            system dynamics differ.
        state_bins: Boundaries used to collapse a continuous state_col
            into discrete buckets before detecting transitions. Default
            splits into off / stage1 / stage2, matching RTU_STG_STA's
            observed values (~0.1 off, ~0.67 stage1, ~1.0 stage2).
        output_col: Name for the new column. Defaults to
            f"{value_col}_ewma{span}_segmented".

    Returns:
        A copy of df with the new smoothed column added. Does not
        mutate the input dataframe.
    """

    df = df.copy()
    output_col = output_col or f"{value_col}_ewma{span}_segmented"

    state_bucket = pd.cut(df[state_col], bins=list(state_bins))
    run_id = (state_bucket != state_bucket.shift()).cumsum()

    df[output_col] = df.groupby(run_id)[value_col].transform(lambda s: s.ewm(span=span).mean())
    return df
