# Blender Agent Prompts for gis-codegen

Six agent prompts for integrating Blender script generation into the gis-codegen
generator package. Prompt 1 is the foundation — implement it first. Prompts 2–6
are independent operations that can be built in parallel after.

| # | Feature | Type | What it generates |
|---|---------|------|-------------------|
| 1 | `blender` platform | New platform | PostGIS→Blender mesh import script |
| 2 | `blender_pbr` | Operation | PBR materials based on geometry/table type |
| 3 | `blender_render` | Operation | Cycles camera, lighting, render config |
| 4 | `blender_extrude` | Operation | 3D building extrusion from height attributes |
| 5 | `blender_procedural` | Operation | Trees, furniture, lights along features |
| 6 | `blender_export` | Operation | Multi-format export (glTF, FBX, OBJ, USD) |

---

## Prompt 1: `blender` Platform — PostGIS→Blender Scene Import Script

```
You are adding a new "blender" platform to the gis-codegen generator package at
src/gis_codegen/generator.py.

GOAL: Implement generate_blender(schema, ops=None) that produces a standalone
Blender Python script (.py) which imports PostGIS layers as 3D meshes.

ARCHITECTURE (follow existing patterns exactly):
- Read generator.py to understand the dispatch pattern used by generate_pyqgis,
  generate_arcpy, etc.
- Add "blender" to the PLATFORMS list and VALID_OPERATIONS where appropriate.
- Register generate_blender in __init__.py's public API.
- Update cli.py's platform choices and app.py's _PLATFORMS list.

GENERATED SCRIPT REQUIREMENTS:
The output .py script should:
1. Import bpy, bmesh, mathutils
2. Clear the default Blender scene (delete cube, camera, light)
3. For each layer in schema["layers"]:
   a. Connect to PostGIS using psycopg2 (connection params from schema)
   b. Query: SELECT ST_AsText(geom), {columns} FROM {qualified_name}
   c. Parse WKT geometries into Blender mesh vertices/faces:
      - POINT/MULTIPOINT → ico sphere at coordinates
      - LINESTRING/MULTILINESTRING → curve object with bevel
      - POLYGON/MULTIPOLYGON → extruded flat mesh (z=0 by default)
   d. Create a Blender collection named "{schema}.{table}"
   e. Assign a default material with a distinct color per layer
4. Set up an orthographic camera looking down at the data extent
5. Add a sun lamp for basic lighting
6. Print summary: layers imported, vertex counts

COORDINATE HANDLING:
- If SRID != 4326, note in comments that coordinates are in projected meters
- Normalize coordinates to scene center (subtract centroid of bounding box)
- Store the centroid offset as a custom property on the scene for reference

USE safe_var() for all Python variable names derived from table names.
USE the schema's geometry.type to choose the correct import strategy.

TESTS: Add TestGenerateBlender to tests/test_generator.py following the pattern
of TestGeneratePyqgis. Test: function exists, returns string, contains "import bpy",
contains collection creation for each layer, handles empty layers list, uses
safe_var for table names. Minimum 12 tests.

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
All tests must pass and coverage must stay ≥80%.
```

---

## Prompt 2: `blender_pbr` Operation — PBR Material Assignment

```
You are adding a "blender_pbr" operation to the gis-codegen generator for the
blender platform at src/gis_codegen/generator.py.

PREREQUISITE: The "blender" platform must already exist (generate_blender).
Read generator.py to understand the operation dispatch pattern (_PYQGIS_OPS,
_ARCPY_OPS, _op_blocks). You will create _BLENDER_OPS following the same pattern.

GOAL: When --op blender_pbr is passed, the generated Blender script adds PBR
(Physically Based Rendering) materials to each imported layer based on its
geometry type and table name.

GENERATED CODE SHOULD:
1. Create a Principled BSDF shader node graph for each layer's material
2. Map geometry types to sensible PBR defaults:
   - POLYGON/MULTIPOLYGON (buildings): Base Color=#C8B496, Roughness=0.7,
     Specular=0.3 (concrete/stone look)
   - POLYGON (parcels/lots): Base Color=#4A7C59, Roughness=0.9 (grass/ground)
   - LINESTRING (roads): Base Color=#3D3D3D, Roughness=0.5, Specular=0.4 (asphalt)
   - LINESTRING (water/rivers): Base Color=#2E5A88, Roughness=0.1, Specular=0.8,
     Transmission=0.3 (water)
   - POINT: Base Color=#CC4444, Metallic=0.8, Roughness=0.3 (marker pins)
3. Use keyword matching on table names to refine material choice:
   - "building", "structure" → concrete PBR
   - "road", "street", "path" → asphalt PBR
   - "water", "river", "lake" → water PBR
   - "park", "green", "tree" → vegetation PBR
   - "parcel", "lot", "land" → ground PBR
4. Set up the node tree programmatically:
   mat = bpy.data.materials.new(name=f"{table}_material")
   mat.use_nodes = True
   bsdf = mat.node_tree.nodes["Principled BSDF"]
   bsdf.inputs["Base Color"].default_value = (r, g, b, 1.0)
   # etc.

Add "blender_pbr" to VALID_OPERATIONS. Register the op function in _BLENDER_OPS.

TESTS: Add tests to test_generator.py:
- Op block contains "Principled BSDF"
- Op block contains material creation
- Building-like table names get concrete colors
- Road-like table names get asphalt colors
- Default fallback material exists
Minimum 8 tests.

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
```

