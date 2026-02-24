"""Tests for gis_codegen.catalogue module."""

import json
import pytest
from gis_codegen.catalogue import (
    VALID_STATUSES,
    _arcpy_categorized_block,
    _arcpy_graduated_block,
    _arcpy_heatmap_block,
    _arcpy_network_line_block,
    _arcpy_points_polygons_block,
    _arcpy_symbology_block,
    _best_field,
    _categorized_block,
    _graduated_block,
    _heatmap_block,
    _network_line_block,
    _points_polygons_block,
    _symbology_block,
    generate_map_arcpy,
    generate_map_pyqgis,
    load_catalogue,
    load_schema,
)


# ---------------------------------------------------------------------------
# load_catalogue
# ---------------------------------------------------------------------------

class TestLoadCatalogue:
    def test_returns_list(self, tmp_catalogue):
        maps = load_catalogue(tmp_catalogue)
        assert isinstance(maps, list)

    def test_correct_count(self, tmp_catalogue):
        # M07 have+Vector, M03 partial+Vector, M44 have+Raster/Vector → 3
        maps = load_catalogue(tmp_catalogue)
        assert len(maps) == 3

    def test_includes_vector_have(self, tmp_catalogue):
        ids = {m["map_id"] for m in load_catalogue(tmp_catalogue)}
        assert "M07" in ids

    def test_includes_vector_partial(self, tmp_catalogue):
        ids = {m["map_id"] for m in load_catalogue(tmp_catalogue)}
        assert "M03" in ids

    def test_includes_raster_vector_have(self, tmp_catalogue):
        ids = {m["map_id"] for m in load_catalogue(tmp_catalogue)}
        assert "M44" in ids

    def test_excludes_raster_only(self, tmp_catalogue):
        ids = {m["map_id"] for m in load_catalogue(tmp_catalogue)}
        assert "M17" not in ids

    def test_excludes_vector_todo(self, tmp_catalogue):
        ids = {m["map_id"] for m in load_catalogue(tmp_catalogue)}
        assert "M10" not in ids

    def test_map_dicts_have_expected_keys(self, tmp_catalogue):
        required = {"map_id", "short_name", "status", "spatial_layer_type", "symbology_type"}
        for m in load_catalogue(tmp_catalogue):
            assert required.issubset(set(m.keys()))

    def test_valid_statuses_constant(self):
        assert "have" in VALID_STATUSES
        assert "partial" in VALID_STATUSES
        assert "todo" not in VALID_STATUSES
        assert "raster" not in VALID_STATUSES


# ---------------------------------------------------------------------------
# Individual renderer block builders
# ---------------------------------------------------------------------------

class TestGraduatedBlock:
    def test_references_var_in_output(self):
        joined = "\n".join(_graduated_block("parcels", "height"))
        assert "lyr_parcels" in joined
        assert "GRAD_FIELD_parcels" in joined

    def test_field_hint_quoted(self):
        joined = "\n".join(_graduated_block("parcels", "height"))
        assert '"height"' in joined

    def test_default_n_classes(self):
        joined = "\n".join(_graduated_block("parcels", "height"))
        assert "5" in joined

    def test_custom_n_classes(self):
        joined = "\n".join(_graduated_block("parcels", "height", n_classes=7))
        assert "7" in joined

    def test_custom_ramp(self):
        joined = "\n".join(_graduated_block("parcels", "height", ramp="Blues"))
        assert "Blues" in joined

    def test_update_classes_call(self):
        joined = "\n".join(_graduated_block("parcels", "height"))
        assert "updateClasses" in joined

    def test_trigger_repaint(self):
        joined = "\n".join(_graduated_block("parcels", "height"))
        assert "triggerRepaint" in joined


