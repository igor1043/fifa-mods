"""Artwork and geometry for the game's coach market; no browser-only mockup."""
from pathlib import Path
import io,math
from PIL import Image,ImageDraw
from layout import Scene
from ui_theme import ACCENT
from profile_layout import profile_scene
from profile_art import pitch,formation,panel,glyph
TABS=('Clubes e ligas','Movimentações','Livres no mercado');MAIN=(0,3,4)
PAGE_SIZE=6
INK='#173449';MUTED='#718797';PAPER='#f2f6f8';LIGHT='#e6edf2';GREEN='#078e47';RED='#cf3546'
def club_xy(i):return 490+i%2*666,318+i//2*188
def free_xy(i):return 96+i%2*870,318+i//2*188
def move_xy(i):return 96+i//4*870,402+i%4*112
def text(s,name,x,y,w,h,value='',size=22,color=INK):s.text(x,y,w,h,value,size,color);s.nodes[-1]['name']=name
def image(s,key,name,x,y,w,h):s.image(key,x,y,w,h);s.nodes[-1]['name']=name
def action(s,x,y,w,h,code,label='',fill=LIGHT,size=22):s.action(x,y,w,h,label,str(code),fill,INK,size)
def card(s,x,y,w,h,code):
 action(s,x,y,w,h,code,fill='#ffffff');s.nodes[-1]['background_asset']='card'

def stars(n):
 im=Image.new('RGBA',(320,64));d=ImageDraw.Draw(im)
 for j in range(5):
  pts=[(j*64+32+26*math.sin(i*math.pi/5)*(1 if i%2==0 else .45),32-26*math.cos(i*math.pi/5)*(1 if i%2==0 else .45)) for i in range(10)]
  d.polygon(pts,fill='#bcc5ce')
  if n>=2*j+2:d.polygon(pts,fill='#e9b329')
  elif n==2*j+1:
   layer=Image.new('RGBA',im.size);ImageDraw.Draw(layer).polygon(pts,fill='#e9b329');im.alpha_composite(layer.crop((j*64,0,j*64+32,64)),(j*64,0))
 return im

