#!/usr/bin/env python3
"""
GitHub API utilities for repository analysis and metrics calculation.

This module provides functions for computing GitHub-based metrics like PR lead time,
review depth, and other delivery indicators from GitHub API data.
"""

import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import statistics
import re


def is_bot_user(username: str, bot_patterns: List[str]) -> bool:
    """
    Check if a username matches any bot patterns from config.
    
    Args:
        username: GitHub username to check
        bot_patterns: List of regex patterns to match against bot usernames
        
    Returns:
        bool: True if username matches any bot pattern
        
    Examples:
        >>> bot_patterns = ['.*bot.*', 'dependabot', 'github-actions.*']
        >>> is_bot_user('dependabot[bot]', bot_patterns)
        True
        >>> is_bot_user('john-doe', bot_patterns)
        False
    """
    if not username or not bot_patterns:
        return False
        
    username_lower = username.lower()
    
    for pattern in bot_patterns:
        try:
            if re.search(pattern.lower(), username_lower):
                return True
        except re.error:
            # Skip invalid regex patterns
            continue
            
    return False


def compute_pr_review_depth(pr: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, int]:
    """
    Compute review depth metrics for a pull request.
    
    Args:
        pr: GitHub PR object with reviews and review comments
        config: Configuration dict containing bot patterns
        
    Returns:
        Dict containing reviewers_count and review_comments_count
        
    Example:
        >>> config = {'bots': {'patterns': ['.*bot.*', 'dependabot']}}
        >>> pr_data = {
        ...     'reviews': [
        ...         {'user': {'login': 'reviewer1'}},
        ...         {'user': {'login': 'bot-reviewer'}},
        ...         {'user': {'login': 'reviewer2'}}
        ...     ],
        ...     'review_comments': [
        ...         {'user': {'login': 'reviewer1'}},
        ...         {'user': {'login': 'reviewer1'}},
        ...         {'user': {'login': 'bot-reviewer'}}
        ...     ]
        ... }
        >>> metrics = compute_pr_review_depth(pr_data, config)
        >>> print(f"Reviewers: {metrics['reviewers_count']}, Comments: {metrics['review_comments_count']}")
    """
    bot_patterns = config.get('bots', {}).get('patterns', [])
    
    # Count unique reviewers (excluding bots)
    reviewers = set()
    for review in pr.get('reviews', []):
        user = review.get('user', {})
        username = user.get('login', '')
        if username and not is_bot_user(username, bot_patterns):
            reviewers.add(username)
    
    # Count review comments (excluding bots)
    comment_count = 0
    for comment in pr.get('review_comments', []):
        user = comment.get('user', {})
        username = user.get('login', '')
        if username and not is_bot_user(username, bot_patterns):
            comment_count += 1
    
    return {
        'reviewers_count': len(reviewers),
        'review_comments_count': comment_count
    }


def compute_pr_lead_time_hours(pr: Dict[str, Any]) -> Optional[float]:
    """
    Compute PR lead time in hours from first commit to merge.
    
    Args:
        pr: GitHub PR object from API
        
    Returns:
        Optional[float]: Lead time in hours, or None if cannot be computed
        
    Lead time is calculated as:
        - For merged PRs: merged_at - first_commit_timestamp
        - Returns None if PR is not merged or missing required timestamps
        
    Handles squash/rebase merge scenarios by using the merged_at time
    rather than trying to track individual commit merges.
    
    Examples:
        >>> pr_data = {
        ...     'merged_at': '2025-01-15T16:30:00Z',
        ...     'created_at': '2025-01-14T10:15:00Z'  # Fallback if no commits
        ... }
        >>> hours = compute_pr_lead_time_hours(pr_data)
        >>> print(f"Lead time: {hours:.1f} hours")
    """
    try:
        # Only compute lead time for merged PRs
        if not pr.get('merged_at'):
            return None
            
        merged_at_str = pr['merged_at']
        merged_at = datetime.fromisoformat(merged_at_str.replace('Z', '+00:00'))
        
        # Try to get the first commit timestamp from commits API
        # For now, we'll use created_at as a proxy for first commit time
        # In a full implementation, this would fetch commits and use the earliest
        created_at_str = pr.get('created_at')
        if not created_at_str:
            return None
            
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        
        # Calculate lead time in hours
        lead_time_delta = merged_at - created_at
        lead_time_hours = lead_time_delta.total_seconds() / 3600
        
        # Sanity check: negative lead time indicates data issues
        if lead_time_hours < 0:
            return None
            
        return lead_time_hours
        
    except (ValueError, KeyError, TypeError) as e:
        # Handle parsing errors, missing fields, or type mismatches
        return None


