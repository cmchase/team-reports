#!/usr/bin/env python3
"""
Shared utilities for ticket processing and categorization.

This module provides reusable functions for working with JIRA tickets,
including categorization logic that can be used across different scripts.
"""

from typing import Dict, Any, List, Optional


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
    # Get ticket details
    components = [comp.name for comp in getattr(issue.fields, 'components', [])]
    project = issue.fields.project.key
    summary = issue.fields.summary.lower()
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
        - components: List of component names
        - updated: Last updated date (YYYY-MM-DD format)
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
        'components': [comp.name for comp in getattr(issue.fields, 'components', [])],
        'updated': str(issue.fields.updated)[:10],  # Just the date part
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
    return [comp.name for comp in getattr(issue.fields, 'components', [])]


def get_ticket_text_content(issue) -> str:
    """
    Get combined searchable text content from a JIRA ticket.
    
    Args:
        issue: JIRA issue object
        
    Returns:
        Combined summary and description text in lowercase
    """
    summary = issue.fields.summary.lower()
    description = (issue.fields.description or "").lower()
    return f"{summary} {description}"
