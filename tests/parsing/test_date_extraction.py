from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.parsing.backblast import (
    extract_bd_date,
    extract_day_of_week,
)


@dataclass
class BdDateTestCase:
    backblast: str
    expected_date: str
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        BdDateTestCase(
            dedent("""
                Backblast! Steubie's Way Too Long 3 Yr Anniversary Celebration Continues
                DATE: 2024-03-09
                AO: <#C04PD48V9KR>
                Q: <@U04SUMEGFRV>
                PAX: <@U04TCJ2GMF0>
                COUNT: 7
            """),
            '2024-03-09',
            'fixture_1',
        ),
        BdDateTestCase(
            dedent("""
                Backblast! Sunday Funday
                DATE: 2024-03-10
                AO: <#C04PD48V9KR>
                Q: <@U04SUMEGFRV>
                PAX: <@U05UGHKUFUN>
                COUNT: 5
            """),
            '2024-03-10',
            'fixture_2',
        ),
        BdDateTestCase(
            dedent("""
                Backblast! 1% better, 1 % more!
                DATE: 2024-03-14
                AO: <#C04PD48V9KR>
                Q: <@U05H7BV7X8A>
                PAX: <@U04TBKAFFGC>
                COUNT: 6
            """),
            '2024-03-14',
            'fixture_3',
        ),
        BdDateTestCase(
            dedent("""
                Backblast! The Best & Worst of Humanity Ruck
                DATE: 2024-03-25
                AO: <#C04PD48V9KR>
                Q: <@U05FLSDT8M6>
                PAX: <@U04SUMEGFRV>
                COUNT: 3
            """),
            '2024-03-25',
            'fixture_4',
        ),
        BdDateTestCase(
            dedent("""
                Backblast! Friday Morning Ruck
                DATE: 2024-03-29
                AO: <#C04PD48V9KR>
                Q: <@U05H7BV7X8A>
                PAX: <@U068PU4CS3A>
                COUNT: 9
            """),
            '2024-03-29',
            'fixture_5',
        ),
        BdDateTestCase(
            dedent("""
                Backblast! Blink and another year has gone by
                DATE: 2024-03-30
                AO: <#C04PD48V9KR>
                Q: <@U0518C64UDC>
                PAX: <@U04SUMEGFRV>
                COUNT: 11
            """),
            '2024-03-30',
            'fixture_6',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_bd_date_from_samples(tcase: BdDateTestCase):
    """Test date extraction for realistic backblast samples."""
    assert extract_bd_date(tcase.backblast) == tcase.expected_date


@dataclass
class DateFormatTestCase:
    input_text: str
    expected: str | None
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        DateFormatTestCase('DATE: 2024-03-09', '2024-03-09', 'iso'),
        DateFormatTestCase('DATE: 2024/03/09', '2024-03-09', 'slash'),
        DateFormatTestCase('DATE: 03/09/2024', '2024-03-09', 'us'),
        # Malformed date (should return None)
        DateFormatTestCase('DATE: not-a-date', None, 'malformed'),
        # No date field at all (should return None)
        DateFormatTestCase('DATE: 2023-02-30', None, 'invalid'),
        DateFormatTestCase('Backblast! No date here', None, 'missing'),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_date_format_normalization(tcase: DateFormatTestCase):
    """Test that different date formats are normalized, and None for invalid/missing."""
    assert extract_bd_date(tcase.input_text) == tcase.expected


@dataclass
class DayOfWeekTestCase:
    date_str: str
    expected_day: str
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        DayOfWeekTestCase('2024-03-09', 'Saturday', 'sat'),
        DayOfWeekTestCase('2024-03-10', 'Sunday', 'sun'),
        DayOfWeekTestCase('2024-03-14', 'Thursday', 'thu'),
        DayOfWeekTestCase('2024-03-25', 'Monday', 'mon'),
        DayOfWeekTestCase('2024-03-29', 'Friday', 'fri'),
        DayOfWeekTestCase('2024-03-30', 'Saturday', 'sat2'),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_day_of_week(tcase: DayOfWeekTestCase):
    """Test day of week calculation for known dates."""
    assert extract_day_of_week(tcase.date_str) == tcase.expected_day


def test_extract_day_of_week_invalid_date():
    """Test day of week extraction with invalid date."""
    assert extract_day_of_week('invalid-date') is None
    assert extract_day_of_week('2024-13-45') is None  # Invalid month and day
