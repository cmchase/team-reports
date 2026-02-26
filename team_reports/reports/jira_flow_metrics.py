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

    def _get_flow_config(self) -> Dict[str, Any]:
        """Return flow_metrics config with defaults."""
        return self.config.get("flow_metrics") or {}

    def _focus_suggestion(
        self,
        cycle_stats: Dict[str, float],
        lead_stats: Dict[str, float],
        total_throughput: int,
    ) -> str:
        """One short suggested focus line from heuristics."""
        if cycle_stats.get("std_dev", 0) > 14:
            return "Review items with cycle time > 3 weeks."
        if lead_stats.get("std_dev", 0) > 30:
            return "Reduce lead time variance (many long-lived items)."
        if total_throughput < 15:
            return "Understand throughput (low completion count this period)."
        return "Keep cycle and lead predictable; consider retro on slowest items."

    def _suggested_actions(
        self,
        cycle_stats: Dict[str, float],
        lead_stats: Dict[str, float],
        has_outliers: bool,
    ) -> List[str]:
        """Short list of suggested actions based on current metrics."""
        actions = []
        if has_outliers:
            actions.append("Retro: discuss 2–3 slowest cycle items.")
        if cycle_stats.get("std_dev", 0) > 14 or lead_stats.get("std_dev", 0) > 30:
            actions.append("Backlog review: items open > 4 weeks.")
        actions.append("Use next flow report to track trends.")
        return actions

    def _next_report_date(self, end_date: str, cadence: str) -> str:
        """Compute next report date from period end and cadence."""
        from datetime import datetime, timedelta
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            return ""
        if cadence == "bi-weekly":
            next_dt = end_dt + timedelta(days=14)
            return next_dt.strftime("%Y-%m-%d")
        # monthly: first day of next month (or last day of current month for "end of month")
        if end_dt.month == 12:
            next_dt = end_dt.replace(year=end_dt.year + 1, month=1, day=1)
        else:
            next_dt = end_dt.replace(month=end_dt.month + 1, day=1)
        return next_dt.strftime("%Y-%m-%d")

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

        issue_records: List[Dict[str, Any]] = []
        cycle_days_list: List[float] = []
        lead_days_list: List[float] = []
        for issue in issues:
            cycle_days, lead_days = cycle_and_lead_from_issue(
                issue, execution_statuses, completed_statuses
            )
            key = getattr(issue, "key", "")
            raw_summary = getattr(issue.fields, "summary", None) or ""
            summary = raw_summary[:60] + ("..." if len(raw_summary) > 60 else "")
            issue_records.append({
                "key": key,
                "summary": summary,
                "cycle_days": cycle_days,
                "lead_days": lead_days,
            })
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
        flow_cfg = self._get_flow_config()
        targets = flow_cfg.get("targets") or {}
        throughput_min = targets.get("throughput_min")
        if throughput_min is not None:
            met = total_throughput >= throughput_min
            throughput_note += f" (Target: ≥ {throughput_min} → {'✓' if met else '✗'})"

        lines = [
            "## Flow metrics",
            f"**Period:** {start_date} to {end_date}",
            f"**Throughput:** {throughput_note} issues completed",
            "",
        ]
        focus = self._focus_suggestion(cycle_stats, lead_stats, total_throughput)
        lines.append(f"**Suggested focus:** {focus}")
        lines.extend([
            "",
            "### Cycle time (execution → done)",
            "Time from first transition into an execution status (e.g. In Progress, Review) to first transition into a completed status.",
            "",
        ])
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
            lines.append(f"- *95th %ile → about 1 in 20 items take longer than {format_duration_days(cycle_stats['p95'])}; consider cap or escalation.*")
            threshold = (self.config.get("flow_metrics") or {}).get("sample_size_warning_threshold", 15)
            if cycle_stats["count"] < threshold:
                lines.append(f"- *Small sample (N={cycle_stats['count']}); treat percentiles with caution.*")
            lines.append(f"- *Based on {cycle_stats['count']} issues with computable cycle time.*")
            cycle_target = targets.get("cycle_median_days")
            if cycle_target is not None and cycle_stats["count"] > 0:
                met = cycle_stats["median"] <= cycle_target
                lines.append(f"- Target: cycle median < {format_duration_days(float(cycle_target))} → Actual: {format_duration_days(cycle_stats['median'])} {'✓' if met else '✗'}")
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
            lines.append(f"- *95th %ile → about 1 in 20 items take longer than {format_duration_days(lead_stats['p95'])}.*")
            threshold = (self.config.get("flow_metrics") or {}).get("sample_size_warning_threshold", 15)
            if lead_stats["count"] < threshold:
                lines.append(f"- *Small sample (N={lead_stats['count']}); treat percentiles with caution.*")
            lines.append(f"- *Based on {lead_stats['count']} issues.*")
            lead_target = targets.get("lead_median_days")
            if lead_target is not None and lead_stats["count"] > 0:
                met = lead_stats["median"] <= lead_target
                lines.append(f"- Target: lead median < {format_duration_days(float(lead_target))} → Actual: {format_duration_days(lead_stats['median'])} {'✓' if met else '✗'}")

        # Outliers: slowest by cycle and by lead (computed for Suggested actions and Slowest items section)
        by_cycle = [r for r in issue_records if r["cycle_days"] is not None]
        by_cycle.sort(key=lambda r: r["cycle_days"], reverse=True)
        by_lead = [r for r in issue_records if r["lead_days"] is not None]
        by_lead.sort(key=lambda r: r["lead_days"], reverse=True)

        # Next report date
        cadence = flow_cfg.get("cadence", "monthly")
        next_date = self._next_report_date(end_date, cadence)
        if next_date:
            lines.extend(["", f"**Next flow report:** {next_date}."])

        # Suggested actions
        has_outliers = len(by_cycle) > 0 or len(by_lead) > 0
        actions = self._suggested_actions(cycle_stats, lead_stats, has_outliers)
        lines.extend(["", "**Suggested actions:**"])
        for a in actions:
            lines.append(f"- {a}")
        lines.append("")

        # Slowest items section
        server_url = self.jira_client.get_server_url() or ""
        lines.extend(["", "### Slowest items"])
        if by_cycle:
            lines.append("**By cycle time:**")
            for r in by_cycle[:3]:
                link = f"[{r['key']}]({server_url}/browse/{r['key']})" if server_url else r["key"]
                lines.append(f"- {link} — {r['summary']} — {format_duration_days(r['cycle_days'])}")
        else:
            lines.append("**By cycle time:** No cycle time outliers.")
        if by_lead:
            lines.append("**By lead time:**")
            for r in by_lead[:3]:
                link = f"[{r['key']}]({server_url}/browse/{r['key']})" if server_url else r["key"]
                lines.append(f"- {link} — {r['summary']} — {format_duration_days(r['lead_days'])}")
        else:
            lines.append("**By lead time:** No lead time data.")

        # Definitions (glossary)
        lines.extend([
            "",
            "### Definitions",
            "- **Cycle time:** First move into an execution status (e.g. In Progress, Review) → first move to a completed status.",
            "- **Lead time:** Issue created → first move to a completed status.",
            "- **Throughput:** Number of issues completed in this period (resolved in date range).",
            "",
            "---",
            "*Throughput = all issues matching base_jql + completed status + resolution date in period. Tighten base_jql in config to scope to one team or board.*",
            "*Cycle/lead use config status_filters (execution, completed). Kanban-friendly; review weekly, monthly, or quarterly for trends.*",
        ])
        return "\n".join(lines)
