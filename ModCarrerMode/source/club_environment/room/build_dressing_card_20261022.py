import portable_paths as portable
"""Local native career card and standalone room screen; never writes a save."""
from pathlib import Path
import sys,json,struct,copy,xml.etree.ElementTree as ET
import secrets,hashlib
ROOT=portable.ROOM
BANK=portable.BANK
import build_screen as b
from build_preview import Code
from build_package import read_nav,walk
from formats import AptFile,BigFile,Reader
from apt_actions import Actions
import native_roster_footer as roster_footer
GAME=portable.GAME;CLASS=('game','screens','career','server16','DressingRoom');FULL='.'.join(CLASS);PAGE=FULL.replace('.','/')
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav';FLOW='data/ui/nav/careermode/server16dressingroomflow.nav';BIG='data/ui/game/screens/career/server16/dressingroom.big'
HEADER_REVISION=69
def screen(payload=None,asset_reader=None):
 if payload is None:payload=json.loads((ROOT/'runtime/room_context_r46.json').read_text(encoding='utf8'))
 club=int(payload['club']);club_name=payload['club_name'];assert club>=0 and club_name
 import room_scene_ui_r52 as scene_ui
 previous=json.loads((ROOT/'runtime/room_control_scope.json').read_text(encoding='utf8')) if (ROOT/'runtime/room_control_scope.json').exists() else {}
 nonce=previous.get('nonce') if previous.get('club')==club else secrets.token_hex(8)
 scope={'pid':payload['pid'],'club':club,'nonce':nonce,'scenes':payload['scene_catalog']}
 (ROOT/'runtime/room_control_scope.json').write_text(json.dumps(scope,ensure_ascii=False,indent=2),encoding='utf8')
 (ROOT/'runtime/room_control_scope.txt').write_text(f'S16ROOMSCOPE 1 {payload["pid"]} {club} {nonce}\n')
 if asset_reader is None:asset_reader=lambda path:(GAME/path).read_bytes()
 b.CLASS=CLASS;b.FULL=FULL
 big=BigFile(BANK/'careertype.big');apt=AptFile(big);data=apt.data;root=Reader(big.entries['1'].data,20,8).ptr()
 def append(blob):data.extend(bytes(-len(data)%8));at=len(data);data.extend(blob);return at
 template=apt.root_frames[0][0];controls=[];chars=[];count,table=struct.unpack_from('<I4xQ',data,root+56)
 panel=AptFile(BigFile(GAME/'data/ui/game/components/careercomponents/careerhubwidget.big'));additions={}
 def addchar(blob):
  cid=count+len(chars);chars.append(append(blob));return cid
 def place(cid,depth,x,y,sx=1,sy=1,label=None,color=0xffffffff):
  raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if label else 14,depth,cid,sx,0,0,sy,x,y);struct.pack_into('<II',raw,44,color,0);struct.pack_into('<Q',raw,56,append(label.encode()+b'\0') if label else 0);return append(raw)
 def bitmap(dds):
  assert dds[:4]==b'DDS ';height,width=struct.unpack_from('<II',dds,12)
  tid=count+len(chars);raw=bytearray(panel.data[panel.characters[1].offset:panel.characters[1].offset+40]);struct.pack_into('<I',raw,32,tid);addchar(raw);additions[str(tid+1)]=dds
  sid=count+len(chars);raw=bytearray(panel.data[panel.characters[2].offset:panel.characters[2].offset+56]);struct.pack_into('<I',raw,16,tid<<16);struct.pack_into('<4fI',raw,32,0,0,width,height,sid);addchar(raw)
  geo=bytearray(panel.big.entries['3'].data[:96]);geo.extend(b''.join(struct.pack('<8f',x,y,0,0,0,0,0,0) for x,y in ((0,height),(0,0),(width,0),(width,0),(width,height),(0,height))))
  for off,value in ((0,len(geo)),(16,len(geo)-16),(32,len(geo)-32),(52,tid)):struct.pack_into('<I',geo,off,value)
  struct.pack_into('<6f',geo,64,1,0,0,1,0,0);additions[str(sid+1)]=bytes(geo);return sid,width,height
 crest_path=f'data/ui/imgassets/crest/light/l{club}.dds'
 try:crest=asset_reader(crest_path)
 except FileNotFoundError:crest=asset_reader(f'data/ui/imgassets/crest/dark/l{club}.dds')
 header_controls=[]
 symbol,width,height=bitmap(crest);scale=92/max(width,height);header_controls.append(place(symbol,1,109+(92-width*scale)/2,65+(110-height*scale)/2,scale,scale,'clubCrest'))
 for i,(name,value,x,y,w,h,size) in enumerate((('title','VESTIÁRIO',223,70,1260,58,46),('subtitle',club_name,223,132,1260,40,28))):
  raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,w,h);struct.pack_into('<If',raw,56,0xffffffff,size);struct.pack_into('<QQ',raw,80,append(value.encode('utf8')+b'\0'),0);cid=addchar(raw);header_controls.append(place(cid,i+2,x,y,label=name))
 # A bitmap/shape placement is not a scriptable MovieClip. Hide its enclosing
 # clip, so the original crest cannot remain under the roster's own header.
 raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);header_frame=append(struct.pack('<I4xQ',len(header_controls),append(struct.pack('<'+'Q'*len(header_controls),*header_controls))));struct.pack_into('<I4xQ',raw,32,1,header_frame);struct.pack_into('<Q',raw,48,0)
 controls.append(place(addchar(raw),1,0,0,label='roomHeader'))
 controls.extend(scene_ui.graphics(apt,data,append,addchar,place,bitmap,scope,asset_reader))
 newtable=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(chars),*chars));struct.pack_into('<I4xQ',data,root+56,count+len(chars),newtable)
 frame=append(struct.pack('<I4xQ',len(controls),append(struct.pack('<'+'Q'*len(controls),*controls))));struct.pack_into('<I4xQ',data,apt.characters[9].offset+32,1,frame)
 er=Reader(data,root+96,8);n=er.i();ex=er.ptr()
 for i in range(n):
  at=ex+i*16;old=Reader(data,at,8).text()
  if 'CareerType' in old:struct.pack_into('<Q',data,at,append(old.replace('game.screens.career.CareerType',FULL).encode()+b'\0'))
 blocks=list(Actions(apt).read_all().cache.values());dictionaries=[bytes(data[v[0].offset:v[0].end]) for v in blocks]
 a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
 for i,name in enumerate(CLASS[:-1]):
  parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
 def ctor(a):
  a.op(89);a.reg(2);a.op(118);a.op(93)
  a.do(R(1),'Initialize',FULL,None,True)
  a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
  a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'));a.set(R(1),'ready',False);a.do(R(1),'InitSceneControl')
  for name,value in (('title','VESTIÁRIO'),('subtitle',club_name)):a.set(P(T('roomHeader'),name),'text',value);a.do(M('ScreenManager'),'AddItemToAnimateIn',P(T('roomHeader'),name))
  a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
 a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
 scene_ui.methods(a,scope)
 def complete(a):
  a.when(T('ready'),lambda a:a.ret());a.set(R(1),'ready',True);a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
  a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
  a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')));a.do(M('HelpManager'),'Update')
 a.function('OnAnimateInComplete',0,complete)
 def exit(a):
  a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None);a.set(R(1),'onKeyDown',None)
  roster_footer.restore(a);a.do(R(1),'PublishRoster','room_close');a.do(PATH('Key'),'removeListener',R(1))
  a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
 a.function('OnExitScreen',0,exit);a.op(0);a.finish();a.align();reg=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
 for tag,target in ((apt.root_frames[0][1],start),(apt.root_frames[0][2],reg)):
  matches=[i for i in range(0,len(apt.entry.original)-7,8) if apt.entry.original[i:i+8]==struct.pack('<Q',tag[-1])];assert len(matches)==1;struct.pack_into('<Q',data,matches[0],target)
 out=ROOT/'package'/BIG;out.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,out,additions)
 parsed=AptFile(BigFile(out));actions=Actions(parsed).read_all();assert not actions.errors and FULL in parsed.exports
 (ROOT/'runtime/room_header.json').write_text(json.dumps({'revision':HEADER_REVISION,'pid':payload['pid'],'catalog_hash':hashlib.sha256(json.dumps(scope['scenes'],sort_keys=True).encode()).hexdigest(),'club':club,'name':club_name,'crest':crest_path,'help':{'ADVANCE':'Selecionar','BACK':'Voltar','LAS_LR':'Opções'},'bytes':out.stat().st_size},ensure_ascii=False,indent=2),encoding='utf8')
 return out
