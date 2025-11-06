#!/usr/bin/env python3
"""
Engineer Quarterly Performance Report Generator

Generates comprehensive quarterly performance reports focused on individual engineers,
tracking their GitHub and Jira activity week-by-week across the quarter with coaching insights.

This report provides:
- Individual engineer performance tracking with weekly granularity
- Performance trend analysis (increasing/stable/decreasing)
- Coaching insights based on configurable thresholds
- Collaboration pattern analysis
- Cross-engineer performance comparisons

Usage:
    python3 engineer_quarterly_performance.py [year] [quarter] [config_file]
    python3 engineer_quarterly_performance.py 2025 2
    python3 engineer_quarterly_performance.py  # Uses current quarter
    python3 engineer_quarterly_performance.py 2025 2 config/jira_config.yaml
"""

import sys
import os
from typing import List, Dict, Any, Tuple
from datetime import datetime
import statistics

from dotenv import load_dotenv
from team_reports.utils.date import get_current_quarter, get_quarter_range
from team_reports.utils.config import load_config, get_config
from team_reports.utils.report import save_report, ensure_reports_directory, render_active_config, render_glossary
from team_reports.utils.engineer_performance import (
    collect_weekly_engineer_data, 
    compute_engineer_trends, 
    generate_coaching_insights,
    format_weekly_metrics_table,
    filter_active_engineers,
    validate_data_quality
)

# Load environment variables
load_dotenv()


