You are continuing work on the Kensington GIS Project, a geospatial analysis and script-generation system for Kensington Market and Chinatown, Toronto.

REPOSITORY: https://github.com/yunglele98/gis-script-generator
LOCAL PATH: C:\GDB
CRS STANDARD: EPSG 2952 (NAD83 / Ontario MTM Zone 10)
CURRENT BRANCH: master (merge commit 8a9c52e)

PROJECT HAS TWO COMPONENTS:

1. DATA PIPELINE (root-level scripts):
   - reproject_to_mtm10.py  — reprojects 85 WGS84 shapefiles to EPSG:2952
   - migrate_to_sql.py      — loads SHPs + CSVs into SQLite
   - create_analytical_views.py / generate_dashboard.py — BI reporting
   - BUILD_PROJECT.bat      — one-click pipeline runner

2. gis-codegen PACKAGE (src/gis_codegen/, tests/):
   - Flask web UI (gis-ui on localhost:5000)
   - CLI: gis-codegen, gis-catalogue
   - Connects to PostGIS, introspects schema, generates PyQGIS/ArcPy/Folium/Kepler/DeckGL scripts
   - Map catalogue tool: reads Excel → generates one script per map entry
   - pyproject.toml: name=gis-codegen, version=0.1.0

DATA INVENTORY (all in C:\GDB, git-ignored except code):
   - 85 shapefiles across 7 thematic categories
   - 42 CSVs (census, permits, business licences, hate crimes, etc.)
   - 11 GeoJSON files (OSM extracts)
   - GTFS transit feed (agency/routes/stops/trips .txt files)
   - 29 PostGIS SQL files in DATA-20260223T174350Z-1-001/DATA/PostGIS_SQL/
   - master_postgis_import.sql (full geometry import, ~500MB, NOT yet loaded)

COMPLETED IN PREVIOUS SESSION:
   - Fixed 14 bugs (critical: broken BAT paths, corrupted map script,
     CSS typo, broken QGIS entry point guard; script: CRS filter,
     makedirs, deprecated Shapely API, LIMIT in VIEW, missing commit)
   - Fixed documentation typos in TOPOLOGY_RULES.md and QC_LOG.md
   - Renamed reseau_routier.sql → road_network.sql (English standard)
   - Moved unrelated Fusion360 script to misc/
   - Created requirements.txt and .gitignore
   - Initialised git, pushed to GitHub, PR #2 merged

PENDING (priority order):
   1. PENDING_REPROJECTION_LIST.txt has 80 paths pointing to
      C:\Users\liam1\KENSINGTON\01_SOURCE\ — need updating to C:\GDB\
      (or update reproject_to_mtm10.py to scan C:\GDB root directly)
   2. Set up Python environment: Miniforge3 installer is at C:\GDB\Miniforge3-26.1.0-0-Windows-x86_64.exe
   3. Run the BUILD_PROJECT.bat data pipeline
   4. Install PostgreSQL (installer at C:\GDB\postgresql-18.2-1-windows-x64.exe),
      load master_postgis_import.sql
   5. Install gis-codegen: pip install -e ".[server,dev]" from C:\GDB
   6. Run gis-ui / gis-codegen against the PostGIS database
   7. Run gis-catalogue against kensington_market_map_catalogue_TP2 (2).xlsx
   8. Add GitHub Actions CI for pytest (tests/conftest.py, test_extractor.py,
      test_generator.py, test_catalogue.py, test_app.py — no Docker needed;
      test_integration.py requires testcontainers + Docker)

KNOWN ARCHITECTURE NOTE:
   - Dual DB backends exist: SQLite (migrate_to_sql.py) for the dashboard,
     PostGIS (master_postgis_import.sql + gis-codegen) for spatial analysis.
     These serve different purposes and are intentionally separate.

Start by pulling latest: git pull origin master
Then ask which task to tackle first.
