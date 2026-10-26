"""Export editor poses into the mod's static native RX3 format; game is read-only."""
from pathlib import Path
from functools import lru_cache
import hashlib, json, math, struct, sys, zipfile
import numpy as np
from rig_io import read_rig

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'export_engine'))
from native_assets import read_model, convert, STRIDE
from containers import big_entries, unpack

MANIFEST=json.loads((ROOT/'assets/scene.json').read_text(encoding='utf8'))
PLAYERS={p['id']:p for p in MANIFEST['variants'][0]['players']}
PRIORITY=('data_patch.big','data_front_end.big','data_graphic1_extra.big','data_graphic2_extra.big','data_graphic3_extra.big','data_graphic1.big','data_graphic2.big','data_graphic3.big','data_front_end_extra.big','data_default.big')

@lru_cache(maxsize=11)
def rig(player_id):
    if type(player_id) is not int or player_id not in PLAYERS:raise ValueError('Jogador fora da biblioteca.')
    return read_rig(ROOT/'assets'/f'player-{player_id}.ff3d')

def vector(value,n,label,limit=10000):
    if not isinstance(value,list) or len(value)!=n or any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>limit for x in value):raise ValueError(label+' inválido.')
    return np.array(value,dtype=float)

def trs(value,root=False):
    p=vector(value.get('position'),3,'Posição',1000 if root else 10000)
    q=vector(value.get('quaternion'),4,'Rotação',2);length=np.linalg.norm(q)
    if not .5<=length<=1.5:raise ValueError('Rotação degenerada.')
    x,y,z,w=q/length;s=vector(value.get('scale'),3,'Escala')
    if np.any(s<=0) or np.any(s>(10 if root else 100)):raise ValueError('Escala fora do limite.')
    matrix=np.eye(4)
    matrix[:3,:3]=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])*s[None,:]
    matrix[:3,3]=p;return matrix

def validate_scene(scene):
    if not isinstance(scene,dict) or scene.get('schema')!=2 or scene.get('type')!='fifa16-offline-scene':raise ValueError('Formato de cena incompatível.')
    actors=scene.get('actors')
    if not isinstance(actors,list) or not 1<=len(actors)<=48:raise ValueError('Exporte de 1 a 48 jogadores.')
    identities=set();parts=0
    for actor in actors:
        if not isinstance(actor,dict):raise ValueError('Jogador inválido.')
        identity=actor.get('id')
        if not isinstance(identity,str) or not identity or len(identity)>100 or identity in identities:raise ValueError('Identificador repetido ou inválido.')
        identities.add(identity);source=rig(actor.get('playerId'));trs(actor,True);bones=actor.get('bones')
        if not isinstance(bones,list) or len(bones)!=len(source['bones']):raise ValueError('Esqueleto incompatível.')
        for state,base in zip(bones,source['bones']):
            if not isinstance(state,dict) or state.get('name')!=base['name']:raise ValueError('Ordem dos ossos incompatível.')
            trs(state)
        parts+=len(source['parts'])
    if parts>512:raise ValueError('A cena ultrapassa as 512 partes do formato estático. Divida-a em cenas menores.')
    views=scene.get('views',[])
    if not isinstance(views,list) or len(views)>20:raise ValueError('Enquadramentos inválidos.')
    for camera in views+([scene['camera']] if scene.get('camera') else []):
        vector(camera.get('position'),3,'Câmera',1000);vector(camera.get('target'),3,'Alvo da câmera',1000)
    return actors

def actor_parts(actor):
    source=rig(actor['playerId']);world=[]
    for state,base in zip(actor['bones'],source['bones']):
        local=trs(state);world.append(local if base['parent']<0 else world[base['parent']]@local)
    delta=np.array(world)@np.array([b['inverse'] for b in source['bones']])
    normals=np.linalg.inv(delta[:,:3,:3]).transpose(0,2,1)
    root=trs(actor,True);root_normal=np.linalg.inv(root[:3,:3]).T
    result=[]
    for part in source['parts']:
        v=part['v'];weights=v['w'].astype(float)/v['w'].sum(axis=1)[:,None]
        p=np.c_[v['p'],np.ones(len(v))];posed=np.zeros((len(v),3));normal=np.zeros_like(posed)
        if part['skinned']:
            for i in range(8):
                joints=np.where(weights[:,i]>0,v['j'][:,i],0)
                posed+=(delta[joints,:3,:]@p[:,:,None])[:,:,0]*weights[:,i,None]
                normal+=(normals[joints]@v['n'][:,:,None])[:,:,0]*weights[:,i,None]
        else:posed=v['p'];normal=v['n']
        output=np.zeros(len(v),dtype=STRIDE)
        output['p']=(posed@root[:3,:3].T+root[:3,3])*100
        normal=normal@root_normal.T;normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-12)
        output['n']=normal;output['uv']=v['uv']
        if not np.isfinite(output.view('<f4')).all() or abs(output['p']).max()>10000:raise ValueError('Malha fora da área exportável de 100 metros.')
        result.append({**part,'v':output})
    return result,source['textures']

