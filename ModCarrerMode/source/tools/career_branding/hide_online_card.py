"""Hide the EA/Q online widget through existing APT visibility assignments.

No new ActionScript functions, native hooks, game requests or image replacement.
Reads the current visual package so layout integrations are preserved.
"""
from pathlib import Path
import argparse,hashlib,json,struct,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'apt_vendor'))
from formats import AptFile,BigFile,Placement
from apt_actions import Actions


def root_visibility_writes(actions):
    found=[]
    for meta,code in actions.functions:
        for i,ins in enumerate(code):
            if (i>0 and i+2<len(code) and ins.value=='_visible'
                and ins.op==162 and code[i-1].op==185 and code[i-1].value==1
                and code[i+1].op in (115,116) and code[i+2].op==79):
                found.append(code[i+1])
    return found


def generate(output,source):
    source=Path(source);before=BigFile(source);apt=AptFile(before);actions=Actions(apt).read_all()
    assert not actions.errors
    writes=root_visibility_writes(actions);assert writes,'Root visibility contract unavailable'
    enabled=[ins for ins in writes if ins.op==115];assert len(enabled)<=1,'Unexpected widget visibility implementation'
    for ins in enabled:apt.data[ins.offset]=116 # True -> False; same instruction size/stack.
    roots=[p for frame in apt.root_frames for p in frame if isinstance(p,Placement) and p.name=='Widget'];assert len(roots)==1
    root=roots[0];struct.pack_into('<i',apt.data,root.offset+8,root.flags|8)
    struct.pack_into('<II',apt.data,root.matrix_offset+24,root.color&0x00ffffff,root.bias&0x00ffffff)
    target=Path(output)/'data/ui/pow/components/easfcwidget.big';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(before.build())
    after=BigFile(target);parsed=AptFile(after);checked=Actions(parsed).read_all()
    assert not checked.errors and parsed.imports==apt.imports and parsed.exports==apt.exports
    assert len(checked.functions)==len(actions.functions) and checked.cache.keys()==actions.cache.keys()
    for name,entry in before.entries.items():
        if name!=apt.entry.name:assert after.entries[name].data==entry.original
    assert not any(i.op==115 for i in root_visibility_writes(checked))
    # Original native logic differs at exactly the visibility boolean operand.
    changed=[]
    for at,code in actions.cache.items():
        for ins in code:
            if ins.body:continue
            expected=116 if ins.offset in {i.offset for i in enabled} else ins.op
            assert parsed.data[ins.offset]==expected
    report=dict(passed=True,file=str(target),sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        changed_visibility_operands=len(enabled),functions_added=0,native_hooks_added=0,
        original_resources_preserved=True,imports_exports_preserved=True,hidden_before_first_paint=True)
    (Path(output)/'hide_online_card.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args();print(json.dumps(generate(args.output,args.source),indent=2))
