#!/usr/bin/env python3
"""
Quarterly Team Summary Generator for Jira Tickets

Generates quarterly summaries by aggregating data across the quarter period,
providing trending analysis and comprehensive insights into team work patterns.

Usage:
    python3 quarterly_team_summary.py [year] [quarter] [config_file]
    python3 quarterly_team_summary.py 2025 4
    python3 quarterly_team_summary.py  # Uses current quarter
    python3 quarterly_team_summary.py 2025 4 custom_team_config.yaml
"""

import sys
import os
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, '.')

from dotenv import load_dotenv
from jira import JIRA
from utils.ticket import categorize_ticket, format_ticket_info
from utils.jira import initialize_jira_client, fetch_tickets_for_date_range
from utils.date import get_current_quarter, get_quarter_range, parse_quarter_from_date
from utils.config import load_config
from utils.report import generate_filename, save_report, ensure_reports_directory

# Load environment variables
load_dotenv()


class QuarterlyTeamSummary:
    def __init__(self, config_file='team_config.yaml'):
        """Initialize the quarterly team summary generator with configuration."""
        # Initialize JIRA client as None - will be set up later in initialize()
        self.jira_client = None
        
        # Load configuration from YAML file using utility function
        self.config = self._load_config(config_file)
        
        # Extract commonly used config values for easy access
        self.base_jql = self.config['base_jql']  # Base JQL query for ticket filtering
        self.team_categories = self.config['team_categories']  # Team categorization rules
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from YAML file using utility function."""
        # Delegate to utility function which handles error checking and validation
        return load_config(config_file)
        
    def initialize(self):
        """Initialize the Jira client connection using environment variables."""
        # Set up JIRA client using credentials from environment variables (.env file)
        # This handles authentication and connection validation
        self.jira_client = initialize_jira_client()
        
    def fetch_tickets(self, start_date: str, end_date: str) -> List[Any]:
        """Fetch tickets for the specified quarterly date range."""
        print(f"🔍 Searching tickets for quarter from {start_date} to {end_date}...")
        
        # Use utility function to fetch tickets with date range filtering
        # Combines base JQL with date constraints and status filters
        return fetch_tickets_for_date_range(self.jira_client, self.base_jql, start_date, end_date, self.config)
        
    def categorize_ticket(self, issue) -> str:
        """Categorize a ticket into one of the configured team categories."""
        # Use utility function to match ticket against team category rules
        # Returns category name or 'Other' if no match found
        return categorize_ticket(issue, self.team_categories)
        
    def format_ticket_info(self, issue) -> Dict[str, str]:
        """Format ticket information into a standardized dictionary for display."""
        # Extract and format key ticket fields (ID, title, assignee, status, etc.)
        # Returns structured data for consistent report formatting
        return format_ticket_info(issue, self.jira_client.server_url, self.config)
    
    def analyze_quarterly_trends(self, tickets: List[Any]) -> Dict[str, Any]:
        """Analyze trends and patterns across the quarter for insights generation."""
        # Initialize trend tracking dictionaries with default values
        trends = {
            'monthly_breakdown': defaultdict(lambda: defaultdict(int)),  # Month -> Category -> Count
            'status_trends': defaultdict(int),                           # Status -> Count
            'assignee_activity': defaultdict(int),                       # Assignee -> Count
            'priority_distribution': defaultdict(int),                   # Priority -> Count
            'component_activity': defaultdict(int)                       # Component -> Count
        }
        
        # Process each ticket to extract trending data
        for ticket in tickets:
            # Get formatted ticket information for analysis
            ticket_info = self.format_ticket_info(ticket)
            
            # Extract trends data with error handling for invalid dates/fields
            try:
                # Parse the updated date to extract month information
                updated_date = datetime.strptime(ticket_info['updated'], '%Y-%m-%d')
                month = updated_date.strftime('%B')  # Full month name (e.g., "October")
                
                # Categorize ticket to track category trends by month
                category = self.categorize_ticket(ticket)
                
                # Accumulate trend data across multiple dimensions
                trends['monthly_breakdown'][month][category] += 1      # Monthly category activity
                trends['status_trends'][ticket_info['status']] += 1    # Overall status distribution
                trends['assignee_activity'][ticket_info['assignee']] += 1  # Team member activity
                trends['priority_distribution'][ticket_info['priority']] += 1  # Priority patterns
                
                # Extract component information if available
                if hasattr(ticket.fields, 'components') and ticket.fields.components:
                    for component in ticket.fields.components:
                        trends['component_activity'][component.name] += 1
                        
            except (ValueError, AttributeError):
                # Skip tickets with invalid dates or missing required fields
                # This prevents crashes from malformed data
                continue
                
        return trends
    
    def generate_quarterly_overview(self, categorized_tickets: Dict[str, List], 
                                  trends: Dict[str, Any], year: int, quarter: int) -> List[str]:
        """Generate the quarterly overview section with high-level statistics and trends."""
        # Calculate total ticket count across all categories
        total_tickets = sum(len(tickets) for tickets in categorized_tickets.values())
        
        # Start building the overview section with header and basic stats
        overview = [
            f"### 📊 Q{quarter} {year} OVERVIEW",
            f"- **Total Tickets Processed:** {total_tickets}",
            f"- **Quarter Period:** Q{quarter} {year}",
            ""
        ]
        
        # Add work distribution breakdown by category with percentages
        overview.append("#### 🎯 Work Distribution by Category")
        for category, tickets in categorized_tickets.items():
            if tickets:  # Only show categories that have tickets
                # Calculate percentage of total work for this category
                percentage = (len(tickets) / total_tickets * 100) if total_tickets > 0 else 0
                overview.append(f"- **{category}:** {len(tickets)} tickets ({percentage:.1f}%)")
        overview.append("")
        
        # Add monthly activity trend if data is available
        if trends['monthly_breakdown']:
            overview.append("#### 📈 Monthly Activity Trend")
            # Show total activity per month within the quarter
            for month, categories in trends['monthly_breakdown'].items():
                month_total = sum(categories.values())  # Sum across all categories for the month
                overview.append(f"- **{month}:** {month_total} tickets")
            overview.append("")
        
        # Add top team members by activity level
        if trends['assignee_activity']:
            overview.append("#### 👥 Most Active Team Members")
            # Sort assignees by ticket count and show top 10
            top_assignees = sorted(trends['assignee_activity'].items(), 
                                 key=lambda x: x[1], reverse=True)[:10]
            for assignee, count in top_assignees:
                overview.append(f"- **{assignee}:** {count} tickets")
            overview.append("")
        
        return overview
    
    def generate_category_trends(self, category_name: str, tickets: List[Any], 
                               trends: Dict[str, Any]) -> List[str]:
        """Generate detailed trend analysis for a specific team category."""
        # Return empty list if no tickets in this category
        if not tickets:
            return []
            
        # Start building category-specific insights section
        section = [f"#### 📊 {category_name} Quarterly Insights", ""]
        
        # Initialize counters for category-specific analysis
        category_statuses = defaultdict(int)    # Status distribution within this category
        category_assignees = defaultdict(int)   # Assignee distribution within this category
        
        # Analyze tickets within this category only
        for ticket in tickets:
            ticket_info = self.format_ticket_info(ticket)
            category_statuses[ticket_info['status']] += 1      # Count tickets by status
            category_assignees[ticket_info['assignee']] += 1   # Count tickets by assignee
        
        # Generate status distribution analysis
        section.append("**Status Distribution:**")
        # Sort statuses by count (most common first) for better readability
        for status, count in sorted(category_statuses.items(), key=lambda x: x[1], reverse=True):
            # Calculate percentage within this category
            percentage = (count / len(tickets) * 100) if len(tickets) > 0 else 0
            section.append(f"- {status}: {count} tickets ({percentage:.1f}%)")
        section.append("")
        
        # Generate top contributors analysis (only if multiple assignees)
        if len(category_assignees) > 1:
            section.append("**Top Contributors:**")
            # Show top 3 contributors to avoid cluttering the report
            top_contributors = sorted(category_assignees.items(), key=lambda x: x[1], reverse=True)[:3]
            for assignee, count in top_contributors:
                section.append(f"- {assignee}: {count} tickets")
            section.append("")
        
        return section
    
    def generate_quarterly_insights(self, trends: Dict[str, Any]) -> List[str]:
        """Generate comprehensive insights and actionable recommendations from trend data."""
        # Start building the insights section with header
        insights = [
            "### 🔍 QUARTERLY INSIGHTS & ANALYSIS",
            ""
        ]
        
        # Analyze and display priority distribution patterns
        if trends['priority_distribution']:
            insights.append("#### ⚠️ Priority Distribution")
            
            # Calculate total tickets with defined priorities (exclude 'Undefined')
            total_prioritized = sum(count for priority, count in trends['priority_distribution'].items() 
                                   if priority != 'Undefined')
            
            # Show priority breakdown for defined priorities
            for priority, count in sorted(trends['priority_distribution'].items(), 
                                        key=lambda x: x[1], reverse=True):
                if priority != 'Undefined':
                    # Calculate percentage among prioritized tickets
                    percentage = (count / total_prioritized * 100) if total_prioritized > 0 else 0
                    insights.append(f"- **{priority}:** {count} tickets ({percentage:.1f}%)")
                    
            # Separately handle undefined priorities as they indicate process gaps
            undefined_count = trends['priority_distribution'].get('Undefined', 0)
            if undefined_count > 0:
                total_tickets = sum(trends['priority_distribution'].values())
                undefined_pct = (undefined_count / total_tickets * 100) if total_tickets > 0 else 0
                insights.append(f"- **Undefined Priority:** {undefined_count} tickets ({undefined_pct:.1f}%)")
            insights.append("")
        
        # Analyze component activity to identify focus areas
        if trends['component_activity']:
            insights.append("#### 🛠️ Most Active Components")
            # Show top 5 components to highlight main areas of work
            top_components = sorted(trends['component_activity'].items(), 
                                  key=lambda x: x[1], reverse=True)[:5]
            for component, count in top_components:
                insights.append(f"- **{component}:** {count} tickets")
            insights.append("")
        
        # Generate data-driven recommendations section
        insights.extend([
            "#### 💡 Recommendations",
            "",
            "Based on this quarter's data:",
            ""
        ])
        
        # Recommendation 1: Priority management assessment
        undefined_count = trends['priority_distribution'].get('Undefined', 0)
        total_tickets = sum(trends['priority_distribution'].values())
        # Flag if more than 30% of tickets lack priority - indicates planning gaps
        if undefined_count > total_tickets * 0.3:
            insights.append("- 🎯 **Priority Management:** Consider reviewing and setting priorities for undefined tickets to improve planning")
        
        # Recommendation 2: Workload distribution analysis
        assignee_counts = list(trends['assignee_activity'].values())
        # Flag if one person handles >40% of work - indicates potential bottleneck
        if assignee_counts and max(assignee_counts) > sum(assignee_counts) * 0.4:
            insights.append("- ⚖️ **Workload Balance:** Consider redistributing work to balance team member assignments")
        
        insights.append("")
        return insights
    
    def generate_quarterly_report(self, categorized_tickets: Dict[str, List], 
                                year: int, quarter: int, start_date: str, end_date: str) -> str:
        """Generate the complete quarterly summary report with all sections."""
        # Collect all tickets from all categories for trend analysis
        all_tickets = []
        for category_tickets in categorized_tickets.values():
            all_tickets.extend(category_tickets)
        
        # Perform comprehensive trend analysis across all tickets
        trends = self.analyze_quarterly_trends(all_tickets)
        
        # Initialize report as list of strings (will be joined at the end)
        report = []
        
        # Generate report header with metadata
        report.extend([
            f"## 📊 QUARTERLY TEAM SUMMARY: Q{quarter} {year}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Quarter Period:** {start_date} to {end_date}",
            ""
        ])
        
        # Add high-level overview section with trends
        report.extend(self.generate_quarterly_overview(categorized_tickets, trends, year, quarter))
        
        # Generate detailed sections for each configured team category
        for category_name, category_rules in self.team_categories.items():
            tickets = categorized_tickets.get(category_name, [])
            
            # Process categories that have tickets
            if tickets:
                description = category_rules.get('description', 'No description')
                report.extend([
                    f"### 🎯 {category_name.upper()} - {description}",
                    f"**Total Tickets:** {len(tickets)}",
                    ""
                ])
                
                # Add category-specific trend insights
                report.extend(self.generate_category_trends(category_name, tickets, trends))
                
                # Group tickets by status for detailed breakdown
                status_groups = defaultdict(list)
                for ticket in tickets:
                    ticket_info = self.format_ticket_info(ticket)
                    status_groups[ticket_info['status']].append(ticket_info)
                
                # Generate status-based ticket listings
                for status, status_tickets in status_groups.items():
                    if status_tickets:
                        report.extend([
                            f"##### 📌 {status} ({len(status_tickets)} tickets)",
                            ""
                        ])
                        
                        # Show most recent tickets (up to 10 per status to avoid overwhelming)
                        recent_tickets = sorted(status_tickets, 
                                              key=lambda x: x['updated'], reverse=True)[:10]
                        
                        # Create markdown table with ticket details
                        report.extend([
                            "| Ticket ID | Assignee | Priority | Updated | Title |",
                            "|-----------|----------|----------|---------|-------|"
                        ])
                        
                        # Format each ticket as a table row
                        for ticket in recent_tickets:
                            # Truncate long titles and assignee names for table formatting
                            title = ticket['summary'][:50] + "..." if len(ticket['summary']) > 50 else ticket['summary']
                            assignee = ticket['assignee'][:15] + "..." if len(ticket['assignee']) > 15 else ticket['assignee']
                            report.append(f"| [{ticket['key']}]({ticket['url']}) | {assignee} | {ticket['priority']} | {ticket['updated']} | {title} |")
                        
                        # Indicate if there are more tickets not shown
                        if len(status_tickets) > 10:
                            report.append(f"*... and {len(status_tickets) - 10} more tickets*")
                        report.append("")
            else:
                # Handle categories with no tickets
                report.extend([
                    f"### 🎯 {category_name.upper()}",
                    "*No tickets found for this category this quarter.*",
                    ""
                ])
        
        # Process uncategorized tickets (may indicate categorization gaps)
        other_tickets = categorized_tickets.get('Other', [])
        if other_tickets:
            report.extend([
                f"### 🔍 OTHER / UNCATEGORIZED TICKETS ({len(other_tickets)} tickets)",
                "",
                "*Showing first 10 tickets - these may need category assignment*",
                "",
                "| Ticket ID | Assignee | Priority | Updated | Title |",
                "|-----------|----------|----------|---------|-------|"
            ])
            
            # Show sample of uncategorized tickets for review
            for ticket in other_tickets[:10]:
                ticket_info = self.format_ticket_info(ticket)
                title = ticket_info['summary'][:50] + "..." if len(ticket_info['summary']) > 50 else ticket_info['summary']
                assignee = ticket_info['assignee'][:15] + "..." if len(ticket_info['assignee']) > 15 else ticket_info['assignee']
                report.append(f"| [{ticket_info['key']}]({ticket_info['url']}) | {assignee} | {ticket_info['priority']} | {ticket_info['updated']} | {title} |")
            
            # Indicate total count if more exist
            if len(other_tickets) > 10:
                report.append(f"*... and {len(other_tickets) - 10} more uncategorized tickets*")
            report.append("")
        
        # Add comprehensive insights and recommendations
        report.extend(self.generate_quarterly_insights(trends))
        
        # Generate report footer with completion metadata
        report.extend([
            "---",
            "",
            f"### ✅ Q{quarter} {year} Report Complete",
            "",
            "*This quarterly report was generated automatically from Jira data.*",
            f"*Report covers the period from {start_date} to {end_date}*"
        ])
        
        # Join all report sections into final markdown string
        return "\n".join(report)
    
    def generate_quarterly_summary(self, year: int, quarter: int) -> str:
        """Generate the complete quarterly summary by orchestrating all data collection and analysis."""
        # Initialize JIRA connection (must be done before any ticket operations)
        self.initialize()
        
        # Calculate the exact date range for the specified quarter
        start_date, end_date = get_quarter_range(year, quarter)
        
        # Fetch all tickets within the quarterly date range
        tickets = self.fetch_tickets(start_date, end_date)
        
        # Handle case where no tickets are found (avoid empty reports)
        if not tickets:
            return f"No tickets found for Q{quarter} {year} ({start_date} to {end_date})"
        
        # Categorize all tickets according to team categorization rules
        categorized_tickets = defaultdict(list)
        for ticket in tickets:
            category = self.categorize_ticket(ticket)  # Determine which team category this ticket belongs to
            categorized_tickets[category].append(ticket)
        
        # Generate the complete formatted report using all collected data
        return self.generate_quarterly_report(categorized_tickets, year, quarter, start_date, end_date)


def parse_quarter_args() -> Tuple[int, int]:
    """Parse command line arguments to determine target year and quarter."""
    # Check if user provided year and quarter as command line arguments
    if len(sys.argv) >= 3:
        try:
            # Extract year and quarter from command line arguments
            year = int(sys.argv[1])
            quarter = int(sys.argv[2])
            
            # Validate quarter is within valid range (1-4)
            if quarter not in [1, 2, 3, 4]:
                raise ValueError("Quarter must be 1, 2, 3, or 4")
            
            return year, quarter
            
        except ValueError as e:
            # Handle invalid input gracefully with helpful error message
            print(f"❌ Invalid year or quarter: {e}")
            sys.exit(1)
    else:
        # No arguments provided - use current quarter automatically
        year, quarter, _, _ = get_current_quarter()
        return year, quarter


def main():
    """Main entry point for the quarterly team summary generator."""
    try:
        # Parse command line arguments to determine target quarter
        year, quarter = parse_quarter_args()
        
        # Display startup information to user
        print(f"🚀 Generating quarterly team summary for Q{quarter} {year}")
        print("=" * 60)
        
        # Check for optional custom configuration file
        config_file = 'team_config.yaml'  # Default configuration file
        if len(sys.argv) >= 4 and sys.argv[3].endswith('.yaml'):
            config_file = sys.argv[3]
            print(f"📝 Using custom config file: {config_file}")
        
        # Initialize the summary generator with configuration
        summary_generator = QuarterlyTeamSummary(config_file)
        
        # Generate the complete quarterly report
        report = summary_generator.generate_quarterly_summary(year, quarter)
        
        # Save the report to file system
        filename = generate_filename(f'quarterly_summary_Q{quarter}', f'{year}-01-01', f'{year}-12-31')
        # Create more descriptive filename for quarterly reports
        quarter_filename = f"quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(report, quarter_filename)
        
        # Display the report to console and show completion message
        print("\n" + report)
        print(f"\n📊 Quarterly summary complete! Saved to: {filepath}")
        
    except Exception as e:
        # Handle any unexpected errors with detailed error information
        print(f"❌ Error generating quarterly summary: {e}")
        import traceback
        traceback.print_exc()  # Show full stack trace for debugging
        sys.exit(1)


# Script entry point - only run if this file is executed directly
if __name__ == "__main__":
    main()
