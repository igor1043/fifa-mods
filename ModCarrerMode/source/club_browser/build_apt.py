"""Native transparent APT lifecycle and original FIFA input legends."""
from pathlib import Path
import os,sys

SOURCE=Path(__file__).resolve().parents[1]
ENV=SOURCE/'club_environment'
os.environ.setdefault('SERVER16_GAME_ROOT',str(SOURCE.parents[1]))
sys.path[:0]=[str(SOURCE),str(ENV),str(ENV/'vendor'),str(ENV/'bank'),str(ENV/'preview'),str(ENV/'market')]
import native_screen as native
import native_roster_footer as roster_footer
b=native.b
from build_preview import Code
CLASS=('game','screens','career','server16','ClubBrowser')
FULL='.'.join(CLASS);PAGE='/'.join(CLASS)
ROOM_CLASS=('game','screens','career','server16','DressingRoomPlayers');ROOM_FULL='.'.join(ROOM_CLASS);ROOM_PAGE='/'.join(ROOM_CLASS)
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION

def script(data,dictionaries,scenes,*,from_room=False):
    CLASS=ROOM_CLASS if from_room else globals()['CLASS'];FULL='.'.join(CLASS)
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
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'navPage',0);a.set(R(1),'hubIndex',1)
        a.set(R(1),'onEnterFrame',T('Ready'));a.do(R(1),'Ready')
    a.function(CLASS[-1],0,ctor,True)
    a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    def ready(a):
        def bind(a):
            a.set(R(1),'onEnterFrame',T('Tick'))
            for i,handler in enumerate(('MouseOpen','MouseXI','MouseRoster','MouseCoach','MouseMascot')):
                button=P(T('scene0'),'action'+str(i));a.set(button,'_alpha',0);a.set(button,'owner',R(1));a.set(button,'onRelease',T(handler))
                if i:a.set(button,'onRollOver',T('HoverXI' if i==1 else 'HoverRoster' if i==2 else 'HoverCoach' if i==3 else 'HoverMascot'))
            a.do(R(1),'SetPage',3 if from_room else 0)
            a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
            a.do(M('HelpManager'),'Update')
            a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
            a.do(R(1),'OnAnimateInComplete')
        a.when(T('bound'),lambda a:a.ret())
        a.when(P(T('scene0'),'action0'),lambda a:(a.set(R(1),'bound',True),bind(a)))
    a.function('Ready',0,ready)
    def tick(a):
        a.when(T('helpDelay'),lambda a:(a.set(R(1),'helpDelay',('bin',11,T('helpDelay'),1)),a.when(('bin',17,b.equal(T('helpDelay'),87),('bin',17,b.equal(T('helpDelay'),60),b.equal(T('helpDelay'),0))),lambda a:a.do(R(1),'RefreshHelp'))))
    a.function('Tick',0,tick)
    # Verified against FIFA's own HelpManager: Update rebuilds items but does
    # not show a hidden display. A transparent custom screen supplies its own
    # help source so an underlying Calendar/controller context cannot win.
    def refresh_help(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show')
        a.when(('bin',17,b.equal(T('navPage'),5),('bin',17,b.equal(T('navPage'),3),b.equal(T('navPage'),4))),roster_footer.apply,roster_footer.restore)
    a.function('RefreshHelp',0,refresh_help)
    def complete(a):
        a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
        a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
        a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
        a.set(R(1),'helpDelay',90);a.do(R(1),'RefreshHelp')
    a.function('OnAnimateInComplete',0,complete)
    def publish(a):a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser',R(2))
    a.function('Publish',1,publish)
    def page(a):
        a.set(R(1),'helpDelay',90);a.set(R(1),'navPage',R(2));a.set(P(T('scene0'),'action0'),'_visible',b.equal(R(2),0))
        for i in (1,2,3,4):a.set(P(T('scene0'),'action'+str(i)),'_visible',b.equal(R(2),1))
        a.when(b.equal(R(2),1),lambda a:a.do(R(1),'PublishFocus'))
        a.do(R(1),'RefreshHelp')
    a.function('SetPage',1,page)
    a.function('PublishFocus',0,lambda a:a.do(R(1),'Publish',('index',('array',('focus_xi','focus_roster','focus_coach','focus_mascot')),T('hubIndex'))))
    def open_detail(a):
        a.when(b.equal(T('navPage'),0),lambda a:(a.do(R(1),'Publish','open'),a.do(R(1),'SetPage',1)))
    a.function('OpenDetail',0,open_detail)
    def open_choice(a,index,page,command):
        def chosen(a):
            a.set(R(1),'hubIndex',index);a.do(R(1),'PublishFocus')
            a.do(R(1),'SetPage',page);a.do(R(1),'Publish',command)
        a.when(b.equal(T('navPage'),1),chosen)
    for name,index,page,command in (('OpenXI',0,2,'xi'),('OpenRoster',1,3,'roster'),('OpenCoach',2,5,'coach'),('OpenMascot',3,6,'mascot')):
        a.function(name,0,lambda a,index=index,page=page,command=command:open_choice(a,index,page,command))
    for name,target in (('MouseOpen','OpenDetail'),('MouseXI','OpenXI'),('MouseRoster','OpenRoster'),('MouseCoach','OpenCoach'),('MouseMascot','OpenMascot')):
        a.function(name,0,lambda a,target=target:a.do(P(R(1),'owner'),target))
    for name,index,command in (('HoverXI',0,'focus_xi'),('HoverRoster',1,'focus_roster'),('HoverCoach',2,'focus_coach'),('HoverMascot',3,'focus_mascot')):
        a.function(name,0,lambda a,index=index,command=command:a.when(b.equal(P(P(R(1),'owner'),'navPage'),1),lambda a:(a.set(P(R(1),'owner'),'hubIndex',index),a.do(P(R(1),'owner'),'PublishFocus'))))
    def back(a):
        a.when(T('exiting'),lambda a:a.ret(True))
        a.when(b.equal(T('navPage'),0),lambda a:(a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.ret(True)))
        a.when(b.equal(T('navPage'),4),lambda a:(a.do(R(1),'SetPage',3),a.do(R(1),'Publish','back'),a.ret(True)))
        if from_room:a.when(b.equal(T('navPage'),3),lambda a:(a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.ret(True)))
        a.do(R(1),'Publish','back')
        a.when(b.equal(T('navPage'),1),lambda a:a.do(R(1),'SetPage',0),lambda a:a.do(R(1),'SetPage',1))
        a.ret(True)
    a.function('Back',0,back)
    def select(a):
        a.when(b.equal(T('navPage'),0),lambda a:(a.do(R(1),'OpenDetail'),a.ret(True)))
        a.when(b.equal(T('navPage'),1),lambda a:(a.when(b.equal(T('hubIndex'),0),lambda a:a.do(R(1),'OpenXI'),lambda a:a.when(b.equal(T('hubIndex'),1),lambda a:a.do(R(1),'OpenRoster'),lambda a:a.when(b.equal(T('hubIndex'),2),lambda a:a.do(R(1),'OpenCoach'),lambda a:a.do(R(1),'OpenMascot')))),a.ret(True)))
        a.when(b.equal(T('navPage'),3),lambda a:(a.do(R(1),'SetPage',4),a.do(R(1),'Publish','detail'),a.ret(True)))
        a.when(b.equal(T('navPage'),2),lambda a:a.do(R(1),'Publish','refresh'));a.ret(True)
    a.function('Select',0,select)
    def event(a):
        a.when(('bin',16,b.equal(T('navPage'),6),b.equal(R(2),P(M('InputCodes'),'OPTION_TOP'))),lambda a:(a.do(R(1),'Publish','mascot_center'),a.ret(True)))
        a.when(('bin',16,b.equal(T('navPage'),0),b.equal(R(2),P(M('InputCodes'),'OPTION_TOP'))),lambda a:(a.do(R(1),'Publish','globe_mode'),a.ret(True)))
        for code,command in (('L2','tab_prev'),('R2','tab_next'),('OPTION_TOP','sort')):
            a.when(('bin',16,P(M('InputCodes'),code),b.equal(R(2),P(M('InputCodes'),code))),lambda a,command=command:(a.when(('bin',17,b.equal(T('navPage'),5),('bin',17,b.equal(T('navPage'),3),b.equal(T('navPage'),4))),lambda a:a.do(R(1),'Publish',command)),a.ret(True)))
        a.when(b.equal(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(R(1),'Back'),a.ret(True)))
        for code in ('ADVANCE','PRIMARY_SELECT'):
            a.when(b.equal(R(2),P(M('InputCodes'),code)),lambda a:(a.do(R(1),'Select'),a.ret(True)))
        for code,command,direction in (('LEFT','left',-1),('LAS_LEFT','left',-1),('RIGHT','right',1),('LAS_RIGHT','right',1)):
            def horizontal(a,command=command,direction=direction):
                def choice(a):
                    a.set(R(1),'hubIndex',('bin',63,('bin',10,('bin',10,T('hubIndex'),direction),4),4))
                    a.do(R(1),'PublishFocus');a.ret(True)
                a.when(b.equal(T('navPage'),1),choice)
                a.when(b.equal(T('navPage'),3),lambda a:a.do(R(1),'Publish',command));a.ret(True)
            cond=('bin',16,P(M('InputCodes'),code),b.equal(R(2),P(M('InputCodes'),code)))
            a.when(cond,horizontal)
        for code,command in (('UP','prev'),('LAS_UP','prev'),('DOWN','next'),('LAS_DOWN','next')):
            cond=('bin',16,P(M('InputCodes'),code),b.equal(R(2),P(M('InputCodes'),code)))
            a.when(cond,lambda a,command=command:(a.when(('bin',17,b.equal(T('navPage'),3),b.equal(T('navPage'),5)),lambda a:a.do(R(1),'Publish',command)),a.ret(True)))
        a.ret(True)
    a.function('LocalEventHandler',2,event)
    def help(a):
        def items(a,values):a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in values)))
        a.when(b.equal(T('navPage'),1),lambda a:items(a,[('ADVANCE','Selecionar'),('BACK','Voltar'),('LAS_LR','Opções')]))
        a.when(b.equal(T('navPage'),2),lambda a:items(a,[('BACK','Voltar'),('ADVANCE','Atualizar')]))
        a.when(b.equal(T('navPage'),3),lambda a:items(a,[('ADVANCE','Detalhes'),('BACK','Voltar'),('LAS_UD','Elenco'),('L2R2','Abas'),('RAS_LR','Girar'),('L1R1','Zoom')]))
        a.when(b.equal(T('navPage'),4),lambda a:items(a,[('BACK','Voltar'),('L2R2','Abas'),('RAS_LR','Girar'),('L1R1','Zoom')]))
        a.when(b.equal(T('navPage'),6),lambda a:items(a,[('BACK','Voltar'),('RAS_LR','Girar'),('L1R1','Zoom'),('OPTION_TOP','Centralizar')]))
        a.when(b.equal(T('navPage'),5),lambda a:items(a,[('BACK','Voltar'),('L2R2','Abas'),('LAS_UD','Percorrer'),('RAS_LR','Girar'),('L1R1','Zoom')]))
        items(a,[('ADVANCE','Ver equipe'),('BACK','Voltar'),('LAS_LR','Percorrer'),('L2R2','Ligas'),('L1R1','Zoom'),('OPTION_TOP','Clubes / seleções')])
    a.function('getHelpContext',0,help)
    def shutdown(a):
        a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True)
        a.set(R(1),'onEnterFrame',None)
        roster_footer.restore(a);a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
    a.function('OnExitScreen',0,shutdown);a.op(0);a.finish()
    a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,registration

def build(game,output,*,from_room=False):
    # No opaque card/background and no per-club artwork embedded in the BIG.
    # Transparent hit area on the centre of the club card, matching the native
    # 1600x900 layout at the APT's 1920x1080 design resolution.
    action=dict(type='action',index=0,x=134.4,y=439.2,w=364.8,h=408,color='#ffffff',ink='#ffffff',text='',size=1)
    nodes=[action]+[dict(type='action',index=i+1,x=72+i*450,y=330,w=426,h=408,color='#ffffff',ink='#ffffff',text='',size=1) for i in range(4)]
    return native.build(game,output,[dict(key='clubs',nodes=nodes,actions=[dict(target='detail'),dict(target='xi'),dict(target='roster'),dict(target='coach'),dict(target='mascot')])],{},script_factory=lambda data,dictionaries,scenes:script(data,dictionaries,scenes,from_room=from_room),full_name=ROOM_FULL if from_room else FULL)

if __name__=='__main__':
    import json
    print(json.dumps(build(Path(sys.argv[1]),Path(sys.argv[2])),ensure_ascii=False))
