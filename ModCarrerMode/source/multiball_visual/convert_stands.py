"""Convert exported FBX geometry to static FIFA RX3 assets and check the result."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image, ImageOps

parser = argparse.ArgumentParser()
parser.add_argument('--meshes', type=Path, required=True)
parser.add_argument('--game', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--tools', type=Path, default=Path(r'J:\mods\fifa 16\02_Ferramentas\mascot_rig_adjuster'))
args = parser.parse_args()
sys.path[:0] = [str(args.tools), str(args.tools / 'vendor/rx3tools')]
from rx3 import Rx3, read_model, VERTEX, INDEX, MESH, TEXTURE, align
from texture_assets import rx3_colour_png

def packed(v):
    return sum((int(round(max(-1, min(1, x)) * 511)) & 1023) << shift
               for x, shift in zip(v, (0, 10, 20)))

def texture(image, template, normal=False):
    image = image.convert('RGBA')
    w, h = image.size
    b = bytearray(template[:16]); b[5] = 2
    count = 0
    while True:
        out = io.BytesIO(); image.save(out, format='DDS', pixel_format='DXT5')
        raw = out.getvalue()[128:]
        pitch = max(1, (image.width + 3) // 4) * 16
        rows = max(1, (image.height + 3) // 4)
        assert len(raw) == pitch * rows
        b.extend(struct.pack('<4I', pitch, rows, len(raw), 0)); b.extend(raw); count += 1
        if image.width == image.height == 1:
            break
        image = image.resize((max(1, image.width // 2), max(1, image.height // 2)), Image.Resampling.LANCZOS)
        if normal:
            a = np.array(image); v = a[:, :, :3].astype(np.float32) / 127.5 - 1
            v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-8)
            a[:, :, :3] = np.clip(np.rint((v + 1) * 127.5), 0, 255).astype(np.uint8)
            a[:, :, 3] = 255; image = Image.fromarray(a)
    struct.pack_into('<I', b, 0, len(b)); struct.pack_into('<4H', b, 8, w, h, 1, count)
    return bytes(b)

reports = []
args.output.mkdir(parents=True, exist_ok=True)
for mesh_path in sorted(p for p in args.meshes.glob('*.json') if not p.stem.endswith('_decoded')):
    data = json.loads(mesh_path.read_text(encoding='utf8'))
    slug = data['variant']; vertices = data['vertices']; indices = data['indices']
    dest = args.output / slug; dest.mkdir(exist_ok=True)
    assert len(data['materials']) == 1 and all(v[4] == 0 for v in vertices)
    rx = Rx3((args.game / 'data/sceneassets/slc/specificcameramansitting_0_24_0.rx3').read_bytes())
    vb = bytearray(align(16 + 20 * len(vertices)))
    struct.pack_into('<4I', vb, 0, len(vb), len(vertices), 20, 1)
    for i, (p, n, t, uv, _) in enumerate(vertices):
        struct.pack_into('<4eII2e', vb, 16 + i * 20, *p, 1, packed(n), packed(t), *uv)
    ib = bytearray(align(16 + 2 * len(indices)))
    struct.pack_into('<4I', ib, 0, len(ib), len(indices), 2, 0)
    struct.pack_into('<' + 'H' * len(indices), ib, 16, *indices)
    for section in rx.sections:
        if section[0] == VERTEX: section[1] = bytes(vb)
        elif section[0] == INDEX: section[1] = bytes(ib)
        elif section[0] == MESH:
            b = bytearray(section[1]); struct.pack_into('<H', b, 0, 4); section[1] = bytes(b)
        elif section[0] == 0x22B2BE36:
            b = bytearray(section[1]); struct.pack_into('<III', b, 16, len(ib), len(indices), 2); section[1] = bytes(b)
    rx.set_names([(MESH, 'standball_' + slug + '_.FxRenderableSimple')])
    (dest / 'model.rx3').write_bytes(rx.build())
    parts, bones = read_model(Rx3((dest / 'model.rx3').read_bytes())); part = parts[0]
    assert len(parts) == 1 and not bones and max(part['indices']) < len(vertices)
    p = np.array(part['positions']).reshape(-1, 3)
    n = np.array(part['normals']).reshape(-1, 3)
    f = np.array(part['indices']).reshape(-1, 3)
    assert np.isfinite(p).all() and np.isfinite(n).all()
    position_error = max(abs(a - b) for i, v in enumerate(vertices) for a, b in zip(v[0], p[i]))
    uv_error = max(abs(a - b) for i, v in enumerate(vertices) for a, b in zip(v[3], part['uvs'][2*i:2*i+2]))
    assert position_error < .02 and uv_error < .002
    dot = np.einsum('ij,ij->i', np.cross(p[f[:, 1]] - p[f[:, 0]], p[f[:, 2]] - p[f[:, 0]]), n[f].mean(axis=1))
    assert (dot > .001).sum() > (dot < -.001).sum() * 10
    # Sphere/mesh contact, including triangle interiors, avoids floating above a
    # recessed seat. This uses the decoded, quantized geometry installed in FIFA.
    radius = 11.1252
    samples = [p]
    for a in range(9):
        for b in range(9 - a):
            samples.append((p[f[:, 0]] * a + p[f[:, 1]] * b + p[f[:, 2]] * (8-a-b)) / 8)
    samples = np.concatenate(samples)
    radial = samples[:, 0]**2 + samples[:, 2]**2
    valid = radial < radius**2
    contact_y = float(np.max(samples[valid, 1] + np.sqrt(radius**2 - radial[valid]))) + .08
    images = data['materials'][0]['images']
    colour_path = Path(next(im['path'] for im in images if 'Base Color' in im['links']))
    normal_path = Path(next(im['path'] for im in images if im['colorspace'] == 'Non-Color'))
    colour = Image.open(colour_path).convert('RGBA').resize((1024, 1024), Image.Resampling.LANCZOS)
    red, green, blue = Image.open(normal_path).convert('RGB').resize((1024, 1024), Image.Resampling.LANCZOS).split()
    normal = Image.merge('RGBA', (red, ImageOps.invert(green), blue, Image.new('L', (1024, 1024), 255)))
    tx = Rx3((args.game / 'data/sceneassets/smoke_machine/textures.rx3').read_bytes())
    sections = [s for s in tx.sections if s[0] == TEXTURE]
    assert len(sections) == 3
    template = sections[0][1]
    for section, im, is_normal in zip(sections, (colour, Image.new('RGBA', (64, 64), (18, 35, 0, 255)), normal), (False, False, True)):
        section[1] = texture(im, template, is_normal)
    tx.set_names([(TEXTURE, 'standball_' + slug + '_' + suffix) for suffix in ('cm', 'coeff', 'nm')])
    (dest / 'textures.rx3').write_bytes(tx.build())
    checked = Rx3((dest / 'textures.rx3').read_bytes())
    for section in checked.get(TEXTURE):
        w, h, _, count = struct.unpack_from('<4H', section, 8); at = 16
        assert count == int(math.log2(max(w, h))) + 1
        for _ in range(count):
            pitch, rows, size, _ = struct.unpack_from('<4I', section, at)
            assert pitch == max(1, (w+3)//4)*16 and rows == max(1, (h+3)//4) and size == pitch*rows
            at += 16 + size; w = max(1, w//2); h = max(1, h//2)
        assert at == len(section)
    (args.meshes / (slug + '_decoded.json')).write_text(json.dumps(part), encoding='utf8')
    (args.meshes / (slug + '_colour.png')).write_bytes(rx3_colour_png(dest / 'textures.rx3'))
    reports.append({'variant': slug, 'vertices': len(vertices), 'triangles': len(indices)//3,
                    'bounds_cm': [p.min(axis=0).tolist(), p.max(axis=0).tolist()],
                    'position_error_cm': position_error, 'uv_error': uv_error,
                    'ball_center_y_cm': round(contact_y, 4),
                    'files': {q.name: {'size': q.stat().st_size, 'sha256': hashlib.sha256(q.read_bytes()).hexdigest()} for q in dest.glob('*.rx3')}})
header = ['#pragma once', 'struct StandAsset { const char* slug; float ballHeight; unsigned modelBytes,textureBytes; const char* modelHash; const char* textureHash; };', 'static const StandAsset standAssets[]={']
for item in reports:
    m, t = item['files']['model.rx3'], item['files']['textures.rx3']
    header.append(' {"%s",%.4ff,%u,%u,"%s","%s"},' % (item['variant'], item['ball_center_y_cm'], m['size'], t['size'], m['sha256'], t['sha256']))
header.append('};')
(Path(__file__).parent / 'stand_assets.h').write_text('\n'.join(header) + '\n', encoding='utf8')
(args.output / 'validation.json').write_text(json.dumps(reports, indent=2), encoding='utf8')
print(json.dumps(reports, indent=2))
