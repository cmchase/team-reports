"""
Tests for engine normalization: stable IDs, last_seen_at, required fields.
"""

import pytest

from team_reports.engine.normalize import (
    stable_id,
    normalize_jira_issue,
    normalize_github_pr,
    normalize_github_commit,
    normalize_github_review,
    normalize_github_issue,
    normalize_gitlab_mr,
    normalize_gitlab_issue,
    normalize_gitlab_commit,
)


REQUIRED = {"id", "source_type", "instance_id", "last_seen_at"}


class TestStableIdDeterminism:
    """Same external id + same instance -> same stable id."""

    def test_same_input_same_id(self):
        a = stable_id("jira", "default-jira", "PROJ-123")
        b = stable_id("jira", "default-jira", "PROJ-123")
        assert a == b

    def test_different_instance_different_id(self):
        a = stable_id("github", "org-a", "42")
        b = stable_id("github", "org-b", "42")
        assert a != b

    def test_different_external_different_id(self):
        a = stable_id("gitlab", "gl", "proj:1")
        b = stable_id("gitlab", "gl", "proj:2")
        assert a != b


class TestLastSeenAtEqualsGeneratedAt:
    """last_seen_at on every normalized artifact equals generated_at."""

    @pytest.fixture
    def generated_at(self):
        return "2025-01-15T12:00:00Z"

    def test_jira(self, generated_at):
        raw = {"key": "PROJ-1", "summary": "x"}
        out = normalize_jira_issue(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_github_pr(self, generated_at):
        raw = {"repository": "r", "number": 1, "title": "y"}
        out = normalize_github_pr(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_github_commit(self, generated_at):
        raw = {"repository": "r", "sha": "abc123"}
        out = normalize_github_commit(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_github_review(self, generated_at):
        raw = {"repository": "r", "number": 1, "id": 99}
        out = normalize_github_review(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_gitlab_mr(self, generated_at):
        raw = {"project": "p", "iid": 2, "title": "z"}
        out = normalize_gitlab_mr(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_gitlab_issue(self, generated_at):
        raw = {"project": "p", "iid": 3}
        out = normalize_gitlab_issue(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at

    def test_gitlab_commit(self, generated_at):
        raw = {"project": "p", "sha": "def456"}
        out = normalize_gitlab_commit(raw, "inst", generated_at)
        assert out["last_seen_at"] == generated_at


class TestRequiredFieldsAllArtifactTypes:
    """Every normalized artifact has id, source_type, instance_id, last_seen_at."""

    def _assert_required(self, out):
        for k in REQUIRED:
            assert k in out, f"missing {k}"
            assert out[k] is not None and out[k] != ""

    def test_jira_issue(self):
        out = normalize_jira_issue({"key": "X-1"}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_github_pr(self):
        out = normalize_github_pr({"repository": "r", "number": 1}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_github_commit(self):
        out = normalize_github_commit({"repository": "r", "sha": "abc"}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_github_review(self):
        out = normalize_github_review({"repository": "r", "number": 1, "id": 1}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_github_issue(self):
        out = normalize_github_issue({"repository": "r", "number": 2}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_gitlab_mr(self):
        out = normalize_gitlab_mr({"project": "p", "iid": 1}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_gitlab_issue(self):
        out = normalize_gitlab_issue({"project": "p", "iid": 2}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)

    def test_gitlab_commit(self):
        out = normalize_gitlab_commit({"project": "p", "sha": "def"}, "inst", "2025-01-01T00:00:00Z")
        self._assert_required(out)