def write_model(scene,target,progress=lambda message:None):
    actors=validate_scene(scene);parts=[];textures=[];lookup={};texture_maps={}
    for i,actor in enumerate(actors):
        progress(f'Congelando pose · jogador {i+1} de {len(actors)}')
        rows,images=actor_parts(actor);mapping=texture_maps.get(actor['playerId'])
        if mapping is None:
            mapping=[]
            for image in images:
                key=hashlib.sha256(struct.pack('<3I',*image[:3])+image[3]).digest()
                if key not in lookup:lookup[key]=len(textures);textures.append(image)
                mapping.append(lookup[key])
            texture_maps[actor['playerId']]=mapping
        for p in rows:
            p['texture']=mapping[p['texture']] if p['texture']>=0 else -1
            p['coeff']=mapping[p['coeff']] if p['coeff']>=0 else -1
        parts.extend(rows)
    if len(textures)>256:raise ValueError('Muitas texturas para o formato estático.')
    with Path(target).open('wb') as handle:
        handle.write(b'FF3D0001'+struct.pack('<II',len(parts),len(textures)))
        for p in parts:
            handle.write(struct.pack('<IIii7f',len(p['v']),len(p['idx']),p['texture'],p['blend'],p['alpha'],*p['color'],*p['tint']))
            handle.write(p['v'].tobytes());handle.write(p['idx'].tobytes())
        for w,h,kind,data in textures:handle.write(struct.pack('<4I',w,h,kind,len(data))+data)
        handle.write(b'FFMAT001'+struct.pack('<I',len(parts)))
        for p in parts:handle.write(struct.pack('<Ii',int('/hair/' in p['asset'].lower()),p['coeff']))
    read_model(target)
    return len(parts),len(textures)

class GameTemplates:
    """Read two prop templates; never materialize or write into the installation."""
    def __init__(self,game):self.game=Path(game);self.tables={}
    def __call__(self,name):
        if name not in ('data/sceneassets/prop/prop_102.rx3','data/sceneassets/prop/prop_102_textures.rx3'):raise ValueError('Template não autorizado.')
        loose=self.game/Path(name)
        if loose.is_file():data=loose.read_bytes()
        else:
            data=None
            for archive in PRIORITY:
                path=self.game/archive
                if not path.is_file():continue
                if archive not in self.tables:self.tables[archive]={n.lower().replace('\\','/'):(o,s) for n,o,s in big_entries(path)}
                entry=self.tables[archive].get(name)
                if entry:
                    with path.open('rb') as handle:handle.seek(entry[0]);data=handle.read(entry[1])
                    break
            if data is None:raise FileNotFoundError('Template do FIFA não encontrado: '+name)
        return data if data[:3]==b'Rx3' or data[:3]==b'RX3' else unpack(data)

def export_package(scene,output,game,progress=lambda message:None):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    try:
        model=output/'scene.ff3d';parts,textures=write_model(scene,model,progress)
        progress('Preparando malhas RX3 e materiais originais…')
        native=output/'native';report=convert(model,native,GameTemplates(game),material_cache=ROOT/'exports/material-cache')
        (output/'scene.json').write_text(json.dumps(scene,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
        manifest={'schema':1,'type':'fifa-friends-static-scene','renderer':'FIFA native GameplayProp','geometry':'native/geometry.rx3','materials':'native/assets.json','editable':'scene.json','intermediate':'scene.ff3d','units':'centimeters','transforms':'baked into vertices','animation':False,'actors':[{'id':a['id'],'playerId':a['playerId']} for a in scene['actors']],'source_parts':parts,'source_textures':textures,'native_slots':report['slots'],'native_used_slots':report['used_slots'],'views':scene.get('views',[]),'camera':scene.get('camera')}
        (output/'scene-native.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
        (output/'LEIA-ME.txt').write_text('CENA ESTÁTICA — FIFA FRIENDS\n\nscene.json: cena editável, ossos locais, posições em metros e escalas do editor.\nscene.ff3d: geometria intermediária em centímetros com pose congelada.\nnative/: RX3 compatíveis com o carregador GameplayProp do mod dos 11.\nscene-native.json: manifesto, unidades e câmeras.\nnative/assets.json: associação entre os 96 slots xi_part_N e atlas_N.\n\nO pacote contém assets; não instala nem registra automaticamente uma cutscene.\nA ligação com a tela/partida e o ciclo de vida ficam no carregador nativo do mod.\nNão é um arquivo de animação EA nem uma linha do tempo. A pose fica estática no RX3.\nA cena editável conserva os 400 ossos de cada jogador para novas versões.\nSombras/luzes do editor são de inspeção; não são exportadas como iluminação do FIFA.\n\nNão substitua diretamente arquivos do jogo sem integrar o manifesto no carregador.\n',encoding='utf8')
        progress('Compactando o pacote da cena…')
        files=sorted(p for p in output.rglob('*') if p.is_file())
        archive=output/'cena-fifa.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as handle:
            for path in files:handle.write(path,path.relative_to(output).as_posix())
        return {'files':len(files),'archive':archive,'parts':parts,'textures':textures,'vertices':report['vertices']}
    except Exception:
        (output/'export-error.txt').write_text('Exportação incompleta. Nenhum arquivo foi instalado no FIFA.',encoding='utf8')
        raise
