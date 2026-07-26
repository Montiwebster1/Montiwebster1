"""Timezone-safe date selection for America/Chicago, DST-aware."""
from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

CENTRAL_TZ = ZoneInfo("America/Chicago")


def today_in_chicago(now_utc: datetime | None = None) -> date:
    """Return today's calendar date in America/Chicago.

    Correct across the DST boundary because ZoneInfo resolves the UTC
    offset (CST -06:00 / CDT -05:00) for the instant given, rather than
    using a fixed offset.
    """
    now = now_utc or datetime.now(tz=ZoneInfo("UTC"))
    if now.tzinfo is None:
        raise ValueError("now_utc must be timezone-aware")
    return now.astimezone(CENTRAL_TZ).date()
