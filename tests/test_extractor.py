"""Tests for gis_codegen.extractor module."""

import pytest
from unittest.mock import MagicMock, patch, call
from gis_codegen.extractor import (
    DB_CONFIG,
    fetch_columns,
    fetch_primary_keys,
    fetch_row_count_estimate,
    extract_schema,
)


# ---------------------------------------------------------------------------
# DB_CONFIG
# ---------------------------------------------------------------------------

class TestDbConfig:
    def test_has_required_keys(self):
        for key in ("host", "port", "dbname", "user", "password"):
            assert key in DB_CONFIG, f"DB_CONFIG missing key: {key}"

    def test_port_is_int(self):
        assert isinstance(DB_CONFIG["port"], int)

    def test_reads_pghost_from_env(self, monkeypatch):
        monkeypatch.setenv("PGHOST", "custom-server")
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["host"] == "custom-server"

    def test_reads_pgport_from_env(self, monkeypatch):
        monkeypatch.setenv("PGPORT", "5433")
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["port"] == 5433

    def test_reads_pgdatabase_from_env(self, monkeypatch):
        monkeypatch.setenv("PGDATABASE", "my_custom_db")
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["dbname"] == "my_custom_db"

    def test_reads_pguser_from_env(self, monkeypatch):
        monkeypatch.setenv("PGUSER", "custom_user")
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["user"] == "custom_user"

    def test_reads_pgpassword_from_env(self, monkeypatch):
        monkeypatch.setenv("PGPASSWORD", "s3cr3t")
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["password"] == "s3cr3t"

    def test_password_empty_by_default_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("PGPASSWORD", raising=False)
        import importlib
        import gis_codegen.extractor as ext
        importlib.reload(ext)
        assert ext.DB_CONFIG["password"] == ""


# ---------------------------------------------------------------------------
# fetch_columns
# ---------------------------------------------------------------------------

def _make_col_row(col_name, data_type, nullable="YES",
                  max_length=None, default=None):
    """Return a dict-like row as returned by RealDictCursor."""
    return {
        "column_name":             col_name,
        "data_type":               data_type,
        "is_nullable":             nullable,
        "character_maximum_length": max_length,
        "column_default":          default,
    }


