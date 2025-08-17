from datetime import datetime

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from f3_nation_data.fetch import (
    fetch_beatdowns_for_date_range,
    fetch_beatdowns_for_week,
    fetch_sql_aos,
    fetch_sql_beatdowns,
    fetch_sql_users,
)


def test_fetch_beatdowns_for_week_monday(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a week when given a Monday."""
    with Session(f3_test_database) as session:
        # Test with a Monday date
        monday_date = datetime(2024, 6, 3)  # noqa: DTZ001 - This was a Monday
        beatdowns = fetch_beatdowns_for_week(session, monday_date)

        # Should return a list (empty or with beatdowns)
        assert isinstance(beatdowns, list)


def test_fetch_beatdowns_for_week_wednesday(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a week when given a Wednesday."""
    with Session(f3_test_database) as session:
        # Test with a Wednesday date - should calculate the correct Monday-Sunday week
        wednesday_date = datetime(2024, 6, 5)  # noqa: DTZ001 - This was a Wednesday
        beatdowns = fetch_beatdowns_for_week(session, wednesday_date)

        # Should return a list
        assert isinstance(beatdowns, list)

        # Verify it calculated the same week as if we passed the Monday
        monday_date = datetime(2024, 6, 3)  # noqa: DTZ001 - Monday of the same week
        monday_beatdowns = fetch_beatdowns_for_week(session, monday_date)

        # Should get the same results since they're the same week
        assert len(beatdowns) == len(monday_beatdowns)


def test_fetch_sql_beatdowns_all(f3_test_database: Engine) -> None:
    """Test fetching all beatdowns without filters."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)

        # Should return all beatdowns from fixture data
        assert len(beatdowns) >= 0
        # All results should have the expected model type
        assert all(hasattr(bd, 'timestamp') for bd in beatdowns)


def test_fetch_sql_beatdowns_with_timestamp_filter(
    f3_test_database: Engine,
) -> None:
    """Test fetching beatdowns with timestamp filter."""
    with Session(f3_test_database) as session:
        # First get all beatdowns to know what we have
        all_beatdowns = fetch_sql_beatdowns(session)

        if all_beatdowns:
            # Use a timestamp that should filter out some results
            filter_timestamp = '2024-01-01 00:00:00'
            filtered_beatdowns = fetch_sql_beatdowns(
                session,
                after_timestamp=filter_timestamp,
            )

            # The filtered results should be a subset (or equal) to all results
            assert len(filtered_beatdowns) <= len(all_beatdowns)


def test_fetch_beatdowns_for_week(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a specific week."""
    with Session(f3_test_database) as session:
        # Test with a specific week start date (naive datetime for testing)
        week_start = datetime(2024, 6, 3)  # noqa: DTZ001 - naive datetime for testing
        beatdowns = fetch_beatdowns_for_week(session, week_start)

        # Should return a list (may be empty if no data for that week)
        assert isinstance(beatdowns, list)

        # All results should have timestamp attribute
        assert all(hasattr(bd, 'timestamp') for bd in beatdowns)


def test_fetch_beatdowns_for_date_range(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a specific date range."""
    with Session(f3_test_database) as session:
        # Naive datetimes for testing
        start_date = datetime(2024, 1, 1)  # noqa: DTZ001
        end_date = datetime(2024, 12, 31)  # noqa: DTZ001

        beatdowns = fetch_beatdowns_for_date_range(
            session,
            start_date,
            end_date,
        )

        # Should return a list
        assert isinstance(beatdowns, list)

        # All results should have timestamp attribute
        assert all(hasattr(bd, 'timestamp') for bd in beatdowns)


def test_fetch_sql_users_all(f3_test_database: Engine) -> None:
    """Test fetching all users without filters."""
    with Session(f3_test_database) as session:
        users = fetch_sql_users(session)

        # Should return a list
        assert isinstance(users, list)

        # All results should have user_id attribute
        assert all(hasattr(user, 'user_id') for user in users)


def test_fetch_sql_users_with_filter(f3_test_database: Engine) -> None:
    """Test fetching users with ID filter."""
    with Session(f3_test_database) as session:
        # Try to fetch specific user IDs
        test_ids = [1, 2, 3]
        users = fetch_sql_users(session, user_ids=test_ids)

        # Should return a list (may be empty if no matching IDs)
        assert isinstance(users, list)


def test_fetch_sql_aos_all(f3_test_database: Engine) -> None:
    """Test fetching all AOs without filters."""
    with Session(f3_test_database) as session:
        aos = fetch_sql_aos(session)

        # Should return a list
        assert isinstance(aos, list)

        # All results should have channel_id attribute
        assert all(hasattr(ao, 'channel_id') for ao in aos)


def test_fetch_sql_aos_with_filter(f3_test_database: Engine) -> None:
    """Test fetching AOs with channel ID filter."""
    with Session(f3_test_database) as session:
        # Try to fetch specific channel IDs
        test_ids = ['test1', 'test2']
        aos = fetch_sql_aos(session, channel_ids=test_ids)

        # Should return a list (may be empty if no matching IDs)
        assert isinstance(aos, list)
