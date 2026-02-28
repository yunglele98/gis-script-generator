# Troubleshooting

This page covers common errors and how to fix them.

---

## Connection Errors

### No password supplied

```
[ERROR] No database password supplied.
Set PGPASSWORD or use --password.
```

**Cause:** The CLI found no password from CLI flags, config file, or environment.

**Fix:**
```bash
export PGPASSWORD=your_password
```
Or pass it directly (less secure):
```bash
gis-codegen --password your_password --platform pyqgis
```

---

### Connection refused

```
could not connect to server: Connection refused
    Is the server running on host "localhost" and accepting
    TCP/IP connections on port 5432?
```

**Cause:** PostgreSQL / PostGIS is not running, or the host/port is wrong.

**Fix:**
1. Verify the server is running: `pg_isready -h localhost -p 5432`
2. Check your `--host` and `--port` flags or config file
3. Try connecting with `psql` to confirm credentials work

---

### Authentication failed

```
FATAL:  password authentication failed for user "postgres"
```

**Cause:** Wrong password or username.

**Fix:** Verify credentials with `psql -h HOST -U USER -d DBNAME`.

---

## Schema / Layer Errors

### No spatial layers found

```
[WARN] No spatial layers found in geometry_columns.
```

**Cause:** The database has no layers registered in the `geometry_columns` view.

**Possible reasons:**
- Tables with geometry columns were created without `AddGeometryColumn` or `ST_SetSRID`
- You are connected to the wrong database
- The user does not have SELECT permission on `geometry_columns`

**Fix:**
```sql
-- Check in psql:
SELECT * FROM geometry_columns;

-- If empty, check if geometry columns exist:
SELECT table_name, column_name, udt_name
FROM information_schema.columns
WHERE udt_name IN ('geometry', 'geography');
```

---

## Operation Warnings

### `--op` flag ignored

```
[warn] Operations are not supported for platform 'folium'. Ignoring: buffer, dissolve
```

**Cause:** You passed `--op` with a platform that does not support operations.

**Behaviour:** This is intentional — the warning is emitted to stderr but the file is still generated without the operations.

**Fix:** Use `--platform pyqgis` or `--platform arcpy` if you need operations.

---

## Package / Import Errors

### Flask not installed

```
ModuleNotFoundError: No module named 'flask'
```

**Fix:** `pip install -e ".[server]"`

---

### openpyxl not installed

```
[ERROR] openpyxl is required for gis-catalogue.
Install with: pip install openpyxl
```

**Fix:** `pip install openpyxl` or `pip install -e ".[dev]"`

---

### Web mapping library not installed

```
ModuleNotFoundError: No module named 'folium'
ModuleNotFoundError: No module named 'keplergl'
ModuleNotFoundError: No module named 'pydeck'
```

**Fix:** `pip install -e ".[web]"` (installs folium, keplergl, pydeck, geopandas)

---

### ArcPy not available

```
ModuleNotFoundError: No module named 'arcpy'
```

**Cause:** ArcPy cannot be installed via pip — it ships with ArcGIS Pro.

**Fix:** Run the generated script using the ArcGIS Pro Python environment, not a standard Python installation.

---

### PyQGIS not available

```
ModuleNotFoundError: No module named 'qgis'
```

**Cause:** PyQGIS ships with QGIS, not pip.

**Fix:** Run the generated script from the QGIS Python console, or configure `sys.path` to include QGIS libraries.

---

## Coverage / Test Issues

### `cli.py` missing from coverage

This is expected. `cli.py` is excluded from coverage measurement (`omit = ["*/cli.py"]` in `pyproject.toml`) because it requires a live database to test. It is covered by integration tests.

---

### Integration tests failing

```
docker.errors.DockerException: Error while fetching server API version
```

**Cause:** Docker is not running.

**Fix:** Start Docker and retry.

```bash
docker info   # should succeed before running integration tests
```

---

## Config File Issues

### Config file not found

The tool searches for `gis_codegen.toml` in this order:
1. `--config FILE` flag
2. `$GIS_CODEGEN_CONFIG` environment variable
3. `./gis_codegen.toml` (current directory)
4. `~/.config/gis_codegen/config.toml`

If none are found, it falls through to environment variables and built-in defaults.

---

### TOML parse error

```
tomllib.TOMLDecodeError: ...
```

**Cause:** Your `gis_codegen.toml` has a syntax error.

**Fix:** Validate your TOML at https://www.toml-lint.com/ or use a TOML linter.

---

## Still stuck?

- Run `gis-codegen --help` to see all available flags
- Check the [Architecture](Architecture) page for data flow details
- Check the [FAQ](FAQ) for common questions
- Open an issue on GitHub with the full error output and your command
