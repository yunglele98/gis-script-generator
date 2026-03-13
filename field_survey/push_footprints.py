"""
Push spatially joined footprints to AGOL layer 51.

Replaces existing features with enriched footprints containing assessment data.
Adds survey launch links to popup.

Usage:
    python -m field_survey.push_footprints --token-file token.txt
"""
import argparse
import json
import logging
import uuid

import geopandas as gpd
import requests
from shapely.geometry import mapping

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

STR_FIELDS = [
    ("address_full", "Adresse", 255),
    ("general_use", "Utilisation", 50),
    ("ba_building_type", "Type de b\u00e2timent", 50),
    ("business_name", "Commerce", 200),
    ("vacancy_status", "Statut de vacance", 100),
    ("ba_risk_band", "Niveau de risque", 50),
    ("ba_facade_material", "Mat\u00e9riau de fa\u00e7ade", 50),
    ("ba_storefront_status", "\u00c9tat du commerce", 50),
    ("architectural_style", "Style architectural", 100),
    ("hr_register_status", "Patrimoine", 100),
    ("hcd_contributing", "Contributif DPC", 20),
    ("ba_street_presence", "Pr\u00e9sence sur rue", 50),
    ("ba_is_neglected", "N\u00e9glig\u00e9", 10),
    ("ba_is_vacant", "Vacant", 20),
]

