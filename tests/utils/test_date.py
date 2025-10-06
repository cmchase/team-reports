#!/usr/bin/env python3
"""
Unit tests for utils.date module

Tests all date utility functions with various edge cases and scenarios.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from utils.date import (
    parse_date_args,
    get_current_week,
    get_last_week, 
    get_week_starting,
    get_date_range,
    get_month_range,
    format_date_for_display,
    validate_date_format,
    get_quarter_range,
    get_current_quarter,
    parse_quarter_from_date
)


class TestParseDateArgs:
    """Test parse_date_args function with various argument combinations."""
    
    def test_parse_two_dates(self):
        """Test parsing when two dates are provided."""
        args = ["2025-01-01", "2025-01-07"] 
        start, end = parse_date_args(args)
        assert start == "2025-01-01"
        assert end == "2025-01-07"
    
    def test_parse_single_date(self):
        """Test parsing when single date is provided (should add 6 days)."""
        args = ["2025-01-01"]
        start, end = parse_date_args(args)
        assert start == "2025-01-01"
        assert end == "2025-01-07"  # +6 days
    
    def test_parse_single_date_different_month(self):
        """Test single date parsing crossing month boundary."""
        args = ["2025-01-30"]
        start, end = parse_date_args(args)
        assert start == "2025-01-30"
        assert end == "2025-02-05"  # Crosses into February
    
    @patch('utils.date.get_current_week')
    def test_parse_no_dates(self, mock_get_current_week):
        """Test parsing when no dates provided (should get current week)."""
        mock_get_current_week.return_value = ("2025-01-06", "2025-01-12")
        
        start, end = parse_date_args([])
        
        mock_get_current_week.assert_called_once()
        assert start == "2025-01-06"
        assert end == "2025-01-12"
    
    def test_parse_more_than_two_dates(self):
        """Test parsing when more than two dates provided (should use first two)."""
        args = ["2025-01-01", "2025-01-07", "2025-01-14"]
        start, end = parse_date_args(args)
        assert start == "2025-01-01"
        assert end == "2025-01-07"  # Should ignore third date
    
    def test_parse_none_args(self):
        """Test parsing when args is None (should use sys.argv)."""
        with patch('sys.argv', ['script.py', '2025-01-01', '2025-01-07']):
            start, end = parse_date_args(None)
            assert start == "2025-01-01"
            assert end == "2025-01-07"


class TestGetCurrentWeek:
    """Test get_current_week function."""
    
    @patch('utils.date.datetime')
    def test_get_current_week_monday(self, mock_datetime):
        """Test when today is Monday."""
        # Mock Monday, January 6, 2025
        mock_now = datetime(2025, 1, 6)  # Monday
        mock_datetime.now.return_value = mock_now
        
        start, end = get_current_week()
        
        assert start == "2025-01-06"  # Same Monday
        assert end == "2025-01-12"    # Following Sunday
    
    @patch('utils.date.datetime')
    def test_get_current_week_friday(self, mock_datetime):
        """Test when today is Friday."""
        # Mock Friday, January 10, 2025
        mock_now = datetime(2025, 1, 10)  # Friday
        mock_datetime.now.return_value = mock_now
        
        start, end = get_current_week()
        
        assert start == "2025-01-06"  # Previous Monday
        assert end == "2025-01-12"    # Following Sunday
    
    @patch('utils.date.datetime')
    def test_get_current_week_sunday(self, mock_datetime):
        """Test when today is Sunday."""
        # Mock Sunday, January 12, 2025
        mock_now = datetime(2025, 1, 12)  # Sunday
        mock_datetime.now.return_value = mock_now
        
        start, end = get_current_week()
        
        assert start == "2025-01-06"  # Previous Monday
        assert end == "2025-01-12"    # Same Sunday


class TestGetLastWeek:
    """Test get_last_week function."""
    
    @patch('utils.date.datetime')
    def test_get_last_week(self, mock_datetime):
        """Test getting last week's date range."""
        # Mock current Monday, January 13, 2025
        mock_now = datetime(2025, 1, 13)  # Monday
        mock_datetime.now.return_value = mock_now
        
        start, end = get_last_week()
        
        assert start == "2025-01-06"  # Previous Monday
        assert end == "2025-01-12"    # Previous Sunday


