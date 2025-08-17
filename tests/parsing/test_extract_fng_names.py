"""Tests for extract_fng_names function."""

from dataclasses import dataclass

import pytest

from f3_nation_data.parsing.backblast import extract_fng_names


@dataclass
class FngNamesTestCase:
    """Test case for FNG names extraction."""

    backblast: str
    expected_fng_names: list[str]
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        # Fixture 1: No FNGs
        FngNamesTestCase(
            """Backblast! Steubie's Way Too Long 3 Yr Anniversary Celebration Continues
DATE: 2024-03-09
AO: <#C04PD48V9KR>
Q: <@U04SUMEGFRV>
PAX: <@U04TCJ2GMF0> <@U063DJFFMB8> <@U06GQ7U4UHY> <@U06MLN75A7M> <@U060KCQ7Y0G> <@U04TBKAFFGC>
FNGs: None
COUNT: 7""",
            [],
            'fixture_1_no_fngs',
        ),
        # Fixture 3: One FNG named "Radio"
        FngNamesTestCase(
            """Backblast! 1% better, 1 % more!
DATE: 2024-03-14
AO: <#C04PD48V9KR>
Q: <@U05H7BV7X8A>
PAX: <@U04TBKAFFGC> <@U06MLN75A7M> <@U06GQ7U4UHY> <@U04TCJ2GMF0> , Radio
FNGs: 1 Radio
COUNT: 6""",
            ['Radio'],
            'fixture_3_one_fng_radio',
        ),
        # Fixture 6: One FNG named "Lil-Bit"
        FngNamesTestCase(
            """Backblast! Blink and another year has gone by
DATE: 2024-03-30
AO: <#C04PD48V9KR>
Q: <@U0518C64UDC>
PAX: <@U04SUMEGFRV> <@U0527GK0PKJ> <@U06GQ7U4UHY> <@U051R13N25D> <@U063DJFFMB8> <@U04TBKAFFGC> <@U05FLSDT8M6> <@U05H7BV7X8A> <@U05269QG9KQ> , Lil-Bit
FNGs: 1 Lil-Bit
COUNT: 11""",
            ['Lil-Bit'],
            'fixture_6_one_fng_lil_bit',
        ),
        # Fixture 4: Edge case where "None" is listed as FNG (should be filtered out)
        FngNamesTestCase(
            """Backblast! The Best & Worst of Humanity Ruck
DATE: 2024-03-25
AO: <#C04PD48V9KR>
Q: <@U05FLSDT8M6>
PAX: <@U04SUMEGFRV> <@U05TMS255DH> <@U05FLSDT8M6> , None
FNGs: 1 None
COUNT: 3""",
            [],  # "None" should be filtered out in extract_pax_from_string
            'fixture_4_none_as_fng',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_fng_names_from_fixtures(tcase: FngNamesTestCase):
    """Test FNG names extraction using real fixture data."""
    actual_fng_names = extract_fng_names(tcase.backblast)

    assert set(actual_fng_names) == set(tcase.expected_fng_names), (
        f'FNG names failed for {tcase.test_id}: expected {tcase.expected_fng_names}, got {actual_fng_names}'
    )


def test_extract_fng_names_no_fng_field():
    """Test handling when there's no FNG field at all."""
    backblast = """Backblast! Test
DATE: 2024-03-09
AO: <#C04PD48V9KR>
Q: <@U04SUMEGFRV>
PAX: <@U04TCJ2GMF0>, Radio
COUNT: 2"""

    # No FNG field, so should return empty list even if non-registered names exist
    assert extract_fng_names(backblast) == []


def test_extract_fng_names_case_insensitive():
    """Test that FNG field matching is case insensitive."""
    backblast = """Backblast! Test
DATE: 2024-03-09
AO: <#C04PD48V9KR>
Q: <@U04SUMEGFRV>
PAX: <@U04TCJ2GMF0>, Radio
fngs: 1 radio
COUNT: 2"""

    # Should find "Radio" even though FNG field is lowercase "radio"
    assert extract_fng_names(backblast) == ['Radio']
