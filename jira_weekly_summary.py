#!/usr/bin/env python3
"""
Weekly Team Summary Generator for Jira Tickets

Generates weekly summaries of team work based on Jira tickets, categorized by team areas:
1. Remediations Core
2. Remediations Platform  
3. QE / Integrations
4. Edge Decommission

Usage:
    python3 jira_weekly_summary.py [start_date] [end_date] [config_file]
    
Examples:
    python3 jira_weekly_summary.py 2025-07-15 2025-07-22
    python3 jira_weekly_summary.py  # Uses current week
    python3 jira_weekly_summary.py 2025-07-15 2025-07-22 config/custom_jira_config.yaml
"""

import sys
import os
from typing import List, Dict, Any
from collections import defaultdict

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from jira import JIRA
from utils.jira import fetch_tickets_with_changelog, compute_cycle_time_days, compute_cycle_time_stats
from utils.date import parse_date_args as parse_date_args_util
from utils.config import load_config, get_config
from utils.report import create_summary_report, save_report, generate_filename, render_active_config
from utils.jira_summary_base import JiraSummaryBase

# Load environment variables
load_dotenv()

class WeeklyTeamSummary(JiraSummaryBase):
    def __init__(self, config_file='config/jira_config.yaml'):
        """Initialize the weekly team summary generator with configuration."""
        super().__init__(config_file)
        
    # All common methods now inherited from JiraSummaryBase:
    # - _load_config: inherited via JiraApiClient
    # - initialize: inherited from JiraSummaryBase
    # - fetch_tickets: inherited from JiraSummaryBase
    # - categorize_ticket: inherited from JiraSummaryBase
    # - format_ticket_info: inherited from JiraSummaryBase
    
    # Removed - now using report_utils.format_table_row
        
    def generate_summary_report(self, categorized_tickets: Dict[str, List], start_date: str, end_date: str) -> str:
        """Generate a formatted summary report"""
        # Generate user-friendly title with day of week
        from datetime import datetime
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Format: "WEEKLY TEAM SUMMARY: Sunday Oct 6 to Saturday Oct 12, 2025"
        # Cross-platform date formatting (%-d doesn't work on Windows)
        try:
            start_day = start_dt.strftime('%A %b %-d')  # "Sunday Oct 6"  
            end_day = end_dt.strftime('%A %b %-d')      # "Saturday Oct 12"
        except ValueError:
            # Fallback for Windows - remove leading zero manually
            start_day = start_dt.strftime('%A %b %d').replace(' 0', ' ')
            end_day = end_dt.strftime('%A %b %d').replace(' 0', ' ')
        year = start_dt.year
        
        title = f"WEEKLY TEAM SUMMARY: {start_day} to {end_day}, {year}"
        
        return create_summary_report(
            title,
            start_date,
            end_date,
            categorized_tickets,
            self.team_categories,
            self.format_ticket_info,
            self.config  # Pass config for categorization flag check
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
        

def generate_wip_analysis(config: Dict[str, Any]) -> str:
    """
    Generate WIP (Work in Progress) analysis section for weekly report.
    
    Shows current WIP per engineer and team total, with over-limit highlights.
    
    Args:
        config: Configuration dictionary with Jira settings and thresholds
        
    Returns:
        str: Markdown section with WIP analysis
    """
    try:
        # Initialize Jira client
        jira_client = initialize_jira_client()
        
        # Get active states from config
        active_states = config.get('states', {}).get('active', ['In Progress', 'Review'])
        
        # Get WIP threshold per engineer
        wip_threshold = config.get('thresholds', {}).get('wip', {}).get('max_per_engineer', 3)
        
        # Build JQL for current active tickets
        base_jql = config.get('base_jql', '')
        
        # Create JQL to find all currently active tickets
        active_states_jql = ','.join([f'"{state}"' for state in active_states])
        if base_jql:
            jql = f"({base_jql}) AND status in ({active_states_jql})"
        else:
            jql = f"status in ({active_states_jql})"
            
        # Fetch current active tickets
        max_results = config.get('report_settings', {}).get('max_results', 200)  
        
        print(f"🔍 Fetching current WIP tickets with JQL: {jql}")
        tickets = jira_client.search_issues(jql, maxResults=max_results, expand='changelog')
        
        if not tickets:
            return f"\n\n### 📊 Flow • Work in Progress (WIP)\n\n*No active tickets found in states: {', '.join(active_states)}*\n"
        
        # Count WIP by engineer
        wip_by_engineer = {}
        unassigned_count = 0
        
        for ticket in tickets:
            assignee = getattr(ticket.fields.assignee, 'displayName', None) if ticket.fields.assignee else None
            
            if assignee:
                wip_by_engineer[assignee] = wip_by_engineer.get(assignee, 0) + 1
            else:
                unassigned_count += 1
        
        # Build report section
        total_wip = sum(wip_by_engineer.values()) + unassigned_count
        section = f"\n\n### 📊 Flow • Work in Progress (WIP)\n\n"
        section += f"**Current WIP:** {total_wip} tickets • **Threshold:** {wip_threshold} per engineer\n\n"
        
        if wip_by_engineer or unassigned_count > 0:
            # WIP table
            section += "#### 👥 WIP by Engineer\n\n"
            section += "| Engineer | WIP Count | Over Limit? |\n"
            section += "|----------|-----------|-------------|\n"
            
            over_limit_engineers = []
            
            # Sort engineers by WIP count (highest first)
            for engineer, count in sorted(wip_by_engineer.items(), key=lambda x: x[1], reverse=True):
                over_limit = count > wip_threshold
                over_limit_text = "🔴 Yes" if over_limit else "✅ No"
                section += f"| {engineer} | {count} | {over_limit_text} |\n"
                
                if over_limit:
                    over_limit_engineers.append(f"{engineer} ({count} tickets)")
            
            # Add unassigned if any
            if unassigned_count > 0:
                section += f"| *Unassigned* | {unassigned_count} | - |\n"
            
            section += "\n"
            
            # Over-limit highlights
            if over_limit_engineers:
                section += "#### 🚨 Over WIP Limit\n\n"
                for engineer_info in over_limit_engineers:
                    section += f"- **{engineer_info}** exceeds threshold of {wip_threshold}\n"
                section += "\n"
            
        return section
        
    except Exception as e:
        return f"\n\n### 📊 Flow • Work in Progress (WIP)\n\n*Error computing WIP analysis: {e}*\n"


def generate_cycle_time_analysis(config: Dict[str, Any], start_date: str, end_date: str) -> str:
    """
    Generate cycle time analysis section for weekly report.
    
    Args:
        config: Configuration dictionary with Jira settings
        start_date: Start date in YYYY-MM-DD format  
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        str: Markdown section with cycle time analysis
    """
    try:
        # Initialize Jira client
        jira_client = initialize_jira_client()
        
        # Build JQL for all tickets (not just completed ones) to get full cycle data
        from utils.jira import build_jql_with_dates
        base_jql = config.get('base_jql', '')
        jql = build_jql_with_dates(base_jql, start_date, end_date, config, 'all')
        
        # Fetch tickets with changelog for cycle time calculation
        max_results = config.get('report_settings', {}).get('max_results', 200)
        tickets = fetch_tickets_with_changelog(jira_client, jql, max_results)
        
        if not tickets:
            return "\n\n### ⏱️ Flow • Cycle Time\n\n*No tickets found for cycle time analysis.*\n"
        
        # Get states configuration
        states_done = config.get('status_filters', {}).get('completed', ['Closed', 'Done'])
        state_in_progress = config.get('states', {}).get('in_progress', 'In Progress')
        
        # Compute cycle times
        cycle_data = []
        for ticket in tickets:
            cycle_time = compute_cycle_time_days(ticket, states_done, state_in_progress)
            if cycle_time is not None:
                cycle_data.append({
                    'ticket': ticket,
                    'cycle_time': cycle_time,
                    'assignee': getattr(ticket.fields.assignee, 'displayName', 'Unassigned') if ticket.fields.assignee else 'Unassigned',
                    'key': ticket.key,
                    'url': f"{jira_client.server_url}/browse/{ticket.key}",
                    'summary': ticket.fields.summary or 'No Summary'
                })
        
        if not cycle_data:
            return "\n\n### ⏱️ Flow • Cycle Time\n\n*No completed tickets with full cycle time data found.*\n"
        
        # Compute statistics
        cycle_times = [item['cycle_time'] for item in cycle_data]
        stats = compute_cycle_time_stats(cycle_times)
        
        # Sort by cycle time for fastest/slowest
        sorted_data = sorted(cycle_data, key=lambda x: x['cycle_time'])
        
        # Build report section
        section = f"\n\n### ⏱️ Flow • Cycle Time\n\n"
        section += f"**{len(cycle_data)} tickets analyzed** • "
        section += f"**Average: {stats['avg']} days** • "
        section += f"**Median: {stats['median']} days** • "
        section += f"**P90: {stats['p90']} days**\n\n"
        
        # Top 5 fastest
        if len(sorted_data) > 0:
            section += "#### 🚀 Fastest (Top 5)\n\n"
            section += "| Ticket | Assignee | Days | Summary |\n"
            section += "|--------|----------|------|----------|\n"
            
            fastest = sorted_data[:5]
            for item in fastest:
                summary = item['summary'][:50] + "..." if len(item['summary']) > 50 else item['summary']
                section += f"| [{item['key']}]({item['url']}) | {item['assignee']} | {item['cycle_time']:.1f} | {summary} |\n"
        
        # Top 5 slowest (if we have more than 5 tickets)
        if len(sorted_data) > 5:
            section += "\n#### 🐌 Slowest (Top 5)\n\n"
            section += "| Ticket | Assignee | Days | Summary |\n"
            section += "|--------|----------|------|----------|\n"
            
            slowest = sorted_data[-5:][::-1]  # Last 5, reversed
            for item in slowest:
                summary = item['summary'][:50] + "..." if len(item['summary']) > 50 else item['summary']
                section += f"| [{item['key']}]({item['url']}) | {item['assignee']} | {item['cycle_time']:.1f} | {summary} |\n"
        
        return section
        
    except Exception as e:
        return f"\n\n### ⏱️ Flow • Cycle Time\n\n*Error computing cycle time: {e}*\n"

def main():
    """Main function"""
    try:
        # Extract config file first, before date parsing
        config_file = 'config/jira_config.yaml'
        date_args = []
        
        # Filter sys.argv to separate date args from config file
        for arg in sys.argv[1:]:
            if arg.endswith('.yaml'):
                config_file = arg
                print(f"📝 Using custom config file: {config_file}")
            else:
                date_args.append(arg)
        
        # Parse dates from filtered arguments
        from utils.date import parse_date_args as parse_date_args_util
        start_date, end_date = parse_date_args_util(date_args)
        
        # Defensive programming: Ensure dates are strings in YYYY-MM-DD format
        start_date = str(start_date).split()[0] if ' ' in str(start_date) else str(start_date)
        end_date = str(end_date).split()[0] if ' ' in str(end_date) else str(end_date)
        
        print(f"🚀 Generating weekly team summary for {start_date} to {end_date}")
        print("=" * 60)
        
        # Load configuration and setup feature flags
        config = get_config([config_file])
        
        # Helper function for clean feature flag checks
        def flag(path: str) -> bool:
            """Check if a feature flag is enabled in config"""
            keys = path.split('.')
            value = config
            try:
                for key in keys:
                    value = value[key]
                return bool(value)
            except (KeyError, TypeError):
                return False
        
        # Feature flags for Jira flow metrics (Phase 2+)
        enable_cycle_time = flag("metrics.flow.cycle_time")
        enable_wip = flag("metrics.flow.wip") 
        enable_blocked_time = flag("metrics.flow.blocked_time")
        
        summary_generator = WeeklyTeamSummary(config_file)
        report = summary_generator.generate_weekly_summary(start_date, end_date)
        
        # Add cycle time analysis if enabled
        if enable_cycle_time:
            print("🔄 Computing weekly cycle time analysis...")
            cycle_time_section = generate_cycle_time_analysis(config, start_date, end_date)
            report += cycle_time_section
        
        # Add WIP analysis if enabled
        if enable_wip:
            print("📊 Computing current WIP analysis...")
            wip_section = generate_wip_analysis(config)
            report += wip_section
        
        # TODO: Future metrics sections (Phase 2+)
        # if enable_blocked_time:
        #     report += generate_blocked_time_analysis(tickets, start_date, end_date)
        
        # Append active configuration block
        config_block = render_active_config(config)
        full_report = report + config_block
        
        # Save report using utility functions
        filename = generate_filename('jira_weekly_summary', start_date, end_date)
        filepath = save_report(full_report, filename)
        
        print("\n" + full_report)
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 