import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def build_production_kid():
    # 1. Clean existing Kid objects
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Kid_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    # 2. Setup Materials
    mats_def = {
        "Mat_Skin": ((0.96, 0.78, 0.68, 1.0), 0.35),
        "Mat_Hair": ((0.24, 0.12, 0.06, 1.0), 0.45),
        "Mat_Eye_White": ((0.98, 0.98, 0.98, 1.0), 0.10),
        "Mat_Eye_Iris": ((0.22, 0.11, 0.04, 1.0), 0.05),
        "Mat_Eye_Pupil": ((0.01, 0.01, 0.01, 1.0), 0.05),
        "Mat_Eye_Highlight": ((1.0, 1.0, 1.0, 1.0), 0.00),
        "Mat_Eyebrow": ((0.18, 0.09, 0.04, 1.0), 0.60),
        "Mat_Eyelid": ((0.20, 0.10, 0.05, 1.0), 0.40),
        "Mat_TShirt": ((0.96, 0.96, 0.96, 1.0), 0.50),
        "Mat_Hoodie": ((0.23, 0.50, 0.76, 1.0), 0.45),
        "Mat_Hoodie_Dark": ((0.18, 0.42, 0.66, 1.0), 0.45),
        "Mat_Shorts": ((0.77, 0.65, 0.49, 1.0), 0.60),
        "Mat_Socks": ((0.95, 0.95, 0.95, 1.0), 0.60),
        "Mat_Shoes_Blue": ((0.22, 0.46, 0.72, 1.0), 0.40),
        "Mat_Shoes_White": ((0.96, 0.96, 0.96, 1.0), 0.30),
        "Mat_Shoes_Gum": ((0.58, 0.38, 0.22, 1.0), 0.50),
        "Mat_Bear_Brown": ((0.75, 0.50, 0.30, 1.0), 0.50),
    }

    mats = {}
    for name, (color, rough) in mats_def.items():
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = color
            bsdf.inputs["Roughness"].default_value = rough
        mat.diffuse_color = color
        mats[name] = mat

    def make_obj(name, bm, mat, mirror=True, subsurf=1):
        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(name, mesh)
        char_col.objects.link(obj)
        if mirror:
            m = obj.modifiers.new("Mirror", 'MIRROR')
            m.use_clip = True
            m.use_axis[0] = True
        if subsurf > 0:
            s = obj.modifiers.new("Subsurf", 'SUBSURF')
            s.levels = subsurf
            s.render_levels = subsurf + 1
        for p in obj.data.polygons:
            p.use_smooth = True
        if mat:
            obj.data.materials.append(mat)
        return obj

    def add_curved_tube(bm_target, points_with_radii, segs=8):
        rings = []
        for (pt, rad, asp) in points_with_radii:
            ring = []
            for i in range(segs):
                ang = 2.0 * math.pi * (i / segs)
                rx = rad * math.cos(ang)
                ry = rad * math.sin(ang) * asp
                ring.append(bm_target.verts.new(pt + Vector((rx, ry, 0.0))))
            rings.append(ring)
        for r in range(len(rings) - 1):
            for i in range(segs):
                v0 = rings[r][i]
                v1 = rings[r][(i + 1) % segs]
                v2 = rings[r + 1][(i + 1) % segs]
                v3 = rings[r + 1][i]
                bm_target.faces.new([v0, v1, v2, v3])
        tip_pt = points_with_radii[-1][0]
        tip_v = bm_target.verts.new(tip_pt)
        for i in range(segs):
            bm_target.faces.new([rings[-1][i], rings[-1][(i + 1) % segs], tip_v])
        root_pt = points_with_radii[0][0]
        root_v = bm_target.verts.new(root_pt)
        for i in range(segs):
            bm_target.faces.new([rings[0][(i + 1) % segs], rings[0][i], root_v])

    # =========================================================================
    # 1. HEAD & FACIAL FEATURES
    # =========================================================================
    z_head = 0.790

    # Head Base Mesh (Pixar Stylized Infant/Child morphology)
    bm_head = bmesh.new()
    bmesh.ops.create_uvsphere(bm_head, u_segments=32, v_segments=24, radius=1.0)
    for v in list(bm_head.verts):
        if v.co.x < -0.0001:
            bm_head.verts.remove(v)
        elif v.co.x <= 0.0001:
            v.co.x = 0.0

    for v in bm_head.verts:
        x, y, z = v.co.x, v.co.y, v.co.z
        x *= 0.075
        y *= 0.080
        z *= 0.095

        # Forehead
        if z > 0.015:
            x *= 1.06
            y *= 1.04
            if y < 0:
                y -= 0.005 * (z / 0.095)

        # Chubby cheeks
        if -0.055 < z < 0.02 and y < 0.025:
            factor = math.cos((z + 0.02) * 28.0)
            if factor > 0:
                x *= (1.0 + factor * 0.22)
                if y < -0.01:
                    y -= factor * 0.016

        # Gentle rounded chin
        if z < -0.045:
            blend = min(1.0, (-z - 0.045) / 0.050)
            x *= (1.0 - blend * 0.32)
            if y < 0:
                y += blend * 0.008

        # Eye sockets
        if -0.020 < z < 0.045 and 0.020 < x < 0.065 and y < -0.020:
            d = math.sqrt((x - 0.040)**2 + (z - 0.010)**2)
            if d < 0.035:
                y += (0.035 - d) * 0.48

        v.co = Vector((x, y, z + z_head))

    make_obj("Kid_Head", bm_head, mats["Mat_Skin"], mirror=True, subsurf=1)

    # Nose (Button nose)
    bm_nose = bmesh.new()
    bmesh.ops.create_uvsphere(bm_nose, u_segments=16, v_segments=12, radius=1.0)
    for v in list(bm_nose.verts):
        if v.co.x < -0.0001:
            bm_nose.verts.remove(v)
        elif v.co.x <= 0.0001:
            v.co.x = 0.0
    for v in bm_nose.verts:
        v.co.x *= 0.010
        v.co.y *= 0.012
        v.co.z *= 0.009
        v.co += Vector((0.0, -0.088, 0.748))
    make_obj("Kid_Nose", bm_nose, mats["Mat_Skin"], mirror=True, subsurf=1)

    # Mouth (Closed pleasant smile)
    bm_mouth = bmesh.new()
    m_steps = 10
    m_verts = []
    for i in range(m_steps + 1):
        t = i / m_steps
        mx = t * 0.025
        mz = 0.718 + (t**2) * 0.007
        my = -0.082 + (t**2) * 0.009
        v_top = bm_mouth.verts.new(Vector((mx, my, mz + 0.002)))
        v_bot = bm_mouth.verts.new(Vector((mx, my, mz - 0.002)))
        m_verts.append((v_top, v_bot))
    for i in range(m_steps):
        t0, b0 = m_verts[i]
        t1, b1 = m_verts[i+1]
        bm_mouth.faces.new([t0, t1, b1, b0])
    bmesh.ops.solidify(bm_mouth, geom=bm_mouth.faces[:] + bm_mouth.verts[:], thickness=-0.003)
    make_obj("Kid_Mouth", bm_mouth, mats["Mat_Eyelid"], mirror=True, subsurf=1)

    # Eyes: Eyeballs, Irises, Pupils, Highlights, Lashes
    eye_center = Vector((0.040, -0.054, 0.792))

    bm_sclera = bmesh.new()
    bmesh.ops.create_uvsphere(bm_sclera, u_segments=20, v_segments=16, radius=0.022)
    for v in bm_sclera.verts:
        v.co.x *= 0.95
        v.co.y *= 0.90
        v.co.z *= 1.05
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center
    make_obj("Kid_Eye_White", bm_sclera, mats["Mat_Eye_White"], mirror=True, subsurf=1)

    bm_iris = bmesh.new()
    bmesh.ops.create_circle(bm_iris, cap_ends=True, segments=24, radius=0.0145)
    for v in bm_iris.verts:
        d = math.sqrt(v.co.x**2 + v.co.y**2)
        vz = - (d**2) * 6.0
        v.co = Vector((v.co.x, vz, v.co.y))
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center + Vector((0.0, -0.0195, 0.0))
    make_obj("Kid_Eye_Iris", bm_iris, mats["Mat_Eye_Iris"], mirror=True, subsurf=0)

    bm_pupil = bmesh.new()
    bmesh.ops.create_circle(bm_pupil, cap_ends=True, segments=20, radius=0.008)
    for v in bm_pupil.verts:
        v.co = Vector((v.co.x, -0.0006, v.co.y))
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center + Vector((0.0, -0.0198, 0.0))
    make_obj("Kid_Eye_Pupil", bm_pupil, mats["Mat_Eye_Pupil"], mirror=True, subsurf=0)

    bm_hl = bmesh.new()
    res1 = bmesh.ops.create_uvsphere(bm_hl, u_segments=10, v_segments=8, radius=0.0038)
    for v in res1['verts']:
        v.co += eye_center + Vector((-0.0045, -0.0212, 0.0065))
    res2 = bmesh.ops.create_uvsphere(bm_hl, u_segments=8, v_segments=6, radius=0.0020)
    for v in res2['verts']:
        v.co += eye_center + Vector((0.0055, -0.0205, -0.0055))
    make_obj("Kid_Eye_Highlights", bm_hl, mats["Mat_Eye_Highlight"], mirror=True, subsurf=0)

    bm_lash = bmesh.new()
    l_steps = 10
    l_verts = []
    for i in range(l_steps + 1):
        t = i / l_steps
        ang = math.pi * (0.05 + 0.90 * t)
        lx = eye_center.x + 0.021 * math.cos(ang)
        lz = eye_center.z + 0.021 * math.sin(ang) * 1.08
        ly = eye_center.y - 0.0185 + math.cos((t - 0.5) * math.pi) * -0.004
        w = math.sin(t * math.pi) * 0.0045 + 0.0018
        v_top = bm_lash.verts.new(Vector((lx, ly - 0.001, lz + w)))
        v_bot = bm_lash.verts.new(Vector((lx, ly, lz)))
        l_verts.append((v_top, v_bot))
    for i in range(l_steps):
        bm_lash.faces.new([l_verts[i][0], l_verts[i+1][0], l_verts[i+1][1], l_verts[i][1]])
    bmesh.ops.solidify(bm_lash, geom=bm_lash.faces[:] + bm_lash.verts[:], thickness=0.002)
    make_obj("Kid_Eyelashes", bm_lash, mats["Mat_Eyelid"], mirror=True, subsurf=1)

    # Eyebrows
    bm_brow = bmesh.new()
    b_steps = 8
    b_verts = []
    for i in range(b_steps + 1):
        t = i / b_steps
        bx = 0.018 + t * 0.042
        bz = 0.832 + math.sin(t * math.pi * 0.85) * 0.014
        by = -0.072 - math.sin(t * math.pi) * 0.005
        w = (1.0 - t * 0.45) * 0.0055
        v_t = bm_brow.verts.new(Vector((bx, by, bz + w)))
        v_b = bm_brow.verts.new(Vector((bx, by, bz - w)))
        b_verts.append((v_t, v_b))
    for i in range(b_steps):
        bm_brow.faces.new([b_verts[i][0], b_verts[i+1][0], b_verts[i+1][1], b_verts[i][1]])
    bmesh.ops.solidify(bm_brow, geom=bm_brow.faces[:] + bm_brow.verts[:], thickness=-0.004)
    make_obj("Kid_Eyebrows", bm_brow, mats["Mat_Eyebrow"], mirror=True, subsurf=1)

    # Ears
    bm_ear = bmesh.new()
    bmesh.ops.create_uvsphere(bm_ear, u_segments=18, v_segments=14, radius=1.0)
    for v in list(bm_ear.verts):
        if v.co.y < -0.15:
            v.co.y *= 0.15
        v.co.x *= 0.011
        v.co.y *= 0.022
        v.co.z *= 0.028
        rot = Matrix.Rotation(0.08, 3, 'X') @ Matrix.Rotation(-0.15, 3, 'Y') @ Matrix.Rotation(0.32, 3, 'Z')
        v.co = rot @ v.co
        v.co += Vector((0.076, -0.004, 0.780))
    make_obj("Kid_Ears", bm_ear, mats["Mat_Skin"], mirror=True, subsurf=1)

    # =========================================================================
    # 2. WAVY LUSH HAIR (Volumetric Disney/Pixar Boy Hair)
    # =========================================================================
    # Full Volumetric Hair Base Mesh covering skull and crown
    bm_hair_base = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hair_base, u_segments=32, v_segments=24, radius=1.0)
    for v in list(bm_hair_base.verts):
        if v.co.x < -0.0001:
            bm_hair_base.verts.remove(v)
        elif v.co.x <= 0.0001:
            v.co.x = 0.0

    for v in list(bm_hair_base.verts):
        sx = v.co.x * 0.088
        sy = v.co.y * 0.092
        sz = v.co.z * 0.098
        # Curved natural hairline: temples and forehead opening
        dist_face = math.sqrt((sx / 0.075)**2 + (sy / 0.070)**2 + (max(0.0, -sz) / 0.070)**2)
        if sy < -0.020 and sz < 0.045 and dist_face < 0.95:
            bm_hair_base.verts.remove(v)
        else:
            # Fluffy volume above head (top reaches Z = 0.985m)
            v.co = Vector((sx * 1.08, sy * 1.06, sz * 1.06 + z_head + 0.035))

    make_obj("Kid_Hair_Base", bm_hair_base, mats["Mat_Hair"], mirror=True, subsurf=1)

    # Stylized Wavy Clumps & Flowing Bangs
    bm_locks = bmesh.new()

    # Bangs sweeping across forehead
    b1 = [
        (Vector((0.008, -0.072, 0.880)), 0.020, 0.8),
        (Vector((0.025, -0.084, 0.865)), 0.024, 0.8),
        (Vector((0.045, -0.086, 0.845)), 0.020, 0.8),
        (Vector((0.060, -0.080, 0.825)), 0.012, 0.6),
        (Vector((0.068, -0.076, 0.810)), 0.003, 0.5),
    ]
    add_curved_tube(bm_locks, b1)

    b2 = [
        (Vector((0.024, -0.065, 0.905)), 0.022, 0.8),
        (Vector((0.050, -0.076, 0.890)), 0.026, 0.8),
        (Vector((0.074, -0.070, 0.860)), 0.020, 0.8),
        (Vector((0.086, -0.060, 0.835)), 0.010, 0.6),
        (Vector((0.092, -0.052, 0.818)), 0.003, 0.5),
    ]
    add_curved_tube(bm_locks, b2)

    # Crown Waves (Natural flowing crests)
    c1 = [
        (Vector((0.012, -0.025, 0.920)), 0.034, 1.0),
        (Vector((0.028, -0.015, 0.955)), 0.036, 1.0),
        (Vector((0.042, -0.005, 0.985)), 0.028, 1.0),
        (Vector((0.050,  0.005, 1.000)), 0.004, 0.5),
    ]
    add_curved_tube(bm_locks, c1)

    c2 = [
        (Vector((0.000, -0.010, 0.930)), 0.035, 1.0),
        (Vector((0.000,  0.012, 0.965)), 0.036, 1.0),
        (Vector((0.015,  0.024, 0.992)), 0.025, 1.0),
        (Vector((0.020,  0.028, 1.000)), 0.004, 0.5),
    ]
    add_curved_tube(bm_locks, c2)

    c3 = [
        (Vector((0.040,  0.000, 0.915)), 0.030, 1.0),
        (Vector((0.062,  0.012, 0.948)), 0.030, 1.0),
        (Vector((0.082,  0.020, 0.975)), 0.020, 0.9),
        (Vector((0.092,  0.024, 0.990)), 0.003, 0.5),
    ]
    add_curved_tube(bm_locks, c3)

    # Sideburns & Ear Framing
    s1 = [
        (Vector((0.076, -0.028, 0.850)), 0.020, 0.8),
        (Vector((0.088, -0.024, 0.815)), 0.022, 0.8),
        (Vector((0.092, -0.018, 0.775)), 0.015, 0.7),
        (Vector((0.092, -0.012, 0.745)), 0.003, 0.5),
    ]
    add_curved_tube(bm_locks, s1)

    # Back Nape Waves
    k1 = [
        (Vector((0.000,  0.070, 0.890)), 0.038, 1.0),
        (Vector((0.000,  0.088, 0.855)), 0.040, 1.0),
        (Vector((0.010,  0.092, 0.815)), 0.032, 1.0),
        (Vector((0.012,  0.088, 0.770)), 0.020, 0.8),
        (Vector((0.010,  0.080, 0.730)), 0.004, 0.5),
    ]
    add_curved_tube(bm_locks, k1)

    k2 = [
        (Vector((0.040,  0.065, 0.880)), 0.032, 1.0),
        (Vector((0.056,  0.076, 0.840)), 0.032, 1.0),
        (Vector((0.065,  0.076, 0.795)), 0.024, 0.9),
        (Vector((0.068,  0.068, 0.755)), 0.010, 0.6),
        (Vector((0.068,  0.060, 0.725)), 0.003, 0.5),
    ]
    add_curved_tube(bm_locks, k2)

    make_obj("Kid_Hair_Locks", bm_locks, mats["Mat_Hair"], mirror=True, subsurf=1)

    # =========================================================================
    # 3. BODY SKIN (Neck, Chest, Arms, Hands, Legs)
    # =========================================================================
    bm_body = bmesh.new()

    # Neck (Z = 0.650 to 0.710)
    neck_levels = [
        (0.710, 0.038, 0.040), # base of chin/jaw
        (0.680, 0.040, 0.042), # mid neck
        (0.650, 0.048, 0.046), # collar base
    ]
    n_grid = []
    segs = 12
    for (nz, rx, ry) in neck_levels:
        row = []
        for i in range(segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (segs // 2))
            nx = rx * math.cos(ang)
            ny = ry * math.sin(ang)
            if i == 0 or i == segs // 2:
                nx = 0.0
            row.append(bm_body.verts.new(Vector((nx, ny, nz))))
        n_grid.append(row)
    for li in range(len(neck_levels) - 1):
        for i in range(segs // 2):
            bm_body.faces.new([n_grid[li][i], n_grid[li][i+1], n_grid[li+1][i+1], n_grid[li+1][i]])

    # Arms (Chubby child arms in relaxed resting pose)
    # Shoulder: (0.110, 0.0, 0.610), Elbow: (0.135, 0.01, 0.500), Wrist: (0.150, 0.02, 0.380)
    arm_levels = [
        (Vector((0.105, 0.000, 0.620)), 0.028),
        (Vector((0.125, 0.005, 0.540)), 0.025),
        (Vector((0.140, 0.010, 0.460)), 0.023),
        (Vector((0.152, 0.015, 0.385)), 0.021),
    ]
    a_grid = []
    a_segs = 10
    for (center, rad) in arm_levels:
        row = []
        for i in range(a_segs):
            ang = 2.0 * math.pi * (i / a_segs)
            ax = center.x + rad * math.cos(ang)
            ay = center.y + rad * math.sin(ang)
            az = center.z
            row.append(bm_body.verts.new(Vector((ax, ay, az))))
        a_grid.append(row)
    for li in range(len(arm_levels) - 1):
        for i in range(a_segs):
            bm_body.faces.new([a_grid[li][i], a_grid[li][(i+1)%a_segs], a_grid[li+1][(i+1)%a_segs], a_grid[li+1][i]])

    # Hands (Stylized 4-finger / thumb child hand)
    wrist_center = Vector((0.156, 0.018, 0.365))
    res_palm = bmesh.ops.create_cube(bm_body, size=0.032)
    for v in res_palm['verts']:
        v.co.x = v.co.x * 0.45 + wrist_center.x
        v.co.y = v.co.y * 0.85 + wrist_center.y
        v.co.z = v.co.z * 1.10 + wrist_center.z - 0.015

    # Thumb
    res_th = bmesh.ops.create_cone(bm_body, cap_ends=True, segments=8, radius1=0.0065, radius2=0.0045, depth=0.022)
    for v in res_th['verts']:
        v.co += Vector((wrist_center.x - 0.010, wrist_center.y - 0.010, wrist_center.z - 0.018))

    # Fingers
    for fi, fy in enumerate([-0.008, 0.0, 0.008]):
        res_fg = bmesh.ops.create_cone(bm_body, cap_ends=True, segments=8, radius1=0.0055, radius2=0.004, depth=0.024)
        for v in res_fg['verts']:
            v.co += Vector((wrist_center.x + 0.002, wrist_center.y + fy, wrist_center.z - 0.038))

    # Legs (Smooth kid legs between shorts and socks: Z = 0.170 to 0.280)
    leg_levels = [
        (Vector((0.054, 0.000, 0.280)), 0.036), # Knee/upper calf
        (Vector((0.054, 0.000, 0.220)), 0.032), # Mid calf
        (Vector((0.054, 0.000, 0.170)), 0.028), # Ankle
    ]
    lg_grid = []
    lg_segs = 10
    for (center, rad) in leg_levels:
        row = []
        for i in range(lg_segs):
            ang = 2.0 * math.pi * (i / lg_segs)
            lx = center.x + rad * math.cos(ang)
            ly = center.y + rad * math.sin(ang)
            lz = center.z
            row.append(bm_body.verts.new(Vector((lx, ly, lz))))
        lg_grid.append(row)
    for li in range(len(leg_levels) - 1):
        for i in range(lg_segs):
            bm_body.faces.new([lg_grid[li][i], lg_grid[li][(i+1)%lg_segs], lg_grid[li+1][(i+1)%lg_segs], lg_grid[li+1][i]])

    make_obj("Kid_Body", bm_body, mats["Mat_Skin"], mirror=True, subsurf=1)

    # =========================================================================
    # 4. T-SHIRT (White crew-neck with ribbed collar)
    # =========================================================================
    bm_ts = bmesh.new()
    ts_levels = [
        (0.655, 0.054, 0.050), # Collar rim
        (0.610, 0.088, 0.068), # Upper chest
        (0.530, 0.086, 0.066), # Mid chest
        (0.460, 0.084, 0.064), # Lower waist
        (0.405, 0.082, 0.064), # Hem
    ]
    ts_grid = []
    for (tz, rx, ry) in ts_levels:
        row = []
        for i in range(segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (segs // 2))
            tx = rx * math.cos(ang)
            ty = ry * math.sin(ang)
            if i == 0 or i == segs // 2:
                tx = 0.0
            row.append(bm_ts.verts.new(Vector((tx, ty, tz))))
        ts_grid.append(row)
    for li in range(len(ts_levels) - 1):
        for i in range(segs // 2):
            bm_ts.faces.new([ts_grid[li][i], ts_grid[li][i+1], ts_grid[li+1][i+1], ts_grid[li+1][i]])

    # Solidify T-shirt thickness
    bmesh.ops.solidify(bm_ts, geom=bm_ts.faces[:] + bm_ts.verts[:], thickness=0.003)
    make_obj("Kid_TShirt", bm_ts, mats["Mat_TShirt"], mirror=True, subsurf=1)

    # Teddy Bear badge on chest (Z = 0.540, Y = -0.070)
    bm_bear = bmesh.new()
    res_bhead = bmesh.ops.create_uvsphere(bm_bear, u_segments=16, v_segments=12, radius=0.016)
    for v in res_bhead['verts']:
        v.co.y *= 0.25
        v.co += Vector((0.0, -0.071, 0.540))
    # Bear ears
    res_bear = bmesh.ops.create_uvsphere(bm_bear, u_segments=10, v_segments=8, radius=0.006)
    for v in res_bear['verts']:
        v.co.y *= 0.25
        v.co += Vector((0.012, -0.071, 0.553))
    make_obj("Kid_Bear_Graphic", bm_bear, mats["Mat_Bear_Brown"], mirror=True, subsurf=1)

    # =========================================================================
    # 5. OPEN BLUE HOODIE (Short Sleeves, Draped Hood, Ribbed Hem, Drawstrings)
    # =========================================================================
    bm_hd = bmesh.new()

    hd_levels = [
        (0.645, 0.098, 0.076), # Shoulder line
        (0.580, 0.100, 0.078), # Mid chest
        (0.500, 0.096, 0.074), # Waist
        (0.440, 0.094, 0.074), # Lower waist
        (0.415, 0.092, 0.072), # Ribbed bottom hem
    ]
    hd_grid = []
    # Open front: angle sweeps from -0.32*pi to +0.86*pi
    h_segs = 10
    for (hz, rx, ry) in hd_levels:
        row = []
        for i in range(h_segs + 1):
            ang = -math.pi * 0.32 + (math.pi * 0.82) * (i / h_segs)
            hx = rx * math.cos(ang)
            hy = ry * math.sin(ang)
            if i == h_segs:
                hx = 0.0
            row.append(bm_hd.verts.new(Vector((hx, hy, hz))))
        hd_grid.append(row)
    for li in range(len(hd_levels) - 1):
        for i in range(h_segs):
            bm_hd.faces.new([hd_grid[li][i], hd_grid[li][i+1], hd_grid[li+1][i+1], hd_grid[li+1][i]])

    # Short Sleeves (Cuffed sleeves from shoulder to mid-bicep)
    res_sl = bmesh.ops.create_cone(bm_hd, cap_ends=True, cap_tris=False, segments=14,
                                   radius1=0.050, radius2=0.044, depth=0.105)
    for v in res_sl['verts']:
        rot = Matrix.Rotation(0.20, 3, 'Y')
        v.co = rot @ v.co
        v.co += Vector((0.118, 0.005, 0.575))

    # Rolled sleeve cuff
    res_cuff = bmesh.ops.create_cone(bm_hd, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.048, radius2=0.046, depth=0.020)
    for v in res_cuff['verts']:
        rot = Matrix.Rotation(0.20, 3, 'Y')
        v.co = rot @ v.co
        v.co += Vector((0.130, 0.007, 0.528))

    # Hood draped on back of neck/shoulders
    res_hood = bmesh.ops.create_uvsphere(bm_hd, u_segments=16, v_segments=12, radius=1.0)
    for v in res_hood['verts']:
        v.co.x *= 0.082
        v.co.y *= 0.055
        v.co.z *= 0.065
        v.co += Vector((0.0, 0.068, 0.625))

    # Side Welt Pockets
    res_pock = bmesh.ops.create_cube(bm_hd, size=0.035)
    for v in res_pock['verts']:
        v.co.x = v.co.x * 0.25 + 0.075
        v.co.y = v.co.y * 0.85 - 0.055
        v.co.z = v.co.z * 1.10 + 0.450

    bmesh.ops.solidify(bm_hd, geom=bm_hd.faces[:] + bm_hd.verts[:], thickness=0.004)
    make_obj("Kid_Hoodie", bm_hd, mats["Mat_Hoodie"], mirror=True, subsurf=1)

    # Hanging White Drawstrings with tips (aglets)
    bm_ds = bmesh.new()
    res_string = bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.0028, radius2=0.0025, depth=0.095)
    for v in res_string['verts']:
        v.co += Vector((0.032, -0.078, 0.560))
    res_aglet = bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.0035, radius2=0.0032, depth=0.015)
    for v in res_aglet['verts']:
        v.co += Vector((0.032, -0.078, 0.510))
    make_obj("Kid_Hoodie_Drawstrings", bm_ds, mats["Mat_TShirt"], mirror=True, subsurf=1)

    # =========================================================================
    # 6. CARGO SHORTS (Khaki with Large Side Flap Pockets and Cuffs)
    # =========================================================================
    bm_sh = bmesh.new()

    # Waist & Crotch Pelvis
    sh_levels = [
        (0.445, 0.088, 0.068), # Waistband
        (0.400, 0.092, 0.072), # Upper hips
        (0.355, 0.090, 0.070), # Crotch
    ]
    s_grid = []
    for (sz, rx, ry) in sh_levels:
        row = []
        for i in range(segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (segs // 2))
            sx = rx * math.cos(ang)
            sy = ry * math.sin(ang)
            if i == 0 or i == segs // 2:
                sx = 0.0
            row.append(bm_sh.verts.new(Vector((sx, sy, sz))))
        s_grid.append(row)
    for li in range(len(sh_levels) - 1):
        for i in range(segs // 2):
            bm_sh.faces.new([s_grid[li][i], s_grid[li][i+1], s_grid[li+1][i+1], s_grid[li+1][i]])

    # Wide Leg Cylinders (Z = 0.260 to 0.365)
    res_leg = bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=14,
                                   radius1=0.052, radius2=0.056, depth=0.110)
    for v in res_leg['verts']:
        v.co += Vector((0.054, 0.000, 0.315))

    # Folded bottom hem cuffs
    res_scuff = bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=14,
                                     radius1=0.055, radius2=0.055, depth=0.022)
    for v in res_scuff['verts']:
        v.co += Vector((0.054, 0.000, 0.268))

    # Chunky Cargo Flap Pocket on outer thigh
    res_pbox = bmesh.ops.create_cube(bm_sh, size=0.038)
    for v in res_pbox['verts']:
        v.co.x = v.co.x * 0.35 + 0.108
        v.co.y = v.co.y * 1.05
        v.co.z = v.co.z * 1.30 + 0.315

    # Pocket Flap
    res_pflap = bmesh.ops.create_cube(bm_sh, size=0.038)
    for v in res_pflap['verts']:
        v.co.x = v.co.x * 0.40 + 0.110
        v.co.y = v.co.y * 1.10
        v.co.z = v.co.z * 0.35 + 0.344

    bmesh.ops.solidify(bm_sh, geom=bm_sh.faces[:] + bm_sh.verts[:], thickness=0.004)
    make_obj("Kid_Shorts", bm_sh, mats["Mat_Shorts"], mirror=True, subsurf=1)

    # =========================================================================
    # 7. SOCKS (White Crew Socks with Folded Ribbed Cuff)
    # =========================================================================
    bm_sk = bmesh.new()
    res_sock = bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.030, radius2=0.032, depth=0.075)
    for v in res_sock['verts']:
        v.co += Vector((0.054, 0.000, 0.135))
    # Folded cuff rim
    res_skcuff = bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=14,
                                      radius1=0.033, radius2=0.033, depth=0.020)
    for v in res_skcuff['verts']:
        v.co += Vector((0.054, 0.000, 0.168))
    bmesh.ops.solidify(bm_sk, geom=bm_sk.faces[:] + bm_sk.verts[:], thickness=0.002)
    make_obj("Kid_Socks", bm_sk, mats["Mat_Socks"], mirror=True, subsurf=1)

    # =========================================================================
    # 8. SNEAKERS / SKATE SHOES (Chunky Blue Canvas, White Sole, White Toe Cap, Laces)
    # Foot Length: 160mm (Y: -0.095 to +0.065), Width: 80mm, Center X: 0.056
    # =========================================================================
    x_shoe = 0.056

    # A. Sole (White Midsole + Gum Outsole)
    bm_sole = bmesh.new()
    # Outsole (gum tread)
    res_outsole = bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in res_outsole['verts']:
        v.co.x = v.co.x * 0.80 + x_shoe
        v.co.y = v.co.y * 1.62 - 0.015
        v.co.z = v.co.z * 0.08 + 0.004
    # Thick White Midsole
    res_midsole = bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in res_midsole['verts']:
        v.co.x = v.co.x * 0.82 + x_shoe
        v.co.y = v.co.y * 1.64 - 0.015
        v.co.z = v.co.z * 0.18 + 0.017
    make_obj("Kid_Shoe_Sole", bm_sole, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    # B. White Rubber Toe Cap
    bm_tc = bmesh.new()
    res_toecap = bmesh.ops.create_uvsphere(bm_tc, u_segments=16, v_segments=12, radius=0.040)
    for v in res_toecap['verts']:
        v.co.x = v.co.x * 0.98 + x_shoe
        v.co.y = v.co.y * 0.80 - 0.065
        v.co.z = v.co.z * 0.65 + 0.030
    make_obj("Kid_Shoe_ToeCap", bm_tc, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    # C. Blue Shoe Upper Canvas
    bm_up = bmesh.new()
    res_upper = bmesh.ops.create_uvsphere(bm_up, u_segments=18, v_segments=14, radius=0.052)
    for v in res_upper['verts']:
        v.co.x = v.co.x * 0.84 + x_shoe
        v.co.y = v.co.y * 1.58 - 0.015
        # Cut flat bottom so sole sits below
        v.co.z = max(0.022, v.co.z * 0.88 + 0.052)
    # Solidify upper
    bmesh.ops.solidify(bm_up, geom=bm_up.faces[:] + bm_up.verts[:], thickness=0.003)
    make_obj("Kid_Shoe_Upper", bm_up, mats["Mat_Shoes_Blue"], mirror=True, subsurf=1)

    # D. White Accent Stripes & Shoelaces
    bm_laces = bmesh.new()
    # Curved skate accent stripe on side
    res_stripe = bmesh.ops.create_cube(bm_laces, size=0.01)
    for v in res_stripe['verts']:
        v.co.x = v.co.x * 0.20 + x_shoe + 0.044
        v.co.y = v.co.y * 5.5 - 0.010
        v.co.z = v.co.z * 0.5 + 0.052
    # Shoelaces (3 chunky white cross bars)
    for lz, ly in [(0.056, -0.045), (0.068, -0.030), (0.080, -0.015)]:
        res_lace = bmesh.ops.create_cube(bm_laces, size=0.01)
        for v in res_lace['verts']:
            v.co.x = v.co.x * 2.8 + x_shoe
            v.co.y = v.co.y * 0.45 + ly
            v.co.z = v.co.z * 0.28 + lz
    make_obj("Kid_Shoe_Laces", bm_laces, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    print("COMPLETE PRODUCTION-READY KID CHARACTER BUILT SUCCESSFULLY!")

build_production_kid()
