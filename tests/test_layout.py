"""
Tests for gis_codegen.layout — template and composition configuration.
"""

import pytest
from pathlib import Path
from gis_codegen.layout import TemplateConfig, CompositionLayout


# ---------------------------------------------------------------------------
# TemplateConfig tests
# ---------------------------------------------------------------------------

class TestTemplateConfigFromToml:
    """Test TemplateConfig.from_toml() loading."""

    def test_loads_all_fields(self, tmp_path):
        """Load a complete template TOML with all sections."""
        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
name = "My Template"

[custom]
preamble = "# Custom preamble"
extra_imports = "import custom_lib"
per_layer_prefix = "print('Start {table}')"
per_layer_suffix = "print('End {table}')"
teardown = "print('Done')"

[sections]
include_sample_rows = false
include_crs_info = false
include_field_list = false
"""
        )

        cfg = TemplateConfig.from_toml(str(toml_file))
        assert cfg.name == "My Template"
        assert cfg.preamble == "# Custom preamble"
        assert cfg.extra_imports == "import custom_lib"
        assert cfg.per_layer_prefix == "print('Start {table}')"
        assert cfg.per_layer_suffix == "print('End {table}')"
        assert cfg.teardown == "print('Done')"
        assert cfg.include_sample_rows is False
        assert cfg.include_crs_info is False
        assert cfg.include_field_list is False

    def test_applies_section_defaults(self, tmp_path):
        """Sections not specified default to True."""
        toml_file = tmp_path / "template.toml"
        toml_file.write_text("name = 'Test'")

        cfg = TemplateConfig.from_toml(str(toml_file))
        assert cfg.include_sample_rows is True
        assert cfg.include_crs_info is True
        assert cfg.include_field_list is True

    def test_partial_toml(self, tmp_path):
        """Load template with only some optional keys."""
        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[custom]
preamble = "# Only preamble"
"""
        )

        cfg = TemplateConfig.from_toml(str(toml_file))
        assert cfg.preamble == "# Only preamble"
        assert cfg.extra_imports is None
        assert cfg.teardown is None

    def test_missing_file_exits(self, tmp_path):
        """from_toml exits if file not found."""
        with pytest.raises(SystemExit):
            TemplateConfig.from_toml(str(tmp_path / "nonexistent.toml"))

    def test_invalid_toml_exits(self, tmp_path):
        """from_toml exits on invalid TOML syntax."""
        toml_file = tmp_path / "bad.toml"
        toml_file.write_text("this is not valid = [ toml ]")

        with pytest.raises(SystemExit):
            TemplateConfig.from_toml(str(toml_file))

    def test_substitute_placeholders(self):
        """Substitute {table}, {schema}, {qualified_name} in text."""
        cfg = TemplateConfig()
        text = "SELECT * FROM {schema}.{table} -- {qualified_name}"
        result = cfg.substitute_placeholders(text, "my_table", "public", "public.my_table")
        assert result == "SELECT * FROM public.my_table -- public.my_table"

    def test_substitute_placeholders_no_matches(self):
        """Placeholders are optional."""
        cfg = TemplateConfig()
        text = "Just some text"
        result = cfg.substitute_placeholders(text, "table", "schema", "schema.table")
        assert result == "Just some text"


# ---------------------------------------------------------------------------
# CompositionLayout tests
# ---------------------------------------------------------------------------

class TestCompositionLayoutFromToml:
    """Test CompositionLayout.from_toml() loading."""

    def test_loads_all_fields(self, tmp_path):
        """Load a complete composition layout TOML."""
        toml_file = tmp_path / "layout.toml"
        toml_file.write_text(
            """
name = "My Layout"
platform = "pyqgis"
output = "out.py"

[[layers]]
table = "public.buildings"
operations = ["buffer", "dissolve"]
classification = "height"

[[layers]]
table = "public.streets"
operations = ["reproject"]

[[layers]]
table = "public.parks"
"""
        )

        layout = CompositionLayout.from_toml(str(toml_file))
        assert layout.name == "My Layout"
        assert layout.platform == "pyqgis"
        assert layout.output == "out.py"
        assert len(layout.layers) == 3

        assert layout.layers[0]["table"] == "public.buildings"
        assert layout.layers[0]["operations"] == ["buffer", "dissolve"]
        assert layout.layers[0]["classification"] == "height"

        assert layout.layers[1]["table"] == "public.streets"
        assert layout.layers[1]["operations"] == ["reproject"]

        assert layout.layers[2]["table"] == "public.parks"
        assert "operations" not in layout.layers[2]

    def test_empty_layers_list(self, tmp_path):
        """Load layout with no layers specified."""
        toml_file = tmp_path / "layout.toml"
        toml_file.write_text("name = 'Empty'")

        layout = CompositionLayout.from_toml(str(toml_file))
        assert layout.layers == []

    def test_missing_file_exits(self, tmp_path):
        """from_toml exits if file not found."""
        with pytest.raises(SystemExit):
            CompositionLayout.from_toml(str(tmp_path / "nonexistent.toml"))

    def test_invalid_toml_exits(self, tmp_path):
        """from_toml exits on invalid TOML syntax."""
        toml_file = tmp_path / "bad.toml"
        toml_file.write_text("[layers] invalid = {toml}")

        with pytest.raises(SystemExit):
            CompositionLayout.from_toml(str(toml_file))


