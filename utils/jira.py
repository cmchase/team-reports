#!/usr/bin/env python3
"""
JIRA utilities for ticket fetching and query building.

This module provides reusable functions for connecting to JIRA,
building JQL queries, and fetching tickets with various filters.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from jira import JIRA


def initialize_jira_client() -> JIRA:
    """
    Initialize and return a JIRA client connection.
    
    Returns:
        JIRA: Authenticated JIRA client instance
        
    Raises:
        ValueError: If required environment variables are missing
        Exception: If connection to JIRA fails
        
    Environment Variables Required:
        - JIRA_SERVER: JIRA server URL
        - JIRA_EMAIL: User email for authentication  
        - JIRA_API_TOKEN: API token for authentication
    """
    server = os.getenv("JIRA_SERVER")
    email = os.getenv("JIRA_EMAIL")
    api_token = os.getenv("JIRA_API_TOKEN")
    
    if not server or not email or not api_token:
        raise ValueError("Missing required environment variables: JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN")
    
    try:
        jira_client = JIRA(
            server=server,
            token_auth=api_token
        )
        print("✅ Connected to Jira")
        return jira_client
        
    except Exception as e:
        print(f"❌ Failed to connect to Jira: {e}")
        raise


def build_jql_with_dates(base_jql: str, start_date: str, end_date: str, 
                        config: Optional[Dict[str, Any]] = None,
                        status_filter_type: str = 'completed') -> str:
    """
    Build JQL query with date range filter and optional status filters.
    
    Args:
        base_jql: Base JQL query (projects, assignees, etc.)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        config: Optional configuration dict with status_filters and report_settings
        status_filter_type: Which status filter to use from config['status_filters']
                           (e.g., 'execution', 'completed', 'planned')
        
    Returns:
        str: Complete JQL query with date filters and ordering
        
    Status Filter Logic:
        Uses config['status_filters'][status_filter_type] to include only tickets
        matching the specified filter criteria. Defaults to 'completed' for
        finished work states.
        
    Example:
        jql = build_jql_with_dates(
            "project = MYPROJ AND assignee = currentUser()",
            "2025-01-01", 
            "2025-01-07",
            {"status_filters": {"completed": ["Closed"]}},
            "completed"
        )
    """
    date_filter = f'resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}"'
    
    # Build filter components
    filters = [f'({base_jql})', f'({date_filter})']
    
    # Add status filter if configured - use configurable filter type
    if config and 'status_filters' in config and status_filter_type in config['status_filters']:
        included_statuses = config['status_filters'][status_filter_type]
        if included_statuses:
            status_list = ', '.join([f'"{status}"' for status in included_statuses])
            status_filter = f'status IN ({status_list})'
            filters.append(f'({status_filter})')
    
    # Get order by from config or use default
    order_by = 'component ASC, resolutiondate DESC'  # Default ordering with resolutiondate
    if config and 'report_settings' in config:
        order_by = config['report_settings'].get('order_by', order_by)
    
    return ' AND '.join(filters) + f' ORDER BY {order_by}'


def fetch_tickets(jira_client: JIRA, jql: str, max_results: int = 200) -> List[Any]:
    """
    Fetch tickets from JIRA using the provided JQL query.
    
    Args:
        jira_client: Authenticated JIRA client instance
        jql: JQL query string
        max_results: Maximum number of results to return (default: 200)
        
    Returns:
        List[Any]: List of JIRA issue objects
        
    Example:
        jql = "project = MYPROJ AND status != Closed"
        tickets = fetch_tickets(jira_client, jql, max_results=100)
    """
    print(f"🔍 Executing JQL query...")
    print(f"📝 JQL: {jql}")
    
    try:
        issues = jira_client.search_issues(jql, maxResults=max_results)
        print(f"📊 Found {len(issues)} tickets")
        return issues
    except Exception as e:
        print(f"❌ Error fetching tickets: {e}")
        return []


def fetch_tickets_for_date_range(jira_client: JIRA, base_jql: str, start_date: str, 
                                end_date: str, config: Optional[Dict[str, Any]] = None,
                                status_filter_type: str = 'completed') -> List[Any]:
    """
    Convenience function to build JQL and fetch tickets for a date range.
    
    Args:
        jira_client: Authenticated JIRA client instance
        base_jql: Base JQL query
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        config: Optional configuration for filters and settings
        status_filter_type: Which status filter to use from config['status_filters']
                           (e.g., 'execution', 'completed', 'planned')
        
    Returns:
        List[Any]: List of JIRA issue objects
    """
    # Get max results from config
    max_results = 200  # Default
    if config and 'report_settings' in config:
        max_results = config['report_settings'].get('max_results', max_results)
    
    # Build JQL and fetch tickets
    jql = build_jql_with_dates(base_jql, start_date, end_date, config, status_filter_type)
    return fetch_tickets(jira_client, jql, max_results)


def get_jira_server_url(jira_client: JIRA) -> str:
    """
    Get the server URL from a JIRA client instance.
    
    Args:
        jira_client: JIRA client instance
        
    Returns:
        str: JIRA server URL
    """
    return jira_client.server_url


def validate_jira_connection(jira_client: JIRA) -> bool:
    """
    Validate that the JIRA connection is working.
    
    Args:
        jira_client: JIRA client instance
        
    Returns:
        bool: True if connection is valid, False otherwise
    """
    try:
        # Try to get server info as a connectivity test
        jira_client.server_info()
        return True
    except Exception:
        return False


def compute_cycle_time_days(issue: Any, states_done: List[str], 
                           state_in_progress: str = "In Progress") -> Optional[float]:
    """
    Compute cycle time in days for a JIRA issue.
    
    Cycle time is measured from the first transition into 'In Progress' 
    to the first time the issue reaches any 'Done' state.
    
    Args:
        issue: JIRA issue object with changelog/history
        states_done: List of status names considered "done" (e.g., ["Closed", "Done"])
        state_in_progress: Status name for "in progress" (default: "In Progress")
        
    Returns:
        Optional[float]: Cycle time in days, or None if transitions are missing
        
    Examples:
        cycle_time = compute_cycle_time_days(issue, ["Closed", "Done"], "In Progress")
        # Returns 3.5 for an issue that took 3.5 days from In Progress to Done
        
        cycle_time = compute_cycle_time_days(issue, ["Closed"])  
        # Returns None if issue never reached In Progress or Done states
    """
    try:
        # Get changelog from issue (expand='changelog' needed when fetching)
        if not hasattr(issue, 'changelog') or not issue.changelog:
            # Try to get it from the issue object directly
            changelog = getattr(issue, 'changelog', None)
            if not changelog:
                return None
        else:
            changelog = issue.changelog
            
        # Find first transition to In Progress and first transition to Done
        first_in_progress = None
        first_done = None
        
        # Sort histories by created date
        histories = sorted(changelog.histories, key=lambda h: h.created)
        
        for history in histories:
            for item in history.items:
                if item.field == 'status':
                    created_time = datetime.strptime(history.created[:19], '%Y-%m-%dT%H:%M:%S')
                    
                    # Check for first transition TO In Progress
                    if item.toString == state_in_progress and first_in_progress is None:
                        first_in_progress = created_time
                    
                    # Check for first transition TO any Done state
                    if item.toString in states_done and first_done is None:
                        first_done = created_time
                        
                    # If we have both, we can stop looking
                    if first_in_progress and first_done:
                        break
                        
            if first_in_progress and first_done:
                break
        
        # Calculate cycle time if we have both transitions
        if first_in_progress and first_done and first_done > first_in_progress:
            delta = first_done - first_in_progress
            return delta.total_seconds() / (24 * 3600)  # Convert to days
        
        return None
        
    except Exception as e:
        # Return None for any parsing errors
        return None


def fetch_tickets_with_changelog(jira_client: JIRA, jql: str, max_results: int = 200) -> List[Any]:
    """
    Fetch tickets from JIRA with changelog data for cycle time analysis.
    
    Args:
        jira_client: Authenticated JIRA client instance
        jql: JQL query string
        max_results: Maximum number of results to return (default: 200)
        
    Returns:
        List[Any]: List of JIRA issue objects with changelog data
        
    Note:
        This function expands the changelog field to get status transition history
        needed for cycle time calculations.
    """
    print(f"🔍 Executing JQL query with changelog...")
    print(f"📝 JQL: {jql}")
    
    try:
        issues = jira_client.search_issues(
            jql, 
            maxResults=max_results,
            expand='changelog'  # This is key for getting status history
        )
        print(f"📊 Found {len(issues)} tickets with changelog data")
        return issues
    except Exception as e:
        print(f"❌ Error fetching tickets with changelog: {e}")
        return []


def compute_cycle_time_stats(cycle_times: List[float]) -> Dict[str, float]:
    """
    Compute cycle time statistics (average, median, p90) from a list of cycle times.
    
    Args:
        cycle_times: List of cycle times in days
        
    Returns:
        Dict[str, float]: Statistics with keys 'avg', 'median', 'p90'
        
    Example:
        stats = compute_cycle_time_stats([1.0, 2.5, 3.0, 4.0, 10.0])
        # Returns {'avg': 4.1, 'median': 3.0, 'p90': 8.2}
    """
    if not cycle_times:
        return {'avg': 0.0, 'median': 0.0, 'p90': 0.0}
    
    sorted_times = sorted(cycle_times)
    n = len(sorted_times)
    
    # Average
    avg = sum(sorted_times) / n
    
    # Median
    if n % 2 == 0:
        median = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
    else:
        median = sorted_times[n//2]
    
    # P90 (90th percentile)
    p90_index = int(0.9 * n) - 1
    if p90_index >= 0:
        p90 = sorted_times[p90_index]
    else:
        p90 = sorted_times[-1]
    
    return {
        'avg': round(avg, 1),
        'median': round(median, 1), 
        'p90': round(p90, 1)
    }
