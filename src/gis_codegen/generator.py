"""
gis_codegen.generator

Generates a PyQGIS (standalone) or ArcPy (ArcGIS Pro) script from a schema
dict produced by gis_codegen.extractor.
"""

import hashlib
import json
import sys
import argparse
import textwrap
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .layout import TemplateConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pg_type_to_pyqgis(data_type: str) -> str:
    """Map PostgreSQL data types to readable PyQGIS field type hints (comments only)."""
    mapping = {
        "integer": "int",
        "bigint": "int",
        "smallint": "int",
        "numeric": "float",
        "double precision": "float",
        "real": "float",
        "boolean": "bool",
        "text": "str",
        "character varying": "str",
        "character": "str",
        "date": "QDate",
        "timestamp without time zone": "QDateTime",
        "timestamp with time zone": "QDateTime",
        "uuid": "str",
        "json": "str",
        "jsonb": "str",
    }
    return mapping.get(data_type, "str")


def pg_type_to_arcpy(data_type: str) -> str:
    """Map PostgreSQL data types to ArcPy field type strings."""
    mapping = {
        "integer": "LONG",
        "bigint": "DOUBLE",
        "smallint": "SHORT",
        "numeric": "DOUBLE",
        "double precision": "DOUBLE",
        "real": "FLOAT",
        "boolean": "SHORT",
        "text": "TEXT",
        "character varying": "TEXT",
        "character": "TEXT",
        "date": "DATE",
        "timestamp without time zone": "DATE",
        "timestamp with time zone": "DATE",
        "uuid": "TEXT",
        "json": "TEXT",
        "jsonb": "TEXT",
    }
    return mapping.get(data_type, "TEXT")


def safe_var(name: str) -> str:
    """Convert a table name to a safe Python variable name."""
    return name.replace("-", "_").replace(" ", "_").replace(".", "_")


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

VALID_OPERATIONS = [
    # general
    "reproject", "export", "buffer", "clip", "select",
    "dissolve", "centroid", "field_calc", "spatial_join", "intersect",
    # 3D massing
    "extrude", "z_stats", "floor_ceiling", "volume", "scene_layer",
]