class TestCompositionLayoutFilterSchema:
    """Test CompositionLayout.filter_schema() layer filtering."""

    @pytest.fixture
    def sample_schema(self):
        """A sample schema with 3 layers."""
        return {
            "database": "test_db",
            "host": "localhost",
            "layer_count": 3,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                },
                {
                    "schema": "public",
                    "table": "streets",
                    "qualified_name": "public.streets",
                    "geometry": {"type": "LINESTRING", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                },
                {
                    "schema": "public",
                    "table": "parks",
                    "qualified_name": "public.parks",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                },
            ],
        }

    def test_filters_and_reorders_layers(self, sample_schema):
        """Filter schema to only specified layers in specified order."""
        layout = CompositionLayout(
            layers=[
                {"table": "public.parks"},
                {"table": "public.buildings"},
            ]
        )

        filtered = layout.filter_schema(sample_schema)
        assert filtered["layer_count"] == 2
        assert len(filtered["layers"]) == 2
        assert filtered["layers"][0]["table"] == "parks"
        assert filtered["layers"][1]["table"] == "buildings"

    def test_ignores_missing_layers(self, sample_schema, capsys):
        """Ignores layers in layout that don't exist in schema."""
        layout = CompositionLayout(
            layers=[
                {"table": "public.buildings"},
                {"table": "public.missing"},  # This doesn't exist
            ]
        )

        filtered = layout.filter_schema(sample_schema)
        assert filtered["layer_count"] == 1
        assert filtered["layers"][0]["table"] == "buildings"

        # Check warning was printed
        captured = capsys.readouterr()
        assert "missing" in captured.err

    def test_empty_layout_returns_empty_schema(self, sample_schema):
        """Layout with no layers returns empty schema."""
        layout = CompositionLayout()

        filtered = layout.filter_schema(sample_schema)
        assert filtered["layer_count"] == 0
        assert filtered["layers"] == []


class TestCompositionLayoutPerLayerOps:
    """Test CompositionLayout.per_layer_ops() operation extraction."""

    def test_returns_ops_dict(self):
        """Return dict of {qualified_name: [ops]}."""
        layout = CompositionLayout(
            layers=[
                {"table": "public.buildings", "operations": ["buffer", "dissolve"]},
                {"table": "public.streets", "operations": ["reproject"]},
                {"table": "public.parks"},  # No operations
            ]
        )

        ops = layout.per_layer_ops()
        assert ops["public.buildings"] == ["buffer", "dissolve"]
        assert ops["public.streets"] == ["reproject"]
        assert "public.parks" not in ops

    def test_single_operation_as_list(self):
        """Single operation is wrapped in a list."""
        layout = CompositionLayout(
            layers=[
                {"table": "public.test", "operations": "buffer"},
            ]
        )

        ops = layout.per_layer_ops()
        assert ops["public.test"] == ["buffer"]

    def test_infers_qualified_name_from_table(self):
        """Infer qualified_name if table has no dot."""
        layout = CompositionLayout(
            layers=[
                {"table": "buildings", "operations": ["buffer"]},
            ]
        )

        ops = layout.per_layer_ops()
        assert "public.buildings" in ops


# ---------------------------------------------------------------------------
# Generator integration tests
# ---------------------------------------------------------------------------

