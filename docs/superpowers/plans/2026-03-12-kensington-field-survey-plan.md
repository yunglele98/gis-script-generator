# Kensington Field Survey Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build 4 Survey123 XLSForms, a PostGIS sync pipeline, and analysis views for a 1-week field study in Kensington Market.

**Architecture:** Survey123 XLSForms define the interview forms, deployed via ArcGIS Online. A Python sync script (`sync_field_data.py`) pulls responses from AGOL into a `field_surveys` PostGIS schema. SQL views join survey data to the existing 46 tables for analysis. Dropdown choice lists are pre-exported from PostGIS as CSVs.

**Tech Stack:** XLSForm (xlsx), Python 3.10+, `arcgis` Python API, `psycopg`, `openpyxl`, PostGIS, ArcGIS Online / Survey123

**Spec:** `docs/superpowers/specs/2026-03-12-kensington-field-survey-design.md`

---

## File Structure

```
gis-script-generator/
├── field_survey/                        # New directory for all field survey tooling
│   ├── xlsform/                         # XLSForm workbooks (one per survey)
│   │   ├── resident_survey.xlsx
│   │   ├── business_survey.xlsx
│   │   ├── intercept_survey.xlsx
│   │   ├── student_survey.xlsx
│   │   └── contact_followup.xlsx
│   ├── choices/                         # Pre-exported choice lists from PostGIS
│   │   ├── business_names.csv
│   │   ├── addresses.csv
│   │   └── block_locations.csv
│   ├── export_choices.py                # Script to generate choice CSVs from PostGIS
│   ├── sync_field_data.py               # AGOL → PostGIS sync script
│   ├── schema.sql                       # PostGIS schema creation (tables + views)
│   ├── form_changelog.md               # Template for tracking form edits
│   └── README.md                        # Quick-start for the field team
├── tests/
│   └── test_field_survey/
│       ├── test_export_choices.py
│       ├── test_build_xlsforms.py
│       └── test_sync_field_data.py
```

**Responsibilities:**
- `export_choices.py` — connects to PostGIS, runs queries, writes CSVs for Survey123 choice lists
- `sync_field_data.py` — authenticates to AGOL, pulls feature layers, upserts into PostGIS `field_surveys` schema
- `schema.sql` — DDL for `field_surveys` schema: 6 raw tables + 5 analysis views
- `xlsform/*.xlsx` — XLSForm workbooks ready to upload to Survey123
- `form_changelog.md` — template for logging form edits during field week

---

## Chunk 1: PostGIS Schema & Choice List Export

### Task 1: Create PostGIS field_surveys schema

**Files:**
- Create: `field_survey/schema.sql`

- [ ] **Step 1: Write the schema SQL**

