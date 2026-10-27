"""Build FIFA 16 mascot model.rx3 packages from club Ball Boy FBX meshes.

The source FBX uses Z-up and the FIFA SLC RX3 uses Y-up. Geometry and UVs
come from the club mesh; skin weights are transferred onto the audited 31-bone
FIFA crowd rig so the existing idle/goal animation code can drive the mascots.
Original FBX, PNG, and RX3 references are read-only.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.kdtree import KDTree

SOURCE_ROOT = Path(r"C:\Users\igorv\OneDrive\Área de Trabalho\mascotes")
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_REFERENCE = Path(os.environ.get(
    "MASCOT_ADJUSTER_TEMPLATE",
    str(PROJECT_ROOT / "ModCarrerMode" / "tools" / "mascot_rig_adjuster" / "assets" / "template_model_animated.rx3"),
))
# Keep the existing mascot package layout/material setup, but source skinning
# from an original FIFA 16 ball boy whose full 31-bone skin was audited.
WEIGHT_REFERENCE = Path(os.environ.get(
    "MASCOT_ADJUSTER_WEIGHT_REF",
    str(PROJECT_ROOT / "ModCarrerMode" / "tools" / "mascot_rig_adjuster" / "assets" / "specificballboy_0_1_0.rx3"),
))
OUTPUT_ROOT = Path(os.environ.get("MASCOT_OUTPUT_ROOT", str(PROJECT_ROOT / "data" / "sceneassets" / "mascot")))
TOOLS = Path(os.environ.get(
    "FIFA_RX3_TOOLS",
    str(PROJECT_ROOT / "ModCarrerMode" / "tools" / "mascot_rig_adjuster" / "vendor" / "rx3tools"),
))
sys.path.insert(0, str(TOOLS))
from rx3 import Rx3, read_model, invert4, FORMAT, VERTEX, INDEX, TEXTURE

CLUBS = (
    ("MASCOTE DO GALO", 1035, "Atlético Mineiro", "specificballboy_1035_0_0_textures.rx3"),
    ("MASCOTE DO VASCO", 569, "Vasco da Gama", "specificballboy_569_0_0_textures.rx3"),
    ("MASCOTE RAPOSA DO CINZEIROOO", 568, "Cruzeiro", "specificballboy_568_0_1_textures.rx3"),
)
ALIGN = lambda n: (n + 15) & ~15
MAX_MASCOT_HEIGHT_CM = 200.0


def game_position(point):
    # FIFA SLC models are Y-up; the source Ball Boy FBX files are Z-up.
    return Vector((point.x, point.z, -point.y)) * 100.0


def game_direction(vector, matrix):
    transformed = matrix @ vector
    result = Vector((transformed.x, transformed.z, -transformed.y))
    if result.length < 1e-8:
        return Vector((0.0, 1.0, 0.0))
    return result.normalized()


def pack_snorm_10(vector):
    value = 0
    for shift, component in zip((0, 10, 20), vector):
        quantized = int(round(max(-1.0, min(1.0, float(component))) * 511.0))
        value |= (quantized & 0x3FF) << shift
    return value


def load_source_mesh(source):
    source = Path(source)
    fbx = source if source.is_file() else source / "ballboy_0_0_1_0_swarmmesh_mesh.fbx"
    if not fbx.is_file():
        raise FileNotFoundError(f"Missing Ball Boy FBX: {fbx}")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(fbx), use_custom_normals=True)
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    mesh_obj = next((obj for obj in meshes if "slc_mat:" in obj.name and ".000" in obj.name), None)
    if mesh_obj is None and meshes:
        mesh_obj = max(meshes, key=lambda obj: (len(obj.data.polygons), len(obj.data.vertices)))
    if mesh_obj is None:
        raise ValueError(f"No base LOD mesh found in {fbx.name}")
    mesh = mesh_obj.data
    if not mesh.uv_layers or mesh.uv_layers.active is None:
        raise ValueError(f"Mesh has no UV map: {fbx.name}")
    mesh.calc_loop_triangles()
    mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
    world3 = mesh_obj.matrix_world.to_3x3()
    normal_matrix = world3.inverted().transposed()
    uv_layer = mesh.uv_layers.active
    vertices = []
    indices = []
    vertex_map = {}

    for triangle in mesh.loop_triangles:
        for loop_index in triangle.loops:
            loop = mesh.loops[loop_index]
            uv = uv_layer.data[loop_index].uv
            position = game_position(mesh_obj.matrix_world @ mesh.vertices[loop.vertex_index].co)
            normal = game_direction(loop.normal, normal_matrix)
            tangent = game_direction(loop.tangent, world3)
            key = (
                loop.vertex_index,
                round(float(uv.x), 7),
                round(float(uv.y), 7),
                *(round(float(c), 5) for c in normal),
                *(round(float(c), 5) for c in tangent),
            )
            vertex_index = vertex_map.get(key)
            if vertex_index is None:
                vertex_index = len(vertices)
                vertex_map[key] = vertex_index
                vertices.append({
                    "position": position,
                    "normal": normal,
                    "tangent": tangent,
                    "uv": (float(uv.x), float(uv.y)),
                })
            indices.append(vertex_index)

    if not vertices or not indices or len(indices) % 3:
        raise ValueError(f"Empty or non-triangle mesh in {fbx.name}")
    if len(vertices) >= 65536:
        raise ValueError(f"Too many vertices for the RX3 16-bit index layout: {len(vertices)}")
    min_y = min(v["position"].y for v in vertices)
    max_y = max(v["position"].y for v in vertices)
    height = max_y - min_y
    if not math.isfinite(height) or height < 1e-6:
        raise ValueError(f"Invalid converted mascot height: {height:.2f} cm")
    # Some source FBX exports apply centimetres twice: the same 1.9 m mesh
    # arrives as 1.9 cm. Normalize this unit mismatch before fitting the rig.
    unit_scale = 1.0
    if height < 20.0:
        unit_scale = 10.0 ** math.ceil(math.log10(100.0 / height))
        for vertex in vertices:
            vertex["position"] *= unit_scale
        min_y *= unit_scale
        max_y *= unit_scale
        height *= unit_scale
    scale_factor = min(1.0, MAX_MASCOT_HEIGHT_CM / height)
    if scale_factor < 1.0:
        center_x = (min(v["position"].x for v in vertices) + max(v["position"].x for v in vertices)) * 0.5
        center_z = (min(v["position"].z for v in vertices) + max(v["position"].z for v in vertices)) * 0.5
        for vertex in vertices:
            position = vertex["position"]
            vertex["position"] = Vector((
                center_x + (position.x - center_x) * scale_factor,
                min_y + (position.y - min_y) * scale_factor,
                center_z + (position.z - center_z) * scale_factor,
            ))
    return vertices, indices, fbx.name, unit_scale * scale_factor


def transfer_weights(vertices, reference_part):
    reference_positions = [
        Vector(reference_part["positions"][i:i + 3])
        for i in range(0, len(reference_part["positions"]), 3)
    ]
    if len(reference_positions) != len(reference_part["joints"]) // 4:
        raise ValueError("Reference rig skin arrays do not match")
    tree = KDTree(len(reference_positions))
    for index, position in enumerate(reference_positions):
        tree.insert(position, index)
    tree.balance()

    all_joints = []
    all_weights = []
    for vertex in vertices:
        nearest = tree.find_n(vertex["position"], min(8, len(reference_positions)))
        accum = {}
        for _point, ref_index, distance in nearest:
            factor = 1.0 / (float(distance) + 0.5) ** 2
            base = ref_index * 4
            for bone, weight in zip(
                reference_part["joints"][base:base + 4],
                reference_part["weights"][base:base + 4],
            ):
                if weight:
                    accum[bone] = accum.get(bone, 0.0) + factor * float(weight) / 255.0
        if not accum:
            raise ValueError("A mascot vertex did not receive any rig weights")
        strongest = sorted(accum.items(), key=lambda row: row[1], reverse=True)[:4]
        total = sum(weight for _bone, weight in strongest)
        joints = [int(bone) for bone, _weight in strongest]
        weights = [int(round(weight / total * 255.0)) for _bone, weight in strongest]
        weights[0] += 255 - sum(weights)
        while len(joints) < 4:
            joints.append(joints[0])
            weights.append(0)
        if any(joint < 0 or joint >= 31 for joint in joints):
            raise ValueError("Transferred skin references a bone outside the 31-bone rig")
        if min(weights) < 0 or max(weights) > 255 or sum(weights) != 255:
            raise ValueError("Transferred skin weights are not normalized")
        all_joints.extend(joints)
        all_weights.extend(weights)

    used = {j for j, w in zip(all_joints, all_weights) if w}
    right_arm = sum(
        1 for j, w in zip(all_joints, all_weights) if w and 17 <= j <= 20
    )
    left_arm = sum(
        1 for j, w in zip(all_joints, all_weights) if w and 22 <= j <= 25
    )
    if not right_arm or not left_arm:
        raise ValueError("Transferred rig does not influence both arms")
    return all_joints, all_weights, sorted(used), right_arm, left_arm


def add_hand_influences(vertices, joints, weights):
    """Weight the outer hand geometry to the game rig's hand bones (19/24)."""
    if len(joints) != len(weights) or len(joints) != len(vertices) * 4:
        raise ValueError("Hand weights do not match the vertex count")
    positions = [v["position"] for v in vertices]
    y_values = [p.y for p in positions]
    band_min, band_max = max(25.0, min(y_values) + 35.0), min(115.0, max(y_values) - 55.0)
    side_max = {}
    for side in (-1, 1):
        values = [side * p.x for p in positions if band_min <= p.y <= band_max and side * p.x > 0]
        if not values:
            raise ValueError(f"Could not locate the {side=} arm/hand span")
        side_max[side] = max(values)

    touched = {-1: 0, 1: 0}
    for index, point in enumerate(positions):
        if not band_min <= point.y <= band_max:
            continue
        side = 1 if point.x >= 0 else -1
        outward = side * point.x / side_max[side]
        t = max(0.0, min(1.0, (outward - 0.76) / (0.96 - 0.76)))
        t = t * t * (3.0 - 2.0 * t)
        if t <= 0.0:
            continue
        hand_bone = 19 if side > 0 else 24
        touched[side] += 1
        start = index * 4
        pairs = [(int(joints[start + k]), int(weights[start + k])) for k in range(4) if weights[start + k]]
        old_hand = sum(w for j, w in pairs if j == hand_bone)
        hand_weight = max(old_hand, int(round(t * 255.0)))
        remainder = 255 - hand_weight
        body = [(j, w) for j, w in pairs if j != hand_bone]
        body = sorted(body, key=lambda row: row[1], reverse=True)[:3]
        total = sum(w for _j, w in body)
        scaled = [(j, int(round(w / total * remainder))) for j, w in body] if total else []
        if scaled:
            scaled[0] = (scaled[0][0], scaled[0][1] + remainder - sum(w for _j, w in scaled))
        result = scaled + [(hand_bone, hand_weight)]
        result += [(result[0][0], 0)] * (4 - len(result))
        joints[start:start + 4] = [j for j, _w in result]
        weights[start:start + 4] = [w for _j, w in result]

    if not touched[-1] or not touched[1]:
        raise ValueError(f"Hand extents not found on both sides: {touched}")
    for i in range(0, len(weights), 4):
        if sum(weights[i:i + 4]) != 255:
            raise ValueError("Hand influence update produced non-normalized weights")
    used = sorted({j for j, w in zip(joints, weights) if w})
    right_arm = sum(1 for j, w in zip(joints, weights) if w and 17 <= j <= 20)
    left_arm = sum(1 for j, w in zip(joints, weights) if w and 22 <= j <= 25)
    return joints, weights, used, right_arm, left_arm, touched


