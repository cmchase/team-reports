#!/usr/bin/env python3
"""
Date utilities for parsing command line arguments and calculating date ranges.

This module provides reusable functions for handling dates in report generation,
including parsing command line arguments and calculating common date ranges.
"""

import sys
from datetime import datetime, timedelta
from typing import Tuple, Optional


def parse_date_args(args: Optional[list] = None) -> Tuple[str, str]:
    """
    Parse command line date arguments or calculate current week dates.
    
    Args:
        args: Optional list of command line arguments. If None, uses sys.argv
        
    Returns:
        Tuple[str, str]: (start_date, end_date) in YYYY-MM-DD format
        
    Parsing Logic:
        - 2+ args: start_date, end_date
        - 1 arg: start_date, calculate end_date as +6 days
        - 0 args: current week (Monday to Sunday)
        
    Examples:
        parse_date_args(["2025-01-01", "2025-01-07"])  # Returns ("2025-01-01", "2025-01-07")
        parse_date_args(["2025-01-01"])                # Returns ("2025-01-01", "2025-01-07")
        parse_date_args([])                            # Returns current week dates
    """
    if args is None:
        args = sys.argv[1:]  # Skip script name
        
    if len(args) >= 2:
        start_date = args[0]
        end_date = args[1]
    elif len(args) == 1:
        # Single date provided, assume it's the start of the week
        start_date = args[0]
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime('%Y-%m-%d')
    else:
        # No dates provided, use current week (Monday to Sunday)
        start_date, end_date = get_current_week()
        
    return start_date, end_date


def get_current_week() -> Tuple[str, str]:
    """
    Get the current week's Monday to Sunday date range.
    
    Returns:
        Tuple[str, str]: (monday_date, sunday_date) in YYYY-MM-DD format
        
    Example:
        monday, sunday = get_current_week()
        # Returns something like ("2025-01-06", "2025-01-12")
    """
    today = datetime.now()
    days_since_monday = today.weekday()
    monday = today - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')


def get_last_week() -> Tuple[str, str]:
    """
    Get last week's Monday to Sunday date range.
    
    Returns:
        Tuple[str, str]: (monday_date, sunday_date) in YYYY-MM-DD format
    """
    today = datetime.now()
    days_since_monday = today.weekday()
    last_monday = today - timedelta(days=days_since_monday + 7)
    last_sunday = last_monday + timedelta(days=6)
    return last_monday.strftime('%Y-%m-%d'), last_sunday.strftime('%Y-%m-%d')


def get_week_starting(date_str: str) -> Tuple[str, str]:
    """
    Get the week (Monday to Sunday) that contains the given date.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Tuple[str, str]: (monday_date, sunday_date) in YYYY-MM-DD format
        
    Example:
        monday, sunday = get_week_starting("2025-01-08")  # Wednesday
        # Returns ("2025-01-06", "2025-01-12")  # Monday to Sunday of that week
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    days_since_monday = date_obj.weekday()
    monday = date_obj - timedelta(days=days_since_monday)
    sunday = monday + timedelta(days=6)
    return monday.strftime('%Y-%m-%d'), sunday.strftime('%Y-%m-%d')


def get_date_range(start_date: str, days: int) -> Tuple[str, str]:
    """
    Get a date range starting from a given date.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        days: Number of days to add (can be negative for past dates)
        
    Returns:
        Tuple[str, str]: (start_date, end_date) in YYYY-MM-DD format
        
    Example:
        start, end = get_date_range("2025-01-01", 6)
        # Returns ("2025-01-01", "2025-01-07")
    """
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = start_dt + timedelta(days=days)
    return start_date, end_dt.strftime('%Y-%m-%d')


def get_month_range(year: int, month: int) -> Tuple[str, str]:
    """
    Get the first and last day of a given month.
    
    Args:
        year: Year (e.g., 2025)
        month: Month number (1-12)
        
    Returns:
        Tuple[str, str]: (first_day, last_day) in YYYY-MM-DD format
        
    Example:
        start, end = get_month_range(2025, 1)
        # Returns ("2025-01-01", "2025-01-31")
    """
    first_day = datetime(year, month, 1)
    
    # Calculate last day of month
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')


def format_date_for_display(date_str: str, format_type: str = "readable") -> str:
    """
    Format a date string for display purposes.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        format_type: "readable" for human-friendly, "compact" for short format
        
    Returns:
        str: Formatted date string
        
    Examples:
        format_date_for_display("2025-01-15", "readable")  # "January 15, 2025"
        format_date_for_display("2025-01-15", "compact")   # "Jan 15"
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    if format_type == "readable":
        return date_obj.strftime('%B %d, %Y')
    elif format_type == "compact":
        return date_obj.strftime('%b %d')
    else:
        return date_str  # Return original if unknown format


def validate_date_format(date_str: str) -> bool:
    """
    Validate that a date string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
        
    Returns:
        bool: True if valid, False otherwise
        
    Example:
        validate_date_format("2025-01-15")  # True
        validate_date_format("01/15/2025")  # False
    """
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def get_quarter_range(year: int, quarter: int) -> Tuple[str, str]:
    """
    Get the first and last day of a given quarter.
    
    Args:
        year: Year (e.g., 2025)
        quarter: Quarter number (1-4)
        
    Returns:
        Tuple[str, str]: (first_day, last_day) in YYYY-MM-DD format
        
    Example:
        start, end = get_quarter_range(2025, 1)
        # Returns ("2025-01-01", "2025-03-31")
    """
    if quarter not in [1, 2, 3, 4]:
        raise ValueError("Quarter must be 1, 2, 3, or 4")
    
    quarter_months = {
        1: (1, 3),   # Q1: Jan-Mar
        2: (4, 6),   # Q2: Apr-Jun  
        3: (7, 9),   # Q3: Jul-Sep
        4: (10, 12)  # Q4: Oct-Dec
    }
    
    start_month, end_month = quarter_months[quarter]
    start_date = datetime(year, start_month, 1)
    
    # Get last day of end_month
    if end_month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, end_month + 1, 1) - timedelta(days=1)
    
    return start_date.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')


def get_current_quarter() -> Tuple[int, int, str, str]:
    """
    Get the current quarter information.
    
    Returns:
        Tuple[int, int, str, str]: (year, quarter, start_date, end_date)
        
    Example:
        year, quarter, start, end = get_current_quarter()
        # Returns (2025, 4, "2025-10-01", "2025-12-31") for October 2025
    """
    today = datetime.now()
    year = today.year
    month = today.month
    
    if month <= 3:
        quarter = 1
    elif month <= 6:
        quarter = 2
    elif month <= 9:
        quarter = 3
    else:
        quarter = 4
    
    start_date, end_date = get_quarter_range(year, quarter)
    return year, quarter, start_date, end_date


def parse_quarter_from_date(date_str: str) -> Tuple[int, int]:
    """
    Determine which quarter a date falls into.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        
    Returns:
        Tuple[int, int]: (year, quarter)
        
    Example:
        year, quarter = parse_quarter_from_date("2025-10-15")
        # Returns (2025, 4)
    """
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    year = date_obj.year
    month = date_obj.month
    
    if month <= 3:
        quarter = 1
    elif month <= 6:
        quarter = 2
    elif month <= 9:
        quarter = 3
    else:
        quarter = 4
    
    return year, quarter
