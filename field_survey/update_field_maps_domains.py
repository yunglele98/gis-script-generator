"""
Update ArcGIS Online feature layer fields with coded value domains.

This converts free-text fields in Field Maps to dropdown selectors,
making ground-truthing faster (tap instead of type).

Usage:
    python -m field_survey.update_field_maps_domains --token-file token.txt

Requires: requests
"""
import argparse
import json
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

REFERER = "https://fieldsurvey.local"

# Feature service admin URL (layer 2 = Building Assessment Points)
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"
LAYER_ID = 2

# Fields to convert to coded value domains
FIELD_DOMAINS = {
    "ba_building_type": {
        "name": "ba_building_type_domain",
        "description": "Building type",
        "values": [
            ("commercial", "Commercial"),
            ("institutional", "Institutional"),
            ("mixed_use", "Mixed Use"),
            ("residential", "Residential"),
            ("vacant_lot", "Vacant Lot"),
        ],
    },
    "ba_facade_material": {
        "name": "ba_facade_material_domain",
        "description": "Facade material",
        "values": [
            ("brick", "Brick"),
            ("concrete", "Concrete"),
            ("glass", "Glass"),
            ("mixed", "Mixed"),
            ("stone", "Stone"),
            ("stucco", "Stucco"),
            ("wood_siding", "Wood Siding"),
            ("metal", "Metal"),
            ("other", "Other"),
        ],
    },
    "ba_has_structural_concern": {
        "name": "ba_structural_domain",
        "description": "Structural concern present",
        "values": [("YES", "Yes"), ("no", "No"), ("unknown", "Unknown")],
    },
    "ba_storefront_status": {
        "name": "ba_storefront_domain",
        "description": "Storefront status",
        "values": [
            ("active", "Active"),
            ("vacant", "Vacant"),
            ("under_renovation", "Under Renovation"),
            ("n/a", "N/A (Residential)"),
        ],
    },
    "ba_is_vacant": {
        "name": "ba_vacant_domain",
        "description": "Is building vacant",
        "values": [("YES", "Yes"), ("no", "No"), ("partial", "Partially Vacant")],
    },
    "ba_business_category": {
        "name": "ba_business_cat_domain",
        "description": "Business category",
        "values": [
            ("Restaurant/Food", "Restaurant / Food"),
            ("Retail/Shop", "Retail / Shop"),
            ("Fashion/Clothing", "Fashion / Clothing"),
            ("Art/Culture", "Art / Culture"),
            ("Bar/Nightlife", "Bar / Nightlife"),
            ("Health/Wellness", "Health / Wellness"),
            ("Services", "Services"),
            ("Market Vendor", "Market Vendor"),
            ("Grocery/Food Retail", "Grocery / Food Retail"),
            ("Other", "Other"),
            ("n/a", "N/A"),
        ],
    },
    "ba_is_neglected": {
        "name": "ba_neglected_domain",
        "description": "Is building neglected",
        "values": [("YES", "Yes"), ("no", "No")],
    },
    "ba_risk_band": {
        "name": "ba_risk_band_domain",
        "description": "Risk band",
        "values": [
            ("Critical", "Critical"),
            ("High", "High"),
            ("Elevated", "Elevated"),
            ("Moderate", "Moderate"),
            ("Low", "Low"),
        ],
    },
    "ba_street_presence": {
        "name": "ba_street_presence_domain",
        "description": "Street presence quality",
        "values": [
            ("maintained", "Maintained"),
            ("neutral", "Neutral"),
            ("neglected", "Neglected"),
        ],
    },
    "ba_condition_rating": {
        "name": "ba_condition_domain",
        "description": "Condition rating (1=worst, 5=best)",
        "field_type": "esriFieldTypeInteger",
        "values": [
            (1, "1 - Critical"),
            (2, "2 - Poor"),
            (3, "3 - Fair"),
            (4, "4 - Good"),
            (5, "5 - Excellent"),
        ],
    },
    "VACANCY_STATUS": {
        "name": "vacancy_status_domain",
        "description": "Vacancy status",
        "values": [
            ("Active / Occupied", "Active / Occupied"),
            ("Confirmed Vacant Storefront", "Confirmed Vacant Storefront"),
            ("Likely Vacant", "Likely Vacant"),
            ("Possibly Vacant / Transitioning", "Possibly Vacant / Transitioning"),
            ("Unconfirmed Tenant", "Unconfirmed Tenant"),
            ("N/A \u2013 Residential", "N/A \u2013 Residential"),
            ("Residential \u2013 Commercial Potential", "Residential \u2013 Commercial Potential"),
        ],
    },
    "GENERAL_USE": {
        "name": "general_use_domain",
        "description": "General land use",
        "values": [
            ("Commercial", "Commercial"),
            ("Residential", "Residential"),
            ("Mixed Use", "Mixed Use"),
            ("Institutional", "Institutional"),
            ("Vacant", "Vacant"),
        ],
    },
    "SITE_CONDITION": {
        "name": "site_condition_domain",
        "description": "Site condition flag",
        "values": [
            ("Cultural Landmark", "Cultural Landmark"),
            ("Development Pressure", "Development Pressure"),
            ("Dilapidated", "Dilapidated"),
            ("KMCLT Owned", "KMCLT Owned"),
            ("Public Art Site", "Public Art Site"),
            ("Vacant Building", "Vacant Building"),
            ("None", "None"),
        ],
    },
    "ARCHITECTURAL_STYLE": {
        "name": "arch_style_domain",
        "description": "Architectural style",
        "values": [
            ("Victorian Bay-and-Gable", "Victorian Bay-and-Gable"),
            ("Victorian Bay-and-Gable (Converted)", "Victorian Bay-and-Gable (Converted)"),
            ("Victorian Bay-and-Gable Semi-Detached", "Victorian Bay-and-Gable Semi-Detached"),
            ("Victorian Vernacular \u2013 Ontario Cottage", "Victorian Vernacular \u2013 Ontario Cottage"),
            ("Victorian Vernacular (Multi-Unit Conversion)", "Victorian Vernacular (Multi-Unit)"),
            ("Edwardian / Early 20th-Century Commercial", "Edwardian / Early 20th-Century Commercial"),
            ("Byzantine Revival", "Byzantine Revival"),
            ("Modernist Institutional", "Modernist Institutional"),
            ("Contemporary Laneway / Infill", "Contemporary Laneway / Infill"),
            ("Post-War Commercial", "Post-War Commercial"),
            ("Other", "Other"),
        ],
    },
    "BUILDING_MATERIAL": {
        "name": "building_material_domain",
        "description": "Primary building material",
        "values": [
            ("Brick (Red or Buff)", "Brick (Red or Buff)"),
            ("Brick (Polychromatic)", "Brick (Polychromatic)"),
            ("Concrete / Masonry", "Concrete / Masonry"),
            ("Stone", "Stone"),
            ("Wood Frame", "Wood Frame"),
            ("Mixed", "Mixed"),
            ("Other", "Other"),
        ],
    },
    "HR_REGISTER_STATUS": {
        "name": "hr_register_domain",
        "description": "Heritage register status",
        "values": [
            ("Listed (Non-Designated)", "Listed (Non-Designated)"),
            ("Part IV Designated (Individual) + Part V HCD", "Part IV + Part V HCD"),
            ("Part V HCD Contributing", "Part V HCD Contributing"),
            ("Part V HCD Likely Contributing", "Part V HCD Likely Contributing"),
            ("Within HCD Boundary \u2013 Non-Contributing", "HCD Non-Contributing"),
            ("Within HCD Boundary \u2013 Status Unconfirmed", "HCD Status Unconfirmed"),
            ("Not Listed", "Not Listed"),
        ],
    },
    "HCD_CONTRIBUTING": {
        "name": "hcd_contributing_domain",
        "description": "HCD contributing status",
        "values": [("Yes", "Yes"), ("No", "No"), ("Unknown", "Unknown")],
    },
    "MORPHOLOGICAL_ZONE": {
        "name": "morph_zone_domain",
        "description": "Morphological zone",
        "values": [
            ("Core Market Spine \u2013 Mixed-Use", "Core Market Spine"),
            ("Secondary Market Street \u2013 Mixed-Use", "Secondary Market Street"),
            ("Perimeter Arterial \u2013 Commercial Corridor", "Perimeter Arterial"),
            ("Residential Interior \u2013 Victorian Fabric", "Residential Interior"),
            ("Institutional / Residential Node", "Institutional / Residential"),
        ],
    },
}


