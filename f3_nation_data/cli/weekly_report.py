"""CLI module for generating weekly F3 Nation beatdown reports."""

import argparse
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy.orm import Session

from f3_nation_data.analytics import (
    WeeklySummary,
    get_ao_mapping,
    get_user_mapping,
    get_week_range,
    get_weekly_summary,
)
from f3_nation_data.database import get_sql_engine
from f3_nation_data.fetch import fetch_beatdowns_for_date_range

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


REGION_MAP = {
    'f3noho': ('F3 NoHo', ':noho:'),
    'f3lakehouston': ('F3 Lake Houston', ':f3-logo-black:'),
    'f3northwestpassage': ('F3 North West Passage', ':northwest-passage:'),
}


class MissingF3NationDatabaseError(Exception):
    """Custom exception for missing F3_NATION_DATABASE environment variable."""

    def __init__(self) -> None:
        """Initialize with a custom error message."""
        msg = 'F3_NATION_DATABASE environment variable is not set. Please set it to your F3 region name.'
        super().__init__(msg)


def parse_date_argument(date_str: str) -> datetime:
    """Parse date argument from command line.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Parsed datetime object

    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError as e:
        msg = f"Invalid date format '{date_str}'. Use YYYY-MM-DD format."
        raise ValueError(msg) from e


def format_weekly_summary_for_template(summary: WeeklySummary) -> dict:
    """Convert WeeklySummary to template-friendly format.

    Args:
        summary: WeeklySummary Pydantic model

    Returns:
        Dictionary suitable for Jinja2 template
    """
    return {
        'total_beatdowns': summary.total_beatdowns,
        'total_attendance': summary.total_attendance,
        'unique_pax': summary.unique_pax,
        'ao_fngs': summary.ao_fngs,
        'ao_max_attendance': summary.ao_max_attendance,
        'top_pax': summary.top_pax,
        'top_aos': summary.top_aos,
        'top_qs': summary.top_qs,
    }


def generate_weekly_report(target_date: datetime | None = None) -> str:
    """Generate weekly beatdown report for the specified week.

    Args:
        target_date: Date within the target week (defaults to current week)

    Returns:
        Formatted report string

    Raises:
        Exception: If database connection or data fetching fails
    """
    # Use current week if no target date provided
    if target_date is None:
        target_date = datetime.now(tz=UTC)

    # Get week range
    week_start, week_end = get_week_range(target_date)

    logger.info(
        'Generating report for week: %s to %s',
        week_start.strftime('%Y-%m-%d'),
        week_end.strftime('%Y-%m-%d'),
    )

    # Connect to database
    engine = get_sql_engine()

    with Session(engine) as session:
        # Get mappings
        logger.info('Loading user and AO mappings...')
        user_mapping = get_user_mapping(session)
        ao_mapping = get_ao_mapping(session)

        # Fetch beatdowns for the week
        logger.info('Fetching beatdowns...')
        beatdowns = fetch_beatdowns_for_date_range(
            session,
            week_start,
            week_end,
        )

        if not beatdowns:
            return f'No beatdowns found for week {week_start.strftime("%Y-%m-%d")} to {week_end.strftime("%Y-%m-%d")}'

        logger.info('Found %d beatdowns for the week', len(beatdowns))

        # Generate analytics
        logger.info('Analyzing data...')
        summary = get_weekly_summary(beatdowns, user_mapping, ao_mapping)

    # Determine region title and emoji from DB name

    db_name = os.environ.get('F3_NATION_DATABASE', '').lower()
    region_title, region_emoji = REGION_MAP.get(
        db_name,
        (db_name, ''),
    )
    if not db_name:
        raise MissingF3NationDatabaseError

    # Load template
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,  # noqa: S701 - Safe for text reports, not web content
    )
    # Add custom filter to prefix @ using a lambda
    env.filters['at_prefix'] = lambda names: [f'@{name}' for name in names]
    template = env.get_template('weekly_report.txt')

    # Format data for template
    template_data = {
        'week_start': week_start,
        'week_end': week_end,
        'summary': format_weekly_summary_for_template(summary),
        'region_title': region_title,
        'region_emoji': region_emoji,
    }

    # Render report
    return template.render(**template_data)


def main() -> None:
    """Main CLI entry point for weekly report generation."""
    parser = argparse.ArgumentParser(
        description='Generate F3 Nation weekly beatdown report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Generate report for current week
  %(prog)s 2024-03-15         # Generate report for week containing March 15, 2024
  %(prog)s --date 2024-03-15  # Same as above
        """,
    )

    parser.add_argument(
        'date',
        nargs='?',
        help='Date within the target week (YYYY-MM-DD format). Defaults to current week.',
    )

    parser.add_argument(
        '--date',
        dest='date_flag',
        help='Date within the target week (YYYY-MM-DD format). Alternative to positional argument.',
    )

    args = parser.parse_args()

    # Determine target date
    target_date = None
    date_str = args.date or args.date_flag

    if date_str:
        try:
            target_date = parse_date_argument(date_str)
        except ValueError:
            logger.exception('Error parsing date')
            sys.exit(1)

    try:
        report = generate_weekly_report(target_date)
        # Use sys.stdout.write instead of print to avoid linter issues
        sys.stdout.write(report + '\n')

    except (OSError, ValueError):
        logger.exception('Error generating report')
        sys.exit(1)


if __name__ == '__main__':
    main()
