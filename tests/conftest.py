"""Shared fixtures for all test modules."""

import pytest


@pytest.fixture
def db_config():
    return {
        "host":     "localhost",
        "port":     5432,
        "dbname":   "test_db",
        "user":     "testuser",
        "password": "testpass",
    }


@pytest.fixture
def schema():
    """Minimal two-layer schema dict (polygon + line)."""
    return {
        "database":    "test_db",
        "host":        "localhost",
        "layer_count": 2,
        "layers": [
            {
                "schema":           "public",
                "table":            "parcels",
                "qualified_name":   "public.parcels",
                "geometry": {"column": "geom", "type": "MULTIPOLYGON", "srid": 4326},
                "columns": [
                    {"name": "parcel_id", "data_type": "integer",           "nullable": False},
                    {"name": "address",   "data_type": "character varying",  "nullable": True},
                    {"name": "height",    "data_type": "double precision",   "nullable": True},
                ],
                "primary_keys":        ["parcel_id"],
                "row_count_estimate":  1000,
            },
            {
                "schema":           "public",
                "table":            "roads",
                "qualified_name":   "public.roads",
                "geometry": {"column": "geom", "type": "MULTILINESTRING", "srid": 4326},
                "columns": [
                    {"name": "road_id", "data_type": "integer", "nullable": False},
                    {"name": "name",    "data_type": "text",    "nullable": True},
                ],
                "primary_keys":        ["road_id"],
                "row_count_estimate":  500,
            },
        ],
    }


@pytest.fixture
def single_layer_schema(schema):
    """Schema with only the parcels layer."""
    s = dict(schema)
    s["layers"]      = [schema["layers"][0]]
    s["layer_count"] = 1
    return s


@pytest.fixture
def map_entry():
    """A representative catalogue map dict (M07)."""
    return {
        "map_id":            "M07",
        "theme":             "Forme urbaine",
        "subtheme":          "Gabarits",
        "title":             "Hauteurs / nombre d'étages (dégradé)",
        "short_name":        "hauteurs_etages_degrade",
        "objective":         "Représenter gabarits et gradient de hauteur",
        "key_questions":     "Où sont les hauteurs fortes/faibles?",
        "key_indicators":    "# étages, distribution",
        "study_scale":       "Quartier",
        "unit_of_analysis":  "bâtiment",
        "classification":    "classes 1–8+",
        "data_sources":      "OSM building:levels",
        "data_vintage":      "2024–2026",
        "spatial_layer_type": "Vector",
        "processing_steps":  "nettoyer niveaux + recoder classes",
        "symbology_type":    "choroplèthe (dégradé)",
        "status":            "have",
        "owner":             "Liam",
        "priority":          "High",
        "effort":            "S",
        "dependencies":      None,
        "deliverable_format": "Layout PDF + couche",
        "validation_checks": "valeurs nulles, plausibilité niveaux, palette lisible",
        "risks_limitations": "OSM incomplet; niveaux estimés",
    }


@pytest.fixture
def tmp_catalogue(tmp_path):
    """Write a minimal catalogue Excel with 4 rows covering all filter cases."""
    import openpyxl

    headers = [
        "map_id", "theme", "subtheme", "title", "short_name", "objective",
        "key_questions", "key_indicators", "study_scale", "unit_of_analysis",
        "classification", "data_sources", "data_vintage", "spatial_layer_type",
        "processing_steps", "symbology_type", "status", "owner", "priority",
        "effort", "dependencies", "deliverable_format", "validation_checks",
        "risks_limitations",
    ]

    rows = [
        # should be included: Vector + have
        ["M07", "Forme urbaine", "Gabarits", "Hauteurs", "hauteurs_test",
         "Obj", "Q", "I", "Quartier", "bâtiment", "classes", "OSM", "2024",
         "Vector", "processing", "choroplèthe (dégradé)", "have", "Liam",
         "High", "S", None, "Layout PDF", "val1, val2", "risk"],
        # should be included: Vector + partial
        ["M03", "Forme urbaine", "Occupation", "Occupation", "occupation_test",
         "Obj", "Q", "I", "Quartier", "parcelle", "usage", "Toronto", "2026",
         "Vector", "harmoniser", "choroplèthe catégoriel", "partial", "TBD",
         "High", "L", None, "Layout PDF + CSV", "check", "risk"],
        # should be excluded: Raster only
        ["M17", "Patrimoine", "Histoire", "Cartes", "cartes_test",
         "Obj", "Q", "I", "Quartier", "raster", "N/A", "Archives", "2020",
         "Raster", "scanning", "série carto", "todo", "TBD",
         "Low", "L", None, "Layout PDF", "check", "risk"],
        # should be excluded: Vector but todo
        ["M10", "Forme urbaine", "Bâti", "Age", "age_test",
         "Obj", "Q", "I", "Quartier", "bâtiment", "age", "Archives", "2024",
         "Vector", "classify", "choroplèthe catégoriel", "todo", "TBD",
         "Med", "L", None, "Layout PDF", "check", "risk"],
        # should be included: Raster/Vector + have (Vector component kept)
        ["M44", "Environnement", "Végétation", "Canopée", "canopee_test",
         "Obj", "Q", "I", "Quartier", "raster + points", "N/A", "Ville", "2024",
         "Raster/Vector", "overlay", "choroplèthe + points", "have", "Liam",
         "High", "M", None, "Layout PDF", "check", "risk"],
    ]

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Catalogue"
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.create_sheet("DataDictionary").append(["column", "meaning"])

    path = tmp_path / "test_catalogue.xlsx"
    wb.save(path)
    return str(path)
