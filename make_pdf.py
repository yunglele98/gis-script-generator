#!/usr/bin/env python3
"""
make_pdf.py  --  Generate the GIS Script Generator user-guide PDF.

Usage:
    pip install fpdf2
    python make_pdf.py
    -> GIS_Script_Generator_User_Guide.pdf
"""

from fpdf import FPDF
from datetime import date

OUTPUT = "GIS_Script_Generator_User_Guide.pdf"

# ---------------------------------------------------------------------------
# Replace characters outside cp1252 so built-in fonts don't choke
# ---------------------------------------------------------------------------

def s(text: str) -> str:
    """Sanitise to cp1252-safe characters."""
    return (
        text
        .replace("\u2192", "->")
        .replace("\u2014", "--")
        .replace("\u2013", "-")
        .replace("\u2018", "'").replace("\u2019", "'")
        .replace("\u201c", '"').replace("\u201d", '"')
        .replace("\u2022", "-")
        .replace("\u00b0", "deg")
        .replace("\u00ab", "<<").replace("\u00bb", ">>")
    )


# ---------------------------------------------------------------------------
# PDF class
# ---------------------------------------------------------------------------

class GuidePDF(FPDF):
    M = 20          # left/right margin
    CW = 170        # usable column width on A4 (210 - 2*20)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(self.CW // 2, 7, s("GIS Script Generator -- User Guide"), ln=0, align="L")
        self.cell(self.CW // 2, 7, f"Page {self.page_no()}", ln=1, align="R")
        self.set_text_color(0, 0, 0)
        self.set_draw_color(180, 180, 180)
        self.line(self.M, self.get_y(), 210 - self.M, self.get_y())
        self.ln(2)

    def footer(self):
        self.set_y(-13)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 6, s(f"Generated {date.today()}  |  gis-codegen v0.1.0"), align="C")
        self.set_text_color(0, 0, 0)

    # ---- layout helpers ------------------------------------------------

    def chapter(self, num, title):
        self.add_page()
        self.set_fill_color(30, 80, 160)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, s(f"  {num}.  {title}"), ln=1, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(4)

    def section(self, title):
        self.ln(3)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(30, 80, 160)
        self.cell(0, 7, s(title), ln=1)
        self.set_text_color(0, 0, 0)
        self.set_draw_color(30, 80, 160)
        self.line(self.M, self.get_y(), 210 - self.M, self.get_y())
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(0, 5, s(text))
        self.ln(1)

    def bullets(self, items):
        self.set_font("Helvetica", "", 10)
        for item in items:
            x = self.get_x()
            self.set_x(self.M + 4)
            self.cell(5, 5, s("-"))
            self.multi_cell(self.CW - 9, 5, s(item))
        self.ln(1)

    def code(self, text, caption=""):
        if caption:
            self.set_font("Helvetica", "BI", 8)
            self.set_text_color(80, 80, 80)
            self.cell(0, 5, s(caption), ln=1)
            self.set_text_color(0, 0, 0)
        self.set_font("Courier", "", 7.5)
        self.set_fill_color(245, 246, 248)
        self.set_draw_color(200, 200, 200)
        self.multi_cell(0, 4, s(text), fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def note(self, text):
        self.set_font("Helvetica", "I", 9)
        self.set_fill_color(255, 251, 224)
        self.set_draw_color(210, 170, 0)
        self.multi_cell(0, 5, s("  NOTE:  " + text), fill=True, border=1)
        self.set_draw_color(0, 0, 0)
        self.ln(2)

    def th(self, cols, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(210, 225, 250)
        for col, w in zip(cols, widths):
            self.cell(w, 6, s(col), border=1, fill=True)
        self.ln()

    def tr(self, cols, widths, shade=False):
        self.set_font("Helvetica", "", 9)
        if shade:
            self.set_fill_color(248, 251, 255)
        for col, w in zip(cols, widths):
            self.cell(w, 6, s(str(col)), border=1, fill=shade)
        self.ln()


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------

def cover(pdf: GuidePDF):
    pdf.add_page()
    pdf.set_fill_color(30, 80, 160)
    pdf.rect(0, 45, 210, 60, "F")
    # Reset position explicitly after rect() (it moves the cursor to x=0)
    pdf.set_xy(pdf.M, 55)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 26)
    pdf.multi_cell(pdf.CW, 13, "GIS Script Generator\nUser Guide", align="C")
    pdf.set_x(pdf.M)
    pdf.set_font("Helvetica", "", 13)
    pdf.multi_cell(pdf.CW, 7, "PyQGIS  |  ArcPy  |  Folium  |  Kepler.gl  |  pydeck\nCatalogue-driven script generation from PostGIS", align="C")
    pdf.set_y(115)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(pdf.M)
    pdf.cell(pdf.CW, 7, f"Version 0.1.0   |   {date.today()}", ln=1, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.M)
    pdf.multi_cell(pdf.CW, 5,
        "This guide covers all seven template types generated by gis-codegen and\n"
        "gis-catalogue, the full operations reference, the symbology dispatch table,\n"
        "and complete CLI documentation.", align="C")


def sec_overview(pdf: GuidePDF):
    pdf.chapter(1, "Project Overview")
    pdf.body(
        "gis-codegen is a command-line tool that connects to a PostGIS database, "
        "extracts spatial layer metadata (geometry type, SRID, columns, primary keys, "
        "row counts), and generates ready-to-run Python scripts for five GIS platforms.\n\n"
        "gis-catalogue reads a map catalogue Excel file and writes one script per map "
        "entry, auto-selecting the correct renderer based on the symbology_type column."
    )

    pdf.section("Template types")
    pdf.th(["CLI command", "Template type", "Output"], [70, 55, 45])
    rows = [
        ("gis-codegen --platform pyqgis",  "PyQGIS standalone",      "any_name.py"),
        ("gis-codegen --platform arcpy",   "ArcPy (ArcGIS Pro)",     "any_name.py"),
        ("gis-codegen --platform folium",  "Folium / Leaflet HTML",  "any_name.py"),
        ("gis-codegen --platform kepler",  "Kepler.gl HTML",         "any_name.py"),
        ("gis-codegen --platform deck",    "pydeck / deck.gl HTML",  "any_name.py"),
        ("gis-catalogue --platform pyqgis","Catalogue PyQGIS (x N)", "M##_name.py"),
        ("gis-catalogue --platform arcpy", "Catalogue ArcPy  (x N)", "M##_name.py"),
    ]
    for i, r in enumerate(rows):
        pdf.tr(r, [70, 55, 45], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("Package layout")
    pdf.code(
        "src/gis_codegen/\n"
        "    __init__.py     Public API: connect, extract_schema, generate_*\n"
        "    extractor.py    PostGIS metadata queries\n"
        "    generator.py    Code generation (PyQGIS, ArcPy, Folium, Kepler, pydeck)\n"
        "    catalogue.py    Excel-driven per-map code generation\n"
        "    cli.py          gis-codegen CLI\n"
        "tests/\n"
        "    conftest.py     Shared fixtures\n"
        "    test_generator.py   test_catalogue.py   test_extractor.py\n"
        "maps/               Generated output (git-ignored)\n"
        "make_pdf.py         This PDF generator"
    )


def sec_install(pdf: GuidePDF):
    pdf.chapter(2, "Installation & Setup")

    pdf.section("Install")
    pdf.code(
        "# From the project root:\n"
        "pip install -e .\n\n"
        "# With web mapping extras (folium, kepler, pydeck):\n"
        'pip install -e ".[web]"\n\n'
        "# With dev tools (pytest, coverage, openpyxl):\n"
        'pip install -e ".[dev]"\n\n'
        "# Entry points after install:\n"
        "gis-codegen   --help\n"
        "gis-catalogue --help"
    )

    pdf.section("Required environment variable")
    pdf.body(
        "PGPASSWORD must always be set before running any command. "
        "It is never stored in config files or embedded in generated scripts."
    )
    pdf.code(
        "# Windows\n"
        "set PGPASSWORD=your_password\n\n"
        "# Linux / macOS\n"
        "export PGPASSWORD=your_password"
    )

    pdf.section("Optional environment variables")
    pdf.th(["Variable", "Default", "Description"], [45, 40, 85])
    ev = [
        ("PGHOST",     "localhost",   "Database host"),
        ("PGPORT",     "5432",        "Database port"),
        ("PGDATABASE", "my_gis_db",   "Database name"),
        ("PGUSER",     "postgres",    "Database user"),
        ("PGPASSWORD", "(required)",  "Database password -- no default"),
    ]
    for i, r in enumerate(ev):
        pdf.tr(r, [45, 40, 85], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("Config file  (gis_codegen.toml)")
    pdf.body("Place in the project root, or pass with --config. CLI flags override it.")
    pdf.code(
        "[database]\n"
        'host   = "localhost"\n'
        "port   = 5432\n"
        'dbname = "my_gis_db"\n'
        'user   = "postgres"\n'
        "# password NOT stored here -- use PGPASSWORD env var\n\n"
        "[defaults]\n"
        'platform      = "pyqgis"\n'
        'schema_filter = "public"\n'
        "no_row_counts = false\n"
        'output        = "output.py"\n'
        'save_schema   = "schema.json"'
    )


def sec_extraction(pdf: GuidePDF):
    pdf.chapter(3, "Schema Extraction")

    pdf.body(
        "The extractor queries geometry_columns, information_schema.columns, "
        "information_schema.table_constraints, and pg_class to build a full "
        "metadata snapshot of all spatial layers in the database."
    )

    pdf.section("Preview layers (no files written)")
    pdf.code("gis-codegen --list-layers\n\n"
             "# Example output:\n"
             "#  schema  table    geom_type        srid   rows\n"
             "#  ------  -----    ---------        ----   ----\n"
             "#  public  parcels  MULTIPOLYGON     4326   ~1 000\n"
             "#  public  roads    MULTILINESTRING  4326   ~500")

    pdf.section("Save schema JSON for offline use")
    pdf.code("gis-codegen --save-schema schema.json\n"
             "# Then generate without a live DB connection:\n"
             "gis-codegen --platform pyqgis -i schema.json -o my_map.py")

    pdf.section("Schema JSON structure")
    pdf.code(
        '{\n'
        '  "database": "my_gis_db",\n'
        '  "host": "localhost",\n'
        '  "layer_count": 1,\n'
        '  "layers": [\n'
        '    {\n'
        '      "schema": "public",\n'
        '      "table": "parcels",\n'
        '      "qualified_name": "public.parcels",\n'
        '      "geometry": {"column":"geom","type":"MULTIPOLYGON","srid":4326},\n'
        '      "columns": [\n'
        '        {"name":"parcel_id","data_type":"integer","nullable":false},\n'
        '        {"name":"address",  "data_type":"character varying","nullable":true}\n'
        '      ],\n'
        '      "primary_keys": ["parcel_id"],\n'
        '      "row_count_estimate": 1000\n'
        '    }\n'
        '  ]\n'
        '}'
    )


def sec_pyqgis(pdf: GuidePDF):
    pdf.chapter(4, "PyQGIS Template")

    pdf.body(
        "PyQGIS scripts connect to PostGIS via QgsDataSourceUri and load layers "
        "into a QGIS project. They can run as standalone scripts (outside QGIS) "
        "or be pasted into the QGIS Python console."
    )

    pdf.section("Generate")
    pdf.code(
        "# From a live database:\n"
        "gis-codegen --platform pyqgis -o my_map.py\n\n"
        "# From a saved schema:\n"
        "gis-codegen --platform pyqgis -i schema.json -o my_map.py\n\n"
        "# Filter to one layer:\n"
        "gis-codegen --platform pyqgis --layer public.parcels -o parcels.py\n\n"
        "# Add operation blocks:\n"
        "gis-codegen --platform pyqgis --op buffer --op dissolve -o parcels.py"
    )

    pdf.section("Template anatomy")
    pdf.code(
        '"""\n'
        "Auto-generated PyQGIS script\n"
        "Database : my_gis_db @ localhost:5432\n"
        "Generated: 2026-02-23 14:00   Layers: 2\n"
        '"""\n'
        "\n"
        "import os, sys\n"
        "from qgis.core import (\n"
        "    QgsApplication, QgsDataSourceUri, QgsVectorLayer, QgsProject,\n"
        "    QgsCoordinateReferenceSystem,\n"
        ")\n"
        "\n"
        "# Remove the next 2 lines if running inside the QGIS console:\n"
        "qgs = QgsApplication([], False)\n"
        "qgs.initQgis()\n"
        "\n"
        "from qgis import processing   # injected only when ops need it\n"
        "\n"
        'DB_HOST = "localhost"\n'
        'DB_PORT = "5432"\n'
        'DB_NAME = "my_gis_db"\n'
        'DB_USER = "postgres"\n'
        'DB_PASSWORD = "..."         # value at generation time\n'
        "\n"
        "# ================================================================\n"
        "# Layer : public.parcels   Geom: MULTIPOLYGON   SRID: 4326\n"
        "# Fields: parcel_id (int), address (str), height (float)\n"
        "# ================================================================\n"
        "uri_parcels = QgsDataSourceUri()\n"
        "uri_parcels.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)\n"
        'uri_parcels.setDataSource("public", "parcels", "geom", "", "parcel_id")\n'
        "\n"
        'lyr_parcels = QgsVectorLayer(uri_parcels.uri(False), "parcels", "postgres")\n'
        "\n"
        "if not lyr_parcels.isValid():\n"
        '    print("[ERROR] Layer \'parcels\' failed to load.")\n'
        "else:\n"
        "    QgsProject.instance().addMapLayer(lyr_parcels)\n"
        "    print(f\"[OK] parcels: {lyr_parcels.featureCount()} features\")\n"
        "    # ... sample loop, op blocks, spatial/attribute filter stubs ...\n"
        "\n"
        "qgs.exitQgis()   # remove if running inside QGIS console"
    )

    pdf.section("How to run")
    pdf.bullets([
        "Standalone:  set PGPASSWORD=...  then  python my_map.py",
        "             (requires the QGIS Python environment on PATH)",
        "QGIS console: paste the script body; remove QgsApplication init/exit lines",
        "QGIS Processing Toolbox: Plugins -> Python Console -> Open Script",
    ])
    pdf.note(
        "The generated script embeds the password value that was in db_config "
        "at generation time. If the password changes, update DB_PASSWORD in "
        "the script or set os.environ['PGPASSWORD'] and change the line to read from it."
    )


def sec_arcpy(pdf: GuidePDF):
    pdf.chapter(5, "ArcPy Template")

    pdf.body(
        "ArcPy scripts create a temporary .sde connection file, access PostGIS "
        "feature classes through that connection, and optionally run analysis "
        "tools. They require ArcGIS Pro with the PostgreSQL client libraries installed."
    )

    pdf.section("Generate")
    pdf.code(
        "gis-codegen --platform arcpy -o my_map.py\n\n"
        "# With 3D massing ops:\n"
        "gis-codegen --platform arcpy --op extrude --op scene_layer -o massing.py"
    )

    pdf.section("Template anatomy")
    pdf.code(
        "import arcpy, os, tempfile\n"
        "\n"
        'DB_HOST = "localhost"\n'
        'DB_PORT = "5432"\n'
        'DB_NAME = "my_gis_db"\n'
        'DB_USER = "postgres"\n'
        'DB_PASSWORD = "..."\n'
        "\n"
        "# --- SDE connection file (created once, reused on subsequent runs) ---\n"
        "SDE_FOLDER = tempfile.gettempdir()\n"
        'SDE_FILE   = os.path.join(SDE_FOLDER, f"{DB_NAME}.sde")\n'
        "if not os.path.exists(SDE_FILE):\n"
        "    arcpy.management.CreateDatabaseConnection(\n"
        '        database_platform="POSTGRESQL",\n'
        '        instance=f"{DB_HOST},{DB_PORT}",\n'
        '        account_authentication="DATABASE_AUTH",\n'
        "        username=DB_USER, password=DB_PASSWORD,\n"
        '        save_user_pass="SAVE_USERNAME", database=DB_NAME, ...\n'
        "    )\n"
        "\n"
        "# ================================================================\n"
        "# Layer : public.parcels\n"
        "# ================================================================\n"
        'fc_parcels = os.path.join(SDE_FILE, "public.parcels")\n'
        "if arcpy.Exists(fc_parcels):\n"
        "    desc  = arcpy.Describe(fc_parcels)\n"
        "    count = int(arcpy.management.GetCount(fc_parcels)[0])\n"
        "    print(f\"[OK] parcels: {count} rows  | {desc.shapeType}\")\n"
        "    # ... SearchCursor sample, op blocks ...\n"
        "else:\n"
        '    print("[ERROR] Layer not found in SDE connection.")'
    )

    pdf.section("How to run")
    pdf.bullets([
        "ArcGIS Pro Python console: paste and run directly",
        "Standalone: run from the ArcGIS Pro Python env  (arcgispro-py3)",
        "Script Tool: add as a Python Script Tool in a Toolbox (.atbx)",
    ])
    pdf.note(
        "The SDE file persists between runs. Delete it manually if you change "
        "the host, database name, or credentials."
    )


def sec_web(pdf: GuidePDF):
    pdf.chapter(6, "Web Mapping Templates")

    pdf.body(
        "Web templates read PostGIS via geopandas + SQLAlchemy and produce a "
        "standalone HTML file. Install extras first:  pip install -e \".[web]\""
    )
    pdf.note(
        "All web templates use  DB_PASSWORD = os.environ[\"PGPASSWORD\"]  -- "
        "the password is NEVER embedded in generated scripts."
    )

    pdf.section("Folium / Leaflet  (--platform folium)")
    pdf.code(
        "gis-codegen --platform folium -o map.py\n"
        "python map.py        # -> map.html"
    )
    pdf.body(
        "Produces a Leaflet map with GeoJson layers and tooltips from the first "
        "5 columns per layer. Polygons, lines, and points each get a distinct "
        "colour from a 6-colour cycling palette. A LayerControl widget is added "
        "automatically. All geometries are reprojected to EPSG:4326."
    )

    pdf.section("Kepler.gl  (--platform kepler)")
    pdf.code(
        "gis-codegen --platform kepler -o kepler_map.py\n"
        "python kepler_map.py     # -> kepler_map.html\n"
        "                         # (or render inline in Jupyter)"
    )
    pdf.body(
        "Loads all layers into a KeplerGl map object. If a height column is "
        "detected (height, floors, elevation, z, roof_height, ...) a 3D tip "
        "comment is added. Enable it in the Kepler UI: Layers -> type -> "
        "3D buildings, height field = detected column."
    )

    pdf.section("pydeck / deck.gl  (--platform deck)")
    pdf.code(
        "gis-codegen --platform deck -o deck_map.py\n"
        "python deck_map.py   # -> deck_map.html"
    )
    pdf.body(
        "Polygon/line layers use GeoJsonLayer; point layers use ScatterplotLayer. "
        "When a height column is detected, commented extrusion lines are added -- "
        "uncomment extruded=True and set pitch=45 for a 3D view."
    )

    pdf.section("Colour palette (shared by Folium and pydeck)")
    pdf.th(["Layer index", "Hex colour", "RGBA"], [35, 40, 95])
    colours = [
        ("0 (first)",  "#ff8c00", "[255, 140,   0, 160]  orange"),
        ("1",          "#0080ff", "[  0, 128, 255, 160]  blue"),
        ("2",          "#00c864", "[  0, 200, 100, 160]  green"),
        ("3",          "#ff3232", "[255,  50,  50, 160]  red"),
        ("4",          "#b400ff", "[180,   0, 255, 160]  purple"),
        ("5+",         "#00c8c8", "[  0, 200, 200, 160]  teal (cycles)"),
    ]
    for i, r in enumerate(colours):
        pdf.tr(r, [35, 40, 95], shade=(i % 2 == 0))


def sec_ops(pdf: GuidePDF):
    pdf.chapter(7, "Operations Reference  (--op flag)")

    pdf.body(
        "Operations inject additional code blocks into PyQGIS or ArcPy scripts. "
        "Repeat --op for multiple operations in one script:"
    )
    pdf.code(
        "gis-codegen --platform pyqgis --op buffer --op dissolve -o out.py\n"
        "gis-codegen --platform arcpy  --op extrude --op scene_layer -o 3d.py"
    )
    pdf.note("Operations are not supported on web platforms (folium, kepler, deck).")

    pdf.section("General operations  (10)")
    pdf.th(["--op value", "PyQGIS", "ArcPy"], [28, 72, 70])
    gen_ops = [
        ("reproject",    "processing: native:reprojectlayer",     "management.Project"),
        ("export",       "QgsVectorFileWriter -> GeoJSON",        "conversion.FeatureClassToShapefile"),
        ("buffer",       "processing: native:buffer",             "analysis.Buffer"),
        ("clip",         "processing: native:clip (commented)",   "analysis.Clip (commented)"),
        ("select",       "selectByExpression",                    "SelectLayerByAttribute"),
        ("dissolve",     "processing: native:dissolve",           "management.Dissolve"),
        ("centroid",     "processing: native:centroids",          "management.FeatureToPoint"),
        ("field_calc",   "processing: native:fieldcalculator",    "management.CalculateField"),
        ("spatial_join", "joinattributesbylocation (commented)",  "analysis.SpatialJoin (commented)"),
        ("intersect",    "native:intersection (commented)",       "analysis.Intersect (commented)"),
    ]
    for i, r in enumerate(gen_ops):
        pdf.tr(r, [28, 72, 70], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.body(
        "Operations marked (commented) produce a ready-to-uncomment template that "
        "requires you to define an input boundary or overlay layer first."
    )
    pdf.body(
        "Processing operations (reproject, buffer, dissolve, centroid, field_calc) "
        "also inject  'from qgis import processing'  at the top of PyQGIS scripts."
    )

    pdf.section("3D massing operations  (5)")
    pdf.th(["--op value", "Description", "Notes"], [28, 80, 62])
    ops_3d = [
        ("extrude",
         "Data-driven height extrusion renderer",
         "PyQGIS: QgsPolygon3DSymbol\nArcPy: ddd.ExtrudePolygon"),
        ("z_stats",
         "Min / max / mean Z vertex statistics",
         "PyQGIS: hasZ + vertex loop\nArcPy: ddd.AddZInformation"),
        ("floor_ceiling",
         "Extrude from base_height to roof_height field",
         "Two-field floor-to-roof extrusion"),
        ("volume",
         "Approx. volume = footprint area x height",
         "Fast estimate; exact: ST_Volume() in PostGIS"),
        ("scene_layer",
         "Export 3D layer package",
         "PyQGIS: native:convert3dtiles\nArcPy: CreateSceneLayerPackage (.slpk)"),
    ]
    for i, r in enumerate(ops_3d):
        pdf.tr(r, [28, 80, 62], shade=(i % 2 == 0))


def sec_catalogue(pdf: GuidePDF):
    pdf.chapter(8, "Catalogue-Driven Generation")

    pdf.body(
        "gis-catalogue reads a map catalogue Excel file and writes one script per "
        "map entry. Only rows where status is 'have' or 'partial' AND "
        "spatial_layer_type contains 'Vector' are included."
    )

    pdf.section("Inclusion rules")
    pdf.th(["status", "spatial_layer_type", "Included?"], [30, 55, 85])
    rules = [
        ("have",    "Vector",        "YES"),
        ("partial", "Vector",        "YES"),
        ("have",    "Raster/Vector", "YES (+ raster TODO note)"),
        ("todo",    "Vector",        "NO  -- skipped"),
        ("have",    "Raster",        "NO  -- skipped"),
        ("todo",    "Raster",        "NO  -- skipped"),
    ]
    for i, r in enumerate(rules):
        pdf.tr(r, [30, 55, 85], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("Key catalogue columns")
    pdf.th(["Column", "Role in generated script"], [45, 125])
    cols = [
        ("map_id",            "Section header comment and layout name  (e.g. M07_layout)"),
        ("short_name",        "Python variable names and PostGIS table name (public.short_name)"),
        ("spatial_layer_type","Triggers raster TODO note when 'Raster' is in the value"),
        ("symbology_type",    "Drives automatic renderer selection (see Section 9)"),
        ("validation_checks", "Written as  # [ ] item  checklist"),
        ("deliverable_format","Written into the export stub comment"),
        ("classification",    "Passed to categorized renderer block as scheme comment"),
    ]
    for i, r in enumerate(cols):
        pdf.tr(r, [45, 125], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("CLI usage")
    pdf.code(
        "# Generate PyQGIS scripts (default):\n"
        "gis-catalogue --input catalogue.xlsx --output-dir ./maps/\n\n"
        "# Generate ArcPy scripts:\n"
        "gis-catalogue --input catalogue.xlsx --platform arcpy --output-dir ./maps_arcpy/\n\n"
        "# Preview what would be generated (no files written):\n"
        "gis-catalogue --input catalogue.xlsx --list\n\n"
        "# Override DB connection:\n"
        "gis-catalogue --input catalogue.xlsx --host myserver --dbname prod_db"
    )

    pdf.section("Output naming")
    pdf.code(
        "# One file per included map:\n"
        "maps/\n"
        "    M03_occupation_sol_2026.py\n"
        "    M07_hauteurs_etages_degrade.py\n"
        "    M27_commerces_typologie_concentrations.py\n"
        "    M35_tc_lignes_arrets.py\n"
        "    ...\n\n"
        "maps_arcpy/\n"
        "    M03_occupation_sol_2026.py   # ArcPy version\n"
        "    M07_hauteurs_etages_degrade.py\n"
        "    ..."
    )


def sec_symbology(pdf: GuidePDF):
    pdf.chapter(9, "Symbology Dispatch Table")

    pdf.body(
        "The symbology_type cell in the catalogue drives automatic renderer "
        "selection. Matching is case-insensitive on the full cell value. "
        "The first matching rule wins."
    )

    pdf.th(
        ["Keyword(s) in symbology_type", "PyQGIS renderer", "ArcPy renderer"],
        [65, 58, 47]
    )
    dispatch = [
        ("heatmap  OR  densit\xe9",
         "QgsHeatmapRenderer",
         "HeatMapRenderer (Pro 3.x)"),
        ("r\xe9seau  OR  network",
         "QgsCategorizedSymbolRenderer\n(QgsLineSymbol per value)",
         "UniqueValueRenderer\n(NET_FIELD placeholder)"),
        ("cat\xe9goriel / cat\xe9gorie\n(without choroplèthe)",
         "QgsCategorizedSymbolRenderer",
         "UniqueValueRenderer"),
        ("choroplèthe + cat\xe9goriel",
         "QgsCategorizedSymbolRenderer",
         "UniqueValueRenderer"),
        ("choroplèthe / d\xe9grad\xe9 / gradu\xe9",
         "QgsGraduatedSymbolRenderer",
         "GraduatedColorsRenderer"),
        ("points  OR  polygones",
         "QgsSingleSymbolRenderer",
         "SimpleRenderer"),
        ("(anything else)",
         "# TODO: configure renderer",
         "# TODO: configure renderer"),
    ]
    for i, r in enumerate(dispatch):
        pdf.tr(r, [65, 58, 47], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.note(
        "All renderer blocks use a TODO comment to mark the field name "
        "(GRAD_FIELD, CAT_FIELD, NET_FIELD) that you must verify against "
        "the actual PostGIS table schema."
    )


def sec_cat_pyqgis(pdf: GuidePDF):
    pdf.chapter(10, "Catalogue PyQGIS Template Anatomy")

    pdf.body(
        "Each file generated by  gis-catalogue --platform pyqgis  has six sections:"
    )

    pdf.section("1  Docstring header  (16 fields)")
    pdf.code(
        '"""\n'
        "Map ID    : M07\n"
        "Title     : Hauteurs / nombre d'etages (degrade)\n"
        "Theme     : Forme urbaine > Gabarits\n"
        "Objective : Representer gabarits et gradient de hauteur\n"
        "Questions : Ou sont les hauteurs fortes/faibles?\n"
        "Indicators: # etages, distribution\n"
        "Scale     : Quartier  |  Unit: batiment\n"
        "Symbology : choroplethe (degrade)\n"
        "Sources   : OSM building:levels  [2024-2026]\n"
        "Processing: nettoyer niveaux + recoder classes\n"
        "Deliverable: Layout PDF + couche\n"
        "Validation: valeurs nulles, plausibilite niveaux, palette lisible\n"
        "Risks     : OSM incomplet; niveaux estimes\n"
        "Status    : have  |  Owner: Liam\n"
        "Generated : 2026-02-23 14:48\n"
        '"""'
    )

    pdf.section("2  QGIS imports & init")
    pdf.code(
        "import os\n"
        "from qgis.core import (\n"
        "    QgsApplication, QgsDataSourceUri, QgsVectorLayer, QgsProject,\n"
        ")\n"
        "qgs = QgsApplication([], False)\n"
        "qgs.initQgis()"
    )

    pdf.section("3  DB credentials")
    pdf.code(
        'DB_HOST = "localhost"\n'
        'DB_PORT = "5432"\n'
        'DB_NAME = "my_gis_db"\n'
        'DB_USER = "postgres"\n'
        'DB_PASSWORD = os.environ["PGPASSWORD"]   # never hardcoded'
    )

    pdf.section("4  Layer load block")
    pdf.code(
        "uri_hauteurs_etages_degrade = QgsDataSourceUri()\n"
        "uri_hauteurs_etages_degrade.setConnection(\n"
        "    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)\n"
        'uri_hauteurs_etages_degrade.setDataSource(\n'
        '    "public", "hauteurs_etages_degrade", "geom", "", "")\n'
        "\n"
        "lyr_hauteurs_etages_degrade = QgsVectorLayer(\n"
        '    uri_hauteurs_etages_degrade.uri(False), "hauteurs_etages_degrade", "postgres")\n'
        "\n"
        "if not lyr_hauteurs_etages_degrade.isValid():\n"
        "    print(\"[ERROR] 'hauteurs_etages_degrade' failed to load.\")\n"
        "else:\n"
        "    QgsProject.instance().addMapLayer(lyr_hauteurs_etages_degrade)\n"
        '    print(f"[OK] {lyr_hauteurs_etages_degrade.featureCount()} features")'
    )

    pdf.section("5  Auto-dispatched symbology block")
    pdf.code(
        "    # --- Symbology: choroplethe (degrade) ---\n"
        "    from qgis.core import (\n"
        "        QgsGraduatedSymbolRenderer, QgsClassificationQuantile,\n"
        "        QgsColorBrewerColorRamp,\n"
        "    )\n"
        '    GRAD_FIELD_... = "value"   # TODO: verify field name\n'
        "    _rend = QgsGraduatedSymbolRenderer(GRAD_FIELD_...)\n"
        "    _rend.setClassificationMethod(QgsClassificationQuantile())\n"
        "    _rend.updateClasses(lyr_..., 5)\n"
        '    _rend.updateColorRamp(QgsColorBrewerColorRamp("YlOrRd", 5))\n'
        "    lyr_....setRenderer(_rend)\n"
        "    lyr_....triggerRepaint()"
    )

    pdf.section("6  Validation checklist & export stub")
    pdf.code(
        "    # --- Validation checks ---\n"
        "    # [ ] valeurs nulles\n"
        "    # [ ] plausibilite niveaux\n"
        "    # [ ] palette lisible\n"
        "\n"
        '    # --- Export: Layout PDF + couche ---\n'
        '    # TODO: configure a QGIS print layout named "M07_layout" then:\n'
        "    # from qgis.core import QgsLayoutExporter\n"
        "    # layout   = QgsProject.instance().layoutManager()\n"
        '    #            .layoutByName("M07_layout")\n'
        "    # exporter = QgsLayoutExporter(layout)\n"
        '    # exporter.exportToPdf("M07_hauteurs_etages_degrade.pdf",\n'
        "    #     QgsLayoutExporter.PdfExportSettings())\n"
        "\n"
        "qgs.exitQgis()"
    )


def sec_cat_arcpy(pdf: GuidePDF):
    pdf.chapter(11, "Catalogue ArcPy Template Anatomy")

    pdf.body(
        "Each file generated by  gis-catalogue --platform arcpy  has the same "
        "six sections as the PyQGIS version but uses ArcPy idioms throughout."
    )

    pdf.section("1-3  Docstring, imports & credentials")
    pdf.code(
        "# Docstring header identical to PyQGIS version.\n\n"
        "import arcpy\n"
        "import os\n"
        "import tempfile\n\n"
        'DB_HOST = "localhost"\n'
        'DB_PORT = "5432"\n'
        'DB_NAME = "my_gis_db"\n'
        'DB_USER = "postgres"\n'
        'DB_PASSWORD = os.environ["PGPASSWORD"]'
    )

    pdf.section("4  SDE connection file")
    pdf.code(
        "SDE_FOLDER = tempfile.gettempdir()\n"
        'SDE_FILE   = os.path.join(SDE_FOLDER, f"{DB_NAME}.sde")\n'
        "\n"
        "if not os.path.exists(SDE_FILE):\n"
        "    arcpy.management.CreateDatabaseConnection(\n"
        '        database_platform="POSTGRESQL",\n'
        '        instance=f"{DB_HOST},{DB_PORT}",\n'
        '        account_authentication="DATABASE_AUTH",\n'
        "        username=DB_USER, password=DB_PASSWORD,\n"
        '        save_user_pass="SAVE_USERNAME", database=DB_NAME, ...\n'
        "    )"
    )

    pdf.section("5  Feature class check, describe, and project setup")
    pdf.code(
        'fc_hauteurs_etages_degrade = os.path.join(SDE_FILE, "public.hauteurs_etages_degrade")\n'
        "\n"
        "if not arcpy.Exists(fc_hauteurs_etages_degrade):\n"
        "    print(\"[ERROR] 'hauteurs_etages_degrade' not found.\")\n"
        "else:\n"
        "    desc  = arcpy.Describe(fc_hauteurs_etages_degrade)\n"
        "    count = int(arcpy.management.GetCount(fc_hauteurs_etages_degrade)[0])\n"
        '    print(f"[OK] {count} rows | {desc.shapeType}")\n'
        "\n"
        "    # --- Add to ArcGIS Pro project ---\n"
        '    APRX_PATH = "CURRENT"   # TODO: or r"C:\\path\\to\\project.aprx"\n'
        "    aprx   = arcpy.mp.ArcGISProject(APRX_PATH)\n"
        "    mp_map = aprx.listMaps()[0]\n"
        "    lyr_hauteurs_etages_degrade = mp_map.addDataFromPath(fc_hauteurs_etages_degrade)"
    )

    pdf.section("6  Auto-dispatched ArcPy symbology block")
    pdf.code(
        "    # --- Symbology: choroplethe (degrade) ---\n"
        '    GRAD_FIELD_... = "value"   # TODO: verify field name\n'
        "    sym = lyr_....symbology\n"
        '    sym.updateRenderer("GraduatedColorsRenderer")\n'
        "    sym.renderer.classificationField = GRAD_FIELD_...\n"
        "    sym.renderer.breakCount = 5\n"
        '    # TODO: sym.renderer.colorRamp = aprx.listColorRamps("Oranges (5 Classes)")[0]\n'
        "    lyr_....symbology = sym\n"
        "    aprx.save()"
    )

    pdf.section("7  Validation checklist & export stub")
    pdf.code(
        "    # --- Validation checks ---\n"
        "    # [ ] valeurs nulles\n"
        "    # [ ] plausibilite niveaux\n"
        "    # [ ] palette lisible\n"
        "\n"
        "    # --- Export: Layout PDF + couche ---\n"
        '    # TODO: configure a layout named "M07_layout" in your .aprx, then:\n'
        '    # layout = aprx.listLayouts("M07_layout")[0]\n'
        '    # layout.exportToPDF("M07_hauteurs_etages_degrade.pdf")'
    )
    pdf.note(
        "Use APRX_PATH = \"CURRENT\" when running inside the ArcGIS Pro console. "
        "For standalone scripts, set APRX_PATH to the path of your .aprx file. "
        "HeatMapRenderer requires ArcGIS Pro 3.x."
    )


def sec_cli(pdf: GuidePDF):
    pdf.chapter(12, "CLI Quick Reference")

    pdf.section("gis-codegen  --  all flags")
    pdf.code(
        "gis-codegen [connection] [generation] [schema]\n\n"
        "Connection flags (override config file and env vars):\n"
        "  --host HOST         Database host\n"
        "  --port PORT         Database port\n"
        "  --dbname DBNAME     Database name\n"
        "  --user USER         Database user\n"
        "  --config FILE       TOML config file path\n\n"
        "Generation flags:\n"
        "  --platform          pyqgis | arcpy | folium | kepler | deck\n"
        "  --op OPERATION      Add an operation block (repeatable)\n"
        "                      See Section 7 for all 15 valid values\n"
        "  --layer SCHEMA.TABLE  Restrict to this layer (repeatable)\n"
        "  -o / --output FILE  Write to file (default: stdout)\n\n"
        "Schema flags:\n"
        "  --list-layers       Print layer table and exit\n"
        "  --save-schema FILE  Save schema JSON and exit\n"
        "  --no-row-counts     Skip row count queries (faster)\n"
        "  --schema-filter S   Only include layers in schema S\n\n"
        "Priority: CLI flags > config file > env vars > built-in defaults"
    )

    pdf.section("gis-catalogue  --  all flags")
    pdf.code(
        "gis-catalogue [options]\n\n"
        "Required:\n"
        "  -i / --input FILE        Path to catalogue .xlsx file\n\n"
        "Optional:\n"
        "  -o / --output-dir DIR    Output directory  (default: ./maps/)\n"
        "  -p / --platform          pyqgis | arcpy    (default: pyqgis)\n"
        "  --host HOST              (default: localhost / PGHOST)\n"
        "  --port PORT              (default: 5432 / PGPORT)\n"
        "  --dbname DBNAME          (default: my_gis_db / PGDATABASE)\n"
        "  --user USER              (default: postgres / PGUSER)\n"
        "  --list                   Print filtered maps and exit (no files written)\n\n"
        "Filter applied automatically:\n"
        '  status IN {"have","partial"}  AND  "Vector" IN spatial_layer_type'
    )

    pdf.section("End-to-end workflow examples")
    pdf.code(
        "# 1. Preview what is in the database:\n"
        "set PGPASSWORD=secret\n"
        "gis-codegen --list-layers\n\n"
        "# 2. Save the schema for offline generation:\n"
        "gis-codegen --save-schema schema.json\n\n"
        "# 3. Generate a PyQGIS script with buffer + dissolve:\n"
        "gis-codegen --platform pyqgis --op buffer --op dissolve -o analysis.py\n\n"
        "# 4. Generate all catalogue maps as PyQGIS scripts:\n"
        "gis-catalogue --input catalogue.xlsx --output-dir ./maps/\n\n"
        "# 5. Generate all catalogue maps as ArcPy scripts:\n"
        "gis-catalogue --input catalogue.xlsx --platform arcpy --output-dir ./maps_arcpy/\n\n"
        "# 6. Generate a Kepler.gl web map:\n"
        "gis-codegen --platform kepler -o kepler_map.py\n"
        "python kepler_map.py"
    )


def sec_testing(pdf: GuidePDF):
    pdf.chapter(13, "Testing")

    pdf.section("Run the test suite")
    pdf.code(
        "# Install dev dependencies:\n"
        'pip install -e ".[dev]"\n\n'
        "# Run all tests:\n"
        "python -m pytest tests/ -v\n\n"
        "# With coverage report:\n"
        "python -m pytest tests/ --cov=gis_codegen --cov-report=term-missing\n\n"
        "# Run one file:\n"
        "python -m pytest tests/test_generator.py -v\n\n"
        "# Filter by keyword:\n"
        'python -m pytest tests/ -k "arcpy" -v'
    )

    pdf.section("Test suite summary")
    pdf.th(["File", "Tests", "What is covered"], [52, 18, 100])
    suite = [
        ("test_generator.py", "124",
         "safe_var, pg_type_to_*, _guess_height_field, 15 op blocks x 2 platforms, "
         "5 generators (pyqgis arcpy folium kepler deck)"),
        ("test_catalogue.py", "108",
         "load_catalogue filtering, 5 PyQGIS + 5 ArcPy renderer blocks, "
         "symbology dispatch x 2 platforms, generate_map_pyqgis, generate_map_arcpy"),
        ("test_extractor.py",  "34",
         "DB_CONFIG env var reading, fetch_columns, fetch_primary_keys, "
         "fetch_row_count_estimate, extract_schema (mocked connection)"),
        ("TOTAL",             "265", ""),
    ]
    for i, r in enumerate(suite):
        pdf.tr(r, [52, 18, 100], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.body(
        "All 265 tests run in under 1 second because the generators are pure "
        "string-building functions -- no database connection or GIS library "
        "is needed to run the test suite."
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pdf = GuidePDF("P", "mm", "A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=22)

    cover(pdf)
    sec_overview(pdf)
    sec_install(pdf)
    sec_extraction(pdf)
    sec_pyqgis(pdf)
    sec_arcpy(pdf)
    sec_web(pdf)
    sec_ops(pdf)
    sec_catalogue(pdf)
    sec_symbology(pdf)
    sec_cat_pyqgis(pdf)
    sec_cat_arcpy(pdf)
    sec_cli(pdf)
    sec_testing(pdf)

    pdf.output(OUTPUT)
    print(f"[OK] {OUTPUT}  ({pdf.page} pages)")


if __name__ == "__main__":
    main()
