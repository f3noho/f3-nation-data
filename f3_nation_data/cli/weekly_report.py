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
from f3_nation_data.version import __version__

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


REGION_MAP = {
    'f3noho': ('F3 NoHo', ':noho:'),
    'f3lakehouston': ('F3 Lake Houston', ':f3-logo-black:'),
    'f3northwestpassage': ('F3 North West Passage', ':northwest-passage:'),
}


def valid_date(date_str: str) -> datetime:
    """Argparse type for validating date argument."""
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=UTC)
    except ValueError:
        msg = f"Invalid date format '{date_str}'. Use YYYY-MM-DD format."
        raise argparse.ArgumentTypeError(msg)  # noqa: B904 - Custom argparse error message


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


def get_weekly_summary_data(
    target_date: datetime | None = None,
) -> tuple[WeeklySummary | None, datetime, datetime]:
    """Fetch and analyze weekly beatdown data."""
    if target_date is None:
        target_date = datetime.now(tz=UTC)
    week_start, week_end = get_week_range(target_date)
    logger.info(
        'Generating report for week: %s to %s',
        week_start.strftime('%Y-%m-%d'),
        week_end.strftime('%Y-%m-%d'),
    )
    engine = get_sql_engine()
    with Session(engine) as session:
        user_mapping = get_user_mapping(session)
        ao_mapping = get_ao_mapping(session)
        beatdowns = fetch_beatdowns_for_date_range(
            session,
            week_start,
            week_end,
        )
        if not beatdowns:
            return None, week_start, week_end
        summary = get_weekly_summary(beatdowns, user_mapping, ao_mapping)
    return summary, week_start, week_end


def get_weekly_template_data(
    summary: WeeklySummary,
    week_start: datetime,
    week_end: datetime,
) -> dict:
    """Prepare template context for weekly report."""
    db_name = os.environ.get('F3_NATION_DATABASE', '').lower()
    region_title, region_emoji = REGION_MAP.get(db_name, (db_name, ''))
    return {
        'week_start': week_start,
        'week_end': week_end,
        'summary': format_weekly_summary_for_template(summary),
        'region_title': region_title,
        'region_emoji': region_emoji,
    }


def render_weekly_report(template_data: dict) -> str:
    """Render the weekly report from template data."""
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,  # noqa: S701 - Safe for text reports, not web content
    )
    env.filters['at_prefix'] = lambda names: [f'@{name}' for name in names]
    template = env.get_template('weekly_report.txt')
    return template.render(**template_data)


def generate_weekly_report(
    target_date: datetime | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Generate weekly beatdown report for the specified week."""
    summary, week_start, week_end = get_weekly_summary_data(target_date)
    week_start_str = week_start.strftime('%Y-%m-%d')
    week_end_str = week_end.strftime('%Y-%m-%d')
    if summary is None:
        # Return None and week range as strings for error handling in main
        return None, week_start_str, week_end_str
    template_data = get_weekly_template_data(summary, week_start, week_end)
    return render_weekly_report(template_data), None, None


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
        type=valid_date,
        help='Date within the target week (YYYY-MM-DD format). Defaults to current week.',
    )

    parser.add_argument(
        '--date',
        dest='date_flag',
        type=valid_date,
        help='Date within the target week (YYYY-MM-DD format). Alternative to positional argument.',
    )

    parser.add_argument(
        '--version',
        action='version',
        version=__version__,
        help='Show CLI version and exit.',
    )

    args = parser.parse_args()

    # Determine target date
    target_date = args.date or args.date_flag

    try:
        report, no_bd_start, no_bd_end = generate_weekly_report(target_date)
        if report is None:
            msg = f'No beatdowns found for week {no_bd_start} to {no_bd_end}'
            logger.error(msg)
            sys.exit(1)
        sys.stdout.write(report + '\n')
    except (OSError, ValueError):
        logger.exception('Error generating report')
        sys.exit(1)


if __name__ == '__main__':
    main()
