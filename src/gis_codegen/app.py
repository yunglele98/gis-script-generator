"""
gis_codegen.app

Minimal Flask web UI for the GIS Script Generator.

Routes:
  GET  /          — connection form + platform selector
  POST /preview   — connect, extract, show layer selection checkboxes
  POST /generate  — generate script for selected layers, return file download

Install:  pip install -e ".[server]"
Run:      gis-ui   (or: python -m gis_codegen.app)
"""

import json

from flask import Flask, request, render_template_string, Response

from gis_codegen.extractor import connect, extract_schema
from gis_codegen.generator import (
    generate_pyqgis, generate_arcpy,
    generate_folium, generate_kepler, generate_deck,
    generate_export, generate_qgs, generate_pyt,
)

app = Flask(__name__)

# ---------------------------------------------------------------------------
# HTML template (embedded — no templates folder required)
# ---------------------------------------------------------------------------

_STYLES = """
    body { font-family: sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; }
    h1   { font-size: 1.4rem; }
    label { display: block; margin-top: 12px; font-weight: bold; }
    input, select { width: 100%; padding: 6px; margin-top: 4px; box-sizing: border-box; }
    input[type=submit] { margin-top: 20px; background: #0070f3; color: #fff;
                         border: none; padding: 10px; cursor: pointer; font-size: 1rem; }
    .error { color: #c00; background: #fee; padding: 10px; margin-top: 12px; border-radius: 4px; }
    fieldset { border: 1px solid #ccc; padding: 12px; margin-top: 16px; }
    legend   { font-weight: bold; }
"""

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GIS Script Generator</title>
  <style>""" + _STYLES + """</style>
</head>
<body>
  <h1>GIS Script Generator</h1>

  {% if error %}
  <div class="error">{{ error }}</div>
  {% endif %}

  <form method="post" action="/preview">
    <fieldset>
      <legend>Database connection</legend>
      <label>Host
        <input name="host" value="{{ host }}" placeholder="localhost">
      </label>
      <label>Port
        <input name="port" value="{{ port }}" placeholder="5432">
      </label>
      <label>Database
        <input name="dbname" value="{{ dbname }}" placeholder="my_gis_db">
      </label>
      <label>User
        <input name="user" value="{{ user }}" placeholder="postgres">
      </label>
      <label>Password
        <input name="password" type="password">
      </label>
    </fieldset>

    <fieldset>
      <legend>Generation options</legend>
      <label>Platform
        <select name="platform">
          {% for p in platforms %}
          <option value="{{ p }}" {% if p == platform %}selected{% endif %}>{{ p }}</option>
          {% endfor %}
        </select>
      </label>
      <label>Schema filter (optional)
        <input name="schema_filter" value="{{ schema_filter }}" placeholder="public">
      </label>
    </fieldset>

    <input type="submit" value="Connect &amp; Preview Layers">
  </form>
