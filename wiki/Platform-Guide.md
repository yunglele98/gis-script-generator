# Platform Guide

`gis-codegen` supports eight output platforms. This page explains what each platform generates, how to use the output, and any platform-specific requirements.

---

## Platform Overview

| Flag | Output file | Open / run with |
|---|---|---|
| `pyqgis` | `.py` Python script | QGIS Python console or standalone |
| `arcpy` | `.py` Python script | ArcGIS Pro Python window or standalone |
| `folium` | `.py` Python script | Run with Python → produces HTML |
| `kepler` | `.py` Python script | Run with Python → produces HTML |
| `deck` | `.py` Python script | Run with Python → produces HTML |
| `export` | `.py` Python script | Run with Python → produces `.gpkg` files |
| `qgs` | `.qgs` QGIS project | Open directly in QGIS |
| `pyt` | `.pyt` Toolbox | Open in ArcGIS Pro Catalog |

---

## PyQGIS (`--platform pyqgis`)

Generates a standalone Python script that:
- Imports PyQGIS libraries
- Creates a `QgsApplication` instance
- Adds each spatial layer as a `QgsVectorLayer` or `QgsRasterLayer`
- Applies optional spatial operations (see [Operations Reference](Operations-Reference))
- Saves the resulting project

**Requirements:** QGIS must be installed. Either run the script from the QGIS Python console, or ensure QGIS Python libraries are on `sys.path`.

**Supports operations:** Yes — all 15 operations (general + 3D massing)

**Example:**
```bash
gis-codegen --platform pyqgis --op buffer --op dissolve --output load_and_process.py
```

---

## ArcPy (`--platform arcpy`)

Generates a Python script that:
- Imports `arcpy`
- Sets the workspace and spatial reference
- Adds each spatial layer
- Applies optional geoprocessing operations

**Requirements:** ArcGIS Pro must be installed. Run the script using ArcGIS Pro's bundled Python environment (`python.exe` from the ArcGIS Pro installation).

**Supports operations:** Yes — all 15 operations (general + 3D massing)

**Example:**
```bash
gis-codegen --platform arcpy --op reproject --op spatial_join --output process.py
```

---

## Folium (`--platform folium`)

Generates a Python script that:
- Reads each layer from PostGIS using GeoPandas
- Adds each layer to a Folium (Leaflet.js) map
- Saves the result as `index.html`

**Requirements:** `pip install -e ".[web]"` (installs `folium`, `geopandas`, `sqlalchemy`)

**Supports operations:** No — `--op` flags emit a warning and are ignored

**Example:**
```bash
gis-codegen --platform folium --output make_map.py
python make_map.py       # writes index.html
# Open index.html in any browser
```

---

## Kepler.gl (`--platform kepler`)

Generates a Python script that:
- Reads each layer using GeoPandas
- Exports data to a Kepler.gl HTML map

**Requirements:** `pip install -e ".[web]"` (installs `keplergl`, `geopandas`)

**Supports operations:** No

**Example:**
```bash
gis-codegen --platform kepler --output kepler_map.py
python kepler_map.py
```

---

## pydeck / deck.gl (`--platform deck`)

Generates a Python script that:
- Reads each layer using GeoPandas
- Creates a pydeck `Layer` for each feature type
- Exports an HTML file with deck.gl visualisation

**Requirements:** `pip install -e ".[web]"` (installs `pydeck`, `geopandas`)

**Supports operations:** No

**Example:**
```bash
gis-codegen --platform deck --output deck_map.py
python deck_map.py
```

---

## GeoPackage Export (`--platform export`)

Generates a Python script that:
- Connects to PostGIS using psycopg2 and GeoPandas
- Exports each spatial layer to a `.gpkg` (GeoPackage) file
- One GeoPackage file per layer, in the current directory

**Requirements:** `pip install -e ".[web]"` (installs `geopandas`)

**Supports operations:** No

**Example:**
```bash
gis-codegen --platform export --output export_layers.py
python export_layers.py   # writes buildings.gpkg, roads.gpkg, etc.
```

---

## QGIS Project File (`--platform qgs`)

Generates a `.qgs` XML file that:
- Defines all spatial layers with their PostGIS connections
- Sets coordinate reference systems, layer names, and rendering order
- Can be opened directly in QGIS without running any Python

**Requirements:** QGIS desktop application

**Supports operations:** No — project files define layer structure only

**Example:**
```bash
gis-codegen --platform qgs --output my_project.qgs
# Double-click my_project.qgs to open in QGIS
```

---

## ArcGIS Python Toolbox (`--platform pyt`)

Generates a `.pyt` Python Toolbox file that:
- Defines an ArcGIS toolbox with one tool per spatial layer
- Each tool includes parameter definitions for the layer
- Can be added to ArcGIS Pro via the Catalog pane

**Requirements:** ArcGIS Pro

**Supports operations:** No — the toolbox provides a GUI wrapper; operations are defined inside each tool

**Example:**
```bash
gis-codegen --platform pyt --output GIS_Tools.pyt
# In ArcGIS Pro: Catalog → Toolboxes → Add Toolbox → GIS_Tools.pyt
```

---

## Operations Support Matrix

| Platform | General ops | 3D Massing ops |
|---|---|---|
| `pyqgis` | ✅ | ✅ |
| `arcpy` | ✅ | ✅ |
| `folium` | ⚠️ Ignored | ⚠️ Ignored |
| `kepler` | ⚠️ Ignored | ⚠️ Ignored |
| `deck` | ⚠️ Ignored | ⚠️ Ignored |
| `export` | ⚠️ Ignored | ⚠️ Ignored |
| `qgs` | ⚠️ Ignored | ⚠️ Ignored |
| `pyt` | ⚠️ Ignored | ⚠️ Ignored |

⚠️ = Warning emitted to stderr, file still generated

See [Operations Reference](Operations-Reference) for the full list of operations.
