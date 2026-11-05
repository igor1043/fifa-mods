"""Native lifecycle and reversible Office carousel entries for career options."""
from pathlib import Path
import json,xml.etree.ElementTree as ET
import build_apt as browser
from build_preview import Code
import native_roster_footer as footer
from build_package import read_nav,walk
native=browser.native;b=browser.b
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
PAGES=(('CareerClubTransfer','Server16EnterCareerClubTransfer','BROWSE_JOBS','OUTRO CLUBE','Solicite uma proposta de outro clube'),
       ('CareerRetirement','Server16EnterCareerRetirement','SETTINGS','APOSENTADORIA','Manter jogadores em atividade ou rejuvenescer'))


def script_for(name):
 CLASS=('game','screens','career','server16',name);FULL='.'.join(CLASS)
 def script(data,dictionaries,scenes):
  b.CLASS=CLASS;b.FULL=FULL;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
  for index,part in enumerate(CLASS[:-1]):
   parent=b.GLOBAL if index==0 else PATH(*CLASS[:index]);a.when(P(parent,part),lambda a:None,lambda a,parent=parent,part=part:a.set(parent,part,('object',)))
  def ctor(a):
   a.op(89);a.reg(2);a.op(118);a.op(93);a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
   a.do(R(1),'Initialize',FULL,None,True);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'));a.set(R(1),'_visible',True);a.set(R(1),'onEnterFrame',T('Ready'));a.do(R(1),'Ready')
  a.function(name,0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
  def ready(a):
   a.when(T('bound'),lambda a:a.ret())
   def bind(a):
    a.set(R(1),'bound',True);a.set(T('scene0'),'_visible',True);a.set(R(1),'helpDelay',90);a.set(R(1),'onEnterFrame',T('Tick'))
    a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')));a.do(PATH('Key'),'addListener',R(1))
    a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
   a.when(P(T('scene0'),'action0'),bind)
  a.function('Ready',0,ready)
  def refresh(a):
   a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show');footer.apply(a)
  a.function('RefreshHelp',0,refresh)
  def tick(a):
   a.when(T('helpDelay'),lambda a:(a.set(R(1),'helpDelay',('bin',11,T('helpDelay'),1)),a.when(('bin',17,b.equal(T('helpDelay'),60),b.equal(T('helpDelay'),0)),lambda a:a.do(R(1),'RefreshHelp'))))
  a.function('Tick',0,tick)
  def complete(a):
   a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True);a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','');a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show');footer.apply(a)
  a.function('OnAnimateInComplete',0,complete)
  def back(a):
   # Navigation events are supplied by ION; a literal "Back" is not the
   # controller's event identifier on every build. Both ESC and BACK use this
   # route, including while the native view is still waiting for its data.
   a.when(('bin',17,T('exiting'),T('backRequested')),lambda a:a.ret(True))
   a.set(R(1),'backRequested',True)
   a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'');a.ret(True)
  a.function('Back',0,back)
  def key(a):
   a.when(b.equal(CALL(PATH('Key'),'getCode'),27),lambda a:a.do(R(1),'Back'))
  a.function('onKeyDown',0,key)
  def event(a):
   a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(R(1),'Back'),a.ret(True)));a.ret(True)
  a.function('LocalEventHandler',2,event)
  a.function('getHelpContext',0,lambda a:a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in [('ADVANCE','Selecionar'),('BACK','Voltar'),('LAS_UD','Navegar'),('LAS_LR','Alterar'),('RAS_UD','Rolar clubes')]))))
  def shutdown(a):
   a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None);a.do(PATH('Key'),'removeListener',R(1));footer.restore(a);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
  a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration
 return script


def build(game,output,name):
 node=dict(type='action',index=0,x=0,y=0,w=1,h=1,color='#ffffff',ink='#ffffff',text='',size=1)
 return native.build(game,output,[dict(key='options',nodes=[node],actions=[dict(target='leave')])],{},script_factory=script_for(name),full_name='game.screens.career.server16.'+name)


def layout(raw):
 root=ET.fromstring(raw);office=root.find('panel_3');used={n.get('ID') for n in root.iter()}|{n.get('tileid') for n in root.iter('tileid')}
 for name,event,tile_name,title,description in PAGES:
  if any(n.get('DESTINATION')==event for n in root.iter()):continue
  tile=next(t for t in office.findall('tile') if t.find('tileid').get('NAME')==tile_name)
  settings=tile.find('settings');settings.set('FILE_PATH','TILE_NESTED');settings.set('ENABLE_CYCLING','TRUE')
  main=tile.find('main_tile');main.set('SUBTILE_TYPE','TILE')
  if not main.get('ID'):main.set('ID',tile.find('tileid').get('tileid'))
  number=sum(n.tag.startswith('subtile') for n in tile)+1;ident=next(str(i) for i in range(1950,1999) if str(i) not in used);used.add(ident)
  slide=ET.SubElement(tile,'subtile'+str(number),SUBTILE_TYPE='TILE',DESTINATION=event,FG_PATH='',BG_ICON=main.get('BG_ICON','Settings_Small'),ID=ident)
  ET.SubElement(slide,'data',ID='TITLE',TYPE='title',PARAM=title,TRANSLATE='FALSE',FORMAT='HS',WIDTH='370',HEIGHT='48',X='18',Y='16')
  ET.SubElement(slide,'data',ID='CAREER_OPTIONS_DESCRIPTION',TYPE='text',PARAM=description,TRANSLATE='FALSE',FORMAT='I',WIDTH='365',HEIGHT='68',X='18',Y='74')
  tile.find('number_of_subtiles').set('LENGTH',str(number))
 return ET.tostring(root,encoding='utf-8',xml_declaration=True)


def navigation(raw):
 nav=read_nav(raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw);hosts=[n for n in walk(nav) if any(t.get('event')=='Server16EnterBankLoans' for t in n.get('transitions',[]))];owners=[n for n in walk(nav) if any(s.get('name')=='Server16BankLoans' for s in n.get('states',[]))]
 if len(hosts)!=1 or len(owners)!=1:raise ValueError('Navegação de carreira incompatível')
 for name,event,*_ in PAGES:
  state='Server16'+name
  if not any(t.get('event')==event for t in hosts[0]['transitions']):hosts[0]['transitions'].append(dict(event=event,targets=[state]))
  if not any(s.get('name')==state for s in owners[0]['states']):owners[0]['states'].append(dict(name=state,type='external',file='/careerMode/server16'+name+'Flow.nav',outputs=dict(back='MainMenuHub',Back='MainMenuHub')))
 return (json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode('utf8')


def stage(game,output):
 game,output=Path(game),Path(output);files={XML:layout((game/XML).read_bytes()),NAV:navigation((game/NAV).read_bytes())}
 for name,event,*_ in PAGES:
  page='game/screens/career/server16/'+name
  flow=dict(name='Server16'+name+'Flow',initial=dict(targets=['Options']),states=[dict(name='Options',onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',page]],['loadView',['background','BOOTFLOW']]],onExit=[['unloadView',['screen']],['unloadScreenController',['Calendar']],['unloadView',['background']]],transitions=[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])
  files['data/ui/nav/careermode/server16'+name.lower()+'flow.nav']=(json.dumps(flow,ensure_ascii=False,indent=2)+'\n').encode('utf8')
  target=output/'data/ui/game/screens/career/server16'/(name.lower()+'.big');target.parent.mkdir(parents=True,exist_ok=True);build(game,target,name)
 for rel,raw in files.items():target=output/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 return list(files)
