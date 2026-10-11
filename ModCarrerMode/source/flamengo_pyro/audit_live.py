import ctypes as C, ctypes.wintypes as W, struct, json, sys
from pathlib import Path
k=C.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)];k.ReadProcessMemory.restype=W.BOOL
k.CloseHandle.argtypes=[W.HANDLE]
pid=int(sys.argv[1]); h=k.OpenProcess(0x410,False,pid)
if not h:raise C.WinError(C.get_last_error())
p=C.WinDLL('psapi',use_last_error=True)
p.EnumProcessModulesEx.argtypes=[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),W.DWORD]
mods=(C.c_void_p*1024)();needed=W.DWORD()
assert p.EnumProcessModulesEx(h,mods,C.sizeof(mods),C.byref(needed),3)
base=mods[0]
def read(a,n):
    buf=C.create_string_buffer(n);got=C.c_size_t()
    if not k.ReadProcessMemory(h,a,buf,n,C.byref(got)) or got.value!=n:raise ValueError(hex(a))
    return buf.raw
def ptr(a):return struct.unpack('<Q',read(a,8))[0]
import re
header=(Path(__file__).parent/'native_signatures.h').read_text()
signatures=re.findall(r'sig\d+\[16\]=\{([^}]+)\}',header)
rvas=re.findall(r'get\(base\+0x([0-9a-f]+),found\)',header)
pe=struct.unpack('<I',read(base+60,4))[0]
checks=[]
for rva,sig in zip(rvas,signatures):
    expected=bytes(int(x,16) for x in sig.split(','));actual=read(base+int(rva,16),16)
    checks.append({'rva':rva,'match':expected==actual,'actual':actual.hex(),'expected':expected.hex()})
result={'pid':pid,'base':hex(base),'timestamp':hex(struct.unpack('<I',read(base+pe+8,4))[0]),'checks':checks,'batch_draw':hex(ptr(base+0x2214520)-base),'particles':[]}
try:
    manager=ptr(base+0x3517420);world=ptr(manager+8);game=ptr(world+0x10);registry=ptr(game+0x20)
    pairs=ptr(registry+8+15*32+24);count=struct.unpack('<i',read(registry+8+15*32+16,4))[0]
    match={'managerVt':hex(ptr(manager)-base),'worldVt':hex(ptr(world)-base),'gameVt':hex(ptr(game)-base),'count':count,'teams':[]}
    for i in range(min(count,2)):
        team=ptr(pairs+i*16+8);stats=ptr(team+0x50)
        match['teams'].append({'vt':hex(ptr(team)-base),'ownerCorrect':ptr(team+0x30)==registry,'side':struct.unpack('<i',read(team+0x58,4))[0],'club':struct.unpack('<i',read(stats+0x80,4))[0]})
    cache=ptr(base+0x34a30b0);rows=ptr(cache+8)
    match.update({'cacheVt':hex(ptr(cache)-base),'homeCallback':hex(ptr(rows+21*16+8)-base),'awayCallback':hex(ptr(rows+6*16+8)-base),'home':struct.unpack('<i',read(rows+21*16,4))[0],'away':struct.unpack('<i',read(rows+6*16,4))[0]})
    result['match']=match
except ValueError as e:result['matchError']=str(e)
for i in range(32):
    obj=ptr(base+0x3504500+i*8)
    if not obj:continue
    try:
        s=ptr(obj+16);m=ptr(s+0x58)
        row={'index':i,'vtable':hex(ptr(obj)-base),'stateIndex':struct.unpack('<i',read(s,4))[0],'name':read(s+8,32).split(b'\0')[0].decode(errors='replace'),'dependent':read(s+0x28,1)[0],'ready':read(s+5,1)[0],'populated':read(s+7,1)[0],'invisible':read(s+4,1)[0],'managerEffect':hex(ptr(m+16)),'instances':list(struct.unpack('<100i',read(s+0x60,400)))}
        if i==31 and row['instances'][0]!=-1:
            node=ptr(m+0x30);seen=set();found=[]
            def visit(n):
                if not n or n in seen or len(seen)>200:return
                seen.add(n);visit(ptr(n));visit(ptr(n+8))
                instance=ptr(n+0x28);data=read(instance,0x300)
                idx=struct.unpack_from('<i',read(n+0x20,4))[0]
                if idx<2:
                    Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010',f'v3_instance_{idx}.bin').write_bytes(data)
                    found.append({'handle':idx,'address':hex(instance),'matrix':struct.unpack_from('<16f',data,0x10),'clock':struct.unpack_from('<4i',data,0x27c),'position':struct.unpack_from('<4f',data,0x90)})
            visit(node);row['instanceDetails']=found
        result['particles'].append(row)
    except ValueError as e:result['particles'].append({'index':i,'unreadable':str(e)})
k.CloseHandle(h)
out=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010')/'v2_live_audit.json'
out.write_text(json.dumps(result,indent=2))
print(json.dumps({'pid':pid,'batch_draw':result['batch_draw'],'match':result.get('match',result.get('matchError')),'particles':[{**row,'instances':[x for x in row.get('instances',[]) if x!=-1]} for row in result['particles'] if row.get('index')==31]},indent=2))
