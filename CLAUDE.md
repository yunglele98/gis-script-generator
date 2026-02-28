# CLAUDE.md — AI Assistant Guide for gis-script-generator

This file provides context for AI assistants (Claude Code and others) working on
this repository.

---

## Repository Overview

**gis-codegen** is a Python tool that connects to a PostGIS database, extracts spatial
layer metadata, and generates ready-to-run GIS scripts or project files for eight
platforms. It also includes a Flask web UI and an Excel-driven map catalogue tool.

The repository has **two distinct components**:

| Component | Location | Purpose |
|---|---|---|
| **gis-codegen package** | `src/gis_codegen/`, `tests/` | Installable Python package (CLI + Flask UI) |
| **Kensington data pipeline** | Root-level `*.py` scripts, `*.bat` | One-off ETL/analysis scripts for the Kensington Market GIS project |

Do not mix these two. The root-level scripts are project-specific utilities, not part
of the installable package.

---

## Project Structure

```
gis-script-generator/
├── src/gis_codegen/          # Installable package
│   ├── __init__.py           # Public API: connect, extract_schema, generate_*
│   ├── extractor.py          # PostGIS metadata queries (read-only connection)
│   ├── generator.py          # Code generation for all 8 platforms
│   ├── catalogue.py          # Excel-driven per-map code generation (gis-catalogue CLI)
│   ├── cli.py                # gis-codegen CLI entry point
│   └── app.py                # Flask web UI (gis-ui entry point)
├── tests/
│   ├── conftest.py
│   ├── test_generator.py     # 173 tests — safe_var, type maps, op blocks, generators
│   ├── test_catalogue.py     # 108 tests — load/filter, renderer blocks, symbology
│   ├── test_extractor.py     # 34 tests  — fetch_columns, PKs, extract_schema
│   ├── test_app.py           # 11 tests  — Flask routes, form, download, errors
│   ├── test_integration.py   # 19 tests  — live PostGIS via testcontainers (Docker)
│   └── Tree_Perc_Ash_Catcher.py  # Unrelated script (moved to misc later if needed)
├── .github/workflows/
│   └── ci.yml                # Unit + integration CI jobs
├── pyproject.toml            # Package metadata, deps, pytest config, coverage
├── gis_codegen.toml          # Example/default config file for connection settings
├── requirements.txt          # Thin requirements list (supplements pyproject.toml)
├── make_pdf.py               # Generates the PDF user guide
├── BUILD_PROJECT.bat         # Windows: one-click Kensington data pipeline runner
│
│   # Kensington data pipeline scripts (root-level, not part of the package):
├── reproject_to_mtm10.py     # Batch reprojects 85 WGS84 shapefiles → EPSG:2952
├── migrate_to_sql.py         # Loads SHPs + CSVs into SQLite
├── create_analytical_views.py
├── generate_dashboard.py     # Produces HTML BI report
├── generate_static_map.py    # Matplotlib static map
├── generate_interactive_map.py # Folium interactive map
├── create_kensington_map.py
├── arc_setup_gdb.py          # ArcPy: initialise MTM10 Master GDB
├── arc_batch_import.py       # ArcPy: batch reprojection + GDB import
├── arc_topology_builder.py   # ArcPy: apply spatial topology rules
├── qgis_master_setup.py      # PyQGIS: automated project configuration
│
│   # Documentation:
├── README.md
├── CONTINUATION_PROMPT.md    # Context for resuming the Kensington project
├── DATA_CATALOG.md           # Inventory of Kensington spatial datasets
├── QC_LOG.md                 # Quality control log
├── TOPOLOGY_RULES.md         # Spatial topology rule definitions
├── TOPOLOGY_SCHEMA.md        # Topology error tracking schema
├── QGIS_PLUGINS.md           # Recommended QGIS plugins
├── KENSINGTON_PROJECT_REPORT.html  # HTML project report
└── misc/                     # Miscellaneous/unrelated files
```

---

## Package Architecture (`src/gis_codegen/`)

### Data Flow

```
PostGIS DB
    │
    ▼
extractor.py      → connect(), extract_schema()  →  schema dict (JSON structure)
    │
    ▼
generator.py      → generate_pyqgis / generate_arcpy / generate_folium /
                    generate_kepler / generate_deck / generate_export /
                    generate_qgs / generate_pyt
    │
    ▼
cli.py            → gis-codegen  (CLI entry point)
catalogue.py      → gis-catalogue (Excel-driven batch generation)
app.py            → gis-ui       (Flask web UI, localhost:5000)
```

### Schema Dict Structure

