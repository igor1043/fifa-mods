"""Native APT lifecycle and original FIFA HelpManager for career competitions."""
from pathlib import Path
import build_apt as browser
native=browser.native;b=browser.b
from build_preview import Code
import native_roster_footer as footer
CLASS=('game','screens','career','server16','CareerCompetitions');FULL='.'.join(CLASS);PAGE='/'.join(CLASS)
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION

def script(data,dictionaries,scenes):
 b.CLASS=CLASS;b.FULL=FULL;a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
 for index,name in enumerate(CLASS[:-1]):
  parent=b.GLOBAL if index==0 else PATH(*CLASS[:index]);a.when(P(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
 def ctor(a):
  a.op(89);a.reg(2);a.op(118);a.op(93)
  a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
  a.do(R(1),'Initialize',FULL,None,True);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
  a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'expanded',False);a.set(R(1),'onEnterFrame',T('Ready'));a.do(R(1),'Ready')
 a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
 def ready(a):
  def bind(a):
   a.set(R(1),'bound',True);a.set(T('scene0'),'_visible',True);a.set(R(1),'onEnterFrame',T('Tick'))
   for i,handler in ((0,None),(1,'OpenBracket'),(2,'CloseBracket')):
    button=P(T('scene0'),'action'+str(i));a.set(button,'_alpha',0);a.set(button,'owner',R(1))
    if handler:a.set(button,'onRelease',T('Mouse'+handler))
   a.set(P(T('scene0'),'action2'),'_visible',False)
   a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
   a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
  a.when(T('bound'),lambda a:a.ret());a.when(P(T('scene0'),'action0'),bind)
 a.function('Ready',0,ready)
 def refresh(a):
  a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show');footer.apply(a)
 a.function('RefreshHelp',0,refresh)
 def tick(a):
  a.when(T('helpDelay'),lambda a:(a.set(R(1),'helpDelay',('bin',11,T('helpDelay'),1)),a.when(('bin',17,b.equal(T('helpDelay'),87),('bin',17,b.equal(T('helpDelay'),60),b.equal(T('helpDelay'),0))),lambda a:a.do(R(1),'RefreshHelp'))))
 a.function('Tick',0,tick)
 def complete(a):
  a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
  a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
  a.set(R(1),'helpDelay',90);a.do(R(1),'RefreshHelp')
 a.function('OnAnimateInComplete',0,complete)
 def opened(a):
  a.set(R(1),'expanded',True);a.set(P(T('scene0'),'action1'),'_visible',False);a.set(P(T('scene0'),'action2'),'_visible',True)
  a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser','comp_bracket');a.do(R(1),'RefreshHelp')
 a.function('OpenBracket',0,opened)
 def closed(a):
  a.set(R(1),'expanded',False);a.set(P(T('scene0'),'action1'),'_visible',True);a.set(P(T('scene0'),'action2'),'_visible',False)
  a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser','comp_close');a.do(R(1),'RefreshHelp')
 a.function('CloseBracket',0,closed)
 for target in ('OpenBracket','CloseBracket'):a.function('Mouse'+target,0,lambda a,target=target:a.do(P(R(1),'owner'),target))
 def event(a):
  a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.when(T('expanded'),lambda a:(a.do(R(1),'CloseBracket'),a.ret(True))),a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.ret(True)))
  for code in ('ADVANCE','PRIMARY_SELECT'):
   a.when(b.equal(R(2),P(M('InputCodes'),code)),lambda a:(a.when(T('expanded'),lambda a:a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser','comp_center'),lambda a:a.do(R(1),'OpenBracket')),a.ret(True)))
  a.when(b.equal(R(2),P(M('InputCodes'),'OPTION_TOP')),lambda a:a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser','comp_mode'))
  # DirectInput/XInput edges are read once by the native screen for navigation.
  # Swallow the underlying Calendar events, avoiding double changes of tab.
  a.ret(True)
 a.function('LocalEventHandler',2,event)
 def help(a):
  expanded=[('BACK','Voltar'),('LAS_LR','Movimentar'),('L1R1','Zoom'),('ADVANCE','Centralizar')]
  a.when(T('expanded'),lambda a:a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in expanded))))
  values=[('ADVANCE','Ampliar'),('BACK','Voltar'),('L2R2','Competições'),('LAS_UD','Tabela'),('LAS_LR','Grupos / fases'),('L1R1','Estatísticas'),('OPTION_TOP','Grupos / chaves'),('RAS_UD','Ranking')]
  a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in values)))
 a.function('getHelpContext',0,help)
 def shutdown(a):
  a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None);footer.restore(a);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
 a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration

def build(game,output):
 nodes=[dict(type='action',index=i,x=x,y=y,w=w,h=h,color='#ffffff',ink='#ffffff',text='',size=1) for i,(x,y,w,h) in enumerate(((0,0,1,1),(600,198,228,38),(1764,42,78,66)))]
 return native.build(game,output,[dict(key='competitions',nodes=nodes,actions=[dict(target='leave') for _ in nodes])],{},script_factory=script,full_name=FULL)
