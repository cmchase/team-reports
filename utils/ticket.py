#!/usr/bin/env python3
"""
Shared utilities for ticket processing and categorization.

This module provides reusable functions for working with JIRA tickets,
including categorization logic that can be used across different scripts.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


def get_completion_date(ticket) -> Optional[str]:
    """
    Get the completion date of a ticket, preferring resolutiondate over updated.
    
    Args:
        ticket: JIRA issue object with fields
        
    Returns:
        str: Completion date in YYYY-MM-DD format, or None if neither date is available
        
    Uses resolutiondate if available (more accurate for when ticket was actually completed),
    falls back to updated date if resolutiondate is not set.
    """
    try:
        # First try to use resolutiondate (most accurate for completion)
        if hasattr(ticket.fields, 'resolutiondate') and ticket.fields.resolutiondate:
            resolution_date = ticket.fields.resolutiondate
            # Handle both string and datetime objects
            if isinstance(resolution_date, str):
                return resolution_date.split('T')[0]  # Extract date part
            else:
                return resolution_date.strftime('%Y-%m-%d')
                
        # Fall back to updated date if resolutiondate is not available
        if hasattr(ticket.fields, 'updated') and ticket.fields.updated:
            updated_date = ticket.fields.updated
            # Handle both string and datetime objects
            if isinstance(updated_date, str):
                return updated_date.split('T')[0]  # Extract date part
            else:
                return updated_date.strftime('%Y-%m-%d')
                
    except (AttributeError, ValueError, TypeError):
        pass
        
    return None


def get_completion_datetime(ticket) -> Optional[datetime]:
    """
    Get the completion datetime of a ticket, preferring resolutiondate over updated.
    
    Args:
        ticket: JIRA issue object with fields
        
    Returns:
        datetime: Completion datetime object, or None if neither date is available
        
    Uses resolutiondate if available, falls back to updated date.
    """
    try:
        # First try to use resolutiondate
        if hasattr(ticket.fields, 'resolutiondate') and ticket.fields.resolutiondate:
            resolution_date = ticket.fields.resolutiondate
            if isinstance(resolution_date, str):
                return datetime.fromisoformat(resolution_date.replace('Z', '+00:00'))
            else:
                return resolution_date
                
        # Fall back to updated date
        if hasattr(ticket.fields, 'updated') and ticket.fields.updated:
            updated_date = ticket.fields.updated
            if isinstance(updated_date, str):
                return datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
            else:
                return updated_date
                
    except (AttributeError, ValueError, TypeError):
        pass
        
    return None


def categorize_ticket(issue, team_categories: Dict[str, Dict[str, Any]]) -> str:
    """
    Categorize a JIRA ticket based on team category rules.
    
    Args:
        issue: JIRA issue object with fields like components, project, summary, description
        team_categories: Dictionary of category rules with structure:
            {
                "Category Name": {
                    "components": ["Component1", "Component2"],  # Optional
                    "projects": ["PROJECT_KEY"],                 # Optional  
                    "keywords": ["keyword1", "keyword2"],        # Optional
                    "description": "Human readable description"
                }
            }
    
    Returns:
        str: Category name that matches the ticket, or 'Other' if no match found
        
    Example:
        team_categories = {
            "Backend Development": {
                "components": ["Backend", "API"],
                "keywords": ["database", "service"],
                "description": "Backend services and API development"
            }
        }
        category = categorize_ticket(jira_issue, team_categories)
    """
    # Get ticket details with None handling
    components_field = getattr(issue.fields, 'components', [])
    components = [comp.name for comp in (components_field or [])]
    project = issue.fields.project.key
    summary = (issue.fields.summary or "").lower()
    description = (issue.fields.description or "").lower()
    
    # Check each category
    for category_name, rules in team_categories.items():
        # Check keywords in summary/description
        if 'keywords' in rules:
            text_to_search = f"{summary} {description}"
            if any(keyword.lower() in text_to_search for keyword in rules['keywords']):
                return category_name

        # Check components
        if 'components' in rules:
            if any(comp in components for comp in rules['components']):
                return category_name
                
        # Check projects
        if 'projects' in rules:
            if project in rules['projects']:
                return category_name
             
    # Default category for uncategorized tickets
    return 'Other'


def format_ticket_info(issue, jira_server_url: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Format ticket information for display in reports.
    
    Args:
        issue: JIRA issue object
        jira_server_url: Base URL of the JIRA server for creating ticket links
        config: Optional configuration for team member name lookup
        
    Returns:
        Dict containing formatted ticket information:
        - key: Ticket key (e.g., "PROJECT-123")
        - summary: Ticket title/summary
        - status: Current status name
        - assignee: Assignee display name or 'Unassigned'
        - priority: Priority name or 'None'
        - story_points: Story points value (0 if not set)
        - components: List of component names
        - updated: Completion date (resolutiondate preferred, fallback to updated date) in YYYY-MM-DD format
        - url: Direct link to the ticket
    """
    # Get assignee email first
    assignee_email = issue.fields.assignee.emailAddress if issue.fields.assignee else None
    
    # Determine display name for assignee
    if not assignee_email:
        assignee_display = 'Unassigned'
    elif config:
        # Use team member mapping if available
        from utils.config import get_team_member_name
        assignee_display = get_team_member_name(config, assignee_email)
    else:
        # Fallback to JIRA display name or email
        assignee_display = issue.fields.assignee.displayName if issue.fields.assignee else 'Unassigned'
    
    return {
        'key': issue.key,
        'summary': issue.fields.summary,
        'status': issue.fields.status.name,
        'assignee': assignee_display,
        'assignee_email': assignee_email or '',
        'priority': issue.fields.priority.name if issue.fields.priority else 'None',
        'story_points': int(getattr(issue.fields, 'customfield_12310243', None) or getattr(issue.fields, 'storypoints', None) or 0),
        'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
        'updated': get_completion_date(issue) or str(issue.fields.updated)[:10],  # Use completion date (resolutiondate preferred)
        'url': f"{jira_server_url}/browse/{issue.key}"
    }


def get_ticket_components(issue) -> List[str]:
    """
    Extract component names from a JIRA ticket.
    
    Args:
        issue: JIRA issue object
        
    Returns:
        List of component names
    """
    components_field = getattr(issue.fields, 'components', [])
    return [comp.name for comp in (components_field or [])]


def get_ticket_text_content(issue) -> str:
    """
    Get combined searchable text content from a JIRA ticket.
    
    Args:
        issue: JIRA issue object
        
    Returns:
        Combined summary and description text in lowercase
    """
    summary = (issue.fields.summary or "").lower()
    description = (issue.fields.description or "").lower()
    return f"{summary} {description}".strip()
