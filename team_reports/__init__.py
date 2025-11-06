"""
Team Reports - Automated team reporting from Jira and GitHub

A comprehensive suite of tools for generating automated team summaries and 
performance reports from multiple data sources including Jira tickets and 
GitHub repositories.
"""

__version__ = "1.0.0"

# Import report classes for public API
from team_reports.reports.jira_weekly import WeeklyTeamSummary
from team_reports.reports.jira_quarterly import QuarterlyTeamSummary
from team_reports.reports.github_weekly import GitHubWeeklySummary
from team_reports.reports.github_quarterly import GitHubQuarterlySummary
from team_reports.reports.engineer_performance import EngineerQuarterlyPerformance

__all__ = [
    'WeeklyTeamSummary',
    'QuarterlyTeamSummary',
    'GitHubWeeklySummary',
    'GitHubQuarterlySummary',
    'EngineerQuarterlyPerformance',
    '__version__',
]
