"""Feature engineering: build labeled feature tables for the Experimental
(ORNL) RTU dataset.

Kept separate from ml/src/features/build_features.py (the Simulated-dataset
equivalent) because the two datasets require genuinely different handling,
established across ml/notebooks/07-10:

- No RTU_STG_STA compressor-stage column exists in this dataset (it tracks
  two physically separate compressors via RTU_COMP_WATT_1/2 instead of one
  staged compressor) - stage2_only() does not apply here.
- The documented "NAN" sentinel string must be passed to na_values
  explicitly, or pandas silently misreads it as text (see notebook 07).
- Season is the dominant confound here, not raw weather - notebook 07 found
  baseline itself varies substantially by season (driven by the documented
  OA-temperature-dependent economizer control logic). The fix established
  is within-season comparison, NOT weather-residualization: every file is
  only ~1-2 days, so residualizing against weather the way
  build_feature_table() does for the 100-day Simulated files is not
  meaningful here.
- Each file already represents a single season/fault/severity combination -
  there is no single continuous time series to split by date the way the
  Simulated dataset's TimeSeriesSplit evaluation worked. Cross-season
  generalization (train on one season, evaluate on another) is the
  season-dataset analog of that forward-in-time evaluation.
"""

from pathlib import Path

import pandas as pd


def build_experimental_feature_table(
    baseline_path: str | Path,
    fault_paths: dict[str, str | Path],
    feature_cols: tuple[str, ...],
    occupied_only: bool = True,
    occu_mod_col: str = "OCCU_MOD",
) -> pd.DataFrame:
    """Build a labeled feature table from Experimental-dataset CSV files.

    Loads a baseline file and one or more fault-severity files (all from
    the SAME season - this function does not pool across seasons, since
    notebook 07 established that pooling is unsafe), applies the na_values
    fix for the documented "NAN" sentinel, converts Datetime, and
    optionally filters to occupied-mode rows only.

    Args:
        baseline_path: Path to that season's unfaulted baseline CSV.
        fault_paths: Mapping of label -> path, one entry per fault-severity
            CSV for the SAME season as baseline_path. All severities are
            pooled under label=1 (binary detection, not per-severity
            classification, matching the Simulated-dataset templates).
        feature_cols: Columns to retain as model features. Callers should
            choose these per-fault based on that fault's own EDA notebook
            (e.g. RTU_OA_DMPR_DM for OA damper stuck - see notebook 08).
        occupied_only: If True (default), filter to OCCU_MOD == 1 rows only.
            Most EDA findings in notebooks 08-10 were established on
            occupied-mode data; set False only if a specific analysis
            needs unoccupied-mode rows too.
        occu_mod_col: Column holding the occupancy-mode indicator.

    Returns:
        A single concatenated, sorted-by-Datetime DataFrame with columns:
        Datetime, one column per entry in feature_cols, label (0=baseline,
        1=any fault), and source_file (which input file each row came from).
    """
    files = {"baseline": baseline_path, **fault_paths}
    dfs = {label: pd.read_csv(path, na_values=["NAN"]) for label, path in files.items()}

    for df in dfs.values():
        df["Datetime"] = pd.to_datetime(df["Datetime"])

    labeled_dfs = []
    for label, df in dfs.items():
        subset = df
        if occupied_only:
            subset = subset[subset[occu_mod_col] == 1]
        subset = subset[["Datetime", *feature_cols]].copy()
        subset["label"] = 0 if label == "baseline" else 1
        subset["source_file"] = label
        labeled_dfs.append(subset)

    return pd.concat(labeled_dfs, ignore_index=True).sort_values("Datetime").reset_index(drop=True)