def compute_pr_lead_time_with_commits(pr: Dict[str, Any], github_token: str, 
                                    github_org: str = "") -> Optional[float]:
    """
    Compute PR lead time using actual first commit timestamp.
    
    Args:
        pr: GitHub PR object from API
        github_token: GitHub API token for making requests
        github_org: GitHub organization name (optional)
        
    Returns:
        Optional[float]: Lead time in hours from first commit to merge
        
    This is a more accurate version that fetches the actual commits
    to find the earliest commit timestamp, rather than using PR created_at.
    """
    try:
        if not pr.get('merged_at'):
            return None
            
        merged_at_str = pr['merged_at']
        merged_at = datetime.fromisoformat(merged_at_str.replace('Z', '+00:00'))
        
        # Build repository path
        repo_name = pr.get('base', {}).get('repo', {}).get('name')
        if not repo_name:
            return None
            
        repo_path = f"{github_org}/{repo_name}" if github_org else repo_name
        
        # Fetch commits for this PR
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        commits_url = f"https://api.github.com/repos/{repo_path}/pulls/{pr['number']}/commits"
        response = requests.get(commits_url, headers=headers)
        
        if response.status_code != 200:
            # Fallback to created_at if we can't fetch commits
            return compute_pr_lead_time_hours(pr)
            
        commits = response.json()
        if not commits:
            return compute_pr_lead_time_hours(pr)
            
        # Find the earliest commit timestamp
        earliest_commit_time = None
        for commit in commits:
            commit_date_str = commit.get('commit', {}).get('author', {}).get('date')
            if commit_date_str:
                commit_date = datetime.fromisoformat(commit_date_str.replace('Z', '+00:00'))
                if earliest_commit_time is None or commit_date < earliest_commit_time:
                    earliest_commit_time = commit_date
        
        if earliest_commit_time is None:
            return compute_pr_lead_time_hours(pr)
            
        # Calculate lead time from first commit to merge
        lead_time_delta = merged_at - earliest_commit_time
        lead_time_hours = lead_time_delta.total_seconds() / 3600
        
        return lead_time_hours if lead_time_hours >= 0 else None
        
    except Exception:
        # Fallback to simpler calculation if anything goes wrong
        return compute_pr_lead_time_hours(pr)


