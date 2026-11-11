"""Grouped native dressing-room preferences with shared mouse/controller focus."""
import build_screen as b
import room_appearance as art
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;EQ=b.equal
ROW_Y=128;ROW_H=78;VISIBLE=5;TRACK_Y=140;TRACK_H=374


def groups(settings):
    return [(label,[i for i,row in enumerate(settings) if row['key'] in keys]) for label,keys in art.GROUPS]


def graphics(scope,place,clip,text,setting,arrow,action_button,panel,neutral,selected):
    parts=[place(panel,1,0,0,11,10.15),place(text('PERSONALIZAÇÃO DO VESTIÁRIO',656,40,27),2,24,17)]
    for i in range(len(scope.get('settings',[]))):parts.append(place(setting,10+i,24,ROW_Y+i*ROW_H,label='setting'+str(i)))
    parts.extend([place(neutral,40,690,TRACK_Y,.1,5.85,label='scrollTrack'),place(selected,41,690,TRACK_Y,.1,2,label='scrollThumb')])
    parts.extend([place(arrow,43,24,68,label='previousGroup'),place(arrow,44,632,68,label='nextGroup'),
                  place(text('',530,36,25),45,88,68,label='groupTitle')])
    parts.extend([place(action_button('Voltar',308),20,24,578,label='close'),place(action_button('Aplicar',308),21,372,578,label='apply'),place(text('As alterações serão usadas ao aplicar.',656,25,18),22,24,548,label='settingsHint')])
    return parts


