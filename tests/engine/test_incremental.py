"""
Tests for incremental refresh: updated_since, cold start, overlap dedup.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from team_reports.engine.models import RefreshOptions, RefreshRequest, SourceStatus


class TestIncrementalRefresh:
    """Incremental mode uses engine_state and passes updated_since/cursor to collectors."""

    def test_incremental_uses_updated_since_when_state_present(self):
        """When engine_state has last_successful_sync_at for a source, collector is called with updated_since."""
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: project = X\n")
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()

            minimal_config = {"base_jql": "project = X", "jira": {}, "github": {}, "gitlab": {}}

            # State with prior successful Jira sync
            engine_state = {
                "jira:default-jira": {
                    "last_successful_sync_at": "2026-01-10T12:00:00Z",
                    "last_attempt_at": "2026-01-10T12:00:00Z",
                    "cursor": {},
                    "last_error": None,
                    "last_mode": "incremental",
                },
            }
            with patch("team_reports.utils.config.get_config", return_value=minimal_config):
                with patch("team_reports.engine.api.load_engine_state", return_value=engine_state):
                    with patch("team_reports.engine.api.collect.collect_jira", return_value=([], SourceStatus("jira", "default-jira", "ok", cursor={}))) as m_jira:
                        with patch("team_reports.engine.api.collect.collect_github", return_value=(
                            {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                            SourceStatus("github", "default-github", "ok", cursor={}),
                        )):
                            with patch("team_reports.engine.api.collect.collect_gitlab", return_value=(
                                {"merge_requests": [], "commits": [], "issues": []},
                                SourceStatus("gitlab", "default-gitlab", "ok", cursor={}),
                            )):
                                with patch("team_reports.engine.api.write_dataset", return_value=("/p/d.json", "/p/m.json", "/p/ts.json")):
                                    with patch("team_reports.engine.api.save_engine_state"):
                                        refresh(
                                            RefreshRequest(
                                                config_path=str(config_path),
                                                team_id="t",
                                                start="2026-01-13",
                                                end="2026-01-19",
                                                options=RefreshOptions(out_dir=str(out_dir), mode="incremental", safety_margin_hours=24),
                                            )
                                        )
            # Jira collector called with updated_since (last_successful_sync_at - 24h)
            m_jira.assert_called_once()
            call_kw = m_jira.call_args[1]
            assert "updated_since" in call_kw
            assert call_kw["updated_since"] is not None
            assert "2026-01-09" in call_kw["updated_since"]  # 24h before 2026-01-10T12

    def test_incremental_cold_start_falls_back_to_full(self):
        """When no prior state exists, incremental runs full fetch and emits incremental_cold_start warning."""
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: project = X\n")
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()

            minimal_config = {"base_jql": "project = X", "jira": {}, "github": {}, "gitlab": {}}
            with patch("team_reports.utils.config.get_config", return_value=minimal_config):
                with patch("team_reports.engine.api.load_engine_state", return_value={}):
                    with patch("team_reports.engine.api.collect.collect_jira", return_value=([], SourceStatus("jira", "default-jira", "ok", cursor={}))):
                        with patch("team_reports.engine.api.collect.collect_github", return_value=(
                            {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                            SourceStatus("github", "default-github", "ok", cursor={}),
                        )):
                            with patch("team_reports.engine.api.collect.collect_gitlab", return_value=(
                                {"merge_requests": [], "commits": [], "issues": []},
                                SourceStatus("gitlab", "default-gitlab", "ok", cursor={}),
                            )):
                                with patch("team_reports.engine.api.write_dataset", return_value=("/p/d.json", "/p/m.json", "/p/ts.json")):
                                    with patch("team_reports.engine.api.save_engine_state"):
                                        result = refresh(
                                            RefreshRequest(
                                                config_path=str(config_path),
                                                team_id="t",
                                                start="2026-01-13",
                                                end="2026-01-19",
                                                options=RefreshOptions(out_dir=str(out_dir), mode="incremental"),
                                            )
                                        )
            cold = [w for w in result.sync_summary.warnings if w.code == "incremental_cold_start"]
            assert len(cold) >= 1
            assert any(w.scope in ("jira", "github", "gitlab") for w in cold)

    def test_overlap_dedup_does_not_duplicate_artifacts(self):
        """Same stable id appearing twice in normalized artifacts yields one artifact after dedup."""
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text("base_jql: project = X\n")
            out_dir = Path(tmp) / "out"
            out_dir.mkdir()

            # Raw that normalizes to same id (same key)
            raw_issue = {"key": "X-1", "issue_id": "100", "fields": {}, "summary": "x", "status": "Done", "updated": "2026-01-15T00:00:00Z", "resolutiondate": "2026-01-15"}

            captured_artifacts = {}

            def capture_write_dataset(*args, **kwargs):
                captured_artifacts["artifacts"] = {k: list(v) for k, v in kwargs.get("artifacts", {}).items()}
                return "/fake/dataset.json", "/fake/meta.json", "/fake/ts.json"

            minimal_config = {"base_jql": "project = X", "jira": {}, "github": {}, "gitlab": {}}
            with patch("team_reports.utils.config.get_config", return_value=minimal_config):
                with patch("team_reports.engine.api.collect.collect_jira", return_value=(
                    [raw_issue, dict(raw_issue)],
                    SourceStatus("jira", "default-jira", "ok", cursor={}),
                )):
                    with patch("team_reports.engine.api.collect.collect_github", return_value=(
                        {"pull_requests": [], "commits": [], "issues": [], "reviews": []},
                        SourceStatus("github", "default-github", "ok", cursor={}),
                    )):
                        with patch("team_reports.engine.api.collect.collect_gitlab", return_value=(
                            {"merge_requests": [], "commits": [], "issues": []},
                            SourceStatus("gitlab", "default-gitlab", "ok", cursor={}),
                        )):
                            with patch("team_reports.engine.api.write_dataset", side_effect=capture_write_dataset):
                                with patch("team_reports.engine.api.save_engine_state"):
                                    refresh(
                                        RefreshRequest(
                                            config_path=str(config_path),
                                            team_id="t",
                                            start="2026-01-13",
                                            end="2026-01-19",
                                            options=RefreshOptions(out_dir=str(out_dir)),
                                        )
                                    )
            jira_arts = captured_artifacts.get("artifacts", {}).get("jira_issues", [])
            ids = [a.get("id") for a in jira_arts if a.get("id")]
            assert len(ids) == len(set(ids)), "duplicate ids in jira_issues"
            assert len(jira_arts) == 1, "same id should dedupe to one artifact"