class TestGetWeekStarting:
    """Test get_week_starting function."""
    
    def test_get_week_starting_monday(self):
        """Test with a Monday date."""
        start, end = get_week_starting("2025-01-06")  # Monday
        assert start == "2025-01-06"  # Same Monday
        assert end == "2025-01-12"    # Following Sunday
    
    def test_get_week_starting_wednesday(self):
        """Test with a Wednesday date."""
        start, end = get_week_starting("2025-01-08")  # Wednesday
        assert start == "2025-01-06"  # Previous Monday
        assert end == "2025-01-12"    # Following Sunday
    
    def test_get_week_starting_sunday(self):
        """Test with a Sunday date."""
        start, end = get_week_starting("2025-01-12")  # Sunday
        assert start == "2025-01-06"  # Previous Monday
        assert end == "2025-01-12"    # Same Sunday


class TestGetDateRange:
    """Test get_date_range function."""
    
    def test_get_date_range_positive_days(self):
        """Test with positive days (future)."""
        start, end = get_date_range("2025-01-01", 6)
        assert start == "2025-01-01"
        assert end == "2025-01-07"
    
    def test_get_date_range_negative_days(self):
        """Test with negative days (past)."""
        start, end = get_date_range("2025-01-07", -6)
        assert start == "2025-01-07"
        assert end == "2025-01-01"
    
    def test_get_date_range_zero_days(self):
        """Test with zero days."""
        start, end = get_date_range("2025-01-01", 0)
        assert start == "2025-01-01"
        assert end == "2025-01-01"
    
    def test_get_date_range_cross_month(self):
        """Test date range crossing month boundary."""
        start, end = get_date_range("2025-01-28", 7)
        assert start == "2025-01-28"
        assert end == "2025-02-04"


class TestGetMonthRange:
    """Test get_month_range function."""
    
    def test_get_month_range_january(self):
        """Test January (31 days)."""
        start, end = get_month_range(2025, 1)
        assert start == "2025-01-01"
        assert end == "2025-01-31"
    
    def test_get_month_range_february(self):
        """Test February (28 days in 2025)."""
        start, end = get_month_range(2025, 2)
        assert start == "2025-02-01"
        assert end == "2025-02-28"
    
    def test_get_month_range_february_leap_year(self):
        """Test February in leap year (29 days)."""
        start, end = get_month_range(2024, 2)  # 2024 is leap year
        assert start == "2024-02-01"
        assert end == "2024-02-29"
    
    def test_get_month_range_december(self):
        """Test December (year boundary)."""
        start, end = get_month_range(2025, 12)
        assert start == "2025-12-01"
        assert end == "2025-12-31"


class TestValidateDateFormat:
    """Test validate_date_format function."""
    
    def test_valid_date_formats(self):
        """Test various valid date formats."""
        valid_dates = [
            "2025-01-01",
            "2025-12-31",
            "2024-02-29",  # Leap year
            "2025-06-15"
        ]
        
        for date_str in valid_dates:
            assert validate_date_format(date_str), f"Should be valid: {date_str}"
    
    def test_invalid_date_formats(self):
        """Test various invalid date formats."""
        invalid_dates = [
            "25-01-01",       # Wrong year format
            "2025/01/01",     # Wrong separators
            "2025-13-01",     # Invalid month
            "2025-01-32",     # Invalid day
            "2025-02-30",     # Invalid day for February
            "not-a-date",     # Not a date
            "",               # Empty string
            "2025-01",        # Incomplete
        ]
        
        for date_str in invalid_dates:
            assert not validate_date_format(date_str), f"Should be invalid: {date_str}"


