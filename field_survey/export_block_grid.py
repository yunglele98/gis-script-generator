"""
Export Kensington road centerlines as GeoJSON for AGOL coverage map.

Usage:
    python -m field_survey.export_block_grid [--password test123]
"""
import argparse
import json
import os

import psycopg


def export_block_grid(conn, outfile: str) -> int:
    """Export road centerlines as GeoJSON for AGOL coverage map layer."""
    cur = conn.cursor()
    cur.execute("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'properties', json_build_object(
                        'street_name', linear_name_full,
                        'centreline_id', centreline_id,
                        'team_assignment', '',
                        'status', 'not_started'
                    ),
                    'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json
                )
            ), '[]'::json)
        )
        FROM opendata.road_centerlines
    """)
    geojson = cur.fetchone()[0]

    with open(outfile, "w") as f:
        json.dump(geojson, f, indent=2)

    feature_count = len(geojson.get("features", []))
    return feature_count


def main():
    parser = argparse.ArgumentParser(description="Export block grid as GeoJSON for AGOL")
    parser.add_argument("--output", default="field_survey/choices/block_grid.geojson")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--dbname", default="kensington")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=os.environ.get("PGPASSWORD", ""))
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    conn = psycopg.connect(
        host=args.host, port=args.port,
        dbname=args.dbname, user=args.user, password=args.password,
    )

    count = export_block_grid(conn, args.output)
    print(f"Exported {count} road segments to {args.output}")
    conn.close()


if __name__ == "__main__":
    main()
