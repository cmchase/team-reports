#!/usr/bin/env python3
"""
Batch Processing Utilities

Shared utilities for batch report generation across different data sources.
Provides date manipulation, week calculation, and batch processing helpers.
"""

import datetime
import re
from typing import List, Tuple, Optional


def get_monday(date_str: str) -> str:
    """
    Calculate the Monday of the week containing the given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        str: Monday of that week in YYYY-MM-DD format
        
    Examples:
        >>> get_monday("2025-10-08")  # Wednesday
        "2025-10-06"  # Monday
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        days_since_monday = date_obj.weekday()  # Monday=0, Sunday=6
        monday = date_obj - datetime.timedelta(days=days_since_monday)
        return monday.strftime("%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD: {e}")


def add_days(date_str: str, days: int) -> str:
    """
    Add a number of days to a date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        days: Number of days to add (can be negative)
        
    Returns:
        str: New date in YYYY-MM-DD format
        
    Examples:
        >>> add_days("2025-10-06", 7)
        "2025-10-13"
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        new_date = date_obj + datetime.timedelta(days=days)
        return new_date.strftime("%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Invalid date format '{date_str}'. Expected YYYY-MM-DD: {e}")


def add_weeks(date_str: str, weeks: int) -> str:
    """
    Add a number of weeks to a date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        weeks: Number of weeks to add (can be negative)
        
    Returns:
        str: New date in YYYY-MM-DD format
        
    Examples:
        >>> add_weeks("2025-10-06", 2)
        "2025-10-20"
    """
    return add_days(date_str, weeks * 7)


def validate_date_format(date_str: str) -> bool:
    """
    Validate that a string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Examples:
        >>> validate_date_format("2025-10-06")
        True
        >>> validate_date_format("2025-13-01")
        False
    """
    pattern = r'^\d{4}-\d{2}-\d{2}$'
    if not re.match(pattern, date_str):
        return False
    
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def generate_weekly_date_ranges(start_date: str, end_date: str) -> List[Tuple[str, str]]:
    """
    Generate a list of weekly date ranges (Monday to Sunday) between two dates.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of tuples (start_week, end_week) for each week
        
    Examples:
        >>> generate_weekly_date_ranges("2025-10-01", "2025-10-15")
        [("2025-09-29", "2025-10-05"), ("2025-10-06", "2025-10-12"), ("2025-10-13", "2025-10-19")]
    """
    if not validate_date_format(start_date) or not validate_date_format(end_date):
        raise ValueError("Both dates must be in YYYY-MM-DD format")
        
    if start_date > end_date:
        raise ValueError("Start date must be before or equal to end date")
    
    ranges = []
    current_monday = get_monday(start_date)
    end_monday = get_monday(end_date)
    
    while current_monday <= end_monday:
        week_end = add_days(current_monday, 6)  # Sunday
        ranges.append((current_monday, week_end))
        current_monday = add_weeks(current_monday, 1)
    
    return ranges


def generate_last_n_weeks_ranges(n: int, reference_date: Optional[str] = None) -> List[Tuple[str, str]]:
    """
    Generate date ranges for the last N weeks (excluding current week).
    
    Args:
        n: Number of weeks to generate
        reference_date: Reference date (default: today)
        
    Returns:
        List of tuples (start_week, end_week) for each week
        
    Examples:
        >>> generate_last_n_weeks_ranges(2, "2025-10-08")
        [("2025-09-23", "2025-09-29"), ("2025-09-30", "2025-10-06")]
    """
    if n < 1:
        raise ValueError("Number of weeks must be positive")
        
    if reference_date is None:
        reference_date = datetime.date.today().strftime("%Y-%m-%d")
    elif not validate_date_format(reference_date):
        raise ValueError("Reference date must be in YYYY-MM-DD format")
    
    # Start from N weeks ago, ending at the start of current week
    # For "last 2 weeks" from Wed Oct 8, we want:
    # Week 1 ago: Sep 30 - Oct 6 (Monday before current week)  
    # Week 2 ago: Sep 23 - Sep 29 (Monday before that)
    current_monday = get_monday(reference_date)
    last_week_monday = add_weeks(current_monday, -1)  # Start of last week
    start_monday = add_weeks(last_week_monday, -(n - 1))  # N weeks before last week
    
    # Generate ranges from start_monday for N weeks
    end_date = add_days(add_weeks(start_monday, n - 1), 6)  # Last Sunday
    
    return generate_weekly_date_ranges(start_monday, end_date)


