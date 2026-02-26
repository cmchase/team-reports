# Flow Metrics Report Enhancements – Build Plan (Cursor-executable)

Execute tasks in order. Each task lists **Files**, **Steps**, and **Verify**. Reference: `docs/FLOW_METRICS_REPORT_PLAN.md`.

---

## Progress

| Phase | Task | Status |
|-------|------|--------|
| 1 | 1.1 Add flow_metrics config schema | ✅ |
| 1 | 1.2 Retain per-issue (key, summary, cycle, lead); add outliers section | ✅ |
| 1 | 1.3 Tail percentile line + sample size warning | ✅ |
| 1 | 1.4 Glossary block | ✅ |
| 1 | 1.5 Focus suggestion heuristic | ✅ |
| 1 | 1.6 Targets + target line + Next report date | ✅ |
| 1 | 1.7 Suggested actions (short checklist) | ✅ |
| 2 | 2.1 History schema + load/save helpers | ✅ |
| 2 | 2.2 Write history after each run; infer cadence | ✅ |
| 2 | 2.3 "Vs last period" + rolling averages in report | ✅ |
| 2 | 2.4 Traffic-light / trend; "What this means" with comparison | ✅ |
| 3 | 3.1 Segment by issue type (and optional component) | ⬜ |
| 3 | 3.2 Optional story points + cycle by size | ⬜ |
| 3 | 3.3 WIP count query + line in report | ⬜ |

---

## Phase 1 – Report and config (no history, no new Jira fields)

### Task 1.1 – Add flow_metrics config schema

**Files**
- `config/default_config.yaml`
- `team_reports/utils/config.py` (if default config is loaded from code; otherwise just YAML)

**Steps**
1. Add a `flow_metrics` section to `config/default_config.yaml`:
   - `cadence: "monthly"` (or `"bi-weekly"`)
   - `targets.cycle_median_days`, `targets.lead_median_days`, `targets.throughput_min` (numeric or null)
   - `sample_size_warning_threshold: 15`
   - Placeholder comments for Phase 2/3: `history_file`, `segment_by`, `story_points_field`, `wip_query` (can add empty/null now or later)
2. Ensure `get_config()` merges this when loading jira config (default_config is already merged in team-reports; confirm flow_metrics is not stripped).

**Verify**
- Load config in a one-liner or test; `config.get("flow_metrics", {}).get("cadence")` is `"monthly"` and targets are present.

---

### Task 1.2 – Retain per-issue (key, summary, cycle, lead); add outliers section

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. In `generate_report`, replace the loop that only appends to `cycle_days_list` / `lead_days_list` with a list of records: e.g. `(issue.key, summary, cycle_days, lead_days)` for each issue. Summary: `getattr(issue.fields, "summary", None) or ""`.
2. Build `cycle_stats` and `lead_stats` from the cycle_days and lead_days lists (unchanged).
3. Sort the list by `cycle_days` desc (drop None); take top 3. Sort by `lead_days` desc; take top 3.
4. After the "Lead time" section and before the footer "---", add a new section **"Slowest items"** (or "Outliers"):
   - **Slowest by cycle time:** up to 3 rows: key (link if you have base URL), summary (truncate e.g. 60 chars), duration (format_duration_days). If none, say "No cycle time outliers."
   - **Slowest by lead time:** same for lead (up to 3). Optionally show "backlog age" = lead − cycle if both present.
5. Use the same Jira server URL as elsewhere (e.g. from `self.jira_client.get_server_url()` or config) for links.

**Verify**
- Run `team-reports jira flow-metrics --start 2026-02-01 --end 2026-02-25`; report includes "Slowest by cycle time" and "Slowest by lead time" with at least one row each when data exists.

---

### Task 1.3 – Tail percentile line + sample size warning

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. After the 85th/95th percentile line for **cycle time**, add one line: e.g. "*95th %ile → about 1 in 20 items take longer than this; consider cap or escalation.*" Use the actual p95 value in the sentence (e.g. "3w 6d"). Only when `cycle_stats["count"] > 0`.
2. Optionally add the same for **lead time** (one line after lead percentiles).
3. Read `flow_metrics.sample_size_warning_threshold` from config (default 15). If `cycle_stats["count"]` < threshold or `lead_stats["count"]` < threshold, add a note before or after the relevant section: "*Small sample (N=&lt;count&gt;); treat percentiles with caution.*"

**Verify**
- Run report; see the new percentile interpretation line(s). Run with a short period that yields few issues; see sample size warning when N < 15.

---

### Task 1.4 – Glossary block

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. Add a **Definitions** (or **Glossary**) block. Place at the **top** of the report (after the "## Flow metrics" title and period/throughput) or at the **bottom** before the closing footer. Recommended: bottom, before "---".
2. Content (one line each):
   - **Cycle time:** First move into an execution status (e.g. In Progress, Review) → first move to a completed status.
   - **Lead time:** Issue created → first move to a completed status.
   - **Throughput:** Number of issues completed in this period (resolved in date range).

**Verify**
- Report contains the Definitions/Glossary block.

