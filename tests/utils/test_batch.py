"""
Unit tests for batch processing utilities.

Tests date manipulation, batch argument parsing, and weekly range generation
for multi-week report generation workflows.
"""

import pytest
from datetime import date, timedelta
from team_reports.utils.batch import (
    get_monday, add_days, add_weeks, validate_date_format,
    generate_weekly_date_ranges, generate_last_n_weeks_ranges,
    generate_n_weeks_from_date_ranges, parse_batch_arguments
)


class TestDateManipulation:
    """Test date manipulation functions"""
    
    def test_get_monday_from_monday(self):
        """Test getting Monday when date is already Monday"""
        result = get_monday("2025-10-06")  # Monday
        assert result == "2025-10-06"
    
    def test_get_monday_from_wednesday(self):
        """Test getting Monday from Wednesday"""
        result = get_monday("2025-10-08")  # Wednesday
        assert result == "2025-10-06"  # Previous Monday
    
    def test_get_monday_from_sunday(self):
        """Test getting Monday from Sunday"""
        result = get_monday("2025-10-12")  # Sunday
        assert result == "2025-10-06"  # Monday of same week
    
    def test_get_monday_invalid_date(self):
        """Test error handling for invalid date"""
        with pytest.raises(ValueError, match="Invalid date format"):
            get_monday("invalid-date")
    
    def test_add_days_positive(self):
        """Test adding positive days"""
        result = add_days("2025-10-06", 7)
        assert result == "2025-10-13"
    
    def test_add_days_negative(self):
        """Test adding negative days (subtraction)"""
        result = add_days("2025-10-13", -7)
        assert result == "2025-10-06"
    
    def test_add_days_zero(self):
        """Test adding zero days"""
        result = add_days("2025-10-06", 0)
        assert result == "2025-10-06"
    
    def test_add_weeks_positive(self):
        """Test adding positive weeks"""
        result = add_weeks("2025-10-06", 2)
        assert result == "2025-10-20"
    
    def test_add_weeks_negative(self):
        """Test adding negative weeks (subtraction)"""
        result = add_weeks("2025-10-20", -2)
        assert result == "2025-10-06"


class TestDateValidation:
    """Test date format validation"""
    
    def test_valid_date_formats(self):
        """Test various valid date formats"""
        valid_dates = [
            "2025-01-01",
            "2025-12-31",
            "2025-02-28",
            "2024-02-29"  # Leap year
        ]
        for date_str in valid_dates:
            assert validate_date_format(date_str), f"Should be valid: {date_str}"
    
    def test_invalid_date_formats(self):
        """Test various invalid date formats"""
        invalid_dates = [
            "2025-13-01",  # Invalid month
            "2025-02-30",  # Invalid day for February
            "25-10-06",    # Wrong year format
            "2025/10/06",  # Wrong separators
            "2025-10-6",   # Missing leading zero
            "not-a-date",  # Not a date
            ""             # Empty string
        ]
        for date_str in invalid_dates:
            assert not validate_date_format(date_str), f"Should be invalid: {date_str}"


class TestWeeklyRangeGeneration:
    """Test weekly date range generation functions"""
    
    def test_generate_weekly_date_ranges_single_week(self):
        """Test generating ranges within a single week"""
        ranges = generate_weekly_date_ranges("2025-10-06", "2025-10-12")
        expected = [("2025-10-06", "2025-10-12")]
        assert ranges == expected
    
    def test_generate_weekly_date_ranges_multiple_weeks(self):
        """Test generating ranges across multiple weeks"""
        ranges = generate_weekly_date_ranges("2025-10-01", "2025-10-15")
        expected = [
            ("2025-09-29", "2025-10-05"),  # Week containing Oct 1
            ("2025-10-06", "2025-10-12"),  # Next week
            ("2025-10-13", "2025-10-19")   # Week containing Oct 15
        ]
        assert ranges == expected
    
    def test_generate_weekly_date_ranges_invalid_order(self):
        """Test error when start date is after end date"""
        with pytest.raises(ValueError, match="Start date must be before or equal"):
            generate_weekly_date_ranges("2025-10-15", "2025-10-01")
    
    def test_generate_last_n_weeks_ranges(self):
        """Test generating last N weeks from reference date"""
        # Using a fixed reference date for predictable testing
        # Reference: 2025-10-08 (Wednesday)
        # Current week: 2025-10-06 (Mon) to 2025-10-12 (Sun)
        # Last week: 2025-09-29 (Mon) to 2025-10-05 (Sun)  
        # 2 weeks ago: 2025-09-22 (Mon) to 2025-09-28 (Sun)
        ranges = generate_last_n_weeks_ranges(2, "2025-10-08")  # Wednesday
        expected = [
            ("2025-09-22", "2025-09-28"),  # Week 2 ago
            ("2025-09-29", "2025-10-05")   # Week 1 ago  
        ]
        assert ranges == expected
    
    def test_generate_last_n_weeks_ranges_invalid_n(self):
        """Test error for invalid week count"""
        with pytest.raises(ValueError, match="Number of weeks must be positive"):
            generate_last_n_weeks_ranges(0)
    
    def test_generate_n_weeks_from_date_ranges(self):
        """Test generating N weeks starting from a date"""
        ranges = generate_n_weeks_from_date_ranges("2025-10-01", 3)
        expected = [
            ("2025-09-29", "2025-10-05"),  # Week containing Oct 1
            ("2025-10-06", "2025-10-12"),  # Week 2
            ("2025-10-13", "2025-10-19")   # Week 3
        ]
        assert ranges == expected


