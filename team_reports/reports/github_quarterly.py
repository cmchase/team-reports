#!/usr/bin/env python3
"""
Quarterly GitHub Repository Summary Generator

Generates quarterly summaries focused on individual contributor performance
from GitHub repositories, tracking pull requests, commits, issues, and code contributions.

Usage:
    python3 github_quarterly_summary.py [year] [quarter] [config_file]
    python3 github_quarterly_summary.py 2025 4
    python3 github_quarterly_summary.py  # Uses current quarter
    python3 github_quarterly_summary.py 2025 4 config/github_config.yaml
"""

import sys
import os
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime, timezone

from dotenv import load_dotenv
from team_reports.utils.date import get_current_quarter, get_quarter_range, parse_quarter_from_date
from team_reports.utils.config import load_config, get_config
from team_reports.utils.report import ensure_reports_directory, save_report, generate_filename, render_active_config, render_glossary
from team_reports.utils.github import generate_pr_lead_time_analysis
from team_reports.utils.github_summary_base import GitHubSummaryBase

# Load environment variables
load_dotenv()


class GitHubQuarterlySummary(GitHubSummaryBase):
    def __init__(
        self,
        config_file='config/github_config.yaml',
        github_token=None
    ):
        """
        Initialize the GitHub quarterly summary generator with configuration.
        
        Args:
            config_file: Path to YAML configuration file
            github_token: Optional GitHub API token (overrides environment)
        """
        super().__init__(
            config_file=config_file,
            github_token=github_token
        )

    def generate_quarterly_summary(self, year: int, quarter: int) -> Tuple[str, Dict[str, List[Dict]]]:
        """Generate the complete quarterly GitHub summary report."""
        start_date, end_date = get_quarter_range(year, quarter)
        print(f"\n🚀 Generating GitHub Quarterly Summary Report: Q{quarter} {year}")
        print(f"📅 Period: {start_date} to {end_date}")
        
        # Fetch all data from GitHub using GitHubApiClient  
        all_data = self.github_client.fetch_all_data(start_date, end_date)
        
        # Analyze the data to get performance metrics using GitHubSummaryBase
        performance = self.analyze_performance(all_data)
        
        # Generate report sections using GitHubSummaryBase methods
        report_lines = [
            f"# 🐙 QUARTERLY GITHUB SUMMARY: Q{quarter} {year}",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*",
            "",
            f"**Report Period:** {start_date} to {end_date}",
            ""
        ]
        
        # Add overview using inherited method (with quarterly settings)
        report_lines.extend(self.generate_overview(performance, start_date, end_date, "quarterly"))
        
        # Add repository summary using inherited method
        report_lines.extend(self.generate_repository_summary(performance))
        
        # Add contributor details using inherited method (with quarterly settings)
        report_lines.extend(self.generate_contributor_details(performance, "quarterly"))
        
        # Return both the report and PR data for optimization
        return '\n'.join(report_lines), all_data['pull_requests']


def main():
    """Main function to generate and save the quarterly GitHub summary report."""
    try:
        # Parse command line arguments
        if len(sys.argv) >= 3:
            year = int(sys.argv[1])
            quarter = int(sys.argv[2])
            config_file = sys.argv[3] if len(sys.argv) > 3 else 'config/github_config.yaml'
        else:
            # Use current quarter
            year, quarter = get_current_quarter()
            config_file = 'config/github_config.yaml'
        
        print(f"\n📅 Generating Quarterly GitHub Summary for: Q{quarter} {year}")
        print(f"⚙️  Using config: {config_file}")
        
        # Validate quarter input
        if not (1 <= quarter <= 4):
            raise ValueError("Quarter must be between 1 and 4")
        
        # Initialize the quarterly summary generator
        quarterly_summary = GitHubQuarterlySummary(config_file)
        
        # Generate the report and get PR data for potential lead time analysis
        report, pr_data = quarterly_summary.generate_quarterly_summary(year, quarter)
        
        # Helper function for clean feature flag checks
        def flag(path: str) -> bool:
            """Check if a feature flag is enabled in config"""
            keys = path.split('.')
            value = quarterly_summary.config
            try:
                for key in keys:
                    value = value[key]
                return bool(value)
            except (KeyError, TypeError):
                return False
        
        # Add PR Lead Time analysis if enabled
        enable_pr_lead_time = flag("metrics.delivery.pr_lead_time")
        
        if enable_pr_lead_time:
            start_date, end_date = get_quarter_range(year, quarter)
            pr_lead_time_section = generate_pr_lead_time_analysis(
                quarterly_summary.config, start_date, end_date, "quarterly", year, quarter, pr_data
            )
            report += pr_lead_time_section
        
        # Add footer before glossary/configuration
        report += "\n\n---\n\n"
        
        # Add glossary if any metrics are enabled
        glossary_entries = {}
        if flag("metrics.delivery.pr_lead_time"):
            glossary_entries["PR Lead Time"] = "First commit → merge."
        if flag("metrics.delivery.review_depth"):
            glossary_entries["Review Depth"] = "Reviewers per PR and review comments."
        
        if glossary_entries:
            glossary_section = render_glossary(glossary_entries)
            report += glossary_section + "\n"
        
        # Add configuration information if enabled
        config_flag = flag("report.show_active_config")
        if config_flag:
            config_section = render_active_config(quarterly_summary.config)
            report += config_section
        
        # Ensure reports directory exists
        ensure_reports_directory()
        
        # Generate filename and save report
        filename = f"github_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(report, filename)
        
        print(f"\n✅ Quarterly GitHub Summary Report Generated Successfully!")
        print(f"📄 Report saved to: {filepath}")
        print(f"📅 Period: Q{quarter} {year}")
        
    except Exception as e:
        print(f"\n❌ Error generating GitHub quarterly summary: {e}")
        print("🔧 Please check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()