"""
Tests for WIP (Work in Progress) analysis functionality.

Updated to work with optimized JIRA API approach that accepts pre-fetched tickets.
"""

import pytest
from unittest.mock import Mock
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
    
    def test_wip_counts_by_state(self):
        """Test WIP counting with different engineers and states."""
        # Create test tickets
        tickets = [
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'Review'),
            self.create_mock_ticket('Bob', 'In Progress'),
            self.create_mock_ticket(None, 'In Progress'),  # Unassigned
        ]
        
        # Test config
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 2}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        # Generate WIP analysis using optimized approach (pre-fetched tickets)
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Verify results
        assert 'Work in Progress (WIP)' in result
        assert 'Current WIP:** 4 tickets' in result  # Note the format includes colons
        assert 'Alice' in result
        assert 'Bob' in result
        assert '2' in result  # Alice's count
        assert '1' in result  # Bob's count and unassigned
    
    def test_over_limit_flag(self):
        """Test WIP over limit flagging."""
        # Create tickets where Alice has 3 tickets (over the limit of 2)
        tickets = [
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'In Progress'),
            self.create_mock_ticket('Alice', 'Review'),  # 3 tickets total
            self.create_mock_ticket('Bob', 'In Progress'),  # 1 ticket (under limit)
        ]
        
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 2}},  # Limit is 2
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Verify Alice is flagged as over limit
        assert 'Over WIP Limit' in result
        assert 'Alice' in result
        assert '🔴 Yes' in result  # Over limit flag for Alice
        assert '✅ No' in result   # Under limit flag for Bob
    
    def test_no_active_tickets(self):
        """Test WIP analysis when no active tickets exist."""
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config, active_tickets=[])
        
        # Should handle empty case gracefully
        assert 'No active tickets found' in result
        assert 'In Progress, Review' in result  # Shows active states
    
    def test_wip_with_base_jql(self):
        """Test WIP analysis with base JQL configuration."""
        tickets = [self.create_mock_ticket('Alice', 'In Progress')]
        
        config = {
            'states': {'active': ['In Progress']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': 'project = MYPROJECT AND assignee = currentUser()',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Should process tickets normally regardless of base JQL
        assert 'Alice' in result
        assert 'Current WIP:** 1 tickets' in result
    
    def test_error_handling(self):
        """Test WIP analysis error handling for invalid data."""
        # Create tickets with problematic data
        tickets = [
            self.create_mock_ticket('Alice', 'In Progress'),
            Mock()  # Incomplete ticket object
        ]
        
        config = {
            'states': {'active': ['In Progress']},
            'thresholds': {'wip': {'max_per_engineer': 3}},
            'base_jql': '',
            'report_settings': {'max_results': 200}
        }
        
        # Should not crash but handle gracefully
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Should still process valid tickets
        assert 'Alice' in result or 'Error computing WIP analysis' in result


class TestWipConfiguration:
    """Test WIP configuration handling."""
    
    def create_mock_ticket(self, assignee_name, status='In Progress'):
        """Create a mock ticket."""
        ticket = Mock()
        ticket.fields = Mock()
        ticket.fields.assignee = Mock()
        ticket.fields.assignee.displayName = assignee_name
        return ticket
    
    def test_default_configuration(self):
        """Test WIP analysis with default configuration values."""
        tickets = [
            self.create_mock_ticket('Alice'),
            self.create_mock_ticket('Bob')
        ]
        
        # Minimal config to test defaults
        config = {
            'states': {'active': ['In Progress', 'Review']},
            'thresholds': {'wip': {'max_per_engineer': 3}}
        }
        
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        assert 'Alice' in result
        assert 'Bob' in result
        assert 'Current WIP:** 2 tickets' in result
    
    def test_custom_active_states(self):
        """Test WIP analysis with custom active states."""
        tickets = [
            self.create_mock_ticket('Alice'),
            self.create_mock_ticket('Alice'),  # Give Alice 2 tickets
            self.create_mock_ticket('Bob')
        ]
        
        config = {
            'states': {'active': ['Custom State 1', 'Custom State 2']},
            'thresholds': {'wip': {'max_per_engineer': 1}},  # Low threshold for testing
        }
        
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Alice should be flagged as over limit (2 tickets, limit 1)
        assert 'Over WIP Limit' in result
        assert 'Alice' in result
        assert 'Bob' in result


class TestWipIntegration:
    """Integration tests for WIP analysis."""
    
    def create_realistic_ticket(self, assignee_name, status, key=None):
        """Create a realistic mock ticket with all expected fields."""
        ticket = Mock()
        ticket.key = key or f"TEST-{hash(assignee_name + status) % 1000}"
        ticket.fields = Mock()
        ticket.fields.assignee = Mock()
        ticket.fields.assignee.displayName = assignee_name
        ticket.fields.status = Mock()
        ticket.fields.status.name = status
        ticket.fields.summary = f"Test ticket for {assignee_name}"
        return ticket
    
    def test_realistic_wip_scenario(self):
        """Test a realistic team WIP scenario."""
        # Simulate realistic team WIP scenario
        tickets = [
            self.create_realistic_ticket('Alice Smith', 'In Progress', 'PROJ-101'),
            self.create_realistic_ticket('Alice Smith', 'Code Review', 'PROJ-102'),
            self.create_realistic_ticket('Alice Smith', 'QA Review', 'PROJ-103'),  # 3 total - over limit
            self.create_realistic_ticket('Bob Jones', 'In Progress', 'PROJ-201'),
            self.create_realistic_ticket('Bob Jones', 'Code Review', 'PROJ-202'),  # 2 total - at limit
            self.create_realistic_ticket('Carol White', 'In Progress', 'PROJ-301'),  # 1 total - under limit
        ]
        
        # Realistic team configuration
        config = {
            'states': {
                'active': ['In Progress', 'Code Review', 'QA Review']
            },
            'thresholds': {
                'wip': {'max_per_engineer': 2}  # Team WIP limit policy
            },
            'base_jql': 'project = PROJ AND team = "Development Team"',
            'report_settings': {'max_results': 200}
        }
        
        result = generate_wip_analysis(config, active_tickets=tickets)
        
        # Verify comprehensive WIP analysis
        assert 'Current WIP:** 6 tickets' in result
        assert 'Threshold:** 2 per engineer' in result
        
        # Check individual contributors
        assert 'Alice Smith' in result
        assert 'Bob Jones' in result  
        assert 'Carol White' in result
        
        # Verify over-limit detection
        assert 'Over WIP Limit' in result
        assert 'Alice Smith (3 tickets)' in result  # Should be flagged
        
        # Verify WIP counts are correct
        assert '3' in result  # Alice's count
        assert '2' in result  # Bob's count  
        assert '1' in result  # Carol's count