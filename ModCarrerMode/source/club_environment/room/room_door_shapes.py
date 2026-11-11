"""Reusable closed-door geometry; no career, file or renderer side effects."""
import math
import numpy as np
from room_visual_r68 import VERT, box, packed

RIGHT_SHIFT_CM = 100.
CENTER_Z = 1450. - RIGHT_SHIFT_CM


def cylinder(center, radius, length, axis=1, sides=12):
    center = np.asarray(center, dtype=float); vertices = []; ids = []
    u, w = (axis + 1) % 3, (axis + 2) % 3
    tangent = np.zeros(3); tangent[axis] = 1
    for end in (-.5, .5):
        for i in range(sides + 1):
            angle = i * math.tau / sides
            normal = np.zeros(3); normal[u] = math.cos(angle); normal[w] = math.sin(angle)
            p = center + radius * normal; p[axis] += length * end
            vertices.append((p, packed(normal), packed(tangent), (i / sides, end + .5)))
    for i in range(sides):
        j = i + sides + 1; ids.extend((i, i + 1, j + 1, i, j + 1, j))
    # Caps are separate vertices so the rim does not smear the side normals.
    for ring, sign in ((0, -1), (sides + 1, 1)):
        normal = np.zeros(3); normal[axis] = sign
        tangent = np.zeros(3); tangent[u] = 1
        start = len(vertices); p = center.copy(); p[axis] += sign * length / 2
        vertices.append((p, packed(normal), packed(tangent), (.5, .5)))
        for i in range(sides + 1):
            vertices.append((vertices[ring + i][0], packed(normal), packed(tangent), (.5, .5)))
        for i in range(sides):
            ids.extend((start, start + i + 1, start + i + 2) if sign > 0 else (start, start + i + 2, start + i + 1))
    v = np.zeros(len(vertices), dtype=VERT)
    for i, item in enumerate(vertices): v[i] = item
    return v, np.asarray(ids, dtype='<u2')


def geometry(include_annex=True):
    groups = {key: [] for key in ('leaves', 'frame', 'metal', 'kick')}
    def solid(key, lo, hi): groups[key].append(box(lo, hi))
    z = CENTER_Z
    # Flush leaves with a visible 6 mm central seam and a recessed reveal.
    for lo, hi in ((z - 77.4, z - .5), (z + .5, z + 77.4)):
        v, idx = box((-849.2, 1001.5, lo), (-844.8, 1233.8, hi))
        v['uv'][:, 0] = (hi - v['p'][:, 2]) / (hi - lo)
        v['uv'][:, 1] = (1233.8 - v['p'][:, 1]) / 232.3
        groups['leaves'].append((v, idx))
        # Brackets project from the leaf; the push bar sits at 105 cm, not 66.
        for pos in (lo + 10., hi - 10.):
            solid('metal', (-844.55, 1099., pos - 2.5), (-837.6, 1111., pos + 2.5))
            solid('kick', (-837.5, 1101., pos - 1.5), (-836.6, 1109., pos + 1.5))
        groups['metal'].append(cylinder((-836.5, 1105., (lo + hi) / 2), 1.6, hi - lo - 13., axis=2))
        # Low dark kick plate, fine stainless border and four small fasteners.
        solid('metal', (-844.55, 1006., lo + 4.), (-844.2, 1031., hi - 4.))
        solid('kick', (-844.05, 1006.7, lo + 4.7), (-843.75, 1030.3, hi - 4.7))
        for y in (1008.2, 1028.8):
            for p in (lo + 6.2, hi - 6.2):
                groups['metal'].append(cylinder((-843.55, y, p), .28, .2, axis=0, sides=8))
    for side in (-1, 1):
        p = z + side * 81.
        solid('frame', (-851., 1000.4, p - 3.2), (-842.7, 1241.8, p + 3.2))
        for y in (1027., 1119., 1211.):
            groups['metal'].append(cylinder((-842.1, y, z + side * 78.5), .85, 10.))
    solid('frame', (-851., 1234.4, z - 84.2), (-842.7, 1241.8, z + 84.2))
    solid('frame', (-850., 1000.5, z - .5), (-848.3, 1234., z + .5))
    solid('metal', (-849., 1000.2, z - 77.4), (-838.8, 1000.8, z + 77.4))
    # Sign backing is proud of the wall, with no coplanar texture layers.
    solid('frame', (-846., 1248., z - 74.), (-842.3, 1276., z + 74.))
    if include_annex:
        from room_annex_doors import geometry as annex_geometry
        for key,shapes in annex_geometry().items():groups.setdefault(key,[]).extend(shapes)
    return groups
