# Kensington Project

The root-level scripts in this repository belong to a real-world GIS project for **Kensington Market and Chinatown, Toronto**. This page describes the project context, data pipeline, and how the Kensington scripts relate to the `gis-codegen` package.

---

## Overview

The Kensington project analyses the spatial, cultural, and demographic landscape of Toronto's Kensington Market and Chinatown neighbourhoods. It uses GIS data to support urban planning, heritage documentation, and community research.

**Target CRS:** EPSG 2952 — NAD83 / Ontario MTM Zone 10
**Source CRS:** Often WGS84 (EPSG 4326) — reprojected during pipeline

---

## Two Backend Architecture

The project intentionally uses two separate database backends:

| Backend | Tool | Purpose |
|---|---|---|
| **SQLite** | `migrate_to_sql.py` | Dashboard and BI reporting |
| **PostGIS** | `gis-codegen` + SQL files | Spatial analysis and map generation |

This dual-backend design is intentional — SQLite is simpler for tabular reporting, while PostGIS is required for spatial queries, topology, and CRS-aware analysis.

---

## Data Inventory

| Data type | Count |
|---|---|
| Shapefiles (`.shp`) | 85 |
| CSV files | 42 |
| GeoJSON files | 11 |
| PostGIS SQL files | 29 |
| GTFS transit feed | 1 |

Full details are in [DATA_CATALOG.md](../DATA_CATALOG.md).

---

## Pipeline Scripts

Root-level scripts form a sequential data pipeline:

### 1. Reprojection

**`reproject_to_mtm10.py`**
Batch reprojects all 85 WGS84 shapefiles to EPSG 2952 (NAD83 / Ontario MTM Zone 10). Must run before any other spatial analysis.

### 2. SQLite Loading (Dashboard Backend)

**`migrate_to_sql.py`**
Loads shapefiles and CSVs into a SQLite database for the BI dashboard.

### 3. Analytical Views

**`create_analytical_views.py`**
Creates SQL views in the SQLite database for aggregated analysis.

### 4. Dashboard

**`generate_dashboard.py`**
Produces an HTML BI report from the SQLite analytical views.

### 5. Static Map

**`generate_static_map.py`**
Creates a static map image using Matplotlib and GeoPandas.

### 6. Interactive Map

**`generate_interactive_map.py`**
Creates an interactive Folium map (Leaflet.js) for web viewing.

### 7. Kensington Map

**`create_kensington_map.py`**
Creates a styled Kensington-specific map product.

### 8. ArcGIS Pro Pipeline

**`arc_setup_gdb.py`**
Initialises an MTM10 Master GDB using ArcPy. Requires ArcGIS Pro.

**`arc_batch_import.py`**
Batch reprojects and imports all shapefiles into the master GDB. Requires ArcGIS Pro.

**`arc_topology_builder.py`**
Applies spatial topology rules to the GDB. Requires ArcGIS Pro.

### 9. QGIS Automation

**`qgis_master_setup.py`**
Automated QGIS project configuration using PyQGIS. Requires QGIS Python interpreter.

---

## Running the Pipeline (Windows)

`BUILD_PROJECT.bat` is a one-click runner for the full data pipeline on Windows:

```cmd
BUILD_PROJECT.bat
```

This runs the pipeline scripts in order. The pipeline is Windows-first — paths reference `C:\GDB` and the ArcGIS Pro installation.

---

## ArcPy Requirements

The `arc_*.py` scripts require **ArcGIS Pro** and its bundled Python environment:

- Cannot be installed via pip
- Must be run using the ArcGIS Pro Python interpreter
- Scripts are designed for Windows

---

## PyQGIS Requirements

`qgis_master_setup.py` requires QGIS's bundled Python interpreter:

- Cannot be installed via pip
- Must be run from the QGIS Python console, or with QGIS libraries on `sys.path`
- Works on Windows, macOS, and Linux

---

## Topology

The project defines spatial topology rules for data quality control. See:
- [TOPOLOGY_RULES.md](../TOPOLOGY_RULES.md) — topology constraint definitions
- [TOPOLOGY_SCHEMA.md](../TOPOLOGY_SCHEMA.md) — error tracking schema
- [QC_LOG.md](../QC_LOG.md) — quality control log and status

---

## QGIS Plugins

Recommended QGIS plugins for working with Kensington data are documented in [QGIS_PLUGINS.md](../QGIS_PLUGINS.md).

---

## Relationship to `gis-codegen`

The root-level Kensington scripts are **not part of the installable package**. They are project-specific utilities that:
- Are not imported by `src/gis_codegen/`
- Are not tested by the test suite
- Will not be included if you `pip install` the package
- Are maintained separately from the package's versioning

The `gis-codegen` package is a general-purpose tool. The Kensington scripts are one example of the kinds of analyses it enables.

---

## Continuation Context

For developers resuming work on the Kensington project, see [CONTINUATION_PROMPT.md](../CONTINUATION_PROMPT.md) for detailed context on where the project was left off and what steps remain.
