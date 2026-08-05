"""Tests for resolve_report_period.

These formalize the same checks that were run manually (as a throwaway
script) before this function was wired into the report endpoint - see
the commit history / build log for that manual verification. Kept as
real pytest here so CI catches a regression automatically, instead of
relying on someone re-running a script by hand.
"""

from datetime import datetime

import pytest
from fastapi import HTTPException

from app.services.report_period import resolve_report_period


def test_daily_period_is_one_calendar_day_with_exclusive_end():
    """A daily report for 2026-08-05 must cover exactly that day, and
    must NOT include a reading timestamped at the start of the next
    day - end has to be exclusive, not inclusive."""
    start, end = resolve_report_period("daily", "2026-08-05")
    assert start == datetime(2026, 8, 5, 0, 0, 0)
    assert end == datetime(2026, 8, 6, 0, 0, 0)


def test_weekly_period_is_seven_days_ending_on_the_anchor_date():
    """Weekly means "the 7 days ending on the anchor date", not a
    Monday-Sunday calendar week - this was an explicit product decision
    made when the endpoint was scoped, not an assumption."""
    start, end = resolve_report_period("weekly", "2026-08-05")
    assert start == datetime(2026, 7, 30, 0, 0, 0)
    assert end == datetime(2026, 8, 6, 0, 0, 0)
    assert (end - start).days == 7


def test_monthly_period_is_the_full_calendar_month():
    start, end = resolve_report_period("monthly", "2026-08-05")
    assert start == datetime(2026, 8, 1, 0, 0, 0)
    assert end == datetime(2026, 9, 1, 0, 0, 0)


def test_monthly_period_handles_december_to_january_rollover():
    """The trickiest case - a naive start.replace(month=start.month + 1)
    would raise ValueError on a December anchor, since month=13 doesn't
    exist. This must roll over into January of the NEXT year instead."""
    start, end = resolve_report_period("monthly", "2026-12-15")
    assert start == datetime(2026, 12, 1, 0, 0, 0)
    assert end == datetime(2027, 1, 1, 0, 0, 0)


def test_daily_period_handles_end_of_february_in_a_non_leap_year():
    """2026 is not a leap year - Feb 28 -> Mar 1 the next day, not
    Feb 29 (which doesn't exist in 2026)."""
    start, end = resolve_report_period("daily", "2026-02-28")
    assert start == datetime(2026, 2, 28, 0, 0, 0)
    assert end == datetime(2026, 3, 1, 0, 0, 0)


def test_missing_date_defaults_to_today():
    start, _ = resolve_report_period("daily", None)
    assert start.date() == datetime.utcnow().date()


def test_malformed_date_raises_a_clean_400_not_a_stack_trace():
    with pytest.raises(HTTPException) as exc_info:
        resolve_report_period("daily", "not-a-date")
    assert exc_info.value.status_code == 400
    assert "not-a-date" in exc_info.value.detail