```sql
-- field_survey/schema.sql
-- Creates field_surveys schema with raw tables and analysis views

CREATE SCHEMA IF NOT EXISTS field_surveys;

-- ============================================================
-- RAW TABLES (1:1 mirror of AGOL feature layers)
-- ============================================================

CREATE TABLE IF NOT EXISTS field_surveys.resident_responses (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,          -- AGOL unique ID (upsert key)
    surveyor_id TEXT,
    survey_timestamp TIMESTAMPTZ,
    block_location TEXT,
    form_version TEXT,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    -- Demographics
    age_range TEXT,
    gender TEXT,
    household_size_range TEXT,
    years_in_neighbourhood TEXT,
    primary_language TEXT,
    -- Housing
    tenure_type TEXT,
    unit_type TEXT,
    monthly_rent_range TEXT,
    rent_increase_last_year TEXT,
    rent_increase_pct TEXT,
    fear_of_displacement INTEGER,           -- likert 1-5
    received_eviction_notice TEXT,
    -- Neighbourhood
    neighbourhood_satisfaction INTEGER,     -- likert 1-5
    biggest_concern TEXT,                   -- comma-separated multi-select
    biggest_asset TEXT,                     -- comma-separated multi-select
    perceived_safety_day INTEGER,           -- likert 1-5
    perceived_safety_night INTEGER,         -- likert 1-5
    noticed_changes_3yr TEXT,
    change_description TEXT,
    change_sentiment TEXT,
    -- Services
    access_grocery INTEGER,
    access_healthcare INTEGER,
    access_transit INTEGER,
    access_greenspace INTEGER,
    missing_services TEXT,
    -- Gentrification
    aware_of_development TEXT,
    development_impact TEXT,
    business_closures_noticed TEXT,
    closure_names TEXT,
    community_belonging INTEGER,            -- likert 1-5
    -- Close
    consent_followup TEXT,
    additional_comments TEXT
);

CREATE TABLE IF NOT EXISTS field_surveys.business_responses (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,
    surveyor_id TEXT,
    survey_timestamp TIMESTAMPTZ,
    business_name TEXT,
    street_address TEXT,
    informed_consent TEXT,
    form_version TEXT,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    geom GEOMETRY(Point, 2952),
    -- Business Profile
    business_type TEXT,
    years_operating TEXT,
    ownership_type TEXT,
    num_employees_range TEXT,
    is_original_business TEXT,
    -- Rent & Economics
    lease_type TEXT,
    monthly_rent_range TEXT,
    rent_change_3yr TEXT,
    revenue_trend_3yr TEXT,
    financial_viability INTEGER,
    -- Neighbourhood Change
    customer_base_change TEXT,
    foot_traffic_trend TEXT,
    competition_change TEXT,
    nearby_closures_noticed TEXT,
    closure_count_estimate TEXT,
    gentrification_impact INTEGER,
    biggest_threat TEXT,
    biggest_opportunity TEXT,
    -- Operations
    patio_program TEXT,
    accessibility_rating INTEGER,
    delivery_apps TEXT,
    heritage_building TEXT,
    -- Community
    belongs_to_bia TEXT,
    community_involvement TEXT,
    neighbourhood_satisfaction INTEGER,
    plans_next_3yr TEXT,
    -- Close
    additional_comments TEXT,
    consent_followup TEXT
);

CREATE TABLE IF NOT EXISTS field_surveys.intercept_responses (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,
    surveyor_id TEXT,
    survey_timestamp TIMESTAMPTZ,
    block_location TEXT,
    form_version TEXT,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    -- Who
    age_range TEXT,
    connection_to_area TEXT,
    visit_frequency TEXT,
    -- Experience
    reason_for_visit TEXT,
    how_arrived TEXT,
    time_spent_today TEXT,
    money_spent_today TEXT,
    -- Perception
    overall_impression INTEGER,
    perceived_safety INTEGER,
    cleanliness INTEGER,
    accessibility INTEGER,
    vibrancy INTEGER,
    -- Change
    noticed_changes TEXT,
    change_sentiment TEXT,
    one_word_kensington TEXT,
    -- Close
    would_recommend TEXT,
    what_would_improve TEXT
);

CREATE TABLE IF NOT EXISTS field_surveys.student_responses (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,
    surveyor_id TEXT,
    survey_timestamp TIMESTAMPTZ,
    campus_location TEXT,
    form_version TEXT,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    -- Profile
    age_range TEXT,
    student_status TEXT,
    faculty TEXT,
    lives_in_kensington_area TEXT,
    housing_type TEXT,
    monthly_rent_range TEXT,
    -- Kensington Relationship
    visit_frequency TEXT,
    reason_for_visit TEXT,
    how_arrived TEXT,
    money_spent_typical TEXT,
    -- Perception
    overall_impression INTEGER,
    perceived_safety INTEGER,
    sense_of_community INTEGER,
    authenticity INTEGER,
    affordability_perception INTEGER,
    -- Housing & Gentrification
    would_live_in_kensington TEXT,
    barrier_to_living_there TEXT,
    aware_of_gentrification TEXT,
    gentrification_opinion TEXT,
    student_housing_impact TEXT,
    -- Close
    one_word_kensington TEXT,
    what_would_improve TEXT
);

CREATE TABLE IF NOT EXISTS field_surveys.field_observations (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,
    surveyor_id TEXT,
    observation_timestamp TIMESTAMPTZ,
    form_version TEXT,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    geom GEOMETRY(Point, 2952),
    observation_type TEXT,
    notes TEXT,
    photo_url TEXT,
    raw_data JSONB                          -- catch-all for Field Maps attributes
);

CREATE TABLE IF NOT EXISTS field_surveys.contact_responses (
    id SERIAL PRIMARY KEY,
    globalid TEXT UNIQUE NOT NULL,
    sync_timestamp TIMESTAMPTZ DEFAULT NOW(),
    random_code TEXT,
    name TEXT,
    contact_method TEXT,
    contact_info TEXT,
    preferred_language TEXT
);

-- ============================================================
-- ANALYSIS VIEWS
-- ============================================================

-- v_resident_by_block: aggregate resident responses to block level
-- joins to building_assessment block-level averages for cross-analysis
CREATE OR REPLACE VIEW field_surveys.v_resident_by_block AS
SELECT
    r.block_location,
    r.response_count,
    r.avg_fear_of_displacement,
    r.avg_neighbourhood_satisfaction,
    r.avg_safety_day,
    r.avg_safety_night,
    r.avg_community_belonging,
    r.avg_access_grocery,
    r.avg_access_healthcare,
    r.avg_access_transit,
    r.avg_access_greenspace,
    r.dominant_tenure,
    r.dominant_change_sentiment,
    -- building_assessment block-level stats (joined by block_location text match)
    ba.avg_displacement_pressure,
    ba.avg_gentrification_index,
    ba.avg_livability_index,
    ba.avg_condition_rating,
    ba.vacancy_count,
    ba.building_count
FROM (
    SELECT
        block_location,
        COUNT(*) AS response_count,
        ROUND(AVG(fear_of_displacement), 2) AS avg_fear_of_displacement,
        ROUND(AVG(neighbourhood_satisfaction), 2) AS avg_neighbourhood_satisfaction,
        ROUND(AVG(perceived_safety_day), 2) AS avg_safety_day,
        ROUND(AVG(perceived_safety_night), 2) AS avg_safety_night,
        ROUND(AVG(community_belonging), 2) AS avg_community_belonging,
        ROUND(AVG(access_grocery), 2) AS avg_access_grocery,
        ROUND(AVG(access_healthcare), 2) AS avg_access_healthcare,
        ROUND(AVG(access_transit), 2) AS avg_access_transit,
        ROUND(AVG(access_greenspace), 2) AS avg_access_greenspace,
        MODE() WITHIN GROUP (ORDER BY tenure_type) AS dominant_tenure,
        MODE() WITHIN GROUP (ORDER BY change_sentiment) AS dominant_change_sentiment
    FROM field_surveys.resident_responses
    GROUP BY block_location
) r
LEFT JOIN (
    -- Aggregate building_assessment by the nearest road segment label
    -- This join depends on block_location matching the label format from export_choices.py
    -- At implementation time, a spatial join or lookup table may be needed
    SELECT
        'placeholder_block' AS block_location,
        ROUND(AVG(displacement_pressure::numeric), 2) AS avg_displacement_pressure,
        ROUND(AVG(gentrification_index), 2) AS avg_gentrification_index,
        ROUND(AVG(livability_index), 2) AS avg_livability_index,
        ROUND(AVG(ba_condition_rating), 2) AS avg_condition_rating,
        COUNT(*) FILTER (WHERE ba_is_vacant = 'Yes') AS vacancy_count,
        COUNT(*) AS building_count
    FROM public.building_assessment
    GROUP BY 1
) ba ON r.block_location = ba.block_location;

-- v_business_linked: direct join to building_assessment + business_licences
CREATE OR REPLACE VIEW field_surveys.v_business_linked AS
SELECT
    b.id AS survey_id,
    b.business_name,
    b.street_address,
    b.business_type,
    b.years_operating,
    b.financial_viability,
    b.gentrification_impact,
    b.plans_next_3yr,
    b.rent_change_3yr,
    b.foot_traffic_trend,
    b.customer_base_change,
    -- building_assessment fields
    ba."ba_condition_rating",
    ba."ba_is_vacant",
    ba."ba_storefront_status",
    ba."displacement_pressure",
    ba."gentrification_index",
    ba."safety_class",
    ba."VACANCY_SIGNALS",
    ba."BUSINESS_NAME" AS db_business_name,
    -- business licence
    bl.licence_type,
    bl.status AS licence_status,
    -- dinesafe
    ds.infraction_count,
    ds.latest_inspection,
    -- cafeto patios
    cp.has_patio_licence,
    cp.patio_category
FROM field_surveys.business_responses b
LEFT JOIN public.building_assessment ba
    ON LOWER(TRIM(b.street_address)) = LOWER(TRIM(ba."ADDRESS_FULL"))
LEFT JOIN online_data.business_licences bl
    ON LOWER(TRIM(b.business_name)) = LOWER(TRIM(bl.business_name))
LEFT JOIN (
    SELECT
        establishment_address,
        COUNT(*) AS infraction_count,
        MAX(inspection_date) AS latest_inspection
    FROM online_data.dinesafe
    GROUP BY establishment_address
) ds ON LOWER(TRIM(b.street_address)) = LOWER(TRIM(ds.establishment_address))
LEFT JOIN (
    SELECT
        municipal_address,
        TRUE AS has_patio_licence,
        category AS patio_category
    FROM online_data.cafeto_patios
) cp ON LOWER(TRIM(b.street_address)) = LOWER(TRIM(cp.municipal_address));

-- v_intercept_by_block: aggregate intercept responses by block
-- joins to crime and collision data for safety cross-analysis
CREATE OR REPLACE VIEW field_surveys.v_intercept_by_block AS
SELECT
    i.block_location,
    i.response_count,
    i.avg_impression,
    i.avg_safety,
    i.avg_cleanliness,
    i.avg_accessibility,
    i.avg_vibrancy,
    i.dominant_visitor_type,
    i.dominant_transport,
    -- Block-level crime/collision stats (joined same way as v_resident_by_block)
    -- NOTE: exact join logic depends on block_location format; spatial join may be
    -- needed at implementation time using a block-to-geometry lookup table
    crime.crime_count,
    crime.dominant_offence,
    ksi.ksi_count,
    ksi.pedestrian_ksi_count
FROM (
    SELECT
        block_location,
        COUNT(*) AS response_count,
        ROUND(AVG(overall_impression), 2) AS avg_impression,
        ROUND(AVG(perceived_safety), 2) AS avg_safety,
        ROUND(AVG(cleanliness), 2) AS avg_cleanliness,
        ROUND(AVG(accessibility), 2) AS avg_accessibility,
        ROUND(AVG(vibrancy), 2) AS avg_vibrancy,
        MODE() WITHIN GROUP (ORDER BY connection_to_area) AS dominant_visitor_type,
        MODE() WITHIN GROUP (ORDER BY how_arrived) AS dominant_transport
    FROM field_surveys.intercept_responses
    GROUP BY block_location
) i
LEFT JOIN (
    SELECT
        'placeholder_block' AS block_location,
        COUNT(*) AS crime_count,
        MODE() WITHIN GROUP (ORDER BY offence) AS dominant_offence
    FROM online_data.major_crime_indicators
    GROUP BY 1
) crime ON i.block_location = crime.block_location
LEFT JOIN (
    SELECT
        'placeholder_block' AS block_location,
        COUNT(*) AS ksi_count,
        COUNT(*) FILTER (WHERE pedestrian = 'Yes') AS pedestrian_ksi_count
    FROM online_data.ksi_collisions
    GROUP BY 1
) ksi ON i.block_location = ksi.block_location;

-- v_student_perception: standalone, comparable columns to intercept
CREATE OR REPLACE VIEW field_surveys.v_student_perception AS
SELECT
    COUNT(*) AS response_count,
    ROUND(AVG(s.overall_impression), 2) AS avg_impression,
    ROUND(AVG(s.perceived_safety), 2) AS avg_safety,
    ROUND(AVG(s.sense_of_community), 2) AS avg_community,
    ROUND(AVG(s.authenticity), 2) AS avg_authenticity,
    ROUND(AVG(s.affordability_perception), 2) AS avg_affordability,
    MODE() WITHIN GROUP (ORDER BY s.visit_frequency) AS dominant_visit_frequency,
    MODE() WITHIN GROUP (ORDER BY s.gentrification_opinion) AS dominant_gentrif_opinion,
    MODE() WITHIN GROUP (ORDER BY s.student_housing_impact) AS dominant_housing_impact
FROM field_surveys.student_responses s;

-- v_field_vs_database: compare Field Maps observations to existing records
CREATE OR REPLACE VIEW field_surveys.v_field_vs_database AS
SELECT
    fo.id AS observation_id,
    fo.observation_type,
    fo.notes,
    fo.observation_timestamp,
    fo.geom,
    -- Nearest building assessment within 25m
    ba."ADDRESS_FULL" AS nearest_address,
    ba."ba_condition_rating" AS db_condition_rating,
    ba."ba_is_vacant" AS db_vacant,
    ba."ba_storefront_status" AS db_storefront_status,
    ST_Distance(fo.geom, ba.geom) AS distance_m
FROM field_surveys.field_observations fo
LEFT JOIN LATERAL (
    SELECT *
    FROM public.building_assessment ba2
    WHERE ba2.geom IS NOT NULL
    ORDER BY fo.geom <-> ba2.geom
    LIMIT 1
) ba ON ST_Distance(fo.geom, ba.geom) < 25;
```

- [ ] **Step 2: Apply schema to PostGIS**

Run:
```bash
cd C:/Users/liam1/gis-script-generator
PGPASSWORD=test123 psql -h localhost -p 5432 -U postgres -d kensington -f field_survey/schema.sql
```

Expected: Tables and views created without errors.

- [ ] **Step 3: Verify schema**

Run:
```bash
PGPASSWORD=test123 psql -h localhost -p 5432 -U postgres -d kensington -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'field_surveys' ORDER BY 1;"
```

Expected: 5 tables listed (business_responses, field_observations, intercept_responses, resident_responses, student_responses).

- [ ] **Step 4: Commit**

```bash
git add field_survey/schema.sql
git commit -m "feat(field-survey): add PostGIS schema for field survey data"
```

---

### Task 2: Build choice list export script

