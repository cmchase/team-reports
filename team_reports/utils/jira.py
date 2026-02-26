#!/usr/bin/env python3
"""
JIRA utilities for ticket fetching and query building.

This module provides reusable functions for connecting to JIRA,
building JQL queries, and fetching tickets with various filters.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from jira import JIRA


def initialize_jira_client(
    jira_server: Optional[str] = None,
    jira_email: Optional[str] = None,
    jira_token: Optional[str] = None
) -> JIRA:
    """
    Initialize and return a JIRA client connection.
    
    Credential Precedence (highest to lowest):
        1. Parameters passed to this function
        2. Environment variables (from os.environ)
        3. .env file (loaded via python-dotenv)
    
    Args:
        jira_server: JIRA server URL (optional, uses env if not provided)
        jira_email: User email for authentication (optional, uses env if not provided)
        jira_token: API token for authentication (optional, uses env if not provided)
    
    Returns:
        JIRA: Authenticated JIRA client instance
        
    Raises:
        ValueError: If required credentials are missing
        Exception: If connection to JIRA fails
        
    Environment Variables (if parameters not provided):
        - JIRA_SERVER: JIRA server URL
        - JIRA_EMAIL: User email for authentication  
        - JIRA_API_TOKEN: API token for authentication
    """
    # Precedence: parameters > environment variables > .env file
    server = jira_server or os.getenv("JIRA_SERVER")
    email = jira_email or os.getenv("JIRA_EMAIL")
    api_token = jira_token or os.getenv("JIRA_API_TOKEN")
    
    if not server or not email or not api_token:
        raise ValueError(
            "Missing required JIRA credentials. Provide via parameters or environment variables: "
            "JIRA_SERVER, JIRA_EMAIL, JIRA_API_TOKEN"
        )
    
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
                        status_filter_type: str = 'completed',
                        updated_since: Optional[str] = None) -> str:
    """
    Build JQL query with date range filter and optional status filters.
    
    Args:
        base_jql: Base JQL query (projects, assignees, etc.)
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        config: Optional configuration dict with status_filters and report_settings
        status_filter_type: Which status filter to use from config['status_filters']
                           (e.g., 'execution', 'completed', 'planned')
        updated_since: Optional ISO8601 datetime; if set, add "updated >= ..." to avoid missing recent updates.
        
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
    if updated_since:
        # Jira accepts "updated >= 'yyyy-MM-dd HH:mm'" or ISO with T
        ts = updated_since.replace("T", " ").replace("Z", "").strip()
        if len(ts) > 19:
            ts = ts[:19]
        filters.append(f'(updated >= "{ts}")')
    
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


