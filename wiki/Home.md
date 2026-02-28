# gis-script-generator Wiki

**gis-codegen** is a Python tool that connects to a PostGIS database, extracts spatial layer metadata, and generates ready-to-run GIS scripts or project files for eight platforms. It also includes a Flask web UI and an Excel-driven map catalogue tool.

---

## Quick Navigation

| Topic | Description |
|---|---|
| [Getting Started](Getting-Started) | Installation, environment setup, first run |
| [CLI Reference](CLI-Reference) | Full command-line reference for `gis-codegen` and `gis-catalogue` |
| [Web UI Guide](Web-UI-Guide) | Using the Flask web interface |
| [Platform Guide](Platform-Guide) | Output details for all 8 supported platforms |
| [Operations Reference](Operations-Reference) | 15 spatial operations with platform support matrix |
| [Excel Catalogue Tool](Excel-Catalogue-Tool) | Batch map generation from spreadsheets |
| [Architecture](Architecture) | Data flow, schema structure, module design |
| [Development & Testing](Development-and-Testing) | Running tests, CI/CD, contributing |
| [Kensington Project](Kensington-Project) | Context for the bundled data pipeline |
| [Troubleshooting](Troubleshooting) | Common errors and fixes |
| [FAQ](FAQ) | Frequently asked questions |

---

## What Does It Do?

```
PostGIS DB  →  extract schema  →  generate script  →  run in QGIS / ArcGIS / browser
```

1. **Connect** to any PostGIS database (read-only, zero writes)
2. **Extract** spatial layer metadata (geometry type, SRID, columns, PKs)
3. **Generate** a complete, runnable script for your chosen platform

---

## Two Components in One Repo

| Component | Location | Purpose |
|---|---|---|
| **gis-codegen package** | `src/gis_codegen/` | Installable CLI + Flask UI |
| **Kensington data pipeline** | Root-level `*.py` scripts | One-off ETL scripts for the Kensington Market GIS project |

See [Kensington Project](Kensington-Project) for details on the data pipeline.

---

## Supported Platforms

| Flag | Output | Use With |
|---|---|---|
| `pyqgis` | Python script | QGIS (PyQGIS) |
| `arcpy` | Python script | ArcGIS Pro |
| `folium` | Python → HTML map | Any browser |
| `kepler` | Python → HTML map | Any browser |
| `deck` | Python → HTML map | Any browser |
| `export` | GeoPackage export script | Any GIS app |
| `qgs` | `.qgs` project file | Open directly in QGIS |
| `pyt` | `.pyt` Python Toolbox | ArcGIS Pro |

---

## Badges

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
