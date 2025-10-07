#!/usr/bin/env python3
"""
Shared Jira API client for eliminating code duplication.

This module provides a centralized Jira API client that can be shared
between weekly summaries, quarterly summaries, and other Jira operations.
"""

import os
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from jira import JIRA

from .config import get_config
from .jira import initialize_jira_client, fetch_tickets_for_date_range

# Load environment variables
load_dotenv()


class JiraApiClient:
    """Centralized Jira API client with common operations."""
    
    def __init__(self, config_file: str = 'config/jira_config.yaml'):
        """Initialize the Jira API client with configuration."""
        # Initialize JIRA client as None - will be set up later in initialize()
        self.jira_client = None
        
        # Load configuration
        self.config = get_config([config_file])
        
        # Extract commonly used config values
        self.base_jql = self.config['base_jql']
    
    def initialize(self):
        """Initialize the Jira client connection using environment variables."""
        # Set up JIRA client using credentials from environment variables (.env file)
        # This handles authentication and connection validation
        self.jira_client = initialize_jira_client()
    
    def fetch_tickets(self, start_date: str, end_date: str) -> List[Any]:
        """Fetch tickets for the specified date range."""
        print(f"🔍 Searching tickets from {start_date} to {end_date}...")
        
        # Get default status filter from config, fallback to 'completed'
        default_filter = self.config.get('report_settings', {}).get('default_status_filter', 'completed')
        return fetch_tickets_for_date_range(self.jira_client, self.base_jql, start_date, end_date, self.config, default_filter)
    
    def get_server_url(self) -> str:
        """Get the Jira server URL for link generation."""
        return self.jira_client.server_url if self.jira_client else ""
