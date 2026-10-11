import ctypes as c,sys,time,json
from ctypes import wintypes as w
from pathlib import Path
sys.path.insert(0,r'J:\mods\fifa 16\01_Projetos\mascotes\mod\tools')
from capture import kernel,entries
k=kernel(); games=[p for p in entries(k) if p['name'].lower()=='fifa16.exe'];assert len(games)==1
pid=games[0]['pid'];mods=entries(k,pid)
dll=Path(r'U:\fifa 16\ModCarrerMode\mods\flamengo_pyro\flamengo_pyro_v3.dll')
k.GetModuleHandleW.argtypes=[w.LPCWSTR];k.GetModuleHandleW.restype=w.HMODULE
k.GetProcAddress.argtypes=[w.HMODULE,c.c_char_p];k.GetProcAddress.restype=c.c_void_p
k.GetModuleHandleExW.argtypes=[w.DWORD,c.c_void_p,c.POINTER(w.HMODULE)]
k.GetModuleFileNameW.argtypes=[w.HMODULE,w.LPWSTR,w.DWORD]
k.VirtualAllocEx.argtypes=[w.HANDLE,c.c_void_p,c.c_size_t,w.DWORD,w.DWORD];k.VirtualAllocEx.restype=c.c_void_p
k.WriteProcessMemory.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)]
k.CreateRemoteThread.argtypes=[w.HANDLE,c.c_void_p,c.c_size_t,c.c_void_p,c.c_void_p,w.DWORD,c.c_void_p];k.CreateRemoteThread.restype=w.HANDLE
k.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
k.VirtualFreeEx.argtypes=[w.HANDLE,c.c_void_p,c.c_size_t,w.DWORD]
h=k.OpenProcess(0x43a,False,pid);assert h
def call(address,data):
 mem=k.VirtualAllocEx(h,None,len(data),0x3000,4);assert mem
 written=c.c_size_t();assert k.WriteProcessMemory(h,mem,data,len(data),c.byref(written)) and written.value==len(data)
 th=k.CreateRemoteThread(h,None,0,address,mem,0,None);assert th
 result=k.WaitForSingleObject(th,10000)
 k.CloseHandle(th)
 if result!=0: raise RuntimeError('Remote call pending; allocation retained, do not retry')
 k.VirtualFreeEx(h,mem,0,0x8000)
try:
 loaded=next((m for m in mods if m['name']==dll.name),None)
 if not loaded:
  load=k.GetProcAddress(k.GetModuleHandleW('kernel32.dll'),b'LoadLibraryW');owner=w.HMODULE();assert k.GetModuleHandleExW(6,load,c.byref(owner))
  path=c.create_unicode_buffer(32768);k.GetModuleFileNameW(owner,path,len(path))
  remote=next(m for m in mods if m['name'].lower()==Path(path.value).name.lower())['base']+load-owner.value
  call(remote,(str(dll)+'\0').encode('utf-16le'))
  loaded=next(m for m in entries(k,pid) if m['name']==dll.name)
  # DONT_RESOLVE_DLL_REFERENCES is only used locally to calculate the export RVA.
  k.LoadLibraryExW.argtypes=[w.LPCWSTR,w.HANDLE,w.DWORD];k.LoadLibraryExW.restype=w.HMODULE
  local=k.LoadLibraryExW(str(dll),None,1);assert local
  start=k.GetProcAddress(local,b'Fifa16ModStart');assert start
  call(loaded['base']+start-local,b'U:\\fifa 16\\ModCarrerMode\\mods\0')
 if '--stop' in sys.argv or '--replay' in sys.argv:
  k.LoadLibraryExW.argtypes=[w.LPCWSTR,w.HANDLE,w.DWORD];k.LoadLibraryExW.restype=w.HMODULE
  local=k.LoadLibraryExW(str(dll),None,1);assert local
  replay=k.GetProcAddress(local,b'Fifa16ModStop' if '--stop' in sys.argv else b'Fifa16PyroReplay');assert replay
  call(loaded['base']+replay-local,b'\0')
 print(json.dumps({'pid':pid,'module':loaded},indent=2))
finally:k.CloseHandle(h)