---

## Prompt 3: `blender_render` Operation — Camera + Cycles Render Setup

```
You are adding a "blender_render" operation to the gis-codegen blender platform
at src/gis_codegen/generator.py.

Read generator.py to understand the existing operation dispatch pattern.

GOAL: When --op blender_render is passed, the generated script configures a
production-quality Cycles render setup based on the imported GIS data extent.

GENERATED CODE SHOULD:

1. CAMERA SETUP:
   - Calculate bounding box of all imported geometry
   - Place camera at 45° angle looking at centroid, distance = 1.5× bbox diagonal
   - Set as perspective camera, focal length 50mm
   - Add a second orthographic top-down camera as alternate
   - Create camera markers for both positions

2. LIGHTING:
   - Sun lamp: elevation 45°, azimuth 135° (afternoon light), strength 3.0
   - HDRI environment: set up nodes for .hdr file loading (path as variable at
     top of script, defaulting to a placeholder with comment to set path)
   - Ambient occlusion enabled

3. RENDER SETTINGS:
   - Engine: Cycles (GPU if available, CPU fallback)
   - Resolution: 1920×1080
   - Samples: 128 (preview), 512 (final)
   - Denoising enabled (OpenImageDenoise)
   - Output path: /tmp/{database}_render.png (configurable variable at top)
   - Film transparent background option (commented out, easy to enable)

4. COMPOSITING:
   - Enable compositing nodes
   - Add Glare node (fog glow, threshold 0.8) for atmospheric effect
   - Add Color Balance node for slight warm tint

The op function signature follows the pattern: _bl_render(var, table, first_col)
but the render setup is per-scene not per-layer, so generate it once (use a
_render_setup_emitted flag pattern or emit it only for the first layer).

TESTS: Minimum 8 tests:
- Contains "bpy.context.scene.render.engine = 'CYCLES'"
- Contains camera creation
- Contains sun lamp
- Contains denoising setting
- Contains resolution settings
- Contains compositing nodes
- Output path uses database name from schema
- GPU preference with CPU fallback

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
```

---

## Prompt 4: `blender_extrude` Operation — 3D Building Extrusion from Attributes

```
You are adding a "blender_extrude" operation to the gis-codegen blender platform
at src/gis_codegen/generator.py.

Read generator.py to understand the operation dispatch and how columns are
accessed from the schema dict.

GOAL: When --op blender_extrude is passed, the generated script extrudes polygon
layers into 3D based on height attributes found in the schema columns.

GENERATED CODE SHOULD:

1. HEIGHT COLUMN DETECTION (in priority order):
   - Look for columns named: "height", "building_height", "max_height",
     "elevation", "z", "stories", "num_floors", "floors"
   - If "stories"/"num_floors"/"floors" found: multiply by 3.0 (meters per floor)
   - If no height column found: use default extrusion of 5.0 meters
   - Comment in generated code explains the detection logic

2. PER-FEATURE EXTRUSION:
   For each polygon feature:
   a. Create mesh from WKT polygon vertices
   b. Enter edit mode via bmesh
   c. Select all faces
   d. bmesh.ops.extrude_face_region() + translate by height value
   e. Exit edit mode
   f. Set origin to geometry center

3. FLOOR SLICING (bonus detail):
   - If stories column exists, add edge loops at each floor height
   - This allows per-floor material assignment later
   - Generated as a commented-out optional section

4. FALLBACK FOR NON-POLYGON LAYERS:
   - Skip extrusion for POINT/LINESTRING layers
   - Add comment: "# Extrusion skipped for {geom_type} layer"

The function should inspect the layer's columns list to find height attributes.
Pass columns through to the op function — you may need to adjust the _op_blocks
dispatcher to pass the full columns list (not just first_col) for blender ops.

TESTS: Minimum 10 tests:
- Contains bmesh extrusion code
- Height column "height" detected correctly
- Height column "stories" uses ×3.0 multiplier
- Default height 5.0 when no height column
- Non-polygon layers skipped
- Contains edit mode enter/exit
- Layer with "num_floors" column uses multiplier
- Multiple polygon layers each get extrusion
- Empty columns list uses default height
- Generated code is valid Python syntax (compile() check)

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
```

