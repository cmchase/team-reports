#!/usr/bin/env python3
"""
Command-line interface for team-reports using Click.

Provides unified CLI for all report types with modern command structure.
"""

import sys
import click
from datetime import datetime
from typing import Optional

# Ensure dotenv is loaded before importing report modules
from dotenv import load_dotenv
load_dotenv()

from team_reports.reports.jira_weekly import WeeklyJiraSummary
from team_reports.reports.jira_quarterly import QuarterlyTeamSummary
from team_reports.reports.github_weekly import WeeklyGitHubSummary
from team_reports.reports.github_quarterly import GitHubQuarterlySummary
from team_reports.reports.engineer_performance import EngineerQuarterlyPerformance
from team_reports.utils.date import get_current_week, get_current_quarter, parse_date_args
# Note: batch command temporarily disabled - use shell script ./run_batch_weekly.sh instead


@click.group()
@click.version_option(version='1.0.0', prog_name='team-reports')
def cli():
    """Team Reports - Automated reporting from Jira and GitHub.
    
    Generate weekly, quarterly, and performance reports with rich analytics.
    """
    pass


@cli.group()
def jira():
    """Jira report commands."""
    pass


@cli.group()
def github():
    """GitHub report commands."""
    pass


@cli.group()
def engineer():
    """Engineer performance report commands."""
    pass


@jira.command('weekly')
@click.argument('start_date', required=False)
@click.argument('end_date', required=False)
@click.option('--config', default='config/jira_config.yaml', help='Path to configuration file')
@click.option('--jira-server', help='Jira server URL (overrides environment)')
@click.option('--jira-email', help='Jira email (overrides environment)')
@click.option('--jira-token', help='Jira API token (overrides environment)')
def jira_weekly(start_date: Optional[str], end_date: Optional[str], config: str,
                jira_server: Optional[str], jira_email: Optional[str], jira_token: Optional[str]):
    """Generate weekly Jira report.
    
    If no dates provided, uses current week.
    
    Examples:
        team-reports jira weekly
        team-reports jira weekly 2025-01-01 2025-01-07
        team-reports jira weekly --config custom.yaml
    """
    try:
        # Parse dates or use current week
        if start_date and end_date:
            start, end = start_date, end_date
        else:
            start, end = get_current_week()
        
        click.echo(f"Generating Jira weekly report: {start} to {end}")
        
        # Create report instance with credentials
        report = WeeklyJiraSummary(
            config_file=config,
            jira_server=jira_server,
            jira_email=jira_email,
            jira_token=jira_token
        )
        
        # Generate complete weekly summary (returns report and tickets)
        summary, tickets = report.generate_weekly_summary(start, end)
        
        # Save report
        from team_reports.utils.report import save_report, generate_filename
        filename = generate_filename('jira_weekly_summary', start, end)
        filepath = save_report(summary, filename)
        
        click.echo(click.style("✅ Report generated successfully!", fg='green'))
        click.echo(f"📄 Report saved to: {filepath}")
        
    except Exception as e:
        import traceback
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        traceback.print_exc()
        sys.exit(1)


@jira.command('quarterly')
@click.argument('year', type=int, required=False)
@click.argument('quarter', type=int, required=False)
@click.option('--config', default='config/jira_config.yaml', help='Path to configuration file')
@click.option('--jira-server', help='Jira server URL (overrides environment)')
@click.option('--jira-email', help='Jira email (overrides environment)')
@click.option('--jira-token', help='Jira API token (overrides environment)')
def jira_quarterly(year: Optional[int], quarter: Optional[int], config: str,
                   jira_server: Optional[str], jira_email: Optional[str], jira_token: Optional[str]):
    """Generate quarterly Jira report.
    
    If no year/quarter provided, uses current quarter.
    
    Examples:
        team-reports jira quarterly
        team-reports jira quarterly 2025 4
        team-reports jira quarterly --config custom.yaml
    """
    try:
        # Use current quarter if not provided
        if year is None or quarter is None:
            year, quarter = get_current_quarter()
        
        click.echo(f"Generating Jira quarterly report: Q{quarter} {year}")
        
        # Create report instance with credentials
        report = QuarterlyTeamSummary(
            config_file=config,
            jira_server=jira_server,
            jira_email=jira_email,
            jira_token=jira_token
        )
        
        # Generate report
        summary, tickets = report.generate_quarterly_summary(year, quarter)
        
        # Save report
        from team_reports.utils.report import save_report
        filename = f"jira_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(summary, filename)
        
        click.echo(click.style("✅ Report generated successfully!", fg='green'))
        click.echo(f"📄 Report saved to: {filepath}")
        click.echo(f"📅 Period: Q{quarter} {year}")
        
    except Exception as e:
        import traceback
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        traceback.print_exc()
        sys.exit(1)


