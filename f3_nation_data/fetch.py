"""Data fetching utilities from SQL database.

This module provides functions to query and fetch F3 data from SQL databases,
with support for incremental syncing and time-based filtering.
"""

from datetime import datetime, timedelta

import sqlalchemy as sa
from sqlalchemy.orm import Session

from f3_nation_data.models.sql.ao import SqlAOModel
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel
from f3_nation_data.models.sql.user import SqlUserModel
from f3_nation_data.utils.datetime_utils import to_unix_timestamp


def _validate_datetime_tz_aware(dt: datetime) -> None:
    """Validate that a datetime object is timezone-aware.

    Args:
        dt: Datetime object to validate

    Raises:
        ValueError: If the datetime object is not timezone-aware
    """
    if dt.tzinfo is None:
        msg = 'datetime object must be timezone-aware'
        raise ValueError(msg)


def fetch_sql_beatdowns(
    session: Session,
    after_timestamp: datetime | None = None,
) -> list[SqlBeatDownModel]:
    """Fetch BeatDown data from the SQL database.

    Only fetches the essential fields: timestamp, ts_edited, backblast, and json.
    Optionally filter by timestamp for incremental syncing.

    Args:
        session: SQLAlchemy Session for the query.
        after_timestamp: If provided, only fetch BeatDowns with timestamp
            greater than this value, or with ts_edited greater than this value.
            Must be a timezone-aware datetime object.

    Returns:
        List of SqlBeatDownModel instances with essential data.
    """
    query = sa.select(SqlBeatDownModel)

    if after_timestamp:
        _validate_datetime_tz_aware(after_timestamp)
        after_timestamp_str = str(to_unix_timestamp(after_timestamp))
        query = query.where(
            (SqlBeatDownModel.timestamp > after_timestamp_str)
            | ((SqlBeatDownModel.ts_edited.is_not(None)) & (SqlBeatDownModel.ts_edited > after_timestamp_str)),
        )

    result = session.execute(query)
    return list(result.scalars().unique().all())


def fetch_beatdowns_for_week(
    session: Session,
    date_in_week: datetime,
) -> list[SqlBeatDownModel]:
    """Fetch all beatdowns that occurred within the week containing the given date.

    Automatically calculates the Monday-to-Sunday week boundaries regardless
    of what day of the week the input date falls on.

    Args:
        session: SQLAlchemy Session for the query.
        date_in_week: Any date within the desired week. The function will
            calculate the full week (Monday to Sunday) containing this date.
            Must be a timezone-aware datetime object.

    Returns:
        List of SqlBeatDownModel instances for the week containing the given date.
    """
    _validate_datetime_tz_aware(date_in_week)

    # Calculate the Monday of the week containing the given date
    # weekday() returns 0=Monday, 1=Tuesday, etc.
    days_since_monday = date_in_week.weekday()
    week_start = date_in_week.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    ) - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=7)

    return fetch_beatdowns_for_date_range(session, week_start, week_end)


def fetch_beatdowns_for_date_range(
    session: Session,
    start_date: datetime,
    end_date: datetime,
) -> list[SqlBeatDownModel]:
    """Fetch all beatdowns within a specific date range.

    Args:
        session: SQLAlchemy Session for the query.
        start_date: Start of the date range (inclusive). Must be timezone-aware.
        end_date: End of the date range (exclusive). Must be timezone-aware.

    Returns:
        List of SqlBeatDownModel instances within the date range.
    """
    _validate_datetime_tz_aware(start_date)
    _validate_datetime_tz_aware(end_date)

    # Convert datetime objects to Unix timestamps (as strings) to match database format
    start_timestamp = str(to_unix_timestamp(start_date))
    end_timestamp = str(to_unix_timestamp(end_date))

    query = sa.select(SqlBeatDownModel).where(
        (SqlBeatDownModel.timestamp >= start_timestamp) & (SqlBeatDownModel.timestamp < end_timestamp),
    )

    result = session.execute(query)
    return list(result.scalars().all())


def fetch_sql_users(
    session: Session,
    user_ids: list[str] | None = None,
) -> list[SqlUserModel]:
    """Fetch User data from the SQL database.

    Args:
        session: SQLAlchemy Session for the query.
        user_ids: If provided, only fetch users with these IDs.

    Returns:
        List of SqlUserModel instances.
    """
    query = sa.select(SqlUserModel)

    if user_ids:
        query = query.where(SqlUserModel.user_id.in_(user_ids))

    result = session.execute(query)
    return list(result.scalars().all())


def fetch_sql_aos(
    session: Session,
    channel_ids: list[str] | None = None,
) -> list[SqlAOModel]:
    """Fetch AO (Area of Operations) data from the SQL database.

    Args:
        session: SQLAlchemy Session for the query.
        channel_ids: If provided, only fetch AOs with these channel IDs.

    Returns:
        List of SqlAOModel instances.
    """
    query = sa.select(SqlAOModel)

    if channel_ids:
        query = query.where(SqlAOModel.channel_id.in_(channel_ids))

    result = session.execute(query)
    return list(result.scalars().all())
