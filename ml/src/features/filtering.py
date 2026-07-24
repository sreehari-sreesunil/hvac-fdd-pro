"""Feature engineering: compressor-operating-state filtering.

Derived from EDA in ml/notebooks/03_eda_condenser_fouling.ipynb: raw,
unfiltered means of RTU_TOT_CAPA (and similar signals) can be muted or
distorted by blending together off / stage-1 / stage-2 operation. Isolating
stage-2-only rows removes that blending and reveals a cleaner fault signal
in several faults examined so far (undercharge, overcharge).
"""

import pandas as pd


def stage2_only(df: pd.DataFrame, stage_col: str = "RTU_STG_STA") -> pd.DataFrame:
    """Filter a telemetry dataframe to compressor stage-2 rows only.

    Uses the same stage bucketing established in notebook 01 (off <0.3,
    stage1 0.3-0.9, stage2 >0.9) to isolate steady, full-capacity operation
    from the noisier off/staging-transition periods that can blend into and
    mute or distort a fault's true signal in a raw, unfiltered mean.

    Args:
        df: A single fault-severity telemetry dataframe.
        stage_col: Column holding the compressor stage indicator.

    Returns:
        A copy containing only rows where the unit is in stage 2.
    """
    return df[df[stage_col] > 0.9].copy()