class EngineerQuarterlyPerformance:
    """Main class for generating engineer quarterly performance reports."""
    
    def __init__(
        self,
        jira_config_file: str = 'config/jira_config.yaml',
        github_config_file: str = 'config/github_config.yaml',
        jira_server: str = None,
        jira_email: str = None,
        jira_token: str = None,
        github_token: str = None
    ):
        """
        Initialize with configuration and optional credentials.
        
        Args:
            jira_config_file: Path to Jira configuration file
            github_config_file: Path to GitHub configuration file
            jira_server: Optional Jira server URL (overrides environment)
            jira_email: Optional Jira email (overrides environment)
            jira_token: Optional Jira API token (overrides environment)
            github_token: Optional GitHub API token (overrides environment)
        """
        self.jira_config_file = jira_config_file
        self.github_config_file = github_config_file
        self.jira_server = jira_server
        self.jira_email = jira_email
        self.jira_token = jira_token
        self.github_token = github_token
        self.config = get_config([jira_config_file])  # Fix: wrap in list
        
    def generate_report(self, year: int, quarter: int) -> str:
        """Generate the complete engineer quarterly performance report."""
        print(f"\n🚀 Generating Engineer Quarterly Performance Report for Q{quarter} {year}")
        
        # Collect all engineer data for the quarter
        print("📊 Collecting engineer performance data...")
        engineer_data = collect_weekly_engineer_data(
            year, quarter, 
            self.jira_config_file, 
            self.github_config_file,
            jira_server=self.jira_server,
            jira_email=self.jira_email,
            jira_token=self.jira_token,
            github_token=self.github_token
        )
        
        if not engineer_data:
            return self._generate_empty_report(year, quarter)
        
        # Compute trends and insights
        print("📈 Computing performance trends...")
        trends = compute_engineer_trends(engineer_data)
        
        # Filter out low-activity engineers to match official reports
        print("🔍 Filtering active contributors...")
        engineer_data = filter_active_engineers(engineer_data, trends)
        
        # Validate data quality against official benchmarks
        print("✅ Validating data quality...")
        data_quality = validate_data_quality(engineer_data, trends)
        
        print("💡 Generating coaching insights...")
        coaching_insights = generate_coaching_insights(engineer_data, trends, self.config)
        
        # Generate report sections
        report_sections = []
        
        # Header
        report_sections.append(self._generate_header(year, quarter))
        
        # Executive Summary
        report_sections.append(self._generate_executive_summary(engineer_data, trends, coaching_insights))
        
        # Data Quality Validation
        report_sections.append(self._generate_data_quality_section(data_quality))
        
        # Individual Engineer Analysis
        report_sections.append(self._generate_individual_analysis(engineer_data, trends, coaching_insights))
        
        # Team Coaching Summary
        report_sections.append(self._generate_team_coaching_summary(engineer_data, trends, coaching_insights))
        
        # Glossary
        report_sections.append(self._generate_glossary())
        
        return '\n'.join(report_sections)
    
    def _generate_empty_report(self, year: int, quarter: int) -> str:
        """Generate report when no data is available."""
        return f"""# 📊 Engineer Quarterly Performance - Q{quarter} {year}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## No Data Available

No engineer performance data was found for Q{quarter} {year}. This could be due to:

- No tickets or PRs in the specified time period
- Configuration issues with team member mapping
- API connectivity problems

Please check your configuration and try again.
"""
    
    def _generate_header(self, year: int, quarter: int) -> str:
        """Generate report header."""
        start_date, end_date = get_quarter_range(year, quarter)
        return f"""# 📊 Engineer Quarterly Performance - Q{quarter} {year}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Period:** {start_date} to {end_date}  
**Focus:** Individual engineer performance tracking and coaching insights

---
"""
    
    def _generate_executive_summary(self, engineer_data: Dict[str, Any], 
                                   trends: Dict[str, Any], 
                                   coaching_insights: Dict[str, List[str]]) -> str:
        """Generate executive summary section."""
        total_engineers = len(engineer_data)
        
        # Calculate team-wide statistics
        team_stats = {
            'total_prs': 0,
            'total_tickets': 0,
            'total_commits': 0,
            'engineers_with_increasing_trend': 0,
            'engineers_needing_coaching': 0
        }
        
        for engineer, data in engineer_data.items():
            trend_data = trends.get(engineer, {})
            weekly_totals = trend_data.get('weekly_totals', {})
            
            team_stats['total_prs'] += weekly_totals.get('total_prs', 0)
            team_stats['total_tickets'] += weekly_totals.get('total_tickets', 0)
            
            # Count commits across all weeks
            for week_data in data['weeks'].values():
                team_stats['total_commits'] += week_data['github']['commits']
            
            # Count trends
            if trend_data.get('productivity_trend') == 'increasing':
                team_stats['engineers_with_increasing_trend'] += 1
                
            # Count engineers with coaching insights
            if coaching_insights.get(engineer):
                team_stats['engineers_needing_coaching'] += 1
        
        # Find top performers
        top_performers = []
        for engineer, data in engineer_data.items():
            trend_data = trends.get(engineer, {})
            weekly_totals = trend_data.get('weekly_totals', {})
            total_output = weekly_totals.get('total_prs', 0) + weekly_totals.get('total_tickets', 0)
            
            display_name = data.get('display_name', engineer)
            top_performers.append((display_name, total_output, trend_data.get('productivity_trend', 'stable')))
        
        top_performers.sort(key=lambda x: x[1], reverse=True)
        
        section = f"""## 📈 Executive Summary

### Team Overview
- **Engineers Tracked:** {total_engineers}
- **Total PRs Merged:** {team_stats['total_prs']}
- **Total Tickets Completed:** {team_stats['total_tickets']} 
- **Total Commits:** {team_stats['total_commits']}

### Performance Trends
- **Engineers with Increasing Productivity:** {team_stats['engineers_with_increasing_trend']} ({team_stats['engineers_with_increasing_trend']/total_engineers*100:.1f}%)
- **Engineers Requiring Coaching Attention:** {team_stats['engineers_needing_coaching']} ({team_stats['engineers_needing_coaching']/total_engineers*100:.1f}%)

### Top Performers (by combined output)
"""
        
        for i, (name, output, trend) in enumerate(top_performers[:5], 1):
            trend_icon = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}[trend]
            section += f"{i}. **{name}** - {output} deliverables {trend_icon}\n"
        
        section += "\n---\n"
        return section
    
    def _generate_data_quality_section(self, data_quality: Dict[str, Any]) -> str:
        """Generate data quality validation section."""
        computed = data_quality['computed_totals']
        benchmarks = data_quality['official_benchmarks']
        validation = data_quality['validation_status']
        variance = data_quality['variance_percentages']
        
        section = f"""## 🔍 Data Quality Validation
        
### Alignment with Official Q3 2025 Reports

| Metric | Computed | Official Benchmark | Variance | Status |
|--------|----------|-------------------|----------|--------|
| **PRs Merged** | {computed['prs']} | {benchmarks['prs']} | {variance['prs']:.1f}% | {'✅' if validation['pr_accuracy'] else '⚠️'} |
| **Tickets Completed** | {computed['tickets']} | {benchmarks['tickets']} | {variance['tickets']:.1f}% | {'✅' if validation['ticket_accuracy'] else '⚠️'} |
| **Active Contributors** | {computed['contributors']} | {benchmarks['contributors']} | — | {'✅' if validation['contributor_count_valid'] else '⚠️'} |

### Data Quality Status

"""
        
        if validation['overall_valid']:
            section += "✅ **EXCELLENT**: All metrics align with official reports (within 5% variance)\n\n"
        else:
            section += "⚠️ **NEEDS ATTENTION**: Some metrics deviate from official benchmarks\n\n"
            
            if not validation['pr_accuracy']:
                section += f"- PR count variance: {variance['prs']:.1f}% (target: <5%)\n"
            if not validation['ticket_accuracy']:
                section += f"- Ticket count variance: {variance['tickets']:.1f}% (target: <5%)\n"
            if not validation['contributor_count_valid']:
                section += f"- Contributor count outside expected range: {computed['contributors']} (target: {benchmarks['contributors']})\n"
            section += "\n"
        
        section += """### Data Processing Notes

- **Bot Exclusion**: Automated accounts filtered using regex patterns
- **Identity Consolidation**: Cross-system user mapping applied (GitHub ↔ Jira)
- **Activity Threshold**: Engineers with <1 PR AND <3 tickets excluded
- **Date Alignment**: Uses same date ranges as official quarterly reports

---
"""
        return section
    
    def _generate_individual_analysis(self, engineer_data: Dict[str, Any], 
                                     trends: Dict[str, Any], 
                                     coaching_insights: Dict[str, List[str]]) -> str:
        """Generate individual engineer analysis sections."""
        section = "\n## 👤 Individual Engineer Analysis\n\n"
        
        # Sort engineers by total output for consistent ordering
        sorted_engineers = []
        for engineer, data in engineer_data.items():
            trend_data = trends.get(engineer, {})
            weekly_totals = trend_data.get('weekly_totals', {})
            total_output = weekly_totals.get('total_prs', 0) + weekly_totals.get('total_tickets', 0)
            display_name = data.get('display_name', engineer)
            sorted_engineers.append((engineer, display_name, total_output))
        
        sorted_engineers.sort(key=lambda x: x[2], reverse=True)
        
        for engineer, display_name, _ in sorted_engineers:
            data = engineer_data[engineer]
            trend_data = trends.get(engineer, {})
            insights = coaching_insights.get(engineer, [])
            
            section += f"### 🔍 {display_name}\n\n"
            
            # Week-by-week metrics table
            section += "#### 📊 Weekly Performance Metrics\n\n"
            section += format_weekly_metrics_table(engineer, data, trend_data)
            section += "\n"
            
            # Performance summary
            weekly_totals = trend_data.get('weekly_totals', {})
            section += "#### 📋 Quarter Summary\n\n"
            section += f"- **Total PRs Merged:** {weekly_totals.get('total_prs', 0)}\n"
            section += f"- **Total Tickets Completed:** {weekly_totals.get('total_tickets', 0)}\n"
            section += f"- **Average PRs per Week:** {weekly_totals.get('avg_prs_per_week', 0):.1f}\n"
            section += f"- **Average Tickets per Week:** {weekly_totals.get('avg_tickets_per_week', 0):.1f}\n"
            
            # Productivity trend
            productivity_trend = trend_data.get('productivity_trend', 'stable')
            trend_icon = {'increasing': '📈', 'decreasing': '📉', 'stable': '➡️'}[productivity_trend]
            section += f"- **Productivity Trend:** {trend_icon} {productivity_trend.title()}\n\n"
            
            # Coaching insights
            if insights:
                section += "#### 💡 Coaching Insights\n\n"
                for insight in insights:
                    section += f"- {insight}\n"
            else:
                section += "#### ✅ No Coaching Concerns\n\nPerformance metrics are within expected ranges.\n"
            
            section += "\n---\n\n"
        
        return section
    
    def _generate_team_coaching_summary(self, engineer_data: Dict[str, Any], 
                                       trends: Dict[str, Any], 
                                       coaching_insights: Dict[str, List[str]]) -> str:
        """Generate team-wide coaching summary."""
        section = "## 🎯 Team Coaching Summary\n\n"
        
        # Cross-engineer analysis
        section += "### 📊 Cross-Engineer Analysis\n\n"
        
        # Performance distribution
        performance_levels = {'high': [], 'medium': [], 'low': []}
        collaboration_scores = []
        
        for engineer, data in engineer_data.items():
            trend_data = trends.get(engineer, {})
            weekly_totals = trend_data.get('weekly_totals', {})
            total_output = weekly_totals.get('total_prs', 0) + weekly_totals.get('total_tickets', 0)
            display_name = data.get('display_name', engineer)
            
            # Categorize performance
            if total_output >= 20:  # High performer
                performance_levels['high'].append(display_name)
            elif total_output >= 10:  # Medium performer
                performance_levels['medium'].append(display_name)
            else:  # Needs attention
                performance_levels['low'].append(display_name)
            
            # Calculate collaboration score
            total_reviews_given = sum(week['github']['reviews_given'] for week in data['weeks'].values())
            total_reviews_received = sum(week['github']['reviews_received'] for week in data['weeks'].values())
            collab_score = total_reviews_given + total_reviews_received
            collaboration_scores.append((display_name, collab_score))
        
        # Performance distribution
        section += "#### 🏆 Performance Distribution\n\n"
        section += f"- **High Performers (20+ deliverables):** {len(performance_levels['high'])} engineers\n"
        if performance_levels['high']:
            section += f"  - {', '.join(performance_levels['high'])}\n"
        
        section += f"- **Solid Performers (10-19 deliverables):** {len(performance_levels['medium'])} engineers\n"
        if performance_levels['medium']:
            section += f"  - {', '.join(performance_levels['medium'])}\n"
        
        section += f"- **Need Attention (<10 deliverables):** {len(performance_levels['low'])} engineers\n"
        if performance_levels['low']:
            section += f"  - {', '.join(performance_levels['low'])}\n"
        
        section += "\n"
        
        # Collaboration analysis
        section += "#### 🤝 Collaboration Network\n\n"
        collaboration_scores.sort(key=lambda x: x[1], reverse=True)
        
        section += "**Most Collaborative Engineers (by review activity):**\n"
        for i, (name, score) in enumerate(collaboration_scores[:5], 1):
            section += f"{i}. {name} - {score} review interactions\n"
        
        section += "\n"
        
        # Priority coaching areas
        section += "### 🎯 Priority Coaching Areas\n\n"
        
        coaching_categories = {
            'productivity': [],
            'collaboration': [],
            'workload': [],
            'trends': []
        }
        
        for engineer, insights in coaching_insights.items():
            display_name = engineer_data[engineer].get('display_name', engineer)
            for insight in insights:
                if 'Low PR output' in insight or 'Limited activity' in insight:
                    coaching_categories['productivity'].append((display_name, insight))
                elif 'review participation' in insight or 'Not participating' in insight:
                    coaching_categories['collaboration'].append((display_name, insight))
                elif 'High WIP levels' in insight:
                    coaching_categories['workload'].append((display_name, insight))
                elif 'trend decreasing' in insight:
                    coaching_categories['trends'].append((display_name, insight))
        
        for category, issues in coaching_categories.items():
            if issues:
                category_title = {
                    'productivity': '📉 Productivity Concerns',
                    'collaboration': '🤝 Collaboration Opportunities',
                    'workload': '🚧 Workload Management',
                    'trends': '📈 Performance Trends'
                }[category]
                
                section += f"#### {category_title}\n\n"
                for name, insight in issues:
                    section += f"- **{name}:** {insight}\n"
                section += "\n"
        
        if not any(coaching_categories.values()):
            section += "#### ✅ No Critical Issues Identified\n\nTeam performance metrics are within expected ranges.\n\n"
        
        section += "---\n"
        return section
    
    def _generate_glossary(self) -> str:
        """Generate glossary section for metrics."""
        glossary_entries = {
            "PR Lead Time": "Duration from first commit to PR merge.",
            "Cycle Time": "Time from 'In Progress' to 'Done' for Jira tickets.",
            "WIP": "Work In Progress - tickets currently in active states.",
            "Review Depth": "Number of reviewers and comments per PR.",
            "Productivity Trend": "Analysis of output changes over time (increasing/stable/decreasing).",
            "Collaboration Score": "Combined review giving and receiving activity."
        }
        
        return render_glossary(glossary_entries)


