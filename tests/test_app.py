"""Tests for gis_codegen.app Flask web UI."""

import json

import pytest
from unittest.mock import patch

from gis_codegen.app import app as flask_app, _PLATFORMS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


@pytest.fixture
def mock_schema():
    return {
        "database":    "test_db",
        "host":        "localhost",
        "layer_count": 2,
        "layers": [
            {
                "schema":           "public",
                "table":            "parcels",
                "qualified_name":   "public.parcels",
                "geometry": {"column": "geom", "type": "MULTIPOLYGON", "srid": 4326},
                "columns": [
                    {"name": "parcel_id", "data_type": "integer",          "nullable": False},
                    {"name": "address",   "data_type": "character varying", "nullable": True},
                ],
                "primary_keys":       ["parcel_id"],
                "row_count_estimate": 100,
            },
        ],
    }


@pytest.fixture
def multi_schema_layers():
    """Schema with layers in two different PostgreSQL schemas."""
    return {
        "database":    "test_db",
        "host":        "localhost",
        "layer_count": 2,
        "layers": [
            {
                "schema":           "public",
                "table":            "parcels",
                "qualified_name":   "public.parcels",
                "geometry": {"column": "geom", "type": "MULTIPOLYGON", "srid": 4326},
                "columns": [
                    {"name": "gid", "data_type": "integer", "nullable": False},
                ],
                "primary_keys":       ["gid"],
                "row_count_estimate": 50,
            },
            {
                "schema":           "staging",
                "table":            "temp_roads",
                "qualified_name":   "staging.temp_roads",
                "geometry": {"column": "geom", "type": "LINESTRING", "srid": 4326},
                "columns": [
                    {"name": "gid", "data_type": "integer", "nullable": False},
                ],
                "primary_keys":       ["gid"],
                "row_count_estimate": 10,
            },
        ],
    }


def _post_preview(client, platform="pyqgis", **overrides):
    """Helper: POST to /preview with sensible defaults."""
    data = {
        "host":     "localhost",
        "port":     "5432",
        "dbname":   "test_db",
        "user":     "testuser",
        "password": "testpass",
        "platform": platform,
        "schema_filter": "",
        **overrides,
    }
    return client.post("/preview", data=data)


def _post_generate(client, schema, platform="pyqgis", selected_layers=None, **overrides):
    """Helper: POST to /generate with schema JSON and selected layers."""
    data = {
        "host":     "localhost",
        "port":     "5432",
        "dbname":   "test_db",
        "user":     "testuser",
        "password": "testpass",
        "platform": platform,
        "schema_json": json.dumps(schema),
        **overrides,
    }
    if selected_layers is not None:
        data["selected_layers"] = selected_layers
    else:
        data["selected_layers"] = [ly["qualified_name"] for ly in schema["layers"]]
    return client.post("/generate", data=data)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------