def flow_stats(values: List[float]) -> Dict[str, float]:
    """
    Compute flow metrics statistics: avg, median, min, max, std_dev, p85, p95, count.
    Excludes zeros and negatives. Used for cycle time and lead time reporting.
    """
    valid = [v for v in values if v is not None and v >= 0]
    if not valid:
        return {
            "avg": 0.0, "median": 0.0, "min": 0.0, "max": 0.0,
            "std_dev": 0.0, "p85": 0.0, "p95": 0.0, "count": 0,
        }
    n = len(valid)
    sorted_v = sorted(valid)
    avg = sum(sorted_v) / n
    median = (sorted_v[(n - 1) // 2] + sorted_v[n // 2]) / 2 if n > 0 else sorted_v[0]
    min_v = min(sorted_v)
    max_v = max(sorted_v)
    variance = sum((x - avg) ** 2 for x in sorted_v) / n if n else 0
    std_dev = (variance ** 0.5) if variance >= 0 else 0.0
    p85_idx = max(0, int(0.85 * n) - 1)
    p95_idx = max(0, int(0.95 * n) - 1)
    return {
        "avg": round(avg, 2), "median": round(median, 2), "min": round(min_v, 2), "max": round(max_v, 2),
        "std_dev": round(std_dev, 2), "p85": round(sorted_v[p85_idx], 2), "p95": round(sorted_v[p95_idx], 2),
        "count": n,
    }


def format_duration_days(days: float) -> str:
    """Format a duration in days as human-readable (e.g. '2 weeks 3 days' or '< 1 minute')."""
    if days < 0:
        return "0 days"
    if days < 1 / (24 * 60):  # less than 1 minute
        return "< 1 minute"
    if days < 1:
        hours = round(days * 24)
        return f"{hours} hour{'s' if hours != 1 else ''}"
    weeks = int(days // 7)
    remainder_days = int(round(days % 7))
    parts = []
    if weeks > 0:
        parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
    if remainder_days > 0 or not parts:
        parts.append(f"{remainder_days} day{'s' if remainder_days != 1 else ''}")
    return " ".join(parts)


def cycle_and_lead_from_issue(
    issue: Any,
    execution_statuses: List[str],
    completed_statuses: List[str],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Compute cycle time and lead time in days from a Jira issue with changelog.
    Cycle: first transition into any execution status -> first transition into any completed status.
    Lead: issue created -> first transition into any completed status.
    Returns (cycle_days, lead_days); either may be None if not computable.
    """
    try:
        created_str = getattr(issue.fields, "created", None) or ""
        if created_str:
            created_dt = datetime.strptime(created_str[:19], "%Y-%m-%dT%H:%M:%S")
        else:
            created_dt = None
        resolution_str = getattr(issue.fields, "resolutiondate", None) or ""
        resolution_dt = None
        if resolution_str:
            try:
                resolution_dt = datetime.strptime(resolution_str[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                pass
        changelog = getattr(issue, "changelog", None)
        if not changelog or not getattr(changelog, "histories", None):
            if created_dt and resolution_dt:
                lead_days = (resolution_dt - created_dt).total_seconds() / (24 * 3600)
                return (None, lead_days)
            return (None, None)
        histories = sorted(changelog.histories, key=lambda h: h.created)
        first_execution = None
        first_done = None
        for history in histories:
            for item in getattr(history, "items", []):
                if getattr(item, "field", None) != "status":
                    continue
                to_str = (getattr(item, "toString", None) or "").strip()
                if not to_str:
                    continue
                try:
                    created_time = datetime.strptime(history.created[:19], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    continue
                if to_str in execution_statuses and first_execution is None:
                    first_execution = created_time
                if to_str in completed_statuses and first_done is None:
                    first_done = created_time
                if first_execution and first_done:
                    break
            if first_execution and first_done:
                break
        cycle_days = None
        if first_execution and first_done and first_done > first_execution:
            cycle_days = (first_done - first_execution).total_seconds() / (24 * 3600)
        lead_days = None
        if first_done and created_dt:
            lead_days = (first_done - created_dt).total_seconds() / (24 * 3600)
        elif resolution_dt and created_dt:
            lead_days = (resolution_dt - created_dt).total_seconds() / (24 * 3600)
        return (cycle_days, lead_days)
    except Exception:
        return (None, None)


def time_in_state_from_issue(
    issue: Any,
    execution_statuses: List[str],
    completed_statuses: List[str],
) -> Optional[Dict[str, float]]:
    """
    Compute days spent in each execution state between first execution and first done.
    Returns status name -> total days in that state (e.g. {"In Progress": 2.5, "Review": 4.0}),
    or None if changelog missing or cycle not computable.
    """
    try:
        changelog = getattr(issue, "changelog", None)
        if not changelog or not getattr(changelog, "histories", None):
            return None
        histories = sorted(changelog.histories, key=lambda h: h.created)
        transitions: List[Tuple[datetime, str]] = []
        first_execution = None
        first_done = None
        for history in histories:
            for item in getattr(history, "items", []):
                if getattr(item, "field", None) != "status":
                    continue
                to_str = (getattr(item, "toString", None) or "").strip()
                if not to_str:
                    continue
                try:
                    created_time = datetime.strptime(history.created[:19], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    continue
                transitions.append((created_time, to_str))
                if to_str in execution_statuses and first_execution is None:
                    first_execution = created_time
                if to_str in completed_statuses and first_done is None:
                    first_done = created_time
        if first_execution is None or first_done is None or first_done <= first_execution:
            return None
        time_in_state: Dict[str, float] = {s: 0.0 for s in execution_statuses}
        current_state: Optional[str] = None
        entered_at: Optional[datetime] = None
        for time, to_str in transitions:
            if time < first_execution:
                continue
            if time == first_execution and current_state is None:
                current_state = to_str
                entered_at = time
                continue
            if time > first_done:
                break
            if current_state is not None and entered_at is not None and current_state in execution_statuses:
                seg_days = (time - entered_at).total_seconds() / (24 * 3600)
                if seg_days > 0:
                    time_in_state[current_state] = time_in_state.get(current_state, 0) + seg_days
            current_state = to_str
            entered_at = time
        if current_state is not None and entered_at is not None and current_state in execution_statuses and entered_at < first_done:
            seg_days = (first_done - entered_at).total_seconds() / (24 * 3600)
            if seg_days > 0:
                time_in_state[current_state] = time_in_state.get(current_state, 0) + seg_days
        return time_in_state
    except Exception:
        return None


def _status_transitions(issue: Any) -> List[Tuple[datetime, str, str]]:
    """Return sorted list of (transition_time, from_status, to_status) for status field."""
    changelog = getattr(issue, "changelog", None)
    if not changelog or not getattr(changelog, "histories", None):
        return []
    out: List[Tuple[datetime, str, str]] = []
    for history in sorted(changelog.histories, key=lambda h: h.created):
        for item in getattr(history, "items", []):
            if getattr(item, "field", None) != "status":
                continue
            from_str = (getattr(item, "fromString", None) or "").strip()
            to_str = (getattr(item, "toString", None) or "").strip()
            if not to_str:
                continue
            try:
                created_time = datetime.strptime(history.created[:19], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                continue
            out.append((created_time, from_str, to_str))
    return sorted(out, key=lambda x: x[0])


def status_at_datetime(
    issue: Any, dt: datetime, execution_statuses: List[str]
) -> Optional[str]:
    """
    Return the status name at the given datetime from changelog.
    Returns None if changelog missing or no status transitions.
    """
    transitions = _status_transitions(issue)
    if not transitions:
        return None
    status = transitions[0][1]  # initial = fromString of first transition
    for t, _from, to in transitions:
        if t <= dt:
            status = to
        else:
            break
    return status


def fetch_issues_in_execution(
    jira_client: JIRA, base_jql: str, execution_statuses: List[str], max_issues: int = 500
) -> List[Any]:
    """
    Fetch issues currently in an execution status (e.g. In Progress, Review) with changelog.
    Used for daily WIP replay and active WIP aging at period end.
    """
    exec_jql = ", ".join(f'"{s}"' for s in execution_statuses)
    jql = f"({base_jql}) AND status IN ({exec_jql})"
    count_result = jira_client.search_issues(jql, maxResults=0)
    total = getattr(count_result, "total", 0)
    if total == 0:
        return []
    fetch_count = min(total, max_issues)
    issues = jira_client.search_issues(jql, maxResults=fetch_count, expand="changelog")
    return list(issues)


def daily_wip_and_avg_peak(
    completed_issues: List[Any],
    execution_issues: List[Any],
    start_date: str,
    end_date: str,
    execution_statuses: List[str],
) -> Tuple[List[int], Optional[float], Optional[int]]:
    """
    Replay changelog to get WIP at end of each day in [start_date, end_date].
    Returns (daily_wip_counts, average_wip, peak_wip).
    Uses end-of-day (23:59:59) for each calendar day. Only issues with changelog are counted.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        return ([], None, None)
    all_issues = list(completed_issues) + list(execution_issues)
    if not all_issues:
        return ([], None, None)
    days: List[datetime] = []
    d = start_dt
    while d <= end_dt:
        days.append(d.replace(hour=23, minute=59, second=59, microsecond=999999))
        d = d + timedelta(days=1)
    daily_counts: List[int] = []
    for day_end in days:
        count = 0
        for issue in all_issues:
            s = status_at_datetime(issue, day_end, execution_statuses)
            if s and s in execution_statuses:
                count += 1
        daily_counts.append(count)
    if not daily_counts:
        return ([], None, None)
    avg = sum(daily_counts) / len(daily_counts)
    peak = max(daily_counts)
    return (daily_counts, avg, peak)


def wip_aging_at_date(
    issues_with_changelog: List[Any],
    end_date: str,
    execution_statuses: List[str],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    For each issue, if status at end_date was in execution, compute days in that state at end_date.
    Returns buckets: "under_1_week", "1_to_2_weeks", "2_to_4_weeks", "over_4_weeks".
    Each bucket is a list of {"key", "summary", "age_days"}.
    """
    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    except ValueError:
        return {}
    buckets: Dict[str, List[Dict[str, Any]]] = {
        "under_1_week": [],
        "1_to_2_weeks": [],
        "2_to_4_weeks": [],
        "over_4_weeks": [],
    }
    for issue in issues_with_changelog:
        transitions = _status_transitions(issue)
        if not transitions:
            continue
        status = transitions[0][1]
        entered_at: Optional[datetime] = None
        for t, _from, to in transitions:
            if t <= end_dt:
                status = to
                if to in execution_statuses:
                    entered_at = t
                else:
                    entered_at = None
            else:
                break
        if status not in execution_statuses or entered_at is None:
            continue
        age_seconds = (end_dt - entered_at).total_seconds()
        age_days = age_seconds / (24 * 3600)
        key = getattr(issue, "key", "")
        raw_summary = getattr(issue.fields, "summary", None) or ""
        summary = (raw_summary[:60] + ("..." if len(raw_summary) > 60 else "")) if raw_summary else ""
        entry = {"key": key, "summary": summary, "age_days": age_days}
        if age_days < 7:
            buckets["under_1_week"].append(entry)
        elif age_days < 14:
            buckets["1_to_2_weeks"].append(entry)
        elif age_days < 28:
            buckets["2_to_4_weeks"].append(entry)
        else:
            buckets["over_4_weeks"].append(entry)
    return buckets


def fetch_flow_issues(
    jira_client: JIRA, jql: str, max_issues: int
) -> Tuple[int, List[Any]]:
    """
    Fetch total count and issues with changelog for flow metrics.
    Returns (total_throughput, list of issues with changelog).
    """
    count_result = jira_client.search_issues(jql, maxResults=0)
    total_throughput = getattr(count_result, "total", 0)
    if total_throughput == 0:
        return (0, [])
    fetch_count = min(total_throughput, max_issues)
    issues = jira_client.search_issues(jql, maxResults=fetch_count, expand="changelog")
    return (total_throughput, list(issues))
