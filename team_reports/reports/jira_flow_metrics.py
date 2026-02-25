#!/usr/bin/env python3
"""
Flow metrics report: cycle time, lead time, throughput, and predictability.

Uses Jira issues resolved in a date range; cycle = first execution status -> completed,
lead = created -> completed. Reads status_filters (execution, completed) from Jira config.
"""

from typing import Any, Dict, List, Optional

from team_reports.utils.jira import (
    fetch_flow_issues,
    flow_stats,
    cycle_and_lead_from_issue,
    format_duration_days,
)
from team_reports.utils.jira_summary_base import JiraSummaryBase


class JiraFlowMetricsReport(JiraSummaryBase):
    """Generate flow metrics (cycle time, lead time, throughput) for a date range."""

    def __init__(
        self,
        config_file: str = "config/jira_config.yaml",
        jira_server: Optional[str] = None,
        jira_email: Optional[str] = None,
        jira_token: Optional[str] = None,
    ):
        super().__init__(
            config_file=config_file,
            jira_server=jira_server,
            jira_email=jira_email,
            jira_token=jira_token,
        )

    def _get_status_lists(self) -> Dict[str, List[str]]:
        """Return execution and completed status lists from config."""
        status_filters = self.config.get("status_filters") or {}
        return {
            "execution": status_filters.get("execution") or ["In Progress", "Review"],
            "completed": status_filters.get("completed") or ["Closed", "Done"],
        }

    def generate_report(
        self,
        start_date: str,
        end_date: str,
        max_issues: int = 300,
    ) -> str:
        """
        Generate flow metrics report for the given date range.
        Returns markdown report text.
        """
        self.initialize()
        status_lists = self._get_status_lists()
        execution_statuses = status_lists["execution"]
        completed_statuses = status_lists["completed"]

        base_jql = " ".join((self.base_jql or "project is not empty").strip().split())
        completed_jql = ", ".join(f'"{s}"' for s in completed_statuses)
        jql = (
            f'({base_jql}) AND status IN ({completed_jql}) '
            f'AND resolutiondate >= "{start_date}" AND resolutiondate <= "{end_date}" '
            f'ORDER BY resolutiondate DESC'
        )

        total_throughput, issues = fetch_flow_issues(
            self.jira_client.jira_client, jql, max_issues
        )

        cycle_days_list: List[float] = []
        lead_days_list: List[float] = []
        for issue in issues:
            cycle_days, lead_days = cycle_and_lead_from_issue(
                issue, execution_statuses, completed_statuses
            )
            if cycle_days is not None:
                cycle_days_list.append(cycle_days)
            if lead_days is not None:
                lead_days_list.append(lead_days)

        cycle_stats = flow_stats(cycle_days_list)
        lead_stats = flow_stats(lead_days_list)
        throughput_note = str(total_throughput)
        if total_throughput > len(issues):
            throughput_note += (
                f" (cycle/lead from first {len(issues)}; increase max_issues for full sample)"
            )

        lines = [
            "## Flow metrics",
            f"**Period:** {start_date} to {end_date}",
            f"**Throughput:** {throughput_note} issues completed",
            "",
            "### Cycle time (execution → done)",
            "Time from first transition into an execution status (e.g. In Progress, Review) to first transition into a completed status.",
            "",
        ]
        if cycle_stats["count"] == 0:
            lines.append(
                "No cycle time data (changelog may be missing or status names may not match config)."
            )
        else:
            lines.append(f"- **Average:** {format_duration_days(cycle_stats['avg'])}")
            lines.append(f"- **Median:** {format_duration_days(cycle_stats['median'])}")
            lines.append(
                f"- **Min:** {format_duration_days(cycle_stats['min'])} | **Max:** {format_duration_days(cycle_stats['max'])}"
            )
            lines.append(
                f"- **Std dev:** {format_duration_days(cycle_stats['std_dev'])} (lower = more predictable)"
            )
            lines.append(
                f"- **85th %ile:** {format_duration_days(cycle_stats['p85'])} | **95th %ile:** {format_duration_days(cycle_stats['p95'])}"
            )
            lines.append(f"- *Based on {cycle_stats['count']} issues with computable cycle time.*")
        lines.extend([
            "",
            "### Lead time (created → done)",
            "Time from issue creation to first transition into a completed status.",
            "",
        ])
        if lead_stats["count"] == 0:
            lines.append("No lead time data.")
        else:
            lines.append(f"- **Average:** {format_duration_days(lead_stats['avg'])}")
            lines.append(f"- **Median:** {format_duration_days(lead_stats['median'])}")
            lines.append(
                f"- **Min:** {format_duration_days(lead_stats['min'])} | **Max:** {format_duration_days(lead_stats['max'])}"
            )
            lines.append(f"- **Std dev:** {format_duration_days(lead_stats['std_dev'])}")
            lines.append(
                f"- **85th %ile:** {format_duration_days(lead_stats['p85'])} | **95th %ile:** {format_duration_days(lead_stats['p95'])}"
            )
            lines.append(f"- *Based on {lead_stats['count']} issues.*")
        lines.extend([
            "",
            "---",
            "*Throughput = all issues matching base_jql + completed status + resolution date in period. Tighten base_jql in config to scope to one team or board.*",
            "*Cycle/lead use config status_filters (execution, completed). Kanban-friendly; review weekly, monthly, or quarterly for trends.*",
        ])
        return "\n".join(lines)
