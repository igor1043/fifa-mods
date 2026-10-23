import portable_paths as portable
"""Read-only APT request bridge, limited to this FIFA session and room page.

The native screen owns all input. This helper never synthesizes input or writes
game memory. Complete, nonce-scoped commands are forwarded to a tiny mailbox.
"""
from pathlib import Path
import ctypes as C,json,re,time,threading
from ctypes import wintypes as W
ROOT=portable.ROOM
PAGE='game/screens/career/server16/DressingRoom'
class Region(C.Structure):
    _fields_=[('base',C.c_void_p),('allocation',C.c_void_p),('allocation_protect',W.DWORD),('partition',W.WORD),('size',C.c_size_t),('state',W.DWORD),('protect',W.DWORD),('type',W.DWORD)]

def decode_requests(data,pid,nonce):
    pattern=re.compile(rb'S16ROOM1\|'+str(pid).encode()+rb'\|'+nonce.encode()+rb'\|([0-9]{1,9})\|(-?[0-9]{1,3})\|ENDROOM')
    result=[]
    for raw in (data,data[0::2] if data.count(b'\x00')>len(data)//4 else b'',data[1::2] if data.count(b'\x00')>len(data)//4 else b''):
        result.extend((int(m[1]),int(m[2])) for m in pattern.finditer(raw))
    return [(seq,code) for seq,code in result if seq>0 and -3<=code<128]

def run(pid):
    import psutil
    from server16_py.memory_access import Memory
    m=Memory();m.process_id=pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,pid);m.base_module=m._get_base_address(psutil.Process(pid).exe())
    k=C.WinDLL('kernel32',use_last_error=True);k.VirtualQueryEx.argtypes=[W.HANDLE,C.c_void_p,C.POINTER(Region),C.c_size_t];k.VirtualQueryEx.restype=C.c_size_t
    scope=None;sequence=0;regions=[];priority=[];cursor=0;offset=0;last_inventory=0;was_room=False
    logfile=ROOT/'runtime/room_scene_controls.log'
    try:
        while psutil.pid_exists(pid):
            try:
                p=m.read_int64(m.base_module+0x3809030)
                for o in (232,192,136,472):p=m.read_int64(p+o)
                in_room=m.read_process_memory(p,128).split(b'\0')[0].decode('ascii',errors='replace')==PAGE
                cfg=json.loads((ROOT/'runtime/room_control_scope.json').read_text(encoding='utf8'))
                if cfg['pid']!=pid:time.sleep(.2);continue
                key=(pid,cfg['club'],cfg['nonce'])
                if key!=scope:scope=key;sequence=0;regions=[];priority=[];cursor=0;offset=0;last_inventory=0
                if not in_room:was_room=False;time.sleep(.2);continue
                if not was_room:last_inventory=0;was_room=True
                now=time.monotonic()
                if now-last_inventory>15 or not regions:
                    regions=[];address=0;region=Region()
                    while k.VirtualQueryEx(m.process_handle,C.c_void_p(address),C.byref(region),C.sizeof(region)):
                        base=region.base or 0;size=region.size
                        if region.state==0x1000 and region.type==0x20000 and region.protect&0xff in (4,8,0x40,0x80) and not region.protect&0x100 and size<=256*1024*1024:regions.append((base,size))
                        if base+size<=address:break
                        address=base+size
                    last_inventory=now;cursor=0;offset=0
                found=[];touched=[];start=time.monotonic();budget=48*1024*1024
                # Once the APT arena is found, command changes normally stay in
                # that arena. Keep a bounded round-robin pass for arena growth.
                for base,size in list(priority):
                    if time.monotonic()-start>.045:break
                    for pos in range(0,size,4*1024*1024):
                        raw=m.read_process_memory(base+pos,min(4*1024*1024+256,size-pos));items=decode_requests(raw,pid,cfg['nonce']);found+=items
                while regions and budget>0 and time.monotonic()-start<.065:
                    base,size=regions[cursor];count=min(4*1024*1024,size-offset)
                    try:raw=m.read_process_memory(base+offset,min(count+256,size-offset));items=decode_requests(raw,pid,cfg['nonce'])
                    except RuntimeError:items=[]
                    if items:found+=items;touched.append((base,size))
                    offset+=count;budget-=count
                    if offset>=size:offset=0;cursor=(cursor+1)%len(regions)
                for region in touched:
                    if region not in priority:priority.append(region)
                priority=priority[-8:]
                if found:
                    seq,code=max(found)
                    if seq>sequence and (code<0 or code<len(cfg['scenes'])):
                        sequence=seq
                        out=ROOT/'runtime/room_camera_command.txt';tmp=out.with_suffix('.new');tmp.write_text(f'S16ROOM 1 {pid} {cfg["club"]} {cfg["nonce"]} {seq} {code}\n');tmp.replace(out)
                        with logfile.open('a',encoding='utf8') as f:f.write(json.dumps({'pid':pid,'club':cfg['club'],'sequence':seq,'command':code})+'\n')
            except (OSError,ValueError,KeyError,RuntimeError):pass
            time.sleep(.12)
    finally:m.close()

def start(pid):
    thread=threading.Thread(target=run,args=(pid,),daemon=True,name='NativeRoomSceneCommands');thread.start();return thread
