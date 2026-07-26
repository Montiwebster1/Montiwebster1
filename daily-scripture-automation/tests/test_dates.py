from datetime import date, datetime
from zoneinfo import ZoneInfo

from daily_scripture.dates import today_in_chicago


def test_utc_evening_is_still_same_day_in_chicago():
    # 11:30 PM UTC on July 26 = 6:30 PM CDT on July 26 (not yet the next day).
    now = datetime(2026, 7, 26, 23, 30, tzinfo=ZoneInfo("UTC"))
    assert today_in_chicago(now) == date(2026, 7, 26)


def test_near_midnight_utc_rolls_to_next_day_in_chicago():
    # 4:30 AM UTC on July 27 = 11:30 PM CDT on July 26 — still July 26 in Chicago.
    now = datetime(2026, 7, 27, 4, 30, tzinfo=ZoneInfo("UTC"))
    assert today_in_chicago(now) == date(2026, 7, 26)


def test_just_after_5am_chicago_boundary():
    # 10:00 AM UTC = 5:00 AM CDT (summer, UTC-5) on the same calendar day.
    now = datetime(2026, 7, 26, 10, 0, tzinfo=ZoneInfo("UTC"))
    assert today_in_chicago(now) == date(2026, 7, 26)


def test_dst_spring_forward_boundary_2027():
    # DST starts 2027-03-14 in the US. Just before, CST is UTC-6.
    before = datetime(2027, 3, 14, 7, 59, tzinfo=ZoneInfo("UTC"))  # 1:59 AM CST
    after = datetime(2027, 3, 14, 9, 1, tzinfo=ZoneInfo("UTC"))  # 4:01 AM CDT
    assert today_in_chicago(before) == date(2027, 3, 14)
    assert today_in_chicago(after) == date(2027, 3, 14)


def test_dst_fall_back_boundary_2026():
    # DST ends 2026-11-01 in the US. 5:00 AM CST the next morning must still
    # compute correctly relative to the UTC instant.
    ten_am_utc = datetime(2026, 11, 2, 11, 0, tzinfo=ZoneInfo("UTC"))  # 5:00 AM CST
    assert today_in_chicago(ten_am_utc) == date(2026, 11, 2)


def test_naive_datetime_rejected():
    import pytest

    with pytest.raises(ValueError):
        today_in_chicago(datetime(2026, 7, 26))
