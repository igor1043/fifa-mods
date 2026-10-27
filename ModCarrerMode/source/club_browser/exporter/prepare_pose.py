"""Compile an authored scene into a bounded, club-independent XI pose recipe."""
from pathlib import Path
import hashlib,json,math,struct,argparse

HERE=Path(__file__).resolve().parent
def floats(value,count,label,positive=False):
    if not isinstance(value,list) or len(value)!=count or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 or (positive and v<=0) for v in value):raise ValueError(label+' inválido')
    return value
def matrix(actor,scene_root=False):
    p=floats(actor.get('position'),3,'Posição');s=floats(actor.get('scale'),3,'Escala',True);q=floats(actor.get('quaternion'),4,'Rotação')
    n=math.sqrt(sum(v*v for v in q))
    if not .5<n<1.5:raise ValueError('Rotação degenerada')
    x,y,z,w=(v/n for v in q)
    r=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
    factor=100 if scene_root else 1
    return [r[row][column]*s[column]*factor if row<3 else 0 for column in range(3) for row in range(4)]+[v*factor for v in p]+[1]
def compile_pose(scene,reference):
    if scene.get('schema')!=2 or scene.get('type')!='fifa16-offline-scene':raise ValueError('Formato de cena inválido')
    actors=scene.get('actors');names=reference['names'];parents=reference['parents']
    if not isinstance(actors,list) or len(actors)!=11 or len({a.get('playerId') for a in actors})!=11:raise ValueError('São necessários onze jogadores distintos')
    if not 1<=len(names)<=1024 or len(parents)!=len(names):raise ValueError('Esqueleto de referência inválido')
    out=bytearray(struct.pack('<8sII',b'FFPOSE02',11,len(names)))
    for i,(name,parent) in enumerate(zip(names,parents)):
        raw=name.encode('utf8')
        if not 0<len(raw)<=128 or not -1<=parent<i:raise ValueError('Ordem do esqueleto inválida')
        out.extend(struct.pack('<I',len(raw))+raw+struct.pack('<i',parent))
    for actor in actors:
        info=reference['players'][str(actor['playerId'])];bones=actor.get('bones')
        if not isinstance(bones,list) or [b.get('name') for b in bones]!=names:raise ValueError('Esqueleto incompatível')
        out.extend(struct.pack('<If',info['height'],info['bind_scale']))
        out.extend(struct.pack('<16f',*matrix(actor,True)))
        for bone in bones:out.extend(struct.pack('<16f',*matrix(bone)))
    return bytes(out)
def read_reference(rigs):
    """Only rig metadata is retained; no model or texture is copied to the mod."""
    result={'schema':1,'players':{}}
    for path in sorted(Path(rigs).glob('player-*.ff3d')):
        with path.open('rb') as f:
            if f.read(8)!=b'FF3D0003':raise ValueError('Rig incompatível')
            _,_,count,player,height=struct.unpack('<5I',f.read(20))
            def text():
                n,=struct.unpack('<I',f.read(4))
                if not 0<n<=4096:raise ValueError('Nome inválido')
                return f.read(n).decode('utf8')
            text();names=[];parents=[];root_inverse=None
            for i in range(count):
                names.append(text());parents.append(struct.unpack('<i',f.read(4))[0]);m=struct.unpack('<16f',f.read(64))
                if i==0:root_inverse=m
            if result.get('names',names)!=names or result.get('parents',parents)!=parents:raise ValueError('Rigs diferentes')
            result.update(names=names,parents=parents)
            m=root_inverse;det=m[0]*(m[5]*m[10]-m[6]*m[9])-m[4]*(m[1]*m[10]-m[2]*m[9])+m[8]*(m[1]*m[6]-m[2]*m[5])
            result['players'][str(player)]={'height':height,'bind_scale':abs(det)**(-1/3)}
    if len(result['players'])<11:raise ValueError('Referências incompletas')
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('scene',type=Path);parser.add_argument('output',type=Path);parser.add_argument('--reference',type=Path,default=HERE/'pose_reference.json');parser.add_argument('--rigs',type=Path);args=parser.parse_args()
    if args.rigs:args.reference.write_text(json.dumps(read_reference(args.rigs),ensure_ascii=False,indent=2),encoding='utf8')
    raw=args.scene.read_bytes();scene=json.loads(raw.decode('utf-8-sig'));recipe=compile_pose(scene,json.loads(args.reference.read_text(encoding='utf8')))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(recipe)
    report={'schema':1,'source_sha256':hashlib.sha256(raw).hexdigest(),'recipe_sha256':hashlib.sha256(recipe).hexdigest(),'recipe_bytes':len(recipe),'players':11,'bones':len(scene['actors'][0]['bones']),'units':'centimeters','mapping':'photo slots; goalkeeper first, remaining actors by native height order','source_player_ids':[a['playerId'] for a in scene['actors']]}
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report))
if __name__=='__main__':main()