---

### Task 1.5 – Focus suggestion heuristic

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. Add a helper (e.g. `_focus_suggestion(cycle_stats, lead_stats, throughput, total_throughput) -> str`) that returns one short "Focus" line based on heuristics, e.g.:
   - If cycle std_dev (days) > 14 → "Focus: review items with cycle time > 3 weeks."
   - Else if lead std_dev (days) > 30 → "Focus: reduce lead time variance (many long-lived items)."
   - Else if throughput is low (e.g. < 15 for a full month) → "Focus: understand throughput (low completion count)."
   - Else → "Focus: keep cycle and lead predictable; consider retro on slowest items."
2. Insert a line in the report (e.g. after throughput or after Definitions): **"Suggested focus:"** &lt;returned string&gt;

**Verify**
- Run report; "Suggested focus:" appears with a sensible line. Optionally run with different date ranges to hit different branches.

---

### Task 1.6 – Targets + target line + Next report date

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- Config already has `flow_metrics.targets` and `flow_metrics.cadence` (Task 1.1).

**Steps**
1. Read `flow_metrics.targets` from config: `cycle_median_days`, `lead_median_days`, `throughput_min`. Any can be missing/null (skip that target).
2. After the cycle time section (or in a small "Goals" block), add a line per target that is set, e.g.:
   - "Target: cycle median &lt; 1.5w → Actual: 1w ✓" or "Target: cycle median &lt; 1.5w → Actual: 2w ✗"
   - Same for lead median and throughput (throughput: "Target: ≥ 20 → Actual: 28 ✓").
3. Compute **Next report date** from `flow_metrics.cadence` and `end_date`:
   - If cadence is `"monthly"`: next = first day of the month after `end_date`, or last day of month containing `end_date` (e.g. "Next flow report: 2026-03-31").
   - If `"bi-weekly"`: next = end_date + 14 days (or next Monday if you prefer a fixed weekday).
4. Add one line: "**Next flow report:** &lt;date&gt;."

**Verify**
- With targets set in config, report shows target vs actual. With cadence monthly, "Next flow report" is the next month end (or next month start); with bi-weekly, ~14 days later.

---

### Task 1.7 – Suggested actions (short checklist)

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. Add a short **Suggested actions** list (2–4 items) driven by conditions:
   - If there are slowest-by-cycle outliers → "• Retro: discuss 2–3 slowest cycle items."
   - If cycle or lead std is high → "• Backlog review: items open > 4 weeks."
   - If lead time improved vs … (no history yet) → skip or use a generic "• Celebrate consistent delivery when metrics are stable."
   - Generic: "• Use next flow report to track trends."
2. Render as a small bullet list (e.g. after "Suggested focus" or in the same block).

**Verify**
- Report shows "Suggested actions" with at least one bullet; when outliers exist, the "Retro: discuss slowest" bullet appears.

---

## Phase 2 – History and comparison

### Task 2.1 – History schema + load/save helpers

**Files**
- New: `team_reports/reports/flow_metrics_history.py` (or under `team_reports/utils/`)

**Steps**
1. Define the history record as a dict (or dataclass): `period_start`, `period_end`, `period_days`, `cadence`, `throughput`, `cycle_median_days`, `cycle_avg_days`, `cycle_std_days`, `cycle_p95_days`, `lead_median_days`, `lead_avg_days`, `lead_std_days`, `lead_p95_days`, `cycle_n`, `lead_n`.
2. Implement `load_flow_metrics_history(history_path: str) -> List[dict]`: read JSON file; return list of records (newest last or newest first—be consistent). If file missing or invalid, return [].
3. Implement `append_flow_metrics_record(history_path: str, record: dict, max_per_cadence: int = 24)`: append record; optionally trim so at most `max_per_cadence` entries per `cadence` (e.g. keep last 24 months for monthly). Ensure directory exists.
4. Implement `get_previous_period(history: List[dict], period_days: int, cadence: str) -> Optional[dict]`: return the most recent record with same cadence (or with period_days in the same band: e.g. 28–31 → monthly, 12–16 → bi-weekly).
5. Implement `get_rolling(history: List[dict], cadence: str, periods: int = 3) -> Optional[dict]`: last N records with same cadence; return dict with mean throughput, mean cycle_median_days, mean lead_median_days (and optionally more).

**Verify**
- Unit tests or a small script: write two records, load, get_previous_period and get_rolling return expected values.

---

### Task 2.2 – Write history after each run; infer cadence

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- Config: `flow_metrics.history_file`, `flow_metrics.history_max_entries_per_cadence`

**Steps**
1. At the end of `generate_report`, build the current record (period_start, period_end, period_days, cadence, throughput, cycle_median_days, …). Compute `period_days` from start_date and end_date. Infer **cadence**: if period_days in 28–31 → "monthly"; if 12–16 → "bi-weekly"; else "custom" (or use config `flow_metrics.cadence` if provided and not inferring).
2. If config has `flow_metrics.history_file`, call append_flow_metrics_record with the new record and `history_max_entries_per_cadence` from config.
3. Resolve path: if relative, from cwd or from Reports dir so it works when run from repo root.

