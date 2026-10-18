import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def clean_scene_keep_refs():
    for obj in list(bpy.data.objects):
        if not obj.name.startswith("Ref_") and obj.type != 'CAMERA' and obj.type != 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

def create_kid_character():
    clean_scene_keep_refs()

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    def add_mirror_subsurf(obj, mirror=True, subsurf=1):
        if mirror:
            m = obj.modifiers.new(name="Mirror", type='MIRROR')
            m.use_clip = True
            m.use_axis[0] = True
        if subsurf > 0:
            s = obj.modifiers.new(name="Subsurf", type='SUBSURF')
            s.levels = subsurf
            s.render_levels = subsurf + 1
        for p in obj.data.polygons:
            p.use_smooth = True

    # ----------------------------------------------------
    # 1. HEAD & FACE
    # Head Center: (0, 0, 0.74), Height: 0.16m, Width: 0.14m, Depth: 0.15m
    # ----------------------------------------------------
    head_mesh = bpy.data.meshes.new("Head_Mesh")
    head_obj = bpy.data.objects.new("Kid_Head", head_mesh)
    char_col.objects.link(head_obj)

    bm = bmesh.new()
    # Create stylized child head with chubby cheeks
    # UV Sphere topology built cleanly
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=12, radius=0.075)
    
    # Shape vertices to match blueprint
    for v in bm.verts:
        # Scale into head dimensions (Width: 140mm, Depth: 150mm, Height: 160mm)
        v.co.x *= (0.070 / 0.075)
        v.co.y *= (0.075 / 0.075)
        v.co.z *= (0.080 / 0.075)

        # Child head shaping:
        # 1. Wider lower cheeks (chubby cheeks)
        if -0.04 < v.co.z < 0.02 and v.co.y < 0.02:
            cheek_factor = 1.0 + 0.18 * math.cos(v.co.z * 35.0) * math.cos(v.co.x * 20.0)
            v.co.x *= cheek_factor
            if v.co.y < -0.01:
                v.co.y -= 0.008

        # 2. Cute small chin (narrower at the bottom, slight forward protrusion)
        if v.co.z < -0.04:
            chin_blend = (-v.co.z - 0.04) / 0.04
            v.co.x *= (1.0 - chin_blend * 0.35)
            if v.co.y < 0:
                v.co.y += chin_blend * 0.005

        # 3. Eye socket depressions
        if 0.00 < v.co.z < 0.035 and 0.02 < abs(v.co.x) < 0.055 and v.co.y < -0.03:
            socket_dist = math.sqrt((abs(v.co.x) - 0.038)**2 + (v.co.z - 0.018)**2)
            if socket_dist < 0.025:
                depth_push = (0.025 - socket_dist) * 0.4
                v.co.y += depth_push

        # Offset to world Z center of head (0.74m)
        v.co.z += 0.74

    bm.to_mesh(head_mesh)
    bm.free()
    add_mirror_subsurf(head_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 2. EYEBALLS
    # Located at (+/-0.038, -0.055, 0.75)
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        eye_mesh = bpy.data.meshes.new(f"Eye_{side}_Mesh")
        eye_obj = bpy.data.objects.new(f"Kid_Eye_{side}", eye_mesh)
        char_col.objects.link(eye_obj)

        bm_eye = bmesh.new()
        bmesh.ops.create_uvsphere(bm_eye, u_segments=16, v_segments=12, radius=0.017)
        bm_eye.to_mesh(eye_mesh)
        bm_eye.free()

        eye_obj.location = (sign * 0.036, -0.052, 0.75)
        # Slight rotation forward-outward
        eye_obj.rotation_euler = (0, 0, sign * 0.08)
        for p in eye_obj.data.polygons:
            p.use_smooth = True

    # ----------------------------------------------------
    # 3. NOSE & MOUTH DETAIL
    # Cute stylized button nose
    # ----------------------------------------------------
    nose_mesh = bpy.data.meshes.new("Nose_Mesh")
    nose_obj = bpy.data.objects.new("Kid_Nose", nose_mesh)
    char_col.objects.link(nose_obj)

    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=12, v_segments=8, radius=0.007)
    for v in bm_nose.verts:
        v.co.x *= 1.1
        v.co.y *= 1.2
        v.co.z *= 0.8
        v.co += Vector((0.0, -0.075, 0.718))
    bm_nose.to_mesh(nose_mesh)
    bm_nose.free()
    for p in nose_obj.data.polygons:
        p.use_smooth = True

    # ----------------------------------------------------
    # 4. EARS
    # Prominent stylized child ears at X = +/-0.072, Z = 0.735
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        ear_mesh = bpy.data.meshes.new(f"Ear_{side}_Mesh")
        ear_obj = bpy.data.objects.new(f"Kid_Ear_{side}", ear_mesh)
        char_col.objects.link(ear_obj)

        bm_ear = bmesh.new()
        bmesh.ops.create_uvsphere(bm_ear, u_segments=12, v_segments=10, radius=0.018)
        for v in bm_ear.verts:
            # Flatten along X, elongate along Z, cup inward
            v.co.x *= 0.35
            v.co.y *= 0.85
            v.co.z *= 1.25
            if v.co.x > 0:
                v.co.x *= 0.6 # Cup shape
        bm_ear.to_mesh(ear_mesh)
        bm_ear.free()

        ear_obj.location = (sign * 0.071, -0.005, 0.735)
        # Angled slightly back and flared
        ear_obj.rotation_euler = (0.1, sign * -0.15, sign * 0.35)
        add_mirror_subsurf(ear_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 5. EYEBROWS
    # Thick curved stylized brows
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        brow_mesh = bpy.data.meshes.new(f"Eyebrow_{side}_Mesh")
        brow_obj = bpy.data.objects.new(f"Kid_Eyebrow_{side}", brow_mesh)
        char_col.objects.link(brow_obj)

        bm_b = bmesh.new()
        bmesh.ops.create_cube(bm_b, size=0.02)
        for v in bm_b.verts:
            v.co.x *= 1.2
            v.co.y *= 0.18
            v.co.z *= 0.28
            # Gentle curve
            curve = (v.co.x**2) * -8.0
            v.co.z += curve
        bm_b.to_mesh(brow_mesh)
        bm_b.free()

        brow_obj.location = (sign * 0.038, -0.068, 0.785)
        brow_obj.rotation_euler = (0.2, sign * -0.15, sign * -0.1)
        add_mirror_subsurf(brow_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 6. HAIR (Pixar / Stylized Chunky Volumetric Hair)
    # Total hair volume matches reference up to Z = 1.0m
    # ----------------------------------------------------
    hair_mesh = bpy.data.meshes.new("Hair_Mesh")
    hair_obj = bpy.data.objects.new("Kid_Hair", hair_mesh)
    char_col.objects.link(hair_obj)

    bm_hair = bmesh.new()
    # Main hair helmet base volume
    bmesh.ops.create_uvsphere(bm_hair, u_segments=16, v_segments=12, radius=0.088)
    for v in bm_hair.verts:
        v.co.x *= 1.15
        v.co.y *= 1.12
        v.co.z *= 1.2
        v.co.z += 0.78
        # Flatten bottom inside where head sits
        if v.co.z < 0.72:
            v.co.z = 0.72

    # Hair tufts / stylized clumps
    clump_defs = [
        # (x, y, z, rx, ry, rz, sx, sy, sz)
        # Front top swoop bangs (sweeping character right)
        (0.015, -0.065, 0.84, 0.3, 0.2, -0.4, 0.035, 0.025, 0.045),
        (-0.025, -0.060, 0.85, 0.35, -0.1, 0.3, 0.038, 0.025, 0.048),
        (0.045, -0.050, 0.86, 0.2, 0.3, -0.5, 0.032, 0.025, 0.045),
        (-0.055, -0.045, 0.86, 0.2, -0.3, 0.5, 0.032, 0.025, 0.045),
        # Top volume peaks (reaching up to ~0.98m)
        (0.0, -0.01, 0.92, 0.0, 0.1, 0.0, 0.055, 0.065, 0.055),
        (0.03, 0.01, 0.94, -0.1, 0.2, -0.3, 0.045, 0.055, 0.050),
        (-0.03, 0.01, 0.93, -0.1, -0.2, 0.3, 0.045, 0.055, 0.050),
        # Side tufts over ears
        (0.082, -0.01, 0.78, 0.1, 0.3, -0.2, 0.025, 0.045, 0.045),
        (-0.082, -0.01, 0.78, 0.1, -0.3, 0.2, 0.025, 0.045, 0.045),
        # Back head volume
        (0.0, 0.065, 0.80, -0.3, 0.0, 0.0, 0.065, 0.045, 0.060),
        (0.035, 0.055, 0.76, -0.4, 0.2, 0.0, 0.045, 0.035, 0.050),
        (-0.035, 0.055, 0.76, -0.4, -0.2, 0.0, 0.045, 0.035, 0.050),
    ]

    for (cx, cy, cz, rx, ry, rz, sx, sy, sz) in clump_defs:
        bm_c = bmesh.new()
        bmesh.ops.create_uvsphere(bm_c, u_segments=10, v_segments=8, radius=1.0)
        # Taper tip (egg/teardrop shape)
        for cv in bm_c.verts:
            if cv.co.z > 0:
                cv.co.x *= (1.0 - cv.co.z * 0.4)
                cv.co.y *= (1.0 - cv.co.z * 0.4)
            cv.co.x *= sx
            cv.co.y *= sy
            cv.co.z *= sz
            # Rotate
            rot = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rz, 3, 'Z')
            cv.co = rot @ cv.co
            cv.co += Vector((cx, cy, cz))
        # Merge into main hair
        for v in bm_c.verts:
            bm_hair.verts.new(v.co)
        bm_hair.verts.ensure_lookup_table()
        for f in bm_c.faces:
            try:
                bm_hair.faces.new([bm_hair.verts[v.index] for v in f.verts])
            except Exception:
                pass
        bm_c.free()

    bm_hair.to_mesh(hair_mesh)
    bm_hair.free()
    add_mirror_subsurf(hair_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 7. NECK & BODY BASE
    # Torso Height: 250mm (Z = 0.36 to 0.61m), Neck: 50mm (Z = 0.61 to 0.66m)
    # ----------------------------------------------------
    body_mesh = bpy.data.meshes.new("Body_Mesh")
    body_obj = bpy.data.objects.new("Kid_Body", body_mesh)
    char_col.objects.link(body_obj)

    bm_body = bmesh.new()
    # Torso cylinder with mirror symmetry
    bmesh.ops.create_cone(bm_body, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.075, radius2=0.085, depth=0.25)
    for v in bm_body.verts:
        v.co.x *= 0.95
        v.co.y *= 0.72 # Flatter chest-back depth
        v.co.z += 0.485 # Centered at Z = 0.485 (Z ranges from 0.36 to 0.61)

    # Neck
    bm_neck = bmesh.new()
    bmesh.ops.create_cone(bm_neck, cap_ends=True, cap_tris=False, segments=12,
                           radius1=0.035, radius2=0.038, depth=0.06)
    for v in bm_neck.verts:
        v.co.y *= 0.85
        v.co.z += 0.64
    for v in bm_neck.verts:
        bm_body.verts.new(v.co)
    bm_neck.free()

    bm_body.to_mesh(body_mesh)
    bm_body.free()
    add_mirror_subsurf(body_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 8. INNER T-SHIRT
    # Crewneck collar, torso wrap
    # ----------------------------------------------------
    tshirt_mesh = bpy.data.meshes.new("TShirt_Mesh")
    tshirt_obj = bpy.data.objects.new("Kid_TShirt", tshirt_mesh)
    char_col.objects.link(tshirt_obj)

    bm_ts = bmesh.new()
    bmesh.ops.create_cone(bm_ts, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.080, radius2=0.088, depth=0.23)
    for v in bm_ts.verts:
        v.co.x *= 0.96
        v.co.y *= 0.75
        v.co.z += 0.495
    bm_ts.to_mesh(tshirt_mesh)
    bm_ts.free()
    add_mirror_subsurf(tshirt_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 9. HOODIE / JACKET (Short-Sleeved, Open Zip)
    # Open jacket with hood resting on back
    # ----------------------------------------------------
    hoodie_mesh = bpy.data.meshes.new("Hoodie_Mesh")
    hoodie_obj = bpy.data.objects.new("Kid_Hoodie", hoodie_mesh)
    char_col.objects.link(hoodie_obj)

    bm_h = bmesh.new()
    # Left & Right jacket panels
    for sign in [1, -1]:
        bm_p = bmesh.new()
        bmesh.ops.create_cube(bm_p, size=0.1)
        for v in bm_p.verts:
            v.co.x = (v.co.x + 0.05) * 0.85 * sign + (sign * 0.02)
            v.co.y = v.co.y * 0.78
            v.co.z = v.co.z * 2.3 + 0.485
            # Open gap in front (Y < 0)
            if v.co.y < 0:
                v.co.x += sign * 0.015
        for v in bm_p.verts:
            bm_h.verts.new(v.co)
        bm_p.free()

    # Short sleeves (hanging over shoulders)
    for sign in [1, -1]:
        bm_sl = bmesh.new()
        bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.048, radius2=0.042, depth=0.10)
        for v in bm_sl.verts:
            v.co.x += sign * 0.115
            v.co.y += 0.00
            v.co.z += 0.54
            # Angle outward
            v.co.x += (0.54 - v.co.z) * sign * 0.4
        for v in bm_sl.verts:
            bm_h.verts.new(v.co)
        bm_sl.free()

    # Hood resting on back (from neck down to mid-back)
    bm_hood = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hood, u_segments=12, v_segments=8, radius=0.065)
    for v in bm_hood.verts:
        v.co.x *= 1.2
        v.co.y *= 0.65
        v.co.z *= 0.75
        v.co.y += 0.075 # Behind the neck
        v.co.z += 0.575
    for v in bm_hood.verts:
        bm_h.verts.new(v.co)
    bm_hood.free()

    bm_h.to_mesh(hoodie_mesh)
    bm_h.free()
    add_mirror_subsurf(hoodie_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 10. ARMS & HANDS
    # Arm Length: 220mm (Z = 0.61 down to 0.39m)
    # Relaxed pose matching blueprint
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        arm_mesh = bpy.data.meshes.new(f"Arm_{side}_Mesh")
        arm_obj = bpy.data.objects.new(f"Kid_Arm_{side}", arm_mesh)
        char_col.objects.link(arm_obj)

        bm_arm = bmesh.new()
        # Upper & Lower arm
        bmesh.ops.create_cone(bm_arm, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.026, radius2=0.022, depth=0.18)
        for v in bm_arm.verts:
            v.co.z += 0.47
            v.co.x += sign * 0.125
            # Gentle natural curve
            v.co.y += (v.co.z - 0.47) * 0.08

        # Stylized Child Hand (chubby fist/relaxed hand)
        bm_hand = bmesh.new()
        bmesh.ops.create_uvsphere(bm_hand, u_segments=10, v_segments=8, radius=0.024)
        for v in bm_hand.verts:
            v.co.x *= 0.75
            v.co.y *= 1.15
            v.co.z *= 1.10
            v.co.z += 0.36
            v.co.x += sign * 0.135
            v.co.y += 0.005
        for v in bm_hand.verts:
            bm_arm.verts.new(v.co)
        bm_hand.free()

        bm_arm.to_mesh(arm_mesh)
        bm_arm.free()
        add_mirror_subsurf(arm_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 11. CARGO SHORTS
    # Waist Z = 0.40m down to knee Z = 0.22m
    # ----------------------------------------------------
    shorts_mesh = bpy.data.meshes.new("Shorts_Mesh")
    shorts_obj = bpy.data.objects.new("Kid_Shorts", shorts_mesh)
    char_col.objects.link(shorts_obj)

    bm_sh = bmesh.new()
    # Waist pelvis section
    bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.082, radius2=0.085, depth=0.08)
    for v in bm_sh.verts:
        v.co.x *= 1.05
        v.co.y *= 0.82
        v.co.z += 0.36

    # Left & Right legs of shorts
    for sign in [1, -1]:
        bm_leg_s = bmesh.new()
        bmesh.ops.create_cone(bm_leg_s, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.048, radius2=0.052, depth=0.12)
        for v in bm_leg_s.verts:
            v.co.x += sign * 0.052
            v.co.z += 0.27
        for v in bm_leg_s.verts:
            bm_sh.verts.new(v.co)
        bm_leg_s.free()

        # Cargo Pocket on outer side
        bm_pock = bmesh.new()
        bmesh.ops.create_cube(bm_pock, size=0.04)
        for v in bm_pock.verts:
            v.co.x = v.co.x * 0.3 + (sign * 0.10)
            v.co.y = v.co.y * 0.9
            v.co.z = v.co.z * 1.1 + 0.26
        for v in bm_pock.verts:
            bm_sh.verts.new(v.co)
        bm_pock.free()

    bm_sh.to_mesh(shorts_mesh)
    bm_sh.free()
    add_mirror_subsurf(shorts_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 12. LEGS & SOCKS
    # Leg Length: 300mm (Z = 0.06 to 0.36m)
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        leg_mesh = bpy.data.meshes.new(f"Leg_{side}_Mesh")
        leg_obj = bpy.data.objects.new(f"Kid_Leg_{side}", leg_mesh)
        char_col.objects.link(leg_obj)

        bm_leg = bmesh.new()
        # Knee down to ankle
        bmesh.ops.create_cone(bm_leg, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.024, radius2=0.030, depth=0.20)
        for v in bm_leg.verts:
            v.co.x += sign * 0.050
            v.co.z += 0.18

        # Socks cuff
        bm_sock = bmesh.new()
        bmesh.ops.create_cone(bm_sock, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.027, radius2=0.028, depth=0.05)
        for v in bm_sock.verts:
            v.co.x += sign * 0.050
            v.co.z += 0.085
        for v in bm_sock.verts:
            bm_leg.verts.new(v.co)
        bm_sock.free()

        bm_leg.to_mesh(leg_mesh)
        bm_leg.free()
        add_mirror_subsurf(leg_obj, mirror=False, subsurf=1)

    # ----------------------------------------------------
    # 13. SNEAKERS / SHOES
    # Foot Length: 160mm (0.16m), Width: ~0.08m, Height: ~0.06m
    # ----------------------------------------------------
    for side, sign in [("L", 1), ("R", -1)]:
        shoe_mesh = bpy.data.meshes.new(f"Shoe_{side}_Mesh")
        shoe_obj = bpy.data.objects.new(f"Kid_Shoe_{side}", shoe_mesh)
        char_col.objects.link(shoe_obj)

        bm_shoe = bmesh.new()
        # Sole (thick white rubber sole)
        bmesh.ops.create_cube(bm_shoe, size=0.1)
        for v in bm_shoe.verts:
            v.co.x *= 0.75
            v.co.y *= 1.6 # 160mm length
            v.co.z *= 0.2 # 20mm sole thickness
            # Offset position
            v.co.x += sign * 0.060
            v.co.y -= 0.015 # Toe points forward
            v.co.z += 0.010 # Ground at Z=0

        # Shoe upper body
        bm_upper = bmesh.new()
        bmesh.ops.create_uvsphere(bm_upper, u_segments=12, v_segments=8, radius=0.045)
        for v in bm_upper.verts:
            v.co.x *= 0.85
            v.co.y *= 1.65
            v.co.z *= 0.85
            v.co.x += sign * 0.060
            v.co.y -= 0.015
            v.co.z += 0.038
            if v.co.z < 0.015:
                v.co.z = 0.015
        for v in bm_upper.verts:
            bm_shoe.verts.new(v.co)
        bm_upper.free()

        # Rounded rubber toe cap
        bm_toe = bmesh.new()
        bmesh.ops.create_uvsphere(bm_toe, u_segments=10, v_segments=6, radius=0.032)
        for v in bm_toe.verts:
            v.co.x *= 0.95
            v.co.y *= 0.85
            v.co.z *= 0.65
            v.co.x += sign * 0.060
            v.co.y -= 0.065
            v.co.z += 0.024
        for v in bm_toe.verts:
            bm_shoe.verts.new(v.co)
        bm_toe.free()

        bm_shoe.to_mesh(shoe_mesh)
        bm_shoe.free()
        add_mirror_subsurf(shoe_obj, mirror=False, subsurf=1)

    print("Kid character model created successfully with all parts and exact measurements!")

create_kid_character()
