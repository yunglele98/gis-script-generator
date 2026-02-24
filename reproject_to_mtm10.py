import geopandas as gpd
import os
import glob

# Configuration
SOURCE_DIR = r"01_SOURCE"
WORKING_DIR = r"02_WORKING\01_MTM10_STAGED_SHP"
TARGET_CRS = "EPSG:2952"

def reproject_all():
    print(f"Starting Batch Reprojection to {TARGET_CRS}...")
    os.makedirs(WORKING_DIR, exist_ok=True)

    # Find all shapefiles and geojson in Source
    files = []
    for ext in ['*.shp', '*.geojson']:
        files.extend(glob.glob(os.path.join(SOURCE_DIR, '**', ext), recursive=True))

    for file_path in files:
        try:
            print(f"Processing: {os.path.basename(file_path)}")
            gdf = gpd.read_file(file_path)

            # Skip files already in the target CRS
            if gdf.crs and gdf.crs.to_epsg() == 2952:
                print(f"  [SKIP] Already in {TARGET_CRS}")
                continue
            
            # Reproject
            gdf_projected = gdf.to_crs(TARGET_CRS)
            
            # Save to Working Directory
            file_name = os.path.basename(file_path)
            # Replace extension to ensure consistency
            base_name = os.path.splitext(file_name)[0]
            output_name = f"{base_name}_MTM10.shp"
            
            output_path = os.path.join(WORKING_DIR, output_name)
            gdf_projected.to_file(output_path)
            print(f"  [SUCCESS] -> {output_name}")
            
        except Exception as e:
            print(f"  [FAILED] {file_path}: {e}")

if __name__ == "__main__":
    reproject_all()
