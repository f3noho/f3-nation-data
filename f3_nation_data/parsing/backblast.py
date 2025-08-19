"""Backblast parsing utilities for F3 Nation data.

This module provides utilities for parsing F3 beatdown backblast content
and transforming SQL models into parsed application models.
"""

import datetime as dt
import json
import re
from dataclasses import dataclass
from datetime import datetime

from f3_nation_data.models.parsed.beatdown import ParsedBeatdown
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel


@dataclass
class PeopleInfo:
    """Information about people extracted from backblast."""

    q_user_id: str | None = None
    coq_user_id: list[str] | None = None
    pax: list[str] | None = None
    non_registered_pax: list[str] | None = None
    fngs: list[str] | None = None


@dataclass
class ContentSections:
    """Content sections extracted from backblast."""

    warmup: str | None = None
    thang: str | None = None
    mary: str | None = None
    announcements: str | None = None
    cot: str | None = None


@dataclass
class AnalyticsData:
    """Analytics data computed from backblast."""

    workout_type: str
    day_of_week: str | None
    has_announcements: bool
    has_cot: bool
    word_count: int | None
    pax_count: int
    fng_count: int


def _is_slack_id(item: str) -> str | None:
    match = re.match(r'^<@([A-Z0-9]+)>$', item)
    return match.group(1) if match else None


def _is_valid_non_registered(item: str) -> bool:
    return bool(item) and not item.startswith('<@') and item not in ['None', 'N/A']


def extract_pax_from_string(pax_string: str) -> tuple[list[str], list[str]]:
    """Extract valid Slack IDs and non-registered names from a PAX string.

    Args:
        pax_string: String containing PAX information (comma-separated).

    Returns:
        Tuple of (slack_ids, non_registered_names) lists with duplicates removed.
    """
    if not pax_string.strip():
        return [], []

    normalized = re.sub(r'\s+', ' ', pax_string.strip()).replace(' <@', ',<@')
    items = [item.strip() for item in normalized.split(',') if item.strip()]

    slack_ids, non_registered_names = [], []
    for item in items:
        slack_id = _is_slack_id(item)
        if slack_id:
            if slack_id not in slack_ids:
                slack_ids.append(slack_id)
        elif _is_valid_non_registered(item) and item not in non_registered_names:
            non_registered_names.append(item)

    return slack_ids, non_registered_names


def extract_pax_count(backblast: str) -> int:
    """Extract the total PAX count from backblast content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        Total PAX count.
    """
    # The explicit COUNT cannot be trusted because there are some FNG fields
    # that are set to None and these are counted as a PAX. Do not trust.
    all_slack_ids: set[str] = set()
    all_non_registered: set[str] = set()

    # Count registered PAX (Slack user IDs)
    pax_pattern = r'^PAX:\s*(.*)$'
    pax_match = re.search(pax_pattern, backblast, re.MULTILINE)
    if pax_match:
        pax_line = pax_match.group(1).strip()
        slack_ids, non_registered = extract_pax_from_string(pax_line)
        all_slack_ids.update(slack_ids)
        all_non_registered.update(non_registered)

    # Count Q
    q_pattern = r'^Q:\s*(.*)$'
    q_match = re.search(q_pattern, backblast, re.MULTILINE)
    if q_match:
        q_line = q_match.group(1).strip()
        q_slack_ids, q_non_registered = extract_pax_from_string(q_line)
        all_slack_ids.update(q_slack_ids)
        all_non_registered.update(q_non_registered)

    return len(all_slack_ids) + len(all_non_registered)


def extract_fng_names(backblast: str) -> list[str]:
    """Extract the list of FNG names from backblast content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        List of FNG names.
    """
    # First, get all non-registered PAX names
    all_non_registered: set[str] = set()

    # Extract from PAX section only (Q's can't be FNGs)
    pax_pattern = r'^PAX:\s*(.*)$'
    pax_match = re.search(pax_pattern, backblast, re.MULTILINE)
    if pax_match:
        pax_line = pax_match.group(1).strip()
        _, non_registered = extract_pax_from_string(pax_line)
        all_non_registered.update(non_registered)

    # Now look for FNG field and check which non-registered names are mentioned
    fng_pattern = r'^FNG[S]?:\s*(.*)$'
    fng_match = re.search(fng_pattern, backblast, re.MULTILINE | re.IGNORECASE)

    if fng_match:
        fng_line = fng_match.group(1).strip().lower()

        # Find which non-registered names are mentioned in the FNG field
        return [name for name in all_non_registered if name.lower() in fng_line]

    return []


def extract_fng_count(backblast: str) -> int:
    """Extract the FNG count from backblast content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        FNG count.
    """
    fng_names = extract_fng_names(backblast)
    return len(fng_names)


def extract_bd_date(backblast: str) -> str | None:
    """Extract the beatdown date from backblast content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        Date string in YYYY-MM-DD format, or None if not found.
    """
    date_patterns = [
        r'DATE:\s*(\d{4}-\d{2}-\d{2})',
        r'DATE:\s*(\d{4}/\d{2}/\d{2})',
        r'DATE:\s*(\d{2}/\d{2}/\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
    ]

    for pattern in date_patterns:
        match = re.search(pattern, backblast)
        if match:
            date_str = match.group(1)
            normalized_date = _normalize_date_string(date_str)
            if normalized_date:
                return normalized_date
    return None