def _pyqgis_op_blocks(var: str, table: str, columns: list[dict], ops: set[str]) -> list[str]:
    """Return 4-space-indented lines for each requested PyQGIS operation."""
    lines = []
    first_col = columns[0]["name"] if columns else "field_name"

    if "reproject" in ops:
        lines += [
            f'    # --- reproject ---',
            f'    # TODO: change "EPSG:4326" to your target CRS',
            f'    _target_crs_{var} = QgsCoordinateReferenceSystem("EPSG:4326")',
            f'    _reproj_{var} = processing.run("native:reprojectlayer", {{',
            f'        "INPUT":      lyr_{var},',
            f'        "TARGET_CRS": _target_crs_{var},',
            f'        "OUTPUT":     "memory:",',
            f'    }})',
            f'    lyr_{var}_reprojected = _reproj_{var}["OUTPUT"]',
            f'    print(f"  Reprojected: {{lyr_{var}_reprojected.featureCount()}} features")',
            f'',
        ]

    if "export" in ops:
        lines += [
            f'    # --- export to GeoJSON ---',
            f'    # TODO: change output path',
            f'    from qgis.core import QgsVectorFileWriter',
            f'    _out_{var} = f"/tmp/{table}.geojson"',
            f'    _err_{var}, _msg_{var} = QgsVectorFileWriter.writeAsVectorFormat(',
            f'        lyr_{var}, _out_{var}, "utf-8", lyr_{var}.crs(), "GeoJSON",',
            f'    )',
            f'    if _err_{var} == QgsVectorFileWriter.NoError:',
            f'        print(f"  Exported to {{_out_{var}}}")',
            f'    else:',
            f'        print(f"  Export error: {{_msg_{var}}}")',
            f'',
        ]

    if "buffer" in ops:
        lines += [
            f'    # --- buffer ---',
            f'    # TODO: set DISTANCE in layer CRS units',
            f'    _buf_{var} = processing.run("native:buffer", {{',
            f'        "INPUT":         lyr_{var},',
            f'        "DISTANCE":      100,',
            f'        "SEGMENTS":      5,',
            f'        "END_CAP_STYLE": 0,',
            f'        "JOIN_STYLE":    0,',
            f'        "MITER_LIMIT":   2,',
            f'        "DISSOLVE":      False,',
            f'        "OUTPUT":        "memory:",',
            f'    }})',
            f'    lyr_{var}_buffer = _buf_{var}["OUTPUT"]',
            f'    print(f"  Buffer: {{lyr_{var}_buffer.featureCount()}} features")',
            f'',
        ]

    if "clip" in ops:
        lines += [
            f'    # --- clip ---',
            f'    # TODO: define clip_layer_{var}, then uncomment',
            f'    # clip_layer_{var} = QgsVectorLayer("/path/to/boundary.shp", "boundary", "ogr")',
            f'    # _clip_{var} = processing.run("native:clip", {{',
            f'    #     "INPUT":   lyr_{var},',
            f'    #     "OVERLAY": clip_layer_{var},',
            f'    #     "OUTPUT":  "memory:",',
            f'    # }})',
            f'    # lyr_{var}_clipped = _clip_{var}["OUTPUT"]',
            f'    # print(f"  Clipped: {{lyr_{var}_clipped.featureCount()}} features")',
            f'',
        ]

    if "select" in ops:
        expr = f'"{first_col}" IS NOT NULL'
        lines += [
            f'    # --- select by attribute ---',
            f'    # TODO: update expression',
            f"    lyr_{var}.selectByExpression('{expr}')",
            f'    print(f"  Selected: {{lyr_{var}.selectedFeatureCount()}} features")',
            f'    lyr_{var}.removeSelection()',
            f'',
        ]

    if "dissolve" in ops:
        lines += [
            f'    # --- dissolve ---',
            f'    # TODO: set FIELD list (empty = dissolve all into one feature)',
            f'    _diss_{var} = processing.run("native:dissolve", {{',
            f'        "INPUT":  lyr_{var},',
            f'        "FIELD":  [],  # e.g. ["district_name"]',
            f'        "OUTPUT": "memory:",',
            f'    }})',
            f'    lyr_{var}_dissolved = _diss_{var}["OUTPUT"]',
            f'    print(f"  Dissolved: {{lyr_{var}_dissolved.featureCount()}} features")',
            f'',
        ]

    if "centroid" in ops:
        lines += [
            f'    # --- centroid ---',
            f'    _cent_{var} = processing.run("native:centroids", {{',
            f'        "INPUT":     lyr_{var},',
            f'        "ALL_PARTS": False,',
            f'        "OUTPUT":    "memory:",',
            f'    }})',
            f'    lyr_{var}_centroids = _cent_{var}["OUTPUT"]',
            f'    print(f"  Centroids: {{lyr_{var}_centroids.featureCount()}} points")',
            f'',
        ]

    if "field_calc" in ops:
        lines += [
            f'    # --- field calculator ---',
            f'    # TODO: set FIELD_NAME and FORMULA (uses QGIS expression syntax)',
            f'    _calc_{var} = processing.run("native:fieldcalculator", {{',
            f'        "INPUT":           lyr_{var},',
            f'        "FIELD_NAME":      "new_field",  # TODO: change',
            f'        "FIELD_TYPE":      0,            # 0=float, 1=int, 2=string',
            f'        "FIELD_LENGTH":    20,',
            f'        "FIELD_PRECISION": 3,',
            f'        "FORMULA":         "$area",      # TODO: change expression',
            f'        "OUTPUT":          "memory:",',
            f'    }})',
            f'    lyr_{var}_calculated = _calc_{var}["OUTPUT"]',
            f'    print(f"  Field calculated: {{lyr_{var}_calculated.featureCount()}} features")',
            f'',
        ]

    if "spatial_join" in ops:
        lines += [
            f'    # --- spatial join ---',
            f'    # TODO: define join_layer_{var}, then uncomment',
            f'    # join_layer_{var} = QgsVectorLayer("/path/to/join.shp", "join", "ogr")',
            f'    # _sjoin_{var} = processing.run("native:joinattributesbylocation", {{',
            f'    #     "INPUT":              lyr_{var},',
            f'    #     "JOIN":               join_layer_{var},',
            f'    #     "PREDICATE":          [0],  # 0=intersects, 1=contains, 2=equals',
            f'    #     "JOIN_FIELDS":        [],   # empty = all fields',
            f'    #     "METHOD":             1,    # 1=first match, 2=largest overlap',
            f'    #     "DISCARD_NONMATCHING": False,',
            f'    #     "OUTPUT":             "memory:",',
            f'    # }})',
            f'    # lyr_{var}_joined = _sjoin_{var}["OUTPUT"]',
            f'    # print(f"  Spatial join: {{lyr_{var}_joined.featureCount()}} features")',
            f'',
        ]

    if "intersect" in ops:
        lines += [
            f'    # --- intersect ---',
            f'    # TODO: define overlay_layer_{var}, then uncomment',
            f'    # overlay_layer_{var} = QgsVectorLayer("/path/to/overlay.shp", "overlay", "ogr")',
            f'    # _isect_{var} = processing.run("native:intersection", {{',
            f'    #     "INPUT":          lyr_{var},',
            f'    #     "OVERLAY":        overlay_layer_{var},',
            f'    #     "INPUT_FIELDS":   [],',
            f'    #     "OVERLAY_FIELDS": [],',
            f'    #     "OUTPUT":         "memory:",',
            f'    # }})',
            f'    # lyr_{var}_intersected = _isect_{var}["OUTPUT"]',
            f'    # print(f"  Intersect: {{lyr_{var}_intersected.featureCount()}} features")',
            f'',
        ]

    # ------------------------------------------------------------------
    # 3D massing operations
    # ------------------------------------------------------------------

    if "extrude" in ops:
        lines += [
            f'    # --- 3D extrude ---',
            f'    # Applies a data-defined extrusion renderer to the layer.',
            f'    # TODO: set HEIGHT_FIELD to your building height attribute.',
            f'    from qgis.core import (',
            f'        QgsPolygon3DSymbol, QgsVectorLayer3DRenderer,',
            f'        QgsAbstract3DSymbol, QgsProperty,',
            f'    )',
            f'    _HEIGHT_FIELD_{var} = "height"  # TODO: change',
            f'    _sym3d_{var} = QgsPolygon3DSymbol()',
            f'    _ddp_{var}   = _sym3d_{var}.dataDefinedProperties()',
            f'    _ddp_{var}.setProperty(',
            f'        QgsAbstract3DSymbol.PropertyExtrusionHeight,',
            f'        QgsProperty.fromField(_HEIGHT_FIELD_{var}),',
            f'    )',
            f'    _sym3d_{var}.setDataDefinedProperties(_ddp_{var})',
            f'    _rndr3d_{var} = QgsVectorLayer3DRenderer()',
            f'    _rndr3d_{var}.setSymbol(_sym3d_{var})',
            f'    lyr_{var}.setRenderer3D(_rndr3d_{var})',
            f'    lyr_{var}.triggerRepaint()',
            f'    print(f"  3D extrusion applied using \'{{_HEIGHT_FIELD_{var}}}\'")',
            f'',
        ]

    if "z_stats" in ops:
        lines += [
            f'    # --- Z statistics ---',
            f'    from qgis.core import QgsWkbTypes',
            f'    if QgsWkbTypes.hasZ(lyr_{var}.wkbType()):',
            f'        _zvals_{var} = []',
            f'        for _feat in lyr_{var}.getFeatures():',
            f'            for _v in _feat.geometry().vertices():',
            f'                _zvals_{var}.append(_v.z())',
            f'        if _zvals_{var}:',
            f'            print(f"  Z min : {{min(_zvals_{var}):.3f}}")',
            f'            print(f"  Z max : {{max(_zvals_{var}):.3f}}")',
            f'            print(f"  Z mean: {{sum(_zvals_{var})/len(_zvals_{var}):.3f}}")',
            f'    else:',
            f'        print("  Layer has no Z values — load a 3D geometry source.")',
            f'',
        ]

    if "floor_ceiling" in ops:
        lines += [
            f'    # --- floor / ceiling heights ---',
            f'    # Extrudes from a base elevation to a roof elevation using two fields.',
            f'    # TODO: set BASE_FIELD and ROOF_FIELD.',
            f'    from qgis.core import (',
            f'        QgsPolygon3DSymbol, QgsVectorLayer3DRenderer,',
            f'        QgsAbstract3DSymbol, QgsProperty,',
            f'    )',
            f'    _BASE_FIELD_{var} = "base_height"  # TODO: change',
            f'    _ROOF_FIELD_{var} = "roof_height"  # TODO: change',
            f'    _sym_fc_{var} = QgsPolygon3DSymbol()',
            f'    _ddp_fc_{var} = _sym_fc_{var}.dataDefinedProperties()',
            f'    # Base (floor) elevation',
            f'    _ddp_fc_{var}.setProperty(',
            f'        QgsAbstract3DSymbol.PropertyHeight,',
            f'        QgsProperty.fromField(_BASE_FIELD_{var}),',
            f'    )',
            f'    # Extrusion = roof - base',
            f'    _ddp_fc_{var}.setProperty(',
            f'        QgsAbstract3DSymbol.PropertyExtrusionHeight,',
            f'        QgsProperty.fromExpression(',
            f'            f\'"{{_ROOF_FIELD_{var}}}" - "{{_BASE_FIELD_{var}}}"\'',
            f'        ),',
            f'    )',
            f'    _sym_fc_{var}.setDataDefinedProperties(_ddp_fc_{var})',
            f'    _rndr_fc_{var} = QgsVectorLayer3DRenderer()',
            f'    _rndr_fc_{var}.setSymbol(_sym_fc_{var})',
            f'    lyr_{var}.setRenderer3D(_rndr_fc_{var})',
            f'    lyr_{var}.triggerRepaint()',
            f'    print(f"  Floor/ceiling extrusion: base=\'{{_BASE_FIELD_{var}}}\' roof=\'{{_ROOF_FIELD_{var}}}\'")',
            f'',
        ]

    if "volume" in ops:
        lines += [
            f'    # --- approximate volume (footprint area × height) ---',
            f'    # TODO: set HEIGHT_FIELD.',
            f'    # For exact 3D volume use ST_Volume() directly in PostGIS.',
            f'    _VOL_HEIGHT_{var} = "height"  # TODO: change',
            f'    _total_vol_{var} = 0.0',
            f'    for _feat in lyr_{var}.getFeatures():',
            f'        _h = _feat[_VOL_HEIGHT_{var}]',
            f'        if _h:',
            f'            _total_vol_{var} += _feat.geometry().area() * float(_h)',
            f'    print(f"  Approx. total volume: {{_total_vol_{var}:,.1f}} (CRS units³)")',
            f'',
        ]

    if "scene_layer" in ops:
        lines += [
            f'    # --- export to 3D Tiles (QGIS 3.34+) ---',
            f'    # TODO: set output directory. Requires the layer to have a 3D renderer.',
            f'    _out_tiles_{var} = f"/tmp/{table}_3dtiles"',
            f'    import os as _os',
            f'    _os.makedirs(_out_tiles_{var}, exist_ok=True)',
            f'    # processing.run("native:convert3dtiles", {{',
            f'    #     "INPUT":           lyr_{var},',
            f'    #     "OUTPUT_FOLDER":   _out_tiles_{var},',
            f'    #     "COMPRESSION":     0,  # 0=None, 1=GZIP',
            f'    # }})',
            f'    # print(f"  3D Tiles written to: {{_out_tiles_{var}}}")',
            f'',
        ]

    return lines


