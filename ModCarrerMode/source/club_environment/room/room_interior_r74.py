"""Quiet architectural finishes over the existing, collision-tested R72 room.

The club identity stays on the lockers, signs and editable focal mural. Paint
and washable ceramic are neutral materials rather than repeated club artwork.
This module never reads or writes a career file.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from rx3 import Rx3
from room_visual_r68 import box, read_mesh
from room_interior_r71 import PREFIX, panel, within


def surface_images():
    # Subtle paint grain, deliberately under two RGB levels: surface finish,
    # not a graphic/noise layer that shimmers or smears in native mipmaps.
    rng = np.random.default_rng(7401)
    grain = rng.integers(-1, 2, (256, 256, 1), dtype=np.int16)
    paint = np.empty((256, 256, 4), dtype=np.uint8)
    paint[:, :, :3] = np.array([224, 223, 218]) + grain
    paint[:, :, 3] = 255
    # 60 x 30 cm ceramic, 2.3 mm joints, world-scaled in the mesh below.
    # Restrained variation between tiles, not baked lighting or grunge.
    tile = np.empty((1024, 1024, 4), dtype=np.uint8)
    tile[:, :, :3] = [209, 209, 201]
    tile[512:, :, :3] = [212, 211, 204]
    tile[:4, :, :3] = tile[512:516, :, :3] = [176, 179, 173]
    tile[:, :4, :3] = [176, 179, 173]
    tile[:, :, 3] = 255
    return {'graphic': Image.fromarray(paint), 'backsplash': Image.fromarray(tile)}


def stage(game, output):
    """Rebuild finish panels without changing the navigable room or furniture."""
    from room_interior_r72 import write_groups, wall_graphic_uv
    game, output = Path(game), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    base = game / PREFIX
    spec = json.loads((base / 'interior_r72.json').read_text(encoding='utf8'))
    source = base / ('interior_r73.rx3' if (base / 'interior_r73.rx3').is_file() else 'interior_r72.rx3')
    rx = Rx3(source.read_bytes())
    groups = {}
    for slot, binding in enumerate(spec['bindings']):
        key = binding['material']
        v, indices = read_mesh(rx, slot)
        if key in ('charcoal', 'metal'):
            # This closed exit straddled the R72 extension cut. Move the whole
            # fixture together: stretching only one leaf made a 5 m wide door.
            p = v['p']
            exit_edge = ((p[:, 0] >= -751.1) & (p[:, 0] <= -743.9)
                         & (p[:, 1] >= 1000) & (p[:, 1] <= 1241.1)
                         & (p[:, 2] >= 767) & (p[:, 2] < 815))
            v['p'][exit_edge, 2] += 360
        triangles = indices.reshape(-1, 3)
        points = v['p'][triangles]
        drop = np.zeros(len(triangles), dtype=bool)
        if key == 'primary':
            # The old 15-22 cm bright surround is not structural geometry.
            drop = within(points, [-465, 1042, 1300], [105, 1265, 1303])
        elif key == 'graphic':
            # Give the hydration backsplash its own practical ceramic finish.
            drop = within(points, [327, 1096, 1301.5], [617, 1252, 1301.9])
        elif key == 'signs':
            drop = within(points, [-744, 1247, 774], [-743, 1273, 1286])
        kept = triangles[~drop]
        if not len(kept):
            raise ValueError('An existing native material group became empty: ' + key)
        if drop.any():
            used, inverse = np.unique(kept, return_inverse=True)
            v, indices = v[used], inverse.reshape(-1).astype('<u2')
        groups[key] = [(v, indices)]

    def add(key, item):
        groups.setdefault(key, []).append(item)

    # Match the shared 4:1 sign atlas, centered over the complete double door.
    add('signs', panel([-743.7, 1260, 1210], 150, 37.5, (1, 0, 0), (0, .50, 1, .75)))

    # Three separate exposed wall sections respect both existing door openings.
    # Frieze and wall use the same neutral paint, so there is no graphic border.
    for left, right in [(-750, -615), (-475, 110), (250, 750)]:
        v, idx = panel([(left + right) / 2, 1132, 1303.1], right - left, 264, (0, 0, -1))
        add('graphic', (wall_graphic_uv(v), idx))
        add('charcoal', box((left, 1000.2, 1301.4), (right, 1010, 1303)))

    # A fine 2 cm charcoal frame around the unchanged 540 x 180 cm club mural.
    add('charcoal', box((-452, 1061, 1299.9), (92, 1245, 1302.6)))
    v, idx = panel([472, 1174, 1301.7], 290, 156, (0, 0, -1))
    v = wall_graphic_uv(v)
    v['uv'][:, 0] *= 4  # 60 cm horizontal repeat, matching the vertical repeat.
    add('backsplash', (v, idx))
    spec['bindings'] = write_groups(base / 'locker_support_r68.rx3', groups, output / 'interior_r74.rx3')
    spec['revision'] = 74
    spec['finish'] = 'neutral matte paint, ceramic backsplash, narrow charcoal mural frame'
    (output / 'interior_r74.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding='utf8')
    return spec


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = stage(args.game, args.output)
    print(json.dumps({'revision': 74, 'material_groups': len(result['bindings'])}))
