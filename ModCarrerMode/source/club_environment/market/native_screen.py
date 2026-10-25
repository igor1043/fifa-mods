"""Separate native FIFA APT, built in staging using the loan screen's ABI."""
from pathlib import Path
import io,json,struct,sys
from PIL import Image,ImageFont,ImageDraw
from functools import lru_cache
import build_screen as b
from build_preview import Code
from formats import AptFile,BigFile,Placement,Reader
from apt_actions import Actions
from bank_art import texture_writer
from layout import TABS

CLASS=('game','screens','career','server16','TransferMarket')
FULL='.'.join(CLASS);PAGE='game/screens/career/server16/TransferMarket'
R=b.reg;T=b.this;P=b.prop;EQ=b.equal;CALL=b.call;PATH=b.path;M=b.MANAGER;ION=b.ION
def arr(values):return ('array',tuple(values))
def color(value):return 0xff000000|int(value.lstrip('#'),16)

@lru_cache(maxsize=8192)
def fit(value,width,size):
    import os
    font=ImageFont.truetype(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/arial.ttf'),round(size))
    text=str(value)
    if font.getlength(text)<=width-6:return text
    while text and font.getlength(text+'…')>width-6:text=text[:-1]
    return text.rstrip()+'…'

def neighbors(actions):
    result=[]
    for i,a in enumerate(actions):
        x=a['x']+a['w']/2;y=a['y']+a['h']/2;row=[]
        for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
            options=[]
            for j,c in enumerate(actions):
                if j==i:continue
                xx=c['x']+c['w']/2-x;yy=c['y']+c['h']/2-y
                primary=xx*dx+yy*dy;cross=abs(xx*dy-yy*dx)
                if primary>1:options.append((primary+cross*4,j))
            row.append(min(options)[1] if options else i)
        result.append(row)
    return result

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
        a.set(R(1),'page',next(i for i,s in enumerate(scenes) if s['key']=='overview'));a.set(R(1),'focus',0)
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100);a.set(R(1),'onEnterFrame',T('WaitForClips'))
        a.do(R(1),'WaitForClips')
    a.function(CLASS[-1],0,ctor,True)
    a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    keys={s['key']:i for i,s in enumerate(scenes)}
    token=str(scenes[0].get('entryToken','review'));available=scenes[0].get('ready',True)
    automatic=bool(scenes[0].get('automatic',False))
    def ready(a):
        def bind(a):
            for i,s in enumerate(scenes):
                for j,action in enumerate(s['actions']):
                    button=P(T('scene'+str(i)),'action'+str(j));a.set(button,'owner',R(1));a.set(button,'index',j)
                    a.set(button,'target',-3 if action['target']=='leave' else keys.get(action['target'],-2));a.set(button,'onRelease',T('Click'));a.set(button,'onRollOver',T('Over'))
            a.set(R(1),'onEnterFrame',None)
            a.set(T('loadingCover'),'_visible',False)
            if automatic:
                a.set(R(1),'pollFrames',0)
                def show_data(a):
                    a.set(b.GLOBAL,'Server16MarketEntryAwaiting',False)
                    a.set(T('loadingCover'),'_visible',False);a.set(R(1),'waiting',False)
                def wait_data(a):
                    a.when(b.G('Server16MarketEntryAwaiting'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16MarketEntryToken',token))
                    a.set(b.GLOBAL,'Server16MarketEntryAwaiting',True)
                    a.set(T('loadingCover'),'_visible',True);a.set(R(1),'waiting',True)
                    a.set(R(1),'onEnterFrame',T('PollAutomatic'))
                if available:
                    # The native owner gate has already verified this package's
                    # session, club, date and fresh readiness publication.
                    show_data(a)
                else:wait_data(a)
            a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
            a.do(R(1),'Refresh');a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
            a.do(R(1),'OnAnimateInComplete')
        # Named children are created after their parent MovieClip. Wait for the
        # last interactive child as well before binding every scene's input.
        last_scene=scenes[-1]
        gate=P(T('scene'+str(len(scenes)-1)),'action'+str(len(last_scene['actions'])-1))
        a.when(('bin',16,T('scene0'),gate),bind)
    a.function('WaitForClips',0,ready)
    def poll(a):
        a.set(R(1),'pollFrames',('bin',71,T('pollFrames'),1))
        def reload(a):
            # A busy controller can ignore a reload. Keep this callback alive
            # until OnExitScreen actually acknowledges removal of the view.
            a.set(R(1),'pollFrames',0);a.set(R(1),'autoReloading',True)
            a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RefreshTransferMarket','')
        a.when(('bin',103,T('pollFrames'),89),reload)
    a.function('PollAutomatic',0,poll)
    def refresh(a):
        for i,s in enumerate(scenes):
            clip=T('scene'+str(i));a.set(clip,'_visible',EQ(T('page'),i))
            for j,_ in enumerate(s['actions']):a.set(P(P(clip,'action'+str(j)),'selected'),'_alpha',('bin',12,EQ(T('focus'),j),100))
        a.do(M('HelpManager'),'Update')
    a.function('Refresh',0,refresh)
    def complete(a):
        a.when(T('screenReady'),lambda a:a.ret())
        a.set(R(1),'screenReady',True)
        a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
        a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
    a.function('OnAnimateInComplete',0,complete)
    def go(a):
        a.when(EQ(R(2),-2),lambda a:(a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'Server16RefreshTransferMarket',''),a.ret()))
        a.when(EQ(R(2),-3),lambda a:(a.do(R(1),'Back'),a.ret()))
        focuses=[]
        for scene in scenes:
            key=scene['key'];tab='leagues' if key.startswith(('leagues','league:')) else 'deals' if key.startswith('deals') else key
            focuses.append(next((i for i,v in enumerate(scene['actions']) if v['target']==tab),0))
        a.set(R(1),'page',R(2));a.set(R(1),'focus',('index',arr(focuses),R(2)));a.do(R(1),'Refresh')
    a.function('Go',1,go)
    def select(a):
        targets=arr(arr(-3 if x['target']=='leave' else keys.get(x['target'],-2) for x in s['actions']) for s in scenes)
        a.do(R(1),'Go',('index',('index',targets,T('page')),T('focus')))
    a.function('Select',0,select)
    def over(a):a.set(P(R(1),'owner'),'focus',P(R(1),'index'));a.do(P(R(1),'owner'),'Refresh')
    def click(a):
        a.when(P(P(R(1),'owner'),'waiting'),lambda a:a.ret())
        a.do(P(R(1),'owner'),'Go',P(R(1),'target'))
    a.function('Over',0,over);a.function('Click',0,click)
    def move(a):
        table=arr(arr(arr(r) for r in neighbors(s['actions'])) for s in scenes)
        a.set(R(1),'focus',('index',('index',('index',table,T('page')),T('focus')),R(2)));a.do(R(1),'Refresh')
    a.function('Move',1,move)
    def shift_page(a):
        previous=arr(keys.get(s.get('pagination',{}).get('previous'),i) for i,s in enumerate(scenes))
        following=arr(keys.get(s.get('pagination',{}).get('next'),i) for i,s in enumerate(scenes))
        a.when(EQ(R(2),-1),lambda a:a.do(R(1),'Go',('index',previous,T('page'))),lambda a:a.do(R(1),'Go',('index',following,T('page'))))
    a.function('ShiftPage',1,shift_page)
    def horizontal(a):
        pages=arr(s.get('pagination',{}).get('count',1) for s in scenes)
        a.when(('bin',103,('index',pages,T('page')),1),lambda a:a.do(R(1),'ShiftPage',R(2)),
            lambda a:a.when(EQ(R(2),-1),lambda a:a.do(R(1),'Move',0),lambda a:a.do(R(1),'Move',1)))
    a.function('Horizontal',1,horizontal)
    def tab(a):
        roots=[keys[k] for k,_ in TABS]
        selected=[]
        for scene in scenes:
            key=scene['key']
            group='leagues' if key.startswith(('leagues','league:')) else 'deals' if key.startswith('deals') else key
            selected.append(next((i for i,(k,_) in enumerate(TABS) if k==group),0))
        index=('bin',63,('bin',71,('bin',71,('index',arr(selected),T('page')),R(2)),len(TABS)),len(TABS))
        a.do(R(1),'Go',('index',arr(roots),index))
    a.function('ChangeTab',1,tab)
    def back(a):
        a.set(R(1),'autoReloading',False)
        a.when(EQ(T('page'),keys['overview']),lambda a:(a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),P(T('navEvents'),'BACK'),''),a.ret()))
        a.do(R(1),'Go',('index',arr(keys.get(s['back'],keys['overview']) for s in scenes),T('page')))
    a.function('Back',0,back)
    def key(a):
        # FIFA PC calls LT/RT "L1/R1" and LB/RB "L2/R2". Use the latter
        # for the physical shoulders and the matching original footer icons.
        for name,method,argument in (('BACK','Back',None),('ADVANCE','Select',None),('PRIMARY_SELECT','Select',None),('LEFT','Horizontal',-1),('RIGHT','Horizontal',1),('LAS_LEFT','Horizontal',-1),('LAS_RIGHT','Horizontal',1),('UP','Move',2),('DOWN','Move',3),('LAS_UP','Move',2),('LAS_DOWN','Move',3),('L2','ChangeTab',-1),('R2','ChangeTab',1)):
            code=P(M('InputCodes'),name)
            def handle(a,method=method,argument=argument,name=name):
                if name!='BACK':a.when(T('waiting'),lambda a:a.ret(True))
                a.do(R(1),method,*(() if argument is None else (argument,)));a.ret(True)
            a.when(('bin',16,code,EQ(R(2),code)),handle)
        a.ret(True)
    a.function('LocalEventHandler',2,key)
    def help_context(a):
        items=[('ADVANCE','Selecionar'),('BACK','Voltar'),('L2R2','Abas')]
        pages=arr(s.get('pagination',{}).get('count',1) for s in scenes)
        def result(a,extra=()):a.ret(arr(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',code,label) for code,label in items+list(extra)))
        a.when(('bin',103,('index',pages,T('page')),1),lambda a:result(a,[('LAS_LR','Páginas')]),result)
    a.function('getHelpContext',0,help_context)
    def shutdown(a):
        a.when(T('exiting'),lambda a:a.ret());a.set(R(1),'exiting',True)
        a.set(R(1),'onEnterFrame',None)
        a.when(T('autoReloading'),lambda a:None,lambda a:a.set(b.GLOBAL,'Server16MarketEntryAwaiting',False))
        for i,s in enumerate(scenes):
            for j,_ in enumerate(s['actions']):
                for event in ('onRelease','onRollOver'):a.set(P(T('scene'+str(i)),'action'+str(j)),event,None)
        a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
    a.function('OnExitScreen',0,shutdown);a.op(0);a.finish()
    a.align();registration=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,registration

def build(game,output,scenes,assets,*,script_factory=None,full_name=FULL):
    game=Path(game);output=Path(output)
    big=BigFile(game/'ModCarrerMode/source/club_environment/bank/careertype.big');apt=AptFile(big);data=apt.data
    root=Reader(big.entries['1'].data,20,8).ptr();count,table=struct.unpack_from('<I4xQ',data,root+56)
    characters=[];additions={};template=apt.root_frames[0][0]
    def append(raw):data.extend(bytes(-len(data)%8));at=len(data);data.extend(raw);return at
    def character(raw):ident=count+len(characters);characters.append(append(raw));return ident
    def place(cid,depth,x,y,sx=1,sy=1,name=None,tint=0xffffffff):
        raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if name else 14,depth,cid,sx,0,0,sy,x,y)
        struct.pack_into('<II',raw,44,tint,0);struct.pack_into('<Q',raw,56,append(name.encode()+b'\0') if name else 0);return append(raw)
    def sprite(parts):
        raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);controls=append(struct.pack('<'+'Q'*len(parts),*parts))
        frame=append(struct.pack('<I4xQ',len(parts),controls));struct.pack_into('<I4xQ',raw,32,1,frame);struct.pack_into('<Q',raw,48,0);return character(raw)
    write=texture_writer(data,append,characters,count,additions,character)
    white=write(Image.new('RGBA',(4,4),'white'));image_chars={}
    dot_image=Image.new('RGBA',(32,32));ImageDraw.Draw(dot_image).ellipse((0,0,31,31),fill='white');dot=write(dot_image)
    for key,path in assets.items():
        with Image.open(path) as im:image=im.convert('RGBA')
        image_chars[key]=(write(image),image.size)
    def rect(depth,x,y,w,h,tint):return place(white,depth,x,y,w/4,h/4,tint=color(tint))
    def text(depth,node,name=None):
        raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,node['w'],node['h'])
        struct.pack_into('<II',raw,48,2,node.get('align',0));struct.pack_into('<If',raw,56,color(node['color']),node['size'])
        value=fit(node['text'],node['w'],node['size']);struct.pack_into('<QQ',raw,80,append(value.encode('utf8')+b'\0'),0)
        return place(character(raw),depth,node['x'],node['y'],name=name)
    scene_controls=[]
    for i,scene in enumerate(scenes):
        parts=[]
        for depth,node in enumerate(scene['nodes'],1):
            if node['y']>=930:continue # Real FIFA HelpManager owns its footer.
            kind=node['type']
            if kind=='rect':parts.append(rect(depth,node['x'],node['y'],node['w'],node['h'],node['color']))
            elif kind=='dot':parts.append(place(dot,depth,node['x'],node['y'],node['w']/32,node['h']/32,tint=color(node['color'])))
            elif kind=='text':parts.append(text(depth,node))
            elif kind=='image':
                if node['asset'] in image_chars:
                    cid,(w,h)=image_chars[node['asset']];parts.append(place(cid,depth,node['x'],node['y'],node['w']/w,node['h']/h))
            elif kind=='action':
                w,h=node['w'],node['h'];border=[rect(1,0,0,w,3,'#35b8ff'),rect(2,0,h-3,w,3,'#35b8ff'),rect(3,0,0,3,h,'#35b8ff'),rect(4,w-3,0,3,h,'#35b8ff')]
                children=[rect(1,0,0,w,h,node['color']),place(sprite(border),2,0,0,name='selected')]
                if node['text']:children.append(text(3,dict(x=12,y=max(1,(h-node['size']*1.2)/2),w=w-24,h=node['size']*1.3,text=node['text'],size=node['size'],color=node['ink'],align=2)))
                parts.append(place(sprite(children),depth,node['x'],node['y'],name='action'+str(node['index'])))
        scene_controls.append(place(sprite(parts),i+1,0,0,name='scene'+str(i)))
    if full_name==FULL:
        # Opaque only within the content card; FIFA owns the footer beneath it.
        loading=[rect(1,60,90,1800,828,'#f4f6f7'),
            text(2,dict(x=110,y=130,w=1690,h=64,text='MERCADO DE TRANSFERÊNCIAS',size=40,color='#334b56')),
            text(3,dict(x=110,y=360,w=1690,h=48,text='Carregando o mercado desta carreira...',size=30,color='#334b56')),
            text(4,dict(x=110,y=420,w=1690,h=36,text='Consultando negociações e clubes em tempo real.',size=24,color='#6b818d'))]
        scene_controls.append(place(sprite(loading),len(scene_controls)+1,0,0,name='loadingCover'))
    frames=append(struct.pack('<I4xQ',len(scene_controls),append(struct.pack('<'+'Q'*len(scene_controls),*scene_controls))))
    struct.pack_into('<I4xQ',data,apt.characters[9].offset+32,1,frames)
    new_table=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(characters),*characters));struct.pack_into('<I4xQ',data,root+56,count+len(characters),new_table)
    er=Reader(data,root+96,8);n=er.i();exports=er.ptr()
    for i in range(n):
        at=exports+i*16;old=Reader(data,at,8).text()
        if 'CareerType' in old:struct.pack_into('<Q',data,at,append(old.replace('game.screens.career.CareerType',full_name).encode()+b'\0'))
    actions=Actions(apt).read_all();dictionaries=[bytes(data[v[0].offset:v[0].end]) for v in actions.cache.values()]
    start,registration=(script_factory or script)(data,dictionaries,scenes)
    for tag,target in ((apt.root_frames[0][1],start),(apt.root_frames[0][2],registration)):
        signature=struct.pack('<Q',tag[-1]);matches=[j for j in range(0,len(apt.entry.original)-7,8) if apt.entry.original[j:j+8]==signature]
        assert len(matches)==1;struct.pack_into('<Q',data,matches[0],target)
    output.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,output,additions)
    check=AptFile(BigFile(output));decoded=Actions(check).read_all();assert not decoded.errors;assert full_name in check.exports
    return dict(path=str(output),bytes=output.stat().st_size,scenes=len(scenes),characters=count+len(characters),native_font_descriptor=2,help='Original FIFA HelpManager',installed=False)
