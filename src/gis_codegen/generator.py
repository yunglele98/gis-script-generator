"""
gis_codegen.generator

Generates a PyQGIS (standalone) or ArcPy (ArcGIS Pro) script from a schema
dict produced by gis_codegen.extractor.
"""

import hashlib
import json
import sys
import argparse
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


def _op_blocks(var: str, table: str, columns: list[dict], ops: set[str],
               registry: dict) -> list[str]:
    """Dispatch requested operations through *registry* and return indented lines."""
    lines = []
    first_col = columns[0]["name"] if columns else "field_name"
    for op_name in VALID_OPERATIONS:
        if op_name in ops and op_name in registry:
            lines += registry[op_name](var, table, first_col)
    return lines


# ---------------------------------------------------------------------------
# PyQGIS operation templates
# ---------------------------------------------------------------------------

def _pq_reproject(var, table, _fc):
    return [
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

def _pq_export(var, table, _fc):
    return [
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

def _pq_buffer(var, table, _fc):
    return [
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

def _pq_clip(var, table, _fc):
    return [
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

def _pq_select(var, table, first_col):
    expr = f'"{first_col}" IS NOT NULL'
    return [
        f'    # --- select by attribute ---',
        f'    # TODO: update expression',
        f"    lyr_{var}.selectByExpression('{expr}')",
        f'    print(f"  Selected: {{lyr_{var}.selectedFeatureCount()}} features")',
        f'    lyr_{var}.removeSelection()',
        f'',
    ]

def _pq_dissolve(var, table, _fc):
    return [
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

def _pq_centroid(var, table, _fc):
    return [
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

def _pq_field_calc(var, table, _fc):
    return [
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

def _pq_spatial_join(var, table, _fc):
    return [
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

def _pq_intersect(var, table, _fc):
    return [
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

def _pq_extrude(var, table, _fc):
    return [
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

def _pq_z_stats(var, table, _fc):
    return [
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

def _pq_floor_ceiling(var, table, _fc):
    return [
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

def _pq_volume(var, table, _fc):
    return [
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

def _pq_scene_layer(var, table, _fc):
    return [
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

_PYQGIS_OPS = {
    "reproject": _pq_reproject, "export": _pq_export, "buffer": _pq_buffer,
    "clip": _pq_clip, "select": _pq_select, "dissolve": _pq_dissolve,
    "centroid": _pq_centroid, "field_calc": _pq_field_calc,
    "spatial_join": _pq_spatial_join, "intersect": _pq_intersect,
    "extrude": _pq_extrude, "z_stats": _pq_z_stats,
    "floor_ceiling": _pq_floor_ceiling, "volume": _pq_volume,
    "scene_layer": _pq_scene_layer,
}


# ---------------------------------------------------------------------------
# ArcPy operation templates
# ---------------------------------------------------------------------------

def _ap_reproject(var, table, _fc):
    return [
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

def _ap_export(var, table, _fc):
    return [
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

def _ap_buffer(var, table, _fc):
    return [
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

def _ap_clip(var, table, _fc):
    return [
        f'    # --- clip ---',
        f'    # TODO: set clip boundary path, then uncomment',
        f'    # _clip_fc_{var}  = r"C:\\path\\to\\boundary.shp"',
        f'    # _out_clip_{var} = os.path.join(tempfile.gettempdir(), "{table}_clipped.shp")',
        f'    # arcpy.analysis.Clip(fc_{var}, _clip_fc_{var}, _out_clip_{var})',
        f'    # print(f"  Clipped to: {{_out_clip_{var}}}")',
        f'',
    ]

def _ap_select(var, table, first_col):
    where = f"{first_col} IS NOT NULL"
    return [
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

def _ap_dissolve(var, table, _fc):
    return [
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

def _ap_centroid(var, table, _fc):
    return [
        f'    # --- centroid ---',
        f'    _out_cent_{var} = os.path.join(tempfile.gettempdir(), "{table}_centroids.shp")',
        f'    arcpy.management.FeatureToPoint(',
        f'        fc_{var}, _out_cent_{var}, point_location="CENTROID",',
        f'    )',
        f'    print(f"  Centroids saved to: {{_out_cent_{var}}}")',
        f'',
    ]

def _ap_field_calc(var, table, _fc):
    return [
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

def _ap_spatial_join(var, table, _fc):
    return [
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

def _ap_intersect(var, table, _fc):
    return [
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

def _ap_extrude(var, table, _fc):
    return [
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

def _ap_z_stats(var, table, _fc):
    return [
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

def _ap_floor_ceiling(var, table, _fc):
    return [
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

def _ap_volume(var, table, _fc):
    return [
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

def _ap_scene_layer(var, table, _fc):
    return [
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

_ARCPY_OPS = {
    "reproject": _ap_reproject, "export": _ap_export, "buffer": _ap_buffer,
    "clip": _ap_clip, "select": _ap_select, "dissolve": _ap_dissolve,
    "centroid": _ap_centroid, "field_calc": _ap_field_calc,
    "spatial_join": _ap_spatial_join, "intersect": _ap_intersect,
    "extrude": _ap_extrude, "z_stats": _ap_z_stats,
    "floor_ceiling": _ap_floor_ceiling, "volume": _ap_volume,
    "scene_layer": _ap_scene_layer,
}


def _pyqgis_op_blocks(var: str, table: str, columns: list[dict], ops: set[str]) -> list[str]:
    """Return 4-space-indented lines for each requested PyQGIS operation."""
    return _op_blocks(var, table, columns, ops, _PYQGIS_OPS)


def _arcpy_op_blocks(var: str, table: str, columns: list[dict], ops: set[str]) -> list[str]:
    """Return 4-space-indented lines for each requested ArcPy operation."""
    return _op_blocks(var, table, columns, ops, _ARCPY_OPS)


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

        header_lines = [
            f'# {"=" * 66}',
            f'# Layer : {schema_name}.{table}',
            f'# Geom  : {geom["type"]}  |  SRID: {geom["srid"]}',
            f'# Rows  : ~{row_est:,}' if row_est >= 0 else f'# Rows  : unknown',
            f'# Fields: {field_comments or "(none)"}',
        ]
        if layer.get("description"):
            header_lines.append(f'# Description: {layer["description"]}')
        if layer.get("owner"):
            header_lines.append(f'# Owner: {layer["owner"]}')
        if layer.get("notes"):
            header_lines.append(f'# Notes: {layer["notes"]}')
        header_lines.append(f'# {"=" * 66}')
        header_lines.append(f'')
        lines += header_lines
        lines += [
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

        header_lines = [
            f'# {"=" * 66}',
            f'# Layer : {schema_name}.{table}',
            f'# Geom  : {geom["type"]}  |  SRID: {geom["srid"]}',
            f'# Rows  : ~{row_est:,}' if row_est >= 0 else f'# Rows  : unknown',
            f'# Fields: {field_comments or "(none)"}',
        ]
        if layer.get("description"):
            header_lines.append(f'# Description: {layer["description"]}')
        if layer.get("owner"):
            header_lines.append(f'# Owner: {layer["owner"]}')
        if layer.get("notes"):
            header_lines.append(f'# Notes: {layer["notes"]}')
        header_lines.append(f'# {"=" * 66}')
        header_lines.append(f'')
        lines += header_lines
        lines += [
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
    dbname, user = db_config["dbname"], db_config["user"]
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
    dbname, user = db_config["dbname"], db_config["user"]
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
    dbname, user = db_config["dbname"], db_config["user"]
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

    # Use the first layer's SRID as project CRS (fallback to 4326)
    project_srid = layers[0]["geometry"]["srid"] if layers else 4326

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
        f'      <authid>EPSG:{project_srid}</authid>\n'
        '    </spatialrefsys>\n'
        '  </projectCrs>\n'
        '  <mapcanvas annotationsVisible="1" name="theMapCanvas">\n'
        f'    <units>{"degrees" if project_srid == 4326 else "meters"}</units>\n'
        '    <extent>\n'
        '      <xmin>-180</xmin>\n'
        '      <ymin>-90</ymin>\n'
        '      <xmax>180</xmax>\n'
        '      <ymax>90</ymax>\n'
        '    </extent>\n'
        '    <rotation>0</rotation>\n'
        '    <destinationsrs>\n'
        '      <spatialrefsys>\n'
        f'        <authid>EPSG:{project_srid}</authid>\n'
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
# Blender (bpy) generator
# ---------------------------------------------------------------------------

def generate_blender(schema: dict, db_config: dict) -> str:
    """Generate a Blender Python script that loads PostGIS layers as 3D meshes.

    Polygon layers are extruded into proper 3D buildings with walls and roof
    geometry via bmesh.  When an address-indexed photo directory is available,
    facade photos are applied as textures to matched buildings via spatial join
    to the addresses table.  Unmatched buildings get procedural brick/concrete
    materials.  Point layers become ico-spheres, line layers become curves.
    Coordinates are centred to avoid floating-point issues.
    """
    host, port = db_config["host"], db_config["port"]
    dbname, user = db_config["dbname"], db_config["user"]
    password = db_config.get("password", "")
    layers = schema["layers"]

    # Detect if any layer has height columns (3D massing data)
    height_columns = [
        "MAX_HEIGHT", "max_height", "AVG_HEIGHT", "avg_height",
        "HEIGHT", "height", "BLDG_HT", "bldg_ht",
        "HEIGHT_MSL", "height_msl", "ELEVATION", "elevation",
    ]

    lines = [
        f'"""',
        f'Auto-generated Blender Python (bpy) script — Realistic 3D Buildings',
        f'Database : {dbname} @ {host}:{port}',
        f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Layers   : {len(layers)}',
        f'',
        f'Features:',
        f'  - 3D extruded buildings with walls and roof geometry',
        f'  - Photo facade textures from HCD photos (address-matched)',
        f'  - Procedural brick/concrete for unmatched buildings',
        f'  - Road network as ground curves',
        f'  - Sun lighting and camera setup',
        f'',
        f'Usage:',
        f'  blender --python <this_file>.py          # opens Blender with scene',
        f'  blender --background --python <this_file>.py  # headless',
        f'',
        f'Requires: psycopg2-binary in Blender Python',
        f'"""',
        f'',
        f'import bpy',
        f'import bmesh',
        f'import math',
        f'import os',
        f'import sys',
        f'import csv',
        f'import site',
        f'from mathutils import Vector',
        f'',
        f'# Ensure user site-packages is on path (Blender disables it by default)',
        f'_user_site = site.getusersitepackages()',
        f'if _user_site not in sys.path:',
        f'    sys.path.append(_user_site)',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Configuration',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'DB_HOST     = "{host}"',
        f'DB_PORT     = {port}',
        f'DB_NAME     = "{dbname}"',
        f'DB_USER     = "{user}"',
        f'DB_PASSWORD = os.environ.get("PGPASSWORD", "{password}")',
        f'',
        f'# Photo directory (HCD heritage photos indexed by address)',
        f'PHOTO_DIR   = r"F:\\06_Images & Graphics\\hcd_photos"',
        f'PHOTO_INDEX = os.path.join(PHOTO_DIR, "_photo_index.csv")',
        f'',
        f'try:',
        f'    import psycopg2',
        f'except ImportError:',
        f'    print("[ERROR] psycopg2 not available. Install into Blender Python:")',
        f'    print("        <blender_python> -m pip install psycopg2-binary")',
        f'    sys.exit(1)',
        f'',
        f'conn = psycopg2.connect(',
        f'    host=DB_HOST, port=DB_PORT, dbname=DB_NAME,',
        f'    user=DB_USER, password=DB_PASSWORD,',
        f')',
        f'cur = conn.cursor()',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# WKT parsing',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'def parse_wkt_polygon(wkt):',
        f'    """Parse WKT POLYGON/MULTIPOLYGON -> list of rings [(x,y,z), ...]."""',
        f'    rings = []',
        f'    wkt = wkt.strip()',
        f'    for prefix in ("MULTIPOLYGON", "POLYGON"):',
        f'        if wkt.upper().startswith(prefix):',
        f'            wkt = wkt[len(prefix):].strip()',
        f'            break',
        f'    if wkt.startswith("Z"):',
        f'        wkt = wkt[1:].strip()',
        f'    wkt = wkt.strip("()")',
        f'    for part in wkt.split("),("):',
        f'        part = part.strip().strip("()")',
        f'        coords = []',
        f'        for pt in part.split(","):',
        f'            vals = pt.strip().split()',
        f'            x, y = float(vals[0]), float(vals[1])',
        f'            z = float(vals[2]) if len(vals) > 2 else 0.0',
        f'            coords.append((x, y, z))',
        f'        if coords:',
        f'            rings.append(coords)',
        f'    return rings',
        f'',
        f'',
        f'def parse_wkt_line(wkt):',
        f'    """Parse WKT LINESTRING/MULTILINESTRING -> list of (x,y,z)."""',
        f'    wkt = wkt.strip()',
        f'    for prefix in ("MULTILINESTRING", "LINESTRING"):',
        f'        if wkt.upper().startswith(prefix):',
        f'            wkt = wkt[len(prefix):].strip()',
        f'            break',
        f'    if wkt.startswith("Z"):',
        f'        wkt = wkt[1:].strip()',
        f'    wkt = wkt.strip("()")',
        f'    coords = []',
        f'    for pt in wkt.split(","):',
        f'        vals = pt.strip().split()',
        f'        x, y = float(vals[0]), float(vals[1])',
        f'        z = float(vals[2]) if len(vals) > 2 else 0.0',
        f'        coords.append((x, y, z))',
        f'    return coords',
        f'',
        f'',
        f'def parse_wkt_point(wkt):',
        f'    """Parse WKT POINT/MULTIPOINT -> (x,y,z)."""',
        f'    wkt = wkt.strip()',
        f'    for prefix in ("MULTIPOINT", "POINT"):',
        f'        if wkt.upper().startswith(prefix):',
        f'            wkt = wkt[len(prefix):].strip()',
        f'            break',
        f'    if wkt.startswith("Z"):',
        f'        wkt = wkt[1:].strip()',
        f'    wkt = wkt.strip("()")',
        f'    vals = wkt.split(",")[0].strip().split()',
        f'    return (float(vals[0]), float(vals[1]),',
        f'            float(vals[2]) if len(vals) > 2 else 0.0)',
        f'',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Material helpers',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'def make_color_material(name, r, g, b, roughness=0.7):',
        f'    """Flat color PBR material."""',
        f'    mat = bpy.data.materials.new(name=name)',
        f'    mat.use_nodes = True',
        f'    bsdf = mat.node_tree.nodes["Principled BSDF"]',
        f'    bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)',
        f'    bsdf.inputs["Roughness"].default_value = roughness',
        f'    return mat',
        f'',
        f'',
        f'def make_brick_material(name, base_r=0.45, base_g=0.22, base_b=0.12):',
        f'    """Procedural brick material with mortar, weathering, and bump."""',
        f'    mat = bpy.data.materials.new(name=name)',
        f'    mat.use_nodes = True',
        f'    nodes = mat.node_tree.nodes',
        f'    links = mat.node_tree.links',
        f'    bsdf = nodes["Principled BSDF"]',
        f'    # Texture coordinate',
        f'    tex_coord = nodes.new("ShaderNodeTexCoord")',
        f'    # Brick texture',
        f'    brick = nodes.new("ShaderNodeTexBrick")',
        f'    brick.inputs["Color1"].default_value = (base_r, base_g, base_b, 1.0)',
        f'    brick.inputs["Color2"].default_value = (base_r*0.85, base_g*0.85, base_b*0.85, 1.0)',
        f'    brick.inputs["Mortar"].default_value = (0.75, 0.73, 0.70, 1.0)',
        f'    brick.inputs["Scale"].default_value = 6.0',
        f'    brick.inputs["Mortar Size"].default_value = 0.012',
        f'    links.new(tex_coord.outputs["Object"], brick.inputs["Vector"])',
        f'    # Weathering noise overlay',
        f'    noise = nodes.new("ShaderNodeTexNoise")',
        f'    noise.inputs["Scale"].default_value = 12.0',
        f'    noise.inputs["Detail"].default_value = 6.0',
        f'    mix = nodes.new("ShaderNodeMixRGB")',
        f'    mix.blend_type = "MULTIPLY"',
        f'    mix.inputs["Fac"].default_value = 0.2',
        f'    links.new(brick.outputs["Color"], mix.inputs["Color1"])',
        f'    links.new(noise.outputs["Color"], mix.inputs["Color2"])',
        f'    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])',
        f'    # Bump from brick pattern',
        f'    bump = nodes.new("ShaderNodeBump")',
        f'    bump.inputs["Strength"].default_value = 0.15',
        f'    links.new(brick.outputs["Fac"], bump.inputs["Height"])',
        f'    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])',
        f'    bsdf.inputs["Roughness"].default_value = 0.85',
        f'    return mat',
        f'',
        f'',
        f'def make_photo_material(name, image_path):',
        f'    """Material with photo texture + subtle weathering for facades."""',
        f'    mat = bpy.data.materials.new(name=name)',
        f'    mat.use_nodes = True',
        f'    nodes = mat.node_tree.nodes',
        f'    links = mat.node_tree.links',
        f'    bsdf = nodes["Principled BSDF"]',
        f'    # Load image',
        f'    img = bpy.data.images.load(image_path)',
        f'    tex_node = nodes.new("ShaderNodeTexImage")',
        f'    tex_node.image = img',
        f'    tex_node.projection = "BOX"',
        f'    tex_node.projection_blend = 0.3',
        f'    # Texture coordinate (Object) for box projection',
        f'    tex_coord = nodes.new("ShaderNodeTexCoord")',
        f'    # Mapping node to scale texture to building size',
        f'    mapping = nodes.new("ShaderNodeMapping")',
        f'    mapping.inputs["Scale"].default_value = (0.06, 0.06, 0.06)',
        f'    links.new(tex_coord.outputs["Object"], mapping.inputs["Vector"])',
        f'    links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])',
        f'    # Mix photo with subtle noise for weathering',
        f'    noise = nodes.new("ShaderNodeTexNoise")',
        f'    noise.inputs["Scale"].default_value = 15.0',
        f'    noise.inputs["Detail"].default_value = 4.0',
        f'    mix = nodes.new("ShaderNodeMixRGB")',
        f'    mix.blend_type = "MULTIPLY"',
        f'    mix.inputs["Fac"].default_value = 0.15  # subtle weathering',
        f'    links.new(tex_node.outputs["Color"], mix.inputs["Color1"])',
        f'    links.new(noise.outputs["Color"], mix.inputs["Color2"])',
        f'    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])',
        f'    # Slight bump from noise for surface detail',
        f'    bump = nodes.new("ShaderNodeBump")',
        f'    bump.inputs["Strength"].default_value = 0.1',
        f'    links.new(noise.outputs["Fac"], bump.inputs["Height"])',
        f'    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])',
        f'    bsdf.inputs["Roughness"].default_value = 0.75',
        f'    return mat',
        f'',
        f'',
        f'def make_ground_material():',
        f'    """Dark asphalt ground plane material."""',
        f'    mat = bpy.data.materials.new(name="ground_asphalt")',
        f'    mat.use_nodes = True',
        f'    bsdf = mat.node_tree.nodes["Principled BSDF"]',
        f'    bsdf.inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1.0)',
        f'    bsdf.inputs["Roughness"].default_value = 0.95',
        f'    return mat',
        f'',
        f'',
        f'def make_road_material():',
        f'    """Road surface material."""',
        f'    mat = bpy.data.materials.new(name="road_surface")',
        f'    mat.use_nodes = True',
        f'    bsdf = mat.node_tree.nodes["Principled BSDF"]',
        f'    bsdf.inputs["Base Color"].default_value = (0.25, 0.25, 0.25, 1.0)',
        f'    bsdf.inputs["Roughness"].default_value = 0.9',
        f'    return mat',
        f'',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Building mesh construction',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'def make_roof_material():',
        f'    """Dark shingle roof material."""',
        f'    mat = bpy.data.materials.new(name="roof_shingle")',
        f'    mat.use_nodes = True',
        f'    nodes = mat.node_tree.nodes',
        f'    links = mat.node_tree.links',
        f'    bsdf = nodes["Principled BSDF"]',
        f'    # Noise texture for shingle variation',
        f'    noise = nodes.new("ShaderNodeTexNoise")',
        f'    noise.inputs["Scale"].default_value = 50.0',
        f'    noise.inputs["Detail"].default_value = 8.0',
        f'    # Color ramp for dark grey variation',
        f'    ramp = nodes.new("ShaderNodeValToRGB")',
        f'    ramp.color_ramp.elements[0].position = 0.3',
        f'    ramp.color_ramp.elements[0].color = (0.12, 0.12, 0.13, 1.0)',
        f'    ramp.color_ramp.elements[1].position = 0.7',
        f'    ramp.color_ramp.elements[1].color = (0.22, 0.21, 0.20, 1.0)',
        f'    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])',
        f'    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])',
        f'    bsdf.inputs["Roughness"].default_value = 0.9',
        f'    return mat',
        f'',
        f'roof_mat = make_roof_material()',
        f'',
        f'',
        f'def build_extruded_building(name, ring, height, collection, wall_material):',
        f'    """Create a 3D building with floor, walls, and roof.',
        f'    ring: list of (x, y) tuples (already offset-adjusted)',
        f'    height: extrusion height in meters',
        f'    Returns the Blender object or None.',
        f'    """',
        f'    if len(ring) < 3:',
        f'        return None',
        f'    # Remove closing vert if duplicated',
        f'    if ring[0] == ring[-1]:',
        f'        ring = ring[:-1]',
        f'    if len(ring) < 3:',
        f'        return None',
        f'    n = len(ring)',
        f'    mesh = bpy.data.meshes.new(name)',
        f'    bm = bmesh.new()',
        f'    # Bottom verts (z=0)',
        f'    bot = [bm.verts.new((p[0], p[1], 0.0)) for p in ring]',
        f'    # Top verts (z=height)',
        f'    top = [bm.verts.new((p[0], p[1], height)) for p in ring]',
        f'    bm.verts.ensure_lookup_table()',
        f'    # Floor face (material slot 0 = wall)',
        f'    try:',
        f'        bm.faces.new(bot)',
        f'    except ValueError:',
        f'        bm.free()',
        f'        return None',
        f'    # Roof face (material slot 1 = roof)',
        f'    try:',
        f'        rf = bm.faces.new(list(reversed(top)))',
        f'        rf.material_index = 1',
        f'    except ValueError:',
        f'        pass',
        f'    # Wall faces (material slot 0 = wall)',
        f'    for i in range(n):',
        f'        j = (i + 1) % n',
        f'        try:',
        f'            bm.faces.new([bot[i], bot[j], top[j], top[i]])',
        f'        except ValueError:',
        f'            pass',
        f'    # Recalculate normals to face outward',
        f'    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)',
        f'    bm.to_mesh(mesh)',
        f'    bm.free()',
        f'    mesh.update()',
        f'    obj = bpy.data.objects.new(name, mesh)',
        f'    collection.objects.link(obj)',
        f'    # Slot 0: wall material, Slot 1: roof material',
        f'    obj.data.materials.append(wall_material)',
        f'    obj.data.materials.append(roof_mat)',
        f'    # Smooth shading for walls',
        f'    obj.data.shade_smooth()',
        f'    return obj',
        f'',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Scene setup',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'# Clear default scene',
        f'bpy.ops.object.select_all(action="SELECT")',
        f'bpy.ops.object.delete(use_global=False)',
        f'',
        f'# Set render engine to Eevee for fast preview',
        f'for _engine in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):',
        f'    try:',
        f'        bpy.context.scene.render.engine = _engine',
        f'        break',
        f'    except TypeError:',
        f'        continue',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Load photo index (address -> image path)',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'photo_map = {{}}  # address -> full image path',
        f'if os.path.exists(PHOTO_INDEX):',
        f'    with open(PHOTO_INDEX, encoding="utf-8") as f:',
        f'        reader = csv.reader(f)',
        f'        next(reader)  # skip header',
        f'        for row in reader:',
        f'            addr, filename = row[0], row[1]',
        f'            full_path = os.path.join(PHOTO_DIR, filename)',
        f'            if os.path.exists(full_path):',
        f'                photo_map[addr.lower()] = full_path',
        f'    print(f"[OK] Loaded {{len(photo_map)}} photo mappings")',
        f'else:',
        f'    print("[warn] No photo index found, using procedural textures only")',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Compute centroid offset from first layer to avoid float precision issues',
        f'# ---------------------------------------------------------------------------',
        f'',
    ]

    # Emit centroid offset — prefer study area centre so clipped features land near origin
    if layers:
        first = layers[0]
        fgeom_col = first["geometry"]["column"]
        fsrid = first["geometry"].get("srid", 4326)
        fschema = first["schema"]
        ftable = first["table"]
        lines += [
            f'# Use study area centre if available, else first-layer centroid',
            f'try:',
            f'    cur.execute("""',
            f'        SELECT ST_X(ST_Centroid(ST_Transform(ST_Union(geometry), {fsrid}))),',
            f'               ST_Y(ST_Centroid(ST_Transform(ST_Union(geometry), {fsrid})))',
            f'        FROM opendata.study_area',
            f'    """)',
            f'    _sa = cur.fetchone()',
            f'    OFFSET_X, OFFSET_Y = _sa[0], _sa[1]',
            f'except Exception:',
            f'    conn.rollback()',
            f'    cur.execute(\'SELECT ST_X(ST_Centroid("{fgeom_col}")), ST_Y(ST_Centroid("{fgeom_col}")) '
            f'FROM "{fschema}"."{ftable}" LIMIT 500\')',
            f'    _centroids = cur.fetchall()',
            f'    OFFSET_X = sum(r[0] for r in _centroids) / len(_centroids) if _centroids else 0.0',
            f'    OFFSET_Y = sum(r[1] for r in _centroids) / len(_centroids) if _centroids else 0.0',
            f'print(f"[OK] Centroid offset: ({{OFFSET_X:.1f}}, {{OFFSET_Y:.1f}})")',
            f'',
        ]
    else:
        lines += [
            f'OFFSET_X = 0.0',
            f'OFFSET_Y = 0.0',
            f'',
        ]

    # Colour palette for procedural brick variations
    brick_palette = [
        (0.45, 0.22, 0.12),  # classic red brick
        (0.55, 0.35, 0.20),  # warm brown brick
        (0.40, 0.38, 0.35),  # grey stone
        (0.60, 0.55, 0.45),  # sandstone
        (0.35, 0.18, 0.10),  # dark red brick
        (0.50, 0.48, 0.42),  # light grey
    ]

    for i, layer in enumerate(layers):
        var = safe_var(layer["table"])
        table = layer["table"]
        schema_name = layer["schema"]
        geom = layer["geometry"]
        geom_type = geom["type"].upper()
        geom_col = geom["column"]
        col_names = [c["name"] for c in layer["columns"]]

        # Detect height column
        ht_col = None
        for hc in height_columns:
            if hc in col_names:
                ht_col = hc
                break

        is_point = "POINT" in geom_type
        is_line = "LINE" in geom_type
        is_poly = "POLYGON" in geom_type
        # Handle generic "GEOMETRY" type: infer from height columns or default polygon
        if not is_point and not is_line and not is_poly:
            if ht_col or any(kw in table.lower() for kw in ("building", "massing", "footprint", "parcel")):
                is_poly = True
            else:
                is_poly = True  # default to polygon for generic geometry

        lines += [
            f'# {"=" * 66}',
            f'# Layer: {schema_name}.{table}  ({geom["type"]}, SRID {geom["srid"]})',
            f'# {"=" * 66}',
            f'',
        ]

        if is_poly:
            # For polygon layers: spatial join to addresses for photo matching
            select_cols = [f'ST_AsText(m."{geom_col}") AS _wkt']
            if ht_col:
                select_cols.append(f'm."{ht_col}"')
            select_cols.append('a.address_full')
            select_str = ", ".join(select_cols)

            lines += [
                f'print("[*] Loading {schema_name}.{table} with address matching ...")',
                f'',
                f'# Try to clip to study area if available, otherwise load all',
                f'try:',
                f'    cur.execute("SELECT 1 FROM opendata.study_area LIMIT 1")',
                f'    _has_study_area = cur.fetchone() is not None',
                f'except Exception:',
                f'    conn.rollback()',
                f'    _has_study_area = False',
                f'',
                f'if _has_study_area:',
                f'    print("    Clipping to study area ...")',
                f'    cur.execute("""',
                f'        SELECT {select_str}',
                f'        FROM "{schema_name}"."{table}" m',
                f'        LEFT JOIN LATERAL (',
                f'            SELECT a.address_full',
                f'            FROM opendata.addresses a',
                f'            WHERE ST_DWithin(ST_Transform(a.geom, {geom["srid"]}), m."{geom_col}", 15)',
                f'            ORDER BY ST_Transform(a.geom, {geom["srid"]}) <-> m."{geom_col}"',
                f'            LIMIT 1',
                f'        ) a ON TRUE',
                f'        WHERE ST_Intersects(m."{geom_col}",',
                f'            ST_Transform((SELECT ST_Buffer(ST_Union(geometry), 100) FROM opendata.study_area), {geom["srid"]}))',
                f'    """)',
                f'else:',
                f'    cur.execute("""',
                f'        SELECT {select_str}',
                f'        FROM "{schema_name}"."{table}" m',
                f'        LEFT JOIN LATERAL (',
                f'            SELECT a.address_full',
                f'            FROM opendata.addresses a',
                f'            WHERE ST_DWithin(ST_Transform(a.geom, {geom["srid"]}), m."{geom_col}", 15)',
                f'            ORDER BY ST_Transform(a.geom, {geom["srid"]}) <-> m."{geom_col}"',
                f'            LIMIT 1',
                f'        ) a ON TRUE',
                f'        LIMIT 50000',
                f'    """)',
                f'rows_{var} = cur.fetchall()',
                f'print(f"    Loaded {{len(rows_{var})}} features")',
                f'',
            ]

            lines += [
                f'# Create collections',
                f'col_textured = bpy.data.collections.new("{table}_textured")',
                f'col_procedural = bpy.data.collections.new("{table}_procedural")',
                f'bpy.context.scene.collection.children.link(col_textured)',
                f'bpy.context.scene.collection.children.link(col_procedural)',
                f'',
                f'# Pre-create procedural brick materials',
                f'brick_mats = [',
            ]
            for bi, (br, bg, bb) in enumerate(brick_palette):
                lines.append(
                    f'    make_brick_material("brick_{bi}", {br}, {bg}, {bb}),'
                )
            lines += [
                f']',
                f'',
                f'# Cache for photo materials (avoid reloading same image)',
                f'photo_mat_cache = {{}}',
                f'textured_count = 0',
                f'procedural_count = 0',
                f'',
                f'_total = len(rows_{var})',
                f'_skipped = 0',
                f'for _idx, _row in enumerate(rows_{var}):',
                f'    if _idx % 100 == 0:',
                f'        print(f"    Progress: {{_idx}}/{{_total}} buildings ...", end="\\r")',
                f'    _wkt = _row[0]',
            ]
            if ht_col:
                lines += [
                    f'    _ht = float(_row[1]) if _row[1] is not None else 3.0',
                    f'    _ht = max(_ht, 0.5)',
                    f'    _addr = _row[2]',
                ]
            else:
                lines += [
                    f'    _ht = 3.0',
                    f'    _addr = _row[1]',
                ]
            lines += [
                f'    _rings = parse_wkt_polygon(_wkt)',
                f'    if not _rings:',
                f'        _skipped += 1',
                f'        continue',
                f'    # Use outer ring only; offset to scene centre',
                f'    _ring = [(_p[0] - OFFSET_X, _p[1] - OFFSET_Y) for _p in _rings[0]]',
                f'',
                f'    # Check for photo match',
                f'    _photo_path = None',
                f'    if _addr:',
                f'        _photo_path = photo_map.get(_addr.lower())',
                f'',
                f'    if _photo_path:',
                f'        if _photo_path not in photo_mat_cache:',
                f'            _mat_name = f"photo_{{os.path.basename(_photo_path)}}"',
                f'            photo_mat_cache[_photo_path] = make_photo_material(_mat_name, _photo_path)',
                f'        _mat = photo_mat_cache[_photo_path]',
                f'        _col = col_textured',
                f'        textured_count += 1',
                f'    else:',
                f'        _mat = brick_mats[_idx % len(brick_mats)]',
                f'        _col = col_procedural',
                f'        procedural_count += 1',
                f'',
                f'    _obj = build_extruded_building(f"{table}_{{_idx}}", _ring, _ht, _col, _mat)',
                f'    if _obj and _addr:',
                f'        _obj["address"] = _addr',
                f'',
                f'print(f"\\n    Buildings: {{textured_count}} photo-textured, {{procedural_count}} procedural, {{_skipped}} skipped")',
                f'',
            ]

        elif is_point:
            # Point layers (POIs etc.)
            lines += [
                f'print("[*] Loading {schema_name}.{table} (points) ...")',
                f'cur.execute(\'SELECT ST_AsText("{geom_col}") FROM "{schema_name}"."{table}" LIMIT 10000\')',
                f'rows_{var} = cur.fetchall()',
                f'',
                f'col_{var} = bpy.data.collections.new("{table}")',
                f'bpy.context.scene.collection.children.link(col_{var})',
                f'mat_{var} = make_color_material("mat_{table}", 0.9, 0.2, 0.2)',
                f'',
                f'for _idx, _row in enumerate(rows_{var}):',
                f'    _pt = parse_wkt_point(_row[0])',
                f'    _x = _pt[0] - OFFSET_X',
                f'    _y = _pt[1] - OFFSET_Y',
                f'    bpy.ops.mesh.primitive_ico_sphere_add(radius=1.5, location=(_x, _y, _pt[2]))',
                f'    _obj = bpy.context.active_object',
                f'    _obj.name = f"{table}_{{_idx}}"',
                f'    col_{var}.objects.link(_obj)',
                f'    bpy.context.scene.collection.objects.unlink(_obj)',
                f'    _obj.data.materials.append(mat_{var})',
                f'',
                f'print(f"    Created {{len(rows_{var})}} point objects")',
                f'',
            ]

        else:  # LINE (roads, cycling network, etc.)
            lines += [
                f'print("[*] Loading {schema_name}.{table} (lines) ...")',
                f'cur.execute(\'SELECT ST_AsText("{geom_col}") FROM "{schema_name}"."{table}" LIMIT 20000\')',
                f'rows_{var} = cur.fetchall()',
                f'',
                f'col_{var} = bpy.data.collections.new("{table}")',
                f'bpy.context.scene.collection.children.link(col_{var})',
                f'mat_{var} = make_road_material()',
                f'',
                f'for _idx, _row in enumerate(rows_{var}):',
                f'    _pts = parse_wkt_line(_row[0])',
                f'    if len(_pts) < 2:',
                f'        continue',
                f'    _curve = bpy.data.curves.new(f"{table}_{{_idx}}", "CURVE")',
                f'    _curve.dimensions = "3D"',
                f'    _spline = _curve.splines.new("POLY")',
                f'    _spline.points.add(len(_pts) - 1)',
                f'    for _j, _pt in enumerate(_pts):',
                f'        _spline.points[_j].co = (_pt[0] - OFFSET_X, _pt[1] - OFFSET_Y, 0.2, 1.0)',
                f'    _obj = bpy.data.objects.new(f"{table}_{{_idx}}", _curve)',
                f'    _obj.data.bevel_depth = 3.0  # road width',
                f'    _obj.data.bevel_resolution = 0',
                f'    _obj.data.fill_mode = "FULL"',
                f'    col_{var}.objects.link(_obj)',
                f'    _obj.data.materials.append(mat_{var})',
                f'',
                f'print(f"    Created {{len(rows_{var})}} road segments")',
                f'',
            ]

    # Ground plane + lighting + camera
    lines += [
        f'# ---------------------------------------------------------------------------',
        f'# Ground plane',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'bpy.ops.mesh.primitive_plane_add(size=2000, location=(0, 0, -0.1))',
        f'_ground = bpy.context.active_object',
        f'_ground.name = "Ground"',
        f'_ground.data.materials.append(make_ground_material())',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Lighting',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'# Main sun',
        f'bpy.ops.object.light_add(type="SUN", location=(100, -100, 500))',
        f'_sun = bpy.context.active_object',
        f'_sun.name = "Sun"',
        f'_sun.data.energy = 4.0',
        f'_sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(-30))',
        f'',
        f'# Ambient fill light',
        f'bpy.ops.object.light_add(type="SUN", location=(-100, 100, 300))',
        f'_fill = bpy.context.active_object',
        f'_fill.name = "Fill"',
        f'_fill.data.energy = 1.0',
        f'_fill.rotation_euler = (math.radians(60), 0, math.radians(150))',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Camera',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'bpy.ops.object.camera_add(location=(150, -250, 200))',
        f'cam = bpy.context.active_object',
        f'cam.name = "Camera"',
        f'cam.rotation_euler = (math.radians(55), 0, math.radians(25))',
        f'cam.data.lens = 35',
        f'bpy.context.scene.camera = cam',
        f'',
        f'# ---------------------------------------------------------------------------',
        f'# Viewport setup',
        f'# ---------------------------------------------------------------------------',
        f'',
        f'for area in bpy.context.screen.areas:',
        f'    if area.type == "VIEW_3D":',
        f'        for space in area.spaces:',
        f'            if space.type == "VIEW_3D":',
        f'                space.shading.type = "MATERIAL"',
        f'                space.clip_end = 10000',
        f'                break',
        f'',
        f'# Set world background to light sky blue',
        f'world = bpy.data.worlds.get("World")',
        f'if world and world.use_nodes:',
        f'    bg = world.node_tree.nodes.get("Background")',
        f'    if bg:',
        f'        bg.inputs["Color"].default_value = (0.53, 0.69, 0.87, 1.0)',
        f'        bg.inputs["Strength"].default_value = 0.8',
        f'',
        f'conn.close()',
        f'print(f"[OK] Blender scene ready. {len(layers)} layer(s) loaded.")',
        f'print("     Tip: Press Numpad 0 for camera view, Z for shading options")',
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
            ly for ly in schema["layers"]
            if ly["qualified_name"] in args.layers
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
