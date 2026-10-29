"""Versioned presentation cache, independent of save data or SQL state.

PNG/JSON only, never pickle. A changed portrait, loose logo, archive, database,
theme or generator invalidates the cache. No club/coach career stats live here.
"""
from pathlib import Path
import hashlib,io,json,os,zipfile
from PIL import Image

_warm={}
def identity(path):
 try:
  s=path.stat();return [str(path),s.st_size,s.st_mtime_ns]
 except OSError:return [str(path),None]

def revision(game,model):
 import portable_paths
 game=Path(game);folder=game/'ModCarrerMode/data/manager_market';paths={folder/p['image'] for p in model['people']};paths.add(folder/'minifaces/NOTFOUND_DEFAULT.png')
 crests={r[4] for k in ('clubRows','hireRows','moveRows') for r in model[k]}|{r[1] for p in model['people'] for r in p.get('spellCards',[])}|{r[3] for p in model['people'] for r in p.get('titleCards',[])}
 for key in crests:
  for kind in ('light','dark'):paths.add(game/f'data/ui/imgAssets/crest/{kind}/l{key.split("_")[1]}.dds')
 leagues={l['id'] for l in model['leagues']}|{t['competition'] for p in model['people'] for t in p.get('career',{}).get('titles',[])}
 for ident in leagues:
  paths.add(game/f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png')
  for kind in ('light','dark'):paths.add(game/f'data/ui/imgAssets/league/{kind}/l{ident}.dds')
 for flag in {p.get('flag','flag_0') for p in model['people']}|{c['flag'] for c in model.get('countries',[])}:paths.add(game/f'data/ui/imgAssets/flags512x512/f_{flag[5:]}.dds')
 paths.update(game/p for p in portable_paths._priority)
 paths.update(game/p for p in ('data/db/fifa_ng_db.db','data/db/fifa_ng_db-meta.xml','ModCarrerMode/data/custom_ui_theme.json'))
 code=[hashlib.sha256(Path(__file__).with_name(p).read_bytes()).hexdigest() for p in ('manager_layout.py','profile_art.py','club_portraits.py','asset_cache.py')]
 current=[(r[4],r[5]) for r in model['clubRows']];formations=sorted({p.get('formation','') for p in model['people']})
 raw=json.dumps([2,code,[identity(p) for p in sorted(paths)],current,formations],sort_keys=True).encode()
 return hashlib.sha256(raw).hexdigest()

def prepared(game,model,factory):
 key=revision(game,model)
 if key in _warm:return dict(_warm[key])
 path=Path(game)/'ModCarrerMode/runtime/manager_market/artwork_cache'/('art_'+key+'.zip');assets=None
 try:
  with zipfile.ZipFile(path) as z:
   names=json.loads(z.read('index.json'));assets={}
   if len(names)>10000:raise ValueError('Excess artwork')
   for i,name in enumerate(names):
    entry=z.getinfo(str(i)+'.png')
    if entry.file_size>8*1024*1024:raise ValueError('Oversized artwork')
    with Image.open(io.BytesIO(z.read(entry))) as src:assets[name]=src.convert('RGBA')
 except (OSError,ValueError,KeyError,zipfile.BadZipFile,json.JSONDecodeError):assets=None
 if assets is None:
  assets=factory();path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix('.'+str(os.getpid())+'.new')
  with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_STORED) as z:
   z.writestr('index.json',json.dumps(list(assets)))
   for i,image in enumerate(assets.values()):
    data=io.BytesIO();image.save(data,format='PNG',compress_level=1);z.writestr(str(i)+'.png',data.getvalue())
  os.replace(temp,path)
 _warm.clear();_warm[key]=assets
 return dict(assets)
