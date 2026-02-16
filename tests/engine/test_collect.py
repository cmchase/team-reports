"""
Tests for engine collect: collectors return RAW only (no id, last_seen_at, source_type, instance_id on artifacts).
"""

from unittest.mock import MagicMock, patch

import pytest

from team_reports.engine import collect


def _no_engine_fields(items):
    """Assert no artifact in items has id or last_seen_at."""
    for item in items:
        assert isinstance(item, dict), "expected dict"
        assert "id" not in item, "collect must not return id (normalize adds it)"
        assert "last_seen_at" not in item, "collect must not return last_seen_at (normalize adds it)"
        assert "source_type" not in item, "collect must not return source_type"
        assert "instance_id" not in item, "collect must not return instance_id (only in SourceStatus)"


class TestCollectReturnsRawOnly:
    """Collect outputs do NOT contain id or last_seen_at."""

    @patch("team_reports.utils.jira.fetch_tickets")
    @patch("team_reports.utils.jira_client.JiraApiClient")
    def test_jira_collect_returns_raw_no_id_no_last_seen_at(self, mock_client_class, mock_fetch):
        mock_fetch.return_value = []
        with patch("team_reports.utils.config.get_config") as mock_config:
            mock_config.return_value = {"base_jql": "project = X", "report_settings": {}, "report": {}}
            raw_list, status = collect.collect_jira("config.yaml", "2025-01-01", "2025-01-07")
        _no_engine_fields(raw_list)
        assert status.instance_id  # instance_id only in SourceStatus

    @patch("team_reports.utils.jira.fetch_tickets")
    @patch("team_reports.utils.jira_client.JiraApiClient")
    def test_jira_collect_one_issue_raw_has_no_engine_fields(self, mock_client_class, mock_fetch):
        # One fake issue: object with key, id, raw, fields
        class FakeFields:
            summary = "Summary"
            updated = "2025-01-15T10:00:00.000+0000"
            resolutiondate = "2025-01-14T12:00:00.000+0000"
            status = MagicMock()
            assignee = None
            reporter = None
        status = MagicMock()
        status.name = "Done"
        FakeFields.status = status
        fake_issue = MagicMock()
        fake_issue.key = "PROJ-1"
        fake_issue.id = "12345"
        fake_issue.raw = {}
        fake_issue.fields = FakeFields()
        mock_fetch.return_value = [fake_issue]
        with patch("team_reports.utils.config.get_config") as mock_config:
            mock_config.return_value = {"base_jql": "project = X", "report_settings": {}, "report": {}}
            raw_list, _ = collect.collect_jira("config.yaml", "2025-01-01", "2025-01-07")
        assert len(raw_list) == 1
        _no_engine_fields(raw_list)
        assert raw_list[0].get("key") == "PROJ-1"
        assert raw_list[0].get("summary") == "Summary"

    @patch("team_reports.utils.github_client.GitHubApiClient")
    def test_github_collect_returns_raw_no_id_no_last_seen_at(self, mock_client_class):
        mock_client_class.return_value.fetch_all_data.return_value = {
            "pull_requests": {"org/repo": [{"number": 1, "node_id": "n", "title": "t", "state": "closed", "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-02T00:00:00Z", "merged_at": "2025-01-02T00:00:00Z", "html_url": "https://x", "user": {"login": "u"}}]},
            "commits": {"org/repo": [{"sha": "abc", "commit": {"message": "m", "author": {"date": "2025-01-01T00:00:00Z"}}, "html_url": "https://x", "author": {}}]},
            "issues": {},
        }
        with patch("team_reports.utils.config.get_config") as mock_config:
            mock_config.return_value = {"github_org": "org"}
            data, status = collect.collect_github("config.yaml", "2025-01-01", "2025-01-07")
        _no_engine_fields(data["pull_requests"])
        _no_engine_fields(data["commits"])
        _no_engine_fields(data["reviews"])
        assert status.instance_id

    @patch("team_reports.utils.gitlab_client.GitLabApiClient")
    def test_gitlab_collect_returns_raw_no_id_no_last_seen_at(self, mock_client_class):
        mock_client_class.return_value.fetch_all_data.return_value = {
            "pull_requests": {"group/proj": [{"number": 1, "iid": 1, "title": "t", "state": "merged", "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-02T00:00:00Z", "merged_at": "2025-01-02T00:00:00Z", "html_url": "https://x", "user": {"login": "u"}}]},
            "commits": {"group/proj": [{"sha": "def", "id": "def", "commit": {"message": "m", "author": {"date": "2025-01-01T00:00:00Z"}}, "html_url": "https://x"}]},
            "issues": {"group/proj": [{"number": 2, "iid": 2, "title": "i", "state": "closed", "created_at": "2025-01-01T00:00:00Z", "updated_at": "2025-01-02T00:00:00Z", "html_url": "https://x", "user": {}}]},
        }
        with patch("team_reports.utils.config.get_config") as mock_config:
            mock_config.return_value = {"base_url": "https://gitlab.com"}
            data, status = collect.collect_gitlab("config.yaml", "2025-01-01", "2025-01-07")
        _no_engine_fields(data["merge_requests"])
        _no_engine_fields(data["commits"])
        _no_engine_fields(data["issues"])
        assert status.instance_id
