import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def setup_materials():
    mats = {
        "Mat_Skin": (0.95, 0.76, 0.65, 1.0),
        "Mat_Hair": (0.22, 0.12, 0.06, 1.0),
        "Mat_Eye_White": (0.98, 0.98, 0.98, 1.0),
        "Mat_Eye_Iris": (0.20, 0.10, 0.05, 1.0),
        "Mat_Eye_Pupil": (0.02, 0.02, 0.02, 1.0),
        "Mat_Eyebrow": (0.18, 0.09, 0.04, 1.0),
        "Mat_TShirt": (0.95, 0.95, 0.95, 1.0),
        "Mat_Hoodie": (0.24, 0.52, 0.78, 1.0),
        "Mat_Shorts": (0.76, 0.62, 0.44, 1.0),
        "Mat_Socks": (0.96, 0.96, 0.96, 1.0),
        "Mat_Shoes_Blue": (0.18, 0.38, 0.62, 1.0),
        "Mat_Shoes_White": (0.96, 0.96, 0.96, 1.0),
    }
    created = {}
    for name, color in mats.items():
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs[0].default_value = color
            # Roughness
            if "Skin" in name:
                bsdf.inputs[2].default_value = 0.5
            elif "Hair" in name:
                bsdf.inputs[2].default_value = 0.6
            elif "Eye_Iris" in name or "Eye_Pupil" in name:
                bsdf.inputs[2].default_value = 0.1
        mat.diffuse_color = color
        created[name] = mat
    return created

def clean_scene_keep_refs():
    for obj in list(bpy.data.objects):
        if not obj.name.startswith("Ref_") and obj.type != 'CAMERA' and obj.type != 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

