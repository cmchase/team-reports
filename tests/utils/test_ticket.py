#!/usr/bin/env python3
"""
Unit tests for utils.ticket module

Tests ticket categorization and formatting functions with mock Jira issue objects.
"""

import pytest
from unittest.mock import MagicMock, Mock
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from team_reports.utils.ticket import (
    categorize_ticket,
    format_ticket_info,
    get_ticket_components,
    get_ticket_text_content
)


class TestCategorizeTicket:
    """Test categorize_ticket function."""
    
    def test_categorize_by_component(self):
        """Test categorization based on component matching."""
        # Mock Jira issue with component
        issue = MagicMock()
        issue.fields.components = [MagicMock()]
        issue.fields.components[0].name = 'Backend API'
        issue.fields.project.key = 'TEST'
        issue.fields.summary = 'API development task'
        issue.fields.description = 'Develop new API endpoint'
        
        team_categories = {
            'Backend': {
                'components': ['Backend API', 'Database'],
                'description': 'Backend development'
            },
            'Frontend': {
                'components': ['UI', 'Frontend'],
                'description': 'Frontend development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Backend'
    
    def test_categorize_by_project(self):
        """Test categorization based on project matching."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'MOBILE'
        issue.fields.summary = 'Mobile app development'
        issue.fields.description = 'Develop mobile feature'
        
        team_categories = {
            'Mobile': {
                'projects': ['MOBILE', 'MOBILE-IOS'],
                'description': 'Mobile development'
            },
            'Web': {
                'projects': ['WEB'],
                'description': 'Web development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Mobile'
    
    def test_categorize_by_keyword_in_summary(self):
        """Test categorization based on keyword in summary."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'TEST'
        issue.fields.summary = 'Fix deployment pipeline issue'
        issue.fields.description = 'The deployment is failing'
        
        team_categories = {
            'DevOps': {
                'keywords': ['deployment', 'infrastructure', 'pipeline'],
                'description': 'DevOps and infrastructure'
            },
            'Backend': {
                'keywords': ['api', 'backend'],
                'description': 'Backend development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'DevOps'
    
    def test_categorize_by_keyword_in_description(self):
        """Test categorization based on keyword in description."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'TEST'
        issue.fields.summary = 'Fix bug'
        issue.fields.description = 'The database query is too slow'
        
        team_categories = {
            'Database': {
                'keywords': ['database', 'sql', 'query'],
                'description': 'Database work'
            },
            'Frontend': {
                'keywords': ['ui', 'frontend'],
                'description': 'Frontend work'  
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Database'
    
    def test_categorize_case_insensitive_keywords(self):
        """Test that keyword matching is case insensitive."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'TEST'
        issue.fields.summary = 'API Development Task'  # Uppercase API
        issue.fields.description = 'Working on REST API'
        
        team_categories = {
            'Backend': {
                'keywords': ['api', 'backend'],  # Lowercase keywords
                'description': 'Backend development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Backend'
    
    def test_categorize_no_match_returns_uncategorized(self):
        """Test that unmatched tickets return 'Uncategorized'."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'UNKNOWN'
        issue.fields.summary = 'Some random task'
        issue.fields.description = 'No matching keywords'
        
        team_categories = {
            'Backend': {
                'components': ['API'],
                'keywords': ['backend'],
                'description': 'Backend development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Other'
    
    def test_categorize_missing_fields_handled(self):
        """Test that missing fields don't cause errors."""
        issue = MagicMock()
        issue.fields.components = None  # None instead of empty list
        issue.fields.project.key = 'TEST'
        issue.fields.summary = None  # None summary  
        issue.fields.description = None  # None description
        
        team_categories = {
            'Backend': {
                'components': ['API'],
                'keywords': ['backend'],
                'description': 'Backend development'
            }
        }
        
        category = categorize_ticket(issue, team_categories)
        
        assert category == 'Other'


class TestFormatTicketInfo:
    """Test format_ticket_info function."""
    
    def test_format_basic_ticket_info(self):
        """Test formatting basic ticket information."""
        issue = MagicMock()
        issue.key = 'TEST-123'
        issue.fields.summary = 'Test ticket summary'
        issue.fields.status.name = 'In Progress'
        issue.fields.priority.name = 'High'
        issue.fields.assignee.displayName = 'John Doe'
        issue.fields.assignee.emailAddress = 'john@example.com'
        issue.fields.updated = '2025-01-15T10:30:00.000+0000'
        
        jira_server_url = 'https://jira.example.com'
        
        info = format_ticket_info(issue, jira_server_url)
        
        assert info['key'] == 'TEST-123'
        assert info['summary'] == 'Test ticket summary'
        assert info['status'] == 'In Progress'
        assert info['priority'] == 'High'
        assert info['assignee'] == 'John Doe'
        assert info['assignee_email'] == 'john@example.com'
        assert info['url'] == 'https://jira.example.com/browse/TEST-123'
        assert '2025-01-15' in info['updated']
    
    def test_format_unassigned_ticket(self):
        """Test formatting ticket with no assignee."""
        issue = MagicMock()
        issue.key = 'TEST-124'
        issue.fields.summary = 'Unassigned ticket'
        issue.fields.status.name = 'Open'
        issue.fields.priority.name = 'Medium'
        issue.fields.assignee = None  # No assignee
        issue.fields.updated = '2025-01-15T10:30:00.000+0000'
        
        jira_server_url = 'https://jira.example.com'
        
        info = format_ticket_info(issue, jira_server_url)
        
        assert info['assignee'] == 'Unassigned'
        assert info['assignee_email'] == ''
    
    def test_format_with_config_team_member_mapping(self):
        """Test formatting with team member name mapping from config."""
        issue = MagicMock()
        issue.key = 'TEST-125'
        issue.fields.summary = 'Test with config'
        issue.fields.status.name = 'Done'
        issue.fields.priority.name = 'Low'
        issue.fields.assignee.displayName = 'john@example.com'  # Email as display name
        issue.fields.assignee.emailAddress = 'john@example.com'
        issue.fields.updated = '2025-01-15T10:30:00.000+0000'
        
        config = {
            'team_members': {
                'john@example.com': 'John Doe (Backend Team)'
            }
        }
        
        jira_server_url = 'https://jira.example.com'
        
        info = format_ticket_info(issue, jira_server_url, config)
        
        assert info['assignee'] == 'John Doe (Backend Team)'
    
    def test_format_missing_priority(self):
        """Test formatting ticket with missing priority."""
        issue = MagicMock()
        issue.key = 'TEST-126'
        issue.fields.summary = 'No priority ticket'
        issue.fields.status.name = 'Open'
        issue.fields.priority = None  # No priority
        issue.fields.assignee.displayName = 'Jane Doe'
        issue.fields.assignee.emailAddress = 'jane@example.com'
        issue.fields.updated = '2025-01-15T10:30:00.000+0000'
        
        jira_server_url = 'https://jira.example.com'
        
        info = format_ticket_info(issue, jira_server_url)
        
        assert info['priority'] == 'None'


class TestGetTicketComponents:
    """Test get_ticket_components function."""
    
    def test_get_components_with_components(self):
        """Test getting components when components exist."""
        issue = MagicMock()
        component1 = MagicMock()
        component1.name = 'Backend API'
        component2 = MagicMock() 
        component2.name = 'Database'
        issue.fields.components = [component1, component2]
        
        components = get_ticket_components(issue)
        
        assert components == ['Backend API', 'Database']
    
    def test_get_components_no_components(self):
        """Test getting components when no components exist."""
        issue = MagicMock()
        issue.fields.components = []
        
        components = get_ticket_components(issue)
        
        assert components == []
    
    def test_get_components_none_components(self):
        """Test getting components when components is None."""
        issue = MagicMock()
        issue.fields.components = None
        
        components = get_ticket_components(issue)
        
        assert components == []


class TestGetTicketTextContent:
    """Test get_ticket_text_content function."""
    
    def test_get_text_with_summary_and_description(self):
        """Test getting text content with both summary and description."""
        issue = MagicMock()
        issue.fields.summary = 'Ticket Summary'
        issue.fields.description = 'Detailed description of the ticket'
        
        text_content = get_ticket_text_content(issue)
        
        expected = 'ticket summary detailed description of the ticket'
        assert text_content == expected
    
    def test_get_text_summary_only(self):
        """Test getting text content with summary only."""
        issue = MagicMock()
        issue.fields.summary = 'Just a summary'
        issue.fields.description = None
        
        text_content = get_ticket_text_content(issue)
        
        assert text_content == 'just a summary'
    
    def test_get_text_description_only(self):
        """Test getting text content with description only."""
        issue = MagicMock()
        issue.fields.summary = None
        issue.fields.description = 'Only description available'
        
        text_content = get_ticket_text_content(issue)
        
        assert text_content == 'only description available'
    
    def test_get_text_no_content(self):
        """Test getting text content when both fields are None."""
        issue = MagicMock()
        issue.fields.summary = None
        issue.fields.description = None
        
        text_content = get_ticket_text_content(issue)
        
        assert text_content == ''
    
    def test_get_text_empty_strings(self):
        """Test getting text content when fields are empty strings."""
        issue = MagicMock()
        issue.fields.summary = ''
        issue.fields.description = ''
        
        text_content = get_ticket_text_content(issue)
        
        assert text_content == ''


# Pytest fixtures for common mock objects
@pytest.fixture
def mock_jira_issue():
    """Fixture providing a mock Jira issue with common fields."""
    issue = MagicMock()
    issue.key = 'PROJ-123'
    issue.fields.summary = 'Sample ticket summary'
    issue.fields.description = 'Sample ticket description with details'
    issue.fields.status.name = 'In Progress'
    issue.fields.priority.name = 'High'
    issue.fields.assignee.displayName = 'John Developer'
    issue.fields.assignee.emailAddress = 'john@example.com'
    issue.fields.updated = '2025-01-15T14:30:45.123+0000'
    issue.fields.project.key = 'PROJ'
    
    # Mock components
    component = MagicMock()
    component.name = 'Backend'
    issue.fields.components = [component]
    
    return issue


@pytest.fixture
def sample_team_categories():
    """Fixture providing sample team categories for testing."""
    return {
        'Backend Development': {
            'components': ['Backend', 'API', 'Database'],
            'keywords': ['backend', 'api', 'service', 'database'],
            'projects': ['BACKEND'],
            'description': 'Backend development tasks'
        },
        'Frontend Development': {
            'components': ['Frontend', 'UI', 'UX'],
            'keywords': ['frontend', 'ui', 'react', 'javascript'],
            'projects': ['WEB', 'UI'],
            'description': 'Frontend and UI development'
        },
        'DevOps': {
            'keywords': ['deployment', 'infrastructure', 'docker', 'kubernetes'],
            'projects': ['INFRA'],
            'description': 'DevOps and infrastructure work'
        },
        'Mobile': {
            'components': ['Mobile', 'iOS', 'Android'],
            'keywords': ['mobile', 'ios', 'android', 'app'],
            'projects': ['MOBILE'],
            'description': 'Mobile app development'
        }
    }


@pytest.fixture
def sample_config():
    """Fixture providing sample configuration with team members."""
    return {
        'team_members': {
            'john@example.com': 'John Doe (Backend)',
            'jane@example.com': 'Jane Smith (Frontend)', 
            'bob@example.com': 'Bob Wilson (DevOps)',
            'alice@example.com': 'Alice Johnson (Mobile)'
        },
        'jira_server': 'https://company.atlassian.net'
    }


class TestCategorizeTicketIntegration:
    """Integration tests for categorize_ticket with realistic scenarios."""
    
    def test_backend_ticket_categorization(self, sample_team_categories):
        """Test categorizing a typical backend ticket."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'BACKEND'
        issue.fields.summary = 'Implement user authentication API endpoint'
        issue.fields.description = 'Create REST API for user login with JWT tokens'
        
        category = categorize_ticket(issue, sample_team_categories)
        
        assert category == 'Backend Development'
    
    def test_devops_ticket_categorization(self, sample_team_categories):
        """Test categorizing a DevOps ticket."""
        issue = MagicMock()
        issue.fields.components = []
        issue.fields.project.key = 'PROJ'
        issue.fields.summary = 'Set up Kubernetes deployment pipeline'
        issue.fields.description = 'Configure CI/CD with Docker and Kubernetes'
        
        category = categorize_ticket(issue, sample_team_categories)
        
        assert category == 'DevOps'


class TestFormatTicketInfoIntegration:
    """Integration tests for format_ticket_info with realistic scenarios."""
    
    def test_complete_ticket_formatting(self, sample_config):
        """Test formatting a complete ticket with all fields."""
        issue = MagicMock()
        issue.key = 'PROJ-456'
        issue.fields.summary = 'Implement user dashboard'
        issue.fields.status.name = 'Code Review'
        issue.fields.priority.name = 'Medium'
        issue.fields.assignee.displayName = 'Jane Smith'
        issue.fields.assignee.emailAddress = 'jane@example.com'
        issue.fields.updated = '2025-01-20T09:15:30.456+0000'
        
        info = format_ticket_info(issue, 'https://jira.company.com', sample_config)
        
        assert info['key'] == 'PROJ-456'
        assert info['assignee'] == 'Jane Smith (Frontend)'  # Mapped from config
        assert info['url'] == 'https://jira.company.com/browse/PROJ-456'
        assert 'PROJ-456' in info['url']


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