def weighted_centers(part):
    result = {}
    count = len(part["positions"]) // 3
    for i in range(count):
        point = part["positions"][i * 3:i * 3 + 3]
        for joint, weight in zip(part["joints"][i * 4:i * 4 + 4], part["weights"][i * 4:i * 4 + 4]):
            if not weight:
                continue
            accum = result.setdefault(int(joint), [0.0, 0.0, 0.0, 0.0])
            for axis in range(3):
                accum[axis] += float(point[axis]) * float(weight)
            accum[3] += float(weight)
    return {joint: [value / accum[3] for value in accum[:3]] for joint, accum in result.items()}


def fit_bind_positions(template_bones, reference_part, vertices, joints, weights):
    """Fit each used bind point to this mesh while preserving the in-game rig offset."""
    ref_centers = weighted_centers(reference_part)
    target_part = {
        "positions": [component for v in vertices for component in v["position"]],
        "joints": joints,
        "weights": weights,
    }
    target_centers = weighted_centers(target_part)
    ref_positions = [Vector(reference_part["positions"][i:i + 3]) for i in range(0, len(reference_part["positions"]), 3)]
    target_positions = [v["position"] for v in vertices]
    extents = []
    for axis in range(3):
        ref_extent = max(p[axis] for p in ref_positions) - min(p[axis] for p in ref_positions)
        target_extent = max(tuple(p)[axis] for p in target_positions) - min(tuple(p)[axis] for p in target_positions)
        extents.append(target_extent / ref_extent if ref_extent > 1e-6 else 1.0)
    # Width and height scale with the mascot. Depth includes tails/feathers, so
    # keep the original bone-depth offset and let the target skin center decide z.
    offset_scale = (extents[0], extents[1], 1.0)
    fitted = {}
    for joint, center in target_centers.items():
        if joint not in ref_centers or joint >= len(template_bones):
            continue
        bind = template_bones[joint][12:15]
        ref_center = ref_centers[joint]
        fitted[joint] = [
            float(center[axis]) + (float(bind[axis]) - float(ref_center[axis])) * offset_scale[axis]
            for axis in range(3)
        ]
    # The arms on the club mascots are posed lower/wider than the game
    # reference. Fit each arm's shoulder, elbow and hand to its own weighted
    # regions rather than carrying the reference forearm's depth offset over.
    for root_joint, upper_joint, forearm_joint, hand_joint in ((16, 17, 18, 19), (21, 22, 23, 24)):
        required = (root_joint, upper_joint, forearm_joint, hand_joint)
        if not all(joint in target_centers for joint in required):
            continue
        root, upper, forearm, hand = (target_centers[joint] for joint in required)
        fitted[upper_joint] = [0.55 * root[a] + 0.45 * upper[a] for a in range(3)]
        fitted[forearm_joint] = [0.5 * upper[a] + 0.5 * forearm[a] for a in range(3)]
        fitted[hand_joint] = list(hand)
    return fitted, extents


