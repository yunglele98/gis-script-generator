# Kensington Market Field Survey — Design Specification

**Date**: 2026-03-12
**Status**: Approved
**Duration**: 1-week on-site field study
**Location**: Kensington Market / Chinatown, Toronto + UofT St. George campus
**Team**: 6 people (3 teams of 2)
**Database**: PostGIS `kensington` on localhost:5432

---

## 1. Architecture Overview

Two ESRI apps working together, syncing to PostGIS via a Python script.

```
┌─────────────────────────────────────────────────────────┐
│                    FIELD WORK (6 people)                 │
│                                                         │
│   ┌──────────────┐         ┌──────────────────┐        │
│   │  Field Maps   │         │   Survey123       │        │
│   │  (observe)    │◄───────►│   (interview)     │        │
│   │              │  linked  │                   │        │
│   │ • Ground-truth│  by     │ • Resident survey │        │
│   │ • Gap-fill    │  location│ • Business survey │        │
│   │ • Photos      │         │ • Intercept survey│        │
│   └──────┬───────┘         │ • Student survey  │        │
│          │                  └────────┬──────────┘        │
└──────────┼──────────────────────────┼────────────────────┘
           │         offline sync     │
           ▼                          ▼
    ┌──────────────────────────────────────┐
    │         ArcGIS Online (AGOL)         │
    │   Feature layers + survey responses  │
    │   Team coverage dashboard            │
    └──────────────────┬───────────────────┘
                       │  Python: sync_field_data.py
                       │  (on-demand or nightly)
                       ▼
    ┌──────────────────────────────────────┐
    │     PostGIS: field_surveys schema    │
    │   Raw tables + analysis views        │
    │   Joins to existing tables (3 schemas)│
    └──────────────────────────────────────┘
```

### Key requirements
- Offline-capable (both apps)
- Real-time form editing via Survey123 Web Designer
- ArcGIS institutional licence (UofT)
- Free/low-cost otherwise

### Scope boundary: Field Maps
The Field Maps project (ground-truthing, gap-filling, observational data) is **pre-existing** and already configured by the user. This spec covers only the Survey123 interview forms and the data pipeline to sync both systems into PostGIS. Field Maps form design is out of scope.

---

## 2. Confidentiality Standards

Applied across all four survey forms.

| Rule | Implementation |
|------|---------------|
| No exact GPS on person-linked surveys | Block-level location only (select from list) |
| No address capture in resident/intercept/student forms | Block or campus location select |
| No photos linked to respondents | Building photos in Field Maps only |
| Household size as ranges | 1 / 2-3 / 4-5 / 6+ |
| Consent gate on every form | `informed_consent` = Yes required to proceed |
| Follow-up contact decoupled | Separate unlinked form + random code card |
| Surveyor ID internal-only | Excluded from any published dataset |

**Exception — Business Survey**: Businesses are public-facing entities. Business name and street address are captured. Owner/staff/customer names are never recorded. Consent text: "Your business may be identified in results. No personal names will be published."

---

## 3. Form Designs

### 3.1 Form 1: Resident Survey

**Target**: People who live in Kensington Market / Chinatown
**Duration**: ~10-15 minutes
**Trigger**: Door-to-door or approached on their street
**Confidentiality**: Block-level, fully anonymous

