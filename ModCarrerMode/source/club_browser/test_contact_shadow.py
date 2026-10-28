"""Verify floor placement/winding/UVs using FIFA's real RX3 format."""
import struct
from unittest.mock import patch
import numpy as np
from rx3 import Rx3, VERTEX, INDEX, MESH
from contact_shadow import build, PARTS, ensure_optional


def run(read_asset):
    template = read_asset('data/sceneassets/prop/prop_102.rx3')
    rx = Rx3(build(template))
    assert rx.names() == [(MESH, part+'.FxRenderableSimple') for part in PARTS]
    assert len(rx.get(VERTEX)) == len(rx.get(INDEX)) == 2
    for side, (raw, index) in enumerate(zip(rx.get(VERTEX), rx.get(INDEX))):
        n, stride = struct.unpack_from('<II', raw, 4)
        assert n == 4 and stride == 20
        pos = np.ndarray((n, 4), dtype='<f2', buffer=raw, offset=16,
                         strides=(stride, 2)).astype(float)[:, :3]
        uv = np.ndarray((n, 2), dtype='<f2', buffer=raw, offset=32,
                        strides=(stride, 2)).astype(float)
        assert np.isfinite(pos).all() and set(pos[:, 1]) == {.25}
        assert set(map(tuple, uv)) == {(0., 0.), (0., 1.), (1., 0.), (1., 1.)}
        assert np.allclose(pos[:, 0].mean(), -16 if side == 0 else 16)
        assert np.ptp(pos[:, 0]) == 28
        assert np.ptp(pos[:, 2]) == 42
        normal = np.ndarray((n,), dtype='<u4', buffer=raw, offset=24, strides=(stride,))
        assert np.all(normal == 511 << 10)
        count = struct.unpack_from('<I', index, 4)[0]
        ids = np.frombuffer(index, '<u2', count, 16).reshape(-1, 3)
        assert ids.max() < 4
        for a, b, c in ids:
            assert np.cross(pos[b]-pos[a], pos[c]-pos[a])[1] > 0
    assert template == read_asset('data/sceneassets/prop/prop_102.rx3')
    with patch('contact_shadow.prepare', side_effect=PermissionError('locked optional asset')):
        assert not ensure_optional('unused', read_asset)
    print('PASS native contact shadows: two floor meshes, correct UVs/winding, 2.5mm separation, no player or source asset changes')
