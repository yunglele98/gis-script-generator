import sqlite3
import os

# Configuration
DB_PATH = r"02_WORKING\04_SQL_DATABASE\KENSINGTON_PROD.sqlite"

def create_views():
    print(f"Enhancing Database with Analytical Views: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # --- VIEW 1: Bicycle Parking Density ---
    # Insight: Which streets have the most bicycle parking?
    # Note: Requires 'bicycle_parking_map_data_2952' table to exist
    try:
        print("  Creating View: v_bicycle_parking_by_street")
        cursor.execute("DROP VIEW IF EXISTS v_bicycle_parking_by_street")
        cursor.execute("""
            CREATE VIEW v_bicycle_parking_by_street AS
            SELECT
                ADDRESS_FU as Street_Address,
                COUNT(*) as Total_Spots,
                STATUS as Condition
            FROM bicycle_parking_map_data_2952
            GROUP BY ADDRESS_FU
            ORDER BY Total_Spots DESC;
        """)
        print("    [OK] Created view.")
    except Exception as e:
        print(f"    [SKIP] Could not create bicycle view (Table missing?): {e}")

    # --- VIEW 2: Building Permit Status ---
    # Insight: What is the breakdown of active vs. completed permits?
    # Note: Requires 'attr_building_permits_active_permits' table
    try:
        print("  Creating View: v_permit_status_summary")
        cursor.execute("DROP VIEW IF EXISTS v_permit_status_summary")
        cursor.execute("""
            CREATE VIEW v_permit_status_summary AS
            SELECT 
                PERMIT_TYP as Permit_Type,
                COUNT(*) as Count
            FROM attr_building_permits_active_permits
            GROUP BY PERMIT_TYP
            ORDER BY Count DESC;
        """)
        print("    [OK] Created view.")
    except Exception as e:
        print(f"    [SKIP] Could not create permit view (Table missing?): {e}")

    conn.commit()
    conn.close()
    print("Database Enhancement Complete.")

if __name__ == "__main__":
    create_views()
