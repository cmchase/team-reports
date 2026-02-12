#!/usr/bin/env python3
"""
Quarterly GitLab summary report.

Generates quarterly summaries of merge requests, commits, and issues
from GitLab projects (including self-hosted instances), mirroring
the GitHub quarterly report structure.
"""

import sys
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

from dotenv import load_dotenv
from team_reports.utils.date import get_current_quarter, get_quarter_range
from team_reports.utils.report import ensure_reports_directory, save_report
from team_reports.utils.gitlab_summary_base import GitLabSummaryBase

load_dotenv()


class QuarterlyGitLabSummary(GitLabSummaryBase):
    """Generate the quarterly GitLab activity summary report."""

    def __init__(
        self,
        config_file: str = "config/gitlab_config.yaml",
        gitlab_token: Optional[str] = None,
    ):
        super().__init__(config_file=config_file, gitlab_token=gitlab_token)

    def generate_quarterly_summary(
        self, year: int, quarter: int
    ) -> Tuple[str, Dict[str, List[Dict]]]:
        """Generate the complete quarterly GitLab summary report."""
        start_date, end_date = get_quarter_range(year, quarter)
        print(f"\nGenerating GitLab Quarterly Summary Report: Q{quarter} {year}")
        print(f"Period: {start_date} to {end_date}")

        all_data = self.gitlab_client.fetch_all_data(start_date, end_date)
        performance = self.analyze_performance(all_data)

        report_lines = [
            f"# QUARTERLY GITLAB SUMMARY: Q{quarter} {year}",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*",
            "",
            f"**Report Period:** {start_date} to {end_date}",
            "",
        ]
        report_lines.extend(
            self.generate_overview(performance, start_date, end_date, "quarterly")
        )
        report_lines.extend(self.generate_repository_summary(performance))
        report_lines.extend(
            self.generate_contributor_details(performance, "quarterly")
        )

        report = "\n".join(report_lines)
        return report, all_data.get("pull_requests", {})


def main():
    """Main function to generate and save the quarterly GitLab summary report."""
    try:
        if len(sys.argv) >= 3:
            year = int(sys.argv[1])
            quarter = int(sys.argv[2])
            config_file = (
                sys.argv[3] if len(sys.argv) > 3 else "config/gitlab_config.yaml"
            )
        else:
            year, quarter, _, _ = get_current_quarter()
            config_file = "config/gitlab_config.yaml"

        print(f"\nGenerating Quarterly GitLab Summary for: Q{quarter} {year}")
        print(f"Using config: {config_file}")

        if not (1 <= quarter <= 4):
            raise ValueError("Quarter must be between 1 and 4")

        quarterly_summary = QuarterlyGitLabSummary(config_file)
        report, _ = quarterly_summary.generate_quarterly_summary(year, quarter)

        report += "\n\n---\n\n"

        if quarterly_summary.config.get("report", {}).get("show_active_config"):
            from team_reports.utils.report import render_active_config
            report += render_active_config(quarterly_summary.config)

        ensure_reports_directory()
        filename = f"gitlab_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(report, filename)

        print(f"\nQuarterly GitLab Summary Report generated successfully.")
        print(f"Report saved to: {filepath}")
        print(f"Period: Q{quarter} {year}")

    except Exception as e:
        print(f"\nError generating GitLab quarterly summary: {e}")
        print("Check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
