#!/usr/bin/env python3
"""
Base class for Jira summary reports to eliminate code duplication.

This module provides a shared base class for both weekly and quarterly
Jira summary generators, centralizing common functionality.
"""

from typing import Dict, List, Any
from .jira_client import JiraApiClient
from .ticket import categorize_ticket, format_ticket_info


class JiraSummaryBase:
    """Base class for Jira summary generators with shared functionality."""
    
    def __init__(self, config_file: str = 'config/jira_config.yaml'):
        """Initialize the Jira summary generator with configuration."""
        # Initialize the Jira API client
        self.jira_client = JiraApiClient(config_file)
        
        # Extract commonly used config values for convenience
        self.config = self.jira_client.config
        self.base_jql = self.jira_client.base_jql
        self.team_categories = self.config.get('team_categories', {})
    
    def initialize(self):
        """Initialize the Jira client connection."""
        self.jira_client.initialize()
    
    def fetch_tickets(self, start_date: str, end_date: str) -> List[Any]:
        """Fetch tickets for the specified date range."""
        return self.jira_client.fetch_tickets(start_date, end_date)
    
    def categorize_ticket(self, issue) -> str:
        """Categorize a ticket into one of the team categories."""
        return categorize_ticket(issue, self.team_categories)
    
    def format_ticket_info(self, issue) -> Dict[str, str]:
        """Format ticket information for display."""
        return format_ticket_info(issue, self.jira_client.get_server_url(), self.config)
    
    def _get_team_member_name(self, assignee_email: str) -> str:
        """Map assignee email to display name using team configuration."""
        team_members = self.config.get('team_members', {})
        return team_members.get(assignee_email, assignee_email)