def _arcpy_op_blocks(var: str, table: str, columns: list[dict], ops: set[str]) -> list[str]:
    """Return 4-space-indented lines for each requested ArcPy operation."""
    lines = []
    first_col = columns[0]["name"] if columns else "field_name"

    if "reproject" in ops:
        lines += [
            f'    # --- reproject ---',
            f'    # TODO: set output path and target WKID',
            f'    _out_reproj_{var} = os.path.join(tempfile.gettempdir(), "{table}_reproj.shp")',
            f'    arcpy.management.Project(',
            f'        fc_{var},',
            f'        _out_reproj_{var},',
            f'        arcpy.SpatialReference(4326),  # TODO: change WKID',
            f'    )',
            f'    print(f"  Reprojected to: {{_out_reproj_{var}}}")',
            f'',
        ]

    if "export" in ops:
        lines += [
            f'    # --- export ---',
            f'    # TODO: set output directory',
            f'    _out_dir_{var} = tempfile.gettempdir()',
            f'    arcpy.conversion.FeatureClassToShapefile(fc_{var}, _out_dir_{var})',
            f'    print(f"  Exported shapefile to: {{_out_dir_{var}}}")',
            f'    # To export as GeoJSON:',
            f'    # arcpy.conversion.FeaturesToJSON(',
            f'    #     fc_{var},',
            f'    #     os.path.join(_out_dir_{var}, "{table}.geojson"),',
            f'    #     geoJSON="GEOJSON",',
            f'    # )',
            f'',
        ]

    if "buffer" in ops:
        lines += [
            f'    # --- buffer ---',
            f'    # TODO: set output path and distance',
            f'    _out_buf_{var} = os.path.join(tempfile.gettempdir(), "{table}_buffer.shp")',
            f'    arcpy.analysis.Buffer(',
            f'        fc_{var},',
            f'        _out_buf_{var},',
            f'        "100 Meters",  # TODO: change distance and units',
            f'        "FULL", "ROUND", "NONE",',
            f'    )',
            f'    print(f"  Buffer saved to: {{_out_buf_{var}}}")',
            f'',
        ]

    if "clip" in ops:
        lines += [
            f'    # --- clip ---',
            f'    # TODO: set clip boundary path, then uncomment',
            f'    # _clip_fc_{var}  = r"C:\\path\\to\\boundary.shp"',
            f'    # _out_clip_{var} = os.path.join(tempfile.gettempdir(), "{table}_clipped.shp")',
            f'    # arcpy.analysis.Clip(fc_{var}, _clip_fc_{var}, _out_clip_{var})',
            f'    # print(f"  Clipped to: {{_out_clip_{var}}}")',
            f'',
        ]

    if "select" in ops:
        where = f"{first_col} IS NOT NULL"
        lines += [
            f'    # --- select by attribute ---',
            f'    # TODO: update where_clause',
            f'    _lyr_sel_{var} = arcpy.management.MakeFeatureLayer(fc_{var}, "{table}_sel")[0]',
            f'    arcpy.management.SelectLayerByAttribute(',
            f'        _lyr_sel_{var}, "NEW_SELECTION", "{where}",',
            f'    )',
            f'    _sel_count_{var} = int(arcpy.management.GetCount(_lyr_sel_{var})[0])',
            f'    print(f"  Selected: {{_sel_count_{var}}} features")',
            f'    arcpy.management.Delete(_lyr_sel_{var})',
            f'',
        ]

    if "dissolve" in ops:
        lines += [
            f'    # --- dissolve ---',
            f'    # TODO: set dissolve_field (None = dissolve all into one feature)',
            f'    _out_diss_{var} = os.path.join(tempfile.gettempdir(), "{table}_dissolved.shp")',
            f'    arcpy.management.Dissolve(',
            f'        fc_{var},',
            f'        _out_diss_{var},',
            f'        dissolve_field=None,  # e.g. "district_name"',
            f'        multi_part="MULTI_PART",',
            f'    )',
            f'    print(f"  Dissolved to: {{_out_diss_{var}}}")',
            f'',
        ]

    if "centroid" in ops:
        lines += [
            f'    # --- centroid ---',
            f'    _out_cent_{var} = os.path.join(tempfile.gettempdir(), "{table}_centroids.shp")',
            f'    arcpy.management.FeatureToPoint(',
            f'        fc_{var}, _out_cent_{var}, point_location="CENTROID",',
            f'    )',
            f'    print(f"  Centroids saved to: {{_out_cent_{var}}}")',
            f'',
        ]

    if "field_calc" in ops:
        lines += [
            f'    # --- field calculator ---',
            f'    # Copies to temp first to avoid modifying the source DB',
            f'    # TODO: set field name, type, and expression',
            f'    _out_calc_{var} = os.path.join(tempfile.gettempdir(), "{table}_calc.shp")',
            f'    arcpy.management.CopyFeatures(fc_{var}, _out_calc_{var})',
            f'    arcpy.management.AddField(_out_calc_{var}, "new_field", "DOUBLE")',
            f'    arcpy.management.CalculateField(',
            f'        _out_calc_{var},',
            f'        "new_field",',
            f'        "!Shape_Area!",  # TODO: change expression',
            f'        "PYTHON3",',
            f'    )',
            f'    print(f"  Field calculated, saved to: {{_out_calc_{var}}}")',
            f'',
        ]

    if "spatial_join" in ops:
        lines += [
            f'    # --- spatial join ---',
            f'    # TODO: set _join_fc_{var} path, then uncomment',
            f'    # _join_fc_{var}   = r"C:\\path\\to\\join_layer.shp"',
            f'    # _out_sjoin_{var} = os.path.join(tempfile.gettempdir(), "{table}_sjoin.shp")',
            f'    # arcpy.analysis.SpatialJoin(',
            f'    #     target_features=fc_{var},',
            f'    #     join_features=_join_fc_{var},',
            f'    #     out_feature_class=_out_sjoin_{var},',
            f'    #     join_operation="JOIN_ONE_TO_ONE",',
            f'    #     join_type="KEEP_ALL",',
            f'    #     match_option="INTERSECT",',
            f'    # )',
            f'    # print(f"  Spatial join saved to: {{_out_sjoin_{var}}}")',
            f'',
        ]

    if "intersect" in ops:
        lines += [
            f'    # --- intersect ---',
            f'    # TODO: set _overlay_fc_{var} path, then uncomment',
            f'    # _overlay_fc_{var} = r"C:\\path\\to\\overlay.shp"',
            f'    # _out_isect_{var}  = os.path.join(tempfile.gettempdir(), "{table}_intersect.shp")',
            f'    # arcpy.analysis.Intersect(',
            f'    #     in_features=[fc_{var}, _overlay_fc_{var}],',
            f'    #     out_feature_class=_out_isect_{var},',
            f'    # )',
            f'    # print(f"  Intersect saved to: {{_out_isect_{var}}}")',
            f'',
        ]

    # ------------------------------------------------------------------
    # 3D massing operations
    # ------------------------------------------------------------------

    if "extrude" in ops:
        lines += [
            f'    # --- 3D extrude (multipatch) ---',
            f'    # Requires 3D Analyst extension.',
            f'    # TODO: set HEIGHT_FIELD to your building height attribute.',
            f'    import arcpy.ddd',
            f'    _HEIGHT_FIELD_{var} = "height"  # TODO: change',
            f'    _out_mp_{var} = os.path.join(tempfile.gettempdir(), "{table}_multipatch.gdb", "{table}_mp")',
            f'    arcpy.management.CreateFileGDB(tempfile.gettempdir(), "{table}_multipatch.gdb")',
            f'    arcpy.ddd.ExtrudePolygon(',
            f'        in_features=fc_{var},',
            f'        out_feature_class=_out_mp_{var},',
            f'        size=_HEIGHT_FIELD_{var},',
            f'    )',
            f'    print(f"  Multipatch saved to: {{_out_mp_{var}}}")',
            f'',
        ]

    if "z_stats" in ops:
        lines += [
            f'    # --- Z statistics ---',
            f'    # Requires 3D Analyst extension. Adds Z fields to a temp copy.',
            f'    import arcpy.ddd',
            f'    _out_z_{var} = os.path.join(tempfile.gettempdir(), "{table}_zstats.shp")',
            f'    arcpy.management.CopyFeatures(fc_{var}, _out_z_{var})',
            f'    arcpy.ddd.AddZInformation(_out_z_{var}, "Z_MIN;Z_MAX;Z_MEAN", "NO_FILTER")',
            f'    with arcpy.da.SearchCursor(_out_z_{var}, ["Z_MIN", "Z_MAX", "Z_MEAN"]) as _cur_z:',
            f'        for _i, _row in enumerate(_cur_z):',
            f'            if _i >= 5: break',
            f'            print(f"  Z_MIN={{_row[0]:.2f}}  Z_MAX={{_row[1]:.2f}}  Z_MEAN={{_row[2]:.2f}}")',
            f'',
        ]

    if "floor_ceiling" in ops:
        lines += [
            f'    # --- floor / ceiling heights ---',
            f'    # Extrudes from a base elevation field to a roof elevation field.',
            f'    # Requires 3D Analyst extension.',
            f'    # TODO: set BASE_FIELD and ROOF_FIELD.',
            f'    import arcpy.ddd',
            f'    _BASE_FIELD_{var} = "base_height"  # TODO: change',
            f'    _ROOF_FIELD_{var} = "roof_height"  # TODO: change',
            f'    _out_fc_{var} = os.path.join(tempfile.gettempdir(), "{table}_massing.gdb", "{table}_mp")',
            f'    arcpy.management.CreateFileGDB(tempfile.gettempdir(), "{table}_massing.gdb")',
            f'    arcpy.ddd.ExtrudePolygon(',
            f'        in_features=fc_{var},',
            f'        out_feature_class=_out_fc_{var},',
            f'        size=_ROOF_FIELD_{var},',
            f'        base_elevation_field=_BASE_FIELD_{var},',
            f'    )',
            f'    print(f"  Massing saved to: {{_out_fc_{var}}}")',
            f'',
        ]

    if "volume" in ops:
        lines += [
            f'    # --- approximate volume (footprint area × height) ---',
            f'    # For exact multipatch volume use arcpy.ddd.SurfaceVolume().',
            f'    # TODO: set HEIGHT_FIELD.',
            f'    _VOL_HEIGHT_{var} = "height"  # TODO: change',
            f'    _total_vol_{var} = 0.0',
            f'    with arcpy.da.SearchCursor(',
            f'        fc_{var}, [_VOL_HEIGHT_{var}, "SHAPE@AREA"]',
            f'    ) as _cur_vol:',
            f'        for _row in _cur_vol:',
            f'            if _row[0] and _row[1]:',
            f'                _total_vol_{var} += _row[0] * _row[1]',
            f'    print(f"  Approx. total volume: {{_total_vol_{var}:,.1f}} (CRS units³)")',
            f'    # For multipatch volume: arcpy.ddd.SurfaceVolume(multipatch_fc, ...)',
            f'',
        ]

    if "scene_layer" in ops:
        lines += [
            f'    # --- export to Scene Layer Package (.slpk) ---',
            f'    # TODO: set output path.',
            f'    _out_slpk_{var} = os.path.join(tempfile.gettempdir(), "{table}.slpk")',
            f'    arcpy.management.CreateSceneLayerPackage(',
            f'        in_dataset=fc_{var},',
            f'        output_slpk=_out_slpk_{var},',
            f'    )',
            f'    print(f"  Scene Layer Package: {{_out_slpk_{var}}}")',
            f'',
        ]

    return lines


