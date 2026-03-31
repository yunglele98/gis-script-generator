"""Tests for gis_codegen.cli — argument parsing and config resolution (no DB required)."""

import argparse

import pytest

from gis_codegen.cli import (
    FALLBACK_DB,
    build_parser,
    find_config_file,
    resolve_db_config,
    resolve_defaults,
)


# ---------------------------------------------------------------------------
# build_parser
# ---------------------------------------------------------------------------

class TestBuildParser:
    def test_returns_argument_parser(self):
        p = build_parser()
        assert isinstance(p, argparse.ArgumentParser)

    def test_platform_choices(self):
        p = build_parser()
        args = p.parse_args(["--platform", "pyqgis"])
        assert args.platform == "pyqgis"

    def test_invalid_platform_rejected(self):
        p = build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["--platform", "not_a_platform"])

    def test_all_connection_flags(self):
        p = build_parser()
        args = p.parse_args([
            "--host", "db.example.com",
            "--port", "9999",
            "--dbname", "geo",
            "--user", "admin",
            "--password", "secret",
        ])
        assert args.host == "db.example.com"
        assert args.port == 9999
        assert args.dbname == "geo"
        assert args.user == "admin"
        assert args.password == "secret"

    def test_defaults_are_none(self):
        p = build_parser()
        args = p.parse_args([])
        assert args.host is None
        assert args.port is None
        assert args.dbname is None
        assert args.platform is None
        assert args.operations is None

    def test_repeatable_op_flag(self):
        p = build_parser()
        args = p.parse_args(["--op", "buffer", "--op", "clip"])
        assert args.operations == ["buffer", "clip"]

    def test_invalid_op_rejected(self):
        p = build_parser()
        with pytest.raises(SystemExit):
            p.parse_args(["--op", "not_an_operation"])

    def test_repeatable_layer_flag(self):
        p = build_parser()
        args = p.parse_args(["--layer", "public.parcels", "--layer", "public.roads"])
        assert args.layers == ["public.parcels", "public.roads"]

    def test_list_layers_flag(self):
        p = build_parser()
        args = p.parse_args(["--list-layers"])
        assert args.list_layers is True

    def test_output_flag(self):
        p = build_parser()
        args = p.parse_args(["-o", "out.py"])
        assert args.output == "out.py"


# ---------------------------------------------------------------------------
# resolve_db_config
# ---------------------------------------------------------------------------

class TestResolveDbConfig:
    def _ns(self, **kwargs):
        """Build a Namespace with all DB fields defaulting to None."""
        defaults = dict(host=None, port=None, dbname=None, user=None, password=None)
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_cli_flags_win(self):
        args = self._ns(host="cli-host", port=1234, dbname="cli-db",
                        user="cli-user", password="cli-pass")
        result = resolve_db_config(args, {})
        assert result["host"] == "cli-host"
        assert result["port"] == 1234
        assert result["password"] == "cli-pass"

    def test_config_file_values(self):
        args = self._ns(password="p")
        config = {"database": {"host": "cfg-host", "port": 9999, "dbname": "cfg-db"}}
        result = resolve_db_config(args, config)
        assert result["host"] == "cfg-host"
        assert result["port"] == 9999
        assert result["dbname"] == "cfg-db"

    def test_cli_overrides_config(self):
        args = self._ns(host="cli-host", password="p")
        config = {"database": {"host": "cfg-host"}}
        result = resolve_db_config(args, config)
        assert result["host"] == "cli-host"

    def test_env_vars_used(self, monkeypatch):
        monkeypatch.setenv("PGHOST", "env-host")
        monkeypatch.setenv("PGPORT", "7777")
        monkeypatch.setenv("PGPASSWORD", "env-pass")
        args = self._ns()
        result = resolve_db_config(args, {})
        assert result["host"] == "env-host"
        assert result["port"] == 7777
        assert result["password"] == "env-pass"

    def test_cli_overrides_env(self, monkeypatch):
        monkeypatch.setenv("PGHOST", "env-host")
        monkeypatch.setenv("PGPASSWORD", "env-pass")
        args = self._ns(host="cli-host", password="cli-pass")
        result = resolve_db_config(args, {})
        assert result["host"] == "cli-host"
        assert result["password"] == "cli-pass"

    def test_fallback_defaults(self, monkeypatch):
        monkeypatch.delenv("PGHOST", raising=False)
        monkeypatch.delenv("PGPORT", raising=False)
        monkeypatch.delenv("PGDATABASE", raising=False)
        monkeypatch.delenv("PGUSER", raising=False)
        args = self._ns(password="p")
        result = resolve_db_config(args, {})
        assert result["host"] == FALLBACK_DB["host"]
        assert result["port"] == FALLBACK_DB["port"]
        assert result["dbname"] == FALLBACK_DB["dbname"]
        assert result["user"] == FALLBACK_DB["user"]

    def test_no_password_exits(self, monkeypatch):
        monkeypatch.delenv("PGPASSWORD", raising=False)
        args = self._ns()
        with pytest.raises(SystemExit):
            resolve_db_config(args, {})


