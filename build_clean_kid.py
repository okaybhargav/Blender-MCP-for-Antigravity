import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def setup_materials():
    mats = {
        "Mat_Skin": (0.95, 0.76, 0.65, 1.0),
        "Mat_Hair": (0.24, 0.12, 0.06, 1.0),
        "Mat_Eye_White": (0.98, 0.98, 0.98, 1.0),
        "Mat_Eye_Iris": (0.22, 0.11, 0.05, 1.0),
        "Mat_Eye_Pupil": (0.02, 0.02, 0.02, 1.0),
        "Mat_Eyebrow": (0.18, 0.09, 0.04, 1.0),
        "Mat_TShirt": (0.96, 0.96, 0.96, 1.0),
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
            if "Skin" in name:
                bsdf.inputs[2].default_value = 0.45
            elif "Eye_Iris" in name or "Eye_Pupil" in name:
                bsdf.inputs[2].default_value = 0.05
            else:
                bsdf.inputs[2].default_value = 0.55
        mat.diffuse_color = color
        created[name] = mat
    return created

def clean_scene_keep_refs():
    for obj in list(bpy.data.objects):
        if not obj.name.startswith("Ref_") and obj.type != 'CAMERA' and obj.type != 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)

def create_mirrored_object(name, bm, mat, subsurf=1, collection=None):
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    if collection:
        collection.objects.link(obj)
    else:
        bpy.context.scene.collection.objects.link(obj)

    # Mirror Modifier with clipping
    m = obj.modifiers.new(name="Mirror", type='MIRROR')
    m.use_clip = True
    m.use_axis[0] = True

    # Subdivision Surface
    if subsurf > 0:
        s = obj.modifiers.new(name="Subsurf", type='SUBSURF')
        s.levels = subsurf
        s.render_levels = subsurf + 1

    for p in obj.data.polygons:
        p.use_smooth = True

    if mat:
        obj.data.materials.append(mat)

    return obj