def stage():
 screen();xml=ET.fromstring((GAME/XML).read_text(encoding='utf8'));panel=xml.find('panel_3')
 assert not any(t.find('tileid').get('NAME')=='SERVER16_DRESSING_ROOM' for t in panel.findall('tile'))
 inbox=next(t for t in panel.findall('tile') if t.find('tileid').get('NAME')=='INBOX');inbox.find('settings').set('HEIGHT','204')
 tile=ET.SubElement(panel,'tile');ET.SubElement(tile,'tileid',tileid='901',NAME='SERVER16_DRESSING_ROOM',PARAM='')
 ET.SubElement(tile,'settings',FILE_PATH='TILE',WIDTH='846',HEIGHT='204',X='109',Y='492');ET.SubElement(tile,'main_tile',FG_PATH='',BG_ICON='TeamSheets_Small',DESTINATION='Server16EnterDressingRoom')
 ET.SubElement(tile,'number_of_subtiles',LENGTH='0');ET.SubElement(tile,'data',ID='TITLE',TYPE='title',PARAM='VESTIÁRIO 3D',TRANSLATE='FALSE',FORMAT='HS')
 ET.SubElement(tile,'data',ID='S16_ROOM_DESCRIPTION',TYPE='text',PARAM='Entrar no ambiente do clube',TRANSLATE='FALSE',FORMAT='SM',WIDTH='790',HEIGHT='60',X='18',Y='76')
 panel.find('entries').set('numberoftiles',str(len(panel.findall('tile'))))
 rects=[]
 for t in panel.findall('tile'):
  s=t.find('settings');x,y,w,h=map(int,(s.get(k) for k in ('X','Y','WIDTH','HEIGHT')))
  for ox,oy,ow,oh in rects:assert min(x+w,ox+ow)<=max(x,ox) or min(y+h,oy+oh)<=max(y,oy)
  rects.append((x,y,w,h))
 nav=read_nav((GAME/NAV).read_text(encoding='utf8'));host=next(v for v in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in v.get('transitions',[])))
 host['transitions'].append({'event':'Server16EnterDressingRoom','targets':['Server16DressingRoom']})
 owner=next(v for v in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in v.get('states',[])))
 owner['states'].append({'name':'Server16DressingRoom','type':'external','file':'/careerMode/server16DressingRoomFlow.nav','outputs':{'Back':'MainMenuHub','back':'MainMenuHub'}})
 flow={'name':'Server16DressingRoomFlow','initial':{'targets':['Room']},'states':[{'name':'Room','onEnter':[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]]],
 'onExit':[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']]],'transitions':[{'event':e,'targets':['Back'],'actions':[['executeCMAction',['ReturnToHubFromCalendar']]]} for e in ('Back','back')]}]}
 flow['states'][0]['transitions'].append({'event':'Server16RefreshDressingRoom','actions':[['unloadView',['screen']],['loadView',['screen',PAGE]]]})
 from club_browser.room_players import integrate
 flow=integrate(flow)
 for rel,data in {XML:ET.tostring(xml,encoding='utf-8',xml_declaration=True),NAV:(json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8'),FLOW:(json.dumps(flow,indent=2)+'\n').encode()}.items():
  p=ROOT/'package'/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 # Shared features remain represented after inserting only this card/branch.
 assert any(v.get('name')=='Server16MatchPreview' for v in walk(nav))
 assert any(t.find('tileid').get('NAME')=='SERVER16_BANK_LOANS' for t in panel.findall('tile'))
 print('Staged native card, separate view and Back route. No live files changed.')
if __name__=='__main__':stage()
