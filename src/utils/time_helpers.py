"""
Time and Date Helper Functions

This module provides utility functions for time-related operations including
timestamp conversions, time window calculations, and date formatting.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


def get_time_window(months: int = 3) -> Tuple[datetime, datetime]:
    """
    Calculate a time window from X months ago until now.

    Args:
        months (int): Number of months to look back (default: 3)

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=months * 30)  # Approximate months as 30 days

    logger.info(f"Time window: {start_time.isoformat()} to {end_time.isoformat()}")
    logger.info(f"Duration: {months} months (~{months * 30} days)")

    return start_time, end_time


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Convert a datetime object to Unix timestamp in milliseconds.

    Args:
        dt (datetime): Datetime object to convert

    Returns:
        int: Unix timestamp in milliseconds
    """
    # Ensure the datetime is timezone-aware (UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
        logger.warning("Datetime was timezone-naive, assumed UTC")

    timestamp_ms = int(dt.timestamp() * 1000)
    logger.debug(f"Converted {dt.isoformat()} to timestamp {timestamp_ms}")
    return timestamp_ms


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Convert a Unix timestamp (in milliseconds or seconds) to datetime.

    Args:
        timestamp (int): Unix timestamp (automatically detects if seconds or milliseconds)

    Returns:
        datetime: UTC datetime object
    """
    # Detect if timestamp is in seconds or milliseconds
    # Timestamps after year 2286 would be > 10 digits in seconds
    if timestamp > 10000000000:  # Milliseconds
        dt = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    else:  # Seconds
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    logger.debug(f"Converted timestamp {timestamp} to {dt.isoformat()}")
    return dt


def parse_iso_timestamp(timestamp_str: str) -> Optional[datetime]:
    """
    Parse an ISO 8601 timestamp string to datetime.

    Args:
        timestamp_str (str): ISO 8601 formatted timestamp string

    Returns:
        Optional[datetime]: Parsed datetime object or None if parsing fails
    """
    try:
        dt = date_parser.isoparse(timestamp_str)

        # Ensure timezone-aware
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            logger.warning(f"Timestamp {timestamp_str} was timezone-naive, assumed UTC")

        logger.debug(f"Parsed timestamp: {timestamp_str} -> {dt.isoformat()}")
        return dt
    except (ValueError, TypeError) as e:
        logger.error(f"Failed to parse timestamp '{timestamp_str}': {e}")
        return None


def format_datetime(dt: datetime, format_type: str = 'iso') -> str:
    """
    Format a datetime object to a string.

    Args:
        dt (datetime): Datetime object to format
        format_type (str): Format type - 'iso', 'human', 'filename', or 'log'

    Returns:
        str: Formatted datetime string
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if format_type == 'iso':
        return dt.isoformat()
    elif format_type == 'human':
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    elif format_type == 'filename':
        return dt.strftime('%Y%m%d_%H%M%S')
    elif format_type == 'log':
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Millisecond precision
    else:
        logger.warning(f"Unknown format type '{format_type}', using ISO format")
        return dt.isoformat()


def get_date_range_days(start_time: datetime, end_time: datetime) -> int:
    """
    Calculate the number of days between two datetime objects.

    Args:
        start_time (datetime): Start datetime
        end_time (datetime): End datetime

    Returns:
        int: Number of days between the dates
    """
    delta = end_time - start_time
    days = delta.days
    logger.debug(f"Date range: {days} days from {start_time} to {end_time}")
    return days


def get_hourly_buckets(start_time: datetime, end_time: datetime) -> list:
    """
    Generate a list of hourly time buckets between start and end times.

    Args:
        start_time (datetime): Start of time range
        end_time (datetime): End of time range

    Returns:
        list: List of datetime objects representing each hour
    """
    buckets = []
    current = start_time.replace(minute=0, second=0, microsecond=0)

    while current <= end_time:
        buckets.append(current)
        current += timedelta(hours=1)

    logger.debug(f"Generated {len(buckets)} hourly buckets")
    return buckets


def get_daily_buckets(start_time: datetime, end_time: datetime) -> list:
    """
    Generate a list of daily time buckets between start and end times.

    Args:
        start_time (datetime): Start of time range
        end_time (datetime): End of time range

    Returns:
        list: List of datetime objects representing each day
    """
    buckets = []
    current = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    while current <= end_time:
        buckets.append(current)
        current += timedelta(days=1)

    logger.debug(f"Generated {len(buckets)} daily buckets")
    return buckets


def is_within_business_hours(dt: datetime, start_hour: int = 9, end_hour: int = 17) -> bool:
    """
    Check if a datetime falls within business hours.

    Args:
        dt (datetime): Datetime to check
        start_hour (int): Business hours start (default: 9 AM)
        end_hour (int): Business hours end (default: 5 PM)

    Returns:
        bool: True if within business hours, False otherwise
    """
    hour = dt.hour
    is_business_hours = start_hour <= hour < end_hour
    return is_business_hours


def calculate_retention_date(retention_days: int) -> datetime:
    """
    Calculate the date before which data should be deleted based on retention policy.

    Args:
        retention_days (int): Number of days to retain data

    Returns:
        datetime: Cutoff datetime for data retention
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    logger.info(f"Data retention cutoff date: {cutoff_date.isoformat()} ({retention_days} days)")
    return cutoff_date


