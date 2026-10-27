"""Load one purpose-built helper into the verified FIFA process, with no UI access."""
import ctypes
from ctypes import wintypes as w
from pathlib import Path
import sys, struct, json, pefile
from live_process import K, modules

def main():
    pid=int(sys.argv[1]);dll=Path(sys.argv[2]).resolve();export=sys.argv[3]
    handle=K.OpenProcess(0x43a,False,pid)
    assert handle,ctypes.get_last_error()
    def read(address,size):
        data=ctypes.create_string_buffer(size);got=ctypes.c_size_t()
        assert K.ReadProcessMemory(handle,address,data,size,ctypes.byref(got)) and got.value==size
        return data.raw
    def call(address,payload=None):
        remote=None
        if payload:
            remote=K.VirtualAllocEx(handle,None,len(payload),0x3000,4);assert remote
            data=ctypes.create_string_buffer(payload);got=ctypes.c_size_t()
            assert K.WriteProcessMemory(handle,remote,data,len(payload),ctypes.byref(got)) and got.value==len(payload)
        thread=K.CreateRemoteThread(handle,None,0,address,remote,0,None);assert thread
        assert K.WaitForSingleObject(thread,5000)==0,'Helper pending; do not retry blindly'
        result=w.DWORD();assert K.GetExitCodeThread(thread,ctypes.byref(result))
        K.CloseHandle(thread)
        if remote:assert K.VirtualFreeEx(handle,remote,0,0x8000)
        return result.value
    path=ctypes.create_unicode_buffer(1024);length=w.DWORD(1024)
    assert K.QueryFullProcessImageNameW(handle,0,path,ctypes.byref(length))
    assert path.value.lower()==r'U:\fifa 16\fifa16.exe'.lower()
    active=modules(pid);base=active['fifa16.exe']['base']
    nt=read(base+struct.unpack_from('<I',read(base,64),60)[0],24)
    assert nt[:4]==b'PE\0\0' and struct.unpack_from('<I',nt,8)[0]==0x577de45c
    parsed=pefile.PE(str(dll));exports={e.name.decode():e.address for e in parsed.DIRECTORY_ENTRY_EXPORT.symbols if e.name}
    assert export in exports
    if dll.name.lower() not in active:
        local=K.GetModuleHandleW('kernel32.dll');entry=K.GetProcAddress(local,b'LoadLibraryW')
        remote=active['kernel32.dll']['base']+entry-local
        assert read(remote,16)==ctypes.string_at(entry,16)
        call(remote,(str(dll)+'\0').encode('utf-16-le'));active=modules(pid)
    loaded=active[dll.name.lower()];assert Path(loaded['path']).resolve()==dll
    payload=bytes.fromhex(sys.argv[5]) if len(sys.argv)>5 else None
    result=call(loaded['base']+exports[export],payload)
    report=dict(pid=pid,base=loaded['base'],result=result,exports={k:loaded['base']+v for k,v in exports.items()})
    print(json.dumps(report,indent=2))
    if len(sys.argv)>4:Path(sys.argv[4]).write_text(json.dumps(report,indent=2))
    K.CloseHandle(handle);assert result==0

if __name__=='__main__':main()
