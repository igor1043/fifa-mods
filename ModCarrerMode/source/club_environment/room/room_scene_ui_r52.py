from ui_theme import ACCENT, ACCENT_TEXT, rgb, rgba
import portable_paths as portable
"""Native APT scene selector. No browser, keyboard hooks or synthetic input."""
import io,struct
from pathlib import Path
from PIL import Image
import build_screen as b
import native_roster_footer as roster_footer
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;EQ=b.equal

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
    controls=[place(panel,1,0,0,8.125,9.3),place(text('CENAS',472,38,28),2,24,18),place(text('Escolha um grupo',472,30,18),3,24,62,label='groupTitle')]
    for i in range(5):controls.append(place(row,10+i,24,106+68*i,label='row'+str(i)))
    controls.append(place(text('',472,28,17),30,24,462,label='counter'))
    page_button=clip([place(neutral,1,0,0,3.3,.5),place(text('',196,30,18),2,10,1,label='label')])
    controls.extend([place(page_button,40,24,510,label='previousPage'),place(page_button,41,284,510,label='nextPage'),place(page_button,42,284,18,label='backGroup')])
    modal=clip(controls)
    def action_button(label,width):
        focus=clip([place(selected,1,0,0,width/64,.75)])
        return clip([place(neutral,1,0,0,width/64,.75),place(focus,2,0,0,label='highlight'),place(text(label,width-30,42,25),3,16,4,label='label')])
    return [place(modal,100,1260,212,label='sceneModal',color=0x00ffffff),place(action_button('Cenas',180),101,1030,930,label='sceneButton'),place(action_button('Jogadores do time',300),102,1230,930,label='playersButton'),place(action_button('Câmera livre',280),103,1550,930,label='freeButton'),place(text('WASD: andar · Mouse com botão direito: olhar · Shift: acelerar',1650,32,22,0xffffffff),104,109,920,label='freeHint')]

