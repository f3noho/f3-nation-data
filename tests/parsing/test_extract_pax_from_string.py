"""Tests for extract_pax_from_string function."""

from dataclasses import dataclass

import pytest

from f3_nation_data.parsing.backblast import extract_pax_from_string


@dataclass
class PaxExtractionTestCase:
    """Test case for PAX extraction."""

    input_string: str
    expected_slack_ids: list[str]
    expected_non_registered_names: list[str]
    test_id: str = ''


@pytest.mark.parametrize(
    'tcase',
    [
        # Empty and None cases
        PaxExtractionTestCase('', [], [], 'empty_string'),
        PaxExtractionTestCase('   ', [], [], 'whitespace_only'),
        PaxExtractionTestCase('None', [], [], 'none_filtered_out'),
        PaxExtractionTestCase('N/A', [], [], 'na_filtered_out'),
        PaxExtractionTestCase('None, N/A', [], [], 'none_and_na_filtered'),
        # Only Slack IDs
        PaxExtractionTestCase(
            '<@U04SUMEGFRV>',
            ['U04SUMEGFRV'],
            [],
            'single_slack_id',
        ),
        PaxExtractionTestCase(
            '<@U04SUMEGFRV>, <@U05H7BV7X8A>',
            ['U04SUMEGFRV', 'U05H7BV7X8A'],
            [],
            'multiple_slack_ids',
        ),
        # Only non-registered names (comma-separated)
        PaxExtractionTestCase(
            'Lil-Bit',
            [],
            ['Lil-Bit'],
            'single_hyphenated_name',
        ),
        PaxExtractionTestCase(
            'Prairie Dog, Zero Turn',
            [],
            ['Prairie Dog', 'Zero Turn'],
            'multiple_space_containing_names',
        ),
        PaxExtractionTestCase(
            'Steubie, Zoom-Zoom, T-Bone',
            [],
            ['Steubie', 'Zoom-Zoom', 'T-Bone'],
            'multiple_mixed_names',
        ),
        # Mixed Slack IDs and names (comma-separated)
        PaxExtractionTestCase(
            '<@U04SUMEGFRV>, Prairie Dog, <@U05H7BV7X8A>',
            ['U04SUMEGFRV', 'U05H7BV7X8A'],
            ['Prairie Dog'],
            'mixed_slack_ids_and_names',
        ),
        PaxExtractionTestCase(
            '<@U123456789>, Lil-Bit',
            ['U123456789'],
            ['Lil-Bit'],
            'slack_id_with_hyphenated_name',
        ),
        # Mixed with filtered values
        PaxExtractionTestCase(
            '<@U123456789>, None, N/A',
            ['U123456789'],
            [],
            'slack_id_with_filtered_values',
        ),
        PaxExtractionTestCase(
            '<@U123456789>, Lil-Bit, None',
            ['U123456789'],
            ['Lil-Bit'],
            'slack_id_name_and_filtered',
        ),
        # Space-separated Slack IDs (gets converted to comma-separated by function)
        PaxExtractionTestCase(
            '<@U04SUMEGFRV> <@U05H7BV7X8A>',
            ['U04SUMEGFRV', 'U05H7BV7X8A'],
            [],
            'space_separated_slack_ids',
        ),
        # Real examples from original tests
        PaxExtractionTestCase(
            '<@U04SUMEGFRV>, <@U05TMS255DH>, <@U05FLSDT8M6>, None',
            ['U04SUMEGFRV', 'U05TMS255DH', 'U05FLSDT8M6'],
            [],
            'multiple_slack_ids_with_none',
        ),
        # Edge cases
        PaxExtractionTestCase(
            '<@INVALID>, regular-name',
            ['INVALID'],
            ['regular-name'],
            'malformed_slack_id_treated_as_name',
        ),
        PaxExtractionTestCase(
            '  Steubie   ,   T-Bone  ',
            [],
            ['Steubie', 'T-Bone'],
            'extra_whitespace_normalized',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_pax_from_string(tcase: PaxExtractionTestCase):
    """Test PAX extraction from various string formats."""
    slack_ids, names = extract_pax_from_string(tcase.input_string)

    # Convert to sets for comparison since order doesn't matter
    assert set(slack_ids) == set(tcase.expected_slack_ids), (
        f"Slack IDs failed for {tcase.test_id}: '{tcase.input_string}'"
    )
    assert set(names) == set(tcase.expected_non_registered_names), (
        f"Non-registered names failed for {tcase.test_id}: '{tcase.input_string}'"
    )
