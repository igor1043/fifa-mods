"""Extract selected L9.94 routines and their dependencies, without a DLL loader.

This is a binary function port. The original L9.65 resource remains unchanged.
No Swiss DirectInput export, initialization entry point or old patch worker is
included. The native V12 adapter supplies configuration, imports and globals.
Requires pefile and capstone only when regenerating the resource.
"""
from pathlib import Path
import argparse
import bisect
import hashlib
import json
import struct
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86_const import X86_OP_MEM, X86_REG_RIP, X86_OP_IMM

DONOR_SHA = '8c5b1322638d88075ed57ad466ee934343b4284d70b011aff3f81a78e07a6de9'
ROOTS = {
    'league_filter_optional': 0x3E90,
    'continental_optional': 0x4500,
    'career_lookup_guard': 0x4C80,
    'weekly_standings_guard': 0x5330,
    'list_unlink_guard': 0x57A0,
    'kit_carousel': 0x5BE0,
    'scoreboards_bce': 0x6930,
    'scoreboards_exe': 0xCFE0,
}
FORBIDDEN = {0x20A0, 0x24C0, 0xA4B0, 0x6D80, 0xD760}  # whole-module initializer, duplicated FCE, duplicated budget

def extract(path, output, manifest_path):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DONOR_SHA:
        raise ValueError('Only the reviewed L9.94 delivery is supported')
    pe = pefile.PE(data=raw)
    base = pe.OPTIONAL_HEADER.ImageBase
    mapped = pe.get_memory_mapped_image()
    image_size = pe.OPTIONAL_HEADER.SizeOfImage
    functions = {e.struct.BeginAddress:(e.struct.EndAddress,e.struct.UnwindData) for e in pe.DIRECTORY_ENTRY_EXCEPTION}
    starts=sorted(functions)
    text=next(s for s in pe.sections if s.Name.rstrip(b'\0')==b'.text')
    text_low,text_high=text.VirtualAddress,text.VirtualAddress+text.Misc_VirtualSize
    cs=Cs(CS_ARCH_X86,CS_MODE_64)
    cs.detail=True

    def owner(rva):
        i=bisect.bisect_right(starts,rva)-1
        if i>=0 and rva<functions[starts[i]][0]:
            return starts[i]
        # Import thunks and leaf helpers have no .pdata record.
        for ins in cs.disasm(mapped[rva:rva+256],base+rva):
            if ins.mnemonic in ('ret','jmp'):
                functions[rva]=(ins.address-base+ins.size,0)
                bisect.insort(starts,rva)
                return rva
        raise ValueError(f'Unbounded leaf dependency {rva:X}')

    selected=set()
    pending=list(ROOTS.values())
    refs=set()
    while pending:
        begin=owner(pending.pop())
        if begin in selected:
            continue
        if begin in FORBIDDEN:
            raise ValueError(f'Whole-module or duplicate worker entered closure: {begin:X}')
        selected.add(begin)
        end,_=functions[begin]
        insns=list(cs.disasm(mapped[begin:end],base+begin))
        if not insns or insns[-1].address+insns[-1].size != base+end:
            raise ValueError(f'Function decoding incomplete {begin:X}')
        for ins in insns:
            for op in ins.operands:
                target=None
                if op.type==X86_OP_MEM and op.mem.base==X86_REG_RIP:
                    target=ins.address+ins.size+op.mem.disp-base
                    refs.add(target)
                elif op.type==X86_OP_IMM and ins.mnemonic in ('call','jmp'):
                    target=op.imm-base
                if target is not None and text_low<=target<text_high:
                    pending.append(target)

    chunks=[]
    for begin in sorted(selected):
        end,_=functions[begin]
        chunks.append((begin,mapped[begin:end],1))
    # Data includes original patch descriptors, assembly templates and log
    # formats. It cannot apply any old patch without the excluded workers.
    for s in pe.sections:
        if s.Name.rstrip(b'\0') in (b'.data',b'.rdata',b'.l9tab',b'.xdata'):
            chunks.append((s.VirtualAddress,mapped[s.VirtualAddress:s.VirtualAddress+s.Misc_VirtualSize],0))
    spans=[(r,r+len(b)) for r,b,k in chunks]
    def included(rva,size=1):
        return any(a<=rva and rva+size<=b for a,b in spans)
    relocations=[]
    removed_startup_pointers=[]
    for block in pe.DIRECTORY_ENTRY_BASERELOC:
        for reloc in block.entries:
            if reloc.type==10 and included(reloc.rva,8):
                value=struct.unpack_from('<Q',mapped,reloc.rva)[0]
                if text_low<=value-base<text_high:
                    reaches_selected=any(a<=value-base<functions[a][0] for a in selected)
                    if not reaches_selected:
                        if reloc.rva in refs:
                            raise ValueError(f'Referenced data pointer reaches unselected code: {reloc.rva:X}')
                        # The copied data section also contains unused MinGW
                        # startup/finalization callbacks. Remove those pointers;
                        # the original DLL entry point is never reconstructed.
                        for i,(rva,data,kind) in enumerate(chunks):
                            if rva<=reloc.rva and reloc.rva+8<=rva+len(data):
                                data=bytearray(data)
                                struct.pack_into('<Q',data,reloc.rva-rva,0)
                                chunks[i]=(rva,bytes(data),kind)
                                break
                        removed_startup_pointers.append(reloc.rva)
                        continue
                relocations.append(reloc.rva)
            elif reloc.type not in (0,10):
                raise ValueError('Unsupported relocation kind')
    imports=[]
    for lib in pe.DIRECTORY_ENTRY_IMPORT:
        for symbol in lib.imports:
            if symbol.name is None:
                raise ValueError('Ordinal import unsupported')
            imports.append((symbol.address-base,lib.dll.decode('ascii'),symbol.name.decode('ascii')))
    unwind=[(a,functions[a][0],functions[a][1]) for a in sorted(selected) if functions[a][1]]
    # Fixed header: magic, original image base, virtual size, record counts.
    payload=bytearray(struct.pack('<8sQ5I',b'SWDELTA1',base,image_size,len(chunks),len(relocations),len(imports),len(unwind)))
    for rva,data,kind in chunks:
        payload.extend(struct.pack('<3I',rva,len(data),kind))
        payload.extend(data)
    for rva in relocations:
        payload.extend(struct.pack('<I',rva))
    for rva,lib,name in imports:
        lb,nb=lib.encode()+b'\0',name.encode()+b'\0'
        payload.extend(struct.pack('<IHH',rva,len(lb),len(nb)))
        payload.extend(lb+nb)
    for a,b,u in unwind:
        payload.extend(struct.pack('<3I',a,b,u))
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(payload)
    manifest={
        'method':'selected-machine-code-functions-added-to-original-host',
        'donor_sha256':DONOR_SHA,
        'payload_sha256':hashlib.sha256(payload).hexdigest(),
        'original_image_base':base,
        'virtual_size':image_size,
        'routines':ROOTS,
        'selected_functions':[{'begin':a,'end':functions[a][0],'unwind':functions[a][1]} for a in sorted(selected)],
        'excluded_initializer':0xA4B0,
        'excluded_duplicate_fce_worker':0x6D80,
        'excluded_duplicate_budget_worker':0xD760,
        'excluded_byte_workers_reimplemented_in_c':[0x20A0,0x24C0],
        'rip_data_references':sorted(refs),
        'chunk_count':len(chunks),
        'code_bytes':sum(len(b) for r,b,k in chunks if k),
        'data_bytes':sum(len(b) for r,b,k in chunks if not k),
        'imports':len(imports),
        'unwind_functions':len(unwind),
        'removed_unused_startup_pointers':removed_startup_pointers,
    }
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(f'Selected {len(selected)} functions, {manifest["code_bytes"]} code bytes; no donor loader/old FCE/budget worker')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('delivery',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('manifest',type=Path)
    args=p.parse_args()
    extract(args.delivery,args.output,args.manifest)

if __name__=='__main__':
    main()
