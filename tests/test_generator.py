"""Tests for gis_codegen.generator module."""

import pytest
from gis_codegen.generator import (
    VALID_OPERATIONS,
    _arcpy_op_blocks,
    _guess_height_field,
    _pyqgis_op_blocks,
    generate_arcpy,
    generate_deck,
    generate_folium,
    generate_kepler,
    generate_pyqgis,
    pg_type_to_arcpy,
    pg_type_to_pyqgis,
    safe_var,
)


# ---------------------------------------------------------------------------
# safe_var
# ---------------------------------------------------------------------------

class TestSafeVar:
    def test_hyphen_to_underscore(self):
        assert safe_var("my-table") == "my_table"

    def test_space_to_underscore(self):
        assert safe_var("my table") == "my_table"

    def test_dot_to_underscore(self):
        assert safe_var("public.roads") == "public_roads"

    def test_already_safe(self):
        assert safe_var("already_safe") == "already_safe"

    def test_empty_string(self):
        assert safe_var("") == ""


# ---------------------------------------------------------------------------
# pg_type_to_pyqgis
# ---------------------------------------------------------------------------

class TestPgTypeToPyqgis:
    @pytest.mark.parametrize("pg_type,expected", [
        ("integer",                    "int"),
        ("bigint",                     "int"),
        ("smallint",                   "int"),
        ("double precision",           "float"),
        ("numeric",                    "float"),
        ("real",                       "float"),
        ("boolean",                    "bool"),
        ("text",                       "str"),
        ("character varying",          "str"),
        ("character",                  "str"),
        ("date",                       "QDate"),
        ("timestamp without time zone","QDateTime"),
        ("timestamp with time zone",   "QDateTime"),
        ("json",                       "str"),
        ("jsonb",                      "str"),
        ("uuid",                       "str"),
        ("unknown_type",               "str"),   # fallback
    ])
    def test_mapping(self, pg_type, expected):
        assert pg_type_to_pyqgis(pg_type) == expected


# ---------------------------------------------------------------------------
# pg_type_to_arcpy
# ---------------------------------------------------------------------------

class TestPgTypeToArcpy:
    @pytest.mark.parametrize("pg_type,expected", [
        ("integer",                    "LONG"),
        ("bigint",                     "DOUBLE"),
        ("smallint",                   "SHORT"),
        ("double precision",           "DOUBLE"),
        ("numeric",                    "DOUBLE"),
        ("real",                       "FLOAT"),
        ("boolean",                    "SHORT"),
        ("text",                       "TEXT"),
        ("character varying",          "TEXT"),
        ("character",                  "TEXT"),
        ("date",                       "DATE"),
        ("timestamp without time zone","DATE"),
        ("timestamp with time zone",   "DATE"),
        ("uuid",                       "TEXT"),
        ("json",                       "TEXT"),
        ("jsonb",                      "TEXT"),
        ("unknown_type",               "TEXT"),  # fallback
    ])
    def test_mapping(self, pg_type, expected):
        assert pg_type_to_arcpy(pg_type) == expected


# ---------------------------------------------------------------------------
# _guess_height_field
# ---------------------------------------------------------------------------

class TestGuessHeightField:
    def test_finds_height(self):
        cols = [{"name": "id"}, {"name": "height"}, {"name": "name"}]
        assert _guess_height_field(cols) == "height"

    def test_finds_floors(self):
        cols = [{"name": "id"}, {"name": "floors"}]
        assert _guess_height_field(cols) == "floors"

    def test_finds_elevation(self):
        cols = [{"name": "address"}, {"name": "elevation"}]
        assert _guess_height_field(cols) == "elevation"

    def test_returns_none_when_absent(self):
        cols = [{"name": "id"}, {"name": "address"}, {"name": "area"}]
        assert _guess_height_field(cols) is None

    def test_case_insensitive_match(self):
        # column named "ELEVATION" → .lower() == "elevation" ∈ _HEIGHT_HINTS
        cols = [{"name": "ELEVATION"}]
        assert _guess_height_field(cols) == "ELEVATION"

    def test_returns_first_match(self):
        cols = [{"name": "z"}, {"name": "height"}]
        assert _guess_height_field(cols) == "z"

    def test_empty_columns(self):
        assert _guess_height_field([]) is None