</body>
</html>"""

_LAYER_PICKER_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Select Layers — GIS Script Generator</title>
  <style>""" + _STYLES + """
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #ddd; }
    th { background: #f5f5f5; }
    tr:hover { background: #f9f9f9; }
    input[type=checkbox] { width: auto; margin: 0; }
    .layer-count { color: #666; margin-top: 8px; }
    .toggle-links { margin-top: 8px; }
    .toggle-links a { cursor: pointer; color: #0070f3; text-decoration: underline;
                      margin-right: 12px; font-size: 0.9rem; }
  </style>
</head>
<body>
  <h1>Select Layers</h1>
  <p class="layer-count">Found <strong>{{ layers|length }}</strong> spatial layer(s)
     in <strong>{{ dbname }}</strong>. Select which to include in the generated
     <strong>{{ platform }}</strong> script.</p>

  <form method="post" action="/generate">
    <input type="hidden" name="host" value="{{ host }}">
    <input type="hidden" name="port" value="{{ port }}">
    <input type="hidden" name="dbname" value="{{ dbname }}">
    <input type="hidden" name="user" value="{{ user }}">
    <input type="hidden" name="password" value="{{ password }}">
    <input type="hidden" name="platform" value="{{ platform }}">
    <input type="hidden" name="schema_json" value="{{ schema_json }}">

    <div class="toggle-links">
      <a onclick="toggleAll(true)">Select all</a>
      <a onclick="toggleAll(false)">Select none</a>
    </div>

    <table>
      <thead>
        <tr>
          <th></th>
          <th>Layer</th>
          <th>Geometry</th>
          <th>SRID</th>
          <th>Rows (est.)</th>
        </tr>
      </thead>
      <tbody>
      {% for ly in layers %}
        <tr>
          <td><input type="checkbox" name="selected_layers" value="{{ ly.qualified_name }}" checked></td>
          <td>{{ ly.qualified_name }}</td>
          <td>{{ ly.geometry.type }}</td>
          <td>{{ ly.geometry.srid }}</td>
          <td>{{ ly.row_count_display }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>

    <input type="submit" value="Generate Script">
  </form>

  <script>
    function toggleAll(state) {
      document.querySelectorAll('input[name="selected_layers"]')
        .forEach(function(cb) { cb.checked = state; });
    }
  </script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PLATFORMS = ["pyqgis", "arcpy", "folium", "kepler", "deck", "export", "qgs", "pyt"]

_EXT_MAP = {
    "qgs": ".qgs",
    "pyt": ".pyt",
}

_GENERATORS = {
    "pyqgis":  lambda schema, db: generate_pyqgis(schema, db, None),
    "arcpy":   lambda schema, db: generate_arcpy(schema, db, None),
    "folium":  generate_folium,
    "kepler":  generate_kepler,
    "deck":    generate_deck,
    "export":  generate_export,
    "qgs":     generate_qgs,
    "pyt":     generate_pyt,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _form_defaults() -> dict[str, object]:
    return dict(
        host="localhost",
        port="5432",
        dbname="my_gis_db",
        user="postgres",
        schema_filter="",
        platform="pyqgis",
        platforms=_PLATFORMS,
        error=None,
    )


def _render_form(**kwargs: object) -> str:
    ctx = {**_form_defaults(), **kwargs}
    return render_template_string(_TEMPLATE, **ctx)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index() -> str:
    return _render_form()


def _validate_connection_form() -> tuple[dict, str, str, str] | tuple[str, int]:
    """Parse and validate the connection form fields.

    Returns (form_data, platform, schema_filter, port_str) on success,
    or (error_html, status_code) on validation failure.
    """
    host          = request.form.get("host", "localhost").strip()
    port_str      = request.form.get("port", "5432").strip()
    dbname        = request.form.get("dbname", "my_gis_db").strip()
    user          = request.form.get("user", "postgres").strip()
    password      = request.form.get("password", "").strip()
    platform      = request.form.get("platform", "pyqgis").strip()
    schema_filter = request.form.get("schema_filter", "").strip()

    try:
        port = int(port_str)
    except ValueError:
        return _render_form(
            host=host, port=port_str, dbname=dbname, user=user,
            platform=platform, schema_filter=schema_filter,
            error="Port must be an integer.",
        ), 400

    if platform not in _PLATFORMS:
        return _render_form(
            host=host, port=port_str, dbname=dbname, user=user,
            platform=platform, schema_filter=schema_filter,
            error=f"Unknown platform: {platform}",
        ), 400

    form_data = {
        "host": host, "port": port, "port_str": port_str,
        "dbname": dbname, "user": user, "password": password,
    }
    return form_data, platform, schema_filter, port_str


@app.route("/preview", methods=["POST"])
def preview() -> str | tuple[str, int]:
    result = _validate_connection_form()
    if isinstance(result[0], str):
        return result  # validation error

    form_data, platform, schema_filter, port_str = result

    db_config = {
        "host":     form_data["host"],
        "port":     form_data["port"],
        "dbname":   form_data["dbname"],
        "user":     form_data["user"],
        "password": form_data["password"],
    }

    try:
        conn   = connect(db_config)
        schema = extract_schema(conn)
        conn.close()
    except Exception as exc:
        return _render_form(
            host=form_data["host"], port=port_str,
            dbname=form_data["dbname"], user=form_data["user"],
            platform=platform, schema_filter=schema_filter,
            error=f"Connection error: {exc}",
        ), 400

    if schema_filter:
        schema["layers"] = [
            ly for ly in schema["layers"] if ly["schema"] == schema_filter
        ]
        schema["layer_count"] = len(schema["layers"])

    # Add display-friendly row counts
    for ly in schema["layers"]:
        est = ly.get("row_count_estimate", -1)
        ly["row_count_display"] = f"~{est:,}" if est >= 0 else "unknown"

    schema_json = json.dumps(schema)

    return render_template_string(
        _LAYER_PICKER_TEMPLATE,
        host=form_data["host"],
        port=port_str,
        dbname=form_data["dbname"],
        user=form_data["user"],
        password=form_data["password"],
        platform=platform,
        layers=schema["layers"],
        schema_json=schema_json,
    )


@app.route("/generate", methods=["POST"])
def generate() -> Response | tuple[str, int]:
    host     = request.form.get("host", "localhost").strip()
    port_str = request.form.get("port", "5432").strip()
    dbname   = request.form.get("dbname", "my_gis_db").strip()
    user     = request.form.get("user", "postgres").strip()
    password = request.form.get("password", "").strip()
    platform = request.form.get("platform", "pyqgis").strip()

    try:
        port = int(port_str)
    except ValueError:
        return _render_form(error="Port must be an integer."), 400

    if platform not in _PLATFORMS:
        return _render_form(error=f"Unknown platform: {platform}"), 400

    db_config = {
        "host": host, "port": port, "dbname": dbname,
        "user": user, "password": password,
    }

    # Restore schema from the hidden field (avoids a second DB connection)
    schema_json = request.form.get("schema_json", "")
    if not schema_json:
        return _render_form(error="Missing schema data. Please start over."), 400

    try:
        schema = json.loads(schema_json)
    except json.JSONDecodeError:
        return _render_form(error="Invalid schema data. Please start over."), 400

    # Filter to selected layers
    selected = request.form.getlist("selected_layers")
    if selected:
        schema["layers"] = [
            ly for ly in schema["layers"] if ly["qualified_name"] in selected
        ]
    schema["layer_count"] = len(schema["layers"])

    if not schema["layers"]:
        return _render_form(error="No layers selected. Please start over."), 400

    # Generate
    code = _GENERATORS[platform](schema, db_config)

    ext      = _EXT_MAP.get(platform, ".py")
    filename = f"{dbname}_{platform}{ext}"

    return Response(
        code,
        mimetype="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    main()
