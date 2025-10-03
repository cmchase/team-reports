#!/usr/bin/env python3
"""
Weekly Team Summary Generator for Jira Tickets

Generates weekly summaries of team work based on Jira tickets, categorized by team areas:
1. Remediations Core
2. Remediations Platform  
3. QE / Integrations
4. Edge Decommission

Usage:
    python3 weekly_team_summary.py [start_date] [end_date] [config_file]
    
Examples:
    python3 weekly_team_summary.py 2025-07-15 2025-07-22
    python3 weekly_team_summary.py  # Uses current week
    python3 weekly_team_summary.py 2025-07-15 2025-07-22 custom_team_config.yaml
"""

import sys
import os
from typing import List, Dict, Any
from collections import defaultdict

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from jira import JIRA
from ticket_utils import categorize_ticket, format_ticket_info
from jira_utils import initialize_jira_client, fetch_tickets_for_date_range
from date_utils import parse_date_args as parse_date_args_util
from config_utils import load_config
from report_utils import create_summary_report, save_report, generate_filename

# Load environment variables
load_dotenv()

class WeeklyTeamSummary:
    def __init__(self, config_file='team_config.yaml'):
        self.jira_client = None
        self.config = self._load_config(config_file)
        self.base_jql = self.config['base_jql']
        self.team_categories = self.config['team_categories']
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        return load_config(config_file)
            

        
    def initialize(self):
        """Initialize the Jira client connection"""
        self.jira_client = initialize_jira_client()
        
    # Removed - now using jira_utils.build_jql_with_dates
        
    def fetch_tickets(self, start_date: str, end_date: str) -> List[Any]:
        """Fetch tickets for the specified date range"""
        print(f"🔍 Searching tickets from {start_date} to {end_date}...")
        return fetch_tickets_for_date_range(self.jira_client, self.base_jql, start_date, end_date, self.config)
            
    def categorize_ticket(self, issue) -> str:
        """Categorize a ticket into one of the team categories"""
        return categorize_ticket(issue, self.team_categories)
        
    def format_ticket_info(self, issue) -> Dict[str, str]:
        """Format ticket information for display"""
        return format_ticket_info(issue, self.jira_client.server_url)
    
    # Removed - now using report_utils.format_table_row
        
    def generate_summary_report(self, categorized_tickets: Dict[str, List], start_date: str, end_date: str) -> str:
        """Generate a formatted summary report"""
        return create_summary_report(
            "WEEKLY TEAM SUMMARY",
            start_date,
            end_date,
            categorized_tickets,
            self.team_categories,
            self.format_ticket_info
        )
        
    def generate_weekly_summary(self, start_date: str, end_date: str) -> str:
        """Generate the complete weekly summary"""
        self.initialize()
        
        # Fetch tickets
        tickets = self.fetch_tickets(start_date, end_date)
        
        if not tickets:
            return f"No tickets found for the period {start_date} to {end_date}"
            
        # Categorize tickets
        categorized_tickets = defaultdict(list)
        for ticket in tickets:
            category = self.categorize_ticket(ticket)
            categorized_tickets[category].append(ticket)
            
        # Generate report
        return self.generate_summary_report(categorized_tickets, start_date, end_date)
        
def parse_date_args():
    """Parse command line date arguments or use current week"""
    # Use the utility function
    return parse_date_args_util(sys.argv[1:])

def main():
    """Main function"""
    try:
        start_date, end_date = parse_date_args()
        
        print(f"🚀 Generating weekly team summary for {start_date} to {end_date}")
        print("=" * 60)
        
        # Check for custom config file argument
        config_file = 'team_config.yaml'
        if len(sys.argv) >= 4 and sys.argv[3].endswith('.yaml'):
            config_file = sys.argv[3]
            print(f"📝 Using custom config file: {config_file}")
        
        summary_generator = WeeklyTeamSummary(config_file)
        report = summary_generator.generate_weekly_summary(start_date, end_date)
        
        # Save report using utility functions
        filename = generate_filename('team_summary', start_date, end_date)
        filepath = save_report(report, filename)
        
        print("\n" + report)
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 