class TestBatchArgumentParsing:
    """Test parsing of batch command line arguments"""
    
    def test_parse_last_n_weeks(self):
        """Test parsing 'last-N' format"""
        result = parse_batch_arguments(['last-4'])
        expected = {
            'mode': 'last_n',
            'params': {'n': 4},
            'config_file': None
        }
        assert result == expected
    
    def test_parse_last_n_weeks_with_config(self):
        """Test parsing 'last-N' with config file"""
        result = parse_batch_arguments(['last-3', 'config/custom.yaml'])
        expected = {
            'mode': 'last_n',
            'params': {'n': 3},
            'config_file': 'config/custom.yaml'
        }
        assert result == expected
    
    def test_parse_n_from_date(self):
        """Test parsing 'YYYY-MM-DD:N' format"""
        result = parse_batch_arguments(['2025-10-01:5'])
        expected = {
            'mode': 'n_from_date',
            'params': {'start_date': '2025-10-01', 'n': 5},
            'config_file': None
        }
        assert result == expected
    
    def test_parse_date_range(self):
        """Test parsing 'YYYY-MM-DD to YYYY-MM-DD' format"""
        result = parse_batch_arguments(['2025-10-01', 'to', '2025-10-15'])
        expected = {
            'mode': 'date_range',
            'params': {'start_date': '2025-10-01', 'end_date': '2025-10-15'},
            'config_file': None
        }
        assert result == expected
    
    def test_parse_date_range_with_config(self):
        """Test parsing date range with config file"""
        result = parse_batch_arguments(['2025-10-01', 'to', '2025-10-15', 'config/test.yaml'])
        expected = {
            'mode': 'date_range',
            'params': {'start_date': '2025-10-01', 'end_date': '2025-10-15'},
            'config_file': 'config/test.yaml'
        }
        assert result == expected
    
    def test_parse_invalid_last_format(self):
        """Test error for invalid 'last-N' format"""
        with pytest.raises(ValueError, match="Invalid format 'last-abc'"):
            parse_batch_arguments(['last-abc'])
        
        with pytest.raises(ValueError, match="Invalid format 'last-0'"):
            parse_batch_arguments(['last-0'])
    
    def test_parse_invalid_n_from_date_format(self):
        """Test error for invalid 'YYYY-MM-DD:N' format"""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_batch_arguments(['invalid-date:3'])
        
        with pytest.raises(ValueError, match="Invalid week count"):
            parse_batch_arguments(['2025-10-01:0'])
    
    def test_parse_invalid_date_range(self):
        """Test error for invalid date range"""
        with pytest.raises(ValueError, match="Start date must be before or equal"):
            parse_batch_arguments(['2025-10-15', 'to', '2025-10-01'])
    
    def test_parse_no_arguments(self):
        """Test error when no arguments provided"""
        with pytest.raises(ValueError, match="No batch arguments provided"):
            parse_batch_arguments([])
    
    def test_parse_unknown_format(self):
        """Test error for unknown argument format"""
        with pytest.raises(ValueError, match="Invalid argument format"):
            parse_batch_arguments(['unknown-format'])


class TestIntegration:
    """Integration tests combining multiple functions"""
    
    def test_full_workflow_last_weeks(self):
        """Test complete workflow for generating last N weeks"""
        # Parse arguments
        parsed = parse_batch_arguments(['last-2'])
        assert parsed['mode'] == 'last_n'
        
        # Generate ranges (using fixed reference date)
        ranges = generate_last_n_weeks_ranges(
            parsed['params']['n'], 
            "2025-10-08"
        )
        
        # Verify we get 2 weeks of Monday-Sunday ranges
        assert len(ranges) == 2
        for start, end in ranges:
            # Verify each range is Monday to Sunday
            assert get_monday(start) == start
            assert add_days(start, 6) == end
    
    def test_full_workflow_n_from_date(self):
        """Test complete workflow for N weeks from date"""
        # Parse arguments  
        parsed = parse_batch_arguments(['2025-10-01:3'])
        assert parsed['mode'] == 'n_from_date'
        
        # Generate ranges
        ranges = generate_n_weeks_from_date_ranges(
            parsed['params']['start_date'],
            parsed['params']['n']
        )
        
        # Verify we get 3 consecutive weeks
        assert len(ranges) == 3
        
        # Verify weeks are consecutive
        for i in range(len(ranges) - 1):
            current_end = ranges[i][1]
            next_start = ranges[i + 1][0]
            # Next week should start the day after current week ends
            assert add_days(current_end, 1) == next_start
