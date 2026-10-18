import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def setup_materials():
    mats = {
        "Mat_Skin": (0.96, 0.78, 0.68, 1.0),
        "Mat_Hair": (0.26, 0.13, 0.07, 1.0),
        "Mat_Eye_White": (0.98, 0.98, 0.98, 1.0),
        "Mat_Eye_Iris": (0.26, 0.13, 0.06, 1.0),
        "Mat_Eye_Pupil": (0.03, 0.03, 0.03, 1.0),
        "Mat_Eye_Highlight": (1.0, 1.0, 1.0, 1.0),
        "Mat_Eyebrow": (0.20, 0.10, 0.05, 1.0),
        "Mat_TShirt": (0.95, 0.95, 0.95, 1.0),
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

def build_v3():
    clean_scene_keep_refs()
    mats = setup_materials()

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    # =========================================================================
    # 1. HEAD (Pixar / Stylized Child Proportions)
    # Head Center: Z = 0.74m
    # Head Height: 160mm (Z: 0.66 to 0.82m)
    # Head Width: 140mm (X: -0.07 to +0.07m)
    # Head Depth: 150mm (Y: -0.075 to +0.075m)
    # Cute round jaw, chubby cheeks, soft small chin
    # =========================================================================
    bm_head = bmesh.new()
    u_segs = 20
    v_segs = 16
    r_x = 0.070
    r_y = 0.075
    r_z = 0.080
    z_head = 0.740

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

            # Pixar child head shaping:
            # 1. Round, soft jaw (NOT pointed)
            if z < -0.02:
                # Keep jaw wide and cute
                jaw_w = 1.0 - 0.15 * ((-z - 0.02) / 0.06)
                x *= max(0.70, jaw_w)
                # Soft chin curve in front
                if y < 0:
                    y += 0.004

            # 2. Chubby cheeks (expanding mid/lower cheeks)
            if -0.035 < z < 0.025 and y < 0.02:
                t = math.cos((z + 0.005) * 32.0)
                if t > 0:
                    x *= (1.0 + t * 0.16)
                    if y < -0.01:
                        y -= t * 0.008

            # 3. Eye socket contouring
            if -0.01 < z < 0.040 and 0.015 < x < 0.060 and y < -0.025:
                dist = math.sqrt((x - 0.037)**2 + (z - 0.015)**2)
                if dist < 0.028:
                    y += (0.028 - dist) * 0.32

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

    # =========================================================================
    # 2. NECK & TORSO (Skin Base)
    # Neck: 50mm (Z: 0.61 to 0.66m), Torso: 250mm (Z: 0.36 to 0.61m)
    # =========================================================================
    bm_body = bmesh.new()

    torso_levels = [
        # (Z, radius_x, radius_y)
        (0.665, 0.033, 0.034), # Neck top (inside head base)
        (0.635, 0.035, 0.036), # Neck middle
        (0.610, 0.042, 0.042), # Neck base / Clavicle
        (0.560, 0.082, 0.062), # Chest
        (0.485, 0.076, 0.058), # Waist
        (0.410, 0.078, 0.062), # Lower waist
        (0.360, 0.074, 0.064), # Pelvis / Crotch
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

    # --- ARMS (Relaxed A-pose matching blueprint) ---
    arm_levels = [
        (Vector((0.082, 0.00, 0.570)), 0.026), # Shoulder
        (Vector((0.108, 0.00, 0.480)), 0.022), # Elbow
        (Vector((0.126, 0.00, 0.390)), 0.019), # Wrist
        (Vector((0.132, 0.00, 0.345)), 0.021), # Palm
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

    # Thumb & Hand tip
    hand_tip = bm_body.verts.new(Vector((0.134, 0.00, 0.320)))
    last_a = a_grid[-1]
    for i in range(a_segs):
        try:
            bm_body.faces.new([last_a[i], last_a[(i + 1) % a_segs], hand_tip])
        except Exception:
            pass

    # --- LEGS (X > 0, from hip Z=0.36 to ankle Z=0.08) ---
    leg_levels = [
        (Vector((0.052, 0.00, 0.360)), 0.038, 0.040), # Hip
        (Vector((0.052, 0.00, 0.230)), 0.028, 0.030), # Knee
        (Vector((0.052, 0.00, 0.085)), 0.023, 0.025), # Ankle
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

    # =========================================================================
    # 3. BIG EXPRESSIVE PIXAR EYES (Mirrored)
    # Diameter ~ 46mm, expressive brown iris, specular reflection
    # =========================================================================
    bm_eye = bmesh.new()
    bmesh.ops.create_uvsphere(bm_eye, u_segments=18, v_segments=14, radius=0.022)
    for v in bm_eye.verts:
        v.co += Vector((0.037, -0.052, 0.748))
    create_mirrored_object("Kid_Eyes", bm_eye, mats["Mat_Eye_White"], subsurf=1, collection=char_col)

    # Iris (Large, beautiful cartoon brown iris)
    bm_iris = bmesh.new()
    bmesh.ops.create_circle(bm_iris, cap_ends=True, segments=18, radius=0.0145)
    for v in bm_iris.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y))
        v.co += Vector((0.037, -0.0735, 0.748))
    create_mirrored_object("Kid_Iris", bm_iris, mats["Mat_Eye_Iris"], subsurf=0, collection=char_col)

    # Pupil
    bm_pupil = bmesh.new()
    bmesh.ops.create_circle(bm_pupil, cap_ends=True, segments=14, radius=0.0075)
    for v in bm_pupil.verts:
        v.co = Vector((v.co.x, 0.0, v.co.y))
        v.co += Vector((0.037, -0.0740, 0.748))
    create_mirrored_object("Kid_Pupil", bm_pupil, mats["Mat_Eye_Pupil"], subsurf=0, collection=char_col)

    # Highlight (Cute anime/Pixar eye glint)
    bm_hl = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hl, u_segments=8, v_segments=6, radius=0.0035)
    for v in bm_hl.verts:
        v.co += Vector((0.034, -0.0745, 0.752))
    create_mirrored_object("Kid_Eye_Highlight", bm_hl, mats["Mat_Eye_Highlight"], subsurf=0, collection=char_col)

    # Cute button nose
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=12, v_segments=8, radius=0.008)
    for v in bm_nose.verts:
        v.co.x *= 1.15
        v.co.y *= 1.30
        v.co.z *= 0.85
        v.co += Vector((0.0, -0.077, 0.718))
    create_mirrored_object("Kid_Nose", bm_nose, mats["Mat_Skin"], subsurf=1, collection=char_col)

    # Eyebrows
    bm_brow = bmesh.new()
    bmesh.ops.create_cube(bm_brow, size=0.02)
    for v in bm_brow.verts:
        v.co.x *= 1.35
        v.co.y *= 0.15
        v.co.z *= 0.28
        v.co.z += (v.co.x**2) * -7.5
        v.co += Vector((0.038, -0.070, 0.785))
    create_mirrored_object("Kid_Eyebrows", bm_brow, mats["Mat_Eyebrow"], subsurf=1, collection=char_col)

    # Ears (Cupped, stylized child ears)
    bm_ear = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ear, u_segments=14, v_segments=10, radius=0.018)
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

    # =========================================================================
    # 4. HAIR (Stylized Pixar / Disney Wavy Hair)
    # Soft, layered, chunky curls with front bangs sweeping across forehead
    # Total height reaches Z = 0.98m (matches 1000mm total height)
    # =========================================================================
    bm_hair = bmesh.new()

    # Scalp base dome (X >= 0, leaving face completely clear)
    bmesh.ops.create_uvsphere(bm_hair, u_segments=18, v_segments=14, radius=0.082)
    for v in list(bm_hair.verts):
        if v.co.x < 0 or (v.co.y < -0.025 and v.co.z < 0.035):
            bm_hair.verts.remove(v)
        else:
            v.co.x *= 1.08
            v.co.y *= 1.10
            v.co.z *= 1.15
            v.co.z += 0.785

    # Organic layered hair clumps (Pixar style)
    hair_clumps = [
        # Front bangs swoop (forehead, sweeping left-to-right)
        (0.015, -0.068, 0.835, 0.30, 0.20, -0.40, 0.032, 0.022, 0.042),
        (0.042, -0.052, 0.850, 0.22, 0.30, -0.50, 0.030, 0.022, 0.042),
        (0.000, -0.055, 0.865, 0.25, 0.00,  0.00, 0.035, 0.025, 0.045),
        # Crown & Top waves (reaching Z = 0.97m)
        (0.000,  0.000, 0.920, 0.00, 0.10,  0.00, 0.055, 0.065, 0.055),
        (0.032,  0.012, 0.935, -0.12, 0.18, -0.25, 0.045, 0.055, 0.050),
        (0.015, -0.025, 0.900, 0.12, 0.12, -0.20, 0.042, 0.045, 0.048),
        # Temples & Above-Ear tufts
        (0.076, -0.015, 0.795, 0.10, 0.32, -0.20, 0.026, 0.042, 0.044),
        (0.065,  0.025, 0.820, -0.10, 0.30, -0.15, 0.032, 0.045, 0.045),
        # Back skull volume
        (0.000,  0.065, 0.810, -0.30, 0.00,  0.00, 0.062, 0.045, 0.058),
        (0.035,  0.055, 0.770, -0.40, 0.18, -0.10, 0.045, 0.035, 0.050),
        (0.000,  0.052, 0.725, -0.50, 0.00,  0.00, 0.048, 0.030, 0.045),
    ]

    for (cx, cy, cz, rx, ry, rz, sx, sy, sz) in hair_clumps:
        bm_c = bmesh.new()
        bmesh.ops.create_uvsphere(bm_c, u_segments=10, v_segments=8, radius=1.0)
        for cv in bm_c.verts:
            if cv.co.z > 0:
                cv.co.x *= (1.0 - cv.co.z * 0.40)
                cv.co.y *= (1.0 - cv.co.z * 0.40)
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

    # =========================================================================
    # 5. INNER T-SHIRT (White Crewneck)
    # Clean cylindrical mesh fitted over torso (Z: 0.38 to 0.615m)
    # =========================================================================
    bm_ts = bmesh.new()
    bmesh.ops.create_cone(bm_ts, cap_ends=True, cap_tris=False, segments=18,
                          radius1=0.078, radius2=0.084, depth=0.235)
    for v in list(bm_ts.verts):
        if v.co.x < 0:
            bm_ts.verts.remove(v)
        else:
            v.co.x *= 0.95
            v.co.y *= 0.72
            v.co.z += 0.495
    create_mirrored_object("Kid_TShirt", bm_ts, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # =========================================================================
    # 6. OUTER HOODIE / JACKET (Blue, Short-Sleeved, Open Front)
    # MUST BE ON THE OUTSIDE OF THE T-SHIRT! Radius = 0.092m
    # =========================================================================
    bm_hd = bmesh.new()

    # Jacket torso (Right half X >= 0, open front gap from X: 0 to 0.025)
    j_levels = [
        # (Z, radius_x, radius_y)
        (0.615, 0.088, 0.072), # Collar
        (0.550, 0.094, 0.075), # Chest
        (0.480, 0.090, 0.072), # Mid torso
        (0.410, 0.092, 0.074), # Lower torso
        (0.380, 0.090, 0.072), # Ribbed bottom hem
    ]
    j_grid = []
    j_segs = 8
    for (jz, rx, ry) in j_levels:
        row = []
        # angle from -pi/3 (open front gap) to +pi/2 (back midline)
        for i in range(j_segs + 1):
            ang = -math.pi * 0.38 + (math.pi * 0.88) * (i / j_segs)
            jx = rx * math.cos(ang)
            jy = ry * math.sin(ang)
            if i == j_segs:
                jx = 0.0 # snap back midline
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

    # Short sleeves (hanging over upper arms)
    bm_sl = bmesh.new()
    bmesh.ops.create_cone(bm_sl, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.055, radius2=0.048, depth=0.12)
    for v in bm_sl.verts:
        v.co.x += 0.118 + (0.540 - (v.co.z + 0.540)) * 0.45
        v.co.z += 0.540
    for v in bm_sl.verts:
        bm_hd.verts.new(v.co)
    bm_sl.free()

    # Hood resting on back of neck
    bm_hood = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hood, u_segments=14, v_segments=10, radius=0.072)
    for v in list(bm_hood.verts):
        if v.co.x < 0:
            bm_hood.verts.remove(v)
        else:
            v.co.x *= 1.25
            v.co.y = v.co.y * 0.65 + 0.082
            v.co.z = v.co.z * 0.75 + 0.585
    for v in bm_hood.verts:
        bm_hd.verts.new(v.co)
    bm_hood.free()

    create_mirrored_object("Kid_Hoodie", bm_hd, mats["Mat_Hoodie"], subsurf=1, collection=char_col)

    # Hanging white drawstrings
    bm_ds = bmesh.new()
    bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.003, radius2=0.0035, depth=0.10)
    for v in bm_ds.verts:
        v.co += Vector((0.028, -0.075, 0.525))
    create_mirrored_object("Kid_Drawstrings", bm_ds, mats["Mat_TShirt"], subsurf=1, collection=char_col)

    # =========================================================================
    # 7. CARGO SHORTS (Khaki with side cargo pockets)
    # Waist Z = 0.39m down to knee Z = 0.22m
    # =========================================================================
    bm_sh = bmesh.new()

    sh_levels = [
        # (Z, radius_x, radius_y)
        (0.395, 0.088, 0.072), # Waistband
        (0.355, 0.092, 0.075), # Hip
        (0.320, 0.090, 0.074), # Crotch
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

    # Loose short leg (Z: 0.22 to 0.32)
    bm_slg = bmesh.new()
    bmesh.ops.create_cone(bm_slg, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.048, radius2=0.054, depth=0.11)
    for v in bm_slg.verts:
        v.co.x += 0.052
        v.co.z += 0.265
    for v in bm_slg.verts:
        bm_sh.verts.new(v.co)
    bm_slg.free()

    # Cargo pocket with flap on side
    bm_pock = bmesh.new()
    bmesh.ops.create_cube(bm_pock, size=0.038)
    for v in bm_pock.verts:
        v.co.x = v.co.x * 0.35 + 0.100
        v.co.y = v.co.y * 0.95
        v.co.z = v.co.z * 1.15 + 0.265
    for v in bm_pock.verts:
        bm_sh.verts.new(v.co)
    bm_pock.free()

    create_mirrored_object("Kid_Shorts", bm_sh, mats["Mat_Shorts"], subsurf=1, collection=char_col)

    # =========================================================================
    # 8. SOCKS (White Crew Socks)
    # =========================================================================
    bm_sk = bmesh.new()
    bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=12,
                          radius1=0.026, radius2=0.027, depth=0.055)
    for v in bm_sk.verts:
        v.co.x += 0.050
        v.co.z += 0.085
    create_mirrored_object("Kid_Socks", bm_sk, mats["Mat_Socks"], subsurf=1, collection=char_col)

    # =========================================================================
    # 9. SNEAKERS / SHOES (Blue Skate Shoes, White Rubber Sole & Toe Cap)
    # Foot Length: 160mm (Y: -0.09 to +0.07m), Sole thickness: 18mm
    # =========================================================================
    bm_shoe = bmesh.new()

    # White Flat Rubber Sole
    bm_sole = bmesh.new()
    bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in bm_sole.verts:
        v.co.x = v.co.x * 0.72 + 0.056
        v.co.y = v.co.y * 1.60 - 0.015
        v.co.z = v.co.z * 0.18 + 0.009
    for v in bm_sole.verts:
        bm_shoe.verts.new(v.co)
    bm_sole.free()

    # White Rubber Toe Cap
    bm_tc = bmesh.new()
    bmesh.ops.create_uvsphere(bm_tc, u_segments=12, v_segments=8, radius=0.034)
    for v in bm_tc.verts:
        v.co.x = v.co.x * 0.95 + 0.056
        v.co.y = v.co.y * 0.80 - 0.068
        v.co.z = v.co.z * 0.65 + 0.022
    for v in bm_tc.verts:
        bm_shoe.verts.new(v.co)
    bm_tc.free()

    # Blue Shoe Upper
    bm_up = bmesh.new()
    bmesh.ops.create_uvsphere(bm_up, u_segments=14, v_segments=10, radius=0.046)
    for v in bm_up.verts:
        v.co.x = v.co.x * 0.82 + 0.056
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
            v.co.x = v.co.x * 3.0 + 0.056
            v.co.y = v.co.y * 0.4 + ly
            v.co.z = v.co.z * 0.3 + lz
        for v in bm_lc.verts:
            bm_shoe.verts.new(v.co)
        bm_lc.free()

    create_mirrored_object("Kid_Shoes", bm_shoe, mats["Mat_Shoes_Blue"], subsurf=1, collection=char_col)

    print("Kid Model v3 built successfully with distinct layered clothing and Pixar features!")

build_v3()
