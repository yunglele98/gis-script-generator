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
