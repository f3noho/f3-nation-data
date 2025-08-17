"""Backblast parsing utilities for F3 Nation data.

This module provides utilities for parsing F3 beatdown backblast content
and transforming SQL models into parsed application models.
"""

import datetime as dt
import json
import re
from datetime import datetime

from f3_nation_data.models.parsed.beatdown import ParsedBeatdown
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel


def extract_pax_from_string(pax_string: str) -> tuple[list[str], list[str]]:
    """Extract valid Slack IDs and non-registered names from a PAX string.

    Args:
        pax_string: String containing PAX information (comma-separated).

    Returns:
        Tuple of (slack_ids, non_registered_names) lists with duplicates removed.
    """
    slack_ids: set[str] = set()
    non_registered_names: set[str] = set()

    if not pax_string.strip():
        return list(slack_ids), list(non_registered_names)

    # Normalize spacing and split by commas
    normalized = re.sub(r'\s+', ' ', pax_string.strip())
    # Handle cases where slack IDs might be separated by spaces instead of commas
    normalized = normalized.replace(' <@', ',<@')

    # Split by commas and process each item
    items = [item.strip() for item in normalized.split(',') if item.strip()]

    for item in items:
        # Check if it's a valid Slack user ID format: <@USERID>
        slack_id_pattern = r'^<@([A-Z0-9]+)>$'
        match = re.match(slack_id_pattern, item)
        if match:
            slack_ids.add(match.group(1))  # Extract just the user ID part
        elif item and not item.startswith('<@') and item not in ['None', 'N/A']:
            # Non-registered name (not empty and not a malformed Slack ID)
            non_registered_names.add(item)

    return list(slack_ids), list(non_registered_names)


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
    # Look for DATE: YYYY-MM-DD pattern
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
            try:
                # Try to parse and normalize to YYYY-MM-DD
                if '/' in date_str:
                    if date_str.startswith('20'):  # YYYY/MM/DD
                        date_obj = datetime.strptime(
                            date_str,
                            '%Y/%m/%d',
                        ).replace(tzinfo=dt.UTC)
                    else:  # MM/DD/YYYY
                        date_obj = datetime.strptime(
                            date_str,
                            '%m/%d/%Y',
                        ).replace(tzinfo=dt.UTC)
                else:  # YYYY-MM-DD
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').replace(
                        tzinfo=dt.UTC,
                    )
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
    return None


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
    # Title: first line
    title = backblast.split('\n', 1)[0].strip() if backblast else None
    # Q and Co-Q
    q_user_id = None
    coq_user_id = None
    pax = None
    non_registered_pax = None
    fngs = None
    warmup = None
    thang = None
    mary = None
    announcements = None
    cot = None

    q_match = re.search(r'^Q:\s*(.*)$', backblast, re.MULTILINE)
    if q_match:
        q_line = q_match.group(1).strip()
        q_ids, _ = extract_pax_from_string(q_line)
        q_user_id = q_ids[0] if q_ids else None
    coq_match = re.search(r'^COQ:\s*(.*)$', backblast, re.MULTILINE)
    if coq_match:
        coq_line = coq_match.group(1).strip()
        coq_ids, _ = extract_pax_from_string(coq_line)
        coq_user_id = coq_ids if coq_ids else None
    pax_match = re.search(r'^PAX:\s*(.*)$', backblast, re.MULTILINE)
    if pax_match:
        pax_line = pax_match.group(1).strip()
        pax, non_registered_pax = extract_pax_from_string(pax_line)
    fngs = extract_fng_names(backblast)
    warmup = _extract_section(backblast, 'WARMUP')
    thang = _extract_section(backblast, 'THANG') or _extract_section(
        backblast,
        'THE THANG',
    )
    mary = _extract_section(backblast, 'MARY')
    announcements = _extract_section(backblast, 'ANNOUNCEMENTS')
    cot = _extract_section(backblast, 'COT')
    # Dates and analytics
    bd_date = extract_bd_date(backblast)
    workout_type = extract_workout_type(backblast)
    day_of_week = extract_day_of_week(bd_date) if bd_date else None
    has_announcements = check_has_announcements(backblast)
    has_cot = check_has_cot(backblast)
    word_count = calculate_word_count(backblast)
    pax_count = extract_pax_count(backblast)
    fng_count = extract_fng_count(backblast)
    return ParsedBeatdown(
        timestamp=sql_bd.timestamp or '',
        last_edited=sql_bd.ts_edited,
        raw_backblast=backblast,
        title=title,
        q_user_id=q_user_id,
        coq_user_id=coq_user_id,
        pax=pax,
        non_registered_pax=non_registered_pax,
        fngs=fngs,
        warmup=warmup,
        thang=thang,
        mary=mary,
        announcements=announcements,
        cot=cot,
        bd_date=bd_date,
        workout_type=workout_type,
        day_of_week=day_of_week,
        has_announcements=has_announcements,
        has_cot=has_cot,
        word_count=word_count,
        pax_count=pax_count,
        fng_count=fng_count,
    )


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
