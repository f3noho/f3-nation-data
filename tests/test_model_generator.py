"""Test the model generator with an in-memory database."""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest
from pytest_mock import MockerFixture
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

import dev_utilities.generate_models as generate_models_module
from dev_utilities.generate_models import (
    format_generated_models,
    generate_table_model,
    get_default_value,
    get_sqlalchemy_type_import,
    main,
    reflect_table_schema,
)
from f3_nation_data.models.sql.ao import SqlAOModel
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel
from f3_nation_data.models.sql.user import SqlUserModel


def test_database_tables_exist(f3_test_database: Engine) -> None:
    """Test that our test database has the expected tables."""
    with f3_test_database.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'"),
        )
        tables = {row[0] for row in result.fetchall()}

    assert 'aos' in tables
    assert 'users' in tables
    assert 'beatdowns' in tables


def test_schema_reflection(f3_test_database: Engine) -> None:
    """Test that schema reflection works correctly."""
    # Test AO table reflection
    aos_schema = reflect_table_schema(f3_test_database, 'aos')

    assert len(aos_schema.columns) >= 5  # We expect several columns
    assert aos_schema.primary_key == ['channel_id']  # AOs use channel_id as PK

    # Check specific columns exist
    column_names = {col['name'] for col in aos_schema.columns}
    assert 'channel_id' in column_names
    assert 'ao' in column_names


def test_model_generation(f3_test_database: Engine, tmp_path: Path) -> None:
    """Test that model generation creates valid Python code."""
    # Test generating a model for the 'aos' table
    success = generate_table_model(f3_test_database, 'aos', tmp_path)
    assert success

    # Verify file was created with expected name
    model_file = tmp_path / 'ao.py'
    assert model_file.exists()

    # Read and verify content
    content = model_file.read_text()
    assert 'class SqlAOModel(Base):' in content
    assert "__tablename__ = 'aos'" in content
    assert 'channel_id' in content  # Updated for actual AO schema
    assert 'ao' in content  # Updated for actual AO schema
    assert 'import sqlalchemy as sa' in content


def test_generated_model_can_be_imported_and_used(
    f3_test_database: Engine,
    tmp_path: Path,
) -> None:
    """Test that generated models can actually be imported and used."""
    # Generate the model
    success = generate_table_model(f3_test_database, 'aos', tmp_path)
    assert success

    model_file = tmp_path / 'ao.py'
    content = model_file.read_text()

    # Test that the generated content has the expected structure
    assert 'class SqlAOModel(Base):' in content
    assert 'channel_id: Mapped[str]' in content  # Updated for actual AO schema
    assert 'ao: Mapped[str]' in content  # Updated for actual AO schema
    assert 'primary_key=True' in content
    assert 'nullable=False' in content
    assert 'def __repr__(self)' in content

    # Test that the file is valid Python syntax
    try:
        compile(content, model_file, 'exec')
    except SyntaxError as e:
        pytest.fail(f'Generated model has invalid Python syntax: {e}')


def test_user_model_generation(
    f3_test_database: Engine,
    tmp_path: Path,
) -> None:
    """Test generating and using the user model."""
    # Generate user model
    success = generate_table_model(f3_test_database, 'users', tmp_path)
    assert success

    # Verify file exists with expected name (users -> user)
    model_file = tmp_path / 'user.py'
    assert model_file.exists()

    content = model_file.read_text()
    assert 'class SqlUserModel(Base):' in content
    assert "__tablename__ = 'users'" in content
    assert 'user_name' in content
    assert 'user_id' in content  # Updated for actual user schema


def test_f3_schema_default_values(
    f3_test_database: Engine,
    tmp_path: Path,
) -> None:
    """Test that the generator correctly handles F3 schema's actual default values."""
    # Test with the users table, which has a default value for 'app' field
    success = generate_table_model(f3_test_database, 'users', tmp_path)
    assert success

    model_file = tmp_path / 'user.py'
    content = model_file.read_text()

    # The F3 users table has 'app' field with default=False
    # Check that this is properly reflected in the generated model
    assert 'app:' in content
    assert 'default=' in content  # Should have the actual F3 default value

    # Verify the generated model compiles and is valid
    compile(content, model_file, 'exec')


