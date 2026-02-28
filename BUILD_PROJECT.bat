@echo off
echo ===================================================
echo   KENSINGTON GIS MASTER BUILD SYSTEM
echo   Target CRS: MTM Zone 10 (EPSG:2952)
echo ===================================================

echo [STEP 1] Batch Reprojection (WGS84 -> MTM10)...
python reproject_to_mtm10.py
if %ERRORLEVEL% NEQ 0 ( echo [ERROR] Reprojection Failed. & pause & exit /b )

echo [STEP 2] Database Migration (SHP/CSV -> SQL)...
python migrate_to_sql.py
if %ERRORLEVEL% NEQ 0 ( echo [ERROR] DB Migration Failed. & pause & exit /b )

echo [STEP 3] Business Intelligence (Creating Views)...
python create_analytical_views.py

echo [STEP 4] Generating Intelligence Report...
python generate_dashboard.py

echo ===================================================
echo   BUILD COMPLETE!
echo   Output: 02_WORKING\05_ANALYSIS_OUTPUTS\Kensington_Report.html
echo ===================================================
pause
