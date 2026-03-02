#!/usr/bin/env python3
"""
Unit tests for cycle time as sum-of-time-in-execution.

Verifies cycle_time_execution_sum_days and cycle_and_lead_from_issue (cycle = sum of
contiguous time in execution statuses only; time in To Do, Backlog, etc. excluded).
"""

import os
import sys
from datetime import datetime
from unittest.mock import Mock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from team_reports.utils.jira import (
    cycle_and_lead_from_issue,
    cycle_time_execution_sum_days,
)


def _mock_issue(transitions, created_iso=None, resolution_iso=None):
    """Build a mock issue with changelog (list of (timestamp_str, from_status, to_status))."""
    issue = Mock()
    issue.fields = Mock()
    issue.fields.created = created_iso or (transitions[0][0][:19] + "+0000" if transitions else "")
    issue.fields.resolutiondate = resolution_iso or (transitions[-1][0][:19] + "+0000" if transitions else None)
    changelog = Mock()
    histories = []
    for timestamp, from_status, to_status in transitions:
        h = Mock()
        h.created = timestamp[:19] if len(timestamp) > 19 else timestamp
        if not h.created.endswith("Z") and "+" not in h.created:
            h.created = h.created + "+0000"
        item = Mock()
        item.field = "status"
        item.fromString = from_status
        item.toString = to_status
        h.items = [item]
        histories.append(h)
    changelog.histories = histories
    issue.changelog = changelog
    return issue


EXECUTION = ["In Progress", "Review"]
COMPLETED = ["Closed", "Done"]


class TestCycleTimeExecutionSumDays:
    """Tests for cycle_time_execution_sum_days: sum only of time in execution statuses."""

    def test_single_execution_segment(self):
        """To Do -> In Progress (day 1) -> Done (day 4): 3 days in execution."""
        transitions = [
            ("2025-01-01T10:00:00", "To Do", "In Progress"),
            ("2025-01-04T10:00:00", "In Progress", "Done"),
        ]
        issue = _mock_issue(transitions)
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is not None
        assert 2.99 <= result <= 3.01

    def test_back_and_forth_only_execution_counted(self):
        """In Progress (day 1) -> To Do (day 2) -> In Progress (day 3) -> Done (day 6). Sum = 1 + 3 = 4 days."""
        transitions = [
            ("2025-01-01T00:00:00", "To Do", "In Progress"),
            ("2025-01-02T00:00:00", "In Progress", "To Do"),
            ("2025-01-03T00:00:00", "To Do", "In Progress"),
            ("2025-01-06T00:00:00", "In Progress", "Done"),
        ]
        issue = _mock_issue(transitions)
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is not None
        assert 3.99 <= result <= 4.01

    def test_never_completed_returns_none(self):
        """No transition to Done -> None."""
        transitions = [
            ("2025-01-01T10:00:00", "To Do", "In Progress"),
            ("2025-01-02T10:00:00", "In Progress", "Review"),
        ]
        issue = _mock_issue(transitions, resolution_iso=None)
        issue.fields.resolutiondate = None
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is None

    def test_direct_to_done_zero_execution(self):
        """To Do -> Done with no execution in between: 0 days."""
        transitions = [
            ("2025-01-01T10:00:00", "To Do", "Done"),
        ]
        issue = _mock_issue(transitions)
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is not None
        assert 0 <= result < 0.01

    def test_multiple_execution_states_summed(self):
        """In Progress (day 1) -> Review (day 2) -> Done (day 3): total 2 days in execution."""
        transitions = [
            ("2025-01-01T00:00:00", "To Do", "In Progress"),
            ("2025-01-02T00:00:00", "In Progress", "Review"),
            ("2025-01-03T00:00:00", "Review", "Done"),
        ]
        issue = _mock_issue(transitions)
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is not None
        assert 1.99 <= result <= 2.01

    def test_no_changelog_returns_none(self):
        """Issue with no changelog returns None."""
        issue = Mock()
        issue.fields = Mock()
        issue.fields.created = "2025-01-01T10:00:00+0000"
        issue.changelog = None
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is None

    def test_empty_histories_returns_none(self):
        """Changelog with no histories returns None."""
        issue = Mock()
        issue.fields = Mock()
        issue.fields.created = "2025-01-01T10:00:00+0000"
        changelog = Mock()
        changelog.histories = []
        issue.changelog = changelog
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is None

    def test_created_before_first_transition(self):
        """Segment from created to first transition uses issue created time."""
        transitions = [
            ("2025-01-05T00:00:00", "To Do", "In Progress"),
            ("2025-01-08T00:00:00", "In Progress", "Done"),
        ]
        issue = _mock_issue(transitions, created_iso="2025-01-01T00:00:00+0000")
        result = cycle_time_execution_sum_days(issue, EXECUTION, COMPLETED)
        assert result is not None
        # 3 days In Progress (Jan 5 -> Jan 8)
        assert 2.99 <= result <= 3.01


class TestCycleAndLeadFromIssueWithSumCycle:
    """Tests for cycle_and_lead_from_issue when cycle = sum of execution time."""

    def test_cycle_is_sum_lead_is_first_done(self):
        """Cycle = sum of execution days; lead = created to first Done."""
        transitions = [
            ("2025-01-01T00:00:00", "To Do", "In Progress"),
            ("2025-01-02T00:00:00", "In Progress", "To Do"),
            ("2025-01-05T00:00:00", "To Do", "In Progress"),
            ("2025-01-10T00:00:00", "In Progress", "Done"),
        ]
        issue = _mock_issue(transitions, created_iso="2025-01-01T00:00:00+0000")
        cycle_days, lead_days = cycle_and_lead_from_issue(issue, EXECUTION, COMPLETED)
        assert cycle_days is not None
        assert lead_days is not None
        # Cycle: 1 day (Jan 1–2) + 5 days (Jan 5–10) = 6 days
        assert 5.9 <= cycle_days <= 6.1
        # Lead: Jan 1 to Jan 10 = 9 days
        assert 8.9 <= lead_days <= 9.1

    def test_lead_fallback_to_resolutiondate_when_no_changelog(self):
        """When changelog is missing, lead uses resolutiondate; cycle is None."""
        issue = Mock()
        issue.fields = Mock()
        issue.fields.created = "2025-01-01T00:00:00+0000"
        issue.fields.resolutiondate = "2025-01-15T00:00:00+0000"
        issue.changelog = None
        cycle_days, lead_days = cycle_and_lead_from_issue(issue, EXECUTION, COMPLETED)
        assert cycle_days is None
        assert lead_days is not None
        assert 13.9 <= lead_days <= 14.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