def _normalize_date_string(date_str: str) -> str | None:
    """Normalize a date string to YYYY-MM-DD format.

    Args:
        date_str: Date string in various formats.

    Returns:
        Normalized date string or None if invalid.
    """
    try:
        if '/' in date_str:
            return _parse_slash_date(date_str)
        # YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').replace(
            tzinfo=dt.UTC,
        )
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        return None


def _parse_slash_date(date_str: str) -> str:
    """Parse date string with slash separators.

    Args:
        date_str: Date string with / separators.

    Returns:
        Normalized date string in YYYY-MM-DD format.
    """
    if date_str.startswith('20'):  # YYYY/MM/DD
        date_obj = datetime.strptime(date_str, '%Y/%m/%d').replace(
            tzinfo=dt.UTC,
        )
    else:  # MM/DD/YYYY
        date_obj = datetime.strptime(date_str, '%m/%d/%Y').replace(
            tzinfo=dt.UTC,
        )
    return date_obj.strftime('%Y-%m-%d')


def extract_workout_type(backblast: str) -> str:
    """Extract the workout type from backblast content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        Workout type string - either 'bootcamp' or 'ruck'.
    """
    content = backblast.lower()

    # First check for bootcamp structure indicators (warmup + thang)
    has_warmup = bool(
        re.search(r'^(warmup|warm\s*up|warm-up):', content, re.MULTILINE),
    )
    has_thang = bool(re.search(r'^(thang|the\s*thang):', content, re.MULTILINE))

    # If it has standard bootcamp structure, it's definitely a bootcamp
    if has_warmup and has_thang:
        return 'bootcamp'

    # Extract metadata section (everything before COUNT:)
    count_pattern = r'^COUNT:'
    count_match = re.search(count_pattern, backblast, re.MULTILINE)
    metadata_section = backblast[: count_match.start()].lower() if count_match else content

    # Check for ruck indicators in metadata section only
    ruck_pattern = r'\b(ruck|rucking|ruck\s*march)\b'
    if re.search(ruck_pattern, metadata_section):
        return 'ruck'

    # Default to bootcamp if no specific type found
    return 'bootcamp'


def extract_day_of_week(bd_date: str) -> str | None:
    """Extract or compute the day of the week.

    Args:
        backblast: The raw backblast text content.
        bd_date: Optional parsed date to compute day from.

    Returns:
        Day of week string (e.g., "Monday"), or None if not determinable.
    """
    try:
        date_obj = datetime.strptime(bd_date, '%Y-%m-%d').replace(tzinfo=dt.UTC)
        return date_obj.strftime('%A')
    except ValueError:
        pass
    return None


def check_has_announcements(backblast: str) -> bool:
    """Check if the backblast contains announcements content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        True if announcements are present, False otherwise.
    """
    announcements_section = _extract_section(backblast, 'ANNOUNCEMENTS')
    return bool(announcements_section and announcements_section.strip())


def check_has_cot(backblast: str) -> bool:
    """Check if the backblast contains Circle of Trust content.

    Args:
        backblast: The raw backblast text content.

    Returns:
        True if COT content is present, False otherwise.
    """
    cot_section = _extract_section(backblast, 'COT')
    return bool(cot_section and cot_section.strip())


def calculate_word_count(backblast: str) -> int | None:
    """Calculate the approximate word count of the backblast content after COUNT.

    Args:
        backblast: The raw backblast text content.

    Returns:
        Word count of content after COUNT line, or None if no content found.
    """
    # Extract only the content after the COUNT line
    content_after_count = extract_after_count(backblast) or backblast

    # Simple word count based on whitespace splitting
    words = content_after_count.split()
    return len(words)


def extract_files_from_json(json_data: str) -> list[str] | None:
    """Extract file URLs from JSON data.

    Args:
        json_data: JSON string containing file information.

    Returns:
        List of file URLs, or None if no files found.
    """
    try:
        data: dict[str, object] = json.loads(json_data)  # pyright:ignore[reportAny]
        files = data.get('files')
        if not isinstance(files, list):
            return None
        file_urls = _extract_urls_from_files(files)  # pyright:ignore[reportUnknownArgumentType]
    except (json.JSONDecodeError, TypeError):
        return None
    else:
        return file_urls if file_urls else None


def _extract_urls_from_files(files_data: list[object]) -> list[str]:
    """Extract URLs from file objects list."""
    file_urls: list[str] = []
    for item in files_data:
        if isinstance(item, dict):
            url = _get_url_from_file_dict(item)  # pyright:ignore[reportUnknownArgumentType]
            if url:
                file_urls.append(url)
        elif isinstance(item, str):
            file_urls.append(item)
    return file_urls


def _get_url_from_file_dict(item: dict[str, object]) -> str | None:
    """Get URL from a file dictionary object."""
    url_fields = ['url', 'permalink', 'url_private', 'permalink_public']
    for url_field in url_fields:
        if url_field in item:
            url_value = item[url_field]
            if isinstance(url_value, str):
                return url_value
    return None