| Section | Field | Type | Notes |
|---------|-------|------|-------|
| **Metadata** | `surveyor_id` | select | Internal QA only |
| | `timestamp` | datetime | Auto |
| | `block_location` | select | Pre-populated Kensington block list |
| | `informed_consent` | select | Yes / No — **gate** |
| **Demographics** | `age_range` | select | 18-24 / 25-34 / 35-44 / 45-54 / 55-64 / 65+ |
| | `gender` | select | Man / Woman / Non-binary / Prefer not to say |
| | `household_size_range` | select | 1 / 2-3 / 4-5 / 6+ |
| | `years_in_neighbourhood` | select | <1 / 1-3 / 3-5 / 5-10 / 10-20 / 20+ |
| | `primary_language` | text | Open text |
| **Housing** | `tenure_type` | select | Rent / Own / Social housing / Other |
| | `unit_type` | select | House / Apartment / Rooming house / Above-shop / Other |
| | `monthly_rent_range` | select | <$800 / $800-1200 / $1200-1600 / $1600-2000 / $2000+ / N/A |
| | `rent_increase_last_year` | select | Yes / No / Don't know |
| | `rent_increase_pct` | select | <2% / 2-5% / 5-10% / >10% / Don't know — *visible if rent_increase = Yes* |
| | `fear_of_displacement` | likert 1-5 | Not at all worried → Extremely worried |
| | `received_eviction_notice` | select | Yes / No / Prefer not to say |
| **Neighbourhood** | `neighbourhood_satisfaction` | likert 1-5 | |
| | `biggest_concern` | select_multiple | Affordability / Safety / Noise / Cleanliness / Traffic / Development / Loss of character / Other |
| | `biggest_asset` | select_multiple | Community / Diversity / Walkability / Food / Markets / Culture / Greenspace / Affordability / Other |
| | `perceived_safety_day` | likert 1-5 | |
| | `perceived_safety_night` | likert 1-5 | |
| | `noticed_changes_3yr` | select | Major changes / Some changes / No change / New to area |
| | `change_description` | text | *Visible if noticed_changes != No change* |
| | `change_sentiment` | select | Positive / Negative / Mixed / Neutral — *visible if noticed_changes != No change* |
| **Services** | `access_grocery` | likert 1-5 | Very difficult → Very easy |
| | `access_healthcare` | likert 1-5 | |
| | `access_transit` | likert 1-5 | |
| | `access_greenspace` | likert 1-5 | |
| | `missing_services` | text | "What service/amenity is missing?" |
| **Gentrification** | `aware_of_development` | select | Yes / No |
| | `development_impact` | select | Positive / Negative / Mixed / No opinion — *visible if Yes* |
| | `business_closures_noticed` | select | Yes / No |
| | `closure_names` | text | *Visible if closures = Yes* |
| | `community_belonging` | likert 1-5 | Not at all → Very strongly |
| **Close** | `consent_followup` | select | Yes / No |
| | `additional_comments` | text | |

**Skip logic**: Rent questions hidden if tenure = Own. Change description hidden if no changes noticed. Follow-up redirects to separate unlinked contact form.

### 3.2 Form 2: Business Owner Survey

**Target**: Shop owners, restaurant operators, market vendors
**Duration**: ~8-12 minutes
**Trigger**: Walk-in during business hours
**Confidentiality**: Business identifiable, no personal names

