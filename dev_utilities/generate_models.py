#!/usr/bin/env python3
"""Generate SQLAlchemy models from F3 Nation database schema.

This script connects to an F3 Nation database, reflects the schema for specified
tables, and generates clean Python model files with proper type hints and documentation.

Environment Variables Required:
    F3_NATION_USER: Database username
    F3_NATION_PASSWORD: Database password
    F3_NATION_HOST: Database hostname/endpoint
    F3_NATION_DATABASE: Database name
    F3_NATION_PORT: Database port (optional, defaults to 3306)

Usage:
    # Set environment variables first
    export F3_NATION_USER="your_username"
    export F3_NATION_PASSWORD="your_password"
    export F3_NATION_HOST="your-db-host.com"
    export F3_NATION_DATABASE="your_db_name"

    # Generate models
    python dev_utilities/generate_models.py

Generated files will be placed in f3_nation_data/models/sql/ with a header
comment indicating they were auto-generated.
"""

import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import Engine, inspect
from sqlalchemy.types import TypeEngine
from toolbelt.logging import configure_logging, get_logger

from f3_nation_data.database import get_sql_engine

# Configure logging
configure_logging()
logger = get_logger(__name__)

# Add the project root to Python path so we can import our modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Tables we want to generate models for
TARGET_TABLES = ['beatdowns', 'aos', 'users']

# Model class name mapping
CLASS_NAMES = {
    'beatdowns': 'SqlBeatDownModel',
    'aos': 'SqlAOModel',
    'users': 'SqlUserModel',
}


@dataclass
class ColumnInfo:
    """Information about a database column for template rendering."""

    name: str
    python_type: str
    sa_type: str
    nullable: bool
    is_pk: bool
    default_value: str | None = None


@dataclass
class TableSchema:
    """Schema information for a database table."""

    columns: list[Any]  # SQLAlchemy ReflectedColumn objects
    primary_key: list[str]
    unique_constraints: list[Any]  # SQLAlchemy ReflectedUniqueConstraint objects


def get_python_type(sql_type: TypeEngine[Any]) -> str:
    """Convert SQLAlchemy type to Python type hint string."""
    type_name = type(sql_type).__name__

    # Handle MySQL-specific types
    if hasattr(sql_type, 'length') and type_name in {'VARCHAR', 'CHAR'}:
        return 'str'

    # Generic type mapping
    type_mapping = {
        'String': 'str',
        'VARCHAR': 'str',
        'CHAR': 'str',
        'TEXT': 'str',
        'LONGTEXT': 'str',
        'Integer': 'int',
        'INTEGER': 'int',
        'BIGINT': 'int',
        'SMALLINT': 'int',
        'TINYINT': 'bool',  # MySQL TINYINT is typically used as boolean
        'Boolean': 'bool',
        'Date': 'date',
        'DateTime': 'datetime',
        'DATETIME': 'datetime',
        'TIMESTAMP': 'datetime',
        'JSON': 'dict[str, Any]',
    }

    return type_mapping.get(type_name, 'Any')


def get_sqlalchemy_type_import(sql_type: TypeEngine[Any]) -> str:
    """Get the appropriate SQLAlchemy type for import and usage."""
    type_name = type(sql_type).__name__

    # Handle special case for VARCHAR with length
    if type_name == 'VARCHAR' and hasattr(sql_type, 'length'):
        length = getattr(sql_type, 'length', None)
        if length is not None:
            return f'sa.String({length})'

    # Type mapping dictionary
    type_mapping = {
        'LONGTEXT': 'LONGTEXT',
        'TINYINT': 'sa.Boolean',  # Convert TINYINT to Boolean
        'String': 'sa.String(45)',  # Default length
        'VARCHAR': 'sa.String(45)',  # Default length
        'Integer': 'sa.Integer',
        'INTEGER': 'sa.Integer',
        'Boolean': 'sa.Boolean',
        'Date': 'sa.Date',
        'DateTime': 'sa.DateTime',
        'DATETIME': 'sa.DateTime',
        'TIMESTAMP': 'sa.DateTime',
        'JSON': 'sa.JSON',
    }

    return type_mapping.get(type_name, f'sa.{type_name}')


def get_default_value(default: str | int, python_type: str) -> str | None:
    """Get the properly formatted default value for a field."""
    if python_type.startswith('bool'):
        return 'True' if default in ('1', 1, True) else 'False'
    if python_type.startswith('str'):
        return f'"{default}"'
    return str(default)


def prepare_column_data(
    column_info: dict[str, Any],
    primary_keys: list[str],
) -> ColumnInfo:
    """Prepare column information for template rendering."""
    col_name = column_info['name']
    sql_type = column_info['type']
    nullable = column_info['nullable']
    is_pk = col_name in primary_keys
    default = column_info.get('default')

    # Get Python type hint
    python_type = get_python_type(sql_type)
    if nullable and not is_pk:
        python_type += ' | None'

    # Get SQLAlchemy type
    sa_type = get_sqlalchemy_type_import(sql_type)

    # Get default value if present
    default_value = None
    if default is not None and default != 'NULL':
        default_value = get_default_value(default, python_type)

    return ColumnInfo(
        name=col_name,
        python_type=python_type,
        sa_type=sa_type,
        nullable=nullable,
        is_pk=is_pk,
        default_value=default_value,
    )


