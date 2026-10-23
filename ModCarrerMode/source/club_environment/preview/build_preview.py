import portable_paths as portable
"""Standalone native match preview with a reusable custom LineupPitch symbol."""
from pathlib import Path
import sys,json,struct,math,io
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
BANK=portable.BANK
import build_screen as b
from formats import BigFile,AptFile,Reader
from apt_actions import Actions
import preview_carousel as carousel
CLASS=('game','screens','career','server16','MatchPreview')
FULL='.'.join(CLASS);PAGE='game/screens/career/server16/MatchPreview'
POSITIONS=('GO','LIB','ALA','LD','ZAG','ZAG','ZAG','LE','ALA','VOL','VOL','VOL','MD','MC','MC','MC','ME','MEI','MEI','MEI','SA','SA','SA','PD','ATA','ATA','ATA','PE')
FIELD_X,FIELD_Y,FIELD_W,FIELD_H=12,94,640,760
PANEL_W,PANEL_H=664,854
HEAD_MAX=88

class Code(b.Code):
    def finish(self):
        for pointer,count in self.parameters:
            self.align();struct.pack_into('<Q',self.data,pointer,len(self.data))
            if not count:self.data.extend(bytes(16))
            for index in range(count):
                self.align();self.data.extend(struct.pack('<I',index+2));self.align()
                at=len(self.data);self.data.extend(bytes(8));self.fixups.append((at,'argument'+str(index)))
        strings={}
        for at,value in self.fixups:
            if isinstance(value,tuple):struct.pack_into('<i',self.data,at,self.labels[value[1]]-at-4)
            else:
                if value not in strings:strings[value]=len(self.data);self.data.extend(value.encode('utf8')+b'\0')
                struct.pack_into('<Q',self.data,at,strings[value])
        self.parameters=[];self.fixups=[]
    def object(self,values):
        return ('map',values)
    def expr(self,v):
        if isinstance(v,tuple) and v and v[0]=='map':
            for key,value in v[1].items():self.string(key);self.expr(value)
            self.expr(len(v[1]));self.op(67)
        elif isinstance(v,tuple) and v and v[0]=='not':self.expr(v[1]);self.op(18)
        elif type(v) is float:self.op(180);self.data.extend(struct.pack('<f',v))
        else:super().expr(v)

R=b.reg;P=b.prop;T=b.this;CALL=b.call;PATH=b.path;EQ=b.equal;G=b.G;M=b.MANAGER;ION=b.ION
def arr(v):return ('array',tuple(v))
def model(team):return ('map',{'team_id':team['team_id'],'name':team['name'],'probable':team['probable'],'formation':team['formation'],'players':arr(('map',p) for p in team['players'])})

