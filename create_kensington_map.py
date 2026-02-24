import folium
import geopandas as gpd
import os

# Configuration — update data_base_dir if source GeoJSON files are stored elsewhere
data_base_dir = r"01_SOURCE"
script_output_dir = r"02_WORKING\03_MAP_OUTPUTS"

os.makedirs(script_output_dir, exist_ok=True)

leisure_geojson_path = os.path.join(data_base_dir, 'leisure.geojson')
reseaucyclable_geojson_path = os.path.join(data_base_dir, 'reseaucyclable.geojson')

kensington_market_coords = (43.655, -79.400)

m = folium.Map(location=kensington_market_coords, zoom_start=15)

try:
    leisure_gdf = gpd.read_file(leisure_geojson_path)
    folium.GeoJson(
        leisure_gdf,
        name='Leisure Areas',
        tooltip=folium.GeoJsonTooltip(fields=['name', 'leisure']),
        style_function=lambda x: {
            'fillColor': '#80FF80',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.7
        }
    ).add_to(m)
    print(f"Added {leisure_geojson_path} to the map.")
except Exception as e:
    print(f"Could not load or add {leisure_geojson_path}: {e}")

try:
    reseaucyclable_gdf = gpd.read_file(reseaucyclable_geojson_path)
    folium.GeoJson(
        reseaucyclable_gdf,
        name='Bicycle Network',
        tooltip=folium.GeoJsonTooltip(fields=['name', 'type']),
        style_function=lambda x: {
            'color': 'blue',
            'weight': 3,
            'opacity': 0.7
        }
    ).add_to(m)
    print(f"Added {reseaucyclable_geojson_path} to the map.")
except Exception as e:
    print(f"Could not load or add {reseaucyclable_geojson_path}: {e}")

folium.LayerControl().add_to(m)

output_html_path = os.path.join(script_output_dir, 'kensington_map.html')
m.save(output_html_path)

print(f"Interactive map saved to {output_html_path}")
print(f"To view the map, open '{output_html_path}' in your web browser.")
