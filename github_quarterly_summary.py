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
import requests
import json
import time

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from utils.date import get_current_quarter, get_quarter_range, parse_quarter_from_date
from utils.config import load_config, get_config
from utils.report import ensure_reports_directory, save_report, generate_filename, render_active_config
from utils.github import compute_pr_lead_time_stats, format_lead_time_duration

# Load environment variables
load_dotenv()


class GitHubQuarterlySummary:
    def __init__(self, config_file='config/github_config.yaml'):
        """Initialize the GitHub quarterly summary generator with configuration."""
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
        """Fetch pull requests for a repository in the date range with detailed information."""
        print(f"🔍 Fetching pull requests for {repo} from {start_date} to {end_date}...")
        
        endpoint = f"repos/{repo}/pulls"
        params = {
            'state': 'all',  # Get open, closed, and merged PRs
            'since': start_date,
            'sort': 'updated',
            'direction': 'desc'
        }
        
        prs = self._github_request(endpoint, params)
        
        # Filter by date range (GitHub API doesn't support date range filtering directly)
        filtered_prs = []
        for pr in prs:
            updated_at = datetime.fromisoformat(pr['updated_at'].replace('Z', '+00:00'))
            start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
            end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
            
            if start_dt <= updated_at <= end_dt:
                filtered_prs.append(pr)
        
        # Fetch detailed information for each PR to get additions/deletions
        detailed_prs = []
        for pr in filtered_prs:
            try:
                print(f"  📊 Fetching details for PR #{pr['number']}...")
                detailed_pr = self._fetch_pr_details(repo, pr['number'])
                # Merge basic PR info with detailed info
                pr.update(detailed_pr)
                detailed_prs.append(pr)
            except Exception as e:
                print(f"  ⚠️  Warning: Could not fetch details for PR #{pr['number']}: {e}")
                # Keep the PR but with 0 additions/deletions
                pr['additions'] = 0
                pr['deletions'] = 0
                detailed_prs.append(pr)
        
        return detailed_prs

    def _fetch_pr_details(self, repo: str, pr_number: int) -> Dict:
        """Fetch detailed information for a specific pull request."""
        url = f"{self.base_url}/repos/{repo}/pulls/{pr_number}"
        
        # Add small delay to avoid hitting rate limits too hard
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
        
        endpoint = f"repos/{repo}/commits"
        params = {
            'since': f"{start_date}T00:00:00Z",
            'until': f"{end_date}T23:59:59Z"
        }
        
        return self._github_request(endpoint, params)

    def fetch_issues(self, repo: str, start_date: str, end_date: str) -> List[Dict]:
        """Fetch issues for a repository in the date range."""
        print(f"🔍 Fetching issues for {repo} from {start_date} to {end_date}...")
        
        endpoint = f"repos/{repo}/issues"
        params = {
            'state': 'all',
            'since': f"{start_date}T00:00:00Z",
            'sort': 'updated',
            'direction': 'desc'
        }
        
        issues = self._github_request(endpoint, params)
        
        # Filter out pull requests (GitHub API includes PRs in issues)
        filtered_issues = []
        for issue in issues:
            if 'pull_request' not in issue:
                updated_at = datetime.fromisoformat(issue['updated_at'].replace('Z', '+00:00'))
                start_dt = datetime.fromisoformat(f"{start_date}T00:00:00+00:00")
                end_dt = datetime.fromisoformat(f"{end_date}T23:59:59+00:00")
                
                if start_dt <= updated_at <= end_dt:
                    filtered_issues.append(issue)
        
        return filtered_issues

    def analyze_contributor_performance(self, all_data: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Analyze individual contributor performance across all repositories."""
        performance = {
            'contributor_prs': defaultdict(list),           # Contributor -> List of PRs
            'contributor_commits': defaultdict(list),       # Contributor -> List of commits
            'contributor_issues': defaultdict(list),        # Contributor -> List of issues
            'contributor_pr_counts': defaultdict(int),      # Contributor -> PR count
            'contributor_commit_counts': defaultdict(int),  # Contributor -> Commit count
            'contributor_issue_counts': defaultdict(int),   # Contributor -> Issue count
            'contributor_lines_added': defaultdict(int),    # Contributor -> Lines added
            'contributor_lines_removed': defaultdict(int),  # Contributor -> Lines removed
            'repository_activity': defaultdict(int),        # Repository -> Total activity
            'monthly_activity': defaultdict(lambda: defaultdict(int)),  # Month -> Contributor -> Count
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
                
                # Track monthly activity
                created_date = datetime.fromisoformat(pr['created_at'].replace('Z', '+00:00'))
                month_key = created_date.strftime('%Y-%m')
                performance['monthly_activity'][month_key][author] += 1
        
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

    def generate_quarterly_overview(self, performance: Dict[str, Any], year: int, quarter: int) -> List[str]:
        """Generate the quarterly overview section."""
        total_prs = sum(performance['contributor_pr_counts'].values())
        total_commits = sum(performance['contributor_commit_counts'].values())
        total_issues = sum(performance['contributor_issue_counts'].values())
        total_lines_added = sum(performance['contributor_lines_added'].values())
        total_lines_removed = sum(performance['contributor_lines_removed'].values())
        total_contributors = len(set(list(performance['contributor_pr_counts'].keys()) + 
                                   list(performance['contributor_commit_counts'].keys()) +
                                   list(performance['contributor_issue_counts'].keys())))
        
        overview = [
            f"### 📊 Q{quarter} {year} GITHUB CONTRIBUTOR OVERVIEW",
            f"- **Total Pull Requests:** {total_prs}",
            f"- **Total Commits:** {total_commits}",
            f"- **Total Issues:** {total_issues}",
            f"- **Lines Added:** {total_lines_added:,}",
            f"- **Lines Removed:** {total_lines_removed:,}",
            f"- **Active Contributors:** {total_contributors}",
            f"- **Quarter Period:** Q{quarter} {year}",
            ""
        ]
        
        # Add top contributors by various metrics
        if performance['contributor_pr_counts']:
            overview.append("#### 🏆 Top Contributors by Pull Requests")
            top_pr_contributors = sorted(performance['contributor_pr_counts'].items(), 
                                       key=lambda x: x[1], reverse=True)[:15]
            
            for i, (contributor, count) in enumerate(top_pr_contributors, 1):
                percentage = (count / total_prs * 100) if total_prs > 0 else 0
                commits = performance['contributor_commit_counts'].get(contributor, 0)
                issues = performance['contributor_issue_counts'].get(contributor, 0)
                lines_added = performance['contributor_lines_added'].get(contributor, 0)
                overview.append(f"{i}. **{contributor}:** {count} PRs ({percentage:.1f}%) • {commits} commits • {issues} issues • +{lines_added:,} lines")
            overview.append("")
        
        return overview

    def generate_contributor_details(self, contributor: str, performance: Dict[str, Any]) -> List[str]:
        """Generate detailed analysis for a specific contributor."""
        prs = performance['contributor_prs'].get(contributor, [])
        commits = performance['contributor_commits'].get(contributor, [])
        issues = performance['contributor_issues'].get(contributor, [])
        
        if not (prs or commits or issues):
            return []
        
        total_prs = len(prs)
        total_commits = len(commits)
        total_issues = len(issues)
        total_lines_added = performance['contributor_lines_added'].get(contributor, 0)
        total_lines_removed = performance['contributor_lines_removed'].get(contributor, 0)
        
        section = [
            f"### 👤 {contributor}",
            f"- **Total Pull Requests:** {total_prs}",
            f"- **Total Commits:** {total_commits}",
            f"- **Total Issues:** {total_issues}",
            f"- **Lines Added:** {total_lines_added:,}",
            f"- **Lines Removed:** {total_lines_removed:,}",
            ""
        ]
        
        # Show recent pull requests
        if prs:
            section.append("#### 🔄 Recent Pull Requests")
            recent_prs = sorted(prs, key=lambda x: x['updated_at'], reverse=True)[:10]
            section.extend([
                "| Repository | PR | State | Lines | Title |",
                "|------------|-------|-------|--------|-------|"
            ])
            
            for pr in recent_prs:
                title = pr['title'][:40] + "..." if len(pr['title']) > 40 else pr['title']
                state_emoji = "✅" if pr['state'] == 'closed' and pr['merged_at'] else "❌" if pr['state'] == 'closed' else "🔄"
                additions = pr.get('additions', 0)
                deletions = pr.get('deletions', 0)
                lines_change = f"+{additions}/-{deletions}" if additions > 0 or deletions > 0 else "No data"
                section.append(f"| {pr['repo']} | [#{pr['number']}]({pr['url']}) | {state_emoji} {pr['state']} | {lines_change} | {title} |")
            section.append("")
        
        # Show repository contributions
        repo_contributions = defaultdict(int)
        for pr in prs:
            repo_contributions[pr['repo']] += 1
        for commit in commits:
            repo_contributions[commit['repo']] += 1
        for issue in issues:
            repo_contributions[issue['repo']] += 1
        
        if repo_contributions:
            section.append("#### 📁 Repository Contributions")
            for repo, count in sorted(repo_contributions.items(), key=lambda x: x[1], reverse=True):
                section.append(f"- **{repo}:** {count} contributions")
            section.append("")
        
        return section

    def generate_quarterly_report(self, performance: Dict[str, Any], year: int, quarter: int, start_date: str, end_date: str) -> str:
        """Generate the complete quarterly GitHub report."""
        report = [
            f"## 📊 QUARTERLY GITHUB CONTRIBUTOR REPORT: Q{quarter} {year}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Quarter Period:** {start_date} to {end_date}",
            ""
        ]
        
        # Add overview section
        report.extend(self.generate_quarterly_overview(performance, year, quarter))
        
        # Add repository activity summary
        if performance['repository_activity']:
            report.append("#### 📈 Repository Activity Summary")
            sorted_repos = sorted(performance['repository_activity'].items(), 
                                key=lambda x: x[1], reverse=True)
            for repo, activity in sorted_repos:
                report.append(f"- **{repo}:** {activity} total activities")
            report.append("")
        
        # Add individual contributor details
        report.append("## 👥 INDIVIDUAL CONTRIBUTOR DETAILS")
        report.append("")
        
        # Get all contributors sorted by total activity
        all_contributors = set()
        all_contributors.update(performance['contributor_pr_counts'].keys())
        all_contributors.update(performance['contributor_commit_counts'].keys())
        all_contributors.update(performance['contributor_issue_counts'].keys())
        
        contributors_by_activity = []
        for contributor in all_contributors:
            total_activity = (performance['contributor_pr_counts'].get(contributor, 0) +
                            performance['contributor_commit_counts'].get(contributor, 0) +
                            performance['contributor_issue_counts'].get(contributor, 0))
            contributors_by_activity.append((contributor, total_activity))
        
        contributors_by_activity.sort(key=lambda x: x[1], reverse=True)
        
        for contributor, _ in contributors_by_activity:
            contributor_section = self.generate_contributor_details(contributor, performance)
            report.extend(contributor_section)
        
        # Add footer
        report.extend([
            "---",
            "",
            f"### ✅ Q{quarter} {year} GitHub Contributor Report Complete",
            "",
            "*This quarterly report was generated automatically from GitHub repository data.*",
            f"*Report covers the period from {start_date} to {end_date}*",
            f"*Focus: Individual contributor performance and code contribution tracking*"
        ])
        
        return "\n".join(report)

    def generate_quarterly_summary(self, year: int, quarter: int) -> str:
        """Generate the complete GitHub quarterly summary."""
        print("🚀 Initializing GitHub API connection...")
        
        # Calculate the exact date range for the specified quarter
        start_date, end_date = get_quarter_range(year, quarter)
        
        # Collect data from all repositories
        all_data = {
            'pull_requests': {},
            'commits': {},
            'issues': {}
        }
        
        for repo in self.repositories:
            repo_name = f"{self.github_org}/{repo}" if self.github_org else repo
            
            try:
                all_data['pull_requests'][repo_name] = self.fetch_pull_requests(repo_name, start_date, end_date)
                all_data['commits'][repo_name] = self.fetch_commits(repo_name, start_date, end_date)
                all_data['issues'][repo_name] = self.fetch_issues(repo_name, start_date, end_date)
            except Exception as e:
                print(f"⚠️  Warning: Failed to fetch data for {repo_name}: {e}")
                continue
        
        # Calculate totals
        total_prs = sum(len(prs) for prs in all_data['pull_requests'].values())
        total_commits = sum(len(commits) for commits in all_data['commits'].values())
        total_issues = sum(len(issues) for issues in all_data['issues'].values())
        
        print(f"📊 Found {total_prs} pull requests, {total_commits} commits, {total_issues} issues")
        
        if total_prs == 0 and total_commits == 0 and total_issues == 0:
            return f"No GitHub activity found for Q{quarter} {year} ({start_date} to {end_date})"
        
        # Analyze contributor performance
        performance = self.analyze_contributor_performance(all_data)
        
        # Generate the complete report
        return self.generate_quarterly_report(performance, year, quarter, start_date, end_date)


def parse_quarter_args() -> Tuple[int, int]:
    """Parse command line arguments to determine target year and quarter."""
    if len(sys.argv) >= 3:
        try:
            year = int(sys.argv[1])
            quarter = int(sys.argv[2])
            if quarter not in [1, 2, 3, 4]:
                raise ValueError("Quarter must be 1, 2, 3, or 4")
            return year, quarter
        except ValueError as e:
            print(f"❌ Invalid arguments: {e}")
            sys.exit(1)
    else:
        # Use current quarter if no arguments provided
        year, quarter = get_current_quarter()
        print(f"📅 Using current quarter: Q{quarter} {year}")
        return year, quarter


def generate_quarterly_pr_lead_time_analysis(config: Dict[str, Any], year: int, quarter: int) -> str:
    """
    Generate quarterly PR lead time analysis with trend insights.
    
    Args:
        config: Configuration dictionary with GitHub settings
        year: Year for the quarter
        quarter: Quarter number (1-4)
        
    Returns:
        str: Markdown section with quarterly PR lead time analysis
    """
    try:
        # Get quarter date range
        start_date, end_date = get_quarter_range(year, quarter)
        
        # Initialize GitHub client
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            return "\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n*Error: GITHUB_TOKEN not configured*\n"
        
        # Get configuration values
        repositories = config.get('repositories', [])
        github_org = config.get('github_org', config.get('github', {}).get('org', ''))
        min_lines_changed = config.get('thresholds', {}).get('delivery', {}).get('min_lines_changed', 5)
        
        if not repositories:
            return "\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n*No repositories configured for analysis*\n"
        
        print(f"🚀 Computing quarterly PR lead time analysis...")
        
        # Collect all merged PRs from the quarter
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
            
            # Filter PRs merged in our quarter date range and fetch detailed info
            for pr in prs:
                if pr.get('merged_at'):
                    merged_date = pr['merged_at'][:10]  # Extract YYYY-MM-DD
                    if start_date <= merged_date <= end_date:
                        # Fetch detailed PR info to get additions/deletions
                        try:
                            detail_url = f"https://api.github.com/repos/{repo_path}/pulls/{pr['number']}"
                            detail_response = requests.get(detail_url, headers=headers)
                            if detail_response.status_code == 200:
                                detail_data = detail_response.json()
                                pr['additions'] = detail_data.get('additions', 0)
                                pr['deletions'] = detail_data.get('deletions', 0)
                                pr['changed_files'] = detail_data.get('changed_files', 0)
                            else:
                                # Fallback if we can't get details
                                pr['additions'] = 0
                                pr['deletions'] = 0
                                pr['changed_files'] = 0
                        except Exception:
                            # Fallback if we can't get details
                            pr['additions'] = 0
                            pr['deletions'] = 0
                            pr['changed_files'] = 0
                        
                        all_prs.append(pr)
        
        # Compute overall quarter statistics
        quarter_stats = compute_pr_lead_time_stats(all_prs, min_lines_changed)
        
        if quarter_stats['count'] == 0:
            return f"\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n*No merged PRs with ≥{min_lines_changed} lines changed found in Q{quarter} {year}*\n"
        
        # Build the section
        section = f"\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n"
        section += f"**Analysis Period:** Q{quarter} {year} ({start_date} to {end_date})\n"
        section += f"**Merged PRs Analyzed:** {quarter_stats['count']} PRs (≥{min_lines_changed} lines changed)\n\n"
        
        # Quarter summary statistics
        avg_formatted = format_lead_time_duration(quarter_stats['avg'])
        median_formatted = format_lead_time_duration(quarter_stats['median']) 
        p90_formatted = format_lead_time_duration(quarter_stats['p90'])
        
        section += f"**📊 Quarter Summary**\n"
        section += f"- **Average Lead Time:** {avg_formatted}\n"
        section += f"- **Median Lead Time:** {median_formatted}\n" 
        section += f"- **90th Percentile:** {p90_formatted}\n\n"
        
        # Monthly breakdown for trend analysis (if we have enough data)
        if quarter_stats['count'] >= 10:
            section += f"**📈 Monthly Trend Analysis**\n"
            
            # Group PRs by month within the quarter
            monthly_stats = {}
            quarter_months = []
            
            # Determine which months are in this quarter
            quarter_start_month = (quarter - 1) * 3 + 1
            for month_offset in range(3):
                month_num = quarter_start_month + month_offset
                if month_num <= 12:
                    quarter_months.append(month_num)
            
            for month in quarter_months:
                month_prs = []
                month_start = f"{year}-{month:02d}-01"
                
                # Find last day of month (simple approximation)
                if month in [1, 3, 5, 7, 8, 10, 12]:
                    last_day = 31
                elif month in [4, 6, 9, 11]:
                    last_day = 30
                else:  # February
                    last_day = 29 if year % 4 == 0 else 28
                
                month_end = f"{year}-{month:02d}-{last_day:02d}"
                
                for pr in all_prs:
                    if pr.get('merged_at'):
                        merged_date = pr['merged_at'][:10]
                        if month_start <= merged_date <= month_end:
                            month_prs.append(pr)
                
                if month_prs:
                    month_stat = compute_pr_lead_time_stats(month_prs, min_lines_changed)
                    if month_stat['count'] > 0:
                        monthly_stats[month] = month_stat
            
            if monthly_stats:
                section += "| Month | PRs | Median Lead Time | Trend |\n"
                section += "|-------|-----|------------------|-------|\n"
                
                month_names = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                             7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
                
                prev_median = None
                for month in sorted(monthly_stats.keys()):
                    stats = monthly_stats[month]
                    median_str = format_lead_time_duration(stats['median'])
                    
                    # Simple trend indicator
                    trend = "—"
                    if prev_median is not None:
                        if stats['median'] < prev_median * 0.9:
                            trend = "📉 Improving"
                        elif stats['median'] > prev_median * 1.1:
                            trend = "📈 Increasing"
                        else:
                            trend = "➡️ Stable"
                    
                    section += f"| {month_names[month]} | {stats['count']} | {median_str} | {trend} |\n"
                    prev_median = stats['median']
                
                section += "\n"
        
        # Top performers (fastest PRs) 
        if quarter_stats['fastest']:
            section += f"#### ⚡ Quarter's Fastest PRs (Top 5)\n\n"
            section += "| PR | Author | Lead Time | Lines | Title |\n"
            section += "|-------|--------|-----------|-------|-------|\n"
            
            for pr in quarter_stats['fastest'][:5]:
                lead_time_str = format_lead_time_duration(pr['lead_time_hours'])
                lines_changed = pr['additions'] + pr['deletions']
                title = pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title']
                section += f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {lead_time_str} | {lines_changed} | {title} |\n"
            section += "\n"
        
        return section
        
    except Exception as e:
        return f"\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n*Error computing quarterly PR lead time analysis: {e}*\n"


def main():
    """Main entry point for the GitHub quarterly summary generator."""
    try:
        # Parse command line arguments
        year, quarter = parse_quarter_args()
        
        print(f"🚀 Generating GitHub quarterly summary for Q{quarter} {year}")
        print("=" * 60)
        
        # Check for optional custom configuration file
        config_file = 'config/github_config.yaml'
        if len(sys.argv) >= 4 and sys.argv[3].endswith('.yaml'):
            config_file = sys.argv[3]
            print(f"📝 Using custom config file: {config_file}")
        
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
        summary_generator = GitHubQuarterlySummary(config_file)
        
        # Generate the complete quarterly report
        report = summary_generator.generate_quarterly_summary(year, quarter)
        
        # Add quarterly PR lead time analysis if enabled
        if enable_pr_lead_time:
            pr_lead_time_section = generate_quarterly_pr_lead_time_analysis(config, year, quarter)
            report += pr_lead_time_section
        
        # TODO: Future quarterly GitHub metrics sections (Phase 2+)
        # if enable_review_depth:
        #     report += generate_quarterly_review_depth_trends(config, year, quarter)
        
        # Append active configuration block
        config_block = render_active_config(config)
        full_report = report + config_block
        
        # Save the report
        quarter_filename = f"github_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(full_report, quarter_filename)
        
        # Display the report and completion message
        print("\n" + full_report)
        print(f"\n📊 GitHub quarterly summary complete! Saved to: {filepath}")
        
    except Exception as e:
        print(f"❌ Error generating GitHub quarterly summary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
