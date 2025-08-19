# f3-nation-data

A Python library for extracting, parsing, and analyzing F3 Nation SQL database
data.

## Overview

This library provides tools for working with F3 Nation database data, focusing
on:

- **Users**: PAX (participants) information
- **AOs**: Areas of Operations (workout locations)
- **Beatdowns**: Workout sessions and backblast data

## Setup

### Environment Variables

Before using this library, you must set the following environment variables to
connect to your F3 Nation database:

```bash
export F3_NATION_USER="your_database_username"
export F3_NATION_PASSWORD="your_database_password"
export F3_NATION_HOST="your-database-host.com"
export F3_NATION_DATABASE="your_database_name"
export F3_NATION_PORT="3306"  # Optional, defaults to 3306
```

**Security Note**: Never commit database credentials to version control. Always
use environment variables.

## Usage

### Example: Gather All Beatdowns for a Given Week

```python
from f3_nation_data.database import get_sql_engine, create_session
from f3_nation_data.fetch import fetch_sql_beatdowns
from f3_nation_data.analytics import get_week_range

# Create database connection
engine = get_sql_engine()
session = create_session(engine)

# Get the current week's date range
week_start, week_end = get_week_range()

# Fetch all beatdowns for the week
beatdowns = fetch_sql_beatdowns(
    session,
    start_date=week_start.date(),
    end_date=week_end.date(),
)

for bd in beatdowns:
    print(f"AO: {bd.ao_id}, Date: {bd.bd_date}, Q: {bd.q_user_id}")

session.close()
```

### Using Context Manager

```python
from f3_nation_data.database import db_session
from f3_nation_data.models.sql import SqlUserModel

with db_session() as session:
    users = session.query(SqlUserModel).all()
    for user in users:
        print(user.user_id, user.user_name)
    # Session automatically commits and closes
```

## Command-Line Interface (CLI)

This project provides a CLI tool for generating weekly F3 Nation beatdown
reports directly from your database.

### Features

- Generate a weekly report for any week (default: current week)
- Region-agnostic analytics and reporting
- Robust error handling and clear output
- Options for specifying week, showing version, and more

### Usage

To run the CLI and generate a weekly report:

```bash
uvx --from f3-nation-data weekly_report [DATE]
```

- `DATE` (optional): Any date within the target week (format: `YYYY-MM-DD`). If
  omitted, the current week is used.

#### Example

```bash
uvx --from f3-nation-data weekly_report 2024-03-09
```

#### Options

- `--date YYYY-MM-DD` : Specify the week by date
- `--version` : Show CLI version and exit

### Output

The CLI prints a formatted weekly report to stdout, including:

- Week summary (beatdowns, attendance, unique PAX)
- Highest attended workout at each AO
- Top HIMs who posted
- Leaders in Q counts
- AO rankings by unique PAX

### Error Handling

- Invalid date format: clear error message and exit
- Missing environment variable: clear error message and exit
- No beatdowns found: clear message and exit

See the [tests](tests/test_weekly_report_cli.py) for examples of CLI output and
error handling.

## Development

### Generating SQL Models

This library includes a script to automatically generate SQLAlchemy models from
your database schema:

```bash
python dev_utilities/generate_models.py
```

This ensures models stay in sync with any database schema changes.

### Code Quality

```bash
# Run all code quality checks (formatting, linting, types, complexity, coverage, prettier)
poe ci-checks
```

You can also run individual tasks (format, lint, test, etc.) if needed, but
`poe ci-checks` is recommended for full validation.

## Architecture

- **SQL Models** (`f3_nation_data/models/sql/`): Direct database mappings using
  SQLAlchemy
- **App Models** (`f3_nation_data/models/app/`): Business logic models using
  Pydantic
- **Database** (`f3_nation_data/database.py`): Connection utilities
- **Parsing** (`f3_nation_data/parsing.py`): Backblast and data parsing
  functions
- **Analytics** (`f3_nation_data/analytics.py`): Data analysis utilities

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.
