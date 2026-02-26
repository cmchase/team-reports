# Flow Metrics Report Enhancements – Plan

**Execution:** See **`docs/FLOW_METRICS_BUILD_PLAN.md`** for a Cursor-executable build plan (tasks, files, steps, verify).

**Goal:** Make flow metrics reports more informative, insightful, and actionable while supporting **monthly** (your team) and **bi-weekly** (other teams) cadences without focusing on too narrow a window.

**Scope:** All recommendations from the 6‑month digest, plus cadence-aware comparison and history. This doc also clarifies what the team-reports library already provides vs what we need to add (data collection, persistence, config).

---

## 1. Cadence: Monthly vs bi-weekly

| Aspect | Approach |
|--------|----------|
| **Report period** | Already supported: `--start` / `--end` or `--days`. Monthly = first–last of month; bi-weekly = two-week window (e.g. 1–14, 15–28). No code change for period length. |
| **Comparison “vs last period”** | Must be **same cadence**: compare this month to last month, or this 2 weeks to previous 2 weeks. Implementation: store **period length** (or type) with each run so we know “previous period” is comparable. |
| **Rolling averages** | 3‑month rolling = last 3 months of data (monthly) or last 6 bi-weekly runs. Same history store; filter by period length when computing. |
| **“Next report date”** | Derived from cadence: e.g. monthly → “Next flow report: end of March”; bi-weekly → “Next: 2026-03-11”. Config or CLI flag (e.g. `--cadence monthly`) to drive the label. |

**Conclusion:** One shared **flow metrics history** (see §5) with a `period_days` or `cadence` field so comparisons and rolling averages respect monthly vs bi-weekly.

---

## 2. Recommendation-by-recommendation plan

For each recommendation we state: **current state**, **data source** (existing library vs new collection vs config), and **implementation notes**.

---

### 2.1 Trend and comparison context

| Item | Current state | Data source | Implementation |
|------|----------------|-------------|----------------|
| **Same period, previous period** | Not present | **New: persisted history** | After generating this period’s metrics, read last entry from history with same `period_days` (or same `cadence`). Write lines like “Cycle median 1w (↓ from 1w 2d last period)”. |
| **Rolling averages (3‑mo / 6‑mo)** | Not present | **New: persisted history** | From history, take last 3 (or 6) entries with same cadence; compute mean throughput, mean cycle_median_days, mean lead_median_days. Add subsection “Rolling (3 months): throughput X, cycle median Y, lead median Z.” |
| **Traffic-light / trend arrows** | Not present | **Derived from above + optional targets** | Compare current metric to (a) previous period or (b) config target. Map to “improving / stable / worsening” and render ✓ / → / ⚠ (or similar). |

**Does the library need to expand?**  
- **Yes.** We need to **persist** a small time series (period + metrics) after each run. The library currently does not write any structured history; it only writes the markdown report. So we add: **flow metrics history** (e.g. JSON file or append to a store) written by the report generator and read when generating the next report.

---

### 2.2 Call out outliers and risk

| Item | Current state | Data source | Implementation |
|------|----------------|-------------|----------------|
| **Outliers: 1–3 slowest by cycle and lead** | Not present; we have per-issue cycle/lead in memory but don’t attach key/summary | **Existing Jira data, small code change** | In `jira_flow_metrics.py`, keep list of `(issue_key, summary, cycle_days, lead_days)` per issue (summary from `issue.fields.summary`). Sort by cycle_days desc, lead_days desc; take top 3 each. Add section “Slowest by cycle time” / “Slowest by lead time” with key, summary, duration. Optional: “age in backlog” = lead − cycle (already computable). |
| **Tail percentiles interpretation** | We have 85th/95th in report | **Existing** | Add one line under percentiles: “95th %ile cycle 3w 6d → about 1 in 20 items take longer; consider cap or escalation.” Template with actual p95 value. |
| **Sample size warning** | Not present | **Existing** | If `cycle_stats["count"]` (or lead count) < threshold (e.g. 15), add note: “Small sample (N=9); treat percentiles with caution.” |

**Does the library need to expand?**  
- **No new Jira fields.** We already fetch issues with changelog and compute cycle/lead per issue. We only need to **retain** key and summary next to each (cycle_days, lead_days) and sort/filter for the report. Optional: expose “age in backlog” (lead − cycle) in that list.

---

### 2.3 Make the report self-interpreting

