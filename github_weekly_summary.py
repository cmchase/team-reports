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
import requests
import json
import time

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from utils.date import parse_date_args, get_current_week
from utils.config import load_config, get_config
from utils.report import ensure_reports_directory, save_report, generate_filename, render_active_config
from utils.github import compute_pr_lead_time_stats, format_lead_time_duration

# Load environment variables
load_dotenv()


class GitHubWeeklySummary:
    def __init__(self, config_file='config/github_config.yaml'):
        """Initialize the GitHub weekly summary generator with configuration."""
        # GitHub API client setup
        self.github_token = os.getenv('GITHUB_TOKEN')
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN environment variable is required")
        
        # Load configuration from YAML file
        self.config = self._load_config(config_file)
        
        # Extract commonly used config values
        self.repositories = self.config.get('repositories', [])
        self.github_org = self.config.get('github_org', '')
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }

    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file with defaults and environment overrides."""
        return get_config([config_file])

    def _github_request(self, endpoint: str, params: Optional[Dict] = None) -> List[Dict]:
        """Make a request to GitHub API with pagination support."""
        url = f"{self.base_url}/{endpoint}"
        all_data = []
        page = 1
        
        while True:
            request_params = {'page': page, 'per_page': 100}
            if params:
                request_params.update(params)
            
            response = requests.get(url, headers=self.headers, params=request_params)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                break
                
            all_data.extend(data)
            page += 1
            
            # GitHub API returns less than per_page if it's the last page
            if len(data) < 100:
                break
        
        return all_data

    def fetch_pull_requests(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch pull requests for a repository in the date range."""
        print(f"🔍 Fetching pull requests for {repo} from {start_date} to {end_date}...")
        
        # Build repo path
        repo_path = f"{self.github_org}/{repo}" if self.github_org else repo
        
        endpoint = f"repos/{repo_path}/pulls"
        params = {
            'state': 'all',  # Get open, closed, and merged PRs
            'since': start_date,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        prs = self._github_request(endpoint, params)
        
        # Filter by date range (GitHub API doesn't support exact date range filtering)
        filtered_prs = []
        for pr in prs:
            updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
            end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
            
            if start_dt <= updated_at <= end_dt:
                # Fetch detailed PR info for code metrics
                try:
                    detailed_pr = self._fetch_pr_details(repo_path, pr['number'])
                    pr.update(detailed_pr)
                except Exception as e:
                    print(f"  ⚠️  Warning: Could not fetch details for PR #{pr['number']}: {e}")
                    pr['additions'] = 0
                    pr['deletions'] = 0
                    pr['changed_files'] = 0
                
                filtered_prs.append(pr)
        
        return filtered_prs

    def _fetch_pr_details(self, repo: str, pr_number: int) -> Dict:
        """Fetch detailed information for a specific pull request."""
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        
        # Add small delay to avoid hitting rate limits
        time.sleep(0.1)
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        pr_data = response.json()
        return {
            'additions': pr_data.get('additions', 0),
            'deletions': pr_data.get('deletions', 0),
            'changed_files': pr_data.get('changed_files', 0)
        }

    def fetch_commits(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch commits for a repository in the date range."""
        print(f"🔍 Fetching commits for {repo} from {start_date} to {end_date}...")
        
        # Build repo path
        repo_path = f"{self.github_org}/{repo}" if self.github_org else repo
        
        endpoint = f"repos/{repo_path}/commits"
        params = {
            'since': f"{start_date}T00:00:00Z",
            'until': f"{end_date}T23:59:59Z"
        }
        
        return self._github_request(endpoint, params)

    def fetch_issues(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch issues for a repository in the date range."""
        print(f"🔍 Fetching issues for {repo} from {start_date} to {end_date}...")
        
        # Build repo path
        repo_path = f"{self.github_org}/{repo}" if self.github_org else repo
        
        endpoint = f"repos/{repo_path}/issues"
        params = {
            'state': 'all',
            'since': f"{start_date}T00:00:00Z",
            'sort': 'updated',
            'direction': 'desc'
        }
        
        issues = self._github_request(endpoint, params)
        
        # Filter out pull requests (GitHub API includes PRs in issues) and by date range
        filtered_issues = []
        for issue in issues:
            if 'pull_request' not in issue:
                updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
                end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
                
                if start_dt <= updated_at <= end_dt:
                    filtered_issues.append(issue)
        
        return filtered_issues

    def fetch_all_data(self, start_date: str, end_date: str) -> Dict[str, Dict[str, List[Dict]]]:
        """Fetch all GitHub data for the specified date range."""
        all_data = {
            'pull_requests': {},
            'commits': {},
            'issues': {}
        }
        
        print(f"🚀 Fetching GitHub data for {len(self.repositories)} repositories...")
        
        for repo in self.repositories:
            print(f"\n📁 Processing repository: {repo}")
            
            try:
                all_data['pull_requests'][repo] = self.fetch_pull_requests(repo, start_date, end_date)
                all_data['commits'][repo] = self.fetch_commits(repo, start_date, end_date)
                all_data['issues'][repo] = self.fetch_issues(repo, start_date, end_date)
                
                pr_count = len(all_data['pull_requests'][repo])
                commit_count = len(all_data['commits'][repo])
                issue_count = len(all_data['issues'][repo])
                
                print(f"  ✅ Found: {pr_count} PRs, {commit_count} commits, {issue_count} issues")
                
            except Exception as e:
                print(f"  ❌ Error fetching data for {repo}: {e}")
                all_data['pull_requests'][repo] = []
                all_data['commits'][repo] = []
                all_data['issues'][repo] = []
        
        return all_data

    def analyze_weekly_performance(self, all_data: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Any]:
        """Analyze GitHub activity data to extract weekly performance metrics."""
        performance = {
            'contributor_prs': defaultdict(list),
            'contributor_commits': defaultdict(list),
            'contributor_issues': defaultdict(list),
            'contributor_pr_counts': defaultdict(int),
            'contributor_commit_counts': defaultdict(int),
            'contributor_issue_counts': defaultdict(int),
            'contributor_lines_added': defaultdict(int),
            'contributor_lines_removed': defaultdict(int),
            'repository_activity': defaultdict(int),
            'daily_activity': defaultdict(lambda: defaultdict(int))
        }
        
        # Process pull requests
        for repo, prs in all_data['pull_requests'].items():
            for pr in prs:
                author = self._get_contributor_name(pr.get('user', {}).get('login', 'Unknown'))
                performance['contributor_prs'][author].append({
                    'repo': repo,
                    'title': pr['title'],
                    'number': pr['number'],
                    'state': pr['state'],
                    'created_at': pr['created_at'],
                    'updated_at': pr['updated_at'],
                    'merged_at': pr.get('merged_at'),
                    'url': pr['html_url'],
                    'additions': pr.get('additions', 0),
                    'deletions': pr.get('deletions', 0),
                    'changed_files': pr.get('changed_files', 0)
                })
                performance['contributor_pr_counts'][author] += 1
                performance['contributor_lines_added'][author] += pr.get('additions', 0)
                performance['contributor_lines_removed'][author] += pr.get('deletions', 0)
                performance['repository_activity'][repo] += 1
                
                # Track daily activity
                created_date = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                day_key = created_date.strftime('%Y-%m-%d')
                performance['daily_activity'][day_key][author] += 1
        
        # Process commits
        for repo, commits in all_data['commits'].items():
            for commit in commits:
                author_info = commit.get('author') or commit.get('commit', {}).get('author', {})
                author = self._get_contributor_name(author_info.get('login') or author_info.get('name', 'Unknown'))
                
                performance['contributor_commits'][author].append({
                    'repo': repo,
                    'message': commit['commit']['message'],
                    'sha': commit['sha'],
                    'date': commit['commit']['author']['date'],
                    'url': commit['html_url']
                })
                performance['contributor_commit_counts'][author] += 1
                performance['repository_activity'][repo] += 1
                
                # Track daily activity
                commit_date = datetime.fromisoformat(commit['commit']['author']['date'].replace('Z', '+00:00'))
                day_key = commit_date.strftime('%Y-%m-%d')
                performance['daily_activity'][day_key][author] += 1
        
        # Process issues
        for repo, issues in all_data['issues'].items():
            for issue in issues:
                author = self._get_contributor_name(issue.get('user', {}).get('login', 'Unknown'))
                performance['contributor_issues'][author].append({
                    'repo': repo,
                    'title': issue['title'],
                    'number': issue['number'],
                    'state': issue['state'],
                    'created_at': issue['created_at'],
                    'updated_at': issue['updated_at'],
                    'url': issue['html_url']
                })
                performance['contributor_issue_counts'][author] += 1
                performance['repository_activity'][repo] += 1
        
        return performance

    def _get_contributor_name(self, github_username: str) -> str:
        """Map GitHub username to display name using team configuration."""
        team_members = self.config.get('team_members', {})
        return team_members.get(github_username, github_username)

    def generate_weekly_overview(self, performance: Dict[str, Any], start_date: str, end_date: str) -> List[str]:
        """Generate the weekly overview section."""
        total_prs = sum(performance['contributor_pr_counts'].values())
        total_commits = sum(performance['contributor_commit_counts'].values())
        total_issues = sum(performance['contributor_issue_counts'].values())
        total_lines_added = sum(performance['contributor_lines_added'].values())
        total_lines_removed = sum(performance['contributor_lines_removed'].values())
        total_contributors = len(set(list(performance['contributor_pr_counts'].keys()) + 
                                   list(performance['contributor_commit_counts'].keys()) +
                                   list(performance['contributor_issue_counts'].keys())))
        
        overview = [
            f"### 📊 WEEKLY GITHUB ACTIVITY OVERVIEW",
            f"- **Total Pull Requests:** {total_prs}",
            f"- **Total Commits:** {total_commits}",
            f"- **Total Issues Updated:** {total_issues}",
            f"- **Lines Added:** +{total_lines_added:,}",
            f"- **Lines Removed:** -{total_lines_removed:,}",
            f"- **Net Lines Changed:** {total_lines_added - total_lines_removed:+,}",
            f"- **Active Contributors:** {total_contributors}",
            ""
        ]

        # Add top contributors if we have activity
        if total_contributors > 0:
            overview.append("#### 🏆 Top Contributors This Week")
            top_pr_contributors = sorted(performance['contributor_pr_counts'].items(), 
                                       key=lambda x: x[1], reverse=True)[:5]
            
            for i, (contributor, count) in enumerate(top_pr_contributors, 1):
                commits = performance['contributor_commit_counts'].get(contributor, 0)
                lines_added = performance['contributor_lines_added'].get(contributor, 0)
                lines_removed = performance['contributor_lines_removed'].get(contributor, 0)
                overview.append(f"**{i}. {contributor}** - {count} PRs, {commits} commits, +{lines_added}/-{lines_removed} lines")
                overview.append("")
            overview.append("")

        return overview

    def generate_repository_summary(self, performance: Dict[str, Any]) -> List[str]:
        """Generate repository activity summary."""
        report = []
        
        if performance['repository_activity']:
            report.append("#### 📁 Repository Activity Summary")
            sorted_repos = sorted(performance['repository_activity'].items(), 
                                key=lambda x: x[1], reverse=True)
            for repo, activity in sorted_repos:
                report.append(f"- **{repo}:** {activity} total activities")
            report.append("")
        
        return report

    def generate_contributor_details(self, performance: Dict[str, Any]) -> List[str]:
        """Generate detailed contributor analysis."""
        report = []
        
        # Get all contributors sorted by total activity
        all_contributors = set()
        all_contributors.update(performance['contributor_pr_counts'].keys())
        all_contributors.update(performance['contributor_commit_counts'].keys())
        all_contributors.update(performance['contributor_issue_counts'].keys())
        
        contributors_by_activity = []
        for contributor in all_contributors:
            prs = performance['contributor_pr_counts'].get(contributor, 0)
            commits = performance['contributor_commit_counts'].get(contributor, 0) 
            issues = performance['contributor_issue_counts'].get(contributor, 0)
            total_activity = prs + commits + issues
            contributors_by_activity.append((contributor, total_activity))
        
        contributors_by_activity.sort(key=lambda x: x[1], reverse=True)
        
        if contributors_by_activity:
            report.append("## 👥 INDIVIDUAL CONTRIBUTOR DETAILS")
            report.append("")
            
            for contributor, _ in contributors_by_activity:
                prs = performance['contributor_prs'][contributor]
                commits = performance['contributor_commits'][contributor]
                issues = performance['contributor_issues'][contributor]
                
                if prs or commits or issues:  # Only show contributors with activity
                    report.extend(self.generate_contributor_section(contributor, prs, commits, issues))
        
        return report

    def generate_contributor_section(self, contributor: str, prs: List[Dict], commits: List[Dict], issues: List[Dict]) -> List[str]:
        """Generate a detailed section for an individual contributor."""
        section = []
        
        # Calculate totals
        total_lines_added = sum(pr.get('additions', 0) for pr in prs)
        total_lines_removed = sum(pr.get('deletions', 0) for pr in prs)
        
        section.append(f"### 👤 {contributor}")
        section.append(f"- **Pull Requests:** {len(prs)}")
        section.append(f"- **Commits:** {len(commits)}")
        section.append(f"- **Issues:** {len(issues)}")
        if total_lines_added > 0 or total_lines_removed > 0:
            section.append(f"- **Code Changes:** +{total_lines_added:,}/-{total_lines_removed:,} lines")
        section.append("")

        # Recent Pull Requests
        if prs:
            section.append("#### 🔄 Pull Requests This Week")
            recent_prs = sorted(prs, key=lambda x: x['updated_at'], reverse=True)[:5]
            section.extend([
                "| Repository | PR | State | Lines | Title |",
                "|------------|----|---------|----- |-------|"
            ])
            
            for pr in recent_prs:
                lines = f"+{pr.get('additions', 0)}/-{pr.get('deletions', 0)}"
                title = pr['title'][:60] + "..." if len(pr['title']) > 60 else pr['title']
                section.append(f"| {pr['repo']} | [#{pr['number']}]({pr['url']}) | {pr['state']} | {lines} | {title} |")
            section.append("")

        # Recent Commits (show top 3)
        if commits:
            section.append("#### 💻 Recent Commits")
            recent_commits = sorted(commits, key=lambda x: x['date'], reverse=True)[:3]
            for commit in recent_commits:
                message = commit['message'].split('\n')[0][:80] + "..." if len(commit['message'].split('\n')[0]) > 80 else commit['message'].split('\n')[0]
                section.append(f"- **{commit['repo']}:** [{commit['sha'][:7]}]({commit['url']}) - {message}")
            section.append("")

        return section

    def generate_report(self, start_date: str, end_date: str, config_file: str = 'config/github_config.yaml') -> str:
        """Generate the complete weekly GitHub summary report."""
        print(f"\n🚀 Generating GitHub Weekly Summary Report: {start_date} to {end_date}")
        print(f"📄 Using configuration: {config_file}")
        
        # Fetch all GitHub data
        all_data = self.fetch_all_data(start_date, end_date)
        
        # Analyze performance
        performance = self.analyze_weekly_performance(all_data)
        
        # Generate report sections
        report_lines = [
            f"# 🐙 WEEKLY GITHUB SUMMARY: {start_date} to {end_date}",
            "",
            f"*Generated on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*",
            ""
        ]
        
        # Add overview
        report_lines.extend(self.generate_weekly_overview(performance, start_date, end_date))
        
        # Add repository summary
        report_lines.extend(self.generate_repository_summary(performance))
        
        # Add contributor details
        report_lines.extend(self.generate_contributor_details(performance))
        
        # Add footer
        report_lines.extend([
            "---",
            "",
            "## 📋 Summary",
            "This weekly GitHub summary provides insights into repository activity, code contributions, and team collaboration patterns. Use this data for sprint reviews, team discussions, and identifying collaboration opportunities.",
            "",
            f"**Report Period:** {start_date} to {end_date}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Repositories Analyzed:** {len(self.repositories)}",
            ""
        ])
        
        return '\n'.join(report_lines)


def generate_pr_lead_time_analysis(config: Dict[str, Any], start_date: str, end_date: str) -> str:
    """
    Generate PR lead time analysis section for weekly report.
    
    Args:
        config: Configuration dictionary with GitHub settings
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        str: Markdown section with PR lead time analysis
    """
    try:
        # Initialize GitHub client
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return "\n\n### 🚀 Delivery • PR Lead Time\n\n*Error: GITHUB_TOKEN not configured*\n"
        
        # Get configuration values
        repositories = config.get('repositories', [])
        github_org = config.get('github_org', config.get('github', {}).get('org', ''))
        min_lines_changed = config.get('thresholds', {}).get('delivery', {}).get('min_lines_changed', 5)
        
        if not repositories:
            return "\n\n### 🚀 Delivery • PR Lead Time\n\n*No repositories configured for analysis*\n"
        
        print(f"🚀 Computing PR lead time analysis...")
        
        # Collect all merged PRs from the period
        all_prs = []
        
        # Create temporary GitHub client to fetch PR data
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        for repo in repositories:
            repo_path = f"{github_org}/{repo}" if github_org else repo
            
            # Fetch merged PRs for this repository
            url = f"https://api.github.com/repos/{repo_path}/pulls"
            params = {
                'state': 'closed',
                'sort': 'updated',
                'direction': 'desc',
                'per_page': 100
            }
            
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                continue
                
            prs = response.json()
            
            # Filter PRs merged in our date range
            for pr in prs:
                if pr.get('merged_at'):
                    merged_date = pr['merged_at'][:10]  # Extract YYYY-MM-DD
                    if start_date <= merged_date <= end_date:
                        all_prs.append(pr)
        
        # Compute lead time statistics
        stats = compute_pr_lead_time_stats(all_prs, min_lines_changed)
        
        if stats['count'] == 0:
            return f"\n\n### 🚀 Delivery • PR Lead Time\n\n*No merged PRs with ≥{min_lines_changed} lines changed found in this period*\n"
        
        # Build the section
        section = f"\n\n### 🚀 Delivery • PR Lead Time\n\n"
        section += f"**Merged PRs Analyzed:** {stats['count']} PRs (≥{min_lines_changed} lines changed)\n\n"
        
        # Summary statistics
        avg_formatted = format_lead_time_duration(stats['avg'])
        median_formatted = format_lead_time_duration(stats['median']) 
        p90_formatted = format_lead_time_duration(stats['p90'])
        
        section += f"**📊 Lead Time Summary**\n"
        section += f"- **Average:** {avg_formatted}\n"
        section += f"- **Median:** {median_formatted}\n" 
        section += f"- **90th Percentile:** {p90_formatted}\n\n"
        
        # Top 5 fastest PRs
        if stats['fastest']:
            section += f"#### ⚡ Top 5 Fastest PRs\n\n"
            section += "| PR | Author | Lead Time | Lines | Title |\n"
            section += "|-------|--------|-----------|-------|-------|\n"
            
            for pr in stats['fastest']:
                lead_time_str = format_lead_time_duration(pr['lead_time_hours'])
                lines_changed = pr['additions'] + pr['deletions']
                title = pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title']
                section += f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {lead_time_str} | {lines_changed} | {title} |\n"
            section += "\n"
        
        # Top 5 slowest PRs  
        if stats['slowest']:
            section += f"#### 🐌 Top 5 Slowest PRs\n\n"
            section += "| PR | Author | Lead Time | Lines | Title |\n"
            section += "|-------|--------|-----------|-------|-------|\n"
            
            for pr in stats['slowest']:
                lead_time_str = format_lead_time_duration(pr['lead_time_hours'])
                lines_changed = pr['additions'] + pr['deletions']
                title = pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title']
                section += f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {lead_time_str} | {lines_changed} | {title} |\n"
            section += "\n"
        
        return section
        
    except Exception as e:
        return f"\n\n### 🚀 Delivery • PR Lead Time\n\n*Error computing PR lead time analysis: {e}*\n"


def main():
    """Main function to generate GitHub weekly summary report."""
    # Parse command line arguments for dates and optional config file
    args = sys.argv[1:]
    
    # Extract config file if provided (last argument ending in .yaml)
    config_file = 'config/github_config.yaml'  # Default
    if args and args[-1].endswith('.yaml'):
        config_file = args.pop()  # Remove config from date args
    
    # Parse date arguments
    start_date, end_date = parse_date_args(args)
    
    try:
        # Load configuration and setup feature flags
        config = get_config([config_file])
        
        # Helper function for clean feature flag checks
        def flag(path: str) -> bool:
            """Check if a feature flag is enabled in config"""
            keys = path.split('.')
            value = config
            try:
                for key in keys:
                    value = value[key]
                return bool(value)
            except (KeyError, TypeError):
                return False
        
        # Feature flags for GitHub delivery metrics (Phase 2+)
        enable_pr_lead_time = flag("metrics.delivery.pr_lead_time")
        enable_review_depth = flag("metrics.delivery.review_depth")
        
        # Initialize the summary generator
        summary_generator = GitHubWeeklySummary(config_file)
        
        # Generate the report
        report_content = summary_generator.generate_report(start_date, end_date, config_file)
        
        # Add PR lead time analysis if enabled
        if enable_pr_lead_time:
            pr_lead_time_section = generate_pr_lead_time_analysis(config, start_date, end_date)
            report_content += pr_lead_time_section
        
        # TODO: Future GitHub metrics sections (Phase 2+)
        # if enable_review_depth:
        #     report_content += generate_review_depth_analysis(config, start_date, end_date)
        
        # Append active configuration block
        config_block = render_active_config(config)
        full_report = report_content + config_block
        
        # Save the report
        ensure_reports_directory()
        filename = generate_filename("github_weekly_summary", start_date, end_date)
        filepath = save_report(full_report, filename)
        
        print(f"\n✅ GitHub Weekly Summary Report Generated!")
        print(f"📄 Report saved to: {filepath}")
        print(f"📅 Period: {start_date} to {end_date}")
        
    except Exception as e:
        print(f"\n❌ Error generating GitHub weekly summary: {e}")
        print("🔧 Please check your configuration and try again.")
        sys.exit(1)


if __name__ == "__main__":
    main()
