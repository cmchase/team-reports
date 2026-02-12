#!/usr/bin/env python3
"""
Weekly GitLab summary report.

Generates weekly summaries of merge requests, commits, and issues
from GitLab projects (including self-hosted instances).
"""

from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from team_reports.utils.gitlab_summary_base import GitLabSummaryBase


class WeeklyGitLabSummary(GitLabSummaryBase):
    """Generate the weekly GitLab activity summary report."""

    def __init__(
        self,
        config_file: str = "config/gitlab_config.yaml",
        gitlab_token: Optional[str] = None,
    ):
        super().__init__(config_file=config_file, gitlab_token=gitlab_token)

    def generate_report(
        self,
        start_date: str,
        end_date: str,
        config_file: str = "config/gitlab_config.yaml",
    ) -> Tuple[str, Dict[str, List[Dict]]]:
        """Generate the complete weekly GitLab summary report."""
        print(f"\nGenerating GitLab Weekly Summary Report: {start_date} to {end_date}")
        print(f"Using configuration: {config_file}")

        all_data = self.gitlab_client.fetch_all_data(start_date, end_date)
        performance = self.analyze_performance(all_data)

        report_lines = [
            f"# WEEKLY GITLAB SUMMARY: {start_date} to {end_date}",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*",
            "",
        ]
        report_lines.extend(
            self.generate_overview(performance, start_date, end_date, "weekly")
        )
        report_lines.extend(self.generate_repository_summary(performance))
        report_lines.extend(self.generate_contributor_details(performance, "weekly"))

        report = "\n".join(report_lines)
        return report, all_data.get("pull_requests", {})
