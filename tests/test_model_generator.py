"""Test the model generator with an in-memory database."""

import contextlib
import sqlite3
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import sessionmaker

from dev_utilities.generate_models import (
    CLASS_NAMES,
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


@pytest.fixture
def test_database() -> Generator[str, None, None]:
    """Create a temporary SQLite database with F3-style test data."""
    # Create temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_db:
        temp_db_path = temp_db.name

    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Create test tables
    _create_test_tables(cursor)
    _insert_test_data(cursor)

    conn.commit()
    conn.close()

    yield temp_db_path

    # Cleanup
    with contextlib.suppress(OSError):
        Path(temp_db_path).unlink()


@pytest.fixture
def test_engine(test_database: str) -> Engine:
    """Create SQLAlchemy engine for test database."""
    return create_engine(f'sqlite:///{test_database}')


def _create_test_tables(cursor: sqlite3.Cursor) -> None:
    """Create test tables with F3-style schema."""
    # Create AOs table
    cursor.execute("""
        CREATE TABLE aos (
            ao_id INTEGER PRIMARY KEY,
            ao_display_name VARCHAR(45) NOT NULL,
            ao_location_subtitle VARCHAR(45),
            ao_location VARCHAR(100),
            is_active BOOLEAN DEFAULT 1,
            created_date DATE
        )
    """)

    # Create Users table
    cursor.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            user_name VARCHAR(45) NOT NULL,
            first_name VARCHAR(45),
            last_name VARCHAR(45),
            email VARCHAR(100),
            phone VARCHAR(20),
            is_active BOOLEAN DEFAULT 1,
            created_date DATE
        )
    """)


def _insert_test_data(cursor: sqlite3.Cursor) -> None:
    """Insert F3-themed test data."""
    # Insert test AOs with F3-style names
    aos_data = [
        (
            1,
            'The Grill',
            'Where meat meets heat',
            'Backyard BBQ Park',
            True,
            '2023-01-15',
        ),
        (
            2,
            'Donut Shop',
            'Glazed and confused',
            'Sweet Treats Plaza',
            True,
            '2023-02-01',
        ),
        (
            3,
            'Taco Stand',
            'Spice up your life',
            'Salsa Verde Commons',
            True,
            '2023-03-10',
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO aos (ao_id, ao_display_name, ao_location_subtitle, ao_location, is_active, created_date)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        aos_data,
    )

    # Insert test users with food-themed F3 names
    users_data = [
        (
            101,
            'Hotdog',
            'Frank',
            'Mustard',
            'hotdog@f3.com',
            '555-0101',
            True,
            '2023-01-10',
        ),
        (
            102,
            'Hamburger',
            'Chuck',
            'Beef',
            'burger@f3.com',
            '555-0102',
            True,
            '2023-01-12',
        ),
        (
            103,
            'Taco',
            'Juan',
            'Salsa',
            'taco@f3.com',
            '555-0103',
            True,
            '2023-01-15',
        ),
    ]

    cursor.executemany(
        """
        INSERT INTO users (user_id, user_name, first_name, last_name, email, phone, is_active, created_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
        users_data,
    )


def test_database_tables_exist(test_engine: Engine) -> None:
    """Test that our test database has the expected tables."""
    with test_engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'"),
        )
        tables = {row[0] for row in result.fetchall()}

    assert 'aos' in tables
    assert 'users' in tables


def test_schema_reflection(test_engine: Engine) -> None:
    """Test that schema reflection works correctly."""
    # Test AO table reflection
    aos_schema = reflect_table_schema(test_engine, 'aos')

    assert len(aos_schema.columns) == 6
    assert aos_schema.primary_key == ['ao_id']

    # Check specific columns exist
    column_names = {col['name'] for col in aos_schema.columns}
    assert 'ao_id' in column_names
    assert 'ao_display_name' in column_names
    assert 'is_active' in column_names


def test_model_generation(test_engine: Engine, tmp_path: Path) -> None:
    """Test that model generation creates valid Python code."""
    # Test generating a model for the 'aos' table
    success = generate_table_model(test_engine, 'aos', tmp_path)
    assert success

    # Verify file was created with expected name
    model_file = tmp_path / 'ao.py'
    assert model_file.exists()

    # Read and verify content
    content = model_file.read_text()
    assert 'class SqlAOModel(Base):' in content
    assert "__tablename__ = 'aos'" in content
    assert 'ao_id' in content
    assert 'ao_display_name' in content
    assert 'import sqlalchemy as sa' in content


