"""Load only the selected CV's artwork, never the complete club catalogue."""
from pathlib import Path
from collections import OrderedDict
import io,json,zipfile
from PIL import Image,ImageDraw
from profile_layout import TITLE_TOP,TITLE_STEP

_indexes=OrderedDict()

def describe(person,revision=''):
 overview=person.get('overview',[]);current=overview[16] if len(overview)>16 else ''
 crests={r[1] for r in person.get('spellCards',[]) if len(r)>1}|{r[3] for r in person.get('titleCards',[]) if len(r)>3}
 if current:crests.add(current)
 return dict(head=person.get('head','head_NOTFOUND_DEFAULT'),image=person.get('image','minifaces/NOTFOUND_DEFAULT.png'),flag=person.get('flag','flag_0'),
             current=current,crests=sorted(crests),competitions=sorted({r[1] for r in person.get('titleCards',[]) if len(r)>1}),revision=revision)

def subset(game,keys,revision):
 if not revision:return {}
 path=Path(game)/'ModCarrerMode/runtime/manager_market/artwork_cache'/('art_'+revision+'.zip')
 try:
  stamp=(str(path),path.stat().st_mtime_ns,path.stat().st_size)
  with zipfile.ZipFile(path) as z:
   if stamp not in _indexes:
    names=json.loads(z.read('index.json'))
    if len(names)>10000:raise ValueError('Catálogo de imagens excessivo')
    _indexes[stamp]={name:str(i)+'.png' for i,name in enumerate(names)}
    while len(_indexes)>2:_indexes.popitem(last=False)
   index=_indexes[stamp];result={}
   for key in keys:
    entry=index.get(key)
    if entry is None:continue
    if z.getinfo(entry).file_size>8*1024*1024:raise ValueError('Imagem excessiva')
    with Image.open(io.BytesIO(z.read(entry))) as image:result[key]=image.convert('RGBA')
   return result
 except (OSError,ValueError,KeyError,zipfile.BadZipFile):return {}

def prepare(game,media):
 from layout import Scene
 from club_portraits import portrait
 from manager_layout import fit_image
 import portable_paths
 keys={media['head'],media['flag'],*media['crests'],*media['competitions']}
 keys.update('cup_'+key.split('_',1)[1] for key in media['competitions'])
 assets=subset(game,keys,media.get('revision',''));scene=Scene('profileArtwork','')
 def image(key,name,x,y,w,h):
  if key in assets:scene.image(key,x,y,w,h);scene.nodes[-1]['name']=name
 shield=Image.new('RGBA',(128,128));ImageDraw.Draw(shield).polygon([(28,18),(100,18),(95,83),(64,112),(33,83)],fill='#b8c6cf')
 generic=Image.new('RGBA',(64,40),'#dbe3e9')
 def read(key,paths,size,fallback=None):
  if key in assets:return
  for path in paths:
   try:
    with Image.open(io.BytesIO(portable_paths.read_asset(path))) as src:assets[key]=fit_image(src,size)
    return
   except (OSError,ValueError):pass
  if fallback is not None:assets[key]=fallback.copy()
 if media['head'] not in assets:
  folder=Path(game)/'ModCarrerMode/data/manager_market';path=folder/media['image']
  fallback=folder/'minifaces/NOTFOUND_DEFAULT.png'
  if not path.resolve().is_relative_to(folder.resolve()):path=fallback
  try:
   with Image.open(path if path.is_file() else fallback) as src:assets[media['head']]=portrait(src).resize((204,204),Image.Resampling.LANCZOS)
  except (OSError,ValueError):assets[media['head']]=Image.new('RGBA',(204,204),'#dbe3e9')
 image(media['head'],'img_'+media['head'],112,218,160,160)
 flag=media['flag'];read(flag,[f'data/ui/imgAssets/flags512x512/f_{flag[5:]}.dds'],(64,40),generic)
 image(flag,'img_'+flag,286,219,28,19)
 for key in media['crests']:
  ident=key.split('_',1)[1];read(key,[f'data/ui/imgAssets/crest/{kind}/l{ident}.dds' for kind in ('light','dark')],(128,128),shield)
  if key==media['current']:image(key,'current_'+key,286,294,36,40)
  for i in range(3):
   image(key,'entry'+str(i)+'_'+key,510,315+i*182+18,74,74)
   image(key,'titleCrest'+str(i)+'_'+key,696,TITLE_TOP+i*TITLE_STEP+101,40,44)
 for key in media['competitions']:
  ident=key.split('_',1)[1];read(key,[f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png',f'data/ui/imgAssets/league/light/l{ident}.dds'],(128,128))
  cup='cup_'+ident;read(cup,[f'data/ui/imgAssets/trophy256x256/t{ident}.dds'],(160,160))
  for i in range(3):
   image(key,'titleCompetition'+str(i)+'_'+key,696,TITLE_TOP+i*TITLE_STEP+20,68,70)
   image(cup,'titleCup'+str(i)+'_'+cup,554,TITLE_TOP+i*TITLE_STEP+20,112,112)
 return scene.pack(),assets