**Files:**
- Create: `field_survey/export_choices.py`
- Create: `tests/test_field_survey/test_export_choices.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_field_survey/test_export_choices.py
import csv
import os
import pytest
from unittest.mock import patch, MagicMock

from field_survey.export_choices import (
    export_business_names,
    export_addresses,
    export_block_locations,
)


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_export_business_names_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [("Cafe A",), ("Shop B",), ("Market C",)]
    outfile = tmp_path / "business_names.csv"

    export_business_names(conn, str(outfile))

    assert outfile.exists()
    rows = list(csv.DictReader(open(outfile)))
    assert len(rows) == 4  # 3 from DB + 1 "Other" fallback
    assert rows[0]["name"] == "Cafe A"
    assert rows[0]["label"] == "Cafe A"
    assert rows[-1]["name"] == "__other__"


def test_export_addresses_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [("123 Kensington Ave",), ("456 Augusta Ave",)]
    outfile = tmp_path / "addresses.csv"

    export_addresses(conn, str(outfile))

    rows = list(csv.DictReader(open(outfile)))
    assert len(rows) == 2
    assert rows[0]["name"] == "123 Kensington Ave"


def test_export_block_locations_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [
        ("Kensington Ave (Dundas to Baldwin)",),
        ("Augusta Ave (Dundas to Nassau)",),
    ]
    outfile = tmp_path / "block_locations.csv"

    export_block_locations(conn, str(outfile))

    rows = list(csv.DictReader(open(outfile)))
    assert len(rows) == 2
    assert "Kensington" in rows[0]["label"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_field_survey/test_export_choices.py -v`
Expected: ImportError — module doesn't exist yet.

- [ ] **Step 3: Write the export script**

```python
# field_survey/export_choices.py
"""
Export PostGIS data as CSV choice lists for Survey123 XLSForms.

Usage:
    python -m field_survey.export_choices [--output-dir field_survey/choices]

Requires: psycopg, connection to kensington database.
"""
import csv
import os
import sys

import psycopg


def export_business_names(conn, outfile: str) -> int:
    """Export distinct business names as XLSForm choice list CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT name FROM (
            SELECT business_name AS name FROM online_data.business_licences
            WHERE business_name IS NOT NULL
            UNION
            SELECT "BUSINESS_NAME" AS name FROM public.building_assessment
            WHERE "BUSINESS_NAME" IS NOT NULL
        ) sub
        ORDER BY name
    """)
    rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (name,) in rows:
            writer.writerow(["business_name", name, name])
        writer.writerow(["business_name", "__other__", "Other (type below)"])

    return len(rows) + 1


def export_addresses(conn, outfile: str) -> int:
    """Export distinct addresses as XLSForm choice list CSV."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT "ADDRESS_FULL"
        FROM public.building_assessment
        WHERE "ADDRESS_FULL" IS NOT NULL
        ORDER BY "ADDRESS_FULL"
    """)
    rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (addr,) in rows:
            writer.writerow(["street_address", addr, addr])

    return len(rows)


def export_block_locations(conn, outfile: str) -> int:
    """Export block-level location labels as XLSForm choice list CSV.

    Format: "Street Name (From Cross St to Cross St)" per spec.
    Falls back to "Street Name (segment N)" if cross-street data unavailable.
    """
    cur = conn.cursor()
    # Try cross-street format first
    cur.execute("""
        SELECT DISTINCT
            r.linear_name_full || ' (' ||
            COALESCE(f.linear_name_full, 'start') || ' to ' ||
            COALESCE(t.linear_name_full, 'end') || ')' AS block_label
        FROM opendata.road_centerlines r
        LEFT JOIN LATERAL (
            SELECT DISTINCT r2.linear_name_full
            FROM opendata.road_centerlines r2
            WHERE r2.from_intersection_id = r.from_intersection_id
            AND r2.linear_name_full != r.linear_name_full
            LIMIT 1
        ) f ON TRUE
        LEFT JOIN LATERAL (
            SELECT DISTINCT r2.linear_name_full
            FROM opendata.road_centerlines r2
            WHERE r2.from_intersection_id = r.to_intersection_id
            AND r2.linear_name_full != r.linear_name_full
            LIMIT 1
        ) t ON TRUE
        ORDER BY 1
    """)
    rows = cur.fetchall()

    # Fallback: simple street name list if cross-street query fails
    if not rows:
        cur.execute("""
            SELECT DISTINCT linear_name_full
            FROM opendata.road_centerlines
            ORDER BY 1
        """)
        rows = cur.fetchall()

    with open(outfile, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["list_name", "name", "label"])
        for (label,) in rows:
            safe_name = label.lower().replace(" ", "_").replace("(", "").replace(")", "")
            writer.writerow(["block_location", safe_name, label])

    return len(rows)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Export PostGIS data as Survey123 choice lists")
    parser.add_argument("--output-dir", default="field_survey/choices")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--dbname", default="kensington")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=os.environ.get("PGPASSWORD", ""))
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    conn = psycopg.connect(
        host=args.host, port=args.port,
        dbname=args.dbname, user=args.user, password=args.password,
    )

    n1 = export_business_names(conn, os.path.join(args.output_dir, "business_names.csv"))
    print(f"Exported {n1} business names")

    n2 = export_addresses(conn, os.path.join(args.output_dir, "addresses.csv"))
    print(f"Exported {n2} addresses")

    n3 = export_block_locations(conn, os.path.join(args.output_dir, "block_locations.csv"))
    print(f"Exported {n3} block locations")

    conn.close()
    print(f"Choice lists saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Create `__init__.py` files**

```bash
touch field_survey/__init__.py
touch tests/test_field_survey/__init__.py
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_field_survey/test_export_choices.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Run export against real database**

Run:
```bash
cd C:/Users/liam1/gis-script-generator
python -m field_survey.export_choices --password test123
```

Expected: 3 CSV files in `field_survey/choices/`, with counts printed (~450 business names, ~1072 addresses, ~56+ block locations).

- [ ] **Step 7: Commit**

```bash
git add field_survey/export_choices.py field_survey/__init__.py tests/test_field_survey/
git commit -m "feat(field-survey): add choice list export script for Survey123 dropdowns"
```

---

## Chunk 2: XLSForm Workbooks

### Task 3: Generate XLSForm workbooks programmatically

Rather than manually crafting 5 xlsx files, we write a Python script that generates them from the spec. This ensures consistency and makes updates easy.

**Files:**
- Create: `field_survey/build_xlsforms.py`

- [ ] **Step 1: Write the XLSForm builder**

