import pytest
from unittest.mock import MagicMock

from field_survey.sync_field_data import (
    build_upsert_sql,
    transform_feature,
    FORM_TABLE_MAP,
)


def test_form_table_map_has_all_forms():
    assert "resident" in FORM_TABLE_MAP
    assert "business" in FORM_TABLE_MAP
    assert "intercept" in FORM_TABLE_MAP
    assert "student" in FORM_TABLE_MAP
    assert "field_obs" in FORM_TABLE_MAP
    assert "contact" in FORM_TABLE_MAP


def test_build_upsert_sql_generates_valid_sql():
    sql = build_upsert_sql("field_surveys.resident_responses", ["globalid", "age_range", "gender"])
    assert "INSERT INTO field_surveys.resident_responses" in sql
    assert "ON CONFLICT (globalid)" in sql
    assert "DO UPDATE SET" in sql


def test_build_upsert_sql_excludes_id_and_globalid_from_update():
    sql = build_upsert_sql("field_surveys.resident_responses", ["globalid", "age_range"])
    set_clause = sql.split("DO UPDATE SET")[1]
    assert "globalid" not in set_clause


def test_transform_feature_extracts_attributes():
    feature = {
        "attributes": {
            "globalid": "abc-123",
            "age_range": "25_34",
            "gender": "man",
            "ObjectID": 1,
        },
        "geometry": {"x": -79.4, "y": 43.65},
    }
    result = transform_feature(feature, include_geom=False)
    assert result["globalid"] == "abc-123"
    assert result["age_range"] == "25_34"
    assert "objectid" not in result  # ObjectID should be skipped


def test_transform_feature_skips_null_geometry():
    feature = {
        "attributes": {"globalid": "abc-123"},
        "geometry": None,
    }
    result = transform_feature(feature, include_geom=True)
    assert result.get("geom") is None
