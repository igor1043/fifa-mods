"""Small floor meshes; reuse the room's existing shadow texture by reference.

This is contact shading, not a full-body shadow map. No player pixels, room
texture, career file or existing game asset is modified by this builder.
"""
from pathlib import Path
import os
import struct
import numpy as np
from native_assets import geometry, STRIDE
from rx3 import Rx3, MESH

MODEL = 'data/sceneassets/server16_club_xi/player_contact_shadow_r1.rx3'
TEXTURE_PATH = 'data/sceneassets/server16_dressing_room_20261022/contact_shadow_r51.rx3'
PARTS = ('xi_floor_contact_1', 'xi_floor_contact_2')


def build(template):
    batches = []
    for x in (-16., 16.):
        v = np.zeros(4, dtype=STRIDE)
        # Centimetres, relative to the actor origin. Lift only 2.5 mm to keep
        # the alpha surface separate from the floor, including in windowed mode.
        v['p'] = [(x-14, .25, -16), (x+14, .25, -16),
                  (x+14, .25, 26), (x-14, .25, 26)]
        v['n'] = (0, 1, 0)
        v['uv'] = [(0, 0), (1, 0), (1, 1), (0, 1)]
        batches.append((v, np.array([0, 1, 2, 0, 2, 3], dtype='<u4')))
    rx = Rx3(geometry(batches, template))
    rx.set_names([(MESH, part+'.FxRenderableSimple') for part in PARTS])
    return rx.build()


def prepare(game, read_asset):
    data = build(read_asset('data/sceneassets/prop/prop_102.rx3'))
    target = Path(game)/MODEL
    if not target.is_file() or target.read_bytes() != data:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name+'.new')
        temporary.write_bytes(data)
        os.replace(temporary, target)
    return target


def ensure_optional(game, read_asset):
    # A missing/locked optional floor asset must never block the player's model.
    try:
        prepare(game, read_asset)
        return True
    except (OSError, ValueError, struct.error):
        return False
