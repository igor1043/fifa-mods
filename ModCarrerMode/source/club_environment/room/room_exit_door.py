"""Closed V3 exit: independent leaf finish, fixed frame and safety hardware.

Coordinates are native centimetres. The existing wall and navigation bounds
are retained; this is a visual replacement, not a new traversable doorway.
"""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageOps
from room_visual_r68 import VERT, box, join, packed, read_mesh, replace_mesh
from room_interior_r71 import panel
from room_door_shapes import RIGHT_SHIFT_CM, CENTER_Z, cylinder, geometry
import room_appearance as appearance

OLD_LO = np.array([-852., 999.9, 1365.])
OLD_HI = np.array([-843., 1280., 1534.])
FINISHES = ('black', 'graphite', 'white', 'walnut', 'steel', 'primary', 'secondary', 'custom')
TEXTURE_SIZE = (512, 1536)


def old_door_triangles(vertices, indices):
    points = vertices['p'][indices.reshape(-1, 3)]
    return ((points >= OLD_LO) & (points <= OLD_HI)).all((1, 2))


def replace_old_fixture(rx):
    """Keep every unrelated triangle and vertex attribute byte-for-byte."""
    removed = []
    for slot, expected in ((0, 60), (1, 48)):
        v, idx = read_mesh(rx, slot); triangles = idx.reshape(-1, 3)
        drop = old_door_triangles(v, idx)
        if int(drop.sum()) != expected:
            raise ValueError('Unexpected existing exit door; room model left unchanged')
        used, inverse = np.unique(triangles[~drop], return_inverse=True)
        replace_mesh(rx, slot, v[used], inverse.reshape(-1).astype('<u2'))
        removed.append(int(drop.sum()))
    # Reuse the existing club-sign atlas and mesh slot, at its new proportions.
    v, idx = read_mesh(rx, 3)
    if len(idx) != 6 or not old_door_triangles(v, idx).all():
        raise ValueError('Unexpected exit sign; room model left unpublished')
    v, idx = panel([-841.9, 1262., CENTER_Z], 146., 27., (1, 0, 0), (0, .5, 1, .75))
    replace_mesh(rx, 3, v, idx)
    return removed




def finish_image(game, context, choice, size=TEXTURE_SIZE):
    """High-resolution matte finishes; custom artwork is local to each club."""
    if choice not in FINISHES: raise ValueError('Invalid exit-door finish')
    if choice == 'custom':
        custom = appearance.asset(game, context['club'], 'exit_door')
        if custom:
            from room_v3 import editable_image
            return ImageOps.fit(editable_image(custom), size, Image.Resampling.LANCZOS)
        choice = 'black'
    folder = Path(game) / appearance.ROOT / 'generic/materials'
    source = folder / ('walnut.png' if choice == 'walnut' else 'exit-door-' + choice + '.png')
    if source.is_file() and choice not in ('primary', 'secondary'):
        with Image.open(source) as image:
            return ImageOps.fit(image.convert('RGBA'), size, Image.Resampling.LANCZOS)
    rgb = {'black': (25, 28, 30), 'graphite': (66, 71, 76), 'white': (231, 232, 228),
           'steel': (157, 164, 168), 'walnut': (84, 55, 37)}.get(choice)
    if choice in ('primary', 'secondary'):
        rgb = tuple(max(12, round(max(0., min(1., c)) * 255)) for c in context['colors'][choice == 'secondary'])
    # Subtle powder-coat grain; no painted lighting or fake shadow in the image.
    noise = np.random.default_rng(7716).normal(0, .55 if choice != 'steel' else .9, (size[1], size[0], 1))
    if choice == 'steel': noise += np.random.default_rng(9).normal(0, .8, (size[1], 1, 1))
    pixels = np.empty((size[1], size[0], 4), dtype=np.uint8)
    pixels[:, :, :3] = np.clip(np.asarray(rgb) + noise, 0, 255).round().astype(np.uint8)
    pixels[:, :, 3] = 255
    return Image.fromarray(pixels)


def prepare(manifest, context, game, add, identity, prefs):
    if not manifest.get('exit_door_bindings'): return
    from room_v3 import PREFIX, texture
    model = PREFIX + manifest['model_files']['exit_door.rx3']
    for binding in manifest['exit_door_bindings']:
        material = binding['material']
        image = finish_image(game, context, prefs.get('door_finish', 'black'),
                             (768,1536) if material=='annex_leaves' else TEXTURE_SIZE) if material in ('leaves','annex_leaves') else Image.new(
            'RGBA', (8, 8), {'frame': (24, 27, 30, 255), 'metal': (161, 170, 176, 255), 'kick': (35, 39, 43, 255)}[material])
        add('v3_exit_door_' + material, model, texture(game, image, 'exit_door'), 'v3_cm', identity, submesh=binding['submesh'])
