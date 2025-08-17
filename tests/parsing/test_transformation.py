"""Tests for SQL to parsed beatdown transformation."""

from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.models.sql.beatdown import SqlBeatDownModel
from f3_nation_data.parsing.backblast import transform_sql_to_parsed_beatdown


@dataclass
class TransformTestCase:
    sql_timestamp: str
    sql_ts_edited: str
    sql_backblast: str
    expected_title: str | None
    expected_q_user_id: str | None
    expected_coq_user_id: list[str] | None
    expected_pax: list[str] | None
    expected_non_registered_pax: list[str] | None
    expected_fngs: list[str]
    expected_bd_date: str | None
    expected_workout_type: str
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        TransformTestCase(
            sql_timestamp='2024-03-09T10:00:00',
            sql_ts_edited='2024-03-09T11:00:00',
            sql_backblast=dedent("""
                Backblast! Standard Beatdown
                DATE: 2024-03-09
                Q: <@U123456>
                COQ: <@U789012>, <@U345678>
                PAX: <@U111111>, <@U222222>, John, Jane
                FNG: John
                COUNT: 6

                WARMUP: SSH, Imperial Walkers
                THANG: Dora 1-2-1
                MARY: Crunches
                ANNOUNCEMENTS: Great workout!
                COT: Prayers for healing
            """).strip(),
            expected_title='Backblast! Standard Beatdown',
            expected_q_user_id='U123456',
            expected_coq_user_id=['U789012', 'U345678'],
            expected_pax=['U111111', 'U222222'],
            expected_non_registered_pax=['John', 'Jane'],
            expected_fngs=['John'],
            expected_bd_date='2024-03-09',
            expected_workout_type='bootcamp',
            test_id='complete_beatdown',
        ),
        TransformTestCase(
            sql_timestamp='2024-03-10T08:00:00',
            sql_ts_edited='2024-03-10T08:30:00',
            sql_backblast=dedent("""
                Backblast! Minimal Data
                Q: <@U123456>
                PAX: <@U111111>
                COUNT: 2
            """).strip(),
            expected_title='Backblast! Minimal Data',
            expected_q_user_id='U123456',
            expected_coq_user_id=None,
            expected_pax=['U111111'],
            expected_non_registered_pax=[],
            expected_fngs=[],
            expected_bd_date=None,
            expected_workout_type='bootcamp',
            test_id='minimal_data',
        ),
        TransformTestCase(
            sql_timestamp='2024-03-11T06:00:00',
            sql_ts_edited='2024-03-11T06:15:00',
            sql_backblast='',
            expected_title=None,
            expected_q_user_id=None,
            expected_coq_user_id=None,
            expected_pax=None,
            expected_non_registered_pax=None,
            expected_fngs=[],
            expected_bd_date=None,
            expected_workout_type='bootcamp',
            test_id='empty_backblast',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_transform_sql_to_parsed_beatdown(tcase: TransformTestCase):
    """Test transformation from SQL model to parsed beatdown."""  # Create SQL model
    sql_bd = SqlBeatDownModel(
        timestamp=tcase.sql_timestamp,
        ts_edited=tcase.sql_ts_edited,
        backblast=tcase.sql_backblast,
    )

    # Transform to parsed model
    parsed_bd = transform_sql_to_parsed_beatdown(sql_bd)

    # Verify core fields (convert datetime to string for comparison)
    assert parsed_bd.timestamp == tcase.sql_timestamp
    assert parsed_bd.last_edited == tcase.sql_ts_edited
    assert parsed_bd.raw_backblast == tcase.sql_backblast
    assert parsed_bd.title == tcase.expected_title
    assert parsed_bd.q_user_id == tcase.expected_q_user_id
    # Check COQ user IDs (order doesn't matter)
    if tcase.expected_coq_user_id:
        assert parsed_bd.coq_user_id is not None
        assert set(parsed_bd.coq_user_id) == set(tcase.expected_coq_user_id)
    else:
        assert parsed_bd.coq_user_id == tcase.expected_coq_user_id
    # Check PAX (order doesn't matter)
    if tcase.expected_pax:
        assert parsed_bd.pax is not None
        assert set(parsed_bd.pax) == set(tcase.expected_pax)
    else:
        assert parsed_bd.pax == tcase.expected_pax
    # Check non-registered PAX (order doesn't matter)
    if tcase.expected_non_registered_pax:
        assert parsed_bd.non_registered_pax is not None
        assert set(parsed_bd.non_registered_pax) == set(
            tcase.expected_non_registered_pax,
        )
    else:
        assert parsed_bd.non_registered_pax == tcase.expected_non_registered_pax
    assert parsed_bd.fngs == tcase.expected_fngs
    assert parsed_bd.bd_date == tcase.expected_bd_date
    assert parsed_bd.workout_type == tcase.expected_workout_type

    # Verify derived fields exist and are correct types
    assert isinstance(parsed_bd.pax_count, int)
    assert isinstance(parsed_bd.fng_count, int)
    assert isinstance(parsed_bd.has_announcements, bool)
    assert isinstance(parsed_bd.has_cot, bool)
    assert isinstance(parsed_bd.word_count, int)

    # Check that FNG count matches FNG names length (handle None case)
    if parsed_bd.fngs is not None:
        assert parsed_bd.fng_count == len(parsed_bd.fngs)
