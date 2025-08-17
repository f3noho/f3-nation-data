"""Tests for extract_pax_count function."""

from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.parsing.backblast import extract_pax_count


@dataclass
class PaxCountTestCase:
    """Test case for PAX count extraction."""

    backblast: str
    expected_count: int
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        # Raw backblast data from our fixtures (not parsed/human-readable)
        PaxCountTestCase(
            (
                "Backblast! Steubie's Way Too Long 3 Yr Anniversary Celebration Continues\n"
                'DATE: 2024-03-09\n'
                'AO: <#C04PD48V9KR>\n'
                'Q: <@U04SUMEGFRV>\n'
                'PAX: <@U04TCJ2GMF0> <@U063DJFFMB8> <@U06GQ7U4UHY> <@U06MLN75A7M> <@U060KCQ7Y0G> <@U04TBKAFFGC> \n'
                'FNGs: None\n'
                'COUNT: 7'
            ),
            7,  # Q: 1 Slack ID + PAX: 6 Slack IDs = 7 total
            'fixture_1_slack_ids_only',
        ),
        PaxCountTestCase(
            (
                'Backblast! Sunday Funday\n'
                'DATE: 2024-03-10\n'
                'AO: <#C04PD48V9KR>\n'
                'Q: <@U04SUMEGFRV>\n'
                'PAX: <@U05UGHKUFUN> <@U04RHPC0YN6> <@U04TBKAFFGC> <@U068PU4CS3A> \n'
                'FNGs: None\n'
                'COUNT: 5'
            ),
            5,  # Q: 1 Slack ID + PAX: 4 Slack IDs = 5 total
            'fixture_2_slack_ids_only',
        ),
        PaxCountTestCase(
            (
                'Backblast! 1% better, 1 % more!\n'
                'DATE: 2024-03-14\n'
                'AO: <#C04PD48V9KR>\n'
                'Q: <@U05H7BV7X8A>\n'
                'PAX: <@U04TBKAFFGC> <@U06MLN75A7M> <@U06GQ7U4UHY> <@U04TCJ2GMF0> , Radio\n'
                'FNGs: 1 Radio\n'
                'COUNT: 6'
            ),
            6,  # Q: 1 Slack ID + PAX: 4 Slack IDs + 1 non-registered (Radio) = 6 total
            'fixture_3_with_fng',
        ),
        PaxCountTestCase(
            (
                'Backblast! The Best & Worst of Humanity Ruck\n'
                'DATE: 2024-03-25\n'
                'AO: <#C04PD48V9KR>\n'
                'Q: <@U05FLSDT8M6>\n'
                'PAX: <@U04SUMEGFRV> <@U05TMS255DH> <@U05FLSDT8M6> , None\n'
                'FNGs: 1 None\n'
                'COUNT: 3'
            ),
            3,  # Q: 1 Slack ID + PAX: 3 Slack IDs (deduped) + 0 non-registered (None filtered) = 3 total
            'fixture_4_with_none_filtered',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_pax_count_from_fixtures(tcase: PaxCountTestCase):
    """Test PAX count extraction using real fixture data."""
    actual_count = extract_pax_count(tcase.backblast)

    assert actual_count == tcase.expected_count, (
        f'PAX count failed for {tcase.test_id}: expected {tcase.expected_count}, got {actual_count}'
    )


def test_extract_pax_count_ignores_explicit_count():
    """Test that the function ignores the explicit COUNT field and calculates its own."""
    # Use actual raw fixture format but change the COUNT to show it's ignored
    backblast = dedent("""
        Backblast! Test with Wrong Count
        DATE: 2024-03-09
        AO: <#C04PD48V9KR>
        Q: <@U04SUMEGFRV>
        PAX: <@U04TCJ2GMF0> <@U063DJFFMB8> <@U06GQ7U4UHY>
        COUNT: 999
    """)

    # Should calculate 4 (1 Q + 3 PAX), not use the COUNT: 999
    assert extract_pax_count(backblast) == 4
