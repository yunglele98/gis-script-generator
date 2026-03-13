"""
Link building assessment data to building footprint polygons via spatial join.

For each footprint polygon, finds the assessment point(s) inside it and copies
key assessment fields onto the footprint. Pushes the enriched footprints as a
new layer in the AGOL feature service.

Usage:
    python -m field_survey.link_footprints --token-file token.txt
"""
import argparse
import json
import logging
import uuid

import requests
from shapely.geometry import Point, shape
from shapely.wkt import loads as wkt_loads

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

# Fields to copy from assessment points to footprints
ASSESSMENT_FIELDS = [
    "ADDRESS_FULL", "GENERAL_USE", "ba_building_type", "BUSINESS_NAME",
    "VACANCY_STATUS", "ba_condition_rating", "ba_risk_band",
    "ba_facade_material", "ba_storefront_status", "ba_is_vacant",
    "ba_street_presence", "ba_is_neglected", "ARCHITECTURAL_STYLE",
    "HR_REGISTER_STATUS", "HCD_CONTRIBUTING",
]


def fetch_all(layer_id, token, out_sr=4326, return_geometry=True):
    """Fetch all features from a layer, handling pagination."""
    headers = {"Referer": REFERER}
    all_features = []
    offset = 0
    while True:
        r = requests.get(
            f"{SERVICE_URL}/{layer_id}/query",
            params={
                "where": "1=1",
                "outFields": "*",
                "returnGeometry": str(return_geometry).lower(),
                "outSR": out_sr,
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


def agol_polygon_to_shapely(geom):
    """Convert AGOL polygon geometry to shapely."""
    rings = geom.get("rings", [])
    if not rings:
        return None
    # Build GeoJSON-like structure
    geojson = {"type": "Polygon", "coordinates": rings}
    try:
        return shape(geojson)
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(description="Link assessments to footprints")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    headers = {"Referer": REFERER}

    # Fetch footprints (layer 51) and assessment points (layer 2)
    log.info("Fetching building footprints (layer 51)...")
    footprints = fetch_all(51, token)
    log.info(f"  {len(footprints)} footprints")

    log.info("Fetching assessment points (layer 2)...")
    points = fetch_all(2, token)
    log.info(f"  {len(points)} assessment points")

    # Convert points to shapely
    point_data = []
    for p in points:
        geom = p.get("geometry", {})
        x, y = geom.get("x"), geom.get("y")
        if x is not None and y is not None:
            point_data.append({
                "shapely": Point(x, y),
                "attrs": p["attributes"],
            })
    log.info(f"  {len(point_data)} points with valid geometry")

    # Spatial join: for each footprint, find contained assessment points
    enriched = []
    matched_points = 0
    unmatched_footprints = 0

    for fp in footprints:
        fp_geom = fp.get("geometry")
        if not fp_geom:
            continue

        poly = agol_polygon_to_shapely(fp_geom)
        if poly is None or poly.is_empty:
            continue

        # Find points inside this footprint (use buffer for near-misses)
        buffered = poly.buffer(0.00005)  # ~5m tolerance
        contained = [pd for pd in point_data if buffered.contains(pd["shapely"])]

        # Build enriched attributes
        new_attrs = {
            "globalid": str(uuid.uuid4()),
        }

        if contained:
            # Use first match (or combine if multiple)
            primary = contained[0]["attrs"]
            for field in ASSESSMENT_FIELDS:
                new_attrs[field.lower()] = primary.get(field)

            if len(contained) > 1:
                addrs = [c["attrs"].get("ADDRESS_FULL", "") for c in contained]
                new_attrs["address_full"] = " | ".join(filter(None, addrs))

            new_attrs["nb_evaluations"] = len(contained)
            matched_points += len(contained)
        else:
            for field in ASSESSMENT_FIELDS:
                new_attrs[field.lower()] = None
            new_attrs["nb_evaluations"] = 0
            unmatched_footprints += 1

        enriched.append({
            "geometry": fp_geom,
            "attributes": new_attrs,
        })

    log.info(f"Spatial join: {matched_points} points matched to {len(enriched) - unmatched_footprints} footprints")
    log.info(f"  {unmatched_footprints} footprints with no assessment match")

    # Add new layer to feature service
    log.info("Adding enriched footprints layer to feature service...")
    layer_def = {
        "layers": [{
            "id": 53,
            "name": "Building Assessments (Footprints)",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPolygon",
            "objectIdField": "OBJECTID",
            "globalIdField": "globalid",
            "fields": [
                {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "Identifiant"},
                {"name": "globalid", "type": "esriFieldTypeGlobalID", "alias": "Identifiant global"},
                {"name": "address_full", "type": "esriFieldTypeString", "alias": "Adresse", "length": 255},
                {"name": "general_use", "type": "esriFieldTypeString", "alias": "Utilisation g\u00e9n\u00e9rale", "length": 50},
                {"name": "ba_building_type", "type": "esriFieldTypeString", "alias": "Type de b\u00e2timent", "length": 50},
                {"name": "business_name", "type": "esriFieldTypeString", "alias": "Nom du commerce", "length": 200},
                {"name": "vacancy_status", "type": "esriFieldTypeString", "alias": "Statut de vacance", "length": 100},
                {"name": "ba_condition_rating", "type": "esriFieldTypeInteger", "alias": "Cote de condition"},
                {"name": "ba_risk_band", "type": "esriFieldTypeString", "alias": "Niveau de risque", "length": 50},
                {"name": "ba_facade_material", "type": "esriFieldTypeString", "alias": "Mat\u00e9riau de fa\u00e7ade", "length": 50},
                {"name": "ba_storefront_status", "type": "esriFieldTypeString", "alias": "\u00c9tat du commerce", "length": 50},
                {"name": "ba_is_vacant", "type": "esriFieldTypeString", "alias": "Vacant", "length": 20},
                {"name": "ba_street_presence", "type": "esriFieldTypeString", "alias": "Pr\u00e9sence sur rue", "length": 50},
                {"name": "ba_is_neglected", "type": "esriFieldTypeString", "alias": "N\u00e9glig\u00e9", "length": 10},
                {"name": "architectural_style", "type": "esriFieldTypeString", "alias": "Style architectural", "length": 100},
                {"name": "hr_register_status", "type": "esriFieldTypeString", "alias": "Statut patrimonial", "length": 100},
                {"name": "hcd_contributing", "type": "esriFieldTypeString", "alias": "Contributif au DPC", "length": 20},
                {"name": "nb_evaluations", "type": "esriFieldTypeInteger", "alias": "Nombre d'\u00e9valuations"},
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
                        "color": [255, 170, 0, 80],
                        "outline": {
                            "type": "esriSLS",
                            "style": "esriSLSSolid",
                            "color": [230, 120, 0, 200],
                            "width": 1.5,
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
        data={"addToDefinition": json.dumps(layer_def), "token": token, "f": "json"},
        headers=headers, timeout=120,
    )
    result = r.json()
    if not result.get("success"):
        log.error(f"Failed to add layer: {result}")
        return

    # Find the actual layer ID
    r = requests.get(SERVICE_URL, params={"f": "json", "token": token},
                     headers=headers, timeout=60)
    svc = r.json()
    layer_id = None
    for l in svc.get("layers", []):
        if l["name"] == "Building Assessments (Footprints)":
            layer_id = l["id"]
            break

    if layer_id is None:
        log.error("Could not find new layer")
        return

    log.info(f"Layer created with ID {layer_id}")

    # Push features in batches
    log.info(f"Pushing {len(enriched)} enriched footprints...")
    batch_size = 100
    total_added = 0
    for i in range(0, len(enriched), batch_size):
        batch = enriched[i:i + batch_size]
        r = requests.post(
            f"{SERVICE_URL}/{layer_id}/addFeatures",
            data={"features": json.dumps(batch), "token": token, "f": "json"},
            headers=headers, timeout=120,
        )
        result = r.json()
        added = sum(1 for res in result.get("addResults", []) if res.get("success"))
        total_added += added
        failed = [res for res in result.get("addResults", []) if not res.get("success")]
        if failed:
            log.warning(f"  Batch {i // batch_size + 1}: {len(failed)} failures: {failed[0]}")
        log.info(f"  Batch {i // batch_size + 1}: {added}/{len(batch)} added")

    log.info(f"Total footprints added: {total_added}")

    # Add to web map in the Evaluation group
    log.info("Adding to web map...")
    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token},
        headers=headers, timeout=60,
    )
    webmap = r.json()

    # Build survey popup (same as building points)
    surveys = [
        ("a7c598edaf414f01bdcbe59074c7d516", "Sondage r\u00e9sidentiel"),
        ("dd843b550835400ebca7b182d5d1e7d4", "Sondage commercial"),
        ("a6cc1e6dc1a240bd9fc60c40e254ff5d", "Sondage passants"),
        ("2bb8e7130db543b5b4b883c72e60a94e", "Sondage \u00e9tudiant"),
        ("680d928040ee417aae4c8385c56fb577", "Suivi contact"),
    ]
    survey_links = "".join(
        f'<a href="https://survey123.arcgis.com/share/{fid}'
        f'?field:survey_address={{address_full}}"'
        f' target="_blank" style="display:inline-block;margin:4px 2px;'
        f'padding:8px 14px;background:#0079c1;color:white;'
        f'border-radius:4px;text-decoration:none;font-size:13px;">'
        f'{title}</a>'
        for fid, title in surveys
    )

    footprint_layer = {
        "id": f"layer_{layer_id}",
        "layerType": "ArcGISFeatureLayer",
        "url": f"{SERVICE_URL}/{layer_id}",
        "title": "\u00c9valuation par immeuble",
        "itemId": FEATURE_SERVICE_ITEM_ID,
        "visibility": True,
        "opacity": 0.7,
        "popupInfo": {
            "title": "{address_full}",
            "description": (
                '<div style="font-family:sans-serif;padding:4px;">'
                '<h3 style="margin:0 0 6px 0;font-size:15px;">{address_full}</h3>'
                '<table style="font-size:12px;border-collapse:collapse;width:100%;margin-bottom:10px;">'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Utilisation</td><td>{general_use}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Type</td><td>{ba_building_type}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Commerce</td><td>{business_name}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Vacance</td><td>{vacancy_status}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Condition</td><td>{ba_condition_rating}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Risque</td><td>{ba_risk_band}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Fa\u00e7ade</td><td>{ba_facade_material}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Style</td><td>{architectural_style}</td></tr>'
                '<tr><td style="padding:3px 8px 3px 0;color:#555;">Patrimoine</td><td>{hr_register_status}</td></tr>'
                '</table>'
                '<div style="margin-top:8px;">'
                '<p style="font-size:12px;color:#555;margin:0 0 6px 0;">Lancer un sondage :</p>'
                + survey_links
                + '</div></div>'
            ),
        },
    }

    # Add to Evaluation group
    for group in webmap["operationalLayers"]:
        if group.get("layerType") == "GroupLayer":
            title = group.get("title", "")
            if "valuation" in title.lower() or "batiment" in title.lower():
                group["layers"].insert(0, footprint_layer)
                log.info(f"Added to group: {title}")
                break

    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    if r.json().get("success"):
        log.info("Web map updated!")
        log.info(f"View: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")
    else:
        log.error(f"Web map update failed: {r.json()}")


if __name__ == "__main__":
    main()
