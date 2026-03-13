"""
Add Survey123 form layers to the AGOL web map and configure building assessment
popup with Survey123 launch links for field teams.

Usage:
    python -m field_survey.add_surveys_to_webmap --token-file token.txt
"""
import argparse
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"
WEBMAP_ITEM_ID = "597d45ca0eda44abbe8806c7736be0bf"
FEATURE_SERVICE_ITEM_ID = "6eb29dbc44374434ba5a8d8c6284a6de"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"

# Survey123 forms: (form_item_id, feature_service_item_id, feature_service_url, french_title)
SURVEYS = [
    (
        "a7c598edaf414f01bdcbe59074c7d516",
        "dfc18f0d4341418091c2706f2dae0780",
        "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_19ca210fff7240229d0cb3e4745f6eb0/FeatureServer/0",
        "Sondage r\u00e9sidentiel",
    ),
    (
        "dd843b550835400ebca7b182d5d1e7d4",
        "309d87d336bd4bcab2f959078f79cd84",
        "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_dfb0dc55eb4741bab9e7e0f35559bae9/FeatureServer/0",
        "Sondage commercial",
    ),
    (
        "a6cc1e6dc1a240bd9fc60c40e254ff5d",
        "68e0b727d7db44368e48994433982e8e",
        "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_777b4c2c4c894383b60a7e89537930ff/FeatureServer/0",
        "Sondage passants",
    ),
    (
        "2bb8e7130db543b5b4b883c72e60a94e",
        "66313a9bb631429e8cff2385ae44f088",
        "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_82a0a794cdd54e2da9cca4d715924788/FeatureServer/0",
        "Sondage \u00e9tudiant",
    ),
    (
        "680d928040ee417aae4c8385c56fb577",
        "833194a21ef04b5a9f8671db75ea666f",
        "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_9f1123b11dc5498ba14fcee11052dd95_form/FeatureServer/0",
        "Suivi contact",
    ),
]


def build_survey_popup():
    """Build a popup for building assessment points with Survey123 launch links."""
    # Survey123 URL scheme: arcgis-survey123://?itemID=<form>&field:address=<value>
    # For web: https://survey123.arcgis.com/share/<form>?field:address=<value>

    survey_links = []
    for form_id, _, _, title in SURVEYS:
        survey_links.append(
            f'<a href="https://survey123.arcgis.com/share/{form_id}'
            f'?field:survey_address={{ADDRESS_FULL}}'
            f'&field:survey_location_lat={{GEO_LATITUDE}}'
            f'&field:survey_location_lon={{GEO_LONGITUDE}}"'
            f' target="_blank" style="display:inline-block;margin:4px 2px;'
            f'padding:8px 14px;background:#0079c1;color:white;'
            f'border-radius:4px;text-decoration:none;font-size:13px;">'
            f'{title}</a>'
        )

    popup_html = (
        '<div style="font-family:sans-serif;padding:4px;">'
        '<h3 style="margin:0 0 6px 0;font-size:15px;">{ADDRESS_FULL}</h3>'
        '<table style="font-size:12px;border-collapse:collapse;width:100%;margin-bottom:10px;">'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Utilisation</td><td>{GENERAL_USE}</td></tr>'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Type</td><td>{ba_building_type}</td></tr>'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Commerce</td><td>{BUSINESS_NAME}</td></tr>'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Vacance</td><td>{VACANCY_STATUS}</td></tr>'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Condition</td><td>{ba_condition_rating}</td></tr>'
        '<tr><td style="padding:3px 8px 3px 0;color:#555;">Risque</td><td>{ba_risk_band}</td></tr>'
        '</table>'
        '<div style="margin-top:8px;">'
        '<p style="font-size:12px;color:#555;margin:0 0 6px 0;">Lancer un sondage :</p>'
        + "\n".join(survey_links)
        + '</div></div>'
    )

    return {
        "title": "{ADDRESS_FULL}",
        "description": popup_html,
        "fieldInfos": [
            {"fieldName": "ADDRESS_FULL", "label": "Adresse", "visible": True},
            {"fieldName": "GENERAL_USE", "label": "Utilisation", "visible": True},
            {"fieldName": "ba_building_type", "label": "Type de b\u00e2timent", "visible": True},
            {"fieldName": "BUSINESS_NAME", "label": "Commerce", "visible": True},
            {"fieldName": "VACANCY_STATUS", "label": "Vacance", "visible": True},
            {"fieldName": "ba_condition_rating", "label": "Condition", "visible": True},
            {"fieldName": "ba_risk_band", "label": "Risque", "visible": True},
            {"fieldName": "GEO_LATITUDE", "label": "Latitude", "visible": False},
            {"fieldName": "GEO_LONGITUDE", "label": "Longitude", "visible": False},
        ],
        "popupElements": [
            {"type": "text", "text": popup_html},
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="Add surveys to AGOL web map")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    headers = {"Referer": REFERER}

    # Get current web map
    log.info("Fetching web map...")
    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token},
        headers=headers, timeout=60,
    )
    webmap = r.json()

    # 1. Add survey layers as a group
    survey_children = []
    for form_id, svc_id, svc_url, title in SURVEYS:
        survey_children.append({
            "id": f"survey_{form_id[:8]}",
            "layerType": "ArcGISFeatureLayer",
            "url": svc_url,
            "title": title,
            "itemId": svc_id,
            "visibility": False,
            "opacity": 0.7,
        })

    survey_group = {
        "id": "group_sondages",
        "layerType": "GroupLayer",
        "title": "Sondages (Survey123)",
        "visibility": True,
        "layers": survey_children,
    }

    # Remove existing survey group if present
    webmap["operationalLayers"] = [
        l for l in webmap["operationalLayers"]
        if l.get("id") != "group_sondages"
    ]

    # Add survey group at the top
    webmap["operationalLayers"].insert(0, survey_group)
    log.info(f"Added Sondages group with {len(survey_children)} survey layers")

    # 2. Configure popup on building assessment layer (layer 2)
    popup = build_survey_popup()
    for group in webmap["operationalLayers"]:
        if group.get("layerType") != "GroupLayer":
            continue
        for layer in group.get("layers", []):
            url = layer.get("url", "")
            if url.endswith("/2"):
                layer["popupInfo"] = popup
                log.info(f"Added survey launch popup to: {layer.get('title')}")

    # 3. Also add popup to the filtered commercial layer
    for group in webmap["operationalLayers"]:
        if group.get("layerType") != "GroupLayer":
            continue
        for layer in group.get("layers", []):
            if layer.get("id", "").endswith("_filtered"):
                layer["popupInfo"] = popup
                log.info(f"Added survey launch popup to: {layer.get('title')}")

    # Push update
    log.info("Updating web map...")
    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers=headers, timeout=120,
    )
    result = r.json()

    if result.get("success"):
        log.info("Web map updated successfully!")
        log.info(f"View: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")
    else:
        log.error(f"Update failed: {result}")


if __name__ == "__main__":
    main()
