"""Re-validates the frozen baseline design using WEATHER-RESIDUALIZED
pressure, not raw pressure - the first validation used raw
RTU_REFG_COND_PRES directly, inconsistent with every other model in this
project, which treats weather-residualization as essential (RTU_OA_TEMP
explains 77-99% of baseline-condition variance for these exact columns).
If the severity gradient found earlier doesn't survive residualization,
it may have been a weather confound, not genuine fault signal.
"""


from src.features.build_features import build_feature_table

K_STD = 3.0

# Baseline-only table, to fit the frozen reference on RESIDUALIZED data.
baseline_table = build_feature_table(
    baseline_path="data/raw/RTU_sim_baseline.csv",
    fault_paths={},
    pressure_temp_cols=("RTU_REFG_COND_PRES",),
)
residual_col = "RTU_REFG_COND_PRES_residual"
frozen_mean = baseline_table[residual_col].mean()
frozen_std = baseline_table[residual_col].std()
print(
    f"Frozen reference (residualized): mean={frozen_mean:.2f}, std={frozen_std:.2f}, from {len(baseline_table)} rows"
)

baseline_z = (baseline_table[residual_col] - frozen_mean) / frozen_std
print(f"\nBaseline itself, deviation rate: {(baseline_z.abs() > K_STD).mean():.4f}")

print("\nCondenser fouling severity progression (residualized):")
for severity in ["10", "20", "30", "40", "50"]:
    fault_table = build_feature_table(
        baseline_path="data/raw/RTU_sim_baseline.csv",
        fault_paths={f"condfouling{severity}": f"data/raw/RTU_sim_condfouling{severity}.csv"},
        pressure_temp_cols=("RTU_REFG_COND_PRES",),
    )
    fault_rows = fault_table[fault_table["label"] == 1]
    z = (fault_rows[residual_col] - frozen_mean) / frozen_std
    print(
        f"  condfouling{severity}: deviation rate={(z.abs() > K_STD).mean():.4f}  n_rows={len(fault_rows)}"
    )
