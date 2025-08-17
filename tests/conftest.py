"""Pytest configuration and shared fixtures for F3 Nation data tests."""

import json
from collections.abc import Generator
from pathlib import Path

import pytest
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Import the committed models for type hints and usage
from f3_nation_data.models.sql.ao import SqlAOModel
from f3_nation_data.models.sql.beatdown import SqlBeatDownModel
from f3_nation_data.models.sql.user import SqlUserModel


@pytest.fixture
def f3_test_database() -> Generator[Engine, None, None]:
    """Create an in-memory SQLite database with F3 test data loaded from JSON fixtures.

    This fixture:
    1. Creates an in-memory SQLite database
    2. Creates tables matching the committed SQL model schemas
    3. Loads test data from JSON fixtures in tests/fixtures/
    4. Returns a SQLAlchemy engine for use in tests
    5. Automatically cleans up when the test completes

    Returns:
        SQLAlchemy Engine connected to the test database
    """
    # Create in-memory SQLite database
    engine = create_engine('sqlite:///:memory:', echo=False)

    # Get the path to fixture files
    fixtures_dir = Path(__file__).parent / 'fixtures'

    with engine.connect() as conn:
        # Create tables matching our committed models exactly
        _create_test_tables(conn)

        # Load and insert test data from JSON fixtures
        _load_fixture_data(conn, fixtures_dir)

        conn.commit()

    yield engine

    # Cleanup (engine disposal happens automatically)
    engine.dispose()


@pytest.fixture
def f3_test_session(f3_test_database: Engine) -> Generator[Session, None, None]:
    """Create a SQLAlchemy session connected to the F3 test database.

    Args:
        f3_test_database: The test database engine fixture

    Yields:
        SQLAlchemy Session for database operations
    """
    session_factory = sessionmaker(bind=f3_test_database)
    session = session_factory()

    try:
        yield session
    finally:
        session.close()


def _create_test_tables(conn: Connection) -> None:
    """Create database tables that match the committed SQL model schemas."""
    # Create AOs table (matches SqlAOModel)
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

    # Create Users table (matches SqlUserModel)
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

    # Create Beatdowns table (matches SqlBeatDownModel)
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


def _load_fixture_data(conn: Connection, fixtures_dir: Path) -> None:
    """Load test data from JSON fixtures into the database tables."""
    # Load AOs data
    aos_file = fixtures_dir / 'aos.json'
    if aos_file.exists():
        with aos_file.open() as f:
            aos_data = json.load(f)

        for ao in aos_data:
            conn.execute(
                text("""
                INSERT INTO aos (channel_id, ao, channel_created, archived, backblast, site_q_user_id)
                VALUES (:channel_id, :ao, :channel_created, :archived, :backblast, :site_q_user_id)
            """),
                ao,
            )

    # Load Users data
    users_file = fixtures_dir / 'users.json'
    if users_file.exists():
        with users_file.open() as f:
            users_data = json.load(f)

        for user in users_data:
            conn.execute(
                text("""
                INSERT INTO users (user_id, user_name, real_name, phone, email, start_date, app, json)
                VALUES (:user_id, :user_name, :real_name, :phone, :email, :start_date, :app, :json)
            """),
                user,
            )

    # Load Beatdowns data
    beatdowns_file = fixtures_dir / 'beatdowns.json'
    if beatdowns_file.exists():
        with beatdowns_file.open() as f:
            beatdowns_data = json.load(f)

        for beatdown in beatdowns_data:
            conn.execute(
                text("""
                INSERT INTO beatdowns (
                    timestamp, ts_edited, ao_id, bd_date, q_user_id, coq_user_id,
                    pax_count, backblast, backblast_parsed, fngs, fng_count, json
                )
                VALUES (
                    :timestamp, :ts_edited, :ao_id, :bd_date, :q_user_id, :coq_user_id,
                    :pax_count, :backblast, :backblast_parsed, :fngs, :fng_count, :json
                )
            """),
                beatdown,
            )


# Convenience fixtures for quick access to model counts
@pytest.fixture
def f3_data_counts(f3_test_session: Session) -> dict[str, int]:
    """Get counts of records in each table for quick test verification.

    Args:
        f3_test_session: Database session fixture

    Returns:
        Dictionary with counts: {'aos': N, 'users': N, 'beatdowns': N}
    """
    return {
        'aos': f3_test_session.query(SqlAOModel).count(),
        'users': f3_test_session.query(SqlUserModel).count(),
        'beatdowns': f3_test_session.query(SqlBeatDownModel).count(),
    }
