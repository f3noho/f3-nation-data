"""Tests for SQL to parsed beatdown transformation."""

from dataclasses import dataclass
from textwrap import dedent

import pytest

from f3_nation_data.models import SqlBeatDownModel
from f3_nation_data.transform import transform_sql_to_beatdown_record


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
    expected_ao_id: str | None
    test_id: str


@pytest.mark.parametrize(
    'tcase',
    [
        TransformTestCase(
            sql_timestamp='1710009600.0',  # 2024-03-09T10:00:00 UTC
            sql_ts_edited='1710013200.0',  # 2024-03-09T11:00:00 UTC
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
            expected_ao_id='C04TYQEEGHM',  # From SQL model since backblast doesn't have AO
            test_id='complete_beatdown',
        ),
        TransformTestCase(
            sql_timestamp='1710096000.0',  # 2024-03-10T08:00:00 UTC
            sql_ts_edited='1710097800.0',  # 2024-03-10T08:30:00 UTC
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
            expected_ao_id='C04TYQEEGHM',  # From SQL model
            test_id='minimal_data',
        ),
        TransformTestCase(
            sql_timestamp='1710182400.0',  # 2024-03-11T06:00:00 UTC
            sql_ts_edited='1710183300.0',  # 2024-03-11T06:15:00 UTC
            sql_backblast='',
            expected_title=None,
            expected_q_user_id=None,
            expected_coq_user_id=None,
            expected_pax=None,
            expected_non_registered_pax=None,
            expected_fngs=[],
            expected_bd_date=None,
            expected_workout_type='bootcamp',
            expected_ao_id='C04TYQEEGHM',  # From SQL model
            test_id='empty_backblast',
        ),
        TransformTestCase(
            sql_timestamp='1756051800.0',  # 2025-08-26T05:30:00 UTC
            sql_ts_edited='1756053600.0',  # 2025-08-26T06:00:00 UTC
            sql_backblast=dedent("""
                Backblast: DORA travels to Argentina!
                Date: 2025-08-26
                Time: 05:30
                Where: <#C08Q6RT19AQ>
                Q: <@U08QZ8KPZEJ>
                PAX: <@U098TJU4FT3> <@U06CYCFKHQQ> <@U09BYQMK4K0>
                FNG: None
                Count: 8

                WARMUP
            """).strip(),
            expected_title='Backblast: DORA travels to Argentina!',
            expected_q_user_id='U08QZ8KPZEJ',
            expected_coq_user_id=None,
            expected_pax=['U098TJU4FT3', 'U06CYCFKHQQ', 'U09BYQMK4K0'],
            expected_non_registered_pax=[],
            expected_fngs=[],
            expected_bd_date='2025-08-26',
            expected_workout_type='bootcamp',
            expected_ao_id='C08Q6RT19AQ',  # Extracted from "Where:" field
            test_id='where_field_ao_extraction',
        ),
        TransformTestCase(
            sql_timestamp='1710268800.0',  # 2024-03-12T07:00:00 UTC
            sql_ts_edited='1710270600.0',  # 2024-03-12T07:30:00 UTC
            sql_backblast=dedent("""
                Backblast: Morning Beatdown
                AO: <#C04PD48V9KR>
                Date: 2024-03-12
                Q: <@U123456>
                PAX: <@U111111>
                COUNT: 2
            """).strip(),
            expected_title='Backblast: Morning Beatdown',
            expected_q_user_id='U123456',
            expected_coq_user_id=None,
            expected_pax=['U111111'],
            expected_non_registered_pax=[],
            expected_fngs=[],
            expected_bd_date='2024-03-12',
            expected_workout_type='bootcamp',
            expected_ao_id='C04PD48V9KR',  # Extracted from "AO:" field
            test_id='ao_field_extraction',
        ),
    ],
    ids=lambda tcase: tcase.test_id,
)
def test_transform_sql_to_parsed_beatdown(tcase: TransformTestCase):
    """Test transformation from SQL model to parsed beatdown."""  # Create SQL model
    sql_bd = SqlBeatDownModel(
        ao_id='C04TYQEEGHM',  # Example AO ID
        timestamp=tcase.sql_timestamp,
        ts_edited=tcase.sql_ts_edited,
        backblast=tcase.sql_backblast,
    )

    # Transform to parsed model
    record = transform_sql_to_beatdown_record(sql_bd)
    parsed_bd = record.backblast

    # Verify core fields (convert datetime to Unix timestamp for comparison)
    assert record.timestamp.timestamp() == float(tcase.sql_timestamp)
    if tcase.sql_ts_edited:
        assert record.last_edited is not None
        assert record.last_edited.timestamp() == float(tcase.sql_ts_edited)
    else:
        assert record.last_edited is None
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
    assert parsed_bd.ao_id == tcase.expected_ao_id

    # Verify derived fields exist and are correct types
    assert isinstance(parsed_bd.pax_count, int)
    assert isinstance(parsed_bd.fng_count, int)
    assert isinstance(parsed_bd.has_announcements, bool)
    assert isinstance(parsed_bd.has_cot, bool)
    assert isinstance(parsed_bd.word_count, int)

    # Check that FNG count matches FNG names length (handle None case)
    if parsed_bd.fngs is not None:
        assert parsed_bd.fng_count == len(parsed_bd.fngs)