```python
# field_survey/build_xlsforms.py
"""
Generate Survey123 XLSForm workbooks from spec definitions.

Usage:
    python -m field_survey.build_xlsforms [--output-dir field_survey/xlsform]
    [--choices-dir field_survey/choices]

Requires: openpyxl
"""
import csv
import os

import openpyxl


# ── Form definitions ────────────────────────────────────────────────────

SURVEYORS = ["Surveyor_1", "Surveyor_2", "Surveyor_3", "Surveyor_4", "Surveyor_5", "Surveyor_6"]

# Each form is a list of dicts with keys:
#   type, name, label, required, relevant, appearance, choice_list, hint
# type values: select_one <list>, select_multiple <list>, text, integer, dateTime, geopoint,
#              begin_group, end_group, note, hidden, range (for likert)

def _likert(name, label, low="1 - Strongly disagree", high="5 - Strongly agree"):
    """Helper: produces a select_one for a 1-5 likert scale."""
    return {
        "type": "select_one likert5",
        "name": name,
        "label": label,
        "hint": f"{low} ... {high}",
        "required": "yes",
    }


def _select(name, label, list_name, **kwargs):
    return {"type": f"select_one {list_name}", "name": name, "label": label, "required": "yes", **kwargs}


def _multi(name, label, list_name, **kwargs):
    return {"type": f"select_multiple {list_name}", "name": name, "label": label, "required": "yes", **kwargs}


def _text(name, label, **kwargs):
    return {"type": "text", "name": name, "label": label, **kwargs}


def _group(name, label):
    return {"type": "begin_group", "name": name, "label": label}


def _end():
    return {"type": "end_group"}


def _note(label):
    return {"type": "note", "name": f"note_{hash(label) % 10000}", "label": label}


# ── Choice lists (inline) ──────────────────────────────────────────────

INLINE_CHOICES = {
    "yes_no": [("yes", "Yes"), ("no", "No")],
    "yes_no_dk": [("yes", "Yes"), ("no", "No"), ("dont_know", "Don't know")],
    "yes_no_pnts": [("yes", "Yes"), ("no", "No"), ("pnts", "Prefer not to say")],
    "consent_gate": [("yes", "Yes, I consent"), ("no", "No, I do not consent")],
    "likert5": [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5")],
    "gender": [("man", "Man"), ("woman", "Woman"), ("nonbinary", "Non-binary"), ("pnts", "Prefer not to say")],
    "age_range": [("18_24", "18-24"), ("25_34", "25-34"), ("35_44", "35-44"), ("45_54", "45-54"), ("55_64", "55-64"), ("65_plus", "65+")],
    "age_range_student": [("18_21", "18-21"), ("22_25", "22-25"), ("26_30", "26-30"), ("30_plus", "30+")],
    "household_size": [("1", "1"), ("2_3", "2-3"), ("4_5", "4-5"), ("6_plus", "6+")],
    "years_neighbourhood": [("lt1", "Less than 1 year"), ("1_3", "1-3 years"), ("3_5", "3-5 years"), ("5_10", "5-10 years"), ("10_20", "10-20 years"), ("20_plus", "20+ years")],
    "tenure": [("rent", "Rent"), ("own", "Own"), ("social", "Social housing"), ("other", "Other")],
    "unit_type": [("house", "House"), ("apartment", "Apartment"), ("rooming", "Rooming house"), ("above_shop", "Above-shop unit"), ("other", "Other")],
    "rent_range_res": [("lt800", "Less than $800"), ("800_1200", "$800-$1,200"), ("1200_1600", "$1,200-$1,600"), ("1600_2000", "$1,600-$2,000"), ("2000_plus", "$2,000+"), ("na", "N/A")],
    "rent_increase_pct": [("lt2", "Less than 2%"), ("2_5", "2-5%"), ("5_10", "5-10%"), ("gt10", "More than 10%"), ("dk", "Don't know")],
    "changes_3yr": [("major", "Major changes"), ("some", "Some changes"), ("none", "No change"), ("new", "New to area")],
    "sentiment": [("positive", "Positive"), ("negative", "Negative"), ("mixed", "Mixed"), ("neutral", "Neutral")],
    "dev_impact": [("positive", "Positive"), ("negative", "Negative"), ("mixed", "Mixed"), ("no_opinion", "No opinion")],
    "concern": [("affordability", "Affordability"), ("safety", "Safety"), ("noise", "Noise"), ("cleanliness", "Cleanliness"), ("traffic", "Traffic"), ("development", "Development"), ("loss_character", "Loss of character"), ("other", "Other")],
    "asset": [("community", "Community"), ("diversity", "Diversity"), ("walkability", "Walkability"), ("food", "Food"), ("markets", "Markets"), ("culture", "Culture"), ("greenspace", "Greenspace"), ("affordability", "Affordability"), ("other", "Other")],
    # Business
    "business_type": [("restaurant", "Restaurant"), ("cafe", "Cafe"), ("retail", "Retail"), ("market_vendor", "Market vendor"), ("service", "Service"), ("bar", "Bar"), ("grocery", "Grocery"), ("other", "Other")],
    "years_operating": [("lt1", "Less than 1 year"), ("1_3", "1-3 years"), ("3_5", "3-5 years"), ("5_10", "5-10 years"), ("10_20", "10-20 years"), ("20_plus", "20+ years")],
    "ownership": [("owner", "Owner-operated"), ("franchise", "Franchise"), ("family", "Family business"), ("partnership", "Partnership"), ("other", "Other")],
    "employees": [("1_2", "1-2"), ("3_5", "3-5"), ("6_10", "6-10"), ("11_20", "11-20"), ("20_plus", "20+")],
    "lease_type": [("month", "Month-to-month"), ("short", "Short-term (< 3 years)"), ("long", "Long-term (3+ years)"), ("own", "Own the building"), ("pnts", "Prefer not to say")],
    "rent_range_biz": [("lt2k", "Less than $2,000"), ("2_4k", "$2,000-$4,000"), ("4_6k", "$4,000-$6,000"), ("6_10k", "$6,000-$10,000"), ("10k_plus", "$10,000+"), ("pnts", "Prefer not to say")],
    "rent_change": [("inc_lot", "Increased a lot"), ("inc_some", "Increased somewhat"), ("stable", "Stable"), ("decreased", "Decreased"), ("new_lease", "New lease"), ("pnts", "Prefer not to say")],
    "revenue_trend": [("growing", "Growing"), ("stable", "Stable"), ("declining", "Declining"), ("pnts", "Prefer not to say")],
    "customer_change": [("tourists", "More tourists"), ("students", "More students"), ("locals", "More locals"), ("no_change", "No change"), ("mixed", "Mixed")],
    "traffic_trend": [("increasing", "Increasing"), ("stable", "Stable"), ("decreasing", "Decreasing"), ("seasonal", "Seasonal")],
    "competition": [("more", "More competition"), ("less", "Less competition"), ("same", "Same"), ("different", "Different type of competition")],
    "closure_count": [("1_2", "1-2"), ("3_5", "3-5"), ("5_plus", "5+")],
    "threat": [("rent", "Rising rent"), ("clientele", "Changing clientele"), ("competition", "Competition"), ("development", "Development"), ("parking", "Parking"), ("crime", "Crime"), ("regulation", "Regulation"), ("none", "None"), ("other", "Other")],
    "opportunity": [("tourism", "Tourism"), ("new_residents", "New residents"), ("events", "Events"), ("online", "Online presence"), ("community", "Community support"), ("other", "Other")],
    "patio": [("yes", "Yes"), ("no", "No"), ("denied", "Applied but denied"), ("na", "Not applicable")],
    "heritage_dk": [("yes", "Yes"), ("no", "No"), ("dk", "Don't know")],
    "bia": [("yes", "Yes"), ("no", "No"), ("dk", "Don't know")],
    "community_inv": [("bia", "BIA"), ("market_events", "Market events"), ("neighbourhood_assoc", "Neighbourhood association"), ("none", "None"), ("other", "Other")],
    "plans_3yr": [("stay", "Stay"), ("expand", "Expand"), ("downsize", "Downsize"), ("relocate", "Relocate"), ("close", "Close"), ("uncertain", "Uncertain")],
    # Intercept
    "connection": [("live", "Live here"), ("work", "Work here"), ("visiting", "Visiting"), ("shopping", "Shopping"), ("passing", "Passing through"), ("student", "Student nearby")],
    "visit_freq": [("daily", "Daily"), ("few_week", "Few times a week"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("first", "First time"), ("rarely", "Rarely")],
    "visit_reason": [("food", "Food"), ("shopping", "Shopping"), ("restaurant_bar", "Restaurant/Bar"), ("work", "Work"), ("live", "Live here"), ("exploring", "Exploring"), ("meeting", "Meeting someone"), ("other", "Other")],
    "transport": [("walk", "Walk"), ("bike", "Bike"), ("ttc", "TTC"), ("car", "Car"), ("rideshare", "Rideshare")],
    "transport_student": [("walk", "Walk"), ("bike", "Bike"), ("ttc", "TTC"), ("car", "Car"), ("other", "Other")],
    "time_spent": [("lt30", "Less than 30 min"), ("30_60", "30 min - 1 hour"), ("1_2hr", "1-2 hours"), ("2_4hr", "2-4 hours"), ("4_plus", "4+ hours")],
    "money_spent": [("0", "$0"), ("lt20", "Less than $20"), ("20_50", "$20-$50"), ("50_100", "$50-$100"), ("100_plus", "$100+")],
    "changes_yn": [("yes", "Yes"), ("no", "No"), ("dk", "Don't visit enough to know")],
    "recommend": [("yes", "Yes"), ("no", "No"), ("maybe", "Maybe")],
    "improve_intercept": [("cleanliness", "Cleanliness"), ("safety", "Safety"), ("seating", "More seating"), ("washrooms", "Public washrooms"), ("less_traffic", "Less traffic"), ("greenery", "More greenery"), ("nothing", "Nothing"), ("other", "Other")],
    # Student
    "student_status": [("undergrad", "Undergraduate"), ("graduate", "Graduate"), ("postdoc", "Post-doc"), ("staff", "Staff")],
    "faculty": [("arts_sci", "Arts & Science"), ("engineering", "Engineering"), ("architecture", "Architecture"), ("planning", "Planning"), ("social_work", "Social Work"), ("other", "Other")],
    "lives_kenso": [("yes", "Yes"), ("no", "No"), ("used_to", "Used to")],
    "housing_student": [("on_campus", "On-campus"), ("rent_nearby", "Rent nearby"), ("rent_elsewhere", "Rent elsewhere"), ("family", "With family"), ("other", "Other")],
    "visit_freq_student": [("daily", "Daily"), ("few_week", "Few times a week"), ("weekly", "Weekly"), ("monthly", "Monthly"), ("rarely", "Rarely"), ("never", "Never")],
    "visit_reason_student": [("food", "Food"), ("bars", "Bars"), ("shopping", "Shopping"), ("vintage", "Vintage stores"), ("exploring", "Exploring"), ("friends", "Friends live there"), ("live", "Live there"), ("never", "Never visit")],
    "would_live": [("yes", "Yes"), ("already", "Already do"), ("no", "No"), ("used_to", "Used to")],
    "barrier": [("rent", "Rent too high"), ("safety", "Safety"), ("far", "Too far from campus"), ("noise", "Noise"), ("quality", "Housing quality"), ("none", "No barrier"), ("other", "Other")],
    "gentrif_aware": [("yes", "Yes"), ("somewhat", "Somewhat"), ("no", "No")],
    "gentrif_opinion": [("positive", "Positive"), ("negative", "Negative"), ("mixed", "Mixed"), ("no_opinion", "No opinion")],
    "student_impact": [("drive_up", "Students drive up rents"), ("priced_out", "Students are also priced out"), ("no_impact", "No impact"), ("dk", "Don't know")],
    "improve_student": [("affordability", "Affordability"), ("safety", "Safety"), ("cleanliness", "Cleanliness"), ("student_spaces", "More student spaces"), ("transit", "Better transit"), ("nothing", "Nothing"), ("other", "Other")],
    # Campus locations
    "campus_loc": [("robarts", "Robarts Library"), ("sidney_smith", "Sidney Smith"), ("hart_house", "Hart House"), ("spadina_college", "Spadina & College"), ("spadina_dundas", "Spadina & Dundas"), ("other", "Other")],
    # Contact
    "contact_method": [("email", "Email"), ("phone", "Phone"), ("either", "Either")],
    "language_pref": [("english", "English"), ("french", "French"), ("mandarin", "Mandarin"), ("cantonese", "Cantonese"), ("portuguese", "Portuguese"), ("spanish", "Spanish"), ("other", "Other")],
    # Surveyor
    "surveyor": [(f"surveyor_{i}", f"Surveyor {i}") for i in range(1, 7)],
}

# ── Form 1: Resident Survey ────────────────────────────────────────────

RESIDENT_SURVEY = [
    _note("**Kensington Market Resident Survey**\n\nThis survey is anonymous. Your responses will be aggregated at the block level. No address or exact location is recorded."),
    # Metadata
    _group("metadata", "Survey Information"),
    _select("surveyor_id", "Surveyor", "surveyor"),
    {"type": "dateTime", "name": "survey_timestamp", "label": "Date/Time", "default": "now()"},
    _select("block_location", "Block Location", "block_location", **{"appearance": "search"}),
    _select("informed_consent", "Do you consent to participate in this anonymous survey?", "consent_gate"),
    {"type": "hidden", "name": "form_version", "label": "Form Version", "default": "1.0"},
    _end(),
    # Demographics
    _group("demographics", "About You"),
    _select("age_range", "Age range", "age_range"),
    _select("gender", "Gender", "gender"),
    _select("household_size_range", "Household size", "household_size"),
    _select("years_in_neighbourhood", "How long have you lived in this neighbourhood?", "years_neighbourhood"),
    _text("primary_language", "What is your primary language at home?", required="no"),
    _end(),
    # Housing
    _group("housing", "Housing"),
    _select("tenure_type", "Do you rent or own?", "tenure"),
    _select("unit_type", "What type of unit do you live in?", "unit_type"),
    _select("monthly_rent_range", "Monthly rent range", "rent_range_res", relevant="${tenure_type} != 'own'"),
    _select("rent_increase_last_year", "Has your rent increased in the last year?", "yes_no_dk", relevant="${tenure_type} != 'own'"),
    _select("rent_increase_pct", "By approximately how much?", "rent_increase_pct", relevant="${rent_increase_last_year} = 'yes'"),
    _likert("fear_of_displacement", "How worried are you about being displaced from your home?", "1 - Not at all worried", "5 - Extremely worried"),
    _select("received_eviction_notice", "Have you received an eviction notice in the past 2 years?", "yes_no_pnts"),
    _end(),
    # Neighbourhood
    _group("neighbourhood", "Your Neighbourhood"),
    _likert("neighbourhood_satisfaction", "Overall satisfaction with the neighbourhood", "1 - Very dissatisfied", "5 - Very satisfied"),
    _multi("biggest_concern", "What are your biggest concerns? (select all that apply)", "concern"),
    _multi("biggest_asset", "What do you value most about the neighbourhood? (select all)", "asset"),
    _likert("perceived_safety_day", "How safe do you feel during the day?", "1 - Very unsafe", "5 - Very safe"),
    _likert("perceived_safety_night", "How safe do you feel at night?", "1 - Very unsafe", "5 - Very safe"),
    _select("noticed_changes_3yr", "Have you noticed changes in the last 3 years?", "changes_3yr"),
    _text("change_description", "Describe the changes you've noticed", relevant="${noticed_changes_3yr} != 'none' and ${noticed_changes_3yr} != 'new'", required="no"),
    _select("change_sentiment", "Overall, are these changes...", "sentiment", relevant="${noticed_changes_3yr} != 'none' and ${noticed_changes_3yr} != 'new'"),
    _end(),
    # Services
    _group("services", "Access to Services"),
    _likert("access_grocery", "Ease of access to grocery stores", "1 - Very difficult", "5 - Very easy"),
    _likert("access_healthcare", "Ease of access to healthcare", "1 - Very difficult", "5 - Very easy"),
    _likert("access_transit", "Ease of access to public transit", "1 - Very difficult", "5 - Very easy"),
    _likert("access_greenspace", "Ease of access to parks/green space", "1 - Very difficult", "5 - Very easy"),
    _text("missing_services", "What service or amenity is missing from this neighbourhood?", required="no"),
    _end(),
    # Gentrification
    _group("gentrification", "Neighbourhood Change"),
    _select("aware_of_development", "Are you aware of new development in the area?", "yes_no"),
    _select("development_impact", "How do you feel about the development?", "dev_impact", relevant="${aware_of_development} = 'yes'"),
    _select("business_closures_noticed", "Have you noticed business closures recently?", "yes_no"),
    _text("closure_names", "Which businesses closed?", relevant="${business_closures_noticed} = 'yes'", required="no"),
    _likert("community_belonging", "How strongly do you feel you belong to this community?", "1 - Not at all", "5 - Very strongly"),
    _end(),
    # Close
    _group("close", "Thank You"),
    _select("consent_followup", "Would you be willing to be contacted for a follow-up?", "yes_no"),
    _text("additional_comments", "Any other comments?", required="no"),
    _end(),
]

# ── Form 2: Business Owner Survey ──────────────────────────────────────

BUSINESS_SURVEY = [
    _note("**Kensington Market Business Survey**\n\nYour business may be identified in published results. No personal names will be recorded or published."),
    _group("metadata", "Survey Information"),
    _select("surveyor_id", "Surveyor", "surveyor"),
    {"type": "dateTime", "name": "survey_timestamp", "label": "Date/Time", "default": "now()"},
    _select("business_name", "Business Name", "business_name", **{"appearance": "search"}),
    _select("street_address", "Street Address", "street_address", **{"appearance": "search"}),
    {"type": "geopoint", "name": "gps_location", "label": "GPS Location"},
    _select("informed_consent", "I understand my business may be identified. No personal names will be published.", "consent_gate"),
    {"type": "hidden", "name": "form_version", "label": "Form Version", "default": "1.0"},
    _end(),
    _group("profile", "Business Profile"),
    _select("business_type", "Type of business", "business_type"),
    _select("years_operating", "Years operating at this location", "years_operating"),
    _select("ownership_type", "Ownership type", "ownership"),
    _select("num_employees_range", "Number of employees", "employees"),
    _select("is_original_business", "Was this business founded at this location?", "yes_no"),
    _end(),
    _group("economics", "Rent & Economics"),
    _select("lease_type", "Lease type", "lease_type"),
    _select("monthly_rent_range", "Monthly rent", "rent_range_biz"),
    _select("rent_change_3yr", "How has rent changed in 3 years?", "rent_change"),
    _select("revenue_trend_3yr", "Revenue trend over 3 years", "revenue_trend"),
    _likert("financial_viability", "Financial viability of business", "1 - At risk of closing", "5 - Very secure"),
    _end(),
    _group("change", "Neighbourhood Change"),
    _select("customer_base_change", "How has your customer base changed?", "customer_change"),
    _select("foot_traffic_trend", "Foot traffic trend", "traffic_trend"),
    _select("competition_change", "How has competition changed?", "competition"),
    _select("nearby_closures_noticed", "Noticed nearby business closures?", "yes_no"),
    _select("closure_count_estimate", "How many closures?", "closure_count", relevant="${nearby_closures_noticed} = 'yes'"),
    _likert("gentrification_impact", "Impact of gentrification on your business", "1 - Very negative", "5 - Very positive"),
    _multi("biggest_threat", "Biggest threats to your business (select all)", "threat"),
    _multi("biggest_opportunity", "Biggest opportunities (select all)", "opportunity"),
    _end(),
    _group("operations", "Operations"),
    _select("patio_program", "Participate in CafeTO patio program?", "patio"),
    _likert("accessibility_rating", "How accessible is your business?", "1 - Not accessible", "5 - Fully accessible"),
    _select("delivery_apps", "Do you use delivery apps?", "yes_no"),
    _select("heritage_building", "Is this a heritage building?", "heritage_dk"),
    _end(),
    _group("community", "Community"),
    _select("belongs_to_bia", "Member of a BIA?", "bia"),
    _multi("community_involvement", "Community involvement (select all)", "community_inv"),
    _likert("neighbourhood_satisfaction", "Neighbourhood satisfaction", "1 - Very dissatisfied", "5 - Very satisfied"),
    _select("plans_next_3yr", "Plans for next 3 years", "plans_3yr"),
    _end(),
    _group("close", "Thank You"),
    _text("additional_comments", "Any other comments?", required="no"),
    _select("consent_followup", "Willing to be contacted for follow-up?", "yes_no"),
    _end(),
]

# ── Form 3: Street Intercept Survey ────────────────────────────────────

INTERCEPT_SURVEY = [
    _note("**Kensington Market Visitor Survey** (3-4 minutes)\n\nThis survey is anonymous."),
    _group("metadata", "Survey Information"),
    _select("surveyor_id", "Surveyor", "surveyor"),
    {"type": "dateTime", "name": "survey_timestamp", "label": "Date/Time", "default": "now()"},
    _select("block_location", "Block Location", "block_location", **{"appearance": "search"}),
    _select("informed_consent", "Do you consent to this anonymous survey?", "consent_gate"),
    {"type": "hidden", "name": "form_version", "label": "Form Version", "default": "1.0"},
    _end(),
    _group("who", "About You"),
    _select("age_range", "Age range", "age_range"),
    _select("connection_to_area", "Connection to Kensington", "connection"),
    _select("visit_frequency", "How often do you visit?", "visit_freq"),
    _end(),
    _group("experience", "Your Visit Today"),
    _multi("reason_for_visit", "Why are you here today? (select all)", "visit_reason"),
    _select("how_arrived", "How did you get here?", "transport"),
    _select("time_spent_today", "Time spent here today", "time_spent"),
    _select("money_spent_today", "Money spent today", "money_spent"),
    _end(),
    _group("perception", "Your Impression"),
    _likert("overall_impression", "Overall impression of Kensington", "1 - Very negative", "5 - Very positive"),
    _likert("perceived_safety", "How safe do you feel?", "1 - Very unsafe", "5 - Very safe"),
    _likert("cleanliness", "Cleanliness", "1 - Very dirty", "5 - Very clean"),
    _likert("accessibility", "Accessibility", "1 - Not accessible", "5 - Very accessible"),
    _likert("vibrancy", "How lively does it feel?", "1 - Dead", "5 - Very lively"),
    _end(),
    _group("change_section", "Change"),
    _select("noticed_changes", "Have you noticed changes?", "changes_yn"),
    _select("change_sentiment", "Are the changes...", "sentiment", relevant="${noticed_changes} = 'yes'"),
    _text("one_word_kensington", "One word to describe Kensington?"),
    _end(),
    _group("close", "Thank You"),
    _select("would_recommend", "Would you recommend visiting Kensington?", "recommend"),
    _multi("what_would_improve", "What would improve Kensington? (select all)", "improve_intercept"),
    _end(),
]

# ── Form 4: Student Survey ─────────────────────────────────────────────

STUDENT_SURVEY = [
    _note("**UofT Student Survey — Kensington Market** (4-5 minutes)\n\nThis survey is anonymous."),
    _group("metadata", "Survey Information"),
    _select("surveyor_id", "Surveyor", "surveyor"),
    {"type": "dateTime", "name": "survey_timestamp", "label": "Date/Time", "default": "now()"},
    _select("campus_location", "Where on campus are you now?", "campus_loc"),
    _select("informed_consent", "Do you consent to this anonymous survey?", "consent_gate"),
    {"type": "hidden", "name": "form_version", "label": "Form Version", "default": "1.0"},
    _end(),
    _group("profile", "About You"),
    _select("age_range", "Age range", "age_range_student"),
    _select("student_status", "Student status", "student_status"),
    _select("faculty", "Faculty", "faculty"),
    _select("lives_in_kensington_area", "Do you live in/near Kensington?", "lives_kenso"),
    _select("housing_type", "Housing type", "housing_student"),
    _select("monthly_rent_range", "Monthly rent", "rent_range_res"),
    _end(),
    _group("kensington", "Kensington Market"),
    _select("visit_frequency", "How often do you visit Kensington?", "visit_freq_student"),
    _multi("reason_for_visit", "Why do you visit? (select all)", "visit_reason_student"),
    _select("how_arrived", "How do you usually get there?", "transport_student", relevant="${visit_frequency} != 'never'"),
    _select("money_spent_typical", "Typical spend per visit", "money_spent", relevant="${visit_frequency} != 'never'"),
    _end(),
    _group("perception", "Your Perception"),
    _likert("overall_impression", "Overall impression of Kensington", "1 - Very negative", "5 - Very positive"),
    _likert("perceived_safety", "How safe does Kensington feel?", "1 - Very unsafe", "5 - Very safe"),
    _likert("sense_of_community", "Sense of community", "1 - No community feel", "5 - Strong community"),
    _likert("authenticity", "How authentic does it feel?", "1 - Commercialized", "5 - Authentic"),
    _likert("affordability_perception", "How affordable is Kensington?", "1 - Too expensive", "5 - Very affordable"),
    _end(),
    _group("housing_gentrif", "Housing & Gentrification"),
    _select("would_live_in_kensington", "Would you live in Kensington?", "would_live"),
    _multi("barrier_to_living_there", "What prevents you? (select all)", "barrier", relevant="${would_live_in_kensington} = 'no'"),
    _select("aware_of_gentrification", "Aware of gentrification in Kensington?", "gentrif_aware"),
    _select("gentrification_opinion", "Your opinion on gentrification there", "gentrif_opinion"),
    _select("student_housing_impact", "Impact of students on Kensington housing", "student_impact"),
    _end(),
    _group("close", "Thank You"),
    _text("one_word_kensington", "One word to describe Kensington?"),
    _multi("what_would_improve", "What would improve Kensington? (select all)", "improve_student"),
    _end(),
]

# ── Form 5: Follow-up Contact (separate, unlinked) ─────────────────────

CONTACT_FORM = [
    _note("**Follow-up Contact Form**\n\nThis form is NOT linked to any survey response. The random code is for consent withdrawal only."),
    _text("random_code", "Random code from card"),
    _text("name", "Name (optional)", required="no"),
    _select("contact_method", "Preferred contact method", "contact_method"),
    _text("contact_info", "Email or phone number"),
    _select("preferred_language", "Preferred language", "language_pref"),
]


# ── XLSForm writer ─────────────────────────────────────────────────────

def _write_xlsform(form_fields, form_title, outfile, choices_dir=None):
    """Write an XLSForm .xlsx workbook."""
    wb = openpyxl.Workbook()

    # ── survey sheet ──
    ws = wb.active
    ws.title = "survey"
    headers = ["type", "name", "label", "hint", "required", "relevant", "appearance", "default"]
    ws.append(headers)

    for field in form_fields:
        row = [
            field.get("type", ""),
            field.get("name", ""),
            field.get("label", ""),
            field.get("hint", ""),
            field.get("required", ""),
            field.get("relevant", ""),
            field.get("appearance", ""),
            field.get("default", ""),
        ]
        ws.append(row)

    # ── choices sheet ──
    ws_choices = wb.create_sheet("choices")
    ws_choices.append(["list_name", "name", "label"])

    # Write inline choices
    used_lists = set()
    for field in form_fields:
        ftype = field.get("type", "")
        for prefix in ("select_one ", "select_multiple "):
            if ftype.startswith(prefix):
                list_name = ftype[len(prefix):]
                used_lists.add(list_name)

    for list_name in sorted(used_lists):
        if list_name in INLINE_CHOICES:
            for name, label in INLINE_CHOICES[list_name]:
                ws_choices.append([list_name, name, label])

    # Append external choice lists from CSV if available
    if choices_dir:
        for csv_file in ["business_names.csv", "addresses.csv", "block_locations.csv"]:
            csv_path = os.path.join(choices_dir, csv_file)
            if os.path.exists(csv_path):
                with open(csv_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("list_name") in used_lists:
                            ws_choices.append([row["list_name"], row["name"], row["label"]])

    # ── settings sheet ──
    ws_settings = wb.create_sheet("settings")
    ws_settings.append(["form_title", "form_id", "version", "style"])
    form_id = form_title.lower().replace(" ", "_").replace("-", "_")
    ws_settings.append([form_title, form_id, "1.0", "theme-grid"])

    wb.save(outfile)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate Survey123 XLSForm workbooks")
    parser.add_argument("--output-dir", default="field_survey/xlsform")
    parser.add_argument("--choices-dir", default="field_survey/choices")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    forms = [
        (RESIDENT_SURVEY, "Kensington Resident Survey", "resident_survey.xlsx"),
        (BUSINESS_SURVEY, "Kensington Business Survey", "business_survey.xlsx"),
        (INTERCEPT_SURVEY, "Kensington Intercept Survey", "intercept_survey.xlsx"),
        (STUDENT_SURVEY, "UofT Student Survey", "student_survey.xlsx"),
        (CONTACT_FORM, "Follow-up Contact", "contact_followup.xlsx"),
    ]

    for fields, title, filename in forms:
        outpath = os.path.join(args.output_dir, filename)
        _write_xlsform(fields, title, outpath, args.choices_dir)
        print(f"Created {outpath} ({len(fields)} fields)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the builder**

Run:
```bash
cd C:/Users/liam1/gis-script-generator
python -m field_survey.build_xlsforms
```

Expected: 5 .xlsx files created in `field_survey/xlsform/`.

- [ ] **Step 3: Verify workbook structure manually**

Run:
```bash
python -c "
import openpyxl
for f in ['resident_survey', 'business_survey', 'intercept_survey', 'student_survey', 'contact_followup']:
    wb = openpyxl.load_workbook(f'field_survey/xlsform/{f}.xlsx')
    print(f'{f}: sheets={wb.sheetnames}, survey_rows={wb[\"survey\"].max_row}, choices_rows={wb[\"choices\"].max_row}')
