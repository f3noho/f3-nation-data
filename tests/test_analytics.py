"""Tests for analytics module functions."""

from datetime import UTC, datetime
from unittest.mock import Mock

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from f3_nation_data.analytics import (
    BeatdownDetails,
    HighestAttendanceResult,
    WeeklySummary,
    analyze_ao_attendance,
    analyze_fngs_by_ao,
    analyze_highest_attendance_per_ao,
    analyze_pax_attendance,
    analyze_q_counts,
    get_ao_mapping,
    get_beatdown_details,
    get_month_range,
    get_user_mapping,
    get_week_range,
    get_weekly_summary,
)
from f3_nation_data.fetch import _timestamp_to_datetime, fetch_sql_beatdowns
from f3_nation_data.models import ParsedBeatdown, SqlBeatDownModel
from f3_nation_data.transform import transform_sql_to_beatdown_record


def test_get_user_mapping(f3_test_database: Engine):
    """Test user mapping retrieval."""
    with Session(f3_test_database) as session:
        user_mapping = get_user_mapping(session)

        # Should have users from fixture data
        assert len(user_mapping) > 0
        assert isinstance(user_mapping, dict)

        # Check specific users from fixture
        assert 'U04SUMEGFRV' in user_mapping  # Steubie
        assert user_mapping['U04SUMEGFRV'] == 'Steubie'

        assert 'U05H7BV7X8A' in user_mapping  # Robotnik
        assert user_mapping['U05H7BV7X8A'] == 'Robotnik'


def test_get_ao_mapping(f3_test_database: Engine):
    """Test AO mapping retrieval."""
    with Session(f3_test_database) as session:
        ao_mapping = get_ao_mapping(session)

        # Should have AOs from fixture data
        assert len(ao_mapping) > 0
        assert isinstance(ao_mapping, dict)

        # Check specific AO from fixture
        assert 'C04PD48V9KR' in ao_mapping  # The Depot
        assert ao_mapping['C04PD48V9KR'] == 'The Depot'


def test_analyze_pax_attendance(f3_test_database: Engine):
    """Test PAX attendance analysis."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        pax_counts = analyze_pax_attendance(
            [transform_sql_to_beatdown_record(bd).backblast for bd in beatdowns],
        )

        # Should return dict with user IDs and counts
        assert isinstance(pax_counts, dict)

        # Should have some PAX from fixture data
        if pax_counts:
            assert all(isinstance(user_id, str) for user_id in pax_counts)
            assert all(isinstance(count, int) for count in pax_counts.values())
            assert all(count > 0 for count in pax_counts.values())


def test_analyze_ao_attendance(f3_test_database: Engine):
    """Test AO attendance analysis, including Qs and Co-Qs in posts."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        ao_mapping = get_ao_mapping(session)
        ao_stats = analyze_ao_attendance(
            [transform_sql_to_beatdown_record(bd).backblast for bd in beatdowns],
            ao_mapping,
        )

        # Should return dict with AO names and AOStats objects
        assert isinstance(ao_stats, dict)
        if ao_stats:
            for ao_name, stats in ao_stats.items():
                assert isinstance(ao_name, str)
                assert hasattr(stats, 'total_posts')
                assert hasattr(stats, 'total_beatdowns')
                assert hasattr(stats, 'unique_pax')
                # total_posts should be >= unique_pax_count (since Qs/Co-Qs may overlap)
                assert stats.total_posts >= stats.unique_pax_count()
                # total_posts should be >= total_beatdowns (at least one post per beatdown)
                assert stats.total_posts >= stats.total_beatdowns
                # unique_pax should be a set
                assert isinstance(stats.unique_pax, set)


def test_analyze_q_counts(f3_test_database: Engine):
    """Test Q leadership analysis."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        user_mapping = get_user_mapping(session)
        q_counts = analyze_q_counts(beatdowns, user_mapping)

        # Should return dict with Q names and counts
        assert isinstance(q_counts, dict)

        if q_counts:
            assert all(isinstance(q_name, str) for q_name in q_counts)
            assert all(isinstance(count, int) for count in q_counts.values())
            assert all(count > 0 for count in q_counts.values())


def test_analyze_fngs_by_ao(f3_test_database: Engine):
    """Test FNG analysis by AO."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        ao_mapping = get_ao_mapping(session)
        ao_fngs = analyze_fngs_by_ao(
            [transform_sql_to_beatdown_record(bd).backblast for bd in beatdowns],
            ao_mapping,
        )

        # Should return dict with AO names and FNG lists
        assert isinstance(ao_fngs, dict)

        if ao_fngs:
            assert all(isinstance(ao_name, str) for ao_name in ao_fngs)
            assert all(isinstance(fng_list, list) for fng_list in ao_fngs.values())


