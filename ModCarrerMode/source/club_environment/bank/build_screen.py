from ui_theme import ACCENT_INK, rgb
import portable_paths as portable
"""Build a separate native APT screen; use only existing fonts and BaseScreen."""
from pathlib import Path
import json, struct, sys
from formats import AptFile, BigFile, Reader, chunk_wrap
from apt_actions import Actions
from apt_assembler import Assembler
from loans import BANKS, AMOUNTS, TERMS, quote

HERE = Path(__file__).resolve().parent
CLASS = ('game','screens','career','server16','BankLoansV2')
FULL = '.'.join(CLASS)
PAGE = 'game/screens/career/server16/BankLoansV2'
NONCE = 'B261021A'

def write_big(big,path,additions,*,compression_level=9):
    content=lambda name:bytes(big.entries[name].data)
    # Native resource groups: APT + geometry, sg1, textures, sg2, constants.
    # Adding geometry/textures after the original sg2 is structurally parseable
    # offline but does not satisfy the native grouped-resource loader.
    entries=[('0',content('0'))]
    entries.extend((n,b) for n,b in additions.items() if not b.startswith(b'DDS '))
    entries.append(('sg1',b''))
    entries.extend((n,b) for n,b in additions.items() if b.startswith(b'DDS '))
    entries.extend([('sg2',b''),('1',content('1'))])
    assert len({n for n,_ in entries})==len(entries)
    header=16+sum(9+len(n.encode('latin1')) for n,_ in entries)
    offset=(header+63)//64*64;directory=bytearray();payload=bytearray(offset-header)
    for name,blob in entries:
        pad=-offset%64;payload.extend(bytes(pad));offset+=pad
        directory.extend(struct.pack('>II',offset,len(blob))+name.encode('latin1')+b'\0')
        payload.extend(blob);offset+=len(blob)
    content=b'BIGF'+struct.pack('<I',offset)+struct.pack('>II',len(entries),header)+directory+payload
    path.write_bytes(chunk_wrap(content,big.wrapper,level=compression_level) if big.wrapper else content)


def reg(n): return ('r', n)
def prop(obj, name): return ('p', obj, name)
def path(*names): return ('path', names)
def call(obj, name, *args): return ('call', obj, name, args)
def plus(a,b): return ('bin',71,a,b)
def equal(a,b): return ('bin',73,a,b)
def this(name): return prop(reg(1),name)
GLOBAL = ('global',)
G = lambda name: prop(GLOBAL,name)
MANAGER = lambda name: path('game','globalClasses',name)
ION = G('ION_CareerMode')


class Code(Assembler):
    def __init__(self, data):
        super().__init__(data); self.serial = 0
    def uid(self):
        self.serial += 1; return 'L'+str(self.serial)
    def expr(self, value):
        if value is None: self.op(117)
        elif type(value) is bool: self.op(115 if value else 116)
        elif isinstance(value,int): self.op(183); self.data.extend(struct.pack('<i',value))
        elif isinstance(value,str): self.string(value)
        elif value[0]=='r': self.reg(value[1])
        elif value[0]=='global': self.global_object()
        elif value[0]=='path': self.path(*value[1])
        elif value[0]=='p': self.expr(value[1]); self.string(value[2]); self.op(78)
        elif value[0]=='bin': self.expr(value[2]); self.expr(value[3]); self.op(value[1])
        elif value[0]=='call':
            for item in reversed(value[3]): self.expr(item)
            self.expr(len(value[3])); self.expr(value[1]); self.string(value[2]); self.op(82)
        elif value[0]=='array':
            for item in reversed(value[1]): self.expr(item)
            self.expr(len(value[1])); self.op(66)
        elif value[0]=='newmethod':
            for item in reversed(value[3]):self.expr(item)
            self.expr(len(value[3]));self.expr(value[1]);self.string(value[2]);self.op(83)
        elif value[0]=='object':self.expr(0);self.string('Object');self.op(64)
        elif value[0]=='index': self.expr(value[1]); self.expr(value[2]); self.op(78)
        else: raise ValueError(value)
    def set(self, obj, name, value):
        self.expr(obj); self.string(name); self.expr(value); self.op(79)
    def do(self, obj, name, *args): self.expr(call(obj,name,*args)); self.op(23)
    def when(self, condition, yes, no=None):
        other,done = self.uid(),self.uid()
        self.expr(condition); self.op(18); self.branch(other)
        yes(self); self.branch(done,False); self.label(other)
        if no: no(self)
        self.label(done)
    def ret(self, value=None): self.expr(value); self.op(62)
    def function(self, name, count, body, constructor=False):
        self.expr(path(*CLASS[:-1]) if constructor else path(*CLASS,'prototype'))
        self.string(name)
        self.op(142); self.align()
        at=len(self.data); self.data.extend(bytes(8)); self.fixups.append((at,''))
        self.data.extend(struct.pack('<IHH',count,12,25 if constructor else 41))
        at=len(self.data); self.data.extend(bytes(8)); self.parameters.append((at,count))
        size_at=len(self.data);self.data.extend(bytes(4));self.align()
        self.data.extend(struct.pack('<I',0x98765432));self.align();self.data.extend(struct.pack('<Q',0x12345678))
        start=len(self.data)
        body(self)
        # A native MovieClip constructor completes without an explicit null
        # result, like the stock constructor. Void methods return undefined.
        if not constructor:self.op(118);self.op(62)
        struct.pack_into('<I',self.data,size_at,len(self.data)-start)
        self.op(79)


