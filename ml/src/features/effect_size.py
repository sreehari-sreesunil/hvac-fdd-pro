"""Feature engineering: effect-size utilities for comparing fault severities.

Derived from EDA in ml/notebooks/01_eda_undercharge.ipynb: raw visual
comparisons of histograms/means can be misleading in both directions (an
overlapping-looking histogram can hide a real, large effect; a clean-looking
monotonic table can hide a near-zero difference between adjacent severities).
Cohen's d gives a real, comparable number instead of an eyeballed impression.
"""

import pandas as pd
from numpy import mean, std


def cohens_d(a: pd.Series, b: pd.Series) -> float:
    """Compute Cohen's d effect size between two samples.

    Uses the pooled standard deviation. Convention: |d| < 0.2 negligible,
    ~0.2-0.5 small, ~0.5-0.8 medium, > 0.8 large.

    Args:
        a: First sample (e.g. one fault severity's values for a column).
        b: Second sample (e.g. a different fault severity, or baseline).

    Returns:
        Cohen's d as a float. Sign indicates direction (mean(a) - mean(b)).
    """
    n_a, n_b = len(a), len(b)
    pooled_std = (
        ((n_a - 1) * std(a, ddof=1) ** 2 + (n_b - 1) * std(b, ddof=1) ** 2) / (n_a + n_b - 2)
    ) ** 0.5
    return (mean(a) - mean(b)) / pooled_std
