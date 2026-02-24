"""
PostGIS integration tests.

Requires Docker and testcontainers:
    pip install -e ".[integration]"
    pytest tests/test_integration.py -v -m integration

These tests are excluded from the regular test run:
    pytest tests/ -m "not integration"
"""

import pytest

# Gracefully skip entire module if testcontainers is not installed
testcontainers = pytest.importorskip("testcontainers")

from testcontainers.postgres import PostgresContainer  # noqa: E402

from gis_codegen.extractor import connect, extract_schema  # noqa: E402
from gis_codegen.generator import generate_pyqgis, generate_arcpy  # noqa: E402

POSTGIS_IMAGE = "postgis/postgis:15-3.3"

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def postgis_container():
    """Start a PostGIS container once for the entire test session."""
    with PostgresContainer(POSTGIS_IMAGE) as container:
        yield container


@pytest.fixture(scope="session")
def live_conn(postgis_container):
    """
    Return a live psycopg2 connection to the PostGIS container.

    Creates the PostGIS extension and two test tables:
      - public.parcels  (MULTIPOLYGON, EPSG:4326)
      - public.roads    (LINESTRING,   EPSG:4326)
    """
    db_config = {
        "host":     postgis_container.get_container_host_ip(),
        "port":     postgis_container.get_exposed_port(5432),
        "dbname":   postgis_container.dbname,
        "user":     postgis_container.username,
        "password": postgis_container.password,
    }
    conn = connect(db_config)
    cur  = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.parcels (
            parcel_id  SERIAL PRIMARY KEY,
            address    TEXT,
            geom       geometry(MULTIPOLYGON, 4326)
        );
    """)
    cur.execute("""
        INSERT INTO public.parcels (address, geom)
        VALUES (
            '123 Main St',
            ST_Multi(ST_GeomFromText(
                'POLYGON((-73.6 45.5, -73.5 45.5, -73.5 45.6, -73.6 45.6, -73.6 45.5))',
                4326
            ))
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS public.roads (
            road_id  SERIAL PRIMARY KEY,
            name     TEXT,
            geom     geometry(LINESTRING, 4326)
        );
    """)
    cur.execute("""
        INSERT INTO public.roads (name, geom)
        VALUES (
            'Rue Principale',
            ST_GeomFromText('LINESTRING(-73.6 45.55, -73.5 45.55)', 4326)
        );
    """)

    conn.commit()
    cur.close()
    yield conn, db_config
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _schema(live_conn):
    conn, db_config = live_conn
    return extract_schema(conn, include_row_counts=False), db_config


# ---------------------------------------------------------------------------
# TestExtractSchemaLive
# ---------------------------------------------------------------------------

class TestExtractSchemaLive:
    def test_layer_count_at_least_two(self, live_conn):
        schema, _ = _schema(live_conn)
        assert schema["layer_count"] >= 2

    def test_parcels_layer_present(self, live_conn):
        schema, _ = _schema(live_conn)
        names = [l["table"] for l in schema["layers"]]
        assert "parcels" in names

    def test_roads_layer_present(self, live_conn):
        schema, _ = _schema(live_conn)
        names = [l["table"] for l in schema["layers"]]
        assert "roads" in names

    def test_parcels_geometry_type(self, live_conn):
        schema, _ = _schema(live_conn)
        parcel = next(l for l in schema["layers"] if l["table"] == "parcels")
        assert "POLYGON" in parcel["geometry"]["type"].upper()

    def test_roads_geometry_type(self, live_conn):
        schema, _ = _schema(live_conn)
        road = next(l for l in schema["layers"] if l["table"] == "roads")
        assert "LINE" in road["geometry"]["type"].upper()

    def test_parcels_srid(self, live_conn):
        schema, _ = _schema(live_conn)
        parcel = next(l for l in schema["layers"] if l["table"] == "parcels")
        assert parcel["geometry"]["srid"] == 4326

    def test_roads_srid(self, live_conn):
        schema, _ = _schema(live_conn)
        road = next(l for l in schema["layers"] if l["table"] == "roads")
        assert road["geometry"]["srid"] == 4326

    def test_parcels_has_address_column(self, live_conn):
        schema, _ = _schema(live_conn)
        parcel = next(l for l in schema["layers"] if l["table"] == "parcels")
        col_names = [c["name"] for c in parcel["columns"]]
        assert "address" in col_names

    def test_parcels_primary_key(self, live_conn):
        schema, _ = _schema(live_conn)
        parcel = next(l for l in schema["layers"] if l["table"] == "parcels")
        assert "parcel_id" in parcel["primary_keys"]

    def test_schema_has_database_key(self, live_conn):
        schema, _ = _schema(live_conn)
        assert "database" in schema

    def test_schema_has_host_key(self, live_conn):
        schema, _ = _schema(live_conn)
        assert "host" in schema


# ---------------------------------------------------------------------------
# TestGeneratorsLive
# ---------------------------------------------------------------------------

class TestGeneratorsLive:
    def test_generate_pyqgis_contains_parcels(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_pyqgis(schema, db_config)
        assert "parcels" in code

    def test_generate_pyqgis_contains_roads(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_pyqgis(schema, db_config)
        assert "roads" in code

    def test_generate_arcpy_contains_parcels(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_arcpy(schema, db_config)
        assert "parcels" in code

    def test_generate_arcpy_contains_roads(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_arcpy(schema, db_config)
        assert "roads" in code

    def test_generate_pyqgis_no_hardcoded_password(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_pyqgis(schema, db_config)
        assert db_config["password"] not in code

    def test_generate_arcpy_no_hardcoded_password(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_arcpy(schema, db_config)
        assert db_config["password"] not in code

    def test_generate_pyqgis_contains_host(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_pyqgis(schema, db_config)
        assert db_config["host"] in code

    def test_generate_arcpy_contains_dbname(self, live_conn):
        schema, db_config = _schema(live_conn)
        code = generate_arcpy(schema, db_config)
        assert db_config["dbname"] in code