def remap_section(joints, weights):
    order = sorted({joint for joint, weight in zip(joints, weights) if weight})
    if not order or len(order) > 31:
        raise ValueError("Invalid used-bone set for RX3 remap")
    data = bytearray(528)
    struct.pack_into("<I", data, 0, len(data))
    data[4] = len(order)
    for compact, joint in enumerate(order):
        data[16 + joint] = compact
        data[16 + 256 + compact] = joint
    return bytes(data), order


def build_rx3(template_bytes, vertices, indices, joints, weights, order, bind_positions=None, bind_transforms=None):
    rx = Rx3(template_bytes)
    parts, bones = read_model(rx)
    if len(parts) != 1 or len(bones) != 31:
        raise ValueError("The template must contain one mesh and the audited 31-bone rig")
    if len(vertices) != len(joints) // 4 or len(joints) != len(weights):
        raise ValueError("Vertex and skin arrays do not match")

    sections = {section[0]: section for section in rx.sections}
    descriptor = rx.get(FORMAT)[0]
    fields = {}
    for token in descriptor[16:].split(b"\0")[0].decode().split():
        semantic, offset, _stream, _usage, fmt = token.split(":")
        fields[semantic] = (int(offset, 16), fmt)
    required = {"p0", "n0", "g0", "t0", "i0", "w0"}
    if not required.issubset(fields):
        raise ValueError(f"Template vertex layout missing {sorted(required - fields.keys())}")
    stride = struct.unpack_from("<I", rx.get(VERTEX)[0], 8)[0]
    vertex_size = ALIGN(16 + stride * len(vertices))
    vb = bytearray(vertex_size)
    struct.pack_into("<4I", vb, 0, vertex_size, len(vertices), stride, 1)
    for index, vertex in enumerate(vertices):
        at = 16 + index * stride
        offset, fmt = fields["p0"]
        if fmt != "4f16":
            raise ValueError(f"Unsupported position format: {fmt}")
        p = vertex["position"]
        struct.pack_into("<4e", vb, at + offset, p.x, p.y, p.z, 1.0)
        offset, fmt = fields["n0"]
        if fmt != "3s10n":
            raise ValueError(f"Unsupported normal format: {fmt}")
        struct.pack_into("<I", vb, at + offset, pack_snorm_10(vertex["normal"]))
        offset, fmt = fields["g0"]
        if fmt != "3s10n":
            raise ValueError(f"Unsupported tangent format: {fmt}")
        struct.pack_into("<I", vb, at + offset, pack_snorm_10(vertex["tangent"]))
        offset, fmt = fields["t0"]
        if fmt != "2f16":
            raise ValueError(f"Unsupported UV format: {fmt}")
        struct.pack_into("<2e", vb, at + offset, *vertex["uv"])
        offset, fmt = fields["i0"]
        if fmt != "4u8":
            raise ValueError(f"Unsupported bone-index format: {fmt}")
        vb[at + offset:at + offset + 4] = bytes(joints[index * 4:index * 4 + 4])
        offset, fmt = fields["w0"]
        if fmt != "4u8n":
            raise ValueError(f"Unsupported bone-weight format: {fmt}")
        vb[at + offset:at + offset + 4] = bytes(weights[index * 4:index * 4 + 4])

    index_count = len(indices)
    index_size = ALIGN(16 + index_count * 2)
    ib = bytearray(index_size)
    struct.pack_into("<4I", ib, 0, index_size, index_count, 2, 0)
    struct.pack_into(f"<{index_count}H", ib, 16, *indices)
    sections[VERTEX][1] = bytes(vb)
    sections[INDEX][1] = bytes(ib)
    sections[0x0F3861A2][1] = remap_section(joints, weights)[0]

    if bind_positions or bind_transforms:
        bind_section = bytearray(sections[0xDF9AEC1E][1])
        bind_count = struct.unpack_from("<I", bind_section, 4)[0]
        if bind_count != 31 or len(bind_section) != 16 + 31 * 64:
            raise ValueError("Unexpected bind-pose section in the 31-bone template")
        for joint, position in (bind_positions or {}).items():
            bind = list(bones[joint])
            bind[12:15] = [float(v) for v in position]
            inverse = invert4(bind)
            struct.pack_into("<16f", bind_section, 16 + joint * 64, *inverse)
        for joint, transform in (bind_transforms or {}).items():
            position = Vector([float(v) for v in transform["position"]])
            qx, qy, qz, qw = [float(v) for v in transform["quaternion"]]
            quaternion = Quaternion((qw, qx, qy, qz))
            matrix = Matrix.LocRotScale(position, quaternion, Vector((1.0, 1.0, 1.0)))
            column_major = [float(matrix[row][column]) for column in range(4) for row in range(4)]
            inverse = invert4(column_major)
            struct.pack_into("<16f", bind_section, 16 + joint * 64, *inverse)
        sections[0xDF9AEC1E][1] = bytes(bind_section)

    # The renderable instance duplicates the indexed-buffer byte/count metadata.
    instance = bytearray(sections[0x22B2BE36][1])
    if len(instance) != 32:
        raise ValueError("Unexpected renderable-instance section size")
    struct.pack_into("<III", instance, 16, index_size, index_count, 2)
    sections[0x22B2BE36][1] = bytes(instance)
    result = rx.build()

    checked_parts, checked_bones = read_model(Rx3(result))
    part = checked_parts[0]
    if len(checked_bones) != 31 or len(part["positions"]) != len(vertices) * 3:
        raise ValueError("Generated RX3 failed its geometry/rig read-back")
    if len(part["indices"]) != index_count or max(part["indices"]) >= len(vertices):
        raise ValueError("Generated RX3 has invalid triangle indices")
    expected_positions = {**(bind_positions or {}), **{joint: transform["position"] for joint, transform in (bind_transforms or {}).items()}}
    for joint, position in expected_positions.items():
        actual_position = checked_bones[joint][12:15]
        if max(abs(actual_position[i] - position[i]) for i in range(3)) > 1e-3:
            raise ValueError(f"Fitted bind point {joint} did not survive RX3 serialization")
    if any(sum(part["weights"][i:i + 4]) != 255 for i in range(0, len(part["weights"]), 4)):
        raise ValueError("Generated RX3 has non-normalized skin weights")
    actual = {j for j, w in zip(part["joints"], part["weights"]) if w}
    if actual != set(order):
        raise ValueError("Generated RX3 bone-remap does not match the skin")
    return result, checked_parts, checked_bones


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    template_bytes = TEMPLATE_REFERENCE.read_bytes()
    reference_parts, reference_bones = read_model(Rx3(template_bytes))
    if len(reference_parts) != 1 or len(reference_bones) != 31:
        raise ValueError("The existing mascot animation model is not a 31-bone reference")
    weight_parts, weight_bones = read_model(Rx3(WEIGHT_REFERENCE.read_bytes()))
    if len(weight_parts) != 1 or len(weight_bones) != 31:
        raise ValueError("The in-game ball boy skin reference must contain one 31-bone mesh")
    bind_error = max(
        abs(a - b)
        for ref_bone, weight_bone in zip(reference_bones, weight_bones)
        for a, b in zip(ref_bone, weight_bone)
    )
    if bind_error > 1e-4:
        raise ValueError(f"Template and in-game ball-boy bind matrices differ: {bind_error:.6f}")
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    for _folder, club, _name, _texture in CLUBS:
        if (OUTPUT_ROOT / str(club)).exists():
            raise FileExistsError(f"Refusing to overwrite existing package: {OUTPUT_ROOT / str(club)}")

    temp_root = Path(tempfile.mkdtemp(prefix=".mascot-fbx-build-", dir=str(OUTPUT_ROOT)))
    built = []
    try:
        for folder_name, club, display_name, texture_name in CLUBS:
            source = SOURCE_ROOT / folder_name
            texture_source = source / texture_name
            if not texture_source.is_file():
                raise FileNotFoundError(f"Missing club texture RX3: {texture_source}")
            texture_rx = Rx3(texture_source.read_bytes())
            texture_names = {name for _type, name in texture_rx.names()}
            if len(texture_rx.get(TEXTURE)) != 3 or not {"head_cm", "head_sk", "head_nm"}.issubset(texture_names):
                raise ValueError(f"Unexpected mascot texture package: {texture_source.name}")

            vertices, indices, fbx_name, auto_scale_factor = load_source_mesh(source)
            joints, weights, order, right_arm, left_arm = transfer_weights(vertices, weight_parts[0])
            joints, weights, order, right_arm, left_arm, hand_vertices = add_hand_influences(vertices, joints, weights)
            fitted_binds, dimension_scale = fit_bind_positions(reference_bones, weight_parts[0], vertices, joints, weights)
            model_bytes, parts, bones = build_rx3(template_bytes, vertices, indices, joints, weights, order, fitted_binds)
            target = temp_root / str(club)
            target.mkdir()
            (target / "model.rx3").write_bytes(model_bytes)
            (target / "model_animated.rx3").write_bytes(model_bytes)
            shutil.copyfile(texture_source, target / "textures.rx3")
            report = {
                "id": club,
                "name": display_name,
                "meshSource": fbx_name,
                "textureSource": texture_name,
                "textureSourceSha256": sha256(texture_source),
                "modelSha256": hashlib.sha256(model_bytes).hexdigest(),
                "vertexCount": len(vertices),
                "triangleCount": len(indices) // 3,
                "sourceUniformScaleToMax200Cm": round(auto_scale_factor, 6),
                "boundsCm": {
                    "min": [min(parts[0]["positions"][i::3]) for i in range(3)],
                    "max": [max(parts[0]["positions"][i::3]) for i in range(3)],
                },
                "boneCount": len(bones),
                "usedBones": order,
                "rightArmWeightedVertices": right_arm,
                "leftArmWeightedVertices": left_arm,
                "handInfluenceVertices": {"negativeX": hand_vertices[-1], "positiveX": hand_vertices[1]},
                "referenceDimensionScale": dimension_scale,
                "fittedBindPositionsCm": {str(j): [round(c, 3) for c in p] for j, p in fitted_binds.items()},
                "rigMethod": "31-bone in-game FIFA 16 ball-boy weights transferred by nearest-surface interpolation",
                "skinReference": str(WEIGHT_REFERENCE),
                "skinReferenceSha256": sha256(WEIGHT_REFERENCE),
                "templateReference": str(TEMPLATE_REFERENCE),
                "maxBindDifferenceFromSkinReference": bind_error,
                "status": "generated; visual game validation pending",
            }
            (target / "club.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            built.append((club, target))
            print("BUILT_MASCOT " + json.dumps(report, ensure_ascii=False))

        for club, temp_package in built:
            final_package = OUTPUT_ROOT / str(club)
            temp_package.rename(final_package)
            print(f"INSTALLED_PACKAGE {final_package}")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()