class TestCategorizedBlock:
    def test_references_var(self):
        joined = "\n".join(_categorized_block("roads", "road_type", "usage"))
        assert "lyr_roads" in joined
        assert "CAT_FIELD_roads" in joined

    def test_classification_in_comment(self):
        joined = "\n".join(_categorized_block("roads", "road_type", "usage classes"))
        assert "usage classes" in joined

    def test_unique_values_call(self):
        joined = "\n".join(_categorized_block("roads", "road_type", ""))
        assert "uniqueValues" in joined

    def test_update_color_ramp(self):
        joined = "\n".join(_categorized_block("roads", "road_type", ""))
        assert "updateColorRamp" in joined


class TestHeatmapBlock:
    def test_heatmap_renderer_class(self):
        joined = "\n".join(_heatmap_block("pts"))
        assert "QgsHeatmapRenderer" in joined

    def test_radius_set(self):
        joined = "\n".join(_heatmap_block("pts"))
        assert "setRadius(15)" in joined

    def test_reds_color_ramp(self):
        joined = "\n".join(_heatmap_block("pts"))
        assert "Reds" in joined

    def test_auto_maximum_value(self):
        joined = "\n".join(_heatmap_block("pts"))
        assert "setMaximumValue(0)" in joined


class TestNetworkLineBlock:
    def test_line_symbol_class(self):
        joined = "\n".join(_network_line_block("roads"))
        assert "QgsLineSymbol" in joined

    def test_net_field_placeholder(self):
        joined = "\n".join(_network_line_block("roads"))
        assert "NET_FIELD_roads" in joined
        assert "route_type" in joined

    def test_unique_values_call(self):
        joined = "\n".join(_network_line_block("roads"))
        assert "uniqueValues" in joined


class TestPointsPolygonsBlock:
    def test_single_symbol_renderer(self):
        joined = "\n".join(_points_polygons_block("sites"))
        assert "QgsSingleSymbolRenderer" in joined

    def test_default_symbol(self):
        joined = "\n".join(_points_polygons_block("sites"))
        assert "defaultSymbol" in joined

    def test_trigger_repaint(self):
        joined = "\n".join(_points_polygons_block("sites"))
        assert "triggerRepaint" in joined


# ---------------------------------------------------------------------------
# _symbology_block dispatch
# ---------------------------------------------------------------------------

class TestSymbologyBlockDispatch:
    def _map(self, stype, classif="", layer_type="Vector"):
        return {
            "symbology_type": stype,
            "classification": classif,
            "spatial_layer_type": layer_type,
        }

    def _joined(self, stype, classif="", layer_type="Vector"):
        return "\n".join(_symbology_block("lyr", self._map(stype, classif, layer_type)))

    def test_heatmap_keyword(self):
        code = self._joined("choroplèthe + heatmap")
        assert "QgsHeatmapRenderer" in code

    def test_densite_keyword(self):
        code = self._joined("points + densité")
        assert "QgsHeatmapRenderer" in code

    def test_graduated_choroplèthe_dégradé(self):
        code = self._joined("choroplèthe (dégradé)")
        assert "QgsGraduatedSymbolRenderer" in code

    def test_categorized_choroplèthe_catégoriel(self):
        code = self._joined("choroplèthe catégoriel")
        assert "QgsCategorizedSymbolRenderer" in code

    def test_graduated_not_categorized(self):
        code = self._joined("choroplèthe (dégradé)")
        assert "QgsCategorizedSymbolRenderer" not in code

    def test_réseau_network(self):
        code = self._joined("réseau")
        assert "QgsLineSymbol" in code

    def test_network_english_keyword(self):
        code = self._joined("network lines")
        assert "QgsLineSymbol" in code

    def test_points_polygones_dispatch(self):
        code = self._joined("points/polygones")
        assert "QgsSingleSymbolRenderer" in code

    def test_unknown_symbology_todo_comment(self):
        code = self._joined("something_completely_unknown")
        assert "TODO: configure renderer" in code

    def test_header_comment_always_present(self):
        lines = _symbology_block("lyr", self._map("choroplèthe (dégradé)"))
        assert any("Symbology" in ln for ln in lines)

    def test_header_shows_symbology_type(self):
        lines = _symbology_block("lyr", self._map("my-symbology-type"))
        assert any("my-symbology-type" in ln for ln in lines)


