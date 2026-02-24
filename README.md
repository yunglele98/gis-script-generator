# gis-codegen

Generate ready-to-run GIS scripts and project files from a PostGIS database schema.

Connects to PostGIS, extracts spatial layer metadata, and writes scripts or project
files for eight GIS platforms — or reads an Excel map catalogue and writes one script
per map entry with auto-selected symbology. A browser-based web UI is also included.

---

## Templates generated

| Command | Output |
|---|---|
| `gis-codegen --platform pyqgis` | PyQGIS standalone script |
| `gis-codegen --platform arcpy` | ArcPy / ArcGIS Pro script |
| `gis-codegen --platform folium` | Folium / Leaflet HTML map |
| `gis-codegen --platform kepler` | Kepler.gl HTML map |
| `gis-codegen --platform deck` | pydeck / deck.gl HTML map |
| `gis-codegen --platform export` | GeoPackage export script |
| `gis-codegen --platform qgs` | QGIS project file (`.qgs`) — open directly in QGIS |
| `gis-codegen --platform pyt` | ArcGIS Python Toolbox (`.pyt`) — open in ArcGIS Pro |
| `gis-catalogue --platform pyqgis` | One PyQGIS script per catalogue map |
| `gis-catalogue --platform arcpy` | One ArcPy script per catalogue map |

---

## Prerequisites

- Python 3.10+
- A running PostGIS database (for live extraction)
- `PGPASSWORD` environment variable set before any command

---

## Installation

```bash
# Core package (PyQGIS, ArcPy, QGS, PYT templates):
pip install -e .

# With web mapping extras (Folium, Kepler.gl, pydeck):
pip install -e ".[web]"

# With web UI (Flask):
pip install -e ".[server]"

# With dev tools (pytest, coverage, openpyxl):
pip install -e ".[dev]"

# With PostGIS integration tests (requires Docker):
pip install -e ".[integration]"
```

---

## Quick start

```bash
# 1. Set credentials (never stored in scripts or config files)
export PGPASSWORD=your_password          # Linux / macOS
set PGPASSWORD=your_password             # Windows

# 2. Preview layers in the database
gis-codegen --list-layers

# 3. Generate a PyQGIS script
gis-codegen --platform pyqgis -o load_layers.py

# 4. Generate an ArcPy script with a buffer operation
gis-codegen --platform arcpy --op buffer -o analysis.py

# 5. Generate a QGIS project file (open directly in QGIS)
gis-codegen --platform qgs -o project.qgs

# 6. Generate an ArcGIS Python Toolbox
gis-codegen --platform pyt -o loader.pyt

# 7. Generate a Kepler.gl web map
gis-codegen --platform kepler -o kepler_map.py
python kepler_map.py                     # -> kepler_map.html
```

---

## Web UI

A browser-based form that connects to PostGIS, extracts the schema, and downloads
the generated file — no command line required.

```bash
pip install -e ".[server]"
gis-ui                                   # opens http://localhost:5000
```

Fill in your connection details, choose a platform, and click **Connect & Generate**.
The script or project file is returned as a download. The password is never stored.

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `PGPASSWORD` | *(required)* | Database password — never stored elsewhere |
| `PGHOST` | `localhost` | Database host |
| `PGPORT` | `5432` | Database port |
| `PGDATABASE` | `my_gis_db` | Database name |
| `PGUSER` | `postgres` | Database user |

---

## Config file  (`gis_codegen.toml`)

Place in the project root (or pass with `--config`). CLI flags override it.

```toml
[database]
host   = "localhost"
port   = 5432
dbname = "my_gis_db"
user   = "postgres"
# password = ...   # prefer PGPASSWORD env var

[defaults]
platform      = "pyqgis"
schema_filter = "public"
no_row_counts = false
```

---

## `gis-codegen` reference

```
gis-codegen [connection] [extraction] [generation]

Connection (override config and env vars):
  --host HOST         Database host
  --port PORT         Database port
  --dbname DBNAME     Database name
  --user USER         Database user
  --config FILE       TOML config file path

Extraction:
  --list-layers       Print layer table and exit
  --save-schema FILE  Save schema JSON and exit
  --no-row-counts     Skip row count queries (faster)
  --schema-filter S   Only include layers in schema S

Generation:
  --platform          pyqgis | arcpy | folium | kepler | deck | export | qgs | pyt
  --op OPERATION      Add an operation block (repeatable; ignored for qgs/pyt)
  --layer SCHEMA.TABLE  Restrict to one layer (repeatable)
  -o / --output FILE  Write to file (default: stdout)
```

