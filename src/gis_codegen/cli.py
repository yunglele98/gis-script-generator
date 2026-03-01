"""
gis_codegen.py

Single-command pipeline: connect to PostGIS → extract schema → generate script.

Connection value priority (highest → lowest):
  1. CLI flags        --host, --port, --dbname, --user, --password
  2. Config file      gis_codegen.toml  (TOML)
  3. Environment      PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD
  4. Built-in defaults

Config file search order (first found wins):
  1. --config FILE
  2. $GIS_CODEGEN_CONFIG
  3. ./gis_codegen.toml
  4. ~/.config/gis_codegen/config.toml

Usage:
    python gis_codegen.py --platform pyqgis -o load_layers.py
    python gis_codegen.py --list-layers
    python gis_codegen.py --config /path/to/gis_codegen.toml --platform arcpy -o out.py
"""

import os
import sys
import json
import argparse
from pathlib import Path
from types import ModuleType

from gis_codegen.extractor import connect, extract_schema
from gis_codegen.generator import (
    generate_pyqgis, generate_arcpy,
    generate_folium, generate_kepler, generate_deck,
    generate_export, generate_qgs, generate_pyt,
    VALID_OPERATIONS,
)
from gis_codegen.layout import TemplateConfig, CompositionLayout


# ---------------------------------------------------------------------------
# TOML loader — stdlib tomllib (3.11+) with tomli fallback
# ---------------------------------------------------------------------------

def _load_toml_module() -> ModuleType | None:
    try:
        import tomllib
        return tomllib
    except ImportError:
        pass
    try:
        import tomli as tomllib
        return tomllib
    except ImportError:
        return None


TOMLLIB = _load_toml_module()