# ---------------------------------------------------------------------------
# VALID_OPERATIONS
# ---------------------------------------------------------------------------

class TestValidOperations:
    _GENERAL = {
        "reproject", "export", "buffer", "clip", "select",
        "dissolve", "centroid", "field_calc", "spatial_join", "intersect",
    }
    _THREED = {"extrude", "z_stats", "floor_ceiling", "volume", "scene_layer"}

    def test_general_ops_present(self):
        assert self._GENERAL.issubset(set(VALID_OPERATIONS))

    def test_3d_ops_present(self):
        assert self._THREED.issubset(set(VALID_OPERATIONS))

    def test_total_count(self):
        assert len(VALID_OPERATIONS) == 15

    def test_no_duplicates(self):
        assert len(VALID_OPERATIONS) == len(set(VALID_OPERATIONS))


# ---------------------------------------------------------------------------
# _pyqgis_op_blocks
# ---------------------------------------------------------------------------

class TestPyqgisOpBlocks:
    _cols = [{"name": "parcel_id", "data_type": "integer"}]

    def _joined(self, ops):
        return "\n".join(_pyqgis_op_blocks("parcels", "parcels", self._cols, ops))

    def test_empty_ops_returns_empty_list(self):
        assert _pyqgis_op_blocks("parcels", "parcels", self._cols, set()) == []

    def test_reproject(self):
        code = self._joined({"reproject"})
        assert "native:reprojectlayer" in code
        assert "lyr_parcels_reprojected" in code

    def test_export(self):
        code = self._joined({"export"})
        assert "QgsVectorFileWriter" in code
        assert "GeoJSON" in code

    def test_buffer(self):
        code = self._joined({"buffer"})
        assert "native:buffer" in code
        assert "DISTANCE" in code

    def test_select_uses_first_col(self):
        code = self._joined({"select"})
        assert "parcel_id" in code
        assert "selectByExpression" in code

    def test_dissolve(self):
        code = self._joined({"dissolve"})
        assert "native:dissolve" in code
        assert "lyr_parcels_dissolved" in code

    def test_centroid(self):
        code = self._joined({"centroid"})
        assert "native:centroids" in code
        assert "lyr_parcels_centroids" in code

    def test_field_calc(self):
        code = self._joined({"field_calc"})
        assert "native:fieldcalculator" in code
        assert "new_field" in code

    def test_extrude(self):
        code = self._joined({"extrude"})
        assert "QgsPolygon3DSymbol" in code
        assert "PropertyExtrusionHeight" in code
        assert "setRenderer3D" in code

    def test_z_stats(self):
        code = self._joined({"z_stats"})
        assert "QgsWkbTypes" in code
        assert "hasZ" in code

    def test_floor_ceiling(self):
        code = self._joined({"floor_ceiling"})
        assert "PropertyHeight" in code
        assert "base_height" in code
        assert "roof_height" in code

    def test_volume(self):
        code = self._joined({"volume"})
        assert "total_vol_parcels" in code
        assert "geometry().area()" in code

    def test_scene_layer(self):
        code = self._joined({"scene_layer"})
        assert "_3dtiles" in code
        assert "makedirs" in code

    def test_multiple_ops_both_present(self):
        code = self._joined({"reproject", "buffer"})
        assert "native:reprojectlayer" in code
        assert "native:buffer" in code


# ---------------------------------------------------------------------------
# _arcpy_op_blocks
# ---------------------------------------------------------------------------

