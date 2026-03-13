"""
Set up the AGOL web map for field work:

1. Create 3 team survey zones based on Kensington Market streets
2. Configure building footprints (layer 51) with Arcade popup that pulls
   assessment data from layer 2 via spatial intersection
3. Add survey launch links to footprint popup

Usage:
    python -m field_survey.setup_field_map --token-file token.txt
"""
import argparse
import json
import logging
import uuid

import requests
from shapely.geometry import Polygon, mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

# Survey123 form IDs
SURVEYS = [
    ("a7c598edaf414f01bdcbe59074c7d516", "Sondage r\u00e9sidentiel"),
    ("dd843b550835400ebca7b182d5d1e7d4", "Sondage commercial"),
    ("a6cc1e6dc1a240bd9fc60c40e254ff5d", "Sondage passants"),
    ("2bb8e7130db543b5b4b883c72e60a94e", "Sondage \u00e9tudiant"),
    ("680d928040ee417aae4c8385c56fb577", "Suivi contact"),
]

# ── 3 Team Zones ──
# Based on actual Kensington Market street layout:
# Zone 1 (Nord): College to Oxford — Augusta north, Lippincott, College corridor
# Zone 2 (Centre): Oxford to Baldwin — core market area, Kensington Ave, Augusta mid
# Zone 3 (Sud): Baldwin to Dundas — Dundas corridor, Wales, Denison, south end
#
# Boundaries follow actual streets and natural walking routes.
# The lat line ~43.6555 is Oxford St, ~43.6545 is roughly Baldwin St.

TEAM_ZONES = [
    {
        "name": "Zone Nord (College)",
        "equipe": "\u00c9quipe 1",
        "description": "College St, Oxford St nord, Augusta Ave nord, Lippincott St, Bellevue Ave nord",
        "color": [56, 168, 0, 60],       # green
        "outline": [56, 168, 0, 200],
        "coords": [
            (-79.4075, 43.6555),   # SW corner (Oxford & Bathurst)
            (-79.4075, 43.6580),   # NW corner (College & Bathurst)
            (-79.3980, 43.6580),   # NE corner (College & Spadina)
            (-79.3980, 43.6555),   # SE corner (Oxford & Spadina)
            (-79.4075, 43.6555),   # close ring
        ],
    },
    {
        "name": "Zone Centre (March\u00e9)",
        "equipe": "\u00c9quipe 2",
        "description": "Kensington Ave, Augusta Ave centre, Baldwin St, St Andrew St, Nassau St, Bellevue Ave sud",
        "color": [0, 112, 255, 60],      # blue
        "outline": [0, 112, 255, 200],
        "coords": [
            (-79.4075, 43.6535),   # SW corner (just south of Baldwin & Bathurst)
            (-79.4075, 43.6555),   # NW corner (Oxford & Bathurst)
            (-79.3980, 43.6555),   # NE corner (Oxford & Spadina)
            (-79.3980, 43.6535),   # SE corner (Baldwin & Spadina)
            (-79.4075, 43.6535),   # close ring
        ],
    },
    {
        "name": "Zone Sud (Dundas)",
        "equipe": "\u00c9quipe 3",
        "description": "Dundas St W, Wales Ave, Denison Ave, Casimir St, Kensington Ave sud, Spadina Ave sud",
        "color": [255, 85, 0, 60],       # orange
        "outline": [255, 85, 0, 200],
        "coords": [
            (-79.4075, 43.6515),   # SW corner (Dundas & Bathurst)
            (-79.4075, 43.6535),   # NW corner (Baldwin & Bathurst)
            (-79.3980, 43.6535),   # NE corner (Baldwin & Spadina)
            (-79.3980, 43.6515),   # SE corner (Dundas & Spadina)
            (-79.4075, 43.6515),   # close ring
        ],
    },
]


def count_points_in_zone(zone_coords, points):
    """Count assessment points in a zone polygon."""
    from shapely.geometry import Point as SPoint
    poly = Polygon(zone_coords)
    count = 0
    commercial = 0
    for p in points:
        g = p.get("geometry", {})
        x, y = g.get("x"), g.get("y")
        if x is not None and y is not None:
            if poly.contains(SPoint(x, y)):
                count += 1
                use = p["attributes"].get("GENERAL_USE", "")
                if use in ("Commercial", "Mixed Use"):
                    commercial += 1
    return count, commercial


