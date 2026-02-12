#!/usr/bin/env python3
"""
Base class for GitLab summary reports.

Mirrors GitHub summary structure: merge requests, commits, issues,
with contributor names from team_members (gitlab_username -> display_name).
"""

from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime

from .gitlab_client import GitLabApiClient
from .github import is_bot_user
from .report import truncate_text


class GitLabSummaryBase:
    """Base class for GitLab summary generators with shared functionality."""

    def __init__(
        self,
        config_file: str = "config/gitlab_config.yaml",
        gitlab_token: Optional[str] = None,
    ):
        """
        Initialize the GitLab summary generator with configuration.

        Args:
            config_file: Path to YAML configuration file
            gitlab_token: Optional GitLab API token (overrides environment)
        """
        self.gitlab_client = GitLabApiClient(
            config_file=config_file,
            gitlab_token=gitlab_token,
        )
        self.config = self.gitlab_client.config
        self.projects = self.gitlab_client.projects

    def _get_contributor_name(self, gitlab_username: str) -> str:
        """Map GitLab username to display name using team configuration."""
        team_members = self.config.get("team_members", {})
        return team_members.get(gitlab_username, gitlab_username)

    def _is_bot_contributor(self, gitlab_username: str) -> bool:
        """Check if a GitLab username matches any configured bot patterns."""
        if not gitlab_username:
            return False
        bot_patterns = self.config.get("bots", {}).get("patterns", [])
        return is_bot_user(gitlab_username, bot_patterns)

    def _get_mr_comment_count(self, mr: Dict[str, Any]) -> int:
        """Placeholder for MR review comment count (GitLab MR discussions not fetched here)."""
        return 0

    def analyze_performance(
        self, all_data: Dict[str, Dict[str, List[Dict]]]
    ) -> Dict[str, Any]:
        """Analyze GitLab activity data to extract performance metrics."""
        performance = {
            "contributor_prs": defaultdict(list),
            "contributor_commits": defaultdict(list),
            "contributor_issues": defaultdict(list),
            "contributor_pr_counts": defaultdict(int),
            "contributor_commit_counts": defaultdict(int),
            "contributor_issue_counts": defaultdict(int),
            "contributor_lines_added": defaultdict(int),
            "contributor_lines_removed": defaultdict(int),
            "repository_activity": defaultdict(int),
            "daily_activity": defaultdict(lambda: defaultdict(int)),
        }

        for repo, prs in all_data["pull_requests"].items():
            for pr in prs:
                author_login = pr.get("user", {}).get("login", "Unknown")
                if self._is_bot_contributor(author_login):
                    continue
                author = self._get_contributor_name(author_login)
                performance["contributor_prs"][author].append({
                    "repo": repo,
                    "title": pr["title"],
                    "number": pr["number"],
                    "state": pr["state"],
                    "created_at": pr["created_at"],
                    "updated_at": pr["updated_at"],
                    "merged_at": pr.get("merged_at"),
                    "url": pr["html_url"],
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                    "body": pr.get("body", ""),
                })
                performance["contributor_pr_counts"][author] += 1
                performance["contributor_lines_added"][author] += pr.get("additions", 0)
                performance["contributor_lines_removed"][author] += pr.get("deletions", 0)
                performance["repository_activity"][repo] += 1
                created_date = datetime.fromisoformat(
                    pr["created_at"].replace("Z", "+00:00")
                )
                day_key = created_date.strftime("%Y-%m-%d")
                performance["daily_activity"][day_key][author] += 1

        for repo, commits in all_data["commits"].items():
            for commit in commits:
                author_info = commit.get("author") or commit.get("commit", {}).get("author", {})
                author_login = author_info.get("login") or author_info.get("name", "Unknown")
                if self._is_bot_contributor(author_login):
                    continue
                author = self._get_contributor_name(author_login)
                c = commit.get("commit", {})
                author_date = c.get("author", {}).get("date", "") if isinstance(c.get("author"), dict) else ""
                if not author_date and isinstance(commit.get("commit"), dict):
                    author_date = (commit["commit"].get("author") or {}).get("date", "")
                performance["contributor_commits"][author].append({
                    "repo": repo,
                    "message": (commit.get("commit") or {}).get("message", commit.get("message", "")),
                    "sha": commit.get("sha", ""),
                    "date": author_date or commit.get("created_at", ""),
                    "url": commit.get("html_url", ""),
                })
                performance["contributor_commit_counts"][author] += 1
                performance["repository_activity"][repo] += 1
                date_str = author_date or commit.get("created_at") or ""
                if date_str:
                    try:
                        commit_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                        day_key = commit_date.strftime("%Y-%m-%d")
                        performance["daily_activity"][day_key][author] += 1
                    except (ValueError, TypeError):
                        pass

        for repo, issues in all_data["issues"].items():
            for issue in issues:
                author_login = issue.get("user", {}).get("login", "Unknown")
                if self._is_bot_contributor(author_login):
                    continue
                author = self._get_contributor_name(author_login)
                performance["contributor_issues"][author].append({
                    "repo": repo,
                    "title": issue["title"],
                    "number": issue["number"],
                    "state": issue["state"],
                    "created_at": issue["created_at"],
                    "updated_at": issue["updated_at"],
                    "url": issue["html_url"],
                })
                performance["contributor_issue_counts"][author] += 1
                performance["repository_activity"][repo] += 1

        return performance

    def generate_overview(
        self,
        performance: Dict[str, Any],
        start_date: str,
        end_date: str,
        report_type: str = "weekly",
    ) -> List[str]:
        """Generate the activity overview section."""
        total_mrs = sum(performance["contributor_pr_counts"].values())
        total_commits = sum(performance["contributor_commit_counts"].values())
        total_issues = sum(performance["contributor_issue_counts"].values())
        total_lines_added = sum(performance["contributor_lines_added"].values())
        total_lines_removed = sum(performance["contributor_lines_removed"].values())
        total_contributors = len(
            set(performance["contributor_pr_counts"].keys()).union(
                performance["contributor_commit_counts"].keys(),
                performance["contributor_issue_counts"].keys(),
            )
        )

        if report_type == "quarterly":
            title = "QUARTERLY GITLAB CONTRIBUTOR OVERVIEW"
        else:
            title = "WEEKLY GITLAB ACTIVITY OVERVIEW"

        overview = [
            f"### {title}",
            f"- **Total Merge Requests:** {total_mrs}",
            f"- **Total Commits:** {total_commits}",
        ]
        if report_type == "weekly":
            overview.append(f"- **Total Issues Updated:** {total_issues}")
            overview.extend([
                f"- **Lines Added:** +{total_lines_added:,}",
                f"- **Lines Removed:** -{total_lines_removed:,}",
                f"- **Net Lines Changed:** {total_lines_added - total_lines_removed:+,}",
                f"- **Active Contributors:** {total_contributors}",
            ])
        else:
            overview.extend([
                f"- **Total Issues:** {total_issues}",
                f"- **Lines Added:** {total_lines_added:,}",
                f"- **Lines Removed:** {total_lines_removed:,}",
                f"- **Active Contributors:** {total_contributors}",
            ])
        overview.append("")
        return overview

    def generate_repository_summary(self, performance: Dict[str, Any]) -> List[str]:
        """Generate repository activity summary."""
        report = []
        if performance["repository_activity"]:
            report.append("#### Repository Activity Summary")
            sorted_repos = sorted(
                performance["repository_activity"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for repo, activity in sorted_repos:
                report.append(f"- **{repo}:** {activity} total activities")
            report.append("")
        return report

    def generate_contributor_details(
        self, performance: Dict[str, Any], report_type: str = "weekly"
    ) -> List[str]:
        """Generate detailed contributor analysis."""
        report = []
        all_contributors = set(performance["contributor_pr_counts"].keys()).union(
            performance["contributor_commit_counts"].keys(),
            performance["contributor_issue_counts"].keys(),
        )
        contributors_by_activity = []
        for contributor in all_contributors:
            prs = performance["contributor_pr_counts"].get(contributor, 0)
            commits = performance["contributor_commit_counts"].get(contributor, 0)
            issues = performance["contributor_issue_counts"].get(contributor, 0)
            contributors_by_activity.append((contributor, prs + commits + issues))
        contributors_by_activity.sort(key=lambda x: x[1], reverse=True)

        if contributors_by_activity:
            report.append("## INDIVIDUAL CONTRIBUTOR DETAILS")
            report.append("")
            for contributor, _ in contributors_by_activity:
                report.extend(
                    self._generate_contributor_section(
                        contributor, performance, report_type
                    )
                )
        return report

    def _generate_contributor_section(
        self,
        contributor: str,
        performance: Dict[str, Any],
        report_type: str,
    ) -> List[str]:
        """Generate a detailed section for an individual contributor."""
        prs = performance["contributor_prs"][contributor]
        commits = performance["contributor_commits"][contributor]
        issues = performance["contributor_issues"][contributor]
        if not (prs or commits or issues):
            return []

        total_lines_added = sum(p.get("additions", 0) for p in prs)
        total_lines_removed = sum(p.get("deletions", 0) for p in prs)
        section = [
            f"### {contributor}",
            f"- **Merge Requests:** {len(prs)}",
            f"- **Commits:** {len(commits)}",
            f"- **Issues:** {len(issues)}",
        ]
        if total_lines_added > 0 or total_lines_removed > 0:
            section.append(
                f"- **Code Changes:** +{total_lines_added:,}/-{total_lines_removed:,} lines"
            )
        section.append("")

        if prs:
            if report_type == "weekly":
                section.append("#### Merge Requests This Week")
            else:
                section.append("#### Recent Merge Requests")
            recent = sorted(prs, key=lambda x: x["updated_at"], reverse=True)[
                : 10 if report_type == "quarterly" else 5
            ]
            section.extend([
                "| Project | MR | State | Lines | Title | Description |",
                "|---------|-----|-------|--------|-------|-------------|",
            ])
            for pr in recent:
                title = pr["title"][:60] + ("..." if len(pr["title"]) > 60 else "")
                desc = truncate_text(pr.get("body", ""), max_length=500)
                lines = f"+{pr.get('additions', 0)}/-{pr.get('deletions', 0)}"
                section.append(
                    f"| {pr['repo']} | [!{pr['number']}]({pr['url']}) | {pr['state']} | {lines} | {title} | {desc} |"
                )
            section.append("")

        if commits:
            section.append("#### Recent Commits")
            recent_commits = sorted(commits, key=lambda x: x["date"], reverse=True)[:3]
            for commit in recent_commits:
                msg = (commit.get("message") or "").split("\n")[0]
                msg = msg[:80] + "..." if len(msg) > 80 else msg
                sha_short = (commit.get("sha") or "")[:7]
                section.append(
                    f"- **{commit['repo']}:** [{sha_short}]({commit['url']}) - {msg}"
                )
            section.append("")

        return section
