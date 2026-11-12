"""Small native APT gallery shell, complete navigation and clickable controls."""
from pathlib import Path
import argparse,copy,json,os,struct,sys,xml.etree.ElementTree as ET

CLASS=('game','screens','career','server16','TrophyRoom');FULL='.'.join(CLASS);PAGE=FULL.replace('.','/')
XML='data/ui/layout/careermanagerhubcfg.xml';NAV='data/ui/nav/careermode/mainmenuhubflow.nav'
FLOW='data/ui/nav/careermode/server16trophyroomflow.nav';BIG='data/ui/game/screens/career/server16/trophyroom.big'


def screen(game,output):
    game=Path(game);os.environ['SERVER16_GAME_ROOT']=str(game)
    source=game/'ModCarrerMode/source';base=source/'club_environment'
    sys.path[:0]=list(map(str,(source,base,base/'vendor',base/'bank',base/'preview',source/'club_browser')))
    import portable_paths as portable
    import build_screen as b
    # When run by file, Python must not bind this builder as the bank builder.
    if not hasattr(b,'reg'):
        import importlib.util
        spec=importlib.util.spec_from_file_location('gallery_bank_builder',base/'bank/build_screen.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
    from build_preview import Code
    import native_roster_footer as footer
    # The shared assembler's function emitter resolves its owner through the
    # bank module's globals. Bind it to THIS screen, including fallback imports.
    import types
    class TrophyCode(Code):
        function=types.FunctionType(Code.function.__code__,dict(Code.function.__globals__,CLASS=CLASS,FULL=FULL),argdefs=Code.function.__defaults__)
    from formats import BigFile,AptFile,Reader
    from apt_actions import Actions
    from PIL import Image
    import io
    R,T,P,CALL,PATH,M,EQ=b.reg,b.this,b.prop,b.call,b.path,b.MANAGER,b.equal
    big=BigFile(portable.BANK/'careertype.big');apt=AptFile(big);data=apt.data
    root=Reader(big.entries['1'].data,20,8).ptr();count,table=struct.unpack_from('<I4xQ',data,root+56)
    chars=[];additions={};template=apt.root_frames[0][0];panel=AptFile(BigFile(game/'data/ui/game/components/careercomponents/careerhubwidget.big'))
    def append(blob):data.extend(bytes(-len(data)%8));at=len(data);data.extend(blob);return at
    def addchar(blob):cid=count+len(chars);chars.append(append(blob));return cid
    def place(cid,depth,x,y,sx=1,sy=1,label=None,color=0xffffffff):
        raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if label else 14,depth,cid,sx,0,0,sy,x,y);struct.pack_into('<II',raw,44,color,0);struct.pack_into('<Q',raw,56,append(label.encode()+b'\0') if label else 0);return append(raw)
    def bitmap(image):
        stream=io.BytesIO();image.save(stream,format='DDS',pixel_format='DXT5');dds=bytearray(stream.getvalue());width,height=image.size
        # FIFA's APT reader expects the legacy block-compressed DDS fields,
        # as in the working dressing-room controls, rather than Pillow's BPP.
        struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
        assert dds[84:88]==b'DXT5' and struct.unpack_from('<I',dds,88)[0]==0
        tid=count+len(chars);raw=bytearray(panel.data[panel.characters[1].offset:panel.characters[1].offset+40]);struct.pack_into('<I',raw,32,tid);addchar(raw);additions[str(tid+1)]=dds
        sid=count+len(chars);raw=bytearray(panel.data[panel.characters[2].offset:panel.characters[2].offset+56]);struct.pack_into('<I',raw,16,tid<<16);struct.pack_into('<4fI',raw,32,0,0,width,height,sid);addchar(raw)
        geo=bytearray(panel.big.entries['3'].data[:96]);geo.extend(b''.join(struct.pack('<8f',x,y,0,0,0,0,0,0) for x,y in ((0,height),(0,0),(width,0),(width,0),(width,height),(0,height))))
        for off,value in ((0,len(geo)),(16,len(geo)-16),(32,len(geo)-32),(52,tid)):struct.pack_into('<I',geo,off,value)
        struct.pack_into('<6f',geo,64,1,0,0,1,0,0);additions[str(sid+1)]=bytes(geo);return sid
    # Scene chrome is drawn by the shared native HUD. This APT owns only
    # input and the native HelpManager footer; there are no bottom action cards.
    # Keep a real named timeline clip, as in the other working native screens.
    # It is transparent; all visible content is drawn by the crisp native HUD.
    anchor=bitmap(Image.new('RGBA',(4,4),(255,255,255,0)))
    raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56])
    anchor_frame=append(struct.pack('<I4xQ',1,append(struct.pack('<Q',place(anchor,1,0,0)))))
    struct.pack_into('<I4xQ',raw,32,1,anchor_frame);struct.pack_into('<Q',raw,48,0)
    anchor_clip=addchar(raw)
    controls=[place(anchor_clip,1,0,0,label='uiAnchor')];focus_symbols=[anchor_clip]
    buttons=[('Próxima taça','camera'),('Câmera livre','free'),('Parede','style'),('Página','page'),('Detalhes','detail'),('Acervo','collection'),('Galeria','list'),('Sala 3D','3d'),('Clube','club'),('Treinador','coach')]
    newtable=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(chars),*chars));struct.pack_into('<I4xQ',data,root+56,count+len(chars),newtable)
    frame=append(struct.pack('<I4xQ',len(controls),append(struct.pack('<'+'Q'*len(controls),*controls))));struct.pack_into('<I4xQ',data,apt.characters[9].offset+32,1,frame)
    er=Reader(data,root+96,8);n=er.i();ex=er.ptr()
    for i in range(n):
        at=ex+i*16;old=Reader(data,at,8).text()
        if 'CareerType' in old:struct.pack_into('<Q',data,at,append(old.replace('game.screens.career.CareerType',FULL).encode()+b'\0'))
    blocks=list(Actions(apt).read_all().cache.values());dictionaries=[bytes(data[v[0].offset:v[0].end]) for v in blocks]
    a=TrophyCode(data);a.align();start=len(data);data.extend(dictionaries[0])
    for i,name in enumerate(CLASS[:-1]):
        parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
    def send(a,command):a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16TrophyRoom',command)
    def init(a):
        a.op(89);a.reg(2);a.op(118);a.op(93);a.do(R(1),'Initialize',FULL,None,True)
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
        a.set(R(1),'staticData',CALL(b.ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(b.ION,'GetEvents','Navigation'));a.set(R(1),'focusIndex',0);a.set(R(1),'freeOpen',False);a.set(R(1),'detailOpen',False)
        a.set(R(1),'coachCollection',False);a.set(R(1),'shelfOpen',True)
        for code in (65,68,83,87):a.set(R(1),'move'+str(code),False)
        for code in (33,34,112,113):a.set(R(1),'held'+str(code),False)
        a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
        # Native input must be ready before binding optional timeline clips.
        # A delayed/missing clip must never disable Back or the free camera.
        a.do(PATH('Key'),'addListener',R(1));a.when(PATH('Mouse'),lambda a:a.do(PATH('Mouse'),'addListener',R(1)))
        # Follow the working Finance lifecycle. Native help clips are created
        # during animate-in, after this screen constructor has returned.
        a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
        a.do(R(1),'OnAnimateInComplete')
    a.function(CLASS[-1],0,init,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    for i,(_,command) in enumerate(buttons):
        a.function('Click'+str(i),0,lambda a,i=i:a.do(P(R(1),'owner'),'Choose',i))
        a.function('Hover'+str(i),0,lambda a,i=i:(a.set(P(R(1),'owner'),'focusIndex',i),a.do(P(R(1),'owner'),'RefreshButtons')))
    def background(a,scene):
        # The native background provider owns the cover. It removes it only
        # after all models are ready, rather than at the first RT/A click.
        a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16FrontendTick','tick')
    def choose(a):
        a.when(('bin',16,T('detailOpen'),('bin',17,EQ(R(2),6),EQ(R(2),7))),lambda a:a.ret())
        a.when(('bin',16,('not',T('shelfOpen')),EQ(R(2),7)),lambda a:a.ret())
        a.when(('bin',16,T('freeOpen'),EQ(R(2),0)),lambda a:a.ret())
        a.when(('bin',16,('bin',16,('not',T('shelfOpen')),('not',T('backgroundReady'))),('bin',17,('bin',17,EQ(R(2),0),EQ(R(2),1)),EQ(R(2),4))),lambda a:a.ret())
        for i,(_,command) in enumerate(buttons):
            def action(a,i=i,command=command):
                if i in (1,4,7):
                    # A previous visit's ready notification cannot uncover a
                    # new 3D request before its own native publication.
                    a.when(T('shelfOpen'),lambda a:a.set(R(1),'backgroundReady',False))
                if i==0:a.when(T('shelfOpen'),lambda a:send(a,'shelf_next'),lambda a:send(a,command))
                elif i==1:
                    def camera_mode(a):
                        a.when(T('freeOpen'),lambda a:(send(a,'fixed'),a.set(R(1),'freeOpen',False),a.set(R(1),'detailOpen',True)),
                               lambda a:(send(a,'free'),a.set(R(1),'freeOpen',True),a.set(R(1),'detailOpen',False)))
                    a.when(T('shelfOpen'),lambda a:(send(a,'3d'),a.set(R(1),'shelfOpen',False),a.set(R(1),'freeOpen',False),a.set(R(1),'detailOpen',True)),camera_mode)
                elif i==4:
                    a.when(T('shelfOpen'),lambda a:(send(a,'shelf_detail'),a.set(R(1),'shelfOpen',False),a.set(R(1),'detailOpen',True)),lambda a:(send(a,command),a.set(R(1),'detailOpen',('not',T('detailOpen')))))
                else:send(a,command)
                if i==4:a.set(R(1),'freeOpen',False)
                if i==6:background(a,False)
                if i in (1,4,7):background(a,True)
                if i in (6,7):a.set(R(1),'shelfOpen',i==6);a.set(R(1),'freeOpen',False);a.set(R(1),'detailOpen',i==7)
                if i==0:a.set(R(1),'freeOpen',False);a.when(('not',T('shelfOpen')),lambda a:a.set(R(1),'detailOpen',True))
                if i==5:a.set(R(1),'coachCollection',('not',T('coachCollection')));a.set(R(1),'freeOpen',False);a.set(R(1),'detailOpen',True)
                if i in (8,9):a.set(R(1),'coachCollection',i==9)
            a.when(EQ(R(2),i),action)
        a.do(R(1),'RefreshButtons')
    a.function('Choose',1,choose)
    def refresh(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')))
        a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show')
        footer.apply(a)
    a.function('RefreshButtons',0,refresh)
    from trophy_room import background_cover
    background_cover.emit(a,b)
    def ui_tick(a):
        # Run the provider queue on FIFA's genuine UI owner, not Render.
        background(a,False)
        a.do(R(1),'SyncBackgroundCover')
        a.set(R(1),'helpFrames',('bin',71,T('helpFrames'),1))
        a.when(('bin',17,EQ(T('helpFrames'),3),EQ(T('helpFrames'),30)),lambda a:a.do(R(1),'RefreshButtons'))
        footer.apply(a)
    a.function('UiTick',0,ui_tick)
    def help(a):
        normal=[('ADVANCE','Detalhes'),('BACK','Galeria'),('L2R2','Próxima / anterior'),('OPTION_TOP','Próxima taça'),('OPTION_LEFT','Câmera livre'),('L1','Galeria')]
        free=[('BACK','Galeria'),('LAS_UD','Andar'),('RAS_LR','Olhar'),('L2R2','Descer / subir'),('OPTION_LEFT','Ver taça'),('L1','Galeria')]
        def result(a,items):a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',k,v) for k,v in items)))
        a.when(T('shelfOpen'),lambda a:result(a,[('ADVANCE','Ver taça em 3D'),('BACK','Voltar'),('LAS_UD','Navegar'),('L2R2','Clube / treinador'),('L1','Galeria'),('R1','Sala 3D'),('OPTION_TOP','Próxima página')]))
        a.when(T('freeOpen'),lambda a:result(a,free))
        a.when(T('detailOpen'),lambda a:result(a,[('BACK','Voltar'),('L2R2','Próxima / anterior'),('RAS_LR','Rotacionar'),('L1R1','Zoom'),('LAS_UD','Histórico'),('OPTION_LEFT','Câmera livre')]))
        result(a,normal)
    a.function('getHelpContext',0,help)
    def begin(a):
        a.when(T('screenReady'),lambda a:a.ret());a.set(R(1),'screenReady',True)
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
        a.set(R(1),'helpFrames',0);a.set(R(1),'onEnterFrame',T('UiTick'));a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','');a.do(b.ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
        a.do(R(1),'RegisterBackgroundCover')
        a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')));a.do(R(1),'RefreshButtons')
    a.function('BeginInput',0,begin)
    def complete(a):
        a.when(('bin',17,T('exiting'),T('helpStarted')),lambda a:a.ret());a.set(R(1),'helpStarted',True)
        a.do(R(1),'BeginInput')
    a.function('OnAnimateInComplete',0,complete)
    def key(a):
        def back(a):
            a.when(T('detailOpen'),lambda a:(send(a,'close_detail'),a.set(R(1),'detailOpen',False),a.do(R(1),'RefreshButtons')),
                   lambda a:a.when(T('shelfOpen'),lambda a:a.do(b.ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),lambda a:a.do(R(1),'Choose',6)));a.ret(True)
        a.when(EQ(R(2),P(M('InputCodes'),'BACK')),back)
        moving=('bin',17,('bin',17,T('move65'),T('move68')),('bin',17,T('move83'),T('move87')))
        for name,i in [('L1',6),('R1',7)]:
            # Native analog triggers control continuous zoom during inspection.
            # Consume the APT aliases without changing view or local UI state.
            def view_key(a,i=i):
                a.when(T('detailOpen'),lambda a:a.ret(True))
                a.do(R(1),'Choose',i);a.ret(True)
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),view_key)
        # Physical LB/RB are edge-owned by the native module. Consume these
        # aliases, which can arrive after its 180 ms UI debounce, without
        # executing a second (or oppositely mapped) navigation command.
        def native_shoulders(a):
            a.when(('bin',16,('not',T('shelfOpen')),('not',T('freeOpen'))),lambda a:(a.set(R(1),'detailOpen',True),a.do(R(1),'RefreshButtons')))
            a.ret(True)
        for name in ('L2','R2'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),native_shoulders)
        for name,i in [('OPTION_LEFT',1),('OPTION_TOP',0),('R3',2),('L3',6)]:
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,i=i:(a.do(R(1),'Choose',i),a.ret(True)))
        a.when(('bin',16,('bin',17,T('freeOpen'),T('detailOpen')),moving),lambda a:a.ret(True))
        def shelf_keys(a):
            for name,command in [('UP','shelf_up'),('LAS_UP','shelf_up'),('DOWN','shelf_down'),('LAS_DOWN','shelf_down'),('LEFT','shelf_left'),('LAS_LEFT','shelf_left'),('RIGHT','shelf_right'),('LAS_RIGHT','shelf_right')]:
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,c=command:(send(a,c),a.ret(True)))
        a.when(T('shelfOpen'),shelf_keys)
        def detail_keys(a):
            for name,command in [('UP','detail_up'),('LAS_UP','detail_up'),('DOWN','detail_down'),('LAS_DOWN','detail_down')]:
                a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,c=command:(send(a,c),a.ret(True)))
        a.when(T('detailOpen'),detail_keys)
        a.when(('bin',17,T('freeOpen'),T('detailOpen')),lambda a:a.ret(True))
        for name,command in [('LEFT','previous'),('LAS_LEFT','previous'),('RIGHT','camera'),('LAS_RIGHT','camera')]:
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a,c=command:(send(a,c),a.ret(True)))
        for name in ('PRIMARY_SELECT','ADVANCE'):
            a.when(('bin',16,P(M('InputCodes'),name),EQ(R(2),P(M('InputCodes'),name))),lambda a:(a.do(R(1),'Choose',4),a.ret(True)))
        a.ret(True)
    a.function('LocalEventHandler',1,key)
    def keyboard(a):
        a.set(R(1),'keyCode',CALL(PATH('Key'),'getCode'))
        for code in (65,68,83,87):a.when(EQ(T('keyCode'),code),lambda a,code=code:a.set(R(1),'move'+str(code),True))
        for code,i in [(112,0),(113,1)]:
            def press(a,code=code,i=i):
                a.when(('not',T('held'+str(code))),lambda a:(a.set(R(1),'held'+str(code),True),a.do(R(1),'Choose',i)))
            a.when(EQ(T('keyCode'),code),press)
        for code,i in [(114,4),(115,5),(80,3),(71,6),(72,7)]:a.when(EQ(T('keyCode'),code),lambda a,i=i:a.do(R(1),'Choose',i))
        for code,listing,scene in [(33,'shelf_prev','previous'),(34,'shelf_next','camera')]:
            def page_key(a,code=code,listing=listing,scene=scene):
                def press(a):
                    a.set(R(1),'held'+str(code),True)
                    a.when(T('shelfOpen'),lambda a:send(a,listing),lambda a:a.when(('not',T('freeOpen')),lambda a:(send(a,scene),a.set(R(1),'detailOpen',True),a.do(R(1),'RefreshButtons'))))
                a.when(('not',T('held'+str(code))),press)
            a.when(EQ(T('keyCode'),code),page_key)
    a.function('onKeyDown',0,keyboard)
    def keyup(a):
        a.set(R(1),'keyCode',CALL(PATH('Key'),'getCode'))
        for code in (65,68,83,87):a.when(EQ(T('keyCode'),code),lambda a,code=code:a.set(R(1),'move'+str(code),False))
        for code in (33,34,112,113):a.when(EQ(T('keyCode'),code),lambda a,code=code:a.set(R(1),'held'+str(code),False))
    a.function('onKeyUp',0,keyup)
    def mouse(a):
        # APT is authored at 1920x1080; the crisp native gallery uses 1600x900.
        # Local mouse coordinates already account for ultrawide side margins.
        a.set(R(1),'pointerX',('bin',12,T('_xmouse'),5/6));a.set(R(1),'pointerY',('bin',12,T('_ymouse'),5/6))
        def inside(x,y,w,h):return ('bin',16,('bin',16,('not',('bin',15,T('pointerX'),x)),('bin',15,T('pointerX'),x+w)),('bin',16,('not',('bin',15,T('pointerY'),y)),('bin',15,T('pointerY'),y+h)))
        # The native HelpManager owns its own footer hit targets.
        for x,w,i in ((1130,180,6),(1320,220,7)):
            a.when(inside(x,55,w,46),lambda a,i=i:(a.do(R(1),'Choose',i),a.ret()))
        def shelf_mouse(a):
            a.when(inside(60,143,210,42),lambda a:a.do(R(1),'Choose',8));a.when(inside(282,143,230,42),lambda a:a.do(R(1),'Choose',9))
            for index in range(18):
                x=60+(index%6)*(1460-5*12)/6+(index%6)*12;y=205+(index//6)*196
                def open_cup(a,index=index):
                    send(a,'shelf_open_'+str(index));background(a,True);a.set(R(1),'shelfOpen',False);a.set(R(1),'detailOpen',True);a.set(R(1),'freeOpen',False);a.do(R(1),'RefreshButtons');a.ret()
                a.when(inside(x,y,(1460-5*12)/6,184),open_cup)
            a.ret()
        a.when(T('shelfOpen'),shelf_mouse)
        # Native HUD owns history, scroll and cup arrows inside this card.
        a.when(inside(1070,213,474,572),lambda a:a.ret())
        a.when(('bin',16,('not',('bin',15,T('pointerY'),195)),('bin',15,T('pointerY'),832)),lambda a:None,lambda a:a.ret())
        a.when(('bin',17,T('freeOpen'),T('detailOpen')),lambda a:a.ret())
        send(a,'pick');a.set(R(1),'detailOpen',True);a.do(R(1),'RefreshButtons')
    a.function('onMouseDown',0,mouse)
    def exit(a):
        a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True);a.do(PATH('Key'),'removeListener',R(1));a.when(PATH('Mouse'),lambda a:a.do(PATH('Mouse'),'removeListener',R(1)));a.set(R(1),'onEnterFrame',None)
        footer.restore(a)
        a.do(R(1),'RestoreBackgroundCover')
        a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(M('HelpManager'),'Show');a.do(R(1),'Shutdown')
    a.function('OnExitScreen',0,exit);a.op(0);a.finish();a.align();reg=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    for tag,target in ((apt.root_frames[0][1],start),(apt.root_frames[0][2],reg)):
        offsets=[i for i in range(0,len(apt.entry.original)-7,8) if apt.entry.original[i:i+8]==struct.pack('<Q',tag[-1])];assert len(offsets)==1;struct.pack_into('<Q',data,offsets[0],target)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,output,additions)
    parsed=AptFile(BigFile(output));actions=Actions(parsed).read_all();assert not actions.errors and FULL in parsed.exports
    assert all(parsed.characters[cid].frames for cid in focus_symbols),'Button focus must be a scriptable MovieClip'
    return output



