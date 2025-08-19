"""Analytics and metrics engine for F3 Nation data.

This module provides analytics functions for beatdown data, including:
- PAX attendance analysis
- AO performance metrics
- Q leadership statistics
- FNG tracking
- Weekly/monthly summaries
"""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel

from .fetch import fetch_sql_aos, fetch_sql_users
from .models.parsed.beatdown import ParsedBeatdown
from .models.sql.beatdown import SqlBeatDownModel
from .parsing.backblast import transform_sql_to_parsed_beatdown

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class HighestAttendanceResult(BaseModel):
    """Result model for highest attendance analysis per AO."""

    attendance_count: int
    q_names: list[str]
    date: str
    title: str


class WeeklySummary(BaseModel):
    """Result model for weekly summary statistics."""

    total_beatdowns: int
    total_attendance: int
    unique_pax: int
    pax_counts: dict[str, int]
    ao_counts: dict[str, int]
    q_counts: dict[str, int]
    ao_fngs: dict[str, list[str]]
    ao_max_attendance: dict[str, HighestAttendanceResult]
    top_pax: list[tuple[str, int]]
    top_aos: list[tuple[str, int]]
    top_qs: list[tuple[str, int]]


class BeatdownDetails(BaseModel):
    """Result model for beatdown detail information."""

    timestamp: str | None
    ao_name: str
    q_name: str
    title: str
    date: str | None
    pax_count: int
    pax_names: list[str]
    fng_names: list[str]
    workout_type: str
    word_count: int


def get_user_mapping(session: 'Session') -> dict[str, str]:
    """Get mapping of user IDs to display names.

    Args:
        session: SQLAlchemy session for database queries

    Returns:
        Dictionary mapping user ID to display name (F3 name or real name)
    """
    user_mapping = {}
    users = fetch_sql_users(session)
    for user in users:
        # Prefer F3 name (user_name), fall back to real_name, then user_id
        display_name = user.user_name or user.real_name or user.user_id
        user_mapping[user.user_id] = display_name
    return user_mapping


def get_ao_mapping(session: 'Session') -> dict[str, str]:
    """Get mapping of channel IDs to AO names.

    Args:
        session: SQLAlchemy session for database queries

    Returns:
        Dictionary mapping channel ID to AO name
    """
    ao_mapping = {}
    aos = fetch_sql_aos(session)
    for ao in aos:
        ao_mapping[ao.channel_id] = ao.ao
    return ao_mapping


def analyze_pax_attendance(
    parsed_beatdowns: list[ParsedBeatdown],
) -> dict[str, int]:
    """Analyze PAX attendance counts from parsed beatdowns."""
    pax_counts = Counter()
    for parsed in parsed_beatdowns:
        # Gather all PAX, Q, and Co-Qs for attendance
        all_posters = set(parsed.pax or [])
        if parsed.q_user_id:
            all_posters.add(parsed.q_user_id)
        if parsed.coq_user_id:
            all_posters.update(parsed.coq_user_id)
        for pax_id in all_posters:
            pax_counts[pax_id] += 1
    return dict(pax_counts)


def analyze_ao_attendance(
    parsed_beatdowns: list[ParsedBeatdown],
    ao_mapping: dict[str, str],
) -> dict[str, int]:
    """Analyze unique PAX attendance by AO from parsed beatdowns."""
    ao_unique_pax = defaultdict(set)
    for parsed in parsed_beatdowns:
        ao_name = ao_mapping.get(parsed.ao_id, parsed.ao_id)
        if parsed.pax:
            ao_unique_pax[ao_name].update(parsed.pax)
    return {ao_name: len(pax_set) for ao_name, pax_set in ao_unique_pax.items()}


def analyze_q_counts(
    parsed_beatdowns: list,
    user_mapping: dict[str, str],
) -> dict[str, int]:
    """Analyze Q (leadership) counts from parsed beatdowns."""
    q_counts = Counter()
    for parsed in parsed_beatdowns:
        # Count main Q
        if parsed.q_user_id:
            q_name = user_mapping.get(parsed.q_user_id, parsed.q_user_id)
            q_counts[q_name] += 1
        # Count Co-Qs
        if parsed.coq_user_id:
            for coq_id in parsed.coq_user_id:
                coq_name = user_mapping.get(coq_id, coq_id)
                q_counts[coq_name] += 1
    return dict(q_counts)


def analyze_fngs_by_ao(
    parsed_beatdowns: list[ParsedBeatdown],
    ao_mapping: dict[str, str],
) -> dict[str, list[str]]:
    """Analyze FNGs (First Name Guys) by AO from parsed beatdowns."""
    ao_fngs = defaultdict(list)
    for parsed in parsed_beatdowns:
        ao_name = ao_mapping.get(parsed.ao_id, parsed.ao_id)
        if parsed.fngs:
            # Remove '@' prefix from FNG names - some backblasts may include it
            ao_fngs[ao_name].extend(
                [fng.removeprefix('@') for fng in parsed.fngs],
            )
    return dict(ao_fngs)


def analyze_highest_attendance_per_ao(
    parsed_beatdowns: list[ParsedBeatdown],
    ao_mapping: dict[str, str],
    user_mapping: dict[str, str],
) -> dict[str, HighestAttendanceResult]:
    """Find the highest attended beatdown per AO from parsed beatdowns."""
    ao_max_attendance = {}
    for parsed in parsed_beatdowns:
        ao_name = ao_mapping.get(parsed.ao_id, parsed.ao_id)
        pax_count = parsed.pax_count or 0
        all_qs = [parsed.q_user_id] + (parsed.coq_user_id or [])
        q_names = [_get_q_display_name(q_user_id, user_mapping) for q_user_id in all_qs]
        date_str = _format_beatdown_date(parsed.bd_date)
        title = parsed.title or 'Untitled Beatdown'
        if ao_name not in ao_max_attendance or pax_count > ao_max_attendance[ao_name].attendance_count:
            ao_max_attendance[ao_name] = HighestAttendanceResult(
                attendance_count=pax_count,
                q_names=q_names,
                date=date_str,
                title=title,
            )
    return ao_max_attendance


