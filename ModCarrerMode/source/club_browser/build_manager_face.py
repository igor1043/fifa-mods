"""Extend FIFA's original ManagerPreferences class; retain every native row."""
from pathlib import Path
import hashlib,json,os,struct,sys

SOURCE=Path(__file__).resolve().parents[1];ENV=SOURCE/'club_environment'
sys.path[:0]=[str(SOURCE),str(ENV),str(ENV/'vendor'),str(ENV/'bank'),str(ENV/'preview'),str(ENV/'manager_market')]
import build_screen as b
from build_preview import Code
from formats import BigFile,AptFile,Reader
from apt_actions import Actions
from manager_market.model_assets import catalog,installed

CLASS=('game','screens','career','ManagerPreferences');PROTO=b.path(*CLASS,'prototype')
R=b.reg;P=b.prop;T=b.this;CALL=b.call;PATH=b.path;M=b.MANAGER;EQ=b.equal;ION=b.ION
ROW='SERVER16_MANAGER_FACE'
NATIVE_CLIPS=('mcMainFrame','mcHighlight','mcRowControl','mcRectangle','mcTextFields','mcImageLoader')


def build(game,original,output,catalog_file):
    game,output=Path(game),Path(output);big=BigFile(original);apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    if 'game.screens.career.ManagerPreferences' not in apt.exports:raise ValueError('Not FIFA manager preferences')
    if b'S16FaceOpen\0' in apt.data:raise ValueError('Preferences already patched; use the original backup')
    registration=next(c for c in apt.root_frames[0] if isinstance(c,tuple) and c[0]=='init' and c[1]==apt.exports['game.screens.career.ManagerPreferences'])
    code=actions.cache[registration[-1]]
    if code[-1].op!=0:raise ValueError('Missing original registration terminator')
    data=apt.data;data.extend(bytes(-len(data)%8));start=len(data);data.extend(data[registration[-1]:code[-1].offset])
    a=Code(data);b.CLASS=CLASS;b.FULL='.'.join(CLASS)
    already=a.uid();a.expr(P(PROTO,'S16FaceInstalled'));a.branch(already);a.set(PROTO,'S16FaceInstalled',True)
    originals={'_InitComponentsData':'S16BaseInit','_LocalEventHandler':'S16BaseInput','getHelpContext':'S16BaseHelp','_OnExitScreen':'S16BaseExit','_OnAnimateInComplete':'S16BaseComplete','_UpdateRow':'S16BaseUpdateRow'}
    for old,new in originals.items():a.set(PROTO,new,P(PROTO,old))
    def send(a,value):a.do(ION,'SendSystemEvent',P(T('m_StaticData'),'SCREEN_CONTROLLER_ID'),'Server16ManagerFace',value)
    def background(a,active):
        a.set(b.GLOBAL,'Server16ManagerFaceActive',active)
        # Creation uses BackgroundBootflow, while the career visualizers use
        # BackgroundFIFA. They can coexist; never let one replace the other's
        # owner or leave its photograph covering the native 3D scene.
        for key in ('Server16ManagerFaceBackgroundOwner','Server16ManagerFaceBootBackgroundOwner'):
            owner=b.G(key)
            a.when(P(owner,'S16SyncManagerFaceBackground'),lambda a,owner=owner:a.do(owner,'S16SyncManagerFaceBackground'))
    def init(a):
        a.do(R(1),'S16BaseInit')
        advance=('index',T('m_RowData'),0)
        # Reuse only the verified native button event descriptor. The owned
        # marker is handled before FIFA's controller, so it never receives a
        # new/unknown provider row name or an out-of-range native option.
        row=a.object(dict(NAME=P(advance,'NAME'),S16Face=True,S16Identity=ROW,TYPE=P(PATH(*CLASS),'TYPE_BUTTON'),LABEL='Face',TITLE='Aparência do treinador',DESC='Escolha um dos modelos 3D instalados para usar nesta carreira.'))
        a.when(T('m_RowData'),lambda a:a.do(T('m_RowData'),'splice',4,0,row))
    a.function('_InitComponentsData',0,init)
    def update_row(a):
        a.do(R(1),'S16BaseUpdateRow',R(2),R(3))
        row=('index',T('m_RowData'),R(3))
        a.when(P(row,'S16Face'),lambda a:(a.set(R(1),'S16FaceValueRow',R(2)),a.set(P(R(2),'txtLink'),'_visible',False)))
    a.function('_UpdateRow',2,update_row)
    def publish_value(a):
        a.when(T('S16FaceActive'),lambda a:a.ret())
        row=T('S16FaceValueRow');field=P(row,'mcInputText');label=P(row,'txtButton')
        a.when(('bin',16,row,('bin',16,P(row,'localToGlobal'),T('globalToLocal'))),lambda a:None,lambda a:a.ret())
        # Use the same value column as the native input/toggle rows. txtLink
        # is only a short nationality link, not the width of the value cell.
        a.set(R(1),'S16ValueTop',a.object(dict(x=P(field,'_x'),y=P(label,'_y'))))
        a.set(R(1),'S16ValueBottom',a.object(dict(x=('bin',11,P(T('mcMainFrame'),'_width'),32),y=b.plus(P(label,'_y'),P(label,'_height')))))
        a.do(row,'localToGlobal',T('S16ValueTop'));a.do(row,'localToGlobal',T('S16ValueBottom'))
        # localToGlobal includes FIFA's root UI scale (and ultrawide offset).
        # The native overlay uses this screen's 1280x720 logical coordinates.
        a.do(R(1),'globalToLocal',T('S16ValueTop'));a.do(R(1),'globalToLocal',T('S16ValueBottom'))
        top=T('S16ValueTop');bottom=T('S16ValueBottom')
        rounded=lambda value:CALL(PATH('Math'),'round',value)
        values=[rounded(P(top,'x')),rounded(P(top,'y')),rounded(('bin',11,P(bottom,'x'),P(top,'x'))),rounded(('bin',11,P(bottom,'y'),P(top,'y')))]
        wire='row:'
        for i,value in enumerate(values):
            if i:wire=b.plus(wire,',')
            wire=b.plus(wire,value)
        a.when(EQ(T('S16ValueWire'),wire),lambda a:None,lambda a:(send(a,wire),a.set(R(1),'S16ValueWire',wire)))
        a.set(R(1),'S16ValueFocus',EQ(CALL(T('mcRowControl'),'getSelectedIndex'),4))
        a.when(EQ(T('S16ValueLastFocus'),T('S16ValueFocus')),lambda a:None,lambda a:(a.when(T('S16ValueFocus'),lambda a:send(a,'row_focus'),lambda a:send(a,'row_blur')),a.set(R(1),'S16ValueLastFocus',T('S16ValueFocus'))))
    a.function('S16FacePublishValue',0,publish_value)
    def refresh(a):
        a.do(M('HelpManager'),'SetCustomSource',CALL(PATH('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')))
        a.do(M('HelpManager'),'Update');a.do(M('HelpManager'),'Show')
    a.function('S16FaceHelp',0,refresh)
    def opened(a):
        a.set(R(1),'S16FaceActive',True)
        background(a,True)
        for name in NATIVE_CLIPS:
            a.set(R(1),'S16Visible_'+name,P(T(name),'_visible'));a.set(T(name),'_visible',False)
        send(a,'open')
        a.do(PATH('Mouse'),'addListener',R(1));a.do(R(1),'S16FaceHelp')
    a.function('S16FaceOpen',0,opened)
    def closed(a):
        a.when(T('S16FaceActive'),lambda a:None,lambda a:a.ret())
        send(a,R(2));a.set(R(1),'S16FaceActive',False)
        background(a,False)
        for name in NATIVE_CLIPS:a.set(T(name),'_visible',T('S16Visible_'+name))
        a.set(R(1),'S16ValueWire',None);a.set(R(1),'S16ValueLastFocus',None)
        a.do(R(1),'S16FacePublishValue')
        a.do(PATH('Mouse'),'removeListener',R(1));a.do(R(1),'S16FaceHelp')
    a.function('S16FaceClose',1,closed)
    def tick(a):
        a.when(T('S16PriorFrame'),lambda a:a.do(R(1),'S16PriorFrame'))
        a.set(R(1),'S16BackgroundTicks',('bin',10,T('S16BackgroundTicks'),1))
        a.when(('bin',103,T('S16BackgroundTicks'),5),lambda a:(a.set(R(1),'S16BackgroundTicks',0),a.do(ION,'SendSystemEvent','Calendar','Server16FrontendTick','tick'),a.do(R(1),'S16FacePublishValue')))
        # Opening/closing already synchronizes both background owners. Avoid
        # rewriting their visibility on every frame of a stationary list.
    a.function('S16FaceFrame',0,tick)
    def complete(a):
        a.do(R(1),'S16BaseComplete')
        a.when(EQ(T('onEnterFrame'),T('S16FaceFrame')),lambda a:None,lambda a:a.set(R(1),'S16PriorFrame',T('onEnterFrame')))
        a.set(R(1),'S16ValueWire',None);a.set(R(1),'S16ValueLastFocus',None)
        a.set(R(1),'S16BackgroundTicks',5);a.set(R(1),'onEnterFrame',T('S16FaceFrame'));send(a,'begin')
    a.function('_OnAnimateInComplete',0,complete)
    def exit(a):
        a.when(T('S16FaceActive'),lambda a:a.do(R(1),'S16FaceClose','cancel'))
        background(a,False)
        send(a,'row_hide')
        a.set(R(1),'onEnterFrame',T('S16PriorFrame'));a.set(R(1),'S16PriorFrame',None)
        a.do(R(1),'S16BaseExit')
    a.function('_OnExitScreen',0,exit)
    def event(a):
        def matches(name):return EQ(R(2),P(b.G('INPUTCODE'),name))
        def face(a):
            a.when(matches('BACK'),lambda a:(a.do(R(1),'S16FaceClose','cancel'),a.ret(True)))
            for code in ('ADVANCE','START','MENU','PAUSE'):
                a.when(matches(code),lambda a:(a.do(R(1),'S16FaceClose','confirm'),a.ret(True)))
            for code,command in [('UI_UP','up'),('UI_DOWN','down'),('PAGE_UP','page_up'),('PAGE_DOWN','page_down'),('OPTION_TOP','center')]:
                a.when(matches(code),lambda a,command=command:send(a,command))
            a.ret(True)
        a.when(T('S16FaceActive'),face)
        row=('index',T('m_RowData'),CALL(T('mcRowControl'),'getSelectedIndex'))
        a.when(matches('ADVANCE'),lambda a:(a.when(P(row,'S16Face'),lambda a:(a.do(R(1),'S16FaceOpen'),a.ret(True))),a.when(EQ(P(row,'TYPE'),P(PATH(*CLASS),'TYPE_BUTTON')),lambda a:send(a,'arm'))))
        a.when(matches('BACK'),lambda a:send(a,'abandon'))
        a.ret(CALL(R(1),'S16BaseInput',R(2),R(3)))
    a.function('_LocalEventHandler',2,event)
    def mouse(a):
        def inside(x0,y0,x1,y1):return ('bin',16,('bin',16,('bin',72,x0,T('_xmouse')),('bin',72,T('_xmouse'),x1)),('bin',16,('bin',72,y0,T('_ymouse')),('bin',72,T('_ymouse'),y1)))
        a.when(T('S16FaceActive'),lambda a:a.when(inside(49,603,394,646),lambda a:a.do(R(1),'S16FaceClose','confirm')))
    a.function('onMouseDown',0,mouse)
    def help(a):
        items=[('ADVANCE','Confirmar'),('BACK','Voltar'),('LAS_UD','Subir / descer'),('RAS_LR','Girar'),('L1R1','Zoom'),('OPTION_TOP','Centralizar')]
        a.when(T('S16FaceActive'),lambda a:a.ret(('array',tuple(CALL(PATH('ion','manager','HelpItem'),'CreateHelpTickerItem',key,label) for key,label in items))))
        a.ret(CALL(R(1),'S16BaseHelp'))
    a.function('getHelpContext',0,help)
    a.label(already);a.op(0);a.finish()
    # Redirect the original class registration, before FIFA instantiates Screen.
    const=next(e for e in big.entries.values() if e.data[:4]==b'Apt1' or e.data[:17]==b'Apt constant file')
    root=Reader(const.data,20,apt.width).ptr();r,_=apt.header(root);count=r.i();frames=r.ptr();n,table=struct.unpack_from('<I4xQ',data,frames)
    changed=False
    for i in range(n):
        at=struct.unpack_from('<Q',data,table+8*i)[0];kind=struct.unpack_from('<i',data,at)[0]
        if kind==8 and struct.unpack_from('<i',data,at+8)[0]==registration[1] and struct.unpack_from('<Q',data,at+16)[0]==registration[-1]:struct.pack_into('<Q',data,at+16,start);changed=True
    if not changed:raise ValueError('Original registration reference not found')
    output.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,output,{})
    check=Actions(AptFile(BigFile(output))).read_all()
    if check.errors:raise ValueError(check.errors)
    rows=[]
    for key,row in sorted(catalog(game).items(),key=lambda item:item[1]['name'].casefold()):
        if installed(game,row) and (game/'ModCarrerMode/data/manager_market'/row['image']).is_file():
            if any(c in row['name']+row['image'] for c in '\t\r\n'):continue
            rows.append(f'{row["assetId"]}\t{key}\t{row["name"]}\t{row["image"]}\t{row["default_club_id"]}\t{row["default_club_name"] or "Sem clube"}')
    catalog_file=Path(catalog_file);catalog_file.parent.mkdir(parents=True,exist_ok=True);catalog_file.write_bytes(('\n'.join(rows)+'\n').encode('utf8'))
    return dict(faces=len(rows),bytes=output.stat().st_size,stage=[apt.stage_width,apt.stage_height],original_fields_preserved=True,sha256=hashlib.sha256(output.read_bytes()).hexdigest())


if __name__=='__main__':
    print(json.dumps(build(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4])),ensure_ascii=True))
