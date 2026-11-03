"""Portable, save-free APT artwork. Verify source bytes before reusing it."""
from pathlib import Path
import hashlib,json,os,shutil
import asset_cache

def sources(game,model):
 import portable_paths
 game=Path(game);folder=game/'ModCarrerMode/data/manager_market';rows={}
 def digest(raw):return hashlib.sha256(raw).hexdigest()
 def local(key,path):
  try:rows[key]=digest(path.read_bytes())
  except OSError:rows[key]=None
 def native(key,paths):
  for path in paths:
   try:rows[key]=[path,digest(portable_paths.read_asset(path))];return
   except (OSError,ValueError):pass
  rows[key]=None
 for p in model['people']:
  path=folder/p['image'];local(p['head'],path if path.is_file() else folder/'minifaces/NOTFOUND_DEFAULT.png')
 local('head_NOTFOUND_DEFAULT',folder/'minifaces/NOTFOUND_DEFAULT.png')
 crests={r[4] for group in ('clubRows','moveRows','hireRows') for r in model[group]}|{r[1] for p in model['people'] for r in p.get('spellCards',[])}|{r[3] for p in model['people'] for r in p.get('titleCards',[])}
 for key in crests:
  ident=key.split('_')[1];native(key,[f'data/ui/imgAssets/crest/{kind}/l{ident}.dds' for kind in ('light','dark')])
 for ident in asset_cache.competition_ids(game,model):
  paths=[f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png']+[f'data/ui/imgAssets/league/{kind}/l{ident}.dds' for kind in ('light','dark')]
  native('competition_'+str(ident),paths)
 for key in asset_cache.flag_keys(game,model):
  if key not in ('flag_0','flag_uk'):native(key,[f'data/ui/imgAssets/flags512x512/f_{key[5:]}.dds'])
 local('theme',game/'ModCarrerMode/data/custom_ui_theme.json')
 return rows

def fingerprint(game,model,revision):
 path=Path(game)/'ModCarrerMode/runtime/manager_market/catalogue-sources.json'
 try:
  cached=json.loads(path.read_bytes())
  if cached.get('revision')==revision:return cached['fingerprint']
 except (OSError,ValueError,KeyError):pass
 value=hashlib.sha256(json.dumps(sources(game,model),sort_keys=True,separators=(',',':')).encode()).hexdigest()
 path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.'+str(os.getpid())+'.new')
 temporary.write_text(json.dumps(dict(revision=revision,fingerprint=value)),encoding='utf8');os.replace(temporary,path)
 return value

def template(game,model,geometry,revision):
 if model.get('ready') is False:return None
 root=Path(game)/'ModCarrerMode/data/manager_market/interface';path=root/'catalogue.big'
 try:
  recipe=json.loads((root/'recipe.json').read_bytes())
  if recipe.get('schema')!=1 or recipe.get('geometry')!=geometry:return None
  # A promoted/relegated club or another save can use a subset of the already
  # prepared art. Validate that complete installed pool, not the membership of
  # today's view, before rebuilding thousands of unchanged images.
  try:basis=artwork_basis(model,json.loads(path.with_suffix('.json').read_bytes()))
  except OSError:basis=None
  if basis is not None:
   if recipe.get('sources')==fingerprint(game,basis,asset_cache.revision(game,basis)):return path
  elif recipe.get('sources')==fingerprint(game,model,revision):return path
 except (OSError,ValueError,KeyError):pass
 return None

def artwork_basis(model,metadata):
 pool={n['asset'] for s in metadata['scenes'] for n in s['nodes'] if n['type']=='image'}
 heads={p['head']:p for p in model['people']}
 required=set(heads)|{r[4] for group in ('clubRows','moveRows','hireRows') for r in model[group]}
 required|={r[1] for p in model['people'] for r in p.get('spellCards',[])}|{r[3] for p in model['people'] for r in p.get('titleCards',[])}
 if not required<=pool:return None
 people=[dict(head=key,image=heads.get(key,{}).get('image','minifaces/'+key[5:]+'.png'),career=dict(titles=[]),flag='flag_0') for key in pool if key.startswith('head_')]
 leagues=[dict(id=l['id'],name=l['name'],country=l['country'],level=l['level'],image=l['image']) for l in model['leagues']]
 return dict(model,people=people,clubRows=[['','','','',key] for key in pool if key.startswith('crest_')],moveRows=[],hireRows=[],leagues=leagues)

def export(game,model,geometry,revision,built,destination):
 root=Path(destination);root.mkdir(parents=True,exist_ok=True)
 for suffix in ('.big','.json'):shutil.copy2(Path(built).with_suffix(suffix),root/('catalogue'+suffix))
 recipe=dict(schema=1,geometry=geometry,sources=fingerprint(game,model,revision),save_data=False)
 (root/'recipe.json').write_text(json.dumps(recipe,indent=2)+'\n',encoding='utf8')
 return recipe
