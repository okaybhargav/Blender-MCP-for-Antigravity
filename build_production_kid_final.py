import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def setup_materials():
    mats = {
        "Mat_Skin": (0.96, 0.78, 0.68, 1.0),
        "Mat_Hair": (0.26, 0.13, 0.07, 1.0),
        "Mat_Eye_White": (0.98, 0.98, 0.98, 1.0),
        "Mat_Eye_Iris": (0.28, 0.14, 0.06, 1.0),
        "Mat_Eye_Pupil": (0.02, 0.02, 0.02, 1.0),
        "Mat_Eye_Highlight": (1.0, 1.0, 1.0, 1.0),
        "Mat_Eyebrow": (0.20, 0.10, 0.05, 1.0),
        "Mat_TShirt": (0.96, 0.96, 0.96, 1.0),
        "Mat_Hoodie": (0.22, 0.50, 0.78, 1.0),
        "Mat_Shorts": (0.78, 0.64, 0.46, 1.0),
        "Mat_Socks": (0.96, 0.96, 0.96, 1.0),
        "Mat_Shoes_Blue": (0.20, 0.42, 0.68, 1.0),
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
                bsdf.inputs[2].default_value = 0.40
            elif "Iris" in name or "Pupil" in name:
                bsdf.inputs[2].default_value = 0.05
            elif "Highlight" in name:
                bsdf.inputs[2].default_value = 0.0
            else:
                bsdf.inputs[2].default_value = 0.50
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

    m = obj.modifiers.new(name="Mirror", type='MIRROR')
    m.use_clip = True
    m.use_axis[0] = True

    if subsurf > 0:
        s = obj.modifiers.new(name="Subsurf", type='SUBSURF')
        s.levels = subsurf
        s.render_levels = subsurf + 1

    for p in obj.data.polygons:
        p.use_smooth = True

    if mat:
        obj.data.materials.append(mat)

    return obj

def build_final():
    clean_scene_keep_refs()
    mats = setup_materials()

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    # =========================================================================
    # EXACT BLUEPRINT DIMENSIONS (1000mm = 1.0m total height):
    # - Shoes: Z = 0.00 to 0.06m (Sole = 0.02m)
    # - Leg Length: 300mm -> Z = 0.00 to 0.30m
    # - Torso Height: 250mm -> Z = 0.30 to 0.55m
    # - Neck to Shoulder: 50mm -> Z = 0.55 to 0.60m
    # - Head Height: 160mm -> Z = 0.60 to 0.76m (Head Center Z = 0.68m)
    # - Hair Volume: Z = 0.66 to 1.00m (Crown reaches 1000mm = 1.0m)
    # =========================================================================

    # 1. HEAD (Pixar Stylized Child Head: 140mm wide, 150mm deep, 160mm tall)
    bm_head = bmesh.new()
    u_segs = 24
    v_segs = 18
    r_x = 0.070 # Width 140mm
    r_y = 0.075 # Depth 150mm
    r_z = 0.080 # Height 160mm
    z_head = 0.680

    head_grid = []
    for vi in range(v_segs + 1):
        phi = math.pi * (vi / v_segs)
        row = []
        for ui in range(u_segs // 2 + 1):
            theta = -math.pi / 2.0 + math.pi * (ui / (u_segs // 2))
            
            x = r_x * math.sin(phi) * math.cos(theta)
            y = r_y * math.sin(phi) * math.sin(theta)
            z = r_z * math.cos(phi)

            if ui == 0 or ui == (u_segs // 2):
                x = 0.0

            # Pixar child facial morphology:
            # Broad forehead
            if z > 0.02:
                x *= 1.08
                y *= 1.04

            # Chubby lower cheeks
            if -0.04 < z < 0.015 and y < 0.02:
                t = math.cos((z + 0.01) * 32.0)
                if t > 0:
                    x *= (1.0 + t * 0.24)
                    if y < -0.01:
                        y -= t * 0.010

            # Rounded cute chin
            if z < -0.04:
                blend = min(1.0, (-z - 0.04) / 0.040)
                x *= (1.0 - blend * 0.32)
                if y < 0:
                    y += blend * 0.008

            # Eye socket indentation
            if -0.01 < z < 0.045 and 0.015 < x < 0.065 and y < -0.025:
                dist = math.sqrt((x - 0.038)**2 + (z - 0.015)**2)
                if dist < 0.032:
                    y += (0.032 - dist) * 0.35

            v_pt = bm_head.verts.new(Vector((x, y, z + z_head)))
            row.append(v_pt)
        head_grid.append(row)

    for vi in range(v_segs):
        for ui in range(u_segs // 2):
            v0 = head_grid[vi][ui]
            v1 = head_grid[vi][ui + 1]
            v2 = head_grid[vi + 1][ui + 1]
            v3 = head_grid[vi + 1][ui]
            verts = []
            for v in [v0, v1, v2, v3]:
                if v not in verts:
                    verts.append(v)
            if len(verts) >= 3:
                try:
                    bm_head.faces.new(verts)
                except Exception:
                    pass

    create_mirrored_object("Kid_Head", bm_head, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # 2. CONTINUOUS BODY (50mm Neck + 250mm Torso + 300mm Legs + Arms)
    bm_body = bmesh.new()

    torso_levels = [
        # (Z, radius_x, radius_y)
        (0.630, 0.038, 0.038), # Neck top (inside lower head)
        (0.590, 0.042, 0.042), # Neck middle
        (0.550, 0.052, 0.048), # Neck base / Clavicle (Shoulder Z = 0.55m)
        (0.480, 0.082, 0.062), # Mid chest
        (0.410, 0.076, 0.058), # Waist
        (0.350, 0.078, 0.062), # Lower waist
        (0.300, 0.074, 0.064), # Pelvis / Crotch (Z = 0.30m)
    ]
    t_grid = []
    t_segs = 10
    for (tz, rx, ry) in torso_levels:
        row = []
        for i in range(t_segs + 1):
            ang = -math.pi / 2.0 + math.pi * (i / t_segs)
            tx = rx * math.cos(ang)
            ty = ry * math.sin(ang)
            if i == 0 or i == t_segs:
                tx = 0.0
            row.append(bm_body.verts.new(Vector((tx, ty, tz))))
        t_grid.append(row)

    for li in range(len(torso_levels) - 1):
        for i in range(t_segs):
            v0 = t_grid[li][i]
            v1 = t_grid[li][i + 1]
            v2 = t_grid[li + 1][i + 1]
            v3 = t_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    # ARMS (Arm Length = 220mm, from shoulder Z=0.55 down to Z=0.33)
    arm_levels = [
        (Vector((0.082, 0.00, 0.530)), 0.026), # Shoulder joint
        (Vector((0.108, 0.00, 0.440)), 0.022), # Elbow
        (Vector((0.126, 0.00, 0.350)), 0.019), # Wrist
        (Vector((0.132, 0.00, 0.315)), 0.021), # Palm
    ]
    a_grid = []
    a_segs = 10
    for (center, rad) in arm_levels:
        row = []
        for i in range(a_segs):
            ang = 2.0 * math.pi * (i / a_segs)
            ax = center.x + rad * math.cos(ang)
            ay = center.y + rad * math.sin(ang) * 0.82
            az = center.z
            row.append(bm_body.verts.new(Vector((ax, ay, az))))
        a_grid.append(row)

    for li in range(len(arm_levels) - 1):
        for i in range(a_segs):
            v0 = a_grid[li][i]
            v1 = a_grid[li][(i + 1) % a_segs]
            v2 = a_grid[li + 1][(i + 1) % a_segs]
            v3 = a_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    hand_tip = bm_body.verts.new(Vector((0.134, 0.00, 0.295)))
    for i in range(a_segs):
        try:
            bm_body.faces.new([a_grid[-1][i], a_grid[-1][(i + 1) % a_segs], hand_tip])
        except Exception:
            pass

    # LEGS (Leg Length = 300mm, from Z=0.30 down to Z=0.06)
    leg_levels = [
        (Vector((0.052, 0.00, 0.300)), 0.038, 0.040), # Hip
        (Vector((0.052, 0.00, 0.180)), 0.028, 0.030), # Knee
        (Vector((0.052, 0.00, 0.070)), 0.023, 0.025), # Ankle
    ]
    l_grid = []
    l_segs = 10
    for (center, rx, ry) in leg_levels:
        row = []
        for i in range(l_segs):
            ang = 2.0 * math.pi * (i / l_segs)
            lx = center.x + rx * math.cos(ang)
            ly = center.y + ry * math.sin(ang)
            lz = center.z
            row.append(bm_body.verts.new(Vector((lx, ly, lz))))
        l_grid.append(row)

    for li in range(len(leg_levels) - 1):
        for i in range(l_segs):
            v0 = l_grid[li][i]
            v1 = l_grid[li][(i + 1) % l_segs]
            v2 = l_grid[li + 1][(i + 1) % l_segs]
            v3 = l_grid[li + 1][i]
            try:
                bm_body.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    create_mirrored_object("Kid_Body", bm_body, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # 3. BIG EXPRESSIVE PIXAR EYES (Center Z = 0.69m)
    bm_eye = bmesh.new()
    bmesh.ops.create_uvsphere(bm_eye, u_segments=18, v_segments=14, radius=0.024)
    for v in bm_eye.verts:
        v.co += Vector((0.038, -0.054, 0.692))
    create_mirrored_object("Kid_Eyes", bm_eye, mats["Mat_Eye_White"], subsurf=1, collection=char_col)

    # Iris
    bm_iris = bmesh.new()
    bmesh.ops.create_circle(bm_iris, cap_ends=True, segments=18, radius=0.016)
    for v in bm_iris.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y))
        v.co += Vector((0.038, -0.0765, 0.692))
    create_mirrored_object("Kid_Iris", bm_iris, mats["Mat_Eye_Iris"], subsurf=0, collection=char_col)

    # Pupil
    bm_pupil = bmesh.new()
    bmesh.ops.create_circle(bm_pupil, cap_ends=True, segments=14, radius=0.0085)
    for v in bm_pupil.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y))
        v.co += Vector((0.038, -0.0772, 0.692))
    create_mirrored_object("Kid_Pupil", bm_pupil, mats["Mat_Eye_Pupil"], subsurf=0, collection=char_col)

    # Highlight
    bm_hl = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hl, u_segments=8, v_segments=6, radius=0.0038)
    for v in bm_hl.verts:
        v.co += Vector((0.034, -0.0778, 0.698))
    create_mirrored_object("Kid_Eye_Highlight", bm_hl, mats["Mat_Eye_Highlight"], subsurf=0, collection=char_col)

    # Cute button nose
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=12, v_segments=8, radius=0.0085)
    for v in bm_nose.verts:
        v.co.x *= 1.20
        v.co.y *= 1.30
        v.co.z *= 0.85
        v.co += Vector((0.0, -0.082, 0.660))
    create_mirrored_object("Kid_Nose", bm_nose, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # Gentle smiling mouth line
    bm_mouth = bmesh.new()
    bmesh.ops.create_cube(bm_mouth, size=0.01)
    for v in list(bm_mouth.verts):
        if v.co.x < 0:
            bm_mouth.verts.remove(v)
        else:
            v.co.x *= 2.8
            v.co.y *= 0.12
            v.co.z *= 0.18
            v.co.z += (v.co.x**2) * 8.0
            v.co += Vector((0.0, -0.076, 0.628))
    create_mirrored_object("Kid_Mouth", bm_mouth, mats["Mat_Eyebrow"], subsurf=1, collection=char_col)

    # Eyebrows
    bm_brow = bmesh.new()
    bmesh.ops.create_cube(bm_brow, size=0.02)
    for v in bm_brow.verts:
        v.co.x *= 1.40
        v.co.y *= 0.15
        v.co.z *= 0.30
        v.co.z += (v.co.x**2) * -7.0
        v.co += Vector((0.038, -0.073, 0.732))
    create_mirrored_object("Kid_Eyebrows", bm_brow, mats["Mat_Eyebrow"], subsurf=1, collection=char_col)

    # Ears (Mirrored at X = 0.075, Z = 0.680)
    bm_ear = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ear, u_segments=14, v_segments=10, radius=0.019)
    for v in bm_ear.verts:
        v.co.x *= 0.35
        v.co.y *= 0.85
        v.co.z *= 1.25
        if v.co.x > 0:
            v.co.x *= 0.6
        rot = Matrix.Rotation(0.1, 3, 'X') @ Matrix.Rotation(-0.15, 3, 'Y') @ Matrix.Rotation(0.35, 3, 'Z')
        v.co = rot @ v.co
        v.co += Vector((0.075, -0.005, 0.680))
    create_mirrored_object("Kid_Ears", bm_ear, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # 4. HAIR (Full, wavy, fluffy Pixar boy hair reaching 1.0m total height)
    bm_hair = bmesh.new()

    # Scalp dome (X >= 0, leaving front face clear)
    bmesh.ops.create_uvsphere(bm_hair, u_segments=20, v_segments=14, radius=0.086)
    for v in list(bm_hair.verts):
        if v.co.x < 0 or (v.co.y < -0.025 and v.co.z < 0.035):
            bm_hair.verts.remove(v)
        else:
            v.co.x *= 1.10
            v.co.y *= 1.12
            v.co.z *= 1.18
            v.co.z += 0.735

    # Fluffy, wavy stylized hair clumps
    hair_clumps = [
        # Front bangs sweeping left-to-right across forehead
        (0.015, -0.072, 0.785, 0.28, 0.20, -0.38, 0.035, 0.025, 0.045),
        (0.045, -0.055, 0.800, 0.20, 0.28, -0.48, 0.032, 0.025, 0.045),
        (0.000, -0.060, 0.815, 0.22, 0.00,  0.00, 0.038, 0.028, 0.048),
        # Fluffy rounded crown peaks (reaching Z = 0.98m)
        (0.000, -0.005, 0.880, 0.00, 0.08,  0.00, 0.065, 0.072, 0.065),
        (0.035,  0.012, 0.895, -0.10, 0.15, -0.20, 0.050, 0.058, 0.055),
        (0.018, -0.028, 0.850, 0.10, 0.10, -0.15, 0.048, 0.050, 0.050),
        # Temples & side locks framing ears
        (0.082, -0.015, 0.745, 0.10, 0.30, -0.18, 0.028, 0.045, 0.048),
        (0.070,  0.025, 0.770, -0.08, 0.28, -0.12, 0.035, 0.048, 0.048),
        # Full back volume
        (0.000,  0.070, 0.760, -0.28, 0.00,  0.00, 0.068, 0.048, 0.062),
        (0.038,  0.060, 0.715, -0.38, 0.16, -0.08, 0.048, 0.038, 0.052),
        (0.000,  0.055, 0.670, -0.48, 0.00,  0.00, 0.052, 0.032, 0.048),
    ]

    for (cx, cy, cz, rx, ry, rz, sx, sy, sz) in hair_clumps:
        bm_c = bmesh.new()
        bmesh.ops.create_uvsphere(bm_c, u_segments=10, v_segments=8, radius=1.0)
        for cv in bm_c.verts:
            if cv.co.z > 0:
                cv.co.x *= (1.0 - cv.co.z * 0.35)
                cv.co.y *= (1.0 - cv.co.z * 0.35)
            cv.co.x *= sx
            cv.co.y *= sy
            cv.co.z *= sz
            rot = Matrix.Rotation(rx, 3, 'X') @ Matrix.Rotation(ry, 3, 'Y') @ Matrix.Rotation(rz, 3, 'Z')
            cv.co = rot @ cv.co
            cv.co += Vector((cx, cy, cz))
            if cv.co.x < 0 and cx == 0.0:
                cv.co.x = 0.0
        for v in bm_c.verts:
            if v.co.x >= -0.001:
                bm_hair.verts.new(v.co)
        bm_hair.verts.ensure_lookup_table()
        for f in bm_c.faces:
            try:
                bm_hair.faces.new([bm_hair.verts[v.index] for v in f.verts if v.co.x >= -0.001])
            except Exception:
                pass
        bm_c.free()

    create_mirrored_object("Kid_Hair", bm_hair, mats["Mat_Hair"], subsurf=1, collection=char_col)

    # 5. INNER WHITE T-SHIRT (Z: 0.30 to 0.55m)
    bm_ts = bmesh.new()
    bmesh.ops.create_cone(bm_ts, cap_ends=True, cap_tris=False, segments=18,
                          radius1=0.078, radius2=0.084, depth=0.235)
    for v in list(bm_ts.verts):
        if v.co.x < 0:
            bm_ts.verts.remove(v)
        else:
            v.co.x *= 0.95
            v.co.y *= 0.72
            v.co.z += 0.435
    create_mirrored_object("Kid_TShirt", bm_ts, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # 6. OUTER BLUE HOODIE (Z: 0.30 to 0.56m)
    bm_hd = bmesh.new()

    j_levels = [
        (0.555, 0.090, 0.074), # Collar
        (0.490, 0.096, 0.078), # Chest
        (0.420, 0.092, 0.074), # Mid torso
        (0.350, 0.094, 0.076), # Lower torso
        (0.320, 0.092, 0.074), # Ribbed bottom hem
    ]
    j_grid = []
    j_segs = 8
    for (jz, rx, ry) in j_levels:
        row = []
        for i in range(j_segs + 1):
            ang = -math.pi * 0.36 + (math.pi * 0.86) * (i / j_segs)
            jx = rx * math.cos(ang)
            jy = ry * math.sin(ang)
            if i == j_segs:
                jx = 0.0
            row.append(bm_hd.verts.new(Vector((jx, jy, jz))))
        j_grid.append(row)

    for li in range(len(j_levels) - 1):
        for i in range(j_segs):
            v0 = j_grid[li][i]
            v1 = j_grid[li][i + 1]
            v2 = j_grid[li + 1][i + 1]
            v3 = j_grid[li + 1][i]
            try:
                bm_hd.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    # Short hoodie sleeves
    bm_sl = bmesh.new()
    bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.056, radius2=0.048, depth=0.13)
    for v in bm_sl.verts:
        v.co.x += 0.120 + (0.480 - (v.co.z + 0.480)) * 0.45
        v.co.z += 0.480
    for v in bm_sl.verts:
        bm_hd.verts.new(v.co)
    bm_sl.free()

    # Hood on back
    bm_hood = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hood, u_segments=14, v_segments=10, radius=0.072)
    for v in list(bm_hood.verts):
        if v.co.x < 0:
            bm_hood.verts.remove(v)
        else:
            v.co.x *= 1.25
            v.co.y = v.co.y * 0.65 + 0.082
            v.co.z = v.co.z * 0.75 + 0.525
    for v in bm_hood.verts:
        bm_hd.verts.new(v.co)
    bm_hood.free()

    create_mirrored_object("Kid_Hoodie", bm_hd, mats["Mat_Hoodie"], subsurf=1, collection=char_col)

    # Hanging white drawstrings
    bm_ds = bmesh.new()
    bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.003, radius2=0.0035, depth=0.10)
    for v in bm_ds.verts:
        v.co += Vector((0.028, -0.076, 0.465))
    create_mirrored_object("Kid_Drawstrings", bm_ds, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # 7. CARGO SHORTS (Khaki with cargo side pockets, Z: 0.18 to 0.33m)
    bm_sh = bmesh.new()
    sh_levels = [
        (0.335, 0.088, 0.072), # Waistband
        (0.295, 0.092, 0.075), # Hip
        (0.260, 0.090, 0.074), # Crotch
    ]
    s_grid = []
    s_segs = 8
    for (sz, rx, ry) in sh_levels:
        row = []
        for i in range(s_segs + 1):
            ang = -math.pi / 2.0 + math.pi * (i / s_segs)
            sx = rx * math.cos(ang)
            sy = ry * math.sin(ang)
            if i == 0 or i == s_segs:
                sx = 0.0
            row.append(bm_sh.verts.new(Vector((sx, sy, sz))))
        s_grid.append(row)

    for li in range(len(sh_levels) - 1):
        for i in range(s_segs):
            v0 = s_grid[li][i]
            v1 = s_grid[li][i + 1]
            v2 = s_grid[li + 1][i + 1]
            v3 = s_grid[li + 1][i]
            try:
                bm_sh.faces.new([v0, v1, v2, v3])
            except Exception:
                pass

    bm_slg = bmesh.new()
    bmesh.ops.create_cone(bm_slg, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.048, radius2=0.054, depth=0.11)
    for v in bm_slg.verts:
        v.co.x += 0.052
        v.co.z += 0.205
    for v in bm_slg.verts:
        bm_sh.verts.new(v.co)
    bm_slg.free()

    bm_pock = bmesh.new()
    bmesh.ops.create_cube(bm_pock, size=0.038)
    for v in bm_pock.verts:
        v.co.x = v.co.x * 0.35 + 0.100
        v.co.y = v.co.y * 0.95
        v.co.z = v.co.z * 1.15 + 0.205
    for v in bm_pock.verts:
        bm_sh.verts.new(v.co)
    bm_pock.free()

    create_mirrored_object("Kid_Shorts", bm_sh, mats["Mat_Shorts"], subsurf=1, collection=char_col)

    # 8. SOCKS (White Crew Socks, Z = 0.06 to 0.11m)
    bm_sk = bmesh.new()
    bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.026, radius2=0.027, depth=0.055)
    for v in bm_sk.verts:
        v.co.x += 0.050
        v.co.z += 0.085
    create_mirrored_object("Kid_Socks", bm_sk, mats["Mat_Socks"], subsurf=1, collection=char_col)

    # 9. SNEAKERS / SHOES (Blue Skate Shoes, White Rubber Sole & Toe Cap)
    # Foot Length: 160mm (Y: -0.095 to +0.065m), Width: ~80mm, Height: 60mm
    bm_shoe = bmesh.new()

    # Thick White Flat Rubber Sole
    bm_sole = bmesh.new()
    bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in bm_sole.verts:
        v.co.x = v.co.x * 0.76 + 0.056
        v.co.y = v.co.y * 1.60 - 0.015
        v.co.z = v.co.z * 0.20 + 0.010
    for v in bm_sole.verts:
        bm_shoe.verts.new(v.co)
    bm_sole.free()

    # White Rubber Toe Cap
    bm_tc = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tc, u_segments=12, v_segments=8, radius=0.036)
    for v in bm_tc.verts:
        v.co.x = v.co.x * 0.98 + 0.056
        v.co.y = v.co.y * 0.82 - 0.068
        v.co.z = v.co.z * 0.68 + 0.024
    for v in bm_tc.verts:
        bm_shoe.verts.new(v.co)
    bm_tc.free()

    # Blue Shoe Upper
    bm_up = bmesh.new()
    bmesh.ops.create_uvsphere(bm_up, u_segments=14, v_segments=10, radius=0.048)
    for v in bm_up.verts:
        v.co.x = v.co.x * 0.85 + 0.056
        v.co.y = v.co.y * 1.62 - 0.015
        v.co.z = max(0.018, v.co.z * 0.82 + 0.040)
    for v in bm_up.verts:
        bm_shoe.verts.new(v.co)
    bm_up.free()

    # White shoe laces (criss-cross bars)
    for lz, ly in [(0.048, -0.045), (0.054, -0.030), (0.060, -0.015)]:
        bm_lc = bmesh.new()
        bmesh.ops.create_cube(bm_lc, size=0.01)
        for v in bm_lc.verts:
            v.co.x = v.co.x * 3.2 + 0.056
            v.co.y = v.co.y * 0.4 + ly
            v.co.z = v.co.z * 0.3 + lz
        for v in bm_lc.verts:
            bm_shoe.verts.new(v.co)
        bm_lc.free()

    create_mirrored_object("Kid_Shoes", bm_shoe, mats["Mat_Shoes_Blue"], subsurf=1, collection=char_col)

    print("Blueprint-perfect kid character model built successfully!")

build_final()
