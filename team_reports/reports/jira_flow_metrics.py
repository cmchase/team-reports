#!/usr/bin/env python3
"""
Flow metrics report: cycle time, lead time, throughput, and predictability.

Uses Jira issues resolved in a date range; cycle = first execution status -> completed,
lead = created -> completed. Reads status_filters (execution, completed) from Jira config.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from team_reports.reports import flow_metrics_history
from team_reports.utils.jira import (
    fetch_flow_issues,
    flow_stats,
    cycle_and_lead_from_issue,
    format_duration_days,
    time_in_state_from_issue,
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
        prev_period: Optional[Dict[str, Any]] = None,
    ) -> str:
        """One short suggested focus line from heuristics."""
        if prev_period is not None:
            prev_cycle = prev_period.get("cycle_median_days")
            prev_lead = prev_period.get("lead_median_days")
            if prev_cycle is not None and cycle_stats.get("median") is not None and cycle_stats["median"] < prev_cycle:
                return "Celebrate: cycle time improved vs last period."
            if prev_lead is not None and lead_stats.get("median") is not None and lead_stats["median"] < prev_lead:
                return "Celebrate: lead time improved vs last period."
        if cycle_stats.get("std_dev", 0) > 14:
            return "Review items with cycle time > 3 weeks."
        if lead_stats.get("std_dev", 0) > 30:
            return "Reduce lead time variance (many long-lived items)."
        if total_throughput < 15:
            return "Understand throughput (low completion count this period)."
        return "Keep cycle and lead predictable; consider retro on slowest items."

    def _what_this_means(
        self,
        total_throughput: int,
        cycle_stats: Dict[str, float],
        lead_stats: Dict[str, float],
        prev_period: Optional[Dict[str, Any]],
        rolling: Optional[Dict[str, Any]],
    ) -> List[str]:
        """2–3 bullets summarizing vs previous period and rolling when available."""
        bullets = []
        if prev_period is not None:
            prev_t = prev_period.get("throughput")
            if prev_t is not None:
                if total_throughput > int(prev_t):
                    bullets.append("Throughput up vs last period.")
                elif total_throughput < int(prev_t):
                    bullets.append("Throughput down vs last period.")
            prev_cycle = prev_period.get("cycle_median_days")
            if prev_cycle is not None and cycle_stats.get("median") is not None:
                if cycle_stats["median"] < prev_cycle:
                    bullets.append("Cycle time improved vs last period.")
                elif cycle_stats["median"] > prev_cycle:
                    bullets.append("Cycle time higher than last period; review execution flow.")
            prev_lead = prev_period.get("lead_median_days")
            if prev_lead is not None and lead_stats.get("median") is not None:
                if lead_stats["median"] > prev_lead:
                    bullets.append("Lead time higher than last period; review backlog age.")
        if rolling is not None and len(bullets) < 3:
            bullets.append(f"Throughput in range of last {rolling.get('periods', 3)} periods (rolling avg: {rolling.get('throughput', 0):.0f}).")
        if not bullets:
            bullets.append("Run again next period to see trends.")
        return bullets[:3]

    def _trend_lines(
        self,
        total_throughput: int,
        cycle_stats: Dict[str, float],
        lead_stats: Dict[str, float],
        targets: Dict[str, Any],
        prev_period: Optional[Dict[str, Any]],
    ) -> List[str]:
        """Traffic-light: improving / stable / worsening vs previous period and targets."""
        lines = []
        # Throughput
        if prev_period is not None and prev_period.get("throughput") is not None:
            prev_t = int(prev_period["throughput"])
            if total_throughput > prev_t:
                lines.append(f"Throughput: {total_throughput} ✓ improving")
            elif total_throughput < prev_t:
                lines.append(f"Throughput: {total_throughput} ↓ worsening")
            else:
                lines.append(f"Throughput: {total_throughput} → stable")
        throughput_min = targets.get("throughput_min")
        if throughput_min is not None:
            lines.append(f"Throughput target ≥{throughput_min}: {'✓' if total_throughput >= throughput_min else '✗'}")
        # Cycle median
        if cycle_stats.get("count", 0) > 0 and cycle_stats.get("median") is not None:
            med = cycle_stats["median"]
            if prev_period is not None and prev_period.get("cycle_median_days") is not None:
                prev_c = prev_period["cycle_median_days"]
                if med < prev_c:
                    lines.append(f"Cycle median: {format_duration_days(med)} ✓ improving")
                elif med > prev_c:
                    lines.append(f"Cycle median: {format_duration_days(med)} ↓ worsening")
                else:
                    lines.append(f"Cycle median: {format_duration_days(med)} → stable")
            cycle_target = targets.get("cycle_median_days")
            if cycle_target is not None:
                lines.append(f"Cycle median target: {'✓' if med <= cycle_target else '✗'}")
        # Lead median
        if lead_stats.get("count", 0) > 0 and lead_stats.get("median") is not None:
            med = lead_stats["median"]
            if prev_period is not None and prev_period.get("lead_median_days") is not None:
                prev_l = prev_period["lead_median_days"]
                if med < prev_l:
                    lines.append(f"Lead median: {format_duration_days(med)} ✓ improving")
                elif med > prev_l:
                    lines.append(f"Lead median: {format_duration_days(med)} ↓ worsening")
                else:
                    lines.append(f"Lead median: {format_duration_days(med)} → stable")
            lead_target = targets.get("lead_median_days")
            if lead_target is not None:
                lines.append(f"Lead median target: {'✓' if med <= lead_target else '✗'}")
        return lines

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

    def _infer_cadence(self, period_days: int) -> str:
        """Infer cadence from period length; 28-31 → monthly, 12-16 → bi-weekly."""
        if 28 <= period_days <= 31:
            return "monthly"
        if 12 <= period_days <= 16:
            return "bi-weekly"
        return (self._get_flow_config().get("cadence")) or "custom"

    def _resolve_history_path(self, history_file: str) -> str:
        """Resolve relative path from cwd so Reports/... works when run from repo root."""
        p = Path(history_file)
        if p.is_absolute():
            return history_file
        return str(Path.cwd() / p)

    def _segment_table(
        self,
        segment_map: Dict[str, List[Tuple[Optional[float], Optional[float]]]],
        order_keys: Optional[List[str]] = None,
        first_column: str = "Type",
    ) -> List[str]:
        """Build markdown table lines: first_column | Count | Median cycle | Median lead."""
        if not segment_map:
            return []
        lines = [f"| {first_column} | Count | Median cycle | Median lead |", "| --- | --- | --- | --- |"]
        keys = order_keys if order_keys is not None else sorted(segment_map.keys())
        for key in keys:
            if key not in segment_map:
                continue
            pairs = segment_map[key]
            cycle_vals = [p[0] for p in pairs if p[0] is not None]
            lead_vals = [p[1] for p in pairs if p[1] is not None]
            n = len(pairs)
            cycle_med = flow_stats(cycle_vals)["median"] if cycle_vals else 0.0
            lead_med = flow_stats(lead_vals)["median"] if lead_vals else 0.0
            lines.append(f"| {key} | {n} | {format_duration_days(cycle_med)} | {format_duration_days(lead_med)} |")
        return lines

    def _classify_slowest_item(
        self,
        summary: str,
        key: str,
        cycle_days: Optional[float],
        lead_days: Optional[float],
        by_lead: bool,
    ) -> str:
        """Classify slowest item by failure mode from title/summary. Default: Unknown: needs manual review."""
        s = (summary or "").lower()
        if any(x in s for x in ["cve", "weakness", "sar", "embargo", "security", "compliance"]):
            return "Security/compliance work"
        if any(x in s for x in ["embargo", "partner", "waiting on", "another team", "external", "dependency"]):
            return "External dependency"
        if any(x in s for x in ["spike", "prototype", "architectural", "architecture", "scope"]):
            return "Scope grew during execution"
        if any(x in s for x in ["build", "pipeline", "ci ", "installer", "packaging", "tooling", "infrastructure"]):
            return "Infrastructure/tooling"
        if by_lead and lead_days is not None and lead_days > 90 and (cycle_days is None or cycle_days < 30):
            return "Backlog age"
        return "Unknown: needs manual review"

    def _next_report_date(self, end_date: str, cadence: str) -> str:
        """Compute next report date from period end and cadence."""
        from datetime import timedelta
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

        flow_cfg = self._get_flow_config()
        wip_count: Optional[int] = None
        if flow_cfg.get("wip_query"):
            exec_jql = ", ".join(f'"{s}"' for s in execution_statuses)
            wip_jql = f"({base_jql}) AND status IN ({exec_jql})"
            wip_result = self.jira_client.jira_client.search_issues(wip_jql, maxResults=0)
            wip_count = getattr(wip_result, "total", 0)

        total_throughput, issues = fetch_flow_issues(
            self.jira_client.jira_client, jql, max_issues
        )

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            start_dt = None
            end_dt = None

        issue_records: List[Dict[str, Any]] = []
        cycle_days_list: List[float] = []
        lead_days_list: List[float] = []
        lead_days_new_work: List[float] = []
        lead_days_aged_backlog: List[float] = []
        active_days_list: List[float] = []
        cycle_days_for_efficiency: List[float] = []
        has_created_dates = True
        segment_by = flow_cfg.get("segment_by") or []
        story_points_field = flow_cfg.get("story_points_field")
        segment_issuetype: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}
        segment_component: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}
        segment_size: Dict[str, List[Tuple[Optional[float], Optional[float]]]] = {}
        time_in_state_lists: Dict[str, List[float]] = {s: [] for s in execution_statuses}
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
                if start_dt is not None:
                    created_str = getattr(issue.fields, "created", None) or ""
                    if created_str:
                        try:
                            created_dt = datetime.strptime(created_str[:10], "%Y-%m-%d")
                            if created_dt >= start_dt:
                                lead_days_new_work.append(lead_days)
                            else:
                                lead_days_aged_backlog.append(lead_days)
                        except (ValueError, TypeError):
                            has_created_dates = False
                    else:
                        has_created_dates = False
            if cycle_days is not None:
                tis = time_in_state_from_issue(issue, execution_statuses, completed_statuses)
                if tis:
                    total_active = sum(tis.values())
                    active_days_list.append(total_active)
                    cycle_days_for_efficiency.append(cycle_days)
                    for state, days in tis.items():
                        if state in time_in_state_lists and days > 0:
                            time_in_state_lists[state].append(days)
            if cycle_days is not None or lead_days is not None:
                if "issuetype" in segment_by:
                    it = getattr(issue.fields, "issuetype", None)
                    it_name = it.name if it and hasattr(it, "name") else "Unknown"
                    segment_issuetype.setdefault(it_name, []).append((cycle_days, lead_days))
                if "component" in segment_by:
                    comps = getattr(issue.fields, "components", None) or []
                    comp_name = comps[0].name if comps and hasattr(comps[0], "name") else "No component"
                    segment_component.setdefault(comp_name, []).append((cycle_days, lead_days))
                if story_points_field:
                    val = getattr(issue.fields, story_points_field, None)
                    if val is None or (isinstance(val, (int, float)) and val == 0):
                        bucket = "Unestimated"
                    elif isinstance(val, (int, float)):
                        if val <= 2:
                            bucket = "Small"
                        elif val <= 5:
                            bucket = "Medium"
                        else:
                            bucket = "Large"
                    else:
                        bucket = "Unestimated"
                    segment_size.setdefault(bucket, []).append((cycle_days, lead_days))

        cycle_stats = flow_stats(cycle_days_list)
        lead_stats = flow_stats(lead_days_list)
        throughput_note = str(total_throughput)
        if total_throughput > len(issues):
            throughput_note += (
                f" (cycle/lead from first {len(issues)}; increase max_issues for full sample)"
            )
        targets = flow_cfg.get("targets") or {}

        # Period length and cadence for history
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            period_days = max(0, (end_dt - start_dt).days + 1)
        except ValueError:
            period_days = 0
        cadence = self._infer_cadence(period_days)

        # Load history for comparison (before appending this run)
        prev_period: Optional[Dict[str, Any]] = None
        rolling: Optional[Dict[str, Any]] = None
        last_3_records: List[Dict[str, Any]] = []
        history_path: Optional[str] = None
        if flow_cfg.get("history_file"):
            history_path = self._resolve_history_path(flow_cfg["history_file"])
            history = flow_metrics_history.load_flow_metrics_history(history_path)
            prev_period = flow_metrics_history.get_previous_period(history, period_days, cadence)
            rolling = flow_metrics_history.get_rolling(history, cadence, periods=3)
            norm = cadence if cadence in ("monthly", "bi-weekly", "custom") else self._infer_cadence(period_days)
            same_cadence = [r for r in history if (r.get("cadence") or self._infer_cadence(r.get("period_days", 0))) == norm]
            last_3_records = same_cadence[-3:] if same_cadence else []
        throughput_min = targets.get("throughput_min")
        if throughput_min is not None:
            met = total_throughput >= throughput_min
            throughput_note += f" (Target: ≥ {throughput_min} → {'✓' if met else '✗'})"

        lines = [
            "## Flow metrics",
            f"**Period:** {start_date} to {end_date}",
            f"**Throughput:** {throughput_note} issues completed",
        ]
        if wip_count is not None:
            lines.append(f"**Current WIP (in execution):** {wip_count} issues. *WIP is as of report generation.*")
        lines.append("")
        lines.append("**WIP snapshot**")
        if wip_count is not None and total_throughput > 0:
            wip_ratio = wip_count / total_throughput
            lines.append(f"- WIP-to-throughput ratio: {wip_ratio:.1f} (current WIP ÷ throughput this period).")
            if wip_ratio > 1.5:
                lines.append("- *Interpretation: flow may be queued; consider reducing WIP.*")
            else:
                lines.append("- *Interpretation: healthy range.*")
        else:
            if wip_count is None:
                lines.append("- *Enable flow_metrics.wip_query in config to see current WIP and ratio.*")
        lines.append("- // TODO: Average WIP during period: requires daily or period-level execution-status snapshot.")
        lines.append("- // TODO: Peak WIP: requires single-day counts or changelog replay by day.")
        lines.append("")
        if prev_period is not None:
            prev_t = prev_period.get("throughput")
            if prev_t is not None:
                diff = total_throughput - int(prev_t)
                if diff > 0:
                    vs = f"*(vs last period: {int(prev_t)} → ↑ {diff})*"
                elif diff < 0:
                    vs = f"*(vs last period: {int(prev_t)} → ↓ {abs(diff)})*"
                else:
                    vs = "*(vs last period: same)*"
                lines.append(vs)
        lines.append("")

        # What this means (2–3 bullets using prev and rolling)
        what_bullets = self._what_this_means(
            total_throughput, cycle_stats, lead_stats, prev_period, rolling
        )
        if what_bullets:
            lines.append("**What this means:**")
            for b in what_bullets:
                lines.append(f"- {b}")
            lines.append("")

        # Traffic-light / trend
        trend_lines = self._trend_lines(
            total_throughput, cycle_stats, lead_stats, targets, prev_period
        )
        if trend_lines:
            lines.append("**Trend:**")
            for t in trend_lines:
                lines.append(f"- {t}")
            lines.append("")

        focus = self._focus_suggestion(cycle_stats, lead_stats, total_throughput, prev_period)
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
            med_line = f"- **Median:** {format_duration_days(cycle_stats['median'])}"
            if prev_period is not None and prev_period.get("cycle_median_days") is not None:
                prev_c = prev_period["cycle_median_days"]
                curr = cycle_stats["median"]
                if curr < prev_c:
                    med_line += f" *(↓ from {format_duration_days(prev_c)} last period)*"
                elif curr > prev_c:
                    med_line += f" *(↑ from {format_duration_days(prev_c)} last period)*"
                else:
                    med_line += " *(same as last period)*"
            lines.append(med_line)
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
        # Cycle time distribution
        if cycle_days_list:
            under_7 = sum(1 for d in cycle_days_list if d < 7)
            w1_w2 = sum(1 for d in cycle_days_list if 7 <= d < 14)
            w2_w4 = sum(1 for d in cycle_days_list if 14 <= d < 28)
            over_28 = sum(1 for d in cycle_days_list if d >= 28)
            n_cycle = len(cycle_days_list)
            pct_under_7 = round(100 * under_7 / n_cycle, 1) if n_cycle else 0
            pct_w1_w2 = round(100 * w1_w2 / n_cycle, 1) if n_cycle else 0
            pct_w2_w4 = round(100 * w2_w4 / n_cycle, 1) if n_cycle else 0
            pct_over_28 = round(100 * over_28 / n_cycle, 1) if n_cycle else 0
            pct_within_2w = pct_under_7 + pct_w1_w2
            lines.extend([
                "",
                "### Cycle time distribution",
                "",
                f"- Under 1 week: {under_7} ({pct_under_7}%)",
                f"- 1–2 weeks: {w1_w2} ({pct_w1_w2}%)",
                f"- 2–4 weeks: {w2_w4} ({pct_w2_w4}%)",
                f"- Over 4 weeks: {over_28} ({pct_over_28}%)",
                f"- *{pct_within_2w}% of issues completed within 2 weeks (target: >= 70%).*",
            ])
            long_tail_n = sum(1 for d in cycle_days_list if d > 56)
            if long_tail_n > 0:
                lines.append(f"- *Long-tail alert: {long_tail_n} issue(s) exceeded 8 weeks. These represent a system problem worth diagnosing, not just noting.*")
            lines.append("")
        # Time in state (execution): In Progress vs Review etc.
        states_with_data = [(s, time_in_state_lists[s]) for s in execution_statuses if time_in_state_lists[s]]
        if states_with_data:
            lines.extend(["", "### Time in state (execution)", ""])
            medians_by_state: List[Tuple[str, float]] = []
            for state, vals in states_with_data:
                st = flow_stats(vals)
                lines.append(f"- **{state}:** median {format_duration_days(st['median'])}, avg {format_duration_days(st['avg'])}")
                medians_by_state.append((state, st["median"]))
            if len(medians_by_state) >= 2:
                medians_by_state.sort(key=lambda x: x[1], reverse=True)
                if medians_by_state[0][1] > 0 and medians_by_state[1][1] > 0 and medians_by_state[0][1] > medians_by_state[1][1] * 1.2:
                    lines.append(f"- *Most cycle time is in {medians_by_state[0][0]}.*")
            if active_days_list and cycle_days_for_efficiency:
                total_active = sum(active_days_list)
                total_cycle = sum(cycle_days_for_efficiency)
                efficiency = (total_active / total_cycle * 100) if total_cycle > 0 else 0
                lines.append(f"- **Flow efficiency:** {efficiency:.0f}% (active execution vs. total cycle time).")
                if efficiency >= 60:
                    lines.append("- *Interpretation: good.*")
                elif efficiency >= 40:
                    lines.append("- *Interpretation: moderate; investigate wait states.*")
                else:
                    lines.append("- *Interpretation: low; significant queue or blocking time present.*")
            lines.append("")
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
            med_line = f"- **Median:** {format_duration_days(lead_stats['median'])}"
            if prev_period is not None and prev_period.get("lead_median_days") is not None:
                prev_l = prev_period["lead_median_days"]
                curr = lead_stats["median"]
                if curr < prev_l:
                    med_line += f" *(↓ from {format_duration_days(prev_l)} last period)*"
                elif curr > prev_l:
                    med_line += f" *(↑ from {format_duration_days(prev_l)} last period)*"
                else:
                    med_line += " *(same as last period)*"
            lines.append(med_line)
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
            if has_created_dates and (lead_days_new_work or lead_days_aged_backlog):
                lines.extend(["", "#### Lead time: new work (created this period)", ""])
                if lead_days_new_work:
                    nw_stats = flow_stats(lead_days_new_work)
                    lines.append(f"- Count: {len(lead_days_new_work)} | Median: {format_duration_days(nw_stats['median'])} | Average: {format_duration_days(nw_stats['avg'])}")
                else:
                    lines.append("- Count: 0 (no issues created and completed in this period).")
                lines.extend(["", "#### Lead time: aged backlog (created before this period)", ""])
                if lead_days_aged_backlog:
                    ab_stats = flow_stats(lead_days_aged_backlog)
                    lines.append(f"- Count: {len(lead_days_aged_backlog)} | Median: {format_duration_days(ab_stats['median'])} | Average: {format_duration_days(ab_stats['avg'])}")
                    lines.append("- *High median here reflects backlog age, not execution speed.*")
                else:
                    lines.append("- Count: 0.")
            elif not has_created_dates:
                lines.append("")
                lines.append("// TODO: creation date segmentation requires created date field in source data")

        # Segment tables (Cycle by issue type, by component, by size)
        if "issuetype" in segment_by and segment_issuetype:
            lines.extend(["", "### Cycle by issue type", ""])
            lines.extend(self._segment_table(segment_issuetype, first_column="Type"))
            lines.append("")
        if "component" in segment_by and segment_component:
            lines.extend(["", "### Cycle by component", ""])
            lines.extend(self._segment_table(segment_component, first_column="Component"))
            lines.append("")
        if story_points_field and segment_size:
            size_order = ["Unestimated", "Small", "Medium", "Large"]
            lines.extend(["", "### Cycle by size", ""])
            lines.extend(self._segment_table(segment_size, order_keys=size_order, first_column="Size"))
            lines.append("")

        # Rolling (3 periods) when history available — interpreted trend
        if rolling is not None:
            lines.extend(["", "### Rolling trend (3-period)", ""])
            tp_avg = rolling.get("throughput", 0)
            cy_avg = rolling.get("cycle_median_days", 0)
            ld_avg = rolling.get("lead_median_days", 0)
            tp_dir = "Stable"
            cy_dir = "Stable"
            ld_dir = "Stable"
            if len(last_3_records) >= 3:
                v1_t, v2_t, v3_t = [r.get("throughput", 0) for r in last_3_records[-3:]]
                if v3_t > v2_t > v1_t:
                    tp_dir = "Trending up"
                elif v3_t < v2_t < v1_t:
                    tp_dir = "Trending down"
                v1_c, v2_c, v3_c = [r.get("cycle_median_days") or 0 for r in last_3_records[-3:]]
                if v3_c < v2_c < v1_c:
                    cy_dir = "Improving"
                elif v3_c > v2_c > v1_c:
                    cy_dir = "Degrading"
                v1_l, v2_l, v3_l = [r.get("lead_median_days") or 0 for r in last_3_records[-3:]]
                if v3_l < v2_l < v1_l:
                    ld_dir = "Improving"
                elif v3_l > v2_l > v1_l:
                    ld_dir = "Degrading"
            lines.append(f"- Throughput: {tp_avg:.0f} — {tp_dir}")
            lines.append(f"- Cycle median: {format_duration_days(cy_avg)} — {cy_dir}")
            lines.append(f"- Lead median: {format_duration_days(ld_avg)} — {ld_dir}")
            degrading_count = sum(1 for d in [tp_dir == "Trending down", cy_dir == "Degrading", ld_dir == "Degrading"] if d)
            if degrading_count >= 2:
                health = "At risk"
            elif degrading_count == 1:
                health = "Watch"
            else:
                health = "Healthy"
            lines.append(f"- *Overall flow health: {health}*")
            lines.append("")

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
                typ = self._classify_slowest_item(r["summary"], r["key"], r.get("cycle_days"), r.get("lead_days"), by_lead=False)
                lines.append(f"  Type: {typ}")
        else:
            lines.append("**By cycle time:** No cycle time outliers.")
        if by_lead:
            lines.append("**By lead time:**")
            for r in by_lead[:3]:
                link = f"[{r['key']}]({server_url}/browse/{r['key']})" if server_url else r["key"]
                lines.append(f"- {link} — {r['summary']} — {format_duration_days(r['lead_days'])}")
                typ = self._classify_slowest_item(r["summary"], r["key"], r.get("cycle_days"), r.get("lead_days"), by_lead=True)
                lines.append(f"  Type: {typ}")
        else:
            lines.append("**By lead time:** No lead time data.")

        # Active WIP aging (open at period end)
        lines.extend([
            "",
            "### Active WIP aging (open at period end)",
            "",
            "// TODO: active WIP aging requires open issue snapshot at period end date",
            "*This would list issues in In Progress or Review at the end of the period, grouped by how long they have been in that state.*",
            "",
        ])

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

        # Append this period to history for next run's comparison
        if history_path:
            record = {
                "period_start": start_date,
                "period_end": end_date,
                "period_days": period_days,
                "cadence": cadence,
                "throughput": total_throughput,
                "cycle_median_days": cycle_stats.get("median"),
                "cycle_avg_days": cycle_stats.get("avg"),
                "cycle_std_days": cycle_stats.get("std_dev"),
                "cycle_p95_days": cycle_stats.get("p95"),
                "lead_median_days": lead_stats.get("median"),
                "lead_avg_days": lead_stats.get("avg"),
                "lead_std_days": lead_stats.get("std_dev"),
                "lead_p95_days": lead_stats.get("p95"),
                "cycle_n": int(cycle_stats.get("count", 0)),
                "lead_n": int(lead_stats.get("count", 0)),
            }
            max_entries = flow_cfg.get("history_max_entries_per_cadence", 24)
            flow_metrics_history.append_flow_metrics_record(history_path, record, max_per_cadence=max_entries)

        return "\n".join(lines)