class TestFetchColumns:
    def _cursor(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    def test_basic_column_structure(self):
        rows = [_make_col_row("parcel_id", "integer", "NO")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert len(result) == 1
        col = result[0]
        assert col["name"] == "parcel_id"
        assert col["data_type"] == "integer"
        assert col["nullable"] is False

    def test_nullable_yes_maps_to_true(self):
        rows = [_make_col_row("address", "character varying", "YES")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert result[0]["nullable"] is True

    def test_nullable_no_maps_to_false(self):
        rows = [_make_col_row("id", "integer", "NO")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert result[0]["nullable"] is False

    def test_max_length_included_when_set(self):
        rows = [_make_col_row("code", "character varying", max_length=20)]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert result[0].get("max_length") == 20

    def test_max_length_absent_when_none(self):
        rows = [_make_col_row("id", "integer")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert "max_length" not in result[0]

    def test_default_included_when_set(self):
        rows = [_make_col_row("active", "boolean", default="true")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert result[0]["default"] == "true"

    def test_default_absent_when_none(self):
        rows = [_make_col_row("id", "integer")]
        result = fetch_columns(self._cursor(rows), "public", "parcels")
        assert "default" not in result[0]

    def test_multiple_columns_preserved_in_order(self):
        rows = [
            _make_col_row("id",      "integer"),
            _make_col_row("name",    "text"),
            _make_col_row("active",  "boolean"),
        ]
        result = fetch_columns(self._cursor(rows), "public", "mytable")
        assert [r["name"] for r in result] == ["id", "name", "active"]

    def test_empty_table_returns_empty_list(self):
        result = fetch_columns(self._cursor([]), "public", "empty")
        assert result == []

    def test_cursor_execute_called_with_schema_and_table(self):
        cur = self._cursor([])
        fetch_columns(cur, "myschema", "mytable")
        # execute should have been called once with (schema, table, schema, table)
        cur.execute.assert_called_once()
        args = cur.execute.call_args[0]
        assert "myschema" in args[1]
        assert "mytable" in args[1]


# ---------------------------------------------------------------------------
# fetch_primary_keys
# ---------------------------------------------------------------------------

def _make_pk_row(col_name):
    return {"column_name": col_name}


class TestFetchPrimaryKeys:
    def _cursor(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        return cur

    def test_single_pk(self):
        result = fetch_primary_keys(self._cursor([_make_pk_row("id")]),
                                    "public", "parcels")
        assert result == ["id"]

    def test_composite_pk(self):
        rows = [_make_pk_row("schema_id"), _make_pk_row("table_id")]
        result = fetch_primary_keys(self._cursor(rows), "public", "mapping")
        assert result == ["schema_id", "table_id"]

    def test_no_pk_returns_empty_list(self):
        result = fetch_primary_keys(self._cursor([]), "public", "no_pk")
        assert result == []

    def test_cursor_execute_called_once(self):
        cur = self._cursor([])
        fetch_primary_keys(cur, "public", "t")
        cur.execute.assert_called_once()


# ---------------------------------------------------------------------------
# fetch_row_count_estimate
# ---------------------------------------------------------------------------

class TestFetchRowCountEstimate:
    def test_returns_estimate_value(self):
        row = {"estimate": 1234}
        cur = MagicMock()
        cur.fetchone.return_value = row
        assert fetch_row_count_estimate(cur, "public", "parcels") == 1234

    def test_returns_minus_one_when_no_row(self):
        cur = MagicMock()
        cur.fetchone.return_value = None
        assert fetch_row_count_estimate(cur, "public", "missing") == -1

    def test_returns_minus_one_on_execute_exception(self):
        cur = MagicMock()
        cur.execute.side_effect = Exception("table not found")
        assert fetch_row_count_estimate(cur, "public", "broken") == -1

    def test_returns_minus_one_on_fetchone_exception(self):
        cur = MagicMock()
        cur.fetchone.side_effect = Exception("cursor error")
        assert fetch_row_count_estimate(cur, "public", "broken") == -1


# ---------------------------------------------------------------------------
# extract_schema
# ---------------------------------------------------------------------------

def _make_mock_conn(dsn_params, spatial_rows, col_rows_per_table=None,
                    pk_rows_per_table=None):
    """
    Build a mock connection for extract_schema.

    spatial_rows      : list of dicts for fetch_spatial_layers
    col_rows_per_table: list of column-row lists, one per spatial row
    pk_rows_per_table : list of pk-row lists, one per spatial row
    """
    n = len(spatial_rows)
    col_rows_per_table = col_rows_per_table or [[] for _ in range(n)]
    pk_rows_per_table  = pk_rows_per_table  or [[] for _ in range(n)]

    # fetchall calls: 1 spatial + n columns + n pks (interleaved per layer)
    fetchall_returns = [spatial_rows]
    for cols, pks in zip(col_rows_per_table, pk_rows_per_table):
        fetchall_returns.append(cols)
        fetchall_returns.append(pks)

    mock_cur = MagicMock()
    mock_cur.__enter__ = lambda self: mock_cur
    mock_cur.__exit__ = MagicMock(return_value=False)
    mock_cur.fetchall.side_effect = fetchall_returns

    mock_conn = MagicMock()
    mock_conn.get_dsn_parameters.return_value = dsn_params
    mock_conn.cursor.return_value = mock_cur
    return mock_conn


class TestExtractSchema:
    _dsn = {"dbname": "test_db", "host": "localhost"}

    def test_empty_db_returns_correct_structure(self):
        conn = _make_mock_conn(self._dsn, [])
        result = extract_schema(conn, include_row_counts=False)
        assert result["database"] == "test_db"
        assert result["host"] == "localhost"
        assert result["layer_count"] == 0
        assert result["layers"] == []

    def test_single_layer_structure(self):
        spatial_row = {
            "schema_name": "public",
            "table_name":  "parcels",
            "geom_column": "geom",
            "geom_type":   "MULTIPOLYGON",
            "srid":        4326,
            "table_comment": None,
        }
        conn = _make_mock_conn(self._dsn, [spatial_row])
        result = extract_schema(conn, include_row_counts=False)

        assert result["layer_count"] == 1
        layer = result["layers"][0]
        assert layer["schema"] == "public"
        assert layer["table"] == "parcels"
        assert layer["qualified_name"] == "public.parcels"
        assert layer["geometry"]["column"] == "geom"
        assert layer["geometry"]["type"] == "MULTIPOLYGON"
        assert layer["geometry"]["srid"] == 4326
        assert layer["columns"] == []
        assert layer["primary_keys"] == []

    def test_layer_comment_included_when_set(self):
        spatial_row = {
            "schema_name":   "public",
            "table_name":    "roads",
            "geom_column":   "geom",
            "geom_type":     "LINESTRING",
            "srid":          4326,
            "table_comment": "Road centrelines",
        }
        conn = _make_mock_conn(self._dsn, [spatial_row])
        result = extract_schema(conn, include_row_counts=False)
        assert result["layers"][0]["comment"] == "Road centrelines"

    def test_layer_comment_absent_when_none(self):
        spatial_row = {
            "schema_name":   "public",
            "table_name":    "parcels",
            "geom_column":   "geom",
            "geom_type":     "POLYGON",
            "srid":          4326,
            "table_comment": None,
        }
        conn = _make_mock_conn(self._dsn, [spatial_row])
        result = extract_schema(conn, include_row_counts=False)
        assert "comment" not in result["layers"][0]

    def test_columns_attached_to_layer(self):
        spatial_row = {
            "schema_name": "public", "table_name": "parcels",
            "geom_column": "geom", "geom_type": "POLYGON", "srid": 4326,
            "table_comment": None,
        }
        col_rows = [
            _make_col_row("parcel_id", "integer", "NO"),
            _make_col_row("address",   "text",    "YES"),
        ]
        conn = _make_mock_conn(self._dsn, [spatial_row], col_rows_per_table=[col_rows])
        result = extract_schema(conn, include_row_counts=False)
        cols = result["layers"][0]["columns"]
        assert len(cols) == 2
        assert cols[0]["name"] == "parcel_id"
        assert cols[1]["name"] == "address"

    def test_primary_keys_attached_to_layer(self):
        spatial_row = {
            "schema_name": "public", "table_name": "parcels",
            "geom_column": "geom", "geom_type": "POLYGON", "srid": 4326,
            "table_comment": None,
        }
        pk_rows = [_make_pk_row("parcel_id")]
        conn = _make_mock_conn(self._dsn, [spatial_row], pk_rows_per_table=[pk_rows])
        result = extract_schema(conn, include_row_counts=False)
        assert result["layers"][0]["primary_keys"] == ["parcel_id"]

    def test_two_layers_both_present(self):
        rows = [
            {"schema_name": "public", "table_name": "parcels",
             "geom_column": "geom", "geom_type": "POLYGON", "srid": 4326,
             "table_comment": None},
            {"schema_name": "public", "table_name": "roads",
             "geom_column": "geom", "geom_type": "LINESTRING", "srid": 4326,
             "table_comment": None},
        ]
        conn = _make_mock_conn(self._dsn, rows)
        result = extract_schema(conn, include_row_counts=False)
        assert result["layer_count"] == 2
        tables = [l["table"] for l in result["layers"]]
        assert "parcels" in tables
        assert "roads" in tables

    def test_row_count_absent_when_include_false(self):
        spatial_row = {
            "schema_name": "public", "table_name": "parcels",
            "geom_column": "geom", "geom_type": "POLYGON", "srid": 4326,
            "table_comment": None,
        }
        conn = _make_mock_conn(self._dsn, [spatial_row])
        result = extract_schema(conn, include_row_counts=False)
        assert "row_count_estimate" not in result["layers"][0]

    def test_row_count_present_when_include_true(self):
        spatial_row = {
            "schema_name": "public", "table_name": "parcels",
            "geom_column": "geom", "geom_type": "POLYGON", "srid": 4326,
            "table_comment": None,
        }
        # When include_row_counts=True, fetch_row_count_estimate is called via fetchone
        mock_cur = MagicMock()
        mock_cur.__enter__ = lambda self: mock_cur
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchall.side_effect = [[spatial_row], [], []]   # spatial, cols, pks
        mock_cur.fetchone.return_value = {"estimate": 999}

        mock_conn = MagicMock()
        mock_conn.get_dsn_parameters.return_value = self._dsn
        mock_conn.cursor.return_value = mock_cur

        result = extract_schema(mock_conn, include_row_counts=True)
        assert result["layers"][0]["row_count_estimate"] == 999
