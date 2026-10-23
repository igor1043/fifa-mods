"""Hide the native EA connection banner, preserving both hub implementations."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'apt_vendor'))
import build as branding
from formats import AptFile,BigFile,Placement,Reader
from apt_actions import Actions
from apt_vm import VM,Object,Native


def generate(output):
    source=HERE/'originals/easfcwidget.big'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==branding.BASELINES['easfcwidget']
    before=BigFile(source);apt=AptFile(before);actions=Actions(apt).read_all()
    assert not actions.errors
    branding.suppress_banner_first_paint(apt)
    branding.append_wrappers(apt,actions,branding.EASFC,[
        ('InitializeLayout',0,branding.easfc_body('InitializeLayout',0)),
        ('ChangeWidgetState',3,branding.easfc_body('ChangeWidgetState',3))])
    target=Path(output)/'data/ui/pow/components/easfcwidget.big'
    branding.write_big(before,target)
    after=BigFile(target);parsed=AptFile(after);checked=Actions(parsed).read_all()
    assert not checked.errors
    for name,entry in before.entries.items():
        if name!=apt.entry.name:assert after.entries[name].data==entry.original
    root=next(p for frame in parsed.root_frames for p in frame
              if isinstance(p,Placement) and p.name=='Widget')
    assert root.flags&8 and root.color>>24==0 and root.bias>>24==0
    def headers(block):
        for ins in block:
            if ins.op in (142,155):assert all(c.op!=0 for c in ins.body)
            if ins.op==142:
                reader=Reader(parsed.data,ins.offset+1,8)
                name=reader.ptr()
                assert 0<name<len(parsed.data)
                reader.string(name)
                reader.pos=(reader.pos+3)//4*4
                count=reader.i();reader.read('h');reader.read('H');params=reader.ptr()
                assert 0<params<len(parsed.data) and params+count*16<=len(parsed.data)
            if ins.body:headers(ins.body)
    for block in checked.cache.values():headers(block)
    calls=[]
    def native(name,owner,args):
        calls.append((name,tuple(args)));owner.set('_visible',True);owner.set('_alpha',100)
    class NativeGlobalVM(VM):
        def run(self,code,*args,**kwargs):
            fixed=[]
            for ins in code:
                if ins.op==88:
                    ins=copy.copy(ins);ins.op,ins.value=161,'_global'
                fixed.append(ins)
            return super().run(fixed,*args,**kwargs)
    vm=NativeGlobalVM(native)
    initializers=[b for b in checked.cache.values() if b[0].op==136]
    for block in initializers:vm.run(block,vm.global_,vm.global_)
    proto=vm.path('.'.join(branding.EASFC))
    methods=('InitializeLayout','ChangeWidgetState')
    originals=[proto.get('Server16Original'+name) for name in methods]
    for block in initializers:vm.run(block,vm.global_,vm.global_)
    assert originals==[proto.get('Server16Original'+name) for name in methods]
    for name in methods:proto.set('Server16Original'+name,Native('original.'+name))
    widget=Object({'_visible':True,'_alpha':0},prototype=proto)
    vm.invoke(proto.get('InitializeLayout'),widget,[])
    assert widget.get('_alpha')==0
    for state in (0,1,2,3,0,1):
        vm.invoke(proto.get('ChangeWidgetState'),widget,[state,True,False])
        assert widget.get('_alpha')==0
    assert len(calls)==7
    report={'passed':True,'file':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'native_resources_preserved':True,'native_callbacks_executed_once':True,
        'hidden_before_first_frame':True,'hidden_after_connection_updates':True,
        'hub_widgets_modified':False,'new_dll':False}
    (Path(output)/'hide_online_card.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    print(json.dumps(generate(parser.parse_args().output),indent=2))
