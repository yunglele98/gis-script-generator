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
    def from_toml(cls, path: str, _seen: frozenset[str] = frozenset()) -> "TemplateConfig":
        """Load template config from TOML file, supporting inheritance via 'extends'."""
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

        # Circular inheritance detection
        abs_path = str(p.resolve())
        if abs_path in _seen:
            print(
                f"[ERROR] Circular template inheritance detected at {path}",
                file=sys.stderr,
            )
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

        # [sections] section
        sections = data.get("sections", {})

        # Check for inheritance
        extends_str = data.get("extends")
        if extends_str:
            base_path = str(p.parent / extends_str)
            base = cls.from_toml(base_path, _seen=_seen | {abs_path})

            # Child overrides base; missing child fields inherit from base
            return cls(
                name=name or base.name,
                preamble=preamble if preamble is not None else base.preamble,
                extra_imports=extra_imports if extra_imports is not None else base.extra_imports,
                per_layer_prefix=per_layer_prefix if per_layer_prefix is not None else base.per_layer_prefix,
                per_layer_suffix=per_layer_suffix if per_layer_suffix is not None else base.per_layer_suffix,
                teardown=teardown if teardown is not None else base.teardown,
                include_sample_rows=sections.get("include_sample_rows", base.include_sample_rows),
                include_crs_info=sections.get("include_crs_info", base.include_crs_info),
                include_field_list=sections.get("include_field_list", base.include_field_list),
            )

        # No inheritance: use defaults
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
    filter_geom_types: list[str] | None = None
    filter_srid: int | None = None
    filter_min_rows: int | None = None
    filter_max_rows: int | None = None
    filter_schemas: list[str] | None = None
    filter_exclude_tables: list[str] | None = None

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

        # [filter] section
        filter_opts = data.get("filter", {})
        filter_geom_types = filter_opts.get("geom_types")
        filter_srid = filter_opts.get("srid")
        filter_min_rows = filter_opts.get("min_rows")
        filter_max_rows = filter_opts.get("max_rows")
        filter_schemas = filter_opts.get("schemas")
        filter_exclude_tables = filter_opts.get("exclude_tables")

        return cls(
            name=name,
            platform=platform,
            output=output,
            layers=layers,
            filter_geom_types=filter_geom_types,
            filter_srid=filter_srid,
            filter_min_rows=filter_min_rows,
            filter_max_rows=filter_max_rows,
            filter_schemas=filter_schemas,
            filter_exclude_tables=filter_exclude_tables,
        )

    def _apply_attribute_filters(self, layers: list[dict]) -> list[dict]:
        """Filter layers by geometry type, SRID, row count, schema, or exclusion list."""
        result = []
        exclude_set = set(self.filter_exclude_tables or [])

        for layer in layers:
            # Check geometry type filter
            if self.filter_geom_types:
                geom_type = layer.get("geometry", {}).get("type", "").upper()
                if geom_type not in [g.upper() for g in self.filter_geom_types]:
                    continue

            # Check SRID filter
            if self.filter_srid is not None:
                srid = layer.get("geometry", {}).get("srid")
                if srid != self.filter_srid:
                    continue

            # Check row count filters
            row_count = layer.get("row_count_estimate", -1)
            if self.filter_min_rows is not None and row_count >= 0:
                if row_count < self.filter_min_rows:
                    continue
            if self.filter_max_rows is not None and row_count >= 0:
                if row_count > self.filter_max_rows:
                    continue

            # Check schema filter
            if self.filter_schemas:
                if layer.get("schema") not in self.filter_schemas:
                    continue

            # Check exclusion list (both table and qualified_name)
            table = layer.get("table")
            qualified_name = layer.get("qualified_name")
            if table in exclude_set or qualified_name in exclude_set:
                continue

            result.append(layer)

        return result

    def filter_schema(self, schema: dict) -> dict:
        """Return a new schema dict with only layout-specified layers in order."""
        # Apply attribute filters first
        filtered_by_attrs = self._apply_attribute_filters(schema.get("layers", []))

        # If no whitelist is specified, use attribute-filtered result
        if not self.layers:
            return {**schema, "layers": filtered_by_attrs, "layer_count": len(filtered_by_attrs)}

        # Build dual-key lookup: both unqualified and qualified names
        layers_by_name = {}
        for layer in filtered_by_attrs:
            table = layer["table"]
            qualified_name = layer.get("qualified_name", table)
            layers_by_name[table] = layer
            layers_by_name[qualified_name] = layer

        # Keep only whitelist-specified layers in specified order
        filtered_layers = []
        for layer_spec in self.layers:
            table = layer_spec.get("table")
            layer = layers_by_name.get(table)
            if layer:
                filtered_layers.append(layer)
            else:
                print(
                    f"[WARN] Layout specifies layer {table} but it is not in the (filtered) schema",
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


@dataclass
class MetadataOverlay:
    """Layer metadata enrichment loaded from TOML (description, owner, notes, etc.)."""

    layers: list[dict] = field(default_factory=list)

    @classmethod
    def from_toml(cls, path: str) -> "MetadataOverlay":
        """Load metadata overlay from TOML file."""
        if TOMLLIB is None:
            print(
                "[ERROR] TOML support requires Python 3.11+ or 'tomli' package.\n"
                "        Install with: pip install tomli",
                file=sys.stderr,
            )
            sys.exit(1)

        p = Path(path)
        if not p.exists():
            print(f"[ERROR] Metadata file not found: {path}", file=sys.stderr)
            sys.exit(1)

        try:
            data = TOMLLIB.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[ERROR] Invalid TOML in {path}: {e}", file=sys.stderr)
            sys.exit(1)

        layers = data.get("layers", [])
        return cls(layers=layers)

    def apply(self, schema: dict) -> dict:
        """Return a new schema with metadata merged into matching layers."""
        if not self.layers:
            return schema

        # Build dual-key lookup: both unqualified and qualified names
        metadata_by_name = {}
        for meta_spec in self.layers:
            table = meta_spec.get("table", "")
            if table:
                metadata_by_name[table] = meta_spec
                # Also add qualified version (infer public schema if not explicit)
                if "." not in table:
                    metadata_by_name[f"public.{table}"] = meta_spec
                else:
                    metadata_by_name[table] = meta_spec

        # Create a new schema with metadata merged into layers
        new_schema = {**schema}
        new_layers = []
        for layer in schema.get("layers", []):
            table = layer["table"]
            qualified_name = layer.get("qualified_name", table)

            # Merge metadata if found
            new_layer = {**layer}
            meta = metadata_by_name.get(qualified_name) or metadata_by_name.get(table)
            if meta:
                # Merge all extra fields from metadata (except 'table' key)
                for key, value in meta.items():
                    if key != "table" and value is not None:
                        new_layer[key] = value

            new_layers.append(new_layer)

        new_schema["layers"] = new_layers
        return new_schema
