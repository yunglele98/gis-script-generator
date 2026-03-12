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
        ROUND(AVG(fear_of_displacement)::numeric, 2) AS avg_fear_of_displacement,
        ROUND(AVG(neighbourhood_satisfaction)::numeric, 2) AS avg_neighbourhood_satisfaction,
        ROUND(AVG(perceived_safety_day)::numeric, 2) AS avg_safety_day,
        ROUND(AVG(perceived_safety_night)::numeric, 2) AS avg_safety_night,
        ROUND(AVG(community_belonging)::numeric, 2) AS avg_community_belonging,
        ROUND(AVG(access_grocery)::numeric, 2) AS avg_access_grocery,
        ROUND(AVG(access_healthcare)::numeric, 2) AS avg_access_healthcare,
        ROUND(AVG(access_transit)::numeric, 2) AS avg_access_transit,
        ROUND(AVG(access_greenspace)::numeric, 2) AS avg_access_greenspace,
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
        ROUND(AVG(displacement_pressure::numeric)::numeric, 2) AS avg_displacement_pressure,
        ROUND(AVG(gentrification_index)::numeric, 2) AS avg_gentrification_index,
        ROUND(AVG(livability_index)::numeric, 2) AS avg_livability_index,
        ROUND(AVG(ba_condition_rating)::numeric, 2) AS avg_condition_rating,
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
    -- Block-level crime/collision stats
    crime.crime_count,
    crime.dominant_offence,
    ksi.ksi_count,
    ksi.pedestrian_ksi_count
FROM (
    SELECT
        block_location,
        COUNT(*) AS response_count,
        ROUND(AVG(overall_impression)::numeric, 2) AS avg_impression,
        ROUND(AVG(perceived_safety)::numeric, 2) AS avg_safety,
        ROUND(AVG(cleanliness)::numeric, 2) AS avg_cleanliness,
        ROUND(AVG(accessibility)::numeric, 2) AS avg_accessibility,
        ROUND(AVG(vibrancy)::numeric, 2) AS avg_vibrancy,
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
    ROUND(AVG(s.overall_impression)::numeric, 2) AS avg_impression,
    ROUND(AVG(s.perceived_safety)::numeric, 2) AS avg_safety,
    ROUND(AVG(s.sense_of_community)::numeric, 2) AS avg_community,
    ROUND(AVG(s.authenticity)::numeric, 2) AS avg_authenticity,
    ROUND(AVG(s.affordability_perception)::numeric, 2) AS avg_affordability,
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
