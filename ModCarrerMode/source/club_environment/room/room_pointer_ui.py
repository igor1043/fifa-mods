"""Local APT pointer dispatch; shared by mouse hit areas and native clip events."""
import build_screen as b
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;EQ=b.equal
ACTION_Y=930
ACTIONS=((0,'sceneButton',1030,180),(1,'playersButton',1230,300),(2,'freeButton',1550,280),(3,'settingsButton',650,355))
def methods(a,settings,v3):
    def both(x,y):return ('bin',16,x,y)
    def rect(x,y,w,h):
        return both(both(('not',('bin',72,T('_xmouse'),x)),('bin',72,T('_xmouse'),b.plus(x,w))),both(('not',('bin',72,T('_ymouse'),y)),('bin',72,T('_ymouse'),b.plus(y,h))))
    def hit(a):
        a.when(both(T('freeCameraOpen'),('not',T('settingsOpen'))),lambda a:a.ret(-1))
        a.when(T('roomPlayersOpen'),lambda a:a.ret(-1))
        def settings_hit(a):
            for code,x in ((403,1104),(404,1712)):
                a.when(rect(x,248,48,39),lambda a,code=code:a.ret(code))
            for i in range(len(settings)):
                visible=P(P(T('roomSettings'),'setting'+str(i)),'_visible')
                y=b.plus(180,P(P(T('roomSettings'),'setting'+str(i)),'_y'))
                a.when(both(visible,rect(1104,y,656,72)),lambda a,i=i:(a.when(rect(1114,b.plus(y,26),48,39),lambda a:a.ret(200+2*i)),a.ret(201+2*i)))
            for code,x,y,w,h in ((400,1104,758,308,48),(401,1452,758,308,48)):
                a.when(rect(x,y,w,h),lambda a,code=code:a.ret(code))
            a.when(both(('bin',103,T('settingsMaxOffset'),0),rect(1770,320,20,374)),lambda a:a.ret(402))
            a.ret(-1)
        if v3:a.when(T('settingsOpen'),settings_hit)
        def scenes_hit(a):
            for i in range(5):
                index=b.plus(('bin',12,T('scenePage'),5),i)
                a.when(both(('bin',72,index,P(T('sceneItems'),'length')),rect(1284,318+68*i,471,63)),lambda a,i=i:a.ret(100+i))
            for code,x,y in ((110,1284,722),(111,1544,722),(112,1544,230)):
                visible=True if code==112 else ('bin',103,P(T('sceneItems'),'length'),5)
                a.when(both(visible,rect(x,y,212,32)),lambda a,code=code:a.ret(code))
            a.ret(-1)
        a.when(T('modalOpen'),scenes_hit)
        for code,_,x,w in ACTIONS[:4 if v3 else 3]:a.when(rect(x,ACTION_Y,w,48),lambda a,code=code:a.ret(code))
        a.ret(-1)
    a.function('RoomPointerTarget',0,hit)
    def activate(a):
        # Native onRelease and Mouse listener can arrive in either order.
        # A press/release cycle may apply exactly one command.
        a.when(both(T('roomPointerCycle'),T('roomPointerHandled')),lambda a:a.ret())
        a.when(T('roomPointerCycle'),lambda a:a.set(R(1),'roomPointerHandled',True))
        for code,method in ((0,'OpenScenes'),(1,'OpenPlayers'),(2,'OpenFreeCamera'),(3,'OpenRoomSettings'),(110,'ShiftScene'),(111,'ShiftScene'),(112,'CloseScenes'),(400,'CloseRoomSettings'),(401,'ApplyRoomSettings')):
            args=(-5,) if code==110 else (5,) if code==111 else ()
            a.when(EQ(R(2),code),lambda a,method=method,args=args:(a.do(R(1),method,*args),a.ret()))
        for code,delta in ((403,-1),(404,1)):
            a.when(EQ(R(2),code),lambda a,delta=delta:(a.do(R(1),'ShiftSettingsGroup',delta),a.ret()))
        for i in range(5):
            a.when(EQ(R(2),100+i),lambda a,i=i:(a.set(R(1),'sceneFocus',b.plus(('bin',12,T('scenePage'),5),i)),a.do(R(1),'ApplyScene'),a.ret()))
        for i in range(len(settings)):
            for offset,delta in ((0,-1),(1,1)):a.when(EQ(R(2),200+2*i+offset),lambda a,i=i,delta=delta:(a.do(R(1),'ShiftRoomSetting',i,delta),a.ret()))
    a.function('ActivateRoomPointer',1,activate)
    def down(a):
        a.set(R(1),'roomPointerCycle',True);a.set(R(1),'roomPointerHandled',False)
        a.set(R(1),'roomPointerPressed',CALL(R(1),'RoomPointerTarget'))
        a.when(EQ(T('roomPointerPressed'),402),lambda a:(a.set(R(1),'settingsDragging',True),a.do(R(1),'DragSettingsScroll')))
    a.function('onMouseDown',0,down)
    def up(a):
        a.when(T('settingsDragging'),lambda a:(a.set(R(1),'settingsDragging',False),a.set(R(1),'onMouseMove',T('RoomMouseMove')),a.set(R(1),'roomPointerHandled',True),a.ret()))
        a.when(T('roomPointerHandled'),lambda a:a.ret())
        a.set(R(1),'roomPointerReleased',CALL(R(1),'RoomPointerTarget'))
        a.when(both(('not',('bin',72,T('roomPointerReleased'),0)),EQ(T('roomPointerPressed'),T('roomPointerReleased'))),lambda a:a.do(R(1),'ActivateRoomPointer',T('roomPointerReleased')))
    a.function('onMouseUp',0,up)
    def move(a):
        a.when(T('settingsDragging'),lambda a:(a.do(R(1),'DragSettingsScroll'),a.ret()))
        a.set(R(1),'roomPointerHover',CALL(R(1),'RoomPointerTarget'))
        group_hover=('bin',17,EQ(T('roomPointerHover'),403),EQ(T('roomPointerHover'),404))
        a.when(both(group_hover,('not',EQ(T('settingsFocus'),-1))),lambda a:(a.set(R(1),'settingsFocus',-1),a.do(R(1),'RefreshRoomSettings'),a.ret()))
        for code,_,_,_ in ACTIONS[:4 if v3 else 3]:
            a.when(both(EQ(T('roomPointerHover'),code),('not',EQ(T('roomActionFocus'),code))),lambda a,code=code:(a.set(R(1),'roomActionFocus',code),a.do(R(1),'RefreshRoomActions'),a.ret()))
        for i in range(5):
            index=b.plus(('bin',12,T('scenePage'),5),i)
            a.when(both(EQ(T('roomPointerHover'),100+i),('not',EQ(T('sceneFocus'),index))),lambda a,index=index:(a.set(R(1),'sceneFocus',index),a.do(R(1),'RefreshSceneModal'),a.ret()))
        for i in range(len(settings)):
            hover=('bin',17,EQ(T('roomPointerHover'),200+2*i),EQ(T('roomPointerHover'),201+2*i))
            a.when(both(hover,('not',EQ(T('settingsFocus'),i))),lambda a,i=i:(a.set(R(1),'settingsFocus',i),a.do(R(1),'RefreshRoomSettings'),a.ret()))
    a.function('RoomMouseMove',0,move)
