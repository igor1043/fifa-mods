from ui_theme import ACCENT, ACCENT_TEXT, rgb, rgba
import portable_paths as portable
"""Native APT scene selector. No browser, keyboard hooks or synthetic input."""
import io,struct
from pathlib import Path
from PIL import Image
import build_screen as b
import native_roster_footer as roster_footer
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;EQ=b.equal
from room_pointer_ui import ACTION_Y

def graphics(apt,data,append,addchar,place,bitmap,scope,read_asset):
    from PIL import ImageDraw
    from room_medical_r53 import player_portrait
    def raster(im):
        f=io.BytesIO();im.save(f,format='DDS',pixel_format='DXT5');raw=bytearray(f.getvalue());struct.pack_into('<I',raw,20,len(raw)-128);struct.pack_into('<I',raw,88,0);return bitmap(raw)[0]
    def image(color):return raster(Image.new('RGBA',(64,64),color))
    neutral=image((231,237,241,226));selected=image(rgba(ACCENT,248));panel=image((236,240,242,198))
    def text(value,w,h,size,color=0xff334b56):
        raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,w,h);struct.pack_into('<If',raw,56,color,size);struct.pack_into('<QQ',raw,80,append(value.encode('utf8')+b'\0'),0);return addchar(raw)
    def clip(controls):
        raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);frame=append(struct.pack('<I4xQ',len(controls),append(struct.pack('<'+'Q'*len(controls),*controls))));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return addchar(raw)
    portraits={}
    for player in dict.fromkeys(s.get('player',0) for s in scope['scenes']):
        if not player:continue
        im,path=player_portrait(read_asset,player)
        canvas=Image.new('RGBA',(128,128),(0,0,0,0))
        if im is not None:
            im.thumbnail((128,128),Image.Resampling.LANCZOS);canvas.alpha_composite(im,((128-im.width)//2,128-im.height))
        else:
            d=ImageDraw.Draw(canvas);d.ellipse((42,12,86,56),fill=(129,147,159));d.rounded_rectangle((24,60,104,125),radius=22,fill=(129,147,159))
        portraits[player]=clip([place(raster(canvas),1,0,0,.43,.43)])
    highlight=clip([place(selected,1,0,0,7.35,.97)])
    children=[place(neutral,1,0,0,7.35,.97),place(highlight,2,0,0,label='highlight')]
    children.extend(place(cid,10+i,8,3,label='head'+str(pid)) for i,(pid,cid) in enumerate(portraits.items()))
    children.append(place(text('',398,56,20),100,12,15,label='label'))
    row=clip(children)
    controls=[place(panel,1,0,0,8.125,9.3),place(text('CENAS',472,38,28),2,24,18,label='modalTitle'),place(text('Escolha um grupo',472,30,18),3,24,62,label='groupTitle')]
    for i in range(5):controls.append(place(row,10+i,24,106+68*i,label='row'+str(i)))
    controls.append(place(text('',472,28,17),30,24,462,label='counter'))
    page_button=clip([place(neutral,1,0,0,3.3,.5),place(text('',196,30,18),2,10,1,label='label')])
    controls.extend([place(page_button,40,24,510,label='previousPage'),place(page_button,41,284,510,label='nextPage'),place(page_button,42,284,18,label='backGroup')])
    modal=clip(controls)
    def action_button(label,width):
        focus=clip([place(selected,1,0,0,width/64,.75)])
        return clip([place(neutral,1,0,0,width/64,.75),place(focus,2,0,0,label='highlight'),place(text(label,width-30,42,25),3,16,4,label='label')])
    result=[place(modal,100,1260,212,label='sceneModal',color=0x00ffffff),place(action_button('Cenas',180),101,1030,ACTION_Y,label='sceneButton'),place(action_button('Jogadores do time',300),102,1230,ACTION_Y,label='playersButton'),place(action_button('Câmera livre',280),103,1550,ACTION_Y,label='freeButton'),place(text('WASD: andar · Botão esquerdo + arrastar: olhar · Shift: acelerar · Esc: voltar · Q / R3: personalização',1700,32,22,0xffffffff),104,109,870,label='freeHint')]
    if scope.get('room_version')==3:
        result.append(place(action_button('Personalização do vestiário',355),105,650,ACTION_Y,label='settingsButton'))
        arrow=clip([place(neutral,1,0,0,.75,.6),place(text('',44,38,28),2,12,0,label='label')])
        focus=clip([place(selected,1,0,0,10.25,1.12)])
        setting=clip([place(neutral,1,0,0,10.25,1.12),place(focus,2,0,0,label='highlight'),place(text('',510,25,17),3,72,5,label='title'),place(text('',510,38,26),4,72,30,label='value'),place(arrow,5,10,26,label='previous'),place(arrow,6,595,26,label='next')])
        from room_settings_ui import graphics as settings_graphics
        parts=settings_graphics(scope,place,clip,text,setting,arrow,action_button,panel,neutral,selected)
        result.append(place(clip(parts),106,1080,180,label='roomSettings',color=0x00ffffff))
    return result

def methods(a,scope):
    v3=scope.get('room_version')==3
    action_names=('sceneButton','playersButton','freeButton')+(('settingsButton',) if v3 else ())
    action_count=len(action_names)
    categories=[('Vestiário',[]),('Jogadores',[]),('Quadros',[]),('Departamento médico',[])]
    for scene in scope['scenes']:
        label=scene['label'];group=3 if label.startswith('Departamento médico') else 1 if ('Camisa ' in label or 'camisa ' in label) else 2 if 'Quadro' in label else 0
        categories[group][1].append({'label':label,'code':scene['id'],'player':scene.get('player',0)})
    categories=[(name,items) for name,items in categories if items]
    settings=scope.get('settings',[]) if v3 else []
    root=[{'label':'Automático · ordem aleatória','code':-1}]+[{'label':name,'code':-101-i} for i,(name,_) in enumerate(categories)]
    objects=lambda items:('array',tuple(('map',v) for v in items))
    groups=('array',tuple(objects(items) for _,items in categories));root_items=objects(root)
    def init(a):
        for key,value in (('modalOpen',False),('sceneFocus',0),('sceneGroup',-1),('sceneItems',root_items),('roomActionFocus',0),('openingPlayers',False),('roomPlayersOpen',False),('roomPlayersDetail',False),('freeCameraOpen',False)):a.set(R(1),key,value)
        a.set(T('roomHeader'),'_visible',False);a.set(T('roomHeader'),'_alpha',0)
        a.set(R(1),'settingsOpen',False);a.set(R(1),'settingsFocus',0);a.set(R(1),'settingsOffset',0);a.set(R(1),'settingsDragging',False)
        if v3:
            mapping='S16ROOM_INPUT_MAP|'
            for name in ('R3','L1','L2'):
                mapping=b.plus(b.plus(mapping,P(M('InputCodes'),name)),'|')
            a.set(b.GLOBAL,'Server16RoomInputMapping',b.plus(mapping,'END_INPUT_MAP'))
            a.set(T('roomSettings'),'_visible',False);a.set(T('roomSettings'),'_alpha',0)
            for i,row in enumerate(settings):
                a.set(R(1),'settingIndex'+str(i),row['selected']);a.set(R(1),'appliedSettingIndex'+str(i),row['selected']);a.set(R(1),'customSettingIndex'+str(i),row.get('custom_selected',row['selected']));a.set(R(1),'appliedCustomSettingIndex'+str(i),row.get('custom_selected',row['selected']))
        a.set(T('freeHint'),'_visible',False);a.set(T('sceneModal'),'_visible',False);a.set(T('sceneModal'),'_alpha',0);a.set(T('sceneButton'),'owner',R(1));a.set(T('sceneButton'),'onRelease',T('SceneButtonClick'));a.set(R(1),'roomFrameHandler',T('WaitForSceneClips'));a.set(R(1),'roomFrontendFrames',0);a.set(R(1),'onEnterFrame',T('RoomUiTick'))
        # The native director initializes on real scene entry. Rebuilding an
        # appearance package must never issue an automatic-camera reset.
        a.when(b.G('Server16RoomSequence'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16RoomSequence',0))
        a.do(R(1),'PublishRoster','room_close');a.do(PATH('Key'),'addListener',R(1))
        a.set(R(1),'roomPointerCycle',False);a.set(R(1),'roomPointerHandled',False);a.set(R(1),'onMouseMove',T('RoomMouseMove'))
        a.when(PATH('Mouse'),lambda a:a.do(PATH('Mouse'),'addListener',R(1)))
    a.function('InitSceneControl',0,init)
    def ui_tick(a):
        a.when(T('roomFrameHandler'),lambda a:a.do(R(1),'roomFrameHandler'))
        a.set(R(1),'roomFrontendFrames',('bin',71,T('roomFrontendFrames'),1))
        a.when(('bin',72,T('roomFrontendFrames'),15),lambda a:a.ret())
        a.set(R(1),'roomFrontendFrames',0)
        a.when(P(b.ION,'SendSystemEvent'),lambda a:a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16FrontendTick','tick'))
    a.function('RoomUiTick',0,ui_tick)
    def identity(a):
        valid=('bin',16,EQ(b.G('Server16ActiveCareerClubId'),scope['club']),('bin',16,('not',T('roomPlayersOpen')),('not',T('freeCameraOpen'))))
        a.set(T('roomHeader'),'_visible',valid);a.set(T('roomHeader'),'_alpha',0)
        a.when(valid,lambda a:a.set(T('roomHeader'),'_alpha',100))
    a.function('RefreshRoomIdentity',0,identity)
    a.function('SceneButtonClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',0))
    a.function('PlayersButtonClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',1))
    a.function('SceneButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',0),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    a.function('PlayersButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',1),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    a.function('FreeButtonClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',2))
    a.function('FreeButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',2),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    a.function('SettingsButtonClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',3))
    a.function('SettingsButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',3),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    def refresh_actions(a):
        buttons=[(0,'sceneButton','SceneButtonClick','SceneButtonOver'),(1,'playersButton','PlayersButtonClick','PlayersButtonOver'),(2,'freeButton','FreeButtonClick','FreeButtonOver')]
        if v3:buttons.append((3,'settingsButton','SettingsButtonClick','SettingsButtonOver'))
        for index,name,click,hover in buttons:
            button=T(name);a.set(button,'owner',R(1));a.set(button,'onRelease',T(click));a.set(button,'onRollOver',T(hover))
            a.set(P(button,'highlight'),'_alpha',0);a.set(P(button,'label'),'textColor',0x334b56)
            a.when(EQ(T('roomActionFocus'),index),lambda a,button=button:(a.set(P(button,'highlight'),'_alpha',100),a.set(P(button,'label'),'textColor',rgb(ACCENT_TEXT))))
        a.do(M('HelpManager'),'Update')
    a.function('RefreshRoomActions',0,refresh_actions)
    def roster_command(a):a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser',R(2))
    a.function('PublishRoster',1,roster_command)
    def roster_help(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update')
        a.when(('bin',16,T('freeCameraOpen'),('not',T('settingsOpen'))),lambda a:a.do(M('HelpManager'),'Hide'),lambda a:a.do(M('HelpManager'),'Show'))
        # Keep native input legends on their own bottom line in every mode,
        # including personalization/free camera, and restore only on exit.
        roster_footer.apply(a)
    a.function('RefreshRosterHelp',0,roster_help)
    def free_open(a):
        a.when(T('freeCameraOpen'),lambda a:a.ret());a.set(R(1),'freeCameraOpen',True);a.set(R(1),'modalOpen',False)
        for name in ('roomHeader','sceneModal')+action_names:a.set(T(name),'_visible',False)
        a.set(T('freeHint'),'_visible',False)
        a.do(R(1),'PublishScene',-4);a.do(R(1),'RefreshRosterHelp')
    a.function('OpenFreeCamera',0,free_open)
    def free_close(a):
        a.set(R(1),'freeCameraOpen',False);a.set(T('freeHint'),'_visible',False);a.do(R(1),'PublishScene',-5)
        for name in ('roomHeader',)+action_names:a.set(T(name),'_visible',True)
        a.do(R(1),'RefreshRoomIdentity')
        a.do(R(1),'RefreshRoomActions');a.do(R(1),'RefreshRosterHelp')
    a.function('CloseFreeCamera',0,free_close)

    def roster_tick(a):
        # APT's animate-in may finish after OpenPlayers. Keep only the roster
        # header visible throughout this mode; do not reload either scene.
        a.set(T('roomHeader'),'_visible',False)
        a.when(T('rosterHelpDelay'),lambda a:(a.set(R(1),'rosterHelpDelay',('bin',11,T('rosterHelpDelay'),1)),a.when(('bin',17,EQ(T('rosterHelpDelay'),60),EQ(T('rosterHelpDelay'),0)),lambda a:a.do(R(1),'RefreshRosterHelp'))))
    a.function('RoomPlayersTick',0,roster_tick)
    def open_players(a):
        a.when(T('roomPlayersOpen'),lambda a:a.ret());a.set(R(1),'roomPlayersOpen',True);a.set(R(1),'roomPlayersDetail',False);a.set(R(1),'modalOpen',False);a.do(R(1),'PublishScene',-3)
        for name in ('roomHeader','sceneModal')+action_names:a.set(T(name),'_visible',False)
        a.do(R(1),'PublishRoster','room_roster');a.set(R(1),'rosterHelpDelay',90);a.set(R(1),'roomFrameHandler',T('RoomPlayersTick'));a.do(R(1),'RefreshRosterHelp')
    a.function('OpenPlayers',0,open_players)
    def roster_back(a):
        a.when(T('roomPlayersDetail'),lambda a:(a.set(R(1),'roomPlayersDetail',False),a.do(R(1),'PublishRoster','back'),a.do(R(1),'RefreshRosterHelp'),a.ret()))
        a.do(R(1),'PublishRoster','room_close');a.set(R(1),'roomPlayersOpen',False);a.set(R(1),'roomFrameHandler',None)
        for name in ('roomHeader',)+action_names:a.set(T(name),'_visible',True)
        a.do(R(1),'RefreshRoomIdentity')
        a.do(R(1),'RefreshRoomActions');a.do(R(1),'RefreshRosterHelp')
    a.function('RoomPlayersBack',0,roster_back)
    def wait(a):
        a.when(T('sceneModal'),lambda a:(a.do(R(1),'RefreshSceneModal'),a.set(T('sceneButton'),'owner',R(1)),a.set(T('sceneButton'),'onRelease',T('SceneButtonClick')),a.do(R(1),'RefreshRoomActions'),a.do(R(1),'RefreshRoomIdentity'),a.do(R(1),'RefreshRosterHelp'),a.set(R(1),'roomFrameHandler',None)))
    a.function('WaitForSceneClips',0,wait)
    def publish(a):
        a.set(b.GLOBAL,'Server16RoomSequence',b.plus(b.G('Server16RoomSequence'),1));value=f'S16ROOM2|{scope["club"]}|{scope["nonce"]}|'
        # FIFA's APT arithmetic rounds to float32. Keep the counter and the
        # six low digits as strings: counter * 1,000,000 loses option bits
        # after only 16 commands (notably the Default/Custom bit).
        sequence=b.plus(b.plus('',b.G('Server16RoomSequence')),'0000000') if v3 else b.G('Server16RoomSequence')
        for part in (sequence,'|',R(2),'|ENDROOM'):value=b.plus(value,part)
        a.set(b.GLOBAL,'Server16RoomRequest',value)
        a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RoomScene',value)
    a.function('PublishScene',1,publish)
    def publish_appearance(a):
        import room_appearance as art
        a.set(b.GLOBAL,'Server16RoomSequence',b.plus(b.G('Server16RoomSequence'),1))
        packed=0
        multiplier=1
        for i,row in enumerate(settings[:art.PACKED_ROWS]):
            packed=b.plus(packed,('bin',12,T('settingIndex'+str(i)),multiplier))
            multiplier*=len(row['options'])
        a.set(R(1),'appearancePacked',packed);a.set(R(1),'appearanceDigits','')
        for divisor in (1000000,100000,10000,1000,100,10,1):
            digit=('bin',63,CALL(PATH('Math'),'floor',('bin',13,T('appearancePacked'),divisor)),10)
            a.set(R(1),'appearanceDigits',b.plus(T('appearanceDigits'),digit))
        sequence=b.plus(b.plus('',b.G('Server16RoomSequence')),T('appearanceDigits'))
        door=next((i for i,row in enumerate(settings) if row['key']=='door_finish'),None)
        code=b.plus(art.DOOR_APPLY_BASE,T('settingIndex'+str(door))) if door is not None else art.GROUPED_APPLY_CODE
        value=b.plus(b.plus(b.plus(b.plus(f'S16ROOM2|{scope["club"]}|{scope["nonce"]}|',sequence),'|'),code),'|ENDROOM')
        a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RoomScene',value)
    a.function('PublishAppearance',0,publish_appearance)
    def refresh(a):
        a.set(T('sceneModal'),'_visible',T('modalOpen'));a.set(T('sceneModal'),'_alpha',0);a.when(T('modalOpen'),lambda a:a.set(T('sceneModal'),'_alpha',100))
        a.set(R(1),'scenePage',CALL(PATH('Math'),'floor',('bin',13,T('sceneFocus'),5)))
        title=P(T('sceneModal'),'groupTitle');a.set(title,'text','Escolha um grupo')
        a.set(P(T('sceneModal'),'modalTitle'),'text','CENAS')

        a.when(('bin',103,T('sceneGroup'),-1),lambda a:a.set(title,'text',('index',('array',tuple(name for name,_ in categories)),T('sceneGroup'))))
        a.set(P(T('sceneModal'),'counter'),'text',b.plus(b.plus(b.plus(b.plus('Item ',b.plus(T('sceneFocus'),1)),' de '),P(T('sceneItems'),'length')),b.plus(' · Página ',b.plus(T('scenePage'),1))))
        for i in range(5):
            row=P(T('sceneModal'),'row'+str(i));index=b.plus(('bin',12,T('scenePage'),5),i);entry=('index',T('sceneItems'),index)
            a.set(row,'_visible',('bin',72,index,P(T('sceneItems'),'length')));a.set(row,'owner',R(1));a.set(row,'slot',i);a.set(row,'onRelease',T('RowClick'));a.set(row,'onRollOver',T('RowOver'))
            a.set(P(row,'label'),'text',P(entry,'label'));a.set(P(row,'label'),'textColor',0x334b56);a.set(P(row,'highlight'),'_alpha',0)
            a.set(P(row,'label'),'_x',12)
            for player in dict.fromkeys(s.get('player',0) for s in scope['scenes']):
                if not player:continue
                a.set(P(row,'head'+str(player)),'_visible',EQ(P(entry,'player'),player))
                a.when(EQ(P(entry,'player'),player),lambda a:a.set(P(row,'label'),'_x',76))
            a.when(EQ(index,T('sceneFocus')),lambda a,row=row:(a.set(P(row,'highlight'),'_alpha',100),a.set(P(row,'label'),'textColor',rgb(ACCENT_TEXT))))
        for name,title_text,method in (('previousPage','< Anterior','PreviousScenePage'),('nextPage','Próxima >','NextScenePage'),('backGroup','< Voltar','SceneBackButton')):
            button=P(T('sceneModal'),name);a.set(button,'owner',R(1));a.set(button,'onRelease',T(method));a.set(P(button,'label'),'text',title_text)
            if name!='backGroup':a.set(button,'_visible',('bin',103,P(T('sceneItems'),'length'),5))
        a.do(M('HelpManager'),'Update')
    a.function('RefreshSceneModal',0,refresh)
    # Keep the cinematic moving while browsing; clear an older view's pause.
    a.function('OpenScenes',0,lambda a:(a.set(R(1),'modalOpen',True),a.do(R(1),'PublishScene',-3),a.do(R(1),'PublishScene',-6),a.do(R(1),'RefreshSceneModal')))
    from room_settings_ui import methods as settings_methods
    settings_methods(a,scope,settings)
    def close(a):
        def root_level(a):a.set(R(1),'sceneGroup',-1);a.set(R(1),'sceneFocus',0);a.set(R(1),'sceneItems',root_items)
        a.when(('bin',103,T('sceneGroup'),-1),root_level,lambda a:(a.set(R(1),'modalOpen',False),a.do(R(1),'PublishScene',-3),a.do(R(1),'PublishScene',-7)));a.do(R(1),'RefreshSceneModal')
    a.function('CloseScenes',0,close)
    a.function('SceneBackButton',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',112))
    def shift(a):
        total=P(T('sceneItems'),'length');a.set(R(1),'sceneFocus',('bin',63,b.plus(b.plus(T('sceneFocus'),R(2)),total),total));a.do(R(1),'RefreshSceneModal')
    a.function('ShiftScene',1,shift)
    a.function('PreviousScenePage',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',110))
    a.function('NextScenePage',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',111))
    def apply(a):
        code=P(('index',T('sceneItems'),T('sceneFocus')),'code');a.set(R(1),'sceneCode',code)
        def group(a):
            a.set(R(1),'sceneGroup',('bin',11,-101,T('sceneCode')));a.set(R(1),'sceneItems',('index',groups,T('sceneGroup')));a.set(R(1),'sceneFocus',0)
        a.when(('bin',72,T('sceneCode'),-100),group,lambda a:(a.do(R(1),'PublishScene',T('sceneCode')),a.set(R(1),'modalOpen',False),a.do(R(1),'PublishScene',-7)));a.do(R(1),'RefreshSceneModal')
    a.function('ApplyScene',0,apply)
    def row_over(a):
        owner=P(R(1),'owner');index=b.plus(('bin',12,P(owner,'scenePage'),5),P(R(1),'slot'))
        a.when(('bin',72,index,P(P(owner,'sceneItems'),'length')),lambda a:(a.set(owner,'sceneFocus',index),a.do(owner,'RefreshSceneModal')))
    a.function('RowOver',0,row_over)
    a.function('RowClick',0,lambda a:a.do(P(R(1),'owner'),'ActivateRoomPointer',b.plus(100,P(R(1),'slot'))))
    def help(a):
        a.when(T('settingsOpen'),lambda a:a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('L1R1','Grupos'),('LAS_UD','Itens'),('LAS_LR','Alterar'),('ADVANCE','Selecionar'),('BACK','Voltar')]))))
        a.when(T('freeCameraOpen'),lambda a:a.ret(('array',())))
        def roster_items(a,details=False):
            items=[('BACK','Voltar'),('L2R2','Abas'),('RAS_LR','Girar'),('L1R1','Zoom')]
            if not details:items=[('ADVANCE','Detalhes'),('BACK','Voltar'),('LAS_UD','Elenco')]+items[1:]
            a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in items)))
        a.when(T('roomPlayersOpen'),lambda a:a.when(T('roomPlayersDetail'),lambda a:roster_items(a,True),roster_items))
        a.when(T('modalOpen'),lambda a:a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar')))))
        a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','LAS_LR','Opções'))))
    a.function('getHelpContext',0,help)
    def key(a):
        def setting_keys(a):
            a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(R(1),'CloseRoomSettings'),a.ret(True)))
            for name,delta in (('L1',-1),('R1',1)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShiftSettingsGroup',delta),a.ret(True)))
            for name,delta in (('UP',-1),('UI_UP',-1),('LAS_UP',-1),('RAS_UP',-1),('DOWN',1),('UI_DOWN',1),('LAS_DOWN',1),('RAS_DOWN',1)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'MoveSettingFocus',delta),a.ret(True)))
            for name,delta in (('LEFT',-1),('UI_LEFT',-1),('LAS_LEFT',-1),('RIGHT',1),('UI_RIGHT',1),('LAS_RIGHT',1)):
                def adjust(a,delta=delta):
                    a.when(EQ(T('settingsFocus'),-1),lambda a:(a.do(R(1),'ShiftSettingsGroup',delta),a.ret(True)))
                    a.when(('bin',72,T('settingsFocus'),len(settings)),lambda a:a.do(R(1),'ShiftRoomSetting',T('settingsFocus'),delta),lambda a:(a.set(R(1),'settingsFocus',b.plus(len(settings),('bin',63,b.plus(b.plus(T('settingsFocus'),delta),2),2))),a.do(R(1),'RefreshRoomSettings')));a.ret(True)
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),adjust)
            for name in ('PRIMARY_SELECT','ADVANCE'):
                def select(a):
                    a.when(EQ(T('settingsFocus'),-1),lambda a:(a.do(R(1),'ShiftSettingsGroup',1),a.ret(True)))
                    a.when(EQ(T('settingsFocus'),len(settings)),lambda a:a.do(R(1),'CloseRoomSettings'),lambda a:a.when(EQ(T('settingsFocus'),len(settings)+1),lambda a:a.do(R(1),'ApplyRoomSettings'),lambda a:a.do(R(1),'ShiftRoomSetting',T('settingsFocus'),1)));a.ret(True)
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),select)
            a.ret(True)
        a.when(T('settingsOpen'),setting_keys)
        def free_keys(a):
            a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:a.do(R(1),'CloseFreeCamera'))
            # buttonDataKeyBoardMouse.ini maps SC_Q to VB_FE_R3. Use the
            # engine's native command, not Flash Key.addListener/getCode.
            a.when(('bin',16,P(M('InputCodes'),'R3'),EQ(R(2),P(M('InputCodes'),'R3'))),lambda a:a.do(R(1),'OpenRoomSettings'))
            a.ret(True)
        a.when(T('freeCameraOpen'),free_keys)
        def roster_keys(a):
            a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:(a.do(R(1),'RoomPlayersBack'),a.ret(True)))
            for name in ('PRIMARY_SELECT','ADVANCE'):
                def detail(a):
                    a.when(T('roomPlayersDetail'),lambda a:None,lambda a:(a.set(R(1),'roomPlayersDetail',True),a.do(R(1),'PublishRoster','detail'),a.do(R(1),'RefreshRosterHelp')));a.ret(True)
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),detail)
            for name,command in (('LEFT','left'),('LAS_LEFT','left'),('RIGHT','right'),('LAS_RIGHT','right'),('UP','prev'),('LAS_UP','prev'),('DOWN','next'),('LAS_DOWN','next'),('L2','tab_prev'),('R2','tab_next'),('OPTION_TOP','sort')):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,command=command:(a.do(R(1),'PublishRoster',command),a.ret(True)))
            a.ret(True)
        a.when(T('roomPlayersOpen'),roster_keys)
        def back(a):
            a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:(a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.do(M('InputManager'),'DisableCurrentLocalEventHandler')));a.ret(True)
        a.when(EQ(R(2),P(M('InputCodes'),'BACK')),back)
        for name in ('PRIMARY_SELECT','SELECT','ADVANCE'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'ApplyScene'),lambda a:a.when(EQ(T('roomActionFocus'),2),lambda a:a.do(R(1),'OpenFreeCamera'),lambda a:a.when(EQ(T('roomActionFocus'),1),lambda a:a.do(R(1),'OpenPlayers'),lambda a:a.when(EQ(T('roomActionFocus'),3),lambda a:a.do(R(1),'OpenRoomSettings'),lambda a:a.do(R(1),'OpenScenes'))))),a.ret(True)))
        for name in ('SECONDARY_SELECT','SECONDARY','SQUARE','X'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')),a.ret(True)))
        def arrows(a):
            for name,delta in (('UP',-1),('DOWN',1),('LEFT',-5),('RIGHT',5),('UI_UP',-1),('UI_DOWN',1),('UI_LEFT',-5),('UI_RIGHT',5),('PREVIOUS',-5),('NEXT',5),('L1',-5),('R1',5)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShiftScene',delta),a.ret(True)))
        def action_arrows(a):
            for name,delta in (('LEFT',-1),('LAS_LEFT',-1),('UI_LEFT',-1),('RIGHT',1),('LAS_RIGHT',1),('UI_RIGHT',1)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.set(R(1),'roomActionFocus',('bin',63,b.plus(b.plus(T('roomActionFocus'),delta),action_count),action_count)),a.do(R(1),'RefreshRoomActions'),a.ret(True)))
        a.when(T('modalOpen'),arrows,action_arrows);a.ret(True)
    a.function('LocalEventHandler',2,key)
    def keyboard(a):
        a.when(T('freeCameraOpen'),lambda a:a.ret())
        a.when(('bin',16,('bin',73,T('roomPlayersOpen'),False),EQ(CALL(PATH('Key'),'getCode'),9)),lambda a:a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')))
    a.function('onKeyDown',0,keyboard)

    from room_pointer_ui import methods as pointer_methods
    pointer_methods(a,settings,v3)
