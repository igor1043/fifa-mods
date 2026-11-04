"""Vector lettering rendered as native FIFA prop meshes, not sampled letters."""
from pathlib import Path
from functools import lru_cache
import hashlib,json,re,unicodedata
import numpy as np
from room_visual_r68 import VERT,packed,join
from room_interior_r72 import write_groups

GLYPHS='ModCarrerMode/data/club_environment/current_dressing_room/generic/lettering.json'


@lru_cache(maxsize=2)
def load(path,modified):return json.loads(Path(path).read_text(encoding='utf8'))


def alphabet(game):
    p=Path(game)/GLYPHS
    return load(str(p),p.stat().st_mtime_ns) if p.is_file() else None


def definition(spec,index):
    lines=spec.get('lines') or ['CLUBE'];panels=spec.get('panels',[])
    panel=panels[index%len(panels)] if isinstance(panels,list) and panels else {}
    if not isinstance(panel,dict):panel={}
    return panel.get('mode','text'),str(panel.get('text',lines[index%len(lines)]))


def label(data,text,base,accent,club,center,width,normal,mode):
    text=unicodedata.normalize('NFC',text);glyphs=data['glyphs'];fallback=glyphs['?']
    chars=[glyphs.get(c,fallback) for c in text]
    units=sum(c['advance'] for c in chars)
    points=[p for c in chars for p in c['v']]
    if not points or units<=0:return {}
    low=min(p[1] for p in points);high=max(p[1] for p in points)
    scale=min(32/max(.1,high-low),width*(.56 if mode=='mixed' else .88)/units)
    pos=-units*scale/2;up=np.array([0.,1.,0.]);n=np.array(normal,dtype=float);right=np.cross(up,n)
    origin=np.array(center,dtype=float)+n*.9-up*((low+high)*scale/2)
    ink='#F5F5F2' if sum(int(base[i:i+2],16) for i in (1,3,5))<540 else '#181A1D'
    runs=re.split(r'(FLAMENGO|MENGÃO| DO )',text) if club==1043 and mode=='text' else [text]
    colors=[accent if club==1043 and run in ('FLAMENGO','MENGÃO',' DO ') else ink for run in runs for _ in run]
    groups={}
    for ch,glyph,color in zip(text,chars,colors):
        if glyph['i']:
            p=np.array(glyph['v']);v=np.zeros(len(p),dtype=VERT)
            v['p']=origin+right*(pos+p[:,0,None]*scale)+up*(p[:,1,None]*scale)
            v['n']=packed(n);v['g']=packed(right);v['uv']=(.5,.5)
            groups.setdefault(color,[]).append((v,np.array(glyph['i'],dtype='<u2')))
        pos+=glyph['advance']*scale
    return groups


def build(game,club,spec,bands,template,prefix):
    data=alphabet(game)
    if data is None:return None,[]
    groups={}
    for key,center,width,normal,index in bands:
        mode,text=definition(spec,index)
        if mode=='illustration':continue
        for color,parts in label(data,text,spec['base'],spec['accent'],club,center,width,normal,mode).items():groups.setdefault(color,[]).extend(parts)
    if not groups:return None,[]
    fingerprint=hashlib.sha256()
    for color,parts in groups.items():
        fingerprint.update(color.encode())
        for v,i in parts:fingerprint.update(v.tobytes());fingerprint.update(i.tobytes())
    relative=prefix+'lettering_'+fingerprint.hexdigest()[:14]+'.rx3';target=Path(game)/relative
    # Preserve one material per ink. Every letter samples a solid 8px color,
    # so the engine cannot replace the text with a blurry low-resolution mip.
    bindings=[{'material':color,'submesh':'room_part_'+str(i+1)} for i,color in enumerate(groups)]
    if not target.is_file():
        target.parent.mkdir(parents=True,exist_ok=True);write_groups(template,groups,target)
    return relative,bindings
