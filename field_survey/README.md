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

Creates CSV files in `field_survey/choices/` with business names, addresses,
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
2. Make your change (see `form_changelog.md` for safe vs. dangerous changes)
3. Bump the `form_version` hidden field
4. Republish
5. Tell team to close and reopen the app
6. Log the change in `form_changelog.md`

## PostGIS schema

**Raw tables** (`field_surveys` schema):
- `resident_responses`, `business_responses`, `intercept_responses`
- `student_responses`, `field_observations`, `contact_responses`

**Analysis views:**
- `v_resident_by_block` — aggregated resident data + building assessment stats
- `v_business_linked` — business responses joined to building assessment, licences, dinesafe, cafeto patios
- `v_intercept_by_block` — aggregated intercept data + crime/collision stats
- `v_student_perception` — student perception averages, comparable to intercept
- `v_field_vs_database` — Field Maps observations matched to nearest building assessment record

## AGOL Coverage Map Setup

1. Upload `field_survey/choices/block_grid.geojson` to AGOL as a hosted feature layer
2. Create a new Web Map and add the block grid layer
3. Style blocks by `team_assignment` (color-coded: Team A = blue, Team B = green, Team C = orange)
4. Add Survey123 response layers (auto-created when forms are published)
5. Style response dots by form type
6. Share the map with all team members
7. Open in ArcGIS Field Maps alongside survey forms for real-time coverage tracking
