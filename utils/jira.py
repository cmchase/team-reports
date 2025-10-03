#!/usr/bin/env python3
"""
JIRA utilities for ticket fetching and query building.

This module provides reusable functions for connecting to JIRA,
building JQL queries, and fetching tickets with various filters.
"""

import os
from typing import List, Dict, Any, Optional
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
    date_filter = f'updated >= "{start_date}" AND updated <= "{end_date}"'
    
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
    order_by = 'component ASC, updated DESC'  # Default ordering
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