class TestGeneratorWithTemplate:
    """Test generate_pyqgis and generate_arcpy with template injection."""

    @pytest.fixture
    def sample_schema(self):
        """A minimal sample schema with one layer."""
        return {
            "database": "test_db",
            "host": "localhost",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [
                        {"name": "id", "data_type": "integer", "nullable": False},
                        {"name": "name", "data_type": "text", "nullable": True},
                    ],
                    "primary_keys": ["id"],
                    "row_count_estimate": 1000,
                }
            ],
        }

    @pytest.fixture
    def db_config(self):
        """A sample database config."""
        return {
            "host": "localhost",
            "port": 5432,
            "dbname": "test_db",
            "user": "postgres",
            "password": "secret",
        }

    def test_pyqgis_injects_preamble(self, sample_schema, db_config, tmp_path):
        """generate_pyqgis injects template preamble."""
        from gis_codegen.generator import generate_pyqgis

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[custom]
preamble = "CUSTOM_VAR = 42"
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_pyqgis(sample_schema, db_config, template=template)
        assert "CUSTOM_VAR = 42" in code

    def test_pyqgis_injects_extra_imports(self, sample_schema, db_config, tmp_path):
        """generate_pyqgis injects extra imports."""
        from gis_codegen.generator import generate_pyqgis

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[custom]
extra_imports = "import numpy as np"
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_pyqgis(sample_schema, db_config, template=template)
        assert "import numpy as np" in code

    def test_pyqgis_toggles_sample_rows(self, sample_schema, db_config, tmp_path):
        """generate_pyqgis respects include_sample_rows flag."""
        from gis_codegen.generator import generate_pyqgis

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[sections]
include_sample_rows = false
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_pyqgis(sample_schema, db_config, template=template)
        assert "Sample: iterate first 5 features" not in code

    def test_pyqgis_toggles_crs_info(self, sample_schema, db_config, tmp_path):
        """generate_pyqgis respects include_crs_info flag."""
        from gis_codegen.generator import generate_pyqgis

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[sections]
include_crs_info = false
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_pyqgis(sample_schema, db_config, template=template)
        assert "CRS" not in code or "crs.authid()" not in code

    def test_pyqgis_injects_per_layer_ops(self, sample_schema, db_config):
        """generate_pyqgis uses per_layer_ops instead of global ops."""
        from gis_codegen.generator import generate_pyqgis

        layout = CompositionLayout(
            layers=[
                {"table": "public.buildings", "operations": ["buffer", "dissolve"]},
            ]
        )
        per_layer_ops = layout.per_layer_ops()

        # With per_layer_ops, generate_pyqgis should include processing imports
        code = generate_pyqgis(sample_schema, db_config, operations=None, per_layer_ops=per_layer_ops)
        assert "from qgis import processing" in code

    def test_arcpy_injects_preamble(self, sample_schema, db_config, tmp_path):
        """generate_arcpy injects template preamble."""
        from gis_codegen.generator import generate_arcpy

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[custom]
preamble = "CUSTOM_VAR = 42"
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_arcpy(sample_schema, db_config, template=template)
        assert "CUSTOM_VAR = 42" in code

    def test_arcpy_toggles_sample_rows(self, sample_schema, db_config, tmp_path):
        """generate_arcpy respects include_sample_rows flag."""
        from gis_codegen.generator import generate_arcpy

        toml_file = tmp_path / "template.toml"
        toml_file.write_text(
            """
[sections]
include_sample_rows = false
"""
        )

        template = TemplateConfig.from_toml(str(toml_file))
        code = generate_arcpy(sample_schema, db_config, template=template)
        assert "Sample: iterate first 5 rows" not in code

    def test_per_layer_ops_falls_back_to_global(self, sample_schema, db_config):
        """generate_pyqgis falls back to global ops for unspecified layers."""
        from gis_codegen.generator import generate_pyqgis

        # Global ops = buffer, but per_layer_ops specifies dissolve
        per_layer_ops = {"public.buildings": ["dissolve"]}
        code = generate_pyqgis(sample_schema, db_config, operations=["buffer"], per_layer_ops=per_layer_ops)

        # Should have processing import because of per_layer_ops
        assert "from qgis import processing" in code


# ---------------------------------------------------------------------------
# MetadataOverlay tests
# ---------------------------------------------------------------------------

