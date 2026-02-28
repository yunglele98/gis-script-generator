# Development & Testing

This page covers how to set up a development environment, run the test suite, and understand the CI/CD pipeline.

---

## Development Setup

```bash
# Clone the repository
git clone <repo-url>
cd gis-script-generator

# Install with all development and server dependencies
pip install -e ".[dev,server]"
```

This installs:
- The `gis-codegen` package in editable mode
- `pytest` and `pytest-cov` for testing
- `openpyxl` for the catalogue tool
- `flask` for the web UI

---

## Running Tests

### Unit Tests (no database, no Docker)

```bash
python -m pytest tests/ -m "not integration" -v --cov=gis_codegen --cov-report=term-missing
```

Unit tests complete in approximately **2 seconds**. No external services are required.

### Integration Tests (requires Docker)

Integration tests use `testcontainers` to spin up a real PostGIS database in Docker.

```bash
# Install integration dependencies
pip install -e ".[dev,integration]"

# Run integration tests
python -m pytest tests/test_integration.py -v -m integration
```

**Requirements for integration tests:**
- Docker must be installed and running
- The `testcontainers[postgres]` package must be installed

### Single Test File

```bash
python -m pytest tests/test_generator.py -v
python -m pytest tests/test_catalogue.py -v
python -m pytest tests/test_extractor.py -v
python -m pytest tests/test_app.py -v
```

### Coverage

```bash
# Coverage report in terminal
python -m pytest tests/ -m "not integration" --cov=gis_codegen --cov-report=term-missing

# HTML coverage report
python -m pytest tests/ -m "not integration" --cov=gis_codegen --cov-report=html
# Open htmlcov/index.html in a browser
```

**Coverage threshold:** 80% (enforced in CI). `cli.py` is excluded from coverage measurement because it requires a live database — it is covered by integration tests instead.

---

## Test Suite Overview

| File | Tests | What it covers |
|---|---|---|
| `tests/test_generator.py` | 173 | `safe_var`, type maps, all 15 operation blocks × 2 platforms, all 8 generator functions |
| `tests/test_catalogue.py` | 108 | Excel load/filter, 10 renderer blocks, symbology dispatch, both generators |
| `tests/test_extractor.py` | 34 | `fetch_columns`, `fetch_primary_keys`, `extract_schema` |
| `tests/test_app.py` | 11 | Flask routes, form rendering, file download, error handling |
| `tests/test_integration.py` | 19 | Live PostGIS database via testcontainers (Docker required) |
| **Total** | **345** | |

### `conftest.py`

`tests/conftest.py` defines shared pytest fixtures, including a mock schema dict that all unit tests use instead of a real database connection.

---

## CI/CD

### GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) runs two jobs:

**`unit` job:**
- Python 3.11
- Installs: `pip install -e ".[dev,server]"`
- Runs all non-integration tests
- Enforces 80% coverage threshold

**`integration` job:**
- Python 3.11
- Installs: `pip install -e ".[dev,integration]"`
- Runs `tests/test_integration.py` only
- Requires Docker (provided by GitHub Actions runner)

**Triggers:**
- Push to `main` or `master`
- All pull requests

---

## Branch Conventions

| Prefix | Purpose |
|---|---|
| `feat/` | New features |
| `fix/` | Bug fixes |
| `claude/` | AI-assisted development |

Default branch: `master`

---

## Adding a New Platform

To add a ninth platform:

1. **Add a generator function** in `generator.py`:
   ```python
   def generate_myplatform(schema: dict, ops: list[str] | None = None) -> str:
       ...
   ```

2. **Export it** from `__init__.py`:
   ```python
   from .generator import generate_myplatform
   ```

3. **Register it** in `cli.py` (the platform choices list and dispatch dict)

4. **Add tests** in `test_generator.py` following existing patterns

5. **Document it** in [Platform Guide](Platform-Guide)

---

## Adding a New Operation

To add a sixteenth operation:

1. **Add the operation name** to `VALID_OPERATIONS` in `generator.py`

2. **Implement the operation block** for PyQGIS (in `generate_pyqgis`)

3. **Implement the operation block** for ArcPy (in `generate_arcpy`)

4. **Add tests** in `test_generator.py` — follow the existing pattern with `@pytest.mark.parametrize`

5. **Document it** in [Operations Reference](Operations-Reference)

---

## Generating the PDF User Guide

```bash
python make_pdf.py
```

This writes `GIS_Script_Generator_User_Guide.pdf` to the project root. The PDF is git-ignored.

---

## Git-Ignored Files

These files are generated locally and never committed:

```
maps/            # gis-catalogue PyQGIS output
maps_arcpy/      # gis-catalogue ArcPy output
*.pdf            # Generated PDF guide
schema.json      # --save-schema snapshots
*.sql            # May contain credentials or large data
htmlcov/         # Coverage HTML reports
*.gpkg           # Generated GeoPackage files
```
