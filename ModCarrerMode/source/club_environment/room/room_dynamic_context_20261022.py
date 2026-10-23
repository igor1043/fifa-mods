import portable_paths as portable
"""Read-only club identity, next-fixture board and camera targets for native room."""
from pathlib import Path
import json,io,hashlib,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from room_native_hanging_20261022 import texture_package
ROOT=portable.ROOM;GAME=portable.GAME;LIVE=GAME/'data/sceneassets/server16_dressing_room_20261022'

def clean(text):
 for _ in range(3):
  if '\u00c3' not in text and '\u00c2' not in text:break
  try:text=text.encode('cp1252').decode('utf8')
  except (UnicodeError,ValueError):break
 return text

def colors(team,base_team=None):
 def value(k,default):
  for row in (team,base_team):
   if row and k in row.fields:return row.value(k)
  return default
 return [[value(f'teamcolor{i}{c}',default)/255 for c,default in zip('rgb',(38,62,88) if i==1 else (225,228,232))] for i in (1,2)]

def make_context(snap,projected,roster,rows,base,read_asset):
 club=snap['club'];teams={r.value('teamid'):r for r in rows('teams')};base_teams={r.value('teamid'):r for r in base.get('teams',[])}
 palette=colors(teams.get(club),base_teams.get(club));fixture=projected['fixture'];opponent=projected['opponent'];user=projected['user'];by_node={r[0]:r for r in snap['nodes']};node=fixture[1];league=0
 for _ in range(12):
  row=by_node.get(node)
  if not row:break
  if row[2]==3 and row[3]>0:league=row[3];break
  node=row[1]
 from competition_names_r57 import competition_name
 league_name=competition_name(league,rows)
 def tactics(teamid):
  sheets=[r for r in rows('teamsheets') if r.value('teamid')==teamid and r.value('isfavourite')==1];row=sheets[0] if len(sheets)==1 else teams.get(teamid);fallback=base_teams.get(teamid);out={}
  for label,keys in [('Ritmo',('busbuildupspeed','buildupplayspeed')),('Passe',('buspassing','buildupplaypassing')),('Mentalidade',('defmentality','defencepressure')),('Agressividade',('defaggression','defenceaggression')),('Largura',('defteamwidth','defenceteamwidth'))]:
   for candidate in (row,fallback):
    if not candidate:continue
    key=next((k for k in keys if k in candidate.fields),None)
    if key:out[label]=candidate.value(key);break
  return out
 context={'pid':snap['pid'],'club':club,'club_name':clean(user.get('name','') or (teams[club].value('teamname') if club in teams else base_teams[club].value('teamname'))),'colors':palette,'fixture':fixture,'date':projected['date'],'league':league,'league_name':league_name,'user':user,'opponent':opponent,'tactics':tactics(club),'opponent_tactics':tactics(opponent['team_id']),'available':projected.get('available',True)}
 context['opponent_colors']=colors(teams.get(opponent['team_id']),base_teams.get(opponent['team_id']))
 numbers={(r.value('teamid'),r.value('playerid')):r.value('jerseynumber') for r in rows('teamplayerlinks')}
 for team in (user,opponent):
  team['name']=clean(team.get('name',''))
  for p in team['players']:p['name']=clean(p['name']);p['number']=numbers.get((team['team_id'],p['id']),0)
 context['board_revision']=4
 payload={k:v for k,v in context.items() if k not in ('pid','date')};signature=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:14];path=LIVE/f'next_match_{club}_{signature}_r52.rx3'
 if not path.exists():texture_package(draw_board(context,read_asset),path,'board_cm')
 context['board_texture']='data/sceneassets/server16_dressing_room_20261022/'+path.name
 context['focus']=[]
 for number in (9,10):
  found=next(((i,p) for i,p in enumerate(roster) if p['number']==number),None)
  if found:
   i,p=found;context['focus'].append({'number':number,'locker':i,'player':p['id'],'name':p['name']})
 (ROOT/'runtime/room_context_r46.json').write_text(json.dumps(context,ensure_ascii=False,indent=2),encoding='utf8')
 return context

