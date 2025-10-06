#!/usr/bin/env python3
"""
Unit tests for utils.report module

Tests report formatting and file management functions.
"""

import pytest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys
from datetime import datetime

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from utils.report import (
    format_table_row,
    create_table_header,
    group_tickets_by_status,
    generate_report_header,
    generate_filename,
    save_report,
    ensure_reports_directory,
    create_summary_report
)


class TestFormatTableRow:
    """Test format_table_row function."""
    
    def test_format_basic_ticket(self):
        """Test formatting a basic ticket row."""
        ticket_info = {
            'key': 'TEST-123',
            'url': 'https://jira.example.com/browse/TEST-123',
            'summary': 'Test ticket summary',
            'assignee': 'John Doe',
            'priority': 'High',
            'updated': '2025-01-01'
        }
        
        row = format_table_row(ticket_info)
        
        assert 'TEST-123' in row
        assert 'John Doe' in row
        assert 'High' in row
        assert '2025-01-01' in row
        assert 'Test ticket summary' in row
        assert '[TEST-123](https://jira.example.com/browse/TEST-123)' in row
    
    def test_format_long_title_truncated(self):
        """Test that long titles are truncated properly."""
        ticket_info = {
            'key': 'TEST-123',
            'url': 'https://jira.example.com/browse/TEST-123',
            'summary': 'This is a very long ticket title that should be truncated because it exceeds the maximum width',
            'assignee': 'John Doe',
            'priority': 'High',
            'updated': '2025-01-01'
        }
        
        row = format_table_row(ticket_info, title_width=50)
        
        # Should contain truncated title with ellipsis
        assert '...' in row
        # Should not contain the full original title
        assert 'exceeds the maximum width' not in row
    
    def test_format_long_assignee_truncated(self):
        """Test that long assignee names are truncated."""
        ticket_info = {
            'key': 'TEST-123',
            'url': 'https://jira.example.com/browse/TEST-123',
            'summary': 'Test ticket',
            'assignee': 'Very Long Assignee Name That Should Be Truncated',
            'priority': 'High',
            'updated': '2025-01-01'
        }
        
        row = format_table_row(ticket_info, assignee_width=20)
        
        # Should contain truncated assignee with ellipsis
        assert '...' in row
        # Should not contain the full assignee name
        assert 'That Should Be Truncated' not in row


class TestCreateTableHeader:
    """Test create_table_header function."""
    
    def test_create_table_header(self):
        """Test creating markdown table header."""
        header_lines = create_table_header()
        
        assert len(header_lines) == 2
        assert 'Ticket ID' in header_lines[0]
        assert 'Assignee' in header_lines[0]
        assert 'Priority' in header_lines[0]
        assert 'Updated' in header_lines[0]
        assert 'Title' in header_lines[0]
        
        # Check separator line
        assert '|' in header_lines[1]
        assert '-' in header_lines[1]


class TestGenerateReportHeader:
    """Test generate_report_header function."""
    
    def test_generate_basic_header(self):
        """Test generating basic report header."""
        header_lines = generate_report_header("TEST REPORT", "2025-01-01", "2025-01-07")
        
        assert len(header_lines) > 0
        assert any("TEST REPORT" in line for line in header_lines)
        assert any("2025-01-01" in line for line in header_lines)
        assert any("2025-01-07" in line for line in header_lines)
    
    def test_generate_header_with_metadata(self):
        """Test header includes generation timestamp."""
        header_lines = generate_report_header("TEST", "2025-01-01", "2025-01-07")
        
        # Should contain generation-related text (exact timestamp varies)
        assert any("Generated" in line for line in header_lines)


class TestGenerateFilename:
    """Test generate_filename function."""
    
    def test_generate_filename_basic(self):
        """Test basic filename generation."""
        filename = generate_filename("report", "2025-01-01", "2025-01-07")
        
        assert filename == "report_2025-01-01_to_2025-01-07.md"
    
    def test_generate_filename_custom_extension(self):
        """Test filename generation with custom extension."""
        filename = generate_filename("report", "2025-01-01", "2025-01-07", "txt")
        
        assert filename == "report_2025-01-01_to_2025-01-07.txt"
    
    def test_generate_filename_different_dates(self):
        """Test filename generation with different date ranges."""
        filename = generate_filename("weekly_summary", "2025-06-15", "2025-06-21")
        
        assert filename == "weekly_summary_2025-06-15_to_2025-06-21.md"


class TestEnsureReportsDirectory:
    """Test ensure_reports_directory function."""
    
    @patch('utils.report.os.makedirs')
    @patch('utils.report.os.path.exists')
    def test_ensure_directory_exists(self, mock_exists, mock_makedirs):
        """Test when directory already exists."""
        mock_exists.return_value = True
        
        result = ensure_reports_directory()
        
        mock_exists.assert_called_once_with('Reports')
        mock_makedirs.assert_not_called()
        assert result == 'Reports'
    
    @patch('utils.report.os.makedirs')
    @patch('utils.report.os.path.exists')
    def test_ensure_directory_created(self, mock_exists, mock_makedirs):
        """Test when directory needs to be created."""
        mock_exists.return_value = False
        
        result = ensure_reports_directory()
        
        mock_exists.assert_called_once_with('Reports')
        mock_makedirs.assert_called_once_with('Reports', exist_ok=True)
        assert result == 'Reports'
    
    @patch('utils.report.os.makedirs')
    @patch('utils.report.os.path.exists')
    def test_ensure_custom_directory(self, mock_exists, mock_makedirs):
        """Test with custom directory name."""
        mock_exists.return_value = False
        
        result = ensure_reports_directory('CustomReports')
        
        mock_exists.assert_called_once_with('CustomReports')
        mock_makedirs.assert_called_once_with('CustomReports', exist_ok=True)
        assert result == 'CustomReports'


