"""
gis_codegen — generate PyQGIS / ArcPy scripts from a PostGIS database.
"""

from gis_codegen.extractor import connect, extract_schema
from gis_codegen.generator import generate_pyqgis, generate_arcpy

__version__ = "0.1.0"
__all__ = ["connect", "extract_schema", "generate_pyqgis", "generate_arcpy"]
