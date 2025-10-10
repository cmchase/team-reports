#!/usr/bin/env python3
"""
Engineer Performance Analysis utilities for longitudinal tracking.

This module provides functions for collecting, aggregating, and analyzing
engineer performance data across quarters with weekly granularity.

Key features:
- Weekly data collection from GitHub and Jira APIs
- Trend analysis and performance trajectory calculation
- Coaching insights generation based on configurable thresholds
- Cross-engineer collaboration analysis
"""

import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, Counter

from .date import get_quarter_range
from .github_client import GitHubApiClient
from .jira_client import JiraApiClient


def generate_weekly_date_ranges(year: int, quarter: int) -> List[Tuple[str, str]]:
    """
    Generate weekly date ranges for a given quarter.
    
    Args:
        year: Year (e.g., 2025)
        quarter: Quarter number (1-4)
        
    Returns:
        List of (start_date, end_date) tuples for each week in the quarter
        
    Example:
        weekly_ranges = generate_weekly_date_ranges(2025, 2)
        # Returns [('2025-04-07', '2025-04-13'), ('2025-04-14', '2025-04-20'), ...]
    """
    start_date_str, end_date_str = get_quarter_range(year, quarter)
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    weekly_ranges = []
    current_monday = start_date - timedelta(days=start_date.weekday())  # Get Monday of first week
    
    while current_monday <= end_date:
        week_start = max(current_monday, start_date)
        week_end = min(current_monday + timedelta(days=6), end_date)
        
        weekly_ranges.append((
            week_start.strftime('%Y-%m-%d'),
            week_end.strftime('%Y-%m-%d')
        ))
        
        current_monday += timedelta(days=7)
    
    return weekly_ranges


