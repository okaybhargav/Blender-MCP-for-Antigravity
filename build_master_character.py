import bpy
import bmesh
from mathutils import Vector, Matrix
import math

def build_master_character():
    # Clean previous Kid objects
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Kid_"):
            bpy.data.objects.remove(obj, do_unlink=True)

    char_col = bpy.data.collections.get("Character_Kid")
    if not char_col:
        char_col = bpy.data.collections.new("Character_Kid")
        bpy.context.scene.collection.children.link(char_col)

    # 1. Materials with Pixar color palette
    materials_config = {
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
        "Mat_Shorts": ((0.77, 0.65, 0.49, 1.0), 0.60),
        "Mat_Socks": ((0.95, 0.95, 0.95, 1.0), 0.60),
        "Mat_Shoes_Blue": ((0.22, 0.46, 0.72, 1.0), 0.40),
        "Mat_Shoes_White": ((0.96, 0.96, 0.96, 1.0), 0.30),
        "Mat_Shoes_Gum": ((0.58, 0.38, 0.22, 1.0), 0.50),
        "Mat_Bear_Brown": ((0.75, 0.50, 0.30, 1.0), 0.50),
    }

    mats = {}
    for name, (col, rough) in materials_config.items():
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name)
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf:
            bsdf.inputs["Base Color"].default_value = col
            bsdf.inputs["Roughness"].default_value = rough
        mat.diffuse_color = col
        mats[name] = mat

    def create_mesh_obj(name, bm, mat, mirror=True, subsurf=1):
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

    # =========================================================================
    # 2. CONTINUOUS BASE BODY (Head, Neck, Torso, Arms, Hands, Legs, Feet)
    # Built as a continuous anatomical mesh so everything is seamlessly connected!
    # =========================================================================
    bm_body = bmesh.new()

    # Vertical landmarks:
    # Ground: Z = 0.000
    # Ankle: Z = 0.080
    # Knee: Z = 0.220
    # Crotch / Pelvis: Z = 0.380
    # Waist: Z = 0.480
    # Chest / Armpits: Z = 0.560
    # Shoulders / Clavicle: Z = 0.630
    # Neck: Z = 0.640 to 0.690 (only 50mm!)
    # Chin: Z = 0.695
    # Head Center: Z = 0.790
    # Skull Top: Z = 0.885

    # A. HEAD (Half-sphere X >= 0 with open eye sockets, nose, mouth cavity, cute cheeks)
    bmesh.ops.create_uvsphere(bm_body, u_segments=32, v_segments=24, radius=1.0)
    for v in list(bm_body.verts):
        if v.co.x < -0.0001:
            bm_body.verts.remove(v)
        elif v.co.x <= 0.0001:
            v.co.x = 0.0

    z_head = 0.790
    eye_center = Vector((0.040, -0.052, 0.792))
    eye_rx = 0.021
    eye_rz = 0.018

    for v in bm_body.verts:
        x = v.co.x * 0.075
        y = v.co.y * 0.080
        z = v.co.z * 0.095

        # Forehead
        if z > 0.015:
            x *= 1.06
            y *= 1.04
            if y < 0:
                y -= 0.005 * (z / 0.095)

        # Cheeks
        if -0.055 < z < 0.02 and y < 0.025:
            factor = math.cos((z + 0.02) * 28.0)
            if factor > 0:
                x *= (1.0 + factor * 0.22)
                if y < -0.01:
                    y -= factor * 0.016

        # Soft rounded chin
        if z < -0.045:
            blend = min(1.0, (-z - 0.045) / 0.050)
            x *= (1.0 - blend * 0.32)
            if y < 0:
                y += blend * 0.008

        v.co = Vector((x, y, z + z_head))

    # Cut eye sockets in head
    faces_to_del = []
    for f in bm_body.faces:
        fc = f.calc_center_median()
        if fc.y < -0.035 and abs(fc.x - eye_center.x) < 0.022 and abs(fc.z - eye_center.z) < 0.019:
            faces_to_del.append(f)
    bmesh.ops.delete(bm_body, geom=faces_to_del, context='FACES')

    bm_body.verts.ensure_lookup_table()
    for v in bm_body.verts:
        if v.is_boundary:
            d = math.sqrt(((v.co.x - eye_center.x)/eye_rx)**2 + ((v.co.z - eye_center.z)/eye_rz)**2)
            if d < 1.4 and v.co.y < -0.030:
                ang = math.atan2(v.co.z - eye_center.z, v.co.x - eye_center.x)
                v.co.x = eye_center.x + eye_rx * math.cos(ang)
                v.co.z = eye_center.z + eye_rz * math.sin(ang)
                v.co.y = -0.062 - 0.006 * math.cos(ang)

    # Cute button nose
    res_nose = bmesh.ops.create_uvsphere(bm_body, u_segments=14, v_segments=10, radius=0.009)
    for v in res_nose['verts']:
        v.co.x *= 1.10
        v.co.y *= 1.15
        v.co.z *= 0.85
        v.co += Vector((0.0, -0.088, 0.748))

    # Smile lips
    m_steps = 10
    m_verts = []
    for i in range(m_steps + 1):
        t = i / m_steps
        mx = t * 0.024
        mz = 0.718 + (t**2) * 0.007
        my = -0.082 + (t**2) * 0.009
        v_top = bm_body.verts.new(Vector((mx, my, mz + 0.002)))
        v_bot = bm_body.verts.new(Vector((mx, my, mz - 0.002)))
        m_verts.append((v_top, v_bot))
    for i in range(m_steps):
        t0, b0 = m_verts[i]
        t1, b1 = m_verts[i+1]
        bm_body.faces.new([t0, t1, b1, b0])

    # Cute ears
    res_ear = bmesh.ops.create_uvsphere(bm_body, u_segments=16, v_segments=12, radius=1.0)
    for v in res_ear['verts']:
        if v.co.y < -0.15:
            v.co.y *= 0.15
        v.co.x *= 0.011
        v.co.y *= 0.022
        v.co.z *= 0.028
        rot = Matrix.Rotation(0.08, 3, 'X') @ Matrix.Rotation(-0.15, 3, 'Y') @ Matrix.Rotation(0.32, 3, 'Z')
        v.co = rot @ v.co + Vector((0.076, -0.004, 0.780))

    # B. NECK & TORSO (Z = 0.380 to 0.695)
    body_levels = [
        # (Z, radius_x, radius_y)
        (0.695, 0.040, 0.042), # Under chin
        (0.660, 0.044, 0.044), # Mid neck
        (0.630, 0.088, 0.062), # Clavicle / Shoulders
        (0.560, 0.090, 0.064), # Chest
        (0.480, 0.084, 0.060), # Waist
        (0.420, 0.086, 0.062), # Hips
        (0.380, 0.084, 0.064), # Crotch / Pelvis
    ]
    b_segs = 12
    b_grid = []
    for (bz, rx, ry) in body_levels:
        row = []
        for i in range(b_segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (b_segs // 2))
            bx = rx * math.cos(ang)
            by = ry * math.sin(ang)
            if i == 0 or i == b_segs // 2:
                bx = 0.0
            row.append(bm_body.verts.new(Vector((bx, by, bz))))
        b_grid.append(row)
    for li in range(len(body_levels) - 1):
        for i in range(b_segs // 2):
            bm_body.faces.new([b_grid[li][i], b_grid[li][i+1], b_grid[li+1][i+1], b_grid[li+1][i]])

    # C. ARMS & HANDS (Extruding from shoulder Z=0.62 down to hands at Z=0.32)
    arm_levels = [
        (Vector((0.095, 0.000, 0.615)), 0.028), # Shoulder joint
        (Vector((0.118, 0.005, 0.525)), 0.025), # Elbow
        (Vector((0.134, 0.010, 0.430)), 0.022), # Forearm
        (Vector((0.144, 0.015, 0.355)), 0.020), # Wrist
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

    # Hand (Palm and 4 chubby child fingers)
    wrist_pt = Vector((0.148, 0.018, 0.335))
    res_palm = bmesh.ops.create_cube(bm_body, size=0.030)
    for v in res_palm['verts']:
        v.co.x = v.co.x * 0.45 + wrist_pt.x
        v.co.y = v.co.y * 0.85 + wrist_pt.y
        v.co.z = v.co.z * 1.05 + wrist_pt.z - 0.014
    # Thumb
    res_th = bmesh.ops.create_cone(bm_body, cap_ends=True, segments=8, radius1=0.0065, radius2=0.004, depth=0.020)
    for v in res_th['verts']:
        v.co += Vector((wrist_pt.x - 0.008, wrist_pt.y - 0.009, wrist_pt.z - 0.016))
    # Fingers
    for fy in [-0.007, 0.0, 0.007]:
        res_fg = bmesh.ops.create_cone(bm_body, cap_ends=True, segments=8, radius1=0.0055, radius2=0.0035, depth=0.022)
        for v in res_fg['verts']:
            v.co += Vector((wrist_pt.x + 0.002, wrist_pt.y + fy, wrist_pt.z - 0.035))

    # D. LEGS & FEET (From crotch Z=0.38 down to ground Z=0.00)
    leg_levels = [
        (Vector((0.054, 0.000, 0.380)), 0.042), # Hip
        (Vector((0.054, 0.000, 0.280)), 0.036), # Thigh
        (Vector((0.054, 0.000, 0.200)), 0.032), # Knee / Calf
        (Vector((0.054, 0.000, 0.100)), 0.028), # Lower calf
        (Vector((0.054, 0.000, 0.050)), 0.026), # Ankle
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

    # Feet (Chunky kid feet touching ground Z=0.00, length 160mm)
    res_foot = bmesh.ops.create_cube(bm_body, size=0.1)
    for v in res_foot['verts']:
        v.co.x = v.co.x * 0.70 + 0.054
        v.co.y = v.co.y * 1.55 - 0.015
        v.co.z = max(0.000, v.co.z * 0.35 + 0.025)

    create_mesh_obj("Kid_Body", bm_body, mats["Mat_Skin"], mirror=True, subsurf=1)

    # =========================================================================
    # 3. EYES (Eyeballs, Irises, Pupils, Highlights, Eyelashes, Eyebrows)
    # =========================================================================
    bm_eye = bmesh.new()
    bmesh.ops.create_uvsphere(bm_eye, u_segments=24, v_segments=18, radius=0.021)
    for v in bm_eye.verts:
        v.co.x *= 0.95
        v.co.y *= 0.90
        v.co.z *= 1.05
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center + Vector((0.0, 0.008, 0.0))
    create_mesh_obj("Kid_Eye_White", bm_eye, mats["Mat_Eye_White"], mirror=True, subsurf=1)

    bm_iris = bmesh.new()
    bmesh.ops.create_circle(bm_iris, cap_ends=True, segments=24, radius=0.0135)
    for v in bm_iris.verts:
        d = math.sqrt(v.co.x**2 + v.co.y**2)
        vz = - (d**2) * 4.0
        v.co = Vector((v.co.x, vz, v.co.y))
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center + Vector((0.0, -0.010, 0.0))
    create_mesh_obj("Kid_Eye_Iris", bm_iris, mats["Mat_Eye_Iris"], mirror=True, subsurf=0)

    bm_pupil = bmesh.new()
    bmesh.ops.create_circle(bm_pupil, cap_ends=True, segments=20, radius=0.0075)
    for v in bm_pupil.verts:
        v.co = Vector((v.co.x, -0.0005, v.co.y))
        rot = Matrix.Rotation(-0.06, 3, 'Y')
        v.co = rot @ v.co + eye_center + Vector((0.0, -0.0102, 0.0))
    create_mesh_obj("Kid_Eye_Pupil", bm_pupil, mats["Mat_Eye_Pupil"], mirror=True, subsurf=0)

    bm_hl = bmesh.new()
    res1 = bmesh.ops.create_uvsphere(bm_hl, u_segments=10, v_segments=8, radius=0.0035)
    for v in res1['verts']:
        v.co += eye_center + Vector((-0.004, -0.0116, 0.006))
    res2 = bmesh.ops.create_uvsphere(bm_hl, u_segments=8, v_segments=6, radius=0.0018)
    for v in res2['verts']:
        v.co += eye_center + Vector((0.005, -0.0110, -0.005))
    create_mesh_obj("Kid_Eye_Highlights", bm_hl, mats["Mat_Eye_Highlight"], mirror=True, subsurf=0)

    bm_lash = bmesh.new()
    l_steps = 10
    l_verts = []
    for i in range(l_steps + 1):
        t = i / l_steps
        ang = math.pi * (0.05 + 0.90 * t)
        lx = eye_center.x + eye_rx * 1.05 * math.cos(ang)
        lz = eye_center.z + eye_rz * 1.08 * math.sin(ang)
        ly = -0.063 - 0.006 * math.cos(ang) - 0.0015
        w = math.sin(t * math.pi) * 0.0040 + 0.0015
        v_top = bm_lash.verts.new(Vector((lx, ly - 0.001, lz + w)))
        v_bot = bm_lash.verts.new(Vector((lx, ly, lz)))
        l_verts.append((v_top, v_bot))
    for i in range(l_steps):
        bm_lash.faces.new([l_verts[i][0], l_verts[i+1][0], l_verts[i+1][1], l_verts[i][1]])
    bmesh.ops.solidify(bm_lash, geom=bm_lash.faces[:] + bm_lash.verts[:], thickness=0.002)
    create_mesh_obj("Kid_Eyelashes", bm_lash, mats["Mat_Eyelid"], mirror=True, subsurf=1)

    bm_brow = bmesh.new()
    b_steps = 8
    b_verts = []
    for i in range(b_steps + 1):
        t = i / b_steps
        bx = 0.018 + t * 0.040
        bz = 0.832 + math.sin(t * math.pi * 0.85) * 0.014
        by = -0.072 - math.sin(t * math.pi) * 0.005
        w = (1.0 - t * 0.45) * 0.0055
        v_t = bm_brow.verts.new(Vector((bx, by, bz + w)))
        v_b = bm_brow.verts.new(Vector((bx, by, bz - w)))
        b_verts.append((v_t, v_b))
    for i in range(b_steps):
        bm_brow.faces.new([b_verts[i][0], b_verts[i+1][0], b_verts[i+1][1], b_verts[i][1]])
    bmesh.ops.solidify(bm_brow, geom=bm_brow.faces[:] + bm_brow.verts[:], thickness=-0.004)
    create_mesh_obj("Kid_Eyebrows", bm_brow, mats["Mat_Eyebrow"], mirror=True, subsurf=1)

    # =========================================================================
    # 4. WAVY LUSH HAIR (Volumetric Disney/Pixar Boy Hair)
    # Wide, rounded dome covering cranium with flowing swept bangs and soft waves
    # =========================================================================
    bm_hair = bmesh.new()
    bmesh.ops.create_uvsphere(bm_hair, u_segments=32, v_segments=24, radius=1.0)
    for v in list(bm_hair.verts):
        if v.co.x < -0.0001:
            bm_hair.verts.remove(v)
        elif v.co.x <= 0.0001:
            v.co.x = 0.0

    for v in list(bm_hair.verts):
        sx = v.co.x * 0.092
        sy = v.co.y * 0.096
        sz = v.co.z * 0.105
        # Cut forehead oval
        if sy < -0.025 and sz < 0.035 and sx < 0.070:
            bm_hair.verts.remove(v)
        else:
            # Fluffy volume hugging skull (Z top = 0.985m)
            v.co = Vector((sx * 1.05, sy * 1.05, sz * 1.02 + z_head + 0.020))

    def add_tube_to_hair(points_with_radii):
        segs = 8
        rings = []
        for (pt, rad, asp) in points_with_radii:
            ring = []
            for i in range(segs):
                ang = 2.0 * math.pi * (i / segs)
                rx = rad * math.cos(ang)
                ry = rad * math.sin(ang) * asp
                ring.append(bm_hair.verts.new(pt + Vector((rx, ry, 0.0))))
            rings.append(ring)
        for r in range(len(rings) - 1):
            for i in range(segs):
                bm_hair.faces.new([rings[r][i], rings[r][(i+1)%segs], rings[r+1][(i+1)%segs], rings[r+1][i]])
        tip_v = bm_hair.verts.new(points_with_radii[-1][0])
        for i in range(segs):
            bm_hair.faces.new([rings[-1][i], rings[-1][(i+1)%segs], tip_v])
        root_v = bm_hair.verts.new(points_with_radii[0][0])
        for i in range(segs):
            bm_hair.faces.new([rings[0][(i+1)%segs], rings[0][i], root_v])

    # Beautiful swept bangs across forehead
    b1 = [
        (Vector((0.008, -0.072, 0.880)), 0.020, 0.8),
        (Vector((0.028, -0.084, 0.865)), 0.024, 0.8),
        (Vector((0.050, -0.086, 0.842)), 0.020, 0.8),
        (Vector((0.065, -0.080, 0.820)), 0.010, 0.6),
        (Vector((0.072, -0.075, 0.805)), 0.003, 0.5),
    ]
    add_tube_to_hair(b1)

    b2 = [
        (Vector((0.026, -0.065, 0.905)), 0.022, 0.8),
        (Vector((0.052, -0.076, 0.888)), 0.025, 0.8),
        (Vector((0.076, -0.070, 0.855)), 0.018, 0.8),
        (Vector((0.088, -0.060, 0.828)), 0.008, 0.6),
        (Vector((0.094, -0.052, 0.810)), 0.003, 0.5),
    ]
    add_tube_to_hair(b2)

    # Soft crown waves following skull contour
    c1 = [
        (Vector((0.015, -0.025, 0.900)), 0.030, 1.0),
        (Vector((0.035, -0.015, 0.935)), 0.032, 1.0),
        (Vector((0.055, -0.005, 0.965)), 0.024, 1.0),
        (Vector((0.068,  0.005, 0.985)), 0.004, 0.5),
    ]
    add_tube_to_hair(c1)

    c2 = [
        (Vector((0.000, -0.010, 0.905)), 0.032, 1.0),
        (Vector((0.000,  0.015, 0.945)), 0.034, 1.0),
        (Vector((0.018,  0.028, 0.975)), 0.022, 1.0),
        (Vector((0.024,  0.032, 0.990)), 0.004, 0.5),
    ]
    add_tube_to_hair(c2)

    # Sideburns
    s1 = [
        (Vector((0.078, -0.028, 0.850)), 0.020, 0.8),
        (Vector((0.090, -0.024, 0.810)), 0.022, 0.8),
        (Vector((0.094, -0.018, 0.770)), 0.014, 0.7),
        (Vector((0.094, -0.012, 0.740)), 0.003, 0.5),
    ]
    add_tube_to_hair(s1)

    # Back waves
    k1 = [
        (Vector((0.000,  0.072, 0.880)), 0.036, 1.0),
        (Vector((0.000,  0.090, 0.845)), 0.038, 1.0),
        (Vector((0.010,  0.094, 0.805)), 0.030, 1.0),
        (Vector((0.012,  0.090, 0.760)), 0.018, 0.8),
        (Vector((0.010,  0.082, 0.720)), 0.004, 0.5),
    ]
    add_tube_to_hair(k1)

    create_mesh_obj("Kid_Hair", bm_hair, mats["Mat_Hair"], mirror=True, subsurf=1)

    # =========================================================================
    # 5. T-SHIRT (White crew-neck with cute teddy bear graphic)
    # =========================================================================
    bm_ts = bmesh.new()
    ts_levels = [
        (0.650, 0.052, 0.048), # Ribbed collar rim
        (0.610, 0.092, 0.068), # Upper chest
        (0.530, 0.090, 0.066), # Mid chest
        (0.460, 0.086, 0.064), # Lower waist
        (0.400, 0.084, 0.064), # Hem peeking below hoodie
    ]
    ts_grid = []
    for (tz, rx, ry) in ts_levels:
        row = []
        for i in range(b_segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (b_segs // 2))
            tx = rx * math.cos(ang)
            ty = ry * math.sin(ang)
            if i == 0 or i == b_segs // 2:
                tx = 0.0
            row.append(bm_ts.verts.new(Vector((tx, ty, tz))))
        ts_grid.append(row)
    for li in range(len(ts_levels) - 1):
        for i in range(b_segs // 2):
            bm_ts.faces.new([ts_grid[li][i], ts_grid[li][i+1], ts_grid[li+1][i+1], ts_grid[li+1][i]])
    bmesh.ops.solidify(bm_ts, geom=bm_ts.faces[:] + bm_ts.verts[:], thickness=0.003)

    # Teddy Bear badge on chest
    res_bhead = bmesh.ops.create_uvsphere(bm_ts, u_segments=16, v_segments=12, radius=0.016)
    for v in res_bhead['verts']:
        v.co.y *= 0.25
        v.co += Vector((0.0, -0.071, 0.540))
    res_bear = bmesh.ops.create_uvsphere(bm_ts, u_segments=10, v_segments=8, radius=0.006)
    for v in res_bear['verts']:
        v.co.y *= 0.25
        v.co += Vector((0.012, -0.071, 0.553))

    create_mesh_obj("Kid_TShirt", bm_ts, mats["Mat_TShirt"], mirror=True, subsurf=1)

    # =========================================================================
    # 6. OPEN HOODIE (Short sleeves, back hood, drawstrings, kangaroo pockets)
    # =========================================================================
    bm_hd = bmesh.new()
    hd_levels = [
        (0.640, 0.098, 0.076), # Shoulder line
        (0.575, 0.100, 0.078), # Mid chest
        (0.500, 0.096, 0.074), # Waist
        (0.440, 0.094, 0.074), # Lower waist
        (0.415, 0.092, 0.072), # Ribbed bottom hem
    ]
    hd_grid = []
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

    # Short Sleeves (From shoulder to mid-bicep)
    res_sl = bmesh.ops.create_cone(bm_hd, cap_ends=True, cap_tris=False, segments=14,
                                   radius1=0.048, radius2=0.042, depth=0.105)
    for v in res_sl['verts']:
        rot = Matrix.Rotation(0.20, 3, 'Y')
        v.co = rot @ v.co + Vector((0.114, 0.005, 0.565))

    # Cuffs
    res_cuff = bmesh.ops.create_cone(bm_hd, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.046, radius2=0.044, depth=0.020)
    for v in res_cuff['verts']:
        rot = Matrix.Rotation(0.20, 3, 'Y')
        v.co = rot @ v.co + Vector((0.125, 0.007, 0.518))

    # Draped hood on back
    res_hood = bmesh.ops.create_uvsphere(bm_hd, u_segments=16, v_segments=12, radius=1.0)
    for v in res_hood['verts']:
        v.co.x *= 0.082
        v.co.y *= 0.055
        v.co.z *= 0.065
        v.co += Vector((0.0, 0.070, 0.620))

    # Kangaroo Pockets
    res_pock = bmesh.ops.create_cube(bm_hd, size=0.035)
    for v in res_pock['verts']:
        v.co.x = v.co.x * 0.25 + 0.072
        v.co.y = v.co.y * 0.85 - 0.055
        v.co.z = v.co.z * 1.10 + 0.450

    bmesh.ops.solidify(bm_hd, geom=bm_hd.faces[:] + bm_hd.verts[:], thickness=0.004)
    create_mesh_obj("Kid_Hoodie", bm_hd, mats["Mat_Hoodie"], mirror=True, subsurf=1)

    # Hanging White Drawstrings
    bm_ds = bmesh.new()
    res_str = bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.0028, radius2=0.0025, depth=0.095)
    for v in res_str['verts']:
        v.co += Vector((0.030, -0.076, 0.555))
    res_agl = bmesh.ops.create_cone(bm_ds, cap_ends=True, segments=8, radius1=0.0035, radius2=0.0032, depth=0.015)
    for v in res_agl['verts']:
        v.co += Vector((0.030, -0.076, 0.505))
    create_mesh_obj("Kid_Hoodie_Drawstrings", bm_ds, mats["Mat_TShirt"], mirror=True, subsurf=1)

    # =========================================================================
    # 7. CARGO SHORTS (Khaki with Large Side Flap Pockets and Knee Cuffs)
    # =========================================================================
    bm_sh = bmesh.new()
    sh_levels = [
        (0.440, 0.090, 0.070), # Waistband
        (0.395, 0.094, 0.074), # Upper hips
        (0.355, 0.092, 0.072), # Crotch
    ]
    s_grid = []
    for (sz, rx, ry) in sh_levels:
        row = []
        for i in range(b_segs // 2 + 1):
            ang = -math.pi / 2.0 + math.pi * (i / (b_segs // 2))
            sx = rx * math.cos(ang)
            sy = ry * math.sin(ang)
            if i == 0 or i == b_segs // 2:
                sx = 0.0
            row.append(bm_sh.verts.new(Vector((sx, sy, sz))))
        s_grid.append(row)
    for li in range(len(sh_levels) - 1):
        for i in range(b_segs // 2):
            bm_sh.faces.new([s_grid[li][i], s_grid[li][i+1], s_grid[li+1][i+1], s_grid[li+1][i]])

    # Wide Leg Cylinders (Z = 0.250 to 0.360)
    res_sleg = bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.052, radius2=0.056, depth=0.115)
    for v in res_sleg['verts']:
        v.co += Vector((0.054, 0.000, 0.310))

    # Folded bottom hem cuffs
    res_scuff = bmesh.ops.create_cone(bm_sh, cap_ends=True, cap_tris=False, segments=14,
                                     radius1=0.055, radius2=0.055, depth=0.022)
    for v in res_scuff['verts']:
        v.co += Vector((0.054, 0.000, 0.262))

    # Chunky Cargo Flap Pocket on outer thigh
    res_pbox = bmesh.ops.create_cube(bm_sh, size=0.038)
    for v in res_pbox['verts']:
        v.co.x = v.co.x * 0.35 + 0.108
        v.co.y = v.co.y * 1.05
        v.co.z = v.co.z * 1.30 + 0.315
    res_pflap = bmesh.ops.create_cube(bm_sh, size=0.038)
    for v in res_pflap['verts']:
        v.co.x = v.co.x * 0.40 + 0.110
        v.co.y = v.co.y * 1.10
        v.co.z = v.co.z * 0.35 + 0.344

    bmesh.ops.solidify(bm_sh, geom=bm_sh.faces[:] + bm_sh.verts[:], thickness=0.004)
    create_mesh_obj("Kid_Shorts", bm_sh, mats["Mat_Shorts"], mirror=True, subsurf=1)

    # =========================================================================
    # 8. SOCKS (White Crew Socks with Folded Ribbed Cuff)
    # =========================================================================
    bm_sk = bmesh.new()
    res_sock = bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=14,
                                    radius1=0.030, radius2=0.032, depth=0.075)
    for v in res_sock['verts']:
        v.co += Vector((0.054, 0.000, 0.135))
    res_skcuff = bmesh.ops.create_cone(bm_sk, cap_ends=True, cap_tris=False, segments=14,
                                      radius1=0.033, radius2=0.033, depth=0.020)
    for v in res_skcuff['verts']:
        v.co += Vector((0.054, 0.000, 0.168))
    bmesh.ops.solidify(bm_sk, geom=bm_sk.faces[:] + bm_sk.verts[:], thickness=0.002)
    create_mesh_obj("Kid_Socks", bm_sk, mats["Mat_Socks"], mirror=True, subsurf=1)

    # =========================================================================
    # 9. SNEAKERS / SKATE SHOES (Chunky Blue Canvas, White Sole, White Toe Cap, Laces)
    # =========================================================================
    x_shoe = 0.054

    # Sole
    bm_sole = bmesh.new()
    res_outsole = bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in res_outsole['verts']:
        v.co.x = v.co.x * 0.80 + x_shoe
        v.co.y = v.co.y * 1.62 - 0.015
        v.co.z = v.co.z * 0.08 + 0.004
    res_midsole = bmesh.ops.create_cube(bm_sole, size=0.1)
    for v in res_midsole['verts']:
        v.co.x = v.co.x * 0.82 + x_shoe
        v.co.y = v.co.y * 1.64 - 0.015
        v.co.z = v.co.z * 0.18 + 0.017
    create_mesh_obj("Kid_Shoe_Sole", bm_sole, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    # Toe Cap
    bm_tc = bmesh.new()
    res_toecap = bmesh.ops.create_uvsphere(bm_tc, u_segments=16, v_segments=12, radius=0.040)
    for v in res_toecap['verts']:
        v.co.x = v.co.x * 0.98 + x_shoe
        v.co.y = v.co.y * 0.80 - 0.065
        v.co.z = v.co.z * 0.65 + 0.030
    create_mesh_obj("Kid_Shoe_ToeCap", bm_tc, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    # Blue Canvas Upper
    bm_up = bmesh.new()
    res_upper = bmesh.ops.create_uvsphere(bm_up, u_segments=18, v_segments=14, radius=0.052)
    for v in res_upper['verts']:
        v.co.x = v.co.x * 0.84 + x_shoe
        v.co.y = v.co.y * 1.58 - 0.015
        v.co.z = max(0.022, v.co.z * 0.88 + 0.052)
    bmesh.ops.solidify(bm_up, geom=bm_up.faces[:] + bm_up.verts[:], thickness=0.003)
    create_mesh_obj("Kid_Shoe_Upper", bm_up, mats["Mat_Shoes_Blue"], mirror=True, subsurf=1)

    # White Stripes & Laces
    bm_laces = bmesh.new()
    res_stripe = bmesh.ops.create_cube(bm_laces, size=0.01)
    for v in res_stripe['verts']:
        v.co.x = v.co.x * 0.20 + x_shoe + 0.044
        v.co.y = v.co.y * 5.5 - 0.010
        v.co.z = v.co.z * 0.5 + 0.052
    for lz, ly in [(0.056, -0.045), (0.068, -0.030), (0.080, -0.015)]:
        res_lace = bmesh.ops.create_cube(bm_laces, size=0.01)
        for v in res_lace['verts']:
            v.co.x = v.co.x * 2.8 + x_shoe
            v.co.y = v.co.y * 0.45 + ly
            v.co.z = v.co.z * 0.28 + lz
    create_mesh_obj("Kid_Shoe_Laces", bm_laces, mats["Mat_Shoes_White"], mirror=True, subsurf=1)

    print("MASTER CHARACTER BUILT SUCCESSFULLY!")

build_master_character()
