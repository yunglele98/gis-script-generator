import arcpy
import os

# Configuration
GDB_PATH = r"02_WORKING\Project_GDBs\KENSINGTON_MASTER.gdb"
DATASET_NAME = "MTM10_Production"
TOPOLOGY_NAME = "Kensington_Topology"

def build_topology():
    print(f"Building Topology: {TOPOLOGY_NAME}...")
    arcpy.env.overwriteOutput = True
    
    dataset_path = os.path.join(GDB_PATH, DATASET_NAME)
    topo_path = os.path.join(dataset_path, TOPOLOGY_NAME)
    
    # 1. Create Topology if it doesn't exist
    if not arcpy.Exists(topo_path):
        arcpy.management.CreateTopology(dataset_path, TOPOLOGY_NAME)
        print(f"  [OK] Created Topology: {TOPOLOGY_NAME}")
    else:
        print(f"  [INFO] {TOPOLOGY_NAME} already exists.")

    # 2. Add Feature Classes to Topology (Example: Buildings)
    # Check if 'buildings' exists (after running batch_import)
    try:
        buildings = os.path.join(dataset_path, "buildings")
        roads = os.path.join(dataset_path, "roads")
        
        if arcpy.Exists(buildings):
            print("  [OK] Adding Buildings to Topology...")
            arcpy.management.AddFeatureClassToTopology(topo_path, buildings, 1, 1)
            # Rule: Buildings Must Not Overlap
            arcpy.management.AddRuleToTopology(topo_path, "Must Not Overlap (Area)", buildings)
            print("    [RULE] Added: Must Not Overlap (Buildings)")
            
        if arcpy.Exists(roads):
            print("  [OK] Adding Roads to Topology...")
            arcpy.management.AddFeatureClassToTopology(topo_path, roads, 1, 1)
            # Rule: Roads Must Not Have Dangles
            arcpy.management.AddRuleToTopology(topo_path, "Must Not Have Dangles (Line)", roads)
            print("    [RULE] Added: Must Not Have Dangles (Roads)")
            
    except Exception as e:
        print(f"  [FAILED] {e}")

if __name__ == "__main__":
    build_topology()
