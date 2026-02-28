# Tree Perc Ash Catcher generator
# Models a simple bottle body + top joint stub + internal tree perc.
# Dimensions are approximate to your blue 6-arm ash catcher.
#
# Paste this into a Fusion 360 Python script file and run via Scripts & Add-Ins.

import adsk.core, adsk.fusion, adsk.cam, traceback, math

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface

        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('No active Fusion 360 design.')
            return

        rootComp = design.rootComponent

        # ------------------------------------------------------------------
        # Units & main parameters (all in mm)
        # ------------------------------------------------------------------
        mm = 0.1  # Fusion internal units are cm → 1 mm = 0.1 cm

        # Bottle body
        body_diam        = 45.0   # outer diameter of main chamber
        body_height      = 90.0   # straight cylinder height
        wall_thickness   = 3.0
        bottom_thickness = 5.0

        # Top “female” joint stub (simplified as a straight cylinder)
        neck_outer  = 22.0   # approx OD of ground-glass joint
        neck_height = 20.0

        # Tree perc
        perc_arm_count     = 6    # number of blue arms
        perc_radius        = 10.0 # radius from center to arm centers
        perc_tube_od       = 8.0  # outer diameter of each arm
        perc_tube_length   = 40.0 # how far arms hang down
        perc_cap_thickness = 4.0  # thickness of the little top disk
        perc_cap_z         = 45.0 # height of perc cap above bottom

        # ------------------------------------------------------------------
        # Convenience refs
        # ------------------------------------------------------------------
        occs = rootComp.occurrences
        transform = adsk.core.Matrix3D.create()
        occ = occs.addNewComponent(transform)
        comp = occ.component
        comp.name = 'Tree Perc Ash Catcher'

        sketches = comp.sketches
        planes   = comp.constructionPlanes
        extrudes = comp.features.extrudeFeatures

        xyPlane = comp.xYConstructionPlane
        origin  = adsk.core.Point3D.create(0, 0, 0)

        # ------------------------------------------------------------------
        # 1) Outer bottle body (solid cylinder)
        # ------------------------------------------------------------------
        sketch_body = sketches.add(xyPlane)
        circles = sketch_body.sketchCurves.sketchCircles

        r_outer = (body_diam * mm) / 2.0
        circles.addByCenterRadius(origin, r_outer)

        prof_outer = sketch_body.profiles.item(0)
        dist_body  = adsk.core.ValueInput.createByReal(body_height * mm)

        ext_body = extrudes.addSimple(
            prof_outer,
            dist_body,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        body = ext_body.bodies.item(0)
        body.name = 'Bottle Body'

        # ------------------------------------------------------------------
        # 2) Hollow out body, leaving thicker bottom
        # ------------------------------------------------------------------
        plane_bottom_offset = planes.addOffset(
            xyPlane,
            adsk.core.ValueInput.createByReal(bottom_thickness * mm)
        )

        sketch_inner = sketches.add(plane_bottom_offset)
        circles_inner = sketch_inner.sketchCurves.sketchCircles

        inner_diam = body_diam - 2.0 * wall_thickness
        r_inner = (inner_diam * mm) / 2.0
        circles_inner.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, 0),
            r_inner
        )

        prof_inner = sketch_inner.profiles.item(0)
        dist_cavity = adsk.core.ValueInput.createByReal(
            (body_height - bottom_thickness) * mm
        )

        extrudes.addSimple(
            prof_inner,
            dist_cavity,
            adsk.fusion.FeatureOperations.CutFeatureOperation
        )

        # ------------------------------------------------------------------
        # 3) Top neck / female joint stub (simplified cylinder)
        # ------------------------------------------------------------------
        plane_top = planes.addOffset(
            xyPlane,
            adsk.core.ValueInput.createByReal(body_height * mm)
        )
        sketch_neck = sketches.add(plane_top)
        circles_neck = sketch_neck.sketchCurves.sketchCircles

        r_neck = (neck_outer * mm) / 2.0
        circles_neck.addByCenterRadius(origin, r_neck)

        prof_neck = sketch_neck.profiles.item(0)
        dist_neck = adsk.core.ValueInput.createByReal(neck_height * mm)

        extrudes.addSimple(
            prof_neck,
            dist_neck,
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )

        # ------------------------------------------------------------------
        # 4) Tree perc (cap disk + 6 hanging tubes as one body)
        # ------------------------------------------------------------------
        plane_perc = planes.addOffset(
            xyPlane,
            adsk.core.ValueInput.createByReal(perc_cap_z * mm)
        )
        sketch_perc = sketches.add(plane_perc)
        circles_perc = sketch_perc.sketchCurves.sketchCircles

        # Cap disk (just a slightly oversized circle so tubes fuse to it)
        r_cap = (perc_radius + perc_tube_od) * mm
        circles_perc.addByCenterRadius(origin, r_cap)

        # Tube circles around center
        tube_r = (perc_tube_od * mm) / 2.0
        for i in range(perc_arm_count):
            angle = 2.0 * math.pi * i / perc_arm_count
            x = (perc_radius * mm) * math.cos(angle)
            y = (perc_radius * mm) * math.sin(angle)
            pt = adsk.core.Point3D.create(x, y, 0)
            circles_perc.addByCenterRadius(pt, tube_r)

        # Split profiles into "big cap" vs "small tube" profiles
        profs = sketch_perc.profiles
        largest_prof = None
        largest_area = 0.0
        small_profiles = []

        for i in range(profs.count):
            p = profs.item(i)
            area = p.areaProperties(
                adsk.fusion.CalculationAccuracy.MediumCalculationAccuracy
            ).area
            if area > largest_area:
                largest_area = area
                largest_prof = p

        for i in range(profs.count):
            p = profs.item(i)
            if p != largest_prof:
                small_profiles.append(p)

        # Cap: extrude upward a little
        dist_cap = adsk.core.ValueInput.createByReal(perc_cap_thickness * mm)
        ext_cap = extrudes.addSimple(
            largest_prof,
            dist_cap,
            adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        )
        perc_body = ext_cap.bodies.item(0)
        perc_body.name = 'Tree Perc'

        # Tubes: extrude downward and JOIN to cap
        tubes_collection = adsk.core.ObjectCollection.create()
        for p in small_profiles:
            tubes_collection.add(p)

        dist_tubes = adsk.core.ValueInput.createByReal(-perc_tube_length * mm)
        extrudes.addSimple(
            tubes_collection,
            dist_tubes,
            adsk.fusion.FeatureOperations.JoinFeatureOperation
        )

        ui.messageBox(
            'Tree-perc ash catcher created.\n'
            'Edit the parameters near the top of the script to tweak sizes.'
        )

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))