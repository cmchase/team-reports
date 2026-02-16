"""
Engine tests: stable IDs, week boundaries, business-day duration,
partial refresh semantics, schema sanity.
"""

import json
import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from team_reports.engine.ids import stable_artifact_id
from team_reports.engine.time_rules import (
    get_week_range_for_date,
    get_weeks_in_range,
    business_days_between,
    weekday_from_name,
    DEFAULT_WEEK_START,
    DEFAULT_WEEK_END,
)
from team_reports.engine.models import (
    SourceStatus,
    SyncSummary,
    Warning,
    asdict_serializable,
)
from team_reports.engine.dataset_writer import write_dataset, SCHEMA_VERSION, dataset_dir
from team_reports.engine.state import load_engine_state, save_engine_state, get_source_state


# ---- Stable ID determinism ----
class TestStableIdDeterminism:
    """Same external artifact must yield same id across calls."""

    def test_same_input_same_id(self):
        a = stable_artifact_id("jira", "default-jira", "PROJ-123")
        b = stable_artifact_id("jira", "default-jira", "PROJ-123")
        assert a == b

    def test_different_instance_different_id(self):
        a = stable_artifact_id("jira", "instance-a", "PROJ-1")
        b = stable_artifact_id("jira", "instance-b", "PROJ-1")
        assert a != b

    def test_different_source_type_different_id(self):
        a = stable_artifact_id("jira", "default", "123")
        b = stable_artifact_id("github", "default", "123")
        assert a != b

    def test_id_is_sha256_hex(self):
        sid = stable_artifact_id("github", "org", "42")
        assert len(sid) == 64
        assert all(c in "0123456789abcdef" for c in sid)


# ---- Week boundary correctness ----
class TestWeekBoundary:
    """Week boundary Wed-Tue and other boundaries."""

    def test_wed_tue_week_containing_wednesday(self):
        # 2025-01-15 is Wednesday
        start, end = get_week_range_for_date("2025-01-15", "WEDNESDAY", "TUESDAY")
        assert start == "2025-01-15"
        assert end == "2025-01-21"

    def test_wed_tue_week_containing_sunday(self):
        # 2025-01-12 is Sunday -> belongs to week Wed 2025-01-08 to Tue 2025-01-14
        start, end = get_week_range_for_date("2025-01-12", "WEDNESDAY", "TUESDAY")
        assert start == "2025-01-08"
        assert end == "2025-01-14"

    def test_monday_sunday_week(self):
        start, end = get_week_range_for_date("2025-01-15", "MONDAY", "SUNDAY")
        # 2025-01-15 is Wednesday -> week Mon 13 to Sun 19
        assert start == "2025-01-13"
        assert end == "2025-01-19"

    def test_weeks_in_range_wed_tue(self):
        time_rules = {"week_boundary_start_day": "WEDNESDAY", "week_boundary_end_day": "TUESDAY"}
        weeks = get_weeks_in_range("2025-01-08", "2025-01-28", time_rules)
        assert len(weeks) >= 2
        # First week should include 2025-01-08
        jan8 = date(2025, 1, 8)
        assert weeks[0][0] <= jan8
        assert weeks[0][1] >= jan8

    def test_weekday_from_name(self):
        assert weekday_from_name("MONDAY") == 0
        assert weekday_from_name("SUNDAY") == 6
        assert weekday_from_name("WEDNESDAY") == 2
        with pytest.raises(ValueError):
            weekday_from_name("INVALID")


# ---- Business-day duration ----
class TestBusinessDayDuration:
    """Durations exclude weekends when business_day_mode is weekday_only."""

    def test_business_days_monday_friday(self):
        n = business_days_between("2025-01-06", "2025-01-10")  # Mon-Fri
        assert n == 5

    def test_business_days_includes_weekend_skips_sat_sun(self):
        n = business_days_between("2025-01-06", "2025-01-12")  # Mon-Sun
        assert n == 5

    def test_business_days_single_day(self):
        n = business_days_between("2025-01-08", "2025-01-08")  # Wednesday
        assert n == 1


