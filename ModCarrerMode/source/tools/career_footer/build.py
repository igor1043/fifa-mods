"""Compose career hub callouts without changing input handlers or providers."""
from pathlib import Path
import argparse,hashlib,json,os,struct,sys

HERE=Path(__file__).resolve().parent
ENV=HERE.parents[1]/'club_environment'
sys.path[:0]=[str(ENV/'vendor'),str(ENV/'preview'),str(ENV/'bank'),str(ENV),str(ENV.parent)]
from formats import AptFile,BigFile,chunk_wrap
from apt_actions import Actions
import build_screen as b
from build_preview import Code

CLASS=('game','screens','fluxHub','FluxHub');PROTO=b.path(*CLASS,'prototype')
HELPER=b.path('game','fluxHelpers','CareerHubDataHelper','prototype')
R=b.reg;P=b.prop;T=b.this;CALL=b.call;EQ=b.equal
ARRAY=lambda *items:('array',items)
OR=lambda a,c:('bin',17,a,c)
AND=lambda a,c:('bin',16,a,c)
IDX=lambda o,i:('index',o,i)
OLD='Server16CareerFooterOriginal';FLAG='Server16CareerFooterInstalled'
ANIMATE='Server16CareerFooterAnimateOriginal';EXIT='Server16CareerFooterExitOriginal'
REVISION='Server16CareerFooterRevision9'
REFRESH=('LoadComponents','UpdateButtonData','NavigatorHighlightCallback','NavigatorHelperChangedCallback','SetFocus')
HUB_COMMANDS=(('ADVANCE','Selecionar'),('BACK','Voltar'),('OPTION_LEFT','Salvar'),
              ('OPTION_TOP','Caixa de e-mails'),('L2R2','Abas'),('LAS','Navegar'),
              ('RAS_LR','Páginas dos cards'),('START','Select + Start · Server16'))


def career_hub(a):
    # ProcessData may have been copied to an existing instance before a
    # scouting wrapper replaced the prototype. The owned XML components are
    # a stable identity; do not depend on function pointer equality alone.
    a.when(T('Server16CareerFooterScope'),lambda a:a.ret(True))
    a.when(P(T('mcFluxNavigator'),'GetDataHelper'),lambda a:register(a,2,CALL(T('mcFluxNavigator'),'GetDataHelper')))
    a.when(AND(R(2),AND(P(R(2),'constructor'),EQ(P(R(2),'constructor'),b.path('game','fluxHelpers','CareerHubDataHelper')))),lambda a:a.ret(True))
    a.when(AND(R(2),AND(P(HELPER,'ProcessData'),EQ(P(R(2),'ProcessData'),P(HELPER,'ProcessData')))),lambda a:a.ret(True))
    # LoadComponents receives the actual XML component list for this hub.
    register(a,3,0);loop,done=a.uid(),a.uid();a.label(loop)
    a.expr(AND(('bin',72,R(3),P(T('m_arrComponentData'),'length')),('bin',72,R(3),32)));a.op(18);a.branch(done)
    item=IDX(T('m_arrComponentData'),R(3));path=P(item,'PATH')
    for name in ('game/components/CareerComponents/CareerHubWidget.swf',
                 'data/ui/game/components/CareerComponents/CareerHubWidget.swf'):
        a.when(EQ(path,name),lambda a:a.ret(True))
    a.when(path,lambda a:a.when(('bin',103,CALL(CALL(path,'toLowerCase'),'indexOf','careerhubwidget'),-1),lambda a:a.ret(True)))
    register(a,3,('bin',71,R(3),1));a.branch(loop,False);a.label(done);a.ret(False)


def bind_help(a):
    a.do(R(1),ANIMATE)
    a.when(EQ(T('onEnterFrame'),T('Server16FrontendFrame')),lambda a:None,lambda a:(a.set(R(1),'Server16FrontendOriginalFrame',T('onEnterFrame')),a.set(R(1),'onEnterFrame',T('Server16FrontendFrame'))))
    a.set(R(1),'Server16FrontendFrames',0)
    # The native helper/components can arrive after AnimateInComplete.
    # Retain this hub's lifetime and recheck scope after provider callbacks.
    a.set(R(1),'Server16CareerFooterActive',True)
    a.when(CALL(R(1),'Server16IsCareerHub'),lambda a:None,lambda a:(a.set(b.GLOBAL,'Server16ActiveCareerClubId',None),a.set(b.GLOBAL,'Server16ActiveCareerClubName',None),a.ret()))
    a.set(b.GLOBAL,'Server16CareerFooterOwner',R(1))
    a.do(R(1),'Server16RefreshCareerHelp')