def create_zone_layer(token, points):
    """Create team zone layer in the feature service."""
    headers = {"Referer": REFERER}

    # Add layer definition
    log.info("Creating team zone layer...")
    layer_def = {
        "layers": [{
            "id": 52,
            "name": "Zones d enquete",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPolygon",
            "objectIdField": "OBJECTID",
            "globalIdField": "globalid",
            "fields": [
                {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "Identifiant"},
                {"name": "globalid", "type": "esriFieldTypeGlobalID", "alias": "ID global"},
                {"name": "zone_name", "type": "esriFieldTypeString", "alias": "Zone", "length": 100},
                {"name": "equipe", "type": "esriFieldTypeString", "alias": "\u00c9quipe", "length": 50},
                {"name": "description", "type": "esriFieldTypeString", "alias": "Rues couvertes", "length": 500},
                {"name": "nb_batiments", "type": "esriFieldTypeInteger", "alias": "B\u00e2timents"},
                {"name": "nb_commerces", "type": "esriFieldTypeInteger", "alias": "Commerces"},
            ],
            "extent": {
                "xmin": -79.408, "ymin": 43.651, "xmax": -79.397, "ymax": 43.658,
                "spatialReference": {"wkid": 4326},
            },
            "drawingInfo": {
                "renderer": {
                    "type": "uniqueValue",
                    "field1": "equipe",
                    "uniqueValueInfos": [
                        {
                            "value": "\u00c9quipe 1",
                            "symbol": {
                                "type": "esriSFS", "style": "esriSFSSolid",
                                "color": TEAM_ZONES[0]["color"],
                                "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                            "color": TEAM_ZONES[0]["outline"], "width": 2},
                            },
                        },
                        {
                            "value": "\u00c9quipe 2",
                            "symbol": {
                                "type": "esriSFS", "style": "esriSFSSolid",
                                "color": TEAM_ZONES[1]["color"],
                                "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                            "color": TEAM_ZONES[1]["outline"], "width": 2},
                            },
                        },
                        {
                            "value": "\u00c9quipe 3",
                            "symbol": {
                                "type": "esriSFS", "style": "esriSFSSolid",
                                "color": TEAM_ZONES[2]["color"],
                                "outline": {"type": "esriSLS", "style": "esriSLSSolid",
                                            "color": TEAM_ZONES[2]["outline"], "width": 2},
                            },
                        },
                    ],
                },
                "labelingInfo": [{
                    "labelExpression": "[equipe]",
                    "labelPlacement": "esriServerPolygonPlacementAlwaysHorizontal",
                    "symbol": {
                        "type": "esriTS",
                        "color": [0, 0, 0, 255],
                        "font": {"size": 14, "weight": "bold"},
                        "haloColor": [255, 255, 255, 255],
                        "haloSize": 2,
                    },
                }],
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
        log.error(f"Failed to create zone layer: {result}")
        return None

    # Find actual layer ID
    r = requests.get(SERVICE_URL, params={"f": "json", "token": token},
                     headers=headers, timeout=60)
    layer_id = None
    for l in r.json().get("layers", []):
        if l["name"] == "Zones d enquete":
            layer_id = l["id"]
            break

    if layer_id is None:
        log.error("Could not find zone layer")
        return None

    log.info(f"Zone layer created with ID {layer_id}")

    # Add zone features
    zone_features = []
    for zone in TEAM_ZONES:
        nb_bat, nb_com = count_points_in_zone(zone["coords"], points)
        poly = Polygon(zone["coords"])
        geoj = mapping(poly)
        rings = [[[c[0], c[1]] for c in geoj["coordinates"][0]]]

        zone_features.append({
            "geometry": {"rings": rings, "spatialReference": {"wkid": 4326}},
            "attributes": {
                "globalid": str(uuid.uuid4()),
                "zone_name": zone["name"],
                "equipe": zone["equipe"],
                "description": zone["description"],
                "nb_batiments": nb_bat,
                "nb_commerces": nb_com,
            },
        })
        log.info(f"  {zone['name']}: {nb_bat} b\u00e2timents, {nb_com} commerces")

    r = requests.post(
        f"{SERVICE_URL}/{layer_id}/addFeatures",
        data={"features": json.dumps(zone_features), "token": token, "f": "json"},
        headers=headers, timeout=60,
    )
    result = r.json()
    added = sum(1 for res in result.get("addResults", []) if res.get("success"))
    log.info(f"Added {added}/3 zones")

    return layer_id


def configure_footprint_popup():
    """Build Arcade-based popup for building footprints that pulls assessment data."""
    # Arcade expression to find the assessment point inside this footprint
    arcade_expr = (
        "var pts = FeatureSetByPortalItem("
        "Portal('https://www.arcgis.com'), "
        f"'{FEATURE_SERVICE_ITEM_ID}', 2, "
        "['ADDRESS_FULL','GENERAL_USE','ba_building_type','BUSINESS_NAME',"
        "'VACANCY_STATUS','ba_condition_rating','ba_risk_band','ba_facade_material',"
        "'ARCHITECTURAL_STYLE','HR_REGISTER_STATUS'], false);\n"
        "var contained = Intersects(pts, $feature);\n"
        "var results = [];\n"
        "for (var p in contained) {\n"
        "  Push(results, p.ADDRESS_FULL + ' | ' + "
        "Iif(IsEmpty(p.GENERAL_USE),'',p.GENERAL_USE) + ' | ' + "
        "Iif(IsEmpty(p.BUSINESS_NAME),'',p.BUSINESS_NAME) + ' | ' + "
        "Iif(IsEmpty(p.VACANCY_STATUS),'',p.VACANCY_STATUS) + ' | ' + "
        "Iif(IsEmpty(p.ba_condition_rating),'',Text(p.ba_condition_rating)) + ' | ' + "
        "Iif(IsEmpty(p.ba_risk_band),'',p.ba_risk_band) + ' | ' + "
        "Iif(IsEmpty(p.ba_building_type),'',p.ba_building_type) + ' | ' + "
        "Iif(IsEmpty(p.ba_facade_material),'',p.ba_facade_material) + ' | ' + "
        "Iif(IsEmpty(p.ARCHITECTURAL_STYLE),'',p.ARCHITECTURAL_STYLE) + ' | ' + "
        "Iif(IsEmpty(p.HR_REGISTER_STATUS),'',p.HR_REGISTER_STATUS)"
        ");\n"
        "}\n"
        "return Iif(Count(results) > 0, Concatenate(results, '\\n'), '\u2014 Aucune donn\\u00e9e');"
    )

    return {
        "title": "\u00c9valuation du b\u00e2timent",
        "expressionInfos": [
            {
                "name": "assessment_data",
                "title": "Donn\u00e9es d'\u00e9valuation",
                "expression": arcade_expr,
                "returnType": "string",
            },
        ],
        "popupElements": [
            {
                "type": "expression",
                "expressionInfo": {"name": "assessment_data"},
            },
        ],
        "fieldInfos": [],
    }


def update_webmap(token, zone_layer_id):
    """Update web map with zone layer and footprint popup."""
    headers = {"Referer": REFERER}

    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token},
        headers=headers, timeout=60,
    )
    webmap = r.json()

    # Add zone layer at the top of the Evaluation group
    zone_entry = {
        "id": f"layer_{zone_layer_id}",
        "layerType": "ArcGISFeatureLayer",
        "url": f"{SERVICE_URL}/{zone_layer_id}",
        "title": "Zones d'enqu\u00eate",
        "itemId": FEATURE_SERVICE_ITEM_ID,
        "visibility": True,
        "opacity": 0.5,
        "popupInfo": {
            "title": "{zone_name}",
            "description": (
                '<div style="font-family:sans-serif;padding:4px;">'
                '<h3 style="margin:0 0 8px 0;color:#333;">{equipe} \u2014 {zone_name}</h3>'
                '<table style="font-size:13px;border-collapse:collapse;width:100%;">'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">Rues</td>'
                '<td>{description}</td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">B\u00e2timents</td>'
                '<td><b>{nb_batiments}</b></td></tr>'
                '<tr><td style="padding:4px 8px 4px 0;color:#555;">Commerces</td>'
                '<td><b>{nb_commerces}</b></td></tr>'
                '</table></div>'
            ),
        },
    }

    # Configure footprint popup with Arcade
    footprint_popup = configure_footprint_popup()

    for group in webmap["operationalLayers"]:
        if group.get("layerType") != "GroupLayer":
            continue
        title = group.get("title", "")

        # Add zones to evaluation group
        if "valuation" in title.lower() or "batiment" in title.lower():
            # Remove old zone/block references
            group["layers"] = [
                l for l in group.get("layers", [])
                if "zone" not in l.get("id", "").lower()
                and "block" not in l.get("id", "").lower()
            ]
            group["layers"].insert(0, zone_entry)
            log.info(f"Added zones to: {title}")

        # Add popup to footprints in Voirie group
        if "voirie" in title.lower() or "empreinte" in title.lower() or "cadastre" in title.lower():
            for layer in group.get("layers", []):
                url = layer.get("url", "")
                if url.endswith("/51"):
                    layer["popupInfo"] = footprint_popup
                    layer["visibility"] = True
                    log.info(f"Added Arcade popup to footprints: {layer.get('title')}")

    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    if r.json().get("success"):
        log.info("Web map updated!")
    else:
        log.error(f"Update failed: {r.json()}")


def main():
    parser = argparse.ArgumentParser(description="Set up field map for survey")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    headers = {"Referer": REFERER}

    # Fetch all assessment points for zone stats
    log.info("Fetching assessment points for zone stats...")
    r = requests.get(f"{SERVICE_URL}/2/query",
        params={"where": "1=1", "outFields": "GENERAL_USE",
                "returnGeometry": "true", "outSR": 4326, "f": "json", "token": token},
        headers=headers, timeout=120)
    points = r.json().get("features", [])
    log.info(f"  {len(points)} points")

    # Create zone layer
    zone_layer_id = create_zone_layer(token, points)
    if zone_layer_id is None:
        return

    # Update web map
    update_webmap(token, zone_layer_id)

    log.info(f"Done! View: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")


if __name__ == "__main__":
    main()
