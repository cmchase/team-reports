"""
Tests for canonical contributor model and identity resolution.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from team_reports.engine import identity
from team_reports.engine.models import RefreshRequest, Warning


# ---- config contributors[] produces stable ids ----
class TestConfigContributorsStableIds:
    """contributors[] in config produces deterministic contributor ids."""

    def test_canonical_contributors_deterministic_ids(self):
        config = {
            "contributors": [
                {"id": "cory", "display_name": "Cory Chase", "jira_emails": ["cory@company.com"], "github_logins": ["cmchase"], "gitlab_usernames": ["cmchase"]},
                {"id": "alice", "display_name": "Alice Dev", "jira_emails": ["alice@company.com"], "github_logins": ["alice"], "gitlab_usernames": []},
            ],
        }
        contribs1, _, _ = identity.parse_contributors_from_config(config)
        contribs2, _, _ = identity.parse_contributors_from_config(config)
        assert len(contribs1) == 2
        assert [c["id"] for c in contribs1] == [c["id"] for c in contribs2]
        assert contribs1[0]["id"] == "contributor:cory"
        assert contribs1[0]["display_name"] == "Cory Chase"
        assert contribs1[0]["identities"]["jira_emails"] == ["cory@company.com"]
        assert contribs1[0]["identities"]["github_logins"] == ["cmchase"]
        assert contribs1[0]["identities"]["gitlab_usernames"] == ["cmchase"]

    def test_id_from_slug_when_no_id_given(self):
        config = {
            "contributors": [
                {"display_name": "Bob Smith", "jira_emails": ["bob@co.com"]},
            ],
        }
        contribs, _, _ = identity.parse_contributors_from_config(config)
        assert len(contribs) == 1
        assert contribs[0]["id"].startswith("contributor:")
        assert "bob" in contribs[0]["id"].lower() or contribs[0]["id"] == "contributor:bob-smith"

    def test_canonical_duplicate_contributor_ids_are_deterministic(self):
        """Same contributor entries in different order yield same ids (suffix from content hash)."""
        config_a = {
            "contributors": [
                {"id": "alice", "display_name": "Alice", "jira_emails": ["a@x.com"]},
                {"id": "alice", "display_name": "Alice", "jira_emails": ["a2@x.com"]},
            ],
        }
        config_b = {
            "contributors": [
                {"id": "alice", "display_name": "Alice", "jira_emails": ["a2@x.com"]},
                {"id": "alice", "display_name": "Alice", "jira_emails": ["a@x.com"]},
            ],
        }
        contribs_a, _, _ = identity.parse_contributors_from_config(config_a)
        contribs_b, _, _ = identity.parse_contributors_from_config(config_b)
        assert len(contribs_a) == 2
        assert len(contribs_b) == 2
        ids_a = {c["id"] for c in contribs_a}
        ids_b = {c["id"] for c in contribs_b}
        assert ids_a == ids_b


# ---- identity index resolves jira/github/gitlab ----
class TestIdentityIndexResolves:
    """build_identity_index and resolve_contributor_id resolve identities correctly."""

    def test_index_resolves_jira_github_gitlab(self):
        contributors = [
            {
                "id": "contributor:cory",
                "display_name": "Cory",
                "identities": {
                    "jira_emails": ["cory@company.com"],
                    "github_logins": ["cmchase"],
                    "gitlab_usernames": ["cmchase"],
                },
            },
        ]
        index = identity.build_identity_index(contributors)
        assert index.get(("jira", "cory@company.com")) == "contributor:cory"
        assert index.get(("github", "cmchase")) == "contributor:cory"
        assert index.get(("gitlab", "cmchase")) == "contributor:cory"

    def test_resolve_contributor_id_returns_none_for_unmapped(self):
        index = identity.build_identity_index([{"id": "c1", "identities": {"jira_emails": ["a@x.com"]}}])
        assert identity.resolve_contributor_id("jira", "other@x.com", index) is None
        assert identity.resolve_contributor_id("github", "unknown", index) is None
        assert identity.resolve_contributor_id("jira", None, index) is None


# ---- artifacts get contributor_id when identity matches ----
class TestArtifactsGetContributorId:
    """Artifacts receive contributor_id when identity matches index."""

    def test_resolution_sets_contributor_id_when_matched(self):
        contributors = [
            {"id": "contributor:alice", "display_name": "Alice", "identities": {"jira_emails": ["alice@co.com"], "github_logins": ["alice"], "gitlab_usernames": ["alice"]}},
        ]
        index = identity.build_identity_index(contributors)
        # Simulate artifact resolution
        art_jira = {"assignee_email": "alice@co.com"}
        art_github_pr = {"pr_author_login": "alice"}
        art_gitlab = {"author_username": "alice"}
        cid_j = identity.resolve_contributor_id("jira", art_jira.get("assignee_email"), index)
        cid_gh = identity.resolve_contributor_id("github", art_github_pr.get("pr_author_login"), index)
        cid_gl = identity.resolve_contributor_id("gitlab", art_gitlab.get("author_username"), index)
        assert cid_j == "contributor:alice"
        assert cid_gh == "contributor:alice"
        assert cid_gl == "contributor:alice"


# ---- unmapped identities create Warning ----
class TestUnmappedIdentityWarning:
    """Unmapped identities produce Warning with code unmapped_identity."""

    def test_unmapped_identity_warning_in_sync_summary(self):
        """Refresh with artifacts whose author is not in config produces unmapped_identity warning."""
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "test_identity_config.yaml"
            config_path.write_text(
                "base_jql: 'project = TEST'\ncontributors: []\nteam_members: {}\n",
                encoding="utf-8",
            )
            with patch("team_reports.engine.api.collect") as mock_collect:
                from team_reports.engine.models import SourceStatus

                # One Jira issue with assignee not in config (raw shape from collect)
                raw_jira = {
                    "key": "T-1",
                    "issue_id": "10000",
                    "fields": {"assignee": "unknown@company.com", "reporter": None, "updated": "2025-01-01T00:00:00Z", "resolutiondate": None, "status": {"name": "Done"}},
                    "summary": "Test",
                    "status": "Done",
                    "updated": "2025-01-01T00:00:00Z",
                    "resolutiondate": None,
                    "assignee": "unknown@company.com",
                    "reporter": None,
                }
                mock_collect.collect_jira.return_value = (
                    [raw_jira],
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
                from team_reports.engine.api import refresh

                result = refresh(RefreshRequest(config_path=str(config_path), team_id="test", start="2025-01-01", end="2025-01-07"))
                unmapped_warnings = [w for w in result.sync_summary.warnings if w.code == "unmapped_identity"]
                assert len(unmapped_warnings) >= 1
                assert "Unmapped" in unmapped_warnings[0].message and "unknown@company.com" in unmapped_warnings[0].message
                assert unmapped_warnings[0].scope == "identity"

    def test_contributor_summary_counts_match_artifacts(self):
        """Computed contributor summaries count only artifacts with contributor_id set."""
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from team_reports.engine.models import RefreshRequest, RefreshOptions, SourceStatus
        from team_reports.engine.api import refresh

        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.yaml"
            config_path.write_text(
                "base_jql: 'project = T'\n"
                "contributors:\n"
                "  - id: alice\n"
                "    display_name: Alice\n"
                "    github_logins: [alice]\n"
                "team_members: {}\n",
                encoding="utf-8",
            )
            with patch("team_reports.engine.api.collect") as mock_collect:
                mock_collect.collect_jira.return_value = (
                    [],
                    SourceStatus("jira", "default-jira", "ok"),
                )
                mock_collect.collect_github.return_value = (
                    {
                        "pull_requests": [
                            {"repository": "r1", "number": 1, "node_id": "n1", "merged_at": "2026-02-05T12:00:00Z", "user": {"login": "alice"}},
                            {"repository": "r1", "number": 2, "node_id": "n2", "merged_at": "2026-02-06T12:00:00Z", "user": {"login": "alice"}},
                        ],
                        "commits": [
                            {"repository": "r1", "sha": "abc", "commit": {"message": "m", "author": {"date": "2026-02-07T12:00:00Z"}}, "author": {"login": "alice"}},
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
                result = refresh(RefreshRequest(config_path=str(config_path), team_id="t", start="2026-02-01", end="2026-02-15", options=RefreshOptions(out_dir=tmp)))
                with open(result.dataset_path) as f:
                    dataset = json.load(f)
                summaries = dataset.get("computed_contributor_summaries", [])
                alice = next((s for s in summaries if s["contributor_id"] == "contributor:alice"), None)
                assert alice is not None
                assert alice["github_pr_merged_count"] == 2
                assert alice["github_commit_count"] == 1
                assert alice["pr_count"] == 2
                assert alice["commit_count"] == 1
