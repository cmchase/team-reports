"""
Tests for engine API: Warning severity, status rollup, preview behavior.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from team_reports.engine.models import Warning, SourceStatus, SyncSummary


class TestWarningSeverityEnum:
    """Warning.severity accepts only low, medium, high."""

    def test_accepts_low_medium_high(self):
        Warning(code="a", message="b", severity="low")
        Warning(code="a", message="b", severity="medium")
        Warning(code="a", message="b", severity="high")

    def test_rejects_info(self):
        with pytest.raises(ValueError, match="severity must be one of"):
            Warning(code="a", message="b", severity="info")

    def test_rejects_error(self):
        with pytest.raises(ValueError, match="severity must be one of"):
            Warning(code="a", message="b", severity="error")

    def test_scope_optional(self):
        w = Warning(code="a", message="b", severity="low", scope="config")
        assert w.scope == "config"
        w2 = Warning(code="a", message="b", severity="low")
        assert w2.scope is None


class TestRefreshRollup:
    """Overall status rollup from source_statuses."""

    def _rollup(self, source_statuses):
        """Replicate refresh() rollup logic for testing."""
        if not source_statuses:
            return "error", True
        if all(s.status == "error" for s in source_statuses):
            return "error", True
        if any(s.status == "error" or s.status == "partial" for s in source_statuses):
            return "partial", True
        return "ok", False

    def test_rollup_error_when_no_sources_configured(self):
        status, partial = self._rollup([])
        assert status == "error"
        assert partial is True

    def test_rollup_error_when_all_sources_error(self):
        sources = [
            SourceStatus("jira", "j1", "error", error_message="e1"),
            SourceStatus("github", "g1", "error", error_message="e2"),
        ]
        status, partial = self._rollup(sources)
        assert status == "error"
        assert partial is True

    def test_rollup_partial_when_any_source_partial(self):
        sources = [
            SourceStatus("jira", "j1", "ok"),
            SourceStatus("github", "g1", "partial", error_message="rate limit"),
        ]
        status, partial = self._rollup(sources)
        assert status == "partial"
        assert partial is True

    def test_rollup_partial_when_any_source_error(self):
        sources = [
            SourceStatus("jira", "j1", "ok"),
            SourceStatus("github", "g1", "error", error_message="e"),
        ]
        status, partial = self._rollup(sources)
        assert status == "partial"
        assert partial is True

    def test_rollup_ok_when_all_ok(self):
        sources = [
            SourceStatus("jira", "j1", "ok"),
            SourceStatus("github", "g1", "ok"),
        ]
        status, partial = self._rollup(sources)
        assert status == "ok"
        assert partial is False

    def test_source_status_cursor_default_dict(self):
        s = SourceStatus("jira", "j1", "ok")
        assert s.cursor == {}
        assert isinstance(s.cursor, dict)


class TestPreviewNoSideEffects:
    """preview() must not write dataset or engine state."""

    def test_preview_does_not_write_files(self):
        """After preview(), write_dataset and engine_state are never called."""
        from team_reports.engine.api import preview
        from team_reports.engine.models import EstimatedCounts

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("base_jql: project = DEMO\n")
            config_path = f.name
        try:
            with patch("team_reports.engine.api.write_dataset") as m_write:
                with patch("team_reports.engine.api.load_engine_state") as m_load:
                    with patch("team_reports.engine.api.save_engine_state") as m_save:
                        with patch("team_reports.engine.preview.estimate_counts") as m_estimate:
                            m_estimate.return_value = (EstimatedCounts(), [])
                            preview(
                                config_path=config_path,
                                team_id="t",
                                start="2026-01-01",
                                end="2026-01-07",
                            )
            m_write.assert_not_called()
            m_load.assert_not_called()
            m_save.assert_not_called()
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_preview_returns_counts_when_clients_mocked(self):
        """With estimators mocked to return known counts, preview result matches."""
        from team_reports.engine.api import preview

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("base_jql: project = X\n")
            config_path = f.name
        try:
            with patch("team_reports.engine.preview.estimate_counts") as m_estimate:
                from team_reports.engine.models import EstimatedCounts

                m_estimate.return_value = (
                    EstimatedCounts(
                        jira_issues=5,
                        github_pull_requests=3,
                        github_commits=0,
                        github_reviews=0,
                        gitlab_merge_requests=2,
                        gitlab_issues=1,
                        gitlab_commits=10,
                    ),
                    [],
                )
                result = preview(
                    config_path=config_path,
                    team_id="t",
                    start="2026-01-01",
                    end="2026-01-07",
                )
            assert result.estimated_counts.jira_issues == 5
            assert result.estimated_counts.github_pull_requests == 3
            assert result.estimated_counts.github_commits == 0
            assert result.estimated_counts.gitlab_merge_requests == 2
            assert result.estimated_counts.gitlab_issues == 1
            assert result.estimated_counts.gitlab_commits == 10
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_preview_emits_warning_on_auth_failure(self):
        """When a source client raises (e.g. auth), preview emits a warning."""
        from team_reports.engine.api import preview

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("base_jql: project = X\n")
            config_path = f.name
        try:
            with patch("team_reports.utils.jira_client.JiraApiClient") as m_client:
                m_client.return_value.initialize.side_effect = Exception("Unauthorized (401)")
                result = preview(
                    config_path=config_path,
                    team_id="t",
                    start="2026-01-01",
                    end="2026-01-07",
                )
            jira_warnings = [w for w in result.warnings if w.scope == "jira"]
            assert any("unavailable" in w.message.lower() or "401" in w.message for w in jira_warnings)
        finally:
            Path(config_path).unlink(missing_ok=True)
