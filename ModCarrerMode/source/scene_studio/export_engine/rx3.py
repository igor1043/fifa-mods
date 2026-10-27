"""Bounded FIFA 16 RX3 reader/writer. Never writes into the game installation.

Layouts checked against the local renderer and tokke001/FIFALibrary22.
"""
import base64
import math
import struct
from containers import unpack

NAME = 0x4C9B9EB2
VERTEX = 0x00587AA1
INDEX = 0x005878F4
FORMAT = 0xC28193F0
MESH = 0xD48D7880
TEXTURE = 0x7A0B60DA
MATERIAL = 0x075BD958
INSTANCE = 0x7E2480EC
LAYER = 0x0DC3FFD4


class Rx3:
    def __init__(self, raw):
        if raw[:3] != b'RX3':
            raw = unpack(raw)
        if raw[:4] != b'RX3l' or len(raw) > 1024 * 1024 * 1024:
            raise ValueError('RX3 little-endian necessário')
        self.version = struct.unpack_from('<I', raw, 4)[0]
        count = struct.unpack_from('<I', raw, 12)[0]
        if not 0 < count <= 20000 or 16 + count * 16 > len(raw):
            raise ValueError('Diretório RX3 inválido')
        self.sections = []
        for i in range(count):
            typ, at, size, reserved = struct.unpack_from('<4I', raw, 16 + 16 * i)
            if at < 16 + count * 16 or size < 4 or at + size > len(raw):
                raise ValueError('Seção RX3 fora do arquivo')
            self.sections.append([typ, raw[at:at + size], reserved])

    def get(self, typ):
        return [s[1] for s in self.sections if s[0] == typ]

    def names(self):
        result = []
        for data in self.get(NAME):
            count = struct.unpack_from('<I', data, 4)[0]
            p = 16
            if count > 30000:
                raise ValueError('Tabela de nomes muito grande')
            for _ in range(count):
                typ, size = struct.unpack_from('<II', data, p)
                p += 8
                if not 0 < size <= 4096 or p + size > len(data):
                    raise ValueError('Nome RX3 inválido')
                result.append((typ, data[p:p + size].split(b'\0')[0].decode('utf8')))
                p += size
        return result

    def set_names(self, names):
        data = bytearray(struct.pack('<4I', 0, len(names), 0, 0))
        for typ, name in names:
            encoded = name.encode('utf8') + b'\0'
            data.extend(struct.pack('<II', typ, len(encoded)) + encoded)
        data = sized(data)
        existing = [s for s in self.sections if s[0] == NAME]
        if len(existing) != 1:
            raise ValueError('Uma tabela de nomes RX3 é necessária')
        existing[0][1] = data

    def build(self):
        count = len(self.sections)
        output = bytearray(align(16 + count * 16))
        output[:16] = b'RX3l' + struct.pack('<III', self.version, 0, count)
        for i, (typ, payload, reserved) in enumerate(self.sections):
            output.extend(b'\0' * (align(len(output)) - len(output)))
            at = len(output)
            output.extend(payload)
            struct.pack_into('<4I', output, 16 + 16 * i, typ, at, len(payload), reserved)
        output.extend(b'\0' * (align(len(output)) - len(output)))
        struct.pack_into('<I', output, 8, len(output))
        return bytes(output)


def align(n):
    return (n + 15) & ~15


def sized(data):
    data = bytearray(data)
    data.extend(b'\0' * (align(len(data)) - len(data)))
    struct.pack_into('<I', data, 0, len(data))
    return bytes(data)


def invert4(values):
    # Input/output is column-major, matching RX3/Three.js bind matrices.
    rows = [[values[c * 4 + r] for c in range(4)] + [float(r == c) for c in range(4)] for r in range(4)]
    for c in range(4):
        k = max(range(c, 4), key=lambda r: abs(rows[r][c]))
        rows[c], rows[k] = rows[k], rows[c]
        d = rows[c][c]
        if abs(d) < 1e-9:
            raise ValueError('Matriz do rig não invertível')
        rows[c] = [v / d for v in rows[c]]
        for r in range(4):
            if r != c:
                d = rows[r][c]
                rows[r] = [a - d * b for a, b in zip(rows[r], rows[c])]
    return [rows[r][c + 4] for c in range(4) for r in range(4)]