class TestIndex:
    def test_get_returns_200(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_form_has_platform_select(self, client):
        r = client.get("/")
        html = r.data.decode()
        assert 'name="platform"' in html

    def test_form_has_connection_fields(self, client):
        r = client.get("/")
        html = r.data.decode()
        assert 'name="host"' in html
        assert 'name="password"' in html

    def test_all_platforms_listed(self, client):
        r = client.get("/")
        html = r.data.decode()
        for p in _PLATFORMS:
            assert p in html

    def test_default_values_populated(self, client):
        r = client.get("/")
        html = r.data.decode()
        assert 'value="localhost"' in html
        assert 'value="5432"' in html

    def test_form_posts_to_preview(self, client):
        r = client.get("/")
        html = r.data.decode()
        assert 'action="/preview"' in html


# ---------------------------------------------------------------------------
# POST /preview — happy paths
# ---------------------------------------------------------------------------

class TestPreviewHappy:
    def test_preview_returns_layer_table(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        assert r.status_code == 200
        html = r.data.decode()
        assert "Select Layers" in html
        assert "public.parcels" in html

    def test_preview_has_checkboxes(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert 'name="selected_layers"' in html
        assert "checked" in html

    def test_preview_shows_geometry_info(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert "MULTIPOLYGON" in html
        assert "4326" in html

    def test_preview_shows_row_count(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert "~100" in html

    def test_preview_has_hidden_schema_json(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert 'name="schema_json"' in html

    def test_preview_has_hidden_connection_fields(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert 'name="host"' in html
        assert 'name="platform"' in html

    def test_preview_shows_layer_count(self, client, multi_schema_layers):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=multi_schema_layers):
            r = _post_preview(client)
        html = r.data.decode()
        assert "<strong>2</strong>" in html

    def test_preview_schema_filter(self, client, multi_schema_layers):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=multi_schema_layers):
            r = _post_preview(client, schema_filter="public")
        html = r.data.decode()
        assert "public.parcels" in html
        assert "staging.temp_roads" not in html

    def test_preview_has_toggle_links(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post_preview(client)
        html = r.data.decode()
        assert "Select all" in html
        assert "Select none" in html


# ---------------------------------------------------------------------------
# POST /preview — error paths
# ---------------------------------------------------------------------------

class TestPreviewErrors:
    def test_invalid_port_returns_400(self, client):
        r = _post_preview(client, port="not_a_number")
        assert r.status_code == 400
        assert b"Port must be an integer" in r.data

    def test_unknown_platform_returns_400(self, client):
        r = _post_preview(client, platform="invalid_platform")
        assert r.status_code == 400
        assert b"Unknown platform" in r.data

    def test_connection_error_returns_400(self, client):
        with patch("gis_codegen.app.connect", side_effect=Exception("refused")):
            r = _post_preview(client)
        assert r.status_code == 400
        assert b"Connection error" in r.data

    def test_extraction_error_returns_400(self, client):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", side_effect=Exception("no tables")):
            r = _post_preview(client)
        assert r.status_code == 400
        assert b"Connection error" in r.data

    def test_error_re_renders_form(self, client):
        with patch("gis_codegen.app.connect", side_effect=Exception("refused")):
            r = _post_preview(client)
        assert b'name="platform"' in r.data

    def test_error_preserves_form_values(self, client):
        with patch("gis_codegen.app.connect", side_effect=Exception("refused")):
            r = _post_preview(client, host="db.example.com", port="9999",
                              dbname="geo_db", user="admin")
        html = r.data.decode()
        assert 'value="db.example.com"' in html
        assert 'value="9999"' in html
        assert 'value="geo_db"' in html
        assert 'value="admin"' in html

    def test_invalid_port_preserves_form_values(self, client):
        r = _post_preview(client, host="myhost", port="abc", dbname="mydb")
        html = r.data.decode()
        assert 'value="myhost"' in html
        assert 'value="abc"' in html
        assert 'value="mydb"' in html


# ---------------------------------------------------------------------------
# POST /generate — happy paths
# ---------------------------------------------------------------------------

class TestGenerateHappy:
    def test_pyqgis_returns_attachment(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="pyqgis")
        assert r.status_code == 200
        assert "attachment" in r.headers["Content-Disposition"]
        assert ".py" in r.headers["Content-Disposition"]

    def test_qgs_returns_xml_attachment(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="qgs")
        assert r.status_code == 200
        assert ".qgs" in r.headers["Content-Disposition"]
        assert "<!DOCTYPE qgis" in r.data.decode()

    def test_pyt_returns_py_attachment(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="pyt")
        assert r.status_code == 200
        assert ".pyt" in r.headers["Content-Disposition"]
        assert "class Toolbox:" in r.data.decode()

    @pytest.mark.parametrize("platform", _PLATFORMS)
    def test_all_platforms_generate_200(self, client, mock_schema, platform):
        r = _post_generate(client, mock_schema, platform=platform)
        assert r.status_code == 200
        assert "attachment" in r.headers["Content-Disposition"]

    def test_filename_matches_dbname_and_platform(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="arcpy", dbname="my_db")
        assert 'my_db_arcpy.py' in r.headers["Content-Disposition"]

    def test_qgs_filename_has_qgs_extension(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="qgs", dbname="spatial")
        assert 'spatial_qgs.qgs' in r.headers["Content-Disposition"]

    def test_empty_password_accepted(self, client, mock_schema):
        r = _post_generate(client, mock_schema, password="")
        assert r.status_code == 200

    def test_selected_layers_filters_output(self, client, multi_schema_layers):
        r = _post_generate(
            client, multi_schema_layers, platform="pyqgis",
            selected_layers=["public.parcels"],
        )
        body = r.data.decode()
        assert "parcels" in body
        assert "temp_roads" not in body

    def test_all_layers_selected_includes_all(self, client, multi_schema_layers):
        r = _post_generate(
            client, multi_schema_layers, platform="pyqgis",
            selected_layers=["public.parcels", "staging.temp_roads"],
        )
        body = r.data.decode()
        assert "parcels" in body
        assert "temp_roads" in body


# ---------------------------------------------------------------------------
# POST /generate — error paths
# ---------------------------------------------------------------------------

class TestGenerateErrors:
    def test_invalid_port_returns_400(self, client, mock_schema):
        r = _post_generate(client, mock_schema, port="not_a_number")
        assert r.status_code == 400
        assert b"Port must be an integer" in r.data

    def test_unknown_platform_returns_400(self, client, mock_schema):
        r = _post_generate(client, mock_schema, platform="invalid_platform")
        assert r.status_code == 400
        assert b"Unknown platform" in r.data

    def test_missing_schema_json_returns_400(self, client):
        data = {
            "host": "localhost", "port": "5432", "dbname": "test_db",
            "user": "testuser", "password": "testpass", "platform": "pyqgis",
            "selected_layers": ["public.parcels"],
        }
        r = client.post("/generate", data=data)
        assert r.status_code == 400
        assert b"Missing schema data" in r.data

    def test_invalid_schema_json_returns_400(self, client):
        data = {
            "host": "localhost", "port": "5432", "dbname": "test_db",
            "user": "testuser", "password": "testpass", "platform": "pyqgis",
            "schema_json": "not-valid-json{{{",
            "selected_layers": ["public.parcels"],
        }
        r = client.post("/generate", data=data)
        assert r.status_code == 400
        assert b"Invalid schema data" in r.data

    def test_no_layers_selected_returns_400(self, client, mock_schema):
        data = {
            "host": "localhost", "port": "5432", "dbname": "test_db",
            "user": "testuser", "password": "testpass", "platform": "pyqgis",
            "schema_json": json.dumps(mock_schema),
            "selected_layers": ["nonexistent.table"],
        }
        r = client.post("/generate", data=data)
        assert r.status_code == 400
        assert b"No layers selected" in r.data