# ---------------------------------------------------------------------------
# generate_map_pyqgis
# ---------------------------------------------------------------------------

class TestGenerateMapPyqgis:
    def test_returns_string(self, map_entry, db_config):
        assert isinstance(generate_map_pyqgis(map_entry, db_config), str)

    def test_docstring_map_id(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert "Map ID    : M07" in code

    def test_docstring_title(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert map_entry["title"] in code

    def test_docstring_status_owner(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert "Status    : have" in code
        assert "Owner: Liam" in code

    def test_short_name_used_as_table(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert f'"public", "{map_entry["short_name"]}"' in code

    def test_pgpassword_env_used(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_no_hardcoded_password(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        # db_config has a password, but generate_map_pyqgis should NOT embed it
        assert db_config["password"] not in code

    def test_db_host_in_output(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert f'"{db_config["host"]}"' in code

    def test_validation_checks_rendered(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        # validation_checks = "valeurs nulles, plausibilité niveaux, palette lisible"
        assert "# [ ] valeurs nulles" in code
        assert "# [ ] plausibilité niveaux" in code
        assert "# [ ] palette lisible" in code

    def test_export_stub_contains_layout_name(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert "M07_layout" in code
        assert "QgsLayoutExporter" in code

    def test_no_raster_note_for_vector_only(self, map_entry, db_config):
        # map_entry has spatial_layer_type = "Vector"
        code = generate_map_pyqgis(map_entry, db_config)
        assert "Raster component" not in code

    def test_raster_note_present_for_raster_vector(self, db_config):
        m = {
            "map_id": "M44",
            "title": "Canopée",
            "short_name": "canopee_test",
            "theme": "Environnement",
            "subtheme": "Végétation",
            "objective": "obj",
            "key_questions": "q",
            "key_indicators": "i",
            "study_scale": "Quartier",
            "unit_of_analysis": "raster + points",
            "classification": "N/A",
            "data_sources": "Ville",
            "data_vintage": "2024",
            "spatial_layer_type": "Raster/Vector",
            "processing_steps": "overlay",
            "symbology_type": "choroplèthe + points",
            "status": "have",
            "owner": "Liam",
            "priority": "High",
            "effort": "M",
            "dependencies": None,
            "deliverable_format": "Layout PDF",
            "validation_checks": "check",
            "risks_limitations": "risk",
        }
        code = generate_map_pyqgis(m, db_config)
        assert "Raster component" in code
        assert "QgsRasterLayer" in code

    def test_qgis_init_and_exit(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert "qgs.initQgis()" in code
        assert "qgs.exitQgis()" in code

    def test_section_header_comment(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        # e.g. "# M07 — hauteurs_etages_degrade"
        assert "# M07" in code
        assert map_entry["short_name"] in code

    def test_layer_valid_check_present(self, map_entry, db_config):
        code = generate_map_pyqgis(map_entry, db_config)
        assert "isValid()" in code


# ---------------------------------------------------------------------------
# ArcPy renderer block builders
# ---------------------------------------------------------------------------

class TestArcpyGraduatedBlock:
    def test_references_var(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert "lyr_parcels" in joined
        assert "GRAD_FIELD_parcels" in joined

    def test_field_hint_quoted(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert '"height"' in joined

    def test_graduated_colors_renderer(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert "GraduatedColorsRenderer" in joined

    def test_classification_field_set(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert "classificationField" in joined

    def test_break_count_default(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert "breakCount = 5" in joined

    def test_break_count_custom(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height", n_classes=7))
        assert "breakCount = 7" in joined

    def test_symbology_assigned_back(self):
        joined = "\n".join(_arcpy_graduated_block("parcels", "height"))
        assert "lyr_parcels.symbology = sym_parcels" in joined


class TestArcpyCategorizedBlock:
    def test_references_var(self):
        joined = "\n".join(_arcpy_categorized_block("roads", "road_type", "usage"))
        assert "lyr_roads" in joined
        assert "CAT_FIELD_roads" in joined

    def test_unique_value_renderer(self):
        joined = "\n".join(_arcpy_categorized_block("roads", "road_type", "usage"))
        assert "UniqueValueRenderer" in joined

    def test_fields_set(self):
        joined = "\n".join(_arcpy_categorized_block("roads", "road_type", "usage"))
        assert "renderer.fields" in joined

    def test_classification_in_comment(self):
        joined = "\n".join(_arcpy_categorized_block("roads", "road_type", "usage classes"))
        assert "usage classes" in joined

    def test_symbology_assigned_back(self):
        joined = "\n".join(_arcpy_categorized_block("roads", "road_type", ""))
        assert "lyr_roads.symbology = sym_roads" in joined


class TestArcpyHeatmapBlock:
    def test_heat_map_renderer(self):
        joined = "\n".join(_arcpy_heatmap_block("pts"))
        assert "HeatMapRenderer" in joined

    def test_requires_arcgis_pro_note(self):
        joined = "\n".join(_arcpy_heatmap_block("pts"))
        assert "ArcGIS Pro" in joined

    def test_symbology_assigned_back(self):
        joined = "\n".join(_arcpy_heatmap_block("pts"))
        assert "lyr_pts.symbology = sym_pts" in joined


class TestArcpyNetworkLineBlock:
    def test_unique_value_renderer(self):
        joined = "\n".join(_arcpy_network_line_block("roads"))
        assert "UniqueValueRenderer" in joined

    def test_net_field_placeholder(self):
        joined = "\n".join(_arcpy_network_line_block("roads"))
        assert "NET_FIELD_roads" in joined
        assert "route_type" in joined

    def test_symbology_assigned_back(self):
        joined = "\n".join(_arcpy_network_line_block("roads"))
        assert "lyr_roads.symbology = sym_roads" in joined


class TestArcpyPointsPolygonsBlock:
    def test_simple_renderer(self):
        joined = "\n".join(_arcpy_points_polygons_block("sites"))
        assert "SimpleRenderer" in joined

    def test_symbology_assigned_back(self):
        joined = "\n".join(_arcpy_points_polygons_block("sites"))
        assert "lyr_sites.symbology = sym_sites" in joined

    def test_todo_note_present(self):
        joined = "\n".join(_arcpy_points_polygons_block("sites"))
        assert "TODO" in joined


# ---------------------------------------------------------------------------
# _arcpy_symbology_block dispatch
# ---------------------------------------------------------------------------

class TestArcpySymbologyBlockDispatch:
    def _map(self, stype, classif=""):
        return {"symbology_type": stype, "classification": classif,
                "spatial_layer_type": "Vector"}

    def _joined(self, stype, classif=""):
        return "\n".join(_arcpy_symbology_block("lyr", self._map(stype, classif)))

    def test_heatmap_keyword(self):
        assert "HeatMapRenderer" in self._joined("choroplèthe + heatmap")

    def test_densite_keyword(self):
        assert "HeatMapRenderer" in self._joined("points + densité")

    def test_graduated_choroplete_degrade(self):
        assert "GraduatedColorsRenderer" in self._joined("choroplèthe (dégradé)")

    def test_categorized_choroplete_categoriel(self):
        assert "UniqueValueRenderer" in self._joined("choroplèthe catégoriel")

    def test_graduated_not_categorized(self):
        code = self._joined("choroplèthe (dégradé)")
        assert "UniqueValueRenderer" not in code

    def test_reseau_network(self):
        code = self._joined("réseau")
        assert "UniqueValueRenderer" in code
        assert "NET_FIELD" in code

    def test_network_english(self):
        assert "UniqueValueRenderer" in self._joined("network lines")

    def test_points_polygones_dispatch(self):
        assert "SimpleRenderer" in self._joined("points/polygones")

    def test_unknown_todo_comment(self):
        assert "TODO: configure renderer" in self._joined("something_unknown")

    def test_header_comment_present(self):
        lines = _arcpy_symbology_block("lyr", self._map("choroplèthe (dégradé)"))
        assert any("Symbology" in ln for ln in lines)


# ---------------------------------------------------------------------------
# generate_map_arcpy
# ---------------------------------------------------------------------------

_RASTER_VECTOR_MAP = {
    "map_id": "M44",
    "title": "Canopée",
    "short_name": "canopee_test",
    "theme": "Environnement",
    "subtheme": "Végétation",
    "objective": "obj",
    "key_questions": "q",
    "key_indicators": "i",
    "study_scale": "Quartier",
    "unit_of_analysis": "raster + points",
    "classification": "N/A",
    "data_sources": "Ville",
    "data_vintage": "2024",
    "spatial_layer_type": "Raster/Vector",
    "processing_steps": "overlay",
    "symbology_type": "choroplèthe + points",
    "status": "have",
    "owner": "Liam",
    "priority": "High",
    "effort": "M",
    "dependencies": None,
    "deliverable_format": "Layout PDF",
    "validation_checks": "check1, check2",
    "risks_limitations": "risk",
}


class TestGenerateMapArcpy:
    def test_returns_string(self, map_entry, db_config):
        assert isinstance(generate_map_arcpy(map_entry, db_config), str)

    def test_imports_arcpy(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "import arcpy" in code
        assert "import tempfile" in code

    def test_docstring_map_id(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "Map ID    : M07" in code

    def test_docstring_title(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert map_entry["title"] in code

    def test_docstring_status_owner(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "Status    : have" in code
        assert "Owner: Liam" in code

    def test_sde_connection_block(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "CreateDatabaseConnection" in code
        assert "SDE_FILE" in code
        assert "POSTGRESQL" in code

    def test_fc_path_uses_short_name(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert f'"public.{map_entry["short_name"]}"' in code

    def test_arcpy_exists_check(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "arcpy.Exists" in code

    def test_arcpy_mp_project_setup(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "arcpy.mp.ArcGISProject" in code
        assert "listMaps" in code
        assert "addDataFromPath" in code

    def test_aprx_save_called(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "aprx.save()" in code

    def test_pgpassword_env_used(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert 'os.environ["PGPASSWORD"]' in code

    def test_no_hardcoded_password(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert db_config["password"] not in code

    def test_db_host_in_output(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert f'"{db_config["host"]}"' in code

    def test_validation_checks_rendered(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "# [ ] valeurs nulles" in code
        assert "# [ ] plausibilité niveaux" in code
        assert "# [ ] palette lisible" in code

    def test_export_stub_contains_layout_name(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "M07_layout" in code
        assert "exportToPDF" in code

    def test_no_raster_note_for_vector_only(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "Raster component" not in code

    def test_raster_note_for_raster_vector(self, db_config):
        code = generate_map_arcpy(_RASTER_VECTOR_MAP, db_config)
        assert "Raster component" in code
        assert "addDataFromPath" in code  # arcpy version uses addDataFromPath for raster too

    def test_section_header_comment(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "# M07" in code
        assert map_entry["short_name"] in code

    def test_graduated_symbology_for_m07(self, map_entry, db_config):
        # M07 has symbology_type "choroplèthe (dégradé)" → GraduatedColorsRenderer
        code = generate_map_arcpy(map_entry, db_config)
        assert "GraduatedColorsRenderer" in code

    def test_current_aprx_default(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert '"CURRENT"' in code

    def test_no_qgis_imports(self, map_entry, db_config):
        code = generate_map_arcpy(map_entry, db_config)
        assert "qgis" not in code.lower()
        assert "QgsApplication" not in code


# ---------------------------------------------------------------------------
# _best_field  (schema field-name resolver)
# ---------------------------------------------------------------------------

def _make_layer(columns, pks=None, geom_col="geom"):
    return {
        "geometry": {"column": geom_col},
        "primary_keys": pks or [],
        "columns": columns,
    }


class TestBestField:
    def test_returns_value_when_no_layer_info(self):
        assert _best_field(None) == "value"

    def test_returns_value_when_no_columns(self):
        assert _best_field(_make_layer([])) == "value"

    def test_picks_integer_for_numeric(self):
        cols = [{"name": "pop", "data_type": "integer"}]
        assert _best_field(_make_layer(cols), numeric=True) == "pop"

    def test_picks_double_precision_for_numeric(self):
        cols = [{"name": "area", "data_type": "double precision"}]
        assert _best_field(_make_layer(cols), numeric=True) == "area"

    def test_picks_text_for_non_numeric(self):
        cols = [{"name": "category", "data_type": "text"}]
        assert _best_field(_make_layer(cols), numeric=False) == "category"

    def test_picks_character_varying_for_non_numeric(self):
        cols = [{"name": "label", "data_type": "character varying"}]
        assert _best_field(_make_layer(cols), numeric=False) == "label"

    def test_skips_geom_column(self):
        cols = [
            {"name": "geom", "data_type": "integer"},  # geom col with numeric type — skip
            {"name": "floors", "data_type": "integer"},
        ]
        assert _best_field(_make_layer(cols)) == "floors"

    def test_skips_primary_key(self):
        cols = [
            {"name": "id", "data_type": "integer"},
            {"name": "height", "data_type": "double precision"},
        ]
        assert _best_field(_make_layer(cols, pks=["id"])) == "height"

    def test_falls_back_to_value_when_no_numeric_match(self):
        cols = [{"name": "label", "data_type": "text"}]
        assert _best_field(_make_layer(cols), numeric=True) == "value"

    def test_falls_back_to_value_when_no_text_match(self):
        cols = [{"name": "floors", "data_type": "integer"}]
        assert _best_field(_make_layer(cols), numeric=False) == "value"


# ---------------------------------------------------------------------------
# load_schema
# ---------------------------------------------------------------------------

class TestLoadSchema:
    def test_returns_dict_keyed_by_table(self, tmp_path):
        data = {
            "database": "testdb", "host": "localhost",
            "layers": [
                {"table": "parcels", "schema": "public",
                 "geometry": {"column": "geom"}, "primary_keys": [], "columns": []},
                {"table": "roads", "schema": "public",
                 "geometry": {"column": "geom"}, "primary_keys": [], "columns": []},
            ]
        }
        p = tmp_path / "schema.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_schema(str(p))
        assert "parcels" in result
        assert "roads" in result

    def test_layer_dict_preserved(self, tmp_path):
        layer = {"table": "parcels", "schema": "public",
                 "geometry": {"column": "geom"}, "primary_keys": ["id"],
                 "columns": [{"name": "id", "data_type": "integer"}]}
        data = {"layers": [layer]}
        p = tmp_path / "schema.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_schema(str(p))
        assert result["parcels"]["primary_keys"] == ["id"]

    def test_empty_layers(self, tmp_path):
        p = tmp_path / "schema.json"
        p.write_text(json.dumps({"layers": []}), encoding="utf-8")
        assert load_schema(str(p)) == {}


# ---------------------------------------------------------------------------
# generate_map_pyqgis with ops and layer_info
# ---------------------------------------------------------------------------

class TestGenerateMapPyqgisOps:
    @pytest.fixture
    def m(self, map_entry):
        return map_entry

    @pytest.fixture
    def dc(self, db_config):
        return db_config

    def test_buffer_op_injected(self, m, dc):
        code = generate_map_pyqgis(m, dc, ops=["buffer"])
        assert "native:buffer" in code

    def test_dissolve_op_injected(self, m, dc):
        code = generate_map_pyqgis(m, dc, ops=["dissolve"])
        assert "native:dissolve" in code

    def test_multiple_ops_all_present(self, m, dc):
        code = generate_map_pyqgis(m, dc, ops=["buffer", "reproject"])
        assert "native:buffer" in code
        assert "native:reprojectlayer" in code

    def test_no_ops_leaves_no_op_code(self, m, dc):
        code = generate_map_pyqgis(m, dc, ops=[])
        assert "native:buffer" not in code

    def test_ops_none_leaves_no_op_code(self, m, dc):
        code = generate_map_pyqgis(m, dc)
        assert "native:buffer" not in code

    def test_layer_info_enriches_field_hint(self, m, dc):
        # map_entry has no classification set; layer_info has a numeric column
        # symbology_type "choroplèthe (dégradé)" -> graduated -> prefer numeric
        m_no_classif = {**m, "classification": None}
        layer_info = _make_layer(
            [{"name": "nb_etages", "data_type": "integer"}], pks=[]
        )
        code = generate_map_pyqgis(m_no_classif, dc, layer_info=layer_info)
        assert '"nb_etages"' in code

    def test_layer_info_not_used_when_classification_set(self, m, dc):
        # if catalogue already has a classification, it should win
        m_with = {**m, "classification": "my_field"}
        layer_info = _make_layer(
            [{"name": "other_field", "data_type": "integer"}], pks=[]
        )
        code = generate_map_pyqgis(m_with, dc, layer_info=layer_info)
        assert '"my_field"' in code

    def test_op_columns_used_from_layer_info(self, m, dc):
        layer_info = _make_layer(
            [{"name": "area_m2", "data_type": "double precision"}], pks=[]
        )
        code = generate_map_pyqgis(m, dc, ops=["buffer"], layer_info=layer_info)
        assert "native:buffer" in code


# ---------------------------------------------------------------------------
# generate_map_arcpy with ops and layer_info
# ---------------------------------------------------------------------------

class TestGenerateMapArcpyOps:
    @pytest.fixture
    def m(self, map_entry):
        return map_entry

    @pytest.fixture
    def dc(self, db_config):
        return db_config

    def test_buffer_op_injected(self, m, dc):
        code = generate_map_arcpy(m, dc, ops=["buffer"])
        assert "analysis.Buffer" in code

    def test_dissolve_op_injected(self, m, dc):
        code = generate_map_arcpy(m, dc, ops=["dissolve"])
        assert "management.Dissolve" in code

    def test_multiple_ops_all_present(self, m, dc):
        code = generate_map_arcpy(m, dc, ops=["buffer", "reproject"])
        assert "analysis.Buffer" in code
        assert "management.Project" in code

    def test_no_ops_leaves_no_op_code(self, m, dc):
        code = generate_map_arcpy(m, dc, ops=[])
        assert "analysis.Buffer" not in code

    def test_ops_none_leaves_no_op_code(self, m, dc):
        code = generate_map_arcpy(m, dc)
        assert "analysis.Buffer" not in code

    def test_layer_info_enriches_field_hint(self, m, dc):
        m_no_classif = {**m, "classification": None}
        layer_info = _make_layer(
            [{"name": "nb_etages", "data_type": "integer"}], pks=[]
        )
        code = generate_map_arcpy(m_no_classif, dc, layer_info=layer_info)
        assert '"nb_etages"' in code

    def test_layer_info_not_used_when_classification_set(self, m, dc):
        m_with = {**m, "classification": "my_field"}
        layer_info = _make_layer(
            [{"name": "other_field", "data_type": "integer"}], pks=[]
        )
        code = generate_map_arcpy(m_with, dc, layer_info=layer_info)
        assert '"my_field"' in code

    def test_op_block_inside_else_branch(self, m, dc):
        # buffer block should appear before aprx.save()
        code = generate_map_arcpy(m, dc, ops=["buffer"])
        buf_pos  = code.index("analysis.Buffer")
        save_pos = code.index("aprx.save()")
        assert buf_pos < save_pos
