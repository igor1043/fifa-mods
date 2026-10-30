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
import asset_cache,club_portraits
from manager_layout import assets_for,scenes_for,stars,TABS,MAIN,club_xy,free_xy,move_xy,PAGE_SIZE

CLASS=('game','screens','career','server16','ManagerMarket');FULL='.'.join(CLASS)
UI_SIGNATURE=hashlib.sha256(Path(__file__).read_bytes()+b''.join(Path(m.__file__).read_bytes() for m in (manager_layout,profile_layout,profile_controller,profile_art,asset_cache,club_portraits,native,b,bank_art))).hexdigest()
R=b.reg;T=b.this;P=b.prop;EQ=b.equal;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
def arr(v):return ('array',tuple(v))

def packed_array(values):
 values=list(values)
 if not values or any(type(v) not in (str,int,float) or '\x1f' in str(v) for v in values):return arr(values)
 return CALL(R(1),'DecodeFields','\x1f'.join(('s' if isinstance(v,str) else 'n')+str(v) for v in values))
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
 def script(data,dictionaries,scenes):
  b.CLASS=CLASS;b.FULL=FULL;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
  for i,name in enumerate(CLASS[:-1]):
   parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
  # Hide the catalogue artwork in bounded frames as well. Thousands of crest
  # variants must not turn the final Ready callback into one giant AVM action.
  operations=[('hide','scene'+str(i),n['name']) for i,s in enumerate(scenes) for n in s['nodes'] if n['type']=='image' and n.get('name') and not n.get('native_group')]
  for key,rows in (('clubs',model['clubRows']),('free',model['freeRows']),('moves',model['moveRows']),('hires',model['hireRows'])):operations.extend(('row',key,row) for row in rows)
  operations.extend(('profile','people',p) for p in model['people'])
  operations.extend(('row','leagues',[l['id'],l['name'],l['country'],l['level'],l['image']]) for l in model['leagues'])
  operations.extend(('row','countries',[c['name'],c['flag']]) for c in model.get('countries',[]) or [dict(name='Aguardando carreira',flag='flag_0')])
  operations.extend(('row','months',m) for m in model.get('months',[]) or [[202601,'Janeiro 2026']]);operations.extend(('value','nations',v) for v in model['nationalities'])
  batches=[operations[i:i+128] for i in range(0,len(operations),128)] or [[]]
  def ctor(a):
   a.op(89);a.reg(2);a.op(118);a.op(93);a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')));a.do(R(1),'Initialize',FULL,None,True)
   a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'screenReady',False);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
   for key,value in dict(tab=0,page=0,country=model.get('initialCountry',0),league=model.get('initialLeague',0),month=model.get('initialMonth',0),hirePage=0,movePage=0,age=0,nation=0,profile=False,person=0,profileTab=0,profileVenue=0,historyPage=0,focus=40,frames=0).items():a.set(R(1),key,value)
   for key in ('clubs','free','moves','hires','people','leagues','countries','months','nations','rendered','profileLoaded'):a.set(R(1),key,arr([]))
   a.set(R(1),'dataStep',0);a.set(R(1),'dataReady',False);a.set(R(1),'onEnterFrame',T('DataFrame'))
  a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
  def decode_fields(a):
   a.set(R(1),'decodedFields',CALL(R(2),'split','\x1f'))
   def decode(a):
    value=ix(T('decodedFields'),T('fieldIndex'));body=CALL(value,'substr',1)
    a.expr(T('decodedFields'));a.expr(T('fieldIndex'))
    a.when(EQ(CALL(value,'charAt',0),'n'),lambda a:a.expr(mul(body,1)),lambda a:a.expr(body));a.op(79)
   loop(a,'fieldIndex',P(T('decodedFields'),'length'),decode);a.ret(T('decodedFields'))
  a.function('DecodeFields',1,decode_fields)
  # Career histories are bytecode in the package, but only the selected
  # coach's arrays are instantiated. Opening the market never loads every CV.
  for person_index,person in enumerate(model['people']):
   def load_person(a,p=person,index=person_index):
    for key,values,nested in (('loadingHistory',p['history'],False),('loadingTitles',p['titles'],False),('loadingSpells',p.get('spellCards',[]),True),('loadingAwards',p.get('titleCards',[]),True)):
     if not nested:a.set(R(1),key,packed_array(values));continue
     a.set(R(1),key,arr([]))
     for value in values:a.do(T(key),'push',packed_array(value))
    target=ix(T('people'),index)
    for col,value in ((7,T('loadingHistory')),(8,T('loadingTitles')),(23,packed_array(p.get('overview',[0]*14+['','','',-1,'','']))),(24,T('loadingSpells')),(25,T('loadingAwards')),(26,packed_array(p.get('visualData',['']*27)))):
     a.expr(target);a.expr(col);a.expr(value);a.op(79)
    a.expr(T('profileLoaded'));a.expr(index);a.expr(True);a.op(79)
    for key in ('loadingHistory','loadingTitles','loadingSpells','loadingAwards'):a.set(R(1),key,None)
   a.function('LoadPerson'+str(person_index),0,load_person)
  profile_groups=(len(model['people'])+63)//64
  for group in range(profile_groups):
   def load_group(a,group=group):
    for index in range(group*64,min(len(model['people']),(group+1)*64)):
     a.when(EQ(T('person'),index),lambda a,index=index:(a.do(R(1),'LoadPerson'+str(index)),a.ret()))
   a.function('LoadProfileGroup'+str(group),0,load_group)
  def ensure_profile(a):
   a.when(ix(T('profileLoaded'),T('person')),lambda a:a.ret())
   for group in range(profile_groups):
    a.when(EQ(floor(div(T('person'),64)),group),lambda a,group=group:(a.do(R(1),'LoadProfileGroup'+str(group)),a.ret()))
  a.function('EnsureProfile',0,ensure_profile)
  for batch_index,batch in enumerate(batches):
   def append_batch(a,batch=batch):
    for kind,key,value in batch:
     if kind=='hide':a.set(P(T(key),value),'_visible',False)
     elif kind=='reset':a.set(R(1),key,arr([]))
     elif kind=='profile':a.do(T('people'),'push',arr([value['name'],*value['details'],arr([]),arr([]),value['head'],value['reputation'],value['nationality'],value.get('flag','flag_0'),value['age'],value.get('style','Equilibrado'),value.get('formation','Não informada') if value.get('formation')!='Não informada' else 'Formação pendente',value.get('freeDays',''),f"{int(value['salary']):,}".replace(',','.'),value.get('secondaryStyle',''),native.fit(value['name'],470,26),native.fit(value['nationality'],293,18),native.fit(value['nationality'],445,19),native.fit(value['nationality'],259,17),arr([]),arr([]),arr([]),arr([])]))
     elif kind=='value' and key in ('loadingSpells','loadingAwards'):a.do(T(key),'push',arr(value))
     else:
      if kind=='row' and key in ('clubs','moves','hires'):
       value=list(value);value[0]=native.fit(value[0],128 if key=='clubs' else 171,17 if key=='clubs' else 20);value[1]=native.fit(value[1],327 if key=='clubs' else 270,24 if key=='clubs' else 21)
      a.do(T(key),'push',arr(value) if kind=='row' else value)
   a.function('DataBatch'+str(batch_index),0,append_batch)
  def data_frame(a):
   a.when(('not',P(T('scene1'),'profileCaption')),lambda a:a.ret())
   for i in (0,1,3,4):a.set(T('scene'+str(i)),'_visible',False)
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
   for i in MAIN:a.set(P(T('scene'+str(i)),'careerMeta'),'text',meta)
   for i,s in enumerate(scenes):
    for j,action in enumerate(s['actions']):
     btn=P(T('scene'+str(i)),'action'+str(j));a.set(btn,'owner',R(1));a.set(btn,'code',int(action['target']));a.set(btn,'onRelease',T('Click'));a.set(btn,'onRollOver',T('Over'))
   a.set(R(1),'onEnterFrame',None);a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')));a.do(R(1),'Refresh');a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
  a.function('Wait',0,wait)
  def complete(a):
   a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True);a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
  a.function('OnAnimateInComplete',0,complete)
  def reveal(a):a.when(R(2),lambda a:(a.set(R(2),'_visible',True),a.set(R(2),'_alpha',100),a.set(R(2),'_x',R(3)),a.set(R(2),'_y',R(4)),a.do(T('rendered'),'push',R(2))))
  a.function('Reveal',3,reveal)
  groups=sorted({n['native_group'] for s in scenes for n in s['nodes'] if n.get('native_group')})
  def find_art(a):
   a.when(ix(R(2),R(3)),lambda a:a.ret(ix(R(2),R(3))))
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
   field(a,root,'pageText',pagetext('page',add(P(T('filtered'),'length'),' clubes')));field(a,root,'empty','Nenhum clube nesta liga.' if model.get('ready') else 'Preparando o mercado da carreira aberta...',EQ(P(T('filtered'),'length'),0))
  def movements(a):
   root=T('scene3');month=ix(ix(T('months'),T('month')),0);field(a,root,'monthName',ix(ix(T('months'),T('month')),1))
   for source,filtered in (('hires','monthHires'),('moves','monthMoves')):
    a.set(R(1),filtered,arr([]));loop(a,'i',P(T(source),'length'),lambda a,source=source,filtered=filtered:a.when(EQ(floor(div(ix(ix(T(source),T('i')),9),100)),month),lambda a:a.do(T(filtered),'push',ix(T(source),T('i')))))
   for panel,(rows,key,prefix,status) in enumerate((('monthHires','hirePage','h_','Contratado'),('monthMoves','movePage','d_','Demitido'))):
    pages(a,T(rows),key,4);field(a,root,prefix+'count',add(P(T(rows),'length'),' contratações' if panel==0 else ' demissões'));field(a,root,prefix+'empty','Nenhuma '+('contratação' if panel==0 else 'demissão')+' neste mês.',EQ(P(T(rows),'length'),0));field(a,root,prefix+'page',pagetext(key,add(P(T(rows),'length'),' registros')))
    for j in range(4):
     i=panel*4+j;idx=add(mul(T(key),4),j);r=ix(T(rows),idx);p=ix(T('people'),ix(r,7));present=lt(idx,P(T(rows),'length'));x,y=move_xy(i)
     for name,value in (('club',ix(r,0)),('coach',ix(r,1)),('nationality',ix(p,22)),('date',ix(r,10)),('status',status)):field(a,root,name+str(i),value,present)
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
   field(a,root,'ageValue',ix(arr(['Todas as idades','Até 40 anos','41 a 55 anos','56 a 70 anos','71 anos ou mais','Idade não informada']),T('age')));field(a,root,'natValue',add('Nacionalidade: ',ix(T('nations'),T('nation'))))
   for i in range(PAGE_SIZE):
    idx=add(mul(T('page'),PAGE_SIZE),i);r=ix(T('filtered'),idx);p=ix(T('people'),ix(r,7));present=lt(idx,P(T('filtered'),'length'));x,y=free_xy(i)
    for name,value in (('coach',ix(p,19)),('nationality',ix(p,21)),('freeDays',ix(p,16)),('age',add(ix(p,13),' anos') if model.get('ready') else ''),('style',ix(p,14)),('formation',ix(p,15)),('status','Livre no mercado')):field(a,root,name+str(i),value,both(present,lt(-1,ix(p,13))) if name=='age' else present)
    a.when(present,lambda a,i=i,r=r,p=p,x=x,y=y:(portrait(a,root,'f_',r,i,x+16,y+12),rating(a,root,'f_',r,i,x+14,y+153),nationality(a,root,'f_',p,i,x+170,y+64)))
   field(a,root,'pageText',pagetext('page',add(P(T('filtered'),'length'),' técnicos · Reputação da maior para a menor')));field(a,root,'empty','Nenhum técnico para os filtros selecionados.',EQ(P(T('filtered'),'length'),0))
  a.function('RefreshClubs',0,clubs);a.function('RefreshMovements',0,movements);a.function('RefreshFree',0,frees);a.function('RefreshProfile',0,profile)
  def refresh(a):
   loop(a,'hidden',P(T('rendered'),'length'),lambda a:a.set(ix(T('rendered'),T('hidden')),'_visible',False));a.set(R(1),'rendered',arr([]))
   for i in range(len(scenes)):a.set(T('scene'+str(i)),'_visible',False)
   if not model.get('ready'):
    a.set(T('scene2'),'_visible',True);a.set(P(T('scene2'),'progress'),'text','Preparando os dados da carreira aberta. Aguarde...');a.do(M('HelpManager'),'Update');a.ret();return
   a.when(T('profile'),lambda a:(a.set(T('scene1'),'_visible',True),a.do(R(1),'RefreshProfile'),a.do(M('HelpManager'),'Update'),a.ret()))
   root=ix(R(1),add('scene',ix(arr(MAIN),T('tab'))));a.set(root,'_visible',True);a.set(R(1),'mainClip',root)
   for tab in range(3):show(a,root,'tabMark'+str(tab),96+tab*580,203);a.set(P(root,'tabMark'+str(tab)),'_visible',EQ(T('tab'),tab))
   for tab,method in enumerate(('RefreshClubs','RefreshMovements','RefreshFree')):a.when(EQ(T('tab'),tab),lambda a,method=method:a.do(R(1),method))
   a.set(R(1),'focusable',arr([]))
   for tab,scene in enumerate(MAIN):
    def buttons(a,scene=scene):
     for j,cmd in enumerate(commands[scene]):
      visible=True
      if 40<=cmd<=48:
       slot=cmd-40
       if scene==3:visible=lt(add(mul(T('hirePage' if slot<4 else 'movePage'),4),slot%4),P(T('monthHires' if slot<4 else 'monthMoves'),'length'))
       else:visible=lt(add(mul(T('page'),PAGE_SIZE),slot),P(T('filtered'),'length'))
      btn=P(T('scene'+str(scene)),'action'+str(j));a.set(btn,'_visible',visible);a.set(P(btn,'selected'),'_alpha',mul(EQ(T('focus'),cmd),100));a.when(visible,lambda a,cmd=cmd:a.do(T('focusable'),'push',cmd))
      if 40<=cmd<=48:
       for node in scenes[scene]['nodes']:
        if node.get('slot')==cmd-40:a.set(P(T('scene'+str(scene)),node['name']),'_visible',visible)
    a.when(EQ(T('tab'),tab),buttons)
   a.set(R(1),'focusExists',False);loop(a,'i',P(T('focusable'),'length'),lambda a:a.when(EQ(ix(T('focusable'),T('i')),T('focus')),lambda a:a.set(R(1),'focusExists',True)))
   a.when(('not',T('focusExists')),lambda a:a.set(R(1),'focus',0));a.do(M('HelpManager'),'Update')
  a.function('Refresh',0,refresh)
  def command(a):
   code=R(2)
   if not model.get('ready'):
    a.when(EQ(code,60),lambda a:a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''));a.ret();return
   a.when(both(T('profile'),both(lt(79,code),lt(code,84))),lambda a:(a.set(R(1),'profileTab',sub(code,80)),a.set(R(1),'historyPage',0)))
   for c,step in ((90,1),(91,-1)):a.when(both(T('profile'),EQ(code,c)),lambda a,step=step:a.set(R(1),'profileVenue',wrap(add(T('profileVenue'),step),3)))
   a.when(lt(code,3),lambda a:(a.set(R(1),'tab',code),a.set(R(1),'profile',False),a.set(R(1),'page',0),a.set(R(1),'focus',40)))
   for c,step in ((10,-1),(11,1)):
    def country(a,step=step):
     a.set(R(1),'country',wrap(add(T('country'),step),P(T('countries'),'length')));a.set(R(1),'foundLeague',False);a.set(R(1),'page',0)
     def choose(a):
      l=ix(T('leagues'),T('j'));a.when(both(('not',T('foundLeague')),EQ(ix(l,2),ix(ix(T('countries'),T('country')),0))),lambda a:(a.set(R(1),'league',ix(l,0)),a.set(R(1),'foundLeague',True)))
     loop(a,'j',P(T('leagues'),'length'),choose)
    a.when(EQ(code,c),country)
   for c,step in ((20,-1),(21,1)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'league',ix(ix(T('leagueRows'),wrap(add(T('leagueIndex'),step),P(T('leagueRows'),'length'))),0)),a.set(R(1),'page',0)))
   for c,step in ((30,-1),(31,1),(32,-12),(33,12)):a.when(EQ(code,c),lambda a,step=step:(a.set(R(1),'month',clamp(add(T('month'),step),0,sub(P(T('months'),'length'),1))),a.set(R(1),'hirePage',0),a.set(R(1),'movePage',0)))
   for c,key,step,size in ((34,'age',-1,6),(35,'age',1,6),(36,'nation',-1,P(T('nations'),'length')),(37,'nation',1,P(T('nations'),'length'))):a.when(EQ(code,c),lambda a,key=key,step=step,size=size:(a.set(R(1),key,wrap(add(T(key),step),size)),a.set(R(1),'page',0)))
   for i in range(9):
    def open_person(a,i=i):
     a.set(R(1),'selectedRow',ix(T('filtered'),add(mul(T('page'),PAGE_SIZE),i)))
     a.when(EQ(T('tab'),1),lambda a:a.set(R(1),'selectedRow',ix(T('monthHires' if i<4 else 'monthMoves'),add(mul(T('hirePage' if i<4 else 'movePage'),4),i%4))))
     a.when(T('selectedRow'),lambda a:(a.set(R(1),'person',ix(T('selectedRow'),7)),a.set(R(1),'profile',True),a.set(R(1),'profileTab',0),a.set(R(1),'profileVenue',0),a.set(R(1),'historyPage',0)))
    a.when(EQ(code,40+i),open_person)
   for c,key,step in ((50,'page',-1),(51,'page',1),(52,'hirePage',-1),(53,'hirePage',1),(54,'movePage',-1),(55,'movePage',1)):a.when(EQ(code,c),lambda a,key=key,step=step:a.set(R(1),key,clamp(add(T(key),step),0,sub(T(key+'Count'),1))))
   for c,step in ((70,-1),(71,1)):a.when(EQ(code,c),lambda a,step=step:a.set(R(1),'historyPage',clamp(add(T('historyPage'),step),0,sub(T('historyPages'),1))))
   a.when(EQ(code,60),lambda a:a.when(T('profile'),lambda a:a.set(R(1),'profile',False),lambda a:a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'')));a.do(R(1),'Refresh')
  a.function('Command',1,command);a.function('Click',0,lambda a:a.do(P(R(1),'owner'),'Command',P(R(1),'code')));a.function('Over',0,lambda a:(a.set(P(R(1),'owner'),'focus',P(R(1),'code')),a.do(P(R(1),'owner'),'Refresh')))
  def move(a):
   a.when(T('profile'),lambda a:(a.when(EQ(T('profileTab'),0),lambda a:a.when(lt(R(2),0),lambda a:a.do(R(1),'Command',91),lambda a:a.do(R(1),'Command',90))),a.ret()));a.set(R(1),'fi',0);loop(a,'j',P(T('focusable'),'length'),lambda a:a.when(EQ(ix(T('focusable'),T('j')),T('focus')),lambda a:a.set(R(1),'fi',T('j'))));a.set(R(1),'fi',wrap(add(T('fi'),R(2)),P(T('focusable'),'length')));a.set(R(1),'focus',ix(T('focusable'),T('fi')));a.do(R(1),'Refresh')
  a.function('Move',1,move)
  def local(a):
   for key in ('BACK','ADVANCE','PRIMARY_SELECT','UP','DOWN','LAS_UP','LAS_DOWN','LEFT','RIGHT','LAS_LEFT','LAS_RIGHT','L2','R2'):
    def handle(a,key=key):
     if key=='BACK':a.do(R(1),'Command',60)
     elif key in ('ADVANCE','PRIMARY_SELECT'):a.when(('not',T('profile')),lambda a:a.do(R(1),'Command',T('focus')))
     elif key in ('UP','LAS_UP','DOWN','LAS_DOWN'):a.do(R(1),'Move',-1 if key in ('UP','LAS_UP') else 1)
     elif key in ('L2','R2'):a.when(T('profile'),lambda a:a.do(R(1),'Command',add(80,wrap(add(T('profileTab'),-1 if key=='L2' else 1),4))),lambda a:a.do(R(1),'Command',wrap(add(T('tab'),-1 if key=='L2' else 1),3)))
     else:
      left=key in ('LEFT','LAS_LEFT');a.when(T('profile'),lambda a:a.do(R(1),'Command',70 if left else 71),lambda a:a.when(EQ(T('tab'),1),lambda a:a.do(R(1),'Command',30 if left else 31),lambda a:a.do(R(1),'Command',50 if left else 51)))
     a.ret(True)
    a.when(EQ(R(2),P(M('InputCodes'),key)),handle)
   a.ret(True)
  a.function('LocalEventHandler',2,local)
  def help_context(a):
   a.when(T('profile'),lambda a:a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('BACK','Voltar'),('L2R2','Abas do perfil'),('LAS_LR','Páginas do histórico')])) )
   a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('ADVANCE','Ver perfil'),('BACK','Voltar'),('L2R2','Abas'),('LAS_LR','Páginas / mês')]))
  a.function('getHelpContext',0,help_context)
  def shutdown(a):
   a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None)
   for i,s in enumerate(scenes):
    for j,_ in enumerate(s['actions']):
     for event in ('onRelease','onRollOver'):a.set(P(T('scene'+str(i)),'action'+str(j)),event,None)
   a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
  a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration
 return script

def build(game,path,model):
 root=Path(game)/'ModCarrerMode/runtime/manager_market'
 # All changing career labels are bound by the controller. The template key
 # covers only geometry, catalogue membership, photos, theme, and generators.
 keys=[]
 for group in ('clubRows','freeRows','moveRows','hireRows'):
  keys.append((group,sorted({str(r[c]) for r in model[group] for c in (4,5)}),sorted({model['people'][r[7]].get('flag','flag_0') for r in model[group]})))
 token=hashlib.sha256((UI_SIGNATURE+asset_cache.revision(game,model)).encode()+json.dumps(keys,sort_keys=True).encode()).hexdigest()
 template=root/'native_templates'/('template_'+token+'.big')
 if template.is_file() and template.with_suffix('.json').is_file():
  try:return native.build_from_template(template,path,script_factory=script_factory(model,{}),full_name=FULL,compression_level=1)
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