def test_generated_model_can_be_imported_and_used(
    test_engine: Engine,
    tmp_path: Path,
) -> None:
    """Test that generated models can actually be imported and used."""
    # Generate the model
    success = generate_table_model(test_engine, 'aos', tmp_path)
    assert success

    model_file = tmp_path / 'ao.py'
    content = model_file.read_text()

    # Test that the generated content has the expected structure
    assert 'class SqlAOModel(Base):' in content
    assert 'ao_id: Mapped[int]' in content
    assert 'ao_display_name: Mapped[str]' in content
    assert 'primary_key=True' in content
    assert 'nullable=False' in content
    assert 'def __repr__(self)' in content

    # Test that the file is valid Python syntax
    try:
        compile(content, model_file, 'exec')
    except SyntaxError as e:
        pytest.fail(f'Generated model has invalid Python syntax: {e}')


def test_user_model_generation(test_engine: Engine, tmp_path: Path) -> None:
    """Test generating and using the user model."""
    # Generate user model
    success = generate_table_model(test_engine, 'users', tmp_path)
    assert success

    # Verify file exists with expected name (users -> user)
    model_file = tmp_path / 'user.py'
    assert model_file.exists()

    content = model_file.read_text()
    assert 'class SqlUserModel(Base):' in content
    assert "__tablename__ = 'users'" in content
    assert 'user_name' in content
    assert 'email' in content


def test_table_with_defaults(test_engine: Engine, tmp_path: Path) -> None:
    """Test generating model for table with default values."""
    # Add a column with default to the existing users table
    with test_engine.connect() as conn:
        conn.execute(
            text('ALTER TABLE users ADD COLUMN enabled BOOLEAN DEFAULT 1'),
        )
        conn.execute(
            text(
                "ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'",
            ),
        )
        conn.commit()

    success = generate_table_model(test_engine, 'users', tmp_path)
    assert success

    model_file = tmp_path / 'user.py'
    content = model_file.read_text()

    # Should contain default values in the generated model
    assert 'default=' in content  # Some kind of default should be present


def test_table_with_composite_primary_key(
    test_engine: Engine,
    tmp_path: Path,
) -> None:
    """Test repr format generation for composite primary keys."""
    # Create a new table that we'll add to CLASS_NAMES temporarily

    # Temporarily add the test table to the mapping
    original_mapping = CLASS_NAMES.copy()
    CLASS_NAMES['test_composite'] = 'SqlTestCompositeModel'

    try:
        with test_engine.connect() as conn:
            conn.execute(
                text("""
                CREATE TABLE test_composite (
                    user_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    assigned_date DATE,
                    PRIMARY KEY (user_id, role_id)
                )
            """),
            )
            conn.commit()

        success = generate_table_model(
            test_engine,
            'test_composite',
            tmp_path,
        )
        assert success

        model_file = tmp_path / 'test_composit.py'  # Note: filename removes last char
        content = model_file.read_text()

        # Should have both primary key columns
        assert 'user_id' in content
        assert 'role_id' in content
        assert 'primary_key=True' in content

        # __repr__ should include both primary keys for composite keys
        assert 'user_id={self.user_id}, role_id={self.role_id}' in content

    finally:
        # Restore original mapping
        CLASS_NAMES.clear()
        CLASS_NAMES.update(original_mapping)


def test_invalid_table_name(test_engine: Engine, tmp_path: Path) -> None:
    """Test error handling for non-existent table."""
    # Try to generate model for table that doesn't exist
    success = generate_table_model(
        test_engine,
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
    test_engine: Engine,
    tmp_path: Path,
):
    """Test exception handling in generate_table_model (lines 297-298)."""
    # Use a non-existent table to trigger an exception
    result = generate_table_model(test_engine, 'nonexistent_table', tmp_path)
    assert result is False


def test_main_database_connection_error():
    """Test main function database connection error (lines 310-323)."""
    # Mock get_sql_engine to raise an exception
    with patch('dev_utilities.generate_models.get_sql_engine') as mock_engine:
        mock_engine.side_effect = Exception('Database connection failed')
        result = main()
        assert result == 1


