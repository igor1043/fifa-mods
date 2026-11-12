"""Extend the installed native career header; preserve its art and lifecycle."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,struct,sys

SOURCE=Path(__file__).resolve().parents[2]
CLASS=('game','components','CareerComponents','CareerHubWidget')
PROTO=CLASS+('prototype',)
MARKER='Server16HeaderMetricsInstalledV8'
PREVIOUS_MARKER='Server16HeaderMetricsInstalledV4'
PREVIOUS_GEOMETRY='Server16HeaderMetricsInstalledV5'
OLD='Server16MetricsOriginal'
HEIGHT=108
ROW_WIDTH=500
METRICS_Y=72
BOARD_BAR_WIDTH=198
RIGHT_WIDTH=650
# Same safe edge/origin as the installed native career branding. This is
# FIFA's 1920-unit UI canvas, not the monitor's pixel width (incl. ultrawide).
RIGHT_EDGE=1811-109
RIGHT_X=RIGHT_EDGE-RIGHT_WIDTH
RIGHT_PARTS=('mcCareerRightStart','mcCareerRightMiddle','mcCareerRightEnd')
RIGHT_ICONS=('mcCareerDateIcon','mcCareerMarketIcon','mcCareerCashIcon','mcCareerRightDivider1','mcCareerRightDivider2')
# All content stays inside the rectangular area after the slanted left end.
# Title groups center their icon + actual text width; values center below.
RIGHT_COLUMNS=(('date',88,148,82),('market',236,208,148),('cash',444,182,83))
INK=0x344D5A
MUTED=0x657D87
GOLD=0xB9A274

def dependencies(studio):
    env=SOURCE/'club_environment'
    os.environ.setdefault('SERVER16_GAME_ROOT',str(SOURCE.parents[1]))
    for path in reversed((studio,env,env/'vendor',env/'bank',env/'preview',SOURCE)):
        if str(path) not in sys.path:sys.path.insert(0,str(path))
    global b,Code,branding
    import build_screen as b
    from build_preview import Code as PreviewCode
    class NativeHeaderCode(PreviewCode):
        def expr(self,value):
            if isinstance(value,tuple) and value and value[0]=='header-number':
                self.expr(value[1]);self.op(74)
            else:super().expr(value)
    Code=NativeHeaderCode
    spec=importlib.util.spec_from_file_location('career_header_branding',SOURCE/'tools/career_branding/build.py')
    branding=importlib.util.module_from_spec(spec);spec.loader.exec_module(branding)

def left_clip(apt):
    """Wrap the original left end in a named sprite; no texture changes."""
    from formats import Placement
    component=next(c for c in apt.characters.values() if c.type==5 and any(isinstance(p,Placement) and p.name=='txtTeam' for f in c.frames for p in f))
    left=next(p for p in component.frames[0] if isinstance(p,Placement) and not p.name and apt.characters[p.character].type==1)
    middle=next(apt.characters[p.character] for p in component.frames[0] if isinstance(p,Placement) and p.name=='mcMiddle')
    data=apt.data
    def append(blob):data.extend(bytes(-len(data)%8));at=len(data);data.extend(blob);return at
    inner=bytearray(data[left.offset:left.offset+80]);struct.pack_into('<ii',inner,8,6,1);struct.pack_into('<6f',inner,20,1,0,0,1,0,0);struct.pack_into('<Q',inner,56,0)
    place=append(inner);controls=append(struct.pack('<Q',place));frames=append(struct.pack('<I4xQ',1,controls))
    sprite=bytearray(data[middle.offset:middle.offset+56]);struct.pack_into('<I4xQ',sprite,32,1,frames);symbol=append(sprite)
    cid=apt.character_count;table=append(bytes(data[apt.character_table:apt.character_table+cid*8])+struct.pack('<Q',symbol))
    struct.pack_into('<I',data,apt.character_count_offset,cid+1);struct.pack_into('<Q',data,apt.character_table_field,table)
    name=append(b'mcHeaderLeft\0');struct.pack_into('<I',data,left.offset+8,left.flags|32);struct.pack_into('<I',data,left.offset+16,cid);struct.pack_into('<Q',data,left.offset+56,name)

def number(value):
    # Native ActionToNumber (0x4a). FIFA's APT runtime need not expose the
    # global Number constructor as a callable method. That missing method
    # produced undefined%, zero money and an empty transfer-window label.
    return ('header-number',value)

def native_icons(apt,upgrade=False):
    """Use native textured triangle geometry, not unsupported MovieClip drawing."""
    from formats import Placement
    data=apt.data
    component=next(c for c in apt.characters.values() if c.type==5 and any(isinstance(p,Placement) and p.name=='txtTeam' for f in c.frames for p in f))
    template=next(p for p in component.frames[0] if isinstance(p,Placement))
    symbols=[];additions={}
    count=struct.unpack_from('<I',data,apt.character_count_offset)[0]
    table=struct.unpack_from('<Q',data,apt.character_table_field)[0]
    def append(blob):
        data.extend(bytes(-len(data)%8));offset=len(data);data.extend(blob);return offset
    def symbol(blob):
        cid=count+len(symbols);symbols.append(append(blob));return cid
    white=bytearray(apt.big.entries['7'].data[:128])
    struct.pack_into('<III',white,12,4,4,16);struct.pack_into('<I',white,28,1)
    texture=count
    raw=bytearray(data[apt.characters[1].offset:apt.characters[1].offset+40])
    struct.pack_into('<I',raw,32,texture);symbol(raw)
    additions[str(texture+1)]=bytes(white)+bytes((255,255,0,0,0,0,0,0))+struct.pack('<HHI',65535,65535,0)
    def icon_clip(shape_id):
        raw=bytearray(data[template.offset:template.offset+80])
        struct.pack_into('<iii6f',raw,8,14,1,shape_id,1,0,0,1,0,0)
        struct.pack_into('<IIQ',raw,44,0xffffffff,0,0)
        struct.pack_into('<Q',raw,56,0)
        placement=append(raw);controls=append(struct.pack('<Q',placement))
        frames=append(struct.pack('<I4xQ',1,controls))
        middle=next(apt.characters[p.character] for p in component.frames[0] if isinstance(p,Placement) and p.name=='mcMiddle')
        raw=bytearray(data[middle.offset:middle.offset+56])
        struct.pack_into('<I4xQ',raw,32,1,frames)
        return symbol(raw)
    def shape(vertices,width,height):
        cid=count+len(symbols)
        raw=bytearray(data[apt.characters[2].offset:apt.characters[2].offset+56])
        struct.pack_into('<I',raw,16,texture<<16)
        struct.pack_into('<4fI',raw,32,0,0,width,height,cid);symbol(raw)
        geo=bytearray(apt.big.entries['3'].data[:96])
        geo.extend(b''.join(struct.pack('<8f',x,y,0,0,0,0,0,0) for x,y in vertices))
        for offset,value in ((0,len(geo)),(16,len(geo)-16),(32,len(geo)-32),(52,texture)):
            struct.pack_into('<I',geo,offset,value)
        struct.pack_into('<6f',geo,64,1,0,0,1,0,0)
        # FIFA uses this primitive count for DrawPrimitive. The generic offline
        # decoder only supports two-triangle quads, so it cannot validate it.
        struct.pack_into('<I',geo,88,len(vertices)//3)
        additions[str(cid+1)]=bytes(geo);return icon_clip(cid)
    chart=[]
    for x,top in ((0,14),(6,8),(12,2)):
        chart.extend(((x,22),(x,top),(x+4,top),(x+4,top),(x+4,22),(x,22)))
    chart_id=shape(chart,16,24)
    star=[(10+math.cos(-math.pi/2+i*math.pi/5)*(10 if i%2==0 else 4.5),12+math.sin(-math.pi/2+i*math.pi/5)*(10 if i%2==0 else 4.5)) for i in range(10)]
    triangles=[]
    for i in range(len(star)):triangles.extend(((10,12),star[i],star[(i+1)%len(star)]))
    star_id=shape(triangles,20,24)
    divider_id=shape(((0,22),(0,2),(1,2),(1,2),(1,22),(0,22)),1,24)
    # A small board/people pictogram and native quads keep the progress bar
    # on FIFA's textured geometry path; MovieClip drawing is unsupported.
    people=[]
    for cx,cy,r in ((8,6,4),(18,8,3)):
        for i in range(10):
            a0=i*math.tau/10;a1=(i+1)*math.tau/10
            people.extend(((cx,cy),(cx+math.cos(a0)*r,cy+math.sin(a0)*r),(cx+math.cos(a1)*r,cy+math.sin(a1)*r)))
    for x,y,w,h in ((2,12,12,10),(15,14,7,8)):
        people.extend(((x,y),(x+w,y),(x+w,y+h),(x,y),(x+w,y+h),(x,y+h)))
    board_id=shape(people,22,24)
    bar_id=shape(((0,0),(BOARD_BAR_WIDTH,0),(BOARD_BAR_WIDTH,3),(0,0),(BOARD_BAR_WIDTH,3),(0,3)),BOARD_BAR_WIDTH,3)
    def quads(rectangles):
        vertices=[]
        for x,y,w,h in rectangles:vertices.extend(((x,y),(x+w,y),(x+w,y+h),(x,y),(x+w,y+h),(x,y+h)))
        return shape(vertices,24,24)
    calendar_id=quads(((1,4,22,2),(1,6,2,17),(21,6,2,17),(1,21,22,2),(6,0,2,7),(16,0,2,7),(3,9,18,2),(6,14,3,3),(12,14,3,3)))
    arrows_id=shape(((1,5),(17,5),(17,11),(1,5),(17,11),(1,11),(17,2),(23,8),(17,14),
                     (7,16),(23,16),(23,21),(7,16),(23,21),(7,21),(7,13),(1,19),(7,24)),24,24)
    wallet_id=quads(((1,5,22,2),(1,7,2,16),(21,7,2,16),(1,21,22,2),(5,1,15,2),(3,3,2,3),(14,11,10,7)))
    controls=[]
    definitions=[] if upgrade else [(12010,chart_id,'mcHeaderEfficiencyIcon',0,GOLD),(12011,star_id,'mcHeaderPrestigeIcon',191,GOLD),(12012,divider_id,'mcHeaderMetricDivider',178,0xD3DDE1)]
    definitions.extend(((12013,divider_id,'mcHeaderBoardDivider',347,0xD3DDE1),(12014,board_id,'mcHeaderBoardIcon',360,GOLD),(12015,bar_id,'mcHeaderBoardTrack',382,0xD3DDE1),(12016,bar_id,'mcHeaderBoardFill',382,GOLD)))
    definitions.extend(((12030,calendar_id,RIGHT_ICONS[0],RIGHT_X+26,GOLD),(12031,arrows_id,RIGHT_ICONS[1],RIGHT_X+204,GOLD),(12032,wallet_id,RIGHT_ICONS[2],RIGHT_X+426,GOLD),(12033,divider_id,RIGHT_ICONS[3],RIGHT_X+186,0xD3DDE1),(12034,divider_id,RIGHT_ICONS[4],RIGHT_X+408,0xD3DDE1)))
    for depth,cid,label,x,color in definitions:
        raw=bytearray(data[template.offset:template.offset+80])
        struct.pack_into('<iii6f',raw,8,46,depth,cid,1,0,0,1,x,METRICS_Y)
        struct.pack_into('<II',raw,44,0xff000000|color,0)
        struct.pack_into('<Q',raw,56,append(label.encode('ascii')+b'\0'));controls.append(append(raw))
    # Reuse the stock card skin with reversed ends, rather than introducing
    # a separate art style or expanding the native canvas bounds.
    placements={p.name:p for p in component.frames[0] if isinstance(p,Placement)}
    for depth,original,label,x,mirror in ((12001,'mcRight',RIGHT_PARTS[0],RIGHT_X+88,-1),(12002,'mcMiddle',RIGHT_PARTS[1],RIGHT_X+88,1),(12003,'mcHeaderLeft',RIGHT_PARTS[2],RIGHT_EDGE,-1)):
        source=placements[original];raw=bytearray(data[source.offset:source.offset+80])
        struct.pack_into('<iii6f',raw,8,source.flags|32,depth,source.character,mirror,0,0,1,x,0)
        struct.pack_into('<Q',raw,56,append(label.encode('ascii')+b'\0'));controls.append(append(raw))
    original_frames=struct.unpack_from('<Q',data,component.offset+40)[0]
    original_count,original_controls=struct.unpack_from('<I4xQ',data,original_frames)
    controls_at=append(bytes(data[original_controls:original_controls+original_count*8])+struct.pack('<'+'Q'*len(controls),*controls))
    frames=append(struct.pack('<I4xQ',original_count+len(controls),controls_at))
    struct.pack_into('<Q',data,component.offset+40,frames)
    table_at=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(symbols),*symbols))
    struct.pack_into('<I',data,apt.character_count_offset,count+len(symbols))
    struct.pack_into('<Q',data,apt.character_table_field,table_at)
    return additions

def correct_legacy_provider_calls(data,block,delta):
    """Stock UIFUtility expects (subscriber, providerID), including unregister."""
    corrected=0
    def visit(code):
        nonlocal corrected
        for index,instruction in enumerate(code[:-1]):
            following=code[index+1]
            if instruction.op==181 and instruction.value==2 and following.op==181 and following.value==3:
                if any(item.value in ('RegisterDataProvider','UnregisterDataProvider') for item in code[index+2:index+18]):
                    data[instruction.offset+delta:instruction.end+delta]=bytes((89,23))
                    data[following.offset+delta+1]=2;corrected+=1
            if instruction.body:visit(instruction.body)
    visit(block)
    if corrected!=2:raise ValueError('Unexpected legacy header subscription layout')

def write_container(big,path,additions):
    from formats import chunk_wrap
    pending=dict(additions);entries=[]
    for name,entry in big.entries.items():
        if name in ('sg1','sg2'):
            for key,blob in list(pending.items()):
                if blob.startswith(b'DDS ')==(name=='sg2'):
                    entries.append((key,blob));del pending[key]
        blob=bytes(entry.data) if entry.data!=entry.original else big.original[entry.offset:entry.offset+entry.length]
        entries.append((name,blob))
    if pending:raise ValueError('Unplaced native icon resources')
    header=16+sum(9+len(name.encode('ascii')) for name,_ in entries)
    offset=(header+63)//64*64;directory=bytearray();payload=bytearray(offset-header)
    for name,blob in entries:
        padding=-offset%64;payload.extend(bytes(padding));offset+=padding
        directory.extend(struct.pack('>II',offset,len(blob))+name.encode('ascii')+b'\0')
        payload.extend(blob);offset+=len(blob)
    content=b'BIGF'+struct.pack('<I',offset)+struct.pack('>II',len(entries),header)+directory+payload
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(chunk_wrap(content,big.wrapper) if big.wrapper else content)

def script(apt,actions,upgrade=False,currency_symbols=('', '', '')):
    R=b.reg;P=b.prop;T=b.this;PATH=b.path;CALL=b.call;EQ=b.equal
    proto=PATH(*PROTO);utility=PATH('game','uif','UIFUtility');provider=P(PATH('game','uif','UIFDataProviderList'),'CM_STATISTICS_DP')
    start,block=next((at,code) for at,code in actions.cache.items() if code[0].op==136 and any(i.value=='CareerHubWidget' for i in code))
    data=apt.data;a=Code(data);a.align();new_start=len(data);data.extend(apt.entry.original[start:block[0].end])
    # The installed V4 already owns the stock wrappers. Run its guarded
    # initializer first, then replace the presentation methods without ever
    # capturing a metrics wrapper as the original lifecycle method.
    if upgrade:branding.copy_initializer(a,apt,block)
    for n in range(1,len(PROTO)+1):a.expr(PATH(*PROTO[:n]));a.op(18);a.branch('metrics_initialize')
    a.expr(P(proto,MARKER));a.branch('metrics_done')
    a.label('metrics_initialize')
    while len(data)%8:a.op(89);a.op(23)
    if not upgrade:
        copy_start=len(data);branding.copy_initializer(a,apt,block)
        correct_legacy_provider_calls(data,block,copy_start-block[0].end)
        for name in ('SetData','Publish','Shutdown'):a.set(proto,OLD+name,P(proto,name))
    b.CLASS=CLASS;b.FULL='.'.join(CLASS)
    def ensure(a):
        a.when(T('__careerHeaderMetrics'),lambda a:a.ret())
        a.set(R(1),'__careerHeaderMetrics',CALL(R(1),'createEmptyMovieClip','__careerHeaderMetrics',12020))
        clip=T('__careerHeaderMetrics')
        for name,x,w,size,ink in (('effLabel',22,106,14,MUTED),('effValue',128,44,18,INK),('boardLabel',215,76,13,MUTED),('boardValue',294,44,17,INK),('prestigeLabel',381,58,14,MUTED),('prestigeValue',442,54,18,INK)):
            a.do(clip,'createTextField',name,12021+x,x,4 if name.endswith('Label') else 0,w,25)
            text=P(clip,name);a.set(text,'selectable',False);a.set(text,'textColor',ink)
            a.set(text,'embedFonts',True)
            fmt=('newmethod',b.GLOBAL,'TextFormat',('EA HelveticaNeue Con Bold',size,ink))
            a.do(text,'setTextFormat',fmt);a.do(text,'setNewTextFormat',fmt)
        a.set(P(clip,'effLabel'),'text','Aproveitamento')
        a.set(P(clip,'prestigeLabel'),'text','Prestígio')
        a.set(P(clip,'boardLabel'),'text','Av. Diretoria')
        a.set(R(1),'__careerRightMetrics',CALL(R(1),'createEmptyMovieClip','__careerRightMetrics',12040))
        right=T('__careerRightMetrics')
        for index,(key,x,w,_) in enumerate(RIGHT_COLUMNS):
            for suffix,size,y,ink in (('Label',12,28,MUTED),('Value',17 if key=='market' else 18,56,INK)):
                name=key+suffix;value=suffix=='Value'
                a.do(right,'createTextField',name,12100+index*2+int(value),x+8,y,w-16,28 if value else 22)
                text=P(right,name);a.set(text,'selectable',False);a.set(text,'textColor',ink);a.set(text,'embedFonts',True)
                a.set(R(1),'__careerRightFormat',('newmethod',b.GLOBAL,'TextFormat',('EA HelveticaNeue Con Bold',size,ink)))
                fmt=T('__careerRightFormat');a.set(fmt,'align','center' if value else 'left')
                a.do(text,'setTextFormat',fmt);a.do(text,'setNewTextFormat',fmt)
        for name,label in (('dateLabel','Data da carreira'),('marketLabel','Mercado de transferências'),('cashLabel','Caixa disponível')):a.set(P(right,name),'text',label)
    a.function('Server16EnsureHeaderMetrics',0,ensure)
    def render(a):
        a.when(T('m_objData'),lambda a:None,lambda a:a.ret())
        tournament=EQ(number(P(T('m_objData'),'IS_TOURNAMENTMODE')),1)
        def standard(a):
            for part in ('mcHeaderLeft','mcMiddle','mcRight'):a.set(T(part),'_height',79)
            a.set(T('mcCrest'),'_y',5)
            a.set(T('txtTeam'),'_y',('bin',13,('bin',11,79,P(T('txtTeam'),'_height')),2))
            for icon in ('mcHeaderEfficiencyIcon','mcHeaderPrestigeIcon','mcHeaderMetricDivider','mcHeaderBoardIcon','mcHeaderBoardDivider','mcHeaderBoardTrack','mcHeaderBoardFill'):a.set(T(icon),'_visible',False)
            a.when(T('__careerHeaderMetrics'),lambda a:a.set(T('__careerHeaderMetrics'),'_visible',False))
            a.when(T('__careerRightMetrics'),lambda a:a.set(T('__careerRightMetrics'),'_visible',False))
            for name in RIGHT_PARTS+RIGHT_ICONS:a.set(T(name),'_visible',False)
            a.ret()
        a.when(tournament,standard)
        a.when(T('__careerCoachGraph'),lambda a:a.set(T('__careerCoachGraph'),'_visible',False))
        a.do(R(1),'Server16EnsureHeaderMetrics');clip=T('__careerHeaderMetrics')
        right=T('__careerRightMetrics');a.set(right,'_x',RIGHT_X);a.set(right,'_y',0);a.set(right,'_visible',True)
        for name in RIGHT_PARTS:a.set(T(name),'_visible',True);a.set(T(name),'_height',HEIGHT)
        a.set(T(RIGHT_PARTS[1]),'_width',RIGHT_WIDTH-88-32)
        for name,offset in zip(RIGHT_ICONS,(114,253,480.5,236,444)):
            a.set(T(name),'_visible',True);a.set(T(name),'_x',RIGHT_X+offset);a.set(T(name),'_y',30 if name in RIGHT_ICONS[:3] else 28)
        for name in RIGHT_ICONS[:3]:a.set(T(name),'_width',18);a.set(T(name),'_height',18)
        for name in RIGHT_ICONS[3:]:a.set(T(name),'_height',50)
        for (key,x,w,fallback),icon in zip(RIGHT_COLUMNS,RIGHT_ICONS[:3]):
            label=P(right,key+'Label');measured=number(P(label,'textWidth'))
            a.set(R(1),'__careerRightLabelWidth',fallback)
            valid_width=('bin',16,EQ(measured,measured),('bin',16,('bin',15,0,measured),('not',('bin',15,w-30,measured))))
            a.when(valid_width,lambda a:a.set(R(1),'__careerRightLabelWidth',measured))
            text_width=T('__careerRightLabelWidth')
            group_x=('bin',71,x,('bin',13,('bin',11,w,('bin',71,26,text_width)),2))
            a.set(T(icon),'_x',('bin',71,RIGHT_X,group_x))
            a.set(label,'_x',('bin',71,group_x,26));a.set(label,'_width',('bin',71,text_width,4))
        for name in ('dateValue','marketValue','cashValue'):a.set(P(right,name),'text','—')
        a.set(T(branding.LOGO),'_visible',False)
        a.set(clip,'_visible',True);a.set(clip,'_x',P(T('txtTeam'),'_x'));a.set(clip,'_y',METRICS_Y)
        a.set(T('txtTeam'),'_y',5);a.set(T('txtName'),'_y',37)
        for part in ('mcHeaderLeft','mcMiddle','mcRight'):a.set(T(part),'_height',HEIGHT)
        # ImageLoader has zero height before its asynchronous crest is ready.
        # Offset from the stock 79px header, whose crest origin is already correct.
        a.set(T('mcCrest'),'_y',5+(HEIGHT-79)/2)
        for icon,offset in (('mcHeaderEfficiencyIcon',0),('mcHeaderPrestigeIcon',356),('mcHeaderMetricDivider',178),('mcHeaderBoardDivider',344),('mcHeaderBoardIcon',191)):
            a.set(T(icon),'_visible',True);a.set(T(icon),'_x',('bin',71,P(clip,'_x'),offset));a.set(T(icon),'_y',METRICS_Y)
        for name in ('mcHeaderBoardTrack','mcHeaderBoardFill'):a.set(T(name),'_visible',False)
        width=('bin',71,('bin',11,P(clip,'_x'),P(T('mcMiddle'),'_x')),ROW_WIDTH+12)
        # Stock text boxes can span the whole header even for a short name.
        # Their reserved width must not stretch the card past its own content.
        a.set(T('mcMiddle'),'_width',width)
        a.set(T('mcRight'),'_x',('bin',71,P(T('mcMiddle'),'_x'),P(T('mcMiddle'),'_width')))
        for key in ('effValue','prestigeValue','boardValue'):a.set(P(clip,key),'text','—')
        valid=('bin',16,T('__careerHeaderData'),EQ(number(P(T('__careerHeaderData'),'CAREER_HEADER_CLUB_ID')),number(P(T('m_objData'),'ASSET_ID'))))
        def values(a):
            for key,field in (('effValue','CAREER_HEADER_EFFICIENCY'),('prestigeValue','CAREER_HEADER_PRESTIGE')):
                a.when(P(T('__careerHeaderData'),field),lambda a,key=key,field=field:a.set(P(clip,key),'text',P(T('__careerHeaderData'),field)))
            rating=number(P(T('__careerHeaderData'),'CAREER_HEADER_BOARD_CONFIDENCE'))
            rating_valid=('bin',16,EQ(rating,rating),('bin',16,('not',('bin',15,rating,0)),('not',('bin',15,100,rating))))
            def confidence(a):
                a.set(P(clip,'boardValue'),'text',('bin',71,rating,'%'))
            a.when(rating_valid,confidence)
            a.when(P(T('__careerHeaderData'),'CAREER_HEADER_DATE'),lambda a:a.set(P(right,'dateValue'),'text',P(T('__careerHeaderData'),'CAREER_HEADER_DATE')))
            days=number(P(T('__careerHeaderData'),'CAREER_HEADER_MARKET_DAYS'))
            def market(a):
                a.when(EQ(days,0),lambda a:a.set(P(right,'marketValue'),'text','Mercado aberto'),
                    lambda a:a.set(P(right,'marketValue'),'text',('bin',71,('bin',71,'Abre em ',days),' dias')))
                a.when(EQ(days,1),lambda a:a.set(P(right,'marketValue'),'text','Abre amanhã'))
            a.when(('bin',16,EQ(days,days),('bin',16,('not',('bin',15,days,0)),('bin',15,days,1500))),market)
            cash=number(P(T('__careerHeaderData'),'CAREER_HEADER_CASH'))
            currency=number(P(T('__careerHeaderData'),'CAREER_HEADER_CURRENCY'))
            money_valid=('bin',16,EQ(cash,cash),('bin',16,EQ(currency,currency),('bin',16,('not',('bin',15,cash,0)),('bin',16,('not',('bin',15,currency,0)),('not',('bin',15,2,currency))))))
            def money(a):
                prefix=('index',('array',tuple(symbol+' ' if symbol else '' for symbol in currency_symbols)),currency)
                a.set(P(right,'cashValue'),'text',('bin',71,prefix,CALL(PATH('ION_Localization'),'LocalizeCurrencyWithType',False,cash,currency)))
            a.when(money_valid,money)
            def player(a):
                a.set(right,'_visible',False);a.set(T(branding.LOGO),'_visible',True)
                for name in RIGHT_PARTS+RIGHT_ICONS+('mcHeaderBoardIcon','mcHeaderBoardDivider','mcHeaderBoardTrack','mcHeaderBoardFill'):a.set(T(name),'_visible',False)
                for name in ('boardLabel','boardValue'):a.set(P(clip,name),'_visible',False)
            for name in ('boardLabel','boardValue'):a.set(P(clip,name),'_visible',True)
            a.when(EQ(number(P(T('__careerHeaderData'),'CAREER_HEADER_MANAGER')),0),player)
        a.when(valid,values)
    a.function('__careerDrawCoachGraph',0,render)
    def set_data(a):
        a.when(('not',EQ(T('__careerHeaderClub'),P(T('m_objData'),'ASSET_ID'))),lambda a:a.set(R(1),'__careerHeaderData',None))
        a.set(R(1),'__careerHeaderClub',P(T('m_objData'),'ASSET_ID'))
        a.do(R(1),OLD+'SetData')
        a.do(R(1),'__careerDrawCoachGraph')
        career=('not',EQ(number(P(T('m_objData'),'IS_TOURNAMENTMODE')),1))
        def register(a):
            a.when(T('__careerMetricsRegistered'),lambda a:a.ret())
            a.set(R(1),'__careerMetricsRegistered',True)
            a.do(utility,'RegisterDataProvider',R(1),provider)
        a.when(career,register)
    a.function('SetData',0,set_data)
    def publish(a):
        def metrics(a):
            # CM_STATISTICS_DP publishes ID/PARAM rows, like the native tiles.
            # Consume only the scoped header fields, keeping unrelated tile data local.
            a.set(R(1),'__careerHeaderData',('object',))
            for field in ('BOARD_CONFIDENCE','MARKET_DAYS','CASH','CURRENCY','MANAGER'):a.set(T('__careerHeaderData'),'CAREER_HEADER_'+field,-1)
            a.expr(P(R(2),'data'));a.store(4)
            loop,done=a.uid(),a.uid();a.label(loop)
            a.expr(('bin',103,P(R(4),'length'),0));a.op(18);a.branch(done)
            a.expr(('bin',11,P(R(4),'length'),1));a.store(5)
            a.expr(0);a.store(7)
            scan=a.uid();a.label(scan)
            a.expr(('bin',15,R(5),0));a.branch(done)
            a.expr(('index',R(4),R(5)));a.store(6)
            fields=(('CAREER_HEADER_CLUB_ID','CAREER_HEADER_CLUB_ID'),
                    ('COACH_EFFICIENCY','CAREER_HEADER_EFFICIENCY'),
                    ('CAREER_HEADER_PRESTIGE','CAREER_HEADER_PRESTIGE'),
                    ('CAREER_HEADER_BOARD_CONFIDENCE','CAREER_HEADER_BOARD_CONFIDENCE'),
                    *((('CAREER_HEADER_'+key,'CAREER_HEADER_'+key) for key in ('DATE','MARKET_DAYS','CASH','CURRENCY','MANAGER'))))
            for bit,(field,target) in enumerate(fields):
                def capture(a,target=target,mask=1<<bit):
                    a.set(T('__careerHeaderData'),target,P(R(6),'PARAM'))
                    a.expr(('bin',97,R(7),mask));a.store(7)
                a.when(EQ(P(R(6),'ID'),field),capture)
            a.expr(EQ(R(7),511));a.branch(done)
            a.expr(('bin',11,R(5),1));a.store(5);a.branch(scan,False);a.label(done)
            a.do(R(1),'__careerDrawCoachGraph');a.ret()
        a.when(EQ(R(3),provider),metrics)
        a.do(R(1),OLD+'Publish',R(2),R(3))
    a.function('Publish',2,publish)
    def shutdown(a):
        a.when(T('__careerMetricsRegistered'),lambda a:a.do(utility,'UnregisterDataProvider',R(1),provider))
        a.set(R(1),'__careerMetricsRegistered',False);a.set(R(1),'__careerHeaderData',None)
        a.do(R(1),OLD+'Shutdown')
    a.function('Shutdown',0,shutdown)
    a.set(proto,MARKER,True);a.label('metrics_done');a.op(0);a.finish()
    signature=struct.pack('<Q',start);refs=[at for at in range(0,len(apt.entry.original)-7,8) if apt.entry.original[at:at+8]==signature]
    if len(refs)!=1:raise ValueError('Ambiguous career header initializer')
    struct.pack_into('<Q',data,refs[0],new_start)

def build(source,output,studio):
    dependencies(studio)
    from formats import AptFile,BigFile
    from apt_actions import Actions
    source,output=Path(source),Path(output)
    big=BigFile(source);apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    if MARKER.encode() in apt.data:
        output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(source.read_bytes());return dict(path=str(output),idempotent=True)
    geometry_ready=PREVIOUS_GEOMETRY.encode() in apt.data
    upgrade=geometry_ready or PREVIOUS_MARKER.encode() in apt.data
    if not upgrade:left_clip(apt)
    additions={} if geometry_ready else native_icons(apt,upgrade)
    from career_currency import currency_symbol
    symbols=tuple(currency_symbol(i,game=source.parents[5]) for i in range(3))
    script(apt,actions,upgrade,symbols);write_container(big,output,additions)
    checked=BigFile(output);parsed=AptFile(checked);decoded=Actions(parsed).read_all()
    if decoded.errors:raise ValueError(decoded.errors)
    parsed.validate_layout()
    for key,entry in big.entries.items():
        if key!=apt.entry.name and bytes(checked.entries[key].data)!=entry.original:raise ValueError('Existing art changed: '+key)
    return dict(path=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),height=HEIGHT,images='unchanged',native_provider='CM_STATISTICS_DP',currency_symbols=symbols)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--studio',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.source,args.output,args.studio),ensure_ascii=False,indent=2))