"
```

Expected: Each workbook has 3 sheets (survey, choices, settings) with appropriate row counts.

- [ ] **Step 4: Write XLSForm tests**

```python
# tests/test_field_survey/test_build_xlsforms.py
import os
import pytest
import openpyxl

from field_survey.build_xlsforms import (
    RESIDENT_SURVEY,
    BUSINESS_SURVEY,
    INTERCEPT_SURVEY,
    STUDENT_SURVEY,
    CONTACT_FORM,
    INLINE_CHOICES,
    _write_xlsform,
)


def test_all_forms_have_consent_gate():
    """Every interview form must have an informed_consent field."""
    for form_name, fields in [
        ("resident", RESIDENT_SURVEY),
        ("business", BUSINESS_SURVEY),
        ("intercept", INTERCEPT_SURVEY),
        ("student", STUDENT_SURVEY),
    ]:
        consent_fields = [f for f in fields if f.get("name") == "informed_consent"]
        assert len(consent_fields) == 1, f"{form_name} missing informed_consent gate"


def test_all_forms_have_form_version():
    """Every form must have a hidden form_version field."""
    for form_name, fields in [
        ("resident", RESIDENT_SURVEY),
        ("business", BUSINESS_SURVEY),
        ("intercept", INTERCEPT_SURVEY),
        ("student", STUDENT_SURVEY),
    ]:
        version_fields = [f for f in fields if f.get("name") == "form_version"]
        assert len(version_fields) == 1, f"{form_name} missing form_version"


