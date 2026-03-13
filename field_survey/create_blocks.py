"""
Create block polygons from building assessment points and add to AGOL web map.

Groups points by street + hundred-block, creates convex hull polygons with a
buffer, computes summary stats, and pushes as a new layer.

Usage:
    python -m field_survey.create_blocks --token-file token.txt
"""
import argparse
import json
import logging
import math
import re
import uuid
from collections import defaultdict

import requests
from shapely.geometry import MultiPoint, mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")


def fetch_points(token):
    """Fetch all building assessment points."""
    headers = {"Referer": REFERER}
    all_features = []
    offset = 0
    while True:
        r = requests.get(
            f"{SERVICE_URL}/2/query",
            params={
                "where": "1=1",
                "outFields": "OBJECTID,ADDRESS_FULL,ba_street,ba_street_number,"
                             "GENERAL_USE,VACANCY_STATUS,ba_building_type,"
                             "ba_condition_rating,ba_risk_band,BUSINESS_NAME",
                "returnGeometry": "true",
                "outSR": "4326",
                "resultOffset": offset,
                "resultRecordCount": 2000,
                "f": "json",
                "token": token,
            },
            headers=headers, timeout=120,
        )
        data = r.json()
        features = data.get("features", [])
        all_features.extend(features)
        if len(features) < 2000:
            break
        offset += 2000
    return all_features