def money(n): return f'{n:,}'.replace(',','.')


def make_script(data,dictionaries):
    a=Code(data);a.align();start=len(data)
    data.extend(dictionaries[0])
    for index,name in enumerate(CLASS[:-1]):
        parent=GLOBAL if index==0 else path(*CLASS[:index])
        a.when(prop(parent,name),lambda a:None,lambda a,parent=parent,name=name:a.set(parent,name,('object',)))
    def constructor(a):
        a.op(89);a.reg(2);a.op(118);a.op(93)
        callback=call(path('cafe','utility','Delegate'),'Create',reg(1),this('OnExitScreen'))
        a.do(MANAGER('ScreenManager'),'SetOnExitScreenCallback',callback)
        a.do(reg(1),'Initialize',FULL,None,True)
        for name in ('InitData','InitComponents','AnimateIn'):a.do(reg(1),name)
    a.function(CLASS[-1],0,constructor,True)
    a.expr(path(*CLASS));a.expr(path('ion','screen','BaseScreen'));a.op(105)
    a.function('getHelpContext',0,lambda a:a.ret(('array',(
        call(path('ion','manager','HelpItem'),'CreateHelpTickerItem','Selecionar','ADVANCE'),
        call(path('ion','manager','HelpItem'),'CreateHelpTickerItem','Voltar','BACK')))))
    def init_data(a):
        a.set(reg(1),'staticData',call(ION,'GetScreenStaticData'))
        # FIFA 16 obtains Navigation event tokens from ION, not a global
        # Navigation object (that object does not implement this API).
        a.set(reg(1),'navEvents',call(ION,'GetEvents','Navigation'))
    a.function('InitData',0,init_data)
    def init_components(a):
        for key,value in [('page',0),('bank',0),('amountIndex',0),('termIndex',1),('focus',0)]:a.set(reg(1),key,value)
        a.when(G('Server16BankSequence'),lambda a:None,lambda a:a.set(GLOBAL,'Server16BankSequence',0))
        a.set(reg(1),'_visible',True);a.set(reg(1),'_alpha',100)
        a.do(reg(1),'InitBankCards')
        a.do(reg(1),'Refresh')
    a.function('InitComponents',0,init_components)
    def init_cards(a):
        a.set(reg(1),'panels',('array',()))
        a.set(reg(1),'panelWidth',('bin',11,('bin',13,plus(call(this('mcGridControl'),'GetVisibleWidth'),prop(path('game','components','GridControl'),'CELL_GAP')),3),prop(path('game','components','GridControl'),'CELL_GAP')))
        a.set(reg(1),'panelHeight',call(this('mcGridControl'),'GetVisibleHeight'))
        delegate=lambda name:call(path('cafe','utility','Delegate'),'Create',reg(1),this(name))
        args=(1,1,3,3,this('panelWidth'),this('panelHeight'),'CareerPanel',delegate('UpdatePanel'),delegate('HighlightPanel'),delegate('UnhighlightPanel'),delegate('SelectPanel'),None,None,delegate('ShutdownPanel'),True)
        a.set(reg(1),'gridData',('newmethod',path('game','components'),'GridControlData',args))
        a.do(this('gridData'),'SetHorizontalWrap',True)
        a.do(this('mcGridControl'),'Init',this('gridData'),this('bank'),prop(path('game','components','GridControl'),'STYLE_TILES'))
    a.function('InitBankCards',0,init_cards)
    def update_panel(a):
        panel=reg(2);index=reg(5)
        a.expr(this('panels'));a.expr(index);a.expr(panel);a.op(79)
        header=prop(panel,'txtHeader');label=prop(panel,'txtLabel')
        a.do(header,'setTextFormat',prop(MANAGER('StyleManager'),'FONT_TILE_HL'))
        a.do(label,'setTextFormat',prop(MANAGER('StyleManager'),'FONT_REGULAR_FHD'))
        a.set(header,'_width',('bin',11,this('panelWidth'),40))
        a.set(label,'_width',('bin',11,this('panelWidth'),40))
        a.set(label,'_height',('bin',11,this('panelHeight'),95))
        a.set(label,'_y',79)
        a.set(header,'text',('index',('array',tuple(b['name'].upper() for b in BANKS)),index))
        a.set(label,'text',('index',('array',tuple(str(b['rate_bps']/100).replace('.',',')+'% de juros ao mes' for b in BANKS)),index))
        a.set(prop(panel,'mcImage'),'_visible',False)
        a.when(equal(index,this('bank')),lambda a:a.do(reg(1),'HighlightPanel',panel,reg(3),reg(4),index),lambda a:a.do(reg(1),'UnhighlightPanel',panel,reg(3),reg(4),index))
    a.function('UpdatePanel',4,update_panel)
    def highlight(a):
        a.set(reg(1),'bank',reg(5))
        for name in ('txtHeader','txtLabel'):a.set(prop(reg(2),name),'textColor',prop(MANAGER('StyleManager'),'COLOR_TEXT_SELECTED'))
        a.do(reg(1),'Refresh')
    a.function('HighlightPanel',4,highlight)
    def unhighlight(a):
        a.set(prop(reg(2),'txtHeader'),'textColor',prop(MANAGER('StyleManager'),'COLOR_TEXT_REGULAR'))
        a.set(prop(reg(2),'txtLabel'),'textColor',prop(MANAGER('StyleManager'),'COLOR_TEXT_DESCRIPTION'))
    a.function('UnhighlightPanel',4,unhighlight)
    def select_panel(a):
        a.when(equal(this('page'),0),lambda a:None,lambda a:a.ret(False))
        a.set(reg(1),'bank',reg(5));a.do(reg(1),'Select');a.ret(True)
    a.function('SelectPanel',4,select_panel)
    a.function('ShutdownPanel',1,lambda a:None)
    def animate(a):
        a.do(MANAGER('ScreenManager'),'AddItemToAnimateIn',this('mcGridControl'))
        a.do(MANAGER('ScreenManager'),'BeginAnimateIn',call(path('cafe','utility','Delegate'),'Create',reg(1),this('OnAnimateInComplete')))
        # The stock Calendar constructor also completes its initial setup
        # explicitly. No calendar cells or simulation events are involved here.
        a.do(reg(1),'OnAnimateInComplete')
    a.function('AnimateIn',0,animate)
    def complete(a):
        a.when(('bin',17,this('exiting'),this('screenReady')),lambda a:a.ret());a.set(reg(1),'screenReady',True)
        a.set(reg(1),'_visible',True);a.set(reg(1),'_alpha',100)
        a.do(ION,'SendEvent',prop(this('staticData'),'SCREEN_CONTROLLER_ID'),'SCREEN_READY','')
        a.do(ION,'SendSystemEvent',prop(this('staticData'),'SCREEN_CONTROLLER_ID'),'DONE_LOADING','')
        a.do(MANAGER('InputManager'),'SetLocalEventHandler',call(path('cafe','utility','Delegate'),'Create',reg(1),this('LocalEventHandler')))
        a.do(MANAGER('HelpManager'),'Update')
    a.function('OnAnimateInComplete',0,complete)
    def refresh(a):
        a.do(this('mcGridControl'),'EnableMouseButton',equal(this('page'),0))
        text=lambda field,value:a.set(this(field),'text',value)
        text('title','EMPRESTIMOS DO CLUBE')
        text('subtitle','Escolha um banco e confira as condicoes antes de contratar.')
        amount=('index',('array',tuple(money(n) for n in AMOUNTS)),this('amountIndex'))
        term=('index',('array',TERMS),this('termIndex'))
        text('amount',plus('VALOR DO EMPRESTIMO: ',amount))
        text('term',plus(plus('PRAZO: ',term),' meses'))
        text('detail','As parcelas vencem mensalmente na data da carreira.')
        text('detail2','O credito e as cobrancas entram no orcamento de transferencias.')
        text('status','Bancos ficticios. Teste local.')
        a.when(equal(this('page'),0),lambda a:text('step','1. ESCOLHA O BANCO'))
        def selection(a):
            text('step','2. ESCOLHA O VALOR E O PRAZO')
            text('status','Cima / baixo alternam entre valor e prazo. Esquerda / direita ajustam.')
            a.set(this('amount'),'textColor',0x334b56);a.set(this('term'),'textColor',0x334b56)
            a.when(equal(this('focus'),0),lambda a:a.set(this('amount'),'textColor',rgb(ACCENT_INK)),lambda a:a.set(this('term'),'textColor',rgb(ACCENT_INK)))
        a.when(equal(this('page'),1),selection)
        for bank in range(3):
            for ai,amount0 in enumerate(AMOUNTS):
                for ti,term0 in enumerate(TERMS):
                    q=quote(bank,amount0,term0)
                    cond=('bin',16,('bin',16,equal(this('bank'),bank),equal(this('amountIndex'),ai)),equal(this('termIndex'),ti))
                    value=f"Parcela mensal: {money(q['payment'])}   |   Ultima parcela: {money(q['payments'][-1]['amount'])}"
                    value2=f"Total: {money(q['total'])}   |   Juros totais: {money(q['total']-amount0)}"
                    a.when(cond,lambda a,value=value,value2=value2:(text('summary',value),text('summary2',value2)))
        def review(a):
            text('step','3. CONFIRMAR CONTRATACAO')
            text('status','A / ENTER contrata este emprestimo. B / ESC retorna sem contratar.')
        a.when(equal(this('page'),2),review)
        def submitted(a):
            text('step','PEDIDO ENVIADO')
            text('status','Aguarde a aplicacao do teste antes de salvar. B / ESC retorna ao modo carreira.')
        a.when(equal(this('page'),3),submitted)
    a.function('Refresh',0,refresh)
    def submit(a):
        a.set(GLOBAL,'Server16BankSequence',plus(G('Server16BankSequence'),1))
        value=f'S16BANK_V1|{NONCE}|'
        for part in (G('Server16BankSequence'),'|',this('bank'),'|',this('amountIndex'),'|',this('termIndex'),'|END_S16BANK'):
            value=plus(value,part)
        a.set(GLOBAL,'Server16BankRequest',value)
        a.set(reg(1),'page',3);a.do(reg(1),'Refresh')
    a.function('Submit',0,submit)
    def back(a):
        def exit_screen(a):
            a.do(ION,'SendEvent',prop(this('staticData'),'SCREEN_CONTROLLER_ID'),prop(this('navEvents'),'BACK'),'')
            a.do(MANAGER('InputManager'),'DisableCurrentLocalEventHandler')
        a.when(('bin',17,equal(this('page'),0),equal(this('page'),3)),exit_screen,
               lambda a:(a.set(reg(1),'page',('bin',11,this('page'),1)),a.do(reg(1),'Refresh')))
    a.function('Back',0,back)
    def select(a):
        a.when(equal(this('page'),2),lambda a:(a.do(reg(1),'Submit'),a.ret()))
        a.when(('bin',72,this('page'),2),lambda a:(a.set(reg(1),'page',plus(this('page'),1)),a.do(reg(1),'Refresh')))
    a.function('Select',0,select)
    def shift(a):
        def wrap_field(field,count):a.set(reg(1),field,('bin',63,plus(plus(this(field),reg(2)),count),count))
        a.when(equal(this('page'),0),lambda a:wrap_field('bank',3))
        a.when(equal(this('page'),1),lambda a:a.when(equal(this('focus'),0),lambda a:wrap_field('amountIndex',4),lambda a:wrap_field('termIndex',3)))
        a.do(reg(1),'Refresh')
    a.function('Shift',1,shift)
    def key(a):
        a.when(equal(reg(2),prop(MANAGER('InputCodes'),'BACK')),lambda a:(a.do(reg(1),'Back'),a.ret(True)))
        # The game's grid owns focus, select animations, pointer interaction and
        # left/right navigation of its native tiles. Back is handled first.
        a.when(equal(this('page'),0),lambda a:a.ret(call(this('mcGridControl'),'LocalEventHandler',reg(2),reg(3))))
        for code,name,args in [('BACK','Back',()),('PRIMARY_SELECT','Select',()),('LEFT','Shift',(-1,)),('RIGHT','Shift',(1,))]:
            cond=equal(reg(2),prop(MANAGER('InputCodes'),code))
            a.when(cond,lambda a,name=name,args=args:(a.do(reg(1),name,*args),a.ret(True)))
        condition=('bin',17,equal(reg(2),prop(MANAGER('InputCodes'),'UP')),equal(reg(2),prop(MANAGER('InputCodes'),'DOWN')))
        a.when(condition,lambda a:(a.set(reg(1),'focus',('bin',11,1,this('focus'))),a.do(reg(1),'Refresh')))
        a.ret(True)
    a.function('LocalEventHandler',2,key)
    def shutdown(a):
        a.when(this('exiting'),lambda a:a.ret());a.set(reg(1),'exiting',True);a.set(reg(1),'onEnterFrame',None)
        a.do(MANAGER('InputManager'),'DisableCurrentLocalEventHandler')
        a.do(this('mcGridControl'),'Shutdown')
        a.do(MANAGER('HelpManager'),'Clear')
        a.do(reg(1),'Shutdown')
    a.function('OnExitScreen',0,shutdown)
    a.op(0);a.finish()
    a.align();register_start=len(data)
    data.extend(dictionaries[1])
    # APT's __Packages export is initialized on demand by a dotted GetVariable.
    # Walking namespace members here does NOT instantiate that package: char 10
    # is an unplaced class symbol, so its DoInitAction has not run yet. Match the
    # stock screen's registration lookup to trigger the class initializer first.
    a.string(FULL);a.op(28)
    a.string(FULL);a.expr(2);a.expr(path('Object'));a.method('registerClass');a.op(23);a.op(0);a.finish()
    return start,register_start


