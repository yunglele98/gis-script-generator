# Kensington GIS: Topology Validation Schema
**Project Standard:** EPSG 2952 (NAD83 / Ontario MTM zone 10)

This directory is reserved for topology error features generated during validation.

## Required Layers (to be created in GIS software):
1. **Validation_Errors_Point.shp**
   - **Fields:** Error_ID (Int), Rule_ID (Int), Description (Text), Severity (Text)
2. **Validation_Errors_Line.shp**
   - **Fields:** Error_ID (Int), Rule_ID (Int), Description (Text), Severity (Text)
3. **Validation_Errors_Polygon.shp**
   - **Fields:** Error_ID (Int), Rule_ID (Int), Description (Text), Severity (Text)

## Validation Rules (Reference TOPOLOGY_RULES.md):
- **Rule 101:** Building overlap.
- **Rule 201:** Road dangle.
- **Rule 301:** Parcel gap.
