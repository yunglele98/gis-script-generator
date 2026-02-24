import arcpy
import os

# Configuration
GDB_PATH = r"02_WORKING\Project_GDBs"
GDB_NAME = "KENSINGTON_MASTER.gdb"
DATASET_NAME = "MTM10_Production"
SR_CODE = 2952  # NAD83 / Ontario MTM zone 10

def initialize_master_gdb():
    print(f"Initializing Master GDB: {GDB_NAME}...")
    full_gdb_path = os.path.join(GDB_PATH, GDB_NAME)
    
    # 1. Create File GDB if it doesn't exist
    if not arcpy.Exists(full_gdb_path):
        arcpy.management.CreateFileGDB(GDB_PATH, GDB_NAME)
        print(f"  [OK] Created {GDB_NAME}")
    else:
        print(f"  [INFO] {GDB_NAME} already exists.")

    # 2. Create Feature Dataset with MTM10 Spatial Reference
    sr = arcpy.SpatialReference(SR_CODE)
    dataset_path = os.path.join(full_gdb_path, DATASET_NAME)
    
    if not arcpy.Exists(dataset_path):
        arcpy.management.CreateFeatureDataset(full_gdb_path, DATASET_NAME, sr)
        print(f"  [OK] Created Feature Dataset: {DATASET_NAME} (EPSG:{SR_CODE})")
    else:
        print(f"  [INFO] {DATASET_NAME} already exists.")

if __name__ == "__main__":
    initialize_master_gdb()