# ---------------------------------------------------------------------------
# PyQGIS generator
# ---------------------------------------------------------------------------

def generate_pyqgis(
    schema: dict,
    db_config: dict,
    operations: list[str] | None = None,
    template: "TemplateConfig | None" = None,
    per_layer_ops: dict[str, list[str]] | None = None,
) -> str:
    host     = db_config["host"]
    port     = db_config["port"]
    dbname   = db_config["dbname"]
    user     = db_config["user"]
    password = db_config["password"]

    layers = schema["layers"]
    ops    = set(operations or [])

    # If per_layer_ops provided, compute union of all ops for needs_processing check
    if per_layer_ops:
        all_ops = ops.copy()
        for ops_list in per_layer_ops.values():
            all_ops.update(ops_list)
        needs_processing = all_ops & {
            "reproject", "buffer", "clip",
            "dissolve", "centroid", "field_calc", "spatial_join", "intersect",
            "scene_layer",
        }
    else:
        needs_processing = ops & {
            "reproject", "buffer", "clip",
            "dissolve", "centroid", "field_calc", "spatial_join", "intersect",
            "scene_layer",
        }

    lines = [
        f'"""',
        f'Auto-generated PyQGIS script',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Run as a standalone script (outside QGIS) or paste into the QGIS',
        f'Python console. In the console, omit the QgsApplication init block.',
        f'"""',
        f'',
        f'import os',
        f'import sys',
        f'',
        f'# -- QGIS standalone init (remove if running inside QGIS console) ------',
        f'from qgis.core import (',
        f'    QgsApplication, QgsDataSourceUri, QgsVectorLayer, QgsProject,',
        f'    QgsCoordinateReferenceSystem,',
        f')',
        f'',
        f'qgs = QgsApplication([], False)',
        f'qgs.initQgis()',
        f'# -------------------------------------------------------------------------',
        f'',
        *([f'from qgis import processing', f''] if needs_processing else []),
        f'# Database connection defaults (edit as needed)',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = "{port}"',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ.get("PGPASSWORD", "")  # set PGPASSWORD before running',
        f'',
    ]

    # Inject template preamble if provided
    if template and template.preamble:
        lines.append(template.preamble)
        lines.append(f'')

    # Inject template extra_imports if provided
    if template and template.extra_imports:
        lines.append(template.extra_imports)
        lines.append(f'')

    for layer in layers:
        schema_name = layer["schema"]
        table       = layer["table"]
        qualified_name = layer.get("qualified_name", f"{schema_name}.{table}")
        geom        = layer["geometry"]
        columns     = layer["columns"]
        pks         = layer["primary_keys"]
        var         = safe_var(table)
        pk_col      = pks[0] if pks else ""
        row_est     = layer.get("row_count_estimate", -1)

        # Determine effective operations for this layer
        layer_ops = per_layer_ops.get(qualified_name) if per_layer_ops else None
        effective_ops = set(layer_ops) if layer_ops else ops

        # Template settings
        include_sample_rows = template.include_sample_rows if template else True
        include_crs_info = template.include_crs_info if template else True
        include_field_list = template.include_field_list if template else True

        field_comments = ", ".join(
            f'{c["name"]} ({pg_type_to_pyqgis(c["data_type"])})'
            for c in columns
        )

        # Cursor field list: primary key + all non-geom columns (first 10 for example)
        sample_fields = [c["name"] for c in columns[:10]]

        # Inject per_layer_prefix if template provided
        if template and template.per_layer_prefix:
            prefix = template.substitute_placeholders(
                template.per_layer_prefix, table, schema_name, qualified_name
            )
            lines.append(prefix)
            lines.append(f'')

        lines += [
            f'# {"=" * 66}',
            f'# Layer : {schema_name}.{table}',
            f'# Geom  : {geom["type"]}  |  SRID: {geom["srid"]}',
            f'# Rows  : ~{row_est:,}' if row_est >= 0 else f'# Rows  : unknown',
            f'# Fields: {field_comments or "(none)"}',
            f'# {"=" * 66}',
            f'',
            f'uri_{var} = QgsDataSourceUri()',
            f'uri_{var}.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)',
            f'uri_{var}.setDataSource(',
            f'    "{schema_name}",',
            f'    "{table}",',
            f'    "{geom["column"]}",  # geometry column',
            f'    "",               # optional SQL WHERE filter',
            f'    "{pk_col}",       # primary key column',
            f')',
            f'',
            f'lyr_{var} = QgsVectorLayer(uri_{var}.uri(False), "{table}", "postgres")',
            f'',
            f'if not lyr_{var}.isValid():',
            f'    print(f"[ERROR] Layer \'{table}\' failed to load — check connection.")',
            f'else:',
            f'    QgsProject.instance().addMapLayer(lyr_{var})',
            f'    print(f"[OK] {table}: {{lyr_{var}.featureCount()}} features")',
            f'',
        ]

        # Conditionally include CRS info
        if include_crs_info:
            lines += [
                f'    # CRS',
                f'    crs = lyr_{var}.crs()',
                f'    print(f"  CRS: {{crs.authid()}}  ({{crs.description()}})")',
                f'',
            ]

        # Conditionally include field list
        if include_field_list:
            lines += [
                f'    # Field names',
                f'    fields = [f.name() for f in lyr_{var}.fields()]',
                f'    print(f"  Fields: {{fields}}")',
                f'',
            ]

        # Conditionally include sample rows
        if include_sample_rows and sample_fields:
            quoted = ", ".join(f'"{f}"' for f in sample_fields)
            lines += [
                f'    # --- Sample: iterate first 5 features ---',
                f'    for i, feat in enumerate(lyr_{var}.getFeatures()):',
                f'        if i >= 5:',
                f'            break',
                f'        print("  row:", {{k: feat[k] for k in [{quoted}]}})',
                f'',
            ]

        lines.extend(_pyqgis_op_blocks(var, table, columns, effective_ops))

        # Inject per_layer_suffix if template provided
        if template and template.per_layer_suffix:
            suffix = template.substitute_placeholders(
                template.per_layer_suffix, table, schema_name, qualified_name
            )
            lines.append(suffix)
            lines.append(f'')

        lines += [
            f'    # --- Example: spatial filter (bounding box) ---',
            f'    # from qgis.core import QgsRectangle',
            f'    # bbox = QgsRectangle(xmin, ymin, xmax, ymax)',
            f'    # request = QgsFeatureRequest().setFilterRect(bbox)',
            f'    # for feat in lyr_{var}.getFeatures(request):',
            f'    #     print(feat.id())',
            f'',
            f'    # --- Example: attribute filter ---',
            f'    # request = QgsFeatureRequest().setFilterExpression(\'"field" = \'value\'\')',
            f'    # for feat in lyr_{var}.getFeatures(request):',
            f'    #     print(feat.id())',
            f'',
        ]

    # Inject template teardown if provided
    if template and template.teardown:
        lines.append(template.teardown)
        lines.append(f'')

    lines += [
        f'# -- Cleanup (standalone only) ----------------------------------------',
        f'qgs.exitQgis()',
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ArcPy generator
# ---------------------------------------------------------------------------

def generate_arcpy(
    schema: dict,
    db_config: dict,
    operations: list[str] | None = None,
    template: "TemplateConfig | None" = None,
    per_layer_ops: dict[str, list[str]] | None = None,
) -> str:
    host     = db_config["host"]
    port     = db_config["port"]
    dbname   = db_config["dbname"]
    user     = db_config["user"]
    password = db_config["password"]

    layers = schema["layers"]
    ops    = set(operations or [])

    lines = [
        f'"""',
        f'Auto-generated ArcPy script',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Requires ArcGIS Pro with the PostgreSQL client libraries installed.',
        f'Run from an ArcGIS Pro Python environment or ArcGIS Pro console.',
        f'"""',
        f'',
        f'import arcpy',
        f'import os',
        f'import tempfile',
        f'',
        f'# Database connection parameters',
        f'DB_HOST     = "{host}"',
        f'DB_INSTANCE = "{host},{port}"  # ArcGIS uses "host,port" format',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ.get("PGPASSWORD", "")  # set PGPASSWORD before running',
        f'',
        f'# Create a temporary .sde connection file',
        f'SDE_FOLDER = tempfile.gettempdir()',
        f'SDE_FILE   = os.path.join(SDE_FOLDER, f"{{DB_NAME}}.sde")',
        f'',
        f'if not os.path.exists(SDE_FILE):',
        f'    arcpy.management.CreateDatabaseConnection(',
        f'        out_folder_path=SDE_FOLDER,',
        f'        out_name=os.path.basename(SDE_FILE),',
        f'        database_platform="POSTGRESQL",',
        f'        instance=DB_INSTANCE,',
        f'        account_authentication="DATABASE_AUTH",',
        f'        username=DB_USER,',
        f'        password=DB_PASSWORD,',
        f'        save_user_pass="SAVE_USERNAME",',
        f'        database=DB_NAME,',
        f'    )',
        f'    print(f"[OK] SDE connection created: {{SDE_FILE}}")',
        f'else:',
        f'    print(f"[OK] Reusing SDE connection: {{SDE_FILE}}")',
        f'',
    ]

    # Inject template preamble if provided
    if template and template.preamble:
        lines.append(template.preamble)
        lines.append(f'')

    # Inject template extra_imports if provided
    if template and template.extra_imports:
        lines.append(template.extra_imports)
        lines.append(f'')

    for layer in layers:
        schema_name = layer["schema"]
        table       = layer["table"]
        qualified_name = layer.get("qualified_name", f"{schema_name}.{table}")
        geom        = layer["geometry"]
        columns     = layer["columns"]
        pks         = layer["primary_keys"]
        var         = safe_var(table)
        row_est     = layer.get("row_count_estimate", -1)

        # Determine effective operations for this layer
        layer_ops = per_layer_ops.get(qualified_name) if per_layer_ops else None
        effective_ops = set(layer_ops) if layer_ops else ops

        # Template settings
        include_sample_rows = template.include_sample_rows if template else True
        include_crs_info = template.include_crs_info if template else True
        include_field_list = template.include_field_list if template else True

        field_comments = ", ".join(
            f'{c["name"]} ({pg_type_to_arcpy(c["data_type"])})'
            for c in columns
        )

        # Fields for SearchCursor sample (pk + first few attrs + SHAPE@)
        cursor_fields = pks[:1] + [c["name"] for c in columns[:4]] + ["SHAPE@"]
        cursor_fields_str = str(cursor_fields)

        # Inject per_layer_prefix if template provided
        if template and template.per_layer_prefix:
            prefix = template.substitute_placeholders(
                template.per_layer_prefix, table, schema_name, qualified_name
            )
            lines.append(prefix)
            lines.append(f'')

        lines += [
            f'# {"=" * 66}',
            f'# Layer : {schema_name}.{table}',
            f'# Geom  : {geom["type"]}  |  SRID: {geom["srid"]}',
            f'# Rows  : ~{row_est:,}' if row_est >= 0 else f'# Rows  : unknown',
            f'# Fields: {field_comments or "(none)"}',
            f'# {"=" * 66}',
            f'',
            f'fc_{var} = os.path.join(SDE_FILE, "{schema_name}.{table}")',
            f'',
            f'if arcpy.Exists(fc_{var}):',
            f'    desc_{var} = arcpy.Describe(fc_{var})',
            f'    print(f"[OK] {table}")',
        ]

        # Conditionally include geometry and CRS info
        if include_crs_info:
            lines += [
                f'    print(f"  Geometry : {{desc_{var}.shapeType}}")',
                f'    print(f"  CRS      : {{desc_{var}.spatialReference.name}}")',
                f'',
            ]

        # Conditionally include field list
        if include_field_list:
            lines += [
                f'    # List fields',
                f'    fields_{var} = arcpy.ListFields(fc_{var})',
                f'    for fld in fields_{var}:',
                f'        print(f"  field: {{fld.name}} ({{fld.type}})")',
                f'',
            ]

        # Row count is included regardless (it's part of basic layer info)
        lines += [
            f'    # Row count',
            f'    count_{var} = int(arcpy.management.GetCount(fc_{var})[0])',
            f'    print(f"  Rows: {{count_{var}}}")',
            f'',
        ]

        # Conditionally include sample rows
        if include_sample_rows and cursor_fields:
            lines += [
                f'    # --- Sample: iterate first 5 rows ---',
                f'    with arcpy.da.SearchCursor(fc_{var}, {cursor_fields_str}) as cur_{var}:',
                f'        for i, row in enumerate(cur_{var}):',
                f'            if i >= 5:',
                f'                break',
                f'            print("  row:", row)',
                f'',
            ]

        lines.extend(_arcpy_op_blocks(var, table, columns, effective_ops))

        # Inject per_layer_suffix if template provided
        if template and template.per_layer_suffix:
            suffix = template.substitute_placeholders(
                template.per_layer_suffix, table, schema_name, qualified_name
            )
            lines.append(suffix)
            lines.append(f'')

        lines += [
            f'    # --- Example: SQL WHERE filter ---',
            f'    # with arcpy.da.SearchCursor(fc_{var}, ["*"], where_clause="field = \'value\'") as cur:',
            f'    #     for row in cur:',
            f'    #         print(row)',
            f'',
            f'else:',
            f'    print(f"[ERROR] Layer \'{schema_name}.{table}\' not found in SDE connection.")',
            f'',
        ]

    # Inject template teardown if provided
    if template and template.teardown:
        lines.append(template.teardown)
        lines.append(f'')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Web mapping helpers
# ---------------------------------------------------------------------------

# Cycling palette used to assign distinct colours to layers
_WEB_COLORS = [
    ("#ff8c00", [255, 140,   0, 160]),   # orange
    ("#0080ff", [  0, 128, 255, 160]),   # blue
    ("#00c864", [  0, 200, 100, 160]),   # green
    ("#ff3232", [255,  50,  50, 160]),   # red
    ("#b400ff", [180,   0, 255, 160]),   # purple
    ("#00c8c8", [  0, 200, 200, 160]),   # teal
]

_HEIGHT_HINTS = {
    "height", "bldg_height", "building_height", "h", "elev", "elevation",
    "floors", "num_floors", "stories", "z", "roof_height", "max_height",
}


def _guess_height_field(columns: list[dict]) -> str | None:
    for col in columns:
        if col["name"].lower() in _HEIGHT_HINTS:
            return col["name"]
    return None


def _db_url_line(host: str, port: int, dbname: str, user: str, password: str) -> str:
    return (
        f'DB_URL = ('
        f'f"postgresql://{{DB_USER}}:{{quote_plus(DB_PASSWORD)}}'
        f'@{{DB_HOST}}:{{DB_PORT}}/{{DB_NAME}}"'
        f')'
    )


# ---------------------------------------------------------------------------
# Web mapping generators
# ---------------------------------------------------------------------------

def generate_folium(schema: dict, db_config: dict) -> str:
    host, port = db_config["host"], db_config["port"]
    dbname, user, password = db_config["dbname"], db_config["user"], db_config["password"]
    layers = schema["layers"]

    lines = [
        f'"""',
        f'Auto-generated Folium (Leaflet) web map',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Install:  pip install geopandas folium sqlalchemy psycopg2-binary',
        f'Run:      python <this_file>.py  →  opens map.html',
        f'"""',
        f'',
        f'import os',
        f'from urllib.parse import quote_plus',
        f'import geopandas as gpd',
        f'import folium',
        f'from sqlalchemy import create_engine',
        f'',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = {port}',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ["PGPASSWORD"]',
        f'OUTPUT_HTML = "map.html"',
        f'',
        f'engine = create_engine(',
        f'    f"postgresql://{{DB_USER}}:{{quote_plus(DB_PASSWORD)}}'
        f'@{{DB_HOST}}:{{DB_PORT}}/{{DB_NAME}}"',
        f')',
        f'',
    ]

    # Load all layers
    for layer in layers:
        var   = safe_var(layer["table"])
        geom  = layer["geometry"]
        table = layer["table"]
        schema_name = layer["schema"]
        tooltip_fields = [c["name"] for c in layer["columns"][:5]]

        lines += [
            f'# {"=" * 66}',
            f'# Layer: {schema_name}.{table}  ({geom["type"]}, SRID {geom["srid"]})',
            f'# {"=" * 66}',
            f'gdf_{var} = gpd.read_postgis(',
            f'    \'SELECT * FROM "{schema_name}"."{table}"\',',
            f'    engine,',
            f'    geom_col="{geom["column"]}",',
            f')',
            f'gdf_{var} = gdf_{var}.to_crs(epsg=4326)',
            f'print(f"[OK] {table}: {{len(gdf_{var})}} features")',
            f'',
        ]

    # Map centre from first layer
    first_var = safe_var(layers[0]["table"]) if layers else "layer"
    lines += [
        f'# --- Build map ---',
        f'_b = gdf_{first_var}.total_bounds  # [minx, miny, maxx, maxy]',
        f'_cx, _cy = (_b[0] + _b[2]) / 2, (_b[1] + _b[3]) / 2',
        f'',
        f'm = folium.Map(location=[_cy, _cx], zoom_start=12, tiles="CartoDB positron")',
        f'',
    ]

    # Add each layer to map
    for i, layer in enumerate(layers):
        var   = safe_var(layer["table"])
        table = layer["table"]
        geom_type = layer["geometry"]["type"].upper()
        hex_color, _ = _WEB_COLORS[i % len(_WEB_COLORS)]
        tooltip_fields = [c["name"] for c in layer["columns"][:5]]
        tooltip_aliases = [c["name"].replace("_", " ").title() for c in layer["columns"][:5]]

        # Style differs by geometry family
        is_line = any(t in geom_type for t in ("LINE", "LINESTRING"))
        is_point = any(t in geom_type for t in ("POINT",))

        if is_line:
            style = (f'{{"color": "{hex_color}", "weight": 2, "fillOpacity": 0.0}}')
        elif is_point:
            style = (f'{{"color": "{hex_color}", "fillColor": "{hex_color}", '
                     f'"radius": 5, "fillOpacity": 0.7}}')
        else:
            style = (f'{{"fillColor": "{hex_color}", "color": "#333333", '
                     f'"weight": 1, "fillOpacity": 0.5}}')

        tooltip_block = ""
        if tooltip_fields:
            fields_str   = str(tooltip_fields)
            aliases_str  = str(tooltip_aliases)
            tooltip_block = (
                f'    tooltip=folium.GeoJsonTooltip(\n'
                f'        fields={fields_str},\n'
                f'        aliases={aliases_str},\n'
                f'        sticky=True,\n'
                f'    ),'
            )

        lines += [
            f'folium.GeoJson(',
            f'    gdf_{var}.__geo_interface__,',
            f'    name="{table}",',
            f'    style_function=lambda _: {style},',
        ]
        if tooltip_fields:
            lines += [
                f'    tooltip=folium.GeoJsonTooltip(',
                f'        fields={str(tooltip_fields)},',
                f'        aliases={str(tooltip_aliases)},',
                f'        sticky=True,',
                f'    ),',
            ]
        lines += [
            f').add_to(m)',
            f'',
        ]

    lines += [
        f'folium.LayerControl(collapsed=False).add_to(m)',
        f'm.save(OUTPUT_HTML)',
        f'print(f"[OK] Map saved to {{OUTPUT_HTML}}")',
    ]

    return "\n".join(lines)


def generate_kepler(schema: dict, db_config: dict) -> str:
    host, port = db_config["host"], db_config["port"]
    dbname, user, password = db_config["dbname"], db_config["user"], db_config["password"]
    layers = schema["layers"]

    lines = [
        f'"""',
        f'Auto-generated Kepler.gl web map',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Install:  pip install geopandas keplergl sqlalchemy psycopg2-binary',
        f'Run:      python <this_file>.py  →  opens kepler_map.html',
        f'         (or call map_k in a Jupyter cell to render inline)',
        f'"""',
        f'',
        f'import os',
        f'from urllib.parse import quote_plus',
        f'import geopandas as gpd',
        f'from keplergl import KeplerGl',
        f'from sqlalchemy import create_engine',
        f'',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = {port}',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ["PGPASSWORD"]',
        f'OUTPUT_HTML = "kepler_map.html"',
        f'',
        f'engine = create_engine(',
        f'    f"postgresql://{{DB_USER}}:{{quote_plus(DB_PASSWORD)}}'
        f'@{{DB_HOST}}:{{DB_PORT}}/{{DB_NAME}}"',
        f')',
        f'',
        f'map_k = KeplerGl(height=600)',
        f'',
    ]

    for layer in layers:
        var         = safe_var(layer["table"])
        table       = layer["table"]
        schema_name = layer["schema"]
        geom        = layer["geometry"]
        height_col  = _guess_height_field(layer["columns"])

        lines += [
            f'# {"=" * 66}',
            f'# Layer: {schema_name}.{table}  ({geom["type"]}, SRID {geom["srid"]})',
        ]
        if height_col:
            lines.append(f'# 3D height field detected: "{height_col}"')
        lines += [
            f'# {"=" * 66}',
            f'gdf_{var} = gpd.read_postgis(',
            f'    \'SELECT * FROM "{schema_name}"."{table}"\',',
            f'    engine,',
            f'    geom_col="{geom["column"]}",',
            f')',
            f'print(f"[OK] {table}: {{len(gdf_{var})}} features")',
            f'map_k.add_data(data=gdf_{var}, name="{table}")',
        ]
        if height_col:
            lines += [
                f'# 3D tip: in the Kepler UI → Layers → {table}',
                f'#   set type to "GeoJson", enable "3D buildings", height field = "{height_col}"',
            ]
        lines.append(f'')

    lines += [
        f'map_k.save_to_html(file_name=OUTPUT_HTML)',
        f'print(f"[OK] Kepler map saved to {{OUTPUT_HTML}}")',
    ]

    return "\n".join(lines)


def generate_deck(schema: dict, db_config: dict) -> str:
    host, port = db_config["host"], db_config["port"]
    dbname, user, password = db_config["dbname"], db_config["user"], db_config["password"]
    layers = schema["layers"]

    lines = [
        f'"""',
        f'Auto-generated pydeck (deck.gl) web map',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Install:  pip install geopandas pydeck sqlalchemy psycopg2-binary',
        f'Run:      python <this_file>.py  →  opens deck_map.html',
        f'"""',
        f'',
        f'import os',
        f'import json',
        f'from urllib.parse import quote_plus',
        f'import geopandas as gpd',
        f'import pydeck as pdk',
        f'from sqlalchemy import create_engine',
        f'',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = {port}',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ["PGPASSWORD"]',
        f'OUTPUT_HTML = "deck_map.html"',
        f'',
        f'engine = create_engine(',
        f'    f"postgresql://{{DB_USER}}:{{quote_plus(DB_PASSWORD)}}'
        f'@{{DB_HOST}}:{{DB_PORT}}/{{DB_NAME}}"',
        f')',
        f'',
        f'_deck_layers = []',
        f'',
    ]

    first_var = safe_var(layers[0]["table"]) if layers else "layer"

    for i, layer in enumerate(layers):
        var         = safe_var(layer["table"])
        table       = layer["table"]
        schema_name = layer["schema"]
        geom        = layer["geometry"]
        height_col  = _guess_height_field(layer["columns"])
        _, rgba     = _WEB_COLORS[i % len(_WEB_COLORS)]
        geom_type   = geom["type"].upper()
        is_point    = "POINT" in geom_type

        lines += [
            f'# {"=" * 66}',
            f'# Layer: {schema_name}.{table}  ({geom["type"]}, SRID {geom["srid"]})',
        ]
        if height_col:
            lines.append(f'# 3D height field detected: "{height_col}"')
        lines += [
            f'# {"=" * 66}',
            f'gdf_{var} = gpd.read_postgis(',
            f'    \'SELECT * FROM "{schema_name}"."{table}"\',',
            f'    engine,',
            f'    geom_col="{geom["column"]}",',
            f')',
            f'gdf_{var} = gdf_{var}.to_crs(epsg=4326)',
            f'print(f"[OK] {table}: {{len(gdf_{var})}} features")',
            f'',
        ]

        if is_point:
            # ScatterplotLayer for points
            lines += [
                f'_lyr_{var} = pdk.Layer(',
                f'    "ScatterplotLayer",',
                f'    data=json.loads(gdf_{var}.to_json())["features"],',
                f'    get_position="geometry.coordinates",',
                f'    get_fill_color={rgba},',
                f'    get_radius=50,',
                f'    radius_min_pixels=3,',
                f'    pickable=True,',
                f')',
            ]
        else:
            # GeoJsonLayer for polygons/lines, with optional 3D extrusion
            lines += [
                f'_lyr_{var} = pdk.Layer(',
                f'    "GeoJsonLayer",',
                f'    data=json.loads(gdf_{var}.to_json()),',
                f'    get_fill_color={rgba},',
                f'    get_line_color=[50, 50, 50, 200],',
                f'    line_width_min_pixels=1,',
                f'    pickable=True,',
            ]
            if height_col:
                lines += [
                    f'    # 3D extrusion — uncomment to enable:',
                    f'    # extruded=True,',
                    f'    # get_elevation="properties.{height_col}",',
                    f'    # elevation_scale=1,',
                ]
            lines.append(f')')

        lines += [
            f'_deck_layers.append(_lyr_{var})',
            f'',
        ]

    lines += [
        f'_b   = gdf_{first_var}.total_bounds',
        f'_cx, _cy = (_b[0] + _b[2]) / 2, (_b[1] + _b[3]) / 2',
        f'',
        f'_view = pdk.ViewState(',
        f'    latitude=_cy,',
        f'    longitude=_cx,',
        f'    zoom=12,',
        f'    pitch=0,  # Set to 45 for 3D view when using extrusion',
        f')',
        f'',
        f'r = pdk.Deck(',
        f'    layers=_deck_layers,',
        f'    initial_view_state=_view,',
        f'    map_style="light",',
        f')',
        f'r.to_html(OUTPUT_HTML)',
        f'print(f"[OK] pydeck map saved to {{OUTPUT_HTML}}")',
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GeoPackage export template
# ---------------------------------------------------------------------------

def generate_export(schema: dict, db_config: dict) -> str:
    """
    Generate a script that exports every spatial layer from PostGIS
    to a single GeoPackage file using geopandas.

    Requires:  pip install -e ".[web]"   (geopandas + sqlalchemy)
    """
    layers = schema.get("layers", [])
    db     = schema.get("database", db_config.get("dbname", "my_gis_db"))
    host   = db_config["host"]
    port   = db_config["port"]
    dbname = db_config["dbname"]
    user   = db_config["user"]
    n      = len(layers)

    lines = [
        f'"""',
        f'Auto-generated PostGIS -> GeoPackage export script',
        f'',
        f'Database : {db} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {n}',
        f'',
        f'Install:  pip install geopandas sqlalchemy psycopg2-binary',
        f'Run:      python <this_file>.py  ->  {dbname}_export.gpkg',
        f'"""',
        f'',
        f'import os',
        f'import sys',
        f'from urllib.parse import quote_plus',
        f'import geopandas as gpd',
        f'from sqlalchemy import create_engine',
        f'',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = {port}',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ["PGPASSWORD"]',
        f'OUTPUT_GPKG = f"{{DB_NAME}}_export.gpkg"',
        f'',
        f'engine = create_engine(',
        f'    f"postgresql://{{DB_USER}}:{{quote_plus(DB_PASSWORD)}}'
        f'@{{DB_HOST}}:{{DB_PORT}}/{{DB_NAME}}"',
        f')',
        f'',
        f'print(f"[export] Writing {{OUTPUT_GPKG}} ({n} layer(s))")',
        f'_ok = 0',
        f'',
    ]

    for i, layer in enumerate(layers):
        var         = safe_var(layer["table"])
        table       = layer["table"]
        schema_name = layer["schema"]
        geom        = layer["geometry"]
        row_est     = layer.get("row_count_estimate", -1)
        rows_hint   = f"~{row_est:,} rows" if row_est >= 0 else "row count unknown"
        # First layer creates the file; subsequent layers append
        write_mode  = '"w"' if i == 0 else '"a"'

        lines += [
            f'# {"=" * 66}',
            f'# [{i + 1}/{n}] {schema_name}.{table}',
            f'#     Geometry : {geom["type"]}   SRID: {geom["srid"]}   {rows_hint}',
            f'# {"=" * 66}',
            f'print(f"[{i + 1}/{n}] {table} ...", end=" ", flush=True)',
            f'try:',
            f'    gdf_{var} = gpd.read_postgis(',
            f'        \'SELECT * FROM "{schema_name}"."{table}"\',',
            f'        engine,',
            f'        geom_col="{geom["column"]}",',
            f'    )',
            f'    # CRS is preserved from PostGIS (SRID {geom["srid"]}).',
            f'    # To reproject: gdf_{var} = gdf_{var}.to_crs(epsg=4326)',
            f'    gdf_{var}.to_file(OUTPUT_GPKG, layer="{table}", driver="GPKG", mode={write_mode})',
            f'    print(f"OK  ({{len(gdf_{var})}} rows)")',
            f'    _ok += 1',
            f'except Exception as _e:',
            f'    print(f"FAILED  ({{_e}})", file=sys.stderr)',
            f'',
        ]

    lines += [
        f'engine.dispose()',
        f'print(f"\\n[DONE] {{_ok}}/{n} layers written to {{OUTPUT_GPKG}}")',
        f'if _ok < {n}:',
        f'    sys.exit(1)',
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# QGIS Project file (.qgs)
# ---------------------------------------------------------------------------

def _qgs_geom_type(geom_type: str) -> tuple[str, int]:
    """Map a PostGIS geometry type to a QGIS geometry name and layerGeometryType code."""
    gt = geom_type.upper()
    if "POINT" in gt:
        return "Point", 0
    if "LINE" in gt:
        return "Line", 1
    return "Polygon", 2


def generate_qgs(schema: dict, db_config: dict) -> str:
    """
    Generate a QGIS project file (.qgs XML) with all PostGIS layers pre-connected.

    Returns XML string — write to a .qgs file and open directly in QGIS.
    Password is NOT embedded; QGIS prompts on open.
    """
    layers = schema.get("layers", [])
    host   = db_config["host"]
    port   = db_config["port"]
    dbname = db_config["dbname"]
    user   = db_config["user"]

    layer_elements = []
    legend_layers  = []

    for layer in layers:
        table       = layer["table"]
        schema_name = layer["schema"]
        qualified   = layer["qualified_name"]
        geom        = layer["geometry"]
        geom_col    = geom["column"]
        geom_type   = geom["type"]
        srid        = geom["srid"]
        pks         = layer.get("primary_keys", [])
        pk          = pks[0] if pks else "id"

        qgs_geom_name, qgs_geom_code = _qgs_geom_type(geom_type)
        layer_id = f"{table}_{hashlib.md5(qualified.encode()).hexdigest()[:8]}"

        datasource = (
            f"dbname='{dbname}' host={host} port={port} sslmode=disable "
            f"key='{pk}' srid={srid} type={qgs_geom_name} "
            f'table="{schema_name}"."{table}" ({geom_col}) sql='
        )

        layer_elements.append(
            f'    <maplayer type="vector" geometry="{qgs_geom_name}" autoRefreshEnabled="0">\n'
            f'      <id>{layer_id}</id>\n'
            f'      <datasource>{datasource}</datasource>\n'
            f'      <layername>{table}</layername>\n'
            f'      <provider encoding="UTF-8">postgres</provider>\n'
            f'      <srs>\n'
            f'        <spatialrefsys>\n'
            f'          <authid>EPSG:{srid}</authid>\n'
            f'        </spatialrefsys>\n'
            f'      </srs>\n'
            f'      <layerGeometryType>{qgs_geom_code}</layerGeometryType>\n'
            f'    </maplayer>'
        )

        legend_layers.append(
            f'      <legendlayer name="{table}" showFeatureCount="0" '
            f'checked="Qt::Checked" open="true" drawingOrder="-1">\n'
            f'        <filegroup open="true" hidden="false">\n'
            f'          <legendlayerfile isInOverview="0" visible="1" layerid="{layer_id}"/>\n'
            f'        </filegroup>\n'
            f'      </legendlayer>'
        )

    layer_elements_str = "\n".join(layer_elements)
    legend_layers_str  = "\n".join(legend_layers)

    return (
        '<!DOCTYPE qgis PUBLIC \'http://mrcc.com/qgis.dtd\' \'SYSTEM\'>\n'
        f'<qgis projectname="{dbname}" version="3.28.0-Firenze">\n'
        '  <projectCrs>\n'
        '    <spatialrefsys>\n'
        '      <authid>EPSG:4326</authid>\n'
        '    </spatialrefsys>\n'
        '  </projectCrs>\n'
        '  <mapcanvas annotationsVisible="1" name="theMapCanvas">\n'
        '    <units>degrees</units>\n'
        '    <extent>\n'
        '      <xmin>-180</xmin>\n'
        '      <ymin>-90</ymin>\n'
        '      <xmax>180</xmax>\n'
        '      <ymax>90</ymax>\n'
        '    </extent>\n'
        '    <rotation>0</rotation>\n'
        '    <destinationsrs>\n'
        '      <spatialrefsys>\n'
        '        <authid>EPSG:4326</authid>\n'
        '      </spatialrefsys>\n'
        '    </destinationsrs>\n'
        '    <rendermaptile>0</rendermaptile>\n'
        '  </mapcanvas>\n'
        '  <projectlayers>\n'
        f'{layer_elements_str}\n'
        '  </projectlayers>\n'
        '  <legend updateDrawingOrder="true">\n'
        f'{legend_layers_str}\n'
        '  </legend>\n'
        '</qgis>'
    )


# ---------------------------------------------------------------------------
# ArcGIS Python Toolbox (.pyt)
# ---------------------------------------------------------------------------

def generate_pyt(schema: dict, db_config: dict) -> str:
    """
    Generate an ArcGIS Python Toolbox (.pyt) file.

    Returns Python source — save as <name>.pyt and open in ArcGIS Pro via
    Insert > Toolbox > Add Python Toolbox.
    Password is NOT hardcoded; the tool dialog prompts for it.
    """
    layers = schema.get("layers", [])
    host   = db_config["host"]
    port   = db_config["port"]
    dbname = db_config["dbname"]
    user   = db_config["user"]
    n      = len(layers)

    lines = [
        '# -*- coding: utf-8 -*-',
        '"""',
        'Auto-generated ArcGIS Python Toolbox (.pyt)',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {n}',
        '',
        'Open in ArcGIS Pro via Insert > Toolbox > Add Python Toolbox',
        '"""',
        '',
        'import os',
        'import arcpy',
        '',
        '',
        'class Toolbox:',
        '    """PostGIS Layer Loader toolbox."""',
        '',
        '    def __init__(self):',
        '        self.label = "PostGIS Loader"',
        '        self.alias = "postgis_loader"',
        '        self.tools = [LoadPostGISLayers]',
        '',
        '',
        'class LoadPostGISLayers:',
        '    """Load all PostGIS layers into the current ArcGIS Pro map."""',
        '',
        '    def __init__(self):',
        '        self.label = "Load PostGIS Layers"',
        '        self.description = (',
        '            "Connect to a PostGIS database and add all spatial layers "',
        '            "to the active map."',
        '        )',
        '',
        '    def getParameterInfo(self):',
        '        host = arcpy.Parameter(',
        '            displayName="Host",',
        '            name="host",',
        '            datatype="GPString",',
        '            parameterType="Required",',
        '            direction="Input",',
        '        )',
        f'        host.value = "{host}"',
        '',
        '        port = arcpy.Parameter(',
        '            displayName="Port",',
        '            name="port",',
        '            datatype="GPString",',
        '            parameterType="Required",',
        '            direction="Input",',
        '        )',
        f'        port.value = "{port}"',
        '',
        '        dbname = arcpy.Parameter(',
        '            displayName="Database",',
        '            name="dbname",',
        '            datatype="GPString",',
        '            parameterType="Required",',
        '            direction="Input",',
        '        )',
        f'        dbname.value = "{dbname}"',
        '',
        '        user = arcpy.Parameter(',
        '            displayName="User",',
        '            name="user",',
        '            datatype="GPString",',
        '            parameterType="Required",',
        '            direction="Input",',
        '        )',
        f'        user.value = "{user}"',
        '',
        '        password = arcpy.Parameter(',
        '            displayName="Password",',
        '            name="password",',
        '            datatype="GPStringHidden",',
        '            parameterType="Required",',
        '            direction="Input",',
        '        )',
        '',
        '        schema_filter = arcpy.Parameter(',
        '            displayName="Schema Filter (optional)",',
        '            name="schema_filter",',
        '            datatype="GPString",',
        '            parameterType="Optional",',
        '            direction="Input",',
        '        )',
        '',
        '        return [host, port, dbname, user, password, schema_filter]',
        '',
        '    def isLicensed(self):',
        '        return True',
        '',
        '    def updateParameters(self, parameters):',
        '        pass',
        '',
        '    def updateMessages(self, parameters):',
        '        pass',
        '',
        '    def execute(self, parameters, messages):',
        '        host          = parameters[0].valueAsText',
        '        port          = parameters[1].valueAsText',
        '        dbname        = parameters[2].valueAsText',
        '        user          = parameters[3].valueAsText',
        '        password      = parameters[4].valueAsText',
        '        schema_filter = parameters[5].valueAsText',
        '',
        '        sde_file = os.path.join(arcpy.env.scratchFolder, "postgis_conn.sde")',
        '',
        '        arcpy.management.CreateDatabaseConnection(',
        '            out_folder_path=arcpy.env.scratchFolder,',
        '            out_name="postgis_conn.sde",',
        '            database_platform="POSTGRESQL",',
        '            instance=host,',
        '            account_authentication="DATABASE_AUTH",',
        '            username=user,',
        '            password=password,',
        '            save_user_pass="SAVE_USERNAME",',
        '            database=dbname,',
        '        )',
        '',
        '        aprx    = arcpy.mp.ArcGISProject("CURRENT")',
        '        act_map = aprx.activeMap',
        '',
        '        _tables = [',
    ]

    for layer in layers:
        lines.append(f'            ("{layer["schema"]}", "{layer["table"]}"),')

    lines += [
        '        ]',
        '        for _schema, _table in _tables:',
        '            if schema_filter and _schema != schema_filter:',
        '                continue',
        r'            _fc = f"{sde_file}\\{dbname}.{_schema}.{_table}"',
        '            act_map.addDataFromPath(_fc)',
        '            messages.addMessage(f"Added: {_schema}.{_table}")',
        '',
        '        messages.addMessage(f"Done. {len(_tables)} layer(s) processed.")',
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_schema(path: str) -> tuple[dict, dict]:
    """Load schema JSON and return (schema_dict, db_config_dict)."""
    with open(path, encoding="utf-8") as f:
        schema = json.load(f)

    # Reconstruct db_config from schema metadata + hardcoded defaults.
    # The extractor writes host/dbname; port/credentials are supplied here.
    db_config = {
        "host":     schema.get("host", "localhost"),
        "port":     5432,
        "dbname":   schema.get("database", "unknown"),
        "user":     "postgres",
        "password": "mypassword",
    }
    return schema, db_config


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a PyQGIS or ArcPy script from a PostGIS schema JSON."
    )
    parser.add_argument(
        "-i", "--input",
        required=True,
        metavar="schema.json",
        help="Schema JSON file produced by schema_extractor.py",
    )
    parser.add_argument(
        "--platform",
        required=True,
        choices=["pyqgis", "arcpy", "folium", "kepler", "deck"],
        help="Target platform",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write generated script to FILE (default: print to stdout)",
    )
    parser.add_argument(
        "--layer",
        metavar="SCHEMA.TABLE",
        action="append",
        dest="layers",
        help="Only generate code for this layer (repeat for multiple). "
             "Example: --layer public.parcels",
    )
    parser.add_argument(
        "--op",
        metavar="OPERATION",
        action="append",
        dest="operations",
        choices=VALID_OPERATIONS,
        help=f"Include an operation block ({', '.join(VALID_OPERATIONS)}). Repeatable.",
    )
    args = parser.parse_args()

    schema, db_config = load_schema(args.input)

    # Apply layer filter
    if args.layers:
        schema["layers"] = [
            l for l in schema["layers"]
            if l["qualified_name"] in args.layers
        ]
        schema["layer_count"] = len(schema["layers"])
        if not schema["layers"]:
            print(f"[ERROR] No layers matched filter: {args.layers}", file=sys.stderr)
            sys.exit(1)

    generators = {
        "pyqgis":  lambda: generate_pyqgis(schema, db_config, args.operations),
        "arcpy":   lambda: generate_arcpy(schema, db_config, args.operations),
        "folium":  lambda: generate_folium(schema, db_config),
        "kepler":  lambda: generate_kepler(schema, db_config),
        "deck":    lambda: generate_deck(schema, db_config),
    }
    code = generators[args.platform]()

    if args.output:
        Path(args.output).write_text(code, encoding="utf-8")
        print(f"[OK] {args.platform} script written to {args.output} "
              f"({schema['layer_count']} layer(s))")
    else:
        print(code)


if __name__ == "__main__":
    main()
