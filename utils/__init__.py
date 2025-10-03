"""
Utils package for JIRA Weekly Reports

This package contains reusable utilities for generating various types of JIRA reports.

Modules:
    jira: JIRA connection and query utilities
    date: Date parsing and range calculation utilities  
    config: YAML configuration loading and validation utilities
    report: Report formatting and file management utilities
    ticket: Ticket categorization and formatting utilities

Usage:
    from utils.jira import initialize_jira_client, fetch_tickets_for_date_range
    from utils.ticket import categorize_ticket, format_ticket_info
    from utils.date import parse_date_args, get_current_week
    from utils.config import load_config
    from utils.report import create_summary_report, save_report
"""

# Expose commonly used functions for convenience
from .jira import initialize_jira_client, fetch_tickets_for_date_range
from .ticket import categorize_ticket, format_ticket_info
from .date import parse_date_args, get_current_week, get_last_week
from .config import load_config, validate_config_structure, get_team_member_name, get_team_members_dict
from .report import create_summary_report, save_report, generate_filename

__all__ = [
    # JIRA utilities
    'initialize_jira_client',
    'fetch_tickets_for_date_range',
    
    # Ticket utilities
    'categorize_ticket', 
    'format_ticket_info',
    
    # Date utilities
    'parse_date_args',
    'get_current_week',
    'get_last_week',
    
    # Config utilities
    'load_config',
    'validate_config_structure',
    'get_team_member_name',
    'get_team_members_dict',
    
    # Report utilities
    'create_summary_report',
    'save_report',
    'generate_filename'
]
