"""Append the existing Server16 Start shortcut to FIFA's pre-match help."""
from pathlib import Path
import os,struct,sys

CLASS=('game','screens','playNow','KickOffHub')


def build(game,source,target):
    game=Path(game);root=game/'ModCarrerMode/source/club_environment'
    sys.path.insert(0,str(root.parent))
    os.environ['SERVER16_GAME_ROOT']=str(game)
    for part in ('vendor','bank','preview',''):
        sys.path.insert(0,str(root/part))
    from formats import AptFile,BigFile,Reader
    from apt_actions import Actions
    import build_screen as b
    from build_preview import Code
    big=BigFile(source);apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    if b'S16PrematchFooterInstalled\0' in apt.data:return Path(source).read_bytes()
    registration=next(c for c in apt.root_frames[0] if isinstance(c,tuple)
        and c[0]=='init' and c[1]==apt.exports['__Packages.'+'.'.join(CLASS)])
    original=actions.cache[registration[-1]];assert original[-1].op==0
    data=apt.data;data.extend(bytes(-len(data)%8));start=len(data)
    data.extend(data[registration[-1]:original[-1].offset]);a=Code(data)
    proto=b.path(*CLASS,'prototype');done=a.uid()
    a.expr(b.prop(proto,'S16PrematchFooterInstalled'));a.branch(done)
    a.set(proto,'S16PrematchFooterInstalled',True)
    a.set(proto,'S16OriginalPrematchHelp',b.prop(proto,'getHelpContext'))
    previous_class,previous_full=b.CLASS,b.FULL
    b.CLASS=CLASS;b.FULL='.'.join(CLASS)
    def help_context(a):
        a.expr(b.call(b.reg(1),'S16OriginalPrematchHelp'));a.op(135);a.align();a.data.extend(struct.pack('<i',2));a.op(23)
        a.do(b.reg(2),'push',b.call(b.path('ion','manager','HelpItem'),'CreateHelpTickerItem','START','Server16'))
        a.ret(b.reg(2))
    try:a.function('getHelpContext',0,help_context)
    finally:b.CLASS=previous_class;b.FULL=previous_full
    a.label(done);a.op(0);a.finish()
    const=next(e for e in big.entries.values() if e.data[:4]==b'Apt1' or e.data[:17]==b'Apt constant file')
    root=Reader(const.data,20,apt.width).ptr();reader,_=apt.header(root);reader.i();frames=reader.ptr()
    count,table=struct.unpack_from('<I4xQ',data,frames);found=False
    for i in range(count):
        at=struct.unpack_from('<Q',data,table+8*i)[0]
        if struct.unpack_from('<i',data,at)[0]==8 and struct.unpack_from('<i',data,at+8)[0]==registration[1] and struct.unpack_from('<Q',data,at+16)[0]==registration[-1]:
            struct.pack_into('<Q',data,at+16,start);found=True
    assert found
    target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
    from server16_py.scoreboard_options_ui import write_native_big
    write_native_big(big,target)
    check=AptFile(BigFile(target));assert not Actions(check).read_all().errors
    assert check.exports==apt.exports and check.imports==apt.imports
    assert all(bytes(check.big.entries[name].data)==bytes(entry.data) for name,entry in big.entries.items())
    return target.read_bytes()
