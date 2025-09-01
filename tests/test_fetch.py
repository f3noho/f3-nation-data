"""Tests for fetch utilities.

Timestamp Usage Strategy:
- Database stores timestamps as Unix timestamps (float as string): "1710009857.949729"
- fetch_sql_beatdowns() expects timezone-aware datetime objects for filtering
- fetch_beatdowns_for_week() and fetch_beatdowns_for_date_range() accept timezone-aware datetime objects
  and convert them internally to Unix timestamps for database queries
- Tests use timezone-aware datetime objects for all datetime inputs
"""

from datetime import UTC, datetime

import pytest
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
        monday_date = datetime(2024, 6, 3, tzinfo=UTC)  # This was a Monday
        beatdowns = fetch_beatdowns_for_week(session, monday_date)

        # Should return a list (empty or with beatdowns)
        assert isinstance(beatdowns, list)


def test_fetch_beatdowns_for_week_wednesday(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a week when given a Wednesday."""
    with Session(f3_test_database) as session:
        # Test with a Wednesday date - should calculate the correct Monday-Sunday week
        wednesday_date = datetime(
            2024,
            6,
            5,
            tzinfo=UTC,
        )  # This was a Wednesday
        beatdowns = fetch_beatdowns_for_week(session, wednesday_date)

        # Should return a list
        assert isinstance(beatdowns, list)

        # Verify it calculated the same week as if we passed the Monday
        monday_date = datetime(
            2024,
            6,
            3,
            tzinfo=UTC,
        )  # Monday of the same week
        monday_beatdowns = fetch_beatdowns_for_week(session, monday_date)

        # Should get the same results since they're the same week
        assert len(beatdowns) == len(monday_beatdowns)


def test_fetch_sql_beatdowns_all(f3_test_database: Engine) -> None:
    """Test fetching all beatdowns and verify we get expected fixture data."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)

        # Should return beatdowns from fixture data
        assert len(beatdowns) > 0

        # All results should have the expected attributes
        assert all(hasattr(bd, 'timestamp') for bd in beatdowns)
        assert all(hasattr(bd, 'ao_id') for bd in beatdowns)
        assert all(hasattr(bd, 'q_user_id') for bd in beatdowns)

        # Verify we have beatdowns with expected data
        ao_ids = [bd.ao_id for bd in beatdowns]
        assert 'C04PD48V9KR' in ao_ids  # The Depot channel ID


def test_fetch_sql_beatdowns_with_timestamp_filter(
    f3_test_database: Engine,
) -> None:
    """Test fetching beatdowns with timestamp filter."""
    with Session(f3_test_database) as session:
        # First get all beatdowns to know what we have
        all_beatdowns = fetch_sql_beatdowns(session)

        if all_beatdowns:
            # Our fixture data uses Unix timestamps like "1710009857.949729" (March 9, 2024)
            # Test with a timestamp before our fixture data
            early_datetime = datetime(
                2023,
                11,
                14,
                tzinfo=UTC,
            )  # November 14, 2023
            filtered_beatdowns = fetch_sql_beatdowns(
                session,
                after_timestamp=early_datetime,
            )

            # Should get all beatdowns since they're all after November 2023
            assert len(filtered_beatdowns) == len(all_beatdowns)

            # Now test with a timestamp after our fixture data
            future_datetime = datetime(
                2027,
                1,
                14,
                tzinfo=UTC,
            )  # January 14, 2027
            future_filtered = fetch_sql_beatdowns(
                session,
                after_timestamp=future_datetime,
            )

            # Should get no beatdowns since they're all before 2027
            assert len(future_filtered) == 0


def test_fetch_beatdowns_for_week(f3_test_database: Engine) -> None:
    """Test fetching beatdowns for a specific week."""
    with Session(f3_test_database) as session:
        # Test with a specific week start date (naive datetime for testing)
        week_start = datetime(
            2024,
            6,
            3,
            tzinfo=UTC,
        )  # naive datetime for testing
        beatdowns = fetch_beatdowns_for_week(session, week_start)

        # Should return a list (may be empty if no data for that week)
        assert isinstance(beatdowns, list)

        # All results should have timestamp attribute
        assert all(hasattr(bd, 'timestamp') for bd in beatdowns)


def test_fetch_sql_beatdowns_naive_datetime_error(
    f3_test_database: Engine,
) -> None:
    """Test that fetch_sql_beatdowns raises error for naive datetime."""
    with Session(f3_test_database) as session:
        naive_dt = datetime(2023, 11, 14)  # noqa: DTZ001
        with pytest.raises(
            ValueError,
            match='datetime object must be timezone-aware',
        ):
            fetch_sql_beatdowns(session, after_timestamp=naive_dt)


def test_fetch_beatdowns_for_week_naive_datetime_error(
    f3_test_database: Engine,
) -> None:
    """Test that fetch_beatdowns_for_week raises error for naive datetime."""
    with Session(f3_test_database) as session:
        naive_dt = datetime(2024, 6, 3)  # noqa: DTZ001
        with pytest.raises(
            ValueError,
            match='datetime object must be timezone-aware',
        ):
            fetch_beatdowns_for_week(session, naive_dt)


def test_fetch_beatdowns_for_date_range_naive_datetime_error(
    f3_test_database: Engine,
) -> None:
    """Test that fetch_beatdowns_for_date_range raises error for naive datetime."""
    with Session(f3_test_database) as session:
        naive_start = datetime(2024, 1, 1)  # noqa: DTZ001
        naive_end = datetime(2024, 12, 31)  # noqa: DTZ001
        tz_aware_end = datetime(2024, 12, 31, tzinfo=UTC)

        # Test naive start_date
        with pytest.raises(
            ValueError,
            match='datetime object must be timezone-aware',
        ):
            fetch_beatdowns_for_date_range(session, naive_start, tz_aware_end)

        # Test naive end_date
        tz_aware_start = datetime(2024, 1, 1, tzinfo=UTC)
        with pytest.raises(
            ValueError,
            match='datetime object must be timezone-aware',
        ):
            fetch_beatdowns_for_date_range(session, tz_aware_start, naive_end)


def test_fetch_sql_users_all(f3_test_database: Engine) -> None:
    """Test fetching all users and verify we get expected fixture data."""
    with Session(f3_test_database) as session:
        users = fetch_sql_users(session)

        # Should return the users from our fixture
        assert len(users) > 0
        assert isinstance(users, list)

        # Verify we have specific users from fixture data
        user_names = [user.user_name for user in users]
        assert 'Steubie' in user_names
        assert 'Robotnik' in user_names

        # Check that each user has expected attributes
        assert all(hasattr(user, 'user_id') for user in users)
        assert all(hasattr(user, 'real_name') for user in users)


def test_fetch_sql_users_with_filter(f3_test_database: Engine) -> None:
    """Test fetching specific users by ID and verify their details."""
    with Session(f3_test_database) as session:
        # First get all users to see what IDs we have
        all_users = fetch_sql_users(session)

        if all_users:
            # Test fetching the first user specifically
            first_user_id = all_users[0].user_id
            filtered_users = fetch_sql_users(session, user_ids=[first_user_id])

            # Should return exactly one user
            assert len(filtered_users) == 1
            assert filtered_users[0].user_id == first_user_id

            # Verify it's the same user we expected
            assert filtered_users[0].user_name == all_users[0].user_name


def test_fetch_sql_aos_all(f3_test_database: Engine) -> None:
    """Test fetching all AOs and verify we get expected fixture data."""
    with Session(f3_test_database) as session:
        aos = fetch_sql_aos(session)

        # Should return the AOs from our fixture
        assert len(aos) > 0
        assert isinstance(aos, list)

        # Verify we have specific AOs from fixture data
        ao_names = [ao.ao for ao in aos]
        assert 'The Depot' in ao_names
        assert 'The Nest' in ao_names

        # Check that each AO has expected attributes
        assert all(hasattr(ao, 'channel_id') for ao in aos)
        assert all(hasattr(ao, 'ao') for ao in aos)


def test_fetch_sql_aos_with_filter(f3_test_database: Engine) -> None:
    """Test fetching specific AOs by channel ID and verify their details."""
    with Session(f3_test_database) as session:
        # First get all AOs to see what channel IDs we have
        all_aos = fetch_sql_aos(session)

        if all_aos:
            # Test fetching a specific AO
            first_channel_id = all_aos[0].channel_id
            filtered_aos = fetch_sql_aos(
                session,
                channel_ids=[first_channel_id],
            )

            # Should return exactly one AO
            assert len(filtered_aos) == 1
            assert filtered_aos[0].channel_id == first_channel_id

            # Verify it's the same AO we expected
            assert filtered_aos[0].ao == all_aos[0].ao
