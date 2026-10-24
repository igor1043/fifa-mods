"""Native transparent APT lifecycle and original FIFA input legends."""
from pathlib import Path
import os,sys

SOURCE=Path(__file__).resolve().parents[1]
ENV=SOURCE/'club_environment'
os.environ.setdefault('SERVER16_GAME_ROOT',str(SOURCE.parents[1]))
sys.path[:0]=[str(SOURCE),str(ENV),str(ENV/'vendor'),str(ENV/'bank'),str(ENV/'preview'),str(ENV/'market')]
import native_screen as native
b=native.b
from build_preview import Code
CLASS=('game','screens','career','server16','ClubBrowser')
FULL='.'.join(CLASS);PAGE='/'.join(CLASS)
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION

def script(data,dictionaries,scenes):
    b.CLASS=CLASS;b.FULL=FULL
    a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
    for index,name in enumerate(CLASS[:-1]):
        parent=b.GLOBAL if index==0 else PATH(*CLASS[:index])
        a.when(P(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
    def ctor(a):
        a.op(89);a.reg(2);a.op(118);a.op(93)
        a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
        a.do(R(1),'Initialize',FULL,None,True)
        a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
        a.set(R(1),'onEnterFrame',T('Ready'));a.do(R(1),'Ready')
    a.function(CLASS[-1],0,ctor,True)
    a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    def ready(a):
        def bind(a):
            a.set(R(1),'onEnterFrame',None)
            button=P(T('scene0'),'action0');a.set(button,'_alpha',0);a.set(button,'owner',R(1));a.set(button,'onRelease',T('MouseOpen'))
            a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
            a.do(M('HelpManager'),'Update')
            a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
            a.do(R(1),'OnAnimateInComplete')
        a.when(T('bound'),lambda a:a.ret())
        a.when(P(T('scene0'),'action0'),lambda a:(a.set(R(1),'bound',True),bind(a)))
    a.function('Ready',0,ready)
    def complete(a):
        a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
        a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
        a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
    a.function('OnAnimateInComplete',0,complete)
    def open_detail(a):a.set(R(1),'detailOpen',True);a.do(M('HelpManager'),'Update')
    a.function('OpenDetail',0,open_detail)
    a.function('MouseOpen',0,lambda a:a.do(P(R(1),'owner'),'OpenDetail'))
    def event(a):
        def back(a):
            a.when(T('exiting'),lambda a:a.ret(True))
            a.when(T('detailOpen'),lambda a:(a.set(R(1),'detailOpen',False),a.do(M('HelpManager'),'Update'),a.ret(True)))
            a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),'');a.ret(True)
        a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),back)
        for code in ('ADVANCE','PRIMARY_SELECT'):
            a.when(b.equal(R(2),P(M('InputCodes'),code)),lambda a:(a.do(R(1),'OpenDetail'),a.ret(True)))
        # Other navigation is handled only by this page's native renderer.
        a.ret(True)
    a.function('LocalEventHandler',2,event)
    def help(a):
        def items(a,values):a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in values)))
        a.when(T('detailOpen'),lambda a:items(a,[('BACK','Voltar'),('ADVANCE','Atualizar')]))
        items(a,[('ADVANCE','Ver titulares'),('BACK','Voltar'),('LAS_LR','Percorrer'),('L2R2','Ligas'),('L1R1','Zoom')])
    a.function('getHelpContext',0,help)
    def shutdown(a):
        a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True)
        a.set(R(1),'onEnterFrame',None)
        a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
    a.function('OnExitScreen',0,shutdown);a.op(0);a.finish()
    a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,registration

def build(game,output):
    # No opaque card/background and no per-club artwork embedded in the BIG.
    # Transparent hit area on the centre of the club card, matching the native
    # 1600x900 layout at the APT's 1920x1080 design resolution.
    action=dict(type='action',index=0,x=134.4,y=439.2,w=364.8,h=408,color='#ffffff',ink='#ffffff',text='',size=1)
    return native.build(game,output,[dict(key='clubs',nodes=[action],actions=[dict(target='detail')])],{},script_factory=script,full_name=FULL)

if __name__=='__main__':
    import json
    print(json.dumps(build(Path(sys.argv[1]),Path(sys.argv[2])),ensure_ascii=False))
