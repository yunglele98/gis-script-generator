from qgis.core import QgsProject, QgsVectorLayer, QgsCoordinateReferenceSystem
import os

# Configuration (Relative to Project Root)
DB_PATH = r"02_WORKING\04_SQL_DATABASE\KENSINGTON_PROD.sqlite"
STYLE_DIR = r"03_RESOURCES\Tools_Installers\qgis_automation\styles"
TARGET_CRS = "EPSG:2952"

def setup_qgis_project():
    print("Starting QGIS Project Automation...")
    project = QgsProject.instance()
    
    # 1. Set Project CRS
    crs = QgsCoordinateReferenceSystem(TARGET_CRS)
    project.setCrs(crs)
    print(f"  [OK] Set Project CRS to: {TARGET_CRS}")

    # 2. Database Tables to Load (Table Name, Style Name)
    layers_to_load = [
        ("buildings_mtm10", "buildings.qml"),
        ("roads_mtm10", "roads.qml")
    ]

    for table_name, style_name in layers_to_load:
        try:
            # Construct Data Source (SpatiaLite)
            uri = f"dbname='{DB_PATH}' table='{table_name}'(geometry) sql="
            layer = QgsVectorLayer(uri, table_name, "spatialite")
            
            if not layer.isValid():
                print(f"  [FAILED] Layer {table_name} is not valid. (Ensure SQL DB is populated)")
                continue
            
            # Apply Style
            style_path = os.path.join(STYLE_DIR, style_name)
            if os.path.exists(style_path):
                layer.loadNamedStyle(style_path)
                print(f"  [OK] Applied style: {style_name} to {table_name}")
            
            # Add to Project
            project.addMapLayer(layer)
            print(f"  [OK] Added layer: {table_name}")
            
        except Exception as e:
            print(f"  [ERROR] Loading {table_name}: {e}")

if __name__ == "__main__":
    setup_qgis_project()
