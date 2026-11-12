"""Bounded native APT data loader and interactive coach market controller."""
from pathlib import Path
import hashlib,json
import bank_art
import build_screen as b
from build_preview import Code
import native_screen as native
import manager_layout
import profile_layout
import profile_controller,profile_art
import asset_cache,club_portraits,prepared_catalogue,template_renderer,market_footer,club_history_ui,live_payload
from profile_request import RESUME
from manager_layout import TAB_W,TAB_STEP,assets_for,scenes_for,stars,TABS,MAIN,club_xy,free_xy,move_xy,PAGE_SIZE,MOVE_TOP,MOVE_HEIGHT,PAGER_Y

CLASS=('game','screens','career','server16','ManagerMarket');FULL='.'.join(CLASS)
UI_SIGNATURE=hashlib.sha256(Path(__file__).read_bytes()+b''.join(Path(m.__file__).read_bytes() for m in (manager_layout,profile_layout,profile_controller,profile_art,asset_cache,club_portraits,prepared_catalogue,template_renderer,market_footer,club_history_ui,live_payload,native,b,bank_art))).hexdigest()
GEOMETRY_SIGNATURE=hashlib.sha256(b''.join(Path(m.__file__).read_bytes() for m in (manager_layout,profile_layout,profile_art,club_history_ui,native,b,bank_art))).hexdigest()
R=b.reg;T=b.this;P=b.prop;EQ=b.equal;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
def arr(v):return ('array',tuple(v))

def packed_array(values,schemas):
 values=list(values)
 if not values or any(not (type(v) in (str,int,float) or v==arr([])) or '\x1c' in str(v) for v in values):return arr(values)
 schema=tuple('a' if v==arr([]) else 's' if type(v) is str else 'i' if type(v) is int else 'n' for v in values)
 index=schemas.setdefault(schema,len(schemas))
 return CALL(R(1),'ReadRecord'+str(index),'\x1c'.join('' if v==arr([]) else str(v) for v in values))

def profile_payload(person):
 if person.get('profilePending'):return ''
 # Store data as strings in the APT constant pool, not 2,000 generated
 # functions. Only the selected CV is decoded by the bounded controller.
 def flat(values):
  return '\x1f'.join(('n'+str(int(v) if isinstance(v,bool) else v)) if type(v) in (int,float,bool) else 's'+str(v or '').replace('\x1d',' ').replace('\x1e',' ').replace('\x1f',' ') for v in values)
 def rows(values):return '\x1e'.join(flat(row) for row in values)
 return '\x1d'.join((flat(person['history']),flat(person['titles']),rows(person.get('spellCards',[])),rows(person.get('titleCards',[])),flat(person.get('overview',[0]*14+['','','',-1,'',''])),flat(person.get('visualData',['']*27)),rows(person.get('yearCards',[]))))
def ix(a,i):return ('index',a,i)
def add(a,c):return ('bin',71,a,c)
def sub(a,c):return ('bin',11,a,c)
def lt(a,c):return ('bin',72,a,c)
def mul(a,c):return ('bin',12,a,c)
def both(a,c):return ('bin',16,a,c)
def either(a,c):return ('bin',17,a,c)
def div(a,c):return ('bin',13,a,c)
def floor(v):return CALL(PATH('Math'),'floor',v)
def clamp(v,lo,hi):return CALL(PATH('Math'),'max',lo,CALL(PATH('Math'),'min',v,hi))
def wrap(v,size):return ('bin',63,add(v,size),size)
def loop(a,index,count,body):
 a.set(R(1),index,0);start,end=a.uid(),a.uid();a.label(start);a.expr(('not',lt(T(index),count)));a.branch(end);body(a);a.set(R(1),index,add(T(index),1));a.branch(start,False);a.label(end)

