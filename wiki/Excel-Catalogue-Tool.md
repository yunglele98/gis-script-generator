# Excel Catalogue Tool

`gis-catalogue` reads a map catalogue spreadsheet (`.xlsx`) and generates one GIS script per map, applying symbology and renderer settings from the spreadsheet.

---

## Overview

Instead of generating a single script for all layers, `gis-catalogue` lets you define each map individually in a spreadsheet — including which layers to include, what symbology to apply, and how to render them.

**Use case:** A city GIS team maintains an Excel spreadsheet tracking 50+ map products. Running `gis-catalogue` once generates all 50 map scripts automatically.

---

## Installation

`openpyxl` is required to read `.xlsx` files:

```bash
pip install -e ".[dev]"
# or
pip install openpyxl
```

If `openpyxl` is missing, `gis-catalogue` exits with a helpful error message.

---

## Spreadsheet Format

The Excel file must have a sheet with the following columns:

### Required Columns

| Column | Values | Description |
|---|---|---|
| `status` | `have`, `partial`, *(anything else)* | Only `have` and `partial` rows are processed |
| `spatial_layer_type` | Must contain `Vector` | Raster-only and Table-only rows are skipped |
| `map_name` | Any string | Output script is named `<map_name>.py` |
| `table_name` | PostgreSQL table name | The layer's table in PostGIS |

### Optional Columns

| Column | Description |
|---|---|
| `schema_name` | PostgreSQL schema (defaults to `public`) |
| `renderer_type` | Symbology renderer (see Renderer Types below) |
| `color` | Layer colour (hex or named colour) |
| `label_field` | Field to use for labels |
| `opacity` | Layer opacity (0.0 – 1.0) |
| `geometry_type` | Override detected geometry type |

---

## Row Filtering Rules

A row is **included** if:
- `status` is `have` or `partial` (case-insensitive)
- `spatial_layer_type` contains the word `Vector` (case-insensitive)

A row is **skipped** if:
- `status` is anything other than `have` or `partial` (e.g. `want`, `missing`, `future`)
- `spatial_layer_type` does not contain `Vector` (e.g. `Raster`, `Table`)

Skipped rows generate no output and no warnings.

---

## Renderer Types

The `renderer_type` column controls symbology in generated PyQGIS/ArcPy scripts:

| `renderer_type` | Description |
|---|---|
| `single_symbol` | One colour for all features (default) |
| `categorized` | Colour by unique values in a field |
| `graduated` | Colour ramp by numeric field range |
| `rule_based` | Custom expression-based symbology |
| `heatmap` | Density heatmap (point layers) |
| `point_cluster` | Cluster nearby points |
| `point_displacement` | Displace overlapping points |
| `inverted_polygon` | Fill everything outside the polygon |
| `2.5d` | Pseudo-3D extrusion effect |
| `null_symbol` | No symbol (invisible / mask layer) |

---

## Running `gis-catalogue`

```bash
# Basic — generates PyQGIS scripts in ./maps/
gis-catalogue map_catalogue.xlsx

# ArcPy scripts in default ./maps_arcpy/ directory
gis-catalogue --platform arcpy map_catalogue.xlsx

# Custom output directory
gis-catalogue --output-dir /data/generated_maps map_catalogue.xlsx

# Custom config file
gis-catalogue --config production.toml map_catalogue.xlsx
```

---

## Output Structure

```
./maps/                     (PyQGIS, default)
├── Downtown_Overview.py
├── Heritage_Buildings.py
├── Transit_Corridors.py
└── ...

./maps_arcpy/               (ArcPy, default)
├── Downtown_Overview.py
├── Heritage_Buildings.py
└── ...
```

Both directories are git-ignored by default.

---

## Example Spreadsheet

| map_name | table_name | schema_name | status | spatial_layer_type | renderer_type | color |
|---|---|---|---|---|---|---|
| Downtown Overview | downtown_boundary | public | have | Vector Polygon | single_symbol | #FF6600 |
| Heritage Buildings | heritage_buildings | public | have | Vector Point | categorized | |
| Future Development | future_sites | public | partial | Vector Polygon | graduated | |
| Population Raster | pop_density | public | have | Raster | *(skipped — not Vector)* | |
| Wish List Layer | future_layer | public | want | Vector Polygon | *(skipped — status = want)* | |

From this spreadsheet, `gis-catalogue` would generate scripts for: `Downtown_Overview.py`, `Heritage_Buildings.py`, `Future_Development.py`.

---

## Relationship to `gis-codegen`

`gis-catalogue` uses the same PostGIS connection and code generation logic as `gis-codegen`, but:
- Input comes from an Excel file rather than CLI flags
- Output is one file per map, not one file for all layers
- Symbology/renderer blocks are included based on spreadsheet values
- The tool is designed for batch production workflows

---

## Troubleshooting

**`openpyxl` not installed:**
```
[ERROR] openpyxl is required for gis-catalogue. Install with: pip install openpyxl
```
Fix: `pip install openpyxl` or `pip install -e ".[dev]"`

**No scripts generated:**
- Check that at least one row has `status = have` or `partial`
- Check that `spatial_layer_type` contains `Vector`
- Look for typos in column names

**Script for a row is empty or wrong:**
- Verify the `table_name` exists in the database
- Run `gis-codegen --list-layers` to see available layers