def read_model(rx):
    descriptors, vertices, indices = rx.get(FORMAT), rx.get(VERTEX), rx.get(INDEX)
    mesh_names = [n for t, n in rx.names() if t == MESH]
    primitives = rx.get(MESH)
    if not vertices or len(vertices) != len(indices) or len(vertices) != len(descriptors):
        raise ValueError('Malhas RX3 inconsistentes')
    parts = []
    for i, (desc, vb, ib) in enumerate(zip(descriptors, vertices, indices)):
        n, stride = struct.unpack_from('<II', vb, 4)
        count, width = struct.unpack_from('<II', ib, 4)
        if not 0 < n <= 500000 or not 0 < count <= 3000000 or not 0 < stride <= 256 or width not in (2, 4):
            raise ValueError('Dimensões da malha inválidas')
        if 16 + n * stride > len(vb) or 16 + count * width > len(ib):
            raise ValueError('Buffer da malha truncado')
        fields = {}
        for token in desc[16:].split(b'\0')[0].decode().split():
            semantic, off, stream, usage, fmt = token.split(':')
            fields[semantic] = (int(off, 16), fmt)
        if 'p0' not in fields:
            raise ValueError('Malha sem posição')
        positions, normals, uvs, joints, weights = [], [], [], [], []
        for v in range(n):
            at = 16 + v * stride
            off, fmt = fields['p0']
            pos = struct.unpack_from('<3e' if fmt == '4f16' else '<3f', vb, at + off)
            if not all(math.isfinite(x) and abs(x) < 100000 for x in pos):
                raise ValueError('Posição da malha inválida')
            positions.extend(pos)
            normal = [0., 1., 0.]
            if 'n0' in fields:
                off, fmt = fields['n0']
                if fmt == '3s10n':
                    packed = struct.unpack_from('<I', vb, at + off)[0]
                    normal = []
                    for shift in (0, 10, 20):
                        value = (packed >> shift) & 1023
                        normal.append(max(-1., (value - 1024 if value & 512 else value) / 511.))
                elif fmt == '3f32':
                    normal = list(struct.unpack_from('<3f', vb, at + off))
            normals.extend(normal)
            off, fmt = fields.get('t0', (0, 'none'))
            uvs.extend(struct.unpack_from('<2e' if fmt == '2f16' else '<2f', vb, at + off) if fmt != 'none' else (0., 0.))
            j, w = [0] * 4, [0] * 4
            if 'i0' in fields and 'w0' in fields:
                off, fmt = fields['i0']
                j = list(struct.unpack_from('<4H' if fmt == '4u16' else '<4B', vb, at + off))
                off, _ = fields['w0']
                w = list(vb[at + off:at + off + 4])
            joints.extend(j)
            weights.extend(w)
        ids = list(struct.unpack_from('<' + str(count) + ('H' if width == 2 else 'I'), ib, 16))
        primitive = struct.unpack_from('<H', primitives[i])[0] if i < len(primitives) else 4
        if primitive == 5:
            triangles = []
            for k in range(2, count):
                a, b, c = ids[k - 2:k + 1]
                if k % 2:
                    a, b = b, a
                if len({a, b, c}) == 3:
                    triangles.extend((a, b, c))
            ids = triangles
        elif primitive != 4 or count % 3:
            raise ValueError('Primitiva não suportada: ' + str(primitive))
        if max(ids, default=0) >= n:
            raise ValueError('Índice da malha inválido')
        parts.append(dict(name=mesh_names[i] if i < len(mesh_names) else 'mascote', positions=positions, normals=normals, uvs=uvs, indices=ids, joints=joints, weights=weights))
    matrices = []
    for section in rx.get(0xDF9AEC1E):
        count = struct.unpack_from('<I', section, 4)[0]
        if count == 31 and len(section) == 16 + 31 * 64:
            for i in range(31):
                m = list(struct.unpack_from('<16f', section, 16 + i * 64))
                m[15] = 1.
                matrices.append(invert4(m))
    return parts, matrices


def pose_parts(parts, matrices, standing=True):
    # A simple visual standing pose, independent of the game's animation graph.
    import copy
    result = copy.deepcopy(parts)
    if standing and len(matrices) == 31:
        shoulders = {17: matrices[17][12:15], 22: matrices[22][12:15]}
        for part in result:
            for i in range(len(part['positions']) // 3):
                p = part['positions'][i * 3:i * 3 + 3]
                n = part['normals'][i * 3:i * 3 + 3]
                total = sum(part['weights'][i * 4:i * 4 + 4])
                if not total:
                    continue
                outp, outn = [0.] * 3, [0.] * 3
                for joint, weight in zip(part['joints'][i * 4:i * 4 + 4], part['weights'][i * 4:i * 4 + 4]):
                    if not weight:
                        continue
                    base = 17 if joint in (17, 18, 19, 20) else 22 if joint in (22, 23, 24, 25) else None
                    pp, nn = p, n
                    if base:
                        angle = math.radians(-68 if base == 17 else 68)
                        c, s = math.cos(angle), math.sin(angle)
                        sx, sy, sz = shoulders[base]
                        x, y = p[0] - sx, p[1] - sy
                        pp = [sx + c * x - s * y, sy + s * x + c * y, p[2]]
                        nn = [c * n[0] - s * n[1], s * n[0] + c * n[1], n[2]]
                    for k in range(3):
                        outp[k] += pp[k] * weight / total
                        outn[k] += nn[k] * weight / total
                part['positions'][i * 3:i * 3 + 3] = outp
                part['normals'][i * 3:i * 3 + 3] = outn
    floor = min(p['positions'][1::3][i] for p in result for i in range(len(p['positions']) // 3))
    for part in result:
        for i in range(1, len(part['positions']), 3):
            part['positions'][i] -= floor
    return result


def diffuse(rx):
    names = [n for t, n in rx.names() if t == TEXTURE]
    textures = rx.get(TEXTURE)
    candidates = [i for i, name in enumerate(names) if name == 'cm' or name.endswith('_cm')]
    if not candidates:
        raise ValueError('Textura de cor do mascote não encontrada')
    i = candidates[0]
    data = textures[i]
    fmt = data[5]
    w, h = struct.unpack_from('<HH', data, 8)
    if fmt not in (0, 1, 2) or not 0 < w <= 4096 or not 0 < h <= 4096:
        raise ValueError('Textura de cor incompatível')
    required = ((w + 3) // 4) * ((h + 3) // 4) * (8 if fmt == 0 else 16)
    if 32 + required > len(data):
        raise ValueError('Textura de cor truncada')
    return i, dict(name=names[i], width=w, height=h, format=fmt, data=base64.b64encode(data[32:32 + required]).decode())