class TestArcpyOpBlocks:
    _cols = [{"name": "road_id", "data_type": "integer"}]

    def _joined(self, ops):
        return "\n".join(_arcpy_op_blocks("roads", "roads", self._cols, ops))

    def test_empty_ops_returns_empty_list(self):
        assert _arcpy_op_blocks("roads", "roads", self._cols, set()) == []

    def test_reproject(self):
        code = self._joined({"reproject"})
        assert "arcpy.management.Project" in code
        assert "SpatialReference" in code

    def test_buffer(self):
        code = self._joined({"buffer"})
        assert "arcpy.analysis.Buffer" in code
        assert "_out_buf_roads" in code

    def test_export(self):
        code = self._joined({"export"})
        assert "FeatureClassToShapefile" in code

    def test_dissolve(self):
        code = self._joined({"dissolve"})
        assert "arcpy.management.Dissolve" in code

    def test_centroid(self):
        code = self._joined({"centroid"})
        assert "FeatureToPoint" in code

    def test_field_calc(self):
        code = self._joined({"field_calc"})
        assert "CalculateField" in code
        assert "CopyFeatures" in code

    def test_extrude(self):
        code = self._joined({"extrude"})
        assert "arcpy.ddd" in code
        assert "ExtrudePolygon" in code

    def test_z_stats(self):
        code = self._joined({"z_stats"})
        assert "AddZInformation" in code
        assert "Z_MIN;Z_MAX;Z_MEAN" in code

    def test_floor_ceiling(self):
        code = self._joined({"floor_ceiling"})
        assert "base_elevation_field" in code
        assert "_BASE_FIELD_roads" in code

    def test_volume(self):
        code = self._joined({"volume"})
        assert "_total_vol_roads" in code
        assert "SHAPE@AREA" in code

    def test_scene_layer(self):
        code = self._joined({"scene_layer"})
        assert "CreateSceneLayerPackage" in code
        assert ".slpk" in code


# ---------------------------------------------------------------------------
# generate_pyqgis
# ---------------------------------------------------------------------------

