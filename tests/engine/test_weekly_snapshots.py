"""
Tests for weekly snapshot computation: normalized fields only, counts in correct week bucket.
Uses time_rules (timezone + week boundaries) and date-based bucketing.
"""

from team_reports.engine.time_rules import (
    get_weeks_in_range,
    iso_to_local_date,
    is_date_in_week,
)


def _default_time_rules(team_timezone: str = "UTC"):
    return {
        "team_timezone": team_timezone,
        "week_boundary_start_day": "WEDNESDAY",
        "week_boundary_end_day": "TUESDAY",
    }


def _compute_weekly_snapshots(
    artifacts: dict,
    range_start: str,
    range_end: str,
    time_rules: dict | None = None,
) -> list:
    """Replicate api.py snapshot logic: normalized fields + iso_to_local_date + is_date_in_week."""
    tr = time_rules or _default_time_rules()
    tz = tr.get("team_timezone", "UTC")
    weeks = get_weeks_in_range(range_start, range_end, tr)
    snapshots = []
    for week_start_d, week_end_d in weeks:
        snap = {
            "week_start": week_start_d.strftime("%Y-%m-%d"),
            "week_end": week_end_d.strftime("%Y-%m-%d"),
            "jira_count": 0,
            "github_pr_count": 0,
            "github_commit_count": 0,
            "gitlab_mr_count": 0,
            "gitlab_commit_count": 0,
            "gitlab_issue_count": 0,
        }
        for art in artifacts.get("jira_issues", []):
            ts = art.get("resolved_at") or art.get("updated_at") or ""
            local_d = iso_to_local_date(ts, tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["jira_count"] += 1
        for art in artifacts.get("github_pull_requests", []):
            local_d = iso_to_local_date(art.get("merged_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["github_pr_count"] += 1
        for art in artifacts.get("github_commits", []):
            local_d = iso_to_local_date(art.get("authored_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["github_commit_count"] += 1
        for art in artifacts.get("gitlab_merge_requests", []):
            local_d = iso_to_local_date(art.get("merged_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_mr_count"] += 1
        for art in artifacts.get("gitlab_commits", []):
            local_d = iso_to_local_date(art.get("authored_at") or "", tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_commit_count"] += 1
        for art in artifacts.get("gitlab_issues", []):
            ts = art.get("updated_at") or art.get("created_at") or ""
            local_d = iso_to_local_date(ts, tz)
            if local_d and is_date_in_week(local_d, week_start_d, week_end_d):
                snap["gitlab_issue_count"] += 1
        snapshots.append(snap)
    return snapshots


class TestWeeklySnapshotsNormalizedFields:
    """Counts land in correct week bucket using normalized timestamps only."""

    def test_jira_resolutiondate_in_week(self):
        # Wed 2026-02-04 to Tue 2026-02-10 (snapshots use normalized keys resolved_at/updated_at)
        artifacts = {
            "jira_issues": [
                {"resolved_at": "2026-02-05T14:00:00Z", "updated_at": "2026-02-05T12:00:00Z"},
                {"resolved_at": "2026-02-09T10:00:00+00:00", "updated_at": "2026-02-08T00:00:00Z"},
                {"updated_at": "2026-02-15T00:00:00Z"},  # no resolved_at, falls in next week
            ],
            "github_pull_requests": [],
            "github_commits": [],
            "gitlab_merge_requests": [],
            "gitlab_commits": [],
            "gitlab_issues": [],
        }
        snaps = _compute_weekly_snapshots(artifacts, "2026-02-04", "2026-02-10")
        assert len(snaps) >= 1
        first = snaps[0]
        assert first["week_start"] <= "2026-02-10" and first["week_end"] >= "2026-02-04"
        # First two issues in week 2026-02-04..2026-02-10 (Wed-Tue); third is 2026-02-15 (next week)
        assert first["jira_count"] == 2

    def test_github_pr_merged_at_bucketed(self):
        artifacts = {
            "jira_issues": [],
            "github_pull_requests": [
                {"merged_at": "2026-02-01T12:00:00Z"},
                {"merged_at": "2026-02-01T23:59:59+00:00"},
            ],
            "github_commits": [],
            "gitlab_merge_requests": [],
            "gitlab_commits": [],
            "gitlab_issues": [],
        }
        snaps = _compute_weekly_snapshots(artifacts, "2026-01-28", "2026-02-04")
        # Week containing 2026-02-01 is Wed 2026-01-28 to Tue 2026-02-03; 2026-02-01 is in that week
        found = next((s for s in snaps if s["week_start"] == "2026-01-28" and s["week_end"] == "2026-02-03"), None)
        assert found is not None
        assert found["github_pr_count"] == 2

    def test_artifact_without_date_not_counted(self):
        artifacts = {
            "jira_issues": [{"resolved_at": None, "updated_at": None}],
            "github_pull_requests": [],
            "github_commits": [],
            "gitlab_merge_requests": [],
            "gitlab_commits": [],
            "gitlab_issues": [],
        }
        snaps = _compute_weekly_snapshots(artifacts, "2026-02-04", "2026-02-10")
        assert len(snaps) >= 1
        assert snaps[0]["jira_count"] == 0

    def test_weekly_snapshots_use_normalized_timestamp_keys(self):
        """Snapshots bucket using only normalized keys: resolved_at/updated_at (Jira), authored_at (commits)."""
        artifacts = {
            "jira_issues": [
                {"resolved_at": "2026-02-05T12:00:00Z", "updated_at": "2026-02-05T12:00:00Z"},
            ],
            "github_pull_requests": [],
            "github_commits": [
                {"authored_at": "2026-02-06T10:00:00Z"},
                {"authored_at": "2026-02-07T10:00:00Z"},
            ],
            "gitlab_merge_requests": [],
            "gitlab_commits": [
                {"authored_at": "2026-02-08T10:00:00Z"},
            ],
            "gitlab_issues": [],
        }
        snaps = _compute_weekly_snapshots(artifacts, "2026-02-04", "2026-02-10")
        assert len(snaps) >= 1
        first = snaps[0]
        assert first["jira_count"] == 1
        assert first["github_commit_count"] == 2
        assert first["gitlab_commit_count"] == 1


class TestWeeklySnapshotReferencesAndHighlights:
    """Snapshot references contain only artifact ids and match counts; highlights present."""

    def test_weekly_snapshot_references_contain_artifact_ids_and_match_counts(self):
        """After refresh, snapshot references list only artifact ids and lengths match counts."""
        import json
        from pathlib import Path
        from unittest.mock import patch
        import tempfile

        from team_reports.engine.models import RefreshRequest, RefreshOptions, SourceStatus
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                "base_jql: 'project = T'\ncontributors: []\nteam_members: {}\n",
                encoding="utf-8",
            )
            with patch("team_reports.engine.api.collect") as mock_collect:
                raw_jira_1 = {
                    "key": "T-1",
                    "issue_id": "1",
                    "fields": {"assignee": None, "reporter": None, "updated": "2026-02-05T12:00:00Z", "resolutiondate": "2026-02-05T12:00:00Z", "status": {"name": "Done"}},
                    "summary": "One",
                    "status": "Done",
                    "updated": "2026-02-05T12:00:00Z",
                    "resolutiondate": "2026-02-05T12:00:00Z",
                    "assignee": None,
                    "reporter": None,
                }
                raw_jira_2 = {
                    "key": "T-2",
                    "issue_id": "2",
                    "fields": {"assignee": None, "reporter": None, "updated": "2026-02-06T12:00:00Z", "resolutiondate": "2026-02-06T12:00:00Z", "status": {"name": "Done"}},
                    "summary": "Two",
                    "status": "Done",
                    "updated": "2026-02-06T12:00:00Z",
                    "resolutiondate": "2026-02-06T12:00:00Z",
                    "assignee": None,
                    "reporter": None,
                }
                mock_collect.collect_jira.return_value = (
                    [raw_jira_1, raw_jira_2],
                    SourceStatus("jira", "default-jira", "ok"),
                )
                mock_collect.collect_github.return_value = (
                    {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                    SourceStatus("github", "default-github", "ok"),
                )
                mock_collect.collect_gitlab.return_value = (
                    {"merge_requests": [], "commits": [], "issues": []},
                    SourceStatus("gitlab", "default-gitlab", "ok"),
                )
                result = refresh(RefreshRequest(config_path=str(config_path), team_id="t", start="2026-02-01", end="2026-02-15", options=RefreshOptions(out_dir=tmp)))
                assert result.dataset_path and Path(result.dataset_path).exists()
                with open(result.dataset_path) as f:
                    dataset = json.load(f)
                snaps = dataset.get("weekly_snapshots", [])
                assert len(snaps) >= 1
                # Issues are resolved 2026-02-05 and 2026-02-06 (week Wed 2026-02-04 - Tue 2026-02-10)
                snap = next((s for s in snaps if s.get("week_start") == "2026-02-04" and s.get("week_end") == "2026-02-10"), snaps[0])
                assert "references" in snap
                refs = snap["references"]
                assert "jira_issue_ids" in refs
                assert snap["jira_count"] == 2
                assert len(refs["jira_issue_ids"]) == 2
                all_jira_ids = {a["id"] for a in dataset["artifacts"]["jira_issues"]}
                for rid in refs["jira_issue_ids"]:
                    assert rid in all_jira_ids
                assert "partial" in snap
                assert "highlights" in snap
                assert len(snap["highlights"]) <= 5
                assert any("2" in h and "Jira" in h for h in snap["highlights"])
                assert "threshold_flags" in snap
                for ref_list in refs.values():
                    assert len(ref_list) <= 500
                    for rid in ref_list:
                        assert isinstance(rid, str)

    def test_weekly_snapshot_highlights_deterministic_and_capped(self):
        """Highlights reflect counts and are capped at 5."""
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from team_reports.engine.models import RefreshRequest, RefreshOptions, SourceStatus
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: 'x'\ncontributors: []\nteam_members: {}\n", encoding="utf-8")
            with patch("team_reports.engine.api.collect") as mock_collect:
                mock_collect.collect_jira.return_value = ([], SourceStatus("jira", "default-jira", "ok"))
                mock_collect.collect_github.return_value = (
                    {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                    SourceStatus("github", "default-github", "ok"),
                )
                mock_collect.collect_gitlab.return_value = (
                    {"merge_requests": [], "commits": [], "issues": []},
                    SourceStatus("gitlab", "default-gitlab", "ok"),
                )
                result = refresh(RefreshRequest(config_path=str(config_path), team_id="t", start="2026-02-01", end="2026-02-15", options=RefreshOptions(out_dir=tmp)))
                with open(result.dataset_path) as f:
                    dataset = json.load(f)
                for snap in dataset.get("weekly_snapshots", []):
                    assert "highlights" in snap
                    assert len(snap["highlights"]) <= 5
                    for h in snap["highlights"]:
                        assert isinstance(h, str)

    def test_threshold_flags_fire_in_synthetic_scenario(self):
        """threshold_flags: no_activity, no_prs_merged, spike_prs fire when conditions met."""
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from team_reports.engine.models import RefreshRequest, RefreshOptions, SourceStatus
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: 'x'\ncontributors: []\nteam_members: {}\n", encoding="utf-8")
            with patch("team_reports.engine.api.collect") as mock_collect:
                # Week 1: 1 PR merged (2026-02-05). Week 2: 3 PRs (spike). Also one week with 0 activity.
                mock_collect.collect_jira.return_value = ([], SourceStatus("jira", "default-jira", "ok"))
                mock_collect.collect_github.return_value = (
                    {
                        "pull_requests": [
                            {"repository": "r", "number": 1, "node_id": "n1", "merged_at": "2026-02-05T12:00:00Z", "user": {}},
                            {"repository": "r", "number": 2, "node_id": "n2", "merged_at": "2026-02-12T12:00:00Z", "user": {}},
                            {"repository": "r", "number": 3, "node_id": "n3", "merged_at": "2026-02-13T12:00:00Z", "user": {}},
                            {"repository": "r", "number": 4, "node_id": "n4", "merged_at": "2026-02-14T12:00:00Z", "user": {}},
                        ],
                        "commits": [
                            {"repository": "r", "sha": "a", "commit": {"message": "m", "author": {"date": "2026-02-12T12:00:00Z"}}, "author": {"login": "x"}},
                        ],
                        "issues": [],
                        "reviews": [],
                    },
                    SourceStatus("github", "default-github", "ok"),
                )
                mock_collect.collect_gitlab.return_value = (
                    {"merge_requests": [], "commits": [], "issues": []},
                    SourceStatus("gitlab", "default-gitlab", "ok"),
                )
                result = refresh(RefreshRequest(config_path=str(config_path), team_id="t", start="2026-02-01", end="2026-02-28", options=RefreshOptions(out_dir=tmp)))
                with open(result.dataset_path) as f:
                    dataset = json.load(f)
                snaps = dataset.get("weekly_snapshots", [])
                codes = []
                for s in snaps:
                    for f in s.get("threshold_flags", []):
                        codes.append(f["code"])
                assert "no_activity" in codes or "no_prs_merged" in codes or "spike_prs" in codes
                snap_with_flags = next((s for s in snaps if s.get("threshold_flags")), None)
                assert snap_with_flags is not None
                for f in snap_with_flags["threshold_flags"]:
                    assert f.get("code") and f.get("severity") in ("low", "medium", "high") and f.get("message")

    def test_partial_propagates_to_snapshots(self):
        """When overall refresh is partial, every snapshot has partial=true."""
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from team_reports.engine.models import RefreshRequest, RefreshOptions, SourceStatus
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: 'x'\ncontributors: []\nteam_members: {}\n", encoding="utf-8")
            with patch("team_reports.engine.api.collect") as mock_collect:
                mock_collect.collect_jira.return_value = ([], SourceStatus("jira", "default-jira", "ok"))
                mock_collect.collect_github.return_value = (
                    {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                    SourceStatus("github", "default-github", "partial", error_message="rate limit"),
                )
                mock_collect.collect_gitlab.return_value = (
                    {"merge_requests": [], "commits": [], "issues": []},
                    SourceStatus("gitlab", "default-gitlab", "ok"),
                )
                result = refresh(RefreshRequest(config_path=str(config_path), team_id="t", start="2026-02-01", end="2026-02-15", options=RefreshOptions(out_dir=tmp)))
                assert result.partial is True
                with open(result.dataset_path) as f:
                    dataset = json.load(f)
                for snap in dataset.get("weekly_snapshots", []):
                    assert snap.get("partial") is True
