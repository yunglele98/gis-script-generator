"""
gis_codegen.extractor

Connects to a PostGIS database and extracts spatial layer metadata:
- Table/view name and schema
- Geometry column name, type, and SRID
- All non-geometry columns with their data types
- Row counts (optional, skipped for large tables)

Output: JSON written to stdout or a file.
"""

import json
import os
import sys
import argparse
import psycopg2
import psycopg2.extras


DB_CONFIG = {
    "host":     os.environ.get("PGHOST",     "localhost"),
    "port":     int(os.environ.get("PGPORT", 5432)),
    "dbname":   os.environ.get("PGDATABASE", "my_gis_db"),
    "user":     os.environ.get("PGUSER",     "postgres"),
    "password": os.environ.get("PGPASSWORD", ""),
}

# PostGIS geometry_columns covers tables registered via AddGeometryColumn or
# views created with ST_SetSRID. The fallback query covers unregistered tables.
SPATIAL_LAYERS_SQL = """
SELECT
    gc.f_table_schema   AS schema_name,
    gc.f_table_name     AS table_name,
    gc.f_geometry_column AS geom_column,
    gc.type             AS geom_type,
    gc.srid             AS srid,
    obj_description(
        (quote_ident(gc.f_table_schema) || '.' || quote_ident(gc.f_table_name))::regclass,
        'pg_class'
    ) AS table_comment
FROM geometry_columns gc
ORDER BY gc.f_table_schema, gc.f_table_name;
"""

NON_GEOM_COLUMNS_SQL = """
SELECT
    c.column_name,
    c.data_type,
    c.character_maximum_length,
    c.is_nullable,
    c.column_default
FROM information_schema.columns c
WHERE c.table_schema = %s
  AND c.table_name   = %s
  AND c.column_name NOT IN (
      SELECT f_geometry_column
      FROM geometry_columns
      WHERE f_table_schema = %s
        AND f_table_name   = %s
  )
ORDER BY c.ordinal_position;
"""

ROW_COUNT_SQL = """
SELECT reltuples::bigint AS estimate
FROM pg_class
WHERE oid = (quote_ident(%s) || '.' || quote_ident(%s))::regclass;
"""

PRIMARY_KEY_SQL = """
SELECT kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
  ON tc.constraint_name = kcu.constraint_name
 AND tc.table_schema    = kcu.table_schema
 AND tc.table_name      = kcu.table_name
WHERE tc.constraint_type = 'PRIMARY KEY'
  AND tc.table_schema    = %s
  AND tc.table_name      = %s
ORDER BY kcu.ordinal_position;
"""


def connect(config: dict):
    try:
        conn = psycopg2.connect(**config)
        conn.set_session(readonly=True, autocommit=True)
        return conn
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Could not connect to database: {e}", file=sys.stderr)
        sys.exit(1)


def fetch_spatial_layers(cur) -> list[dict]:
    cur.execute(SPATIAL_LAYERS_SQL)
    return cur.fetchall()


def fetch_columns(cur, schema: str, table: str) -> list[dict]:
    cur.execute(NON_GEOM_COLUMNS_SQL, (schema, table, schema, table))
    rows = cur.fetchall()
    columns = []
    for row in rows:
        col = {
            "name": row["column_name"],
            "data_type": row["data_type"],
            "nullable": row["is_nullable"] == "YES",
        }
        if row["character_maximum_length"]:
            col["max_length"] = row["character_maximum_length"]
        if row["column_default"]:
            col["default"] = row["column_default"]
        columns.append(col)
    return columns


def fetch_primary_keys(cur, schema: str, table: str) -> list[str]:
    cur.execute(PRIMARY_KEY_SQL, (schema, table))
    return [row["column_name"] for row in cur.fetchall()]


def fetch_row_count_estimate(cur, schema: str, table: str) -> int:
    """Uses pg_class statistics — fast, approximate."""
    try:
        cur.execute(ROW_COUNT_SQL, (schema, table))
        row = cur.fetchone()
        return row["estimate"] if row else -1
    except Exception as exc:
        print(f"[WARN] Row count estimate failed for {schema}.{table}: {exc}",
              file=sys.stderr)
        return -1


def extract_schema(conn, include_row_counts: bool = True) -> dict:
    layers = []
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        spatial_rows = fetch_spatial_layers(cur)

        if not spatial_rows:
            print("[WARN] No spatial layers found in geometry_columns.", file=sys.stderr)

        for row in spatial_rows:
            schema = row["schema_name"]
            table  = row["table_name"]

            layer = {
                "schema":       schema,
                "table":        table,
                "qualified_name": f"{schema}.{table}",
                "geometry": {
                    "column": row["geom_column"],
                    "type":   row["geom_type"],
                    "srid":   row["srid"],
                },
                "columns":      fetch_columns(cur, schema, table),
                "primary_keys": fetch_primary_keys(cur, schema, table),
            }

            if row["table_comment"]:
                layer["comment"] = row["table_comment"]

            if include_row_counts:
                layer["row_count_estimate"] = fetch_row_count_estimate(cur, schema, table)

            layers.append(layer)

    return {
        "database": conn.get_dsn_parameters().get("dbname", "unknown"),
        "host":     conn.get_dsn_parameters().get("host", "unknown"),
        "layer_count": len(layers),
        "layers": layers,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract spatial layer schema from a PostGIS database."
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        help="Write JSON output to FILE instead of stdout.",
    )
    parser.add_argument(
        "--no-row-counts",
        action="store_true",
        help="Skip row count estimates (faster for databases with many tables).",
    )
    parser.add_argument(
        "--schema-filter",
        metavar="SCHEMA",
        help="Only extract layers from this schema (e.g. 'public').",
    )
    args = parser.parse_args()

    if not DB_CONFIG["password"]:
        print("[ERROR] No password found. Set the PGPASSWORD environment variable.",
              file=sys.stderr)
        sys.exit(1)

    conn = connect(DB_CONFIG)
    result = extract_schema(conn, include_row_counts=not args.no_row_counts)
    conn.close()

    if args.schema_filter:
        result["layers"] = [
            l for l in result["layers"] if l["schema"] == args.schema_filter
        ]
        result["layer_count"] = len(result["layers"])

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"[OK] Schema written to {args.output} ({result['layer_count']} layers)")
    else:
        print(output)


if __name__ == "__main__":
    main()