---

## `gis-catalogue` reference

```
gis-catalogue --input catalogue.xlsx [options]

Required:
  -i / --input FILE       Path to catalogue .xlsx file

Optional:
  -o / --output-dir DIR   Output directory (default: ./maps/)
  -p / --platform         pyqgis | arcpy (default: pyqgis)
  --host / --port / --dbname / --user
  --schema FILE           Schema JSON from gis-codegen --save-schema (offline mode)
  --op OPERATION          Add an operation block to every script (repeatable)
  --list                  Preview filtered maps without writing files
```

Inclusion rules: rows where `status` is `have` or `partial`
**and** `spatial_layer_type` contains `Vector`.

---

## Operations (`--op`)

Applies to `pyqgis` and `arcpy` platforms only.

### General (10)

| Value | PyQGIS | ArcPy |
|---|---|---|
| `reproject` | `native:reprojectlayer` | `management.Project` |
| `export` | `QgsVectorFileWriter` | `conversion.FeatureClassToShapefile` |
| `buffer` | `native:buffer` | `analysis.Buffer` |
| `clip` | `native:clip` | `analysis.Clip` |
| `select` | `selectByExpression` | `SelectLayerByAttribute` |
| `dissolve` | `native:dissolve` | `management.Dissolve` |
| `centroid` | `native:centroids` | `management.FeatureToPoint` |
| `field_calc` | `native:fieldcalculator` | `management.CalculateField` |
| `spatial_join` | `joinattributesbylocation` | `analysis.SpatialJoin` |
| `intersect` | `native:intersection` | `analysis.Intersect` |

### 3D massing (5)

| Value | Description |
|---|---|
| `extrude` | Data-driven height extrusion renderer |
| `z_stats` | Min/max/mean Z vertex statistics |
| `floor_ceiling` | Extrude from `base_height` to `roof_height` field |
| `volume` | Approximate volume = footprint area × height |
| `scene_layer` | Export 3D layer package (.slpk / 3D tiles) |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev,server]"

# Run unit tests (no DB or Docker required)
python -m pytest tests/ -m "not integration" -v --cov=gis_codegen --cov-report=term-missing

# Run PostGIS integration tests (requires Docker)
pip install -e ".[integration]"
python -m pytest tests/test_integration.py -v -m integration

# Generate the PDF user guide
python make_pdf.py
```

### Test suite

| File | Tests | What it covers |
|---|---|---|
| `test_generator.py` | 173 | `safe_var`, type maps, 15 op blocks × 2 platforms, 8 generators incl. QGS/PYT |
| `test_catalogue.py` | 108 | Load/filter, 10 renderer blocks, symbology dispatch, both generators |
| `test_extractor.py` | 34 | `fetch_columns`, `fetch_primary_keys`, `extract_schema` |
| `test_app.py` | 11 | Flask routes, form rendering, file download, error handling |
| `test_integration.py` | 19 | Live PostGIS container via testcontainers (requires Docker) |
| **Total** | **345** | |

Unit tests (all except `test_integration.py`) run in under 2 seconds with no database required.

---

## Project layout

```
src/gis_codegen/
    __init__.py       Public API: connect, extract_schema, generate_*
    extractor.py      PostGIS metadata queries
    generator.py      Code generation (PyQGIS, ArcPy, Folium, Kepler, pydeck, QGS, PYT)
    catalogue.py      Excel-driven per-map code generation
    cli.py            gis-codegen CLI entry point
    app.py            Flask web UI (gis-ui entry point)
tests/
    conftest.py
    test_generator.py
    test_catalogue.py
    test_extractor.py
    test_app.py
    test_integration.py
.github/workflows/
    ci.yml            Unit + integration CI jobs
make_pdf.py           Generates GIS_Script_Generator_User_Guide.pdf
gis_codegen.toml      Example config file
```