`extract_schema()` returns:
```json
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
      "columns":      [{"name": "gid", "data_type": "integer", "nullable": false}],
      "primary_keys": ["gid"],
      "comment":      "Optional table comment",
      "row_count_estimate": 42000
    }
  ]
}
```

### Supported Platforms

| `--platform` | Output | File extension |
|---|---|---|
| `pyqgis` | PyQGIS standalone Python script | `.py` |
| `arcpy` | ArcPy / ArcGIS Pro Python script | `.py` |
| `folium` | Folium / Leaflet HTML map generator | `.py` |
| `kepler` | Kepler.gl HTML map generator | `.py` |
| `deck` | pydeck / deck.gl HTML map generator | `.py` |
| `export` | GeoPackage export script | `.py` |
| `qgs` | QGIS project file (open directly in QGIS) | `.qgs` |
| `pyt` | ArcGIS Python Toolbox | `.pyt` |

### Operations (`--op`)

Only apply to `pyqgis` and `arcpy` platforms. Ignored with a warning for others.

**General (10):** `reproject`, `export`, `buffer`, `clip`, `select`, `dissolve`,
`centroid`, `field_calc`, `spatial_join`, `intersect`

**3D massing (5):** `extrude`, `z_stats`, `floor_ceiling`, `volume`, `scene_layer`

Defined in `generator.py` as `VALID_OPERATIONS`.

---

## Configuration & Environment

### Connection Priority (highest → lowest)