def generate_model_file(table_name: str, table_schema: TableSchema) -> str:
    """Generate Python model file content using Jinja2 template."""
    class_name = CLASS_NAMES[table_name]
    timestamp = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
    primary_keys = table_schema.primary_key

    # Prepare column data for template
    columns = [prepare_column_data(col_info, primary_keys) for col_info in table_schema.columns]

    # Determine what imports are needed
    needs_date = any('date' in col.python_type and 'datetime' not in col.python_type for col in columns)
    needs_datetime = any('datetime' in col.python_type for col in columns)
    needs_any = any('dict[str, Any]' in col.python_type for col in columns)
    needs_longtext = any(col.sa_type == 'LONGTEXT' for col in columns)

    # Generate repr format string
    if len(primary_keys) == 1:
        repr_format = f'{{self.{primary_keys[0]}}}'
    else:
        pk_parts = [f'{field}={{self.{field}}}' for field in primary_keys]
        repr_format = ', '.join(pk_parts)

    # Set up Jinja2 environment
    template_dir = Path(__file__).parent / 'templates'
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=False,  # noqa: S701 - Safe for code generation, not web content
    )
    template = env.get_template('sqlalchemy_model.py.j2')

    # Render the template
    return template.render(
        table_name=table_name,
        class_name=class_name,
        timestamp=timestamp,
        primary_keys=primary_keys,
        columns=columns,
        needs_date=needs_date,
        needs_datetime=needs_datetime,
        needs_any=needs_any,
        needs_longtext=needs_longtext,
        repr_format=repr_format,
    )


def reflect_table_schema(engine: Engine, table_name: str) -> TableSchema:
    """Reflect schema information for a specific table."""
    inspector = inspect(engine)

    # Get column information
    columns = inspector.get_columns(table_name)

    # Get primary key
    pk_constraint = inspector.get_pk_constraint(table_name)
    primary_key = pk_constraint['constrained_columns']

    # Get unique constraints
    unique_constraints = inspector.get_unique_constraints(table_name)

    return TableSchema(
        columns=columns,
        primary_key=primary_key,
        unique_constraints=unique_constraints,
    )


def format_generated_models(output_dir: Path) -> None:
    """Format the generated model files using toolbelt."""
    try:
        logger.info('formatting_models_starting', output_dir=str(output_dir))

        # Run toolbelt format on the generated files
        # This is safe as we control the output_dir path
        result = subprocess.run(  # noqa: S603
            ['tb', 'format', 'python', str(output_dir)],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,  # Don't raise exception on non-zero exit
        )

        if result.returncode == 0:
            logger.info('formatting_models_successful')
        else:
            logger.warning(
                'formatting_models_failed',
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )

    except (subprocess.SubprocessError, OSError) as e:
        logger.warning(
            'formatting_models_error',
            error=str(e),
            error_type=type(e).__name__,
        )


def generate_table_model(
    engine: Engine,
    table_name: str,
    output_dir: Path,
) -> bool:
    """Generate a single table model file.

    Args:
        engine: SQLAlchemy engine for database connection
        table_name: Name of the table to generate model for
        output_dir: Directory to write the generated model file

    Returns:
        True if successful, False if failed
    """
    try:
        # Reflect table schema
        schema = reflect_table_schema(engine, table_name)
        logger.info(
            'schema_reflected',
            table=table_name,
            column_count=len(schema.columns),
            primary_key=schema.primary_key,
        )

        # Generate model file content
        model_content = generate_model_file(table_name, schema)

        # Write to file
        # Map table names to output file names
        file_mapping = {
            'aos': 'ao.py',
            'users': 'user.py',
            'beatdowns': 'beatdown.py',
        }

        filename = file_mapping.get(table_name, f'{table_name[:-1]}.py')
        output_file = output_dir / filename

        with Path(output_file).open('w') as f:
            f.write(model_content)

        logger.info(
            'model_generated',
            table=table_name,
            file=str(output_file),
        )

    except Exception as e:
        logger.exception(
            'model_generation_failed',
            table=table_name,
            error=str(e),
            error_type=type(e).__name__,
        )
        return False
    else:
        return True


def main() -> int:
    """Generate SQL models from database schema."""
    logger.info('database_connection_starting')

    # Connect to database
    try:
        engine = get_sql_engine()
        logger.info('database_connection_successful')
    except Exception as e:
        logger.exception(
            'database_connection_failed',
            error=str(e),
            error_type=type(e).__name__,
            required_env_vars=[
                'F3_NATION_USER',
                'F3_NATION_PASSWORD',
                'F3_NATION_HOST',
                'F3_NATION_DATABASE',
                'F3_NATION_PORT (optional, defaults to 3306)',
            ],
        )
        return 1

    # Generate models
    try:
        # Create output directory
        output_dir = project_root / 'f3_nation_data' / 'models' / 'sql'
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info('output_directory_ready', path=str(output_dir))

        for table_name in TARGET_TABLES:
            logger.info('model_generation_starting', table=table_name)
            generate_table_model(engine, table_name, output_dir)

        logger.info('generation_complete', output_dir=str(output_dir))

        # Format the generated files
        format_generated_models(output_dir)

    except Exception as e:
        logger.exception(
            'model_generation_failed',
            error=str(e),
            error_type=type(e).__name__,
        )
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
