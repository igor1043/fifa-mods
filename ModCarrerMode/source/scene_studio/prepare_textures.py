from pathlib import Path
import sys,hashlib,json
from rig_io import read_rig
sys.path.insert(0,str(Path(__file__).resolve().parent/'export_engine'))
from native_assets import decode
root=Path(__file__).resolve().parent;folder=root/'assets/textures';folder.mkdir(exist_ok=True)
scene=json.loads((root/'assets/scene.json').read_text(encoding='utf8'));maps={}
for p in scene['variants'][0]['players']:
 rig=read_rig(root/'assets'/f'player-{p["id"]}.ff3d');images=[]
 for texture in rig['textures']:
  key=hashlib.sha256(str(texture[:3]).encode()+texture[3]).hexdigest()[:24]+'.png'
  target=folder/key
  if not target.exists():decode(texture).save(target)
  images.append('assets/textures/'+key)
 maps[str(p['id'])]=images
(root/'texture-map.json').write_text(json.dumps(maps),encoding='utf8');print('TEXTURES_READY',len(list(folder.glob('*.png'))))