def refresh_help(a):
    a.when(AND(T('Server16CareerFooterActive'),CALL(R(1),'Server16IsCareerHub')),lambda a:None,lambda a:a.ret())
    a.set(R(1),'Server16CareerFooterScope',True)
    a.set(b.GLOBAL,'Server16CareerFooterOwner',R(1))
    a.do(R(1),'Server16CaptureCareerClub')
    # A custom view may have owned HelpManager immediately before this hub.
    # Explicitly claim our contextual delegate when this hub becomes active.
    a.when(T('Server16CareerFooterDelegate'),lambda a:None,lambda a:a.set(R(1),'Server16CareerFooterDelegate',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext'))))
    a.do(b.MANAGER('HelpManager'),'SetCustomSource',T('Server16CareerFooterDelegate'))
    a.do(b.MANAGER('HelpManager'),'Update');a.do(b.MANAGER('HelpManager'),'Show')


def frontend_frame(a):
    # The native UI event is independent of FCE updates, which may stop when
    # Career closes. Preserve the original frame callback and throttle the
    # pulse; the C bridge verifies page lifetime and the factory owner thread.
    a.when(T('Server16FrontendOriginalFrame'),lambda a:a.do(R(1),'Server16FrontendOriginalFrame'))
    a.set(R(1),'Server16FrontendFrames',('bin',71,T('Server16FrontendFrames'),1))
    a.when(('bin',72,T('Server16FrontendFrames'),15),lambda a:a.ret())
    a.set(R(1),'Server16FrontendFrames',0)
    a.when(P(b.ION,'SendSystemEvent'),lambda a:a.do(b.ION,'SendSystemEvent','Calendar','Server16FrontendTick','tick'))
    # A provider can install its own source after UpdateButtonData. Recover
    # the footer only on the still-active, unlocked hub and leave modals alone.
    manager=b.MANAGER('HelpManager')
    a.when(AND(T('Server16CareerFooterActive'),AND(T('m_isAnimatedIn'),('not',T('m_bLockNavigation')))),
           lambda a:a.when(AND(('not',P(P(manager,'m_arrCustomSourceStack'),'length')),
                               ('not',EQ(P(manager,'m_cbCustomSource'),T('Server16CareerFooterDelegate')))),
                           lambda a:a.do(R(1),'Server16RefreshCareerHelp')))


def unbind_help(a):
    a.set(R(1),'Server16CareerFooterActive',False)
    a.set(R(1),'Server16CareerFooterScope',False)
    a.when(EQ(b.G('Server16CareerFooterOwner'),R(1)),lambda a:a.set(b.GLOBAL,'Server16CareerFooterOwner',None))
    a.when(EQ(T('onEnterFrame'),T('Server16FrontendFrame')),lambda a:a.set(R(1),'onEnterFrame',T('Server16FrontendOriginalFrame')))
    a.set(R(1),'Server16FrontendOriginalFrame',None)
    manager=b.MANAGER('HelpManager')
    a.when(AND(T('Server16CareerFooterDelegate'),EQ(P(manager,'m_cbCustomSource'),T('Server16CareerFooterDelegate'))),lambda a:a.do(manager,'SetCustomSource',None))
    a.set(R(1),'Server16CareerFooterDelegate',None);a.ret(CALL(R(1),EXIT))


def capture_club(a):
    source=P(b.G('Server16CareerBrandOwner'),'m_objData')
    club=P(source,'ASSET_ID')
    a.when(('bin',103,club,0),lambda a:(a.set(b.GLOBAL,'Server16ActiveCareerClubId',club),a.set(b.GLOBAL,'Server16ActiveCareerClubName',P(source,'TEAM_NAME'))))


def register(a,index,value):
    a.expr(value);a.store(index)


def write_big(big,path):
    entries=[(name,bytes(e.data) if e.data!=e.original else big.original[e.offset:e.offset+e.length]) for name,e in big.entries.items()]
    header=16+sum(9+len(name.encode('latin1')) for name,_ in entries)
    offset=(header+63)//64*64;directory=bytearray();payload=bytearray(offset-header)
    for name,blob in entries:
        pad=-offset%64;payload.extend(bytes(pad));offset+=pad
        directory.extend(struct.pack('>II',offset,len(blob))+name.encode('latin1')+b'\0');payload.extend(blob);offset+=len(blob)
    content=b'BIGF'+struct.pack('<I',offset)+struct.pack('>II',len(entries),header)+directory+payload
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(chunk_wrap(content,big.wrapper) if big.wrapper else content)


def tile_help(a):
    # Long news can replace HelpManager's source, including when the user is
    # on another card. Inspect the navigator's current panel, not its focus.
    register(a,4,P(T('mcFluxNavigator'),'m_arrTiles'))
    register(a,5,0)
    panel_loop,panel_done=a.uid(),a.uid();a.label(panel_loop)
    a.expr(AND(('bin',72,R(5),P(R(4),'length')),('bin',72,R(5),32)));a.op(18);a.branch(panel_done)
    register(a,2,IDX(R(4),R(5)))
    register(a,3,0);loop,done=a.uid(),a.uid();a.label(loop)
    a.expr(AND(R(2),('bin',72,R(3),8)));a.op(18);a.branch(done)
    def news_help(a):
        # Native updateBodyLarge installs its own help delegate on each news
        # update. Compose that delegate too, otherwise its next timer tick
        # replaces the hub commands with only the news-scroll action again.
        a.when(P(R(2),'Server16CareerNewsHelpOriginal'),lambda a:None,lambda a:(
            a.set(R(2),'Server16CareerNewsHelpOriginal',P(R(2),'GetCustomHelpContext')),
            a.set(R(2),'GetCustomHelpContext',T('Server16NewsHelpContext'))))
        register(a,6,IDX(CALL(R(2),'Server16CareerNewsHelpOriginal'),0))
        a.when(AND(('not',T('Server16FooterNewsAdded')),R(6)),lambda a:(
            a.do(T('Server16FooterItems'),'push',R(6)),
            a.set(R(1),'Server16FooterNewsAdded',True)))
    a.when(AND(P(R(2),'GetCustomHelpContext'),P(R(2),'m_isNeedAScroll')),news_help)
    register(a,2,P(R(2),'m_oCurrentSubtile'))
    register(a,3,('bin',71,R(3),1));a.branch(loop,False);a.label(done)
    register(a,5,('bin',71,R(5),1));a.branch(panel_loop,False);a.label(panel_done)


def news_help_context(a):
    # Invoked with the news tile as 'this', including native interval callbacks.
    register(a,2,b.G('Server16CareerFooterOwner'))
    a.when(AND(P(R(2),'Server16CareerFooterActive'),CALL(R(2),'Server16IsCareerHub')),
           lambda a:a.ret(CALL(R(2),'getHelpContext')))
    a.ret(CALL(R(1),'Server16CareerNewsHelpOriginal'))


def help_context(a):
    # Retain native behavior in main menu, tournaments, FUT and every other hub.
    # ProcessData is specific to this helper (and may include our scouting
    # carousel wrapper). GetHelpContext can be inherited by unrelated hubs.
    own=CALL(R(1),'Server16IsCareerHub')
    a.when(own,lambda a:None,lambda a:a.ret(CALL(R(1),OLD)))
    a.do(R(1),'Server16CaptureCareerClub')
    a.when(T('m_isAnimatedIn'),lambda a:None,lambda a:a.ret(ARRAY()))
    # The hub owns one complete legend. Native providers continue to own
    # action dispatch, but their parallel legends must not be concatenated.
    items=[CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem',icon,label)
           for icon,label in HUB_COMMANDS]
    a.set(R(1),'Server16FooterItems',ARRAY(*items))
    a.set(R(1),'Server16FooterNewsAdded',False)
    a.do(R(1),'Server16AppendTileHelp')
    a.do(T('Server16FooterItems'),'sort',P(b.MANAGER('HelpManager'),'CompareHelpItemsOrder'))
    a.ret(T('Server16FooterItems'))


def generate(source,destination):
    source,destination=Path(source),Path(destination)
    big=BigFile(source);apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    start,block=next((s,c) for s,c in actions.cache.items() if c[0].op==136 and any(i.value=='FluxHub' for i in c))
    active_start=start
    values=[i.value for i in block if isinstance(i.value,str)]
    if REVISION in values:raise ValueError('This footer revision is already installed.')
    if FLAG in values:
        # Earlier revisions retain the untouched native initializer and method
        # bodies. Upgrade that initializer, without stacking recursive wrappers
        # or rolling back any other movie resource, import or native handler.
        candidates=[]
        for offset in range(0,start,8):
            if apt.data[offset]!=136:continue
            try:original=actions.decode(offset)
            except (ValueError,IndexError,struct.error):continue
            names=[i.value for i in original if isinstance(i.value,str)]
            if 'FluxHub' in names and FLAG not in names and any(i.op==142 for i in original):
                candidates.append((offset,original))
        if len(candidates)!=1:raise ValueError('Cannot identify the preserved native career hub initializer.')
        start,block=candidates[0]
    methods={block[i-1].value:i for i in range(1,len(block)) if block[i].op==142}
    assert 'getHelpContext' in methods and 'LocalEventHandler' in methods and block[-1].op==0
    old=b.CLASS;b.CLASS=CLASS
    try:
        data=apt.data;a=Code(data);a.align();new_start=len(data)
        data.extend(apt.entry.original[start:block[0].end])
        # The existing class initializer executes exactly once; an APT reload
        # must not capture our own wrapper as the original native function.
        skip=a.uid()
        a.when(P(PROTO,REVISION),lambda a:a.branch(skip,False))
        while len(data)%8:a.op(89);a.op(23)
        data.extend(apt.entry.original[block[0].end:block[-1].offset])
        a.set(PROTO,OLD,P(PROTO,'getHelpContext'))
        a.set(PROTO,ANIMATE,P(PROTO,'AnimateInComplete'));a.set(PROTO,EXIT,P(PROTO,'OnExitScreen'))
        for name in REFRESH:a.set(PROTO,'Server16FooterOriginal'+name,P(PROTO,name))
        a.function('Server16IsCareerHub',0,career_hub)
        a.function('Server16FrontendFrame',0,frontend_frame)
        a.function('Server16CaptureCareerClub',0,capture_club)
        a.function('Server16RefreshCareerHelp',0,refresh_help)
        a.function('Server16AppendTileHelp',0,tile_help)
        a.function('Server16NewsHelpContext',0,news_help_context)
        a.function('getHelpContext',0,help_context)
        a.function('AnimateInComplete',0,bind_help);a.function('OnExitScreen',0,unbind_help)
        for name in REFRESH:
            def context_changed(a,name=name):
                a.do(R(1),'Server16FooterOriginal'+name,R(2))
                # Components and providers arrive asynchronously after animate-in.
                # Reclaim the hub context after they publish, including on return
                # from a custom career view. Never replace native input handlers.
                a.do(R(1),'Server16RefreshCareerHelp')
            a.function(name,1,context_changed)
        a.set(PROTO,REVISION,True);a.set(PROTO,FLAG,True);a.label(skip);a.op(0);a.finish()
    finally:b.CLASS=old
    references=[at for at in range(0,len(apt.entry.original)-7,8) if apt.entry.original[at:at+8]==struct.pack('<Q',active_start)]
    assert len(references)==1,references
    struct.pack_into('<Q',data,references[0],new_start)
    write_big(big,destination)
    result=AptFile(BigFile(destination));checked=Actions(result).read_all()
    assert not checked.errors and result.imports==apt.imports and result.exports==apt.exports
    for name,entry in big.entries.items():
        if name!=apt.entry.name:assert result.big.entries[name].data==entry.original
    report=dict(source=str(source),file=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                native_handlers_preserved=True,imports_exports_preserved=True,footer_scope='CareerHubDataHelper',
                resources_preserved=True,new_methods=14,contextual_carousel=True,news_scroll_native=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(json.dumps(generate(args.source,args.output),indent=2))
