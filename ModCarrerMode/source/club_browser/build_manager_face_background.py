"""Hide only FIFA's actual photograph MovieClip during the face selector."""
from pathlib import Path
import struct,sys
import build_manager_face as screen
from formats import BigFile,AptFile,Reader
from apt_actions import Actions
from build_preview import Code
b=screen.b;R=b.reg;T=b.this;P=b.prop;CALL=b.call
CLASS=('game','background','BackgroundFIFA')
OWNER='Server16ManagerFaceBackgroundOwner';BOOT_OWNER='Server16ManagerFaceBootBackgroundOwner'
ACTIVE='Server16ManagerFaceActive';SYNC='S16SyncManagerFaceBackground'

def build(source,output):
    big=BigFile(Path(source));apt=AptFile(big);actions=Actions(apt).read_all()
    if actions.errors:raise ValueError(actions.errors)
    classes=[name for name in ('BackgroundFIFA','BackgroundBootflow') if 'game.background.'+name in apt.exports]
    if len(classes)!=1:raise ValueError('Unknown native background class')
    cls=('game','background',classes[0]);proto=b.path(*cls,'prototype')
    owner=BOOT_OWNER if classes[0]=='BackgroundBootflow' else OWNER
    registration=next(row for row in apt.root_frames[0] if isinstance(row,tuple) and row[:2]==('init',apt.exports['.'.join(cls)]))
    code=actions.cache[registration[-1]]
    if b'S16FaceBackgroundInstalled\0' in apt.data:raise ValueError('Use the unmodified background backup')
    data=apt.data;data.extend(bytes(-len(data)%8));start=len(data);data.extend(data[registration[-1]:code[-1].offset])
    a=Code(data);old_class=b.CLASS;b.CLASS=cls
    try:
        done=a.uid();a.expr(P(proto,'S16FaceBackgroundInstalled'));a.branch(done)
        a.set(proto,'S16FaceBackgroundInstalled',True)
        if classes[0]=='BackgroundFIFA':a.set(proto,'S16FaceNativeLoadImage',P(proto,'LoadImage'))
        a.set(proto,'S16FaceNativeLoadComplete',P(proto,'LoadImageComplete'))
        def sync(a):
            a.set(b.GLOBAL,owner,R(1))
            def visibility(node):
                def hide(a):
                    a.when(P(node,'S16FaceHidden'),lambda a:a.when(P(node,'_visible'),lambda a:a.set(node,'S16FacePreviousVisible',True)),
                           lambda a:a.set(node,'S16FacePreviousVisible',P(node,'_visible')))
                    a.set(node,'S16FaceHidden',True);a.set(node,'_visible',False)
                def restore(a):
                    a.when(P(node,'S16FaceHidden'),lambda a:(a.set(node,'_visible',P(node,'S16FacePreviousVisible')),a.set(node,'S16FaceHidden',False)))
                a.when(b.G(ACTIVE),hide,restore)
            visibility(R(1))
            # ImageLoader owns a separately positioned native image (_z).
            # Hide the loader too, preserving its own previous visibility.
            child=T('mcImageLoader' if classes[0]=='BackgroundBootflow' else 'mcImage')
            a.when(child,lambda a:visibility(child))
        a.function(SYNC,0,sync)
        def load(a):
            a.expr(CALL(R(1),'S16FaceNativeLoadImage',R(2)));a.store(4)
            a.do(R(1),SYNC);a.ret(R(4))
        def complete(a):a.do(R(1),'S16FaceNativeLoadComplete',R(2));a.do(R(1),SYNC)
        if classes[0]=='BackgroundFIFA':a.function('LoadImage',1,load)
        a.function('LoadImageComplete',1,complete)
        a.label(done);a.op(0);a.finish()
    finally:b.CLASS=old_class
    const=next(e for e in big.entries.values() if e.data[:4]==b'Apt1' or e.data[:17]==b'Apt constant file')
    root=Reader(const.data,20,apt.width).ptr();reader,_=apt.header(root);reader.i();frames=reader.ptr();count,table=struct.unpack_from('<I4xQ',data,frames)
    matched=0
    for i in range(count):
        at=struct.unpack_from('<Q',data,table+i*8)[0]
        if struct.unpack_from('<i',data,at)[0]==8 and struct.unpack_from('<i',data,at+8)[0]==registration[1] and struct.unpack_from('<Q',data,at+16)[0]==registration[-1]:
            struct.pack_into('<Q',data,at+16,start);matched+=1
    if matched!=1:raise ValueError('Ambiguous background registration')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);b.write_big(big,output,{})
    check=AptFile(BigFile(output));decoded=Actions(check).read_all()
    if decoded.errors or check.exports!=apt.exports:raise ValueError('Invalid background extension')
    for name,entry in big.entries.items():
        if name!=apt.entry.name and bytes(check.big.entries[name].data)!=bytes(entry.original):raise ValueError('Native background resource changed')
    return output

if __name__=='__main__':print(build(Path(sys.argv[1]),Path(sys.argv[2])))
