import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import os

# Configuration
DB_PATH = r"02_WORKING\04_SQL_DATABASE\KENSINGTON_PROD.sqlite"
OUTPUT_HTML = r"02_WORKING\05_ANALYSIS_OUTPUTS\Kensington_Report.html"

def generate_report():
    print(f"Generating Business Intelligence Report: {OUTPUT_HTML}...")
    os.makedirs(os.path.dirname(OUTPUT_HTML), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    # --- Generate Chart: Bicycle Parking ---
    try:
        df_bikes = pd.read_sql_query("SELECT * FROM v_bicycle_parking_by_street LIMIT 10", conn)
        
        plt.figure(figsize=(10, 6))
        plt.bar(df_bikes['Street_Address'], df_bikes['Total_Spots'], color='#1f77b4')
        plt.title('Top 10 Streets for Bicycle Parking')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        # Save to Base64 String
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        bike_chart_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
    except Exception as e:
        print(f"  [WARN] Could not generate bike chart: {e}")
        bike_chart_b64 = ""

    # --- Generate Chart: Permits ---
    try:
        df_permits = pd.read_sql_query("SELECT * FROM v_permit_status_summary LIMIT 5", conn)
        
        plt.figure(figsize=(8, 8))
        plt.pie(df_permits['Count'], labels=df_permits['Permit_Type'], autopct='%1.1f%%', startangle=140)
        plt.title('Building Permit Distribution')
        plt.axis('equal')
        
        # Save to Base64 String
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        permit_chart_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
    except Exception as e:
        print(f"  [WARN] Could not generate permit chart: {e}")
        permit_chart_b64 = ""

    # --- Generate HTML ---
    html_content = f"""
    <html>
    <head>
        <title>Kensington GIS Intelligence Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f4f4f4; }}
            .container {{ max-width: 800px; margin: auto; background: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; }}
            h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 10px; }}
            .chart {{ text-align: center; margin-bottom: 40px; }}
            img {{ max-width: 100%; height: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Kensington Market Intelligence Report</h1>
            <p>Generated automatically from <strong>KENSINGTON_PROD.sqlite</strong>.</p>
            
            <h2>Bicycle Infrastructure Analysis</h2>
            <div class="chart">
                <img src="data:image/png;base64,{bike_chart_b64}" alt="Bicycle Parking Chart">
                <p>Top streets by bicycle parking capacity.</p>
            </div>

            <h2>Urban Development Analysis</h2>
            <div class="chart">
                <img src="data:image/png;base64,{permit_chart_b64}" alt="Permit Distribution Chart">
                <p>Breakdown of active building permit types.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    with open(OUTPUT_HTML, "w", encoding='utf-8') as f:
        f.write(html_content)
        
    conn.close()
    print("Report Generation Complete.")

if __name__ == "__main__":
    generate_report()
