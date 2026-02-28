# Web UI Guide

`gis-ui` provides a browser-based interface for generating GIS scripts without using the command line.

---

## Starting the Server

```bash
# Install with Flask support
pip install -e ".[server]"

# Start the server
gis-ui
```

The server starts on **http://localhost:5000**. Open this URL in your browser.

---

## The Form

The web UI presents a single-page form with the following fields:

### Connection Settings

| Field | Default | Description |
|---|---|---|
| **Host** | `localhost` | PostGIS server hostname |
| **Port** | `5432` | PostgreSQL port |
| **Database** | `my_gis_db` | Database name |
| **User** | `postgres` | Username |
| **Password** | *(empty)* | Password — entered per request, never stored |

### Generation Settings

| Field | Options | Description |
|---|---|---|
| **Platform** | All 8 platforms | Select your target GIS platform |
| **Operations** | All 15 operations | Multi-select (only effective for pyqgis/arcpy) |

---

## Security

- Passwords are submitted via HTTP POST and used **only for the duration of the request**
- Passwords are **never** stored server-side (no session, no database, no file)
- The server is designed for local use (`localhost`) — do not expose it publicly without authentication

---

## Workflow

1. Fill in your connection details and password
2. Select your target platform
3. Optionally select one or more operations
4. Click **Generate**
5. The browser downloads the generated script file directly

---

## Architecture Note

The entire web UI is implemented as a single embedded HTML template inside `src/gis_codegen/app.py`. There is no `templates/` folder — everything is self-contained in one file. This keeps deployment simple: just install and run `gis-ui`.

---

## Troubleshooting the Web UI

**Server won't start:**
```
ModuleNotFoundError: No module named 'flask'
```
Solution: `pip install -e ".[server]"`

**Connection refused in the form:**
- Check that your PostGIS server is running and reachable from localhost
- Verify the password via `psql` first

**Download doesn't start:**
- Check the browser console for errors
- Try a different browser
- Check the terminal for Python tracebacks

---

## Alternatives

If you prefer the command line, see [CLI Reference](CLI-Reference). For batch processing of many maps, see [Excel Catalogue Tool](Excel-Catalogue-Tool).