def compute_block_id(street, street_number):
    """Compute block ID from street name and number."""
    if not street:
        return None
    try:
        num = int(re.sub(r"[^\d]", "", str(street_number or "0")) or "0")
    except (ValueError, TypeError):
        num = 0
    hundred = (num // 100) * 100
    return f"{street} - {hundred}s"


def create_block_polygons(features):
    """Group points into blocks and create convex hull polygons."""
    blocks = defaultdict(lambda: {"points": [], "features": []})

    for f in features:
        attrs = f["attributes"]
        geom = f.get("geometry", {})
        x, y = geom.get("x"), geom.get("y")
        if x is None or y is None:
            continue

        street = attrs.get("ba_street") or ""
        street_num = attrs.get("ba_street_number") or ""
        block_id = compute_block_id(street, street_num)
        if not block_id:
            # Try to parse street from ADDRESS_FULL
            addr = attrs.get("ADDRESS_FULL", "")
            match = re.match(r"(\d+)\s+(.+)", addr)
            if match:
                street_num = match.group(1)
                street = match.group(2)
                block_id = compute_block_id(street, street_num)
        if not block_id:
            block_id = "Non assign\u00e9"

        blocks[block_id]["points"].append((x, y))
        blocks[block_id]["features"].append(attrs)

    # Create polygons
    block_features = []
    for block_id, data in sorted(blocks.items()):
        points = data["points"]
        attrs_list = data["features"]

        if len(points) < 1:
            continue

        # Create geometry: convex hull with buffer for single/collinear points
        mp = MultiPoint(points)
        if len(points) == 1:
            hull = mp.buffer(0.0003)  # ~30m buffer for single points
        elif len(points) == 2:
            hull = mp.convex_hull.buffer(0.00015)
        else:
            hull = mp.convex_hull
            if hull.geom_type == "LineString":
                hull = hull.buffer(0.00015)
            else:
                hull = hull.buffer(0.00008)  # slight buffer to enclose edge points

        # Compute stats
        total = len(attrs_list)
        commercial = sum(1 for a in attrs_list if a.get("GENERAL_USE") in ("Commercial", "Mixed Use"))
        residential = sum(1 for a in attrs_list if a.get("GENERAL_USE") == "Residential")
        vacant = sum(1 for a in attrs_list
                     if a.get("VACANCY_STATUS") and "Vacant" in str(a.get("VACANCY_STATUS", "")))

        # Get street name from block_id
        parts = block_id.rsplit(" - ", 1)
        street_name = parts[0] if len(parts) == 2 else block_id
        address_range = parts[1] if len(parts) == 2 else ""

        # Convert shapely geometry to AGOL rings
        geoj = mapping(hull)
        if geoj["type"] == "Polygon":
            rings = [list(geoj["coordinates"][0])]
        elif geoj["type"] == "MultiPolygon":
            rings = [list(geoj["coordinates"][0][0])]
        else:
            continue

        # Convert rings to AGOL format [[x,y], ...]
        agol_rings = [[[c[0], c[1]] for c in ring] for ring in rings]

        block_features.append({
            "geometry": {
                "rings": agol_rings,
                "spatialReference": {"wkid": 4326},
            },
            "attributes": {
                "block_id": block_id,
                "rue": street_name,
                "plage_adresses": address_range,
                "total_batiments": total,
                "commerces": commercial,
                "residentiels": residential,
                "vacants": vacant,
                "taux_vacance_pct": round(vacant / total * 100, 1) if total > 0 else 0,
                "globalid": str(uuid.uuid4()),
            },
        })

    return block_features


def add_block_layer(token, block_features):
    """Add block layer to the feature service and web map."""
    headers = {"Referer": REFERER}

    # Step 1: Add new layer definition to the feature service
    log.info("Adding block layer definition to feature service...")
    layer_def = {
        "layers": [{
            "id": 52,
            "name": "Survey Blocks",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPolygon",
            "objectIdField": "OBJECTID",
            "globalIdField": "globalid",
            "fields": [
                {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "Identifiant"},
                {"name": "globalid", "type": "esriFieldTypeGlobalID", "alias": "Identifiant global"},
                {"name": "block_id", "type": "esriFieldTypeString", "alias": "\u00celot", "length": 100},
                {"name": "rue", "type": "esriFieldTypeString", "alias": "Rue", "length": 100},
                {"name": "plage_adresses", "type": "esriFieldTypeString", "alias": "Plage d'adresses", "length": 20},
                {"name": "total_batiments", "type": "esriFieldTypeInteger", "alias": "Total b\u00e2timents"},
                {"name": "commerces", "type": "esriFieldTypeInteger", "alias": "Commerces"},
                {"name": "residentiels", "type": "esriFieldTypeInteger", "alias": "R\u00e9sidentiels"},
                {"name": "vacants", "type": "esriFieldTypeInteger", "alias": "Vacants"},
                {"name": "taux_vacance_pct", "type": "esriFieldTypeDouble", "alias": "Taux de vacance (%)"},
            ],
            "extent": {
                "xmin": -79.405, "ymin": 43.652, "xmax": -79.390, "ymax": 43.660,
                "spatialReference": {"wkid": 4326},
            },
            "drawingInfo": {
                "renderer": {
                    "type": "simple",
                    "symbol": {
                        "type": "esriSFS",
                        "style": "esriSFSSolid",
                        "color": [51, 153, 255, 40],
                        "outline": {
                            "type": "esriSLS",
                            "style": "esriSLSSolid",
                            "color": [51, 153, 255, 200],
                            "width": 2,
                        },
                    },
                },
            },
            "hasAttachments": False,
            "capabilities": "Create,Delete,Query,Update,Editing",
        }],
    }

    r = requests.post(
        f"{ADMIN_URL}/addToDefinition",
        data={
            "addToDefinition": json.dumps(layer_def),
            "token": token,
            "f": "json",
        },
        headers=headers, timeout=120,
    )
    result = r.json()

    if not result.get("success"):
        log.error(f"Failed to add layer definition: {result}")
        # Layer might already exist — try to use it
        if "already exists" in str(result).lower():
            log.info("Layer already exists, will add features to it")
        else:
            return None

    # Find the actual layer ID that was created
    r = requests.get(SERVICE_URL, params={"f": "json", "token": token},
                     headers=headers, timeout=60)
    svc = r.json()
    block_layer_id = None
    for l in svc.get("layers", []):
        if l["name"] == "Survey Blocks":
            block_layer_id = l["id"]
            break

    if block_layer_id is None:
        log.error("Could not find the new Survey Blocks layer")
        return None

    log.info(f"Block layer created with ID {block_layer_id}")

    # Step 2: Add features in batches
    log.info(f"Adding {len(block_features)} block polygons...")
    batch_size = 100
    total_added = 0
    for i in range(0, len(block_features), batch_size):
        batch = block_features[i:i + batch_size]
        r = requests.post(
            f"{SERVICE_URL}/{block_layer_id}/addFeatures",
            data={
                "features": json.dumps(batch),
                "token": token,
                "f": "json",
            },
            headers=headers, timeout=120,
        )
        result = r.json()
        added = sum(1 for res in result.get("addResults", []) if res.get("success"))
        total_added += added
        log.info(f"  Batch {i // batch_size + 1}: {added}/{len(batch)} added")

    log.info(f"Total blocks added: {total_added}")
    return block_layer_id


def add_to_webmap(token, block_layer_id):
    """Add block layer to the web map in the evaluation group with popup."""
    headers = {"Referer": REFERER}

    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token},
        headers=headers, timeout=60,
    )
    webmap = r.json()

    # Build block layer entry with popup
    block_layer = {
        "id": f"layer_{block_layer_id}",
        "layerType": "ArcGISFeatureLayer",
        "url": f"{SERVICE_URL}/{block_layer_id}",
        "title": "\u00celots d'enqu\u00eate",
        "itemId": FEATURE_SERVICE_ITEM_ID,
        "visibility": True,
        "opacity": 0.6,
        "popupInfo": {
            "title": "{block_id}",
            "description": (
                '<div style="font-family:sans-serif;padding:4px;">'
                '<h3 style="margin:0 0 8px 0;font-size:15px;">{block_id}</h3>'
                '<table style="font-size:13px;border-collapse:collapse;width:100%;">'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">B\u00e2timents</td><td><b>{total_batiments}</b></td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">Commerces</td><td><b>{commerces}</b></td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">R\u00e9sidentiels</td><td><b>{residentiels}</b></td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">Vacants</td><td><b>{vacants}</b></td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">Taux de vacance</td><td><b>{taux_vacance_pct}%</b></td></tr>'
                '</table>'
                '</div>'
            ),
            "fieldInfos": [
                {"fieldName": "block_id", "label": "\u00celot", "visible": True},
                {"fieldName": "rue", "label": "Rue", "visible": True},
                {"fieldName": "plage_adresses", "label": "Plage d'adresses", "visible": True},
                {"fieldName": "total_batiments", "label": "B\u00e2timents", "visible": True},
                {"fieldName": "commerces", "label": "Commerces", "visible": True},
                {"fieldName": "residentiels", "label": "R\u00e9sidentiels", "visible": True},
                {"fieldName": "vacants", "label": "Vacants", "visible": True},
                {"fieldName": "taux_vacance_pct", "label": "Taux de vacance (%)", "visible": True},
            ],
        },
    }

    # Add to the Evaluation des batiments group
    for group in webmap["operationalLayers"]:
        if group.get("layerType") == "GroupLayer":
            title = group.get("title", "")
            if "valuation" in title.lower() or "batiment" in title.lower():
                # Insert at the top of the group
                group["layers"].insert(0, block_layer)
                log.info(f"Added block layer to group: {title}")
                break
    else:
        # Fallback: add as top-level
        webmap["operationalLayers"].insert(0, block_layer)
        log.info("Added block layer at top level")

    # Push
    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    result = r.json()
    if result.get("success"):
        log.info("Web map updated with block layer!")
    else:
        log.error(f"Web map update failed: {result}")


