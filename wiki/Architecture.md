# Architecture

This page describes the internal design of `gis-codegen`: data flow, module responsibilities, schema structure, and key design decisions.

---

## High-Level Data Flow

```
PostGIS Database (read-only)
        │
        ▼
  extractor.py
  ┌─────────────────────────────────────┐
  │ connect()          — psycopg2 conn  │
  │ fetch_columns()    — column types   │
  │ fetch_primary_keys() — PK list      │
  │ extract_schema()   — full schema    │
  └─────────────────────────────────────┘
        │
        │  schema dict (JSON structure)
        ▼
  generator.py
  ┌─────────────────────────────────────┐
  │ generate_pyqgis()                   │
  │ generate_arcpy()                    │
  │ generate_folium()                   │
  │ generate_kepler()                   │
  │ generate_deck()                     │
  │ generate_export()                   │
  │ generate_qgs()                      │
  │ generate_pyt()                      │
  └─────────────────────────────────────┘
        │
        ▼
  Output (stdout or file)
  ┌─────────────────────────────────────┐
  │ .py script (most platforms)         │
  │ .qgs project file                   │
  │ .pyt Python Toolbox                 │
  └─────────────────────────────────────┘
```

---

## Module Responsibilities

### `extractor.py`

Handles all database interaction. All connections are:
- **Read-only** — `autocommit=True`, no writes or DDL
- **Querying `geometry_columns`** — the standard PostGIS metadata view

Key functions:

| Function | Description |
|---|---|
| `connect(host, port, dbname, user, password)` | Returns a psycopg2 connection |
| `fetch_columns(conn, schema, table)` | Returns list of `{name, data_type, nullable}` dicts |
| `fetch_primary_keys(conn, schema, table)` | Returns list of primary key column names |
| `extract_schema(conn)` | Returns the full schema dict (see below) |

### `generator.py`

Pure functions — no database access. Takes a schema dict, returns a string of generated code.

Key components:

| Component | Description |
|---|---|
| `safe_var(name)` | Converts table names to valid Python identifiers |
| `pg_type_to_pyqgis(pg_type)` | Maps PostgreSQL types to `QVariant.Type` constants |
| `pg_type_to_arcpy(pg_type)` | Maps PostgreSQL types to ArcPy field type strings |
| `VALID_OPERATIONS` | Set of all 15 recognised operation names |
| `generate_*()` | One function per platform — all accept `(schema, ops=[])` |

### `catalogue.py`

Extends generator functionality for Excel-driven batch workflows:
- Reads `.xlsx` files using `openpyxl`
- Filters rows by `status` and `spatial_layer_type`
- Builds per-map schema dicts from spreadsheet data
- Calls generator functions with symbology/renderer blocks

### `cli.py`

Entry point for `gis-codegen` and `gis-catalogue`:
- Parses CLI arguments with `argparse`
- Loads config file via `_load_toml_module()` (handles `tomllib` vs `tomli`)
- Resolves connection parameters following the priority order
- Validates that a password is available
- Calls `extractor.py` then `generator.py`

**Note:** `cli.py` is excluded from unit test coverage because it requires a live database. It is covered by integration tests.

### `app.py`

Flask web application:
- Single embedded HTML template (no `templates/` folder)
- POST handler: accepts form data, calls extractor + generator, returns file download
- Password is used per-request only, never persisted
- `gis-ui` entry point starts the development server

---

## Schema Dict Structure

`extract_schema()` returns a dict with this structure:

```python
{
    "database": "my_gis_db",
    "host":     "localhost",
    "layer_count": 3,
    "layers": [
        {
            "schema":         "public",
            "table":          "buildings",
            "qualified_name": "public.buildings",
            "geometry": {
                "column": "geom",
                "type":   "MULTIPOLYGON",
                "srid":   2952
            },
            "columns": [
                {
                    "name":      "gid",
                    "data_type": "integer",
                    "nullable":  False
                },
                {
                    "name":      "height_m",
                    "data_type": "double precision",
                    "nullable":  True
                }
            ],
            "primary_keys": ["gid"],
            "comment":      "Building footprints with heights",
            "row_count_estimate": 42000
        }
    ]
}
```

This dict is passed directly to all `generate_*()` functions.

---

## Type Mapping

### PostgreSQL → PyQGIS

| PostgreSQL type | PyQGIS QVariant type |
|---|---|
| `integer`, `bigint`, `smallint` | `QVariant.Int` |
| `double precision`, `numeric`, `real` | `QVariant.Double` |
| `text`, `varchar`, `char` | `QVariant.String` |
| `boolean` | `QVariant.Bool` |
| `date` | `QVariant.Date` |
| `timestamp`, `timestamptz` | `QVariant.DateTime` |
| *(others)* | `QVariant.String` |

### PostgreSQL → ArcPy

| PostgreSQL type | ArcPy field type |
|---|---|
| `integer`, `bigint`, `smallint` | `LONG` |
| `double precision`, `real` | `DOUBLE` |
| `numeric` | `DOUBLE` |
| `text`, `varchar`, `char` | `TEXT` |
| `boolean` | `SHORT` |
| `date` | `DATE` |
| `timestamp`, `timestamptz` | `DATE` |
| *(others)* | `TEXT` |

---

## `safe_var()` Name Sanitisation

Table names from PostGIS are converted to valid Python variable names:

```python
safe_var("public.buildings")   # → "public_buildings"
safe_var("my-layer")           # → "my_layer"
safe_var("layer with spaces")  # → "layer_with_spaces"
safe_var("123_start")          # → "_123_start"
```

Characters replaced: `-`, ` ` (space), `.` → `_`

If the name starts with a digit, a `_` prefix is added.

---

## Configuration Resolution

The CLI resolves connection parameters in this priority order:

```
1. --flag (CLI argument)          ← highest priority
2. config file [database] section
3. environment variable (PGHOST, etc.)
4. built-in default               ← lowest priority
```

Password has no built-in default — it must come from one of the first three.

---

## Design Decisions

**Read-only connections:** `extractor.py` connects with `autocommit=True` and issues only `SELECT` statements. This prevents any accidental writes to production databases.

**Pure generator functions:** `generator.py` has no side effects and no database access. This makes it easy to test (173 unit tests with no mocking of database calls), and allows the same generator to be called from CLI, web UI, and catalogue tool.

**Single HTML template:** The Flask app embeds its template as a string in `app.py`. This is intentional — it keeps the web UI self-contained in a single file, simplifying installation and deployment.

**`tomllib` / `tomli` fallback:** Python 3.11+ includes `tomllib` in the standard library. For Python 3.10 compatibility, `cli.py` falls back to the `tomli` package when `tomllib` is not available.

**`openpyxl` optional import:** `catalogue.py` imports `openpyxl` at module level and exits with a helpful message if it is missing. This avoids a hard dependency on `openpyxl` for users who only use the core CLI.
