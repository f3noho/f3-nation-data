# Development Utilities

This directory contains scripts and tools for maintaining and developing the F3
Nation Data library.

## Scripts

### `generate_models.py`

Automatically generates SQLAlchemy models from any F3 Nation database schema.

**Purpose:**

- Keep SQL models in sync with actual database schema
- Eliminate manual model creation and maintenance
- Provide "snapshot" models that exactly match the database

**Usage:**

```bash
# Generate models for all target tables
python dev_utilities/generate_models.py
```

**What it does:**

1. Connects to an F3 Nation database using environment variables
2. Reflects the schema for target tables (`beatdowns`, `aos`, `users`)
3. Generates clean Python model files using Jinja2 templates
4. Automatically formats generated files with toolbelt
5. Places generated files in `f3_nation_data/models/sql/`

**Generated files include:**

- Auto-generated header comments with timestamp
- Proper SQLAlchemy type mappings (VARCHAR → String, TINYINT → Boolean, etc.)
- Conditional imports (only imports what's actually needed)
- Correct primary key definitions
- Proper nullable/non-nullable field handling
- Clean `__repr__` methods
- Professional code formatting

**Logging:**

The script uses structured logging via toolbelt for clean, parseable output:

- Events are logged as discrete actions rather than prose
- Context data is provided in YAML format for complex information
- Errors include detailed context for debugging

**Environment Requirements:**

- `F3_NATION_USER` - Database username
- `F3_NATION_PASSWORD` - Database password
- `F3_NATION_HOST` - Database hostname/endpoint
- `F3_NATION_DATABASE` - Database name
- `F3_NATION_PORT` - Database port (optional, defaults to 3306)

**Example Output:**

```
[INFO] database_connection_starting
[INFO] database_connection_successful
[INFO] output_directory_ready
  path: /path/to/f3_nation_data/models/sql
[INFO] model_generation_starting
  table: beatdowns
[INFO] schema_reflected
  column_count: 12
  primary_key:
  - ao_id
  - bd_date
  - q_user_id
  table: beatdowns
[INFO] model_generated
  file: /path/to/beatdown.py
  table: beatdowns
[INFO] generation_complete
  output_dir: /path/to/f3_nation_data/models/sql
[INFO] formatting_models_starting
  output_dir: /path/to/f3_nation_data/models/sql
[INFO] formatting_models_successful
```

**When to run:**

- When database schema changes
- Periodically to ensure models stay in sync

**Generated files contain header:**

```python
"""Auto-generated SQLAlchemy model for [table] table.

This file was automatically generated from the F3 Nation database schema.
Generated on: 2025-08-16 21:07:57 UTC

DO NOT EDIT MANUALLY - Use dev_utilities/generate_models.py to regenerate.
Auto-formatted with toolbelt for consistent code style.
"""
```

**Key Features:**

- **Jinja2 Templates**: Uses professional templates instead of string
  concatenation
- **Automatic Formatting**: Generated files are automatically formatted with
  toolbelt
- **Conditional Imports**: Only imports the types actually used by each model
- **Error Isolation**: Individual table failures don't stop the entire process
- **Type Safety**: Uses dataclasses internally for better code maintainability

## Configuration

The script targets these tables by default:

- `beatdowns` → `SqlBeatDownModel`
- `aos` → `SqlAOModel`
- `users` → `SqlUserModel`

To add more tables, edit the `TARGET_TABLES` and `CLASS_NAMES` constants in
`generate_models.py`.

## Type Mappings

The script handles MySQL-specific types:

- `VARCHAR(45)` → `sa.String(45)` / `str`
- `LONGTEXT` → `LONGTEXT` / `str`
- `TINYINT` → `sa.Boolean` / `bool`
- `INTEGER` → `sa.Integer` / `int`
- `DATE` → `sa.Date` / `date`
- `JSON` → `sa.JSON` / `dict[str, Any]`