def script_factory(model,assets):
 years=sorted({int(m[0])//100 for m in model.get('months',[])}) or [model['date']//10000]
 initial_country=model.get('initialCountry',0)+1
 mine_country=(model.get('countries') or [dict(name='')])[initial_country-1]['name']
 initial_league=next((i+1 for i,l in enumerate([l for l in model['leagues'] if l['country']==mine_country]) if l['id']==model.get('initialLeague')),0)
 def script(data,dictionaries,scenes):
  b.CLASS=CLASS;b.FULL=FULL;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
  for i,name in enumerate(CLASS[:-1]):
   parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
  # Hide the catalogue artwork in bounded frames as well. Thousands of crest
  # variants must not turn the final Ready callback into one giant AVM action.
  operations=[('hide','scene'+str(i),n['name']) for i,s in enumerate(scenes) for n in s['nodes'] if n['type']=='image' and n.get('name') and not n.get('native_group')]
  for key,rows in (('clubs',model['clubRows']),('free',model['freeRows']),('moves',model['moveRows']),('hires',model['hireRows'])):operations.extend(('row',key,row) for row in rows)
  operations.extend(('profile','people',p) for p in model['people'])
  history_clubs=model.get('historyClubRows',[[r[0],r[4],int(r[4].split('_')[1]),r[8]] for r in model['clubRows']])
  operations.extend(('row','historyClubs',[native.fit(r[0],478,27),r[1],r[2],r[3]]) for r in history_clubs)
  operations.extend(('row','timelineRows',r) for r in (model.get('clubHistory') or {}).get('rows',[]))
  operations.extend(('row','leagues',[l['id'],l['name'],l['country'],l['level'],l['image'],native.fit(l['country']+' · '+l['name'],260,18)]) for l in model['leagues'])
  operations.extend(('row','countries',[c['name'],c['flag']]) for c in model.get('countries',[]) or [dict(name='Aguardando carreira',flag='flag_0')])
  operations.extend(('row','months',m) for m in model.get('months',[]) or [[202601,'Janeiro 2026']]);operations.extend(('value','nations',v) for v in model['nationalities'])
  batches=[operations[i:i+128] for i in range(0,len(operations),128)] or [[]]
  def ctor(a):
   a.op(89);a.reg(2);a.op(118);a.op(93);a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')));a.do(R(1),'Initialize',FULL,None,True)
   a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'screenReady',False);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
   defaults=dict(tab=0,page=0,country=model.get('initialCountry',0),league=model.get('initialLeague',0),movementCountry=initial_country,movementLeague=initial_league,yearMenu=False,dragScroll=0,month=model.get('initialMonth',0),hirePage=0,movePage=0,age=0,nation=0,profile=False,person=0,profileTab=0,profileVenue=0,profileMediaPerson=-1,warmPerson=-1,warmFocus=-1,warmFrames=0,historyPage=0,focus=0,frames=0,marketEnabled=bool(model.get('settings',{}).get('enabled',True)),cadenceIndex=(1,7,30).index(model.get('settings',{}).get('cadence',1)),settingsSerial=0,settingsPending=False,clubTimeline=bool(model.get('clubHistory')),historyPending=False,timelinePage=0,mouseIsDown=False,pagerInputFrame=-100,pagerInputCommand=-1,monthInputFrame=-100,monthInputCommand=-1)
   defaults.update(historyLoadedClub=(model.get('clubHistory') or {}).get('club',0),historyClubName=(model.get('clubHistory') or {}).get('name','Clube'),historyClubCrest=(model.get('clubHistory') or {}).get('crest',''))
   defaults.update(model.get('resume',{}))
   for key,value in defaults.items():a.set(R(1),key,value)
   a.set(R(1),'profileRequested',arr([]))
   for key in ('clubs','free','moves','hires','people','leagues','countries','months','nations','rendered','profileLoaded','historyClubs','timelineRows'):a.set(R(1),key,arr([]))
   a.set(R(1),'dataStep',0);a.set(R(1),'dataReady',False);a.set(R(1),'onEnterFrame',T('DataFrame'));a.do(PATH('Mouse'),'addListener',R(1))
  a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
  def decode_fields(a):
   a.when(EQ(R(2),''),lambda a:a.ret(arr([])))
   a.set(R(1),'decodedFields',CALL(R(2),'split','\x1f'))
   def decode(a):
    value=ix(T('decodedFields'),T('fieldIndex'));body=CALL(value,'substr',1)
    a.expr(T('decodedFields'));a.expr(T('fieldIndex'))
    a.when(EQ(CALL(value,'charAt',0),'n'),lambda a:a.expr(mul(body,1)),lambda a:a.expr(body));a.op(79)
   loop(a,'fieldIndex',P(T('decodedFields'),'length'),decode);a.ret(T('decodedFields'))
  a.function('DecodeFields',1,decode_fields)
  def decode_rows(a):
   a.set(R(1),'decodedRows',arr([]));a.when(EQ(R(2),''),lambda a:a.ret(T('decodedRows')))
   a.set(R(1),'encodedRows',CALL(R(2),'split','\x1e'))
   loop(a,'profileRowIndex',P(T('encodedRows'),'length'),lambda a:a.do(T('decodedRows'),'push',CALL(R(1),'DecodeFields',ix(T('encodedRows'),T('profileRowIndex')))))
   a.ret(T('decodedRows'))
  a.function('DecodeRows',1,decode_rows)
  def ensure_profile(a):
   if model.get('lazyProfiles'):
    a.when(('not',ix(T('profileRequested'),T('person'))),lambda a:(a.do(R(1),'RequestProfile',T('person')),a.expr(T('profileRequested')),a.expr(T('person')),a.expr(True),a.op(79)))
   a.when(ix(T('profileLoaded'),T('person')),lambda a:a.ret())
   if model.get('lazyProfiles'):a.when(EQ(ix(ix(T('people'),T('person')),28),''),lambda a:a.ret())
   target=ix(T('people'),T('person'));a.set(R(1),'profileParts',CALL(ix(target,28),'split','\x1d'))
   for col,part,nested in ((7,0,False),(8,1,False),(24,2,True),(25,3,True),(23,4,False),(26,5,False),(27,6,True)):
    a.expr(target);a.expr(col);a.expr(CALL(R(1),'DecodeRows' if nested else 'DecodeFields',ix(T('profileParts'),part)));a.op(79)
   a.expr(T('profileLoaded'));a.expr(T('person'));a.expr(True);a.op(79)
  a.function('EnsureProfile',0,ensure_profile)
  def request_profile(a):
   wire=add('S16MGRP1|'+model.get('profileToken','')+'|',R(2))
   for key in RESUME:wire=add(add(wire,'|'),T(key))
   wire=add(wire,'|END')
   a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ManagerProfile',wire)
  a.function('RequestProfile',1,request_profile)
  def received_profile(a,payload):
   person=P(payload,'person');target=ix(T('people'),person)
   a.expr(target);a.expr(28);a.expr(P(payload,'encoded'));a.op(79)
   a.expr(T('profileLoaded'));a.expr(person);a.expr(False);a.op(79)
   a.set(R(1),'profileMediaPerson',person);a.set(T('profileHolder'),'_visible',True);a.set(T('profileHolder'),'_alpha',100);a.do(R(1),'EnsureProfile');a.do(R(1),'Refresh')
   # One completion receipt, after actual mounted delivery, through the
   # existing read-only mailbox (-1 never performs a profile/world change).
   wire='S16MGRP1|'+model.get('profileToken','')+'|-1'
   for key in RESUME:wire=add(add(wire,'|'),T('person') if key=='focus' else T(key))
   a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ManagerProfile',add(wire,'|END'))
  live_payload.emit(a,'profile','managerprofile',lambda d:both(both(EQ(P(d,'kind'),'profile'),EQ(P(d,'token'),model.get('profileToken',''))),both(EQ(P(d,'person'),T('person')),EQ(P(d,'date'),model['date']))),received_profile,interval=3,parent=None,art_host=T('scene1') if model.get('lazyProfiles') else None,artwork=bool(model.get('lazyProfiles')),filename=add('managerprofile_'+model.get('profileToken','')[:16]+'_',add(T('person'),'_')) if model.get('lazyProfiles') else None)
  schemas={}
  for batch_index,batch in enumerate(batches):
   def append_batch(a,batch=batch):
    for kind,key,value in batch:
     if kind=='hide':a.set(P(T(key),value),'_visible',False)
     elif kind=='reset':a.set(R(1),key,arr([]))
     elif kind=='profile':a.do(T('people'),'push',packed_array([value['name'],*value['details'],arr([]),arr([]),value['head'],value['reputation'],value['nationality'],value.get('flag','flag_0'),value['age'],value.get('style','Equilibrado'),value.get('formation','Não informada') if value.get('formation')!='Não informada' else 'Formação pendente',value.get('freeDays',''),f"{int(value['salary']):,}".replace(',','.'),value.get('secondaryStyle',''),native.fit(value['name'],470,26),native.fit(value['nationality'],293,18),native.fit(value['nationality'],445,19),native.fit(value['nationality'],259,17),arr([]),arr([]),arr([]),arr([]),arr([]),profile_payload(value)],schemas))
     elif kind=='value' and key in ('loadingSpells','loadingAwards'):a.do(T(key),'push',arr(value))
     else:
      if kind=='row' and key in ('clubs','moves','hires'):
       value=list(value);value[0]=native.fit(value[0],128 if key=='clubs' else 171,17 if key=='clubs' else 20);value[1]=native.fit(value[1],327 if key=='clubs' else 270,24 if key=='clubs' else 21)
      a.do(T(key),'push',packed_array(value,schemas) if kind=='row' else value)
   a.function('DataBatch'+str(batch_index),0,append_batch)
  # Split strings in the native VM; convert only the schema's numeric fields.
  # This avoids emitting a full AVM expression for every field of 2,000 coaches
  # without replacing it with a costly interpreted loop for every string.
  for schema,index in schemas.items():
   def read_record(a,schema=schema):
    a.set(R(1),'recordFields',CALL(R(2),'split','\x1c'))
    for column,kind in enumerate(schema):
     if kind=='s':continue
     a.expr(T('recordFields'));a.expr(column)
     a.expr(arr([]) if kind=='a' else floor(mul(ix(T('recordFields'),column),1)) if kind=='i' else mul(ix(T('recordFields'),column),1));a.op(79)
    a.ret(T('recordFields'))
   a.function('ReadRecord'+str(index),1,read_record)
  def data_frame(a):
   a.when(('not',P(T('scene1'),'profileCaption')),lambda a:a.ret())
   for i in (0,1,3,4,5,6,7):a.set(T('scene'+str(i)),'_visible',False)
   a.set(T('scene2'),'_visible',True);a.set(P(T('scene2'),'progress'),'text',add('Preparando os dados: ',add(floor(div(mul(T('dataStep'),100),len(batches))),'%')))
   # Two bounded dispatches per frame; each inner callback retains the original
   # conservative 128-value stack budget. Never build a giant literal array.
   # Legacy APT member lookup can fold case: DataStep would be shadowed by
   # the numeric dataStep property and stop initialization before SCREEN_READY.
   a.do(R(1),'AdvanceDataChunk');a.when(('not',T('dataReady')),lambda a:a.do(R(1),'AdvanceDataChunk'))
  def data_step(a):
   for i in range(len(batches)):
    def step(a,i=i):
     a.do(R(1),'DataBatch'+str(i));a.set(R(1),'dataStep',i+1)
     if i==len(batches)-1:
      for key in ('loadingHistory','loadingTitles','loadingSpells','loadingAwards'):a.set(R(1),key,None)
      a.set(R(1),'dataReady',True);a.set(R(1),'onEnterFrame',T('Wait'));a.do(R(1),'Wait')
     a.ret()
    a.when(EQ(T('dataStep'),i),step)
  a.function('AdvanceDataChunk',0,data_step);a.function('DataFrame',0,data_frame)
  commands=[[int(x['target']) for x in s['actions']] for s in scenes]
  def wait(a):
   a.when(either(('not',T('dataReady')),T('inputBound')),lambda a:a.ret());a.when(('not',P(T('scene1'),'profileCaption')),lambda a:a.ret());a.set(R(1),'inputBound',True)
   date=str(model['date']);meta=model['clubName']+' · '+date[6:8]+'/'+date[4:6]+'/'+date[:4]+' · Salários em moeda da carreira' if model.get('ready') else 'Aguardando os dados da carreira aberta...'
   for i in (*MAIN,7):a.set(P(T('scene'+str(i)),'careerMeta'),'text',meta)
   for i,s in enumerate(scenes):
    for j,action in enumerate(s['actions']):
     btn=P(T('scene'+str(i)),'action'+str(j));a.set(btn,'owner',R(1));a.set(btn,'code',int(action['target']));a.set(btn,'onRelease',None);a.set(btn,'onRollOver',None)
     if 200<=int(action['target'])<=203:
      a.set(btn,'onPress',T('ScrollPress'));a.set(btn,'onRelease',T('ScrollRelease'));a.set(btn,'onReleaseOutside',T('ScrollRelease'))
   a.set(R(1),'onEnterFrame',T('ScrollFrame'));a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')));a.do(R(1),'Refresh');a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
  a.function('Wait',0,wait)
  def complete(a):
   a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True);a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
  a.function('OnAnimateInComplete',0,complete)
  def reveal(a):a.when(R(2),lambda a:(a.set(R(2),'_visible',True),a.set(R(2),'_alpha',100),a.set(R(2),'_x',R(3)),a.set(R(2),'_y',R(4)),a.do(T('rendered'),'push',R(2))))
  a.function('Reveal',3,reveal)
  groups=sorted({n['native_group'] for s in scenes for n in s['nodes'] if n.get('native_group')})
  def find_art(a):
   a.when(ix(R(2),R(3)),lambda a:a.ret(ix(R(2),R(3))))
   media=ix(P(P(P(R(2),'profilePayload'),'view'),'scene0'),R(3))
   a.when(P(R(2),'profilePayload'),lambda a:a.when(media,lambda a:a.ret(media)))
   for group in groups:
    a.when(P(R(2),group),lambda a,group=group:a.when(ix(P(R(2),group),R(3)),lambda a,group=group:a.ret(ix(P(R(2),group),R(3)))))
   a.ret(None)
  a.function('FindArtwork',2,find_art)
  def show(a,root,name,x,y):a.do(R(1),'Reveal',CALL(R(1),'FindArtwork',root,name),x,y)
  def field(a,root,name,value,visible=True):a.set(P(root,name),'_visible',visible);a.when(visible,lambda a:a.set(P(root,name),'text',value))
  def portrait(a,root,prefix,r,slot,x,y):
   key=ix(r,5);a.when(EQ(key,'head_NOTFOUND_DEFAULT'),lambda a:show(a,root,prefix+'fallback'+str(slot),x,y),lambda a:show(a,root,add(prefix,key),x,y))
  def rating(a,root,prefix,r,slot,x,y):show(a,root,add(prefix+'rating'+str(slot)+'_',ix(r,6)),x,y)
  def nationality(a,root,prefix,p,slot,x,y):show(a,root,add(prefix+'flag'+str(slot)+'_',ix(p,12)),x,y)
  def pages(a,rows,key,size):
   a.set(R(1),key+'Count',CALL(PATH('Math'),'max',1,CALL(PATH('Math'),'ceil',div(P(rows,'length'),size))));a.set(R(1),key,clamp(T(key),0,sub(T(key+'Count'),1)))
  def pagetext(key,count):return add(add(add('Página ',add(T(key),1)),add(' de ',T(key+'Count'))),add(' · ',count))
  def profile(a):
   a.do(R(1),'EnsureProfile')
   profile_controller.emit(a,scenes,R=R,T=T,P=P,ix=ix,add=add,mul=mul,lt=lt,EQ=EQ,both=both,either=either,clamp=clamp,div=div,CALL=CALL,PATH=PATH,field=field,show=show)
  def dots(a,root,key,count,prefix,start):
   for dot in range(16):
    for state in ('On','Off'):
     active=EQ(floor(div(T(key),4)) if prefix else T(key),dot)
     a.when(both(both(lt(dot,count),lt(count,17)),active if state=='On' else ('not',active)),lambda a,dot=dot,state=state:show(a,root,prefix+'pageDot'+state+str(dot),start+dot*19,PAGER_Y+2))
  def clubs(a):
   root=T('scene0');a.set(R(1),'leagueRows',arr([]))
   loop(a,'i',P(T('leagues'),'length'),lambda a:a.when(EQ(ix(ix(T('leagues'),T('i')),2),ix(ix(T('countries'),T('country')),0)),lambda a:a.do(T('leagueRows'),'push',ix(T('leagues'),T('i')))))
   a.set(R(1),'leagueIndex',0);loop(a,'i',P(T('leagueRows'),'length'),lambda a:a.when(EQ(ix(ix(T('leagueRows'),T('i')),0),T('league')),lambda a:a.set(R(1),'leagueIndex',T('i'))))
   l=ix(T('leagueRows'),T('leagueIndex'));a.set(R(1),'filtered',arr([]));loop(a,'i',P(T('clubs'),'length'),lambda a:a.when(EQ(ix(ix(T('clubs'),T('i')),8),T('league')),lambda a:a.do(T('filtered'),'push',ix(T('clubs'),T('i')))))
   pages(a,T('filtered'),'page',PAGE_SIZE);field(a,root,'countryName',ix(ix(T('countries'),T('country')),0));field(a,root,'countryCount',add(add(add(T('country'),1),' / '),P(T('countries'),'length')))
   show(a,root,add('country_',ix(ix(T('countries'),T('country')),1)),151,365);show(a,root,add('league_',ix(l,4)),147,511)
   field(a,root,'leagueName',ix(l,1));field(a,root,'leagueCount',add(add(add(T('leagueIndex'),1),' / '),P(T('leagueRows'),'length')));field(a,root,'leagueLevel',add(ix(l,3),'ª divisão'));field(a,root,'clubCount',add(P(T('filtered'),'length'),' clubes'))
   for i in range(PAGE_SIZE):
    idx=add(mul(T('page'),PAGE_SIZE),i);r=ix(T('filtered'),idx);p=ix(T('people'),ix(r,7));present=lt(idx,P(T('filtered'),'length'));x,y=club_xy(i)
    for name,value in (('club',ix(r,0)),('coach',ix(r,1)),('nationality',ix(p,20)),('tenure',ix(r,2)),('amount',ix(p,17))):field(a,root,name+str(i),value,present)
    def row(a,i=i,r=r,p=p,x=x,y=y):
     show(a,root,add('c_',ix(r,4)),x+551,y+13);portrait(a,root,'c_',r,i,x+10,y+14);rating(a,root,'c_',r,i,x+174,y+84);nationality(a,root,'c_',p,i,x+174,y+58)
    a.when(present,row)
   dots(a,root,'page',T('pageCount'),'',1100)
   field(a,root,'pageText',pagetext('page',add(P(T('filtered'),'length'),' clubes')));field(a,root,'empty','Nenhum clube nesta liga.' if model.get('ready') else 'Preparando o mercado da carreira aberta...',EQ(P(T('filtered'),'length'),0))
  def movements(a):
   root=T('scene3');month=ix(ix(T('months'),T('month')),0);field(a,root,'monthName',ix(ix(T('months'),T('month')),1));field(a,root,'yearName',floor(div(month,100)))
   field(a,root,'movementCountry','Todos os países');a.when(lt(0,T('movementCountry')),lambda a:field(a,root,'movementCountry',ix(ix(T('countries'),sub(T('movementCountry'),1)),0)))
   a.set(R(1),'movementLeagues',arr([]))
   loop(a,'i',P(T('leagues'),'length'),lambda a:a.when(either(EQ(T('movementCountry'),0),EQ(ix(ix(T('leagues'),T('i')),2),ix(ix(T('countries'),sub(T('movementCountry'),1)),0))),lambda a:a.do(T('movementLeagues'),'push',ix(T('leagues'),T('i')))))
   a.set(R(1),'movementLeagueId',0);field(a,root,'movementLeague','Todas as ligas')
   a.when(lt(0,T('movementLeague')),lambda a:(a.set(R(1),'movementLeagueId',ix(ix(T('movementLeagues'),sub(T('movementLeague'),1)),0)),field(a,root,'movementLeague',ix(ix(T('movementLeagues'),sub(T('movementLeague'),1)),1))))
   for source,filtered in (('hires','monthHires'),('moves','monthMoves')):
    a.set(R(1),filtered,arr([]));loop(a,'i',P(T(source),'length'),lambda a,source=source,filtered=filtered:a.when(both(both(EQ(floor(div(ix(ix(T(source),T('i')),9),100)),month),either(EQ(T('movementLeague'),0),EQ(ix(ix(T(source),T('i')),8),T('movementLeagueId')))),either(EQ(T('movementCountry'),0),EQ(ix(ix(T(source),T('i')),11),ix(ix(T('countries'),sub(T('movementCountry'),1)),0)))),lambda a:a.do(T(filtered),'push',ix(T(source),T('i')))))
   for panel,(rows,key,prefix,status) in enumerate((('monthHires','hirePage','h_','Contratado'),('monthMoves','movePage','d_','Demitido'))):
    a.set(R(1),key+'Count',CALL(PATH('Math'),'max',1,sub(P(T(rows),'length'),3)));a.set(R(1),key,clamp(T(key),0,sub(T(key+'Count'),1)));field(a,root,prefix+'count',add(P(T(rows),'length'),' contratações' if panel==0 else ' saídas'));field(a,root,prefix+'empty','Nenhuma '+('contratação' if panel==0 else 'saída')+' neste mês.',EQ(P(T(rows),'length'),0));field(a,root,prefix+'page',add(add(add(add(T(key),1),'–'),CALL(PATH('Math'),'min',add(T(key),4),P(T(rows),'length'))),add(' de ',P(T(rows),'length'))));show(a,root,prefix+'scrollTrack',96+panel*870+847,MOVE_TOP);show(a,root,prefix+'scrollThumb',96+panel*870+847,MOVE_TOP);a.set(P(root,prefix+'scrollThumb'),'_height',div(MOVE_HEIGHT*4,CALL(PATH('Math'),'max',4,P(T(rows),'length'))));a.set(P(root,prefix+'scrollThumb'),'_y',add(MOVE_TOP,mul(div(T(key),CALL(PATH('Math'),'max',1,sub(T(key+'Count'),1))),sub(MOVE_HEIGHT,div(MOVE_HEIGHT*4,CALL(PATH('Math'),'max',4,P(T(rows),'length')))))))
    dots(a,root,key,CALL(PATH('Math'),'ceil',div(P(T(rows),'length'),4)),prefix,366+panel*870)
    a.when(EQ(P(T(rows),'length'),0),lambda a,prefix=prefix:field(a,root,prefix+'page',''))
    for j in range(4):
     i=panel*4+j;idx=add(T(key),j);r=ix(T(rows),idx);p=ix(T('people'),ix(r,7));present=lt(idx,P(T(rows),'length'));x,y=move_xy(i)
     for name,value in (('club',ix(r,0)),('coach',ix(r,1)),('nationality',ix(p,22)),('date',ix(r,10)),('status',status if panel==0 else ix(r,3))):field(a,root,name+str(i),value,present)
     if panel==0:a.when(both(present,lt(12,P(r,'length'))),lambda a,i=i,r=r:field(a,root,'status'+str(i),ix(r,12),True))
     def row(a,j=j,r=r,p=p,x=x,y=y,prefix=prefix):
      show(a,root,add(prefix,ix(r,4)),x+25,y+14);portrait(a,root,prefix,r,j,x+284,y+10);rating(a,root,prefix,r,j,x+101,y+61);nationality(a,root,prefix,p,j,x+374,y+47)
     a.when(present,row)
  def frees(a):
   root=T('scene4');a.set(R(1),'filtered',arr([]))
   def filterrow(a):
    r=ix(T('free'),T('i'));age=ix(r,9)
    ageok=either(EQ(T('age'),0),either(both(EQ(T('age'),1),both(lt(-1,age),lt(age,41))),either(both(EQ(T('age'),2),both(lt(40,age),lt(age,56))),either(both(EQ(T('age'),3),both(lt(55,age),lt(age,71))),either(both(EQ(T('age'),4),lt(70,age)),both(EQ(T('age'),5),lt(age,0)))))))
    natok=either(EQ(T('nation'),0),EQ(ix(r,10),ix(T('nations'),T('nation'))));a.when(both(both(ageok,natok),EQ(ix(r,11),1)),lambda a:a.do(T('filtered'),'push',r))
   loop(a,'i',P(T('free'),'length'),filterrow);pages(a,T('filtered'),'page',PAGE_SIZE)
   field(a,root,'natValue',add('Nacionalidade: ',ix(T('nations'),T('nation'))))
   for nation in model['nationalities']:
    flag=next((p.get('flag','flag_0') for p in model['people'] if p.get('nationality')==nation),'flag_0')
    a.when(EQ(ix(T('nations'),T('nation')),nation),lambda a,flag=flag:show(a,root,'filter_'+flag,1200,279))
   for i in range(PAGE_SIZE):
    idx=add(mul(T('page'),PAGE_SIZE),i);r=ix(T('filtered'),idx);p=ix(T('people'),ix(r,7));present=lt(idx,P(T('filtered'),'length'));x,y=free_xy(i)
    for name,value in (('coach',ix(p,19)),('nationality',ix(p,21)),('freeDays',ix(p,16)),('age',add(ix(p,13),' anos') if model.get('ready') else ''),('style',ix(p,14)),('formation',ix(p,15)),('status','Livre no mercado')):field(a,root,name+str(i),value,both(present,lt(-1,ix(p,13))) if name=='age' else present)
    a.when(present,lambda a,i=i,r=r,p=p,x=x,y=y:(portrait(a,root,'f_',r,i,x+16,y+12),rating(a,root,'f_',r,i,x+14,y+153),nationality(a,root,'f_',p,i,x+170,y+64)))
   dots(a,root,'page',T('pageCount'),'',1100)
   field(a,root,'pageText',pagetext('page',add(P(T('filtered'),'length'),' técnicos · Reputação da maior para a menor')));field(a,root,'empty','Nenhum técnico para os filtros selecionados.',EQ(P(T('filtered'),'length'),0))
  def refresh_settings(a):
   root=T('scene5');field(a,root,'marketState',CALL(R(1),'MarketStateLabel'));field(a,root,'cadenceName',ix(arr(('Diário','Semanal','Mensal')),T('cadenceIndex')));field(a,root,'cadenceHelp',ix(arr(('Decisões avaliadas todos os dias, como no padrão atual.','Decisões agrupadas por semana do calendário da carreira.','Decisões agrupadas por mês do calendário da carreira.')),T('cadenceIndex')))
   a.when(T('marketEnabled'),lambda a:show(a,root,'marketSwitchOn',1575,407),lambda a:show(a,root,'marketSwitchOff',1575,407));field(a,root,'settingsFeedback',CALL(R(1),'SettingsFeedback'))
  a.function('MarketStateLabel',0,lambda a:a.when(T('marketEnabled'),lambda a:a.ret('Ativo'),lambda a:a.ret('Desativado')))
  a.function('SettingsFeedback',0,lambda a:a.when(T('settingsPending'),lambda a:a.ret('Salvando preferências...'),lambda a:a.ret(model.get('settingsError') or 'Preferências salvas para este usuário.')))
  a.function('RefreshSettings',0,refresh_settings)
  def request_settings(a):
   a.set(R(1),'settingsSerial',add(T('settingsSerial'),1));a.set(R(1),'settingsPending',True)
   wire=add('S16MGRS1|'+model.get('profileToken','')+'|',mul(T('marketEnabled'),1));wire=add(add(wire,'|'),T('cadenceIndex'));wire=add(add(wire,'|'),T('settingsSerial'));wire=add(wire,'|END');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ManagerSettings',wire)
  a.function('RequestSettings',0,request_settings)
  club_history_ui.emit(a,model,scenes,R=R,T=T,P=P,ix=ix,add=add,sub=sub,mul=mul,div=div,lt=lt,EQ=EQ,both=both,clamp=clamp,CALL=CALL,PATH=PATH,arr=arr,loop=loop,field=field,show=show,pages=pages,dots=dots,club_xy=club_xy)
  a.function('DotState',1,lambda a:a.when(EQ(T('page'),R(2)),lambda a:a.ret('On'),lambda a:a.ret('Off')))
  a.function('RefreshClubs',0,clubs);a.function('RefreshMovements',0,movements);a.function('RefreshFree',0,frees);a.function('RefreshProfile',0,profile)
  def refresh(a):
   a.when(T('profileHolder'),lambda a:a.set(T('profileHolder'),'_alpha',0))
   loop(a,'hidden',P(T('rendered'),'length'),lambda a:a.set(ix(T('rendered'),T('hidden')),'_visible',False));a.set(R(1),'rendered',arr([]))
   for i in range(len(scenes)):a.set(T('scene'+str(i)),'_visible',False)
   if not model.get('ready'):
    a.set(T('scene2'),'_visible',True);a.set(P(T('scene2'),'progress'),'text','Preparando os dados da carreira aberta. Aguarde...');a.do(M('HelpManager'),'Update');market_footer.apply(a);a.ret();return
   def show_profile(a):
    if model.get('lazyProfiles'):
     a.do(R(1),'EnsureProfile')
     a.when(('not',ix(T('profileLoaded'),T('person'))),lambda a:(a.set(T('scene2'),'_visible',True),a.set(P(T('scene2'),'progress'),'text',add('Consultando histórico de ',ix(ix(T('people'),T('person')),0))),a.do(M('HelpManager'),'Update'),market_footer.apply(a),a.ret()))
    a.when(EQ(T('profileMediaPerson'),T('person')),lambda a:a.set(T('profileHolder'),'_alpha',100))
    a.set(T('scene1'),'_visible',True);a.do(R(1),'RefreshProfile');a.do(M('HelpManager'),'Update');market_footer.apply(a);a.ret()
   a.when(T('profile'),show_profile)
   def show_timeline(a):
    a.when(T('historyPending'),lambda a:(a.set(T('scene2'),'_visible',True),field(a,T('scene2'),'progress','Consultando os técnicos e títulos deste clube...'),a.ret()))
    a.set(T('scene7'),'_visible',True);a.do(R(1),'RefreshClubTimeline');a.do(M('HelpManager'),'Update');market_footer.apply(a);a.ret()
   a.when(T('clubTimeline'),show_timeline)
   root=ix(R(1),add('scene',ix(arr(MAIN),T('tab'))));a.set(root,'_visible',True);a.set(R(1),'mainClip',root)
   for tab in range(len(TABS)):show(a,root,'tabMark'+str(tab),96+tab*TAB_STEP,203);a.set(P(root,'tabMark'+str(tab)),'_visible',EQ(T('tab'),tab))
   for tab,method in enumerate(('RefreshClubs','RefreshMovements','RefreshFree','RefreshHistoryClubs','RefreshSettings')):a.when(EQ(T('tab'),tab),lambda a,method=method:a.do(R(1),method))
   a.set(R(1),'focusable',arr([]))
   for tab,scene in enumerate(MAIN):
    def buttons(a,scene=scene):
     for j,cmd in enumerate(commands[scene]):
      visible=True
      if 40<=cmd<=48:
       slot=cmd-40
       if scene==3:visible=lt(add(T('hirePage' if slot<4 else 'movePage'),slot%4),P(T('monthHires' if slot<4 else 'monthMoves'),'length'))
       else:visible=lt(add(mul(T('page'),PAGE_SIZE),slot),P(T('filtered'),'length'))
      elif 100<=cmd<=115:visible=both(lt(cmd-100,T('pageCount')),lt(T('pageCount'),17))
      elif 120<=cmd<=155:
       count=P(T('monthHires' if cmd<140 else 'monthMoves'),'length');dots_count=CALL(PATH('Math'),'ceil',div(count,4));visible=both(lt((cmd-120)%20,dots_count),lt(dots_count,17))
      elif 300<=cmd<400:visible=T('yearMenu')
      elif cmd in (200,201):visible=lt(4,P(T('monthHires' if cmd==200 else 'monthMoves'),'length'))
      btn=P(T('scene'+str(scene)),'action'+str(j))
      if cmd in (51,53,55):
       count=T('pageCount') if cmd==51 else CALL(PATH('Math'),'ceil',div(P(T('monthHires' if cmd==53 else 'monthMoves'),'length'),4))
       start=1100 if cmd==51 else 366 if cmd==53 else 1236
       used=CALL(PATH('Math'),'min',16,count);a.set(btn,'_x',add(start+12,mul(used,19)))
       a.when(lt(16,count),lambda a:a.set(btn,'_x',start+12))
      a.set(btn,'_visible',visible);a.set(P(btn,'selected'),'_alpha',mul(EQ(T('focus'),cmd),100))
      if cmd<200 or cmd>=300:a.when(visible,lambda a,cmd=cmd:a.do(T('focusable'),'push',cmd))
      if 40<=cmd<=48:
       for node in scenes[scene]['nodes']:
        if node.get('slot')==cmd-40:a.set(P(T('scene'+str(scene)),node['name']),'_visible',visible)
    a.when(EQ(T('tab'),tab),buttons)
   a.set(R(1),'focusExists',False);loop(a,'i',P(T('focusable'),'length'),lambda a:a.when(EQ(ix(T('focusable'),T('i')),T('focus')),lambda a:a.set(R(1),'focusExists',True)))
   a.when(('not',T('focusExists')),lambda a:a.set(R(1),'focus',0));a.do(M('HelpManager'),'Update');market_footer.apply(a)
  a.function('Refresh',0,refresh)
  def command(a):
   code=R(2)
   paging=either(both(lt(49,code),lt(code,56)),either(EQ(code,581),EQ(code,582)))
   a.when(both(paging,both(EQ(T('pagerInputCommand'),code),lt(sub(T('frames'),T('pagerInputFrame')),6))),lambda a:a.ret())
   a.when(paging,lambda a:(a.set(R(1),'pagerInputFrame',T('frames')),a.set(R(1),'pagerInputCommand',code)))
   a.when(both(either(EQ(code,30),EQ(code,31)),both(EQ(T('monthInputCommand'),code),lt(sub(T('frames'),T('monthInputFrame')),6))),lambda a:a.ret())
   a.when(either(EQ(code,30),EQ(code,31)),lambda a:(a.set(R(1),'monthInputFrame',T('frames')),a.set(R(1),'monthInputCommand',code)))
   if not model.get('ready'):
    a.when(EQ(code,60),lambda a:a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''));a.ret();return
   a.when(both(T('profile'),both(lt(79,code),lt(code,85))),lambda a:(a.set(R(1),'profileTab',sub(code,80)),a.set(R(1),'historyPage',0)))
   for c,step in ((90,1),(91,-1)):a.when(both(T('profile'),EQ(code,c)),lambda a,step=step:a.set(R(1),'profileVenue',wrap(add(T('profileVenue'),step),3)))
   a.when(both(EQ(code,1),('not',EQ(T('tab'),1))),lambda a:(a.set(R(1),'movementCountry',initial_country),a.set(R(1),'movementLeague',initial_league)))
   a.when(lt(code,len(TABS)),lambda a:(a.set(R(1),'tab',code),a.set(R(1),'clubTimeline',False),a.set(R(1),'historyPending',False),a.set(R(1),'profile',False),a.set(R(1),'page',0),a.set(R(1),'focus',code),a.set(R(1),'yearMenu',False)))
   a.when(both(('not',T('profile')),EQ(code,400)),lambda a:(a.set(R(1),'marketEnabled',('not',T('marketEnabled'))),a.do(R(1),'RequestSettings')))
   for setting_code,step in ((401,-1),(402,1),(403,1)):
    a.when(both(('not',T('profile')),EQ(code,setting_code)),lambda a,step=step:(a.set(R(1),'cadenceIndex',wrap(add(T('cadenceIndex'),step),3)),a.do(R(1),'RequestSettings')))
   for c,step in ((581,-1),(582,1)):
    a.when(EQ(code,c),lambda a,step=step:a.set(R(1),'timelinePage',clamp(add(T('timelinePage'),step),0,sub(T('timelinePageCount'),1))))
   a.when(EQ(code,583),lambda a:(a.set(R(1),'clubTimeline',False),a.set(R(1),'historyPending',False),a.set(R(1),'focus',40)))
   for c,step in ((10,-1),(11,1)):
    def country(a,step=step):
     a.set(R(1),'country',wrap(add(T('country'),step),P(T('countries'),'length')));a.set(R(1),'foundLeague',False);a.set(R(1),'page',0)
     def choose(a):
      l=ix(T('leagues'),T('j'));a.when(both(('not',T('foundLeague')),EQ(ix(l,2),ix(ix(T('countries'),T('country')),0))),lambda a:(a.set(R(1),'league',ix(l,0)),a.set(R(1),'foundLeague',True)))
     loop(a,'j',P(T('leagues'),'length'),choose)
    a.when(EQ(code,c),country)
   for c,step in ((20,-1),(21,1)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'league',ix(ix(T('leagueRows'),wrap(add(T('leagueIndex'),step),P(T('leagueRows'),'length'))),0)),a.set(R(1),'page',0)))
   for c,step in ((22,-1),(23,1)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'movementLeague',wrap(add(T('movementLeague'),step),add(P(T('movementLeagues'),'length'),1))),a.set(R(1),'hirePage',0),a.set(R(1),'movePage',0)))
   for c,step in ((24,-1),(25,1)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'movementCountry',wrap(add(T('movementCountry'),step),add(P(T('countries'),'length'),1))),a.set(R(1),'movementLeague',0),a.set(R(1),'hirePage',0),a.set(R(1),'movePage',0)))
   a.when(both(lt(99,code),lt(code,116)),lambda a:a.set(R(1),'page',clamp(sub(code,100),0,sub(T('pageCount'),1))))
   for base,key,rows in ((120,'hirePage','monthHires'),(140,'movePage','monthMoves')):
    a.when(both(lt(base-1,code),lt(code,base+16)),lambda a,base=base,key=key,rows=rows:a.set(R(1),key,clamp(mul(sub(code,base),4),0,CALL(PATH('Math'),'max',0,sub(P(T(rows),'length'),4)))))
   def choose_year(a,year):
    month=ix(ix(T('months'),T('month')),0);a.set(R(1),'desiredMonth',sub(month,mul(floor(div(month,100)),100)));a.set(R(1),'yearDistance',100)
    def choose(a):
     value=ix(ix(T('months'),T('j')),0);distance=CALL(PATH('Math'),'abs',sub(sub(value,mul(year,100)),T('desiredMonth')))
     a.when(both(EQ(floor(div(value,100)),year),lt(distance,T('yearDistance'))),lambda a:(a.set(R(1),'yearDistance',distance),a.set(R(1),'month',T('j'))))
    loop(a,'j',P(T('months'),'length'),choose);a.set(R(1),'hirePage',0);a.set(R(1),'movePage',0)
   for c,step in ((32,-1),(33,1)):
    a.when(EQ(code,c),lambda a,step=step:choose_year(a,add(floor(div(ix(ix(T('months'),T('month')),0),100)),step)))
   for i,year in enumerate(years):
    a.when(EQ(code,300+i),lambda a,year=year:(choose_year(a,year),a.set(R(1),'yearMenu',False),a.set(R(1),'focus',38)))
   a.when(EQ(code,38),lambda a:(a.set(R(1),'yearMenu',('not',T('yearMenu'))),a.set(R(1),'focus',38)))
   a.when(T('yearMenu'),lambda a:a.set(R(1),'focus',add(300,sub(floor(div(ix(ix(T('months'),T('month')),0),100)),years[0]))))
   for c,step in ((30,-1),(31,1)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'month',clamp(add(T('month'),step),0,sub(P(T('months'),'length'),1))),a.set(R(1),'hirePage',0),a.set(R(1),'movePage',0)))
   for c,key,step,size in ((34,'age',-1,6),(35,'age',1,6),(36,'nation',-1,P(T('nations'),'length')),(37,'nation',1,P(T('nations'),'length'))):a.when(EQ(code,c),lambda a,key=key,step=step,size=size:(a.set(R(1),key,wrap(add(T(key),step),size)),a.set(R(1),'page',0)))
   for slot in range(3):
    a.when(both(T('clubTimeline'),EQ(code,540+slot)),lambda a,slot=slot:(a.set(R(1),'person',ix(ix(T('timelineRows'),add(T('timelinePage'),slot)),11)),a.set(R(1),'profile',True),a.set(R(1),'profileTab',0),a.set(R(1),'historyPage',0)))
   for i in range(9):
    def open_person(a,i=i):
     a.when(EQ(T('tab'),3),lambda a:(a.do(R(1),'RequestClubHistory',ix(ix(T('filtered'),add(mul(T('page'),PAGE_SIZE),i)),2)),a.ret()))
     a.set(R(1),'selectedRow',ix(T('filtered'),add(mul(T('page'),PAGE_SIZE),i)))
     a.when(EQ(T('tab'),1),lambda a:a.set(R(1),'selectedRow',ix(T('monthHires' if i<4 else 'monthMoves'),add(T('hirePage' if i<4 else 'movePage'),i%4))))
     a.when(T('selectedRow'),lambda a:(a.set(R(1),'person',ix(T('selectedRow'),7)),a.set(R(1),'profile',True),a.set(R(1),'profileTab',0),a.set(R(1),'profileVenue',0),a.set(R(1),'historyPage',0)))
    a.when(EQ(code,40+i),open_person)
   for c,key,step in ((50,'page',-1),(51,'page',1),(52,'hirePage',-1),(53,'hirePage',1),(54,'movePage',-1),(55,'movePage',1)):a.when(EQ(code,c),lambda a,key=key,step=step:a.set(R(1),key,clamp(add(T(key),step),0,sub(T(key+'Count'),1))))
   for c,step in ((70,-1),(71,1)):a.when(EQ(code,c),lambda a,step=step:a.set(R(1),'historyPage',clamp(add(T('historyPage'),step),0,sub(T('historyPages'),1))))
   a.when(both(both(EQ(code,60),T('clubTimeline')),('not',T('profile'))),lambda a:(a.set(R(1),'clubTimeline',False),a.set(R(1),'historyPending',False),a.set(R(1),'focus',40),a.do(R(1),'Refresh'),a.ret()))
   a.when(both(EQ(code,60),T('yearMenu')),lambda a:(a.set(R(1),'yearMenu',False),a.set(R(1),'focus',38),a.do(R(1),'Refresh'),a.ret()))
   def back_profile(a):
    a.set(R(1),'profile',False)
   a.when(EQ(code,60),lambda a:a.when(T('profile'),back_profile,lambda a:a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'')));a.do(R(1),'Refresh')
  a.function('Command',1,command);a.function('Click',0,lambda a:a.do(P(R(1),'owner'),'Command',P(R(1),'code')));a.function('Over',0,lambda a:(a.set(P(R(1),'owner'),'focus',P(R(1),'code')),a.do(P(R(1),'owner'),'PaintFocus')))
  def paint_focus(a):
   for scene in (*MAIN,7):
    for index,button in enumerate(scenes[scene]['actions']):a.set(P(P(T('scene'+str(scene)),'action'+str(index)),'selected'),'_alpha',mul(EQ(T('focus'),int(button['target'])),100))
  a.function('PaintFocus',0,paint_focus)
  # Screen-local hit rectangles work even when art covers the button clip.
  def pointer(a,activate):
   a.when(either(('not',T('inputBound')),T('exiting')),lambda a:a.ret())
   for scene,s in enumerate(scenes):
    root=T('scene'+str(scene))
    for j,box in sorted(enumerate(s['actions']),key=lambda item:int(item[1]['target'])<300):
     x=P(P(root,'action'+str(j)),'_x') if int(box['target']) in (51,53,55) else box['x']
     inside=both(both(('not',lt(T('_xmouse'),x)),lt(T('_xmouse'),add(x,box['w']))),both(('not',lt(T('_ymouse'),box['y'])),lt(T('_ymouse'),box['y']+box['h'])))
     def hit(a,code=int(box['target'])):
      if activate:a.do(R(1),'Command',code)
      else:a.set(R(1),'focus',code);a.do(R(1),'PaintFocus')
      a.ret()
     a.when(both(both(both(P(root,'_visible'),P(P(root,'action'+str(j)),'_visible')),T('yearMenu') if 300<=int(box['target'])<400 else ('not',T('yearMenu'))),inside),hit)
  def drag_scroll(a):
   for mode,key,top,height,visible,rows in ((1,'hirePage',MOVE_TOP,MOVE_HEIGHT,4,'monthHires'),(2,'movePage',MOVE_TOP,MOVE_HEIGHT,4,'monthMoves'),(3,'historyPage',315,530,3,'profileRows'),(4,'timelinePage',365,522,3,'timelineRows')):
    def drag(a,key=key,top=top,height=height,visible=visible,rows=rows):
     count=P(T(rows),'length');thumb=div(height*visible,CALL(PATH('Math'),'max',visible,count))
     if key=='historyPage':thumb=CALL(PATH('Math'),'max',profile_layout.HISTORY_THUMB_MIN,thumb)
     span=CALL(PATH('Math'),'max',1,sub(height,thumb));limit=CALL(PATH('Math'),'max',0,sub(count,visible))
     grab=T('profileScrollGrab') if key=='historyPage' else div(thumb,2)
     target=floor(add(mul(clamp(div(sub(sub(T('_ymouse'),top),grab),span),0,1),limit),.5))
     a.when(('not',EQ(T(key),target)),lambda a:(a.set(R(1),key,target),a.do(R(1),'Refresh')));a.ret()
    a.when(EQ(T('dragScroll'),mode),drag)
  a.function('DragScroll',0,drag_scroll)
  def start_scroll(a):
   a.set(R(1),'dragScroll',R(2))
   def history_grab(a):
    thumb=CALL(PATH('Math'),'max',profile_layout.HISTORY_THUMB_MIN,div(1590,CALL(PATH('Math'),'max',3,P(T('profileRows'),'length'))))
    top=add(315,mul(div(T('historyPage'),CALL(PATH('Math'),'max',1,sub(P(T('profileRows'),'length'),3))),sub(530,thumb)))
    a.set(R(1),'profileScrollGrab',div(thumb,2))
    inside=both(('not',lt(T('_ymouse'),top)),lt(T('_ymouse'),add(top,thumb)))
    a.when(inside,lambda a:a.set(R(1),'profileScrollGrab',sub(T('_ymouse'),top)))
   a.when(EQ(R(2),3),history_grab);a.do(R(1),'DragScroll')
  a.function('StartScroll',1,start_scroll)
  a.function('ScrollPress',0,lambda a:a.do(P(R(1),'owner'),'StartScroll',sub(P(R(1),'code'),199)))
  a.function('ScrollRelease',0,lambda a:a.set(P(R(1),'owner'),'dragScroll',0))
  def warm_profile(a):
   a.when(either(T('profile'),T('clubTimeline')),lambda a:a.ret())
   a.when(('not',either(EQ(T('tab'),0),EQ(T('tab'),2))),lambda a:a.ret())
   a.when(('not',both(lt(39,T('focus')),lt(T('focus'),40+PAGE_SIZE))),lambda a:a.ret())
   row=ix(T('filtered'),add(mul(T('page'),PAGE_SIZE),sub(T('focus'),40)))
   a.when(('not',row),lambda a:a.ret())
   person=ix(row,7)
   a.when(EQ(T('warmPerson'),person),lambda a:a.ret())
   a.when(('not',EQ(T('warmFocus'),person)),lambda a:(a.set(R(1),'warmFocus',person),a.set(R(1),'warmFrames',0)))
   a.set(R(1),'warmFrames',add(T('warmFrames'),1))
   a.when(lt(T('warmFrames'),5),lambda a:a.ret())
   a.set(R(1),'warmPerson',person);a.do(R(1),'RequestProfile',person)
  a.function('WarmProfile',0,warm_profile)
  def scroll_frame(a):
   market_footer.apply(a)
   if model.get('lazyProfiles'):a.do(R(1),'WarmProfile')
   a.when(T('historyPending'),lambda a:a.do(R(1),'historyPoll'))
   profile_waiting=('not',ix(T('profileLoaded'),T('person')))
   if model.get('lazyProfiles'):profile_waiting=either(profile_waiting,('not',EQ(T('profileMediaPerson'),T('person'))))
   a.when(both(T('profile'),profile_waiting),lambda a:a.do(R(1),'profilePoll'))
   a.set(R(1),'frames',add(T('frames'),1))
   a.when(lt(0,T('mouseSelectFrames')),lambda a:a.set(R(1),'mouseSelectFrames',sub(T('mouseSelectFrames'),1)))
   a.when(lt(0,T('dragScroll')),lambda a:a.do(R(1),'DragScroll'))
  a.function('ScrollFrame',0,scroll_frame)
  def mouse_down(a):
   # FIFA can also forward the same mouse click as ADVANCE on release.
   # The screen-local hit test already dispatched it; swallow only that echo.
   a.set(R(1),'mouseSelectFrames',4);a.set(R(1),'mouseIsDown',True)
   a.when(T('yearMenu'),lambda a:(pointer(a,True),a.ret()))
   for mode,x,y,height,condition in ((1,945,MOVE_TOP,MOVE_HEIGHT,both(('not',T('profile')),EQ(T('tab'),1))),(2,1815,MOVE_TOP,MOVE_HEIGHT,both(('not',T('profile')),EQ(T('tab'),1))),(3,1824,315,530,both(T('profile'),either(either(EQ(T('profileTab'),1),EQ(T('profileTab'),2)),EQ(T('profileTab'),4)))),(4,1824,365,522,both(T('clubTimeline'),('not',T('profile'))))):
    inside=both(both(lt(x-12,T('_xmouse')),lt(T('_xmouse'),x+14)),both(lt(y-5,T('_ymouse')),lt(T('_ymouse'),y+height+5)))
    a.when(both(condition,inside),lambda a,mode=mode:(a.do(R(1),'StartScroll',mode),a.ret()))
   pointer(a,True)
  a.function('onMouseDown',0,mouse_down)
  a.function('onMouseMove',0,lambda a:a.when(lt(0,T('dragScroll')),lambda a:a.do(R(1),'DragScroll'),lambda a:pointer(a,False)))
  a.function('onMouseUp',0,lambda a:(a.set(R(1),'dragScroll',0),a.set(R(1),'mouseIsDown',False),a.set(R(1),'mouseSelectFrames',4)))
  def move(a):
   a.when(T('yearMenu'),lambda a:(a.when(either(EQ(R(2),2),EQ(R(2),3)),lambda a:a.set(R(1),'focus',clamp(add(T('focus'),sub(mul(EQ(R(2),3),2),1)),300,299+len(years)))),a.do(R(1),'Refresh'),a.ret()))
   a.when(T('profile'),lambda a:(a.when(EQ(T('profileTab'),0),lambda a:a.do(R(1),'Command',sub(91,EQ(R(2),3)))),a.when(either(either(EQ(T('profileTab'),1),EQ(T('profileTab'),2)),EQ(T('profileTab'),4)),lambda a:a.do(R(1),'Command',add(70,EQ(R(2),3)))),a.ret()))
   a.when(both(EQ(T('tab'),1),both(EQ(R(2),3),either(EQ(T('focus'),43),EQ(T('focus'),47)))),lambda a:(a.do(R(1),'Command',add(53,mul(2,EQ(T('focus'),47)))),a.ret()))
   a.when(both(EQ(T('tab'),1),both(EQ(R(2),2),either(both(EQ(T('focus'),40),lt(0,T('hirePage'))),both(EQ(T('focus'),44),lt(0,T('movePage')))))),lambda a:(a.do(R(1),'Command',add(52,mul(2,EQ(T('focus'),44)))),a.ret()))
   a.when(T('clubTimeline'),lambda a:(a.do(R(1),'TimelineMove',R(2)),a.ret()))
   def settings_move(a):
    a.set(R(1),'settingsOldFocus',T('focus'));code=T('settingsOldFocus');direction=R(2)
    a.when(lt(code,len(TABS)),lambda a:a.when(EQ(direction,3),lambda a:a.set(R(1),'focus',400),lambda a:a.when(lt(direction,2),lambda a:a.set(R(1),'focus',clamp(add(code,sub(mul(EQ(direction,1),2),1)),0,len(TABS)-1)))))
    a.when(EQ(code,400),lambda a:a.set(R(1),'focus',CALL(R(1),'SettingsFocus',direction)))
    a.when(either(either(EQ(code,401),EQ(code,402)),EQ(code,403)),lambda a:a.when(EQ(direction,2),lambda a:a.set(R(1),'focus',400),lambda a:a.when(lt(direction,2),lambda a:(a.do(R(1),'Command',add(401,EQ(direction,1))),a.set(R(1),'focus',403)))))
    a.do(R(1),'Refresh');a.ret()
   a.when(EQ(T('tab'),4),settings_move)
   for tab,scene in enumerate(MAIN):
    def navigate(a,tab=tab,scene=scene):
     buttons={int(v['target']):v for v in scenes[scene]['actions'] if int(v['target'])<200};a.set(R(1),'nextFocus',T('focus'))
     for code,box in buttons.items():
      for direction in range(4):
       target=code
       if 100<=code<=155:
        base=100 if code<120 else 120 if code<140 else 140;left,right=(50,51) if base==100 else (52,53) if base==120 else (54,55)
        target=(code-1 if code>base else left) if direction==0 else (code+1 if code<base+15 else right) if direction==1 else (44 if base==140 else 40)
       elif code in (50,52,54) and direction==1:target=100 if code==50 else 120 if code==52 else 140
       elif code in (51,53,55) and direction==0:target=50 if code==51 else 52 if code==53 else 54
       elif code<len(TABS):target=(10 if tab in (0,3) else 30 if tab==1 else 36) if direction==3 else max(0,min(len(TABS)-1,code+(-1 if direction==0 else 1))) if direction<2 else code
       elif tab in (0,3) and code in (10,11,20,21) and direction>=2:target=0 if direction==2 and code<20 else 10 if direction==2 else 20 if code<20 else 40
       else:
        x,y=box['x']+box['w']/2,box['y']+box['h']/2;options=[]
        for dest,other in buttons.items():
         if dest==code:continue
         dx=other['x']+other['w']/2-x;dy=other['y']+other['h']/2-y
         primary=(-dx,dx,-dy,dy)[direction];secondary=abs(dy) if direction<2 else abs(dx)
         if primary>10:options.append((primary+secondary*3,dest))
        if options:target=min(options)[1]
       a.when(both(EQ(T('focus'),code),EQ(R(2),direction)),lambda a,target=target:a.set(R(1),'nextFocus',target))
     a.set(R(1),'validNext',False);loop(a,'j',P(T('focusable'),'length'),lambda a:a.when(EQ(ix(T('focusable'),T('j')),T('nextFocus')),lambda a:a.set(R(1),'validNext',True)))
     def fallback(a):
      a.when(both(EQ(R(2),1),either(EQ(T('focus'),50),either(EQ(T('focus'),52),EQ(T('focus'),54)))),lambda a:a.set(R(1),'focus',add(T('focus'),1)))
      a.when(both(EQ(R(2),1),both(lt(99,T('focus')),lt(T('focus'),156))),lambda a:a.set(R(1),'focus',51 if tab!=1 else add(53,mul(2,lt(139,T('focus'))))))
     a.when(T('validNext'),lambda a:a.set(R(1),'focus',T('nextFocus')),fallback)
    a.when(EQ(T('tab'),tab),navigate)
   a.do(R(1),'Refresh')
  a.function('SettingsFocus',1,lambda a:a.when(EQ(R(2),2),lambda a:a.ret(4),lambda a:a.when(EQ(R(2),3),lambda a:a.ret(403),lambda a:a.ret(400))))
  a.function('SettingsSelectorFocus',1,lambda a:a.when(EQ(R(2),0),lambda a:a.ret(401),lambda a:a.ret(402)))
  a.function('Move',1,move)
  a.function('onMouseWheel',1,lambda a:a.when(both(T('clubTimeline'),('not',T('profile'))),lambda a:a.do(R(1),'Command',add(581,EQ(lt(0,R(2)),False))),lambda a:a.when(T('profile'),lambda a:a.when(lt(0,R(2)),lambda a:a.do(R(1),'Command',70),lambda a:a.do(R(1),'Command',71)),lambda a:a.when(EQ(T('tab'),1),lambda a:a.do(R(1),'Command',add(add(52,EQ(lt(0,R(2)),False)),mul(2,lt(43,T('focus')))))))))
  def local(a):
   a.when(T('historyPending'),lambda a:(a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:a.do(R(1),'Command',60)),a.ret(True)))
   for key in ('BACK','ADVANCE','PRIMARY_SELECT','UP','DOWN','LAS_UP','LAS_DOWN','LEFT','RIGHT','LAS_LEFT','LAS_RIGHT','RAS_LEFT','RAS_RIGHT','RAS_UP','RAS_DOWN','OPTION_LEFT','OPTION_TOP','L1','R1','L2','R2'):
    def handle(a,key=key):
     if key=='BACK':a.do(R(1),'Command',60)
     elif key in ('ADVANCE','PRIMARY_SELECT'):a.when(either(T('mouseIsDown'),lt(0,T('mouseSelectFrames'))),lambda a:a.ret(True));a.when(('not',T('profile')),lambda a:a.do(R(1),'Command',T('focus')))
     elif key in ('UP','LAS_UP','DOWN','LAS_DOWN'):a.do(R(1),'Move',2 if key in ('UP','LAS_UP') else 3)
     elif key in ('OPTION_LEFT','OPTION_TOP'):a.when(EQ(T('tab'),4),lambda a:a.ret(True));a.when(('not',T('profile')),lambda a:a.when(EQ(T('tab'),1),lambda a:a.do(R(1),'Command',add(52 if key=='OPTION_LEFT' else 53,mul(2,lt(43,T('focus'))))),lambda a:a.do(R(1),'Command',50 if key=='OPTION_LEFT' else 51)))
     elif key.startswith('RAS_'):a.when(both(T('clubTimeline'),('not',T('profile'))),lambda a:(a.do(R(1),'Command',581 if key in ('RAS_LEFT','RAS_UP') else 582),a.ret(True)));a.when(EQ(T('tab'),4),lambda a:(a.do(R(1),'Command',401 if key in ('RAS_LEFT','RAS_UP') else 402),a.ret(True)));a.when(T('profile'),lambda a:a.do(R(1),'Command',70 if key in ('RAS_LEFT','RAS_UP') else 71),lambda a:a.when(EQ(T('tab'),1),lambda a:a.do(R(1),'Command',add(52 if key in ('RAS_LEFT','RAS_UP') else 53,mul(2,lt(43,T('focus'))))),lambda a:a.do(R(1),'Command',50 if key in ('RAS_LEFT','RAS_UP') else 51)))
     elif key in ('L1','R1'):a.when(both(T('clubTimeline'),('not',T('profile'))),lambda a:(a.do(R(1),'Command',581 if key=='L1' else 582),a.ret(True)));a.when(EQ(T('tab'),4),lambda a:(a.do(R(1),'Command',401 if key=='L1' else 402),a.ret(True)));a.when(('not',T('profile')),lambda a:a.when(EQ(T('tab'),1),lambda a:a.do(R(1),'Command',30 if key=='L1' else 31),lambda a:a.do(R(1),'Command',50 if key=='L1' else 51)))
     elif key in ('L2','R2'):a.when(T('profile'),lambda a:a.do(R(1),'Command',add(80,wrap(add(T('profileTab'),-1 if key=='L2' else 1),5))),lambda a:a.do(R(1),'Command',wrap(add(T('tab'),-1 if key=='L2' else 1),len(TABS))))
     else:
      left=key in ('LEFT','LAS_LEFT');a.when(T('profile'),lambda a:a.do(R(1),'Command',70 if left else 71),lambda a:a.do(R(1),'Move',0 if left else 1))
     a.ret(True)
    a.when(both(P(M('InputCodes'),key),EQ(R(2),P(M('InputCodes'),key))),handle)
   a.ret(True)
  a.function('LocalEventHandler',2,local)
  def help_context(a):
   a.when(T('profile'),lambda a:a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('BACK','Voltar'),('L2R2','Abas do perfil'),('LAS_LR','Páginas do histórico')])) )
   a.when(both(T('clubTimeline'),('not',T('profile'))),lambda a:a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('ADVANCE','Ver perfil'),('BACK','Clubes'),('L2R2','Abas'),('RAS_UD','Rolar histórico')])))
   a.when(both(('not',T('profile')),EQ(T('tab'),4)),lambda a:a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('ADVANCE','Alterar'),('BACK','Voltar'),('L2R2','Abas'),('L1R1','Frequência'),('LAS_UD','Navegar')])))
   a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('ADVANCE','Ver perfil'),('BACK','Voltar'),('L2R2','Abas'),('L1R1','Mês / páginas'),('RAS_UD','Listas / páginas'),('LAS_UD','Navegar')]))
  a.function('getHelpContext',0,help_context)
  def shutdown(a):
   a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None);a.do(PATH('Mouse'),'removeListener',R(1))
   for i,s in enumerate(scenes):
    for j,_ in enumerate(s['actions']):
     for event in ('onPress','onRelease','onReleaseOutside','onRollOver'):a.set(P(T('scene'+str(i)),'action'+str(j)),event,None)
   a.do(M('InputManager'),'DisableCurrentLocalEventHandler');market_footer.restore(a);a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
  a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration
 return script

