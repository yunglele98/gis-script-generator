"""
Update all Field Maps layers: French labels, essential fields only, coded domains.
"""
import json
import requests

TOKEN_FILE = "C:/Users/liam1/token.txt"
REFERER = "https://fieldsurvey.local"
WEBMAP_ID = "597d45ca0eda44abbe8806c7736be0bf"
SERVICE_URL = "https://services6.arcgis.com/133a00biU9FItiqJ/arcgis/rest/services/Kensington_Market_Collectif_Humanis_WFL1/FeatureServer"


def get_token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def field(name, label, input_type="text-box", editable=True, **kwargs):
    el = {
        "type": "field",
        "fieldName": name,
        "label": label,
        "editableExpression": "expr/system/true" if editable else "expr/system/false",
        "inputType": {"type": input_type},
    }
    if input_type in ("text-box", "text-area"):
        el["inputType"]["maxLength"] = kwargs.get("maxLength", 254)
        el["inputType"]["minLength"] = 0
    return el


def group(label, fields, state="expanded"):
    return {
        "type": "group",
        "label": label,
        "formElements": fields,
        "initialState": state,
    }


EXPR_INFOS = [
    {"expression": "false", "name": "expr/system/false", "returnType": "boolean", "title": "False"},
    {"expression": "true", "name": "expr/system/true", "returnType": "boolean", "title": "True"},
]


# ── Form definitions per layer ────────────────────────────────────────

