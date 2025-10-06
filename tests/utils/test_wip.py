"""
Tests for WIP (Work in Progress) analysis functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from jira_weekly_summary import generate_wip_analysis


class TestWipCounts:
    """Test WIP counting by engineer and state."""
    
    def create_mock_ticket(self, assignee_name=None, status='In Progress'):
        """Create a mock Jira ticket for testing."""
        ticket = Mock()
        ticket.fields = Mock()
        ticket.fields.status = Mock()
        ticket.fields.status.name = status
        
        if assignee_name:
            ticket.fields.assignee = Mock()
            ticket.fields.assignee.displayName = assignee_name
        else:
            ticket.fields.assignee = None
            
        return ticket
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_wip_counts_by_state(self, mock_jira_init):
        """Test WIP counting with different engineers and states."""
        # Mock Jira client and search results
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        
        # Create test tickets
        tickets = [
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'Review'),
            self.create_mock_ticket('Bob', 'In Progress'),
            self.create_mock_ticket(None, 'In Progress'),  # Unassigned
        ]
        mock_jira.search_issues.return_value = tickets
        
        # Test config
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 2}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        # Generate WIP analysis
        result = generate_wip_analysis(config)
        
        # Verify results
        assert 'Work in Progress (WIP)' in result
        assert 'Current WIP:** 4 tickets' in result  # Note the format includes colons
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Unassigned' in result
        assert '| Alice | 2 |' in result
        assert '| Bob | 1 |' in result
        assert '| *Unassigned* | 1 |' in result
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_over_limit_flag(self, mock_jira_init):
        """Test over-limit detection and highlighting."""
        # Mock Jira client
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        
        # Create tickets where Alice is over limit
        tickets = [
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'Review'),
            self.create_mock_ticket('Alice', 'In Progress'),  # 4 tickets for Alice
            self.create_mock_ticket('Bob', 'In Progress'),    # 1 ticket for Bob
        ]
        mock_jira.search_issues.return_value = tickets
        
        # Test config with threshold of 3
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        # Generate WIP analysis
        result = generate_wip_analysis(config)
        
        # Verify over-limit detection
        assert 'Over WIP Limit' in result
        assert 'Alice (4 tickets)' in result
        assert 'exceeds threshold of 3' in result
        assert '🔴 Yes' in result  # Alice should be marked as over limit
        assert '✅ No' in result   # Bob should be within limit
        
        # Verify Alice has 4, Bob has 1
        assert '| Alice | 4 | 🔴 Yes |' in result
        assert '| Bob | 1 | ✅ No |' in result
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_no_active_tickets(self, mock_jira_init):
        """Test WIP analysis when no active tickets exist."""
        # Mock Jira client with empty results
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        mock_jira.search_issues.return_value = []
        
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config)
        
        # Should show no active tickets message
        assert 'No active tickets found in states' in result
        assert 'In Progress, Review' in result
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_wip_with_base_jql(self, mock_jira_init):
        """Test WIP analysis respects base JQL filter."""
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        mock_jira.search_issues.return_value = []
        
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': 'project = TEST AND assignee is not EMPTY',
            'report_settings': {'max_results': 200}
        }
        
        generate_wip_analysis(config)
        
        # Verify JQL construction
        expected_jql = '(project = TEST AND assignee is not EMPTY) AND status in ("In Progress","Review")'
        mock_jira.search_issues.assert_called_once_with(
            expected_jql, maxResults=200, expand='changelog'
        )
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_error_handling(self, mock_jira_init):
        """Test WIP analysis handles errors gracefully."""
        # Mock Jira client to raise an exception
        mock_jira_init.side_effect = Exception("Jira connection failed")
        
        config = {
            'states': {'active': ['In Progress']},
            'thresholds': {'wip': {'max_per_engineer': 3}}
        }
        
        result = generate_wip_analysis(config)
        
        # Should return error message instead of crashing
        assert 'Error computing WIP analysis' in result
        assert 'Jira connection failed' in result


class TestWipConfiguration:
    """Test WIP analysis with different configuration scenarios."""
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_default_configuration(self, mock_jira_init):
        """Test WIP analysis uses default values when config is minimal."""
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        mock_jira.search_issues.return_value = []
        
        # Minimal config - should use defaults
        config = {}
        
        result = generate_wip_analysis(config)
        
        # Should use default active states and threshold
        expected_jql = 'status in ("In Progress","Review")'
        mock_jira.search_issues.assert_called_once_with(
            expected_jql, maxResults=200, expand='changelog'
        )
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_custom_active_states(self, mock_jira_init):
        """Test WIP analysis with custom active states."""
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        mock_jira.search_issues.return_value = []
        
        config = {
            'states': {'active': ['Development', 'Testing', 'Code Review']},
            'thresholds': {'wip': {'max_per_engineer': 5}}
        }
        
        generate_wip_analysis(config)
        
        # Should use custom active states
        expected_jql = 'status in ("Development","Testing","Code Review")'
        mock_jira.search_issues.assert_called_once_with(
            expected_jql, maxResults=200, expand='changelog'
        )


class TestWipIntegration:
    """Integration tests for WIP analysis."""
    
    @patch('jira_weekly_summary.initialize_jira_client')
    def test_realistic_wip_scenario(self, mock_jira_init):
        """Test a realistic WIP scenario with mixed engineers and states."""
        mock_jira = Mock()
        mock_jira_init.return_value = mock_jira
        
        # Create a realistic set of tickets
        tickets = [
            # Alice: 3 tickets (at threshold)
            Mock(fields=Mock(assignee=Mock(displayName='Alice Smith'))),
            Mock(fields=Mock(assignee=Mock(displayName='Alice Smith'))),
            Mock(fields=Mock(assignee=Mock(displayName='Alice Smith'))),
            
            # Bob: 5 tickets (over threshold of 3)
            Mock(fields=Mock(assignee=Mock(displayName='Bob Johnson'))),
            Mock(fields=Mock(assignee=Mock(displayName='Bob Johnson'))),
            Mock(fields=Mock(assignee=Mock(displayName='Bob Johnson'))),
            Mock(fields=Mock(assignee=Mock(displayName='Bob Johnson'))),
            Mock(fields=Mock(assignee=Mock(displayName='Bob Johnson'))),
            
            # Charlie: 1 ticket (under threshold)
            Mock(fields=Mock(assignee=Mock(displayName='Charlie Brown'))),
            
            # Unassigned: 2 tickets
            Mock(fields=Mock(assignee=None)),
            Mock(fields=Mock(assignee=None)),
        ]
        mock_jira.search_issues.return_value = tickets
        
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': 'project = MYPROJECT',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config)
        
        # Verify comprehensive output
        assert 'Current WIP:** 11 tickets' in result
        assert 'Threshold:** 3 per engineer' in result
        assert 'Alice Smith' in result
        assert 'Bob Johnson' in result 
        assert 'Charlie Brown' in result
        assert 'Over WIP Limit' in result
        assert 'Bob Johnson (5 tickets)** exceeds threshold' in result
        
        # Alice should be at limit (✅), Bob over limit (🔴), Charlie under (✅)
        assert '| Bob Johnson | 5 | 🔴 Yes |' in result
        assert '| Alice Smith | 3 | ✅ No |' in result  # At threshold is OK
        assert '| Charlie Brown | 1 | ✅ No |' in result
