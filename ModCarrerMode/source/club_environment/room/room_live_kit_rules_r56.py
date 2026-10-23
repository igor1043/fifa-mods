import portable_paths as portable
"""Bounded read of the evaluated FIFA Lua kit assignments. Never executes Lua."""
import struct,math

def read_assignments(memory,club,kit,league,defaults):
    def data(at,n):
        if not 0x10000<=at<0x7fffffffffff or not 0<n<=655360:raise ValueError('Lua bounds')
        raw=memory.read_process_memory(at,n)
        if not isinstance(raw,(bytes,bytearray)) or len(raw)!=n:raise ValueError('Lua short read')
        return raw
    def pointer(at):return struct.unpack('<Q',data(at,8))[0]
    def value(raw):
        tag=struct.unpack_from('<i',raw,8)[0]
        return tag,struct.unpack_from('<d' if tag==3 else '<Q',raw)[0]
    def field(table,key):
        h=data(table,64)
        if h[8]!=5 or h[11]>14:raise ValueError('Lua table')
        count=struct.unpack_from('<I',h,56)[0]
        if isinstance(key,int) and 1<=key<=count:return value(data(struct.unpack_from('<Q',h,24)[0]+(key-1)*16,16))
        nodes=struct.unpack_from('<Q',h,32)[0];raw=data(nodes,(1<<h[11])*40)
        for at in range(0,len(raw),40):
            typ=struct.unpack_from('<i',raw,at+24)[0]
            if isinstance(key,int):
                match=typ==3 and struct.unpack_from('<d',raw,at+16)[0]==key
            else:
                match=False
                if typ==4:
                    p=struct.unpack_from('<Q',raw,at+16)[0]
                    n=struct.unpack('<Q',data(p+16,8))[0]
                    match=n==len(key) and data(p+24,n)==key.encode('ascii')
            if match:return value(raw[at:at+16])
        return 0,0
    def at(table,*keys):
        v=(5,table)
        for key in keys:
            if v[0]!=5:return None
            v=field(int(v[1]),key)
        return int(v[1]) if v[0]==3 and math.isfinite(v[1]) and -1<=v[1]<=0xffffffff and int(v[1])==v[1] else None
    vm=pointer(memory.base_module+0x3613fd0);global_table=pointer(vm+0x78)
    out=dict(defaults);sources={}
    for dest,name in (('name_font','kitNameFont'),('font','kitNumberSet'),('color','kitNumberColourShirt'),('name_color_argb','kitNameColour'),('layout','kitNameCurve')):
        selected=None;source=''
        for table,keys in ((name+'Backup',(club,kit)),(name,(club,kit)),(name+'Tournament',(club,kit,league))):
            current=at(global_table,table,*keys)
            if current is not None and current>=0:selected=current;source=table
        # An explicit -1 in the final assignment means retain database fallback.
        if selected is not None:
            if dest=='name_color_argb':out['name_color']=[(selected>>shift)&255 for shift in (16,8,0)]
            else:out[dest]=selected
            sources[dest]=source
    out['assignment_sources']=sources
    return out

def apply_live(context,info):
    from server16_py.memory_access import Memory
    import psutil
    m=Memory();pid=context['pid'];process=psutil.Process(pid)
    if process.name().lower()!='fifa16.exe':return False
    m.process_id=pid;m.process_handle=m.kernel32.OpenProcess(0x410,False,pid);m.base_module=m._get_base_address(process.exe())
    try:
        for typ,defaults in info.items():info[typ]=read_assignments(m,context['club'],typ,context['league'],defaults)
        return True
    except (OSError,ValueError,TypeError,struct.error):return False
    finally:m.close()
