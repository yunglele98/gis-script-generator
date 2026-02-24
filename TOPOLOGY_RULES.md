# Kensington GIS: Topology Ruleset
**Project Standard:** EPSG 2952 (NAD83 / Ontario MTM zone 10)

To ensure spatial integrity between coincident layers (e.g., roads matching parcel edges), the following rules are mandated for the Master GDB:

## 1. Building & Infrastructure
- **Buildings** (Polygon): Must not overlap.
- **Buildings** (Polygon): Must not be self-intersecting.
- **Buildings** (Polygon): Must be contained within **Cadastral Parcels**.

## 2. Transportation Network
- **Road Network** (Line): Must not have dangles (unless dead-ends).
- **Road Network** (Line): Must not overlap itself.
- **Sidewalks** (Line): Must not overlap **Road Network** centerlines.
- **Sidewalks** (Line): Must match endpoint of adjacent segments (no gaps).

## 3. Administrative & Parcels
- **Cadastral Parcels** (Polygon): Must not have gaps.
- **Cadastral Parcels** (Polygon): Must not overlap.
- **AOI Boundaries** (Polygon): Must be coincident with **Census Tract** boundaries.

## 4. Environmental
- **Street Trees** (Point): Must be located within **Sidewalk** or **Green Space** buffers.
- **Canopy** (Polygon): Must not overlap **Building** footprints (unless overhanging).

## Validation Workflow
1. Run reproject_to_mtm10.py to stage data.
2. Import staged shapefiles into a **Feature Dataset** in the Master GDB.
3. Apply these rules via the **Topology** toolset in ArcGIS/QGIS.
