import ctypes as c,struct,time,json,argparse,math
from ctypes import wintypes as w
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--pid',type=int,required=True);p.add_argument('--seconds',type=int,default=150);a=p.parse_args()
root=Path(__file__).parent
k=c.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];k.OpenProcess.restype=w.HANDLE
k.ReadProcessMemory.argtypes=[w.HANDLE,c.c_void_p,c.c_void_p,c.c_size_t,c.POINTER(c.c_size_t)];k.ReadProcessMemory.restype=w.BOOL
k.CloseHandle.argtypes=[w.HANDLE]
h=k.OpenProcess(0x410,False,a.pid)
if not h:raise RuntimeError('Read-only process handle unavailable')
def read(addr,n):
 if addr<0x10000:return b''
 b=c.create_string_buffer(n);got=c.c_size_t()
 return bytes(b) if k.ReadProcessMemory(h,addr,b,n,c.byref(got)) and got.value==n else b''
def num(addr,fmt):
 b=read(addr,struct.calcsize(fmt));return struct.unpack(fmt,b)[0] if b else 0
def q(addr):return num(addr,'<Q')
base=0x140000000
def sources():
 manager=q(base+0x3517420)
 if q(manager)!=base+0x2226730:return 0,0
 world=q(manager+8);game=q(world+0x10);reg=q(game+0x20)
 if num(reg+8+81*32,'<I')!=81:return 0,0
 count=num(reg+8+81*32+16,'<I');pairs=q(reg+8+81*32+24)
 crowd=0
 if not 1<=count<=8:return 0,0
 for i in range(count):
  obj=q(pairs+i*16+8)
  if q(obj+0x2918)==obj and q(obj+0x28e8)==base+0x2312f88:crowd=obj;break
 provider=q(q(q(q(q(base+0x3504750)+0x10)+0x90))+0x28)
 return crowd,provider
def upright(m):
 def distance(i,j):return math.sqrt(sum((m[i*16+12+t]-m[j*16+12+t])**2 for t in range(3)))
 ta,tb=distance(3,4),distance(7,8)
 if min(ta,tb)<1:return False
 la,lb=ta+distance(4,5),tb+distance(8,9);foot=min(m[5*16+13],m[9*16+13])
 return m[2*16+13]-foot>=.9*(la+lb)/2 and m[3*16+13]-m[4*16+13]>=.5*ta and m[7*16+13]-m[8*16+13]>=.5*tb
start=time.monotonic();tracks={};previous={};lastSummary=''
print('COLLECTING read-only',a.pid,flush=True)
out=(root/'goal_tracks.jsonl').open('w',encoding='utf8')
try:
 while time.monotonic()-start<a.seconds:
  crowd,provider=sources()
  if not crowd or not provider:time.sleep(.05);continue
  entries=read(crowd+0x450,64*0x90)
  if len(entries)!=64*0x90:time.sleep(.05);continue
  candidates=[]
  for slot in range(64):
   clip,behavior=struct.unpack_from('<ii',entries,slot*0x90+0x20)
   if behavior!=14:continue
   address=provider+slot*0xdb0+0x10
   raw=read(address,31*64)
   if len(raw)!=31*64 or raw!=read(address,31*64):continue
   if read(crowd+0x470+slot*0x90,8)!=entries[slot*0x90+0x20:slot*0x90+0x28]:continue
   m=struct.unpack('<496f',raw)
   if not all(math.isfinite(v) and abs(v)<1000 for v in m) or not upright(m):continue
   if any(abs(m[j*16+15]-1)>.001 for j in range(31)):continue
   height=max(m[19*16+13],m[24*16+13])-m[14*16+13]
   key=(crowd,provider,slot,clip)
   candidates.append((slot,clip,round(height,1)))
   if previous.get(key)==raw:continue
   previous[key]=raw
   record={'time':time.monotonic()-start,'slot':slot,'clip':clip,'behavior':behavior,'handAboveHeadCm':height,'matrices':m}
   out.write(json.dumps(record)+'\n');out.flush();tracks.setdefault(str(key),[]).append(record)
  summary=str(candidates)
  if int(time.monotonic()-start)//5!=lastSummary:
   print('UPRIGHT GOAL SOURCES',summary,flush=True);lastSummary=int(time.monotonic()-start)//5
  time.sleep(1/30)
finally:
 out.close();k.CloseHandle(h)
 (root/'goal_tracks.json').write_text(json.dumps(tracks),encoding='utf8')
 print('SAVED',[(key,len(frames),max(f['handAboveHeadCm'] for f in frames)) for key,frames in tracks.items()],flush=True)