| Section | Field | Type | Notes |
|---------|-------|------|-------|
| **Metadata** | `surveyor_id` | select | Internal only |
| | `timestamp` | datetime | Auto |
| | `business_name` | searchable select | Pre-populated from `business_licences` + `building_assessment`, with "Other" fallback |
| | `street_address` | searchable select | Pre-populated from `building_assessment.ADDRESS_FULL`, auto-fills from business_name |
| | `gps_location` | geopoint | Exact — business location is public |
| | `informed_consent` | select | "Business may be identified, no personal names published" — gate |
| **Business Profile** | `business_type` | select | Restaurant / Cafe / Retail / Market vendor / Service / Bar / Grocery / Other |
| | `years_operating` | select | <1 / 1-3 / 3-5 / 5-10 / 10-20 / 20+ |
| | `ownership_type` | select | Owner-operated / Franchise / Family business / Partnership / Other |
| | `num_employees_range` | select | 1-2 / 3-5 / 6-10 / 11-20 / 20+ |
| | `is_original_business` | select | Yes (founded here) / No (relocated here) |
| **Rent & Economics** | `lease_type` | select | Month-to-month / Short-term (<3yr) / Long-term (3yr+) / Own the building / Prefer not to say |
| | `monthly_rent_range` | select | <$2K / $2-4K / $4-6K / $6-10K / $10K+ / Prefer not to say |
| | `rent_change_3yr` | select | Increased a lot / Increased somewhat / Stable / Decreased / New lease / Prefer not to say |
| | `revenue_trend_3yr` | select | Growing / Stable / Declining / Prefer not to say |
| | `financial_viability` | likert 1-5 | At risk of closing → Very secure |
| **Neighbourhood Change** | `customer_base_change` | select | More tourists / More students / More locals / No change / Mixed |
| | `foot_traffic_trend` | select | Increasing / Stable / Decreasing / Seasonal |
| | `competition_change` | select | More competition / Less / Same / Different type |
| | `nearby_closures_noticed` | select | Yes / No |
| | `closure_count_estimate` | select | 1-2 / 3-5 / 5+ — *visible if Yes* |
| | `gentrification_impact` | likert 1-5 | Very negative → Very positive |
| | `biggest_threat` | select_multiple | Rising rent / Changing clientele / Competition / Development / Parking / Crime / Regulation / None / Other |
| | `biggest_opportunity` | select_multiple | Tourism / New residents / Events / Online presence / Community support / Other |
| **Operations** | `patio_program` | select | Yes / No / Applied but denied / Not applicable |
| | `accessibility_rating` | likert 1-5 | Not accessible → Fully accessible |
| | `delivery_apps` | select | Yes / No |
| | `heritage_building` | select | Yes / No / Don't know |
| **Community** | `belongs_to_bia` | select | Yes / No / Don't know |
| | `community_involvement` | select_multiple | BIA / Market events / Neighbourhood association / None / Other |
| | `neighbourhood_satisfaction` | likert 1-5 | |
| | `plans_next_3yr` | select | Stay / Expand / Downsize / Relocate / Close / Uncertain |
| **Close** | `additional_comments` | text | |
| | `consent_followup` | select | Yes / No — if Yes, surveyor records business name + contact method in a separate note (business is already identifiable by name/address, so the unlinked random-code system is not needed here) |

**Dropdown sources**: `business_name` populated from `business_licences.business_name` UNION `building_assessment.BUSINESS_NAME`. `street_address` populated from `building_assessment.ADDRESS_FULL`.

**DB joins**: Direct match on `ADDRESS_FULL` to `building_assessment`, `business_licences`, `cafeto_patios`, `dinesafe`.

### 3.3 Form 3: Street Intercept Survey

**Target**: Pedestrians, shoppers, visitors in Kensington
**Duration**: ~3-4 minutes
**Trigger**: Approach in public areas
**Confidentiality**: Block-level, fully anonymous

| Section | Field | Type | Notes |
|---------|-------|------|-------|
| **Metadata** | `surveyor_id` | select | Internal only |
| | `timestamp` | datetime | Auto |
| | `block_location` | select | Kensington block list |
| | `informed_consent` | select | Yes / No — gate |
| **Who** | `age_range` | select | 18-24 / 25-34 / 35-44 / 45-54 / 55-64 / 65+ |
| | `connection_to_area` | select | Live here / Work here / Visiting / Shopping / Passing through / Student nearby (note: UofT students intercepted IN Kensington get this form, not Form 4; Form 4 is campus-only) |
| | `visit_frequency` | select | Daily / Few times a week / Weekly / Monthly / First time / Rarely |
| **Experience** | `reason_for_visit` | select_multiple | Food / Shopping / Restaurant-bar / Work / Live here / Exploring / Meeting someone / Other |
| | `how_arrived` | select | Walk / Bike / TTC / Car / Rideshare |
| | `time_spent_today` | select | <30min / 30min-1hr / 1-2hrs / 2-4hrs / 4hrs+ |
| | `money_spent_today` | select | $0 / <$20 / $20-50 / $50-100 / $100+ |
| **Perception** | `overall_impression` | likert 1-5 | Very negative → Very positive |
| | `perceived_safety` | likert 1-5 | |
| | `cleanliness` | likert 1-5 | |
| | `accessibility` | likert 1-5 | |
| | `vibrancy` | likert 1-5 | Dead → Very lively |
| **Change** | `noticed_changes` | select | Yes / No / Don't visit enough to know |
| | `change_sentiment` | select | Better / Worse / Mixed / Neutral — *visible if Yes* |
| | `one_word_kensington` | text | "One word to describe Kensington" |
| **Close** | `would_recommend` | select | Yes / No / Maybe |
| | `what_would_improve` | select_multiple | Cleanliness / Safety / More seating / Public washrooms / Less traffic / More greenery / Nothing / Other |

