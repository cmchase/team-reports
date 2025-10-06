#!/usr/bin/env python3
"""
Report utilities for formatting, file management, and report generation.

This module provides reusable functions for creating formatted reports,
managing output files, and generating consistent report structures.
"""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict


def format_table_row(ticket_info: Dict[str, str], title_width: int = 50, 
                    assignee_width: int = 20) -> str:
    """
    Format a single ticket as a markdown table row.
    
    Args:
        ticket_info: Dictionary containing ticket information
        title_width: Maximum width for the title column
        assignee_width: Maximum width for the assignee column
        
    Returns:
        str: Formatted markdown table row
        
    Expected ticket_info structure:
        {
            'key': 'PROJECT-123',
            'url': 'https://jira.example.com/browse/PROJECT-123',
            'summary': 'Ticket title',
            'assignee': 'John Doe',
            'priority': 'High',
            'updated': '2025-01-15'
        }
    """
    # Create markdown link for ticket ID
    ticket_link = f"[{ticket_info['key']}]({ticket_info['url']})"
    
    # Truncate title if too long
    title = ticket_info['summary']
    if len(title) > title_width:
        title = title[:title_width-3] + "..."
    
    # Truncate assignee if too long  
    assignee = ticket_info['assignee']
    if len(assignee) > assignee_width:
        assignee = assignee[:assignee_width-3] + "..."
    
    return f"| {ticket_link:<25} | {assignee:<{assignee_width}} | {ticket_info['priority']:<8} | {ticket_info['updated']:<10} | {title:<{title_width}} |"


def create_table_header() -> List[str]:
    """
    Create standard markdown table header for ticket tables.
    
    Returns:
        List[str]: Table header lines
    """
    return [
        "| Ticket ID                | Assignee             | Priority | Updated    | Title                                              |",
        "|--------------------------|----------------------|----------|------------|----------------------------------------------------| "
    ]


def group_tickets_by_status(tickets: List[Any], format_func) -> Dict[str, List[Dict[str, str]]]:
    """
    Group tickets by their status and format them.
    
    Args:
        tickets: List of JIRA ticket objects
        format_func: Function to format ticket info (e.g., format_ticket_info from ticket_utils)
        
    Returns:
        Dict[str, List[Dict[str, str]]]: Tickets grouped by status
        
    Example:
        status_groups = group_tickets_by_status(tickets, format_ticket_info)
        # Returns: {"In Progress": [ticket_info1, ...], "To Do": [ticket_info2, ...]}
    """
    status_groups = defaultdict(list)
    for ticket in tickets:
        ticket_info = format_func(ticket)
        status_groups[ticket_info['status']].append(ticket_info)
    return dict(status_groups)


def generate_report_header(title: str, start_date: str, end_date: str) -> List[str]:
    """
    Generate standard report header with title and metadata.
    
    Args:
        title: Report title
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List[str]: Report header lines
    """
    return [
        f"## 📊 {title.upper()}: {start_date} to {end_date}",
        "",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        ""
    ]


def generate_overview_section(categorized_tickets: Dict[str, List], 
                            custom_title: str = "OVERVIEW") -> List[str]:
    """
    Generate overview section with ticket counts by category.
    
    Args:
        categorized_tickets: Dictionary of tickets grouped by category
        custom_title: Custom title for the overview section
        
    Returns:
        List[str]: Overview section lines
    """
    total_tickets = sum(len(tickets) for tickets in categorized_tickets.values())
    
    overview = [
        f"### 📈 {custom_title}",
        f"- **Total Tickets:** {total_tickets}"
    ]
    
    for category, tickets in categorized_tickets.items():
        if tickets:  # Only show categories with tickets
            overview.append(f"- **{category}:** {len(tickets)} tickets")
    
    overview.append("")
    return overview


def generate_category_section(category_name: str, category_description: str, 
                            tickets: List[Any], format_func) -> List[str]:
    """
    Generate a complete category section with status breakdowns.
    
    Args:
        category_name: Name of the category
        category_description: Description of the category
        tickets: List of tickets in this category
        format_func: Function to format ticket info
        
    Returns:
        List[str]: Complete category section lines
    """
    section = [
        f"### 🎯 {category_name.upper()} - {category_description}",
        ""
    ]
    
    if not tickets:
        section.extend([
            "*No tickets found for this category this week.*",
            ""
        ])
        return section
    
    # Group by status and create subsections
    status_groups = group_tickets_by_status(tickets, format_func)
    
    for status, status_tickets in status_groups.items():
        section.extend([
            f"#### 📌 {status} ({len(status_tickets)} tickets)",
            ""
        ])
        
        # Add table
        section.extend(create_table_header())
        for ticket in status_tickets:
            section.append(format_table_row(ticket))
        section.append("")
    
    return section


