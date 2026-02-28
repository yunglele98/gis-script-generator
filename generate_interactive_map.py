import geopandas as gpd
import folium
import os

# Configuration
WORKING_DIR = r"02_WORKING\01_MTM10_STAGED_SHP"
OUTPUT_DIR = r"02_WORKING\03_MAP_OUTPUTS"
TARGET_CRS = "EPSG:4326"  # Required for Folium (Leaflet)

# Ensure output directory exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def generate_webmap():
    print("Generating Interactive Web Map...")
    
    try:
        # 1. Load Data (Bicycle Parking)
        bike_path = os.path.join(WORKING_DIR, "Bicycle Parking Map Data - 2952", "Bicycle Parking Map Data - 2952.shp")
        gdf_bike = gpd.read_file(bike_path)
        
        # 2. Reproject to WGS84 (Lat/Lon)
        gdf_bike_web = gdf_bike.to_crs(TARGET_CRS)
        
        # 3. Create Folium Map (Lat, Lon)
        # Calculate center from bounding box (faster than unioning all geometries)
        minx, miny, maxx, maxy = gdf_bike_web.total_bounds
        center_lat = (miny + maxy) / 2
        center_lon = (minx + maxx) / 2
        m = folium.Map(location=[center_lat, center_lon], zoom_start=15, tiles="CartoDB positron")
        
        # 4. Add Features
        folium.GeoJson(
            gdf_bike_web,
            name="Bicycle Parking",
            tooltip=folium.GeoJsonTooltip(fields=['ADDRESS_FU', 'STATUS'], aliases=['Address:', 'Status:']),
            marker=folium.CircleMarker(radius=5, color='green', fill=True, fill_color='green')
        ).add_to(m)
        
        # 5. Add Controls
        folium.LayerControl().add_to(m)
        
        # 6. Save HTML
        output_file = os.path.join(OUTPUT_DIR, "kensington_interactive_bikes.html")
        m.save(output_file)
        print(f"Map saved to: {output_file}")
        
    except Exception as e:
        print(f"Error generating web map: {e}")
        print("Ensure shapefiles exist in 02_WORKING/01_MTM10_STAGED_SHP")

if __name__ == "__main__":
    generate_webmap()
