# gis-codegen

Generate ready-to-run Python scripts from a PostGIS database schema.

Connects to PostGIS, extracts spatial layer metadata, and writes scripts
for five GIS platforms — or reads an Excel map catalogue and writes one
script per map entry with auto-selected symbology.

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
# Core package (PyQGIS + ArcPy templates):
pip install -e .

# With web mapping extras (Folium, Kepler.gl, pydeck):
pip install -e ".[web]"

# With dev tools (pytest, coverage, openpyxl):
pip install -e ".[dev]"
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

# 5. Generate a Kepler.gl web map
gis-codegen --platform kepler -o kepler_map.py
python kepler_map.py                     # -> kepler_map.html
```

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
  --platform          pyqgis | arcpy | folium | kepler | deck | export
  --op OPERATION      Add an operation block (repeatable)
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
  --list                  Preview filtered maps without writing files
```

Inclusion rules: rows where `status` is `have` or `partial`
**and** `spatial_layer_type` contains `Vector`.

---

## Operations (`--op`)

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
pip install -e ".[dev]"

# Run the full test suite (265 tests, no DB required)
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=gis_codegen --cov-report=term-missing

# Generate the PDF user guide
python make_pdf.py
```

### Test suite

| File | Tests | Coverage |
|---|---|---|
| `test_generator.py` | 140 | `safe_var`, type maps, 15 op blocks × 2 platforms, 6 generators |
| `test_catalogue.py` | 108 | Load/filter, 10 renderer blocks, symbology dispatch, both generators |
| `test_extractor.py` | 34 | `DB_CONFIG`, `fetch_columns`, `fetch_primary_keys`, `extract_schema` |
| **Total** | **312** | |

All tests are pure unit tests (mocked connections) and run in under 1 second.

---

## Project layout

```
src/gis_codegen/
    __init__.py       Public API: connect, extract_schema, generate_*
    extractor.py      PostGIS metadata queries
    generator.py      Code generation (PyQGIS, ArcPy, Folium, Kepler, pydeck)
    catalogue.py      Excel-driven per-map code generation
    cli.py            gis-codegen CLI entry point
tests/
    conftest.py
    test_generator.py
    test_catalogue.py
    test_extractor.py
make_pdf.py           Generates GIS_Script_Generator_User_Guide.pdf
gis_codegen.toml      Example config file
```