**15 taps + 1 word.** Under 4 minutes.

### 3.4 Form 4: Student Survey (UofT Campus)

**Target**: UofT students on St. George campus
**Duration**: ~4-5 minutes
**Trigger**: Approach near common areas
**Confidentiality**: Campus-level location, fully anonymous

| Section | Field | Type | Notes |
|---------|-------|------|-------|
| **Metadata** | `surveyor_id` | select | Internal only |
| | `timestamp` | datetime | Auto |
| | `campus_location` | select | Robarts / Sidney Smith / Hart House / Spadina & College / Spadina & Dundas / Other |
| | `informed_consent` | select | Yes / No — gate |
| **Profile** | `age_range` | select | 18-21 / 22-25 / 26-30 / 30+ (note: student-specific bins; not directly comparable to intercept/resident age ranges — cross-analysis should use broad buckets like under-25 / 25+) |
| | `student_status` | select | Undergrad / Graduate / Post-doc / Staff |
| | `faculty` | select | Arts & Sci / Engineering / Architecture / Planning / Social Work / Other |
| | `lives_in_kensington_area` | select | Yes / No / Used to |
| | `housing_type` | select | On-campus / Rent nearby / Rent elsewhere / With family / Other |
| | `monthly_rent_range` | select | <$800 / $800-1200 / $1200-1600 / $1600-2000 / $2000+ / N/A |
| **Kensington Relationship** | `visit_frequency` | select | Daily / Few times a week / Weekly / Monthly / Rarely / Never |
| | `reason_for_visit` | select_multiple | Food / Bars / Shopping / Vintage stores / Exploring / Friends live there / Live there / Never visit |
| | `how_arrived` | select | Walk / Bike / TTC / Car / Other |
| | `money_spent_typical` | select | $0 / <$20 / $20-50 / $50-100 / $100+ |
| **Perception** | `overall_impression` | likert 1-5 | |
| | `perceived_safety` | likert 1-5 | |
| | `sense_of_community` | likert 1-5 | No community feel → Strong community |
| | `authenticity` | likert 1-5 | Feels commercialized → Feels authentic |
| | `affordability_perception` | likert 1-5 | Too expensive → Very affordable |
| **Housing & Gentrification** | `would_live_in_kensington` | select | Yes / Already do / No / Used to |
| | `barrier_to_living_there` | select_multiple | Rent too high / Safety / Too far / Noise / Housing quality / No barrier / Other — *visible if No* |
| | `aware_of_gentrification` | select | Yes / Somewhat / No |
| | `gentrification_opinion` | select | Positive / Negative / Mixed / No opinion |
| | `student_housing_impact` | select | Students drive up rents / Students are also priced out / No impact / Don't know |
| **Close** | `one_word_kensington` | text | Comparable to intercept form |
| | `what_would_improve` | select_multiple | Affordability / Safety / Cleanliness / More student spaces / Better transit / Nothing / Other |

### 3.5 Follow-up Contact Form (Separate, Unlinked)

**Purpose**: Decouples identity from survey responses for confidentiality.

| Field | Type | Notes |
|-------|------|-------|
| `random_code` | text | Surveyor enters the code from the card given to respondent |
| `name` | text | Optional |
| `contact_method` | select | Email / Phone / Either |
| `contact_info` | text | |
| `preferred_language` | select | English / French / Mandarin / Cantonese / Portuguese / Spanish / Other |

No GPS. No link to any survey response. The random code exists only so the respondent can withdraw consent later by quoting their code.

---

## 4. Team Structure

Three teams of 2, all with access to both Field Maps and Survey123.

