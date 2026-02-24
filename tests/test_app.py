"""Tests for gis_codegen.app Flask web UI."""

import pytest
from unittest.mock import patch, MagicMock

from gis_codegen.app import app as flask_app


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


def _post(client, platform="pyqgis", **overrides):
    """Helper: POST to /generate with sensible defaults."""
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
        for p in ["pyqgis", "arcpy", "folium", "kepler", "deck", "export", "qgs", "pyt"]:
            assert p in html


# ---------------------------------------------------------------------------
# POST /generate — happy paths
# ---------------------------------------------------------------------------

class TestGenerateHappy:
    def test_pyqgis_returns_attachment(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post(client, platform="pyqgis")
        assert r.status_code == 200
        assert "attachment" in r.headers["Content-Disposition"]
        assert ".py" in r.headers["Content-Disposition"]

    def test_qgs_returns_xml_attachment(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post(client, platform="qgs")
        assert r.status_code == 200
        assert ".qgs" in r.headers["Content-Disposition"]
        assert "<!DOCTYPE qgis" in r.data.decode()

    def test_pyt_returns_py_attachment(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post(client, platform="pyt")
        assert r.status_code == 200
        assert ".pyt" in r.headers["Content-Disposition"]
        assert "class Toolbox:" in r.data.decode()

    def test_schema_filter_applied(self, client, mock_schema):
        with patch("gis_codegen.app.connect"), \
             patch("gis_codegen.app.extract_schema", return_value=mock_schema):
            r = _post(client, platform="pyqgis", schema_filter="public")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /generate — error paths
# ---------------------------------------------------------------------------

class TestGenerateErrors:
    def test_invalid_port_returns_400(self, client):
        r = _post(client, port="not_a_number")
        assert r.status_code == 400
        assert b"Port must be an integer" in r.data

    def test_connection_error_returns_400(self, client):
        with patch("gis_codegen.app.connect", side_effect=Exception("refused")):
            r = _post(client)
        assert r.status_code == 400
        assert b"Connection error" in r.data

    def test_error_re_renders_form(self, client):
        with patch("gis_codegen.app.connect", side_effect=Exception("refused")):
            r = _post(client)
        # The response should still contain the form
        assert b'name="platform"' in r.data
