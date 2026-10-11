"""Read-only observation of Server16's documented match context chains."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import struct,sys,json,datetime
k=C.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
k.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
k.ReadProcessMemory.restype=W.BOOL
k.CloseHandle.argtypes=[W.HANDLE]
h=k.OpenProcess(0x410,False,int(sys.argv[1]))
if not h:raise C.WinError(C.get_last_error())
ps=C.WinDLL('psapi')
ps.EnumProcessModulesEx.argtypes=[W.HANDLE,C.c_void_p,W.DWORD,C.POINTER(W.DWORD),W.DWORD]
modules=(C.c_void_p*1024)();size=W.DWORD()
assert ps.EnumProcessModulesEx(h,modules,C.sizeof(modules),C.byref(size),3)
base=modules[0]
def read(addr,n):
    buf=C.create_string_buffer(n);got=C.c_size_t()
    if not addr or not k.ReadProcessMemory(h,addr,buf,n,C.byref(got)) or got.value!=n:
        raise ValueError('unreadable chain')
    return buf.raw
def ptr(addr):return struct.unpack('<Q',read(addr,8))[0]
def chain(root,offsets):
    p=ptr(base+root)
    for o in offsets[:-1]:p=ptr(p+o)
    return p+offsets[-1]
def integer(addr):return struct.unpack('<i',read(addr,4))[0]
def string(addr):return read(addr,64).split(b'\0')[0].decode('utf-8',errors='replace')
queries={
    'clock_raw':(56299464,[5500],integer),
    'stats_home':(56299464,[5484],integer),
    'stats_away':(56299464,[5488],integer),
    'page':(58757168,[232,192,136,472,0],string),
    'competition':(56170408,[504,3544,1712,80,40],integer),
    'stage':(56170408,[504,3544,1712,80,44],integer),
    'stadium_first':(55673768,[1552,80,3448,832,3068],integer),
    'stadium_alter':(55673768,[1552,80,3440,832,3068],integer),
    'stadium_name_176':(57964392,[408,48,41580],string),
    'stadium_name_261':(57964392,[296,48,51436],string),
}
result={'pid':int(sys.argv[1]),'observed_at':datetime.datetime.now().isoformat()}
try:
    for name,(root,offsets,decode) in queries.items():
        try:result[name]=decode(chain(root,offsets))
        except ValueError:result[name]=None
    try:
        rows=ptr(ptr(base+0x34a30b0)+8)
        result['pyro_score']=[integer(rows+21*16),integer(rows+6*16)]
    except ValueError:result['pyro_score']=None
finally:k.CloseHandle(h)
dest=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010\v17_teste')
dest.mkdir(exist_ok=True)
(dest/'contexto_memoria.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True,indent=2))