def background_flow(raw):
    flow=json.loads(raw) if isinstance(raw,(str,bytes)) else copy.deepcopy(raw)
    state=next(s for s in flow['states'] if s['name']=='Gallery')
    # BOOTFLOW alone instantiates BackgroundBootflow: a static ImageLoader
    # which never subscribes to BackgroundDP. Use the native FIFA component
    # with BOOTFLOW as its image parameter, just like MainFEFlow. It follows
    # the provider's transparent image when the native room becomes ready.
    show=['loadView',['background','FIFA','BOOTFLOW']];hide=['unloadView',['background']]
    state['onEnter']=[a for a in state['onEnter'] if not (a[0]=='loadView' and a[1] and a[1][0]=='background')]
    state['onEnter'].append(show)
    if hide not in state['onExit']:state['onExit'].append(hide)
    # Keep the existing photograph view mounted. BackgroundDP switches its
    # image between BOOTFLOW and transparent only when native readiness changes.
    state['transitions']=[t for t in state['transitions'] if t.get('event') not in ('Server16TrophyGallery','Server16TrophyScene')]
    return flow


def navigation(game,output):
    game,output=Path(game),Path(output)
    sys.path[:0]=[str(game/'ModCarrerMode/source/club_environment/bank'),str(game/'ModCarrerMode/source/club_environment/vendor')]
    from build_package import read_nav,walk
    xml=ET.fromstring((game/XML).read_bytes());tile=next(t for t in xml.findall('panel_7/tile') if t.find('tileid').get('NAME')=='MY_TEAM_CLUB')
    assert tile.find('subtile1').get('DESTINATION')=='Server16EnterDressingRoom'
    if tile.find('subtile2') is None:
        subtile=ET.SubElement(tile,'subtile2',SUBTILE_TYPE='TILE',ID='908',DESTINATION='Server16EnterTrophyRoom',FG_PATH='',HIGHLIGHTABLE='TRUE')
        ET.SubElement(tile,'number_of_subtiles') if tile.find('number_of_subtiles') is None else None
        tile.find('number_of_subtiles').set('LENGTH','2')
        ET.SubElement(subtile,'data',ID='TITLE',TYPE='title',PARAM='SALA DE TROFÉUS',TRANSLATE='FALSE',FORMAT='HS',WIDTH='1500',HEIGHT='50',X='28',Y='22')
        ET.SubElement(subtile,'data',ID='S16_TROPHY_DESC',TYPE='text',PARAM='Explore as conquistas do clube em uma galeria 3D, com as taças de cada competição e o ano de cada título.',TRANSLATE='FALSE',FORMAT='SM',WIDTH='550',HEIGHT='100',X='28',Y='100')
        ET.SubElement(subtile,'data',ID='S16_TROPHY_IMAGE',TYPE='image',PATH='imgAssets/tiles/careerHub/server16_trophy_room.dds',WIDTH='1200',HEIGHT='300',X='505',Y='0')
    nav=read_nav((game/NAV).read_text(encoding='utf8'))
    host=next(v for v in walk(nav) if any(t.get('event')=='Server16EnterDressingRoom' for t in v.get('transitions',[])))
    if not any(t.get('event')=='Server16EnterTrophyRoom' for t in host['transitions']):host['transitions'].append(dict(event='Server16EnterTrophyRoom',targets=['Server16TrophyRoom']))
    owner=next(v for v in walk(nav) if any(s.get('name')=='Server16DressingRoom' for s in v.get('states',[])))
    if not any(s.get('name')=='Server16TrophyRoom' for s in owner['states']):owner['states'].append(dict(name='Server16TrophyRoom',type='external',file='/careerMode/server16TrophyRoomFlow.nav',outputs={'Back':'MainMenuHub','back':'MainMenuHub'}))
    flow=dict(name='Server16TrophyRoomFlow',initial=dict(targets=['Gallery']),states=[dict(name='Gallery',
        onEnter=[['executeCMAction',['EnterCalendar']],['loadScreenController',['Calendar']],['loadView',['screen',PAGE]]],
        onExit=[['unloadView',['screen',PAGE]],['unloadScreenController',['Calendar']]],
        transitions=[dict(event=e,targets=['Back'],actions=[['executeCMAction',['ReturnToHubFromCalendar']]]) for e in ('Back','back')])])
    flow=background_flow(flow)
    for relative,blob in {XML:ET.tostring(xml,encoding='utf-8',xml_declaration=True),NAV:(json.dumps(nav,ensure_ascii=False,indent=2)+'\n').encode(),FLOW:(json.dumps(flow,indent=2)+'\n').encode()}.items():
        path=output/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(blob)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    screen(a.game,a.output/BIG);navigation(a.game,a.output)