---

## Prompt 5: `blender_procedural` Operation — Procedural Urban Detail Generation

```
You are adding a "blender_procedural" operation to the gis-codegen blender
platform at src/gis_codegen/generator.py.

GOAL: When --op blender_procedural is passed, the generated script adds
procedural urban details (trees, street furniture, poles) along line and
point features using Blender's geometry nodes or scripted placement.

GENERATED CODE SHOULD:

1. TREE PLACEMENT (for layers with "tree", "park", "green" in name):
   - At each POINT feature: place a procedural low-poly tree
   - Tree generator function:
     a. Cone mesh for canopy (segments=8, radius=2.0, depth=3.0)
     b. Cylinder for trunk (radius=0.15, depth=2.0)
     c. Join into single object
     d. Add slight random rotation (±5°) and scale variation (0.8–1.2×)
   - Green material for canopy, brown for trunk

2. STREET FURNITURE (for layers with "furniture", "bench", "amenity" in name):
   - At each POINT: place a simple bench (box primitives composed)
   - Wood-tone material

3. POLE/LIGHT PLACEMENT (for layers with "light", "pole", "utility" in name):
   - Cylinder (radius=0.05, height=6.0)
   - Optional: point light at top (strength=100, warm white)

4. LINE-BASED DISTRIBUTION (for road/path LINESTRING layers):
   - Sample points along the line at regular intervals (every 15 meters)
   - Place street lights alternating sides, offset 2m from centerline
   - Generated as optional commented section (can be verbose)

5. RANDOMIZATION:
   - Use a seed derived from feature index for reproducibility
   - import random; random.seed(feature_index)

Keep the generated functions compact. Each procedural object generator should
be a self-contained function at the top of the script.

TESTS: Minimum 8 tests:
- Contains procedural tree function (cone + cylinder)
- Tree-named layers trigger tree placement
- Road layers get street light distribution code
- Contains random seed for reproducibility
- Point layers get furniture/pole based on name matching
- Non-matching layers get no procedural detail (skip comment)
- Contains material assignment for procedural objects
- Code compiles without syntax errors

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
```

---

## Prompt 6: `blender_export` Operation — Multi-Format Scene Export

```
You are adding a "blender_export" operation to the gis-codegen blender platform
at src/gis_codegen/generator.py.

GOAL: When --op blender_export is passed, the generated script adds export
routines that save the Blender scene in multiple formats for downstream use.

GENERATED CODE SHOULD (appended at end of script):

1. SAVE .BLEND FILE:
   bpy.ops.wm.save_as_mainfile(filepath=f"/tmp/{database}_scene.blend")

2. EXPORT FORMATS (each in a clearly labeled section):
   a. glTF 2.0 (.glb) — for web viewers and game engines:
      bpy.ops.export_scene.gltf(
          filepath=f"/tmp/{database}_scene.glb",
          export_format='GLB',
          use_selection=False,
          export_apply=True,
      )
   b. FBX — for Unreal Engine / Unity:
      bpy.ops.export_scene.fbx(
          filepath=f"/tmp/{database}_scene.fbx",
          use_selection=False,
          apply_scale_options='FBX_SCALE_ALL',
      )
   c. OBJ — for legacy compatibility:
      bpy.ops.export_scene.obj(
          filepath=f"/tmp/{database}_scene.obj",
          use_selection=False,
      )
   d. USD (.usdc) — for CesiumJS/3D Tiles pipelines:
      bpy.ops.wm.usd_export(
          filepath=f"/tmp/{database}_scene.usdc",
          selected_objects_only=False,
      )

3. RENDER OUTPUT:
   - Render current camera view to PNG:
     bpy.context.scene.render.filepath = f"/tmp/{database}_render.png"
     bpy.ops.render.render(write_still=True)

4. OUTPUT SUMMARY:
   Print a summary of all exported files with full paths.

All output paths should use a configurable OUTPUT_DIR variable at the top of
the generated script, defaulting to "/tmp".

The database name comes from schema["database"], sanitized with safe_var().

TESTS: Minimum 8 tests:
- Contains .blend save
- Contains glTF export call
- Contains FBX export
- Contains OBJ export
- Contains USD export
- Output paths include database name
- OUTPUT_DIR variable defined at top of script
- Contains render output call
- safe_var used for database name in paths

Run: python -m pytest tests/ -m "not integration" -v --cov=gis_codegen
```
