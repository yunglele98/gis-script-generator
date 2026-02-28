# Getting Started

This page walks you through installing `gis-codegen`, configuring your PostGIS connection, and generating your first GIS script.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | Uses `str \| None` union syntax (PEP 604) |
| PostGIS | Any | Read-only access required |
| pip | Any | For installation |

Optional, depending on your use case:
- **Docker** — for running integration tests
- **QGIS** — to use generated `.qgs` project files or run PyQGIS scripts
- **ArcGIS Pro** — to use generated `.pyt` toolboxes or run ArcPy scripts

---

## Installation

Install the package with the extras appropriate for your use case:

```bash
# Core package only (CLI, no web UI)
pip install -e .

# With web UI (Flask)
pip install -e ".[server]"

# With web mapping libraries (folium, keplergl, pydeck)
pip install -e ".[web]"

# With dev/test tools (pytest, openpyxl)
pip install -e ".[dev]"

# Recommended for development: everything except integration
pip install -e ".[dev,server]"

# With PostGIS integration tests (requires Docker)
pip install -e ".[dev,integration]"
```

After installation, three entry points become available:

| Command | Purpose |
|---|---|
| `gis-codegen` | Main CLI — connect, extract, generate |
| `gis-catalogue` | Batch generation from an Excel spreadsheet |
| `gis-ui` | Flask web UI on `http://localhost:5000` |

---

## Environment Setup

### Set Your Password

Passwords are **never** stored in config files. Always use the environment variable:

```bash
export PGPASSWORD=your_password
```

On Windows:
```cmd
set PGPASSWORD=your_password
```

### Other Connection Variables (optional)

```bash
export PGHOST=localhost      # default: localhost
export PGPORT=5432           # default: 5432
export PGDATABASE=my_gis_db # default: my_gis_db
export PGUSER=postgres       # default: postgres
```

### Config File (optional)

Create `gis_codegen.toml` in your project root:

```toml
[database]
host     = "localhost"
port     = 5432
dbname   = "my_gis_db"
user     = "postgres"
# Do NOT put password here — use PGPASSWORD env var
```

The tool searches for this file in the following order:
1. Path from `--config FILE` flag
2. Path in `$GIS_CODEGEN_CONFIG` env var
3. `./gis_codegen.toml` (current directory)
4. `~/.config/gis_codegen/config.toml` (user config dir)

---

## Your First Script

### List All Spatial Layers

```bash
gis-codegen --list-layers
```

This connects to PostGIS and prints a table of all spatial layers found in `geometry_columns`.

### Generate a PyQGIS Script

```bash
gis-codegen --platform pyqgis --output my_layers.py
```

This generates a complete Python script that loads all your spatial layers into QGIS.

### Generate an ArcPy Script with Operations

```bash
gis-codegen --platform arcpy --op buffer --op dissolve --output process_layers.py
```

### Generate a Folium Map

```bash
gis-codegen --platform folium --output map_viewer.py
python map_viewer.py   # produces index.html
```

### Generate a QGIS Project File

```bash
gis-codegen --platform qgs --output project.qgs
# Open project.qgs directly in QGIS
```

---

## Connection Options

All connection parameters can be passed as CLI flags, which take highest priority:

```bash
gis-codegen \
  --host db.example.com \
  --port 5432 \
  --dbname spatial_db \
  --user readonly_user \
  --platform pyqgis \
  --output output.py
```

---

## Next Steps

- [CLI Reference](CLI-Reference) — full flag reference
- [Platform Guide](Platform-Guide) — what each platform generates
- [Operations Reference](Operations-Reference) — available spatial operations
- [Web UI Guide](Web-UI-Guide) — browser-based interface
