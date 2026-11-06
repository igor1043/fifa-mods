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


def career_hub(a):
    # ProcessData may have been copied to an existing instance before a
    # scouting wrapper replaced the prototype. The owned XML components are
    # a stable identity; do not depend on function pointer equality alone.
    helper=CALL(T('mcFluxNavigator'),'GetDataHelper')
    a.when(AND(P(HELPER,'ProcessData'),EQ(P(helper,'ProcessData'),P(HELPER,'ProcessData'))),lambda a:a.ret(True))
    a.when(b.G('Server16CareerBrandOwner'),lambda a:a.ret(True))
    register(a,3,0);loop,done=a.uid(),a.uid();a.label(loop)
    a.expr(AND(('bin',72,R(3),P(T('m_arrComponentData'),'length')),('bin',72,R(3),32)));a.op(18);a.branch(done)
    item=IDX(T('m_arrComponentData'),R(3));path=P(item,'PATH')
    a.when(OR(EQ(path,'game/components/CareerComponents/CareerHubWidget.swf'),EQ(path,'game/components/careercomponents/careerhubwidget.swf')),lambda a:a.ret(True))
    register(a,3,('bin',71,R(3),1));a.branch(loop,False);a.label(done);a.ret(False)


def bind_help(a):
    a.do(R(1),ANIMATE)
    a.when(CALL(R(1),'Server16IsCareerHub'),lambda a:None,lambda a:(a.set(b.GLOBAL,'Server16ActiveCareerClubId',None),a.set(b.GLOBAL,'Server16ActiveCareerClubName',None),a.ret()))
    a.do(R(1),'Server16CaptureCareerClub')
    # A custom view may have owned HelpManager immediately before this hub.
    # Explicitly claim our contextual delegate when this hub becomes active.
    a.set(R(1),'Server16CareerFooterDelegate',CALL(b.path('cafe','utility','Delegate'),'Create',R(1),T('getHelpContext')))
    a.do(b.MANAGER('HelpManager'),'SetCustomSource',T('Server16CareerFooterDelegate'))
    a.do(b.MANAGER('HelpManager'),'Update');a.do(b.MANAGER('HelpManager'),'Show')


def unbind_help(a):
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


def append_items(a):
    # Parameters are source; R1 is the hub; scratch registers are local to
    # this call so helper/nav loops cannot overwrite the caller's iteration.
    a.when(R(2),lambda a:None,lambda a:a.ret())
    register(a,3,0);loop,done=a.uid(),a.uid();a.label(loop)
    a.expr(('bin',72,R(3),P(R(2),'length')));a.op(18);a.branch(done)
    register(a,4,IDX(R(2),R(3)))
    def item(a):
        register(a,5,False);register(a,6,0)
        scan,end=a.uid(),a.uid();a.label(scan)
        a.expr(('bin',72,R(6),P(T('Server16FooterItems'),'length')));a.op(18);a.branch(end)
        current=IDX(T('Server16FooterItems'),R(6))
        same=OR(EQ(current,R(4)),AND(P(R(4),'icon'),EQ(P(current,'icon'),P(R(4),'icon'))))
        a.when(same,lambda a:register(a,5,True))
        register(a,6,('bin',71,R(6),1));a.branch(scan,False);a.label(end)
        a.when(('not',R(5)),lambda a:a.do(T('Server16FooterItems'),'push',R(4)))
    a.when(R(4),item)
    register(a,3,('bin',71,R(3),1));a.branch(loop,False);a.label(done)


