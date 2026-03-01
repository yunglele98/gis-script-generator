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
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(
        pdf.CW, 7,
        "PyQGIS  |  ArcPy  |  QGIS Project  |  ArcGIS Toolbox\n"
        "Folium  |  Kepler.gl  |  pydeck  |  Web UI\n"
        "Catalogue-driven script generation from PostGIS",
        align="C",
    )
    pdf.set_y(120)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(pdf.M)
    pdf.cell(pdf.CW, 7, f"Version 0.1.0   |   {date.today()}", ln=1, align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(pdf.M)
    pdf.multi_cell(
        pdf.CW, 5,
        "This guide covers all eight template types generated by gis-codegen and\n"
        "gis-catalogue, the Web UI, the full operations reference, the symbology\n"
        "dispatch table, and complete CLI documentation.",
        align="C",
    )


def sec_overview(pdf: GuidePDF):
    pdf.chapter(1, "Project Overview")
    pdf.body(
        "gis-codegen is a command-line tool that connects to a PostGIS database, "
        "extracts spatial layer metadata (geometry type, SRID, columns, primary keys, "
        "row counts), and generates ready-to-run scripts or project files for eight "
        "GIS platforms.\n\n"
        "gis-catalogue reads a map catalogue Excel file and writes one script per map "
        "entry, auto-selecting the correct renderer based on the symbology_type column.\n\n"
        "gis-ui launches a browser-based form that connects, extracts, and returns the "
        "generated file as a download -- no command line required."
    )

    pdf.section("Template types")
    pdf.th(["CLI command", "Template type", "Output file"], [72, 53, 45])
    rows = [
        ("gis-codegen --platform pyqgis",   "PyQGIS standalone script",      "*.py"),
        ("gis-codegen --platform arcpy",    "ArcPy / ArcGIS Pro script",     "*.py"),
        ("gis-codegen --platform folium",   "Folium / Leaflet HTML map",     "*.py"),
        ("gis-codegen --platform kepler",   "Kepler.gl HTML map",            "*.py"),
        ("gis-codegen --platform deck",     "pydeck / deck.gl HTML map",     "*.py"),
        ("gis-codegen --platform export",   "PostGIS -> GeoPackage script",  "*.py"),
        ("gis-codegen --platform qgs",      "QGIS project file",             "*.qgs"),
        ("gis-codegen --platform pyt",      "ArcGIS Python Toolbox",         "*.pyt"),
        ("gis-catalogue --platform pyqgis", "Catalogue PyQGIS (x N maps)",   "M##_name.py"),
        ("gis-catalogue --platform arcpy",  "Catalogue ArcPy  (x N maps)",   "M##_name.py"),
    ]
    for i, r in enumerate(rows):
        pdf.tr(r, [72, 53, 45], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("Package layout")
    pdf.code(
        "src/gis_codegen/\n"
        "    __init__.py         Public API: connect, extract_schema, generate_*\n"
        "    extractor.py        PostGIS metadata queries\n"
        "    generator.py        Code generation (all 8 platforms)\n"
        "    catalogue.py        Excel-driven per-map code generation\n"
        "    cli.py              gis-codegen CLI entry point\n"
        "    app.py              Flask web UI (gis-ui entry point)\n"
        "tests/\n"
        "    conftest.py         Shared fixtures\n"
        "    test_generator.py   test_catalogue.py   test_extractor.py\n"
        "    test_app.py         test_integration.py\n"
        ".github/workflows/\n"
        "    ci.yml              Unit + integration CI jobs\n"
        "maps/                   Generated output (git-ignored)\n"
        "make_pdf.py             This PDF generator"
    )


def sec_install(pdf: GuidePDF):
    pdf.chapter(2, "Installation & Setup")

    pdf.section("Install")
    pdf.code(
        "# From the project root:\n"
        "pip install -e .\n\n"
        "# With web mapping extras (folium, kepler, pydeck):\n"
        'pip install -e ".[web]"\n\n'
        "# With Flask web UI:\n"
        'pip install -e ".[server]"\n\n'
        "# With dev tools (pytest, coverage, openpyxl):\n"
        'pip install -e ".[dev]"\n\n'
        "# With PostGIS integration tests (requires Docker):\n"
        'pip install -e ".[integration]"\n\n'
        "# Entry points after install:\n"
        "gis-codegen   --help\n"
        "gis-catalogue --help\n"
        "gis-ui                   # launches web UI at http://localhost:5000"
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


def sec_configuration(pdf: GuidePDF):
    pdf.chapter(3, "Configuration & Connection")

    pdf.section("Connection value priority")
    pdf.body(
        "When a command runs, connection values are resolved in this order (highest wins):"
    )
    pdf.code(
        "1. CLI flags       --host, --port, --dbname, --user, --password\n"
        "2. Config file     gis_codegen.toml  [database] section\n"
        "3. Environment     PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD\n"
        "4. Built-in        localhost / 5432 / my_gis_db / postgres"
    )
    pdf.body(
        "Example: gis-codegen --host prod.example.com --platform pyqgis will use "
        "prod.example.com for the host, but PGPORT, PGDATABASE, and PGUSER from "
        "env vars or config file."
    )

    pdf.section("Config file search order")
    pdf.body(
        "gis-codegen looks for a TOML config file in this order (first found wins):"
    )
    pdf.code(
        "1. --config FILE                          (explicit CLI path)\n"
        "2. $GIS_CODEGEN_CONFIG env var            (if set)\n"
        "3. ./gis_codegen.toml                     (project root)\n"
        "4. ~/.config/gis_codegen/config.toml      (user home)"
    )
    pdf.body(
        "Tip: Use project-level gis_codegen.toml for workspace defaults, and "
        "user-level config.toml for persistent personal settings."
    )

    pdf.section("Complete config file reference")
    pdf.code(
        "# [database] section -- connection credentials\n"
        "[database]\n"
        'host     = "localhost"      # PGHOST override\n'
        "port     = 5432             # PGPORT override\n"
        'dbname   = "my_gis_db"      # PGDATABASE override\n'
        'user     = "postgres"       # PGUSER override\n'
        "# password = \"pass\"          # NOT recommended; use PGPASSWORD env var\n\n"
        "# [defaults] section -- pre-set generation options\n"
        "[defaults]\n"
        'platform      = "pyqgis"    # default platform (pyqgis or arcpy)\n'
        'schema_filter = "public"    # only extract from this PG schema\n'
        "no_row_counts = false       # set to true to speed up on large DBs\n"
        'output        = "output.py" # output file (overridable with -o)\n'
        'save_schema   = "schema.json"  # auto-save schema for offline use'
    )

    pdf.section("Password security best practices")
    pdf.body(
        "PGPASSWORD should never be stored in committed config files or scripts."
    )
    pdf.code(
        "# Good: set as environment variable at shell level\n"
        "export PGPASSWORD=secret\n"
        "gis-codegen --list-layers\n\n"
        "# Good: use shell script or CI secret management\n"
        "# Avoid: hardcoding in gis_codegen.toml\n"
        "# Avoid: embedding in generated Python scripts"
    )
    pdf.body(
        "Windows users: use set instead of export. The password expires when the "
        "shell closes, so this is safe for interactive use."
    )


def sec_extraction(pdf: GuidePDF):
    pdf.chapter(4, "Schema Extraction")

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
    pdf.chapter(5, "PyQGIS Template")

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
        'DB_HOST = "localhost"\n'
        'DB_PORT = "5432"\n'
        'DB_NAME = "my_gis_db"\n'
        'DB_USER = "postgres"\n'
        'DB_PASSWORD = "..."         # value at generation time\n'
        "\n"
        "# ================================================================\n"
        "# Layer : public.parcels   Geom: MULTIPOLYGON   SRID: 4326\n"
        "# ================================================================\n"
        "uri_parcels = QgsDataSourceUri()\n"
        "uri_parcels.setConnection(DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)\n"
        'uri_parcels.setDataSource("public", "parcels", "geom", "", "parcel_id")\n'
        "\n"
        'lyr_parcels = QgsVectorLayer(uri_parcels.uri(False), "parcels", "postgres")\n'
        "if not lyr_parcels.isValid():\n"
        '    print("[ERROR] Layer \'parcels\' failed to load.")\n'
        "else:\n"
        "    QgsProject.instance().addMapLayer(lyr_parcels)\n"
        "    print(f\"[OK] parcels: {lyr_parcels.featureCount()} features\")\n"
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


def sec_arcpy(pdf: GuidePDF):
    pdf.chapter(6, "ArcPy Template")

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
        'fc_parcels = os.path.join(SDE_FILE, "public.parcels")\n'
        "if arcpy.Exists(fc_parcels):\n"
        "    count = int(arcpy.management.GetCount(fc_parcels)[0])\n"
        "    print(f\"[OK] parcels: {count} rows\")"
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


def sec_qgs(pdf: GuidePDF):
    pdf.chapter(7, "QGIS Project File  (--platform qgs)")

    pdf.body(
        "Instead of a Python script, this platform emits a .qgs XML file that "
        "opens directly in QGIS 3.x. All PostGIS layers appear pre-connected in "
        "the Layers panel -- no scripting required. QGIS prompts for the database "
        "password on open; it is never embedded in the file."
    )

    pdf.section("Generate")
    pdf.code(
        "gis-codegen --platform qgs -o project.qgs\n\n"
        "# Then open in QGIS:\n"
        "#   File -> Open Project -> select project.qgs\n"
        "#   QGIS prompts for the PostGIS password\n"
        "#   All layers appear in the Layers panel"
    )

    pdf.section("Key design decisions")
    pdf.bullets([
        "Layer IDs are deterministic: {table}_{md5(qualified_name)[:8]} -- "
        "safe to version-control, same ID on every regeneration",
        "Geometry type mapping: POINT/MULTIPOINT -> Point (code 0), "
        "LINESTRING/MULTILINESTRING -> Line (code 1), "
        "POLYGON/MULTIPOLYGON -> Polygon (code 2)",
        "Project CRS and map canvas default to EPSG:4326 (world bounds)",
        "Per-layer <srs> uses minimal <authid>EPSG:{srid}</authid> -- "
        "QGIS resolves the full WKT from its internal EPSG registry",
        "sslmode=disable in the datasource string (change to require for production)",
    ])

    pdf.section("File structure")
    pdf.code(
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        "<qgis projectname=\"my_gis_db\" version=\"3.28.0-Firenze\">\n"
        "  <projectCrs>\n"
        "    <spatialrefsys><authid>EPSG:4326</authid></spatialrefsys>\n"
        "  </projectCrs>\n"
        "  <mapcanvas name=\"theMapCanvas\">\n"
        "    <units>degrees</units>\n"
        "    <extent>-180 -90 180 90</extent>\n"
        "    <destinationsrs><spatialrefsys><authid>EPSG:4326</authid></spatialrefsys></destinationsrs>\n"
        "  </mapcanvas>\n"
        "  <projectlayers>\n"
        "    <maplayer type=\"vector\" geometry=\"Polygon\">\n"
        "      <id>parcels_a1b2c3d4</id>\n"
        "      <datasource>dbname='my_gis_db' host=localhost port=5432\n"
        "        sslmode=disable key='parcel_id' srid=4326 type=Polygon\n"
        "        table=\"public\".\"parcels\" (geom) sql=</datasource>\n"
        "      <layername>parcels</layername>\n"
        "      <provider encoding=\"UTF-8\">postgres</provider>\n"
        "      <srs><spatialrefsys><authid>EPSG:4326</authid></spatialrefsys></srs>\n"
        "      <layerGeometryType>2</layerGeometryType>\n"
        "    </maplayer>\n"
        "  </projectlayers>\n"
        "  <legend>...</legend>\n"
        "</qgis>"
    )

    pdf.note(
        "--op flags are silently ignored for the qgs platform. "
        "Operations are only supported on pyqgis and arcpy."
    )


def sec_pyt(pdf: GuidePDF):
    pdf.chapter(8, "ArcGIS Python Toolbox  (--platform pyt)")

    pdf.body(
        "This platform generates a .pyt Python Toolbox file. When opened in "
        "ArcGIS Pro via Insert -> Toolbox -> Add Python Toolbox, it presents a "
        "GUI dialog with connection parameters pre-filled. Running the tool loads "
        "all PostGIS layers into the active map. The password is never hardcoded -- "
        "the dialog prompts for it at runtime."
    )

    pdf.section("Generate")
    pdf.code(
        "gis-codegen --platform pyt -o loader.pyt\n\n"
        "# Then in ArcGIS Pro:\n"
        "#   Insert -> Toolbox -> Add Python Toolbox\n"
        "#   Navigate to loader.pyt\n"
        "#   Double-click 'Load PostGIS Layers'\n"
        "#   Fill in password, click Run"
    )

    pdf.section("Toolbox structure")
    pdf.code(
        "class Toolbox:\n"
        "    def __init__(self):\n"
        "        self.label = \"PostGIS Loader\"\n"
        "        self.tools = [LoadPostGISLayers]\n"
        "\n"
        "class LoadPostGISLayers:\n"
        "    def getParameterInfo(self):   # 6 parameters:\n"
        "        # host     (GPString, Required, default from db_config)\n"
        "        # port     (GPString, Required, default from db_config)\n"
        "        # dbname   (GPString, Required, default from db_config)\n"
        "        # user     (GPString, Required, default from db_config)\n"
        "        # password (GPStringHidden, Required, NO default)\n"
        "        # schema_filter (GPString, Optional)\n"
        "\n"
        "    def isLicensed(self):  return True\n"
        "    def updateParameters(self, parameters):  pass\n"
        "    def updateMessages(self, parameters):    pass\n"
        "\n"
        "    def execute(self, parameters, messages):\n"
        "        # CreateDatabaseConnection -> postgis_conn.sde in scratchFolder\n"
        "        # ArcGISProject('CURRENT').activeMap.addDataFromPath per layer\n"
        "        _tables = [\n"
        "            ('public', 'parcels'),\n"
        "            ('public', 'roads'),\n"
        "            ...\n"
        "        ]"
    )

    pdf.note(
        "--op flags are silently ignored for the pyt platform. "
        "Operations are only supported on pyqgis and arcpy."
    )


def sec_webui(pdf: GuidePDF):
    pdf.chapter(9, "Web UI  (gis-ui)")

    pdf.body(
        "The web UI is a minimal Flask application that exposes the full "
        "gis-codegen pipeline as a browser form. Fill in the connection details, "
        "choose a platform, and click Generate -- the script or project file is "
        "returned as a file download. No command line or Python knowledge needed."
    )

    pdf.section("Start the server")
    pdf.code(
        'pip install -e ".[server]"\n'
        "gis-ui\n"
        "# -> Serving on http://0.0.0.0:5000\n"
        "# Open http://localhost:5000 in a browser"
    )

    pdf.section("Routes")
    pdf.th(["Method", "Path", "Description"], [20, 35, 115])
    routes = [
        ("GET",  "/",          "Render the connection + platform form"),
        ("POST", "/generate",  "Connect, extract, generate, return file download"),
    ]
    for i, r in enumerate(routes):
        pdf.tr(r, [20, 35, 115], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("File download extensions")
    pdf.th(["Platform", "Downloaded as"], [30, 140])
    exts = [
        ("qgs",                        "*.qgs  (QGIS project file)"),
        ("pyt",                        "*.pyt  (ArcGIS Python Toolbox)"),
        ("pyqgis, arcpy, folium, ...", "*.py   (Python script)"),
    ]
    for i, r in enumerate(exts):
        pdf.tr(r, [30, 140], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.section("Security notes")
    pdf.bullets([
        "Password is submitted via POST body only -- never in the URL or query string",
        "Password is never stored, logged, or reflected in the response",
        "Jinja2 autoescaping is active (Flask default) -- XSS safe",
        "Connection errors re-render the form with an error message (HTTP 400); "
        "the error text is from the psycopg2 exception and does not include the password",
        "No authentication layer is included -- run behind a reverse proxy or "
        "firewall if exposing beyond localhost",
    ])

    pdf.note(
        "The web UI supports all eight platforms. "
        "--op flags are not available in the web form; "
        "use the CLI directly for operation blocks."
    )


def sec_webmaps(pdf: GuidePDF):
    pdf.chapter(10, "Web Mapping Templates  (folium / kepler / deck)")

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

    pdf.section("GeoPackage export  (--platform export)")
    pdf.code(
        "gis-codegen --platform export -o export.py\n"
        "python export.py     # -> my_gis_db_export.gpkg"
    )
    pdf.body(
        "Dumps every spatial layer from PostGIS to a single GeoPackage file using "
        "geopandas. Each layer is written in a try/except block so one failure does "
        "not abort the rest. The script exits with code 1 if any layer failed."
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
    pdf.chapter(11, "Operations Reference  (--op flag)")

    pdf.body(
        "Operations inject additional code blocks into PyQGIS or ArcPy scripts. "
        "Repeat --op for multiple operations in one script:"
    )
    pdf.code(
        "gis-codegen --platform pyqgis --op buffer --op dissolve -o out.py\n"
        "gis-codegen --platform arcpy  --op extrude --op scene_layer -o 3d.py"
    )
    pdf.note(
        "Operations are not supported on web platforms (folium, kepler, deck, export) "
        "or on qgs and pyt. The --op flag is silently ignored for those platforms."
    )

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
    pdf.chapter(12, "Catalogue-Driven Generation")

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
        ("symbology_type",    "Drives automatic renderer selection (see Chapter 12)"),
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
        "# Use a saved schema JSON instead of a live DB connection:\n"
        "gis-catalogue --input catalogue.xlsx --schema schema.json\n\n"
        "# Add operation blocks to every script:\n"
        "gis-catalogue --input catalogue.xlsx --op buffer --op reproject\n\n"
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
        "    ..."
    )


def sec_symbology(pdf: GuidePDF):
    pdf.chapter(13, "Symbology Dispatch Table")

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
    pdf.chapter(14, "Catalogue PyQGIS Template Anatomy")

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
        "Symbology : choroplethe (degrade)\n"
        "Sources   : OSM building:levels  [2024-2026]\n"
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
        "    QgsProject.instance().addMapLayer(lyr_hauteurs_etages_degrade)"
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
        "    # ...\n"
        "\n"
        "qgs.exitQgis()"
    )


def sec_cat_arcpy(pdf: GuidePDF):
    pdf.chapter(15, "Catalogue ArcPy Template Anatomy")

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

    pdf.section("5  Feature class check and project setup")
    pdf.code(
        'fc_... = os.path.join(SDE_FILE, "public.hauteurs_etages_degrade")\n'
        "\n"
        "if arcpy.Exists(fc_...):\n"
        "    count = int(arcpy.management.GetCount(fc_...)[0])\n"
        '    print(f"[OK] {count} rows")\n'
        "\n"
        '    aprx   = arcpy.mp.ArcGISProject("CURRENT")\n'
        "    mp_map = aprx.listMaps()[0]\n"
        "    lyr_... = mp_map.addDataFromPath(fc_...)"
    )

    pdf.section("6  Auto-dispatched ArcPy symbology block")
    pdf.code(
        "    # --- Symbology: choroplethe (degrade) ---\n"
        '    GRAD_FIELD_... = "value"   # TODO: verify field name\n'
        "    sym = lyr_....symbology\n"
        '    sym.updateRenderer("GraduatedColorsRenderer")\n'
        "    sym.renderer.classificationField = GRAD_FIELD_...\n"
        "    sym.renderer.breakCount = 5\n"
        "    lyr_....symbology = sym\n"
        "    aprx.save()"
    )
    pdf.note(
        "Use APRX_PATH = \"CURRENT\" when running inside the ArcGIS Pro console. "
        "For standalone scripts, set APRX_PATH to the path of your .aprx file."
    )


def sec_cli(pdf: GuidePDF):
    pdf.chapter(16, "CLI Quick Reference")

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
        "  --platform          pyqgis | arcpy | folium | kepler | deck |\n"
        "                      export | qgs | pyt\n"
        "  --op OPERATION      Add an operation block (repeatable)\n"
        "                      See Chapter 10 for all 15 valid values\n"
        "                      (ignored for folium/kepler/deck/export/qgs/pyt)\n"
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
        "  --schema FILE            Schema JSON from gis-codegen --save-schema\n"
        "                           (offline mode -- no DB connection needed)\n"
        "  --op OPERATION           Add operation block to every script (repeatable)\n"
        "  --list                   Print filtered maps and exit (no files written)\n\n"
        "Filter applied automatically:\n"
        '  status IN {"have","partial"}  AND  "Vector" IN spatial_layer_type'
    )

    pdf.section("gis-ui  --  web UI")
    pdf.code(
        "gis-ui\n"
        "# Starts Flask server at http://0.0.0.0:5000\n"
        "# Open http://localhost:5000 in a browser\n\n"
        "# Requires:  pip install -e \".[server]\""
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
        "# 4. Open all layers directly in QGIS:\n"
        "gis-codegen --platform qgs -o project.qgs\n\n"
        "# 5. Load all layers into ArcGIS Pro via a toolbox dialog:\n"
        "gis-codegen --platform pyt -o loader.pyt\n\n"
        "# 6. Generate all catalogue maps as PyQGIS scripts:\n"
        "gis-catalogue --input catalogue.xlsx --output-dir ./maps/\n\n"
        "# 7. Generate a Kepler.gl web map:\n"
        "gis-codegen --platform kepler -o kepler_map.py\n"
        "python kepler_map.py\n\n"
        "# 8. Use the browser-based web UI:\n"
        "gis-ui"
    )


def sec_testing(pdf: GuidePDF):
    pdf.chapter(17, "Testing")

    pdf.section("Unit tests  (no database or Docker required)")
    pdf.code(
        "# Install dev + server extras:\n"
        'pip install -e ".[dev,server]"\n\n'
        "# Run all unit tests (excludes integration):\n"
        'python -m pytest tests/ -m "not integration" -v\n\n'
        "# With coverage report (must reach 80%):\n"
        'python -m pytest tests/ -m "not integration" \\\n'
        "    --cov=gis_codegen --cov-report=term-missing\n\n"
        "# Run one file:\n"
        "python -m pytest tests/test_generator.py -v\n\n"
        "# Filter by keyword:\n"
        'python -m pytest tests/ -k "qgs" -v'
    )

    pdf.section("Integration tests  (requires Docker)")
    pdf.code(
        "# Install integration extras:\n"
        'pip install -e ".[dev,integration]"\n\n'
        "# Run integration tests (spins up postgis/postgis:15-3.3 container):\n"
        "python -m pytest tests/test_integration.py -v -m integration\n\n"
        "# The tests skip gracefully if testcontainers is not installed."
    )

    pdf.section("Test suite summary")
    pdf.th(["File", "Tests", "What is covered"], [52, 18, 100])
    suite = [
        ("test_generator.py", "173",
         "safe_var, pg_type_to_*, _qgs_geom_type, 15 op blocks x 2 platforms, "
         "8 generators (pyqgis arcpy folium kepler deck export qgs pyt)"),
        ("test_catalogue.py", "108",
         "load_catalogue filtering, 5 PyQGIS + 5 ArcPy renderer blocks, "
         "symbology dispatch x 2 platforms, generate_map_pyqgis, generate_map_arcpy"),
        ("test_extractor.py",  "34",
         "fetch_columns, fetch_primary_keys, fetch_row_count_estimate, "
         "extract_schema (mocked connection)"),
        ("test_app.py",        "11",
         "GET / form rendering, POST /generate happy paths (pyqgis, qgs, pyt), "
         "error paths (bad port, connection failure)"),
        ("test_integration.py", "19",
         "Live PostGIS container via testcontainers: extract_schema, "
         "generate_pyqgis, generate_arcpy end-to-end (requires Docker)"),
        ("TOTAL",             "345", ""),
    ]
    for i, r in enumerate(suite):
        pdf.tr(r, [52, 18, 100], shade=(i % 2 == 0))
    pdf.ln(3)

    pdf.body(
        "Unit tests (all except test_integration.py) run in under 2 seconds "
        "because the generators are pure string-building functions -- no database "
        "connection or GIS library is needed."
    )

    pdf.section("CI pipeline  (.github/workflows/ci.yml)")
    pdf.bullets([
        "unit job: runs on ubuntu-latest, installs .[dev,server], "
        "runs pytest -m 'not integration' with coverage",
        "integration job: runs on ubuntu-latest (Docker available), "
        "installs .[dev,integration], runs pytest test_integration.py -m integration",
        "Both jobs trigger on push to main/master and on pull requests",
    ])


def sec_workflows(pdf: GuidePDF):
    pdf.chapter(18, "Practical Workflows")

    pdf.section("Workflow 1: Load all layers in QGIS with 3D visualization")
    pdf.body(
        "Goal: Open all spatial layers in QGIS and extrude buildings by height."
    )
    pdf.code(
        "# 1. Connect to PostGIS and generate a PyQGIS script with 3D extrusion:\n"
        "set PGPASSWORD=secret\n"
        "gis-codegen --platform pyqgis --op extrude --op z_stats \\\n"
        "             -o load_3d.py\n\n"
        "# 2. Open QGIS\n"
        "# 3. Open Python console (Plugins > Python Console)\n"
        "# 4. Run the script:\n"
        "exec(open('load_3d.py').read())\n\n"
        "# 5. In the Layers panel, select a layer and use the 3D view button"
    )
    pdf.body(
        "The generated script includes height calculations and is ready for 3D "
        "rendering. For full 3D visualization, use the --op scene_layer operation "
        "to export a 3D layer package."
    )

    pdf.section("Workflow 2: Create web maps from PostGIS data")
    pdf.body(
        "Goal: Generate interactive Leaflet and Kepler.gl maps from the database."
    )
    pdf.code(
        "# 1. Generate a Folium map (Leaflet):\n"
        "gis-codegen --platform folium -o my_map.py\n"
        "python my_map.py  # -> my_map.html\n\n"
        "# 2. Generate a Kepler.gl map (large datasets):\n"
        "gis-codegen --platform kepler -o kepler_map.py\n"
        "python kepler_map.py  # -> kepler_map.html\n\n"
        "# 3. Generate a pydeck map (deck.gl with 3D support):\n"
        "gis-codegen --platform deck -o deck_map.py\n"
        "python deck_map.py  # -> deck_map.html\n\n"
        "# Open the .html files in any browser"
    )
    pdf.body(
        "Each generator automatically selects an appropriate layer color scheme "
        "based on geometry type and data distribution."
    )

    pdf.section("Workflow 3: Filter layers and apply operations")
    pdf.body(
        "Goal: Generate scripts for only polygon layers, with buffer and dissolve."
    )
    pdf.code(
        "# List layers first to see geometry types:\n"
        "gis-codegen --list-layers\n\n"
        "# Generate PyQGIS for specific layers with operations:\n"
        "gis-codegen --platform pyqgis \\\n"
        "             --layer public.buildings \\\n"
        "             --layer public.parcels \\\n"
        "             --op buffer --op dissolve \\\n"
        "             -o analysis.py"
    )
    pdf.body(
        "Tip: --layer accepts schema.table format. Repeat --layer to select "
        "multiple layers. Operations are applied in order."
    )

    pdf.section("Workflow 4: Batch generate scripts from an Excel catalogue")
    pdf.body(
        "Goal: Create one script per map in an Excel catalogue, auto-configured."
    )
    pdf.code(
        "# 1. Prepare catalogue.xlsx with columns:\n"
        "#    map_id, theme, symbology_type, status, spatial_layer_type, etc.\n"
        "# 2. Run gis-catalogue:\n"
        "gis-catalogue --input catalogue.xlsx \\\n"
        "               --platform pyqgis \\\n"
        "               --output-dir ./generated_scripts/\n\n"
        "# 3. Check what was filtered (dry-run):\n"
        "gis-catalogue --input catalogue.xlsx --list"
    )
    pdf.body(
        "Included maps: status IN {have, partial} AND spatial_layer_type contains Vector. "
        "The symbology_type column determines which renderer is used (choropleth, categorized, etc.)."
    )

    pdf.section("Workflow 5: Offline generation with saved schema")
    pdf.body(
        "Goal: Generate scripts when database is offline or unavailable."
    )
    pdf.code(
        "# 1. While database is online, save the schema:\n"
        "gis-codegen --save-schema schema.json\n\n"
        "# 2. Later, generate scripts offline using the saved schema:\n"
        "gis-codegen --schema schema.json --platform arcpy -o output.py\n\n"
        "# 3. No database connection is needed for offline generation:\n"
        "gis-catalogue --input catalogue.xlsx \\\n"
        "               --schema schema.json \\\n"
        "               --platform arcpy"
    )
    pdf.body(
        "Schema files are regular JSON and can be committed to version control. "
        "Use this for reproducible, offline-friendly CI/CD pipelines."
    )


def sec_troubleshooting(pdf: GuidePDF):
    pdf.chapter(19, "Troubleshooting")

    pdf.section("Error: No database password supplied")
    pdf.body(
        "This error occurs when PGPASSWORD is not set and no password was "
        "provided via CLI flags or config file."
    )
    pdf.code(
        "# Solution 1: Set PGPASSWORD environment variable\n"
        "set PGPASSWORD=your_password  # Windows\n"
        "gis-codegen --list-layers\n\n"
        "# Solution 2: Pass password on command line\n"
        "gis-codegen --password your_password --list-layers\n\n"
        "# Solution 3: Add to gis_codegen.toml [database] section\n"
        "# (Not recommended for security)"
    )

    pdf.section("Error: No spatial layers found")
    pdf.body(
        "The database connected successfully, but no geometry columns were found."
    )
    pdf.code(
        "# Check which tables have geometry:\n"
        "SELECT table_name, column_name, geometry_type, srid\n"
        "FROM geometry_columns;"
    )
    pdf.body(
        "Common causes: (1) Geometry columns were added manually without "
        "AddGeometryColumn function; (2) table is in a non-public schema and "
        "--schema-filter excludes it; (3) the layer is actually a view and "
        "the geometry wasn't registered."
    )

    pdf.section("Error: Operation ignored (warning)")
    pdf.body(
        "This is a warning, not an error. Operations (--op) are only supported "
        "on pyqgis and arcpy platforms."
    )
    pdf.code(
        "# Good: operation is applied\n"
        "gis-codegen --platform pyqgis --op buffer -o out.py\n\n"
        "# Warning: operation is silently ignored (generates file anyway)\n"
        "gis-codegen --platform qgs --op buffer -o out.qgs\n"
        "[warn] --op buffer ignored (qgs does not support operations)"
    )
    pdf.body(
        "This is intentional design. The script still generates successfully."
    )

    pdf.section("Error: Connection refused (ECONNREFUSED)")
    pdf.body(
        "The CLI tried to connect to the database but the server is unreachable."
    )
    pdf.code(
        "# Check connection parameters:\n"
        "gis-codegen --host localhost --port 5432 --dbname mydb \\\n"
        "             --user postgres --list-layers\n\n"
        "# Verify PostgreSQL is running:\n"
        "psql --host localhost -U postgres -c 'SELECT 1'  # If psql is installed\n\n"
        "# Check firewall (if remote):\n"
        "telnet prod.example.com 5432"
    )

    pdf.section("Error: Missing module (openpyxl, fpdf2, etc.)")
    pdf.body(
        "A required optional dependency is not installed."
    )
    pdf.code(
        "# For gis-catalogue (uses openpyxl for Excel):\n"
        'pip install -e ".[dev]"\n\n'
        "# For PDF generation:\n"
        "pip install fpdf2\n\n"
        "# For web mapping:\n"
        'pip install -e ".[web]"\n\n'
        "# For everything:\n"
        'pip install -e ".[dev,server,web,integration]"'
    )

    pdf.section("Generated script fails with ImportError")
    pdf.body(
        "The generated script imports a module that is not installed in the "
        "target environment."
    )
    pdf.code(
        "# For PyQGIS scripts, run inside QGIS Python console\n"
        "# For ArcPy scripts, run in ArcGIS Pro Python environment\n"
        "# For Folium/Kepler/pydeck, install web dependencies:\n"
        'pip install -e ".[web]"'
    )
    pdf.body(
        "Generated scripts use minimal imports: qgis.core (PyQGIS), arcpy (ArcPy), "
        "folium (Folium), etc. Ensure the target platform has its SDK installed."
    )

    pdf.section("Generated script missing columns")
    pdf.body(
        "The script ran but some attribute columns are missing from the output layer."
    )
    pdf.code(
        "# This usually means the column was dropped in a dissolve or spatial join.\n"
        "# Check the source table:\n"
        "SELECT * FROM public.my_table LIMIT 1;\n\n"
        "# And verify the generated script includes all columns in the operation"
    )
    pdf.body(
        "The generators include all columns by default unless an operation "
        "(e.g., dissolve) drops them. Review the operation parameters in the "
        "generated script."
    )


def sec_architecture(pdf: GuidePDF):
    pdf.chapter(20, "Architecture & Design")

    pdf.section("System overview")
    pdf.body(
        "gis-codegen is a code generation pipeline with three main stages:"
    )
    pdf.code(
        "PostGIS Database\n"
        "      |\n"
        "      v\n"
        "  Extractor (extract_schema)\n"
        "      |\n"
        "      | Returns: Schema dict (JSON structure)\n"
        "      |\n"
        "      v\n"
        "  Generator (generate_* functions)\n"
        "      |\n"
        "      | Returns: Python code string (or XML for QGS)\n"
        "      |\n"
        "      v\n"
        "  Output (stdout or file)\n"
    )

    pdf.section("Schema dict structure")
    pdf.body(
        "extract_schema() returns a normalized dictionary representing all spatial "
        "layers in the database. This structure is the lingua franca between "
        "extraction and generation."
    )
    pdf.code(
        "{\n"
        '  "database": "my_gis_db",\n'
        '  "host": "localhost",\n'
        '  "layer_count": 3,\n'
        '  "layers": [\n'
        "    {\n"
        '      "schema": "public",\n'
        '      "table": "buildings",\n'
        '      "qualified_name": "public.buildings",\n'
        '      "geometry": {\n'
        '        "column": "geom",\n'
        '        "type": "MULTIPOLYGON",\n'
        '        "srid": 4326\n'
        "      },\n"
        '      "columns": [\n'
        "        {\"name\": \"gid\", \"data_type\": \"integer\", "
        "\"nullable\": false},\n"
        "        {\"name\": \"height\", \"data_type\": \"double precision\", "
        "\"nullable\": true}\n"
        "      ],\n"
        '      "primary_keys": ["gid"],\n'
        '      "row_count_estimate": 42000,\n'
        '      "comment": "Optional table description"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    pdf.section("Generator functions")
    pdf.body(
        "Each platform has a generator function that takes a schema dict and "
        "returns a string of code ready to run."
    )
    pdf.code(
        "from gis_codegen import generate_pyqgis, generate_arcpy\n\n"
        "schema = extract_schema(conn)\n"
        "pyqgis_code = generate_pyqgis(schema, operations=['buffer'])\n"
        "arcpy_code = generate_arcpy(schema, operations=['buffer'])\n\n"
        "# Write to file or stdout\n"
        "with open('load.py', 'w') as f:\n"
        "    f.write(pyqgis_code)"
    )

    pdf.section("Operation blocks")
    pdf.body(
        "Operations are Python code blocks inserted into the generated script. "
        "Each operation (buffer, clip, dissolve, etc.) is implemented as a "
        "template that receives the layer name and geometry type as context."
    )
    pdf.code(
        "Valid operations: reproject, export, buffer, clip, select, dissolve,\n"
        "                  centroid, field_calc, spatial_join, intersect,\n"
        "                  extrude, z_stats, floor_ceiling, volume, scene_layer\n\n"
        "PyQGIS operations use QGIS Processing algorithms (native:buffer, etc.).\n"
        "ArcPy operations use ArcGIS Spatial Analyst and Management tools."
    )

    pdf.section("Type mapping")
    pdf.body(
        "PostgreSQL data types are mapped to platform-specific types."
    )
    pdf.code(
        "PostgreSQL          PyQGIS              ArcPy\n"
        "-----------------------------------------------\n"
        "integer             QVariant.Int        -  (not used)\n"
        "text                QVariant.String     TEXT\n"
        "double precision    QVariant.Double     DOUBLE\n"
        "boolean             QVariant.Bool       -\n"
        "timestamp           QVariant.DateTime   DATE\n"
    )
    pdf.body(
        "Type mappings are defined in generator.py as pg_type_to_pyqgis() and "
        "pg_type_to_arcpy() functions. Custom types fall back to STRING."
    )

    pdf.section("Catalogue (map-driven generation)")
    pdf.body(
        "gis-catalogue reads an Excel file where each row represents a \"map\" "
        "(a visualization of one or more layers with a specific symbology)."
    )
    pdf.code(
        "Columns: map_id, theme, symbology_type, status, spatial_layer_type,\n"
        "         data sources, description, owner, effort, dependencies, ...\n\n"
        "Filter: status IN {have, partial} AND spatial_layer_type contains Vector\n\n"
        "Symbology dispatch table maps symbology_type to renderer logic:\n"
        '  "choroplèthe (dégradé)" -> continuous color scale (PyQGIS GraduatedSymbol)\n'
        '  "choroplèthe catégoriel" -> categorical colors (PyQGIS CategorizedSymbol)\n'
        '  "points" -> single color (PyQGIS SimpleMarker)'
    )
    pdf.body(
        "One script is generated per included map, with per-map layer selection "
        "and symbology applied automatically."
    )

    pdf.section("Extension points")
    pdf.body(
        "Developers can extend gis-codegen by:"
    )
    pdf.bullets([
        "Adding custom generators for new platforms (implement signature: "
        "generate_myplatform(schema: dict, operations: list = None) -> str)",
        "Adding custom operations (add to VALID_OPERATIONS set and implement "
        "_op_MYOP_pyqgis/arcpy functions)",
        "Adding custom symbology renderers (extend SymbologyRenderer class in "
        "catalogue.py)",
        "Using the public API (connect, extract_schema, generate_*) in custom "
        "workflows",
        "Saving and loading schemas offline for reproducible batch generation",
    ])

    pdf.section("Performance notes")
    pdf.bullets([
        "Unit tests (no database): ~2 seconds",
        "Extraction with row counts: depends on table size, usually 1-5 seconds",
        "Extraction with --no-row-counts: <1 second (recommended for large DBs)",
        "Generation: instant (string building)",
        "Catalogue: ~1 second per 100 maps (depends on layer count and operations)",
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    pdf = GuidePDF("P", "mm", "A4")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(auto=True, margin=22)

    cover(pdf)
    sec_overview(pdf)           # Ch  1
    sec_install(pdf)            # Ch  2
    sec_configuration(pdf)      # Ch  3
    sec_extraction(pdf)         # Ch  4
    sec_pyqgis(pdf)             # Ch  5
    sec_arcpy(pdf)              # Ch  6
    sec_qgs(pdf)                # Ch  7
    sec_pyt(pdf)                # Ch  8
    sec_webui(pdf)              # Ch  9
    sec_webmaps(pdf)            # Ch 10
    sec_ops(pdf)                # Ch 11
    sec_catalogue(pdf)          # Ch 12
    sec_symbology(pdf)          # Ch 13
    sec_cat_pyqgis(pdf)         # Ch 14
    sec_cat_arcpy(pdf)          # Ch 15
    sec_cli(pdf)                # Ch 16
    sec_testing(pdf)            # Ch 17
    sec_workflows(pdf)          # Ch 18
    sec_troubleshooting(pdf)    # Ch 19
    sec_architecture(pdf)       # Ch 20

    pdf.output(OUTPUT)
    print(f"[OK] {OUTPUT}  ({pdf.page} pages)")


if __name__ == "__main__":
    main()