def test_resident_rent_skip_logic():
    """Rent questions should be hidden when tenure = own."""
    rent_fields = [f for f in RESIDENT_SURVEY if f.get("name") == "monthly_rent_range"]
    assert len(rent_fields) == 1
    assert "tenure_type" in rent_fields[0].get("relevant", "")


def test_inline_choices_cover_all_form_selects():
    """All select_one/select_multiple references must have matching choice lists."""
    all_forms = RESIDENT_SURVEY + BUSINESS_SURVEY + INTERCEPT_SURVEY + STUDENT_SURVEY + CONTACT_FORM
    external_lists = {"block_location", "business_name", "street_address"}
    for field in all_forms:
        ftype = field.get("type", "")
        for prefix in ("select_one ", "select_multiple "):
            if ftype.startswith(prefix):
                list_name = ftype[len(prefix):]
                assert list_name in INLINE_CHOICES or list_name in external_lists, \
                    f"Missing choice list: {list_name} (field: {field.get('name')})"


def test_write_xlsform_creates_valid_workbook(tmp_path):
    """XLSForm workbook has required sheets and rows."""
    outfile = str(tmp_path / "test.xlsx")
    _write_xlsform(INTERCEPT_SURVEY, "Test Survey", outfile)
    wb = openpyxl.load_workbook(outfile)
    assert "survey" in wb.sheetnames
    assert "choices" in wb.sheetnames
    assert "settings" in wb.sheetnames
    assert wb["survey"].max_row > 10  # header + fields
    assert wb["choices"].max_row > 5  # header + some choices