def compute_pr_lead_time_stats(prs: List[Dict[str, Any]], min_lines_changed: int = 5, config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Compute lead time statistics for a list of PRs.
    
    Args:
        prs: List of GitHub PR objects
        min_lines_changed: Minimum lines changed to include PR (filters trivial PRs)
        
    Returns:
        Dict with lead time statistics and PR details
        
    Example:
        >>> stats = compute_pr_lead_time_stats(pr_list, min_lines_changed=10)
        >>> print(f"Median lead time: {stats['median']:.1f} hours")
    """
    # Filter out trivial PRs and collect lead times
    lead_times = []
    qualifying_prs = []
    
    # Get bot patterns for filtering
    bot_patterns = config.get('bots', {}).get('patterns', []) if config else []
    
    for pr in prs:
        # Skip if not merged
        if not pr.get('merged_at'):
            continue
            
        # Skip bot PRs
        author_login = pr.get('user', {}).get('login', 'Unknown')
        if author_login != 'Unknown' and is_bot_user(author_login, bot_patterns):
            continue
            
        # Filter trivial PRs based on lines changed
        additions = pr.get('additions', 0)
        deletions = pr.get('deletions', 0) 
        total_changes = additions + deletions
        
        if total_changes < min_lines_changed:
            continue
            
        # Compute lead time
        lead_time = compute_pr_lead_time_hours(pr)
        if lead_time is not None:
            lead_times.append(lead_time)
            qualifying_prs.append({
                'number': pr['number'],
                'title': pr['title'],
                'author': author_login,
                'url': pr['html_url'],
                'lead_time_hours': lead_time,
                'additions': additions,
                'deletions': deletions
            })
    
    if not lead_times:
        return {
            'count': 0,
            'avg': 0,
            'median': 0,
            'p90': 0,
            'fastest': [],
            'slowest': [],
            'all_prs': []
        }
    
    # Calculate statistics
    avg_lead_time = statistics.mean(lead_times)
    median_lead_time = statistics.median(lead_times)
    p90_lead_time = statistics.quantiles(lead_times, n=10)[8] if len(lead_times) >= 10 else max(lead_times)
    
    # Sort PRs by lead time for fastest/slowest lists
    sorted_prs = sorted(qualifying_prs, key=lambda x: x['lead_time_hours'])
    fastest_prs = sorted_prs[:5]  # Top 5 fastest
    slowest_prs = sorted_prs[-5:][::-1]  # Top 5 slowest (reversed)
    
    return {
        'count': len(lead_times),
        'avg': avg_lead_time,
        'median': median_lead_time,
        'p90': p90_lead_time,
        'fastest': fastest_prs,
        'slowest': slowest_prs,
        'all_prs': qualifying_prs
    }


def is_trivial_pr(pr: Dict[str, Any], min_lines_threshold: int = 5) -> bool:
    """
    Check if a PR should be considered trivial based on lines changed.
    
    Args:
        pr: GitHub PR object
        min_lines_threshold: Minimum total lines changed to be considered non-trivial
        
    Returns:
        bool: True if PR is trivial (should be filtered out)
    """
    additions = pr.get('additions', 0)
    deletions = pr.get('deletions', 0)
    total_changes = additions + deletions
    
    return total_changes < min_lines_threshold


def format_lead_time_duration(hours: float) -> str:
    """
    Format lead time hours into a human-readable duration.
    
    Args:
        hours: Lead time in hours
        
    Returns:
        str: Formatted duration (e.g., "2.5h", "1d 4h", "3d 2h")
    """
    if hours < 24:
        return f"{hours:.1f}h"
    
    days = int(hours // 24)
    remaining_hours = hours % 24
    
    if remaining_hours < 1:
        return f"{days}d"
    else:
        return f"{days}d {remaining_hours:.1f}h"


def generate_pr_lead_time_analysis(
    config: Dict[str, Any], 
    start_date: str, 
    end_date: str,
    report_type: str = "weekly",  # "weekly" or "quarterly"
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    all_prs_data: Optional[Dict[str, List[Dict]]] = None
) -> str:
    """
    Unified PR lead time analysis for both weekly and quarterly reports.
    
    Args:
        config: Configuration dictionary with GitHub settings
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        report_type: "weekly" or "quarterly" for report-specific formatting
        year: Year for quarterly reports (required if report_type="quarterly")
        quarter: Quarter number for quarterly reports (required if report_type="quarterly")
        all_prs_data: Optional pre-fetched PR data to avoid duplicate API calls
        
    Returns:
        str: Markdown section with PR lead time analysis
    """
    try:
        from .github_client import GitHubApiClient
        
        # Get configuration values
        min_lines_changed = config.get('thresholds', {}).get('delivery', {}).get('min_lines_changed', 5)
        repositories = config.get('repositories', [])
        
        if not repositories:
            title = "Weekly" if report_type == "weekly" else f"Q{quarter} {year} Quarterly"
            return f"\n\n### 🚀 Delivery • {title} PR Lead Time\n\n*No repositories configured for analysis*\n"
        
        print(f"🚀 Computing {report_type} PR lead time analysis...")
        
        # Initialize GitHub client
        github_client = GitHubApiClient()
        
        # Get merged PRs for the date range
        all_prs = github_client.get_merged_prs_for_lead_time(start_date, end_date, all_prs_data)
        
        # Compute lead time statistics
        stats = compute_pr_lead_time_stats(all_prs, min_lines_changed, config)
        
        if stats['count'] == 0:
            if report_type == "quarterly":
                return f"\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n*No merged PRs with ≥{min_lines_changed} lines changed found in Q{quarter} {year}*\n"
            else:
                return f"\n\n### 🚀 Delivery • PR Lead Time\n\n*No merged PRs with ≥{min_lines_changed} lines changed found in this period*\n"
        
        # Build the section header based on report type
        if report_type == "quarterly":
            section = f"\n\n### 🚀 Delivery • Quarterly PR Lead Time\n\n"
            section += f"**Analysis Period:** Q{quarter} {year} ({start_date} to {end_date})\n"
            section += f"**Merged PRs Analyzed:** {stats['count']} PRs (≥{min_lines_changed} lines changed)\n\n"
        else:
            section = f"\n\n### 🚀 Delivery • PR Lead Time\n\n"
            section += f"**Merged PRs Analyzed:** {stats['count']} PRs (≥{min_lines_changed} lines changed)\n\n"
        
        # Summary statistics (common to both report types)
        avg_formatted = format_lead_time_duration(stats['avg'])
        median_formatted = format_lead_time_duration(stats['median']) 
        p90_formatted = format_lead_time_duration(stats['p90'])
        
        if report_type == "quarterly":
            section += f"**📊 Quarter Summary**\n"
        else:
            section += f"**📊 Lead Time Summary**\n"
        
        section += f"- **Average:** {avg_formatted}\n"
        section += f"- **Median:** {median_formatted}\n" 
        section += f"- **90th Percentile:** {p90_formatted}\n\n"
        
        # Monthly breakdown for quarterly reports (if enough data)
        if report_type == "quarterly" and stats['count'] >= 10 and quarter and year:
            section += _generate_quarterly_monthly_breakdown(all_prs, year, quarter, min_lines_changed, start_date, end_date)
        
        # Top performers (fastest PRs) - common to both
        if stats['fastest']:
            section += f"#### ⚡ Top 5 Fastest PRs\n\n"
            section += "| PR | Author | Lead Time | Lines | Title |\n"
            section += "|-------|--------|-----------|-------|-------|\n"
            
            for pr in stats['fastest'][:5]:
                lead_time_str = format_lead_time_duration(pr['lead_time_hours'])
                lines_changed = pr['additions'] + pr['deletions']
                title = pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title']
                section += f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {lead_time_str} | {lines_changed} | {title} |\n"
            section += "\n"
        
        # Top 5 slowest PRs (common to both)
        if stats['slowest']:
            section += f"#### 🐌 Top 5 Slowest PRs\n\n"
            section += "| PR | Author | Lead Time | Lines | Title |\n"
            section += "|-------|--------|-----------|-------|-------|\n"
            
            for pr in stats['slowest'][:5]:
                lead_time_str = format_lead_time_duration(pr['lead_time_hours'])
                lines_changed = pr['additions'] + pr['deletions']
                title = pr['title'][:50] + "..." if len(pr['title']) > 50 else pr['title']
                section += f"| [#{pr['number']}]({pr['url']}) | {pr['author']} | {lead_time_str} | {lines_changed} | {title} |\n"
            section += "\n"
        
        return section
        
    except Exception as e:
        error_title = "Quarterly PR Lead Time" if report_type == "quarterly" else "PR Lead Time"
        return f"\n\n### 🚀 Delivery • {error_title}\n\n*Error computing PR lead time analysis: {e}*\n"


def _generate_quarterly_monthly_breakdown(all_prs: List[Dict], year: int, quarter: int, 
                                        min_lines_changed: int, start_date: str, end_date: str) -> str:
    """Generate monthly trend analysis for quarterly reports."""
    section = f"**📈 Monthly Trend Analysis**\n"
    
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
            month_stat = compute_pr_lead_time_stats(month_prs, min_lines_changed, {})
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
    
    return section


def compute_review_depth_stats(prs: List[Dict[str, Any]], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute review depth statistics for a list of PRs.
    
    Args:
        prs: List of GitHub PR objects with reviews and review comments
        config: Configuration dict containing bot patterns
        
    Returns:
        Dict with review depth statistics
        
    Example:
        >>> config = {'bots': {'patterns': ['.*bot.*']}}
        >>> stats = compute_review_depth_stats(pr_list, config)
        >>> print(f"Median reviewers: {stats['median_reviewers']}, Median comments: {stats['median_comments']}")
    """
    reviewers_counts = []
    comments_counts = []
    
    for pr in prs:
        # Only include merged PRs
        if not pr.get('merged_at'):
            continue
            
        depth_metrics = compute_pr_review_depth(pr, config)
        reviewers_counts.append(depth_metrics['reviewers_count'])
        comments_counts.append(depth_metrics['review_comments_count'])
    
    if not reviewers_counts:
        return {
            'count': 0,
            'median_reviewers': 0.0,
            'median_comments': 0.0,
            'avg_reviewers': 0.0,
            'avg_comments': 0.0
        }
    
    return {
        'count': len(reviewers_counts),
        'median_reviewers': statistics.median(reviewers_counts) if reviewers_counts else 0.0,
        'median_comments': statistics.median(comments_counts) if comments_counts else 0.0,
        'avg_reviewers': statistics.mean(reviewers_counts) if reviewers_counts else 0.0,
        'avg_comments': statistics.mean(comments_counts) if comments_counts else 0.0
    }


def generate_review_depth_analysis(
    config: Dict[str, Any], 
    start_date: str, 
    end_date: str,
    report_type: str = "weekly",
    all_prs_data: Optional[Dict[str, List[Dict]]] = None
) -> str:
    """
    Generate review depth analysis section for GitHub reports.
    
    Args:
        config: Configuration dictionary with GitHub settings
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format  
        report_type: "weekly" or "quarterly" for report-specific formatting
        all_prs_data: Optional pre-fetched PR data to avoid duplicate API calls
        
    Returns:
        str: Markdown section with review depth analysis
    """
    try:
        from .github_client import GitHubApiClient
        
        repositories = config.get('repositories', [])
        
        if not repositories:
            return f"\n\n### 📊 Delivery • Review Depth\n\n*No repositories configured for analysis*\n"
        
        print(f"📊 Computing {report_type} review depth analysis...")
        
        # Initialize GitHub client if we need to fetch data
        if not all_prs_data:
            github_client = GitHubApiClient()
            all_data = github_client.fetch_all_data(start_date, end_date)
            all_prs_data = all_data['pull_requests']
        
        # Collect all PRs across repositories
        all_prs = []
        for repo_path, prs in all_prs_data.items():
            all_prs.extend(prs)
        
        # Compute review depth statistics
        stats = compute_review_depth_stats(all_prs, config)
        
        if stats['count'] == 0:
            return f"\n\n### 📊 Delivery • Review Depth\n\n*No merged PRs found in this period*\n"
        
        # Build the section
        section = f"\n\n### 📊 Delivery • Review Depth\n\n"
        section += f"**Merged PRs Analyzed:** {stats['count']} PRs\n\n"
        
        # Summary statistics
        section += f"**📈 Review Engagement**\n"
        section += f"- **Median Reviewers per PR:** {stats['median_reviewers']:.1f}\n"
        section += f"- **Median Comments per PR:** {stats['median_comments']:.1f}\n\n"
        
        return section
        
    except Exception as e:
        return f"\n\n### 📊 Delivery • Review Depth\n\n*Error computing review depth analysis: {e}*\n"
