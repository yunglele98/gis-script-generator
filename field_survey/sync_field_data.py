"""
Sync Survey123 and Field Maps data from ArcGIS Online to PostGIS.

Usage:
    python -m field_survey.sync_field_data \
        --config field_survey/sync_config.json \
        --db-password test123

Requires: requests, psycopg
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Map form keys to PostGIS table names
FORM_TABLE_MAP = {
    "resident": "field_surveys.resident_responses",
    "business": "field_surveys.business_responses",
    "intercept": "field_surveys.intercept_responses",
    "student": "field_surveys.student_responses",
    "field_obs": "field_surveys.field_observations",
    "contact": "field_surveys.contact_responses",
}

# AGOL fields to skip (internal ESRI fields)
SKIP_FIELDS = {
    "ObjectID", "objectid", "OBJECTID", "Shape__Area", "Shape__Length",
    "CreationDate", "Creator", "EditDate", "Editor",
}

# Known form versions (sync warns on unknown)
KNOWN_VERSIONS = {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}


def build_upsert_sql(table: str, columns: list[str]) -> str:
    """Build an INSERT ... ON CONFLICT (globalid) DO UPDATE SQL statement."""
    placeholders = ", ".join([f"%({c})s" for c in columns])
    col_list = ", ".join(columns)
    update_cols = [c for c in columns if c not in ("globalid", "id")]
    set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])

    return f"""
        INSERT INTO {table} ({col_list}, sync_timestamp)
        VALUES ({placeholders}, NOW())
        ON CONFLICT (globalid) DO UPDATE SET
            {set_clause},
            sync_timestamp = NOW()
    """


def transform_feature(feature: dict, include_geom: bool = False) -> dict:
    """Extract attributes from an AGOL feature, optionally including geometry."""
    attrs = {}
    for k, v in feature.get("attributes", {}).items():
        if k in SKIP_FIELDS:
            continue
        # Skip note fields (XLSForm display-only, not stored in PostGIS)
        if k.lower().startswith("note_"):
            continue
        # Convert AGOL epoch timestamps to datetime
        if isinstance(v, int) and v > 1_000_000_000_000:
            v = datetime.fromtimestamp(v / 1000, tz=timezone.utc).isoformat()
        attrs[k.lower()] = v

    if include_geom and feature.get("geometry"):
        geom = feature["geometry"]
        x, y = geom.get("x"), geom.get("y")
        if x is not None and y is not None:
            # AGOL query requests outSR=2952, so coordinates are already projected
            attrs["geom"] = f"SRID=2952;POINT({x} {y})"

    return attrs


def sync_layer(conn, layer_url: str, table: str, include_geom: bool = False, token: str = None):
    """Pull all features from an AGOL feature layer and upsert into PostGIS."""
    log.info(f"Syncing {layer_url} -> {table}")

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": str(include_geom).lower(),
        "outSR": 2952,
        "f": "json",
    }
    if token:
        params["token"] = token

    headers = {"Referer": "https://fieldsurvey.local"} if token else {}
    resp = requests.get(f"{layer_url}/query", params=params, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        log.error(f"AGOL error: {data['error']}")
        return 0

    features = data.get("features", [])

    if not features:
        log.warning(f"No features returned from {layer_url}")
        return 0

    # Transform all features
    rows = [transform_feature(f, include_geom) for f in features]

    # Filter columns to only those that exist in the target table
    cur = conn.cursor()
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s",
        (table.split(".")[0], table.split(".")[1]),
    )
    db_columns = {r[0] for r in cur.fetchall()}
    all_columns = list(rows[0].keys())
    columns = [c for c in all_columns if c in db_columns]
    skipped_cols = set(all_columns) - set(columns)
    if skipped_cols:
        log.info(f"Skipping columns not in {table}: {skipped_cols}")
    # Keep only known columns in each row
    rows = [{k: v for k, v in row.items() if k in db_columns} for row in rows]

    # Check form versions
    for row in rows:
        ver = row.get("form_version")
        if ver and ver not in KNOWN_VERSIONS:
            log.warning(f"Unknown form_version '{ver}' — check changelog")

    # Filter out rows where informed_consent != 'yes' (if field exists)
    if "informed_consent" in columns:
        before = len(rows)
        rows = [r for r in rows if r.get("informed_consent") == "yes"]
        skipped = before - len(rows)
        if skipped:
            log.info(f"Skipped {skipped} rows without consent")

    sql = build_upsert_sql(table, columns)

    count = 0
    for row in rows:
        try:
            cur.execute(sql, row)
            count += 1
        except Exception as e:
            log.error(f"Failed to upsert row {row.get('globalid')}: {e}")
            conn.rollback()
            continue
    conn.commit()

    log.info(f"Synced {count}/{len(rows)} features to {table}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Sync AGOL survey data to PostGIS")
    parser.add_argument("--config", help="JSON config file with AGOL layer URLs")
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="kensington")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--db-password", default=os.environ.get("PGPASSWORD", ""))
    parser.add_argument("--agol-token", default=os.environ.get("AGOL_TOKEN", ""),
                        help="AGOL access token (or set AGOL_TOKEN env var)")
    args = parser.parse_args()

    if not args.config:
        log.error("Provide --config with AGOL layer URLs. Example config:")
        log.error(json.dumps({
            "layers": {
                "resident": {"url": "https://services.arcgis.com/.../0", "geom": False},
                "business": {"url": "https://services.arcgis.com/.../1", "geom": True},
            }
        }, indent=2))
        sys.exit(1)

    with open(args.config) as f:
        config = json.load(f)

    conn = psycopg.connect(
        host=args.db_host, port=args.db_port,
        dbname=args.db_name, user=args.db_user, password=args.db_password,
    )

    total = 0
    for form_key, layer_conf in config.get("layers", {}).items():
        table = FORM_TABLE_MAP.get(form_key)
        if not table:
            log.warning(f"Unknown form key '{form_key}', skipping")
            continue

        count = sync_layer(
            conn,
            layer_url=layer_conf["url"],
            table=table,
            include_geom=layer_conf.get("geom", False),
            token=args.agol_token or None,
        )
        total += count

    conn.close()
    log.info(f"Sync complete. {total} total features synced.")


if __name__ == "__main__":
    main()
