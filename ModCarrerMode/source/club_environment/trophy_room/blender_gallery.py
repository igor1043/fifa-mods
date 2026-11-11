"""Bake fixed gallery lighting and render the actual exported gallery geometry.

Run with Blender --background --python ... -- --scene scene.json --output folder.
Trophies in preview come directly from installed FIFA RX3 meshes.
"""
import argparse,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--scene',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--preview-only',action='store_true');args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    doc=json.loads(args.scene.read_text(encoding='utf8'));out=args.output;out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
    scene.cycles.max_bounces=4;scene.cycles.diffuse_bounces=2
    # Prefer the installed GPU, while retaining a CPU path on other machines.
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        if any(d.type=='OPTIX' for d in prefs.devices):
            for device in prefs.devices:device.use=device.type=='OPTIX'
            scene.cycles.device='GPU'
    except (RuntimeError,TypeError):pass
    scene.cycles.use_denoising=True;scene.world.color=(.20,.20,.20)
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.image_settings.file_format='PNG';scene.render.resolution_x=1440;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.film_transparent=False
    scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.47,.52,.57,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.12
    def rgb(hex):return tuple((int(hex[i:i+2],16)/255)**2.2 for i in (1,3,5))
    mats={}
    for key,values in doc['materials'].items():
        color,rough,metal=values;m=bpy.data.materials.new(key);m.use_nodes=True
        bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*rgb(color),1)
        bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
        if key=='glass':
            bs.inputs['Transmission Weight'].default_value=1;bs.inputs['IOR'].default_value=1.45;bs.inputs['Alpha'].default_value=1
            bs.inputs['Roughness'].default_value=.012
        if key=='emission':
            bs.inputs['Emission Color'].default_value=(1,.92,.72,1);bs.inputs['Emission Strength'].default_value=3
        if key=='stone':
            noise=m.node_tree.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=36;noise.inputs['Detail'].default_value=2
            bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.013
            m.node_tree.links.new(noise.outputs['Fac'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
        mats[key]=m
    def image_mat(key,path,metal=0):
        m=bpy.data.materials.new(key);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF')
        tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
        m.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);bs.inputs['Roughness'].default_value=.24 if metal else .65
        bs.inputs['Metallic'].default_value=metal;mats[key]=m
    for key,path in doc.get('images',{}).items():image_mat(key,path)
    def point(p):return (p[0]/100,-p[2]/100,p[1]/100)
    static=[];objects=[]
    excluded={'identity','exit','primary','secondary','glass','chrome','emission'}
    for part in doc['parts']:
        mesh=bpy.data.meshes.new(part['name']);indices=part['indices'];faces=[indices[i:i+3] for i in range(0,len(indices),3)]
        mesh.from_pydata([point(p) for p in part['positions']],[],faces);mesh.update()
        ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);objects.append(ob)
        material=part['material'];mesh.materials.append(mats.get(material,mats['wall']))
        layer=mesh.uv_layers.new(name='UVMap')
        for polygon in mesh.polygons:
            for li in polygon.loop_indices:
                uv=part['uvs'][mesh.loops[li].vertex_index];layer.data[li].uv=(uv[0],1-uv[1])
        if material=='glass':ob.visible_shadow=False
        if material not in excluded and not material.startswith('plaque_'):static.append(ob)
        if material not in ('glass','identity') and not material.startswith('plaque_'):
            bevel=ob.modifiers.new('Fine cabinet edges','BEVEL');bevel.width=.006;bevel.segments=2
    # Ceiling sources illuminate the cabinets, not the outdoor stadium.
    for x in (-doc['dimensions'][0]/2+180,doc['dimensions'][0]/2-180):
        for z in (-580,-290,0,290,580):
            lamp=bpy.data.lights.new('Gallery ceiling spot','AREA');lamp.energy=165;lamp.shape='RECTANGLE';lamp.size=1.25;lamp.size_y=.45
            lamp.color=(1,.95,.88)
            ob=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(ob);ob.location=point((x,306,z))
    for z in (-480,300):
        lamp=bpy.data.lights.new('Gallery diffuse fill','AREA');lamp.energy=110;lamp.shape='DISK';lamp.size=3
        ob=bpy.data.objects.new(lamp.name,lamp);scene.collection.objects.link(ob);ob.location=point((0,320,z))
    if not args.preview_only:
        # Bake actual geometry occlusion into one reusable room texture. Club
        # logos, editable wall PNGs, plaques and metallic cups remain separate.
        bpy.ops.object.select_all(action='DESELECT')
        for ob in static:ob.select_set(True)
        bpy.context.view_layer.objects.active=static[0];bpy.ops.object.join();ob=bpy.context.object
        for modifier in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(67),island_margin=.006);bpy.ops.object.mode_set(mode='OBJECT')
        image=bpy.data.images.new('Gallery baked illumination',2048,2048,alpha=False)
        for material in ob.data.materials:
            nodes=material.node_tree.nodes;node=nodes.new('ShaderNodeTexImage');node.image=image;nodes.active=node
        scene.cycles.bake_type='COMBINED';scene.render.bake.use_pass_glossy=False;scene.render.bake.use_pass_transmission=False;scene.render.bake.margin=12
        bpy.ops.object.bake(type='COMBINED');image.filepath_raw=str(out/'room-lighting.png');image.file_format='PNG';image.save()
        mesh=ob.data;mesh.calc_loop_triangles();uv=mesh.uv_layers.active.data;positions=[];normals=[];uvs=[];indices=[]
        for tri in mesh.loop_triangles:
            for li in tri.loops:
                p=mesh.vertices[mesh.loops[li].vertex_index].co;n=mesh.loops[li].normal
                positions.append([p.x*100,p.z*100,-p.y*100]);normals.append([n.x,n.z,-n.y]);uvs.append([uv[li].uv.x,1-uv[li].uv.y]);indices.append(len(indices))
        (out/'baked-mesh.json').write_text(json.dumps(dict(positions=positions,normals=normals,uvs=uvs,indices=indices)),encoding='utf8')
        # Use the original material graph for the preview render.
    for trophy in doc.get('preview_cups',[]):
        image_mat(trophy['material'],trophy['image'],.78)
        for part in trophy['parts']:
            mesh=bpy.data.meshes.new(part['name']);ids=part['indices'];mesh.from_pydata([point(p) for p in part['positions']],[],[ids[i:i+3] for i in range(0,len(ids),3)]);mesh.update()
            ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);mesh.materials.append(mats[trophy['material']]);uv=mesh.uv_layers.new()
            for poly in mesh.polygons:
                poly.use_smooth=True
                for li in poly.loop_indices:
                    tex=part['uvs'][mesh.loops[li].vertex_index];uv.data[li].uv=(tex[0],1-tex[1])
    camera_data=bpy.data.cameras.new('Preview');camera=bpy.data.objects.new('Preview',camera_data);scene.collection.objects.link(camera);scene.camera=camera
    for i,pose in enumerate(doc['cameras'][:3]):
        camera.location=point(pose['eye']);target=Vector(point(pose['target']));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
        camera_data.angle=math.radians(pose['fov']);camera_data.clip_start=.02;camera_data.clip_end=100
        scene.render.filepath=str(out/f'gallery-preview-{i+1}.png');bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'trophy-gallery.blend'))


if __name__=='__main__':main()
