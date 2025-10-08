#!/usr/bin/env python3
"""
Weekly GitHub Repository Summary Generator

Generates weekly summaries focused on GitHub repository activity for sprint reviews,
tracking pull requests, commits, issues, and code contributions for the past week.

Usage:
    python3 github_weekly_summary.py [start_date] [end_date] [config_file]
    python3 github_weekly_summary.py 2025-10-07 2025-10-13
    python3 github_weekly_summary.py  # Uses current week
    python3 github_weekly_summary.py 2025-10-07 2025-10-13 config/custom_github_config.yaml
"""

import sys
import os
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict, Counter
from datetime import datetime, timezone

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from utils.date import parse_date_args, get_current_week
from utils.config import load_config, get_config
from utils.report import ensure_reports_directory, save_report, generate_filename, render_active_config
from utils.github import generate_pr_lead_time_analysis, generate_review_depth_analysis
from utils.github_summary_base import GitHubSummaryBase

# Load environment variables
load_dotenv()


class GitHubWeeklySummary(GitHubSummaryBase):
    def __init__(self, config_file='config/github_config.yaml'):
        """Initialize the GitHub weekly summary generator with configuration."""
        super().__init__(config_file)

    def generate_report(self, start_date: str, end_date: str, config_file: str = 'config/github_config.yaml') -> Tuple[str, Dict[str, List[Dict]]]:
        """Generate the complete weekly GitHub summary report."""
        print(f"\n🚀 Generating GitHub Weekly Summary Report: {start_date} to {end_date}")
        print(f"📄 Using configuration: {config_file}")
        
        # Fetch all data from GitHub using GitHubApiClient  
        all_data = self.github_client.fetch_all_data(start_date, end_date)
        
        # Analyze the data to get performance metrics using GitHubSummaryBase
        performance = self.analyze_performance(all_data)
        
        # Generate report sections using GitHubSummaryBase methods
        report_lines = [
            f"# 🐙 WEEKLY GITHUB SUMMARY: {start_date} to {end_date}",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*",
            ""
        ]
        
        # Add overview using inherited method
        report_lines.extend(self.generate_overview(performance, start_date, end_date, "weekly"))
        
        # Add repository summary using inherited method
        report_lines.extend(self.generate_repository_summary(performance))
        
        # Add contributor details using inherited method
        report_lines.extend(self.generate_contributor_details(performance, "weekly"))
        
        # Return both the report and PR data for optimization
        return '\n'.join(report_lines), all_data['pull_requests']


def main():
    """Main function to generate and save the weekly GitHub summary report."""
    try:
        # Parse command line arguments
        start_date, end_date, config_file = parse_date_args("weekly")
        
        print(f"\n📅 Generating Weekly GitHub Summary for: {start_date} to {end_date}")
        print(f"⚙️  Using config: {config_file}")
        
        # Initialize the weekly summary generator
        weekly_summary = GitHubWeeklySummary(config_file)
        
        # Generate the report and get PR data for potential lead time analysis
        report, pr_data = weekly_summary.generate_report(start_date, end_date, config_file)
        
        # Helper function for clean feature flag checks
        def flag(path: str) -> bool:
            """Check if a feature flag is enabled in config"""
            keys = path.split('.')
            value = weekly_summary.config
            try:
                for key in keys:
                    value = value[key]
                return bool(value)
            except (KeyError, TypeError):
                return False
        
        # Add PR Lead Time analysis if enabled
        enable_pr_lead_time = flag("metrics.delivery.pr_lead_time")
        
        if enable_pr_lead_time:
            pr_lead_time_section = generate_pr_lead_time_analysis(
                weekly_summary.config, start_date, end_date, "weekly", None, None, pr_data
            )
            report += pr_lead_time_section
        
        # Add Review Depth analysis if enabled
        enable_review_depth = flag("metrics.delivery.review_depth")
        
        if enable_review_depth:
            review_depth_section = generate_review_depth_analysis(
                weekly_summary.config, start_date, end_date, "weekly", pr_data
            )
            report += review_depth_section
        
        # Add footer before configuration
        report += "\n\n---\n\n"
        
        # Add configuration information if enabled
        config_flag = flag("report.show_active_config")
        if config_flag:
            config_section = render_active_config(weekly_summary.config)
            report += config_section
        
        # Ensure reports directory exists
        ensure_reports_directory()
        
        # Generate filename and save report
        filename = generate_filename(start_date, end_date, 'github_weekly_summary')
        filepath = save_report(report, filename)
        
        print(f"\n✅ Weekly GitHub Summary Report Generated Successfully!")
        print(f"📄 Report saved to: {filepath}")
        print(f"📅 Period: {start_date} to {end_date}")
        
    except Exception as e:
        print(f"\n❌ Error generating GitHub weekly summary: {e}")
        print("🔧 Please check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()