def fit_image(src,size):
 im=src.convert('RGBA');box=im.getbbox()
 if box:im=im.crop(box)
 im.thumbnail(size,Image.Resampling.LANCZOS);out=Image.new('RGBA',size);out.alpha_composite(im,((size[0]-im.width)//2,(size[1]-im.height)//2));return out

def assets_for(game,model):
 from asset_cache import prepared
 return prepared(game,model,lambda:prepare_assets(game,model))

def prepare_assets(game,model):
 import portable_paths as portable
 assets={'stars_'+str(i):stars(i) for i in range(11)};assets['accent']=Image.new('RGBA',(4,4),ACCENT)
 folder=Path(game)/'ModCarrerMode/data/manager_market';default=folder/'minifaces/NOTFOUND_DEFAULT.png'
 from club_portraits import colors,portrait
 palettes=colors(game);current={model['people'][r[7]]['head']:palettes.get(int(r[4].split('_')[1])) for r in model['clubRows'] if r[5]!='head_NOTFOUND_DEFAULT'}
 for p in model['people']+[dict(head='head_NOTFOUND_DEFAULT',image='minifaces/NOTFOUND_DEFAULT.png')]:
  if p['head'] in assets:continue
  path=folder/p['image']
  with Image.open(path if path.is_file() else default) as src:assets[p['head']]=portrait(src,current.get(p['head']))
 def art(key,candidates,size,fallback):
  for candidate in candidates:
   try:
    with Image.open(io.BytesIO(portable.read_asset(candidate))) as src:assets[key]=fit_image(src,size)
    return
   except (OSError,ValueError):pass
  assets[key]=fallback.copy()
 shield=Image.new('RGBA',(128,128));ImageDraw.Draw(shield).polygon([(28,18),(100,18),(95,83),(64,112),(33,83)],fill='#b8c6cf')
 crest_keys={r[4] for group in ('clubRows','moveRows','hireRows') for r in model[group]}|{r[1] for p in model['people'] for r in p.get('spellCards',[])}|{r[3] for p in model['people'] for r in p.get('titleCards',[])}
 for key in crest_keys:
  ident=key.split('_')[1];art(key,[f'data/ui/imgAssets/crest/{kind}/l{ident}.dds' for kind in ('light','dark')],(128,128),shield)
 for l in model['leagues']:
  ident=l['id'];art(l['image'],[f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png',f'data/ui/imgAssets/league/light/l{ident}.dds',f'data/ui/imgAssets/league/dark/l{ident}.dds'],(128,128),shield)
 for ident in {t['competition'] for p in model['people'] for t in p.get('career',{}).get('titles',[])}:art('competition_'+str(ident),[f'data/ui/imgAssets/careerCompetitionIcons/{ident}.png',f'data/ui/imgAssets/league/light/l{ident}.dds',f'data/ui/imgAssets/league/dark/l{ident}.dds'],(128,128),shield)
 assets['track']=Image.new('RGBA',(4,4),'#dbe5eb')
 generic=Image.new('RGBA',(64,40));d=ImageDraw.Draw(generic);d.rounded_rectangle((1,1,62,38),5,fill='#dbe3e9');d.ellipse((22,10,42,30),outline='#8c9eaa',width=2);d.line((23,20,41,20),fill='#8c9eaa',width=2)
 flags={p.get('flag','flag_0') for p in model['people']}|{c['flag'] for c in model.get('countries',[])}|{'flag_0'}
 for key in flags:
  if key=='flag_uk':
   im=Image.new('RGBA',(64,40),'#173d76');d=ImageDraw.Draw(im);d.line((0,0,64,40),fill='white',width=10);d.line((0,40,64,0),fill='white',width=10);d.line((0,0,64,40),fill='#c83246',width=4);d.line((0,40,64,0),fill='#c83246',width=4);d.rectangle((25,0,38,40),fill='white');d.rectangle((0,13,64,26),fill='white');d.rectangle((28,0,35,40),fill='#c83246');d.rectangle((0,16,64,23),fill='#c83246');assets[key]=im
  elif key=='flag_0':assets[key]=generic
  else:art(key,[f'data/ui/imgAssets/flags512x512/f_{key[5:]}.dds'],(64,40),generic)
 assets['card']=panel(656,180,radius=12)
 coin=Image.new('RGBA',(128,128));d=ImageDraw.Draw(coin)
 for y in (80,56,32):d.ellipse((16,y-16,108,y+24),fill=LIGHT,outline=INK,width=6)
 assets['coin']=coin
 for name in ('coach','shield','trophy'):assets['nav_'+name]=glyph(name)
 assets['nav_left']=glyph('chevron');assets['nav_right']=assets['nav_left'].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
 for person in model['people']:
  value=person.get('formation','')
  if formation(value):
   key='profile_pitch_'+value.replace('-','_').replace('–','_')
   if key not in assets:assets[key]=pitch(value)
 return assets

def shell(model,key,title):
 s=Scene(key,title);s.rect(60,90,1800,828,PAPER);s.text(96,111,1680,50,'MERCADO DE TÉCNICOS',36,INK,bold=True)
 date=str(model['date']);s.text(98,164,1700,29,model['clubName']+' · '+date[6:8]+'/'+date[4:6]+'/'+date[:4]+' · Salários em moeda da carreira' if model.get('ready') else 'Aguardando os dados da carreira aberta...',21,MUTED)
 for i,label in enumerate(TABS):
  action(s,96+i*580,203,568,44,i,size=24);image(s,'accent','tabMark'+str(i),96+i*580,203,568,44)
  s.image('nav_'+('shield','trophy','coach')[i],235+i*580,215,22,22)
  text(s,'navLabel'+str(i),96+i*580,212,568,30,label,24);s.nodes[-1]['align']=2
 return s

def row_images(s,assets,prefix,rows,model,*,head=80,crest=96,slots=8,rating_height=24):
 used={r[c] for r in rows for c in (4,5)};flags={model['people'][r[7]].get('flag','flag_0') for r in rows}|{'flag_0'}
 for key in assets:
  if key in used and key.startswith('head_') and key!='head_NOTFOUND_DEFAULT':image(s,key,prefix+key,0,0,head,head)
  if key in used and key.startswith('crest_'):image(s,key,prefix+key,0,0,crest,crest)
 for i in range(slots):
  image(s,'head_NOTFOUND_DEFAULT',prefix+'fallback'+str(i),0,0,head,head)
  for key in assets:
   if key in flags:image(s,key,prefix+'flag'+str(i)+'_'+key,0,0,28,18)
  for n in range(11):image(s,'stars_'+str(n),prefix+'rating'+str(i)+'_'+str(n),0,0,118,rating_height)

def scenes_for(model,assets):
 s=shell(model,'clubs','Clubes e ligas')
 s.image('card',96,294,366,144);s.text(114,306,270,25,'PAÍS / REGIÃO',19,MUTED);text(s,'countryCount',363,308,80,23,'',17,MUTED)
 action(s,108,357,32,45,10,fill='#ffffff');action(s,416,357,32,45,11,fill='#ffffff');s.image('nav_left',116,370,16,20);s.image('nav_right',424,370,16,20);text(s,'countryName',210,358,204,47,'',29)
 s.image('card',96,454,366,167);s.text(114,468,260,25,'LIGA',19,MUTED);text(s,'leagueCount',363,470,80,23,'',17,MUTED)
 action(s,108,523,32,48,20,fill='#ffffff');action(s,416,523,32,48,21,fill='#ffffff');s.image('nav_left',116,538,16,20);s.image('nav_right',424,538,16,20);text(s,'leagueName',211,510,202,67,'',22);text(s,'leagueLevel',211,578,202,28,'',17,MUTED)
 text(s,'clubCount',114,651,325,45,'',30);s.text(490,278,1300,31,'CLUBES · TÉCNICO · REPUTAÇÃO · SALÁRIO MENSAL',22,INK)
 for i in range(PAGE_SIZE):
  x,y=club_xy(i);card(s,x,y,654,180,40+i);s.rect(x+511,y+18,1,142,LIGHT)
  text(s,'club'+str(i),x+516,y+87,128,35,'',17);s.nodes[-1]['align']=2;text(s,'coach'+str(i),x+174,y+17,327,32,'',24)
  s.image('coin',x+174,y+140,22,22);text(s,'amount'+str(i),x+205,y+137,155,29,'',22);s.text(x+362,y+143,60,22,'/ mês',16,MUTED)
  s.rect(x+527,y+128,110,38,LIGHT);s.text(x+538,y+139,100,23,'Ver perfil ›',16,INK)
  text(s,'nationality'+str(i),x+208,y+55,293,25,'',18,MUTED);text(s,'tenure'+str(i),x+174,y+113,327,23,'',15,MUTED)
 action(s,490,885,70,30,50,'‹');action(s,1756,885,60,30,51,'›');text(s,'pageText',579,889,1150,28,'',18,MUTED);text(s,'empty',520,560,1200,80,'',25,MUTED)
 row_images(s,assets,'c_',model['clubRows'],model,head=152,crest=64,slots=PAGE_SIZE)
 for key in assets:
  if key.startswith('flag_'):image(s,key,'country_'+key,151,365,48,30)
  elif key.startswith('league_'):image(s,key,'league_'+key,147,511,60,68)

 if 'track' not in assets:assets['track']=Image.new('RGBA',(4,4),'#dbe5eb')
 if 'accent' not in assets:assets['accent']=Image.new('RGBA',(4,4),ACCENT)
 if 'card' not in assets:assets['card']=Image.new('RGBA',(8,8),'white')
 p=profile_scene(assets)
 loading=Scene('loading','Carregando o mercado');loading.rect(60,90,1800,828,PAPER);loading.text(100,125,1680,64,'MERCADO DE TÉCNICOS',39,INK);loading.text(100,360,1680,52,'Carregando o mercado desta carreira...',30,INK);text(loading,'progress',100,426,1660,44,'Preparando os dados...',24,MUTED)

 moves=shell(model,'movements','Demissões e contratações')
 moves.text(96,278,670,35,'DEMISSÕES E CONTRATAÇÕES',26,INK,bold=True)
 action(moves,1052,277,60,39,32,'«');action(moves,1124,277,60,39,30,'‹');text(moves,'monthName',1204,282,450,34,'',25);action(moves,1674,277,60,39,31,'›');action(moves,1746,277,60,39,33,'»')
 for panel,(title,color,prefix,label) in enumerate((('CONTRATAÇÕES',GREEN,'h_','contratações'),('DEMISSÕES',RED,'d_','demissões'))):
  x=96+panel*870;moves.rect(x,338,5,507,color);moves.text(x+22,351,540,38,title,27,color,bold=True);text(moves,prefix+'count',x+620,357,205,28,'',19,color)
  for j in range(4):
   i=panel*4+j;_,y=move_xy(i);card(moves,x+15,y,831,104,40+i);text(moves,'club'+str(i),x+103,y+20,171,34,'',20);text(moves,'coach'+str(i),x+374,y+14,290,30,'',22)
   text(moves,'nationality'+str(i),x+407,y+45,259,25,'',17,MUTED);text(moves,'date'+str(i),x+374,y+75,290,24,'',16,MUTED)
   moves.rect(x+674,y+31,151,35,'#e6f5ed' if panel==0 else '#fbecef');text(moves,'status'+str(i),x+684,y+39,134,26,'',17,color)
  text(moves,prefix+'empty',x+50,559,745,65,'',24,MUTED);action(moves,x+19,865,55,36,52+panel*2,'‹');action(moves,x+789,865,55,36,53+panel*2,'›');text(moves,prefix+'page',x+94,872,675,27,'',17,MUTED)
  row_images(moves,assets,prefix,model['hireRows' if panel==0 else 'moveRows'],model,head=76,crest=72,slots=4)

 free=shell(model,'free','Livres no mercado');free.text(96,278,570,33,'TÉCNICOS LIVRES NO MERCADO',24,INK,bold=True)
 action(free,735,276,42,34,34,'‹');text(free,'ageValue',792,283,265,26,'',18);action(free,1061,276,42,34,35,'›')
 action(free,1150,276,42,34,36,'‹');text(free,'natValue',1207,283,536,26,'',18);action(free,1763,276,42,34,37,'›')
 for i in range(PAGE_SIZE):
  x,y=free_xy(i);card(free,x,y,858,180,40+i);text(free,'coach'+str(i),x+170,y+17,470,35,'',26)
  free.rect(x+665,y+17,175,35,'#e7f6ef');text(free,'status'+str(i),x+679,y+26,157,25,'',16,GREEN)
  text(free,'nationality'+str(i),x+205,y+61,445,27,'',19,MUTED);text(free,'freeDays'+str(i),x+170,y+94,270,27,'',18,MUTED)
  free.rect(x+170,y+131,230,32,'#eef3f6');text(free,'style'+str(i),x+182,y+139,206,25,'',18,INK)
  free.rect(x+416,y+131,218,32,'#eef3f6');text(free,'formation'+str(i),x+428,y+139,194,25,'',17,MUTED)
  free.rect(x+653,y+127,187,40,LIGHT);free.text(x+697,y+140,143,27,'Ver perfil  ›',19,INK);text(free,'age'+str(i),x+459,y+94,180,27,'',18,MUTED)
 action(free,96,885,65,30,50,'‹');action(free,1752,885,65,30,51,'›');text(free,'pageText',180,889,1540,27,'',18,MUTED);text(free,'empty',120,548,1640,80,'',26,MUTED)
 row_images(free,assets,'f_',model['freeRows'],model,head=128,crest=72,slots=PAGE_SIZE)
 # Hide the whole empty card, including its salary/status decoration.
 for scene,bounds in ((s,[(*club_xy(i),654,180) for i in range(PAGE_SIZE)]),(moves,[(move_xy(i)[0]+15,move_xy(i)[1],831,104) for i in range(8)]),(free,[(*free_xy(i),858,180) for i in range(PAGE_SIZE)])):
  for j,node in enumerate(scene.nodes):
   if node['type']=='action' or node['x']==0 or node.get('name'):continue
   for slot,(x,y,w,h) in enumerate(bounds):
    if x<=node['x']<x+w and y<=node['y']<y+h:
     if node['type']=='rect':
      rounded=node['w']>100 and node['h']<=70;key=('pill_' if rounded else 'fill_')+node['color'][1:]
      if key not in assets:
       im=Image.new('RGBA',(256,64)) if rounded else Image.new('RGBA',(4,4),node['color'])
       if rounded:ImageDraw.Draw(im).rounded_rectangle((0,0,255,63),12,fill=node['color'])
       assets[key]=im
      node.update(type='image',asset=key)
     node.setdefault('name','deco'+str(j));node['slot']=slot;break
 return [s.pack(),p.pack(),loading.pack(),moves.pack(),free.pack()]
