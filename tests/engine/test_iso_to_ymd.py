"""
Tests for iso_to_ymd: ISO8601 and date-only parsing to YYYY-MM-DD.
"""

import pytest

from team_reports.engine.time_rules import iso_to_ymd


class TestIsoToYmd:
    def test_iso_z_suffix(self):
        assert iso_to_ymd("2026-02-01T00:30:00Z") == "2026-02-01"

    def test_iso_offset(self):
        assert iso_to_ymd("2026-02-01T00:30:00+00:00") == "2026-02-01"

    def test_date_only(self):
        assert iso_to_ymd("2026-02-01") == "2026-02-01"

    def test_invalid_returns_none(self):
        assert iso_to_ymd("not-a-date") is None
        assert iso_to_ymd("2026-13-01") is None  # invalid month
        assert iso_to_ymd("") is None
        assert iso_to_ymd("   ") is None

    def test_falsy_returns_none(self):
        assert iso_to_ymd("") is None
        assert iso_to_ymd(None) is None