| Team | Primary Focus | Zone |
|------|--------------|------|
| **Team A** | Field Maps (ground-truth) + Resident interviews (Form 1) + Intercepts (Form 3) | Kensington blocks |
| **Team B** | Field Maps (ground-truth) + Business interviews (Form 2) + Intercepts (Form 3) | Kensington blocks |
| **Team C** | Student surveys (Form 4) | UofT St. George campus |

- Teams A and B split Kensington geographically — coverage grid on AGOL tracks progress
- Team C can rotate into Kensington when student survey targets are met
- All teams can log Field Maps observations opportunistically

---

## 5. Data Pipeline: AGOL → PostGIS

### Sync script: `sync_field_data.py`

1. Authenticates to AGOL via `arcgis` Python API (institutional credentials)
2. Pulls each Survey123 feature layer as GeoJSON
3. Pulls Field Maps feature layer
4. Upserts into `field_surveys` schema raw tables (idempotent)
5. Stamps each row with `form_version` and `sync_timestamp`
6. Refreshes analysis views

### PostGIS schema: `field_surveys`

**Raw tables** (1:1 mirror of AGOL):
- `resident_responses`
- `business_responses`
- `intercept_responses`
- `student_responses`
- `field_observations`

**Analysis views**:
- `v_resident_by_block` — aggregates resident responses to block level, joins to `building_assessment` block-level stats
- `v_business_linked` — direct join by address to `building_assessment`, `business_licences`, `cafeto_patios`, `dinesafe`
- `v_intercept_by_block` — aggregates intercept responses, joins to `major_crime_indicators`, `ksi_collisions`, vacancy rates
- `v_student_perception` — standalone, columns comparable to intercept for cross-analysis
- `v_field_vs_database` — compares Field Maps observations against existing database records

### Join strategies

| Survey | Join method | Target tables |
|--------|------------|---------------|
| Resident | Block-level spatial join (anonymized) | `building_assessment` aggregated per block |
| Business | Direct address + name match | `building_assessment`, `business_licences`, `cafeto_patios`, `dinesafe` |
| Intercept | Block-level spatial join | `major_crime_indicators`, `ksi_collisions` |
| Student | No spatial join to Kensington | Standalone — cross-compare with intercept |
| Field Maps | Direct address or nearest-feature join | Any table, depends on observation type |

---

## 6. Real-time Form Editing Workflow

### Safe changes (anytime during field week):
- Add a select option to a dropdown
- Add a new question at end of a section
- Reword a question label
- Adjust skip logic conditions
- Add a new section

### Dangerous changes (end-of-day only, team agreement):
- Reorder questions
- Change a field name (requires sync script update)
- Remove a question
- Change field type

### Process:
1. Team member flags issue in group chat
2. Designated editor (1-2 people with AGOL edit access) makes change in Survey123 Web Designer
3. Republishes form (~30 seconds)
4. Notifies team in group chat: "Close and reopen Survey123 to get update"
5. Bumps hidden `form_version` field
6. Logs change in shared changelog (date, what, why)

### Version tracking:
- Hidden `form_version` field in every form, incremented on each republish
- **Responsibility**: The designated form editor (1-2 people) is responsible for bumping the version and logging the change. The sync script warns if it encounters an unknown version not listed in the changelog.
- Sync script preserves version in PostGIS
- Allows filtering analysis by form version if a question changed meaning mid-week

---

## 7. Dropdown Data Sources

Pre-populated from PostGIS for the business survey:

### `business_name` dropdown
```sql
SELECT DISTINCT business_name FROM online_data.business_licences
UNION
SELECT DISTINCT "BUSINESS_NAME" FROM public.building_assessment
WHERE "BUSINESS_NAME" IS NOT NULL
ORDER BY 1;
```

### `street_address` dropdown
```sql
SELECT DISTINCT "ADDRESS_FULL" FROM public.building_assessment
ORDER BY 1;
```

### `block_location` dropdown (for anonymous forms)
Generated from `opendata.road_centerlines` intersected with the study area boundary. Each entry is a street segment label: "Street Name (From Cross St to Cross St)".

