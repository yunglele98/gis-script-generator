"""
Layout system for template-based and composition-based script generation.

Two features:
1. TemplateConfig: TOML-based templates for custom code injection and section control
2. CompositionLayout: TOML-based layer selection with per-layer operation control
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path


def _load_toml_module():
    """Load tomllib (Python 3.11+) or tomli fallback."""
    try:
        import tomllib
        return tomllib
    except ImportError:
        pass
    try:
        import tomli as tomllib
        return tomllib
    except ImportError:
        return None


TOMLLIB = _load_toml_module()


@dataclass
class TemplateConfig:
    """Reusable script template configuration loaded from TOML."""

    name: str = ""
    preamble: str | None = None
    extra_imports: str | None = None
    per_layer_prefix: str | None = None
    per_layer_suffix: str | None = None
    teardown: str | None = None
    include_sample_rows: bool = True
    include_crs_info: bool = True
    include_field_list: bool = True

    @classmethod
    def from_toml(cls, path: str) -> "TemplateConfig":
        """Load template config from TOML file."""
        if TOMLLIB is None:
            print(
                "[ERROR] TOML support requires Python 3.11+ or 'tomli' package.\n"
                "        Install with: pip install tomli",
                file=sys.stderr,
            )
            sys.exit(1)

        p = Path(path)
        if not p.exists():
            print(f"[ERROR] Template file not found: {path}", file=sys.stderr)
            sys.exit(1)

        try:
            data = TOMLLIB.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] Invalid TOML in {path}: {e}", file=sys.stderr)
            sys.exit(1)

        # Top-level keys
        name = data.get("name", "")

        # [custom] section
        custom = data.get("custom", {})
        preamble = custom.get("preamble")
        extra_imports = custom.get("extra_imports")
        per_layer_prefix = custom.get("per_layer_prefix")
        per_layer_suffix = custom.get("per_layer_suffix")
        teardown = custom.get("teardown")

        # [sections] section (defaults to True if not specified)
        sections = data.get("sections", {})
        include_sample_rows = sections.get("include_sample_rows", True)
        include_crs_info = sections.get("include_crs_info", True)
        include_field_list = sections.get("include_field_list", True)

        return cls(
            name=name,
            preamble=preamble,
            extra_imports=extra_imports,
            per_layer_prefix=per_layer_prefix,
            per_layer_suffix=per_layer_suffix,
            teardown=teardown,
            include_sample_rows=include_sample_rows,
            include_crs_info=include_crs_info,
            include_field_list=include_field_list,
        )

    def substitute_placeholders(self, text: str, table: str, schema: str, qualified_name: str) -> str:
        """Substitute {table}, {schema}, {qualified_name} in text."""
        return (
            text.replace("{table}", table)
            .replace("{schema}", schema)
            .replace("{qualified_name}", qualified_name)
        )


@dataclass
class CompositionLayout:
    """Layer composition and per-layer operation config loaded from TOML."""

    name: str = ""
    platform: str | None = None
    output: str | None = None
    layers: list[dict] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: str) -> "CompositionLayout":
        """Load composition layout from TOML file."""
        if TOMLLIB is None:
            print(
                "[ERROR] TOML support requires Python 3.11+ or 'tomli' package.\n"
                "        Install with: pip install tomli",
                file=sys.stderr,
            )
            sys.exit(1)

        p = Path(path)
        if not p.exists():
            print(f"[ERROR] Layout file not found: {path}", file=sys.stderr)
            sys.exit(1)

        try:
            data = TOMLLIB.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] Invalid TOML in {path}: {e}", file=sys.stderr)
            sys.exit(1)

        name = data.get("name", "")
        platform = data.get("platform")
        output = data.get("output")
        layers = data.get("layers", [])

        return cls(name=name, platform=platform, output=output, layers=layers)

    def filter_schema(self, schema: dict) -> dict:
        """Return a new schema dict with only layout-specified layers in order."""
        if not self.layers:
            return {**schema, "layers": [], "layer_count": 0}

        # Build a lookup for fast access
        layers_by_table = {layer["table"]: layer for layer in schema.get("layers", [])}

        # Keep only specified layers in specified order
        filtered_layers = []
        for layer_spec in self.layers:
            table = layer_spec.get("table")
            if table in layers_by_table:
                filtered_layers.append(layers_by_table[table])
            else:
                print(
                    f"[WARN] Layout specifies layer {table} but it is not in the schema",
                    file=sys.stderr,
                )

        return {**schema, "layers": filtered_layers, "layer_count": len(filtered_layers)}

    def per_layer_ops(self) -> dict[str, list[str]]:
        """Return {qualified_name: ops} for layers that specify operations."""
        ops_map = {}
        for layer_spec in self.layers:
            ops = layer_spec.get("operations")
            if ops:
                # Infer qualified_name from table (assume public schema if not explicit)
                table = layer_spec.get("table", "")
                if "." in table:
                    qualified_name = table
                else:
                    qualified_name = f"public.{table}"
                ops_map[qualified_name] = ops if isinstance(ops, list) else [ops]
        return ops_map
