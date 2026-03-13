"""
Translate all AGOL layer field aliases and domain labels to French.

Updates:
- Field aliases on the feature service (admin API)
- Layer titles in the web map (remove 3D references, French names)
- Domain coded value labels to French

Usage:
    python -m field_survey.translate_layers --token-file token.txt
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
ADMIN_URL = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

# ── French field aliases (field_name → French label) ──
# Applied to ALL layers that have the field. Case-insensitive matching.
FIELD_ALIASES_FR = {
    # ESRI internal
    "objectid": "Identifiant",
    "globalid": "Identifiant global",
    "creationdate": "Date de création",
    "creator": "Créateur",
    "editdate": "Date de modification",
    "editor": "Éditeur",

    # Building Assessment (ba_) fields
    "id": "Identifiant",
    "address_full": "Adresse complète",
    "match_type": "Type de correspondance",
    "ba_address": "Adresse",
    "ba_street": "Rue",
    "ba_street_number": "Numéro civique",
    "ba_block": "Îlot",
    "ba_building_type": "Type de bâtiment",
    "ba_stories": "Nombre d'étages",
    "ba_facade_material": "Matériau de façade",
    "ba_condition_rating": "Cote de condition",
    "ba_condition_issues": "Problèmes de condition",
    "ba_issue_count": "Nombre de problèmes",
    "ba_has_structural_concern": "Préoccupation structurale",
    "ba_storefront_status": "État du commerce",
    "ba_is_vacant": "Vacant",
    "ba_signage": "Affichage",
    "ba_business_category": "Catégorie de commerce",
    "ba_heritage_features": "Caractéristiques patrimoniales",
    "ba_heritage_count": "Nombre d'éléments patrimoniaux",
    "ba_has_heritage": "Présence patrimoniale",
    "ba_street_presence": "Présence sur rue",
    "ba_is_neglected": "Négligé",
    "ba_risk_score": "Score de risque",
    "ba_risk_band": "Niveau de risque",
    "ba_notes": "Notes",

    # Location
    "geo_latitude": "Latitude",
    "geo_longitude": "Longitude",

    # Land use & zoning
    "general_use": "Utilisation générale",
    "land_use_category": "Catégorie d'utilisation du sol",
    "commercial_use_type": "Type d'usage commercial",
    "mpac_code": "Code MPAC",
    "mpac_desc": "Description MPAC",
    "tax_class": "Classe fiscale",
    "zn_zone_code": "Code de zonage",

    # Business
    "business_name": "Nom du commerce",
    "bl_summary": "Résumé du permis commercial",
    "bl_all_names_history": "Historique des noms commerciaux",

    # Vacancy
    "vacancy_status": "Statut de vacance",
    "vacancy_score": "Score de vacance",
    "vacancy_signals": "Signaux de vacance",
    "commercial_continuity": "Continuité commerciale",
    "activation_indicators": "Indicateurs d'activation",

    # Site
    "site_condition": "Condition du site",
    "site_notes": "Notes du site",
    "priority_retail_street": "Rue commerciale prioritaire",
    "gentrification_pressure": "Pression de gentrification",

    # Building dimensions
    "storeys": "Étages",
    "bldg_height_max_m": "Hauteur max. (m)",
    "bldg_height_avg_m": "Hauteur moy. (m)",
    "bldg_footprint_sqm": "Empreinte au sol (m²)",
    "lot_width_ft": "Largeur du lot (pi)",
    "lot_depth_ft": "Profondeur du lot (pi)",
    "pb_lot_area_sqm": "Superficie du lot (m²)",
    "lot_coverage_pct": "Couverture du lot (%)",
    "gfa_total_sqm": "Surface brute totale (m²)",
    "fsi": "Indice de superficie de plancher",
    "front_setback": "Marge de recul avant",
    "lots_sharing_footprint": "Lots partageant l'empreinte",

    # Architecture & heritage
    "architectural_style": "Style architectural",
    "building_material": "Matériau de construction",
    "construction_period": "Période de construction",
    "construction_decade": "Décennie de construction",
    "development_phase": "Phase de développement",
    "morphological_zone": "Zone morphologique",
    "street_character": "Caractère de la rue",

    # Heritage register
    "hr_register_status": "Statut au registre du patrimoine",
    "hr_protection_level": "Niveau de protection",
    "hcd_plan_index_num": "Numéro d'index du plan DPC",
    "hcd_sub_area": "Sous-zone DPC",
    "hcd_typology": "Typologie DPC",
    "hcd_construction_date": "Date de construction DPC",
    "hcd_statement": "Énoncé DPC",
    "hcd_study_context": "Contexte de l'étude DPC",
    "hcd_contributing": "Contributif au DPC",
    "hcd_statement_full": "Énoncé complet DPC",

    # Residential
    "dwelling_units": "Unités d'habitation",
    "avg_unit_size_sqm": "Taille moy. des unités (m²)",
    "bedroom_mix": "Répartition des chambres",
    "residential_floors": "Étages résidentiels",
    "gfa_residential_sqm": "Surface résidentielle (m²)",
    "gfa_commercial_sqm": "Surface commerciale (m²)",
    "gfa_residential_pct": "Surface résidentielle (%)",
    "residential_density": "Densité résidentielle",
    "tenure_estimate": "Estimation du mode d'occupation",

    # Financial
    "cva_2024": "Valeur foncière 2024",
    "commercial_rent_range_psf": "Loyer commercial (fourchette/pi²)",
    "commercial_rent_mid_psf": "Loyer commercial médian (pi²)",
    "rent_occupied_mo": "Loyer occupé (mois)",
    "rent_market_mo": "Loyer du marché (mois)",
    "annual_res_income": "Revenu résidentiel annuel",
    "res_income_to_cva_pct": "Ratio revenu/valeur foncière (%)",

    # Short-term rental
    "str_registered": "Hébergement touristique enregistré",
    "airbnb_closest_m": "Airbnb le plus proche (m)",
    "airbnb_density_75m": "Densité Airbnb (75 m)",
    "str_airbnb_summary": "Résumé hébergement touristique",

    # Permits & development
    "permits_count": "Nombre de permis",
    "permits_total_cost": "Coût total des permis",
    "permits_units_created": "Unités créées par permis",
    "bp_summary": "Résumé des permis de construire",
    "has_dev_app": "Demande d'aménagement",
    "dev_app_summary": "Résumé demande d'aménagement",
    "dev_apps_nearby_count": "Demandes d'aménagement à proximité",
    "dev_apps_nearby": "Aménagements à proximité",

    # Other data
    "osm_match": "Correspondance OpenStreetMap",
    "emp_summary": "Résumé de l'emploi",
    "tree_canopy_summary": "Résumé de la canopée",
    "poi_summary": "Résumé des points d'intérêt",

    # Common GIS fields
    "gid": "Identifiant",
    "geom": "Géométrie",
    "shape__area": "Superficie",
    "shape__length": "Périmètre",
    "shape": "Forme",
}

# ── French layer titles (layer_id → French name, no 3D references) ──
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

# ── French domain coded value labels ──
DOMAIN_LABELS_FR = {
    "ba_building_type_domain": {
        "Commercial": "Commercial",
        "Institutional": "Institutionnel",
        "Mixed Use": "Usage mixte",
        "Residential": "Résidentiel",
        "Vacant Lot": "Terrain vacant",
    },
    "ba_facade_material_domain": {
        "Brick": "Brique",
        "Concrete": "Béton",
        "Glass": "Verre",
        "Mixed": "Mixte",
        "Stone": "Pierre",
        "Stucco": "Stuc",
        "Wood Siding": "Parement de bois",
        "Metal": "Métal",
        "Other": "Autre",
    },
    "ba_structural_domain": {
        "Yes": "Oui",
        "No": "Non",
        "Unknown": "Inconnu",
    },
    "ba_storefront_domain": {
        "Active": "Actif",
        "Vacant": "Vacant",
        "Under Renovation": "En rénovation",
        "N/A (Residential)": "S/O (Résidentiel)",
    },
    "ba_vacant_domain": {
        "Yes": "Oui",
        "No": "Non",
        "Partially Vacant": "Partiellement vacant",
    },
    "ba_business_cat_domain": {
        "Restaurant / Food": "Restaurant / Alimentation",
        "Retail / Shop": "Commerce de détail",
        "Fashion / Clothing": "Mode / Vêtements",
        "Art / Culture": "Art / Culture",
        "Bar / Nightlife": "Bar / Vie nocturne",
        "Health / Wellness": "Santé / Bien-être",
        "Services": "Services",
        "Market Vendor": "Vendeur du marché",
        "Grocery / Food Retail": "Épicerie / Alimentation",
        "Other": "Autre",
        "N/A": "S/O",
    },
    "ba_neglected_domain": {
        "Yes": "Oui",
        "No": "Non",
    },
    "ba_risk_band_domain": {
        "Critical": "Critique",
        "High": "Élevé",
        "Elevated": "Haussé",
        "Moderate": "Modéré",
        "Low": "Faible",
    },
    "ba_street_presence_domain": {
        "Maintained": "Entretenu",
        "Neutral": "Neutre",
        "Neglected": "Négligé",
    },
    "ba_condition_domain": {
        "1 - Critical": "1 - Critique",
        "2 - Poor": "2 - Mauvais",
        "3 - Fair": "3 - Passable",
        "4 - Good": "4 - Bon",
        "5 - Excellent": "5 - Excellent",
    },
    "vacancy_status_domain": {
        "Active / Occupied": "Actif / Occupé",
        "Confirmed Vacant Storefront": "Commerce vacant confirmé",
        "Likely Vacant": "Probablement vacant",
        "Possibly Vacant / Transitioning": "Possiblement vacant / En transition",
        "Unconfirmed Tenant": "Locataire non confirmé",
        "N/A – Residential": "S/O – Résidentiel",
        "Residential – Commercial Potential": "Résidentiel – Potentiel commercial",
    },
    "general_use_domain": {
        "Commercial": "Commercial",
        "Residential": "Résidentiel",
        "Mixed Use": "Usage mixte",
        "Institutional": "Institutionnel",
        "Vacant": "Vacant",
    },
    "site_condition_domain": {
        "Cultural Landmark": "Repère culturel",
        "Development Pressure": "Pression de développement",
        "Dilapidated": "Délabré",
        "KMCLT Owned": "Propriété du KMCLT",
        "Public Art Site": "Site d'art public",
        "Vacant Building": "Bâtiment vacant",
        "None": "Aucun",
    },
    "arch_style_domain": {
        "Victorian Bay-and-Gable": "Victorien baie et pignon",
        "Victorian Bay-and-Gable (Converted)": "Victorien baie et pignon (converti)",
        "Victorian Bay-and-Gable Semi-Detached": "Victorien baie et pignon jumelé",
        "Victorian Vernacular – Ontario Cottage": "Vernaculaire victorien – Cottage ontarien",
        "Victorian Vernacular (Multi-Unit)": "Vernaculaire victorien (multi-logement)",
        "Edwardian / Early 20th-Century Commercial": "Édouardien / Commercial début 20e siècle",
        "Byzantine Revival": "Néo-byzantin",
        "Modernist Institutional": "Institutionnel moderniste",
        "Contemporary Laneway / Infill": "Ruelle contemporaine / Intercalaire",
        "Post-War Commercial": "Commercial d'après-guerre",
        "Other": "Autre",
    },
    "building_material_domain": {
        "Brick (Red or Buff)": "Brique (rouge ou chamois)",
        "Brick (Polychromatic)": "Brique (polychrome)",
        "Concrete / Masonry": "Béton / Maçonnerie",
        "Stone": "Pierre",
        "Wood Frame": "Ossature de bois",
        "Mixed": "Mixte",
        "Other": "Autre",
    },
    "hr_register_domain": {
        "Listed (Non-Designated)": "Inscrit (non désigné)",
        "Part IV + Part V HCD": "Partie IV + Partie V DPC",
        "Part V HCD Contributing": "Partie V DPC contributif",
        "Part V HCD Likely Contributing": "Partie V DPC probablement contributif",
        "HCD Non-Contributing": "DPC non contributif",
        "HCD Status Unconfirmed": "Statut DPC non confirmé",
        "Not Listed": "Non inscrit",
    },
    "hcd_contributing_domain": {
        "Yes": "Oui",
        "No": "Non",
        "Unknown": "Inconnu",
    },
    "morph_zone_domain": {
        "Core Market Spine": "Axe central du marché",
        "Secondary Market Street": "Rue secondaire du marché",
        "Perimeter Arterial": "Artère périphérique",
        "Residential Interior": "Intérieur résidentiel",
        "Institutional / Residential": "Institutionnel / Résidentiel",
    },
}


def update_field_aliases(token):
    """Update field aliases to French on all layers via admin API."""
    headers = {"Referer": REFERER}

    # Get all layers
    r = requests.get(SERVICE_URL, params={"f": "json", "token": token},
                     headers=headers, timeout=60)
    service_info = r.json()
    all_layers = service_info.get("layers", [])

    total_updated = 0
    for layer_meta in all_layers:
        layer_id = layer_meta["id"]

        # Get full layer definition
        r = requests.get(f"{SERVICE_URL}/{layer_id}",
                         params={"f": "json", "token": token},
                         headers=headers, timeout=60)
        layer_def = r.json()
        fields = layer_def.get("fields", [])

        fields_to_update = []
        for field in fields:
            fname = field["name"].lower()
            if fname in FIELD_ALIASES_FR:
                new_alias = FIELD_ALIASES_FR[fname]
                if field.get("alias") != new_alias:
                    fields_to_update.append({
                        "name": field["name"],
                        "alias": new_alias,
                    })

        if not fields_to_update:
            continue

        # Update via admin API
        update_def = {"fields": fields_to_update}
        r = requests.post(
            f"{ADMIN_URL}/{layer_id}/updateDefinition",
            data={
                "updateDefinition": json.dumps(update_def),
                "token": token,
                "f": "json",
            },
            headers=headers,
            timeout=120,
        )
        result = r.json()
        if result.get("success"):
            log.info(f"  Layer {layer_id} ({layer_meta['name']}): {len(fields_to_update)} aliases updated")
            total_updated += len(fields_to_update)
        else:
            log.warning(f"  Layer {layer_id}: alias update failed: {result}")

    log.info(f"Total field aliases updated: {total_updated}")


def update_domain_labels(token):
    """Update domain coded value labels to French."""
    headers = {"Referer": REFERER}

    # Get layer 2 (has most domains)
    r = requests.get(f"{SERVICE_URL}/2",
                     params={"f": "json", "token": token},
                     headers=headers, timeout=60)
    layer_def = r.json()
    fields = layer_def.get("fields", [])

    fields_to_update = []
    for field in fields:
        domain = field.get("domain")
        if not domain or domain.get("type") != "codedValue":
            continue

        domain_name = domain.get("name", "")
        if domain_name not in DOMAIN_LABELS_FR:
            continue

        fr_labels = DOMAIN_LABELS_FR[domain_name]
        new_coded_values = []
        changed = False
        for cv in domain.get("codedValues", []):
            old_name = cv["name"]
            new_name = fr_labels.get(old_name, old_name)
            if new_name != old_name:
                changed = True
            new_coded_values.append({"code": cv["code"], "name": new_name})

        if changed:
            new_domain = dict(domain)
            new_domain["codedValues"] = new_coded_values
            fields_to_update.append({
                "name": field["name"],
                "domain": new_domain,
            })

    if fields_to_update:
        update_def = {"fields": fields_to_update}
        r = requests.post(
            f"{ADMIN_URL}/2/updateDefinition",
            data={
                "updateDefinition": json.dumps(update_def),
                "token": token,
                "f": "json",
            },
            headers=headers,
            timeout=120,
        )
        result = r.json()
        if result.get("success"):
            log.info(f"Updated {len(fields_to_update)} domain labels to French")
        else:
            log.warning(f"Domain label update failed: {result}")
            # Try one by one
            success = 0
            for fu in fields_to_update:
                r2 = requests.post(
                    f"{ADMIN_URL}/2/updateDefinition",
                    data={
                        "updateDefinition": json.dumps({"fields": [fu]}),
                        "token": token,
                        "f": "json",
                    },
                    headers=headers,
                    timeout=60,
                )
                if r2.json().get("success"):
                    log.info(f"    Updated domain for {fu['name']}")
                    success += 1
                else:
                    log.warning(f"    Failed domain for {fu['name']}: {r2.json()}")
            log.info(f"Updated {success}/{len(fields_to_update)} domains individually")
    else:
        log.info("No domain labels needed updating")


def update_webmap_titles(token):
    """Update layer titles in the web map to French (no 3D references)."""
    headers = {"Referer": REFERER}

    r = requests.get(
        f"https://www.arcgis.com/sharing/rest/content/items/{WEBMAP_ITEM_ID}/data",
        params={"f": "json", "token": token},
        headers=headers, timeout=60,
    )
    webmap = r.json()

    changed = 0
    for group in webmap.get("operationalLayers", []):
        if group.get("layerType") == "GroupLayer":
            for layer in group.get("layers", []):
                url = layer.get("url", "")
                # Extract layer ID from URL
                try:
                    lid = int(url.rstrip("/").split("/")[-1])
                except (ValueError, IndexError):
                    continue
                if lid in LAYER_TITLES_FR:
                    new_title = LAYER_TITLES_FR[lid]
                    if layer.get("title") != new_title:
                        layer["title"] = new_title
                        changed += 1

    if changed:
        r = requests.post(
            f"https://www.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ITEM_ID}/update",
            data={"text": json.dumps(webmap), "f": "json", "token": token},
            headers=headers, timeout=120,
        )
        result = r.json()
        if result.get("success"):
            log.info(f"Updated {changed} layer titles in web map")
        else:
            log.error(f"Web map title update failed: {result}")
    else:
        log.info("All web map titles already in French")


def main():
    parser = argparse.ArgumentParser(description="Translate AGOL layers to French")
    parser.add_argument("--token-file", default="C:/Users/liam1/token.txt")
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    log.info("=== Step 1: Update field aliases to French ===")
    update_field_aliases(token)

    log.info("=== Step 2: Update domain labels to French ===")
    update_domain_labels(token)

    log.info("=== Step 3: Update web map layer titles ===")
    update_webmap_titles(token)

    log.info("Done! View at: https://www.arcgis.com/apps/mapviewer/index.html?webmap=" + WEBMAP_ITEM_ID)


if __name__ == "__main__":
    main()
