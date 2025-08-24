import os
import sys
from datetime import UTC, datetime
from textwrap import dedent
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import Engine

from f3_nation_data.cli import weekly_report

EXPECTED_REPORT = dedent("""
    ```
    :noho: F3 NoHo Weekly Beatdown Report
    Week of March 04 - March 10, 2024

    📊 Week Summary: 1 beatdowns, 7 total attendance, 7 unique PAX



    📈 Highest Attended Workout at Each AO:
     7 #the depot (Q: @Steubie) on 08/23/2025 - Breakfast Bonanza

    💪 Top HIMs Who Posted This Week:
    1 @Hose
    1 @Kohl's
    1 @Olean
    1 @Prairie Dog
    1 @Splinter
    1 @Steubie
    1 @Zero Turn
    👑 Leaders in Q Counts:
    • No one has Q'd 2 or more times this week

    🏆 AO Stats:
    - 7 posts — #The Depot (avg 7 per BD)
        - 1 BDs, 7 Unique Pax
    REGION TOTAL: 7 posts, 1 beatdowns, 7 unique PAX




    🏆 AO Stats:

    | AO Name              | BDs/DDs | Unique PAX | Posts | Avg PAX/BD |
    |----------------------|---------|------------|-------|------------|
    | The Depot            |       1 |          7 |     7 |          7 |
    |----------------------|---------|------------|-------|------------|
    | REGION TOTAL         |       1 |          7 |     7 |      -     |

    ```
""")


@pytest.mark.usefixtures('f3_test_database')
def test_weekly_report_cli_output(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
    f3_test_database: Engine,
) -> None:
    # Patch environment variable
    mocker.patch.dict(os.environ, {'F3_NATION_DATABASE': 'f3noho'})
    # Patch get_sql_engine to use the test database
    mocker.patch.object(
        weekly_report,
        'get_sql_engine',
        return_value=f3_test_database,
    )
    # Patch sys.argv to simulate CLI call with a fixed date argument matching the test data
    mocker.patch.object(sys, 'argv', ['weekly_report', '2024-03-09'])

    # Run main and capture output
    weekly_report.main()
    captured = capsys.readouterr()
    output = captured.out

    # Compare to expected report
    assert output.strip() == EXPECTED_REPORT.strip()


def test_invalid_date_argument(
    mocker: MockerFixture,
    capsys: pytest.CaptureFixture,
):
    # Patch sys.argv to simulate CLI call with invalid date
    mocker.patch.object(sys, 'argv', ['weekly_report', 'not-a-date'])
    with pytest.raises(SystemExit) as excinfo:
        weekly_report.main()
    captured = capsys.readouterr()
    assert 'Invalid date format' in captured.err or 'Invalid date format' in captured.out
    assert excinfo.value.code == 2  # argparse exits with code 2 for argument errors


def test_no_beatdowns_found(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    # Patch environment variable
    mocker.patch.dict(os.environ, {'F3_NATION_DATABASE': 'f3noho'})
    # Patch get_sql_engine to return a dummy engine
    mocker.patch.object(weekly_report, 'get_sql_engine', return_value=None)
    # Patch fetch_beatdowns_for_date_range to return empty list
    mocker.patch.object(
        weekly_report,
        'fetch_beatdowns_for_date_range',
        return_value=[],
    )
    # Patch sys.argv to simulate CLI call with a fixed date argument
    mocker.patch.object(sys, 'argv', ['weekly_report', '2024-03-09'])
    # Patch get_user_mapping and get_ao_mapping to return empty dicts
    mocker.patch.object(weekly_report, 'get_user_mapping', return_value={})
    mocker.patch.object(weekly_report, 'get_ao_mapping', return_value={})

    # Patch Session to be a no-op context manager using MagicMock

    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock
    session_mock.__exit__.return_value = None
    mocker.patch.object(weekly_report, 'Session', return_value=session_mock)
    with pytest.raises(SystemExit) as excinfo:
        weekly_report.main()
    assert excinfo.value.code == 1
    # Logging output is captured by caplog
    assert 'No beatdowns found for week' in caplog.text


def test_weekly_report_cli_default_week(
    mocker: MockerFixture,
    f3_test_database: Engine,
) -> None:
    # Patch environment variable
    mocker.patch.dict(os.environ, {'F3_NATION_DATABASE': 'f3noho'})
    # Patch get_sql_engine to use the test database
    mocker.patch.object(
        weekly_report,
        'get_sql_engine',
        return_value=f3_test_database,
    )
    # Patch sys.argv to simulate CLI call with no date argument
    mocker.patch.object(sys, 'argv', ['weekly_report'])
    # Patch get_week_range to always return a fixed week for deterministic output
    mocker.patch.object(
        weekly_report,
        'get_week_range',
        return_value=(
            datetime(2024, 3, 4, tzinfo=UTC),
            datetime(2024, 3, 10, tzinfo=UTC),
        ),
    )
    # Patch other dependencies as needed for deterministic output
    mocker.patch.object(weekly_report, 'get_user_mapping', return_value={})
    mocker.patch.object(weekly_report, 'get_ao_mapping', return_value={})
    mocker.patch.object(
        weekly_report,
        'fetch_beatdowns_for_date_range',
        return_value=[],
    )
    # Patch Session to be a no-op context manager using MagicMock
    session_mock = MagicMock()
    session_mock.__enter__.return_value = session_mock
    session_mock.__exit__.return_value = None
    mocker.patch.object(weekly_report, 'Session', return_value=session_mock)
    with pytest.raises(SystemExit) as excinfo:
        weekly_report.main()
    assert excinfo.value.code == 1


def test_weekly_report_cli_error_handling(
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
):
    # Patch environment variable
    mocker.patch.dict(os.environ, {'F3_NATION_DATABASE': 'f3noho'})
    # Patch sys.argv to simulate CLI call
    mocker.patch.object(sys, 'argv', ['weekly_report', '2024-03-09'])
    # Patch generate_weekly_report to raise OSError
    mocker.patch.object(
        weekly_report,
        'generate_weekly_report',
        side_effect=OSError('Test OSError'),
    )
    with pytest.raises(SystemExit) as excinfo:
        weekly_report.main()
    assert excinfo.value.code == 1
    assert 'Error generating report' in caplog.text
