# CLI Reference

This page documents all commands and flags for `gis-codegen` and `gis-catalogue`.

---

## `gis-codegen`

The main command for connecting to PostGIS, extracting schema metadata, and generating GIS scripts.

### Synopsis

```
gis-codegen [CONNECTION OPTIONS] [OUTPUT OPTIONS] [OPERATION OPTIONS]
```

### Connection Options

| Flag | Default | Description |
|---|---|---|
| `--host HOST` | `localhost` | PostGIS server hostname or IP |
| `--port PORT` | `5432` | PostgreSQL port |
| `--dbname DBNAME` | `my_gis_db` | Database name |
| `--user USER` | `postgres` | Database username |
| `--password PASS` | *(env var)* | Password — prefer `PGPASSWORD` env var |
| `--config FILE` | *(search path)* | Path to `gis_codegen.toml` config file |

**Connection priority (highest to lowest):**
1. CLI flags
2. Config file `[database]` section
3. Environment variables (`PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`)
4. Built-in defaults

**Note:** Password has no built-in default. It must come from `--password`, the config file, or `PGPASSWORD`.

### Output Options

| Flag | Default | Description |
|---|---|---|
| `--platform PLATFORM` | *(required)* | Target platform — see [Platform Guide](Platform-Guide) |
| `--output FILE` / `-o FILE` | stdout | Write generated code to a file instead of stdout |
| `--save-schema FILE` | *(none)* | Save the extracted schema as JSON to a file |
| `--list-layers` | — | Print all detected spatial layers and exit |

### Platform Values

| Value | Description |
|---|---|
| `pyqgis` | PyQGIS standalone Python script |
| `arcpy` | ArcPy / ArcGIS Pro Python script |
| `folium` | Folium / Leaflet HTML map generator |
| `kepler` | Kepler.gl HTML map generator |
| `deck` | pydeck / deck.gl HTML map generator |
| `export` | GeoPackage export script |
| `qgs` | QGIS project file (`.qgs`) |
| `pyt` | ArcGIS Python Toolbox (`.pyt`) |

### Operation Options

| Flag | Description |
|---|---|
| `--op OPERATION` | Add a spatial operation to the generated script (repeatable) |

Operations are only supported by `pyqgis` and `arcpy` platforms. Using `--op` with other platforms emits a `[warn]` to stderr but still generates the file.

See [Operations Reference](Operations-Reference) for the full list.

### Examples

```bash
# Generate a PyQGIS script from a remote database
gis-codegen \
  --host postgis.example.com \
  --dbname city_gis \
  --user analyst \
  --platform pyqgis \
  --output load_layers.py

# Generate an ArcPy script with buffer and clip operations
gis-codegen --platform arcpy --op buffer --op clip --output process.py

# Generate a Folium map and run it immediately
gis-codegen --platform folium --output make_map.py
python make_map.py

# Save the schema to JSON for inspection
gis-codegen --platform pyqgis --save-schema schema.json --output load.py

# List all spatial layers in the database
gis-codegen --list-layers

# Use a custom config file
gis-codegen --config /etc/gis/production.toml --platform qgs --output project.qgs
```

---

## `gis-catalogue`

Batch-generates per-map scripts from an Excel spreadsheet. Each row in the spreadsheet represents one map/layer.

### Synopsis

```
gis-catalogue [OPTIONS] EXCEL_FILE
```

### Options

| Flag | Default | Description |
|---|---|---|
| `--platform PLATFORM` | `pyqgis` | Target platform (`pyqgis` or `arcpy`) |
| `--output-dir DIR` | `./maps` (pyqgis) or `./maps_arcpy` (arcpy) | Directory for output scripts |
| `--config FILE` | *(search path)* | Path to `gis_codegen.toml` |

### Excel Format

The input spreadsheet must contain the following columns:

| Column | Required | Description |
|---|---|---|
| `status` | Yes | Row is included only if value is `have` or `partial` (case-insensitive) |
| `spatial_layer_type` | Yes | Row is included only if value contains `Vector` |
| `map_name` | Yes | Used as the output script filename |
| `table_name` | Yes | PostGIS table to query |
| `schema_name` | No | Schema (defaults to `public`) |
| `renderer_type` | No | Symbology type (see below) |
| `color` | No | Layer colour |

Rows where `status` is not `have`/`partial`, or where `spatial_layer_type` does not contain `Vector`, are **silently skipped**.

### Output

Each included row generates one `.py` file in the output directory:
- `./maps/<map_name>.py` for PyQGIS
- `./maps_arcpy/<map_name>.py` for ArcPy

Both output directories are git-ignored by default.

### Examples

```bash
# Generate PyQGIS scripts from an Excel catalogue
gis-catalogue map_catalogue.xlsx

# Generate ArcPy scripts into a custom directory
gis-catalogue --platform arcpy --output-dir ./arcpy_scripts map_catalogue.xlsx

# Use a specific database config
gis-catalogue --config production.toml map_catalogue.xlsx
```

See [Excel Catalogue Tool](Excel-Catalogue-Tool) for full details on the spreadsheet format and symbology options.

---

## `gis-ui`

Starts the Flask web UI.

### Synopsis

```
gis-ui
```

No flags. The server starts on `http://localhost:5000`.

See [Web UI Guide](Web-UI-Guide) for usage details.

---

## Config File Format

`gis_codegen.toml` uses standard TOML syntax:

```toml
[database]
host     = "localhost"
port     = 5432
dbname   = "my_gis_db"
user     = "postgres"
# password — do NOT store here; use PGPASSWORD env var
```

All keys are optional — any key not present falls through to environment variables or built-in defaults.