| Item | Current state | Data source | Implementation |
|------|----------------|-------------|----------------|
| **“What this means” (2–3 bullets)** | Not present | **Heuristics from current metrics + optional history** | Rules: e.g. “Throughput in range of last 6 months” (need history); “Cycle time improved vs last period” (need previous period); “Lead time much lower than recent months” (need history or previous). Without history, we can still do: “Throughput N issues”; “Cycle median X (target Y if configured)”; “Lead median Z.” So: **Phase 1** without history = 2–3 bullets from current numbers + targets; **Phase 2** with history = add comparison bullets. |
| **One “Focus” suggestion** | Not present | **Heuristics + optional config** | Rules: e.g. if cycle std_dev high → “Focus: review items with cycle > 3 weeks”; if lead std high → “Focus: reduce lead time variance”; if throughput down vs last → “Focus: understand throughput drop.” Can be config-driven (thresholds) or fixed rules. |
| **Glossary / one-line definitions** | Not present | **Static text** | Add a short “Definitions” block at top or bottom: “**Cycle time:** First move into execution (e.g. In Progress) → first move to done. **Lead time:** Created → first move to done. **Throughput:** Issues completed in this period.” No new data. |

**Does the library need to expand?**  
- **Only if we want comparison bullets.** Then we need history (and optionally targets in config). Glossary and focus heuristic need no new collection.

---

### 2.4 Segment when possible

| Item | Current state | Data source | Implementation |
|------|----------------|-------------|----------------|
| **By type or label** | Not present | **Jira: issue type, components, labels** | We already have the issue object. Read `issue.fields.issuetype.name`; optionally `issue.fields.components[*].name` or `issue.fields.labels`. Group issues by type (and optionally by component/label). Compute cycle/lead stats per group. Add table “Cycle by issue type” (and optionally “Throughput by component”). **Config:** e.g. `flow_metrics.segment_by: ["issuetype"]` or `["issuetype", "component"]` so teams can opt in. |
| **By size (story points)** | Not present | **Jira: custom field** | Many boards use a custom field for story points (e.g. `customfield_10016`). Config: `flow_metrics.story_points_field: "customfield_10016"` (or leave unset to skip). Bucket issues into Small / Medium / Large (e.g. 1–2, 3–5, 8+); table “Cycle by size.” |
| **WIP vs completed** | Not present | **New Jira query** | One extra query: count of issues matching base_jql and status IN (execution) as of “now” (or period end if we want point-in-time). Add line: “Current WIP (in execution): N issues.” Optionally link to board or a saved filter. |

**Does the library need to expand?**  
- **Yes.** We need to (1) read **issuetype** (and optionally components/labels) from each issue in the existing loop; (2) optionally read a **story-points custom field** if configured; (3) run **one additional Jira count query** for WIP. No new API beyond what Jira already exposes.

---

### 2.5 Tie to goals and actions

| Item | Current state | Data source | Implementation |
|------|----------------|-------------|----------------|
| **Target line** | Not present | **Config** | e.g. in `jira_config.yaml` or `default_config.yaml`: `flow_metrics.targets.cycle_median_days: 10`, `lead_median_days: 21`, `throughput_min: 20`. Report: “Target: cycle median &lt; 1.5w → Actual: 1w ✓.” |
| **Suggested actions** | Not present | **Rules + config** | Fixed short list with conditions: “Retro: discuss 2–3 slowest cycle items” (if we have outliers); “Backlog review: items open > 4 weeks” (could be a link or reminder); “Celebrate: lead time down” (if comparison says improving). Can be purely heuristic or config-driven checklist. |
| **Next report date** | Not present | **Config or derived** | If `flow_metrics.cadence: "monthly"` then next = first day of next month (or last day of current). If `"bi-weekly"` then next = +14 days from period end. Add line: “Next flow report: YYYY-MM-DD.” |

**Does the library need to expand?**  
- **Config only.** No new Jira data; add a small **flow_metrics** config block (targets, cadence, optional checklist).

---

## 3. What the team-reports library provides today vs what we add

| Capability | Today | After enhancements |
|------------|--------|---------------------|
| Period (monthly / bi-weekly) | ✅ Any range via start/end or days | ✅ Same; cadence used for comparison + “next report” label |
| Throughput, cycle stats, lead stats | ✅ From current run | ✅ Same; plus persisted for history |
| Per-issue cycle/lead | ✅ In memory, not tied to key/summary | ✅ Retain key/summary for outliers section |
| Issue type, components, labels | ❌ Not read | ✅ Read in loop; segment tables |
| Story points | ❌ Not read | ✅ Optional custom field; segment by size |
| WIP count | ❌ Not available | ✅ One extra Jira count query |
| Previous period / rolling | ❌ Not available | ✅ Persist metrics; read history |
| Targets, cadence, focus | ❌ Not available | ✅ Config block + heuristics |

So: **library expansion** = persist history, retain per-issue identity for outliers, read issuetype (and optional components/labels, story points), one WIP query, and a flow_metrics config section. No change to core Jira/changelog logic.

---

## 4. Phased implementation

So that work is predictable and we don’t block on “everything at once”:

**Phase 1 – No new data (report and config only)**  
- Outliers: top 3 slowest by cycle and by lead (key, summary, duration); keep (key, summary, cycle_days, lead_days) in the existing loop.  
- Tail percentile line (“1 in 20 items take longer…”).  
- Sample size warning when N &lt; 15.  
- Glossary (cycle, lead, throughput).  
- One “Focus” suggestion from heuristics (e.g. high std → “review items with cycle > 3w”).  
- Optional: config targets + target line (actual vs target); “Next report” from config cadence.

**Phase 2 – Persisted history and comparison**  
- Define flow metrics history schema and file location (e.g. `Reports/flow_metrics_history.json` or under config).  
- After each run, append (or upsert) one record: period_start, period_end, period_days, throughput, cycle_median, lead_median, cycle_std, lead_std, etc.  
- When generating report, load history; find “previous period” (same period_days or cadence); compute rolling 3‑month (and optionally 6‑month).  
- Add to report: “vs last period”, rolling averages, traffic-light/trend.  
- “What this means” bullets that use previous period and rolling.

**Phase 3 – Segmentation and WIP**  
- In the issue loop, read issuetype (and optionally components/labels from config).  
- Build segment tables: cycle by issue type, throughput by type (and optionally by component).  
- Optional: story points field from config; bucket and “cycle by size” table.  
- One WIP count query; add “Current WIP: N” (and optional link).

**Phase 4 – Goals and actions**  
- Config: `flow_metrics.targets` and `flow_metrics.cadence` (if not in Phase 1).  
- Suggested actions: small checklist (e.g. “Retro: slowest items”, “Backlog review”, “Celebrate”) with conditions so the report can tick or suggest.  
- “Next flow report: &lt;date&gt;” from cadence.

Phases 1 and 4 overlap (targets + next report can be Phase 1). Order can be: **1 → 2 → 3 → 4** or **1 (including targets + next report) → 2 → 3**, then 4 as polish.

---

## 5. Data model: flow metrics history

So that “vs last period” and “rolling average” work for both monthly and bi-weekly:

**Option A – JSON file (e.g. `Reports/flow_metrics_history.json`)**  
- Append-only or “last N per cadence” to avoid unbounded growth.  
- Record shape (minimal):

```json
{
  "period_start": "2026-02-01",
  "period_end": "2026-02-25",
  "period_days": 25,
  "cadence": "monthly",
  "throughput": 28,
  "cycle_median_days": 7,
  "cycle_avg_days": 10,
  "cycle_std_days": 12,
  "cycle_p95_days": 25,
  "lead_median_days": 14,
  "lead_avg_days": 39,
  "lead_std_days": 45,
  "lead_p95_days": 108,
  "cycle_n": 26,
  "lead_n": 28
}
```

- **cadence** can be inferred (e.g. period_days in 28–31 → monthly, 12–16 → bi-weekly) or set by config/CLI.  
- When loading, filter by `cadence` (or `period_days` band) so we compare monthly to monthly and bi-weekly to bi-weekly.

**Option B – Same structure, different store**  
- e.g. SQLite or a small DB under `.team_reports/` if we want querying later. For Phase 2, a single JSON file is enough.

---

## 6. Config schema additions

Proposed addition (under `default_config.yaml` or `jira_config.yaml`):

```yaml
# Flow metrics report (optional)
flow_metrics:
  # Cadence for "next report" and comparison (monthly | bi-weekly)
  cadence: "monthly"
  # Targets for target line and traffic-light
  targets:
    cycle_median_days: 10
    lead_median_days: 21
    throughput_min: 20
  # Persisted history (file path relative to cwd or reports dir)
  history_file: "Reports/flow_metrics_history.json"
  history_max_entries_per_cadence: 24
  # Segmentation
  segment_by: ["issuetype"]
  story_points_field: null   # e.g. "customfield_10016"
  # WIP
  wip_query: true
  # Sample size warning threshold
  sample_size_warning_threshold: 15
```

Teams that run monthly leave `cadence: "monthly"`; teams that run bi-weekly set `cadence: "bi-weekly"`. Comparison and rolling averages then use only entries with that cadence.

---

## 7. Summary

| Theme | Library expansion? | Main addition |
|-------|--------------------|----------------|
| Cadence (monthly / bi-weekly) | Config + history shape | Store `period_days`/`cadence`; compare only same cadence. |
| Trend & comparison | Yes | Persist metrics; read previous period; rolling 3/6. |
| Outliers & risk | Small | Keep key/summary per issue; tail line + sample warning. |
| Self-interpreting | Heuristics + optional history | “What this means”, “Focus”, glossary. |
| Segment | Yes | Read issuetype (and optional components, labels, story points); WIP query. |
| Goals & actions | Config | Targets, “next report” date, suggested actions. |

**Predictable approach:** Run monthly or every two weeks; report content stays the same; comparison and “next report” are cadence-aware so the report fits the team’s rhythm without focusing on too narrow a window.

If you want, next step can be a **ticket-sized breakdown** (e.g. one doc or list of tasks per phase) for implementation in the team-reports repo.
