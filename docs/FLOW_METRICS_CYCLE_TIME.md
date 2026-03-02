# Flow Metrics: Cycle Time (Sum of Time in Execution)

This document describes how **cycle time** is calculated in the flow metrics report and how it differs from lead time.

## Definition

**Cycle time** is the **sum of time (in days) an issue spent in execution statuses** (e.g. In Progress, Review) until its first transition to a completed status (e.g. Done, Closed).

Only time actually spent in execution statuses is counted. Time spent in To Do, Backlog, or any other non-execution status is **excluded**. If an issue moves In Progress → To Do → In Progress → Done, the cycle time is the sum of the two In Progress segments only.

**Lead time** is unchanged: issue **created** → **first transition into a completed status** (from changelog), or created → resolution date if changelog is missing.

## Why sum-only execution?

Earlier behaviour used “first move into execution → first move to done,” which could produce very large values (e.g. 100+ weeks) when an issue was moved to In Progress long ago, then back to backlog, and completed much later. That span is not meaningful for flow.

Summing only time in execution statuses gives a metric that reflects **actual time in execution** and is comparable across issues and periods.

## How it’s computed

1. **Changelog**: The issue must be fetched with `expand=changelog` so status transition history is available.
2. **Transitions**: Status transitions are read as `(time, from_status, to_status)` from the changelog and sorted by time.
3. **First completion**: The first transition whose `to_status` is in the configured completed statuses (e.g. Done, Closed) is found. If there is none, cycle time is not defined (e.g. issue not yet completed).
4. **Sum**: From issue creation (or first transition) up to that first completion time, each segment between two consecutive transitions is attributed to the **from_status** of the later transition. Only segments where `from_status` is in the configured execution statuses (e.g. In Progress, Review) are summed. That sum, in days, is the cycle time.

## Configuration

Execution and completed statuses come from `status_filters` in your Jira config, e.g.:

```yaml
status_filters:
  execution: ["In Progress", "Review"]
  completed: ["Closed", "Done"]
```

Cycle time uses these same lists; no separate config is required.

## Tests

- **`tests/utils/test_cycle_time_execution_sum.py`** – Tests for `cycle_time_execution_sum_days` and `cycle_and_lead_from_issue` (cycle = sum of execution time).
- **`tests/utils/test_cycle_time.py`** – Tests for the legacy `compute_cycle_time_days` (first In Progress → first Done), still used where that behaviour is desired.

## Code

- **`team_reports.utils.jira.cycle_time_execution_sum_days`** – Computes cycle time as the sum of time in execution statuses.
- **`team_reports.utils.jira.cycle_and_lead_from_issue`** – Returns `(cycle_days, lead_days)`; `cycle_days` is from `cycle_time_execution_sum_days`, `lead_days` from changelog (or resolution date).
