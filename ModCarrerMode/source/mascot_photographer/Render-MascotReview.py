"""Render real exported RX3 skin in support and captured crowd poses."""
import argparse, json, sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

p=argparse.ArgumentParser()
p.add_argument('--model',required=True);p.add_argument('--texture',required=True)
p.add_argument('--tools',required=True);p.add_argument('--output',required=True)
p.add_argument('--frames',type=int,default=12)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
from rx3 import Rx3,read_model
root=Path(__file__).resolve().parent/'assets/animations'
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
parts,raw=read_model(Rx3(Path(a.model).read_bytes()));part=parts[0]
parents=[-1,0,1,2,3,4,5,2,7,8,9,2,11,12,13,14,13,16,17,18,19,13,21,22,23,24,9,5,0,28,0]
def matrix(raw):return Matrix([raw[i:i+4] for i in range(0,16,4)]).transposed()
bind=[matrix(m) for m in raw];inverse=[m.inverted() for m in bind]
ref=[matrix(m) for m in json.loads((root/'walk_baked.json').read_text())['referenceBind']]
verts=[Vector(part['positions'][i:i+3]) for i in range(0,len(part['positions']),3)]
floor=min(v.y for v in verts)
def pose(clip,fraction):
    frame=min(clip['frames'],key=lambda f:abs(f['time']-fraction*clip['duration']))
    src=[matrix(frame['matrices'][j*16:(j+1)*16]) for j in range(31)]
    delta=[src[j].to_quaternion()@ref[j].to_quaternion().inverted() for j in range(31)]
    posed=[]
    for j,parent in enumerate(parents):
        pos=bind[j].translation.copy() if parent<0 or j==2 else posed[parent].translation+delta[parent]@(bind[j].translation-bind[parent].translation)
        posed.append(Matrix.LocRotScale(pos,delta[j]@bind[j].to_quaternion(),Vector((1,1,1))))
    skin=[posed[j]@inverse[j] for j in range(31)];xyz=[]
    for i,v in enumerate(verts):
        result=Vector((0,0,0))
        for slot in range(4):
            k=i*4+slot;result+=(skin[part['joints'][k]]@v)*(part['weights'][k]/255)
        xyz.append(result)
    lift=floor-min(v.y for v in xyz)
    if 'liftCm' in clip:lift+=clip['liftCm'][clip['frames'].index(frame)]
    return [(v.x/100,-v.z/100,(v.y+lift)/100) for v in xyz]

bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.cycles.use_denoising=True
s.render.resolution_x=480;s.render.resolution_y=600;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True
s.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.08,.11,1)
s.world.node_tree.nodes['Background'].inputs[1].default_value=.8
s.view_settings.view_transform='Standard'
for loc,power in [((-3,-4,5),500),((3,-2,3),400)]:
    light=bpy.data.lights.new('Area','AREA');light.energy=power;light.size=4
    ob=bpy.data.objects.new('Area',light);s.collection.objects.link(ob);ob.location=loc
    ob.rotation_euler=(Vector((0,0,1.2))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));s.collection.objects.link(cam)
cam.data.type='ORTHO';s.camera=cam
mesh=bpy.data.meshes.new('Final RX3');ind=part['indices']
mesh.from_pydata([(v.x/100,-v.z/100,v.y/100) for v in verts],[],[ind[i:i+3] for i in range(0,len(ind),3)]);mesh.update()
ob=bpy.data.objects.new('Mascot',mesh);s.collection.objects.link(ob)
uv=mesh.uv_layers.new()
for loop in mesh.loops:
    i=loop.vertex_index;uv.data[loop.index].uv=(part['uvs'][i*2],1-part['uvs'][i*2+1])
for poly in mesh.polygons:poly.use_smooth=True
mat=bpy.data.materials.new('Final package diffuse');mat.use_nodes=True
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(a.texture)
shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Roughness'].default_value=.75
mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);mesh.materials.append(mat)
clips={name:json.loads((root/(name+'_baked.json')).read_text()) for name in ('idle','walk','cheer','goal_arms','goal_euphoric','goal_fists','goal_jump')}
def render(label,clip,fraction,detail=False):
    xyz=pose(clips[clip],fraction)
    for dest,v in zip(mesh.vertices,xyz):dest.co=v
    mesh.update()
    height=1.4 if detail else 1.10
    cam.location=(2.0 if detail else 0,-5,height)
    cam.rotation_euler=(Vector((0,0,height))-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=1.55 if detail else 2.65
    s.render.filepath=str(out/(label+'.png'));bpy.ops.render.render(write_still=True)
for name,clip,fraction,detail in [('idle','idle',.5,False),('walk','walk',.5,False),('support','cheer',.5,False),('goal_arms','goal_arms',.50,False),('head_arms','goal_arms',.50,True),('body_turn','goal_fists',.50,True),('goal_jump','goal_jump',.25,False)]:
    render(name,clip,fraction,detail)
s.render.resolution_x=320;s.render.resolution_y=400;s.cycles.samples=4
for i in range(a.frames):render(f'animation_{i:02d}','goal_euphoric',i/a.frames)
print('REVIEW RENDERED',out,flush=True)