def build_domain_json(domain_def):
    """Build an AGOL coded value domain definition."""
    field_type = domain_def.get("field_type", "esriFieldTypeString")
    return {
        "type": "codedValue",
        "name": domain_def["name"],
        "description": domain_def["description"],
        "codedValues": [
            {"code": code, "name": label} for code, label in domain_def["values"]
        ],
        "fieldType": field_type,
        "mergePolicy": "esriMPTDefaultValue",
        "splitPolicy": "esriSPTDefaultValue",
    }


def update_domains(token):
    """Push coded value domains to the feature layer."""
    headers = {"Referer": REFERER}
    admin_url = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

    # Step 1: Get current layer definition
    log.info("Fetching current layer definition...")
    r = requests.get(
        f"{SERVICE_URL}/{LAYER_ID}",
        params={"f": "json", "token": token},
        headers=headers,
    )
    layer_def = r.json()
    current_fields = {f["name"]: f for f in layer_def.get("fields", [])}

    # Step 2: Build update definition with domains on fields
    fields_update = []
    for field_name, domain_def in FIELD_DOMAINS.items():
        if field_name not in current_fields:
            log.warning(f"Field {field_name} not found in layer, skipping")
            continue

        field = current_fields[field_name]
        domain = build_domain_json(domain_def)
        fields_update.append({"name": field_name, "domain": domain})
        log.info(f"  {field_name}: {len(domain_def['values'])} choices")

    if not fields_update:
        log.error("No fields to update")
        return

    # Step 3: Apply the update
    update_def = {"fields": fields_update}

    log.info(f"Updating {len(fields_update)} fields with domains...")
    r = requests.post(
        f"{admin_url}/{LAYER_ID}/updateDefinition",
        data={"updateDefinition": json.dumps(update_def), "token": token, "f": "json"},
        headers=headers,
    )
    result = r.json()

    if result.get("success"):
        log.info(f"Successfully updated {len(fields_update)} field domains")
    else:
        log.error(f"Update failed: {result}")
        # Try alternative: update fields one at a time
        if "error" in result:
            log.info("Trying individual field updates...")
            success = 0
            for field_update in fields_update:
                single_def = {"fields": [field_update]}
                r2 = requests.post(
                    f"{admin_url}/{LAYER_ID}/updateDefinition",
                    data={
                        "updateDefinition": json.dumps(single_def),
                        "token": token,
                        "f": "json",
                    },
                    headers=headers,
                )
                res2 = r2.json()
                if res2.get("success"):
                    log.info(f"  Updated {field_update['name']}")
                    success += 1
                else:
                    log.error(f"  Failed {field_update['name']}: {res2}")
            log.info(f"Updated {success}/{len(fields_update)} fields individually")


def main():
    parser = argparse.ArgumentParser(
        description="Add coded value domains to Field Maps layer"
    )
    parser.add_argument(
        "--token-file",
        default="C:/Users/liam1/token.txt",
        help="Path to file containing AGOL token",
    )
    args = parser.parse_args()

    with open(args.token_file) as f:
        token = f.read().strip()

    update_domains(token)


if __name__ == "__main__":
    main()
