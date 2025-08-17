"""Database connection utilities for F3 Nation data."""

import os
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def _get_required_env(key: str, error_msg: str) -> str:
    """Get a required environment variable or raise ValueError with custom message.

    Args:
        key: Environment variable key
        error_msg: Error message to show if the key is missing

    Returns:
        The environment variable value

    Raises:
        ValueError: If the environment variable is not set
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(error_msg)
    return value


def get_sql_engine(
    user: str | None = None,
    password: str | None = None,
    host: str | None = None,
    database: str | None = None,
    port: int | None = None,
) -> Engine:
    """Create a SQLAlchemy engine for F3 Nation database.

    All parameters can be provided directly or will be read from environment variables.

    Args:
        user: Database username (defaults to F3_NATION_USER env var)
        password: Database password (defaults to F3_NATION_PASSWORD env var)
        host: Database host (defaults to F3_NATION_HOST env var - REQUIRED)
        database: Database name (defaults to F3_NATION_DATABASE env var - REQUIRED)
        port: Database port (defaults to F3_NATION_PORT env var or 3306)

    Environment Variables:
        F3_NATION_USER: Database username
        F3_NATION_PASSWORD: Database password
        F3_NATION_HOST: Database hostname/endpoint (REQUIRED)
        F3_NATION_DATABASE: Database name (REQUIRED)
        F3_NATION_PORT: Database port (optional, defaults to 3306)

    Raises:
        ValueError: If required credentials or connection details are missing

    Example:
        # Using environment variables
        export F3_NATION_USER="your_username"
        export F3_NATION_PASSWORD="your_password"
        export F3_NATION_HOST="your-region.rds.amazonaws.com"
        export F3_NATION_DATABASE="f3_database_name"

        engine = get_sql_engine()
    """
    # Use provided values or fall back to environment variables with validation
    db_user = user or _get_required_env(
        'F3_NATION_USER',
        'Database username required',
    )
    db_password = password or _get_required_env(
        'F3_NATION_PASSWORD',
        'Database password required',
    )
    db_host = host or _get_required_env(
        'F3_NATION_HOST',
        'Database host required',
    )
    db_database = database or _get_required_env(
        'F3_NATION_DATABASE',
        'Database name required',
    )
    db_port = port or int(os.getenv('F3_NATION_PORT', '3306'))

    connection_string = f'mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}'

    return create_engine(connection_string)


def create_session(engine: Engine) -> Session:
    """Create a database session from an engine."""
    session_local = sessionmaker(bind=engine)
    return session_local()


@contextmanager
def db_session(
    user: str | None = None,
    password: str | None = None,
    host: str | None = None,
    database: str | None = None,
    port: int | None = None,
) -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    engine = get_sql_engine(user, password, host, database, port)
    session = create_session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