def test_analyze_highest_attendance_per_ao(f3_test_database: Engine):
    """Test highest attendance per AO analysis."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        ao_mapping = get_ao_mapping(session)
        user_mapping = get_user_mapping(session)

        ao_max = analyze_highest_attendance_per_ao(
            [transform_sql_to_beatdown_record(bd).backblast for bd in beatdowns],
            ao_mapping,
            user_mapping,
        )

        assert isinstance(ao_max, dict)

        if ao_max:
            assert len(ao_max) > 0

            # Check that all values are HighestAttendanceResult instances
            for ao_name, result in ao_max.items():
                assert isinstance(ao_name, str)
                assert isinstance(result, HighestAttendanceResult)
                assert isinstance(result.attendance_count, int)
                assert result.attendance_count >= 0
                assert isinstance(result.q_names, list)
                assert all(isinstance(q_name, str) for q_name in result.q_names)
                assert isinstance(result.date, str)
                assert isinstance(result.title, str)


def test_get_weekly_summary(f3_test_database: Engine):
    """Test comprehensive weekly summary."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        user_mapping = get_user_mapping(session)
        ao_mapping = get_ao_mapping(session)

        summary = get_weekly_summary(beatdowns, user_mapping, ao_mapping)

        # Should return WeeklySummary model
        assert isinstance(summary, WeeklySummary)

        # Check data types
        assert isinstance(summary.total_beatdowns, int)
        assert isinstance(summary.total_attendance, int)
        assert isinstance(summary.unique_pax, int)
        assert isinstance(summary.pax_counts, dict)
        assert isinstance(summary.ao_counts, dict)
        assert isinstance(summary.q_counts, dict)
        assert isinstance(summary.ao_fngs, dict)
        assert isinstance(summary.ao_max_attendance, dict)
        assert isinstance(summary.top_pax, list)
        assert isinstance(summary.top_aos, list)
        assert isinstance(summary.top_qs, list)


def test_get_beatdown_details(f3_test_database: Engine):
    """Test beatdown detail extraction."""
    with Session(f3_test_database) as session:
        beatdowns = fetch_sql_beatdowns(session)
        user_mapping = get_user_mapping(session)
        ao_mapping = get_ao_mapping(session)

        if beatdowns:
            details = get_beatdown_details(
                beatdowns[0],
                user_mapping,
                ao_mapping,
            )

            # Should return BeatdownDetails model
            assert isinstance(details, BeatdownDetails)

            # Check data types using dot notation
            assert isinstance(details.timestamp, (str, type(None)))
            assert isinstance(details.ao_name, str)
            assert isinstance(details.q_name, str)
            assert isinstance(details.title, str)
            assert isinstance(details.pax_count, int)
            assert isinstance(details.pax_names, list)
            assert isinstance(details.fng_names, list)
            assert isinstance(details.workout_type, str)
            assert isinstance(details.word_count, int)


def test_get_week_range():
    """Test week range calculation."""
    # Test with a known Wednesday (2024-03-13)
    test_date = datetime(
        2024,
        3,
        13,
        15,
        30,
        0,
        tzinfo=UTC,
    )  # Wednesday afternoon
    week_start, week_end = get_week_range(test_date)

    # Should give us Monday (March 11) to Sunday (March 17)
    assert week_start.year == 2024
    assert week_start.month == 3
    assert week_start.day == 11  # Monday
    assert week_start.hour == 0
    assert week_start.minute == 0
    assert week_start.second == 0

    assert week_end.year == 2024
    assert week_end.month == 3
    assert week_end.day == 17  # Sunday
    assert week_end.hour == 23
    assert week_end.minute == 59
    assert week_end.second == 59


def test_get_week_range_default():
    """Test week range with default (current) date."""
    week_start, week_end = get_week_range()

    # Should return datetime objects
    assert isinstance(week_start, datetime)
    assert isinstance(week_end, datetime)

    # Week should be 6 days long
    assert (week_end.date() - week_start.date()).days == 6

    # Start should be Monday (weekday 0)
    assert week_start.weekday() == 0


def test_get_month_range():
    """Test month range calculation."""
    # Test with March 15, 2024
    test_date = datetime(2024, 3, 15, tzinfo=UTC)
    month_start, month_end = get_month_range(test_date)

    # Should get March 1 to March 31
    assert month_start.date() == datetime(2024, 3, 1, tzinfo=UTC).date()
    assert month_end.date() == datetime(2024, 3, 31, tzinfo=UTC).date()

    # Check start time
    assert month_start.hour == 0
    assert month_start.minute == 0
    assert month_start.second == 0
    assert month_start.microsecond == 0