def build_production_kid():
    clean_scene_keep_refs()
    mats = setup_materials()

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    # =========================================================================
    # 1. CONTINUOUS ANATOMICAL BODY BASE MESH (Head, Neck, Torso, Arms, Legs)
    # Modeled for X >= 0 with Mirror Modifier
    # =========================================================================
    bm_body = bmesh.new()

    # --- HEAD (Half-Sphere grid from midline X=0) ---
    # Create lat-long grid for X >= 0
    u_segs = 16 # for full circle = 32
    v_segs = 16
    r_x = 0.070 # Width 140mm
    r_y = 0.075 # Depth 150mm
    r_z = 0.080 # Height 160mm
    z_head = 0.740

    head_grid = []
    for vi in range(v_segs + 1):
        phi = math.pi * (vi / v_segs) # 0 (top) to pi (bottom)
        row = []
        for ui in range(u_segs // 2 + 1):
            theta = -math.pi / 2.0 + math.pi * (ui / (u_segs // 2)) # -pi/2 (front midline) to +pi/2 (back midline)
            
            x = r_x * math.sin(phi) * math.cos(theta)
            y = r_y * math.sin(phi) * math.sin(theta)
            z = r_z * math.cos(phi)

            # Snap midline vertices to exact X = 0
            if ui == 0 or ui == (u_segs // 2):
                x = 0.0

            # Stylized shaping:
            # Chubby cheeks
            if -0.04 < z < 0.015 and y < 0.01:
                t = math.cos((z + 0.01) * 35.0)
                if t > 0:
                    x *= (1.0 + t * 0.18)
                    if y < -0.02:
                        y -= t * 0.008

            # Tapered cute chin
            if z < -0.04:
                blend = min(1.0, (-z - 0.04) / 0.038)
                x *= (1.0 - blend * 0.40)
                if y < 0:
                    y += blend * 0.006

            # Eye socket indentation
            if -0.005 < z < 0.035 and 0.018 < x < 0.055 and y < -0.025:
                dist = math.sqrt((x - 0.038)**2 + (z - 0.015)**2)
                if dist < 0.025:
                    y += (0.025 - dist) * 0.35

            v_pt = bm_body.verts.new(Vector((x, y, z + z_head)))
            row.append(v_pt)
        head_grid.append(row)

    # Stitch head grid faces
    for vi in range(v_segs):
        for ui in range(u_segs // 2):
            v0 = head_grid[vi][ui]
            v1 = head_grid[vi][ui + 1]
            v2 = head_grid[vi + 1][ui + 1]
            v3 = head_grid[vi + 1][ui]
            # Avoid duplicate/degenerate faces at poles
            verts = []
            for v in [v0, v1, v2, v3]:
                if v not in verts:
                    verts.append(v)
            if len(verts) >= 3:
                try:
                    bm_body.faces.new(verts)
                except Exception:
                    pass

    # --- NECK & TORSO (X >= 0) ---
    torso_levels = [
        # (Z, radius_x, radius_y)
        (0.660, 0.032, 0.034), # Neck top
        (0.610, 0.036, 0.038), # Neck base / Clavicle
        (0.550, 0.082, 0.062), # Chest / Armpits
        (0.480, 0.076, 0.058), # Waist
        (0.410, 0.078, 0.064), # Hips
        (0.360, 0.075, 0.066), # Crotch / Pelvis
    ]
    torso_grid = []
    t_segs = 8 # half-perimeter segments from front midline to back midline
    for (tz, rx, ry) in torso_levels:
        row = []
        for i in range(t_segs + 1):
            ang = -math.pi / 2.0 + math.pi * (i / t_segs)
            tx = rx * math.cos(ang)
            ty = ry * math.sin(ang)
            if i == 0 or i == t_segs:
                tx = 0.0
            row.append(bm_body.verts.new(Vector((tx, ty, tz))))
        torso_grid.append(row)

    for li in range(len(torso_levels) - 1):
        for i in range(t_segs):
            v0 = torso_grid[li][i]
            v1 = torso_grid[li][i + 1]
            v2 = torso_grid[li + 1][i + 1]
            v3 = torso_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    # --- ARM (Right side X > 0, relaxed A-pose) ---
    arm_levels = [
        # (center, radius)
        (Vector((0.085, 0.00, 0.560)), 0.026), # Shoulder
        (Vector((0.110, 0.00, 0.470)), 0.022), # Elbow
        (Vector((0.128, 0.00, 0.380)), 0.019), # Wrist
        (Vector((0.134, 0.00, 0.340)), 0.022), # Palm center
    ]
    arm_grid = []
    a_segs = 8
    for (center, rad) in arm_levels:
        row = []
        for i in range(a_segs):
            ang = 2.0 * math.pi * (i / a_segs)
            ax = center.x + rad * math.cos(ang)
            ay = center.y + rad * math.sin(ang) * 0.8
            az = center.z
            row.append(bm_body.verts.new(Vector((ax, ay, az))))
        arm_grid.append(row)

    for li in range(len(arm_levels) - 1):
        for i in range(a_segs):
            v0 = arm_grid[li][i]
            v1 = arm_grid[li][(i + 1) % a_segs]
            v2 = arm_grid[li + 1][(i + 1) % a_segs]
            v3 = arm_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    # Cap hand tip
    hand_tip = bm_body.verts.new(Vector((0.136, 0.00, 0.315)))
    last_row = arm_grid[-1]
    for i in range(a_segs):
        try:
            bm_body.faces.new([last_row[i], last_row[(i + 1) % a_segs], hand_tip])
        except Exception:
            pass

    # --- LEG (Right side X > 0) ---
    leg_levels = [
        # (center, radius_x, radius_y)
        (Vector((0.052, 0.00, 0.360)), 0.038, 0.040), # Hip joint
        (Vector((0.052, 0.00, 0.230)), 0.028, 0.030), # Knee
        (Vector((0.052, 0.00, 0.080)), 0.023, 0.025), # Ankle
    ]
    leg_grid = []
    l_segs = 8
    for (center, rx, ry) in leg_levels:
        row = []
        for i in range(l_segs):
            ang = 2.0 * math.pi * (i / l_segs)
            lx = center.x + rx * math.cos(ang)
            ly = center.y + ry * math.sin(ang)
            lz = center.z
            row.append(bm_body.verts.new(Vector((lx, ly, lz))))
        leg_grid.append(row)

    for li in range(len(leg_levels) - 1):
        for i in range(l_segs):
            v0 = leg_grid[li][i]
            v1 = leg_grid[li][(i + 1) % l_segs]
            v2 = leg_grid[li + 1][(i + 1) % l_segs]
            v3 = leg_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    create_mirrored_object("Kid_Body", bm_body, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # =========================================================================
    # 2. EYEBALLS & PUPILS (Right side X > 0, Mirrored)
    # =========================================================================
    bm_eye = bmesh.new()
    bmesh.ops.create_uvsphere(bm_eye, u_segments=16, v_segments=12, radius=0.0165)
    for v in bm_eye.verts:
        v.co += Vector((0.037, -0.055, 0.752))
    create_mirrored_object("Kid_Eyes", bm_eye, mats["Mat_Eye_White"], subsurf=1, collection=char_col)

    # Iris
    bm_iris = bmesh.new()
    bmesh.ops.create_circle(bm_iris, cap_ends=True, segments=16, radius=0.0105)
    for v in bm_iris.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y)) # orient facing front
        v.co += Vector((0.037, -0.0718, 0.752))
    create_mirrored_object("Kid_Iris", bm_iris, mats["Mat_Eye_Iris"], subsurf=0, collection=char_col)

    # Pupil
    bm_pupil = bmesh.new()
    bmesh.ops.create_circle(bm_pupil, cap_ends=True, segments=12, radius=0.0055)
    for v in bm_pupil.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y))
        v.co += Vector((0.037, -0.0722, 0.752))
    create_mirrored_object("Kid_Pupil", bm_pupil, mats["Mat_Eye_Pupil"], subsurf=0, collection=char_col)

    # Eyebrows (Mirrored)
    bm_brow = bmesh.new()
    bmesh.ops.create_cube(bm_brow, size=0.02)
    for v in bm_brow.verts:
        v.co.x *= 1.25
        v.co.y *= 0.15
        v.co.z *= 0.25
        v.co.z += (v.co.x**2) * -8.0
        v.co += Vector((0.038, -0.071, 0.785))
    create_mirrored_object("Kid_Eyebrows", bm_brow, mats["Mat_Eyebrow"], subsurf=1, collection=char_col)

    # Ears (Mirrored at X = 0.072)
    bm_ear = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ear, u_segments=12, v_segments=10, radius=0.017)
    for v in bm_ear.verts:
        v.co.x *= 0.35
        v.co.y *= 0.85
        v.co.z *= 1.25
        if v.co.x > 0:
            v.co.x *= 0.6
        rot = Matrix.Rotation(0.1, 3, 'X') @ Matrix.Rotation(-0.15, 3, 'Y') @ Matrix.Rotation(0.35, 3, 'Z')
        v.co = rot @ v.co
        v.co += Vector((0.071, -0.005, 0.735))
    create_mirrored_object("Kid_Ears", bm_ear, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # Button nose
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=12, v_segments=8, radius=0.007)
    for v in bm_nose.verts:
        v.co.x *= 1.15
        v.co.y *= 1.25
        v.co.z *= 0.85
        v.co += Vector((0.0, -0.077, 0.718))
    create_mirrored_object("Kid_Nose", bm_nose, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # =========================================================================
    # 3. HAIR (Chunky Stylized Hair Volume - Mirrored on X)
    # Does NOT swallow the face!
    # =========================================================================
    bm_hair = bmesh.new()

    # Hair scalp cap (covers top and back from Z = 0.76 to Z = 0.88)
    bmesh.ops.create_uvsphere(bm_hair, u_segments=16, v_segments=12, radius=0.082)
    for v in list(bm_hair.verts):
        # Keep X >= 0 for mirror, and keep Y > -0.02 or Z > 0.035
        if v.co.x < 0 or (v.co.y < -0.02 and v.co.z < 0.035):
            bm_hair.verts.remove(v)
        else:
            v.co.x *= 1.08
            v.co.y *= 1.10
            v.co.z *= 1.18
            v.co.z += 0.785

    # Chunky stylized hair tufts (X >= 0)
    tuft_specs = [
        # Front bangs swoop
        (0.015, -0.068, 0.835, 0.32, 0.22, -0.45, 0.028, 0.020, 0.040),
        (0.040, -0.052, 0.852, 0.22, 0.32, -0.55, 0.028, 0.022, 0.040),
        # Crown messy peaks (up to Z = 0.96m)
        (0.000, -0.005, 0.915, 0.00, 0.12, -0.10, 0.050, 0.060, 0.052),
        (0.028,  0.010, 0.940, -0.15, 0.22, -0.35, 0.042, 0.050, 0.048),
        # Side tufts over ears
        (0.078, -0.015, 0.795, 0.12, 0.35, -0.22, 0.024, 0.040, 0.042),
        # Back layers
        (0.000, 0.065, 0.810, -0.35, 0.00, 0.00, 0.058, 0.040, 0.055),
        (0.032, 0.058, 0.770, -0.45, 0.20, -0.10, 0.042, 0.032, 0.048),
    ]

    for (cx, cy, cz, rx, ry, rz, sx, sy, sz) in tuft_specs:
        bm_t = bmesh.new()
        bmesh.ops.create_uvsphere(bm_t, u_segments=10, v_segments=8, radius=1.0)
        for cv in bm_t.verts:
            if cv.co.z > 0:
                cv.co.x *= (1.0 - cv.co.z * 0.45)
                cv.co.y *= (1.0 - cv.co.z * 0.45)
            cv.co.x *= sx
            cv.co.y *= sy
            cv.co.z *= sz
            rot = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rz, 3, 'Z')
            cv.co = rot @ cv.co
            cv.co += Vector((cx, cy, cz))
            if cv.co.x < 0 and cx == 0.0:
                cv.co.x = 0.0 # snap midline
        for v in bm_t.verts:
            if v.co.x >= -0.001:
                bm_hair.verts.new(v.co)
        bm_hair.verts.ensure_lookup_table()
        for f in bm_t.faces:
            try:
                bm_hair.faces.new([bm_hair.verts[v.index] for v in f.verts if v.co.x >= -0.001])
            except Exception:
                pass
        bm_t.free()

    create_mirrored_object("Kid_Hair", bm_hair, mats["Mat_Hair"], subsurf=1, collection=char_col)

    # =========================================================================
    # 4. T-SHIRT (White Crewneck, Mirrored on X)
    # =========================================================================
    bm_ts = bmesh.new()
    bmesh.ops.create_cone(bm_ts, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.080, radius2=0.088, depth=0.235)
    for v in list(bm_ts.verts):
        if v.co.x < 0:
            bm_ts.verts.remove(v)
        else:
            v.co.x *= 0.96
            v.co.y *= 0.74
            v.co.z += 0.495
    create_mirrored_object("Kid_TShirt", bm_ts, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # =========================================================================
    # 5. HOODIE / JACKET (Blue, Open Front, Mirrored on X)
    # =========================================================================
    bm_hd = bmesh.new()

    # Jacket torso panel (Right side X > 0, with gap in front X < 0.02)
    bm_jp = bmesh.new()
    bmesh.ops.create_cube(bm_jp, size=0.1)
    for v in bm_jp.verts:
        v.co.x = (v.co.x + 0.05) * 0.88 + 0.018
        v.co.y = v.co.y * 0.82
        v.co.z = v.co.z * 2.35 + 0.495
        if v.co.y < 0:
            v.co.x += 0.016 # open gap
    for v in bm_jp.verts:
        bm_hd.verts.new(v.co)
    bm_jp.free()

    # Short sleeve (loose over upper arm)
    bm_sl = bmesh.new()
    bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.052, radius2=0.045, depth=0.12)
    for v in bm_sl.verts:
        v.co.x += 0.118 + (0.540 - (v.co.z + 0.540)) * 0.45
        v.co.z += 0.540
    for v in bm_sl.verts:
        bm_hd.verts.new(v.co)
    bm_sl.free()

    # Hood on back
    bm_hood = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hood, u_segments=14, v_segments=10, radius=0.068)
    for v in list(bm_hood.verts):
        if v.co.x < 0:
            bm_hood.verts.remove(v)
        else:
            v.co.x *= 1.25
            v.co.y = v.co.y * 0.65 + 0.080
            v.co.z = v.co.z * 0.75 + 0.585
    for v in bm_hood.verts:
        bm_hd.verts.new(v.co)
    bm_hood.free()

    create_mirrored_object("Kid_Hoodie", bm_hd, mats["Mat_Hoodie"], subsurf=1, collection=char_col)

    # Drawstring (white cord hanging in front)
    bm_ds = bmesh.new()
    bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.003, radius2=0.0035, depth=0.10)
    for v in bm_ds.verts:
        v.co += Vector((0.028, -0.068, 0.525))
    create_mirrored_object("Kid_Drawstrings", bm_ds, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # =========================================================================
    # 6. CARGO SHORTS (Khaki, Mirrored on X)
    # =========================================================================
    bm_sh = bmesh.new()

    # Half pelvis waistband
    bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=16,
                          radius1=0.082, radius2=0.085, depth=0.09)
    for v in list(bm_sh.verts):
        if v.co.x < 0:
            bm_sh.verts.remove(v)
        else:
            v.co.x *= 1.05
            v.co.y *= 0.82
            v.co.z += 0.365

    # Short leg
    bm_slg = bmesh.new()
    bmesh.ops.create_cone(bm_slg, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.048, radius2=0.052, depth=0.13)
    for v in bm_slg.verts:
        v.co.x += 0.052
        v.co.z += 0.275
    for v in bm_slg.verts:
        bm_sh.verts.new(v.co)
    bm_slg.free()

    # Cargo pocket with flap
    bm_pock = bmesh.new()
    bmesh.ops.create_cube(bm_pock, size=0.038)
    for v in bm_pock.verts:
        v.co.x = v.co.x * 0.35 + 0.098
        v.co.y = v.co.y * 0.95
        v.co.z = v.co.z * 1.15 + 0.270
    for v in bm_pock.verts:
        bm_sh.verts.new(v.co)
    bm_pock.free()

    create_mirrored_object("Kid_Shorts", bm_sh, mats["Mat_Shorts"], subsurf=1, collection=char_col)

    # =========================================================================
    # 7. SOCKS (White, Mirrored on X)
    # =========================================================================
    bm_sk = bmesh.new()
    bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.026, radius2=0.027, depth=0.055)
    for v in bm_sk.verts:
        v.co.x += 0.050
        v.co.z += 0.085
    create_mirrored_object("Kid_Socks", bm_sk, mats["Mat_Socks"], subsurf=1, collection=char_col)

    # =========================================================================
    # 8. SNEAKERS (Blue skate shoes, White Soles & Toe Caps, Mirrored on X)
    # =========================================================================
    bm_shoe = bmesh.new()

    # Thick White Rubber Sole (flat, 18mm)
    bm_sole = bmesh.new()
    bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in bm_sole.verts:
        v.co.x = v.co.x * 0.72 + 0.058
        v.co.y = v.co.y * 1.60 - 0.015 # 160mm length
        v.co.z = v.co.z * 0.18 + 0.009
    for v in bm_sole.verts:
        bm_shoe.verts.new(v.co)
    bm_sole.free()

    # Rounded White Rubber Toe Cap
    bm_tc = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tc, u_segments=12, v_segments=8, radius=0.034)
    for v in bm_tc.verts:
        v.co.x = v.co.x * 0.95 + 0.058
        v.co.y = v.co.y * 0.80 - 0.068
        v.co.z = v.co.z * 0.65 + 0.022
    for v in bm_tc.verts:
        bm_shoe.verts.new(v.co)
    bm_tc.free()

    # Blue Shoe Upper
    bm_up = bmesh.new()
    bmesh.ops.create_uvsphere(bm_up, u_segments=14, v_segments=10, radius=0.046)
    for v in bm_up.verts:
        v.co.x = v.co.x * 0.82 + 0.058
        v.co.y = v.co.y * 1.62 - 0.015
        v.co.z = max(0.016, v.co.z * 0.82 + 0.038)
    for v in bm_up.verts:
        bm_shoe.verts.new(v.co)
    bm_up.free()

    # White laces
    for lz, ly in [(0.046, -0.045), (0.052, -0.030), (0.058, -0.015)]:
        bm_lc = bmesh.new()
        bmesh.ops.create_cube(bm_lc, size=0.01)
        for v in bm_lc.verts:
            v.co.x = v.co.x * 3.0 + 0.058
            v.co.y = v.co.y * 0.4 + ly
            v.co.z = v.co.z * 0.3 + lz
        for v in bm_lc.verts:
            bm_shoe.verts.new(v.co)
        bm_lc.free()

    create_mirrored_object("Kid_Shoes", bm_shoe, mats["Mat_Shoes_Blue"], subsurf=1, collection=char_col)

    print("Clean mirrored production kid model generated successfully!")

build_production_kid()