def extract_after_count(text: str) -> str | None:
    """Extract all text after the 'COUNT:' line in the backblast.

    Args:
        text: The full backblast string.

    Returns:
        The content after the 'COUNT:' line, or None if not found.
    """
    pattern = r'^COUNT:.*\n([\s\S]*)'
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def transform_sql_to_parsed_beatdown(
    sql_bd: SqlBeatDownModel,
) -> ParsedBeatdown:
    """Transform a SQL beatdown row into a fully parsed App BeatDown model."""
    backblast = sql_bd.backblast or ''

    # Extract basic content
    title = _extract_title(backblast)

    # Extract people information
    people = _extract_all_people(backblast)

    # Extract content sections
    sections = _extract_all_sections(backblast)

    # Compute analytics
    bd_date = extract_bd_date(backblast)
    analytics = _compute_simple_analytics(backblast, bd_date)

    return ParsedBeatdown(
        ao_id=sql_bd.ao_id,
        timestamp=sql_bd.timestamp or '',
        last_edited=sql_bd.ts_edited,
        raw_backblast=backblast,
        title=title,
        q_user_id=people.q_user_id,
        coq_user_id=people.coq_user_id,
        pax=people.pax,
        non_registered_pax=people.non_registered_pax,
        fngs=people.fngs,
        warmup=sections.warmup,
        thang=sections.thang,
        mary=sections.mary,
        announcements=sections.announcements,
        cot=sections.cot,
        bd_date=bd_date,
        workout_type=analytics.workout_type,
        day_of_week=analytics.day_of_week,
        has_announcements=analytics.has_announcements,
        has_cot=analytics.has_cot,
        word_count=analytics.word_count,
        pax_count=analytics.pax_count,
        fng_count=analytics.fng_count,
    )


def _extract_all_people(backblast: str) -> PeopleInfo:
    """Extract all people-related information from backblast."""
    people = PeopleInfo()

    # Extract Q (can be multiple)
    q_match = re.search(r'^Q:\s*(.*)$', backblast, re.MULTILINE)
    q_ids = []
    if q_match:
        q_line = q_match.group(1).strip()
        q_ids, _ = extract_pax_from_string(q_line)
        people.q_user_id = q_ids[0] if q_ids else None

    # Extract COQ
    coq_match = re.search(r'^COQ:\s*(.*)$', backblast, re.MULTILINE)
    coq_ids = []
    if coq_match:
        coq_line = coq_match.group(1).strip()
        coq_ids, _ = extract_pax_from_string(coq_line)

    # Combine Qs and COQs for coq_user_id (Q IDs first, then COQ IDs)
    combined_coqs = q_ids[1:] + coq_ids if q_ids else coq_ids
    people.coq_user_id = combined_coqs if combined_coqs else None

    # Extract PAX
    pax_match = re.search(r'^PAX:\s*(.*)$', backblast, re.MULTILINE)
    if pax_match:
        pax_line = pax_match.group(1).strip()
        people.pax, people.non_registered_pax = extract_pax_from_string(
            pax_line,
        )

    # Extract FNGs
    people.fngs = extract_fng_names(backblast)

    return people


def _extract_all_sections(backblast: str) -> ContentSections:
    """Extract all workout content sections from backblast."""
    return ContentSections(
        warmup=_extract_section(backblast, 'WARMUP'),
        thang=_extract_section(backblast, 'THANG') or _extract_section(backblast, 'THE THANG'),
        mary=_extract_section(backblast, 'MARY'),
        announcements=_extract_section(backblast, 'ANNOUNCEMENTS'),
        cot=_extract_section(backblast, 'COT'),
    )


def _compute_simple_analytics(
    backblast: str,
    bd_date: str | None,
) -> AnalyticsData:
    """Compute simple analytical properties from backblast."""
    return AnalyticsData(
        workout_type=extract_workout_type(backblast),
        day_of_week=extract_day_of_week(bd_date) if bd_date else None,
        has_announcements=check_has_announcements(backblast),
        has_cot=check_has_cot(backblast),
        word_count=calculate_word_count(backblast),
        pax_count=extract_pax_count(backblast),
        fng_count=extract_fng_count(backblast),
    )


def _extract_title(backblast: str) -> str | None:
    """Extract title from the first line of backblast."""
    return backblast.split('\n', 1)[0].strip() if backblast else None


# Helper functions
def _extract_section(text: str, section: str) -> str | None:
    """Extract a section from the backblast text."""
    # First try inline format: "SECTION: content on same line"
    inline_pattern = rf'(?im)^{re.escape(section)}:[ \t]*(.+)$'
    inline_match = re.search(inline_pattern, text)
    if inline_match:
        return inline_match.group(1).strip()

    # Then try multi-line format: "SECTION:\n content on next lines"
    multiline_pattern = rf'(?im)^{re.escape(section)}:[ \t]*\n([\s\S]*?)(?=^[A-Z ]+:|\Z)'
    multiline_match = re.search(multiline_pattern, text)
    if multiline_match:
        return multiline_match.group(1).strip()

    return None
