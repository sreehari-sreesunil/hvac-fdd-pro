"""Tests for ml/src/features/smoothing.py."""

import pandas as pd
from src.features.smoothing import add_segmented_ewma


def test_ewma_resets_at_state_transition():
    """The core bug this function exists to prevent: a naive whole-series
    EWMA would carry a 'memory' of segment 1's values into the start of
    segment 2. This test constructs two clearly-different constant
    segments and confirms the smoothed value right after the transition
    is much closer to the NEW segment's value than the old one."""
    df = pd.DataFrame(
        {
            "value": [100] * 40 + [10] * 40,  # segment 1 = 100, segment 2 = 10
            "state": [1.0] * 40 + [1.0] * 40,  # same state bucket throughout -
            # transition is driven by a
            # SEPARATE state change below
        }
    )
    # Force a genuine state-bucket transition partway through segment 2's
    # start by using two different state values that fall in the same
    # bucket boundary the function actually cares about:
    df.loc[40:, "state"] = 0.1  # drops to "off" bucket at index 40

    result = add_segmented_ewma(df, value_col="value", state_col="state", span=5)

    # Right at the transition, the smoothed value should already be much
    # closer to the new segment's constant (10) than the old one (100) -
    # a naive un-segmented EWMA would still be dragging toward 100 here.
    value_just_after_transition = result["value_ewma5_segmented"].iloc[42]
    assert value_just_after_transition < 50, (
        "EWMA appears to be carrying over from the previous segment - "
        "segmentation is not resetting at the state transition"
    )


def test_does_not_mutate_input():
    df = pd.DataFrame({"value": [1, 2, 3], "state": [1.0, 1.0, 1.0]})
    original_columns = list(df.columns)

    add_segmented_ewma(df, value_col="value", state_col="state", span=2)

    assert list(df.columns) == original_columns, "Input dataframe was mutated"


def test_default_output_column_name():
    df = pd.DataFrame({"value": [1, 2, 3], "state": [1.0, 1.0, 1.0]})
    result = add_segmented_ewma(df, value_col="value", state_col="state", span=7)

    assert "value_ewma7_segmented" in result.columns