def update_field_aliases(token, block_layer_id):
    """Set French aliases on the block layer fields."""
    headers = {"Referer": REFERER}
    update_def = {
        "fields": [
            {"name": "block_id", "alias": "\u00celot"},
            {"name": "rue", "alias": "Rue"},
            {"name": "plage_adresses", "alias": "Plage d'adresses"},
            {"name": "total_batiments", "alias": "Total b\u00e2timents"},
            {"name": "commerces", "alias": "Commerces"},
            {"name": "residentiels", "alias": "R\u00e9sidentiels"},
            {"name": "vacants", "alias": "Vacants"},
            {"name": "taux_vacance_pct", "alias": "Taux de vacance (%)"},
        ]
    }
    r = requests.post(
        f"{ADMIN_URL}/{block_layer_id}/updateDefinition",
        data={"updateDefinition": json.dumps(update_def), "token": token, "f": "json"},
        headers=headers, timeout=60,
    )
    if r.json().get("success"):
        log.info("Field aliases updated to French")


def main():
    parser = argparse.ArgumentParser(description="Create block polygons for field survey")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    # Fetch points
    log.info("Fetching building assessment points...")
    features = fetch_points(token)
    log.info(f"Fetched {len(features)} points")

    # Create block polygons
    log.info("Creating block polygons...")
    block_features = create_block_polygons(features)
    log.info(f"Created {len(block_features)} blocks")

    # Add to feature service
    block_layer_id = add_block_layer(token, block_features)
    if block_layer_id is None:
        return

    # Update aliases
    update_field_aliases(token, block_layer_id)

    # Add to web map
    add_to_webmap(token, block_layer_id)

    log.info(f"Done! View: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")


if __name__ == "__main__":
    main()