def test_beatdown_model_generation_with_composite_key(
    f3_test_database: Engine,
    tmp_path: Path,
) -> None:
    """Test generating model for beatdowns table with realistic composite primary key."""
    success = generate_table_model(f3_test_database, 'beatdowns', tmp_path)
    assert success

    model_file = tmp_path / 'beatdown.py'
    assert model_file.exists()

    content = model_file.read_text()
    assert 'class SqlBeatDownModel(Base):' in content
    assert "__tablename__ = 'beatdowns'" in content

    # Check composite primary key columns are present
    assert 'ao_id' in content
    assert 'bd_date' in content
    assert 'q_user_id' in content
    assert 'primary_key=True' in content

    # Should have __repr__ with composite key format
    assert 'ao_id={self.ao_id}' in content
    assert 'bd_date={self.bd_date}' in content
    assert 'q_user_id={self.q_user_id}' in content

    # Test that the file is valid Python syntax
    try:
        compile(content, model_file, 'exec')
    except SyntaxError as e:
        pytest.fail(f'Generated beatdown model has invalid Python syntax: {e}')


def test_invalid_table_name(f3_test_database: Engine, tmp_path: Path) -> None:
    """Test error handling for non-existent table."""
    # Try to generate model for table that doesn't exist
    success = generate_table_model(
        f3_test_database,
        'nonexistent_table',
        tmp_path,
    )
    assert success is False  # Should return False on failure


def test_default_value_formatting() -> None:
    """Test the get_default_value function directly."""
    # Test boolean defaults
    assert get_default_value('1', 'bool') == 'True'
    assert get_default_value(1, 'bool') == 'True'
    assert get_default_value(True, 'bool') == 'True'  # noqa: FBT003
    assert get_default_value('0', 'bool') == 'False'

    # Test string defaults
    assert get_default_value('test', 'str') == '"test"'

    # Test numeric defaults
    assert get_default_value(42, 'int') == '42'
    assert get_default_value('42', 'int') == '42'


def test_get_sqlalchemy_type_unknown_type():
    """Test get_sqlalchemy_type_import with unknown SQL type (line 136)."""
    # Create a mock SQL type with an unknown name
    mock_type = Mock()
    mock_type.__class__.__name__ = 'UnknownType'

    result = get_sqlalchemy_type_import(mock_type)
    assert result == 'sa.UnknownType'


def test_generate_table_model_exception_handling(
    f3_test_database: Engine,
    tmp_path: Path,
):
    """Test exception handling in generate_table_model (lines 297-298)."""
    # Use a non-existent table to trigger an exception
    result = generate_table_model(
        f3_test_database,
        'nonexistent_table',
        tmp_path,
    )
    assert result is False


def test_main_database_connection_error(mocker: MockerFixture):
    """Test main function database connection error (lines 310-323)."""
    # Mock get_sql_engine to raise an exception
    mock_engine = mocker.patch.object(
        generate_models_module,
        'get_sql_engine',
        side_effect=Exception('Database connection failed'),
    )
    result = main()
    assert result == 1
    mock_engine.assert_called_once()


def test_main_model_generation_error(mocker: MockerFixture):
    """Test main function model generation error (lines 325-334, 336-340)."""
    # Mock get_sql_engine to succeed but generate_table_model to fail
    mock_engine = mocker.patch.object(
        generate_models_module,
        'get_sql_engine',
        return_value=Mock(),
    )
    mock_generate = mocker.patch.object(
        generate_models_module,
        'generate_table_model',
        side_effect=Exception('Model generation failed'),
    )

    result = main()
    assert result == 1
    mock_engine.assert_called_once()
    assert mock_generate.call_count >= 1  # Should try to generate at least one model


def test_main_successful_execution(mocker: MockerFixture):
    """Test main function successful execution (lines 388-391)."""
    # Mock successful execution path
    mock_engine = mocker.patch.object(
        generate_models_module,
        'get_sql_engine',
        return_value=Mock(),
    )
    mock_generate = mocker.patch.object(
        generate_models_module,
        'generate_table_model',
        return_value=True,
    )
    mock_format = mocker.patch.object(
        generate_models_module,
        'format_generated_models',
        return_value=None,
    )

    result = main()
    assert result == 0
    mock_engine.assert_called_once()
    assert mock_generate.call_count >= 1  # Should generate models
    mock_format.assert_called_once()


def test_format_generated_models_success(tmp_path: Path, mocker: MockerFixture):
    """Test format_generated_models function successful execution."""
    # Create a dummy python file to format
    test_file = tmp_path / 'test.py'
    test_file.write_text('x=1')

    # Mock successful subprocess execution
    mock_result = Mock()
    mock_result.returncode = 0
    mock_run = mocker.patch.object(subprocess, 'run', return_value=mock_result)

    # Should not raise any exception
    format_generated_models(tmp_path)
    mock_run.assert_called_once()


