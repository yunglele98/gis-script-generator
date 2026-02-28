# FAQ

Frequently asked questions about `gis-codegen`.

---

## General

### What does gis-codegen actually do?

It connects to your PostGIS database, reads the metadata of all spatial layers (geometry type, CRS, columns, primary keys), and generates a complete, runnable GIS script for your chosen platform. You don't have to write the boilerplate — `gis-codegen` does it for you.

---

### Does it modify my database?

No. All connections are **read-only** (`autocommit=True`, SELECT-only queries). `gis-codegen` never writes to, modifies, or deletes anything in your database.

---

### Do I need QGIS or ArcGIS Pro installed?

Not to generate scripts. `gis-codegen` itself has no dependency on QGIS, ArcGIS Pro, ArcPy, or PyQGIS. You only need those installed to *run* the generated scripts in those environments.

---

### Can I use this with a non-PostGIS database?

No. `gis-codegen` specifically queries the `geometry_columns` view and other PostGIS metadata tables. It requires a PostgreSQL database with the PostGIS extension.

---

### What PostgreSQL/PostGIS versions are supported?

Any version of PostGIS that supports the `geometry_columns` view (PostGIS 2.0+). The tool uses standard read-only queries and does not depend on any specific PostgreSQL or PostGIS version features.

---

## Installation

### Why is my Python too old?

`gis-codegen` requires Python 3.10+ because it uses the `str | None` union type syntax (PEP 604). Python 3.9 and earlier use `Optional[str]` syntax. Upgrade to Python 3.10 or later.

---

### I installed it but `gis-codegen` is not found

Make sure the package was installed in the right environment and that `~/.local/bin` (or the equivalent for your Python installation) is on your `PATH`.

```bash
pip install -e .
which gis-codegen    # should show a path
gis-codegen --help
```

---

## Platforms

### Which platforms support operations?

Only `pyqgis` and `arcpy`. See [Operations Reference](Operations-Reference) and [Platform Guide](Platform-Guide).

---

### Can I generate scripts for multiple platforms at once?

Not in a single command. Run `gis-codegen` once per platform:

```bash
gis-codegen --platform pyqgis --output load_qgis.py
gis-codegen --platform arcpy  --output load_arcpy.py
gis-codegen --platform folium --output make_map.py
```

---

### How do I open a `.qgs` file?

Double-click it in your file manager, or use **File → Open Project** in QGIS. The project file embeds PostGIS connection information, so you will be prompted for a password when QGIS connects.

---

### How do I use a `.pyt` toolbox in ArcGIS Pro?

In ArcGIS Pro: **Catalog pane → Toolboxes → right-click → Add Toolbox** → select your `.pyt` file. The toolbox will appear with one tool per spatial layer.

---

## Configuration

### Where should I put my database password?

Use the `PGPASSWORD` environment variable. Never put it in the config file or as a CLI flag in scripts (both can end up in shell history or logs).

```bash
export PGPASSWORD=secret
```

---

### Can I have multiple config files for different databases?

Yes. Use the `--config` flag to specify which file to use:

```bash
gis-codegen --config production.toml --platform pyqgis
gis-codegen --config staging.toml    --platform arcpy
```

---

## Generated Scripts

### Will the generated script work without modification?

Usually yes for basic use. The generated script is complete and runnable. You may want to customise it — for example, to filter to specific layers, change styling, or add project-specific logic.

---

### Can I add custom code to the generated script?

Yes — the generated script is just Python (or XML for `.qgs`). Edit it freely after generation.

---

### Why does the generated script import `geopandas` / `psycopg2`?

For platforms like `folium`, `kepler`, and `deck`, the generated script reads data from PostGIS at runtime using GeoPandas and psycopg2. Install the `[web]` extras to provide these dependencies.

---

## Excel Catalogue

### What if some rows in my spreadsheet should be skipped?

Set their `status` to anything other than `have` or `partial` (e.g. `want`, `future`, `missing`). Those rows will be silently skipped.

---

### Does gis-catalogue connect to the database?

Yes — it uses the same PostGIS connection as `gis-codegen` to verify layer existence and extract column metadata.

---

### Can I use gis-catalogue with ArcPy?

Yes: `gis-catalogue --platform arcpy map_catalogue.xlsx`

Scripts go to `./maps_arcpy/` by default.

---

## Testing & Development

### Why is `cli.py` excluded from coverage?

`cli.py` requires a live PostGIS connection to test meaningfully. It is excluded from unit test coverage and instead covered by integration tests (which require Docker). This is intentional and documented in `pyproject.toml`.

---

### How do I run only the fast tests?

```bash
python -m pytest tests/ -m "not integration"
```

This skips the integration tests (which require Docker) and runs all 326 unit tests in about 2 seconds.

---

### Can I contribute a new platform or operation?

Yes — see [Development & Testing](Development-and-Testing) for instructions on adding platforms and operations, including test requirements.
