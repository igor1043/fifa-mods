import portable_paths as portable
"""Native APT scene selector. No browser, keyboard hooks or synthetic input."""
import io,struct
from pathlib import Path
from PIL import Image
import build_screen as b
R=b.reg;T=b.this;P=b.prop;CALL=b.call;PATH=b.path;M=b.MANAGER;EQ=b.equal

def graphics(apt,data,append,addchar,place,bitmap):
    def image(color):
        f=io.BytesIO();Image.new('RGBA',(64,64),color).save(f,format='DDS',pixel_format='DXT5');raw=bytearray(f.getvalue());struct.pack_into('<I',raw,20,len(raw)-128);struct.pack_into('<I',raw,88,0);return bitmap(raw)[0]
    from formats import BigFile
    dark=bitmap(bytes(BigFile(portable.GAME/'data/ui/game/components/careercomponents/careerhubwidget.big').entries['4'].data))[0];neutral=image((218,224,226,255));selected=image((172,185,192,255))
    def text(value,w,h,size,color=0xff334b56):
        raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,w,h);struct.pack_into('<If',raw,56,color,size);struct.pack_into('<QQ',raw,80,append(value.encode('utf8')+b'\0'),0);return addchar(raw)
    def clip(controls):
        raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);frame=append(struct.pack('<I4xQ',len(controls),append(struct.pack('<'+'Q'*len(controls),*controls))));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return addchar(raw)
    # Selected state is a real MovieClip; alpha cannot toggle a named Shape.
    highlight=clip([place(selected,1,0,0,7.35,.59)])
    row=clip([place(neutral,1,0,0,7.35,.59),place(highlight,2,0,0,label='highlight'),place(text('',454,38,20),3,10,4,label='label')])
    panel=image((236,240,242,240))
    controls=[place(panel,1,0,0,8.125,7.11),place(text('CENAS',472,38,28),2,24,18),place(text('Escolha um grupo',472,30,18),3,24,57,label='groupTitle')]
    for i in range(5):controls.append(place(row,10+i,24,100+42*i,label='row'+str(i)))
    controls.extend([place(text('',472,28,17),30,24,324,label='counter'),place(text('Setas: escolher',472,28,17),31,24,407)])
    page_button=clip([place(neutral,1,0,0,3.3,.5),place(text('',196,30,18),2,10,1,label='label')])
    controls.extend([place(page_button,40,24,359,label='previousPage'),place(page_button,41,284,359,label='nextPage')])
    controls.append(place(page_button,42,284,18,label='backGroup'))
    modal=clip(controls)
    button=clip([place(neutral,1,0,0,3.4,.75),place(text('Cenas',195,42,25),2,18,4,label='label')])
    return [place(modal,100,1290,230,label='sceneModal',color=0x00ffffff),place(button,101,1580,930,label='sceneButton')]