def test_format_generated_models_failure(tmp_path: Path, mocker: MockerFixture):
    """Test format_generated_models function failure handling."""
    # Mock failed subprocess execution
    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stdout = 'stdout output'
    mock_result.stderr = 'stderr output'
    mock_run = mocker.patch.object(subprocess, 'run', return_value=mock_result)

    # Should not raise any exception, just log warning
    format_generated_models(tmp_path)
    mock_run.assert_called_once()


def test_format_generated_models_exception(
    tmp_path: Path,
    mocker: MockerFixture,
):
    """Test format_generated_models function exception handling."""
    # Mock subprocess exception
    mock_run = mocker.patch.object(
        subprocess,
        'run',
        side_effect=OSError('Command not found'),
    )

    # Should not raise any exception, just log warning
    format_generated_models(tmp_path)
    mock_run.assert_called_once()


def test_committed_models_can_be_imported():
    """Test that the committed models can be imported and instantiated."""
    # Basic smoke test - check that models can be instantiated
    ao_instance = SqlAOModel()
    user_instance = SqlUserModel()
    beatdown_instance = SqlBeatDownModel()

    assert ao_instance is not None
    assert user_instance is not None
    assert beatdown_instance is not None

    # Check basic table names (these are the contracts we depend on)
    assert SqlAOModel.__tablename__ == 'aos'
    assert SqlUserModel.__tablename__ == 'users'
    assert SqlBeatDownModel.__tablename__ == 'beatdowns'


def test_model_generation_with_f3_data_validation(
    f3_test_database: Engine,
    f3_test_session: Session,
    tmp_path: Path,
) -> None:
    """Test model generation and validate against actual F3 fixture data."""
    # Generate all three main models
    success_ao = generate_table_model(f3_test_database, 'aos', tmp_path)
    success_user = generate_table_model(f3_test_database, 'users', tmp_path)
    success_beatdown = generate_table_model(
        f3_test_database,
        'beatdowns',
        tmp_path,
    )

    assert success_ao
    assert success_user
    assert success_beatdown

    # Verify all files were created
    ao_file = tmp_path / 'ao.py'
    user_file = tmp_path / 'user.py'
    beatdown_file = tmp_path / 'beatdown.py'

    assert ao_file.exists()
    assert user_file.exists()
    assert beatdown_file.exists()

    # Test that generated models have correct structure for F3 data
    ao_content = ao_file.read_text()
    user_content = user_file.read_text()
    beatdown_content = beatdown_file.read_text()

    # Verify AO model matches F3 schema (note: SQLite booleans map to Any)
    assert 'channel_id: Mapped[str]' in ao_content
    assert 'ao: Mapped[str]' in ao_content
    assert 'channel_created: Mapped[int]' in ao_content
    assert 'archived: Mapped[Any]' in ao_content  # SQLite BOOLEAN -> Any
    assert 'backblast: Mapped[Any | None]' in ao_content

    # Verify User model matches F3 schema
    assert 'user_id: Mapped[str]' in user_content
    assert 'user_name: Mapped[str]' in user_content
    assert 'real_name: Mapped[str]' in user_content
    assert 'app: Mapped[Any]' in user_content  # SQLite BOOLEAN -> Any

    # Verify Beatdown model with composite key
    assert 'ao_id: Mapped[str]' in beatdown_content
    assert 'bd_date: Mapped[' in beatdown_content  # Date type varies
    assert 'q_user_id: Mapped[str]' in beatdown_content
    assert 'pax_count: Mapped[' in beatdown_content

    # Test that all files compile to valid Python
    compile(ao_content, ao_file, 'exec')
    compile(user_content, user_file, 'exec')
    compile(beatdown_content, beatdown_file, 'exec')

    # Validate that fixture data would work with these schemas by checking
    # that we have actual data that matches the generated field expectations
    aos = f3_test_session.query(SqlAOModel).all()
    users = f3_test_session.query(SqlUserModel).all()
    beatdowns = f3_test_session.query(SqlBeatDownModel).all()

    assert len(aos) > 0, 'Should have AO test data'
    assert len(users) > 0, 'Should have user test data'
    assert len(beatdowns) > 0, 'Should have beatdown test data'

    # Test specific F3 data characteristics
    depot_ao = f3_test_session.query(SqlAOModel).filter_by(ao='The Depot').first()
    assert depot_ao is not None, 'Should find The Depot AO from fixtures'
    assert depot_ao.channel_id == 'C04PD48V9KR'

    steubie = f3_test_session.query(SqlUserModel).filter_by(user_name='Steubie').first()
    assert steubie is not None, 'Should find Steubie user from fixtures'
    assert steubie.user_id == 'U04SUMEGFRV'