def build(game,path,model):
 root=Path(game)/'ModCarrerMode/runtime/manager_market'
 # All changing career labels are bound by the controller. The template key
 # covers only geometry, catalogue membership, photos, theme, and generators.
 keys=[('profileMedia',bool(model.get('lazyProfiles')))]
 for group in ('clubRows','freeRows','moveRows','hireRows'):
  keys.append((group,sorted({r[1] for r in model.get('historyClubRows',[])}|{r[4] for r in model['clubRows']}|{p['head'] for p in model['people']}),sorted(asset_cache.flag_keys(game,model))))
 revision=asset_cache.revision(game,model)
 token=hashlib.sha256((GEOMETRY_SIGNATURE+revision).encode()+json.dumps(keys,sort_keys=True).encode()).hexdigest()
 template=root/'native_templates'/('template_'+token+'.big')
 if template.is_file() and template.with_suffix('.json').is_file():
  try:return template_renderer.build(template,path,script_factory=script_factory(model,{}),full_name=FULL)
  except (OSError,ValueError,KeyError,AssertionError):pass
 prepared=prepared_catalogue.template(game,model,GEOMETRY_SIGNATURE,revision)
 if prepared:
  try:return template_renderer.build(prepared,path,script_factory=script_factory(model,{}),full_name=FULL)
  except (OSError,ValueError,KeyError,AssertionError):pass
 assets=assets_for(game,model)
 # The largest portrait placement is 202 design pixels. Store heads at the
 # next complete DXT block (204), not 256 for thousands of offscreen coaches.
 # Source minifaces remain untouched; no displayed portrait loses resolution.
 # The full catalogue must remain below the native 128 MiB package limit.
 from PIL import Image
 for key,image in list(assets.items()):
  if key.startswith('head_') and (image.width>204 or image.height>204):
   copy=image.copy();copy.thumbnail((204,204),Image.Resampling.LANCZOS);assets[key]=copy
 scenes=scenes_for(model,assets)
 return native.build(game,path,scenes,assets,script_factory=script_factory(model,assets),full_name=FULL,compression_level=1,catalogue_groups=True,texture_cache=root/'texture_cache',template_cache=template)
def waiting():return dict(date=20260101,clubName='Carreira',ready=False,people=[],clubRows=[],freeRows=[],moveRows=[],hireRows=[],leagues=[],countries=[],months=[],nationalities=['Todas'],initialLeague=0,initialCountry=0,initialMonth=0)
