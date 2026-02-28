"""
gis_codegen.app

Minimal Flask web UI for the GIS Script Generator.

Routes:
  GET  /          — connection form + platform selector
  POST /generate  — connect, extract, generate, return file download

Install:  pip install -e ".[server]"
Run:      gis-ui   (or: python -m gis_codegen.app)
"""

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

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>GIS Script Generator</title>
  <style>
    body { font-family: sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; }
    h1   { font-size: 1.4rem; }
    label { display: block; margin-top: 12px; font-weight: bold; }
    input, select { width: 100%; padding: 6px; margin-top: 4px; box-sizing: border-box; }
    input[type=submit] { margin-top: 20px; background: #0070f3; color: #fff;
                         border: none; padding: 10px; cursor: pointer; font-size: 1rem; }
    .error { color: #c00; background: #fee; padding: 10px; margin-top: 12px; border-radius: 4px; }
    fieldset { border: 1px solid #ccc; padding: 12px; margin-top: 16px; }
    legend   { font-weight: bold; }
  </style>
</head>
<body>
  <h1>GIS Script Generator</h1>

  {% if error %}
  <div class="error">{{ error }}</div>
  {% endif %}

  <form method="post" action="/generate">
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

    <input type="submit" value="Connect &amp; Generate">
  </form>
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


@app.route("/generate", methods=["POST"])
def generate() -> Response | tuple[str, int]:
    host          = request.form.get("host", "localhost").strip()
    port_str      = request.form.get("port", "5432").strip()
    dbname        = request.form.get("dbname", "my_gis_db").strip()
    user          = request.form.get("user", "postgres").strip()
    password      = request.form.get("password", "").strip()
    platform      = request.form.get("platform", "pyqgis").strip()
    schema_filter = request.form.get("schema_filter", "").strip()

    # Validate port
    try:
        port = int(port_str)
    except ValueError:
        return _render_form(
            host=host, port=port_str, dbname=dbname, user=user,
            platform=platform, schema_filter=schema_filter,
            error="Port must be an integer.",
        ), 400

    # Validate platform
    if platform not in _PLATFORMS:
        return _render_form(
            host=host, port=port_str, dbname=dbname, user=user,
            platform=platform, schema_filter=schema_filter,
            error=f"Unknown platform: {platform}",
        ), 400

    db_config = {
        "host":     host,
        "port":     port,
        "dbname":   dbname,
        "user":     user,
        "password": password,
    }

    # Connect and extract
    try:
        conn   = connect(db_config)
        schema = extract_schema(conn)
        conn.close()
    except Exception as exc:
        return _render_form(
            host=host, port=port_str, dbname=dbname, user=user,
            platform=platform, schema_filter=schema_filter,
            error=f"Connection error: {exc}",
        ), 400

    # Optional schema filter
    if schema_filter:
        schema["layers"] = [
            l for l in schema["layers"] if l["schema"] == schema_filter
        ]
        schema["layer_count"] = len(schema["layers"])

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