def test_get_month_range_december():
    """Test month range for December (year boundary)."""
    test_date = datetime(2024, 12, 15, tzinfo=UTC)
    month_start, month_end = get_month_range(test_date)

    # Should get December 1 to December 31
    assert month_start.date() == datetime(2024, 12, 1, tzinfo=UTC).date()
    assert month_end.date() == datetime(2024, 12, 31, tzinfo=UTC).date()


def test_get_month_range_default():
    """Test month range with default (current) date."""
    month_start, month_end = get_month_range()

    # Should start on first day of month
    assert month_start.day == 1

    # Month range should be at least 28 days (February)
    assert (month_end - month_start).days >= 27


def test_date_parsing_error_handling():
    """Test that date parsing errors are handled gracefully."""
    # Create a mock beatdown with invalid date to trigger exception handler
    mock_beatdown = SqlBeatDownModel(
        timestamp='1234567890.123456',
        ao_id='test_ao',
        q_user_id='test_user',
        backblast='Test backblast with invalid date\nDATE: invalid-date-format\nQIC: test\nPAX: user1, user2',
    )

    ao_mapping = {'test_ao': 'Test AO'}
    user_mapping = {'test_user': 'Test User'}

    # This should not crash, even with invalid date
    result = analyze_highest_attendance_per_ao(
        [transform_sql_to_beatdown_record(mock_beatdown).backblast],
        ao_mapping,
        user_mapping,
    )

    # Should still return a valid result with 'Unknown Date'
    assert isinstance(result, dict)
    if result:
        for attendance_result in result.values():
            assert attendance_result.date == 'Unknown Date'


def test_timestamp_to_datetime():
    """Test _timestamp_to_datetime function coverage."""
    # Test with a valid timestamp string
    timestamp_str = '1699555200.123456'  # Nov 9, 2023
    result = _timestamp_to_datetime(timestamp_str)

    assert result is not None
    assert result.year == 2023
    assert result.month == 11
    assert result.day == 9


def test_analyze_highest_attendance_invalid_date():
    """Test highest attendance analysis with invalid date format."""
    # Create mock beatdown with invalid date
    mock_beatdown = Mock(spec=SqlBeatDownModel)
    mock_beatdown.ao_id = 'C04TYQEEGHM'
    mock_beatdown.timestamp = '1234567890.123'

    # Mock parsed beatdown with invalid date
    mock_parsed = Mock()
    mock_parsed.ao_id = 'C04TYQEEGHM'
    mock_parsed.pax_count = 5
    mock_parsed.q_user_id = 'U04SUMEGFRV'
    mock_parsed.coq_user_id = []  # Ensure this is a list, not a Mock
    mock_parsed.bd_date = '2020-02-30'  # Invalid date (Feb 30th doesn't exist)
    mock_parsed.title = 'Test Beatdown'

    ao_mapping = {'C04TYQEEGHM': 'The Fort'}
    user_mapping = {'U04SUMEGFRV': 'Steubie'}

    result = analyze_highest_attendance_per_ao(
        [mock_parsed],
        ao_mapping,
        user_mapping,
    )

    # Should handle invalid date gracefully
    assert 'The Fort' in result
    fort_result = result['The Fort']
    assert isinstance(fort_result, HighestAttendanceResult)
    assert fort_result.attendance_count == 5
    assert fort_result.q_names == ['Steubie']
    assert fort_result.date == 'Unknown Date'  # Should fallback to 'Unknown Date'
    assert fort_result.title == 'Test Beatdown'


def test_q_and_pax_overlap():
    """Test attendance and Q counting when Q/Co-Q are also in PAX."""
    # Slack IDs
    slack_id = 'U12345'
    coq_id = 'U67890'
    # Sample beatdown: Q is also in PAX, plus a Co-Q
    parsed = ParsedBeatdown(
        raw_backblast='Test backblast content',
        ao_id='C1',
        pax=[slack_id, coq_id],
        q_user_id=slack_id,
        coq_user_id=[coq_id],
        fngs=[],
        bd_date='2025-08-18',
        pax_count=2,
        title='Overlap Test',
        word_count=10,
        workout_type='bootcamp',
    )
    # User mapping
    user_mapping = {slack_id: 'QMan', coq_id: 'CoQMan'}
    # Should count Q and Co-Q correctly, and attendance only once per user
    pax_counts = analyze_pax_attendance([parsed])
    q_counts = analyze_q_counts([parsed], user_mapping)

    assert pax_counts == {slack_id: 1, coq_id: 1}
    assert q_counts == {'QMan': 1, 'CoQMan': 1}