# ---------------------------------------------------------------------------
# resolve_defaults
# ---------------------------------------------------------------------------

class TestResolveDefaults:
    def test_config_fills_unset_platform(self):
        args = argparse.Namespace(
            platform=None, schema_filter=None,
            no_row_counts=False, output=None, save_schema=None,
        )
        config = {"defaults": {"platform": "arcpy"}}
        result = resolve_defaults(args, config)
        assert result.platform == "arcpy"

    def test_cli_overrides_config_platform(self):
        args = argparse.Namespace(
            platform="pyqgis", schema_filter=None,
            no_row_counts=False, output=None, save_schema=None,
        )
        config = {"defaults": {"platform": "arcpy"}}
        result = resolve_defaults(args, config)
        assert result.platform == "pyqgis"

    def test_empty_config_leaves_args_unchanged(self):
        args = argparse.Namespace(
            platform="deck", schema_filter="public",
            no_row_counts=True, output="out.py", save_schema=None,
        )
        result = resolve_defaults(args, {})
        assert result.platform == "deck"
        assert result.schema_filter == "public"
        assert result.output == "out.py"

    def test_config_fills_multiple_fields(self):
        args = argparse.Namespace(
            platform=None, schema_filter=None,
            no_row_counts=False, output=None, save_schema=None,
        )
        config = {"defaults": {
            "platform": "folium",
            "schema_filter": "staging",
            "output": "map.py",
        }}
        result = resolve_defaults(args, config)
        assert result.platform == "folium"
        assert result.schema_filter == "staging"
        assert result.output == "map.py"


# ---------------------------------------------------------------------------
# find_config_file
# ---------------------------------------------------------------------------

class TestFindConfigFile:
    def test_explicit_path_returned(self, tmp_path):
        cfg = tmp_path / "my_config.toml"
        cfg.write_text("[database]\nhost = 'x'\n")
        assert find_config_file(str(cfg)) == cfg

    def test_explicit_missing_exits(self):
        with pytest.raises(SystemExit):
            find_config_file("/nonexistent/config.toml")

    def test_env_var_path(self, tmp_path, monkeypatch):
        cfg = tmp_path / "env_config.toml"
        cfg.write_text("[database]\n")
        monkeypatch.setenv("GIS_CODEGEN_CONFIG", str(cfg))
        assert find_config_file(None) == cfg

    def test_env_var_missing_exits(self, monkeypatch):
        monkeypatch.setenv("GIS_CODEGEN_CONFIG", "/nonexistent/env_config.toml")
        with pytest.raises(SystemExit):
            find_config_file(None)

    def test_none_when_no_config_found(self, monkeypatch, tmp_path):
        monkeypatch.delenv("GIS_CODEGEN_CONFIG", raising=False)
        monkeypatch.chdir(tmp_path)
        assert find_config_file(None) is None