class TestMetadataOverlayFromToml:
    """Test MetadataOverlay.from_toml() loading."""

    def test_loads_layer_metadata(self, tmp_path):
        """Load metadata with description, owner, notes."""
        from gis_codegen.layout import MetadataOverlay

        toml_file = tmp_path / "metadata.toml"
        toml_file.write_text(
            """
[[layers]]
table = "buildings"
description = "Building footprints from aerial survey 2024"
owner = "GIS Team"
notes = "Source: City Open Data Portal"

[[layers]]
table = "public.streets"
description = "Centreline street network"
"""
        )

        overlay = MetadataOverlay.from_toml(str(toml_file))
        assert len(overlay.layers) == 2
        assert overlay.layers[0]["table"] == "buildings"
        assert overlay.layers[0]["description"] == "Building footprints from aerial survey 2024"
        assert overlay.layers[0]["owner"] == "GIS Team"
        assert overlay.layers[0]["notes"] == "Source: City Open Data Portal"
        assert overlay.layers[1]["table"] == "public.streets"

    def test_missing_file_exits(self, tmp_path):
        """from_toml exits if file not found."""
        from gis_codegen.layout import MetadataOverlay

        with pytest.raises(SystemExit):
            MetadataOverlay.from_toml(str(tmp_path / "nonexistent.toml"))

    def test_invalid_toml_exits(self, tmp_path):
        """from_toml exits on invalid TOML syntax."""
        from gis_codegen.layout import MetadataOverlay

        toml_file = tmp_path / "bad.toml"
        toml_file.write_text("[[layers] invalid syntax {")

        with pytest.raises(SystemExit):
            MetadataOverlay.from_toml(str(toml_file))

    def test_apply_merges_metadata(self, tmp_path):
        """apply() merges metadata into matching schema layers."""
        from gis_codegen.layout import MetadataOverlay

        toml_file = tmp_path / "metadata.toml"
        toml_file.write_text(
            """
[[layers]]
table = "buildings"
description = "Building footprints"
owner = "Team A"
"""
        )

        overlay = MetadataOverlay.from_toml(str(toml_file))
        schema = {
            "database": "test_db",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                }
            ],
        }

        new_schema = overlay.apply(schema)
        assert new_schema["layers"][0]["description"] == "Building footprints"
        assert new_schema["layers"][0]["owner"] == "Team A"
        assert new_schema != schema  # Non-destructive

    def test_apply_by_qualified_name(self, tmp_path):
        """apply() matches by qualified name."""
        from gis_codegen.layout import MetadataOverlay

        toml_file = tmp_path / "metadata.toml"
        toml_file.write_text(
            """
[[layers]]
table = "public.buildings"
description = "Qualified name match"
"""
        )

        overlay = MetadataOverlay.from_toml(str(toml_file))
        schema = {
            "database": "test_db",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                }
            ],
        }

        new_schema = overlay.apply(schema)
        assert new_schema["layers"][0]["description"] == "Qualified name match"

    def test_apply_skips_missing_layers(self, tmp_path):
        """apply() skips metadata for layers not in schema."""
        from gis_codegen.layout import MetadataOverlay

        toml_file = tmp_path / "metadata.toml"
        toml_file.write_text(
            """
[[layers]]
table = "missing"
description = "Not in schema"
"""
        )

        overlay = MetadataOverlay.from_toml(str(toml_file))
        schema = {
            "database": "test_db",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                }
            ],
        }

        new_schema = overlay.apply(schema)
        assert "description" not in new_schema["layers"][0]


# ---------------------------------------------------------------------------
# TemplateConfig inheritance tests
# ---------------------------------------------------------------------------

class TestTemplateConfigInheritance:
    """Test TemplateConfig template inheritance via extends."""

    def test_child_inherits_base_preamble(self, tmp_path):
        """Child template inherits preamble from base."""
        base_file = tmp_path / "base.toml"
        base_file.write_text(
            """
[custom]
preamble = "# Base preamble"
"""
        )

        child_file = tmp_path / "child.toml"
        child_file.write_text(
            """
extends = "base.toml"
name = "Child"
"""
        )

        cfg = TemplateConfig.from_toml(str(child_file))
        assert cfg.name == "Child"
        assert cfg.preamble == "# Base preamble"

    def test_child_overrides_base_preamble(self, tmp_path):
        """Child preamble overrides base preamble."""
        base_file = tmp_path / "base.toml"
        base_file.write_text(
            """
[custom]
preamble = "# Base preamble"
"""
        )

        child_file = tmp_path / "child.toml"
        child_file.write_text(
            """
extends = "base.toml"
[custom]
preamble = "# Child preamble"
"""
        )

        cfg = TemplateConfig.from_toml(str(child_file))
        assert cfg.preamble == "# Child preamble"

    def test_child_inherits_section_flags(self, tmp_path):
        """Child inherits section flags from base when not specified."""
        base_file = tmp_path / "base.toml"
        base_file.write_text(
            """
[sections]
include_sample_rows = false
include_crs_info = true
"""
        )

        child_file = tmp_path / "child.toml"
        child_file.write_text(
            """
extends = "base.toml"
[sections]
include_sample_rows = true
"""
        )

        cfg = TemplateConfig.from_toml(str(child_file))
        assert cfg.include_sample_rows is True  # overridden
        assert cfg.include_crs_info is True  # inherited

    def test_circular_inheritance_exits(self, tmp_path):
        """Circular template inheritance exits with error."""
        file_a = tmp_path / "a.toml"
        file_a.write_text('extends = "b.toml"')

        file_b = tmp_path / "b.toml"
        file_b.write_text('extends = "a.toml"')

        with pytest.raises(SystemExit):
            TemplateConfig.from_toml(str(file_a))

    def test_extends_resolves_relative_path(self, tmp_path):
        """extends path is relative to the child file."""
        subdir = tmp_path / "templates"
        subdir.mkdir()

        base_file = subdir / "base.toml"
        base_file.write_text(
            """
[custom]
preamble = "# From subdir"
"""
        )

        child_file = subdir / "child.toml"
        child_file.write_text('extends = "base.toml"')

        cfg = TemplateConfig.from_toml(str(child_file))
        assert cfg.preamble == "# From subdir"


