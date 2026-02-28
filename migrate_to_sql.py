import geopandas as gpd
import pandas as pd
import sqlite3
import os
import glob

# Configuration
WORKING_SHP = r"02_WORKING\01_MTM10_STAGED_SHP"
SOURCE_DIR = r"01_SOURCE"
SQL_DB_PATH = r"02_WORKING\04_SQL_DATABASE\KENSINGTON_PROD.sqlite"

def migrate_data():
    print(f"Initializing SQL Migration to: {SQL_DB_PATH}...")
    os.makedirs(os.path.dirname(SQL_DB_PATH), exist_ok=True)

    # 1. Connect to SQLite
    conn = sqlite3.connect(SQL_DB_PATH)
    
    # --- PHASE 1: Import Spatial Layers (Shapefiles) ---
    print("\nPhase 1: Importing Spatial Layers...")
    shp_files = glob.glob(os.path.join(WORKING_SHP, "**", "*.shp"), recursive=True)
    
    for shp in shp_files:
        try:
            table_name = os.path.splitext(os.path.basename(shp))[0].replace(" ", "_").replace("-", "_").lower()
            print(f"  Importing spatial table: {table_name}")
            gdf = gpd.read_file(shp)
            # We convert geometry to WKT (Well-Known Text) for a simpler SQLite import 
            # Or use SpatiaLite format if available
            gdf['geometry_wkt'] = gdf.geometry.apply(lambda x: x.wkt if x is not None else None)
            df_for_sql = pd.DataFrame(gdf.drop(columns='geometry'))
            df_for_sql.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"    [OK] {len(gdf)} records imported.")
        except Exception as e:
            print(f"    [FAILED] {shp}: {e}")

    # --- PHASE 2: Import Attribute Data (CSVs) ---
    print("\nPhase 2: Importing Attribute CSVs...")
    csv_files = glob.glob(os.path.join(SOURCE_DIR, "**", "*.csv"), recursive=True)
    
    for csv in csv_files:
        try:
            table_name = "attr_" + os.path.splitext(os.path.basename(csv))[0].replace(" ", "_").replace("-", "_").lower()
            print(f"  Importing attribute table: {table_name}")
            df = pd.read_csv(csv, low_memory=False)
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            print(f"    [OK] {len(df)} records imported.")
        except Exception as e:
            print(f"    [FAILED] {csv}: {e}")

    conn.commit()
    conn.close()
    print("\nMigration Complete.")

if __name__ == "__main__":
    migrate_data()
