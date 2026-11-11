"""Build shared native room assets and an honest preview using installed FIFA cups."""
from pathlib import Path
import argparse,copy,json,os,shutil,sys
import numpy as np
from PIL import Image
if __package__ is None:
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]));__package__='trophy_room'
from . import geometry,assets


def prepare(game,output):
    game=Path(game);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    seeds=game/'ModCarrerMode/data/trophy_room';seeds.mkdir(parents=True,exist_ok=True)
    for source,name in [(game/'data/sceneassets/server16_dressing_room_v3/scenery.rx3','prop-template.rx3'),
                        (game/'ModCarrerMode/runtime/club_environment/room/assets/texture_template.rx3','texture-template.rx3')]:
        if not (seeds/name).is_file():shutil.copy2(source,seeds/name)
    identity,_=assets.club_identity(game,1043);custom=seeds/'custom/1043';custom.mkdir(parents=True,exist_ok=True)
    if not (custom/'identity-wall.png').is_file():assets.flamengo_wall(game).save(custom/'identity-wall.png')
    doc=geometry.build();doc['materials']=geometry.MATERIALS;doc['images']={}
    wall=output/'identity.png';assets.identity_image(game,identity,True).save(wall);doc['images']['identity']=str(wall)
    door=output/'door.png';assets.surface_image(game,'door').save(door);doc['images']['door']=str(door)
    leather=output/'leather.png';assets.surface_image(game,'leather').save(leather);doc['images']['leather']=str(leather)
    exit=output/'exit.png';im=Image.new('RGBA',(512,128),'#284b3d');assets.center(__import__('PIL.ImageDraw',fromlist=['Draw']).Draw(im),(256,64),'SAÍDA',65,'#ffffff',True);im.save(exit);doc['images']['exit']=str(exit)
    labels={}
    names=game/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json'
    if names.is_file():labels=json.loads(names.read_text(encoding='utf8')).get('names',{})
    # Preview specimens show the original native cups, never career evidence.
    doc['preview_cups']=[]
    available=[i for i in (1003,7,229,9,23,1009) if (game/f'data/sceneassets/trophy/trophy_{i}.rx3').is_file()]
    samples=[]
    for i,slot in enumerate(doc['slots']):
        ident=available[i%len(available)];cup=assets.native_cup(game,ident)
        sample=dict(competition=ident,root=ident,date=20260101,year=2026,name=labels.get(f'TrophyName_{ident}',f'Taça {ident}'))
        samples.append(sample);plaque=output/f'plaque-{i}.png';assets.plaque(game,sample,i).save(plaque);doc['images'][f'plaque_{i}']=str(plaque)
        rx=assets.Rx3((game/cup['texture']).read_bytes());image=output/f'cup-{ident}.png'
        if not image.is_file():assets.decode_texture(rx,cup['diffuse']).save(image)
        parts,_=assets.read_model(assets.Rx3((game/cup['model']).read_bytes()))
        converted=[];c,s=np.cos(slot['yaw']),np.sin(slot['yaw'])
        for part in parts:
            p=(np.asarray(part['positions']).reshape(-1,3)+cup['offset'])*cup['scale']
            p=np.stack((p[:,0]*c+p[:,2]*s,p[:,1],-p[:,0]*s+p[:,2]*c),axis=1)+[slot['x'],slot['y'],slot['z']]
            converted.append(dict(name=part['name'],positions=p.tolist(),indices=part['indices'],uvs=np.asarray(part['uvs']).reshape(-1,2).tolist()))
        doc['preview_cups'].append(dict(material=f'cup_{ident}',image=str(image),parts=converted))
    assets.atomic(output/'scene.json',json.dumps(doc,ensure_ascii=False).encode('utf8'))
    return output/'scene.json'