# ---- Partial refresh writes dataset + meta ----
class TestPartialRefreshWritesDataset:
    """When some sources fail, dataset_latest.json and meta are still written with partial flags."""

    def test_write_dataset_with_partial_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync_summary = SyncSummary(
                generated_at="2025-01-15T12:00:00Z",
                sources=[
                    SourceStatus("jira", "default-jira", "ok"),
                    SourceStatus("github", "default-github", "error", error_message="rate limit"),
                ],
                warnings=[Warning("github_error", "rate limit", "high", scope="github")],
            )
            dataset_path, meta_path, _ = write_dataset(
                out_dir=tmp,
                team_id="test-team",
                requested_start="2025-01-01",
                requested_end="2025-01-07",
                effective_start="2025-01-01",
                effective_end="2025-01-07",
                buffer_days=0,
                safety_margin_hours=24,
                time_rules={"team_timezone": "UTC", "week_boundary_start_day": "WEDNESDAY", "week_boundary_end_day": "TUESDAY"},
                status="partial",
                partial=True,
                sync_summary=sync_summary,
                weekly_snapshots=[],
                artifacts={"jira_issues": [], "github_pull_requests": [], "github_commits": [], "github_reviews": [], "gitlab_merge_requests": [], "gitlab_commits": [], "gitlab_issues": []},
                contributors=[],
                computed_contributor_summaries=[],
            )
            assert Path(dataset_path).exists()
            assert Path(meta_path).exists()
            with open(dataset_path) as f:
                d = json.load(f)
            assert d["status"] == "partial"
            assert d["partial"] is True
            assert len(d["sync_summary"]["sources"]) == 2
            with open(meta_path) as f:
                m = json.load(f)
            assert "sources" in m
            assert any(s.get("status") == "error" for s in m["sources"])


# ---- Schema sanity ----
class TestSchemaSanity:
    """dataset_latest.json has required keys and schema_version 1.0."""

    def test_dataset_has_required_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync_summary = SyncSummary(
                generated_at="2025-01-15T12:00:00Z",
                sources=[],
                warnings=[],
            )
            dataset_path, _, _ = write_dataset(
                out_dir=tmp,
                team_id="test-team",
                requested_start="2025-01-01",
                requested_end="2025-01-07",
                effective_start="2025-01-01",
                effective_end="2025-01-07",
                buffer_days=0,
                safety_margin_hours=24,
                time_rules={},
                status="ok",
                partial=False,
                sync_summary=sync_summary,
                weekly_snapshots=[],
                artifacts={
                    "jira_issues": [],
                    "github_pull_requests": [],
                    "github_commits": [],
                    "github_reviews": [],
                    "gitlab_merge_requests": [],
                    "gitlab_commits": [],
                    "gitlab_issues": [],
                },
                contributors=[],
                computed_contributor_summaries=[],
            )
            with open(dataset_path) as f:
                d = json.load(f)
            required = [
                "schema_version",
                "team_id",
                "requested_range",
                "effective_sync_window",
                "time_rules",
                "status",
                "partial",
                "sync_summary",
                "weekly_snapshots",
                "artifacts",
                "contributors",
                "computed_contributor_summaries",
            ]
            for key in required:
                assert key in d, f"Missing key: {key}"
            assert d["schema_version"] == "1.0"
            assert "jira_issues" in d["artifacts"]
            assert "github_pull_requests" in d["artifacts"]
            assert "gitlab_merge_requests" in d["artifacts"]

    def test_required_fields_non_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync_summary = SyncSummary(
                generated_at="2025-01-15T12:00:00Z",
                sources=[],
                warnings=[],
            )
            dataset_path, _, _ = write_dataset(
                out_dir=tmp,
                team_id="t",
                requested_start="2025-01-01",
                requested_end="2025-01-07",
                effective_start="2025-01-01",
                effective_end="2025-01-07",
                buffer_days=0,
                safety_margin_hours=24,
                time_rules={},
                status="ok",
                partial=False,
                sync_summary=sync_summary,
                weekly_snapshots=[],
                artifacts={
                    "jira_issues": [],
                    "github_pull_requests": [],
                    "github_commits": [],
                    "github_reviews": [],
                    "gitlab_merge_requests": [],
                    "gitlab_commits": [],
                    "gitlab_issues": [],
                },
                contributors=[],
                computed_contributor_summaries=[],
            )
            with open(dataset_path) as f:
                d = json.load(f)
            assert d["schema_version"] is not None
            assert d["team_id"] is not None
            assert d["requested_range"] is not None
            assert d["status"] is not None
            assert isinstance(d["partial"], bool)


# ---- Engine state ----
class TestEngineState:
    """engine_state.json is per team and stores per-source state."""

    def test_save_and_load_engine_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_engine_state(tmp, "team-1", {"jira:default-jira": {"last_successful_sync_at": "2025-01-15T12:00:00Z"}})
            loaded = load_engine_state(tmp, "team-1")
            assert "jira:default-jira" in loaded
            assert loaded["jira:default-jira"]["last_successful_sync_at"] == "2025-01-15T12:00:00Z"

    def test_get_source_state_creates_entry(self):
        state = {}
        get_source_state(state, "github", "default-github")
        assert "github:default-github" in state