def draw_board(c,read_asset):
 im=Image.new('RGBA',(1600,1008),(239,238,228,255));d=ImageDraw.Draw(im)
 def font(size,bold=False):return ImageFont.truetype(str(portable.FONTS/('arialbd.ttf' if bold else 'arial.ttf')),size)
 def text(x,y,s,size=30,color=(30,45,51),bold=False):d.text((x,y),str(s),font=font(size,bold),fill=color+(255,))
 def icon(paths,box):
  for path in paths:
   try:
    img=Image.open(io.BytesIO(read_asset(path))).convert('RGBA');img.thumbnail((box[2],box[3]),Image.Resampling.LANCZOS);im.alpha_composite(img,(box[0]+(box[2]-img.width)//2,box[1]+(box[3]-img.height)//2));return path
   except (FileNotFoundError,OSError,ValueError):pass
  return ''
 primary=tuple(round(v*255) for v in c['colors'][0]);d.rectangle((0,0,1600,13),fill=primary+(255,));text(42,32,'PRÓXIMA PARTIDA',48,bold=True)
 league=c['league'];icon([f'data/ui/imgassets/careerCompetitionIcons/{league}.png',f'data/ui/imgassets/league/light/l{league}.dds',f'data/ui/imgassets/league/dark/l{league}.dds',f'data/ui/imgassets/league/{league}.dds',f'data/ui/imgassets/cmCalendarCompetitions/cmCalendarCompetitions{league}.dds'],(1330,28,210,100))
 text(42,95,c['league_name'] or ('Competição '+str(league) if league else 'Calendário da carreira'),28)
 if not c['available']:text(220,400,'Sem próxima partida agendada',48,bold=True);return im.resize((2048,2048),Image.Resampling.LANCZOS)
 fixture=c['fixture'];date=str(fixture[3]);hour=fixture[4];text(670,42,f'{date[6:8]}/{date[4:6]}/{date[:4]}  •  {hour//100:02d}:{hour%100:02d}',30)
 for team,x in ((c['user'],42),(c['opponent'],825)):
  ident=team['team_id'];icon([f'data/ui/imgassets/crest/light/l{ident}.dds',f'data/ui/imgassets/crest/dark/l{ident}.dds'],(x,152,100,100));text(x+122,168,team['name'],36,bold=True)
  subtitle=('SEU TIME • '+('MANDANTE' if fixture[5]==ident else 'VISITANTE')) if ident==c['club'] else 'ADVERSÁRIO • ESCALAÇÃO PROVÁVEL'
  text(x+122,216,subtitle,22);text(x,275,'FORMAÇÃO '+team['formation'],29,bold=True)
  left,top,w,h=x,325,690,460;d.rounded_rectangle((left,top,left+w,top+h),radius=12,fill=(34,79,57),outline=(125,151,128),width=3)
  d.rectangle((left+14,top+14,left+w-14,top+h-14),outline=(168,190,163),width=2);d.line((left+w/2,top+14,left+w/2,top+h-14),fill=(168,190,163),width=2);d.ellipse((left+w/2-55,top+h/2-55,left+w/2+55,top+h/2+55),outline=(168,190,163),width=2)
  color=primary if ident==c['club'] else tuple(round(v*255) for v in c['opponent_colors'][0]);luma=sum(color)/3;ink=(20,27,31) if luma>150 else (255,255,255)
  for p in team['players']:
   px=left+40+p['y']*(w-80);py=top+32+p['x']*(h-64);d.ellipse((px-29,py-29,px+29,py+29),fill=(12,26,36),outline=color+(255,),width=4)
   label=str(p['number']);box=d.textbbox((0,0),label,font=font(36,True));d.text((round(px-(box[2]-box[0])/2),round(py-(box[3]-box[1])/2-box[1])),label,font=font(36,True),fill=(255,255,255,255),stroke_width=1,stroke_fill=(0,0,0,255))

  saved=c['tactics'] if ident==c['club'] else c['opponent_tactics'];y=813
  text(x,y,'TÁTICAS GRAVADAS',24,bold=True)
  for j,(key,value) in enumerate(saved.items()):text(x+(j%3)*218,y+37+(j//3)*43,f'{key}: {value}',20)
 text(42,958,'Onze adversário provável. Formações e parâmetros vêm do save; nenhuma tática é inventada.',24,(71,78,78))
 return im.resize((2048,2048),Image.Resampling.LANCZOS)

def write_tour(context,roster,frame,rotation,generation):
 data=json.loads((ROOT/'runtime/room_roles_r57.json').read_text(encoding='utf8'));focus=[]
 for p in context['focus']:
  origin,yaw=frame(p['locker']);r=rotation(yaw);eye=origin+r@np.array([0,187,285]);target=origin+r@np.array([0,165,54]);eye[0]=max(-575,min(575,eye[0]));focus.append([p['number'],*eye.tolist(),*target.tolist()])
 # The renderer consumes look-at targets from scene/locker anchors, not club names.
 bounds=data['camera_bounds'];width=bounds['half_width']-306;back=bounds['back'];front=bounds['front']
 eyes=[[0,187,front-200],[width,185,front-370],[width,182,50],[width,185,back+310],[0,188,back+220],[-width,185,back+310],[-width,182,50],[-width,185,front-370]]
 target_slots=[None,28,22,2,0,11,23,29];path=[]
 for eye,slot,fov in zip(eyes,target_slots,[74,64,62,62,66,62,62,64]):
  if slot is None:target=data['board_anchor']['target']
  else:
   origin,yaw=frame(slot);target=(origin+rotation(yaw)@np.array([0,170,54])).tolist()
  path.append([*eye,*target,fov])
 anchor=data['board_anchor'];target=np.array(anchor['target']);normal=np.array(anchor['normal']);eye=target+normal*348;eye[1]=188
 details=[[ *eye.tolist(),*target.tolist(),57]]
 shirts=[]
 order=list(range(34,11,-2))+list(range(12))+list(range(13,35,2))
 for i in order:
  if i>=len(roster):continue
  origin,yaw=frame(i);r=rotation(yaw);eye=origin+r@np.array([0,187,225]);eye[0]=max(-575,min(575,eye[0]));target=origin+r@np.array([0,165,54]);shirts.append([roster[i]['number'],*eye.tolist(),*target.tolist()])
 medical=json.loads((ROOT/'runtime/medical_room_r57.json').read_text(encoding='utf8'));navigation=medical['navigation'];extra=[s['pose'] for s in medical['scenes']]
 obstacles=data['obstacles']+medical['obstacles'];lines=[f'S16TOUR 5 {context["pid"]} {context["club"]} {generation} {len(focus)} {len(obstacles)} {len(path)} {len(details)} {len(shirts)} {len(navigation)} {len(extra)}']
 lines+=[' '.join(map(str,p)) for p in focus]
 lines+=[' '.join(map(str,p['lo']+p['hi'])) for p in obstacles]
 lines+=[' '.join(map(str,p)) for p in path+details+shirts+navigation+extra]
 path=ROOT/'runtime/room_tour_r46.txt';temp=path.with_suffix('.tmp');temp.write_text('\n'.join(lines)+'\n');temp.replace(path)
