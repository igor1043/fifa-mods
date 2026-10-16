"""Blender QA: render decoded RX3 supports and their calculated ball contacts."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--meshes',type=Path,required=True)
parser.add_argument('--assets',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
reports=json.loads((args.assets/'validation.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1800;scene.render.resolution_y=750;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.4,.45,.5,1)
for k,report in enumerate(reports):
    slug=report['variant'];part=json.loads((args.meshes/(slug+'_decoded.json')).read_text())
    p=part['positions'];ids=part['indices'];x=(k-2)*.52
    mesh=bpy.data.meshes.new(slug)
    mesh.from_pydata([(p[i]/100+x,-p[i+2]/100,p[i+1]/100) for i in range(0,len(p),3)],[],[ids[i:i+3] for i in range(0,len(ids),3)])
    mesh.update();uv=mesh.uv_layers.new(name='UVMap')
    for loop in mesh.loops:uv.data[loop.index].uv=(part['uvs'][2*loop.vertex_index],1-part['uvs'][2*loop.vertex_index+1])
    n=part['normals'];mesh.normals_split_custom_set_from_vertices([(n[i],-n[i+2],n[i+1]) for i in range(0,len(n),3)])
    obj=bpy.data.objects.new(slug,mesh);scene.collection.objects.link(obj)
    mat=bpy.data.materials.new(slug);mat.use_nodes=True
    bs=mat.node_tree.nodes['Principled BSDF'];bs.inputs['Roughness'].default_value=.62
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(args.meshes/(slug+'_colour.png')))
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);mesh.materials.append(mat)
    for face in mesh.polygons:face.use_smooth=True
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=.111252,location=(x,0,report['ball_center_y_cm']/100))
    ball=bpy.context.object;ball.name='Ball contact '+slug
    ballmat=bpy.data.materials.get('White ball') or bpy.data.materials.new('White ball')
    ballmat.diffuse_color=(.9,.92,.94,1);ball.data.materials.append(ballmat)
    for face in ball.data.polygons:face.use_smooth=True
    bpy.ops.object.text_add(location=(x-.15,-.26,.002),rotation=(1.570796327,0,0))
    label=bpy.context.object;label.data.body=slug.upper();label.data.size=.035
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.002))
mat=bpy.data.materials.new('Grass');mat.diffuse_color=(.025,.1,.025,1);bpy.context.object.data.materials.append(mat)
bpy.ops.object.light_add(type='AREA',location=(-1,-2,3));bpy.context.object.data.energy=450;bpy.context.object.data.size=4
bpy.ops.object.light_add(type='AREA',location=(2,1,2));bpy.context.object.data.energy=250;bpy.context.object.data.size=3
bpy.ops.object.camera_add(location=(0,-3.8,1.55));camera=bpy.context.object;scene.camera=camera
camera.rotation_euler=(Vector((0,0,.18))-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO';camera.data.ortho_scale=2.7
scene.view_settings.view_transform='Standard'
scene.render.filepath=str(args.output);bpy.ops.render.render(write_still=True)
