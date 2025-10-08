#!/usr/bin/env python3
"""
Base class for GitHub summary reports to eliminate code duplication.

This module provides a shared base class for both weekly and quarterly
GitHub summary generators, centralizing common functionality.
"""

from typing import Dict, List, Any, Tuple
from collections import defaultdict
from datetime import datetime

from .github_client import GitHubApiClient
from .github import generate_pr_lead_time_analysis, is_bot_user


class GitHubSummaryBase:
    """Base class for GitHub summary generators with shared functionality."""
    
    def __init__(self, config_file: str = 'config/github_config.yaml'):
        """Initialize the GitHub summary generator with configuration."""
        # Initialize the GitHub API client
        self.github_client = GitHubApiClient(config_file)
        
        # Extract commonly used config values for convenience
        self.config = self.github_client.config
        self.repositories = self.github_client.repositories
        self.github_org = self.github_client.github_org
    
    def _get_contributor_name(self, github_username: str) -> str:
        """Map GitHub username to display name using team configuration."""
        team_members = self.config.get('team_members', {})
        return team_members.get(github_username, github_username)
    
    def _is_bot_contributor(self, github_username: str) -> bool:
        """Check if a GitHub username matches any configured bot patterns."""
        if not github_username:
            return False
        bot_patterns = self.config.get('bots', {}).get('patterns', [])
        return is_bot_user(github_username, bot_patterns)
    
    def _get_pr_comment_count(self, pr: Dict[str, Any]) -> int:
        """Get the number of review comments for a PR, excluding bots."""
        from .github import compute_pr_review_depth
        
        # Only compute if review data is available
        if not pr.get('review_comments'):
            return 0
            
        depth_metrics = compute_pr_review_depth(pr, self.config)
        return depth_metrics['review_comments_count']
    
    def analyze_performance(self, all_data: Dict[str, Dict[str, List[Dict]]]) -> Dict[str, Any]:
        """Analyze GitHub activity data to extract performance metrics."""
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
                author_login = pr.get('user', {}).get('login', 'Unknown')
                
                # Skip bot contributors
                if self._is_bot_contributor(author_login):
                    continue
                    
                author = self._get_contributor_name(author_login)
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
                author_login = author_info.get('login') or author_info.get('name', 'Unknown')
                
                # Skip bot contributors
                if self._is_bot_contributor(author_login):
                    continue
                    
                author = self._get_contributor_name(author_login)
                
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
                author_login = issue.get('user', {}).get('login', 'Unknown')
                
                # Skip bot contributors
                if self._is_bot_contributor(author_login):
                    continue
                    
                author = self._get_contributor_name(author_login)
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
    
    def generate_overview(self, performance: Dict[str, Any], start_date: str, end_date: str, report_type: str = "weekly") -> List[str]:
        """Generate the activity overview section."""
        total_prs = sum(performance['contributor_pr_counts'].values())
        total_commits = sum(performance['contributor_commit_counts'].values())
        total_issues = sum(performance['contributor_issue_counts'].values())
        total_lines_added = sum(performance['contributor_lines_added'].values())
        total_lines_removed = sum(performance['contributor_lines_removed'].values())
        total_contributors = len(set(list(performance['contributor_pr_counts'].keys()) + 
                                   list(performance['contributor_commit_counts'].keys()) +
                                   list(performance['contributor_issue_counts'].keys())))
        
        if report_type == "quarterly":
            title = "QUARTERLY GITHUB CONTRIBUTOR OVERVIEW"
        else:
            title = "WEEKLY GITHUB ACTIVITY OVERVIEW"
        
        overview = [
            f"### 📊 {title}",
            f"- **Total Pull Requests:** {total_prs}",
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
        else:  # quarterly
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
        
        if performance['repository_activity']:
            report.append("#### 📁 Repository Activity Summary")
            sorted_repos = sorted(performance['repository_activity'].items(), 
                                key=lambda x: x[1], reverse=True)
            for repo, activity in sorted_repos:
                report.append(f"- **{repo}:** {activity} total activities")
            report.append("")
        
        return report
    
    def generate_contributor_details(self, performance: Dict[str, Any], report_type: str = "weekly") -> List[str]:
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
                contributor_section = self._generate_contributor_section(contributor, performance, report_type)
                report.extend(contributor_section)
        
        return report
    
    def _generate_contributor_section(self, contributor: str, performance: Dict[str, Any], report_type: str) -> List[str]:
        """Generate a detailed section for an individual contributor."""
        prs = performance['contributor_prs'][contributor]
        commits = performance['contributor_commits'][contributor]
        issues = performance['contributor_issues'][contributor]
        
        if not (prs or commits or issues):  # Only show contributors with activity
            return []
        
        # Calculate totals
        total_lines_added = sum(pr.get('additions', 0) for pr in prs)
        total_lines_removed = sum(pr.get('deletions', 0) for pr in prs)
        
        section = [
            f"### 👤 {contributor}",
            f"- **Pull Requests:** {len(prs)}",
            f"- **Commits:** {len(commits)}",
            f"- **Issues:** {len(issues)}",
        ]
        
        if total_lines_added > 0 or total_lines_removed > 0:
            section.append(f"- **Code Changes:** +{total_lines_added:,}/-{total_lines_removed:,} lines")
        section.append("")

        # Recent Pull Requests
        if prs:
            if report_type == "weekly":
                section.append("#### 🔄 Pull Requests This Week")
                recent_prs = sorted(prs, key=lambda x: x['updated_at'], reverse=True)[:5]
            else:
                section.append("#### 🔄 Recent Pull Requests")
                recent_prs = sorted(prs, key=lambda x: x['updated_at'], reverse=True)[:10]
            
            section.extend([
                "| Repository | PR | State | Lines | Comments | Title |",
                "|------------|-------|-------|--------|----------|-------|"
            ])
            
            for pr in recent_prs:
                title = pr['title'][:40 if report_type == "quarterly" else 60] + ("..." if len(pr['title']) > (40 if report_type == "quarterly" else 60) else "")
                
                # Calculate comment count (excluding bots)
                comment_count = self._get_pr_comment_count(pr)
                
                if report_type == "quarterly":
                    state_emoji = "✅" if pr['state'] == 'closed' and pr['merged_at'] else "❌" if pr['state'] == 'closed' else "🔄"
                    additions = pr.get('additions', 0)
                    deletions = pr.get('deletions', 0)
                    lines_change = f"+{additions}/-{deletions}" if additions > 0 or deletions > 0 else "No data"
                    section.append(f"| {pr['repo']} | [#{pr['number']}]({pr['url']}) | {state_emoji} {pr['state']} | {lines_change} | {comment_count} | {title} |")
                else:
                    lines = f"+{pr.get('additions', 0)}/-{pr.get('deletions', 0)}"
                    section.append(f"| {pr['repo']} | [#{pr['number']}]({pr['url']}) | {pr['state']} | {lines} | {comment_count} | {title} |")
            section.append("")

        # Recent Commits (show top 3)
        if commits:
            section.append("#### 💻 Recent Commits")
            recent_commits = sorted(commits, key=lambda x: x['date'], reverse=True)[:3]
            for commit in recent_commits:
                message = commit['message'].split('\n')[0][:80] + "..." if len(commit['message'].split('\n')[0]) > 80 else commit['message'].split('\n')[0]
                section.append(f"- **{commit['repo']}:** [{commit['sha'][:7]}]({commit['url']}) - {message}")
            section.append("")
        
        # Repository contributions (for quarterly reports)
        if report_type == "quarterly":
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
    
    def add_pr_lead_time_analysis(self, report: str, config: Dict[str, Any], start_date: str, 
                                 end_date: str, report_type: str = "weekly", year: int = None, 
                                 quarter: int = None, pr_data: Dict[str, List[Dict]] = None) -> str:
        """Add PR lead time analysis to the report if enabled."""
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
        
        enable_pr_lead_time = flag("metrics.delivery.pr_lead_time")
        
        if enable_pr_lead_time:
            pr_lead_time_section = generate_pr_lead_time_analysis(
                config, start_date, end_date, report_type, year, quarter, pr_data
            )
            report += pr_lead_time_section
        
        return report