class TestGetQuarterRange:
    """Test get_quarter_range function."""
    
    def test_quarter_ranges_2025(self):
        """Test all quarters for 2025."""
        q1_start, q1_end = get_quarter_range(2025, 1)
        assert q1_start == "2025-01-01"
        assert q1_end == "2025-03-31"
        
        q2_start, q2_end = get_quarter_range(2025, 2)
        assert q2_start == "2025-04-01"
        assert q2_end == "2025-06-30"
        
        q3_start, q3_end = get_quarter_range(2025, 3)
        assert q3_start == "2025-07-01"
        assert q3_end == "2025-09-30"
        
        q4_start, q4_end = get_quarter_range(2025, 4)
        assert q4_start == "2025-10-01"
        assert q4_end == "2025-12-31"
    
    def test_quarter_range_leap_year(self):
        """Test Q1 in leap year (affects Q1 end date calculation)."""
        q1_start, q1_end = get_quarter_range(2024, 1)  # 2024 is leap year
        assert q1_start == "2024-01-01"
        assert q1_end == "2024-03-31"  # Should still be March 31


class TestParseQuarterFromDate:
    """Test parse_quarter_from_date function."""
    
    def test_parse_quarter_from_dates(self):
        """Test parsing quarter from various dates."""
        # Q1 dates
        year, quarter = parse_quarter_from_date("2025-01-15")
        assert year == 2025 and quarter == 1
        
        year, quarter = parse_quarter_from_date("2025-03-31")
        assert year == 2025 and quarter == 1
        
        # Q2 dates  
        year, quarter = parse_quarter_from_date("2025-04-01")
        assert year == 2025 and quarter == 2
        
        year, quarter = parse_quarter_from_date("2025-06-30")
        assert year == 2025 and quarter == 2
        
        # Q3 dates
        year, quarter = parse_quarter_from_date("2025-07-01") 
        assert year == 2025 and quarter == 3
        
        year, quarter = parse_quarter_from_date("2025-09-30")
        assert year == 2025 and quarter == 3
        
        # Q4 dates
        year, quarter = parse_quarter_from_date("2025-10-01")
        assert year == 2025 and quarter == 4
        
        year, quarter = parse_quarter_from_date("2025-12-31")
        assert year == 2025 and quarter == 4


@patch('utils.date.datetime')
class TestGetCurrentQuarter:
    """Test get_current_quarter function."""
    
    def test_current_quarter_q1(self, mock_datetime):
        """Test when current date is in Q1."""
        mock_now = datetime(2025, 2, 15)  # February
        mock_datetime.now.return_value = mock_now
        
        year, quarter, start, end = get_current_quarter()
        
        assert year == 2025
        assert quarter == 1  
        assert start == "2025-01-01"
        assert end == "2025-03-31"
    
    def test_current_quarter_q4(self):
        """Test when current date is in Q4."""
        with patch('utils.date.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 15)  # November
            
            year, quarter, start, end = get_current_quarter()
            
            assert year == 2025
            assert quarter == 4
            assert start == "2025-10-01"
            assert end == "2025-12-31"


# Pytest fixtures for common test data
@pytest.fixture
def sample_dates():
    """Fixture providing sample dates for testing."""
    return {
        'monday': '2025-01-06',
        'wednesday': '2025-01-08', 
        'friday': '2025-01-10',
        'sunday': '2025-01-12',
        'month_start': '2025-01-01',
        'month_end': '2025-01-31',
        'year_start': '2025-01-01',
        'year_end': '2025-12-31'
    }


@pytest.fixture  
def sample_quarters():
    """Fixture providing sample quarter data."""
    return {
        2025: {
            1: ('2025-01-01', '2025-03-31'),
            2: ('2025-04-01', '2025-06-30'),
            3: ('2025-07-01', '2025-09-30'),
            4: ('2025-10-01', '2025-12-31')
        }
    }


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
