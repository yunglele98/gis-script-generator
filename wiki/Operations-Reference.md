# Operations Reference

Spatial operations add geoprocessing steps to generated `pyqgis` and `arcpy` scripts. Pass one or more `--op` flags to include operations.

**Note:** Operations are only effective for `pyqgis` and `arcpy` platforms. Using `--op` with any other platform (`folium`, `kepler`, `deck`, `export`, `qgs`, `pyt`) emits a `[warn]` to stderr but still generates the file.

---

## Using Operations

```bash
# Single operation
gis-codegen --platform pyqgis --op buffer --output buffered.py

# Multiple operations (applied in order)
gis-codegen --platform arcpy --op reproject --op buffer --op dissolve --output pipeline.py
```

---

## General Operations (10)

These operations apply standard GIS geoprocessing to every layer in the schema.

| `--op` value | Description |
|---|---|
| `reproject` | Reproject all layers to a specified CRS |
| `export` | Export layers to a file format (GeoPackage, Shapefile, etc.) |
| `buffer` | Create buffer zones around features at a specified distance |
| `clip` | Clip layers to the extent of a clip layer |
| `select` | Select features by attribute expression |
| `dissolve` | Dissolve features by a common attribute value |
| `centroid` | Compute centroids of polygon or line features |
| `field_calc` | Calculate or update a field using an expression |
| `spatial_join` | Join attributes from one layer to another based on spatial relationship |
| `intersect` | Compute the geometric intersection of two or more layers |

---

## 3D Massing Operations (5)

These operations are designed for working with 3D building data and urban analysis. They require height or elevation attributes in the source layers.

| `--op` value | Description |
|---|---|
| `extrude` | Extrude polygon footprints to 3D by a height field |
| `z_stats` | Compute Z-value statistics (min, max, mean) for 3D features |
| `floor_ceiling` | Calculate floor and ceiling elevations from height fields |
| `volume` | Estimate volumetric calculations for extruded building masses |
| `scene_layer` | Publish layers as an ArcGIS Scene Layer (arcpy only) |

---

## Platform Support

| Operation | PyQGIS | ArcPy |
|---|---|---|
| `reproject` | ✅ | ✅ |
| `export` | ✅ | ✅ |
| `buffer` | ✅ | ✅ |
| `clip` | ✅ | ✅ |
| `select` | ✅ | ✅ |
| `dissolve` | ✅ | ✅ |
| `centroid` | ✅ | ✅ |
| `field_calc` | ✅ | ✅ |
| `spatial_join` | ✅ | ✅ |
| `intersect` | ✅ | ✅ |
| `extrude` | ✅ | ✅ |
| `z_stats` | ✅ | ✅ |
| `floor_ceiling` | ✅ | ✅ |
| `volume` | ✅ | ✅ |
| `scene_layer` | ⚠️ No-op | ✅ |

---

## Examples

### Buffer + Dissolve Pipeline (ArcPy)

```bash
gis-codegen \
  --platform arcpy \
  --op buffer \
  --op dissolve \
  --output buffer_dissolve.py
```

### 3D Massing Analysis (PyQGIS)

```bash
gis-codegen \
  --platform pyqgis \
  --op extrude \
  --op z_stats \
  --op volume \
  --output massing_analysis.py
```

### Full Processing Pipeline

```bash
gis-codegen \
  --platform arcpy \
  --op reproject \
  --op clip \
  --op buffer \
  --op spatial_join \
  --op dissolve \
  --output full_pipeline.py
```

---

## Invalid Operations

Passing an unrecognised `--op` value causes `gis-codegen` to exit with an error listing the valid operation names. Run `gis-codegen --help` to see available options.