1. CLI flags (`--host`, `--port`, `--dbname`, `--user`, `--password`)
2. Config file `[database]` section
3. Environment variables (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`)
4. Built-in defaults (`localhost`, `5432`, `my_gis_db`, `postgres`)

**Password has no built-in default** — it must come from one of the first three sources.
Never store passwords in committed config files; use `PGPASSWORD`.

### Config File Search Order

1. `--config FILE`
2. `$GIS_CODEGEN_CONFIG` environment variable
3. `./gis_codegen.toml` (project root)
4. `~/.config/gis_codegen/config.toml` (user-level)

### Required Environment Variables

| Variable | Default | Notes |
|---|---|---|
| `PGPASSWORD` | *(required)* | Never committed or stored in scripts |
| `PGHOST` | `localhost` | |
| `PGPORT` | `5432` | |
| `PGDATABASE` | `my_gis_db` | |
| `PGUSER` | `postgres` | |

### Kensington Project CRS

All Kensington spatial data targets **EPSG 2952** (NAD83 / Ontario MTM Zone 10).
Source data is often WGS84 (EPSG 4326). The reprojection script handles conversion.

---

## Development Workflows

### Installation

```bash
# Core package only:
pip install -e .

# With web mapping extras (folium, kepler, pydeck):
pip install -e ".[web]"

# With Flask web UI:
pip install -e ".[server]"

# With dev tools (pytest, coverage, openpyxl):
pip install -e ".[dev]"

# All dev + server (recommended for development):
pip install -e ".[dev,server]"

# With PostGIS integration tests (requires Docker):
pip install -e ".[dev,integration]"
```

### Running Tests

```bash
# Unit tests only (no DB or Docker — runs in ~2 seconds):
python -m pytest tests/ -m "not integration" -v --cov=gis_codegen --cov-report=term-missing

# Integration tests (requires Docker with PostGIS via testcontainers):
python -m pytest tests/test_integration.py -v -m integration

# Single test file:
python -m pytest tests/test_generator.py -v
```

**Coverage threshold:** 80% (enforced in CI). `cli.py` is excluded from coverage
(`[tool.coverage.run] omit = ["*/cli.py"]`) because it requires a live DB; it is
covered by integration tests instead.

### CI

Two jobs in `.github/workflows/ci.yml`:
- **unit**: Python 3.11, `pip install -e ".[dev,server]"`, runs all non-integration tests
- **integration**: Python 3.11, `pip install -e ".[dev,integration]"`, runs `test_integration.py`

CI triggers on push to `main`/`master` and on all pull requests.

### Web UI

```bash
pip install -e ".[server]"
gis-ui   # starts Flask on http://localhost:5000
```

The web UI is a single embedded HTML template in `app.py` (no `templates/` folder).
Passwords are never stored server-side.

### Generating the PDF User Guide

```bash
python make_pdf.py   # writes GIS_Script_Generator_User_Guide.pdf
```

---

## Key Conventions

### Python Style

- **Python 3.10+** minimum. Uses `str | None` union syntax (PEP 604), `match`
  statements are not used but type union syntax is throughout.
- TOML is loaded via stdlib `tomllib` (Python 3.11+) with `tomli` as a fallback
  for Python 3.10. This logic lives in `cli.py::_load_toml_module()`.
- All database connections are opened **read-only** with `autocommit=True`
  (`extractor.py::connect()`).
- `safe_var(name)` in `generator.py` converts table names to valid Python identifiers
  (replaces `-`, ` `, `.` with `_`).
- Type mapping functions (`pg_type_to_pyqgis`, `pg_type_to_arcpy`) in `generator.py`
  map PostgreSQL data types to platform-appropriate types.

### Security Conventions

- **Never commit passwords** — always use `PGPASSWORD` env var.
- The web UI (`app.py`) accepts passwords via POST form but never persists them.
- `.gitignore` excludes `*.sql` files (which may contain credentials or large data).

### File Naming

- Generated output scripts are written to `stdout` by default, or to `-o FILE`.
- Generated catalogue scripts go to `./maps/` (pyqgis) or `./maps_arcpy/` (arcpy)
  by default — both are git-ignored.
- Schema JSON snapshots (`--save-schema`) are git-ignored.

### Catalogue Inclusion Rules

`gis-catalogue` reads `.xlsx` files and includes only rows where:
- `status` is `have` or `partial` (case-insensitive)
- `spatial_layer_type` contains `Vector`

Raster-only and Table-only entries are skipped.

### Operations on Non-Supporting Platforms

`--op` flags are silently warned about (not errored) when used with platforms that
don't support them (`folium`, `kepler`, `deck`, `export`, `qgs`, `pyt`).

---

## Test Suite Summary

| File | Count | Scope |
|---|---|---|
| `test_generator.py` | 173 | `safe_var`, type maps, 15 op blocks × 2 platforms, all 8 generators |
| `test_catalogue.py` | 108 | Load/filter, 10 renderer blocks, symbology dispatch, both generators |
| `test_extractor.py` | 34 | `fetch_columns`, `fetch_primary_keys`, `extract_schema` |
| `test_app.py` | 11 | Flask routes, form rendering, file download, error handling |
| `test_integration.py` | 19 | Live PostGIS via testcontainers (Docker required) |
| **Total** | **345** | |

Unit tests (all except `test_integration.py`) require no database or Docker.

---

## Kensington Project Context

The root-level scripts belong to a real-world GIS project for **Kensington Market
and Chinatown, Toronto**. Key facts:

- **Dual DB backends** (intentional): SQLite (`migrate_to_sql.py`) for the dashboard,
  PostGIS (`master_postgis_import.sql` + `gis-codegen`) for spatial analysis.
- **Data volume**: 85 shapefiles, 42 CSVs, 11 GeoJSON files, GTFS feed,
  29 PostGIS SQL files.
- **Windows-first pipeline**: `BUILD_PROJECT.bat` is the one-click runner for the
  data pipeline. The repo is developed on Windows (paths in `CONTINUATION_PROMPT.md`
  reference `C:\GDB`).
- **ArcPy scripts** (`arc_*.py`) require ArcGIS Pro and cannot run in a standard
  Python environment.
- **PyQGIS scripts** (`qgis_master_setup.py`) require QGIS's bundled Python
  interpreter unless QGIS libraries are on `sys.path`.

---

## Common Pitfalls

1. **Password not set**: The CLI exits with `[ERROR] No database password supplied.`
   if `PGPASSWORD` is not set and no password is in the config or CLI flags.

2. **No spatial layers found**: `extract_schema()` queries `geometry_columns`.
   Tables registered via `AddGeometryColumn` or views with `ST_SetSRID` are included;
   tables with geometry columns added manually may not appear.

3. **`--op` ignored warning**: Using `--op` with `qgs`, `pyt`, `folium`, etc. emits
   `[warn]` to stderr but still generates the file. This is intentional.

4. **`cli.py` excluded from coverage**: Do not be alarmed by its absence in coverage
   reports. It is tested via integration tests, not unit tests.

5. **`openpyxl` required for `gis-catalogue`**: The catalogue module imports `openpyxl`
   at module level and exits with a helpful message if it is missing. Install with
   `pip install -e ".[dev]"`.

6. **ArcPy / PyQGIS not installable via pip**: Generated scripts target these
   environments, but the generator itself has no dependency on them. Tests mock
   all platform-specific behaviour.

---

## Branch & Git Conventions

- Default branch: `master`
- Feature branches follow `feat/`, `fix/`, `claude/` prefixes
- CI runs on push to `master` and on all PRs
- Generated outputs (`maps/`, `maps_arcpy/`, `*.pdf`, `schema.json`) are git-ignored
- `.sql` files are git-ignored (may contain large data or credentials)