# ---------------------------------------------------------------------------
# CompositionLayout attribute filtering tests
# ---------------------------------------------------------------------------

class TestCompositionLayoutAttributeFilters:
    """Test CompositionLayout smart attribute filtering."""

    @pytest.fixture
    def multi_layer_schema(self):
        """Schema with 5 diverse layers."""
        return {
            "database": "test_db",
            "layer_count": 5,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                    "row_count_estimate": 1000,
                },
                {
                    "schema": "public",
                    "table": "streets",
                    "qualified_name": "public.streets",
                    "geometry": {"type": "LINESTRING", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                    "row_count_estimate": 500,
                },
                {
                    "schema": "public",
                    "table": "parks",
                    "qualified_name": "public.parks",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                    "row_count_estimate": 50,
                },
                {
                    "schema": "admin",
                    "table": "boundaries",
                    "qualified_name": "admin.boundaries",
                    "geometry": {"type": "POLYGON", "srid": 2952, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                    "row_count_estimate": 10,
                },
                {
                    "schema": "public",
                    "table": "points",
                    "qualified_name": "public.points",
                    "geometry": {"type": "POINT", "srid": 4326, "column": "geom"},
                    "columns": [],
                    "primary_keys": ["id"],
                    "row_count_estimate": 10000,
                },
            ],
        }

    def test_filter_by_geom_types(self, multi_layer_schema):
        """Filter keeps only matching geometry types."""
        layout = CompositionLayout(filter_geom_types=["POLYGON"])
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 3
        assert filtered["layers"][0]["table"] == "buildings"
        assert filtered["layers"][1]["table"] == "parks"
        assert filtered["layers"][2]["table"] == "boundaries"

    def test_filter_by_srid(self, multi_layer_schema):
        """Filter keeps only matching SRID."""
        layout = CompositionLayout(filter_srid=2952)
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 1
        assert filtered["layers"][0]["table"] == "boundaries"

    def test_filter_by_min_rows(self, multi_layer_schema):
        """Filter keeps layers with row count >= min_rows."""
        layout = CompositionLayout(filter_min_rows=100)
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 4
        # parks (50) and boundaries (10) are excluded
        tables = [l["table"] for l in filtered["layers"]]
        assert "parks" not in tables
        assert "boundaries" not in tables

    def test_filter_by_max_rows(self, multi_layer_schema):
        """Filter keeps layers with row count <= max_rows."""
        layout = CompositionLayout(filter_max_rows=1000)
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 4
        # points (10000) is excluded
        tables = [l["table"] for l in filtered["layers"]]
        assert "points" not in tables

    def test_filter_by_schema(self, multi_layer_schema):
        """Filter keeps only layers in specified schemas."""
        layout = CompositionLayout(filter_schemas=["public"])
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 4
        assert filtered["layers"][0]["schema"] == "public"

    def test_filter_exclude_tables(self, multi_layer_schema):
        """Filter excludes specified tables by unqualified name."""
        layout = CompositionLayout(filter_exclude_tables=["parks", "points"])
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 3
        tables = [l["table"] for l in filtered["layers"]]
        assert "parks" not in tables
        assert "points" not in tables

    def test_filter_exclude_qualified_names(self, multi_layer_schema):
        """Filter excludes tables specified by qualified name."""
        layout = CompositionLayout(filter_exclude_tables=["admin.boundaries"])
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 4
        assert all(l["table"] != "boundaries" for l in filtered["layers"])

    def test_multiple_filters_combine_with_and(self, multi_layer_schema):
        """Multiple filters combine with AND semantics."""
        layout = CompositionLayout(
            filter_geom_types=["POLYGON"],
            filter_srid=4326,
            filter_min_rows=100
        )
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 2
        tables = [l["table"] for l in filtered["layers"]]
        assert "buildings" in tables
        assert "parks" not in tables  # excluded by min_rows

    def test_whitelist_and_filter_intersect(self, multi_layer_schema):
        """Whitelist and attribute filters apply to result."""
        layout = CompositionLayout(
            layers=[
                {"table": "buildings"},
                {"table": "streets"},
                {"table": "parks"},
            ],
            filter_min_rows=100
        )
        filtered = layout.filter_schema(multi_layer_schema)
        # Only buildings and streets meet min_rows=100
        assert filtered["layer_count"] == 2
        tables = [l["table"] for l in filtered["layers"]]
        assert "buildings" in tables
        assert "streets" in tables
        assert "parks" not in tables

    def test_no_filters_no_whitelist_returns_all(self, multi_layer_schema):
        """Layout with no filters or whitelist returns all layers."""
        layout = CompositionLayout()
        filtered = layout.filter_schema(multi_layer_schema)
        assert filtered["layer_count"] == 5


