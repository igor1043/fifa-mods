"""Anchor the Corinthians jaw, beard and lower hair using RX3 skin bytes only."""
from pathlib import Path
import argparse, sys, struct, json, hashlib, io
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

parser = argparse.ArgumentParser()
parser.add_argument('--package', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--tools', required=True)
args = parser.parse_args()
package, output, tools = Path(args.package), Path(args.output), Path(args.tools)
output.mkdir(parents=True, exist_ok=True)
sys.path[:0] = [str(tools), str(tools / 'vendor/rx3tools')]
from rx3 import Rx3, read_model, FORMAT, VERTEX
from texture_assets import rx3_colour_png

raw = (package / 'model_animated.rx3').read_bytes()
rx = Rx3(raw)
parts, bind = read_model(rx)
part = parts[0]
xyz = np.asarray(part['positions']).reshape(-1, 3)
uv = np.asarray(part['uvs']).reshape(-1, 2)
js = np.asarray(part['joints']).reshape(-1, 4)
ws = np.asarray(part['weights']).reshape(-1, 4)
image = Image.open(io.BytesIO(rx3_colour_png(package / 'textures.rx3'))).convert('RGB')
colors = np.asarray(image)[np.clip((uv[:, 1] * (image.height - 1)).astype(int), 0, image.height - 1),
                           np.clip((uv[:, 0] * (image.width - 1)).astype(int), 0, image.width - 1)] / 255
neck, head = np.asarray(bind[13][12:15]), np.asarray(bind[14][12:15])
span = head[1] - neck[1]
oldhead = np.sum(ws * (js == 14), axis=1) / 255
oldneck = np.sum(ws * (js == 13), axis=1) / 255
region = ((xyz[:, 1] > neck[1] - .65 * span) & (xyz[:, 1] < head[1] + .5 * span)
          & (abs(xyz[:, 0] - head[0]) < 1.4 * span) & (xyz[:, 2] > head[2] - .5 * span))
skin = ((colors[:, 0] > colors[:, 1] + .07) & (colors[:, 1] > colors[:, 2] + .025)
        & (colors[:, 0] > .28))
seeds = np.flatnonzero(region & skin)
if len(seeds) < 100:
    raise ValueError('Face selection too small for the reviewed Corinthians model')
pairs = cKDTree(xyz[seeds]).query_pairs(2.5, output_type='ndarray')
graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(seeds), len(seeds)))
_, labels = connected_components(graph, directed=False)
face = seeds[labels == np.bincount(labels).argmax()]
near, _ = cKDTree(xyz[face]).query(xyz)
black = colors.max(axis=1) < .30
# Include the sides and underside of the chin, rather than only its front surface.
jaw = region & (skin | black) & (near < 5) & (xyz[:, 1] > xyz[face, 1].min() - 3)
# Include the lateral jaw and hair even when the authored head weight is zero.
# Shoulder weights on these vertices were the source of the remaining stretching.
# The cape lies behind this bounded head shell and retains its torso weights.
hair = (black & (abs(xyz[:, 0] - head[0]) < 1.4 * span)
        & (xyz[:, 1] > neck[1] - .3 * span) & (xyz[:, 1] < head[1] + .2 * span)
        & (xyz[:, 2] > head[2] - 1.45 * span) & (xyz[:, 2] < head[2] + .25 * span)
        & (((xyz[:, 0]-head[0])/(1.4*span))**2 + ((xyz[:, 2]-head[2])/(1.5*span))**2 < 1))
core = jaw | hair
distance, _ = cKDTree(xyz[core]).query(xyz)
transition = (region & ~core & (distance < 2) & (oldhead > .3)
              & (oldhead + oldneck > .9) & (xyz[:, 1] > neck[1]))
newjs, newws = js.copy(), ws.copy()
changed = []
for i in np.flatnonzero(core | transition):
    h = 1.0 if core[i] else max(oldhead[i], .9 * (1 - distance[i] / 2))
    if h <= oldhead[i] + 1e-5:
        continue
    amount = round(h * 255)
    newjs[i], newws[i] = [14, 13, 0, 0], [amount, 255 - amount, 0, 0]
    if not np.array_equal(newjs[i], js[i]) or not np.array_equal(newws[i], ws[i]):
        changed.append(int(i))
if not 20 <= len(changed) <= 700:
    raise ValueError('Unexpected size of head weight adjustment')
fields = {}
for token in rx.get(FORMAT)[0][16:].split(b'\0')[0].decode().split():
    semantic, offset, _, _, fmt = token.split(':')
    fields[semantic] = (int(offset, 16), fmt)
assert fields['i0'][1] == '4u8' and fields['w0'][1] == '4u8n'
entries = [struct.unpack_from('<4I', raw, 16 + 16 * i) for i in range(struct.unpack_from('<I', raw, 12)[0])]
vb = next(entry for entry in entries if entry[0] == VERTEX)
stride = struct.unpack_from('<I', raw, vb[1] + 8)[0]
result, allowed = bytearray(raw), set()
for i in changed:
    for semantic, values in [('i0', newjs[i]), ('w0', newws[i])]:
        start = vb[1] + 16 + i * stride + fields[semantic][0]
        result[start:start + 4] = bytes(values.tolist())
        allowed.update(range(start, start + 4))
assert len(result) == len(raw) and all(a == b or i in allowed for i, (a, b) in enumerate(zip(raw, result)))
assert {int(j) for j, w in zip(newjs.flat, newws.flat) if w} == {int(j) for j, w in zip(js.flat, ws.flat) if w}
checked, checked_bind = read_model(Rx3(result))
for key in ['positions', 'normals', 'tangents', 'uvs', 'indices']:
    if key in part:
        assert checked[0][key] == part[key], key
assert checked_bind == bind and np.all(newws.sum(axis=1) == 255)
assert np.all(np.sum(newws * (newjs == 14), axis=1)[core] == 255)
assert np.all(xyz[changed, 1] > neck[1] - .65 * span)
for name in ['model.rx3', 'model_animated.rx3']:
    (output / name).write_bytes(result)
report = {'club': 1041, 'changedVertices': len(changed), 'rigidJawVertices': int(jaw.sum()),
          'rigidLowerHairVertices': int(hair.sum()), 'changedIndices': changed,
          'geometryUvBindPreserved': True, 'weightsNormalized': True,
          'method': 'complete lower face and lateral jaw, removing neck/shoulder influence; bounded lower hair shell including zero-head vertices; skin bytes only',
          'sha256': hashlib.sha256(result).hexdigest()}
(output / 'head_weights_report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps({k: v for k, v in report.items() if k != 'changedIndices'}))