def help_context(a):
    # Retain native behavior in main menu, tournaments, FUT and every other hub.
    register(a,3,CALL(T('mcFluxNavigator'),'GetDataHelper'))
    # ProcessData is specific to this helper (and may include our scouting
    # carousel wrapper). GetHelpContext can be inherited by unrelated hubs.
    own=CALL(R(1),'Server16IsCareerHub')
    a.when(own,lambda a:None,lambda a:a.ret(CALL(R(1),OLD)))
    a.do(R(1),'Server16CaptureCareerClub')
    a.when(T('m_isAnimatedIn'),lambda a:None,lambda a:a.ret(ARRAY()))
    # When the game locks navigation (advance calendar/dialog), use its exact
    # contextual help, not stale Save/Back callouts from the previous idle state.
    a.when(T('m_bLockNavigation'),lambda a:a.ret(CALL(R(1),OLD)))
    a.set(R(1),'Server16FooterItems',ARRAY())
    a.do(R(1),'Server16AppendHubHelp',T('m_arrHubHelpItems'))
    a.do(R(1),'Server16AppendHubHelp',CALL(R(3),'GetHelpContext'))
    a.do(R(1),'Server16AppendHubHelp',CALL(T('mcFluxNavigator'),'GetHelpContext'))
    # The advance-calendar tile returns an empty help list. The hub's native
    # ADVANCE handler still selects whichever actionable tile has focus.
    # This zero-argument wrapper has no preloaded global in R2. Native
    # UpdateButtonData uses flags 297, but our generated method uses 41.
    # Address the actual global so localization cannot abort all callouts.
    for icon,key in (('ADVANCE','Select'),('BACK','Back'),('OPTION_LEFT','CM_Settings_Save'),('OPTION_TOP','CM_Hub_Callout_Inbox')):
        # These three hub actions are declared in careermanagerhubcfg.xml for
        # every tab. Restore their descriptions when a temporary native DP
        # publishes only Back; retain any richer provider label already added.
        item=CALL(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem',icon,CALL(b.GLOBAL,'ltxt',key))
        a.do(R(1),'Server16AppendHubHelp',ARRAY(item))
    a.do(T('Server16FooterItems'),'sort',P(b.MANAGER('HelpManager'),'CompareHelpItemsOrder'))
    a.ret(T('Server16FooterItems'))


def generate(source,destination):
    source,destination=Path(source),Path(destination)
    big=BigFile(source);apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    if FLAG in actions.constants or FLAG.encode() in apt.data:raise ValueError('Footer already patched; use rollback baseline')
    start,block=next((s,c) for s,c in actions.cache.items() if c[0].op==136 and any(i.value=='FluxHub' for i in c))
    methods={block[i-1].value:i for i in range(1,len(block)) if block[i].op==142}
    assert 'getHelpContext' in methods and 'LocalEventHandler' in methods and block[-1].op==0
    old=b.CLASS;b.CLASS=CLASS
    try:
        data=apt.data;a=Code(data);a.align();new_start=len(data)
        data.extend(apt.entry.original[start:block[0].end])
        # The existing class initializer executes exactly once; an APT reload
        # must not capture our own wrapper as the original native function.
        skip=a.uid()
        a.when(P(PROTO,FLAG),lambda a:a.branch(skip,False))
        while len(data)%8:a.op(89);a.op(23)
        data.extend(apt.entry.original[block[0].end:block[-1].offset])
        a.set(PROTO,OLD,P(PROTO,'getHelpContext'))
        a.set(PROTO,ANIMATE,P(PROTO,'AnimateInComplete'));a.set(PROTO,EXIT,P(PROTO,'OnExitScreen'))
        a.function('Server16IsCareerHub',0,career_hub)
        a.function('Server16CaptureCareerClub',0,capture_club)
        a.function('Server16AppendHubHelp',1,append_items)
        a.function('getHelpContext',0,help_context)
        a.function('AnimateInComplete',0,bind_help);a.function('OnExitScreen',0,unbind_help)
        a.set(PROTO,FLAG,True);a.label(skip);a.op(0);a.finish()
    finally:b.CLASS=old
    references=[at for at in range(0,len(apt.entry.original)-7,8) if apt.entry.original[at:at+8]==struct.pack('<Q',start)]
    assert len(references)==1,references
    struct.pack_into('<Q',data,references[0],new_start)
    write_big(big,destination)
    result=AptFile(BigFile(destination));checked=Actions(result).read_all()
    assert not checked.errors and result.imports==apt.imports and result.exports==apt.exports
    for name,entry in big.entries.items():
        if name!=apt.entry.name:assert result.big.entries[name].data==entry.original
    report=dict(source=str(source),file=str(destination),sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                native_handlers_preserved=True,imports_exports_preserved=True,footer_scope='CareerHubDataHelper',
                resources_preserved=True,new_methods=6)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();print(json.dumps(generate(args.source,args.output),indent=2))