def finish_legacy_preview(game,output):
    game=Path(game);output=Path(output);destination=game/assets.PREFIX;destination.mkdir(parents=True,exist_ok=True)
    seeds=game/'ModCarrerMode/data/trophy_room';doc=geometry.build()
    baked=json.loads((output/'baked-mesh.json').read_text());assets.mesh_file([baked],seeds/'prop-template.rx3',destination/'gallery.rx3')
    bindings=[dict(key='gallery',model=assets.PREFIX+'gallery.rx3',texture=assets.PREFIX+'room-lighting.rx3',submesh='gallery_part_1',diffuse='gallery_cm',metal=False,alpha=False)]
    assets.rx_texture(Image.open(output/'room-lighting.png'),seeds/'texture-template.rx3','gallery_cm',destination/'room-lighting.rx3')
    groups={}
    for part in doc['parts']:
        key=part['material']
        if key in ('identity','exit','primary','secondary','glass','chrome','emission') or key.startswith('plaque_'):groups.setdefault(key,[]).append(part)
    separate=[]
    for key,parts in groups.items():
        positions=[];uvs=[];indices=[]
        for p in parts:
            offset=len(positions);positions+=p['positions'];uvs+=p['uvs'];indices += [i+offset for i in p['indices']]
        separate.append(dict(positions=positions,uvs=uvs,indices=indices))
        bindings.append(dict(key=key,model=assets.PREFIX+'gallery-details.rx3',submesh=f'gallery_part_{len(separate)}',alpha=key=='glass',metal=key=='chrome',diffuse='gallery_cm'))
    assets.mesh_file(separate,seeds/'prop-template.rx3',destination/'gallery-details.rx3')
    # Native normal/specular companion maps, with materials kept separate.
    for key,pixels in [('normal',(128,128,255,255)),('matte',(16,16,16,80)),('metal',(210,210,210,245)),('white',(255,255,255,255))]:
        assets.rx_texture(Image.new('RGBA',(4,4),pixels),seeds/'texture-template.rx3',{'normal':'gallery_nm','white':'gallery_cm'}.get(key,'gallery_coeff'),destination/(key+'.rx3'))
    assets.atomic(destination/'layout.json',json.dumps(dict(revision=geometry.REVISION,bindings=bindings,slots=doc['slots'],obstacles=doc['obstacles'],cameras=doc['cameras'],capacity=doc['capacity']),ensure_ascii=False,indent=2).encode('utf8'))
    shutil.copy2(output/'room-lighting.png',destination/'room-lighting.png')
    return destination


def clean_surfaces(game,output):
    """Unlit base colours plus native indoor lighting, as in the dressing room.

    Each architectural material is a separate mesh. No baked light, AO, noise
    or shadow image is multiplied into the wall/floor/cabinet albedo.
    """
    game,out=Path(game),Path(output);out.mkdir(parents=True,exist_ok=True)
    seeds=game/'ModCarrerMode/data/trophy_room';doc=geometry.build();groups={}
    for part in doc['parts']:groups.setdefault(part['material'],[]).append(part)
    parts=[];bindings=[];dynamic={'identity','exit','primary','secondary','glass','chrome','emission'}
    model=f'gallery-clean-r{geometry.REVISION}.rx3'
    for material,items in groups.items():
        positions=[];normals=[];uvs=[];indices=[]
        for p in items:
            offset=len(positions);positions+=p['positions'];uvs+=p['uvs'];indices += [offset+i for i in p['indices']]
        parts.append(dict(positions=positions,uvs=uvs,indices=indices))
        lo=np.min(positions,axis=0);hi=np.max(positions,axis=0)
        key=material if material in dynamic or material.startswith('plaque_') else 'surface_'+material
        binding=dict(key=key,model=assets.PREFIX+model,submesh=f'gallery_part_{len(parts)}',
                     alpha=material=='glass',metal=material=='chrome',diffuse='gallery_cm',lighting_point=((lo+hi)*.5).tolist(),
                     baked=material in ('identity','exit','emission') or material.startswith('plaque_'))
        if key.startswith('surface_'):
            texture=f'{key}-r{geometry.REVISION}.rx3'
            assets.rx_texture(assets.surface_image(game,material),seeds/'texture-template.rx3','gallery_cm',out/texture)
            binding['texture']=assets.PREFIX+texture
        bindings.append(binding)
    assets.mesh_file(parts,seeds/'prop-template.rx3',out/model)
    assets.atomic(out/'layout.json',json.dumps(dict(revision=geometry.REVISION,bindings=bindings,slots=doc['slots'],obstacles=doc['obstacles'],
        cameras=doc['cameras'],capacity=doc['capacity'],lighting='native indoor SH and ceiling spots; clean unlit albedo'),indent=2).encode('utf8'))
    return out


def finish(game,output):
    game,output=Path(game),Path(output)
    prepared=clean_surfaces(game,output/'native-clean');destination=game/assets.PREFIX;destination.mkdir(parents=True,exist_ok=True)
    for path in prepared.iterdir():shutil.copy2(path,destination/path.name)
    seeds=game/'ModCarrerMode/data/trophy_room'
    for key,pixels in [('normal',(128,128,255,255)),('matte',(16,16,16,80)),('metal',(210,210,210,245)),('white',(255,255,255,255))]:
        assets.rx_texture(Image.new('RGBA',(4,4),pixels),seeds/'texture-template.rx3',{'normal':'gallery_nm','white':'gallery_cm'}.get(key,'gallery_coeff'),destination/(key+'.rx3'))
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--finish',action='store_true');a=p.parse_args()
    print(finish(a.game,a.output) if a.finish else prepare(a.game,a.output))
