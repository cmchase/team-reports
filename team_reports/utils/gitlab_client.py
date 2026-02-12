#!/usr/bin/env python3
"""
GitLab API client for team reports.

Provides merge requests, commits, and issues from GitLab (including self-hosted
e.g. https://gitlab.cee.redhat.com) with a shape compatible with the summary reporting.
"""

import os
import urllib.parse
from datetime import datetime
from typing import Dict, List, Any, Optional

import requests
from dotenv import load_dotenv

from .config import get_config

load_dotenv()


class GitLabApiClient:
    """GitLab API client with pagination and normalized responses for reports."""

    def __init__(
        self,
        config_file: str = "config/gitlab_config.yaml",
        gitlab_token: Optional[str] = None,
    ):
        """
        Initialize the GitLab API client.

        Credential precedence: gitlab_token parameter > GITLAB_TOKEN env var.

        Args:
            config_file: Path to YAML configuration file.
            gitlab_token: Optional token (overrides environment).

        Raises:
            ValueError: If token is not provided.
        """
        self.gitlab_token = gitlab_token or os.getenv("GITLAB_TOKEN")
        if not self.gitlab_token:
            raise ValueError(
                "GitLab token required. Provide via gitlab_token parameter or "
                "GITLAB_TOKEN environment variable"
            )

        self.config = get_config([config_file])
        self.projects = self.config.get("projects", [])
        base = (self.config.get("base_url") or "https://gitlab.com").rstrip("/")
        self.base_url = f"{base}/api/v4"
        self.headers = {"PRIVATE-TOKEN": self.gitlab_token}

    def _project_id_param(self, project: str) -> str:
        """Return project identifier for API (URL-encoded path)."""
        return urllib.parse.quote(project, safe="")

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> List[Dict]:
        """Make a GET request with pagination (page, per_page)."""
        url = f"{self.base_url}/{endpoint}"
        all_data = []
        page = 1
        per_page = 100

        while True:
            request_params = {"page": page, "per_page": per_page}
            if params:
                request_params.update(params)

            response = requests.get(url, headers=self.headers, params=request_params)
            response.raise_for_status()

            data = response.json()
            if not data:
                break

            all_data.extend(data)
            page += 1
            if len(data) < per_page:
                break

        return all_data

    def _normalize_mr(self, mr: Dict, project_path: str) -> Dict:
        """Normalize a merge request to a GitHub-like shape for summary code."""
        author = mr.get("author") or {}
        username = author.get("username") or "unknown"
        return {
            "number": mr.get("iid"),
            "title": mr.get("title", ""),
            "state": mr.get("state", ""),
            "created_at": mr.get("created_at", ""),
            "updated_at": mr.get("updated_at", ""),
            "merged_at": mr.get("merged_at"),
            "html_url": mr.get("web_url", ""),
            "user": {"login": username},
            "body": mr.get("description") or "",
            "additions": mr.get("additions", 0) or 0,
            "deletions": mr.get("deletions", 0) or 0,
            "changed_files": mr.get("changes_count", 0) or 0,
            "repo": project_path,
        }

    def _normalize_commit(self, commit: Dict, project_path: str) -> Dict:
        """Normalize a commit to a GitHub-like shape. GitLab list returns id, author_name, message, created_at, web_url."""
        author = commit.get("author")
        if isinstance(author, dict):
            author_login = author.get("username") or author.get("name") or "unknown"
            author_name = author.get("name")
        else:
            author_login = commit.get("author_name") or commit.get("author_email") or "unknown"
            author_name = commit.get("author_name")

        author_date = commit.get("created_at") or ""
        if not author_date and isinstance(author, dict):
            author_date = (commit.get("commit") or {}).get("author", {}).get("date", "")
        message = commit.get("message") or commit.get("title") or ""

        return {
            "sha": commit.get("id") or commit.get("short_id", ""),
            "html_url": commit.get("web_url", ""),
            "commit": {
                "message": message,
                "author": {"date": author_date, "name": author_name},
            },
            "author": {"login": author_login, "name": author_name},
            "repo": project_path,
        }

    def _normalize_issue(self, issue: Dict, project_path: str) -> Dict:
        """Normalize an issue to a GitHub-like shape."""
        user = issue.get("author") or {}
        username = user.get("username") if isinstance(user, dict) else "unknown"
        return {
            "number": issue.get("iid"),
            "title": issue.get("title", ""),
            "state": issue.get("state", ""),
            "created_at": issue.get("created_at", ""),
            "updated_at": issue.get("updated_at", ""),
            "html_url": issue.get("web_url", ""),
            "user": {"login": username},
            "repo": project_path,
        }

    def fetch_merge_requests(
        self, project: str, start_date: str, end_date: str
    ) -> List[Dict]:
        """Fetch merge requests merged in the date range."""
        print(f"  Fetching merge requests for {project} from {start_date} to {end_date}...")
        proj_id = self._project_id_param(project)
        endpoint = f"projects/{proj_id}/merge_requests"
        params = {
            "state": "all",
            "order_by": "updated_at",
            "sort": "desc",
            "per_page": 100,
        }
        mrs = self._make_request(endpoint, params)

        start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        normalized = []
        for mr in mrs:
            merged_at = mr.get("merged_at")
            if not merged_at:
                continue
            merged_dt = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            )
            if not (start_dt <= merged_dt <= end_dt):
                continue
            normalized.append(self._normalize_mr(mr, project))
        return normalized

    def fetch_commits(self, project: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch commits in the date range."""
        print(f"  Fetching commits for {project} from {start_date} to {end_date}...")
        proj_id = self._project_id_param(project)
        endpoint = f"projects/{proj_id}/repository/commits"
        params = {
            "since": f"{start_date}T00:00:00Z",
            "until": f"{end_date}T23:59:59Z",
            "with_stats": "true",
        }
        commits = self._make_request(endpoint, params)
        return [self._normalize_commit(c, project) for c in commits]

    def fetch_issues(self, project: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch issues updated in the date range."""
        print(f"  Fetching issues for {project} from {start_date} to {end_date}...")
        proj_id = self._project_id_param(project)
        endpoint = f"projects/{proj_id}/issues"
        params = {
            "state": "all",
            "order_by": "updated_at",
            "sort": "desc",
            "per_page": 100,
        }
        issues = self._make_request(endpoint, params)
        start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
        end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
        normalized = []
        for issue in issues:
            updated_at = issue.get("updated_at")
            if not updated_at:
                continue
            updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            if not (start_dt <= updated_dt <= end_dt):
                continue
            normalized.append(self._normalize_issue(issue, project))
        return normalized

    def fetch_all_data(
        self, start_date: str, end_date: str
    ) -> Dict[str, Dict[str, List[Dict]]]:
        """Fetch MRs, commits, and issues for all projects (keyed by project path)."""
        all_data = {
            "pull_requests": {},
            "commits": {},
            "issues": {},
        }
        print(f"  Fetching GitLab data for {len(self.projects)} projects...")
        for project in self.projects:
            try:
                all_data["pull_requests"][project] = self.fetch_merge_requests(
                    project, start_date, end_date
                )
                all_data["commits"][project] = self.fetch_commits(
                    project, start_date, end_date
                )
                all_data["issues"][project] = self.fetch_issues(
                    project, start_date, end_date
                )
                print(
                    f"  Found: {len(all_data['pull_requests'][project])} MRs, "
                    f"{len(all_data['commits'][project])} commits, "
                    f"{len(all_data['issues'][project])} issues"
                )
            except Exception as e:
                print(f"  Error fetching data for {project}: {e}")
                all_data["pull_requests"][project] = []
                all_data["commits"][project] = []
                all_data["issues"][project] = []
        return all_data
