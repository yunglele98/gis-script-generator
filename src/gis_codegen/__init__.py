"""
gis_codegen — generate PyQGIS / ArcPy scripts from a PostGIS database.
"""

from gis_codegen.extractor import connect, extract_schema
from gis_codegen.generator import (
    generate_pyqgis, generate_arcpy,
    generate_qgs, generate_pyt,
    generate_blender,
)
from gis_codegen.layout import TemplateConfig, CompositionLayout, MetadataOverlay

__version__ = "0.1.0"
__all__ = [
    "connect", "extract_schema",
    "generate_pyqgis", "generate_arcpy",
    "generate_qgs", "generate_pyt", "generate_blender",
    "TemplateConfig", "CompositionLayout", "MetadataOverlay",
]
