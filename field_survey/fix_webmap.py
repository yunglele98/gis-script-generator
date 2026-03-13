"""
Regroup loose layers in the AGOL web map.

Keeps existing groups (Infrastructure/transport, Environnement, Voirie/empreintes/cadastre)
and regroups loose layers into:
- Évaluation des bâtiments (all building-related)
- Services communautaires
- Économie / Emploi (+ business survey + filtered commercial points)

Usage:
    python -m field_survey.fix_webmap --token-file token.txt
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

BUSINESS_SURVEY_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/service_dfb0dc55eb4741bab9e7e0f35559bae9/FeatureServer/0"
BUSINESS_SURVEY_ITEM_ID = "f49eca888bdb49ee9a38b028b639dfe6"

LAYER_TITLES_FR = {
    0: "Type de bâtiment (épingles)",
    1: "Poteaux de services publics",
    2: "Points d'évaluation des bâtiments",
    3: "Supports à vélos",
    4: "Abribus",
    5: "Logement social",
    6: "Lieux de culte",
    7: "Hôpitaux",
    8: "Écoles",
    9: "Registre du patrimoine",
    10: "Arbres de rue",
    11: "Réseau piétonnier",
    12: "Axes routiers",
    13: "Logement communautaire",
    14: "Points d'emploi",
    15: "Style architectural",
    16: "Contribution au DPC",
    17: "Zone morphologique",
    18: "Logement communautaire",
    19: "Points d'emploi",
    20: "Matériau de façade",
    21: "Zone d'influence du DPC",
    22: "Zones de politique de zonage",
    23: "Limites de hauteur de zonage",
    24: "Secteur Kensington-Chinatown",
    25: "Couverture du sol",
    26: "Canopée des arbres",
    27: "Stationnements",
    28: "Trottoirs",
    29: "Surfaces de route",
    30: "Vacance",
    31: "Période de construction",
    32: "Statut patrimonial",
    34: "Gentrification",
    35: "Pression de gentrification",
    36: "Densité ISP",
    37: "Couverture du lot",
    38: "Unités d'habitation",
    39: "Utilisation du sol",
    40: "Valeur foncière",
    41: "Score de risque",
    42: "Cote de condition",
    43: "Hauteur du bâtiment",
    44: "Toiture solaire",
    45: "Époque de construction",
    47: "Ruelles",
    48: "Réseau cyclable",
    49: "Espaces verts",
    50: "Limites de propriété",
    51: "Empreintes de bâtiments",
}


def get_webmap_data(token):
    """Fetch current web map JSON."""
    url = f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data"
    r = requests.get(url, params={"f": "json", "token": token},
                     headers={"Referer": REFERER}, timeout=60)
    r.raise_for_status()
    return r.json()


def build_layer(layer_id, visible=False, opacity=1.0):
    """Build a proper operationalLayer entry for a feature layer."""
    title = LAYER_TITLES_FR.get(layer_id, f"Couche {layer_id}")
    return {
        "id": f"layer_{layer_id}",
        "layerType": "ArcGISFeatureLayer",
        "url": f"{SERVICE_URL}/{layer_id}",
        "title": title,
        "itemId": FEATURE_SERVICE_ITEM_ID,
        "visibility": visible,
        "opacity": opacity,
    }


def build_filtered_layer(layer_id, title, definition_expression, visible=False):
    """Build a layer with a definition expression filter."""
    layer = build_layer(layer_id, visible=visible)
    layer["id"] = f"layer_{layer_id}_filtered"
    layer["title"] = title
    layer["layerDefinition"] = {
        "definitionExpression": definition_expression,
    }
    return layer


def build_external_layer(url, item_id, title, visible=False):
    """Build a layer referencing an external feature service."""
    return {
        "id": f"external_{item_id}",
        "layerType": "ArcGISFeatureLayer",
        "url": url,
        "title": title,
        "itemId": item_id,
        "visibility": visible,
        "opacity": 1.0,
    }


def build_group(title, children, visible=True):
    """Build a group layer containing child layers."""
    return {
        "id": f"group_{title.lower().replace(' ', '_').replace('é', 'e').replace('â', 'a').replace('î', 'i').replace('/', '_')}",
        "layerType": "GroupLayer",
        "title": title,
        "visibility": visible,
        "layers": children,
    }


def fix_webmap(token):
    """Regroup loose layers, keeping existing groups intact."""
    log.info("Fetching current web map data...")
    webmap = get_webmap_data(token)

    # Separate existing groups from loose layers
    existing_groups = []
    loose_layers = []
    for layer in webmap.get("operationalLayers", []):
        if layer.get("layerType") == "GroupLayer":
            existing_groups.append(layer)
        else:
            loose_layers.append(layer)

    log.info(f"Found {len(existing_groups)} existing groups, {len(loose_layers)} loose layers")
    for g in existing_groups:
        log.info(f"  Keeping group: {g.get('title')} ({len(g.get('layers',[]))} layers)")

    # Build new groups for loose layers
    # 1. Évaluation des bâtiments
    eval_layer_ids = [
        2, 9, 32, 21, 16, 15, 20, 31, 45,
        34, 35, 30,
        43, 42, 41, 40, 39, 38, 37, 36, 44, 17, 25, 0,
    ]
    eval_children = [build_layer(lid, visible=(lid == 2)) for lid in eval_layer_ids]
    eval_group = build_group("Évaluation des bâtiments", eval_children)

    # 2. Services communautaires
    svc_layer_ids = [5, 18, 13, 8, 7, 6]
    svc_children = [build_layer(lid) for lid in svc_layer_ids]
    svc_group = build_group("Services communautaires", svc_children)

    # 3. Économie / Emploi
    econ_children = [
        build_layer(14),
        build_layer(19),
        build_external_layer(
            BUSINESS_SURVEY_URL, BUSINESS_SURVEY_ITEM_ID,
            "Sondage commercial (Survey123)",
        ),
        build_filtered_layer(
            2, "Commerces (~543 points)",
            "GENERAL_USE IN ('Commercial','Mixed Use')",
        ),
    ]
    econ_group = build_group("Économie / Emploi", econ_children)

    # Assemble: existing groups + new groups
    operational_layers = existing_groups + [eval_group, svc_group, econ_group]

    # Check for any layers that fell through the cracks
    all_grouped_ids = set(eval_layer_ids + svc_layer_ids + [14, 19])
    # IDs already in existing groups
    for g in existing_groups:
        for child in g.get("layers", []):
            url = child.get("url", "")
            try:
                lid = int(url.rstrip("/").split("/")[-1])
                all_grouped_ids.add(lid)
            except (ValueError, IndexError):
                pass
    # Zonage layers — add as a small group if not already grouped
    zonage_ids = [22, 23, 24]
    if not any(lid in all_grouped_ids for lid in zonage_ids):
        zonage_children = [build_layer(lid) for lid in zonage_ids]
        operational_layers.append(build_group("Zonage et politiques", zonage_children))
        for lid in zonage_ids:
            all_grouped_ids.add(lid)

    webmap["operationalLayers"] = operational_layers

    # Push update
    log.info("Updating web map...")
    r = requests.post(
        f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
        data={"text": json.dumps(webmap), "f": "json", "token": token},
        headers={"Referer": REFERER},
        timeout=120,
    )
    r.raise_for_status()
    result = r.json()

    if result.get("success"):
        log.info("Web map updated successfully!")
        log.info(f"View at: https://www.arcgis.com/apps/mapviewer/index.html?webmap={WEBMAP_ITEM_ID}")
    else:
        log.error(f"Update failed: {result}")


def main():
    parser = argparse.ArgumentParser(description="Fix broken AGOL web map")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    fix_webmap(token)


if __name__ == "__main__":
    main()