```

- [ ] **Step 5: Run XLSForm tests**

Run: `python -m pytest tests/test_field_survey/test_build_xlsforms.py -v`
Expected: 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add field_survey/build_xlsforms.py field_survey/xlsform/ tests/test_field_survey/test_build_xlsforms.py
git commit -m "feat(field-survey): add XLSForm builder, workbooks, and tests"
```

---

## Chunk 3: AGOL Sync Script

### Task 4: Build the AGOL → PostGIS sync script

**Files:**
- Create: `field_survey/sync_field_data.py`
- Create: `tests/test_field_survey/test_sync_field_data.py`

- [ ] **Step 1: Write the test**

```python
# tests/test_field_survey/test_sync_field_data.py
import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

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
    # globalid should not appear in the SET clause
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
    assert "ObjectID" not in result


def test_transform_feature_skips_null_geometry():
    feature = {
        "attributes": {"globalid": "abc-123"},
        "geometry": None,
    }
    result = transform_feature(feature, include_geom=True)
    assert result.get("geom") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_field_survey/test_sync_field_data.py -v`
Expected: ImportError.

- [ ] **Step 3: Write the sync script**

```python
# field_survey/sync_field_data.py
"""
Sync Survey123 and Field Maps data from ArcGIS Online to PostGIS.

Usage:
    python -m field_survey.sync_field_data \
        --agol-url https://services.arcgis.com/... \
        --db-password test123

Requires: arcgis, psycopg
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone

import psycopg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────

# Map form keys to PostGIS table names
FORM_TABLE_MAP = {
    "resident": "field_surveys.resident_responses",
    "business": "field_surveys.business_responses",
    "intercept": "field_surveys.intercept_responses",
    "student": "field_surveys.student_responses",
    "field_obs": "field_surveys.field_observations",
    "contact": "field_surveys.contact_responses",
}

# AGOL fields to skip (internal ESRI fields)
SKIP_FIELDS = {"ObjectID", "objectid", "OBJECTID", "Shape__Area", "Shape__Length",
               "CreationDate", "Creator", "EditDate", "Editor"}

# Known form versions (sync warns on unknown)
KNOWN_VERSIONS = {"1.0", "1.1", "1.2", "1.3", "1.4", "1.5"}


# ── Helpers ─────────────────────────────────────────────────────────────

def build_upsert_sql(table: str, columns: list[str]) -> str:
    """Build an INSERT ... ON CONFLICT (globalid) DO UPDATE SQL statement."""
    placeholders = ", ".join([f"%({c})s" for c in columns])
    col_list = ", ".join(columns)
    update_cols = [c for c in columns if c not in ("globalid", "id")]
    set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])

    return f"""
        INSERT INTO {table} ({col_list}, sync_timestamp)
        VALUES ({placeholders}, NOW())
        ON CONFLICT (globalid) DO UPDATE SET
            {set_clause},
            sync_timestamp = NOW()
    """


def transform_feature(feature: dict, include_geom: bool = False) -> dict:
    """Extract attributes from an AGOL feature, optionally including geometry."""
    attrs = {}
    for k, v in feature.get("attributes", {}).items():
        if k in SKIP_FIELDS:
            continue
        # Convert AGOL epoch timestamps to datetime
        if isinstance(v, int) and v > 1_000_000_000_000:
            v = datetime.fromtimestamp(v / 1000, tz=timezone.utc).isoformat()
        attrs[k.lower()] = v

    if include_geom and feature.get("geometry"):
        geom = feature["geometry"]
        x, y = geom.get("x"), geom.get("y")
        if x is not None and y is not None:
            # AGOL returns WGS84 by default; we request outSR=2952 in the query,
            # so coordinates are already in EPSG 2952 (NAD83 Ontario MTM Zone 10)
            attrs["geom"] = f"SRID=2952;POINT({x} {y})"

    return attrs


def sync_layer(conn, layer_url: str, table: str, include_geom: bool = False, token: str = None):
    """Pull all features from an AGOL feature layer and upsert into PostGIS."""
    try:
        from arcgis.features import FeatureLayer
    except ImportError:
        log.error("arcgis package not installed. Run: pip install arcgis")
        sys.exit(1)

    log.info(f"Syncing {layer_url} -> {table}")

    fl = FeatureLayer(layer_url, token=token)
    # Request EPSG 2952 so coordinates match PostGIS schema (avoids WGS84 default)
    result = fl.query(where="1=1", out_fields="*", return_geometry=include_geom, out_sr=2952)
    features = json.loads(result.to_json).get("features", [])

    if not features:
        log.warning(f"No features returned from {layer_url}")
        return 0

    # Transform all features
    rows = [transform_feature(f, include_geom) for f in features]

    # Use columns from first row
    columns = list(rows[0].keys())

    # Check form versions
    for row in rows:
        ver = row.get("form_version")
        if ver and ver not in KNOWN_VERSIONS:
            log.warning(f"Unknown form_version '{ver}' — check changelog")

    # Filter out rows where informed_consent != 'yes' (if field exists)
    if "informed_consent" in columns:
        before = len(rows)
        rows = [r for r in rows if r.get("informed_consent") == "yes"]
        skipped = before - len(rows)
        if skipped:
            log.info(f"Skipped {skipped} rows without consent")

    sql = build_upsert_sql(table, columns)

    cur = conn.cursor()
    count = 0
    for row in rows:
        try:
            cur.execute(sql, row)
            count += 1
        except Exception as e:
            log.error(f"Failed to upsert row {row.get('globalid')}: {e}")
            conn.rollback()
            continue
    conn.commit()

    log.info(f"Synced {count}/{len(rows)} features to {table}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Sync AGOL survey data to PostGIS")
    parser.add_argument("--config", help="JSON config file with AGOL layer URLs")
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--db-port", default="5432")
    parser.add_argument("--db-name", default="kensington")
    parser.add_argument("--db-user", default="postgres")
    parser.add_argument("--db-password", default=os.environ.get("PGPASSWORD", ""))
    parser.add_argument("--agol-token", default=os.environ.get("AGOL_TOKEN", ""),
                        help="AGOL access token (or set AGOL_TOKEN env var)")
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            config = json.load(f)
    else:
        log.error("Provide --config with AGOL layer URLs. Example config:")
        log.error(json.dumps({
            "layers": {
                "resident": {"url": "https://services.arcgis.com/.../0", "geom": False},
                "business": {"url": "https://services.arcgis.com/.../1", "geom": True},
                "intercept": {"url": "https://services.arcgis.com/.../2", "geom": False},
                "student": {"url": "https://services.arcgis.com/.../3", "geom": False},
                "field_obs": {"url": "https://services.arcgis.com/.../4", "geom": True},
            }
        }, indent=2))
        sys.exit(1)

    conn = psycopg.connect(
        host=args.db_host, port=args.db_port,
        dbname=args.db_name, user=args.db_user, password=args.db_password,
    )

    total = 0
    for form_key, layer_conf in config.get("layers", {}).items():
        table = FORM_TABLE_MAP.get(form_key)
        if not table:
            log.warning(f"Unknown form key '{form_key}', skipping")
            continue

        count = sync_layer(
            conn,
            layer_url=layer_conf["url"],
            table=table,
            include_geom=layer_conf.get("geom", False),
            token=args.agol_token or None,
        )
        total += count

    conn.close()
    log.info(f"Sync complete. {total} total features synced.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_field_survey/test_sync_field_data.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Create example sync config**

Create `field_survey/sync_config_example.json`:
```json
{
    "layers": {
        "resident": {
            "url": "https://services.arcgis.com/YOUR_ORG/arcgis/rest/services/Resident_Survey/FeatureServer/0",
            "geom": false
        },
        "business": {
            "url": "https://services.arcgis.com/YOUR_ORG/arcgis/rest/services/Business_Survey/FeatureServer/0",
            "geom": true
        },
        "intercept": {
            "url": "https://services.arcgis.com/YOUR_ORG/arcgis/rest/services/Intercept_Survey/FeatureServer/0",
            "geom": false
        },
        "student": {
            "url": "https://services.arcgis.com/YOUR_ORG/arcgis/rest/services/Student_Survey/FeatureServer/0",
            "geom": false
        },
        "field_obs": {
            "url": "https://services.arcgis.com/YOUR_ORG/arcgis/rest/services/Field_Maps/FeatureServer/0",
            "geom": true
        }
    }
}
```

- [ ] **Step 6: Commit**

```bash
git add field_survey/sync_field_data.py field_survey/sync_config_example.json tests/test_field_survey/test_sync_field_data.py
git commit -m "feat(field-survey): add AGOL-to-PostGIS sync script with upsert and consent filtering"
```

---

## Chunk 4: Remaining Deliverables

### Task 5: Create form changelog template

**Files:**
- Create: `field_survey/form_changelog.md`

- [ ] **Step 1: Write the changelog template**

```markdown
# Form Changelog