def methods(a,scope):
    categories=[('Vestiário',[]),('Jogadores',[]),('Quadros',[]),('Departamento médico',[])]
    for scene in scope['scenes']:
        label=scene['label'];group=3 if label.startswith('Departamento médico') else 1 if ('Camisa ' in label or 'camisa ' in label) else 2 if 'Quadro' in label else 0
        categories[group][1].append({'label':label,'code':scene['id'],'player':scene.get('player',0)})
    categories=[(name,items) for name,items in categories if items]
    root=[{'label':'Automático · ordem aleatória','code':-1}]+[{'label':name,'code':-101-i} for i,(name,_) in enumerate(categories)]
    objects=lambda items:('array',tuple(('map',v) for v in items))
    groups=('array',tuple(objects(items) for _,items in categories));root_items=objects(root)
    def init(a):
        for key,value in (('modalOpen',False),('sceneFocus',0),('sceneGroup',-1),('sceneItems',root_items),('roomActionFocus',0),('openingPlayers',False),('roomPlayersOpen',False),('roomPlayersDetail',False),('freeCameraOpen',False)):a.set(R(1),key,value)
        a.set(T('freeHint'),'_visible',False);a.set(T('sceneModal'),'_visible',False);a.set(T('sceneModal'),'_alpha',0);a.set(T('sceneButton'),'owner',R(1));a.set(T('sceneButton'),'onRelease',T('SceneButtonClick'));a.set(R(1),'onEnterFrame',T('WaitForSceneClips'))
        a.when(b.G('Server16RoomSequence'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16RoomSequence',0));a.do(R(1),'PublishScene',-1)
        a.do(R(1),'PublishRoster','room_close');a.do(PATH('Key'),'addListener',R(1))
    a.function('InitSceneControl',0,init)
    a.function('SceneButtonClick',0,lambda a:a.do(P(R(1),'owner'),'OpenScenes'))
    a.function('PlayersButtonClick',0,lambda a:a.do(P(R(1),'owner'),'OpenPlayers'))
    a.function('SceneButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',0),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    a.function('PlayersButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',1),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    a.function('FreeButtonClick',0,lambda a:a.do(P(R(1),'owner'),'OpenFreeCamera'))
    a.function('FreeButtonOver',0,lambda a:(a.set(P(R(1),'owner'),'roomActionFocus',2),a.do(P(R(1),'owner'),'RefreshRoomActions')))
    def refresh_actions(a):
        for index,name,click,hover in ((0,'sceneButton','SceneButtonClick','SceneButtonOver'),(1,'playersButton','PlayersButtonClick','PlayersButtonOver'),(2,'freeButton','FreeButtonClick','FreeButtonOver')):
            button=T(name);a.set(button,'owner',R(1));a.set(button,'onRelease',T(click));a.set(button,'onRollOver',T(hover))
            a.set(P(button,'highlight'),'_alpha',0);a.set(P(button,'label'),'textColor',0x334b56)
            a.when(EQ(T('roomActionFocus'),index),lambda a,button=button:(a.set(P(button,'highlight'),'_alpha',100),a.set(P(button,'label'),'textColor',rgb(ACCENT_TEXT))))
        a.do(M('HelpManager'),'Update')
    a.function('RefreshRoomActions',0,refresh_actions)
    def roster_command(a):a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16ClubBrowser',R(2))
    a.function('PublishRoster',1,roster_command)
    def roster_help(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')));a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show')
        a.when(T('roomPlayersOpen'),roster_footer.apply,roster_footer.restore)
    a.function('RefreshRosterHelp',0,roster_help)
    def free_open(a):
        a.when(T('freeCameraOpen'),lambda a:a.ret());a.set(R(1),'freeCameraOpen',True);a.set(R(1),'modalOpen',False)
        for name in ('roomHeader','sceneButton','playersButton','freeButton','sceneModal'):a.set(T(name),'_visible',False)
        a.set(T('freeHint'),'_visible',True);a.do(R(1),'PublishScene',-4);a.do(R(1),'RefreshRosterHelp')
    a.function('OpenFreeCamera',0,free_open)
    def free_close(a):
        a.set(R(1),'freeCameraOpen',False);a.set(T('freeHint'),'_visible',False);a.do(R(1),'PublishScene',-5)
        for name in ('roomHeader','sceneButton','playersButton','freeButton'):a.set(T(name),'_visible',True)
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
        for name in ('roomHeader','sceneButton','playersButton','freeButton','sceneModal'):a.set(T(name),'_visible',False)
        a.do(R(1),'PublishRoster','room_roster');a.set(R(1),'rosterHelpDelay',90);a.set(R(1),'onEnterFrame',T('RoomPlayersTick'));a.do(R(1),'RefreshRosterHelp')
    a.function('OpenPlayers',0,open_players)
    def roster_back(a):
        a.when(T('roomPlayersDetail'),lambda a:(a.set(R(1),'roomPlayersDetail',False),a.do(R(1),'PublishRoster','back'),a.do(R(1),'RefreshRosterHelp'),a.ret()))
        a.do(R(1),'PublishRoster','room_close');a.set(R(1),'roomPlayersOpen',False);a.set(R(1),'onEnterFrame',None)
        for name in ('roomHeader','sceneButton','playersButton','freeButton'):a.set(T(name),'_visible',True)
        a.do(R(1),'RefreshRoomActions');a.do(R(1),'RefreshRosterHelp')
    a.function('RoomPlayersBack',0,roster_back)
    def wait(a):
        a.when(T('sceneModal'),lambda a:(a.do(R(1),'RefreshSceneModal'),a.set(T('sceneButton'),'owner',R(1)),a.set(T('sceneButton'),'onRelease',T('SceneButtonClick')),a.do(R(1),'RefreshRoomActions'),a.set(R(1),'onEnterFrame',None)))
    a.function('WaitForSceneClips',0,wait)
    def publish(a):
        a.set(b.GLOBAL,'Server16RoomSequence',b.plus(b.G('Server16RoomSequence'),1));value=f'S16ROOM2|{scope["club"]}|{scope["nonce"]}|'
        for part in (b.G('Server16RoomSequence'),'|',R(2),'|ENDROOM'):value=b.plus(value,part)
        a.set(b.GLOBAL,'Server16RoomRequest',value)
        a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RoomScene',value)
    a.function('PublishScene',1,publish)
    def refresh(a):
        a.set(T('sceneModal'),'_visible',T('modalOpen'));a.set(T('sceneModal'),'_alpha',0);a.when(T('modalOpen'),lambda a:a.set(T('sceneModal'),'_alpha',100))
        a.set(R(1),'scenePage',CALL(PATH('Math'),'floor',('bin',13,T('sceneFocus'),5)))
        title=P(T('sceneModal'),'groupTitle');a.set(title,'text','Escolha um grupo')
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
    a.function('OpenScenes',0,lambda a:(a.set(R(1),'modalOpen',True),a.do(R(1),'PublishScene',-3),a.do(R(1),'RefreshSceneModal')))
    def close(a):
        def root_level(a):a.set(R(1),'sceneGroup',-1);a.set(R(1),'sceneFocus',0);a.set(R(1),'sceneItems',root_items)
        a.when(('bin',103,T('sceneGroup'),-1),root_level,lambda a:(a.set(R(1),'modalOpen',False),a.do(R(1),'PublishScene',-3)));a.do(R(1),'RefreshSceneModal')
    a.function('CloseScenes',0,close)
    a.function('SceneBackButton',0,lambda a:a.do(P(R(1),'owner'),'CloseScenes'))
    def shift(a):
        total=P(T('sceneItems'),'length');a.set(R(1),'sceneFocus',('bin',63,b.plus(b.plus(T('sceneFocus'),R(2)),total),total));a.do(R(1),'RefreshSceneModal')
    a.function('ShiftScene',1,shift)
    a.function('PreviousScenePage',0,lambda a:a.do(P(R(1),'owner'),'ShiftScene',-5))
    a.function('NextScenePage',0,lambda a:a.do(P(R(1),'owner'),'ShiftScene',5))
    def apply(a):
        code=P(('index',T('sceneItems'),T('sceneFocus')),'code');a.set(R(1),'sceneCode',code)
        def group(a):
            a.set(R(1),'sceneGroup',('bin',11,-101,T('sceneCode')));a.set(R(1),'sceneItems',('index',groups,T('sceneGroup')));a.set(R(1),'sceneFocus',0)
        a.when(('bin',72,T('sceneCode'),-100),group,lambda a:(a.do(R(1),'PublishScene',T('sceneCode')),a.set(R(1),'modalOpen',False)));a.do(R(1),'RefreshSceneModal')
    a.function('ApplyScene',0,apply)
    def row_over(a):
        owner=P(R(1),'owner');index=b.plus(('bin',12,P(owner,'scenePage'),5),P(R(1),'slot'))
        a.when(('bin',72,index,P(P(owner,'sceneItems'),'length')),lambda a:(a.set(owner,'sceneFocus',index),a.do(owner,'RefreshSceneModal')))
    a.function('RowOver',0,row_over)
    a.function('RowClick',0,lambda a:(a.do(R(1),'onRollOver'),a.do(P(R(1),'owner'),'ApplyScene')))
    def help(a):
        a.when(T('freeCameraOpen'),lambda a:a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in [('BACK','Voltar'),('LAS_UD','Andar'),('RAS_LR','Olhar')]))))
        def roster_items(a,details=False):
            items=[('BACK','Voltar'),('L2R2','Abas'),('RAS_LR','Girar'),('L1R1','Zoom')]
            if not details:items=[('ADVANCE','Detalhes'),('BACK','Voltar'),('LAS_UD','Elenco')]+items[1:]
            a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in items)))
        a.when(T('roomPlayersOpen'),lambda a:a.when(T('roomPlayersDetail'),lambda a:roster_items(a,True),roster_items))
        a.when(T('modalOpen'),lambda a:a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar')))))
        a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','LAS_LR','Opções'))))
    a.function('getHelpContext',0,help)
    def key(a):
        a.when(T('freeCameraOpen'),lambda a:(a.when(EQ(R(2),P(M('InputCodes'),'BACK')),lambda a:a.do(R(1),'CloseFreeCamera')),a.ret(True)))
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
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'ApplyScene'),lambda a:a.when(EQ(T('roomActionFocus'),2),lambda a:a.do(R(1),'OpenFreeCamera'),lambda a:a.when(EQ(T('roomActionFocus'),1),lambda a:a.do(R(1),'OpenPlayers'),lambda a:a.do(R(1),'OpenScenes')))),a.ret(True)))
        for name in ('SECONDARY_SELECT','SECONDARY','SQUARE','X'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')),a.ret(True)))
        def arrows(a):
            for name,delta in (('UP',-1),('DOWN',1),('LEFT',-5),('RIGHT',5),('UI_UP',-1),('UI_DOWN',1),('UI_LEFT',-5),('UI_RIGHT',5),('PREVIOUS',-5),('NEXT',5),('L1',-5),('R1',5)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShiftScene',delta),a.ret(True)))
        def action_arrows(a):
            for name,delta in (('LEFT',-1),('LAS_LEFT',-1),('UI_LEFT',-1),('RIGHT',1),('LAS_RIGHT',1),('UI_RIGHT',1)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.set(R(1),'roomActionFocus',('bin',63,b.plus(b.plus(T('roomActionFocus'),delta),3),3)),a.do(R(1),'RefreshRoomActions'),a.ret(True)))
        a.when(T('modalOpen'),arrows,action_arrows);a.ret(True)
    a.function('LocalEventHandler',2,key)
    def keyboard(a):
        a.when(T('freeCameraOpen'),lambda a:a.ret())
        a.when(('bin',16,('bin',73,T('roomPlayersOpen'),False),EQ(CALL(PATH('Key'),'getCode'),9)),lambda a:a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')))
    a.function('onKeyDown',0,keyboard)
