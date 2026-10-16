"""Blender: export the supplied FBX supports, preserving their UVs and materials."""
import argparse
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector

parser = argparse.ArgumentParser()
parser.add_argument('--sources', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
args.output.mkdir(parents=True, exist_ok=True)
variants = [('brasileirao', '1-BRASILEIRAO'), ('generic1', '2-GENERICO1'),
            ('generic2', '3-GENERIC 2'), ('cbf', '4-CBF'), ('paulistao', '5-PAULISTAO')]
for slug, folder in variants:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    fbx = next((args.sources / folder).glob('*.fbx'))
    bpy.ops.import_scene.fbx(filepath=str(fbx))
    objects = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
    lo = [min(p[i] for p in points) for i in range(3)]
    hi = [max(p[i] for p in points) for i in range(3)]
    # 26 cm across, centred under a regulation-size match ball; preserve shape.
    scale = 26.0 / max(hi[0] - lo[0], hi[1] - lo[1])
    center = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    vertices, indices, lookup, materials = [], [], {}, []
    for obj in objects:
        bpy.context.view_layer.objects.active = obj
        original_triangles = sum(len(p.vertices) - 2 for p in obj.data.polygons)
        if original_triangles > 2400:
            modifier = obj.modifiers.new('Sideline distance', 'DECIMATE')
            modifier.ratio = 2400.0 / original_triangles
            modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh = obj.data
        mesh.calc_loop_triangles()
        assert mesh.uv_layers.active, obj.name
        mesh.calc_tangents(uvmap=mesh.uv_layers.active.name)
        nm = obj.matrix_world.to_3x3().inverted().transposed()
        tm = obj.matrix_world.to_3x3()
        material_offset = len(materials)
        for mat in mesh.materials:
            images = []
            if mat and mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        images.append({'name': node.image.name,
                                       'path': bpy.path.abspath(node.image.filepath),
                                       'colorspace': node.image.colorspace_settings.name,
                                       'links': [link.to_socket.name for link in node.outputs['Color'].links]})
            materials.append({'name': mat.name if mat else '', 'images': images})
        def direction(p):
            return [float(p.x), float(p.z), float(-p.y)]
        for tri in mesh.loop_triangles:
            for li in tri.loops:
                loop = mesh.loops[li]
                p = (obj.matrix_world @ mesh.vertices[loop.vertex_index].co - center) * scale
                normal = (nm @ loop.normal).normalized()
                tangent = (tm @ loop.tangent).normalized()
                uv = mesh.uv_layers.active.data[li].uv
                vertex = [direction(p), direction(normal), direction(tangent),
                          [float(uv.x), float(1 - uv.y)], material_offset + tri.material_index]
                key = tuple(round(x, 7) for field in vertex[:4] for x in field) + (vertex[4],)
                if key not in lookup:
                    lookup[key] = len(vertices)
                    vertices.append(vertex)
                indices.append(lookup[key])
    assert len(vertices) < 65536 and vertices
    report = {'variant': slug, 'vertices': vertices, 'indices': indices,
              'materials': materials, 'source_bounds': [lo, hi], 'width_cm': 26.0}
    (args.output / (slug + '.json')).write_text(json.dumps(report), encoding='utf8')
    print(slug, len(vertices), 'vertices', len(indices) // 3, 'triangles', materials)
