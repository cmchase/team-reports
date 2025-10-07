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


def compute_pr_lead_time_stats(prs: List[Dict[str, Any]], min_lines_changed: int = 5) -> Dict[str, Any]:
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
    
    for pr in prs:
        # Skip if not merged
        if not pr.get('merged_at'):
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
                'author': pr.get('user', {}).get('login', 'Unknown'),
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
