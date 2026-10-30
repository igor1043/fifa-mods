"""Two native pages with FIFA's original keyboard/controller help assets."""
from pathlib import Path
import build_apt as browser
from build_preview import Code
import native_roster_footer as footer
native=browser.native;b=browser.b
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION

def full(kind):return 'game.screens.career.server16.'+('WorldClubRanking' if kind=='clubs' else 'WorldNationRanking')

def script(data,dictionaries,scenes,kind):
    FULL=full(kind);CLASS=tuple(FULL.split('.'));b.CLASS=CLASS;b.FULL=FULL
    a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
    for i,name in enumerate(CLASS[:-1]):
        parent=b.GLOBAL if i==0 else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
    def ctor(a):
        a.op(89);a.reg(2);a.op(118);a.op(93)
        a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
        a.do(R(1),'Initialize',FULL,None,True);a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'onEnterFrame',T('Ready'));a.do(R(1),'Ready')
    a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    def ready(a):
        a.when(T('bound'),lambda a:a.ret())
        def bind(a):
            a.set(R(1),'bound',True);a.set(P(T('scene0'),'action0'),'_alpha',0);a.set(R(1),'onEnterFrame',T('Tick'))
            a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
            a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')));a.do(R(1),'OnAnimateInComplete')
        a.when(P(T('scene0'),'action0'),bind)
    a.function('Ready',0,ready)
    def refresh(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show');footer.apply(a)
    a.function('RefreshHelp',0,refresh)
    def tick(a):a.when(T('helpDelay'),lambda a:(a.set(R(1),'helpDelay',('bin',11,T('helpDelay'),1)),a.when(('bin',17,b.equal(T('helpDelay'),87),b.equal(T('helpDelay'),0)),lambda a:a.do(R(1),'RefreshHelp'))))
    a.function('Tick',0,tick)
    def complete(a):
        a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
        a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','');a.set(R(1),'helpDelay',90);a.do(R(1),'RefreshHelp')
    a.function('OnAnimateInComplete',0,complete)
    def event(a):
        a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.ret(True)))
        for code,command in (('ADVANCE','rank_filter'),('PRIMARY_SELECT','rank_filter'),('OPTION_LEFT','rank_top'),('OPTION_TOP','rank_mine')):
            a.when(b.equal(R(2),P(M('InputCodes'),code)),lambda a,command=command:(a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser',command),a.ret(True)))
        # Native edges own scrolling/tabs, avoiding double commands from APT.
        a.ret(True)
    a.function('LocalEventHandler',2,event)
    def help(a):
        values=[('ADVANCE','Região / liga'),('BACK','Voltar'),('LAS_UD','Classificação'),('L1R1','Rankings'),('L2R2','Filtro'),('OPTION_LEFT','Topo'),('OPTION_TOP','Minha posição'),('RAS_UD','Páginas')]
        a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in values)))
    a.function('getHelpContext',0,help)
    def shutdown(a):
        a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.set(R(1),'onEnterFrame',None);footer.restore(a);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
    a.function('OnExitScreen',0,shutdown);a.op(0);a.finish();a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish();return start,registration

def build(game,output,kind):
    if kind not in ('clubs','nations'):raise ValueError(kind)
    action=dict(type='action',index=0,x=0,y=0,w=1,h=1,color='#ffffff',ink='#ffffff',text='',size=1)
    return native.build(game,output,[dict(key='ranking',nodes=[action],actions=[dict(target='leave')])],{},script_factory=lambda d,c,s:script(d,c,s,kind),full_name=full(kind))
