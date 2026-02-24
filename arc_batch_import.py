import arcpy
import os
import glob

# Configuration
SOURCE_DIR = r"01_SOURCE"
TARGET_GDB = r"02_WORKING\Project_GDBs\KENSINGTON_MASTER.gdb"
TARGET_DATASET = "MTM10_Production"
TARGET_SR_CODE = 2952

def batch_import_and_project():
    print(f"Starting Batch Import into {TARGET_GDB}...")
    arcpy.env.overwriteOutput = True
    
    # 1. Target Spatial Reference
    target_sr = arcpy.SpatialReference(TARGET_SR_CODE)
    target_path = os.path.join(TARGET_GDB, TARGET_DATASET)
    
    # 2. Find all shapefiles in Source
    shp_files = glob.glob(os.path.join(SOURCE_DIR, "**", "*.shp"), recursive=True)
    
    for shp in shp_files:
        try:
            # Clean name for GDB (no spaces/hyphens)
            base_name = os.path.splitext(os.path.basename(shp))[0]
            clean_name = arcpy.ValidateTableName(base_name, TARGET_GDB)
            output_path = os.path.join(target_path, clean_name)
            
            # Check source SR
            source_sr = arcpy.Describe(shp).spatialReference
            
            if source_sr.factoryCode == TARGET_SR_CODE:
                print(f"  [IMPORT] {clean_name} (Native MTM10)")
                arcpy.management.CopyFeatures(shp, output_path)
            else:
                print(f"  [PROJECT] {clean_name} (WGS84 -> MTM10)")
                arcpy.management.Project(shp, output_path, target_sr)
            
            print(f"    [OK] Imported to {TARGET_DATASET}")
            
        except Exception as e:
            print(f"    [FAILED] {shp}: {e}")

if __name__ == "__main__":
    batch_import_and_project()
