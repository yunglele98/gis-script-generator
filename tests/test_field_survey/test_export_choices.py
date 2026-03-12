import csv
import pytest
from unittest.mock import MagicMock

from field_survey.export_choices import (
    export_business_names,
    export_addresses,
    export_block_locations,
)


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value = cur
    return conn, cur


def test_export_business_names_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [("Cafe A",), ("Shop B",), ("Market C",)]
    outfile = tmp_path / "business_names.csv"

    count = export_business_names(conn, str(outfile))

    assert outfile.exists()
    rows = list(csv.DictReader(open(outfile)))
    assert count == 4  # 3 from DB + 1 "Other" fallback
    assert len(rows) == 4
    assert rows[0]["name"] == "Cafe A"
    assert rows[0]["label"] == "Cafe A"
    assert rows[-1]["name"] == "__other__"


def test_export_addresses_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [("123 Kensington Ave",), ("456 Augusta Ave",)]
    outfile = tmp_path / "addresses.csv"

    count = export_addresses(conn, str(outfile))

    rows = list(csv.DictReader(open(outfile)))
    assert count == 2
    assert len(rows) == 2
    assert rows[0]["name"] == "123 Kensington Ave"


def test_export_block_locations_writes_csv(mock_conn, tmp_path):
    conn, cur = mock_conn
    cur.fetchall.return_value = [
        ("Kensington Ave (Dundas to Baldwin)",),
        ("Augusta Ave (Dundas to Nassau)",),
    ]
    outfile = tmp_path / "block_locations.csv"

    count = export_block_locations(conn, str(outfile))

    rows = list(csv.DictReader(open(outfile)))
    assert count == 2
    assert len(rows) == 2
    assert "Kensington" in rows[0]["label"]