def generate_n_weeks_from_date_ranges(start_date: str, n: int) -> List[Tuple[str, str]]:
    """
    Generate N weekly date ranges starting from a given date.
    
    Args:
        start_date: Starting date in YYYY-MM-DD format
        n: Number of weeks to generate
        
    Returns:
        List of tuples (start_week, end_week) for each week
        
    Examples:
        >>> generate_n_weeks_from_date_ranges("2025-10-01", 3)
        [("2025-09-29", "2025-10-05"), ("2025-10-06", "2025-10-12"), ("2025-10-13", "2025-10-19")]
    """
    if n < 1:
        raise ValueError("Number of weeks must be positive")
        
    if not validate_date_format(start_date):
        raise ValueError("Start date must be in YYYY-MM-DD format")
    
    start_monday = get_monday(start_date)
    end_date = add_weeks(start_monday, n - 1)
    week_end = add_days(end_date, 6)
    
    return generate_weekly_date_ranges(start_monday, week_end)


def parse_batch_arguments(args: List[str]) -> dict:
    """
    Parse batch processing arguments into structured format.
    
    Args:
        args: List of command line arguments
        
    Returns:
        dict: Parsed arguments with 'mode', 'params', and 'config_file'
        
    Examples:
        >>> parse_batch_arguments(['last-4'])
        {'mode': 'last_n', 'params': {'n': 4}, 'config_file': None}
        
        >>> parse_batch_arguments(['2025-10-01:3', 'config/custom.yaml'])
        {'mode': 'n_from_date', 'params': {'start_date': '2025-10-01', 'n': 3}, 'config_file': 'config/custom.yaml'}
    """
    result = {'mode': None, 'params': {}, 'config_file': None}
    
    # Extract config file if present (ends with .yaml)
    config_args = [arg for arg in args if arg.endswith('.yaml')]
    non_config_args = [arg for arg in args if not arg.endswith('.yaml')]
    
    if config_args:
        result['config_file'] = config_args[0]
    
    if not non_config_args:
        raise ValueError("No batch arguments provided")
    
    first_arg = non_config_args[0]
    
    # Pattern: last-N
    if first_arg.startswith('last-'):
        n_str = first_arg[5:]  # Remove 'last-' prefix
        if not n_str.isdigit() or int(n_str) < 1:
            raise ValueError(f"Invalid format '{first_arg}'. Use 'last-N' where N is a positive number")
        result['mode'] = 'last_n'
        result['params']['n'] = int(n_str)
    
    # Pattern: YYYY-MM-DD:N
    elif ':' in first_arg:
        parts = first_arg.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid format '{first_arg}'. Use 'YYYY-MM-DD:N'")
        
        start_date, n_str = parts
        if not validate_date_format(start_date):
            raise ValueError(f"Invalid date format '{start_date}'. Use YYYY-MM-DD")
        if not n_str.isdigit() or int(n_str) < 1:
            raise ValueError(f"Invalid week count '{n_str}'. Must be a positive number")
            
        result['mode'] = 'n_from_date'
        result['params']['start_date'] = start_date
        result['params']['n'] = int(n_str)
    
    # Pattern: YYYY-MM-DD to YYYY-MM-DD
    elif len(non_config_args) >= 3 and non_config_args[1] == 'to':
        start_date = non_config_args[0]
        end_date = non_config_args[2]
        
        if not validate_date_format(start_date):
            raise ValueError(f"Invalid start date format '{start_date}'. Use YYYY-MM-DD")
        if not validate_date_format(end_date):
            raise ValueError(f"Invalid end date format '{end_date}'. Use YYYY-MM-DD")
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")
            
        result['mode'] = 'date_range'
        result['params']['start_date'] = start_date
        result['params']['end_date'] = end_date
    
    else:
        raise ValueError(f"Invalid argument format '{first_arg}'. Use 'last-N', 'YYYY-MM-DD:N', or 'YYYY-MM-DD to YYYY-MM-DD'")
    
    return result