@github.command('weekly')
@click.argument('start_date', required=False)
@click.argument('end_date', required=False)
@click.option('--config', default='config/github_config.yaml', help='Path to configuration file')
@click.option('--github-token', help='GitHub API token (overrides environment)')
def github_weekly(start_date: Optional[str], end_date: Optional[str], config: str,
                  github_token: Optional[str]):
    """Generate weekly GitHub report.
    
    If no dates provided, uses current week.
    
    Examples:
        team-reports github weekly
        team-reports github weekly 2025-01-01 2025-01-07
        team-reports github weekly --github-token YOUR_TOKEN
    """
    try:
        # Parse dates or use current week
        if start_date and end_date:
            start, end = start_date, end_date
        else:
            start, end = get_current_week()
        
        click.echo(f"Generating GitHub weekly report: {start} to {end}")
        
        # Create report instance with credentials
        report = WeeklyGitHubSummary(
            config_file=config,
            github_token=github_token
        )
        
        # Generate report
        summary, data = report.generate_report(start, end, config)
        
        # Save report
        from team_reports.utils.report import save_report, generate_filename
        filename = generate_filename('github_weekly_summary', start, end)
        filepath = save_report(summary, filename)
        
        click.echo(click.style("✅ Report generated successfully!", fg='green'))
        click.echo(f"📄 Report saved to: {filepath}")
        
    except Exception as e:
        import traceback
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        traceback.print_exc()
        sys.exit(1)


@github.command('quarterly')
@click.argument('year', type=int, required=False)
@click.argument('quarter', type=int, required=False)
@click.option('--config', default='config/github_config.yaml', help='Path to configuration file')
@click.option('--github-token', help='GitHub API token (overrides environment)')
def github_quarterly(year: Optional[int], quarter: Optional[int], config: str,
                     github_token: Optional[str]):
    """Generate quarterly GitHub report.
    
    If no year/quarter provided, uses current quarter.
    
    Examples:
        team-reports github quarterly
        team-reports github quarterly 2025 4
        team-reports github quarterly --github-token YOUR_TOKEN
    """
    try:
        # Use current quarter if not provided
        if year is None or quarter is None:
            year, quarter = get_current_quarter()
        
        click.echo(f"Generating GitHub quarterly report: Q{quarter} {year}")
        
        # Create report instance with credentials
        report = GitHubQuarterlySummary(
            config_file=config,
            github_token=github_token
        )
        
        # Generate report
        summary, data = report.generate_quarterly_summary(year, quarter)
        
        # Save report
        from team_reports.utils.report import save_report
        filename = f"github_quarterly_summary_Q{quarter}_{year}.md"
        filepath = save_report(summary, filename)
        
        click.echo(click.style("✅ Report generated successfully!", fg='green'))
        click.echo(f"📄 Report saved to: {filepath}")
        click.echo(f"📅 Period: Q{quarter} {year}")
        
    except Exception as e:
        import traceback
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        traceback.print_exc()
        sys.exit(1)


@engineer.command('performance')
@click.argument('year', type=int, required=False)
@click.argument('quarter', type=int, required=False)
@click.option('--jira-config', default='config/jira_config.yaml', help='Path to Jira configuration file')
@click.option('--github-config', default='config/github_config.yaml', help='Path to GitHub configuration file')
@click.option('--jira-server', help='Jira server URL (overrides environment)')
@click.option('--jira-email', help='Jira email (overrides environment)')
@click.option('--jira-token', help='Jira API token (overrides environment)')
@click.option('--github-token', help='GitHub API token (overrides environment)')
def engineer_performance(year: Optional[int], quarter: Optional[int],
                        jira_config: str, github_config: str,
                        jira_server: Optional[str], jira_email: Optional[str],
                        jira_token: Optional[str], github_token: Optional[str]):
    """Generate engineer quarterly performance report.
    
    If no year/quarter provided, uses current quarter.
    
    Examples:
        team-reports engineer performance
        team-reports engineer performance 2025 2
        team-reports engineer performance --jira-config custom.yaml
    """
    try:
        # Use current quarter if not provided
        if year is None or quarter is None:
            year, quarter = get_current_quarter()
        
        click.echo(f"Generating Engineer Performance report: Q{quarter} {year}")
        
        # Create report instance with credentials
        report = EngineerQuarterlyPerformance(
            jira_config_file=jira_config,
            github_config_file=github_config,
            jira_server=jira_server,
            jira_email=jira_email,
            jira_token=jira_token,
            github_token=github_token
        )
        
        # Generate report
        summary = report.generate_report(year, quarter)
        
        # Save report
        from team_reports.utils.report import save_report
        filename = f"engineer_quarterly_performance_Q{quarter}_{year}.md"
        filepath = save_report(summary, filename)
        
        click.echo(click.style("✅ Report generated successfully!", fg='green'))
        click.echo(f"📄 Report saved to: {filepath}")
        click.echo(f"📅 Period: Q{quarter} {year}")
        
    except Exception as e:
        import traceback
        click.echo(click.style(f"❌ Error: {e}", fg='red'), err=True)
        traceback.print_exc()
        sys.exit(1)


# Batch command temporarily disabled - use shell script instead:
# ./run_batch_weekly.sh jira last-4
# ./run_batch_weekly.sh github 2025-09-01:6
#
# @cli.command('batch')
# @click.argument('report_type', type=click.Choice(['jira', 'github']))
# @click.argument('spec')
# @click.option('--config', help='Path to configuration file')
# def batch(report_type: str, spec: str, config: Optional[str]):
#     """Generate multiple weekly reports in batch."""
#     click.echo("Batch command currently uses shell script: ./run_batch_weekly.sh")
#     click.echo(f"Example: ./run_batch_weekly.sh {report_type} {spec}")
#     sys.exit(1)


if __name__ == '__main__':
    cli()