def main():
    """Main entry point for engineer quarterly performance report."""
    try:
        # Parse command line arguments
        config_file = 'config/jira_config.yaml'
        args = []
        
        # Filter command line arguments
        for arg in sys.argv[1:]:
            if arg in ['-h', '--help']:
                print(__doc__)
                print("\nUsage:")
                print("  python3 engineer_quarterly_performance.py [year] [quarter] [config_file]")
                print("\nExamples:")
                print("  python3 engineer_quarterly_performance.py 2025 2")
                print("  python3 engineer_quarterly_performance.py  # Uses current quarter")
                print("  python3 engineer_quarterly_performance.py 2025 2 config/custom_jira_config.yaml")
                sys.exit(0)
            elif arg.endswith('.yaml'):
                config_file = arg
            else:
                args.append(arg)
        
        # Parse year and quarter
        if len(args) >= 2:
            try:
                year = int(args[0])
                quarter = int(args[1])
            except ValueError:
                raise ValueError(f"Year and quarter must be integers, got: {args[0]}, {args[1]}")
        elif len(args) == 1:
            try:
                year = int(args[0])
                current_year, current_quarter, _, _ = get_current_quarter()
                quarter = current_quarter
            except ValueError:
                raise ValueError(f"Year must be an integer, got: {args[0]}")
        else:
            year, quarter, _, _ = get_current_quarter()
        
        # Validate quarter
        if not 1 <= quarter <= 4:
            raise ValueError(f"Quarter must be between 1 and 4, got: {quarter}")
        
        print(f"🚀 Engineer Quarterly Performance Analysis")
        print(f"📅 Period: Q{quarter} {year}")
        print(f"⚙️ Config: {config_file}")
        
        # Generate report
        performance_analyzer = EngineerQuarterlyPerformance(config_file)
        report = performance_analyzer.generate_report(year, quarter)
        
        # Add active configuration if enabled
        config = get_config([config_file])  # Fix: wrap in list
        def flag(path: str) -> bool:
            keys = path.split('.')
            value = config
            try:
                for key in keys:
                    value = value[key]
                return bool(value)
            except (KeyError, TypeError):
                return False
        
        if flag("report.show_active_config"):
            config_section = render_active_config(config)
            report += "\n" + config_section
        
        # Save report
        ensure_reports_directory()
        filename = f"engineer_quarterly_performance_Q{quarter}_{year}.md"
        filepath = save_report(report, filename)
        
        print(f"\n✅ Engineer Quarterly Performance Report Generated Successfully!")
        print(f"📄 Report saved to: {filepath}")
        print(f"📅 Period: Q{quarter} {year}")
        
    except ValueError as e:
        print(f"❌ Invalid input: {e}")
        print("Usage: python3 engineer_quarterly_performance.py [year] [quarter] [config_file]")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating engineer quarterly performance report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
