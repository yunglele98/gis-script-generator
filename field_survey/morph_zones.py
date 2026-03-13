"""
Replace team survey zones with dissolved morphological zones.

Dissolves per-building morphological zone polygons (layer 17) into zone-level
polygons, computes stats, and pushes to layer 52.

Usage:
    python -m field_survey.morph_zones --token-file token.txt
"""
import argparse
import json
import logging
import uuid
from collections import defaultdict

import requests
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

ZONE_FR = {
    "Core Market Spine \u2013 Mixed-Use": "Axe central du march\u00e9",
    "Secondary Market Street \u2013 Mixed-Use": "Rue secondaire du march\u00e9",
    "Perimeter Arterial \u2013 Commercial Corridor": "Art\u00e8re p\u00e9riph\u00e9rique commerciale",
    "Residential Interior \u2013 Victorian Fabric": "Int\u00e9rieur r\u00e9sidentiel victorien",
    "Institutional / Residential Node": "N\u0153ud institutionnel / r\u00e9sidentiel",
    "Laneway / Interior Passage \u2013 Worker Cottage": "Ruelle / Cottage ouvrier",
}


def fetch_all(layer_id, token, fields="*"):
    """Fetch all features from a layer."""
    headers = {"Referer": REFERER}
    all_feats = []
    offset = 0
    while True:
        r = requests.get(
            f"{SERVICE_URL}/{layer_id}/query",
            params={
                "where": "1=1", "outFields": fields,
                "returnGeometry": "true", "outSR": 4326,
                "resultOffset": offset, "resultRecordCount": 2000,
                "f": "json", "token": token,
            },
            headers=headers, timeout=120,
        )
        feats = r.json().get("features", [])
        all_feats.extend(feats)
        if len(feats) < 2000:
            break
        offset += 2000
    return all_feats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    headers = {"Referer": REFERER}

    # Fetch morphological zone polygons (layer 17)
    log.info("Fetching morphological zone polygons (layer 17)...")
    morph_feats = fetch_all(17, token, "MORPHOLOGICAL_ZONE")
    log.info(f"  {len(morph_feats)} features")

    # Group by zone and dissolve
    zones = defaultdict(list)
    for f in morph_feats:
        zone = f["attributes"].get("MORPHOLOGICAL_ZONE")
        if not zone:
            continue
        rings = f.get("geometry", {}).get("rings", [])
        if not rings:
            continue
        try:
            poly = shape({"type": "Polygon", "coordinates": rings})
            if poly.is_valid and not poly.is_empty:
                zones[zone].append(poly)
        except Exception:
            pass

    log.info(f"  {len(zones)} distinct zones")

    dissolved = {}
    for zone_name, polys in zones.items():
        merged = unary_union(polys)
        dissolved[zone_name] = merged
        n = len(merged.geoms) if merged.geom_type == "MultiPolygon" else 1
        log.info(f"  {zone_name}: {len(polys)} polys -> {n} parts")

    # Count assessment points per zone
    log.info("Counting points per zone...")
    r = requests.get(
        f"{SERVICE_URL}/2/query",
        params={
            "where": "1=1",
            "outFields": "GENERAL_USE,MORPHOLOGICAL_ZONE",
            "returnGeometry": "false",
            "f": "json", "token": token,
        },
        headers=headers, timeout=120,
    )
    pts = r.json().get("features", [])

    zone_stats = defaultdict(lambda: {"total": 0, "commercial": 0})
    for p in pts:
        z = p["attributes"].get("MORPHOLOGICAL_ZONE")
        if not z:
            continue
        zone_stats[z]["total"] += 1
        use = p["attributes"].get("GENERAL_USE", "")
        if use in ("Commercial", "Mixed Use"):
            zone_stats[z]["commercial"] += 1

    for z, s in zone_stats.items():
        log.info(f"  {z}: {s['total']} bat, {s['commercial']} comm")

    # Delete old zone features from layer 52
    log.info("Deleting old zones from layer 52...")
    r = requests.post(
        f"{SERVICE_URL}/52/deleteFeatures",
        data={"where": "1=1", "token": token, "f": "json"},
        headers=headers, timeout=120,
    )
    log.info(f"  Deleted: {len(r.json().get('deleteResults', []))}")

    # Add zone_morpho field if not exists
    r = requests.post(
        f"{ADMIN_URL}/52/addToDefinition",
        data={
            "addToDefinition": json.dumps({
                "fields": [{
                    "name": "zone_morpho", "type": "esriFieldTypeString",
                    "alias": "Zone morphologique (EN)", "length": 120,
                    "nullable": True, "editable": True,
                }]
            }),
            "token": token, "f": "json",
        },
        headers=headers, timeout=60,
    )
    log.info(f"  Add field: {r.json().get('success', r.json())}")

    # Prepare dissolved zone features
    zone_features = []
    for zone_name, geom in dissolved.items():
        fr_name = ZONE_FR.get(zone_name, zone_name)
        stats = zone_stats.get(zone_name, {"total": 0, "commercial": 0})

        if geom.geom_type == "Polygon":
            geoj = mapping(geom)
            rings = [[[c[0], c[1]] for c in ring] for ring in geoj["coordinates"]]
        elif geom.geom_type == "MultiPolygon":
            rings = []
            for poly in geom.geoms:
                geoj = mapping(poly)
                for ring in geoj["coordinates"]:
                    rings.append([[c[0], c[1]] for c in ring])
        else:
            continue

        zone_features.append({
            "geometry": {"rings": rings, "spatialReference": {"wkid": 4326}},
            "attributes": {
                "globalid": str(uuid.uuid4()),
                "zone_name": fr_name,
                "equipe": "",
                "description": fr_name,
                "nb_batiments": stats["total"],
                "nb_commerces": stats["commercial"],
                "zone_morpho": zone_name,
            },
        })

    log.info(f"Pushing {len(zone_features)} dissolved zones...")
    r = requests.post(
        f"{SERVICE_URL}/52/addFeatures",
        data={"features": json.dumps(zone_features), "token": token, "f": "json"},
        headers=headers, timeout=120,
    )
    result = r.json()
    added = sum(1 for res in result.get("addResults", []) if res.get("success"))
    log.info(f"  Added: {added}/{len(zone_features)}")

    for res in result.get("addResults", []):
        if not res.get("success"):
            log.warning(f"  Failed: {res}")

    # Update web map
    log.info("Updating web map...")
    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token}, headers=headers, timeout=60,
    )
    webmap = r.json()

    for group in webmap.get("operationalLayers", []):
        if group.get("layerType") != "GroupLayer":
            continue
        for layer in group.get("layers", []):
            if layer.get("url", "").endswith("/52"):
                layer["title"] = "Zones d'enqu\u00eate (morphologiques)"
                layer["visibility"] = True
                layer["opacity"] = 0.4
                layer["popupInfo"] = {
                    "title": "{zone_name}",
                    "description": (
                        '<div style="font-family:sans-serif;padding:4px;">'
                        '<h3 style="margin:0 0 8px 0;">{zone_name}</h3>'
                        '<table style="font-size:13px;border-collapse:collapse;width:100%;">'
                        '<tr><td style="padding:4px 8px 4px 0;color:#555;">B\u00e2timents</td>'
                        '<td><b>{nb_batiments}</b></td></tr>'
                        '<tr><td style="padding:4px 8px 4px 0;color:#555;">Commerces</td>'
                        '<td><b>{nb_commerces}</b></td></tr>'
                        '</table></div>'
                    ),
                }
                log.info(f"  Updated: {layer['title']}")

    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    log.info(f"  Web map: {r.json().get('success')}")
    log.info("Done!")


if __name__ == "__main__":
    main()
