import geopandas as gpd
import matplotlib.pyplot as plt
import os

# Configuration
WORKING_DIR = r"02_WORKING\01_MTM10_STAGED_SHP"
OUTPUT_DIR = r"02_WORKING\03_MAP_OUTPUTS"

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_map():
    print("Generating Static Map...")
    
    # 1. Load Data (MTM10 Projected)
    # Adjust paths based on your actual shapefile names inside the folders
    # Example: specific shapefile inside the folder
    try:
        roads_path = os.path.join(WORKING_DIR, "Edge_of_Roadway_EPSG2952", "Edge of Roadway - 2952.shp")
        sidewalks_path = os.path.join(WORKING_DIR, "Sidewalks_EPSG2952", "Sidewalks - 2952.shp")
        
        gdf_roads = gpd.read_file(roads_path)
        gdf_sidewalks = gpd.read_file(sidewalks_path)
        
        # 2. Setup Plot
        fig, ax = plt.subplots(figsize=(12, 12))
        
        # 3. Plot Layers
        gdf_roads.plot(ax=ax, color='gray', linewidth=0.5, label='Road Edges')
        gdf_sidewalks.plot(ax=ax, color='orange', alpha=0.6, label='Sidewalks')
        
        # 4. Styling
        ax.set_title("Kensington Market Infrastructure (MTM Zone 10)", fontsize=16)
        ax.set_axis_off()
        plt.legend()
        
        # 5. Save Output
        output_file = os.path.join(OUTPUT_DIR, "kensington_static_infrastructure.png")
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"Map saved to: {output_file}")
        
    except Exception as e:
        print(f"Error generating map: {e}")
        print("Ensure shapefiles exist in 02_WORKING/01_MTM10_STAGED_SHP")

if __name__ == "__main__":
    generate_map()