def methods(a,scope):
    categories=[('Vestiário',[]),('Jogadores',[]),('Quadros',[]),('Departamento médico',[])]
    for scene in scope['scenes']:
        label=scene['label'];group=3 if label.startswith('Departamento médico') else 1 if ('Camisa ' in label or 'camisa ' in label) else 2 if 'Quadro' in label else 0
        categories[group][1].append({'label':label,'code':scene['id']})
    categories=[(name,items) for name,items in categories if items]
    root=[{'label':'Automático · ordem aleatória','code':-1}]+[{'label':name,'code':-101-i} for i,(name,_) in enumerate(categories)]
    objects=lambda items:('array',tuple(('map',v) for v in items))
    groups=('array',tuple(objects(items) for _,items in categories));root_items=objects(root)
    def init(a):
        for key,value in (('modalOpen',False),('sceneFocus',0),('sceneGroup',-1),('sceneItems',root_items)):a.set(R(1),key,value)
        a.set(T('sceneModal'),'_visible',False);a.set(T('sceneModal'),'_alpha',0);a.set(T('sceneButton'),'owner',R(1));a.set(T('sceneButton'),'onRelease',T('SceneButtonClick'));a.set(R(1),'onEnterFrame',T('WaitForSceneClips'))
        a.when(b.G('Server16RoomSequence'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16RoomSequence',0));a.do(R(1),'PublishScene',-1)
        a.do(PATH('Key'),'addListener',R(1))
    a.function('InitSceneControl',0,init)
    a.function('SceneButtonClick',0,lambda a:a.do(P(R(1),'owner'),'OpenScenes'))
    def wait(a):
        a.when(T('sceneModal'),lambda a:(a.do(R(1),'RefreshSceneModal'),a.set(T('sceneButton'),'owner',R(1)),a.set(T('sceneButton'),'onRelease',T('SceneButtonClick')),a.set(R(1),'onEnterFrame',None)))
    a.function('WaitForSceneClips',0,wait)
    def publish(a):
        a.set(b.GLOBAL,'Server16RoomSequence',b.plus(b.G('Server16RoomSequence'),1));value=f'S16ROOM1|{scope["pid"]}|{scope["nonce"]}|'
        for part in (b.G('Server16RoomSequence'),'|',R(2),'|ENDROOM'):value=b.plus(value,part)
        a.set(b.GLOBAL,'Server16RoomRequest',value)
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
            a.when(EQ(index,T('sceneFocus')),lambda a,row=row:(a.set(P(row,'highlight'),'_alpha',100),a.set(P(row,'label'),'textColor',0x172b34)))
        for name,title_text,method in (('previousPage','< Anterior','PreviousScenePage'),('nextPage','Próxima >','NextScenePage'),('backGroup','< Voltar','SceneBackButton')):
            button=P(T('sceneModal'),name);a.set(button,'owner',R(1));a.set(button,'onRelease',T(method));a.set(P(button,'label'),'text',title_text)
            if name!='backGroup':a.set(button,'_visible',('bin',103,P(T('sceneItems'),'length'),5))
        a.do(M('HelpManager'),'Update')
    a.function('RefreshSceneModal',0,refresh)
    a.function('OpenScenes',0,lambda a:(a.set(R(1),'modalOpen',True),a.do(R(1),'PublishScene',-2),a.do(R(1),'RefreshSceneModal')))
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
        a.when(T('modalOpen'),lambda a:a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','ADVANCE','Selecionar'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar')))))
        a.ret(('array',(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','SQUARE','Cenas'),CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'))))
    a.function('getHelpContext',0,help)
    def key(a):
        def back(a):
            a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:(a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.do(M('InputManager'),'DisableCurrentLocalEventHandler')));a.ret(True)
        a.when(EQ(R(2),P(M('InputCodes'),'BACK')),back)
        for name in ('PRIMARY_SELECT','SELECT','ADVANCE'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'ApplyScene'),lambda a:a.do(R(1),'OpenScenes')),a.ret(True)))
        for name in ('SECONDARY_SELECT','SECONDARY','SQUARE','X'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')),a.ret(True)))
        def arrows(a):
            for name,delta in (('UP',-1),('DOWN',1),('LEFT',-5),('RIGHT',5),('UI_UP',-1),('UI_DOWN',1),('UI_LEFT',-5),('UI_RIGHT',5),('PREVIOUS',-5),('NEXT',5),('L1',-5),('R1',5)):
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,delta=delta:(a.do(R(1),'ShiftScene',delta),a.ret(True)))
        a.when(T('modalOpen'),arrows);a.ret(True)
    a.function('LocalEventHandler',2,key)
    def keyboard(a):
        a.when(EQ(CALL(PATH('Key'),'getCode'),9),lambda a:a.when(T('modalOpen'),lambda a:a.do(R(1),'CloseScenes'),lambda a:a.do(R(1),'OpenScenes')))
    a.function('onKeyDown',0,keyboard)
