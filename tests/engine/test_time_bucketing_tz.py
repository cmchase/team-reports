"""
Timezone-aware week bucketing: local date conversion and Wed–Tue boundaries.
"""

from datetime import date

import pytest

from team_reports.engine.time_rules import (
    get_weeks_in_range,
    iso_to_local_date,
    is_date_in_week,
)


# ---- iso_to_local_date ----
class TestIsoToLocalDate:
    """Convert ISO timestamps to local date in team_timezone."""

    def test_midnight_utc_in_america_new_york_is_previous_day(self):
        # 2026-02-01 00:30 UTC = 2026-01-31 19:30 EST (New York, no DST in Jan/Feb)
        result = iso_to_local_date("2026-02-01T00:30:00Z", "America/New_York")
        assert result == date(2026, 1, 31)

    def test_date_only_treated_as_local(self):
        result = iso_to_local_date("2026-02-15", "America/New_York")
        assert result == date(2026, 2, 15)

    def test_utc_unchanged_for_utc_zone(self):
        result = iso_to_local_date("2026-02-01T00:30:00Z", "UTC")
        assert result == date(2026, 2, 1)

    def test_invalid_returns_none(self):
        assert iso_to_local_date("", "UTC") is None
        assert iso_to_local_date("not-a-date", "UTC") is None


# ---- get_weeks_in_range Wed–Tue ----
class TestWeeksInRangeWedTue:
    """Week windows use configured boundary days and cover the range."""

    def test_wed_tue_windows_cover_range(self):
        time_rules = {
            "week_boundary_start_day": "WEDNESDAY",
            "week_boundary_end_day": "TUESDAY",
        }
        weeks = get_weeks_in_range("2026-02-01", "2026-02-15", time_rules)
        assert len(weeks) >= 1
        for week_start, week_end in weeks:
            assert week_start <= week_end
        # At least one full Wed–Tue window: Wed=2, Tue=1
        full_weeks = [(ws, we) for ws, we in weeks if ws.weekday() == 2 and we.weekday() == 1]
        assert len(full_weeks) >= 1, "expected at least one window to start Wednesday and end Tuesday"
        # Full range [2026-02-01, 2026-02-15] is covered
        min_start = min(ws for ws, _ in weeks)
        max_end = max(we for _, we in weeks)
        assert min_start <= date(2026, 2, 1)
        assert max_end >= date(2026, 2, 15)

    def test_deterministic_ordering(self):
        time_rules = {"week_boundary_start_day": "WEDNESDAY", "week_boundary_end_day": "TUESDAY"}
        weeks = get_weeks_in_range("2026-02-01", "2026-02-15", time_rules)
        for i in range(len(weeks)):
            assert weeks[i][0] <= weeks[i][1]
        for i in range(len(weeks) - 1):
            assert weeks[i][0] <= weeks[i + 1][0]


# ---- Bucketing: Tuesday night local -> correct Wed–Tue week ----
class TestBucketingTuesdayNightLocal:
    """Artifact with timestamp on Tuesday night (local) buckets into that Wed–Tue week."""

    def test_tuesday_night_local_bucketed_into_that_week(self):
        # Tue 2026-02-03 23:00 America/New_York = Wed 2026-02-04 04:00 UTC
        # So in UTC the timestamp is 2026-02-04; in New York it's still 2026-02-03 (Tuesday).
        # Week Wed 2026-01-28 – Tue 2026-02-03 should contain this artifact.
        time_rules = {
            "team_timezone": "America/New_York",
            "week_boundary_start_day": "WEDNESDAY",
            "week_boundary_end_day": "TUESDAY",
        }
        tz = time_rules["team_timezone"]
        weeks = get_weeks_in_range("2026-01-28", "2026-02-10", time_rules)
        # Find the week that ends on Tue 2026-02-03
        week_jan28_feb3 = next((w for w in weeks if w[1] == date(2026, 2, 3)), None)
        assert week_jan28_feb3 is not None
        week_start, week_end = week_jan28_feb3
        # Tuesday night in NY: 2026-02-03 23:00 EST = 2026-02-04 04:00 UTC
        ts_utc = "2026-02-04T04:00:00Z"
        local_d = iso_to_local_date(ts_utc, tz)
        assert local_d == date(2026, 2, 3)
        assert is_date_in_week(local_d, week_start, week_end)
        # Same artifact must not be in the following week (Wed 2026-02-04 – Tue 2026-02-10)
        week_feb4_feb10 = next((w for w in weeks if w[0] == date(2026, 2, 4)), None)
        if week_feb4_feb10:
            assert not is_date_in_week(local_d, week_feb4_feb10[0], week_feb4_feb10[1])