def collect_weekly_engineer_data(year: int, quarter: int, jira_config_file: str, 
                                github_config_file: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Collect weekly engineer performance data for an entire quarter.
    
    Args:
        year: Year to analyze
        quarter: Quarter number (1-4)
        jira_config_file: Path to Jira configuration file
        github_config_file: Path to GitHub configuration file (optional)
        
    Returns:
        Dictionary mapping engineer names to their weekly performance data:
        {
            "john.doe": {
                "weeks": {
                    "2025-04-07": {"github": {...}, "jira": {...}},
                    "2025-04-14": {"github": {...}, "jira": {...}},
                    ...
                },
                "display_name": "John Doe",
                "total_weeks": 13
            }
        }
    """
    print(f"🔍 Collecting engineer data for Q{quarter} {year}...")
    
    # Load configuration
    from .config import get_config
    jira_config = get_config([jira_config_file])  # Fix: wrap in list
    
    # Initialize clients with proper configuration
    # Use default GitHub config if not specified
    if github_config_file is None:
        github_config_file = 'config/github_config.yaml'
    
    try:
        github_client = GitHubApiClient(github_config_file)
        print(f"✅ Loaded GitHub config with {len(github_client.repositories)} repositories")
    except Exception as e:
        print(f"⚠️  Warning: Could not load GitHub config ({e}). GitHub metrics will be empty.")
        github_client = None
    
    jira_client = JiraApiClient(jira_config_file)
    jira_client.initialize()
    
    # PERFORMANCE OPTIMIZATION: Use quarter-wide date ranges instead of weekly
    from .date import get_quarter_range
    start_date, end_date = get_quarter_range(year, quarter)
    
    print(f"⚡ Performance mode: Collecting data for entire quarter ({start_date} to {end_date})")
    
    # Collect ALL data for the quarter at once
    if github_client:
        print("📊 Fetching GitHub data for entire quarter...")
        github_data = github_client.fetch_all_data(start_date, end_date)
    else:
        github_data = {'pull_requests': {}, 'commits': {}}
    
    print("🎫 Fetching Jira data for entire quarter...")
    jira_tickets = jira_client.fetch_tickets(start_date, end_date)
    
    # Now process the data into weekly buckets
    weekly_ranges = generate_weekly_date_ranges(year, quarter)
    engineer_data = defaultdict(lambda: {"weeks": {}, "display_name": "", "total_weeks": len(weekly_ranges)})
    
    print(f"🔄 Processing data into {len(weekly_ranges)} weekly buckets...")
    
    # Process GitHub data by week
    github_weekly_data = _distribute_github_data_by_week(github_data, weekly_ranges, jira_config)
    
    # Process Jira data by week  
    jira_weekly_data = _distribute_jira_data_by_week(jira_tickets, weekly_ranges, jira_config)
    
    # Merge weekly data
    all_engineers = set(github_weekly_data.keys()) | set(jira_weekly_data.keys())
    
    for engineer in all_engineers:
        engineer_github_weeks = github_weekly_data.get(engineer, {})
        engineer_jira_weeks = jira_weekly_data.get(engineer, {})
        
        # Merge weekly data for this engineer
        for week_start, _ in weekly_ranges:
            engineer_data[engineer]["weeks"][week_start] = {
                "github": engineer_github_weeks.get(week_start, _empty_github_metrics()),
                "jira": engineer_jira_weeks.get(week_start, _empty_jira_metrics())
            }
        
        # Set display name from team members config
        if not engineer_data[engineer]["display_name"]:
            team_members = jira_config.get('team_members', {})
            engineer_data[engineer]["display_name"] = team_members.get(engineer, engineer)
    
    print(f"✅ Data processing complete! Found {len(engineer_data)} engineers")
    return dict(engineer_data)


def _distribute_github_data_by_week(github_data: Dict[str, Any], 
                                   weekly_ranges: List[Tuple[str, str]], 
                                   config: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Distribute GitHub data into weekly buckets by engineer.
    
    Returns:
        {
            "engineer_id": {
                "2025-04-07": {"prs_merged": 2, "commits": 5, ...},
                "2025-04-14": {"prs_merged": 1, "commits": 3, ...},
                ...
            }
        }
    """
    from datetime import datetime
    
    engineer_weekly_data = defaultdict(lambda: defaultdict(lambda: _empty_github_metrics()))
    
    # Process PRs by merge date
    for repo, prs in github_data.get('pull_requests', {}).items():
        for pr in prs:
            author = pr.get('user', {}).get('login', 'unknown')
            if author == 'unknown':
                continue
                
            # Find which week this PR belongs to based on merge date
            merged_at = pr.get('merged_at')
            if not merged_at:
                continue
                
            merged_date = datetime.fromisoformat(merged_at.replace('Z', '+00:00'))
            merged_date_str = merged_date.strftime('%Y-%m-%d')
            
            # Find the matching week
            week_key = None
            for week_start, week_end in weekly_ranges:
                if week_start <= merged_date_str <= week_end:
                    week_key = week_start
                    break
            
            if week_key:
                metrics = engineer_weekly_data[author][week_key]
                metrics['prs_created'] += 1
                if pr.get('merged_at'):
                    metrics['prs_merged'] += 1
                    metrics['lines_added'] += pr.get('additions', 0)
                    metrics['lines_deleted'] += pr.get('deletions', 0)
                    
                    # Add review metrics if available
                    if 'reviews' in pr:
                        from .github import compute_pr_review_depth
                        review_depth = compute_pr_review_depth(pr, config)
                        metrics['reviews_received'] += review_depth.get('reviewers_count', 0)
                        metrics['comments_received'] += review_depth.get('review_comments_count', 0)
                
                # Count reviews given by this engineer
                for review in pr.get('reviews', []):
                    reviewer = review.get('user', {}).get('login')
                    if reviewer and reviewer != author and week_key:
                        engineer_weekly_data[reviewer][week_key]['reviews_given'] += 1
                
                # Count comments given by this engineer
                for comment in pr.get('review_comments', []):
                    commenter = comment.get('user', {}).get('login')
                    if commenter and commenter != author and week_key:
                        engineer_weekly_data[commenter][week_key]['comments_given'] += 1
    
    # Process commits by commit date
    for repo, commits in github_data.get('commits', {}).items():
        for commit in commits:
            author = commit.get('author', {}).get('login')
            if not author:
                continue
                
            # Find which week this commit belongs to
            commit_date = commit.get('commit', {}).get('author', {}).get('date')
            if not commit_date:
                continue
                
            commit_datetime = datetime.fromisoformat(commit_date.replace('Z', '+00:00'))
            commit_date_str = commit_datetime.strftime('%Y-%m-%d')
            
            # Find the matching week
            week_key = None
            for week_start, week_end in weekly_ranges:
                if week_start <= commit_date_str <= week_end:
                    week_key = week_start
                    break
            
            if week_key:
                engineer_weekly_data[author][week_key]['commits'] += 1
    
    # Convert defaultdicts to regular dicts
    return {engineer: dict(weeks) for engineer, weeks in engineer_weekly_data.items()}


def _distribute_jira_data_by_week(tickets: List[Any], 
                                 weekly_ranges: List[Tuple[str, str]], 
                                 config: Dict[str, Any]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Distribute Jira tickets into weekly buckets by engineer based on completion date.
    
    Returns:
        {
            "engineer_email": {
                "2025-04-07": {"tickets_completed": 2, "current_wip": 1, ...},
                "2025-04-14": {"tickets_completed": 1, "current_wip": 2, ...},
                ...
            }
        }
    """
    from datetime import datetime
    
    engineer_weekly_data = defaultdict(lambda: defaultdict(lambda: _empty_jira_metrics()))
    
    # Get team member mapping
    team_members = config.get('team_members', {})
    completed_states = config.get('status_filters', {}).get('completed', ['Closed', 'Done'])
    active_states = config.get('states', {}).get('active', ['In Progress', 'Review'])
    
    for ticket in tickets:
        assignee_email = getattr(ticket.fields.assignee, 'emailAddress', None) if ticket.fields.assignee else None
        if not assignee_email:
            continue
            
        status = ticket.fields.status.name
        
        # For completed tickets, find the week they were completed
        if status in completed_states:
            # Use updated date as proxy for completion date
            updated_str = ticket.fields.updated.split('T')[0]  # Get just the date part
            
            # Find the matching week
            week_key = None
            for week_start, week_end in weekly_ranges:
                if week_start <= updated_str <= week_end:
                    week_key = week_start
                    break
            
            if week_key:
                engineer_weekly_data[assignee_email][week_key]['tickets_completed'] += 1
                
                # Calculate cycle time if possible
                try:
                    from .jira import compute_cycle_time_days
                    states_done = config.get('status_filters', {}).get('completed', ['Closed', 'Done'])
                    state_in_progress = config.get('states', {}).get('in_progress', 'In Progress')
                    
                    cycle_time = compute_cycle_time_days(ticket, states_done, state_in_progress)
                    if cycle_time is not None:
                        engineer_weekly_data[assignee_email][week_key]['cycle_times'].append(cycle_time)
                except Exception:
                    pass  # Skip cycle time if not available
        
        # For active tickets, add to current WIP for latest week
        elif status in active_states:
            # Add to the last week of the quarter
            if weekly_ranges:
                last_week_key = weekly_ranges[-1][0]
                engineer_weekly_data[assignee_email][last_week_key]['current_wip'] += 1
    
    # Calculate average cycle times for each engineer/week
    for engineer, weeks in engineer_weekly_data.items():
        for week_key, metrics in weeks.items():
            if metrics['cycle_times']:
                import statistics
                metrics['avg_cycle_time'] = statistics.mean(metrics['cycle_times'])
            else:
                metrics['avg_cycle_time'] = 0.0
    
    # Convert defaultdicts to regular dicts
    return {engineer: dict(weeks) for engineer, weeks in engineer_weekly_data.items()}


def _extract_github_engineer_metrics(github_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Extract per-engineer metrics from GitHub data."""
    engineer_metrics = defaultdict(lambda: _empty_github_metrics())
    
    # Process pull requests
    for repo, prs in github_data.get('pull_requests', {}).items():
        for pr in prs:
            author = pr.get('user', {}).get('login', 'unknown')
            if author == 'unknown':
                continue
                
            metrics = engineer_metrics[author]
            metrics['prs_created'] += 1
            
            if pr.get('merged_at'):
                metrics['prs_merged'] += 1
                metrics['lines_added'] += pr.get('additions', 0)
                metrics['lines_deleted'] += pr.get('deletions', 0)
                
                # Add review metrics if available
                if 'reviews' in pr:
                    from .github import compute_pr_review_depth
                    review_depth = compute_pr_review_depth(pr, config)
                    metrics['reviews_received'] += review_depth.get('reviewers_count', 0)
                    metrics['comments_received'] += review_depth.get('review_comments_count', 0)
            
            # Count reviews given by this engineer
            for review in pr.get('reviews', []):
                reviewer = review.get('user', {}).get('login')
                if reviewer and reviewer != author:
                    engineer_metrics[reviewer]['reviews_given'] += 1
            
            # Count comments given by this engineer
            for comment in pr.get('review_comments', []):
                commenter = comment.get('user', {}).get('login')
                if commenter and commenter != author:
                    engineer_metrics[commenter]['comments_given'] += 1
    
    # Process commits
    for repo, commits in github_data.get('commits', {}).items():
        for commit in commits:
            author = commit.get('author', {}).get('login')
            if author:
                engineer_metrics[author]['commits'] += 1
    
    return dict(engineer_metrics)


def _extract_jira_engineer_metrics(tickets: List[Any], start_date: str, end_date: str, 
                                  config: Dict[str, Any], jira_client: JiraApiClient) -> Dict[str, Dict[str, Any]]:
    """Extract per-engineer metrics from Jira tickets."""
    engineer_metrics = defaultdict(lambda: _empty_jira_metrics())
    
    # Get team member mapping
    team_members = config.get('team_members', {})
    
    for ticket in tickets:
        assignee_email = getattr(ticket.fields.assignee, 'emailAddress', None) if ticket.fields.assignee else None
        assignee_name = team_members.get(assignee_email, assignee_email) if assignee_email else 'Unassigned'
        
        if assignee_name == 'Unassigned' or not assignee_email:
            continue
            
        metrics = engineer_metrics[assignee_email]
        
        # Check if ticket was completed in this week
        status = ticket.fields.status.name
        completed_states = config.get('status_filters', {}).get('completed', ['Closed', 'Done'])
        
        if status in completed_states:
            metrics['tickets_completed'] += 1
            
            # Calculate cycle time if possible
            try:
                from .jira import compute_cycle_time_days
                states_done = config.get('status_filters', {}).get('completed', ['Closed', 'Done'])
                state_in_progress = config.get('states', {}).get('in_progress', 'In Progress')
                
                cycle_time = compute_cycle_time_days(ticket, states_done, state_in_progress)
                if cycle_time is not None:
                    metrics['cycle_times'].append(cycle_time)
            except Exception:
                pass  # Skip cycle time if not available
        
        # Count current WIP (tickets in active states)
        active_states = config.get('states', {}).get('active', ['In Progress', 'Review'])
        if status in active_states:
            metrics['current_wip'] += 1
    
    # Calculate average cycle times
    for engineer, metrics in engineer_metrics.items():
        if metrics['cycle_times']:
            metrics['avg_cycle_time'] = statistics.mean(metrics['cycle_times'])
        else:
            metrics['avg_cycle_time'] = 0.0
    
    return dict(engineer_metrics)


def _empty_github_metrics() -> Dict[str, Any]:
    """Return empty GitHub metrics structure."""
    return {
        'prs_created': 0,
        'prs_merged': 0,
        'commits': 0,
        'lines_added': 0,
        'lines_deleted': 0,
        'reviews_given': 0,
        'reviews_received': 0,
        'comments_given': 0,
        'comments_received': 0
    }


def _empty_jira_metrics() -> Dict[str, Any]:
    """Return empty Jira metrics structure."""
    return {
        'tickets_completed': 0,
        'current_wip': 0,
        'cycle_times': [],
        'avg_cycle_time': 0.0
    }


def compute_engineer_trends(engineer_data: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Compute performance trends for each engineer.
    
    Args:
        engineer_data: Engineer data from collect_weekly_engineer_data()
        
    Returns:
        Dictionary mapping engineer names to trend analysis:
        {
            "john.doe": {
                "productivity_trend": "increasing",  # increasing/stable/decreasing
                "collaboration_trend": "stable",
                "velocity_trend": "decreasing",
                "trends": {
                    "prs_merged": [1, 2, 3, 2, 4],  # weekly values
                    "tickets_completed": [2, 1, 3, 2, 2]
                }
            }
        }
    """
    trends = {}
    
    for engineer, data in engineer_data.items():
        weeks = data['weeks']
        weekly_data = {}
        
        # Extract time series for key metrics
        metrics_series = {
            'prs_merged': [],
            'commits': [],
            'tickets_completed': [],
            'reviews_given': [],
            'lines_changed': []
        }
        
        # Sort weeks chronologically
        sorted_weeks = sorted(weeks.keys())
        
        for week_date in sorted_weeks:
            week_data = weeks[week_date]
            github = week_data['github']
            jira = week_data['jira']
            
            metrics_series['prs_merged'].append(github['prs_merged'])
            metrics_series['commits'].append(github['commits'])
            metrics_series['tickets_completed'].append(jira['tickets_completed'])
            metrics_series['reviews_given'].append(github['reviews_given'])
            metrics_series['lines_changed'].append(github['lines_added'] + github['lines_deleted'])
        
        # Calculate trends
        engineer_trends = {
            'productivity_trend': _calculate_trend(metrics_series['prs_merged'], metrics_series['tickets_completed']),
            'collaboration_trend': _calculate_trend(metrics_series['reviews_given']),
            'velocity_trend': _calculate_trend(metrics_series['lines_changed']),
            'trends': metrics_series,
            'weekly_totals': {
                'avg_prs_per_week': statistics.mean(metrics_series['prs_merged']) if metrics_series['prs_merged'] else 0,
                'avg_tickets_per_week': statistics.mean(metrics_series['tickets_completed']) if metrics_series['tickets_completed'] else 0,
                'total_prs': sum(metrics_series['prs_merged']),
                'total_tickets': sum(metrics_series['tickets_completed'])
            }
        }
        
        trends[engineer] = engineer_trends
    
    return trends


def _calculate_trend(series: List[float], secondary_series: Optional[List[float]] = None) -> str:
    """
    Calculate trend direction from a time series.
    
    Args:
        series: Primary metric series
        secondary_series: Optional secondary series to combine with primary
        
    Returns:
        "increasing", "stable", or "decreasing"
    """
    if not series or len(series) < 3:
        return "stable"
    
    # Combine series if secondary provided
    if secondary_series and len(secondary_series) == len(series):
        combined_series = [a + b for a, b in zip(series, secondary_series)]
    else:
        combined_series = series
    
    # Remove zeros for better trend detection
    non_zero_values = [x for x in combined_series if x > 0]
    if len(non_zero_values) < 3:
        return "stable"
    
    # Simple trend detection using first half vs second half
    mid_point = len(non_zero_values) // 2
    first_half_avg = statistics.mean(non_zero_values[:mid_point])
    second_half_avg = statistics.mean(non_zero_values[mid_point:])
    
    ratio = second_half_avg / first_half_avg if first_half_avg > 0 else 1.0
    
    if ratio > 1.2:  # 20% increase
        return "increasing"
    elif ratio < 0.8:  # 20% decrease
        return "decreasing"
    else:
        return "stable"


def generate_coaching_insights(engineer_data: Dict[str, Dict[str, Any]], 
                             trends: Dict[str, Dict[str, Any]], 
                             config: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Generate coaching insights based on performance data and trends.
    
    Args:
        engineer_data: Engineer performance data
        trends: Engineer trend analysis
        config: Configuration with coaching thresholds
        
    Returns:
        Dictionary mapping engineer names to lists of coaching insights
    """
    insights = {}
    
    # Get coaching thresholds from config
    thresholds = config.get('coaching', {
        'min_prs_per_week': 1.0,
        'max_wip_threshold': 3,
        'min_review_participation': 0.5,
        'productivity_concern_weeks': 3
    })
    
    for engineer, data in engineer_data.items():
        engineer_insights = []
        trend_data = trends.get(engineer, {})
        weekly_totals = trend_data.get('weekly_totals', {})
        
        # Performance insights
        avg_prs = weekly_totals.get('avg_prs_per_week', 0)
        if avg_prs < thresholds['min_prs_per_week']:
            engineer_insights.append(f"⚠️ Low PR output: {avg_prs:.1f} PRs/week (target: {thresholds['min_prs_per_week']})")
        
        # Collaboration insights
        total_reviews_given = sum(week['github']['reviews_given'] for week in data['weeks'].values())
        total_reviews_received = sum(week['github']['reviews_received'] for week in data['weeks'].values())
        
        if total_reviews_given > 0 and total_reviews_received > 0:
            review_ratio = total_reviews_given / total_reviews_received
            if review_ratio < thresholds['min_review_participation']:
                engineer_insights.append(f"🤝 Low review participation: giving {total_reviews_given} vs receiving {total_reviews_received} reviews")
        elif total_reviews_given == 0 and total_reviews_received > 0:
            engineer_insights.append("🤝 Not participating in code reviews - consider reviewing others' PRs")
        
        # Trend insights
        productivity_trend = trend_data.get('productivity_trend', 'stable')
        if productivity_trend == 'decreasing':
            engineer_insights.append("📉 Productivity trend decreasing - check for blockers or workload issues")
        elif productivity_trend == 'increasing':
            engineer_insights.append("📈 Productivity trend increasing - great momentum!")
        
        # WIP management insights
        recent_wip_levels = []
        sorted_weeks = sorted(data['weeks'].keys())[-4:]  # Last 4 weeks
        for week in sorted_weeks:
            recent_wip_levels.append(data['weeks'][week]['jira']['current_wip'])
        
        avg_recent_wip = statistics.mean(recent_wip_levels) if recent_wip_levels else 0
        if avg_recent_wip > thresholds['max_wip_threshold']:
            engineer_insights.append(f"🚧 High WIP levels: {avg_recent_wip:.1f} tickets (target: <{thresholds['max_wip_threshold']})")
        
        # Activity pattern insights
        active_weeks = sum(1 for week in data['weeks'].values() 
                          if week['github']['prs_merged'] + week['jira']['tickets_completed'] > 0)
        total_weeks = data['total_weeks']
        
        if active_weeks < total_weeks * 0.7:  # Less than 70% active weeks
            engineer_insights.append(f"📅 Limited activity: productive in {active_weeks}/{total_weeks} weeks")
        
        insights[engineer] = engineer_insights
    
    return insights


def format_weekly_metrics_table(engineer: str, data: Dict[str, Any], trends: Dict[str, Any]) -> str:
    """
    Format week-by-week metrics table for an individual engineer.
    
    Args:
        engineer: Engineer identifier
        data: Engineer's weekly data
        trends: Engineer's trend analysis
        
    Returns:
        Formatted markdown table showing weekly metrics
    """
    weeks = data['weeks']
    sorted_weeks = sorted(weeks.keys())
    
    # Create table header
    table = "| Metric | " + " | ".join([f"Week {i+1}" for i in range(len(sorted_weeks))]) + " | Trend |\n"
    table += "|--------|" + "|".join(["--------" for _ in sorted_weeks]) + "|-------|\n"
    
    # Metrics to display
    metrics = [
        ('PRs Merged', 'github', 'prs_merged'),
        ('Commits', 'github', 'commits'),
        ('Tickets Done', 'jira', 'tickets_completed'),
        ('Reviews Given', 'github', 'reviews_given'),
        ('Lines Changed', None, None)  # Special case - calculated
    ]
    
    trend_data = trends.get('trends', {})
    
    for metric_name, source, field in metrics:
        row = f"| **{metric_name}** |"
        
        for week_date in sorted_weeks:
            week_data = weeks[week_date]
            
            if metric_name == 'Lines Changed':
                value = week_data['github']['lines_added'] + week_data['github']['lines_deleted']
            else:
                value = week_data[source][field]
            
            row += f" {value} |"
        
        # Add trend indicator
        if metric_name == 'PRs Merged':
            trend = trends.get('productivity_trend', 'stable')
        elif metric_name == 'Reviews Given':
            trend = trends.get('collaboration_trend', 'stable')
        elif metric_name == 'Lines Changed':
            trend = trends.get('velocity_trend', 'stable')
        else:
            trend = 'stable'
        
        trend_icon = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}[trend]
        row += f" {trend_icon} {trend} |\n"
        
        table += row
    
    return table
