"""Tests for workout type extraction."""

from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.parsing.backblast import extract_workout_type


@dataclass
class WorkoutTypeTestCase:
    backblast: str
    expected_type: str
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        # Standard bootcamp with warmup and thang
        WorkoutTypeTestCase(
            dedent("""
                Backblast! Standard Bootcamp
                DATE: 2024-03-09
                Q: <@U123>
                PAX: <@U456>
                COUNT: 2
                
                WARMUP: SSH, Imperial Walkers
                THANG: Dora 1-2-1
                MARY: Crunches
            """),
            'bootcamp',
            'bootcamp_with_structure',
        ),
        # Ruck with explicit ruck keyword
        WorkoutTypeTestCase(
            dedent("""
                Backblast! Friday Morning Ruck
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                This was a great ruck march through downtown.
                COUNT: 5
                
                We covered 3 miles with our rucksacks.
            """),
            'ruck',
            'explicit_ruck',
        ),
        # Ruck with "rucking" keyword
        WorkoutTypeTestCase(
            dedent("""
                Backblast! Early Morning
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                Rucking is the best way to start the day.
                COUNT: 3
            """),
            'ruck',
            'rucking_keyword',
        ),
        # Default to bootcamp when no clear indicators
        WorkoutTypeTestCase(
            dedent("""
                Backblast! Unknown Type
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                COUNT: 4
                
                Some content here.
            """),
            'bootcamp',
            'default_bootcamp',
        ),
        # Bootcamp without warmup but with thang
        WorkoutTypeTestCase(
            dedent("""
                Backblast! No Warmup
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                COUNT: 4
                
                THANG: Main workout
            """),
            'bootcamp',
            'thang_only',
        ),
        # Bootcamp with warmup but no thang
        WorkoutTypeTestCase(
            dedent("""
                Backblast! No Thang
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                COUNT: 4
                
                WARMUP: SSH
            """),
            'bootcamp',
            'warmup_only',
        ),
        # Test "ruck march" variant
        WorkoutTypeTestCase(
            dedent("""
                Backblast! March Time
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                Today's ruck march was challenging.
                COUNT: 4
            """),
            'ruck',
            'ruck_march',
        ),  # Test case where "ruck" appears after COUNT (should be bootcamp)
        WorkoutTypeTestCase(
            dedent("""
                Backblast! After Count Discussion
                DATE: 2024-03-29
                Q: <@U123>
                PAX: <@U456>
                COUNT: 4

                Today we talked about future ruck preparation.
            """),
            'bootcamp',
            'ruck_after_count',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_extract_workout_type(tcase: WorkoutTypeTestCase):
    """Test workout type extraction for various scenarios."""
    assert extract_workout_type(tcase.backblast) == tcase.expected_type