FIELDS = (
    ('title',109,145,1702,65,48), ('subtitle',109,215,1702,48,28),
    ('step',109,278,1702,54,34),
    ('amount',129,545,1600,56,34),('term',129,615,1600,56,34),
    ('summary',129,705,1600,45,30),('summary2',129,755,1600,45,30),
    ('detail',129,825,1600,38,25),('detail2',129,864,1600,38,25),
    ('status',109,935,1702,45,26),
)


def build():
    output=HERE/'package/data/ui/game/screens/career/server16/bankloans.big'
    output.parent.mkdir(parents=True,exist_ok=True)
    big=BigFile(HERE/'careertype.big');apt=AptFile(big);data=apt.data
    root=Reader(big.entries['1'].data,20,8).ptr()
    def append(blob):
        data.extend(bytes(-len(data)%8));at=len(data);data.extend(blob);return at
    controls=[];new_chars=[]
    template=apt.root_frames[0][0]
    count,table=struct.unpack_from('<I4xQ',data,root+56)
    # A white texture and native rectangle geometry provide opaque panels.
    # They are new characters in this package, not replacements for any game UI.
    panel_source=AptFile(BigFile(portable.GAME/'data/ui/game/components/careercomponents/careerhubwidget.big'))
    tex_id,shape_id=count,count+1
    blob=bytearray(panel_source.data[panel_source.characters[1].offset:panel_source.characters[1].offset+40])
    struct.pack_into('<I',blob,32,tex_id);new_chars.append(append(blob))
    blob=bytearray(panel_source.data[panel_source.characters[2].offset:panel_source.characters[2].offset+56])
    struct.pack_into('<I',blob,16,tex_id<<16);struct.pack_into('<4fI',blob,32,0,0,1,1,shape_id)
    new_chars.append(append(blob))
    geo=bytearray(panel_source.big.entries['3'].data)
    struct.pack_into('<I',geo,16+36,tex_id);struct.pack_into('<6f',geo,16+48,1,0,0,1,0,0)
    for index,xy in enumerate(((0,1),(0,0),(1,0),(1,0),(1,1),(0,1))):struct.pack_into('<2f',geo,96+index*32,*xy)
    header=bytearray(panel_source.big.entries['7'].data[:128]);struct.pack_into('<III',header,12,4,4,16);struct.pack_into('<I',header,28,1)
    texture=bytes(header)+bytes((255,255,0,0,0,0,0,0))+struct.pack('<HHI',65535,65535,0)
    additions={str(tex_id+1):texture,str(shape_id+1):bytes(geo)}
    for depth,(x,y,w,h,color) in enumerate((((48,100,1824,785,0xfff4f6f7) if globals().get('USE_R60') else (89,130,1742,855,0xfff4f6f7)),),1):
        place=bytearray(data[template.offset:template.offset+80])
        # 0x20 means HasName. Anonymous panel shapes must clear that flag;
        # FIFA's native PlaceObject reader dereferences name without a null check.
        struct.pack_into('<iii6f',place,8,14,depth,shape_id,w,0,0,h,x,y)
        struct.pack_into('<I',place,44,color);struct.pack_into('<Q',place,56,0)
        controls.append(append(place))
    # Keep the actual imported FIFA GridControl + CareerPanel linkage. It owns
    # the tile background, selected state, focus and pointer/keyboard behavior.
    native_grid=apt.characters[9].frames[0][0]
    place=bytearray(data[native_grid.offset:native_grid.offset+80])
    struct.pack_into('<i',place,12,5)
    struct.pack_into('<6f',place,20,6.8079986572265625,0,0,.72,109,340)
    controls.append(append(place))
    # New native text instances use the game's original font descriptors.
    for index,(name,x,y,width,height,size) in enumerate(FIELDS):
        blob=bytearray(data[apt.characters[3].offset:apt.characters[3].offset+96])
        struct.pack_into('<4f',blob,32,0,0,width,height)
        struct.pack_into('<I',blob,48,2);struct.pack_into('<If',blob,56,0xff334b56,size)
        if name.startswith('summaryValue') or name in ('responseHint','overviewBudget','overviewWage') or name.startswith('cell') and name.endswith('_2'):struct.pack_into('<I',blob,52,1)
        struct.pack_into('<QQ',blob,80,append(b'\0'),0)
        char=append(blob);new_chars.append(char)
        place=bytearray(data[template.offset:template.offset+80])
        struct.pack_into('<iii6f',place,8,38,index+10,count+index+2,1,0,0,1,x,y)
        struct.pack_into('<Q',place,56,append(name.encode()+b'\0'))
        controls.append(append(place))
    if globals().get('USE_R57'):
        from bank_ui_r57 import graphics
        graphics(data,apt,template,shape_id,append,new_chars,controls,count,additions)
    if globals().get('USE_R60'):
        from bank_display import normalize_root
        from bank_ui_r60 import BUTTONS
        normalize_root(data,controls,FIELDS,BUTTONS)
    new_table=append(bytes(data[table:table+count*8])+struct.pack('<'+'Q'*len(new_chars),*new_chars))
    struct.pack_into('<I4xQ',data,root+56,count+len(new_chars),new_table)
    control_table=append(struct.pack('<'+'Q'*len(controls),*controls))
    frames=append(struct.pack('<I4xQ',len(controls),control_table))
    struct.pack_into('<I4xQ',data,apt.characters[9].offset+32,1,frames)
    # Rename only this package's exports. The original CareerType file is intact.
    er=Reader(data,root+96,8);export_count=er.i();exports=er.ptr()
    for index in range(export_count):
        at=exports+index*16;old=Reader(data,at,8).text()
        if 'CareerType' in old:struct.pack_into('<Q',data,at,append(old.replace('game.screens.career.CareerType',FULL).encode()+b'\0'))
    original_actions=Actions(apt).read_all()
    dictionaries=[bytes(data[b[0].offset:b[0].end]) for b in original_actions.cache.values()]
    assert len(dictionaries)==2 and all(block[0]==136 for block in dictionaries)
    start,registration=make_script(data,dictionaries)
    for tag,target in [(apt.root_frames[0][1],start),(apt.root_frames[0][2],registration)]:
        old=struct.pack('<Q',tag[-1]);matches=[i for i in range(0,len(apt.entry.original)-7,8) if apt.entry.original[i:i+8]==old]
        assert len(matches)==1,matches
        struct.pack_into('<Q',data,matches[0],target)
    write_big(big,output,additions)
    parsed=AptFile(BigFile(output));actions=Actions(parsed).read_all()
    assert not actions.errors,actions.errors
    assert FULL in parsed.exports and 'game.screens.career.CareerType' not in parsed.exports
    (HERE/'screen_metadata.json').write_text(json.dumps({'page':PAGE,'class':FULL,'nonce':NONCE,
        'fields':FIELDS,'file':str(output),'bytes':output.stat().st_size,'methods':len(actions.functions)},indent=2))
    print('Built native screen:',output,output.stat().st_size,'bytes')

if __name__=='__main__':build()