**Verify**
- Run flow-metrics; `Reports/flow_metrics_history.json` (or configured path) exists and contains one new record with correct cadence and numbers.

---

### Task 2.3 – "Vs last period" + rolling averages in report

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- `team_reports/reports/flow_metrics_history.py` (or utils)

**Steps**
1. At the start of `generate_report` (after computing cycle_stats, lead_stats), if history_file is set: load history, get previous period (same cadence), get rolling 3 (and optionally 6).
2. In the report body:
   - After throughput line: if previous period exists, add "*(vs last period: &lt;throughput_prev&gt; → &lt;diff or ↑/↓&gt;)*". Similarly for cycle median and lead median in their sections: "Cycle median 1w *(↓ from 1w 2d last period)*" when previous exists.
   - Add a small subsection **"Rolling (3 periods)"**: throughput X, cycle median Y, lead median Z (formatted). Only when rolling data exists.
3. Use format_duration_days for any duration in these lines.

**Verify**
- Run flow-metrics twice (e.g. two different months); second report shows "vs last period" and "Rolling (3 periods)" once history has 2+ records.

---

### Task 2.4 – Traffic-light / trend; "What this means" with comparison

**Files**
- `team_reports/reports/jira_flow_metrics.py`

**Steps**
1. **Traffic-light:** For cycle_median, lead_median, throughput: compare to (a) previous period and (b) config targets if set. Define "improving" (e.g. cycle lower than last, or under target), "stable", "worsening". Add a short line per metric, e.g. "Cycle median: 1w ✓ improving" or "Throughput: 28 → stable."
2. **"What this means":** Add 2–3 bullet bullets that summarize: e.g. "Throughput in range of last 3 periods." / "Cycle time improved vs last period." / "Lead time higher than last period; review backlog age." Use previous period and rolling when available; otherwise current metrics only. Place this block near the top (after period/throughput) or after the metrics sections.
3. Ensure "Suggested focus" (Task 1.5) can use "improving/worsening" when available (e.g. "Celebrate: lead time improving").

**Verify**
- Report shows traffic-light/trend and "What this means" bullets; with history, at least one comparison bullet appears.

---

## Phase 3 – Segmentation and WIP

### Task 3.1 – Segment by issue type (and optional component)

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- Config: `flow_metrics.segment_by: ["issuetype"]` or `["issuetype", "component"]`

**Steps**
1. In the issue loop, for each issue with cycle_days or lead_days, read `issue.fields.issuetype.name` (and if segment_by includes "component", `issue.fields.components` → list of names). Build a map: segment_key → list of (cycle_days, lead_days). Segment_key for type is the type name; for component use first component or "No component".
2. After the main cycle/lead sections, add **"Cycle by issue type"** table: columns e.g. Type | Count | Median cycle | Median lead (or Avg). Only when config has `flow_metrics.segment_by` including "issuetype".
3. If "component" in segment_by, add **"Throughput by component"** or "Cycle by component" (small table). Handle empty components.

**Verify**
- With `segment_by: ["issuetype"]`, report includes "Cycle by issue type" with at least one row per type present in the data.

---

### Task 3.2 – Optional story points + cycle by size

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- Config: `flow_metrics.story_points_field: "customfield_10016"` (or null to skip)

**Steps**
1. If `flow_metrics.story_points_field` is set, in the issue loop read the custom field (e.g. `getattr(issue.fields, "customfield_10016", None)`). Bucket: 0 or null → "Unestimated", 1–2 → "Small", 3–5 → "Medium", 6+ → "Large".
2. Build segment map size_bucket → list of (cycle_days, lead_days). Add table **"Cycle by size"**: Size | Count | Median cycle | Median lead. Only when story_points_field is configured and at least one issue has a value.

**Verify**
- With story_points_field set and issues that have story points, report shows "Cycle by size" table.

---

### Task 3.3 – WIP count query + line in report

**Files**
- `team_reports/reports/jira_flow_metrics.py`
- `team_reports/utils/jira.py` (optional: add a small helper for WIP count)
- Config: `flow_metrics.wip_query: true`

**Steps**
1. If config `flow_metrics.wip_query` is true: build JQL `(base_jql) AND status IN (execution_statuses)`. Run search with maxResults=0 to get total count (or search_issues with maxResults=0).
2. Add one line in the report (e.g. after Throughput or in a small "Current state" line): "**Current WIP (in execution):** N issues." Optionally add a note that this is as of report run time.
3. Use the same base_jql and execution statuses from config.

**Verify**
- With wip_query true, report shows "Current WIP (in execution): N" with N ≥ 0.

---

## Completion

- When all tasks are done, run a full flow-metrics report for a month that has history; confirm all sections appear (outliers, glossary, focus, targets, next report, suggested actions, vs last period, rolling, traffic-light, What this means, segment tables if configured, WIP).
- Update `docs/FLOW_METRICS_REPORT_PLAN.md` status or add a "Implemented" note at the top pointing to this build plan and completion date.