SURVEYS = [
    ("a7c598edaf414f01bdcbe59074c7d516", "Sondage r\u00e9sidentiel"),
    ("dd843b550835400ebca7b182d5d1e7d4", "Sondage commercial"),
    ("a6cc1e6dc1a240bd9fc60c40e254ff5d", "Sondage passants"),
    ("2bb8e7130db543b5b4b883c72e60a94e", "Sondage \u00e9tudiant"),
    ("680d928040ee417aae4c8385c56fb577", "Suivi contact"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    headers = {"Referer": REFERER}

    # Load joined geojson
    log.info("Loading joined footprints...")
    result = gpd.read_file(
        "C:/Users/liam1/gis-script-generator/field_survey/kensington_footprints_joined.geojson"
    )
    log.info(f"  {len(result)} footprints ({(result['nb_evaluations'] > 0).sum()} with data)")

    # Delete existing features
    log.info("Deleting existing features from layer 51...")
    r = requests.post(
        f"{SERVICE_URL}/51/deleteFeatures",
        data={"where": "1=1", "token": token, "f": "json"},
        headers=headers, timeout=120,
    )
    log.info(f"  Deleted: {len(r.json().get('deleteResults', []))}")

    # Add new fields
    log.info("Adding assessment fields to layer 51...")
    new_fields = []
    for fname, alias, length in STR_FIELDS:
        new_fields.append({
            "name": fname, "type": "esriFieldTypeString",
            "alias": alias, "length": length, "nullable": True, "editable": True,
        })
    new_fields.append({
        "name": "ba_condition_rating", "type": "esriFieldTypeInteger",
        "alias": "Cote de condition", "nullable": True, "editable": True,
    })
    new_fields.append({
        "name": "nb_evaluations", "type": "esriFieldTypeInteger",
        "alias": "Nombre d'\u00e9valuations", "nullable": True, "editable": True,
    })

    r = requests.post(
        f"{ADMIN_URL}/51/addToDefinition",
        data={"addToDefinition": json.dumps({"fields": new_fields}), "token": token, "f": "json"},
        headers=headers, timeout=120,
    )
    add_result = r.json()
    if add_result.get("success"):
        log.info("  Fields added")
    else:
        log.info(f"  Fields result: {add_result}")

    # Prepare features
    log.info("Preparing features for upload...")
    agol_features = []
    for _, row in result.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue

        try:
            geoj = mapping(geom)
            if geoj["type"] == "Polygon":
                rings = [[[c[0], c[1]] for c in ring] for ring in geoj["coordinates"]]
            elif geoj["type"] == "MultiPolygon":
                rings = [[[c[0], c[1]] for c in geoj["coordinates"][0][0]]]
            else:
                continue
        except Exception:
            continue

        attrs = {"globalid": str(uuid.uuid4())}

        # Integer fields
        for int_field in ["ba_condition_rating", "nb_evaluations"]:
            val = row.get(int_field)
            if val is not None and str(val) not in ("", "nan", "None", "NaN"):
                try:
                    attrs[int_field] = int(float(val))
                except (ValueError, TypeError):
                    attrs[int_field] = None
            else:
                attrs[int_field] = 0 if int_field == "nb_evaluations" else None

        # String fields
        for fname, _, length in STR_FIELDS:
            # Find column (case-insensitive)
            col = None
            for c in result.columns:
                if c.lower() == fname.lower():
                    col = c
                    break
            val = row.get(col) if col else None
            if val is not None and str(val) not in ("", "nan", "None", "NaN"):
                attrs[fname] = str(val)[:length]
            else:
                attrs[fname] = None

        agol_features.append({
            "geometry": {"rings": rings, "spatialReference": {"wkid": 4326}},
            "attributes": attrs,
        })

    log.info(f"  {len(agol_features)} features ready")

    # Upload in batches
    log.info("Uploading...")
    total_added = 0
    batch_size = 50
    for i in range(0, len(agol_features), batch_size):
        batch = agol_features[i:i + batch_size]
        r = requests.post(
            f"{SERVICE_URL}/51/addFeatures",
            data={"features": json.dumps(batch), "token": token, "f": "json"},
            headers=headers, timeout=120,
        )
        rj = r.json()
        added = sum(1 for res in rj.get("addResults", []) if res.get("success"))
        failed_list = [res for res in rj.get("addResults", []) if not res.get("success")]
        total_added += added

        # Retry failures one by one
        if failed_list:
            for j, res in enumerate(rj.get("addResults", [])):
                if not res.get("success"):
                    r2 = requests.post(
                        f"{SERVICE_URL}/51/addFeatures",
                        data={"features": json.dumps([batch[j]]), "token": token, "f": "json"},
                        headers=headers, timeout=60,
                    )
                    if r2.json().get("addResults", [{}])[0].get("success"):
                        total_added += 1

        if (i // batch_size) % 5 == 0:
            log.info(f"  Progress: {total_added}/{i + len(batch)}")

    log.info(f"Total uploaded: {total_added}/{len(agol_features)}")

    # Update web map popup
    log.info("Updating web map...")
    survey_links = ""
    for fid, title in SURVEYS:
        survey_links += (
            '<a href="https://survey123.arcgis.com/share/' + fid
            + '?field:survey_address={address_full}"'
            + ' target="_blank" style="display:inline-block;margin:3px 2px;'
            + 'padding:7px 12px;background:#0079c1;color:white;'
            + 'border-radius:4px;text-decoration:none;font-size:12px;">'
            + title + '</a>'
        )

    popup = {
        "title": "{address_full}",
        "description": (
            '<div style="font-family:sans-serif;padding:4px;">'
            '<h3 style="margin:0 0 6px 0;font-size:14px;">{address_full}</h3>'
            '<table style="font-size:12px;border-collapse:collapse;width:100%;margin-bottom:8px;">'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Utilisation</td><td>{general_use}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Type</td><td>{ba_building_type}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Commerce</td><td>{business_name}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Vacance</td><td>{vacancy_status}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Condition</td><td>{ba_condition_rating}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Risque</td><td>{ba_risk_band}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Fa\u00e7ade</td><td>{ba_facade_material}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Style</td><td>{architectural_style}</td></tr>'
            '<tr><td style="padding:3px 6px 3px 0;color:#555;">Patrimoine</td><td>{hr_register_status}</td></tr>'
            '</table>'
            '<div style="margin-top:6px;">'
            '<p style="font-size:11px;color:#555;margin:0 0 4px 0;">Lancer un sondage :</p>'
            + survey_links
            + '</div></div>'
        ),
    }

    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token}, headers=headers, timeout=60,
    )
    webmap = r.json()

    for group in webmap.get("operationalLayers", []):
        if group.get("layerType") != "GroupLayer":
            continue
        for layer in group.get("layers", []):
            if layer.get("url", "").endswith("/51"):
                layer["popupInfo"] = popup
                layer["title"] = "\u00c9valuation par immeuble"
                layer["visibility"] = True
                log.info(f"  Updated: {layer['title']}")

    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    log.info(f"  Web map: {r.json().get('success')}")
    log.info(f"View: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")


if __name__ == "__main__":
    main()
