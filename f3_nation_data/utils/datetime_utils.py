"""Datetime utilities for F3 Nation data processing.

This module provides utilities for converting between Unix timestamps and
timezone-aware datetime objects, ensuring consistent datetime handling
across the library.
"""

import datetime as dt


def from_unix_timestamp(timestamp: str | float | None) -> dt.datetime | None:
    """Convert Unix timestamp to timezone-aware datetime.

    Args:
        timestamp: Unix timestamp as string or float, or None

    Returns:
        Timezone-aware datetime object, or None if input is None or invalid
    """
    if timestamp is None:
        return None

    try:
        # Convert to float if it's a string
        if isinstance(timestamp, str):
            timestamp = float(timestamp)

        # Create datetime from timestamp and make it timezone-aware (UTC)
        return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC)
    except (ValueError, TypeError, OSError):
        return None


def to_unix_timestamp(dt_obj: dt.datetime | None) -> float | None:
    """Convert timezone-aware datetime to Unix timestamp.

    Args:
        dt_obj: Timezone-aware datetime object, or None

    Returns:
        Unix timestamp as float, or None if input is None
    """
    if dt_obj is None:
        return None

    if dt_obj.tzinfo is None:
        msg = 'datetime object must be timezone-aware'
        raise ValueError(msg)

    return dt_obj.timestamp()


def ensure_timezone_aware(dt_obj: dt.datetime) -> dt.datetime:
    """Ensure a datetime object is timezone-aware, defaulting to UTC.

    Args:
        dt_obj: Datetime object that may or may not be timezone-aware

    Returns:
        Timezone-aware datetime object
    """
    if dt_obj.tzinfo is None:
        return dt_obj.replace(tzinfo=dt.UTC)
    return dt_obj
