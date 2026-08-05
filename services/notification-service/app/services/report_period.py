"""Resolves a report period ("daily"/"weekly"/"monthly") plus an anchor
date into a concrete [start, end) datetime window.

Kept as a small, pure function (no DB, no HTTP) deliberately - the
date-window math is the one part of the report endpoint worth being able
to reason about and test in isolation, separate from the alert-querying
and asset-service-calling logic that surrounds it.
"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status

ReportPeriod = Literal["daily", "weekly", "monthly"]


def resolve_report_period(period: ReportPeriod, date_str: str | None) -> tuple[datetime, datetime]:
    """Turn a period + anchor date into a concrete [start, end) window.

    Args:
        period: Already validated by FastAPI's Literal type on the
            endpoint itself - this function trusts it's one of the three
            known values and does not re-validate it.
        date_str: Optional "YYYY-MM-DD" anchor date. Defaults to today
            (UTC) if omitted, matching the endpoint's documented default
            behaviour ("if date is omitted, default to now").

    Returns:
        (start, end) - end is exclusive, so a query should filter
        created_at >= start AND created_at < end, never <= end. This
        matters most for "daily": a report for 2026-08-05 must not
        accidentally include a reading timestamped exactly at
        2026-08-06 00:00:00.

    Raises:
        HTTPException: 400 if date_str is present but not a valid
            "YYYY-MM-DD" date.
    """
    if date_str is None:
        anchor = datetime.utcnow().date()
    else:
        try:
            anchor = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date '{date_str}' - expected YYYY-MM-DD",
            ) from err

    anchor_start = datetime(anchor.year, anchor.month, anchor.day)

    if period == "daily":
        start = anchor_start
        end = start + timedelta(days=1)
    elif period == "weekly":
        # The 7-day window ENDING on the anchor date (inclusive of the
        # anchor day itself) - so start is 6 days before anchor, and end
        # is the day after anchor. This matches the product decision
        # made when this endpoint was scoped: "weekly = the 7-day window
        # ending on that date", not a Monday-Sunday calendar week.
        end = anchor_start + timedelta(days=1)
        start = end - timedelta(days=7)
    else:  # period == "monthly"
        start = datetime(anchor.year, anchor.month, 1)
        # First day of the NEXT month, handling the December -> January
        # rollover explicitly - "start.replace(month=start.month + 1)"
        # would raise ValueError on a December anchor (month=13 is
        # invalid), so the year/month rollover has to be done by hand
        # rather than relying on a single .replace() call.
        if start.month == 12:
            end = datetime(start.year + 1, 1, 1)
        else:
            end = datetime(start.year, start.month + 1, 1)

    return start, end
