#!/usr/bin/env python3
"""
Quarterly Team Summary Generator for Jira Tickets

Generates quarterly summaries focused on individual contributor performance,
tracking ticket completion counts and productivity metrics per team member.

Usage:
    python3 jira_quarterly_summary.py [year] [quarter] [config_file]
    python3 jira_quarterly_summary.py 2025 4
    python3 jira_quarterly_summary.py  # Uses current quarter
    python3 jira_quarterly_summary.py 2025 4 custom_team_config.yaml
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
from utils.ticket import format_ticket_info
from utils.jira import initialize_jira_client, fetch_tickets_for_date_range
from utils.date import get_current_quarter, get_quarter_range, parse_quarter_from_date
from utils.config import load_config, get_config
from utils.report import generate_filename, save_report, ensure_reports_directory, render_active_config

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
        # Get default status filter from config, fallback to 'completed'
        default_filter = self.config.get('report_settings', {}).get('default_status_filter', 'completed')
        return fetch_tickets_for_date_range(self.jira_client, self.base_jql, start_date, end_date, self.config, default_filter)
        
    def format_ticket_info(self, issue) -> Dict[str, str]:
        """Format ticket information into a standardized dictionary for display."""
        # Extract and format key ticket fields (ID, title, assignee, status, etc.)
        # Returns structured data for consistent report formatting
        return format_ticket_info(issue, self.jira_client.server_url, self.config)
    
    def analyze_contributor_performance(self, tickets: List[Any]) -> Dict[str, Any]:
        """Analyze individual contributor performance and productivity metrics."""
        # Initialize performance tracking dictionaries
        performance = {
            'contributor_tickets': defaultdict(list),        # Assignee -> List of tickets
            'contributor_counts': defaultdict(int),          # Assignee -> Total count
            'contributor_story_points': defaultdict(int),    # Assignee -> Total story points
            'status_distribution': defaultdict(int),         # Status -> Count
            'story_point_distribution': defaultdict(int),    # Story Points -> Count
            'monthly_activity': defaultdict(lambda: defaultdict(int)),  # Month -> Assignee -> Count
            'component_activity': defaultdict(int)           # Component -> Count
        }
        
        # Process each ticket to extract contributor performance data
        for ticket in tickets:
            # Get formatted ticket information for analysis
            ticket_info = self.format_ticket_info(ticket)
            assignee = ticket_info['assignee']
            
            # Track tickets per contributor
            performance['contributor_tickets'][assignee].append(ticket_info)
            performance['contributor_counts'][assignee] += 1
            performance['contributor_story_points'][assignee] += ticket_info['story_points']
            
            # Track overall distributions
            performance['status_distribution'][ticket_info['status']] += 1
            performance['story_point_distribution'][ticket_info['story_points']] += 1
            
            # Extract monthly activity with error handling
            try:
                # Parse the updated date to extract month information
                updated_date = datetime.strptime(ticket_info['updated'], '%Y-%m-%d')
                month = updated_date.strftime('%B')  # Full month name (e.g., "October")
                performance['monthly_activity'][month][assignee] += 1
                        
            except (ValueError, AttributeError):
                # Skip tickets with invalid dates or missing required fields
                continue
            
            # Extract component information if available
            if hasattr(ticket.fields, 'components') and ticket.fields.components:
                for component in ticket.fields.components:
                    performance['component_activity'][component.name] += 1
                
        return performance
    
    def generate_quarterly_overview(self, performance: Dict[str, Any], year: int, quarter: int) -> List[str]:
        """Generate the quarterly overview section focused on contributor performance."""
        # Calculate total ticket count, story points, and contributor count
        total_tickets = sum(performance['contributor_counts'].values())
        total_story_points = sum(performance['contributor_story_points'].values())
        total_contributors = len(performance['contributor_counts'])
        
        # Start building the overview section with header and basic stats
        overview = [
            f"### 📊 Q{quarter} {year} CONTRIBUTOR OVERVIEW",
            f"- **Total Tickets Processed:** {total_tickets}",
            f"- **Total Story Points Completed:** {total_story_points}",
            f"- **Active Contributors:** {total_contributors}",
            f"- **Quarter Period:** Q{quarter} {year}",
            ""
        ]
        
        # Add top contributors by ticket count
        if performance['contributor_counts']:
            overview.append("#### 🏆 Top Contributors by Ticket Count & Story Points")
            # Sort contributors by ticket count and show all (or top 15 if too many)
            top_contributors = sorted(performance['contributor_counts'].items(), 
                                    key=lambda x: x[1], reverse=True)
            
            # Show all contributors if reasonable number, otherwise limit to top 15
            display_count = min(15, len(top_contributors))
            for i, (contributor, count) in enumerate(top_contributors[:display_count], 1):
                percentage = (count / total_tickets * 100) if total_tickets > 0 else 0
                story_points = performance['contributor_story_points'][contributor]
                sp_percentage = (story_points / total_story_points * 100) if total_story_points > 0 else 0
                overview.append(f"{i}. **{contributor}:** {count} tickets ({percentage:.1f}%) • {story_points} Points ({sp_percentage:.1f}%)")
            
            if len(top_contributors) > display_count:
                overview.append(f"*... and {len(top_contributors) - display_count} more contributors*")
            overview.append("")
        
        # Add monthly activity trend if data is available
        if performance['monthly_activity']:
            overview.append("#### 📈 Monthly Activity Summary")
            # Show total activity per month within the quarter
            for month, contributors in performance['monthly_activity'].items():
                month_total = sum(contributors.values())  # Sum across all contributors for the month
                active_contributors = len(contributors)
                overview.append(f"- **{month}:** {month_total} tickets ({active_contributors} contributors)")
            overview.append("")
        
        return overview
    
    def generate_contributor_details(self, contributor: str, tickets: List[Dict[str, str]], performance: Dict[str, Any]) -> List[str]:
        """Generate detailed analysis for a specific contributor."""
        if not tickets:
            return []
            
        # Calculate total story points for this contributor
        total_story_points = sum(ticket['story_points'] for ticket in tickets)
        
        # Start building contributor section
        section = [
            f"### 👤 {contributor}", 
            f"- **Total Tickets:** {len(tickets)}", 
            f"- **Total Story Points:**  {total_story_points}",
            ""
        ]
        
        # Analyze tickets for this contributor
        status_breakdown = defaultdict(int)
        story_point_breakdown = defaultdict(int)
        
        # Group tickets by status and story points
        for ticket in tickets:
            # status_breakdown[ticket['status']] += 1
            story_point_breakdown[ticket['story_points']] += 1
        
        # Show status distribution
        if status_breakdown:
            section.append("#### 📊 Status Breakdown")
            for status, count in sorted(status_breakdown.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / len(tickets) * 100) if len(tickets) > 0 else 0
                section.append(f"- **{status}:** {count} tickets ({percentage:.1f}%)")
            section.append("")
        
        # Show story point distribution
        if story_point_breakdown:
            section.append("#### 📏 Story Point Breakdown")
            for story_points, count in sorted(story_point_breakdown.items(), 
                                            key=lambda x: x[0] if x[0] != 0 else float('inf')):
                percentage = (count / len(tickets) * 100) if len(tickets) > 0 else 0
                sp_label = f"{story_points} Points" if story_points > 0 else "No Points"
                section.append(f"- **{sp_label}:** {count} tickets ({percentage:.1f}%)")
            section.append("")
        
        # Show recent tickets (limit to 15 for readability)
        section.append("#### 🎫 Recent Tickets")
        recent_tickets = sorted(tickets, key=lambda x: x['updated'], reverse=True)[:15]
        
        section.extend([
            "| Ticket ID | Status | Size | Updated | Title |",
            "|-----------|--------|------|---------|-------|"
        ])
        
        for ticket in recent_tickets:
            # Truncate long titles for table formatting
            title = ticket['summary'][:60] + "..." if len(ticket['summary']) > 60 else ticket['summary']
            section.append(f"| [{ticket['key']}]({ticket['url']}) | {ticket['status']} | {ticket['story_points']} | {ticket['updated']} | {title} |")
        
        if len(tickets) > 15:
            section.append(f"*... and {len(tickets) - 15} more tickets*")
        section.append("")
        
        return section
    
    def generate_quarterly_insights(self, performance: Dict[str, Any]) -> List[str]:
        """Generate insights focused on contributor performance patterns."""
        # Start building the insights section with header
        insights = [
            "### 🔍 QUARTERLY PERFORMANCE INSIGHTS",
            ""
        ]
        
        # Analyze overall story point distribution
        if performance['story_point_distribution']:
            insights.append("#### 📏 Overall Story Point Distribution")
            total_tickets = sum(performance['story_point_distribution'].values())
            
            for story_points, count in sorted(performance['story_point_distribution'].items(), 
                                            key=lambda x: x[0] if x[0] != 0 else float('inf')):
                percentage = (count / total_tickets * 100) if total_tickets > 0 else 0
                sp_label = f"{story_points} Points" if story_points > 0 else "No Points"
                insights.append(f"- **{sp_label}:** {count} tickets ({percentage:.1f}%)")
            insights.append("")
        
        # Analyze component activity to identify focus areas
        if performance['component_activity']:
            insights.append("#### 🛠️ Most Active Components")
            # Show top 10 components to highlight main areas of work
            top_components = sorted(performance['component_activity'].items(), 
                                  key=lambda x: x[1], reverse=True)[:10]
            for component, count in top_components:
                insights.append(f"- **{component}:** {count} tickets")
            insights.append("")
        
        # Generate team productivity insights
        insights.extend([
            "#### 💡 Team Productivity Insights",
            "",
            "Based on this quarter's contributor data:",
            ""
        ])
        
        # Calculate productivity metrics
        contributor_counts = list(performance['contributor_counts'].values())
        total_contributors = len(contributor_counts)
        total_tickets = sum(contributor_counts)
        
        if contributor_counts:
            avg_tickets_per_contributor = total_tickets / total_contributors
            max_tickets = max(contributor_counts)
            min_tickets = min(contributor_counts)
            
            insights.append(f"- 📊 **Average tickets per contributor:** {avg_tickets_per_contributor:.1f}")
            insights.append(f"- 📈 **Highest contributor ticket count:** {max_tickets}")
            insights.append(f"- 📉 **Lowest contributor ticket count:** {min_tickets}")
            
            # Identify workload distribution pattern
            high_performers = sum(1 for count in contributor_counts if count > avg_tickets_per_contributor * 1.5)
            if high_performers > 0:
                insights.append(f"- 🏆 **High performers (>150% avg):** {high_performers} contributors")
            
            # Flag potential workload imbalances
            if max_tickets > avg_tickets_per_contributor * 3:
                insights.append("- ⚠️ **Workload Balance:** Consider reviewing ticket distribution - significant variance detected")
        
        insights.append("")
        return insights
    
    def generate_quarterly_report(self, performance: Dict[str, Any], year: int, quarter: int, start_date: str, end_date: str) -> str:
        """Generate the complete quarterly summary report focused on individual contributors."""
        # Initialize report as list of strings (will be joined at the end)
        report = []
        
        # Generate report header with metadata
        report.extend([
            f"## 📊 QUARTERLY CONTRIBUTOR REPORT: Q{quarter} {year}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Quarter Period:** {start_date} to {end_date}",
            ""
        ])
        
        # Add high-level overview section
        report.extend(self.generate_quarterly_overview(performance, year, quarter))
        
        # Generate individual contributor sections
        # Sort contributors by ticket count (highest first)
        sorted_contributors = sorted(performance['contributor_counts'].items(), 
                                   key=lambda x: x[1], reverse=True)
        
        report.append("## 👥 INDIVIDUAL CONTRIBUTOR DETAILS")
        report.append("")
        
        for contributor, ticket_count in sorted_contributors:
            # Get tickets for this contributor
            contributor_tickets = performance['contributor_tickets'][contributor]
            
            # Generate detailed section for this contributor
            contributor_section = self.generate_contributor_details(contributor, contributor_tickets, performance)
            report.extend(contributor_section)
        
        # Add comprehensive insights and analysis
        report.extend(self.generate_quarterly_insights(performance))
        
        # Generate report footer with completion metadata
        report.extend([
            "---",
            "",
            f"### ✅ Q{quarter} {year} Contributor Report Complete",
            "",
            "*This quarterly report was generated automatically from Jira data.*",
            f"*Report covers the period from {start_date} to {end_date}*",
            f"*Focus: Individual contributor performance and ticket completion tracking*"
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
        
        # Analyze contributor performance across all tickets
        performance = self.analyze_contributor_performance(tickets)
        
        # Generate the complete formatted report using all collected performance data
        return self.generate_quarterly_report(performance, year, quarter, start_date, end_date)


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
        
        # Append active configuration block
        config = get_config([config_file])
        config_block = render_active_config(config)
        full_report = report + config_block
        
        # Save the report to file system
        filename = generate_filename(f'jira_quarterly_summary_Q{quarter}', f'{year}-01-01', f'{year}-12-31')
        # Create more descriptive filename for quarterly reports
        quarter_filename = f"jira_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(full_report, quarter_filename)
        
        # Display the report to console and show completion message
        print("\n" + full_report)
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
