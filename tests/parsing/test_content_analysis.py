"""Tests for word count and content checks."""

from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.parsing.backblast import (
    calculate_word_count,
    check_has_announcements,
    check_has_cot,
    extract_after_count,
)


@dataclass
class WordCountTestCase:
    backblast: str
    expected_count: int
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        WordCountTestCase(
            dedent("""
                Backblast! Test
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                This is the main content after count.
                It has multiple words for testing purposes.
            """),
            14,  # "This is the main content after count. It has multiple words for testing purposes."
            'basic_word_count',
        ),
        WordCountTestCase(
            dedent("""
                Backblast! No Content After Count
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
            """),
            13,  # Full backblast when no COUNT found
            'no_content_after_count',
        ),
        WordCountTestCase(
            dedent("""
                Backblast! No Count Line
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                
                This content should be counted entirely.
                Multiple lines of text here.
            """),
            21,  # Entire backblast content when no COUNT line
            'no_count_line',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_calculate_word_count(tcase: WordCountTestCase):
    """Test word count calculation."""
    assert calculate_word_count(tcase.backblast) == tcase.expected_count


@dataclass
class ContentCheckTestCase:
    backblast: str
    has_announcements: bool
    has_cot: bool
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        ContentCheckTestCase(
            dedent("""
                Backblast! With Both
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                ANNOUNCEMENTS: Welcome new PAX!
                COT: Prayers for healing.
            """),
            True,
            True,
            'both_present',
        ),
        ContentCheckTestCase(
            dedent("""
                Backblast! Announcements Only
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                ANNOUNCEMENTS: Check the calendar.
            """),
            True,
            False,
            'announcements_only',
        ),
        ContentCheckTestCase(
            dedent("""
                Backblast! COT Only
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                COT: Thoughts and prayers.
            """),
            False,
            True,
            'cot_only',
        ),
        ContentCheckTestCase(
            dedent("""
                Backblast! Neither
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                Just the workout content.
            """),
            False,
            False,
            'neither_present',
        ),
        ContentCheckTestCase(
            dedent("""
                Backblast! Empty Sections
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                ANNOUNCEMENTS:
                COT:
            """),
            False,
            False,
            'empty_sections',
        ),
        ContentCheckTestCase(
            dedent("""
                Backblast! Inline Content
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                ANNOUNCEMENTS: Great workout today!
                COT: Thanks for the support.
            """),
            True,
            True,
            'inline_content',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_content_checks(tcase: ContentCheckTestCase):
    """Test announcements and COT presence checks."""
    assert check_has_announcements(tcase.backblast) == tcase.has_announcements
    assert check_has_cot(tcase.backblast) == tcase.has_cot


@dataclass
class ExtractAfterCountTestCase:
    backblast: str
    expected_content: str | None
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        ExtractAfterCountTestCase(
            dedent("""
                Backblast! Test
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                This is after the count line.
                Multiple lines here.
            """),
            'This is after the count line.\nMultiple lines here.',
            'basic_extraction',
        ),
        ExtractAfterCountTestCase(
            dedent("""
                Backblast! No Count
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                
                No count line present.
            """),
            None,
            'no_count_line',
        ),
        ExtractAfterCountTestCase(
            dedent("""
                Backblast! Count at End
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2"""),
            None,  # No content after COUNT when at end
            'count_at_end',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_after_count(tcase: ExtractAfterCountTestCase):
    """Test extraction of content after COUNT line."""
    result = extract_after_count(tcase.backblast)
    if tcase.expected_content is None:
        assert result is None
    else:
        assert result == tcase.expected_content