LAYER_FORMS = {
    "Building Assessment Points": {
        "title": "\u00c9valuation des b\u00e2timents",
        "formElements": [
            group("Identification", [
                field("ADDRESS_FULL", "Adresse", editable=False),
                field("BUSINESS_NAME", "Nom du commerce"),
                field("ba_building_type", "Type de b\u00e2timent"),
                field("GENERAL_USE", "Utilisation du sol"),
                field("ba_business_category", "Cat\u00e9gorie de commerce"),
            ]),
            group("\u00c9valuation terrain", [
                field("ba_condition_rating", "\u00c9tat (1\u20135)"),
                field("ba_condition_issues", "Probl\u00e8mes observ\u00e9s", input_type="text-area"),
                field("ba_has_structural_concern", "Pr\u00e9occupation structurelle?"),
                field("ba_facade_material", "Mat\u00e9riau de fa\u00e7ade"),
                field("ba_stories", "Nombre d'\u00e9tages"),
                field("ba_street_presence", "Pr\u00e9sence sur rue"),
                field("ba_is_neglected", "N\u00e9glig\u00e9?"),
            ]),
            group("Vacance et devanture", [
                field("ba_is_vacant", "Vacant?"),
                field("ba_storefront_status", "\u00c9tat de la devanture"),
                field("VACANCY_STATUS", "Statut de vacance"),
                field("ba_signage", "Description de l'enseigne", input_type="text-area"),
            ]),
            group("Patrimoine", [
                field("ARCHITECTURAL_STYLE", "Style architectural"),
                field("BUILDING_MATERIAL", "Mat\u00e9riau principal"),
                field("HR_REGISTER_STATUS", "Statut patrimonial"),
                field("HCD_CONTRIBUTING", "Contributeur ACP?"),
                field("MORPHOLOGICAL_ZONE", "Zone morphologique"),
            ]),
            group("Notes", [
                field("ba_notes", "Notes de terrain", input_type="text-area", maxLength=2000),
            ]),
            group("R\u00e9f\u00e9rence (lecture seule)", [
                field("CONSTRUCTION_PERIOD", "P\u00e9riode de construction", editable=False),
                field("CVA_2024", "\u00c9valuation fonci\u00e8re 2024", editable=False),
                field("DWELLING_UNITS", "Unit\u00e9s de logement", editable=False),
                field("FSI", "COS", editable=False),
                field("TENURE_ESTIMATE", "Mode d'occupation", editable=False),
                field("BL_ALL_NAMES_HISTORY", "Historique commercial", editable=False),
            ], state="collapsed"),
        ],
    },
    "3D Building Height": {
        "title": "Hauteur des b\u00e2timents",
        "formElements": [
            group("Identification", [
                field("ADDRESS_FULL", "Adresse", editable=False),
                field("MAX_HEIGHT", "Hauteur maximum", editable=False),
                field("STOREYS", "Nombre d'\u00e9tages", editable=False),
            ]),
            group("\u00c9valuation", [
                field("ba_condition_rating", "\u00c9tat"),
                field("ba_building_type", "Type de b\u00e2timent"),
                field("GENERAL_USE", "Utilisation du sol"),
            ]),
        ],
    },
    "Street Trees": {
        "title": "Arbres de rue",
        "formElements": [
            group("Localisation", [
                field("address4", "Adresse", editable=False),
                field("streetn5", "Rue", editable=False),
            ]),
            group("Identification de l'arbre", [
                field("common_14", "Nom commun"),
                field("botanic13", "Nom botanique"),
                field("dbh_tru15", "DHP du tronc (cm)"),
                field("site11", "Site"),
            ]),
        ],
    },
    "Social Housing": {
        "title": "Logement social",
        "formElements": [
            group("Identification", [
                field("dev_nam5", "Nom du d\u00e9veloppement"),
                field("pstl_co8", "Code postal"),
            ]),
            group("D\u00e9tails", [
                field("rgi_uni11", "Unit\u00e9s RGI"),
                field("mrkt_un10", "Unit\u00e9s au march\u00e9"),
                field("yr_buil12", "Ann\u00e9e de construction"),
                field("flr_abv16", "Nombre d'\u00e9tages"),
                field("bld_for15", "Style architectural"),
            ]),
        ],
    },
    "Transit Shelters": {
        "title": "Abribus",
        "formElements": [
            group("\u00c9tat", [
                field("status14", "Statut"),
            ]),
        ],
    },
    "Bike Racks": {
        "title": "Supports \u00e0 v\u00e9los",
        "formElements": [
            group("\u00c9tat", [
                field("status14", "Statut"),
            ]),
        ],
    },
    "Utility Poles": {
        "title": "Poteaux utilitaires",
        "formElements": [
            group("Type", [
                field("subtype3", "Type de poteau"),
            ]),
        ],
    },
    "Schools": {
        "title": "\u00c9coles",
        "formElements": [
            group("Information", [
                field("name4", "Nom de l'\u00e9cole", editable=False),
                field("school_6", "Niveau scolaire", editable=False),
                field("board_n7", "Commission scolaire", editable=False),
            ]),
        ],
    },
    "Hospitals": {
        "title": "H\u00f4pitaux",
        "formElements": [
            group("Information", [
                field("agency_3", "Nom de l'institution", editable=False),
            ]),
        ],
    },
    "Places of Worship": {
        "title": "Lieux de culte",
        "formElements": [
            group("Information", [
                field("fth_org23", "Nom de l'organisation", editable=False),
                field("fth_fai24", "Foi religieuse", editable=False),
            ]),
        ],
    },
    "Laneways": {
        "title": "Ruelles",
        "formElements": [
            group("Information", [
                field("name", "Nom de la ruelle"),
                field("service", "Ruelle / All\u00e9e priv\u00e9e"),
            ]),
        ],
    },
    "Road Surfaces": {
        "title": "Surfaces de rue",
        "formElements": [
            group("Information", [
                field("SUBTYPE3", "Section de rue", editable=False),
            ]),
        ],
    },
    "Building Footprints": {
        "title": "Empreintes de b\u00e2timents",
        "formElements": [
            group("Information", [
                field("SUBTYPE3", "Immeuble / garage", editable=False),
            ]),
        ],
    },
    "Green Spaces": {
        "title": "Espaces verts",
        "formElements": [
            group("Information", [
                field("AREA_NA9", "Nom du parc", editable=False),
            ]),
        ],
    },
    "Cycling Network": {
        "title": "R\u00e9seau cyclable",
        "formElements": [
            group("Information", [
                field("INFRA_L14", "Infrastructure partag\u00e9e", editable=False),
                field("INFRA_H15", "Infrastructure r\u00e9serv\u00e9e", editable=False),
            ]),
        ],
    },
}


def update_webmap(token):
    headers = {"Referer": REFERER}

    # Get current web map
    r = requests.get(
        f"https://uqam.maps.arcgis.com/sharing/rest/content/items/{WEBMAP_ID}/data",
        params={"f": "json", "token": token},
        headers=headers,
    )
    webmap = r.json()

    updated_count = 0

    def process_layers(layers):
        nonlocal updated_count
        for layer in layers:
            title = layer.get("title", "")
            if title in LAYER_FORMS:
                form_def = LAYER_FORMS[title]
                layer["formInfo"] = {
                    "formElements": form_def["formElements"],
                    "expressionInfos": EXPR_INFOS,
                    "title": form_def["title"],
                }
                updated_count += 1
                print(f"  Updated: {title} -> {form_def['title']}")
            if "layers" in layer:
                process_layers(layer["layers"])

    process_layers(webmap.get("operationalLayers", []))

    # Save
    r = requests.post(
        f"https://uqam.maps.arcgis.com/sharing/rest/content/users/uqam2006/items/{WEBMAP_ID}/update",
        data={"text": json.dumps(webmap), "token": token, "f": "json"},
        headers=headers,
    )
    result = r.json()
    if result.get("success"):
        print(f"\nUpdated {updated_count} layers to French with essential fields only")
    else:
        print(f"ERROR: {result}")