def load_toml(path: Path) -> dict:
    if TOMLLIB is None:
        print(
            "[ERROR] TOML support requires Python 3.11+ or 'tomli' package.\n"
            "        Install with: pip install tomli",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(path, "rb") as f:
        return TOMLLIB.load(f)


# ---------------------------------------------------------------------------
# Config resolution
# ---------------------------------------------------------------------------

FALLBACK_DB = {
    "host":   "localhost",
    "port":   5432,
    "dbname": "my_gis_db",
    "user":   "postgres",
    # password has no fallback — must come from CLI, config, or PGPASSWORD
}

CONFIG_SEARCH_PATHS = [
    Path("gis_codegen.toml"),
    Path.home() / ".config" / "gis_codegen" / "config.toml",
]


def find_config_file(explicit: str | None) -> Path | None:
    """Return the first config file found, or None."""
    if explicit:
        p = Path(explicit)
        if not p.exists():
            print(f"[ERROR] Config file not found: {explicit}", file=sys.stderr)
            sys.exit(1)
        return p

    env_path = os.environ.get("GIS_CODEGEN_CONFIG")
    if env_path:
        p = Path(env_path)
        if not p.exists():
            print(f"[ERROR] Config file from GIS_CODEGEN_CONFIG not found: {env_path}",
                  file=sys.stderr)
            sys.exit(1)
        return p

    for candidate in CONFIG_SEARCH_PATHS:
        if candidate.exists():
            return candidate

    return None


def resolve_db_config(cli_args: argparse.Namespace, config: dict) -> dict:
    """
    Merge connection settings with priority:
      CLI flags > config file [database] > env vars > FALLBACK_DB
    """
    file_db = config.get("database", {})

    env_db = {
        "host":     os.environ.get("PGHOST"),
        "port":     int(os.environ.get("PGPORT", 0)) or None,
        "dbname":   os.environ.get("PGDATABASE"),
        "user":     os.environ.get("PGUSER"),
        "password": os.environ.get("PGPASSWORD"),
    }

    def pick(key: str) -> str | int | None:
        cli_val = getattr(cli_args, key, None)
        if cli_val is not None:
            return cli_val
        if file_db.get(key) is not None:
            return file_db[key]
        if env_db.get(key) is not None:
            return env_db[key]
        return FALLBACK_DB.get(key)  # None for password if not set anywhere

    password = pick("password")
    if not password:
        print(
            "[ERROR] No database password supplied.\n"
            "        Provide one via: PGPASSWORD env var, config [database] password, "
            "or --password flag.",
            file=sys.stderr,
        )
        sys.exit(1)

    return {
        "host":     pick("host"),
        "port":     pick("port"),
        "dbname":   pick("dbname"),
        "user":     pick("user"),
        "password": password,
    }


def resolve_defaults(cli_args: argparse.Namespace, config: dict) -> argparse.Namespace:
    """
    Apply [defaults] section from config file to CLI args that were not set.
    CLI flags always win; config [defaults] fills in the rest.
    """
    defaults = config.get("defaults", {})

    mapping = {
        "platform":      "platform",
        "schema_filter": "schema_filter",
        "no_row_counts": "no_row_counts",
        "output":        "output",
        "save_schema":   "save_schema",
    }
    for cfg_key, arg_key in mapping.items():
        if getattr(cli_args, arg_key, None) is None or getattr(cli_args, arg_key) is False:
            val = defaults.get(cfg_key)
            if val is not None:
                setattr(cli_args, arg_key, val)

    return cli_args


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="gis_codegen",
        description="Extract PostGIS schema and generate a PyQGIS or ArcPy script.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    p.add_argument(
        "--config", metavar="FILE",
        help="Path to a TOML config file (overrides auto-discovery).",
    )

    # --- Connection (all default to None so we can detect 'not set') ---
    conn = p.add_argument_group(
        "database connection",
        "Override order: CLI flag > config [database] > env var (PGHOST etc.) > built-in default",
    )
    conn.add_argument("--host",     default=None, help="DB host")
    conn.add_argument("--port",     default=None, type=int, help="DB port")
    conn.add_argument("--dbname",   default=None, help="Database name")
    conn.add_argument("--user",     default=None, help="DB user")
    conn.add_argument("--password", default=None, help="DB password")

    # --- Extraction options ---
    ext = p.add_argument_group("extraction options")
    ext.add_argument(
        "--schema-filter", metavar="SCHEMA", default=None,
        help="Only extract layers from this PostgreSQL schema (e.g. 'public').",
    )
    ext.add_argument(
        "--no-row-counts", action="store_true", default=False,
        help="Skip row count estimates (faster for large databases).",
    )
    ext.add_argument(
        "--save-schema", metavar="FILE", default=None,
        help="Also save the intermediate schema JSON to FILE.",
    )

    # --- Generation options ---
    gen = p.add_argument_group("generation options")
    gen.add_argument(
        "--platform",
        choices=["pyqgis", "arcpy", "folium", "kepler", "deck", "export", "qgs", "pyt"],
        default=None,
        help="Target platform (required unless --list-layers).",
    )
    gen.add_argument(
        "--layer", metavar="SCHEMA.TABLE", action="append", dest="layers",
        help="Only generate code for this layer (repeatable).",
    )
    gen.add_argument(
        "-o", "--output", metavar="FILE", default=None,
        help="Write generated script to FILE (default: stdout).",
    )
    gen.add_argument(
        "--op", metavar="OPERATION", action="append", dest="operations",
        choices=VALID_OPERATIONS,
        help=f"Add an operation block to every layer "
             f"({', '.join(VALID_OPERATIONS)}). Repeatable.",
    )
    gen.add_argument(
        "--template", metavar="FILE", default=None,
        help="TOML template file for custom code layout (preamble, imports, etc.).",
    )
    gen.add_argument(
        "--layout", metavar="FILE", default=None,
        help="TOML composition layout file (layer selection + per-layer operations).",
    )

    # --- Preview ---
    p.add_argument(
        "--list-layers", action="store_true",
        help="Print a summary of spatial layers and exit (no script generated).",
    )

    return p


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    args = build_parser().parse_args()

    # Load config file (may be None)
    config_path = find_config_file(args.config)
    config = load_toml(config_path) if config_path else {}
    if config_path:
        print(f"[cfg]  Using config: {config_path}", file=sys.stderr)

    db_config = resolve_db_config(args, config)
    args      = resolve_defaults(args, config)

    # Step 1: extract
    print(f"[1/2] Connecting to {db_config['dbname']} @ "
          f"{db_config['host']}:{db_config['port']} ...", file=sys.stderr)
    conn   = connect(db_config)
    schema = extract_schema(conn, include_row_counts=not args.no_row_counts)
    conn.close()
    print(f"      Found {schema['layer_count']} spatial layer(s).", file=sys.stderr)

    # --list-layers: print summary and exit
    if args.list_layers:
        col_w = max((len(l["qualified_name"]) for l in schema["layers"]), default=20)
        print(f"\n  {'LAYER':<{col_w}}  {'GEOM TYPE':<20}  {'SRID':<6}  ROWS (est.)")
        print(f"  {'-' * col_w}  {'-' * 20}  {'-' * 6}  ----------")
        for layer in schema["layers"]:
            row_est  = layer.get("row_count_estimate", -1)
            rows_str = f"~{row_est:,}" if row_est >= 0 else "unknown"
            print(f"  {layer['qualified_name']:<{col_w}}"
                  f"  {layer['geometry']['type']:<20}"
                  f"  {layer['geometry']['srid']:<6}"
                  f"  {rows_str}")
        print(f"\n  {schema['layer_count']} layer(s) in {schema['database']}\n")
        sys.exit(0)

    # Filter by PostgreSQL schema
    if args.schema_filter:
        schema["layers"] = [l for l in schema["layers"] if l["schema"] == args.schema_filter]
        schema["layer_count"] = len(schema["layers"])
        print(f"      After schema filter '{args.schema_filter}': "
              f"{schema['layer_count']} layer(s).", file=sys.stderr)
        if not schema["layers"]:
            print(f"[ERROR] No layers found in schema '{args.schema_filter}'. "
                  f"Use --list-layers to see available schemas.", file=sys.stderr)
            sys.exit(1)

    # Filter by qualified table name
    if args.layers:
        schema["layers"] = [
            l for l in schema["layers"] if l["qualified_name"] in args.layers
        ]
        schema["layer_count"] = len(schema["layers"])
        if not schema["layers"]:
            print(f"[ERROR] No layers matched: {args.layers}", file=sys.stderr)
            sys.exit(1)
        print(f"      After layer filter: {schema['layer_count']} layer(s).", file=sys.stderr)

    # Optionally persist schema JSON
    if args.save_schema:
        Path(args.save_schema).write_text(
            json.dumps(schema, indent=2, default=str), encoding="utf-8"
        )
        print(f"      Schema saved to {args.save_schema}.", file=sys.stderr)

    # Load template and layout if provided
    template = TemplateConfig.from_toml(args.template) if args.template else None
    layout = CompositionLayout.from_toml(args.layout) if args.layout else None

    # Apply composition layout (filters and reorders layers)
    if layout:
        schema = layout.filter_schema(schema)
        print(f"      After layout filter: {schema['layer_count']} layer(s).", file=sys.stderr)

    # Determine effective platform (layout can override if not explicitly set)
    platform = args.platform
    if not platform and layout and layout.platform:
        platform = layout.platform
        print(f"      Using platform from layout: {platform}", file=sys.stderr)

    if not platform:
        print("[ERROR] --platform is required unless --list-layers is used.", file=sys.stderr)
        sys.exit(1)

    # Determine effective output path (layout can override if not explicitly set)
    output_path = args.output
    if not output_path and layout and layout.output:
        output_path = layout.output
        print(f"      Using output path from layout: {output_path}", file=sys.stderr)

    # Step 2: generate
    print(f"[2/2] Generating {platform} script ...", file=sys.stderr)
    _no_op_platforms = {"folium", "kepler", "deck", "export", "qgs", "pyt"}
    if args.operations and platform in _no_op_platforms:
        print(f"[warn] --op flags are ignored for {platform}.",
              file=sys.stderr)
    elif args.operations:
        print(f"      Operations: {', '.join(args.operations)}", file=sys.stderr)

    # Get per-layer operations from layout
    per_layer_ops = layout.per_layer_ops() if layout else None

    generators = {
        "pyqgis":  lambda: generate_pyqgis(schema, db_config, args.operations, template=template, per_layer_ops=per_layer_ops),
        "arcpy":   lambda: generate_arcpy(schema, db_config, args.operations, template=template, per_layer_ops=per_layer_ops),
        "folium":  lambda: generate_folium(schema, db_config),
        "kepler":  lambda: generate_kepler(schema, db_config),
        "deck":    lambda: generate_deck(schema, db_config),
        "export":  lambda: generate_export(schema, db_config),
        "qgs":     lambda: generate_qgs(schema, db_config),
        "pyt":     lambda: generate_pyt(schema, db_config),
    }
    code = generators[platform]()

    if output_path:
        Path(output_path).write_text(code, encoding="utf-8")
        print(f"[OK]  Written to {output_path}", file=sys.stderr)
    else:
        print(code)


if __name__ == "__main__":
    main()