```sql
-- Approximate query: generates block labels from road centerlines within study area
SELECT DISTINCT
    linear_name_full || ' (' ||
    COALESCE(from_street, 'start') || ' to ' ||
    COALESCE(to_street, 'end') || ')' AS block_label
FROM (
    SELECT
        r.linear_name_full,
        r.centreline_id,
        -- Cross streets derived from intersection IDs joined back to centerlines
        f.linear_name_full AS from_street,
        t.linear_name_full AS to_street
    FROM opendata.road_centerlines r
    LEFT JOIN opendata.road_centerlines f ON r.from_intersection_id = f.to_intersection_id
        AND f.linear_name_full != r.linear_name_full
    LEFT JOIN opendata.road_centerlines t ON r.to_intersection_id = t.from_intersection_id
        AND t.linear_name_full != r.linear_name_full
    WHERE ST_Intersects(r.geom, (SELECT geometry FROM opendata.study_area LIMIT 1))
) sub
ORDER BY 1;
```

**Expected count**: ~20-40 block segments (Kensington is a small neighbourhood). This is a manageable dropdown size. The exact query may need tuning at implementation time based on actual cross-street data quality.

### Dropdown pipeline: PostGIS → Survey123

All dropdown data is exported as CSV choice lists and embedded in the XLSForm:

1. Run SQL queries above against PostGIS
2. Export results as CSV files: `choices_business_name.csv`, `choices_address.csv`, `choices_block.csv`
3. Import into the XLSForm `choices` sheet (or paste into Survey123 Web Designer)
4. Republish forms

Deliverable 6 ("Dropdown data exports") includes a Python script that automates steps 1-2. Step 3 is manual in Survey123 Web Designer or done via XLSForm editing.

---

## 8. Analysis Questions This Enables

| Question | Data sources |
|----------|-------------|
| Do residents on high-displacement-pressure blocks actually report fear of displacement? | `v_resident_by_block` + `building_assessment.displacement_pressure` |
| Are DB-flagged vacancy signals accurate? | `v_business_linked` + `building_assessment.VACANCY_SIGNALS` |
| Do students perceive Kensington as affordable vs. visitors on-site? | `v_student_perception` vs `v_intercept_by_block` |
| Do street trees the DB says exist still exist? What condition? | `field_observations` vs `opendata.street_trees` |
| Does perceived safety correlate with actual crime data? | Intercept + resident `perceived_safety` vs `major_crime_indicators` |
| Do business owners confirm the gentrification pressure indices? | `v_business_linked.gentrification_impact` vs `building_assessment.gentrification_index` |
| What services do residents say are missing vs. what the DB shows exists? | `resident_responses.missing_services` vs POIs, health services, childcare |

---

## 9. Deliverables (Implementation)

1. **4 Survey123 forms** (XLSForm or Web Designer)
2. **Follow-up contact form** (separate, unlinked)
3. **AGOL coverage map** with block grid, team assignments, response dots
4. **`sync_field_data.py`** — Python script to pull AGOL → PostGIS
5. **PostGIS schema migration** — `field_surveys` schema with raw tables + analysis views
6. **Dropdown data exports** — CSV/JSON for Survey123 choice lists
7. **Form changelog template** — shared doc for tracking edits

---

## 10. Prerequisites & Out-of-Scope Items

These items are **not designed in this spec** but must be addressed before or during field work:

| Item | Status | Notes |
|------|--------|-------|
| **Research Ethics Board (REB) approval** | Must be confirmed before any human-subject interviews | UofT REB required for student surveys; may also apply to resident/business surveys depending on whether this is academic research |
| **Sampling strategy & target sample sizes** | Separate planning item | Define target N per form, sampling method (convenience vs. systematic), and minimum thresholds for statistical validity |
| **Field Maps form design** | Pre-existing | Already built by user; out of scope for this spec |
| **Sync script error handling** | Implementation detail | Covered during plan/build phase — includes duplicate detection, consent filtering, network failure recovery, schema mismatch handling |
| **Multi-language support** | To be determined | Kensington has significant Chinese and Portuguese-speaking populations; forms may need translation for resident surveys |