def update_domains_french(token):
    headers = {"Referer": REFERER}
    admin_url = SERVICE_URL.replace("/rest/services/", "/rest/admin/services/")

    FRENCH_DOMAINS = {
        "ba_building_type": {
            "name": "ba_building_type_domain",
            "values": [
                ("commercial", "Commercial"),
                ("institutional", "Institutionnel"),
                ("mixed_use", "Usage mixte"),
                ("residential", "R\u00e9sidentiel"),
                ("vacant_lot", "Terrain vacant"),
            ],
        },
        "ba_facade_material": {
            "name": "ba_facade_material_domain",
            "values": [
                ("brick", "Brique"), ("concrete", "B\u00e9ton"), ("glass", "Verre"),
                ("mixed", "Mixte"), ("stone", "Pierre"), ("stucco", "Stuc"),
                ("wood_siding", "Rev\u00eatement de bois"), ("metal", "M\u00e9tal"), ("other", "Autre"),
            ],
        },
        "ba_has_structural_concern": {
            "name": "ba_structural_domain",
            "values": [("YES", "Oui"), ("no", "Non"), ("unknown", "Inconnu")],
        },
        "ba_storefront_status": {
            "name": "ba_storefront_domain",
            "values": [("active", "Actif"), ("vacant", "Vacant"), ("under_renovation", "En r\u00e9novation"), ("n/a", "S/O")],
        },
        "ba_is_vacant": {
            "name": "ba_vacant_domain",
            "values": [("YES", "Oui"), ("no", "Non"), ("partial", "Partiellement vacant")],
        },
        "ba_business_category": {
            "name": "ba_business_cat_domain",
            "values": [
                ("Restaurant/Food", "Restaurant / Alimentation"), ("Retail/Shop", "Commerce de d\u00e9tail"),
                ("Fashion/Clothing", "Mode / V\u00eatements"), ("Art/Culture", "Art / Culture"),
                ("Bar/Nightlife", "Bar / Vie nocturne"), ("Health/Wellness", "Sant\u00e9 / Bien-\u00eatre"),
                ("Services", "Services"), ("Market Vendor", "Vendeur de march\u00e9"),
                ("Grocery/Food Retail", "\u00c9picerie"), ("Other", "Autre"), ("n/a", "S/O"),
            ],
        },
        "ba_is_neglected": {
            "name": "ba_neglected_domain",
            "values": [("YES", "Oui"), ("no", "Non")],
        },
        "ba_risk_band": {
            "name": "ba_risk_band_domain",
            "values": [("Critical", "Critique"), ("High", "\u00c9lev\u00e9"), ("Elevated", "Mod\u00e9r\u00e9-\u00e9lev\u00e9"), ("Moderate", "Mod\u00e9r\u00e9"), ("Low", "Faible")],
        },
        "ba_street_presence": {
            "name": "ba_street_presence_domain",
            "values": [("maintained", "Entretenu"), ("neutral", "Neutre"), ("neglected", "N\u00e9glig\u00e9")],
        },
        "ba_condition_rating": {
            "name": "ba_condition_domain",
            "field_type": "esriFieldTypeInteger",
            "values": [(1, "1 - Critique"), (2, "2 - Mauvais"), (3, "3 - Passable"), (4, "4 - Bon"), (5, "5 - Excellent")],
        },
        "VACANCY_STATUS": {
            "name": "vacancy_status_domain",
            "values": [
                ("Active / Occupied", "Actif / Occup\u00e9"),
                ("Confirmed Vacant Storefront", "Devanture vacante"),
                ("Likely Vacant", "Probablement vacant"),
                ("Possibly Vacant / Transitioning", "En transition"),
                ("Unconfirmed Tenant", "Locataire non confirm\u00e9"),
                ("N/A \u2013 Residential", "S/O \u2013 R\u00e9sidentiel"),
                ("Residential \u2013 Commercial Potential", "Potentiel commercial"),
            ],
        },
        "GENERAL_USE": {
            "name": "general_use_domain",
            "values": [("Commercial", "Commercial"), ("Residential", "R\u00e9sidentiel"), ("Mixed Use", "Usage mixte"), ("Institutional", "Institutionnel"), ("Vacant", "Vacant")],
        },
        "SITE_CONDITION": {
            "name": "site_condition_domain",
            "values": [
                ("Cultural Landmark", "Rep\u00e8re culturel"), ("Development Pressure", "Pression de d\u00e9veloppement"),
                ("Dilapidated", "D\u00e9labr\u00e9"), ("KMCLT Owned", "Propri\u00e9t\u00e9 KMCLT"),
                ("Public Art Site", "Art public"), ("Vacant Building", "B\u00e2timent vacant"), ("None", "Aucune"),
            ],
        },
        "ARCHITECTURAL_STYLE": {
            "name": "arch_style_domain",
            "values": [
                ("Victorian Bay-and-Gable", "Victorien \u00e0 baie et pignon"),
                ("Victorian Bay-and-Gable (Converted)", "Victorien (converti)"),
                ("Victorian Bay-and-Gable Semi-Detached", "Victorien jumel\u00e9"),
                ("Victorian Vernacular \u2013 Ontario Cottage", "Cottage ontarien"),
                ("Victorian Vernacular (Multi-Unit Conversion)", "Vernaculaire multilogement"),
                ("Edwardian / Early 20th-Century Commercial", "\u00c9douardien commercial"),
                ("Byzantine Revival", "N\u00e9o-byzantin"),
                ("Modernist Institutional", "Moderniste"),
                ("Contemporary Laneway / Infill", "Contemporain / Intercalaire"),
                ("Post-War Commercial", "Commercial d'apr\u00e8s-guerre"),
                ("Other", "Autre"),
            ],
        },
        "BUILDING_MATERIAL": {
            "name": "building_material_domain",
            "values": [
                ("Brick (Red or Buff)", "Brique (rouge/chamois)"), ("Brick (Polychromatic)", "Brique polychrome"),
                ("Concrete / Masonry", "B\u00e9ton / Ma\u00e7onnerie"), ("Stone", "Pierre"),
                ("Wood Frame", "Ossature bois"), ("Mixed", "Mixte"), ("Other", "Autre"),
            ],
        },
        "HR_REGISTER_STATUS": {
            "name": "hr_register_domain",
            "values": [
                ("Listed (Non-Designated)", "Inscrit (non d\u00e9sign\u00e9)"),
                ("Part IV Designated (Individual) + Part V HCD", "Partie IV + V ACP"),
                ("Part V HCD Contributing", "ACP contributeur"),
                ("Part V HCD Likely Contributing", "ACP probablement contributeur"),
                ("Within HCD Boundary \u2013 Non-Contributing", "ACP non-contributeur"),
                ("Within HCD Boundary \u2013 Status Unconfirmed", "ACP non confirm\u00e9"),
                ("Not Listed", "Non inscrit"),
            ],
        },
        "HCD_CONTRIBUTING": {
            "name": "hcd_contributing_domain",
            "values": [("Yes", "Oui"), ("No", "Non"), ("Unknown", "Inconnu")],
        },
        "MORPHOLOGICAL_ZONE": {
            "name": "morph_zone_domain",
            "values": [
                ("Core Market Spine \u2013 Mixed-Use", "\u00c9pine centrale du march\u00e9"),
                ("Secondary Market Street \u2013 Mixed-Use", "Rue secondaire du march\u00e9"),
                ("Perimeter Arterial \u2013 Commercial Corridor", "Art\u00e8re p\u00e9riph\u00e9rique"),
                ("Residential Interior \u2013 Victorian Fabric", "Int\u00e9rieur r\u00e9sidentiel"),
                ("Institutional / Residential Node", "N\u0153ud institutionnel"),
            ],
        },
    }

    fields_update = []
    for field_name, domain_def in FRENCH_DOMAINS.items():
        field_type = domain_def.get("field_type", "esriFieldTypeString")
        domain = {
            "type": "codedValue",
            "name": domain_def["name"],
            "description": domain_def.get("description", ""),
            "codedValues": [{"code": code, "name": label} for code, label in domain_def["values"]],
            "fieldType": field_type,
            "mergePolicy": "esriMPTDefaultValue",
            "splitPolicy": "esriSPTDefaultValue",
        }
        fields_update.append({"name": field_name, "domain": domain})

    update_def = {"fields": fields_update}
    r = requests.post(
        f"{admin_url}/2/updateDefinition",
        data={"updateDefinition": json.dumps(update_def), "token": token, "f": "json"},
        headers=headers,
    )
    result = r.json()
    if result.get("success"):
        print(f"Updated {len(fields_update)} domain labels to French")
    else:
        print(f"Domain update error: {result}")


if __name__ == "__main__":
    token = get_token()
    print("Updating web map forms (French, essential fields only)...")
    update_webmap(token)
    print("\nUpdating dropdown labels to French...")
    update_domains_french(token)
    print("\nDone!")