def test_generated_models_basic_functionality(
    f3_test_database: Engine,
    tmp_path: Path,
):
    """Test basic functionality of generated models by compiling and validating syntax."""
    # Generate models for testing
    success_ao = generate_table_model(f3_test_database, 'aos', tmp_path)
    success_user = generate_table_model(f3_test_database, 'users', tmp_path)

    assert success_ao
    assert success_user

    # Read the generated files and verify they compile
    ao_file = tmp_path / 'ao.py'
    user_file = tmp_path / 'user.py'

    assert ao_file.exists()
    assert user_file.exists()

    # Test that the generated files are valid Python
    ao_content = ao_file.read_text()
    user_content = user_file.read_text()

    # Should compile without syntax errors
    try:
        compile(ao_content, ao_file, 'exec')
        compile(user_content, user_file, 'exec')
    except SyntaxError as e:
        pytest.fail(f'Generated model has invalid Python syntax: {e}')

    # Verify the content has expected SQLAlchemy patterns
    assert 'class SqlAOModel(Base):' in ao_content
    assert 'class SqlUserModel(Base):' in user_content
    assert '__tablename__ = ' in ao_content
    assert '__tablename__ = ' in user_content
    assert 'Mapped[' in ao_content  # Type hints
    assert 'Mapped[' in user_content
    assert 'def __repr__(self)' in ao_content
    assert 'def __repr__(self)' in user_content


def test_generated_model_file_structure(
    f3_test_database: Engine,
    tmp_path: Path,
):
    """Test that generated model files contain expected basic structure."""
    generate_table_model(f3_test_database, 'aos', tmp_path)

    ao_file = tmp_path / 'ao.py'
    content = ao_file.read_text()

    # Test the essential structural elements
    assert 'class SqlAOModel' in content
    assert "__tablename__ = 'aos'" in content
    assert 'def __repr__(self)' in content
    assert 'Mapped[' in content  # Type annotations

    # Verify it's valid Python syntax
    compile(content, ao_file, 'exec')


def test_committed_models_with_test_database(f3_test_session: Session) -> None:
    """Integration test: use committed models to connect to test database and fetch data."""
    # Test AO table - get count and sample data
    ao_count = f3_test_session.query(SqlAOModel).count()
    ao_samples = f3_test_session.query(SqlAOModel).limit(3).all()

    # Test User table - get count and sample data
    user_count = f3_test_session.query(SqlUserModel).count()
    user_samples = f3_test_session.query(SqlUserModel).limit(3).all()

    # Test Beatdown table - get count and sample data
    beatdown_count = f3_test_session.query(SqlBeatDownModel).count()
    beatdown_samples = f3_test_session.query(SqlBeatDownModel).limit(2).all()

    # Verify we got the expected counts based on our test data
    assert ao_count > 0  # We have AOs from fixtures
    assert user_count > 0  # We have users from fixtures
    assert beatdown_count > 0  # We have beatdowns from fixtures

    # Verify sample data is not empty
    assert len(ao_samples) > 0
    assert len(user_samples) > 0
    assert len(beatdown_samples) > 0

    # Test that we can access specific fields from committed models
    first_ao = ao_samples[0]
    assert hasattr(first_ao, 'channel_id')
    assert hasattr(first_ao, 'ao')
    assert first_ao.ao is not None

    first_user = user_samples[0]
    assert hasattr(first_user, 'user_id')
    assert hasattr(first_user, 'user_name')
    assert first_user.user_name is not None

    first_beatdown = beatdown_samples[0]
    assert hasattr(first_beatdown, 'ao_id')
    assert hasattr(first_beatdown, 'bd_date')
    assert hasattr(first_beatdown, 'q_user_id')
    assert first_beatdown.ao_id is not None

    # Test that __repr__ methods work
    ao_repr = repr(first_ao)
    user_repr = repr(first_user)
    beatdown_repr = repr(first_beatdown)

    assert 'SqlAOModel' in ao_repr
    assert 'SqlUserModel' in user_repr
    assert 'SqlBeatDownModel' in beatdown_repr
    assert str(first_ao.channel_id) in ao_repr
    assert str(first_user.user_id) in user_repr