Track all form edits during the field week. **Every republish must be logged here.**

| Date | Time | Form | Version | Editor | Change | Reason |
|------|------|------|---------|--------|--------|--------|
| 2026-03-XX | HH:MM | Resident / Business / Intercept / Student | v1.X | Name | What changed | Why |

## Rules
- Bump `form_version` hidden field on every republish
- Safe changes (anytime): add option, add question, reword, adjust skip logic
- Dangerous changes (end-of-day only): reorder questions, change field name/type, remove question
- Notify team in group chat after every republish
```

- [ ] **Step 2: Commit**

```bash
git add field_survey/form_changelog.md
git commit -m "docs(field-survey): add form changelog template for field week"
```

---

### Task 6: AGOL coverage map setup guide

This deliverable cannot be fully automated (AGOL web map configuration is done via the portal UI), but we provide the block grid data and setup instructions.

**Files:**
- Create: `field_survey/export_block_grid.py`

- [ ] **Step 1: Write block grid exporter**

This script exports the road centerlines as a GeoJSON file that can be uploaded to AGOL as the coverage grid layer.

```python
# field_survey/export_block_grid.py
"""
Export Kensington road centerlines as GeoJSON for AGOL coverage map.

Usage:
    python -m field_survey.export_block_grid --password test123
"""
import argparse
import json
import os

import psycopg


def export_block_grid(conn, outfile: str) -> int:
    cur = conn.cursor()
    cur.execute("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'properties', json_build_object(
                        'street_name', linear_name_full,
                        'centreline_id', centreline_id,
                        'team_assignment', '',
                        'status', 'not_started'
                    ),
                    'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json
                )
            ), '[]'::json)
        )
        FROM opendata.road_centerlines
    """)
    geojson = cur.fetchone()[0]

    with open(outfile, "w") as f:
        json.dump(geojson, f, indent=2)

    feature_count = len(geojson.get("features", []))
    return feature_count


def main():
    parser = argparse.ArgumentParser(description="Export block grid as GeoJSON for AGOL")
    parser.add_argument("--output", default="field_survey/choices/block_grid.geojson")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--dbname", default="kensington")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default=os.environ.get("PGPASSWORD", ""))
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    conn = psycopg.connect(
        host=args.host, port=args.port,
        dbname=args.dbname, user=args.user, password=args.password,
    )

    count = export_block_grid(conn, args.output)
    print(f"Exported {count} road segments to {args.output}")
    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the export**

```bash
python -m field_survey.export_block_grid --password test123
```

Expected: GeoJSON file with ~162 road segments.

- [ ] **Step 3: Add AGOL setup instructions to README**

Append to README:

```markdown
## AGOL Coverage Map Setup

1. Upload `field_survey/choices/block_grid.geojson` to AGOL as a hosted feature layer
2. Create a new Web Map and add the block grid layer
3. Style blocks by `team_assignment` (color-coded: Team A = blue, Team B = green, Team C = orange)
4. Add Survey123 response layers (auto-created when forms are published)
5. Style response dots by form type
6. Share the map with all team members
7. Open in ArcGIS Field Maps alongside survey forms for real-time coverage tracking
```

- [ ] **Step 4: Commit**

```bash
git add field_survey/export_block_grid.py field_survey/README.md
git commit -m "feat(field-survey): add block grid exporter and AGOL coverage map setup guide"
```

---

## Chunk 5: README & Final Integration

### Task 7: Update field survey README

**Files:**
- Create: `field_survey/README.md`

- [ ] **Step 1: Write the README**

```markdown
# Kensington Field Survey Toolkit

Tools for the 1-week Kensington Market field study. Manages Survey123 forms,
PostGIS data sync, and analysis views.

## Quick Start

### 1. Install dependencies

```bash
pip install psycopg openpyxl arcgis
```

### 2. Set up PostGIS schema

```bash
PGPASSWORD=test123 psql -h localhost -U postgres -d kensington -f field_survey/schema.sql
```

### 3. Export choice lists for Survey123

```bash
python -m field_survey.export_choices --password test123
```

This creates CSV files in `field_survey/choices/` with business names, addresses,
and block locations from the database.

### 4. Build XLSForm workbooks

```bash
python -m field_survey.build_xlsforms
```

Creates 5 `.xlsx` files in `field_survey/xlsform/`. Upload each to Survey123
via ArcGIS Online.

### 5. Sync data from AGOL to PostGIS

After collecting data in the field:

```bash
python -m field_survey.sync_field_data \
    --config field_survey/sync_config.json \
    --db-password test123 \
    --agol-token YOUR_TOKEN
```

Edit `sync_config.json` (copy from `sync_config_example.json`) with your
actual AGOL feature layer URLs.

## Forms

| Form | File | Target | Duration |
|------|------|--------|----------|
| Resident Survey | `resident_survey.xlsx` | Kensington residents | 10-15 min |
| Business Survey | `business_survey.xlsx` | Shop/restaurant owners | 8-12 min |
| Street Intercept | `intercept_survey.xlsx` | Visitors/passersby | 3-4 min |
| Student Survey | `student_survey.xlsx` | UofT students (campus) | 4-5 min |
| Follow-up Contact | `contact_followup.xlsx` | Decoupled contact info | 1 min |

## Editing forms in the field

1. Open Survey123 Web Designer on AGOL
2. Make your change (see spec for safe vs. dangerous changes)
3. Bump the `form_version` hidden field
4. Republish
5. Tell team to close and reopen the app
6. Log the change in the shared changelog

## PostGIS schema

- **Raw tables**: `field_surveys.{resident,business,intercept,student}_responses`, `field_surveys.field_observations`
- **Views**: `field_surveys.v_resident_by_block`, `v_business_linked`, `v_intercept_by_block`, `v_student_perception`, `v_field_vs_database`
```

- [ ] **Step 2: Commit**

```bash
git add field_survey/README.md
git commit -m "docs(field-survey): add README with quick start and form reference"
```

---

### Task 8: End-to-end integration test

- [ ] **Step 1: Apply PostGIS schema**

Run:
```bash
cd C:/Users/liam1/gis-script-generator
python -c "
import psycopg
conn = psycopg.connect(host='localhost', port=5432, dbname='kensington', user='postgres', password='test123')
with open('field_survey/schema.sql') as f:
    conn.execute(f.read())
conn.commit()
print('Schema applied successfully')
conn.close()
"
```

- [ ] **Step 2: Export choices and verify**

Run:
```bash
python -m field_survey.export_choices --password test123
```

Verify:
```bash
wc -l field_survey/choices/*.csv
```

Expected: ~450+ lines in business_names.csv, ~1072+ in addresses.csv, 50+ in block_locations.csv.

- [ ] **Step 3: Build XLSForms and verify**

Run:
```bash
python -m field_survey.build_xlsforms
ls -la field_survey/xlsform/
```

Expected: 5 .xlsx files, each 10-30 KB.

- [ ] **Step 4: Run all tests**

Run:
```bash
python -m pytest tests/test_field_survey/ -v
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
git add -A field_survey/ tests/test_field_survey/
git commit -m "feat(field-survey): complete field survey toolkit — forms, sync, schema, choices"
```

---

## Summary

| Task | What | Spec Deliverable | Files |
|------|------|-----------------|-------|
| 1 | PostGIS schema (6 tables + 5 views) | #5 | `field_survey/schema.sql` |
| 2 | Choice list export script | #6 | `field_survey/export_choices.py`, tests |
| 3 | XLSForm workbook generator | #1, #2 | `field_survey/build_xlsforms.py`, 5 xlsx, tests |
| 4 | AGOL → PostGIS sync script | #4 | `field_survey/sync_field_data.py`, tests, config |
| 5 | Form changelog template | #7 | `field_survey/form_changelog.md` |
| 6 | AGOL coverage map setup | #3 | `field_survey/export_block_grid.py`, README instructions |
| 7 | README | — | `field_survey/README.md` |
| 8 | End-to-end integration | — | Verify everything works together |

**After implementation**: Upload the 5 XLSForm workbooks to Survey123 via AGOL, upload the block grid GeoJSON, configure the coverage map, and share with your team.
