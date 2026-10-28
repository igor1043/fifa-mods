import portable_paths as portable
"""Read active career and reference native FIFA scene assets. No save writes."""
from pathlib import Path
import sys,struct,json,math,collections,subprocess,xml.etree.ElementTree as ET,os,re,time,hashlib
import numpy as np
from functools import lru_cache
from PIL import Image,ImageFont,ImageDraw
from rx3 import Rx3,VERTEX,FORMAT,MESH,TEXTURE
from room_native_hanging_20261022 import prepare_geometry,hardware_texture,texture_package
from room_dynamic_context_20261022 import make_context,write_tour
from room_native_kit_rules_r46 import rules,number_candidates,name_candidates
from kit_selection import current_kits
ROOT=portable.ROOM;GAME=portable.GAME
CACHE=ROOT/'runtime/native_source_geometry';CACHE.mkdir(exist_ok=True)
EXTRACT=None
sys.path.insert(0,str(portable.PREVIEW))
import room_projection_r52 as projection
from room_roster_r52 import roster_order,scene_catalog
projection.TABLES.update({'teamkits','leagueteamlinks','leagues'})
_asset_cache={}
_archive_stamp=[(str(p.relative_to(GAME)),p.stat().st_size,p.stat().st_mtime_ns) for folder in (GAME,GAME/'data') for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.big','.bh')]
_missing_index=CACHE/'missing_assets_r56.json'
try:_previous_missing=json.loads(_missing_index.read_text(encoding='utf8'))
except (OSError,ValueError):_previous_missing={}
_missing_assets=set(_previous_missing.get('paths',[])) if _previous_missing.get('stamp')==[list(p) for p in _archive_stamp] else set()
def read_asset(path):
 if path in _asset_cache:return _asset_cache[path]
 direct=GAME/path
 if direct.is_file():
  data=direct.read_bytes();_asset_cache[path]=data;return data
 if path in _missing_assets:raise FileNotFoundError(path)
 try:data=portable.read_asset(path)
 except FileNotFoundError:
  _missing_assets.add(path);_missing_index.write_text(json.dumps({'stamp':_archive_stamp,'paths':sorted(_missing_assets)}),encoding='utf8');raise
 _asset_cache[path]=data;return data
@lru_cache(maxsize=512)
def bounds(path):
 rx=Rx3(read_asset(path));vb=rx.get(VERTEX)[0];n,stride=struct.unpack_from('<II',vb,4)
 fmt=rx.get(FORMAT)[0][16:].split(b'\0')[0].decode();pfield=next(x for x in fmt.split() if x.startswith('p0:'));off=int(pfield.split(':')[1],16);half=pfield.endswith('4f16')
 p=np.ndarray((n,3),dtype='<f2' if half else '<f4',buffer=vb,offset=16+off,strides=(stride,2 if half else 4)).astype(np.float32)
 return p.min(axis=0),p.max(axis=0),next(n.removesuffix('.FxRenderableSimple') for t,n in rx.names() if t==MESH)
def frame(i):
 if i<12:return np.array([-630+i*90 if i<6 else 180+(i-6)*90,0,-592],dtype=float),0
 q=i-12;left=q%2==0;return np.array([-732 if left else 732,0,-410+(q//2)*102],dtype=float),math.pi/2 if left else -math.pi/2
def rotation(y):return np.array([[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]])
def placed(i,lo,hi,center,height,width,hang):
 origin,yaw=frame(i);size=hi-lo;s=min(height/max(.1,size[1]),width/max(.1,size[0]));mid=(lo+hi)/2
 r=rotation(yaw);orient=r@rotation(math.pi if hang else 0)*s
 anchor=np.array([mid[0],hi[1] if hang else lo[1],mid[2]])
 t=origin+r@np.array(center)-orient@anchor;t+=np.array([100000,1000,0])
 m=np.eye(4);m[:3,:3]=orient;m[:3,3]=t;return m.T.reshape(-1).tolist()
def quad(i,center,width,height):
 origin,yaw=frame(i);r=rotation(yaw);m=np.eye(4);m[:3,:3]=r@np.diag([width,height,1]);m[:3,3]=origin+r@np.array(center)+[100000,1000,0];return m.T.reshape(-1).tolist()
def locker_matrix(i):
 origin,yaw=frame(i);m=np.eye(4);m[:3,:3]=rotation(yaw);m[:3,3]=origin+[100000,1000,0];return m.T.reshape(-1).tolist()

def career():
 current=projection.project();snap=json.loads((GAME/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text());assert snap['pid']==current['pid']
 cached=projection.last_tables;assert cached and cached[:2]==(snap['savePath'],snap['saveWriteTime100ns']),'Validated career projection changed'
 saved,base=cached[2:]
 rows=lambda n:saved[n] if n in saved else base.get(n,[]);club=snap['club'];players={r.value('playerid'):r for r in rows('players')};links={r.value('playerid'):r for r in rows('teamplayerlinks') if r.value('teamid')==club}
 order=[]
 for r in rows('teamsheets'):
  if r.value('teamid')==club and r.value('isfavourite')==1:order=[r.value('playerid'+str(i)) for i in range(11)];break
 order=roster_order(players,links,order)
 cache=json.loads((portable.PREVIEW/'base_name_cache.json').read_text(encoding='utf8'));names={int(k):v for k,v in cache.get('names',{}).items()}
 wanted={players[pid].value(k) for pid in order for k in ('commonnameid','playerjerseynameid','lastnameid') if k in players[pid].fields}
 own=ROOT/'runtime/native_roster_names.json';own_cache=json.loads(own.read_text(encoding='utf8')) if own.exists() else {};names.update({int(k):v for k,v in own_cache.items()})
 names.update({r.value('nameid'):r.value('name') for r in saved.get('dcplayernames',[])})
 state_path=ROOT/'runtime/native_roster_names_state_r56.json';dbstat=(GAME/'data/db/fifa_ng_db.db').stat();dbstamp=[dbstat.st_size,dbstat.st_mtime_ns]
 queried=json.loads(state_path.read_text(encoding='utf8')) if state_path.exists() else {}
 if queried.get('stamp')!=dbstamp:queried={'stamp':dbstamp,'ids':[]}
 missing={ident for ident in wanted if ident>0}-set(names)-set(queried['ids'])
 if missing:
  request=ROOT/'runtime/native_name_ids.json';request.write_text(json.dumps(sorted(missing)))
  from server16_py.fifa_db import _find_python32,_find_dll
  out=subprocess.run([str(_find_python32()),'-B',str(portable.PREVIEW/'names_worker.py'),str(_find_dll()),str(GAME/'data/db/fifa_ng_db.db'),str(GAME/'data/db/fifa_ng_db-meta.xml'),str(request)],check=True,capture_output=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  found=json.loads(out.stdout);own_cache.update(found);own.write_text(json.dumps(own_cache,ensure_ascii=False),encoding='utf8');names.update({int(k):v for k,v in found.items()})
  queried['ids']=sorted(set(queried['ids'])|missing);state_path.write_text(json.dumps(queried),encoding='utf8')
 names.update({r.value('nameid'):r.value('name') for r in saved.get('dcplayernames',[])})
 edited={r.value('playerid'):r for r in rows('editedplayernames')}
 roster=[]
 for pid in order:
  p=players[pid];value=lambda k,default=0:p.value(k) if k in p.fields else default
  name=names.get(value('playerjerseynameid')) or names.get(value('commonnameid')) or names.get(value('lastnameid')) or ''
  if pid in edited:
   edit=edited[pid];name=next((edit.value(k) for k in ('playerjerseyname','commonname','surname') if k in edit.fields and edit.value(k)),name)
  for _ in range(3):
   if '\u00c3' not in name and '\u00c2' not in name:break
   try:fixed=name.encode('cp1252').decode('utf8')
   except (UnicodeEncodeError,UnicodeDecodeError):break
   if fixed==name:break
   name=fixed
  roster.append(dict(id=pid,name=name,number=links[pid].value('jerseynumber'),shoe=value('shoetypecode',15),design=value('shoedesigncode'),goalkeeper=value('preferredposition1')==0,glove=value('gkglovetypecode')))
 kit_fields=('teamtechid','teamid','teamkittypetechid','year','teamkitid','numberfonttype','numbercolor','jerseynamefonttype','jerseynamecolorr','jerseynamecolorg','jerseynamecolorb','jerseynamelayouttype','jerseybacknameplacementcode','jerseybacknamefontcase')
 kits=current_kits([{k:r.value(k) if k in r.fields else None for k in kit_fields} for r in rows('teamkits')],club)
 info={}
 for typ in (0,2):
  r=kits.get(typ,{});get=lambda k,default=0:r[k] if r.get(k) is not None else default
  info[typ]={'font':get('numberfonttype'),'color':get('numbercolor'),'name_font':get('jerseynamefonttype'),'name_color':[get('jerseynamecolor'+c,255) for c in 'rgb'],'layout':get('jerseynamelayouttype'),'name_placement':get('jerseybacknameplacementcode'),'name_case':get('jerseybacknamefontcase')}
 context=make_context(snap,current,roster,rows,base,read_asset)
 from room_medical_r53 import context_for_room
 context_for_room(context,roster,rows)
 try:team_rules=read_asset(f'data/fifarna/lua/assignments/teams/team_{club}.lua').decode('utf8',errors='replace')
 except FileNotFoundError:team_rules=''
 context['kit_rules']=rules(team_rules,club,context['league'],info)
 from room_live_kit_rules_r56 import apply_live
 context['kit_rules']['evaluated_lua_assignments']=apply_live(context,info)
 return snap,roster,info,context
def prepare():
 began=time.perf_counter();snap,roster,kits,context=career();read_ms=round((time.perf_counter()-began)*1000);club=snap['club'];print_sources=[];components={};native_refs=set();hanging={k:prepare_geometry(k,read_asset) for k in {2 if p['goalkeeper'] else 0 for p in roster}};hardware=hardware_texture()
 from room_kit_print_r56 import name_model,number_models,name_stamp,locker_plate
 native_names={};native_numbers={};print_warnings=[]
 for typ in hanging:
  kit_rx=Rx3(read_asset(f'data/sceneassets/kit/kit_{club}_{typ}_0.rx3'))
  try:native_names[typ]=name_model(club,typ,kit_rx)
  except ValueError as error:native_names[typ]=(None,None);print_warnings.append(f'kit {typ} name: {error}')
  try:native_numbers[typ]=number_models(club,typ,kit_rx)
  except ValueError as error:native_numbers[typ]={};print_warnings.append(f'kit {typ} number: {error}')
 def add(key,model,texture,texname,matrix,alpha=False,submesh=None,overlay=(0,0,0,0),page=-1,pages=0,bank=0):
  if key not in components:
   if submesh is None:submesh=bounds(model)[2]
   components[key]=dict(key=key,model=model,texture=texture,texname=texname,alpha=alpha,submesh=submesh,overlay=overlay,page=page,pages=pages,bank=bank,matrices=[]);native_refs.update(x for x in (model,texture) if not x.startswith('data/sceneassets/server16_dressing_room_20261022'))
  components[key]['matrices'].append(matrix)
 club_badge=Image.open(__import__('io').BytesIO(read_asset(f'data/ui/imgassets/crest/light/l{club}.dds'))).convert('RGBA')
 for i,p in enumerate(roster):
  typ=2 if p['goalkeeper'] else 0;jersey='data/sceneassets/body/jersey_0_'+('0' if typ==2 else '8')+'_0_0_1_0_0.rx3'
  kit=f'data/sceneassets/kit/kit_{club}_{typ}_0.rx3';native_refs.add(jersey);model=hanging[typ];pose=locker_matrix(i)
  add('jersey_'+str(typ),model,kit,'jersey_cm',pose,submesh='room_part_1')
  add('hanger_'+str(typ),model,hardware,'hardware_cm',pose,submesh='room_part_2')
  support='data/sceneassets/server16_dressing_room_20261022/locker_support_r68.rx3'
  if (GAME/support).is_file():add('hanger_support_'+str(typ),support,hardware,'hardware_cm',pose,submesh='room_part_1')
  shoe=f'data/sceneassets/shoe/shoe_{p["shoe"]}.rx3'
  try:lo,hi,sub=bounds(shoe)
  except FileNotFoundError:shoe='data/sceneassets/shoe/shoe_15.rx3';lo,hi,sub=bounds(shoe)
  shoe_tex=f'data/sceneassets/shoe/shoe_{p["shoe"]}_{p["design"]}_textures.rx3;data/sceneassets/shoe/shoe_15_0_textures.rx3'
  add('shoe_'+str(p['shoe'])+'_'+str(p['design']),shoe,shoe_tex,'shoe_cm',placed(i,lo,hi,[0,19,77],14,52,False),submesh=sub)
  info=kits[typ];font=info['font'];color=info['color']
  candidates=number_candidates(club,typ,context['league'],context['kit_rules']['default_league'],font,color)
  number_path=None;digits={}
  for path in candidates:
   try:rx=Rx3(read_asset(path));digits={int(m.group(1)):n for t,n in rx.names() if t==TEXTURE and (m:=re.search(r'_([0-9])(?:\..*)?$',n))};assert len(digits)==10;number_path=path;break
   except (FileNotFoundError,AssertionError):continue
  number=str(p['number']) if number_path and 0<=p['number']<=99 else ''
  for d,digit in enumerate(number):
   slot=4 if len(number)==1 else 5+d
   surface=native_numbers[typ].get(slot,(None,None))[0]
   if surface:add(f'number_{typ}_{slot}_{digit}',surface,number_path,digits[int(digit)],pose,True,'room_part_1')
  font_bytes=None
  for path in name_candidates(club,typ,context['league'],context['kit_rules']['default_league'],info['name_font']):
   try:
    candidate=read_asset(path);ImageFont.truetype(__import__('io').BytesIO(candidate),70);font_bytes=candidate;break
   except (FileNotFoundError,OSError):continue
  print_sources.append({'player':p['id'],'number':p['number'],'name':p['name'],'kit_type':typ,'number_asset':number_path,'name_font_asset':path if font_bytes else None,'name_color':info['name_color'],'native_name_hotspot':native_names[typ][1],'native_number_hotspots':{str(k):v[1] for k,v in native_numbers[typ].items()},'name_layout':info['layout'],'name_placement':info['name_placement'],'assignment_sources':info.get('assignment_sources',{}),'placement_source':'native kit UV hotspots r61'})
  name_surface,name_rect=native_names[typ]
  im=name_stamp(p['name'],font_bytes,info['name_color'],name_rect) if font_bytes and name_surface else None
  if im is not None:
   tag=hashlib.sha256(im.tobytes()+str((im.size,info,name_rect,'native_print_r61')).encode()).hexdigest()[:10]
   dest=GAME/f'data/sceneassets/server16_dressing_room_20261022/live_name_{club}_{p["id"]}_{tag}.rx3'
   if not dest.exists():texture_package(im,dest,'name_cm')
   relative='data/sceneassets/server16_dressing_room_20261022/'+dest.name
   add('name_'+str(i),name_surface,relative,'name_cm',pose,True,'room_part_1')
  plate=locker_plate(p['name'],context['colors'],club_badge);tag=hashlib.sha256(plate.tobytes()).hexdigest()[:12];dest=GAME/f'data/sceneassets/server16_dressing_room_20261022/locker_plate_{club}_{p["id"]}_{tag}_r56.rx3'
  if not dest.exists():texture_package(plate,dest,'plate_cm')
  add('plate_'+str(i),'data/sceneassets/server16_dressing_room_20261022/print_surface.rx3','data/sceneassets/server16_dressing_room_20261022/'+dest.name,'plate_cm',quad(i,[0,272,72],78,20),False,'room_part_1')
 crest=np.eye(4);crest[0,3]=100000
 add('club_crest','data/sceneassets/server16_dressing_room_20261022/crest_surfaces_r62.rx3',f'data/ui/imgassets/crest/light/l{club}.dds','',crest.T.reshape(-1).tolist(),True,'room_part_1')
 ball='data/sceneassets/ball/ball_23.rx3';lo,hi,sub=bounds(ball);scale=22/max(hi-lo);mid=(lo+hi)/2
 for layer in range(2):
  for x in range(3):
   for z in range(2):
    count=layer*6+x*2+z+1;r=rotation(count*.63);m=np.eye(4);m[:3,:3]=r*scale;m[:3,3]=np.array([-306+x*26,1035+layer*23,321+z*28])+[100000,0,0]-r@(mid*scale)
    add('balls',ball,'data/sceneassets/ball/ball_23_textures.rx3','ball_cm',m.T.reshape(-1).tolist(),False,sub)
 for center,yaw in (([-244,1011,263],1.8),([-317,1011,263],-.6)):
  r=rotation(yaw);m=np.eye(4);m[:3,:3]=r*scale;m[:3,3]=np.array(center)+[100000,0,0]-r@(mid*scale);add('balls',ball,'data/sceneassets/ball/ball_23_textures.rx3','ball_cm',m.T.reshape(-1).tolist(),False,sub)
 roles=json.loads((ROOT/'runtime/room_roles_r62.json').read_text(encoding='utf8'))
 matrix=np.eye(4);matrix[0,3]=100000;identity=matrix.T.reshape(-1).tolist();prefix='data/sceneassets/server16_dressing_room_20261022/'
 for i,role in enumerate(roles['roles']):
  name=role['role'];overlay=(0,0,0,0)
  if name in ('primary','secondary'):
   color=context['colors'][0 if name=='primary' else 1];rgb=tuple(round(255*min(1.,v*role['shade'])) for v in color);tag=hashlib.sha256(bytes(rgb)).hexdigest()[:12];filename=f'theme_{club}_{tag}_r48.rx3';dest=GAME/(prefix+filename)
   if not dest.exists():texture_package(Image.new('RGBA',(8,8),rgb+(255,)),dest,'theme_cm')
   texture=prefix+filename;texname='theme_cm' 
  elif name=='neutral':
   rgb=tuple(role['rgb']);tag=hashlib.sha256(bytes(rgb)).hexdigest()[:12];filename=f'neutral_{tag}_r62.rx3';dest=GAME/(prefix+filename)
   if not dest.exists():texture_package(Image.new('RGBA',(8,8),rgb+(255,)),dest,'neutral_cm')
   texture=prefix+filename;texname='neutral_cm'
  elif name=='floor':texture=prefix+'floor_textures_r44.rx3';texname='floor_cm'
  elif name=='ceiling':texture=prefix+('ceiling_r68.rx3' if (GAME/(prefix+'ceiling_r68.rx3')).is_file() else 'ceiling_r49.rx3');texname='ceiling_cm'
  elif name=='board':texture=context['board_texture'];texname='board_cm'
  else:raise ValueError('Unknown role '+name)
  role_model='room_roles_r68.rx3' if (GAME/(prefix+'room_roles_r68.rx3')).is_file() else 'room_roles_r62.rx3'
  add('role_'+name+'_'+str(i),prefix+role_model,texture,texname,identity,submesh=role['submesh'],overlay=overlay)
 add('floor_shadows',prefix+'floor_shadows_r56.rx3',prefix+'floor_shadows_texture_r56.rx3','shadow_cm',identity,True,'room_part_1')
 add('table_shadows',prefix+'floor_shadows_r56.rx3',prefix+'contact_shadow_r51.rx3','shadow_cm',identity,True,'room_part_2')
 assert 0<len(components)<=256,'Native room component group limit exceeded'
 from room_medical_r53 import prepare as prepare_medical
 prepare_medical(context,read_asset,add,identity)
 context['scene_catalog']=scene_catalog(context,roster)
 prepare_header(context)
 generation=int(time.time());write_tour(context,roster,frame,rotation,generation)
 config=f'S16NATIVE 3 {snap["pid"]} {club} {generation} {len(components)}\n'
 for c in components.values():
  assert 1<=len(c['matrices'])<=64
  config+=' '.join(json.dumps(str(c[k]),ensure_ascii=True) for k in ('key','model','submesh','texture','texname'))+f' {int(c["alpha"])} {len(c["matrices"])} {c["page"]} {c["pages"]} {c["bank"]} '+ ' '.join(format(v,'.7g') for v in c['overlay'])+'\n'
  config+='\n'.join(' '.join(format(float(x),'.9g') for x in m) for m in c['matrices'])+'\n'
 target=ROOT/'runtime/native_components_v2.txt';tmp=target.with_suffix('.tmp');tmp.write_text(config);os.replace(tmp,target)
 report={'preparation_ms':round((time.perf_counter()-began)*1000),'career_read_ms':read_ms,'pid':snap['pid'],'club':club,'save':snap['savePath'],'roster':roster,'kit_prints':kits,'print_sources':print_sources,'print_warnings':print_warnings,'context':context,'component_groups':len(components),'instances':sum(len(c['matrices']) for c in components.values()),'native_references':sorted(native_refs),'native_assets_packaged':False}
 (ROOT/'runtime/native_components_manifest_r46.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({k:report[k] for k in ('pid','club','component_groups','instances','native_assets_packaged')}))
def prepare_header(context):
 import build_dressing_card_20261022 as ui
 target=GAME/ui.BIG;state=ROOT/'runtime/room_header.json'
 previous=json.loads(state.read_text(encoding='utf8')) if state.exists() else {}
 catalog_hash=hashlib.sha256(json.dumps(context['scene_catalog'],sort_keys=True).encode()).hexdigest()
 if previous.get('revision')==ui.HEADER_REVISION and previous.get('pid')==context['pid'] and previous.get('club')==context['club'] and previous.get('name')==context['club_name'] and previous.get('catalog_hash')==catalog_hash and target.exists():return
 path=ui.screen(context,read_asset);temp=target.with_name(target.name+'.s16-new');temp.write_bytes(path.read_bytes());temp.replace(target)

def calendar_stamp(pid,details=False):
 from server16_py.memory_access import Memory
 from server16_py.career_context import competition_session
 import psutil
 m=Memory();m.process_id=pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,pid);m.base_module=m._get_base_address(psutil.Process(pid).exe())
 try:
  profile=competition_session(m,True)
  if not isinstance(profile,dict) or not profile.get('registry_address'):raise ValueError('Aguardando contexto da carreira')
  code=m.read_process_memory(m.base_module+0x44563f0,24)
  if code[7:9]!=b'\xc7\x01':raise ValueError('Calendar descriptor changed')
  index=struct.unpack_from('<I',code,9)[0]
  if index>=256:raise ValueError('Calendar index')
  calendar=m.read_int64(m.read_int64(profile['registry_address']+index*32+24))
  date=tuple(struct.unpack('<3i',m.read_process_memory(calendar+0x34,12)))
  return (date,profile) if details else date
 finally:m.close()

def publish_room_ready(pid):
 import prepared_views
 import build_dressing_card_20261022 as ui
 header=json.loads((ROOT/'runtime/room_header.json').read_text(encoding='utf8'))
 snap=json.loads((GAME/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text())
 if header.get('revision')!=ui.HEADER_REVISION or header.get('pid')!=pid or snap.get('pid')!=pid or header['club']!=snap.get('club'):return
 parts,profile=calendar_stamp(pid,True)
 if profile.get('club_id')!=header['club']:return
 import build_dressing_card_20261022 as ui
 revision=hashlib.sha256((GAME/ui.BIG).read_bytes()).hexdigest()
 prepared_views.publish(ROOT/'runtime/view_ready.tsv',dict(pid=pid,process_created_100ns=snap.get('processCreated100ns',0)),profile,parts[2]*10000+parts[1]*100+parts[0],revision)

def watch():
 import psutil
 pid=int(sys.argv[sys.argv.index('--pid')+1]) if '--pid' in sys.argv else next(p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower()=='fifa16.exe')
 import ctypes as C
 from ctypes import wintypes as W
 kernel=C.WinDLL('kernel32',use_last_error=True);kernel.CreateMutexW.argtypes=[C.c_void_p,W.BOOL,W.LPCWSTR];kernel.CreateMutexW.restype=W.HANDLE;kernel.CloseHandle.argtypes=[W.HANDLE]
 mutex=kernel.CreateMutexW(None,False,f'Local\\Server16NativeRoomAssets_{pid}')
 if not mutex:raise C.WinError(C.get_last_error())
 if C.get_last_error()==183:
  kernel.CloseHandle(mutex);print('Native room helper already running for this FIFA session');return
 # Commands use the native ION event bridge; no private-heap polling thread.
 marker=ROOT/'runtime/native_asset_helper_r46.pid';marker.write_text(f'{pid} {os.getpid()}\n')
 logfile=ROOT/'runtime/native_asset_helper_r46.log';logfile.write_text(f'Native room asset helper session game_pid={pid}\n');last=None
 while psutil.pid_exists(pid):
  try:
   snap=json.loads((GAME/'ModCarrerMode/runtime/career_fce_snapshot.json').read_text());stamp=(snap.get('pid'),snap.get('club'),snap.get('savePath'),snap.get('saveWriteTime100ns'),calendar_stamp(pid),tuple(tuple(r[:11]) for r in snap.get('fixtures',[]) if snap.get('club') in r[5:7]),(ROOT/'runtime/medical_native_capture.tsv').stat().st_mtime_ns if (ROOT/'runtime/medical_native_capture.tsv').exists() else 0)
   if snap.get('pid')==pid and stamp!=last:
    prepare();last=stamp
    with logfile.open('a') as f:f.write(f'PREPARED club={snap["club"]} native game assets, no save writes\n')
   publish_room_ready(pid)
  except Exception as e:
   with logfile.open('a') as f:f.write(type(e).__name__+': '+str(e)+'\n')
  time.sleep(2)
 with logfile.open('a') as f:f.write('SESSION_END\n')
if __name__=='__main__':
 if '--watch' in sys.argv:watch()
 else:prepare()
