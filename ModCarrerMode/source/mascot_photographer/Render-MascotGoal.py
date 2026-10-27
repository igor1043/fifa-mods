"""Blender preview of the final RX3 skin retargeted with the native goal capture."""
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

parser = argparse.ArgumentParser()
parser.add_argument('--model', required=True)
parser.add_argument('--texture', required=True)
parser.add_argument('--tools', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--clip', default='goal_euphoric_baked.json')
parser.add_argument('--frames', type=int, default=28)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
sys.path.insert(0, str(Path(args.tools) / 'vendor/rx3tools'))
from rx3 import Rx3, read_model

root = Path(__file__).resolve().parent
out = Path(args.output)
out.mkdir(parents=True, exist_ok=True)
part, raw_bind = read_model(Rx3(Path(args.model).read_bytes()))
part = part[0]
clip = json.loads((root / 'assets/animations' / args.clip).read_text())
reference = json.loads((root / 'assets/animations/walk_baked.json').read_text())['referenceBind']
parents = [-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]

def matrix(raw):
    return Matrix([raw[i:i+4] for i in range(0,16,4)]).transposed()

bind = [matrix(m) for m in raw_bind]
ref = [matrix(m) for m in reference]
inv = [m.inverted() for m in bind]
vertices = [Vector(part['positions'][i:i+3]) for i in range(0,len(part['positions']),3)]
indices = part['indices']
floor = min(v.y for v in vertices)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 4
scene.cycles.use_denoising = True
scene.render.resolution_x = 320
scene.render.resolution_y = 400
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.09,.10,.13,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .8
scene.view_settings.view_transform = 'Standard'
for loc, power in [((-3,-4,5),500),((3,-2,3),400)]:
    light = bpy.data.lights.new('Area', 'AREA')
    light.energy = power
    light.size = 4
    ob = bpy.data.objects.new('Area',light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0,0,1.2))-ob.location).to_track_quat('-Z','Y').to_euler()
camdata = bpy.data.cameras.new('Camera')
cam = bpy.data.objects.new('Camera',camdata)
scene.collection.objects.link(cam)
camdata.type = 'ORTHO'
camdata.ortho_scale = 2.75
scene.camera = cam
cam.location = (0,-5,1.10)
cam.rotation_euler = (Vector((0,0,1.10))-cam.location).to_track_quat('-Z','Y').to_euler()
mesh = bpy.data.meshes.new('Final RX3')
mesh.from_pydata([(v.x/100,-v.z/100,v.y/100) for v in vertices],[],[indices[i:i+3] for i in range(0,len(indices),3)])
mesh.update()
ob = bpy.data.objects.new('Mascot',mesh)
scene.collection.objects.link(ob)
uv = mesh.uv_layers.new()
for loop in mesh.loops:
    i = loop.vertex_index
    uv.data[loop.index].uv = (part['uvs'][i*2],1-part['uvs'][i*2+1])
for poly in mesh.polygons:
    poly.use_smooth = True
material = bpy.data.materials.new('Package diffuse')
material.use_nodes = True
node = material.node_tree.nodes.new('ShaderNodeTexImage')
node.image = bpy.data.images.load(args.texture)
bs = material.node_tree.nodes.get('Principled BSDF')
bs.inputs['Roughness'].default_value = .75
material.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
mesh.materials.append(material)
for index in range(args.frames):
    t = index * clip['duration'] / args.frames
    frame = min(clip['frames'],key=lambda f:abs(f['time']-t))
    src = [matrix(frame['matrices'][j*16:(j+1)*16]) for j in range(31)]
    delta = [src[j].to_quaternion() @ ref[j].to_quaternion().inverted() for j in range(31)]
    pose = []
    for j,parent in enumerate(parents):
        pos = bind[j].translation.copy() if parent < 0 or j == 2 else pose[parent].translation + delta[parent] @ (bind[j].translation-bind[parent].translation)
        pose.append(Matrix.LocRotScale(pos,delta[j] @ bind[j].to_quaternion(),Vector((1,1,1))))
    sk = [pose[j] @ inv[j] for j in range(31)]
    xyz = []
    for i, vertex in enumerate(vertices):
        v = Vector((0,0,0))
        for slot in range(4):
            k = i*4+slot
            v += (sk[part['joints'][k]] @ vertex) * (part['weights'][k]/255)
        xyz.append(v)
    lift = floor-min(v.y for v in xyz)
    if 'liftCm' in clip:
        frameIndex = clip['frames'].index(frame)
        lift += clip['liftCm'][frameIndex]
    for dest,v in zip(mesh.vertices,xyz):
        dest.co = (v.x/100,-v.z/100,(v.y+lift)/100)
    mesh.update()
    scene.render.filepath = str(out/f'goal_{index:02d}.png')
    bpy.ops.render.render(write_still=True)
print('Rendered final mascot goal reaction',flush=True)