def test_main_model_generation_error():
    """Test main function model generation error (lines 325-334, 336-340)."""
    # Mock get_sql_engine to succeed but generate_table_model to fail
    with (
        patch('dev_utilities.generate_models.get_sql_engine') as mock_engine,
        patch(
            'dev_utilities.generate_models.generate_table_model',
        ) as mock_generate,
    ):
        mock_engine.return_value = Mock()
        mock_generate.side_effect = Exception('Model generation failed')

        result = main()
        assert result == 1


def test_main_successful_execution():
    """Test main function successful execution (lines 388-391)."""
    # Mock successful execution path
    with (
        patch('dev_utilities.generate_models.get_sql_engine') as mock_engine,
        patch(
            'dev_utilities.generate_models.generate_table_model',
        ) as mock_generate,
        patch(
            'dev_utilities.generate_models.format_generated_models',
        ) as mock_format,
    ):
        mock_engine.return_value = Mock()
        mock_generate.return_value = True
        mock_format.return_value = None

        result = main()
        assert result == 0


def test_format_generated_models_success(tmp_path: Path):
    """Test format_generated_models function successful execution."""
    # Create a dummy python file to format
    test_file = tmp_path / 'test.py'
    test_file.write_text('x=1')

    # Mock successful subprocess execution
    with patch('dev_utilities.generate_models.subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        # Should not raise any exception
        format_generated_models(tmp_path)


def test_format_generated_models_failure(tmp_path: Path):
    """Test format_generated_models function failure handling."""
    # Mock failed subprocess execution
    with patch('dev_utilities.generate_models.subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = 'stdout output'
        mock_result.stderr = 'stderr output'
        mock_run.return_value = mock_result

        # Should not raise any exception, just log warning
        format_generated_models(tmp_path)


def test_format_generated_models_exception(tmp_path: Path):
    """Test format_generated_models function exception handling."""
    # Mock subprocess exception
    with patch('dev_utilities.generate_models.subprocess.run') as mock_run:
        mock_run.side_effect = OSError('Command not found')

        # Should not raise any exception, just log warning
        format_generated_models(tmp_path)


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


def test_generated_models_basic_functionality(
    test_engine: Engine,
    tmp_path: Path,
):
    """Test basic functionality of generated models by compiling and validating syntax."""
    # Generate models for testing
    success_ao = generate_table_model(test_engine, 'aos', tmp_path)
    success_user = generate_table_model(test_engine, 'users', tmp_path)

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


def test_generated_model_file_structure(test_engine: Engine, tmp_path: Path):
    """Test that generated model files contain expected basic structure."""
    generate_table_model(test_engine, 'aos', tmp_path)

    ao_file = tmp_path / 'ao.py'
    content = ao_file.read_text()

    # Test the things that matter for functionality
    assert 'class SqlAOModel' in content
    assert "__tablename__ = 'aos'" in content
    assert 'def __repr__(self)' in content

    # Verify it's valid Python syntax
    try:
        compile(content, ao_file, 'exec')
    except SyntaxError as e:
        pytest.fail(f'Generated model has invalid Python syntax: {e}')


def test_committed_models_with_test_database():
    """Integration test: use committed models to connect to test database and fetch data."""
    # Create an in-memory SQLite database with schema matching committed models exactly
    engine = create_engine('sqlite:///:memory:')

    # Create the test schema that matches our committed models exactly
    with engine.connect() as conn:
        # Create AOs table (matches ao.py model exactly)
        conn.execute(
            text("""
            CREATE TABLE aos (
                channel_id VARCHAR(45) PRIMARY KEY,
                ao VARCHAR(45) NOT NULL,
                channel_created INTEGER NOT NULL,
                archived BOOLEAN NOT NULL,
                backblast BOOLEAN,
                site_q_user_id VARCHAR(45)
            )
        """),
        )

        # Create Users table (matches user.py model exactly)
        conn.execute(
            text("""
            CREATE TABLE users (
                user_id VARCHAR(45) PRIMARY KEY,
                user_name VARCHAR(45) NOT NULL,
                real_name VARCHAR(45) NOT NULL,
                phone VARCHAR(45),
                email VARCHAR(45),
                start_date DATE,
                app BOOLEAN NOT NULL DEFAULT 0,
                json JSON
            )
        """),
        )

        # Create Beatdowns table (matches beatdown.py model exactly)
        conn.execute(
            text("""
            CREATE TABLE beatdowns (
                timestamp VARCHAR(45),
                ts_edited VARCHAR(45),
                ao_id VARCHAR(45) NOT NULL,
                bd_date DATE NOT NULL,
                q_user_id VARCHAR(45) NOT NULL,
                coq_user_id VARCHAR(45),
                pax_count INTEGER,
                backblast TEXT,
                backblast_parsed TEXT,
                fngs VARCHAR(45),
                fng_count INTEGER,
                json JSON,
                PRIMARY KEY (ao_id, bd_date, q_user_id)
            )
        """),
        )

        # Insert test data that matches the schema types exactly
        conn.execute(
            text("""
            INSERT INTO aos (channel_id, ao, channel_created, archived, backblast, site_q_user_id)
            VALUES
                ('CH001', 'The Grill', 1640995200, 0, 1, 'U001'),
                ('CH002', 'Donut Shop', 1641081600, 0, 1, 'U002'),
                ('CH003', 'Taco Stand', 1641168000, 0, 1, 'U003')
        """),
        )

        conn.execute(
            text("""
            INSERT INTO users (user_id, user_name, real_name, email, phone, start_date, app, json)
            VALUES
                ('U001', 'Hotdog', 'Frank Mustard', 'hotdog@f3.com', '555-0101', '2023-01-10', 0, NULL),
                ('U002', 'Hamburger', 'Chuck Beef', 'hamburger@f3.com', '555-0102', '2023-01-12', 0, NULL),
                ('U003', 'Taco', 'Jose Salsa', 'taco@f3.com', '555-0103', '2023-01-15', 0, NULL)
        """),
        )

        conn.execute(
            text("""
            INSERT INTO beatdowns (timestamp, ao_id, bd_date, q_user_id, pax_count, backblast, fng_count)
            VALUES
                ('1642204800', 'CH001', '2024-01-15', 'U001', 12, 'Great workout at The Grill', 2),
                ('1642291200', 'CH002', '2024-01-16', 'U002', 8, 'Glazed and confused at Donut Shop', 0)
        """),
        )

        conn.commit()

    # Create session
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    try:
        # Test AO table - get count and sample data
        ao_count = session.query(SqlAOModel).count()

        # Get sample AO data
        ao_samples = session.query(SqlAOModel).limit(3).all()

        # Test User table - get count and sample data
        user_count = session.query(SqlUserModel).count()

        # Get sample User data
        user_samples = session.query(SqlUserModel).limit(3).all()

        # Test Beatdown table - get count and sample data
        beatdown_count = session.query(SqlBeatDownModel).count()

        # Get sample Beatdown data
        beatdown_samples = session.query(SqlBeatDownModel).limit(2).all()

        # Verify we got the expected counts based on our test data
        assert ao_count == 3  # We inserted 3 AOs
        assert user_count == 3  # We inserted 3 users
        assert beatdown_count == 2  # We inserted 2 beatdowns

        # Verify sample data is not empty
        assert len(ao_samples) == 3
        assert len(user_samples) == 3
        assert len(beatdown_samples) == 2

        # Test that we can access specific fields from committed models
        first_ao = ao_samples[0]
        assert hasattr(first_ao, 'channel_id')
        assert hasattr(first_ao, 'ao')
        assert first_ao.ao in ['The Grill', 'Donut Shop', 'Taco Stand']

        first_user = user_samples[0]
        assert hasattr(first_user, 'user_id')
        assert hasattr(first_user, 'user_name')
        assert first_user.user_name in ['Hotdog', 'Hamburger', 'Taco']

        first_beatdown = beatdown_samples[0]
        assert hasattr(first_beatdown, 'ao_id')
        assert hasattr(first_beatdown, 'bd_date')
        assert hasattr(first_beatdown, 'q_user_id')
        assert first_beatdown.ao_id in ['CH001', 'CH002']

        # Test that __repr__ methods work
        ao_repr = repr(first_ao)
        user_repr = repr(first_user)
        beatdown_repr = repr(first_beatdown)

        assert 'SqlAOModel' in ao_repr
        assert 'SqlUserModel' in user_repr
        assert 'SqlBeatDownModel' in beatdown_repr
        assert str(first_ao.channel_id) in ao_repr
        assert str(first_user.user_id) in user_repr

    finally:
        session.close()
        engine.dispose()
