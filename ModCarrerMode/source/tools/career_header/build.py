"""Extend the installed native career header; preserve its art and lifecycle."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,math,os,struct,sys

SOURCE=Path(__file__).resolve().parents[2]
CLASS=('game','components','CareerComponents','CareerHubWidget')
PROTO=CLASS+('prototype',)
MARKER='Server16HeaderMetricsInstalledV4'
OLD='Server16MetricsOriginal'
HEIGHT=100
ROW_WIDTH=324
METRICS_Y=72
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
    from build_preview import Code
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

def native_icons(apt):
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
    controls=[]
    for depth,cid,label,x,color in ((12010,chart_id,'mcHeaderEfficiencyIcon',0,GOLD),(12011,star_id,'mcHeaderPrestigeIcon',191,GOLD),(12012,divider_id,'mcHeaderMetricDivider',178,0xD3DDE1)):
        raw=bytearray(data[template.offset:template.offset+80])
        struct.pack_into('<iii6f',raw,8,46,depth,cid,1,0,0,1,x,METRICS_Y)
        struct.pack_into('<II',raw,44,0xff000000|color,0)
        struct.pack_into('<Q',raw,56,append(label.encode('ascii')+b'\0'));controls.append(append(raw))
    original_frames=struct.unpack_from('<Q',data,component.offset+40)[0]
    original_count,original_controls=struct.unpack_from('<I4xQ',data,original_frames)
    controls_at=append(bytes(data[original_controls:original_controls+original_count*8])+struct.pack('<3Q',*controls))
    frames=append(struct.pack('<I4xQ',original_count+3,controls_at))
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

def script(apt,actions):
    R=b.reg;P=b.prop;T=b.this;PATH=b.path;CALL=b.call;EQ=b.equal
    proto=PATH(*PROTO);utility=PATH('game','uif','UIFUtility');provider=P(PATH('game','uif','UIFDataProviderList'),'CM_STATISTICS_DP')
    start,block=next((at,code) for at,code in actions.cache.items() if code[0].op==136 and any(i.value=='CareerHubWidget' for i in code))
    data=apt.data;a=Code(data);a.align();new_start=len(data);data.extend(apt.entry.original[start:block[0].end])
    for n in range(1,len(PROTO)+1):a.expr(PATH(*PROTO[:n]));a.op(18);a.branch('metrics_initialize')
    a.expr(P(proto,MARKER));a.branch('metrics_done')
    a.label('metrics_initialize')
    while len(data)%8:a.op(89);a.op(23)
    copy_start=len(data);branding.copy_initializer(a,apt,block)
    correct_legacy_provider_calls(data,block,copy_start-block[0].end)
    for name in ('SetData','Publish','Shutdown'):a.set(proto,OLD+name,P(proto,name))
    b.CLASS=CLASS;b.FULL='.'.join(CLASS)
    def ensure(a):
        a.when(T('__careerHeaderMetrics'),lambda a:a.ret())
        a.set(R(1),'__careerHeaderMetrics',CALL(R(1),'createEmptyMovieClip','__careerHeaderMetrics',12020))
        clip=T('__careerHeaderMetrics')
        for name,x,w,size,ink in (('effLabel',22,106,14,MUTED),('effValue',128,44,18,INK),('prestigeLabel',216,60,14,MUTED),('prestigeValue',279,54,18,INK)):
            a.do(clip,'createTextField',name,12021+x,x,4 if name.endswith('Label') else 0,w,25)
            text=P(clip,name);a.set(text,'selectable',False);a.set(text,'textColor',ink)
            a.set(text,'embedFonts',True)
            fmt=('newmethod',b.GLOBAL,'TextFormat',('EA HelveticaNeue Con Bold',size,ink))
            a.do(text,'setTextFormat',fmt);a.do(text,'setNewTextFormat',fmt)
        a.set(P(clip,'effLabel'),'text','Aproveitamento')
        a.set(P(clip,'prestigeLabel'),'text','Prestígio')
    a.function('Server16EnsureHeaderMetrics',0,ensure)
    def render(a):
        a.when(T('m_objData'),lambda a:None,lambda a:a.ret())
        tournament=EQ(CALL(b.GLOBAL,'Number',P(T('m_objData'),'IS_TOURNAMENTMODE')),1)
        def standard(a):
            for part in ('mcHeaderLeft','mcMiddle','mcRight'):a.set(T(part),'_height',79)
            a.set(T('mcCrest'),'_y',5)
            a.set(T('txtTeam'),'_y',('bin',13,('bin',11,79,P(T('txtTeam'),'_height')),2))
            for icon in ('mcHeaderEfficiencyIcon','mcHeaderPrestigeIcon','mcHeaderMetricDivider'):a.set(T(icon),'_visible',False)
            a.when(T('__careerHeaderMetrics'),lambda a:a.set(T('__careerHeaderMetrics'),'_visible',False))
            a.ret()
        a.when(tournament,standard)
        a.when(T('__careerCoachGraph'),lambda a:a.set(T('__careerCoachGraph'),'_visible',False))
        a.do(R(1),'Server16EnsureHeaderMetrics');clip=T('__careerHeaderMetrics')
        a.set(clip,'_visible',True);a.set(clip,'_x',P(T('txtTeam'),'_x'));a.set(clip,'_y',METRICS_Y)
        a.set(T('txtTeam'),'_y',5);a.set(T('txtName'),'_y',37)
        for part in ('mcHeaderLeft','mcMiddle','mcRight'):a.set(T(part),'_height',HEIGHT)
        # ImageLoader has zero height before its asynchronous crest is ready.
        # Offset from the stock 79px header, whose crest origin is already correct.
        a.set(T('mcCrest'),'_y',5+(HEIGHT-79)/2)
        for icon,offset in (('mcHeaderEfficiencyIcon',0),('mcHeaderPrestigeIcon',191),('mcHeaderMetricDivider',178)):
            a.set(T(icon),'_visible',True);a.set(T(icon),'_x',('bin',71,P(clip,'_x'),offset));a.set(T(icon),'_y',METRICS_Y)
        a.set(T('mcMiddle'),'_width',CALL(PATH('Math'),'max',P(T('mcMiddle'),'_width'),('bin',71,('bin',11,P(clip,'_x'),P(T('mcMiddle'),'_x')),ROW_WIDTH+12)))
        a.set(T('mcRight'),'_x',('bin',71,P(T('mcMiddle'),'_x'),P(T('mcMiddle'),'_width')))
        a.set(P(clip,'effValue'),'text','—');a.set(P(clip,'prestigeValue'),'text','—')
        valid=('bin',16,T('__careerHeaderData'),EQ(CALL(b.GLOBAL,'Number',P(T('__careerHeaderData'),'CAREER_HEADER_CLUB_ID')),CALL(b.GLOBAL,'Number',P(T('m_objData'),'ASSET_ID'))))
        def values(a):
            for key,field in (('effValue','CAREER_HEADER_EFFICIENCY'),('prestigeValue','CAREER_HEADER_PRESTIGE')):
                a.when(P(T('__careerHeaderData'),field),lambda a,key=key,field=field:a.set(P(clip,key),'text',P(T('__careerHeaderData'),field)))
        a.when(valid,values)
    a.function('__careerDrawCoachGraph',0,render)
    def set_data(a):
        a.when(('not',EQ(T('__careerHeaderClub'),P(T('m_objData'),'ASSET_ID'))),lambda a:a.set(R(1),'__careerHeaderData',None))
        a.set(R(1),'__careerHeaderClub',P(T('m_objData'),'ASSET_ID'))
        a.do(R(1),OLD+'SetData')
        career=('not',EQ(CALL(b.GLOBAL,'Number',P(T('m_objData'),'IS_TOURNAMENTMODE')),1))
        def register(a):
            a.when(T('__careerMetricsRegistered'),lambda a:a.ret())
            a.set(R(1),'__careerMetricsRegistered',True)
            a.do(utility,'RegisterDataProvider',R(1),provider)
        a.when(career,register)
    a.function('SetData',0,set_data)
    def publish(a):
        def metrics(a):
            # CM_STATISTICS_DP publishes ID/PARAM rows, like the native tiles.
            # Consume only our three fields, keeping unrelated tile data local.
            a.set(R(1),'__careerHeaderData',('object',))
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
                    ('CAREER_HEADER_PRESTIGE','CAREER_HEADER_PRESTIGE'))
            for bit,(field,target) in enumerate(fields):
                def capture(a,target=target,mask=1<<bit):
                    a.set(T('__careerHeaderData'),target,P(R(6),'PARAM'))
                    a.expr(('bin',97,R(7),mask));a.store(7)
                a.when(EQ(P(R(6),'ID'),field),capture)
            a.expr(EQ(R(7),7));a.branch(done)
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
    left_clip(apt);additions=native_icons(apt);script(apt,actions);write_container(big,output,additions)
    checked=BigFile(output);parsed=AptFile(checked);decoded=Actions(parsed).read_all()
    if decoded.errors:raise ValueError(decoded.errors)
    parsed.validate_layout()
    for key,entry in big.entries.items():
        if key!=apt.entry.name and bytes(checked.entries[key].data)!=entry.original:raise ValueError('Existing art changed: '+key)
    return dict(path=str(output),bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),height=HEIGHT,images='unchanged',native_provider='CM_STATISTICS_DP')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--studio',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(build(args.source,args.output,args.studio),ensure_ascii=False,indent=2))