def get_s3_prefix_for_date(dt: datetime, prefix_format: str = 'waf') -> str:
    """
    Generate an S3 prefix path for a given date.

    Args:
        dt (datetime): Date to generate prefix for
        prefix_format (str): Format type - 'waf' or 'custom'

    Returns:
        str: S3 prefix path

    Example:
        >>> get_s3_prefix_for_date(datetime(2024, 1, 15), 'waf')
        '2024/01/15/'
    """
    if prefix_format == 'waf':
        # WAF logs typically use YYYY/MM/DD/ format
        return dt.strftime('%Y/%m/%d/')
    else:
        return dt.strftime('%Y-%m-%d/')


def get_time_window_description(start_time: datetime, end_time: datetime) -> str:
    """
    Generate a human-readable description of a time window.

    Args:
        start_time (datetime): Start of time range
        end_time (datetime): End of time range

    Returns:
        str: Human-readable description
    """
    days = get_date_range_days(start_time, end_time)

    if days <= 1:
        return "Last 24 hours"
    elif days <= 7:
        return f"Last {days} days"
    elif days <= 31:
        return f"Last {days} days (~1 month)"
    elif days <= 93:
        return f"Last {days} days (~{days // 30} months)"
    else:
        months = days // 30
        return f"Last {days} days (~{months} months)"


def now_utc() -> datetime:
    """
    Get the current UTC datetime.

    Returns:
        datetime: Current UTC datetime
    """
    return datetime.now(timezone.utc)


def today_utc() -> datetime:
    """
    Get today's date at midnight UTC.

    Returns:
        datetime: Today at 00:00:00 UTC
    """
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_today_window() -> Tuple[datetime, datetime]:
    """
    Get time window for today (from midnight UTC to now).

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects
    """
    end_time = datetime.now(timezone.utc)
    start_time = today_utc()

    logger.info(f"Today's window: {start_time.isoformat()} to {end_time.isoformat()}")
    return start_time, end_time


def get_yesterday_window() -> Tuple[datetime, datetime]:
    """
    Get time window for yesterday (full 24 hours).

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects
    """
    today_start = today_utc()
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start - timedelta(microseconds=1)

    logger.info(f"Yesterday's window: {yesterday_start.isoformat()} to {yesterday_end.isoformat()}")
    return yesterday_start, yesterday_end


def get_past_week_window() -> Tuple[datetime, datetime]:
    """
    Get time window for the past 7 days.

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects
    """
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=7)

    logger.info(f"Past week window: {start_time.isoformat()} to {end_time.isoformat()}")
    return start_time, end_time


def get_custom_window(start_date_str: str, end_date_str: str) -> Tuple[datetime, datetime]:
    """
    Parse custom date range from user input strings.

    Args:
        start_date_str (str): Start date (formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO 8601)
        end_date_str (str): End date (formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO 8601)

    Returns:
        Tuple[datetime, datetime]: (start_time, end_time) as UTC datetime objects

    Raises:
        ValueError: If date parsing fails or end_time is before start_time
    """
    try:
        # Parse start date
        start_time = date_parser.parse(start_date_str)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
            logger.warning(f"Start date was timezone-naive, assumed UTC")

        # Parse end date
        end_time = date_parser.parse(end_date_str)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)
            logger.warning(f"End date was timezone-naive, assumed UTC")

        # Validate
        if end_time < start_time:
            raise ValueError("End date must be after start date")

        logger.info(f"Custom window: {start_time.isoformat()} to {end_time.isoformat()}")
        return start_time, end_time

    except Exception as e:
        logger.error(f"Failed to parse custom date range: {e}")
        raise ValueError(f"Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS format. Error: {e}")
