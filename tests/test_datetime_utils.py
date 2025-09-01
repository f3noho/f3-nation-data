"""Tests for datetime utilities."""

from datetime import UTC, datetime

import pytest

from f3_nation_data.utils.datetime_utils import (
    ensure_timezone_aware,
    from_unix_timestamp,
    to_unix_timestamp,
)


class TestFromUnixTimestamp:
    """Test from_unix_timestamp function."""

    def test_valid_string_timestamp(self):
        """Test conversion from valid string timestamp."""
        timestamp_str = '1699531200.123456'  # Nov 9, 2023 12:00:00.123456 UTC
        result = from_unix_timestamp(timestamp_str)

        assert result is not None
        assert result.year == 2023
        assert result.month == 11
        assert result.day == 9
        assert result.hour == 12
        assert result.minute == 0
        assert result.second == 0
        assert result.microsecond == 123456
        assert result.tzinfo == UTC

    def test_valid_float_timestamp(self):
        """Test conversion from valid float timestamp."""
        timestamp_float = 1699531200.123456
        result = from_unix_timestamp(timestamp_float)

        assert result is not None
        assert result.year == 2023
        assert result.month == 11
        assert result.day == 9
        assert result.tzinfo == UTC

    def test_none_input(self):
        """Test None input returns None."""
        result = from_unix_timestamp(None)
        assert result is None

    def test_invalid_string(self):
        """Test invalid string input returns None."""
        result = from_unix_timestamp('invalid')
        assert result is None

    def test_invalid_type(self):
        """Test invalid type input returns None."""
        result = from_unix_timestamp([])  # type: ignore[arg-type]
        assert result is None


class TestToUnixTimestamp:
    """Test to_unix_timestamp function."""

    def test_valid_datetime(self):
        """Test conversion from valid timezone-aware datetime."""
        dt = datetime(2023, 11, 9, 12, 0, 0, 123456, tzinfo=UTC)
        result = to_unix_timestamp(dt)

        assert result is not None
        assert isinstance(result, float)
        assert result == 1699531200.123456

    def test_none_input(self):
        """Test None input returns None."""
        result = to_unix_timestamp(None)
        assert result is None

    def test_naive_datetime_raises_error(self):
        """Test that naive datetime raises ValueError."""
        dt = datetime(2023, 11, 9, 12, 0, 0)  # noqa: DTZ001
        with pytest.raises(
            ValueError,
            match='datetime object must be timezone-aware',
        ):
            to_unix_timestamp(dt)


class TestEnsureTimezoneAware:
    """Test ensure_timezone_aware function."""

    def test_already_timezone_aware(self):
        """Test datetime that is already timezone-aware."""
        dt = datetime(2023, 11, 9, 12, 0, 0, tzinfo=UTC)
        result = ensure_timezone_aware(dt)

        assert result == dt
        assert result.tzinfo == UTC

    def test_naive_datetime(self):
        """Test naive datetime gets UTC timezone added."""
        dt = datetime(2023, 11, 9, 12, 0, 0)  # noqa: DTZ001
        result = ensure_timezone_aware(dt)

        assert result.year == 2023
        assert result.month == 11
        assert result.day == 9
        assert result.hour == 12
        assert result.tzinfo == UTC