def methods(a,scope,settings):
    if not settings:
        for name in ('OpenRoomSettings','CloseRoomSettings'):a.function(name,0,lambda a:a.ret())
        return
    sections=groups(settings);n=len(settings)
    def refresh(a):
        a.set(T('roomSettings'),'_visible',T('settingsOpen'));a.set(T('roomSettings'),'_alpha',100)
        a.set(P(T('roomSettings'),'settingsHint'),'text','As alterações serão usadas ao aplicar.')
        a.set(P(T('roomSettings'),'groupTitle'),'textColor',0x334b56)
        a.when(EQ(T('settingsFocus'),-1),lambda a:a.set(P(T('roomSettings'),'groupTitle'),'textColor',0xb9a274))
        for i,row in enumerate(settings):
            c=P(T('roomSettings'),'setting'+str(i));options=('array',tuple(('map',v) for v in row['options']))
            a.set(c,'_visible',False);a.set(P(c,'title'),'text',row['title']);a.set(P(c,'value'),'text',P(('index',options,T('settingIndex'+str(i))),'label'))
            a.set(P(c,'highlight'),'_alpha',0)
            a.when(EQ(T('settingsFocus'),i),lambda a,c=c:a.set(P(c,'highlight'),'_alpha',55))
            hint={'drawer_art':'Personalizada: use locker-box-front.png na pasta do clube.',
                  'table_top':'Personalizada: use table-top.png na pasta do clube.',
                  'door_finish':'Aplica a todas as portas. Personalizada: exit-door.png.'}.get(row['key'])
            if hint:a.when(EQ(T('settingsFocus'),i),lambda a,hint=hint:a.set(P(T('roomSettings'),'settingsHint'),'text',hint))
            for name,delta,label in [('previous',-1,'‹'),('next',1,'›')]:
                button=P(c,name);a.set(button,'owner',R(1));a.set(button,'row',i);a.set(button,'delta',delta)
                a.set(P(button,'label'),'text',label);a.set(button,'onRelease',T('SettingsArrowClick'))
        for g,(label,indices) in enumerate(sections):
            def section(a,g=g,label=label,indices=indices):
                maximum=max(0,len(indices)-VISIBLE)
                a.set(R(1),'settingsMaxOffset',maximum)
                a.set(P(T('roomSettings'),'groupTitle'),'text',f'{label}  ·  {g+1}/{len(sections)}')
                for pos,i in enumerate(indices):
                    a.when(EQ(T('settingsFocus'),i),lambda a,pos=pos:(
                        a.when(('bin',72,pos,T('settingsOffset')),lambda a:a.set(R(1),'settingsOffset',pos)),
                        a.when(('bin',103,pos,b.plus(T('settingsOffset'),VISIBLE-1)),lambda a:a.set(R(1),'settingsOffset',pos-VISIBLE+1))))
                for pos,i in enumerate(indices):
                    c=P(T('roomSettings'),'setting'+str(i))
                    a.set(c,'_visible',('bin',16,('not',('bin',72,pos,T('settingsOffset'))),('bin',72,pos,b.plus(T('settingsOffset'),VISIBLE))))
                    a.set(c,'_y',b.plus(ROW_Y,('bin',12,('bin',11,pos,T('settingsOffset')),ROW_H)))
                track=P(T('roomSettings'),'scrollTrack');thumb=P(T('roomSettings'),'scrollThumb')
                a.set(track,'_visible',maximum>0);a.set(thumb,'_visible',maximum>0)
                if maximum:
                    height=TRACK_H*VISIBLE/len(indices)
                    a.set(thumb,'_height',height);a.set(thumb,'_y',b.plus(TRACK_Y,('bin',12,T('settingsOffset'),(TRACK_H-height)/maximum)))
                    a.set(thumb,'owner',R(1));a.set(thumb,'onPress',T('SettingsScrollPress'));a.set(thumb,'onRelease',T('SettingsScrollRelease'));a.set(thumb,'onReleaseOutside',T('SettingsScrollRelease'))
            a.when(EQ(T('settingsGroup'),g),section)
        for name,code,label in [('previousGroup',403,'‹'),('nextGroup',404,'›')]:
            button=P(T('roomSettings'),name);a.set(button,'owner',R(1));a.set(button,'code',code)
            a.set(P(button,'label'),'text',label);a.set(button,'onRelease',T('SettingsGroupClick'))
        for offset,name,method in ((0,'close','SettingsCloseClick'),(1,'apply','SettingsApplyClick')):
            button=P(T('roomSettings'),name);a.set(button,'owner',R(1));a.set(button,'onRelease',T(method))
            a.set(P(button,'highlight'),'_alpha',0);a.set(P(button,'label'),'textColor',0x334b56)
            a.when(EQ(T('settingsFocus'),n+offset),lambda a,button=button:(a.set(P(button,'highlight'),'_alpha',100),a.set(P(button,'label'),'textColor',0x1f2c32)))
        a.do(b.MANAGER('HelpManager'),'Update')
    a.function('RefreshRoomSettings',0,refresh)
    def shift_group(a):
        a.set(R(1),'settingsGroup',('bin',63,b.plus(b.plus(T('settingsGroup'),R(2)),len(sections)),len(sections)))
        a.set(R(1),'settingsOffset',0)
        for g,(_,indices) in enumerate(sections):a.when(EQ(T('settingsGroup'),g),lambda a,indices=indices:a.set(R(1),'settingsFocus',indices[0]))
        a.do(R(1),'RefreshRoomSettings')
    a.function('ShiftSettingsGroup',1,shift_group)
    a.function('SettingsGroupClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',P(R(1),'code')))
    def move(a):
        for g,(_,indices) in enumerate(sections):
            order=[-1]+indices+[n,n+1]
            def advance(a,order=order):
                a.set(R(1),'settingsPosition',0)
                for pos,i in enumerate(order):a.when(EQ(T('settingsFocus'),i),lambda a,pos=pos:a.set(R(1),'settingsPosition',pos))
                index=('bin',63,b.plus(b.plus(T('settingsPosition'),R(2)),len(order)),len(order))
                a.set(R(1),'settingsFocus',('index',('array',tuple(order)),index))
            a.when(EQ(T('settingsGroup'),g),advance)
        a.do(R(1),'RefreshRoomSettings')
    a.function('MoveSettingFocus',1,move)
    def scroll(a):
        a.when(T('settingsOpen'),lambda a:None,lambda a:a.ret())
        a.set(R(1),'settingsOffset',CALL(PATH('Math'),'max',0,CALL(PATH('Math'),'min',T('settingsMaxOffset'),b.plus(T('settingsOffset'),R(2)))))
        for g,(_,indices) in enumerate(sections):a.when(EQ(T('settingsGroup'),g),lambda a,indices=indices:a.set(R(1),'settingsFocus',('index',('array',tuple(indices)),T('settingsOffset'))))
        a.do(R(1),'RefreshRoomSettings')
    a.function('ScrollRoomSettings',1,scroll)
    a.function('onMouseWheel',1,lambda a:a.do(R(1),'ScrollRoomSettings',('bin',12,R(2),-1)))
    def drag(a):
        a.when(('bin',16,T('settingsOpen'),T('settingsDragging')),lambda a:None,lambda a:a.ret())
        for g,(_,indices) in enumerate(sections):
            maximum=max(0,len(indices)-VISIBLE)
            if not maximum:continue
            height=TRACK_H*VISIBLE/len(indices)
            offset=CALL(PATH('Math'),'round',('bin',12,('bin',11,T('_ymouse'),180+TRACK_Y),maximum/(TRACK_H-height)))
            a.when(EQ(T('settingsGroup'),g),lambda a,offset=offset:(a.set(R(1),'settingsOffset',0),a.do(R(1),'ScrollRoomSettings',offset)))
    a.function('DragSettingsScroll',0,drag)
    a.function('SettingsScrollPress',0,lambda a:(a.set(P(R(1),'owner'),'settingsDragging',True),a.set(P(R(1),'owner'),'onMouseMove',P(P(R(1),'owner'),'DragSettingsScroll'))))
    a.function('SettingsScrollRelease',0,lambda a:(a.set(P(R(1),'owner'),'settingsDragging',False),a.set(P(R(1),'owner'),'onMouseMove',P(P(R(1),'owner'),'RoomMouseMove'))))
    def open_(a):
        for i in range(n):
            a.set(R(1),'settingIndex'+str(i),T('appliedSettingIndex'+str(i)));a.set(R(1),'customSettingIndex'+str(i),T('appliedCustomSettingIndex'+str(i)))
        a.set(R(1),'settingsGroup',0);a.set(R(1),'settingsFocus',sections[0][1][0]);a.set(R(1),'settingsOffset',0)
        a.set(R(1),'settingsOpen',True);a.set(R(1),'modalOpen',False);a.set(T('sceneModal'),'_visible',False)
        a.do(R(1),'PublishScene',-6);a.do(R(1),'RefreshRoomSettings');a.do(R(1),'RefreshRosterHelp')
    a.function('OpenRoomSettings',0,open_)
    a.function('CloseRoomSettings',0,lambda a:(a.set(R(1),'settingsOpen',False),a.set(R(1),'settingsDragging',False),a.set(R(1),'onMouseMove',T('RoomMouseMove')),a.set(T('roomSettings'),'_visible',False),a.do(R(1),'PublishScene',-7),a.do(R(1),'RefreshRosterHelp')))
    a.function('SettingsCloseClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',400))
    def apply(a):
        a.set(R(1),'appearanceDirty',False)
        for i in range(n):a.when(('not',EQ(T('settingIndex'+str(i)),T('appliedSettingIndex'+str(i)))),lambda a:a.set(R(1),'appearanceDirty',True))
        a.when(T('appearanceDirty'),lambda a:a.do(R(1),'PublishAppearance'))
        for i in range(n):
            a.set(R(1),'appliedSettingIndex'+str(i),T('settingIndex'+str(i)));a.set(R(1),'appliedCustomSettingIndex'+str(i),T('customSettingIndex'+str(i)))
        a.do(R(1),'CloseRoomSettings')
    a.function('ApplyRoomSettings',0,apply)
    a.function('SettingsApplyClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',401))
    a.function('SettingsArrowClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',b.plus(200,b.plus(('bin',12,P(R(1),'row'),2),('bin',13,b.plus(P(R(1),'delta'),1),2)))))
    def shift(a):
        for i,row in enumerate(settings):
            def change(a,i=i,row=row):
                group=next(g for g,(_,ids) in enumerate(sections) if i in ids)
                a.when(('not',EQ(T('settingsGroup'),group)),lambda a:(a.set(R(1),'settingsGroup',group),a.set(R(1),'settingsOffset',0)))
                count=len(row['options']);name='settingIndex'+str(i)
                a.set(R(1),'settingsFocus',i);a.set(R(1),name,('bin',63,b.plus(b.plus(T(name),R(3)),count),count))
                options=('array',tuple(('map',v) for v in row['options']))
                if row['key'] in ('finish','backs','floor','fascia'):
                    a.when(EQ(P(('index',options,T(name)),'value'),'custom'),lambda a:a.set(R(1),'settingIndex0',1))
                if row['key']=='style':
                    def default(a):
                        for j,other in enumerate(settings):
                            if other['key'] not in ('finish','backs','floor','fascia'):continue
                            a.set(R(1),'customSettingIndex'+str(j),T('settingIndex'+str(j)))
                            for k,item in enumerate(other['options']):
                                if item['value']=='custom':
                                    fallback=next(v for v,x in enumerate(other['options']) if x['value']!='custom')
                                    a.when(EQ(T('settingIndex'+str(j)),k),lambda a,j=j,fallback=fallback:a.set(R(1),'settingIndex'+str(j),fallback))
                    def custom(a):
                        for j,other in enumerate(settings):
                            if other['key'] in ('finish','backs','floor','fascia'):a.set(R(1),'settingIndex'+str(j),T('customSettingIndex'+str(j)))
                    a.when(EQ(P(('index',options,T(name)),'value'),'default'),default)
                    a.when(EQ(P(('index',options,T(name)),'value'),'custom'),custom)
            a.when(EQ(R(2),i),change)
        a.do(R(1),'RefreshRoomSettings')
    a.function('ShiftRoomSetting',2,shift)
