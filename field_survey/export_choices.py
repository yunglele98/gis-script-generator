"""
Export PostGIS data as CSV choice lists for Survey123 XLSForms.

Usage:
    python -m field_survey.export_choices [--output-dir field_survey/choices]

Requires: psycopg, connection to kensington database.
"""
import csv
import os
import sys

import psycopg


def export_business_names(conn, outfile: str) -> int:
    """Export distinct business names as XLSForm choice list CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT name FROM (
            SELECT business_name AS name FROM online_data.business_licences
            WHERE business_name IS NOT NULL
            UNION
            SELECT "BUSINESS_NAME" AS name FROM public.building_assessment
            WHERE "BUSINESS_NAME" IS NOT NULL
        ) sub
        ORDER BY name
    """)
    rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (name,) in rows:
            writer.writerow(["business_name", name, name])
        writer.writerow(["business_name", "__other__", "Other (type below)"])

    return len(rows) + 1


def export_addresses(conn, outfile: str) -> int:
    """Export distinct addresses as XLSForm choice list CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT "ADDRESS_FULL"
        FROM public.building_assessment
        WHERE "ADDRESS_FULL" IS NOT NULL
        ORDER BY "ADDRESS_FULL"
    """)
    rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (addr,) in rows:
            writer.writerow(["street_address", addr, addr])

    return len(rows)


def export_block_locations(conn, outfile: str) -> int:
    """Export block-level location labels as XLSForm choice list CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT
            r.linear_name_full || ' (' ||
            COALESCE(f.linear_name_full, 'start') || ' to ' ||
            COALESCE(t.linear_name_full, 'end') || ')' AS block_label
        FROM opendata.road_centerlines r
        LEFT JOIN LATERAL (
            SELECT DISTINCT r2.linear_name_full
            FROM opendata.road_centerlines r2
            WHERE r2.from_intersection_id = r.from_intersection_id
            AND r2.linear_name_full != r.linear_name_full
            LIMIT 1
        ) f ON TRUE
        LEFT JOIN LATERAL (
            SELECT DISTINCT r2.linear_name_full
            FROM opendata.road_centerlines r2
            WHERE r2.from_intersection_id = r.to_intersection_id
            AND r2.linear_name_full != r.linear_name_full
            LIMIT 1
        ) t ON TRUE
        ORDER BY 1
    """)
    rows = cur.fetchall()

    # Fallback: simple street name list if cross-street query returns nothing
    if not rows:
        cur.execute("""
            SELECT DISTINCT linear_name_full
            FROM opendata.road_centerlines
            ORDER BY 1
        """)
        rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (label,) in rows:
            safe_name = label.lower().replace(" ", "_").replace("(", "").replace(")", "")
            writer.writerow(["block_location", safe_name, label])

    return len(rows)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export PostGIS data as Survey123 choice lists")
    parser.add_argument("--output-dir", default="field_survey/choices")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--dbname", default="kensington")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=os.environ.get("PGPASSWORD", ""))
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    conn = psycopg.connect(
        host=args.host, port=args.port,
        dbname=args.dbname, user=args.user, password=args.password,
    )

    n1 = export_business_names(conn, os.path.join(args.output_dir, "business_names.csv"))
    print(f"Exported {n1} business names")

    n2 = export_addresses(conn, os.path.join(args.output_dir, "addresses.csv"))
    print(f"Exported {n2} addresses")

    n3 = export_block_locations(conn, os.path.join(args.output_dir, "block_locations.csv"))
    print(f"Exported {n3} block locations")

    conn.close()
    print(f"Choice lists saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