def generate_uncategorized_section(tickets: List[Any], format_func, 
                                 title: str = "OTHER / UNCATEGORIZED TICKETS") -> List[str]:
    """
    Generate section for uncategorized tickets.
    
    Args:
        tickets: List of uncategorized tickets
        format_func: Function to format ticket info
        title: Section title
        
    Returns:
        List[str]: Uncategorized section lines
    """
    if not tickets:
        return []
    
    section = [
        f"### 🔍 {title}",
        ""
    ]
    
    # Add table
    section.extend(create_table_header())
    for ticket in tickets:
        ticket_info = format_func(ticket)
        section.append(format_table_row(ticket_info))
    section.append("")
    
    return section


def generate_report_footer() -> List[str]:
    """
    Generate standard report footer.
    
    Returns:
        List[str]: Report footer lines
    """
    return [
        "---",
        "",
        "### ✅ Report Complete",
        "",
        "*This report was generated automatically from Jira data.*"
    ]


def ensure_reports_directory(reports_dir: str = "Reports") -> str:
    """
    Ensure the reports directory exists, create if it doesn't.
    
    Args:
        reports_dir: Directory name for reports
        
    Returns:
        str: Path to the reports directory
    """
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir


def generate_filename(prefix: str, start_date: str, end_date: str, 
                     extension: str = "md") -> str:
    """
    Generate a standardized filename for reports.
    
    Args:
        prefix: Filename prefix (e.g., 'jira_weekly_summary', 'github_weekly_summary')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        extension: File extension (default: 'md')
        
    Returns:
        str: Generated filename
        
    Example:
        filename = generate_filename('jira_weekly_summary', '2025-01-01', '2025-01-07')
        # Returns: 'jira_weekly_summary_2025-01-01_to_2025-01-07.md'
    """
    return f"{prefix}_{start_date}_to_{end_date}.{extension}"


def save_report(content: str, filename: str, reports_dir: str = "Reports") -> str:
    """
    Save report content to a file in the reports directory.
    
    Args:
        content: Report content to save
        filename: Filename for the report
        reports_dir: Directory to save reports in
        
    Returns:
        str: Full path to the saved file
        
    Example:
        filepath = save_report(report_content, 'jira_weekly_summary.md')
    """
    reports_path = ensure_reports_directory(reports_dir)
    filepath = os.path.join(reports_path, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"📄 Report saved to: {filepath}")
    return filepath


def create_summary_report(title: str, start_date: str, end_date: str,
                         categorized_tickets: Dict[str, List],
                         team_categories: Dict[str, Dict[str, Any]],
                         format_func) -> str:
    """
    Create a complete summary report with all sections.
    
    Args:
        title: Report title
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        categorized_tickets: Tickets grouped by category
        team_categories: Team category configuration
        format_func: Function to format ticket info
        
    Returns:
        str: Complete report as markdown string
    """
    report = []
    
    # Header
    report.extend(generate_report_header(title, start_date, end_date))
    
    # Overview
    report.extend(generate_overview_section(categorized_tickets))
    
    # Category sections
    for category_name, category_rules in team_categories.items():
        tickets = categorized_tickets.get(category_name, [])
        description = category_rules.get('description', 'No description')
        report.extend(generate_category_section(category_name, description, tickets, format_func))
    
    # Uncategorized section
    other_tickets = categorized_tickets.get('Other', [])
    report.extend(generate_uncategorized_section(other_tickets, format_func))
    
    # Footer
    report.extend(generate_report_footer())
    
    return "\n".join(report)


def format_duration(start_date: str, end_date: str) -> str:
    """
    Format a date range for display in report titles.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        str: Formatted duration string
        
    Example:
        duration = format_duration('2025-01-01', '2025-01-07')
        # Returns: "January 1 - 7, 2025" (if same month)
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    if start_dt.year == end_dt.year and start_dt.month == end_dt.month:
        # Same month
        return f"{start_dt.strftime('%B %d')} - {end_dt.day}, {start_dt.year}"
    elif start_dt.year == end_dt.year:
        # Same year, different months
        return f"{start_dt.strftime('%B %d')} - {end_dt.strftime('%B %d')}, {start_dt.year}"
    else:
        # Different years
        return f"{start_dt.strftime('%B %d, %Y')} - {end_dt.strftime('%B %d, %Y')}"