def build_model():
    clean_scene_keep_refs()
    mats = setup_materials()

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    def finish_mesh(obj, mirror=True, subsurf=1, mat=None):
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
        if mat and mat.name not in [m.name for m in obj.data.materials]:
            obj.data.materials.append(mat)
        return obj

    # =========================================================================
    # 1. HEAD & FACE
    # Head Center: (0, 0, 0.74m)
    # Head Width: 140mm (X: -0.07 to +0.07)
    # Head Height: 160mm (Z: 0.66 to 0.82)
    # Head Depth: 150mm (Y: -0.075 to +0.075)
    # =========================================================================
    head_mesh = bpy.data.meshes.new("Head_Mesh")
    head_obj = bpy.data.objects.new("Kid_Head", head_mesh)
    char_col.objects.link(head_obj)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=16, radius=0.075)

    for v in bm.verts:
        # Scale to match blueprint bounding box
        v.co.x *= (0.070 / 0.075)
        v.co.y *= (0.075 / 0.075)
        v.co.z *= (0.080 / 0.075)

        # Chubby cheeks: expand lower cheeks in front
        if -0.04 < v.co.z < 0.015 and v.co.y < 0.02:
            cheek_t = math.cos((v.co.z + 0.01) * 35.0) * math.cos(v.co.x * 18.0)
            if cheek_t > 0:
                v.co.x *= (1.0 + cheek_t * 0.16)
                if v.co.y < -0.02:
                    v.co.y -= cheek_t * 0.008

        # Small cute chin
        if v.co.z < -0.04:
            chin_blend = min(1.0, (-v.co.z - 0.04) / 0.035)
            v.co.x *= (1.0 - chin_blend * 0.40)
            if v.co.y < 0:
                v.co.y += chin_blend * 0.006

        # Eye socket depressions
        if -0.005 < v.co.z < 0.035 and 0.020 < abs(v.co.x) < 0.055 and v.co.y < -0.03:
            dist = math.sqrt((abs(v.co.x) - 0.037)**2 + (v.co.z - 0.015)**2)
            if dist < 0.024:
                push = (0.024 - dist) * 0.35
                v.co.y += push

        # Offset to world Z
        v.co.z += 0.74

    bm.to_mesh(head_mesh)
    bm.free()
    finish_mesh(head_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

    # Cute button nose
    nose_mesh = bpy.data.meshes.new("Nose_Mesh")
    nose_obj = bpy.data.objects.new("Kid_Nose", nose_mesh)
    char_col.objects.link(nose_obj)
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=12, v_segments=8, radius=0.007)
    for v in bm_nose.verts:
        v.co.x *= 1.15
        v.co.y *= 1.25
        v.co.z *= 0.85
        v.co += Vector((0.0, -0.077, 0.718))
    bm_nose.to_mesh(nose_mesh)
    bm_nose.free()
    finish_mesh(nose_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

    # Gentle smiling mouth
    mouth_mesh = bpy.data.meshes.new("Mouth_Mesh")
    mouth_obj = bpy.data.objects.new("Kid_Mouth", mouth_mesh)
    char_col.objects.link(mouth_obj)
    bm_m = bmesh.new()
    bmesh.ops.create_cube(bm_m, size=0.01)
    for v in bm_m.verts:
        v.co.x *= 2.5
        v.co.y *= 0.15
        v.co.z *= 0.20
        # Curve into a gentle smile
        v.co.z += (v.co.x**2) * 8.0
        v.co += Vector((0.0, -0.071, 0.682))
    bm_m.to_mesh(mouth_mesh)
    bm_m.free()
    finish_mesh(mouth_obj, mirror=False, subsurf=1, mat=mats["Mat_Hair"])

    # =========================================================================
    # 2. EYEBALLS & PUPILS
    # Position: (+/- 0.037, -0.054, 0.75m)
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        # Sclera (Eyeball white)
        eye_mesh = bpy.data.meshes.new(f"Eye_{side}_Mesh")
        eye_obj = bpy.data.objects.new(f"Kid_Eye_{side}", eye_mesh)
        char_col.objects.link(eye_obj)
        bm_e = bmesh.new()
        bmesh.ops.create_uvsphere(bm_e, u_segments=16, v_segments=12, radius=0.0165)
        bm_e.to_mesh(eye_mesh)
        bm_e.free()
        eye_obj.location = (sign * 0.036, -0.055, 0.752)
        eye_obj.rotation_euler = (0, 0, sign * 0.06)
        finish_mesh(eye_obj, mirror=False, subsurf=1, mat=mats["Mat_Eye_White"])

        # Iris (Large expressive brown cartoon iris)
        iris_mesh = bpy.data.meshes.new(f"Iris_{side}_Mesh")
        iris_obj = bpy.data.objects.new(f"Kid_Iris_{side}", iris_mesh)
        char_col.objects.link(iris_obj)
        bm_ir = bmesh.new()
        bmesh.ops.create_circle(bm_ir, cap_ends=True, segments=16, radius=0.0105)
        bm_ir.to_mesh(iris_mesh)
        bm_ir.free()
        iris_obj.location = (sign * 0.036, -0.071, 0.752)
        iris_obj.rotation_euler = (1.5707963, 0, sign * 0.06)
        finish_mesh(iris_obj, mirror=False, subsurf=0, mat=mats["Mat_Eye_Iris"])

        # Pupil & Specular highlight
        pupil_mesh = bpy.data.meshes.new(f"Pupil_{side}_Mesh")
        pupil_obj = bpy.data.objects.new(f"Kid_Pupil_{side}", pupil_mesh)
        char_col.objects.link(pupil_obj)
        bm_pu = bmesh.new()
        bmesh.ops.create_circle(bm_pu, cap_ends=True, segments=12, radius=0.0055)
        bm_pu.to_mesh(pupil_mesh)
        bm_pu.free()
        pupil_obj.location = (sign * 0.036, -0.0715, 0.752)
        pupil_obj.rotation_euler = (1.5707963, 0, sign * 0.06)
        finish_mesh(pupil_obj, mirror=False, subsurf=0, mat=mats["Mat_Eye_Pupil"])

        # Highlight dot
        hl_mesh = bpy.data.meshes.new(f"Highlight_{side}_Mesh")
        hl_obj = bpy.data.objects.new(f"Kid_Highlight_{side}", hl_mesh)
        char_col.objects.link(hl_obj)
        bm_hl = bmesh.new()
        bmesh.ops.create_uvsphere(bm_hl, u_segments=8, v_segments=6, radius=0.0028)
        bm_hl.to_mesh(hl_mesh)
        bm_hl.free()
        hl_obj.location = (sign * 0.034, -0.0725, 0.755)
        finish_mesh(hl_obj, mirror=False, subsurf=0, mat=mats["Mat_Eye_White"])

    # =========================================================================
    # 3. EARS
    # Prominent stylized ears at X = +/- 0.072, Z = 0.735
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        ear_mesh = bpy.data.meshes.new(f"Ear_{side}_Mesh")
        ear_obj = bpy.data.objects.new(f"Kid_Ear_{side}", ear_mesh)
        char_col.objects.link(ear_obj)

        bm_ear = bmesh.new()
        bmesh.ops.create_uvsphere(bm_ear, u_segments=14, v_segments=10, radius=0.017)
        for v in bm_ear.verts:
            v.co.x *= 0.35
            v.co.y *= 0.85
            v.co.z *= 1.25
            if v.co.x * sign > 0:
                v.co.x *= 0.6 # Cupped ear canal
        bm_ear.to_mesh(ear_mesh)
        bm_ear.free()
        ear_obj.location = (sign * 0.071, -0.005, 0.735)
        ear_obj.rotation_euler = (0.1, sign * -0.15, sign * 0.35)
        finish_mesh(ear_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

    # =========================================================================
    # 4. EYEBROWS
    # Thick curved stylized brows above eyes
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        brow_mesh = bpy.data.meshes.new(f"Eyebrow_{side}_Mesh")
        brow_obj = bpy.data.objects.new(f"Kid_Eyebrow_{side}", brow_mesh)
        char_col.objects.link(brow_obj)

        bm_b = bmesh.new()
        bmesh.ops.create_cube(bm_b, size=0.02)
        for v in bm_b.verts:
            v.co.x *= 1.3
            v.co.y *= 0.15
            v.co.z *= 0.28
            curve = (v.co.x**2) * -8.0
            v.co.z += curve
        bm_b.to_mesh(brow_mesh)
        bm_b.free()
        brow_obj.location = (sign * 0.038, -0.071, 0.782)
        brow_obj.rotation_euler = (0.22, sign * -0.15, sign * -0.12)
        finish_mesh(brow_obj, mirror=False, subsurf=1, mat=mats["Mat_Eyebrow"])

    # =========================================================================
    # 5. HAIR (Stylized Pixar / Disney Chunky Hair)
    # Does NOT cover the face! Sits on top, sides, and back.
    # Front bangs swoop across the forehead above the brows.
    # Top volume reaches Z = 0.98m (matches 1000mm total height).
    # =========================================================================
    hair_mesh = bpy.data.meshes.new("Hair_Mesh")
    hair_obj = bpy.data.objects.new("Kid_Hair", hair_mesh)
    char_col.objects.link(hair_obj)

    bm_hair = bmesh.new()

    # Skull hair base (only covers top and back of skull, leaving face clear)
    bmesh.ops.create_uvsphere(bm_hair, u_segments=20, v_segments=14, radius=0.082)
    for v in list(bm_hair.verts):
        # Keep only top/back (Y > -0.015 or Z > 0.035)
        if v.co.y < -0.025 and v.co.z < 0.03:
            # Delete front-face penetrating vertices
            bm_hair.verts.remove(v)
        else:
            v.co.x *= 1.08
            v.co.y *= 1.10
            v.co.z *= 1.18
            v.co.z += 0.785

    # Individual stylized chunky hair clumps (teardrop curved volumes)
    clump_specs = [
        # Front sweeping bangs (forehead)
        (0.012, -0.068, 0.835, 0.32, 0.22, -0.45, 0.030, 0.020, 0.042),
        (-0.028, -0.062, 0.845, 0.38, -0.12, 0.32, 0.034, 0.022, 0.045),
        (0.042, -0.052, 0.852, 0.22, 0.32, -0.55, 0.028, 0.022, 0.040),
        (-0.052, -0.048, 0.855, 0.22, -0.32, 0.52, 0.028, 0.022, 0.040),
        # Crown & Top Messy Peaks (reaching Z = 0.96 - 0.98m)
        (0.000, -0.005, 0.915, 0.00, 0.12, -0.10, 0.052, 0.060, 0.055),
        (0.028,  0.010, 0.940, -0.15, 0.22, -0.35, 0.042, 0.050, 0.048),
        (-0.028,  0.010, 0.935, -0.15, -0.22, 0.35, 0.042, 0.050, 0.048),
        (0.015, -0.025, 0.895, 0.15, 0.15, -0.25, 0.040, 0.040, 0.045),
        # Side tufts (temples & above ears)
        (0.078, -0.015, 0.795, 0.12, 0.35, -0.22, 0.024, 0.040, 0.042),
        (-0.078, -0.015, 0.795, 0.12, -0.35, 0.22, 0.024, 0.040, 0.042),
        # Back head layers
        (0.000, 0.065, 0.810, -0.35, 0.00, 0.00, 0.060, 0.040, 0.055),
        (0.032, 0.058, 0.770, -0.45, 0.20, -0.10, 0.042, 0.032, 0.048),
        (-0.032, 0.058, 0.770, -0.45, -0.20, 0.10, 0.042, 0.032, 0.048),
        (0.000, 0.055, 0.730, -0.55, 0.00, 0.00, 0.045, 0.028, 0.042),
    ]

    for (cx, cy, cz, rx, ry, rz, sx, sy, sz) in clump_specs:
        bm_c = bmesh.new()
        bmesh.ops.create_uvsphere(bm_c, u_segments=10, v_segments=8, radius=1.0)
        for cv in bm_c.verts:
            if cv.co.z > 0:
                cv.co.x *= (1.0 - cv.co.z * 0.45)
                cv.co.y *= (1.0 - cv.co.z * 0.45)
            cv.co.x *= sx
            cv.co.y *= sy
            cv.co.z *= sz
            rot = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rz, 3, 'Z')
            cv.co = rot @ cv.co
            cv.co += Vector((cx, cy, cz))
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
    finish_mesh(hair_obj, mirror=False, subsurf=1, mat=mats["Mat_Hair"])

    # =========================================================================
    # 6. NECK & BODY BASE (Skin)
    # Neck: Z = 0.61 to 0.67m, Torso: Z = 0.36 to 0.61m
    # =========================================================================
    body_mesh = bpy.data.meshes.new("Body_Mesh")
    body_obj = bpy.data.objects.new("Kid_Body", body_mesh)
    char_col.objects.link(body_obj)

    bm_body = bmesh.new()
    # Torso
    bmesh.ops.create_cone(bm_body, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.075, radius2=0.082, depth=0.25)
    for v in bm_body.verts:
        v.co.x *= 0.94
        v.co.y *= 0.70
        v.co.z += 0.485

    # Neck
    bm_neck = bmesh.new()
    bmesh.ops.create_cone(bm_neck, cap_ends=True, cap_tris=False, segments=12,
                           radius1=0.034, radius2=0.036, depth=0.065)
    for v in bm_neck.verts:
        v.co.y *= 0.85
        v.co.z += 0.642
    for v in bm_neck.verts:
        bm_body.verts.new(v.co)
    bm_neck.free()

    bm_body.to_mesh(body_mesh)
    bm_body.free()
    finish_mesh(body_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

    # =========================================================================
    # 7. INNER T-SHIRT (White Crewneck)
    # Fits neatly over torso, crewneck collar at neck base
    # =========================================================================
    tshirt_mesh = bpy.data.meshes.new("TShirt_Mesh")
    tshirt_obj = bpy.data.objects.new("Kid_TShirt", tshirt_mesh)
    char_col.objects.link(tshirt_obj)

    bm_ts = bmesh.new()
    bmesh.ops.create_cone(bm_ts, cap_ends=True, cap_tris=False, segments=18,
                          radius1=0.078, radius2=0.086, depth=0.235)
    for v in bm_ts.verts:
        v.co.x *= 0.95
        v.co.y *= 0.73
        v.co.z += 0.495

    # Collar rim
    bm_col = bmesh.new()
    bmesh.ops.create_cone(bm_col, cap_ends=False, segments=16,
                          radius1=0.038, radius2=0.040, depth=0.015)
    for v in bm_col.verts:
        v.co.y *= 0.85
        v.co.z += 0.612
    for v in bm_col.verts:
        bm_ts.verts.new(v.co)
    bm_col.free()

    bm_ts.to_mesh(tshirt_mesh)
    bm_ts.free()
    finish_mesh(tshirt_obj, mirror=False, subsurf=1, mat=mats["Mat_TShirt"])

    # =========================================================================
    # 8. SHORT-SLEEVE HOODIE / JACKET (Blue, Open Front)
    # Open jacket with hood on back, short sleeves, hem band, drawstrings
    # =========================================================================
    hoodie_mesh = bpy.data.meshes.new("Hoodie_Mesh")
    hoodie_obj = bpy.data.objects.new("Kid_Hoodie", hoodie_mesh)
    char_col.objects.link(hoodie_obj)

    bm_h = bmesh.new()

    # Jacket torso panels (left and right, open front gap)
    for sign in [1, -1]:
        bm_jp = bmesh.new()
        bmesh.ops.create_cube(bm_jp, size=0.1)
        for v in bm_jp.verts:
            # Half torso coverage
            v.co.x = (v.co.x + 0.05) * 0.88 * sign + (sign * 0.018)
            v.co.y = v.co.y * 0.82
            v.co.z = v.co.z * 2.35 + 0.495
            # Open front gap (X between -0.02 and +0.02 in front)
            if v.co.y < 0:
                v.co.x += sign * 0.018
        for v in bm_jp.verts:
            bm_h.verts.new(v.co)
        bm_jp.free()

    # Short hoodie sleeves (loose cut over shoulders)
    for sign in [1, -1]:
        bm_sl = bmesh.new()
        bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=14,
                              radius1=0.052, radius2=0.045, depth=0.12)
        for v in bm_sl.verts:
            v.co.x += sign * 0.118
            v.co.z += 0.540
            # Splay outward matching relaxed A-pose
            v.co.x += (0.540 - v.co.z) * sign * 0.45
        for v in bm_sl.verts:
            bm_h.verts.new(v.co)
        bm_sl.free()

    # Hood folded back over the neck and upper back
    bm_hood = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hood, u_segments=16, v_segments=10, radius=0.068)
    for v in bm_hood.verts:
        v.co.x *= 1.25
        v.co.y *= 0.65
        v.co.z *= 0.75
        v.co.y += 0.080 # Extends behind neck
        v.co.z += 0.585
    for v in bm_hood.verts:
        bm_h.verts.new(v.co)
    bm_hood.free()

    # Ribbed bottom hem
    bm_hem = bmesh.new()
    bmesh.ops.create_cone(bm_hem, cap_ends=True, cap_tris=False, segments=18,
                          radius1=0.082, radius2=0.082, depth=0.025)
    for v in bm_hem.verts:
        v.co.x *= 0.98
        v.co.y *= 0.78
        v.co.z += 0.385
    for v in bm_hem.verts:
        bm_h.verts.new(v.co)
    bm_hem.free()

    bm_h.to_mesh(hoodie_mesh)
    bm_h.free()
    finish_mesh(hoodie_obj, mirror=False, subsurf=1, mat=mats["Mat_Hoodie"])

    # Two white drawstrings hanging from hoodie collar
    for side, sign in [("L", 1), ("R", -1)]:
        ds_mesh = bpy.data.meshes.new(f"Drawstring_{side}_Mesh")
        ds_obj = bpy.data.objects.new(f"Kid_Drawstring_{side}", ds_mesh)
        char_col.objects.link(ds_obj)
        bm_ds = bmesh.new()
        bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.003, radius2=0.0035, depth=0.10)
        for v in bm_ds.verts:
            v.co += Vector((sign * 0.028, -0.068, 0.525))
        bm_ds.to_mesh(ds_mesh)
        bm_ds.free()
        finish_mesh(ds_obj, mirror=False, subsurf=1, mat=mats["Mat_TShirt"])

    # =========================================================================
    # 9. ARMS & HANDS
    # Arm Length: 220mm (Shoulder 0.61m down to fingertips 0.36m)
    # Relaxed natural pose matching blueprint
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        arm_mesh = bpy.data.meshes.new(f"Arm_{side}_Mesh")
        arm_obj = bpy.data.objects.new(f"Kid_Arm_{side}", arm_mesh)
        char_col.objects.link(arm_obj)

        bm_arm = bmesh.new()
        # Forearm / lower arm visible beneath short sleeves
        bmesh.ops.create_cone(bm_arm, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.024, radius2=0.021, depth=0.17)
        for v in bm_arm.verts:
            v.co.z += 0.465
            v.co.x += sign * 0.125
            v.co.y += (v.co.z - 0.465) * 0.05

        # Stylized Child Hand (chubby, cute fingers)
        # Palm
        bm_hand = bmesh.new()
        bmesh.ops.create_uvsphere(bm_hand, u_segments=10, v_segments=8, radius=0.022)
        for v in bm_hand.verts:
            v.co.x *= 0.70
            v.co.y *= 1.15
            v.co.z *= 1.10
            v.co.z += 0.360
            v.co.x += sign * 0.132
            v.co.y += 0.005
        for v in bm_hand.verts:
            bm_arm.verts.new(v.co)
        bm_hand.free()

        # Thumb
        bm_th = bmesh.new()
        bmesh.ops.create_cone(bm_th, cap_ends=True, segments=8, radius1=0.0065, radius2=0.005, depth=0.018)
        for v in bm_th.verts:
            v.co.x += sign * 0.120
            v.co.y -= 0.015
            v.co.z += 0.365
        for v in bm_th.verts:
            bm_arm.verts.new(v.co)
        bm_th.free()

        bm_arm.to_mesh(arm_mesh)
        bm_arm.free()
        finish_mesh(arm_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

    # =========================================================================
    # 10. CARGO SHORTS (Khaki with side cargo pockets)
    # Waist: Z = 0.40m down to knee Z = 0.22m
    # =========================================================================
    shorts_mesh = bpy.data.meshes.new("Shorts_Mesh")
    shorts_obj = bpy.data.objects.new("Kid_Shorts", shorts_mesh)
    char_col.objects.link(shorts_obj)

    bm_sh = bmesh.new()
    # Pelvis waistband
    bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=18,
                          radius1=0.082, radius2=0.085, depth=0.09)
    for v in bm_sh.verts:
        v.co.x *= 1.05
        v.co.y *= 0.82
        v.co.z += 0.365

    # Left & Right loose short legs
    for sign in [1, -1]:
        bm_slg = bmesh.new()
        bmesh.ops.create_cone(bm_slg, cap_ends=True, cap_tris=False, segments=14,
                              radius1=0.048, radius2=0.052, depth=0.13)
        for v in bm_slg.verts:
            v.co.x += sign * 0.052
            v.co.z += 0.275
        for v in bm_slg.verts:
            bm_sh.verts.new(v.co)
        bm_slg.free()

        # Folded cuff hem at knee
        bm_cuff = bmesh.new()
        bmesh.ops.create_cone(bm_cuff, cap_ends=False, segments=14,
                              radius1=0.054, radius2=0.054, depth=0.020)
        for v in bm_cuff.verts:
            v.co.x += sign * 0.052
            v.co.z += 0.220
        for v in bm_cuff.verts:
            bm_sh.verts.new(v.co)
        bm_cuff.free()

        # Side cargo pocket box + flap
        bm_pock = bmesh.new()
        bmesh.ops.create_cube(bm_pock, size=0.038)
        for v in bm_pock.verts:
            v.co.x = v.co.x * 0.35 + (sign * 0.098)
            v.co.y = v.co.y * 0.95
            v.co.z = v.co.z * 1.15 + 0.270
        for v in bm_pock.verts:
            bm_sh.verts.new(v.co)
        bm_pock.free()

        # Pocket flap
        bm_flap = bmesh.new()
        bmesh.ops.create_cube(bm_flap, size=0.015)
        for v in bm_flap.verts:
            v.co.x = v.co.x * 0.8 + (sign * 0.100)
            v.co.y = v.co.y * 2.3
            v.co.z = v.co.z * 0.4 + 0.295
        for v in bm_flap.verts:
            bm_sh.verts.new(v.co)
        bm_flap.free()

    bm_sh.to_mesh(shorts_mesh)
    bm_sh.free()
    finish_mesh(shorts_obj, mirror=False, subsurf=1, mat=mats["Mat_Shorts"])

    # =========================================================================
    # 11. LEGS & SOCKS
    # Leg Length: 300mm (Z = 0.06 to 0.36m)
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        # Leg skin (between shorts and socks)
        leg_mesh = bpy.data.meshes.new(f"Leg_{side}_Mesh")
        leg_obj = bpy.data.objects.new(f"Kid_Leg_{side}", leg_mesh)
        char_col.objects.link(leg_obj)

        bm_leg = bmesh.new()
        bmesh.ops.create_cone(bm_leg, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.024, radius2=0.030, depth=0.18)
        for v in bm_leg.verts:
            v.co.x += sign * 0.050
            v.co.z += 0.180
        bm_leg.to_mesh(leg_mesh)
        bm_leg.free()
        finish_mesh(leg_obj, mirror=False, subsurf=1, mat=mats["Mat_Skin"])

        # White Crew Socks
        sock_mesh = bpy.data.meshes.new(f"Sock_{side}_Mesh")
        sock_obj = bpy.data.objects.new(f"Kid_Sock_{side}", sock_mesh)
        char_col.objects.link(sock_obj)

        bm_sk = bmesh.new()
        bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=12,
                              radius1=0.026, radius2=0.027, depth=0.055)
        for v in bm_sk.verts:
            v.co.x += sign * 0.050
            v.co.z += 0.085
        bm_sk.to_mesh(sock_mesh)
        bm_sk.free()
        finish_mesh(sock_obj, mirror=False, subsurf=1, mat=mats["Mat_Socks"])

    # =========================================================================
    # 12. SNEAKERS / SHOES (Blue Skate Shoes with White Rubber Soles & Toe Caps)
    # Foot Length: 160mm (0.16m), Width: ~0.08m, Height: ~0.06m
    # =========================================================================
    for side, sign in [("L", 1), ("R", -1)]:
        shoe_mesh = bpy.data.meshes.new(f"Shoe_{side}_Mesh")
        shoe_obj = bpy.data.objects.new(f"Kid_Shoe_{side}", shoe_mesh)
        char_col.objects.link(shoe_obj)

        bm_sh = bmesh.new()

        # 1. White Rubber Sole (flat, 18mm thick)
        bmesh.ops.create_cube(bm_sh, size=0.1)
        for v in bm_sh.verts:
            v.co.x *= 0.72
            v.co.y *= 1.60 # 160mm length
            v.co.z *= 0.18 # 18mm thickness
            v.co.x += sign * 0.058
            v.co.y -= 0.015
            v.co.z += 0.009 # Ground at Z = 0

        # 2. White Rubber Toe Cap
        bm_tc = bmesh.new()
        bmesh.ops.create_uvsphere(bm_tc, u_segments=12, v_segments=8, radius=0.034)
        for v in bm_tc.verts:
            v.co.x *= 0.95
            v.co.y *= 0.80
            v.co.z *= 0.65
            v.co.x += sign * 0.058
            v.co.y -= 0.068
            v.co.z += 0.022
        for v in bm_tc.verts:
            bm_sh.verts.new(v.co)
        bm_tc.free()

        # 3. Blue Shoe Upper Body
        bm_up = bmesh.new()
        bmesh.ops.create_uvsphere(bm_up, u_segments=14, v_segments=10, radius=0.046)
        for v in bm_up.verts:
            v.co.x *= 0.82
            v.co.y *= 1.62
            v.co.z *= 0.82
            v.co.x += sign * 0.058
            v.co.y -= 0.015
            v.co.z += 0.038
            if v.co.z < 0.016:
                v.co.z = 0.016
        for v in bm_up.verts:
            bm_sh.verts.new(v.co)
        bm_up.free()

        # 4. White Shoe Laces (Criss-Cross bars)
        for lz, ly in [(0.046, -0.045), (0.052, -0.030), (0.058, -0.015)]:
            bm_lc = bmesh.new()
            bmesh.ops.create_cube(bm_lc, size=0.01)
            for v in bm_lc.verts:
                v.co.x *= 3.0
                v.co.y *= 0.4
                v.co.z *= 0.3
                v.co.x += sign * 0.058
                v.co.y += ly
                v.co.z += lz
            for v in bm_lc.verts:
                bm_sh.verts.new(v.co)
            bm_lc.free()

        bm_sh.to_mesh(shoe_mesh)
        bm_sh.free()
        finish_mesh(shoe_obj, mirror=False, subsurf=1, mat=mats["Mat_Shoes_Blue"])

    print("Complete kid character model built successfully with clean production parts!")

build_model()