def script(data,dictionaries,payload,head_ids):
    b.CLASS=CLASS;b.FULL=FULL
    a=Code(data);a.align();start=len(data);data.extend(dictionaries[0])
    for i,name in enumerate(CLASS[:-1]):
        parent=b.GLOBAL if not i else PATH(*CLASS[:i]);a.when(P(parent,name),lambda a:None,lambda a,p=parent,n=name:a.set(p,n,('object',)))
    def ctor(a):
        a.op(89);a.reg(2);a.op(118);a.op(93)
        a.do(M('ScreenManager'),'SetOnExitScreenCallback',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnExitScreen')))
        a.do(R(1),'Initialize',FULL,None,True)
        a.set(R(1),'screenReady',False)
        a.set(R(1),'staticData',CALL(ION,'GetScreenStaticData'));a.set(R(1),'navEvents',CALL(ION,'GetEvents','Navigation'))
        a.do(R(1),'InitComponents');a.do(R(1),'AnimateIn')
    a.function(CLASS[-1],0,ctor,True);a.expr(PATH(*CLASS));a.expr(PATH('ion','screen','BaseScreen'));a.op(105)
    a.function('getHelpContext',0,lambda a:a.ret(arr((CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem','BACK','Voltar'),))))
    def init(a):
        a.set(R(1),'userID',payload['user']['team_id'])
        a.set(R(1),'carouselPage',0)
        a.set(R(1),'portraitAssets',('map',{str(pid):True for pid in head_ids}))
        a.set(R(1),'pitchClipsReady',False)
        a.set(R(1),'onEnterFrame',T('WaitForPitchClips'))
    a.function('InitComponents',0,init)
    def populate(a):
        a.when(T('pitchClipsReady'),lambda a:a.ret())
        available=True
        for side in ('userPitch','opponentPitch'):
            for child in ('teamName','formation','crest','p0','p10'):
                available=('bin',16,available,P(T(side),child))
            available=('bin',16,available,P(P(T(side),'p10'),'face'))
        for child in ('venuePage','userHistory','opponentHistory','pageDot2'):
            available=('bin',16,available,T(child))
        a.when(('not',available),lambda a:a.ret())
        a.set(R(1),'pitchClipsReady',True);a.set(R(1),'onEnterFrame',None)
        if payload.get('available',True):
            for side,key in [('userPitch','user'),('opponentPitch','opponent')]:a.do(R(1),'RenderPitch',T(side),model(payload[key]))
        else:
            a.set(T('userPitch'),'_visible',False);a.set(T('opponentPitch'),'_visible',False)
        a.set(T('screenTitle'),'text','PRÓXIMA PARTIDA — ESCALAÇÕES')
        a.set(T('matchInfo'),'text',f"{payload['fixture'][3]%100:02d}/{payload['fixture'][3]//100%100:02d}/{payload['fixture'][3]//10000}   •   {payload['fixture'][4]//100:02d}:{payload['fixture'][4]%100:02d}")
        a.set(T('status'),'text','Provável escalação adversária. As escolhas finais podem mudar até a partida.')
        if not payload.get('available',True):
            a.set(T('status'),'text','Não há próxima partida agendada nesta carreira.');a.set(T('matchInfo'),'text','')
        a.do(R(1),'InitCarousel')
        # This existing view model supplies the user's current unsaved team sheet.
        if payload.get('available',True):a.do(PATH('game','uif','UIFUtility'),'RegisterDataProvider',R(1),P(PATH('game','uif','UIFDataProviderList'),'StartingXIDP'))
    a.function('WaitForPitchClips',0,populate)
    def render(a):
        clip=R(2);team=R(3)
        a.set(P(clip,'teamName'),'text',P(team,'name'))
        a.set(P(clip,'teamName'),'textColor',payload['opponent'].get('header_ink',0xffffff))
        a.set(P(clip,'caption'),'textColor',payload['opponent'].get('header_ink',0xffffff))
        a.when(EQ(P(team,'team_id'),payload['user']['team_id']),lambda a:(a.set(P(clip,'teamName'),'textColor',payload['user'].get('header_ink',0xffffff)),a.set(P(clip,'caption'),'textColor',payload['user'].get('header_ink',0xffffff))))
        a.set(P(clip,'formation'),'text',P(team,'formation'))
        a.set(P(clip,'caption'),'text','SEU TIME TITULAR')
        a.when(P(team,'probable'),lambda a:a.set(P(clip,'caption'),'text','PROVÁVEL ESCALAÇÃO'))
        a.do(R(1),'LoadCrest',P(clip,'crest'),P(team,'team_id'))
        # Portraits need more height than FIFA's shirt markers. Preserve the
        # formation's rows while spreading them to avoid heads covering names.
        a.set(R(1),'rowLevels',arr((0.0,)))
        for j in range(1,11):
            py=P(('index',P(team,'players'),j),'y');a.set(R(1),'newBand',True)
            for k in range(1,11):
                previous=('index',T('rowLevels'),k)
                cond=('bin',16,('bin',72,k,P(T('rowLevels'),'length')),('bin',72,CALL(PATH('Math'),'abs',('bin',11,py,previous)),.09))
                a.when(cond,lambda a:a.set(R(1),'newBand',False))
            a.when(T('newBand'),lambda a,py=py:a.do(T('rowLevels'),'push',py))
        a.set(R(1),'rowStep',('bin',13,590,CALL(PATH('Math'),'max',1,('bin',11,P(T('rowLevels'),'length'),1))))
        a.set(R(1),'headSize',CALL(PATH('Math'),'max',48,CALL(PATH('Math'),'min',HEAD_MAX,('bin',11,T('rowStep'),56))))
        for i in range(11):
            player=('index',P(team,'players'),i);slot=P(clip,'p'+str(i))
            a.set(R(1),'rowRank',1)
            for j in range(1,11):
                cond=('bin',16,('bin',72,j,P(T('rowLevels'),'length')),('bin',72,('index',T('rowLevels'),j),('bin',11,P(player,'y'),.09)))
                a.when(cond,lambda a:a.set(R(1),'rowRank',('bin',71,T('rowRank'),1)))
            a.when(EQ(P(player,'position'),0),lambda a:a.set(R(1),'rowRank',0))
            a.set(slot,'_x',('bin',71,82,('bin',12,CALL(PATH('Math'),'max',0,CALL(PATH('Math'),'min',1,P(player,'x'))),500)))
            a.set(slot,'_y',('bin',11,700,('bin',12,T('rowRank'),T('rowStep'))))
            a.set(P(slot,'face'),'desiredSize',T('headSize'))
            a.set(P(slot,'face'),'_x',('bin',13,('bin',11,0,T('headSize')),2))
            for label in ('ratingBG','positionBG','position','rating'):a.set(P(slot,label),'_y',T('headSize'))
            a.set(P(slot,'name'),'_y',('bin',71,T('headSize'),28))
            a.set(P(slot,'name'),'text',CALL(R(1),'FormatName',P(player,'name')))
            a.set(P(slot,'rating'),'text',P(player,'overall'))
            a.set(P(slot,'position'),'text',('index',arr(POSITIONS),P(player,'position')))
            a.set(P(slot,'position'),'textColor',0xe4427c)
            a.when(('bin',72,P(player,'position'),20),lambda a:a.set(P(slot,'position'),'textColor',0x7bdc41))
            a.when(('bin',72,P(player,'position'),9),lambda a:a.set(P(slot,'position'),'textColor',0x24b8e4))
            a.when(EQ(P(player,'position'),0),lambda a:a.set(P(slot,'position'),'textColor',0xe4c62b))
            a.do(R(1),'LoadPortrait',P(slot,'face'),P(player,'id'))
    a.function('RenderPitch',2,render)
    def format_name(a):
        a.set(R(1),'shortName',CALL(R(2),'toUpperCase'))
        def shorten(a):
            a.set(R(1),'nameParts',CALL(T('shortName'),'split',' '))
            a.when(('bin',103,P(T('nameParts'),'length'),1),lambda a:a.set(R(1),'shortName',('bin',71,('bin',71,CALL(T('shortName'),'substr',0,1),'. '),('index',T('nameParts'),('bin',11,P(T('nameParts'),'length'),1)))))
            a.when(('bin',103,P(T('shortName'),'length'),11),lambda a:a.set(R(1),'shortName',('index',T('nameParts'),('bin',11,P(T('nameParts'),'length'),1))))
            a.set(R(1),'shortName',CALL(T('shortName'),'substr',0,11))
        a.when(('bin',103,P(T('shortName'),'length'),10),shorten)
        a.ret(T('shortName'))
    a.function('FormatName',1,format_name)
    # Portrait DDSs are native resources in THIS movie. attachMovie resolves
    # local exports synchronously, without external paths or empty loader bounds.
    def portrait(a):
        a.set(R(1),'headSymbol','S16Head_0')
        a.when(('index',T('portraitAssets'),('bin',71,'',R(3))),lambda a:a.set(R(1),'headSymbol',('bin',71,'S16Head_',R(3))))
        a.set(R(1),'imageClip',CALL(R(2),'attachMovie',T('headSymbol'),'portrait',1))
        a.set(T('imageClip'),'_width',P(R(2),'desiredSize'));a.set(T('imageClip'),'_height',P(R(2),'desiredSize'))
        a.set(T('imageClip'),'_visible',True);a.set(T('imageClip'),'_alpha',100)
    a.function('LoadPortrait',2,portrait)
    def crest(a):
        a.set(R(1),'imageClip',CALL(R(2),'attachMovie',('bin',71,'S16Crest_',R(3)),'crest',1))
        a.set(T('imageClip'),'_width',56);a.set(T('imageClip'),'_height',56)
    a.function('LoadCrest',2,crest)
    def publish(a):
        def own(a):
            a.set(R(1),'published',('newmethod',PATH('game','uif','DataProviders'),'StartingXIDP',(R(2),)))
            a.set(R(1),'sheet',CALL(T('published'),'GetTeamSheetsAt',CALL(T('published'),'GetFavouriteTeamSheetIndex')))
            def matching(a):
                a.set(R(1),'livePlayers',arr(()))
                a.set(R(1),'livePlayersValid',True)
                for i in range(11):
                    pp=CALL(T('sheet'),'GetPlayersAt',i);info=CALL(pp,'GetSimpleInfo')
                    player=('map',{'id':CALL(info,'GetPlayerID'),'name':CALL(info,'GetName'),'position':CALL(info,'GetPositionID'),'overall':CALL(info,'GetOverall'),'x':CALL(pp,'GetPosX'),'y':CALL(pp,'GetPosY')})
                    a.do(T('livePlayers'),'push',player)
                    current=('index',T('livePlayers'),i)
                    valid=('bin',16,('bin',103,P(current,'id'),0),P(current,'name'))
                    for field,low,high in (('position',0,28),('overall',1,100),('x',0,1.001),('y',0,1.001)):
                        valid=('bin',16,valid,('bin',16,('not',('bin',72,P(current,field),low)),('bin',72,P(current,field),high)))
                    a.when(valid,lambda a:None,lambda a:a.set(R(1),'livePlayersValid',False))
                team=('map',{'team_id':T('userID'),'name':payload['user']['name'],'probable':False,'formation':CALL(T('sheet'),'GetType'),'players':T('livePlayers')})
                # Some hub publications expose shirts/names without player IDs.
                # Never erase the complete save projection with that payload.
                a.when(T('livePlayersValid'),lambda a:a.do(R(1),'RenderPitch',T('userPitch'),team))
            a.when(EQ(CALL(T('sheet'),'GetTeamID'),T('userID')),matching)
        a.when(EQ(R(3),P(PATH('game','uif','UIFDataProviderList'),'StartingXIDP')),own)
    a.function('Publish',2,publish)
    def animate(a):
        # BaseScreen.Initialize hands visibility to ScreenManager. Completing
        # Calendar's controller alone does not enter the native screen layer.
        for child in ('userPitch','opponentPitch','screenTitle','matchInfo','status','venuePage','userHistory','opponentHistory','previousPage','nextPage','pageLabel','pageDot0','pageDot1','pageDot2'):
            a.do(M('ScreenManager'),'AddItemToAnimateIn',T(child))
        a.do(M('ScreenManager'),'BeginAnimateIn',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('OnAnimateInComplete')))
        a.do(R(1),'OnAnimateInComplete')
    a.function('AnimateIn',0,animate)
    def complete(a):
        a.when(T('screenReady'),lambda a:a.ret())
        a.set(R(1),'screenReady',True)
        a.set(R(1),'_visible',True);a.set(R(1),'_alpha',100)
        a.do(ION,'SendEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
        a.do(ION,'SendSystemEvent',P(T('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
        a.do(M('InputManager'),'SetLocalEventHandler',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('LocalEventHandler')))
        a.do(R(1),'ShowPage',T('carouselPage'))
        a.do(M('HelpManager'),'Update')
    a.function('OnAnimateInComplete',0,complete)
    carousel.methods(a,payload,b)
    def shutdown(a):
        a.do(PATH('game','uif','UIFUtility'),'UnregisterDataProvider',R(1))
        a.do(M('InputManager'),'DisableCurrentLocalEventHandler');a.do(M('HelpManager'),'Clear');a.do(R(1),'Shutdown')
        # Same class-release pattern used by GridControl.Shutdown. A later
        # opening must initialize the freshly prepared payload, not old AS data.
        a.do(PATH('Object'),'registerClass',FULL,None)
        a.expr(PATH(*CLASS[:-1]));a.string(CLASS[-1]);a.op(58);a.op(23)
    a.function('OnExitScreen',0,shutdown);a.op(0);a.finish()
    a.align();register=len(data);data.extend(dictionaries[1]);a.string(FULL);a.op(28);a.string(FULL);a.expr(2);a.expr(PATH('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,register

def build(payload=None):
    if payload is None:payload=json.loads((HERE/'lineups.json').read_text(encoding='utf8'))
    big=BigFile(BANK/'careertype.big');apt=AptFile(big);data=apt.data;root=Reader(big.entries['1'].data,20,8).ptr()
    count,table=struct.unpack_from('<I4xQ',data,root+56);characters=[]
    def append(blob):data.extend(bytes(-len(data)%8));at=len(data);data.extend(blob);return at
    def char(blob):index=count+len(characters);characters.append(append(blob));return index
    def name(value):return append(value.encode('utf8')+b'\0')
    template=apt.root_frames[0][0]
    def place(cid,depth,x,y,w=1,h=1,label=None,color=0xffffffff):
        raw=bytearray(data[template.offset:template.offset+80]);struct.pack_into('<iii6f',raw,8,46 if label else 14,depth,cid,w,0,0,h,x,y);struct.pack_into('<II',raw,44,color,0);struct.pack_into('<Q',raw,56,name(label) if label else 0);return append(raw)
    def text(depth,x,y,width,height,size,label,color=0xff334b56,align=0,font=2,value=''):
        raw=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96]);struct.pack_into('<4f',raw,32,0,0,width,height);struct.pack_into('<II',raw,48,font,align);struct.pack_into('<If',raw,56,color,size);struct.pack_into('<QQ',raw,80,name(value),0);return place(char(raw),depth,x,y,label=label)
    def sprite(controls):
        controls_at=append(struct.pack('<'+'Q'*len(controls),*controls));frames=append(struct.pack('<I4xQ',len(controls),controls_at));raw=bytearray(data[apt.characters[9].offset:apt.characters[9].offset+56]);struct.pack_into('<I4xQ',raw,32,1,frames);return char(raw)
    panel=AptFile(BigFile(portable.GAME/'data/ui/game/components/careercomponents/careerhubwidget.big'))
    additions={};art_exports=[];image_resources={};art_symbols={}
    def texture(dds):
        ident=count+len(characters);raw=bytearray(panel.data[panel.characters[1].offset:panel.characters[1].offset+40]);struct.pack_into('<I',raw,32,ident);char(raw);additions[str(ident+1)]=bytes(dds);return ident
    def shape(tex,width,height,vertices=None):
        ident=count+len(characters);raw=bytearray(panel.data[panel.characters[2].offset:panel.characters[2].offset+56]);struct.pack_into('<I',raw,16,tex<<16);struct.pack_into('<4fI',raw,32,0,0,width,height,ident);char(raw)
        if vertices is None:vertices=((0,height),(0,0),(width,0),(width,0),(width,height),(0,height))
        geo=bytearray(panel.big.entries['3'].data[:96]);geo.extend(b''.join(struct.pack('<8f',x,y,0,0,0,0,0,0) for x,y in vertices))
        for offset,value in ((0,len(geo)),(16,len(geo)-16),(32,len(geo)-32),(52,tex)):struct.pack_into('<I',geo,offset,value)
        struct.pack_into('<6f',geo,64,1,0,0,1,0,0);additions[str(ident+1)]=bytes(geo);return ident
    header=bytearray(panel.big.entries['7'].data[:128]);struct.pack_into('<III',header,12,4,4,16);struct.pack_into('<I',header,28,1)
    tex_id=texture(bytes(header)+bytes((255,255,0,0,0,0,0,0))+struct.pack('<HHI',65535,65535,0));shape_id=shape(tex_id,1,1)
    # Preserve each DDS byte-for-byte. All squad portraits are bundled so an
    # unsaved change of XI can select another player without a file-path lookup.
    ui=portable.GAME/'data/ui/imgAssets';head_ids={0}
    for side in ('user','opponent'):head_ids.update(payload[side].get('portrait_ids',[]));head_ids.update(p['id'] for p in payload[side]['players'])
    def native_file(paths):
        for relative in paths:
            try:return portable.materialize('data/ui/imgAssets/'+relative)
            except FileNotFoundError:continue
        return None
    fallback=native_file(('heads/notfound.dds','heads/p0.dds'))
    if fallback is None:
        fallback=HERE/'runtime/empty_head.dds';fallback.parent.mkdir(parents=True,exist_ok=True)
        Image.new('RGBA',(128,128),(0,0,0,0)).save(fallback,format='DDS',pixel_format='DXT5')
        raw=bytearray(fallback.read_bytes());struct.pack_into('<I',raw,20,len(raw)-128);struct.pack_into('<I',raw,88,0);fallback.write_bytes(raw)
    content_symbols={}
    def embedded(symbol,path):
        dds=path.read_bytes();assert dds[:4]==b'DDS ',path
        key=bytes(dds)
        if key not in content_symbols:
            height,width=struct.unpack_from('<II',dds,12);tex=texture(dds);image_shape=shape(tex,width,height)
            clip=sprite([place(image_shape,1,0,0)])
            content_symbols[key]=(clip,tex+1,width,height)
        clip,entry,width,height=content_symbols[key];art_exports.append((symbol,clip));art_symbols[symbol]=clip;image_resources[symbol]={'entry':entry,'width':width,'height':height,'source':str(path)}
    for pid in sorted(head_ids):
        path=native_file((f'heads/p{pid}.dds',)) if pid else None
        embedded('S16Head_'+str(pid),path or fallback)
    crest_ids={payload[s]['team_id'] for s in ('user','opponent')}
    crest_ids.update(game['opponent_id'] for s in ('user','opponent') for game in payload[s].get('recent',[]))
    for team in sorted(crest_ids):
        path=native_file((f'crest/light/l{team}.dds',f'crest/dark/l{team}.dds','crest/light/notfound.dds')) or fallback
        embedded('S16Crest_'+str(team),path)
    from preview_art import competition_art
    competition_ids={game.get('competition_id',0) for s in ('user','opponent') for game in payload[s].get('recent',[])}
    for ident in sorted(competition_ids):
        path=competition_art(ui,ident,HERE/'runtime/art_cache')
        if path is not None:embedded('S16Competition_'+str(ident),path)
    # Native triangle strips produce smooth continuous centre/penalty arcs.
    def ring(start=0,end=2*math.pi):
        vertices=[]
        for i in range(72):
            a=start+(end-start)*i/72;b_=start+(end-start)*(i+1)/72
            outer=lambda t:(.5+.5*math.cos(t),.5+.5*math.sin(t))
            inner=lambda t:(.5+.482*math.cos(t),.5+.482*math.sin(t))
            vertices.extend((outer(a),inner(a),outer(b_),outer(b_),inner(a),inner(b_)))
        return shape(tex_id,1,1,vertices)
    def round_art(kind):
        im=Image.new('RGBA',(256,256),(255,255,255,0));draw=ImageDraw.Draw(im)
        if kind=='dot':draw.ellipse((5,5,250,250),fill=(255,255,255,255))
        elif kind in ('left','right'):draw.polygon(((30,128),(226,12),(226,244)) if kind=='left' else ((226,128),(30,12),(30,244)),fill='white')
        else:draw.ellipse((4,4,252,252),outline=(255,255,255,255),width=5)
        if kind=='top':draw.rectangle((0,0,255,126),fill=(255,255,255,0))
        if kind=='bottom':draw.rectangle((0,129,255,255),fill=(255,255,255,0))
        f=io.BytesIO();im.save(f,format='DDS',pixel_format='DXT5');dds=bytearray(f.getvalue());struct.pack_into('<I',dds,20,len(dds)-128);struct.pack_into('<I',dds,88,0)
        tex=texture(bytes(dds));cid=shape(tex,1,1);geo=bytearray(additions[str(cid+1)]);struct.pack_into('<6f',geo,64,256,0,0,256,0,0);additions[str(cid+1)]=bytes(geo);return cid
    circle=round_art('circle');top_arc=round_art('top');bottom_arc=round_art('bottom');dot_shape=round_art('dot')
    pc=[];depth=0
    def rect(x,y,w,h,color):
        nonlocal depth;depth+=1;pc.append(place(shape_id,depth,x,y,w,h,color=color))
    rect(0,0,PANEL_W,PANEL_H,0xffd4d7cf);rect(0,0,PANEL_W,80,payload['user'].get('header_color',0xff163e62))
    for i in range(10):rect(FIELD_X,FIELD_Y+i*76,FIELD_W,76,0xff2a6127 if i%2 else 0xff2d672a)
    # This field has the reference's portrait aspect, 640 / 760 = 0.8421.
    line=0xff6d8f61
    for r in ((12,94,640,3),(12,851,640,3),(12,94,3,760),(649,94,3,760),(12,473,640,3),
              (172,94,3,134),(489,94,3,134),(172,225,320,3),(172,720,3,134),(489,720,3,134),(172,720,320,3),
              (260,94,3,45),(401,94,3,45),(260,136,144,3),(260,809,3,45),(401,809,3,45),(260,809,144,3)):
        rect(*r,line)
    for cid,x,y,w,h in ((circle,246,409,172,130),(top_arc,276,182,112,90),(bottom_arc,276,676,112,90)):
        depth+=1;pc.append(place(cid,depth,x,y,w,h,color=line))
    rect(330,472,4,4,line);rect(330,191,4,4,line);rect(330,754,4,4,line)
    empty=sprite([])
    def native_art(symbol,desired,label):
        if symbol not in image_resources:return None
        resource=image_resources[symbol]
        return sprite([place(art_symbols[symbol],1,0,0,desired/resource['width'],desired/resource['height'],label=label)])
    def short_name(name):
        name=name.upper()
        if len(name)>10:
            words=name.split()
            if len(words)>1:name=name[0]+'. '+words[-1]
            if len(name)>11:name=words[-1]
            name=name[:11]
        return name
    def native_pitch(team):
        controls=pc.copy();controls[0]=place(shape_id,1,0,0,0,0,color=0x00ffffff);controls[1]=place(shape_id,2,0,0,PANEL_W,80,color=team.get('header_color',0xff163e62))
        ink=0xff000000|team.get('header_ink',0xffffff)
        crest_symbol=native_art('S16Crest_'+str(team['team_id']),56,'crest')
        controls.extend([place(crest_symbol,200,14,10,label='crest'),text(201,84,8,560,42,31,'teamName',ink,value=team['name']),text(202,84,50,560,26,20,'caption',ink,value='PROVÁVEL ESCALAÇÃO' if team['probable'] else 'SEU TIME TITULAR'),text(203,20,803,210,49,41,'formation',0xffffffff,font=4,value=team['formation'])])
        bands=[0.0]
        for p in team['players'][1:]:
            if all(abs(p['y']-b)>=.09 for b in bands[1:]):bands.append(p['y'])
        step=590/max(1,len(bands)-1);head=max(48,min(HEAD_MAX,step-56))
        for i,p in enumerate(team['players']):
            rank=0 if p['position']==0 else 1+sum(b<p['y']-.09 for b in bands[1:])
            face=native_art('S16Head_'+str(p['id']),head,'portrait')
            pos=p['position'];color=0xffe4c62b if pos==0 else 0xff24b8e4 if pos<9 else 0xff7bdc41 if pos<20 else 0xffe4427c
            parts=[place(face,1,-head/2,0,label='face'),place(shape_id,2,-56,head,112,26,label='ratingBG',color=0xf220272c),text(3,-60,head+28,120,27,20,'name',0xffffffff,align=2,value=short_name(p['name'])),place(shape_id,4,-56,head,0,26,label='positionBG',color=0xff20272c),text(5,-53,head,58,28,23,'position',color,value=POSITIONS[pos]),text(6,18,head,37,29,26,'rating',0xffffffff,align=1,value=str(p['overall']))]
            controls.append(place(sprite(parts),220+i,82+max(0,min(1,p['x']))*500,700-rank*step,label='p'+str(i)))
        return sprite(controls)
    pitch_symbol=native_pitch(payload['user']);opponent_symbol=native_pitch(payload['opponent'])
    controls=[place(shape_id,0,carousel.CARD_X,carousel.CARD_Y,carousel.CARD_W,carousel.CARD_H,label='outerCard',color=0xffedf0ed),place(pitch_symbol,1,carousel.PITCH_X[0],carousel.PITCH_Y,carousel.PITCH_SCALE,carousel.PITCH_SCALE,label='userPitch'),place(opponent_symbol,2,carousel.PITCH_X[1],carousel.PITCH_Y,carousel.PITCH_SCALE,carousel.PITCH_SCALE,label='opponentPitch'),text(3,226,48,1468,55,38,'screenTitle',0xffffffff),text(4,226,106,1468,30,23,'matchInfo',0xffffffff),text(5,226,860,1195,25,17,'status',0xff334b56)]
    controls.extend(carousel.graphics(payload,place,text,sprite,shape_id,lambda vertices:shape(tex_id,1,1,vertices),dot_shape,(round_art('left'),round_art('right')),native_art))
    ctl=append(struct.pack('<'+'Q'*len(controls),*controls));frames=append(struct.pack('<I4xQ',len(controls),ctl));struct.pack_into('<I4xQ',data,apt.characters[9].offset+32,1,frames)
    newtable=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(characters),*characters));struct.pack_into('<I4xQ',data,root+56,count+len(characters),newtable)
    er=Reader(data,root+96,8);n=er.i();export_table=er.ptr();exports=[]
    for i in range(n):
        at=export_table+i*16;old=Reader(data,at,8).text();cid=struct.unpack_from('<I',data,at+8)[0];exports.append((old.replace('game.screens.career.CareerType',FULL),cid))
    exports.append(('Server16LineupPitch',pitch_symbol));exports.append(('Server16OpponentLineupPitch',opponent_symbol));exports.extend(art_exports);new_exports=append(b''.join(struct.pack('<QI4x',name(n),cid) for n,cid in exports));struct.pack_into('<I4xQ',data,root+96,len(exports),new_exports)
    acts=Actions(apt).read_all();dictionaries=[bytes(data[block[0].offset:block[0].end]) for block in acts.cache.values()];start,registration=script(data,dictionaries,payload,head_ids)
    for tag,target in [(apt.root_frames[0][1],start),(apt.root_frames[0][2],registration)]:
        signature=struct.pack('<Q',tag[-1]);matches=[i for i in range(0,len(apt.entry.original)-7,8) if apt.entry.original[i:i+8]==signature];assert len(matches)==1;struct.pack_into('<Q',data,matches[0],target)
    output=HERE/'package/data/ui/game/screens/career/server16/matchpreview.big';output.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,output,additions)
    parsed=AptFile(BigFile(output));decoded=Actions(parsed).read_all();assert not decoded.errors,decoded.errors;assert parsed.exports['Server16LineupPitch']==pitch_symbol
    (HERE/'image_resources.json').write_text(json.dumps(image_resources,ensure_ascii=False,indent=2),encoding='utf8')
    print('Built custom LineupPitch component and two-pitch native screen:',output.stat().st_size,'bytes')
    return output

if __name__=='__main__':build()
