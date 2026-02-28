"""Tests for gis_codegen.generator module."""

import pytest
from gis_codegen.generator import (
    VALID_OPERATIONS,
    _arcpy_op_blocks,
    _guess_height_field,
    _pyqgis_op_blocks,
    _qgs_geom_type,
    generate_arcpy,
    generate_deck,
    generate_export,
    generate_folium,
    generate_kepler,
    generate_pyqgis,
    generate_pyt,
    generate_qgs,
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


# ---------------------------------------------------------------------------
# generate_export
# ---------------------------------------------------------------------------

class TestGenerateExport:
    def test_returns_string(self, schema, db_config):
        assert isinstance(generate_export(schema, db_config), str)

    def test_geopandas_import(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "import geopandas as gpd" in code

    def test_sqlalchemy_engine(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "create_engine" in code

    def test_pgpassword_env_used(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_no_hardcoded_password(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert db_config["password"] not in code

    def test_output_gpkg_defined(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "OUTPUT_GPKG" in code
        assert ".gpkg" in code

    def test_both_layers_exported(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert '"parcels"' in code
        assert '"roads"' in code

    def test_read_postgis_called_per_layer(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert code.count("read_postgis") == 2

    def test_to_file_gpkg_driver(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert 'driver="GPKG"' in code

    def test_first_layer_write_mode(self, schema, db_config):
        # First layer must use mode="w" to create the file
        code = generate_export(schema, db_config)
        assert 'mode="w"' in code

    def test_second_layer_append_mode(self, schema, db_config):
        # Subsequent layers must use mode="a" to avoid overwriting
        code = generate_export(schema, db_config)
        assert 'mode="a"' in code

    def test_per_layer_try_except(self, schema, db_config):
        # Each layer wrapped in try/except so one failure doesn't abort
        code = generate_export(schema, db_config)
        assert code.count("try:") == 2
        assert code.count("except Exception") == 2

    def test_engine_disposed(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "engine.dispose()" in code

    def test_sys_exit_on_partial_failure(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "sys.exit(1)" in code

    def test_crs_comment_present(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "to_crs" in code  # commented-out reprojection hint

    def test_db_constants_present(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert f'DB_HOST     = "{db_config["host"]}"' in code
        assert f'DB_NAME     = "{db_config["dbname"]}"' in code

    def test_srid_in_comment(self, schema, db_config):
        code = generate_export(schema, db_config)
        assert "SRID: 4326" in code

    def test_single_layer_schema(self, single_layer_schema, db_config):
        code = generate_export(single_layer_schema, db_config)
        # Only one layer → only mode="w", no mode="a"
        assert 'mode="w"' in code
        assert 'mode="a"' not in code


# ---------------------------------------------------------------------------
# _qgs_geom_type
# ---------------------------------------------------------------------------

class TestQgsGeomType:
    @pytest.mark.parametrize("geom_type,expected_name,expected_code", [
        ("POINT",           "Point",   0),
        ("MULTIPOINT",      "Point",   0),
        ("LINESTRING",      "Line",    1),
        ("MULTILINESTRING", "Line",    1),
        ("POLYGON",         "Polygon", 2),
        ("MULTIPOLYGON",    "Polygon", 2),
        ("GEOMETRY",        "Polygon", 2),  # unknown → polygon fallback
    ])
    def test_mapping(self, geom_type, expected_name, expected_code):
        name, code = _qgs_geom_type(geom_type)
        assert name == expected_name
        assert code == expected_code

    def test_case_insensitive(self):
        name, code = _qgs_geom_type("point")
        assert name == "Point"
        assert code == 0


# ---------------------------------------------------------------------------
# generate_qgs
# ---------------------------------------------------------------------------

class TestGenerateQgs:
    def test_returns_xml_declaration(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert xml.startswith("<!DOCTYPE qgis")

    def test_qgis_root_element(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert "<qgis " in xml
        assert "</qgis>" in xml

    def test_project_name_is_dbname(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert f'projectname="{db_config["dbname"]}"' in xml

    def test_epsg4326_project_crs(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert "EPSG:4326" in xml

    def test_both_layers_present(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert "<layername>parcels</layername>" in xml
        assert "<layername>roads</layername>" in xml

    def test_provider_is_postgres(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert xml.count(">postgres</provider>") == 2

    def test_datasource_contains_host_and_dbname(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert f"host={db_config['host']}" in xml
        assert f"dbname='{db_config['dbname']}'" in xml

    def test_password_not_in_output(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert db_config["password"] not in xml

    def test_geometry_type_polygon(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        # parcels is MULTIPOLYGON → geometry="Polygon", layerGeometryType 2
        assert 'geometry="Polygon"' in xml
        assert "<layerGeometryType>2</layerGeometryType>" in xml

    def test_geometry_type_line(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        # roads is MULTILINESTRING → geometry="Line", layerGeometryType 1
        assert 'geometry="Line"' in xml
        assert "<layerGeometryType>1</layerGeometryType>" in xml

    def test_layer_id_deterministic(self, schema, db_config):
        xml1 = generate_qgs(schema, db_config)
        xml2 = generate_qgs(schema, db_config)
        # Extract all layer <id> tags — must be identical across calls
        import re
        ids1 = re.findall(r"<id>([^<]+)</id>", xml1)
        ids2 = re.findall(r"<id>([^<]+)</id>", xml2)
        assert ids1 == ids2
        assert len(ids1) == 2

    def test_layer_id_format(self, schema, db_config):
        import re
        xml = generate_qgs(schema, db_config)
        ids = re.findall(r"<id>([^<]+)</id>", xml)
        for layer_id in ids:
            # format: {table}_{8 hex chars}
            assert re.match(r"^[a-z_]+_[0-9a-f]{8}$", layer_id), \
                f"Unexpected layer id format: {layer_id}"

    def test_srid_per_layer(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        # Both layers have srid=4326 → should appear in SRS blocks
        assert xml.count("EPSG:4326") >= 2

    def test_primary_key_in_datasource(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert "key='parcel_id'" in xml
        assert "key='road_id'" in xml

    def test_legend_layer_names(self, schema, db_config):
        xml = generate_qgs(schema, db_config)
        assert 'name="parcels"' in xml
        assert 'name="roads"' in xml

    def test_single_layer_schema(self, single_layer_schema, db_config):
        xml = generate_qgs(single_layer_schema, db_config)
        assert "<layername>parcels</layername>" in xml
        assert "roads" not in xml

    def test_empty_layers(self, db_config):
        empty_schema = {"database": "test_db", "layer_count": 0, "layers": []}
        xml = generate_qgs(empty_schema, db_config)
        assert "<qgis " in xml
        assert "<maplayer" not in xml


# ---------------------------------------------------------------------------
# generate_pyt
# ---------------------------------------------------------------------------

class TestGeneratePyt:
    def test_returns_python_source(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "class Toolbox:" in code
        assert "class LoadPostGISLayers:" in code

    def test_toolbox_lists_tool(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "self.tools = [LoadPostGISLayers]" in code

    def test_six_parameters(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert code.count("arcpy.Parameter(") == 6

    def test_host_default_prefilled(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert f'host.value = "{db_config["host"]}"' in code

    def test_port_default_prefilled(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert f'port.value = "{db_config["port"]}"' in code

    def test_dbname_default_prefilled(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert f'dbname.value = "{db_config["dbname"]}"' in code

    def test_user_default_prefilled(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert f'user.value = "{db_config["user"]}"' in code

    def test_password_not_hardcoded(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert db_config["password"] not in code

    def test_password_param_required(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        # password param must be Required, not Optional
        assert 'parameterType="Required"' in code

    def test_both_layers_in_execute(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert '"parcels"' in code
        assert '"roads"' in code

    def test_create_database_connection_called(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "CreateDatabaseConnection" in code

    def test_add_data_from_path_called(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "addDataFromPath" in code

    def test_scratch_folder_used(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "arcpy.env.scratchFolder" in code

    def test_is_licensed_returns_true(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert "def isLicensed(self):" in code
        assert "return True" in code

    def test_schema_filter_param_optional(self, schema, db_config):
        code = generate_pyt(schema, db_config)
        assert 'parameterType="Optional"' in code


# ---------------------------------------------------------------------------
# Password safety in generate_pyqgis and generate_arcpy
# ---------------------------------------------------------------------------

class TestPasswordNotEmbedded:
    """Generated scripts must never contain the literal database password."""

    def test_pyqgis_no_hardcoded_password(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert db_config["password"] not in code

    def test_pyqgis_uses_pgpassword_env(self, schema, db_config):
        code = generate_pyqgis(schema, db_config)
        assert 'os.environ.get("PGPASSWORD"' in code

    def test_arcpy_no_hardcoded_password(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert db_config["password"] not in code

    def test_arcpy_uses_pgpassword_env(self, schema, db_config):
        code = generate_arcpy(schema, db_config)
        assert 'os.environ.get("PGPASSWORD"' in code

    def test_pyqgis_with_special_chars_in_password(self, schema, db_config):
        cfg = {**db_config, "password": "s3cr3t!@#$"}
        code = generate_pyqgis(schema, cfg)
        assert "s3cr3t!@#$" not in code

    def test_arcpy_with_special_chars_in_password(self, schema, db_config):
        cfg = {**db_config, "password": "s3cr3t!@#$"}
        code = generate_arcpy(schema, cfg)
        assert "s3cr3t!@#$" not in code


# ---------------------------------------------------------------------------
# floor_ceiling operation generates syntactically valid Python
# ---------------------------------------------------------------------------

class TestFloorCeilingOp:
    """The floor_ceiling PyQGIS operation must produce parseable Python."""

    def _floor_ceiling_lines(self, schema):
        cols = schema["layers"][0]["columns"]
        return _pyqgis_op_blocks("parcels", "parcels", cols, {"floor_ceiling"})

    def test_generates_lines(self, schema):
        lines = self._floor_ceiling_lines(schema)
        assert len(lines) > 0

    def test_output_is_valid_python(self, schema):
        lines = self._floor_ceiling_lines(schema)
        # Strip the 4-space indent so we can compile as a module
        src = "\n".join(ln[4:] if ln.startswith("    ") else ln for ln in lines)
        # compile() raises SyntaxError if the generated code is malformed
        compile(src, "<floor_ceiling>", "exec")

    def test_base_field_variable_referenced(self, schema):
        lines = self._floor_ceiling_lines(schema)
        joined = "\n".join(lines)
        assert "_BASE_FIELD_parcels" in joined

    def test_roof_field_variable_referenced(self, schema):
        lines = self._floor_ceiling_lines(schema)
        joined = "\n".join(lines)
        assert "_ROOF_FIELD_parcels" in joined

    def test_expression_uses_f_string_not_format(self, schema):
        lines = self._floor_ceiling_lines(schema)
        joined = "\n".join(lines)
        # Must use f-string interpolation, not the old .format() workaround
        assert ".format(" not in joined


# ---------------------------------------------------------------------------
# Empty-schema edge cases for generate_pyqgis and generate_arcpy
# ---------------------------------------------------------------------------

class TestEmptySchemaGenerators:
    _EMPTY = {"database": "test_db", "layer_count": 0, "layers": []}

    def test_pyqgis_empty_schema_returns_string(self, db_config):
        code = generate_pyqgis(self._EMPTY, db_config)
        assert isinstance(code, str)

    def test_pyqgis_empty_schema_has_init_block(self, db_config):
        code = generate_pyqgis(self._EMPTY, db_config)
        assert "QgsApplication" in code

    def test_arcpy_empty_schema_returns_string(self, db_config):
        code = generate_arcpy(self._EMPTY, db_config)
        assert isinstance(code, str)

    def test_arcpy_empty_schema_has_import(self, db_config):
        code = generate_arcpy(self._EMPTY, db_config)
        assert "import arcpy" in code