class TestGeneratePyqgis:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_pyqgis(schema, db_config), str)

    def test_db_constants_present(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert f'DB_HOST     = "{db_config["host"]}"' in code
        assert f'DB_PORT     = "{db_config["port"]}"' in code
        assert f'DB_NAME     = "{db_config["dbname"]}"' in code
        assert f'DB_USER     = "{db_config["user"]}"' in code

    def test_both_layers_present(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "parcels" in code
        assert "roads" in code

    def test_single_layer_schema(self, single_layer_schema, db_config):
        code = generate_pyqgis(single_layer_schema, db_config)
        assert "parcels" in code
        assert "uri_roads" not in code

    def test_qgs_init_and_exit(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "qgs.initQgis()" in code
        assert "qgs.exitQgis()" in code

    def test_qgsdatasourceuri_present(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "QgsDataSourceUri" in code
        assert "uri_parcels.setDataSource" in code

    def test_field_names_in_output(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "parcel_id" in code
        assert "address" in code
        assert "height" in code

    def test_processing_import_injected_for_buffer(self, schema, db_config):
        code = generate_pyqgis(schema, db_config, operations=["buffer"])
        assert "from qgis import processing" in code

    def test_processing_import_injected_for_reproject(self, schema, db_config):
        code = generate_pyqgis(schema, db_config, operations=["reproject"])
        assert "from qgis import processing" in code

    def test_processing_import_absent_without_ops(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "from qgis import processing" not in code

    def test_processing_import_absent_for_export_only(self, schema, db_config):
        # export uses QgsVectorFileWriter, not processing.run
        code = generate_pyqgis(schema, db_config, operations=["export"])
        assert "from qgis import processing" not in code

    def test_buffer_op_included(self, schema, db_config):
        code = generate_pyqgis(schema, db_config, operations=["buffer"])
        assert "native:buffer" in code

    def test_extrude_op_included(self, schema, db_config):
        code = generate_pyqgis(schema, db_config, operations=["extrude"])
        assert "QgsPolygon3DSymbol" in code

    def test_no_ops_no_operation_blocks(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "native:buffer" not in code
        assert "QgsPolygon3DSymbol" not in code

    def test_geometry_type_in_comments(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert "MULTIPOLYGON" in code
        assert "MULTILINESTRING" in code


# ---------------------------------------------------------------------------
# generate_arcpy
# ---------------------------------------------------------------------------

class TestGenerateArcpy:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_arcpy(schema, db_config), str)

    def test_sde_connection_block(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert "CreateDatabaseConnection" in code
        assert "SDE_FILE" in code
        assert "POSTGRESQL" in code

    def test_db_constants_present(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert f'DB_NAME     = "{db_config["dbname"]}"' in code
        assert f'DB_USER     = "{db_config["user"]}"' in code

    def test_both_layers_present(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert "fc_parcels" in code
        assert "fc_roads" in code

    def test_arcpy_exists_check(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert "arcpy.Exists(fc_parcels)" in code

    def test_arcpy_describe_call(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert "arcpy.Describe" in code

    def test_buffer_op_included(self, schema, db_config):
        code = generate_arcpy(schema, db_config, operations=["buffer"])
        assert "arcpy.analysis.Buffer" in code

    def test_scene_layer_op_included(self, schema, db_config):
        code = generate_arcpy(schema, db_config, operations=["scene_layer"])
        assert "CreateSceneLayerPackage" in code


# ---------------------------------------------------------------------------
# generate_folium
# ---------------------------------------------------------------------------

class TestGenerateFolium:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_folium(schema, db_config), str)

    def test_folium_imports(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "import folium" in code
        assert "import geopandas as gpd" in code
        assert "from sqlalchemy import create_engine" in code

    def test_pgpassword_env_used(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_no_hardcoded_password(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert db_config["password"] not in code

    def test_both_layers_loaded(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "gdf_parcels" in code
        assert "gdf_roads" in code

    def test_geojson_layers_added(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "folium.GeoJson" in code

    def test_layer_control_added(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "LayerControl" in code

    def test_map_saved(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "m.save" in code
        assert "OUTPUT_HTML" in code

    def test_reprojected_to_4326(self, schema, db_config):
        code = generate_folium(schema, db_config)
        assert "to_crs(epsg=4326)" in code


# ---------------------------------------------------------------------------
# generate_kepler
# ---------------------------------------------------------------------------

class TestGenerateKepler:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_kepler(schema, db_config), str)

    def test_keplergl_import(self, schema, db_config):
        code = generate_kepler(schema, db_config)
        assert "KeplerGl" in code

    def test_pgpassword_env_used(self, schema, db_config):
        code = generate_kepler(schema, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_height_field_hint_for_parcels(self, schema, db_config):
        # parcels layer has "height" column → 3D hint comment
        code = generate_kepler(schema, db_config)
        assert "3D height field detected" in code

    def test_add_data_calls(self, schema, db_config):
        code = generate_kepler(schema, db_config)
        assert "map_k.add_data" in code

    def test_save_to_html(self, schema, db_config):
        code = generate_kepler(schema, db_config)
        assert "save_to_html" in code


# ---------------------------------------------------------------------------
# generate_deck
# ---------------------------------------------------------------------------

class TestGenerateDeck:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_deck(schema, db_config), str)

    def test_pydeck_import(self, schema, db_config):
        code = generate_deck(schema, db_config)
        assert "import pydeck as pdk" in code

    def test_pgpassword_env_used(self, schema, db_config):
        code = generate_deck(schema, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_height_extrusion_commented_out(self, schema, db_config):
        # parcels has "height" → get_elevation hint present but commented
        code = generate_deck(schema, db_config)
        assert "get_elevation" in code
        assert "properties.height" in code

    def test_deck_layers_list_built(self, schema, db_config):
        code = generate_deck(schema, db_config)
        assert "_deck_layers" in code
        assert "_deck_layers.append" in code

    def test_pdk_deck_created(self, schema, db_config):
        code = generate_deck(schema, db_config)
        assert "pdk.Deck" in code

    def test_to_html_written(self, schema, db_config):
        code = generate_deck(schema, db_config)
        assert "to_html" in code
        assert "OUTPUT_HTML" in code

    def test_geojson_layer_for_polygon(self, schema, db_config):
        # parcels is MULTIPOLYGON → GeoJsonLayer
        code = generate_deck(schema, db_config)
        assert "GeoJsonLayer" in code
