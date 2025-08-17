"""Tests for database connection utilities."""

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from f3_nation_data import database
from f3_nation_data.database import (
    _get_required_env,
    create_session,
    db_session,
    get_sql_engine,
)


def test_get_required_env_success(mocker: MockerFixture) -> None:
    """Test getting an existing environment variable."""
    mocker.patch.dict('os.environ', {'TEST_VAR': 'test_value'})
    result = _get_required_env('TEST_VAR', 'Error message')
    assert result == 'test_value'


def test_get_required_env_missing(mocker: MockerFixture) -> None:
    """Test error when environment variable is missing."""
    mocker.patch.dict('os.environ', {}, clear=True)
    with pytest.raises(ValueError, match='Custom error message'):
        _get_required_env('MISSING_VAR', 'Custom error message')


def test_get_required_env_empty_string(mocker: MockerFixture) -> None:
    """Test error when environment variable is empty string."""
    mocker.patch.dict('os.environ', {'EMPTY_VAR': ''})
    with pytest.raises(ValueError, match='Variable is empty'):
        _get_required_env('EMPTY_VAR', 'Variable is empty')


def test_get_sql_engine_with_parameters() -> None:
    """Test engine creation with direct parameters."""
    engine = get_sql_engine(
        user='test_user',
        password='test_password',  # noqa: S106 - madeup test password
        host='localhost',
        database='test_db',
        port=3306,
    )

    assert isinstance(engine, Engine)
    # Check that the connection string is correct
    url = str(engine.url)
    assert 'test_user' in url
    assert 'localhost' in url
    assert 'test_db' in url
    assert '3306' in url


def test_get_sql_engine_with_env_vars(mocker: MockerFixture) -> None:
    """Test engine creation using environment variables."""
    env_vars = {
        'F3_NATION_USER': 'env_user',
        'F3_NATION_PASSWORD': 'env_password',
        'F3_NATION_HOST': 'env_host',
        'F3_NATION_DATABASE': 'env_db',
        'F3_NATION_PORT': '3307',
    }

    mocker.patch.dict('os.environ', env_vars)
    engine = get_sql_engine()

    assert isinstance(engine, Engine)
    url = str(engine.url)
    assert 'env_user' in url
    assert 'env_host' in url
    assert 'env_db' in url
    assert '3307' in url


def test_get_sql_engine_mixed_params_and_env(mocker: MockerFixture) -> None:
    """Test that direct parameters override environment variables."""
    env_vars = {
        'F3_NATION_USER': 'env_user',
        'F3_NATION_PASSWORD': 'env_password',
        'F3_NATION_HOST': 'env_host',
        'F3_NATION_DATABASE': 'env_db',
    }

    mocker.patch.dict('os.environ', env_vars)
    engine = get_sql_engine(
        user='param_user',
        host='param_host',
    )

    # Check URL components directly since password gets masked in string representation
    url = engine.url
    assert url.username == 'param_user'  # Parameter overrides env
    assert url.host == 'param_host'  # Parameter overrides env
    assert url.password == 'env_password'  # noqa: S105 - madeup test password
    assert url.database == 'env_db'  # Uses env var


def test_get_sql_engine_default_port(mocker: MockerFixture) -> None:
    """Test that port defaults to 3306 when not specified."""
    env_vars = {
        'F3_NATION_USER': 'user',
        'F3_NATION_PASSWORD': 'password',
        'F3_NATION_HOST': 'host',
        'F3_NATION_DATABASE': 'db',
    }

    mocker.patch.dict('os.environ', env_vars, clear=True)
    engine = get_sql_engine()
    url = str(engine.url)
    assert '3306' in url


def test_get_sql_engine_missing_user(mocker: MockerFixture) -> None:
    """Test error when username is missing."""
    mocker.patch.dict('os.environ', {}, clear=True)
    with pytest.raises(ValueError, match='Database username required'):
        get_sql_engine(
            password='password123',  # noqa: S106 - madeup test password
            host='host',
            database='db',
        )


def test_get_sql_engine_missing_password(mocker: MockerFixture) -> None:
    """Test error when password is missing."""
    mocker.patch.dict('os.environ', {}, clear=True)
    with pytest.raises(ValueError, match='Database password required'):
        get_sql_engine(
            user='user',
            host='host',
            database='db',
        )


def test_get_sql_engine_missing_host(mocker: MockerFixture) -> None:
    """Test error when host is missing."""
    mocker.patch.dict('os.environ', {}, clear=True)
    with pytest.raises(ValueError, match='Database host required'):
        get_sql_engine(
            user='user',
            password='password123',  # noqa: S106 - madeup test password
            database='db',
        )


def test_get_sql_engine_missing_database(mocker: MockerFixture) -> None:
    """Test error when database is missing."""
    mocker.patch.dict('os.environ', {}, clear=True)
    with pytest.raises(ValueError, match='Database name required'):
        get_sql_engine(
            user='user',
            password='password123',  # noqa: S106 - madeup test password
            host='host',
        )


def test_create_session(f3_test_database: Engine) -> None:
    """Test session creation from engine."""
    session = create_session(f3_test_database)

    assert isinstance(session, Session)
    assert session.bind == f3_test_database

    # Test that we can execute a query
    result = session.execute(text('SELECT 1 as test')).scalar()
    assert result == 1

    session.close()


def test_db_session_success(
    mocker: MockerFixture,
    f3_test_database: Engine,
) -> None:
    """Test successful database session context manager."""
    mock_get_engine = mocker.patch.object(database, 'get_sql_engine')
    mock_get_engine.return_value = f3_test_database

    with db_session(
        user='test',
        password='test',  # noqa: S106 - madeup test password
        host='test',
        database='test',
    ) as session:
        assert isinstance(session, Session)
        result = session.execute(text('SELECT 1 as test')).scalar()
        assert result == 1


def test_db_session_rollback_on_exception(
    mocker: MockerFixture,
    f3_test_database: Engine,
) -> None:
    """Test that session rolls back on exception."""
    mock_get_engine = mocker.patch.object(database, 'get_sql_engine')
    mock_get_engine.return_value = f3_test_database

    test_error_msg = 'Test error'

    def _test_context_with_error() -> None:
        with db_session(
            user='test',
            password='test',  # noqa: S106 - madeup test password
            host='test',
            database='test',
        ) as session:
            session.execute(text('SELECT 1'))
            raise ValueError(test_error_msg)

    with pytest.raises(ValueError, match=test_error_msg):
        _test_context_with_error()


def test_db_session_passes_parameters(
    mocker: MockerFixture,
    f3_test_database: Engine,
) -> None:
    """Test that db_session passes parameters to get_sql_engine."""
    mock_get_engine = mocker.patch.object(database, 'get_sql_engine')
    mock_get_engine.return_value = f3_test_database

    with db_session(
        user='test_user',
        password='test_pass',  # noqa: S106 - madeup test password
        host='test_host',
        database='test_db',
        port=3307,
    ):
        pass

    mock_get_engine.assert_called_once_with(
        'test_user',
        'test_pass',
        'test_host',
        'test_db',
        3307,
    )