class TestSaveReport:
    """Test save_report function."""
    
    @patch('utils.report.ensure_reports_directory')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_report_success(self, mock_file, mock_ensure_dir):
        """Test successful report saving."""
        mock_ensure_dir.return_value = 'Reports'
        
        content = "# Test Report\nThis is test content."
        filepath = save_report(content, "test_report.md")
        
        mock_ensure_dir.assert_called_once_with("Reports")
        mock_file.assert_called_once_with('Reports/test_report.md', 'w', encoding='utf-8')
        mock_file().write.assert_called_once_with(content)
        assert filepath == 'Reports/test_report.md'
    
    @patch('utils.report.ensure_reports_directory')
    @patch('builtins.open', new_callable=mock_open)
    def test_save_report_custom_directory(self, mock_file, mock_ensure_dir):
        """Test saving report to custom directory."""
        mock_ensure_dir.return_value = 'CustomDir'
        
        content = "Test content"
        filepath = save_report(content, "test.md", "CustomDir")
        
        mock_ensure_dir.assert_called_once_with("CustomDir")
        assert filepath == 'CustomDir/test.md'


class TestGroupTicketsByStatus:
    """Test group_tickets_by_status function."""
    
    def test_group_tickets_by_status(self):
        """Test grouping tickets by their status."""
        # Create mock tickets
        ticket1 = MagicMock()
        ticket2 = MagicMock()
        ticket3 = MagicMock()
        
        # Mock format function that returns ticket info with status
        def mock_format_func(ticket):
            ticket_map = {
                ticket1: {'key': 'TEST-1', 'status': 'In Progress'},
                ticket2: {'key': 'TEST-2', 'status': 'Done'},
                ticket3: {'key': 'TEST-3', 'status': 'In Progress'}
            }
            return ticket_map[ticket]
        
        tickets = [ticket1, ticket2, ticket3]
        
        grouped = group_tickets_by_status(tickets, mock_format_func)
        
        assert 'In Progress' in grouped
        assert 'Done' in grouped
        assert len(grouped['In Progress']) == 2
        assert len(grouped['Done']) == 1
        assert grouped['In Progress'][0]['key'] == 'TEST-1'
        assert grouped['Done'][0]['key'] == 'TEST-2'


class TestCreateSummaryReport:
    """Test create_summary_report function."""
    
    @patch('utils.report.generate_report_header')
    def test_create_summary_report_basic(self, mock_header):
        """Test creating basic summary report."""
        mock_header.return_value = ["# MOCK HEADER"]
        
        categorized_tickets = {
            'Backend': [
                {'key': 'TEST-1', 'summary': 'Backend task', 'status': 'Done'}
            ],
            'Frontend': [
                {'key': 'TEST-2', 'summary': 'Frontend task', 'status': 'In Progress'}
            ]
        }
        
        def mock_format_func(ticket):
            return ticket  # Just return the ticket as-is for testing
            
        report = create_summary_report(
            "TEST SUMMARY",
            "2025-01-01",
            "2025-01-07",
            categorized_tickets,
            {},  # Empty team_categories
            mock_format_func
        )
        
        mock_header.assert_called_once_with("TEST SUMMARY", "2025-01-01", "2025-01-07")
        assert isinstance(report, str)
        assert "MOCK HEADER" in report
        assert "Backend" in report
        assert "Frontend" in report
        assert "TEST-1" in report
        assert "TEST-2" in report


# Pytest fixtures for common test data
@pytest.fixture
def sample_ticket_info():
    """Fixture providing sample ticket information."""
    return {
        'key': 'PROJ-123',
        'url': 'https://jira.example.com/browse/PROJ-123',
        'summary': 'Implement new feature for user authentication',
        'assignee': 'Jane Developer',
        'priority': 'High',
        'updated': '2025-01-15',
        'status': 'In Progress'
    }


@pytest.fixture
def sample_tickets():
    """Fixture providing sample tickets for grouping tests."""
    return [
        {
            'key': 'TEST-1',
            'summary': 'First ticket',
            'status': 'Done',
            'assignee': 'John Doe'
        },
        {
            'key': 'TEST-2', 
            'summary': 'Second ticket',
            'status': 'In Progress',
            'assignee': 'Jane Smith'
        },
        {
            'key': 'TEST-3',
            'summary': 'Third ticket', 
            'status': 'Done',
            'assignee': 'Bob Wilson'
        }
    ]


@pytest.fixture
def sample_categorized_tickets():
    """Fixture providing sample categorized tickets."""
    return {
        'Backend Development': [
            {'key': 'BACK-1', 'summary': 'API endpoint', 'status': 'Done'},
            {'key': 'BACK-2', 'summary': 'Database migration', 'status': 'In Progress'}
        ],
        'Frontend Development': [
            {'key': 'FRONT-1', 'summary': 'UI component', 'status': 'Review'},
            {'key': 'FRONT-2', 'summary': 'User interface', 'status': 'Done'}
        ],
        'Testing': [
            {'key': 'TEST-1', 'summary': 'Unit tests', 'status': 'To Do'}
        ]
    }


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