def get_weekly_summary(
    beatdowns: list[SqlBeatDownModel],
    user_mapping: dict[str, str],
    ao_mapping: dict[str, str],
) -> WeeklySummary:
    """Get comprehensive weekly summary statistics.

    Args:
        beatdowns: List of beatdown models
        user_mapping: Dictionary mapping user ID to display name
        ao_mapping: Dictionary mapping channel ID to AO name
    Returns:
        Dictionary with summary statistics
    """
    # Parse all beatdowns once
    parsed_beatdowns = [transform_sql_to_parsed_beatdown(bd) for bd in beatdowns]
    pax_counts = analyze_pax_attendance(parsed_beatdowns)
    ao_counts = analyze_ao_attendance(parsed_beatdowns, ao_mapping)
    q_counts = analyze_q_counts(parsed_beatdowns, user_mapping)
    ao_fngs = analyze_fngs_by_ao(parsed_beatdowns, ao_mapping)
    ao_max_attendance = analyze_highest_attendance_per_ao(
        parsed_beatdowns,
        ao_mapping,
        user_mapping,
    )
    return WeeklySummary(
        total_beatdowns=len(beatdowns),
        total_attendance=sum(ao_counts.values()),
        unique_pax=len(pax_counts),
        pax_counts=pax_counts,
        ao_counts=ao_counts,
        q_counts=q_counts,
        ao_fngs=ao_fngs,
        ao_max_attendance=ao_max_attendance,
        top_pax=[
            (user_mapping.get(user_id, user_id), count)
            for user_id, count in sorted(
                pax_counts.items(),
                key=lambda x: (-x[1], user_mapping.get(x[0], x[0]).lower()),
            )[:10]
        ],
        top_aos=sorted(ao_counts.items(), key=lambda x: x[1], reverse=True),
        top_qs=[
            (q, count)
            for q, count in sorted(
                q_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )
            if count >= 2
        ],
    )


def get_beatdown_details(
    beatdown: SqlBeatDownModel,
    user_mapping: dict[str, str],
    ao_mapping: dict[str, str],
) -> BeatdownDetails:
    """Get detailed information about a specific beatdown.

    Args:
        beatdown: Beatdown model
        user_mapping: Dictionary mapping user ID to display name
        ao_mapping: Dictionary mapping channel ID to AO name

    Returns:
        Dictionary with beatdown details
    """
    parsed = transform_sql_to_parsed_beatdown(beatdown)
    fngs = [fng.removeprefix('@') for fng in parsed.fngs or []]

    return BeatdownDetails(
        timestamp=beatdown.timestamp,
        ao_name=ao_mapping.get(beatdown.ao_id, beatdown.ao_id),
        q_name=user_mapping.get(parsed.q_user_id, 'Unknown Q') if parsed.q_user_id else 'Unknown Q',
        title=parsed.title or 'Untitled Beatdown',
        date=parsed.bd_date,
        pax_count=parsed.pax_count or 0,
        pax_names=[user_mapping.get(pax_id, pax_id) for pax_id in (parsed.pax or [])],
        fng_names=fngs,
        workout_type=parsed.workout_type or 'bootcamp',
        word_count=parsed.word_count or 0,
    )


# Convenience functions for common analytics tasks
def get_week_range(date: datetime | None = None) -> tuple[datetime, datetime]:
    """Get the start and end of a week (Monday to Sunday).

    Args:
        date: Date within the week (defaults to today)

    Returns:
        Tuple of (week_start, week_end) datetime objects
    """
    if date is None:
        date = datetime.now(tz=UTC)

    # Calculate days since Monday (0=Monday, 6=Sunday)
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    week_end = week_start + timedelta(days=6)

    # Set to start/end of day
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
    )

    return week_start, week_end


def get_month_range(date: datetime | None = None) -> tuple[datetime, datetime]:
    """Get the start and end of a month.

    Args:
        date: Date within the month (defaults to today)

    Returns:
        Tuple of (month_start, month_end) datetime objects
    """
    if date is None:
        date = datetime.now(tz=UTC)

    # First day of the month
    month_start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Last day of the month
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    month_end = next_month - timedelta(microseconds=1)

    return month_start, month_end


def _format_beatdown_date(bd_date: str | None) -> str:
    """Format beatdown date string for display.

    Args:
        bd_date: Date string in YYYY-MM-DD format or None

    Returns:
        Formatted date string in MM/DD/YYYY format or 'Unknown Date'
    """
    if not bd_date:
        return 'Unknown Date'

    try:
        date_obj = datetime.strptime(bd_date, '%Y-%m-%d').replace(tzinfo=UTC)
        return date_obj.strftime('%m/%d/%Y')
    except (ValueError, TypeError):
        return 'Unknown Date'


def _get_q_display_name(
    q_user_id: str | None,
    user_mapping: dict[str, str],
) -> str:
    """Get display name for Q (workout leader).

    Args:
        q_user_id: User ID of the Q or None
        user_mapping: Dictionary mapping user ID to display name

    Returns:
        Display name for Q or 'Unknown Q' if not found
    """
    if not q_user_id:
        return 'Unknown Q'
    return user_mapping.get(q_user_id, 'Unknown Q')