# ---------------------------------------------------------------------------
# Metadata + Generator integration tests
# ---------------------------------------------------------------------------

class TestMetadataInGeneratedCode:
    """Test that metadata is emitted in generated scripts."""

    @pytest.fixture
    def schema_with_metadata(self):
        """Schema with metadata fields populated."""
        return {
            "database": "test_db",
            "host": "localhost",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [
                        {"name": "id", "data_type": "integer", "nullable": False},
                    ],
                    "primary_keys": ["id"],
                    "row_count_estimate": 1000,
                    "description": "Building footprints",
                    "owner": "GIS Team",
                    "notes": "Updated monthly",
                }
            ],
        }

    @pytest.fixture
    def db_config(self):
        """Database config fixture."""
        return {
            "host": "localhost",
            "port": 5432,
            "dbname": "test_db",
            "user": "postgres",
            "password": "secret",
        }

    def test_pyqgis_emits_description(self, schema_with_metadata, db_config):
        """generate_pyqgis includes Description comment."""
        from gis_codegen.generator import generate_pyqgis

        code = generate_pyqgis(schema_with_metadata, db_config)
        assert "# Description: Building footprints" in code

    def test_pyqgis_emits_owner(self, schema_with_metadata, db_config):
        """generate_pyqgis includes Owner comment."""
        from gis_codegen.generator import generate_pyqgis

        code = generate_pyqgis(schema_with_metadata, db_config)
        assert "# Owner: GIS Team" in code

    def test_pyqgis_emits_notes(self, schema_with_metadata, db_config):
        """generate_pyqgis includes Notes comment."""
        from gis_codegen.generator import generate_pyqgis

        code = generate_pyqgis(schema_with_metadata, db_config)
        assert "# Notes: Updated monthly" in code

    def test_arcpy_emits_metadata(self, schema_with_metadata, db_config):
        """generate_arcpy includes metadata comments."""
        from gis_codegen.generator import generate_arcpy

        code = generate_arcpy(schema_with_metadata, db_config)
        assert "# Description: Building footprints" in code
        assert "# Owner: GIS Team" in code
        assert "# Notes: Updated monthly" in code

    def test_no_metadata_no_comments(self, db_config):
        """Script without metadata has no extra comments."""
        from gis_codegen.generator import generate_pyqgis

        schema = {
            "database": "test_db",
            "host": "localhost",
            "layer_count": 1,
            "layers": [
                {
                    "schema": "public",
                    "table": "buildings",
                    "qualified_name": "public.buildings",
                    "geometry": {"type": "POLYGON", "srid": 4326, "column": "geom"},
                    "columns": [
                        {"name": "id", "data_type": "integer", "nullable": False},
                    ],
                    "primary_keys": ["id"],
                    "row_count_estimate": 1000,
                }
            ],
        }

        code = generate_pyqgis(schema, db_config)
        assert "# Description:" not in code
        assert "# Owner:" not in code
        assert "# Notes:" not in code
