#!/usr/bin/env python3
"""
Unit tests for cycle time calculation functionality.

Tests the compute_cycle_time_days function with various transition scenarios.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from team_reports.utils.jira import compute_cycle_time_days, compute_cycle_time_stats


class TestComputeCycleTimeDays:
    """Test compute_cycle_time_days function with various scenarios."""
    
    def create_mock_issue_with_transitions(self, transitions):
        """
        Create a mock issue with specified status transitions.
        
        Args:
            transitions: List of tuples (timestamp_str, from_status, to_status)
                        e.g., [('2025-01-01T10:00:00', 'To Do', 'In Progress')]
        """
        issue = Mock()
        changelog = Mock()
        
        histories = []
        for timestamp, from_status, to_status in transitions:
            history = Mock()
            history.created = timestamp + '+0000'  # Add timezone info
            
            item = Mock()
            item.field = 'status'
            item.fromString = from_status
            item.toString = to_status
            
            history.items = [item]
            histories.append(history)
        
        changelog.histories = histories
        issue.changelog = changelog
        
        return issue
    
    def test_normal_cycle_time_calculation(self):
        """Test normal path: To Do -> In Progress -> Closed."""
        transitions = [
            ('2025-01-01T10:00:00', 'To Do', 'In Progress'),
            ('2025-01-04T14:00:00', 'In Progress', 'Closed')
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Closed', 'Done']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should be approximately 3.17 days (3 days + 4 hours)
        assert result is not None
        assert 3.0 < result < 3.5
    
    def test_back_and_forth_transitions(self):
        """Test with back-and-forth transitions - should use first occurrence."""
        transitions = [
            ('2025-01-01T10:00:00', 'To Do', 'In Progress'),
            ('2025-01-02T10:00:00', 'In Progress', 'To Do'),  # Moved back
            ('2025-01-03T10:00:00', 'To Do', 'In Progress'),  # Moved to progress again
            ('2025-01-06T10:00:00', 'In Progress', 'Closed')  # Finally closed
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should use first In Progress (2025-01-01) to first Closed (2025-01-06)
        # That's 5 days exactly
        assert result is not None
        assert 4.9 < result < 5.1
    
    def test_missing_in_progress_transition(self):
        """Test when issue never went to In Progress."""
        transitions = [
            ('2025-01-01T10:00:00', 'To Do', 'Closed')  # Direct to closed
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None since never went to In Progress
        assert result is None
    
    def test_missing_done_transition(self):
        """Test when issue never reached Done state."""
        transitions = [
            ('2025-01-01T10:00:00', 'To Do', 'In Progress'),
            ('2025-01-02T10:00:00', 'In Progress', 'Review')  # Stuck in Review
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Closed', 'Done']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None since never reached Done state
        assert result is None
    
    def test_multiple_done_states(self):
        """Test with multiple valid Done states."""
        transitions = [
            ('2025-01-01T10:00:00', 'To Do', 'In Progress'),
            ('2025-01-03T10:00:00', 'In Progress', 'Done'),  # First done state reached
            ('2025-01-04T10:00:00', 'Done', 'Closed')       # Later transition
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Done', 'Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should use first Done transition (2 days)
        assert result is not None
        assert 1.9 < result < 2.1
    
    def test_custom_in_progress_state(self):
        """Test with custom In Progress state name."""
        transitions = [
            ('2025-01-01T10:00:00', 'Backlog', 'Development'),
            ('2025-01-05T10:00:00', 'Development', 'Completed')
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Completed']
        
        result = compute_cycle_time_days(issue, states_done, 'Development')
        
        # Should be 4 days exactly
        assert result is not None
        assert 3.9 < result < 4.1
    
    def test_invalid_date_order(self):
        """Test when Done comes before In Progress (invalid scenario)."""
        transitions = [
            ('2025-01-05T10:00:00', 'To Do', 'In Progress'),  # Later start
            ('2025-01-01T10:00:00', 'In Progress', 'Closed')  # Earlier end
        ]
        
        issue = self.create_mock_issue_with_transitions(transitions)
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None for invalid date order
        assert result is None
    
    def test_no_changelog(self):
        """Test issue with no changelog data."""
        issue = Mock()
        issue.changelog = None
        
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None when no changelog available
        assert result is None
    
    def test_no_status_changes(self):
        """Test issue with changelog but no status changes."""
        issue = Mock()
        changelog = Mock()
        
        # History with non-status changes
        history = Mock()
        history.created = '2025-01-01T10:00:00+0000'
        
        item = Mock()
        item.field = 'assignee'  # Not a status change
        item.fromString = 'User A'
        item.toString = 'User B'
        
        history.items = [item]
        changelog.histories = [history]
        issue.changelog = changelog
        
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None when no status changes found
        assert result is None
    
    def test_malformed_dates(self):
        """Test handling of malformed date strings."""
        issue = Mock()
        changelog = Mock()
        
        history = Mock()
        history.created = 'invalid-date-string'
        
        item = Mock()
        item.field = 'status'
        item.fromString = 'To Do'
        item.toString = 'In Progress'
        
        history.items = [item]
        changelog.histories = [history]
        issue.changelog = changelog
        
        states_done = ['Closed']
        
        result = compute_cycle_time_days(issue, states_done, 'In Progress')
        
        # Should return None for malformed dates
        assert result is None


class TestComputeCycleTimeStats:
    """Test compute_cycle_time_stats function."""
    
    def test_empty_list(self):
        """Test with empty cycle times list."""
        result = compute_cycle_time_stats([])
        
        expected = {'avg': 0.0, 'median': 0.0, 'p90': 0.0}
        assert result == expected
    
    def test_single_value(self):
        """Test with single cycle time."""
        result = compute_cycle_time_stats([5.5])
        
        expected = {'avg': 5.5, 'median': 5.5, 'p90': 5.5}
        assert result == expected
    
    def test_even_count_values(self):
        """Test with even number of values."""
        cycle_times = [1.0, 2.0, 3.0, 4.0]
        result = compute_cycle_time_stats(cycle_times)
        
        # Avg = 2.5, Median = (2+3)/2 = 2.5, P90 = 4.0 (90% of 4 = index 2.6 -> index 2 = 3.0)
        assert result['avg'] == 2.5
        assert result['median'] == 2.5
        # P90 index = int(0.9 * 4) - 1 = 2, so sorted_times[2] = 3.0
        assert result['p90'] == 3.0
    
    def test_odd_count_values(self):
        """Test with odd number of values."""
        cycle_times = [1.0, 3.0, 5.0]
        result = compute_cycle_time_stats(cycle_times)
        
        # Avg = 3.0, Median = 3.0, P90 = 3.0 (90% of 3 = index 1.7 -> index 1 = 3.0) 
        assert result['avg'] == 3.0
        assert result['median'] == 3.0
        # P90 index = int(0.9 * 3) - 1 = 1, so sorted_times[1] = 3.0
        assert result['p90'] == 3.0
    
    def test_larger_dataset(self):
        """Test with larger dataset."""
        cycle_times = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        result = compute_cycle_time_stats(cycle_times)
        
        # Avg = 5.5, Median = (5+6)/2 = 5.5, P90 = 9.0 (90% of 10 = index 8)
        assert result['avg'] == 5.5
        assert result['median'] == 5.5
        # P90 index = int(0.9 * 10) - 1 = 8, so sorted_times[8] = 9.0
        assert result['p90'] == 9.0
    
    def test_unsorted_input(self):
        """Test that function handles unsorted input."""
        cycle_times = [5.0, 1.0, 3.0, 9.0, 2.0]
        result = compute_cycle_time_stats(cycle_times)
        
        # Should sort internally: [1.0, 2.0, 3.0, 5.0, 9.0]
        # Avg = 4.0, Median = 3.0, P90 = 5.0 (90% of 5 = index 3.5 -> index 3 = 5.0)
        assert result['avg'] == 4.0
        assert result['median'] == 3.0
        # P90 index = int(0.9 * 5) - 1 = 3, so sorted_times[3] = 5.0
        assert result['p90'] == 5.0
    
    def test_rounding(self):
        """Test that results are rounded to 1 decimal place."""
        cycle_times = [1.123, 2.456, 3.789]
        result = compute_cycle_time_stats(cycle_times)
        
        # All values should be rounded to 1 decimal place
        assert result['avg'] == 2.5  # (1.123 + 2.456 + 3.789) / 3 = 2.456 -> 2.5
        assert result['median'] == 2.5  # 2.456 -> 2.5
        assert result['p90'] == 2.5  # P90 index = 1, sorted_times[1] = 2.456 -> 2.5
    
    def test_duplicate_values(self):
        """Test with duplicate values."""
        cycle_times = [2.0, 2.0, 2.0, 2.0, 2.0]
        result = compute_cycle_time_stats(cycle_times)
        
        # All stats should be 2.0
        assert result['avg'] == 2.0
        assert result['median'] == 2.0
        assert result['p90'] == 2.0


# Integration test fixtures
@pytest.fixture
def mock_jira_issue_normal():
    """Fixture for normal issue with complete cycle."""
    issue = Mock()
    changelog = Mock()
    
    # Normal flow: To Do -> In Progress -> Closed
    history1 = Mock()
    history1.created = '2025-01-01T09:00:00+0000'
    item1 = Mock()
    item1.field = 'status'
    item1.fromString = 'To Do'
    item1.toString = 'In Progress'
    history1.items = [item1]
    
    history2 = Mock()
    history2.created = '2025-01-04T17:00:00+0000'  # 3 days + 8 hours later
    item2 = Mock()
    item2.field = 'status' 
    item2.fromString = 'In Progress'
    item2.toString = 'Closed'
    history2.items = [item2]
    
    changelog.histories = [history1, history2]
    issue.changelog = changelog
    
    return issue


class TestCycleTimeIntegration:
    """Integration tests for cycle time calculation."""
    
    def test_realistic_issue_flow(self, mock_jira_issue_normal):
        """Test with realistic issue transition flow."""
        states_done = ['Closed', 'Done']
        
        result = compute_cycle_time_days(mock_jira_issue_normal, states_done, 'In Progress')
        
        # Should be approximately 3.33 days (3 days + 8 hours)
        assert result is not None
        assert 3.3 < result < 3.4
    
    def test_integration_with_stats(self):
        """Test integration between cycle time calculation and stats."""
        # Create multiple issues with known cycle times
        cycle_times_expected = [1.0, 2.0, 3.0, 4.0, 5.0]
        
        # Test that our stats function works correctly
        stats = compute_cycle_time_stats(cycle_times_expected)
        
        assert stats['avg'] == 3.0
        assert stats['median'] == 3.0
        assert stats['p90'] == 4.0  # P90 index = int(0.9 * 5) - 1 = 3


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
