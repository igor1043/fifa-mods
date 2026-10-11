"""Read-only observation of particle definitions and per-instance parameter storage."""
import sys,json,struct,ctypes as C
from pathlib import Path
sys.argv=[sys.argv[0],sys.argv[1]]
prefix=(Path(__file__).parent/'read_match_context_v17.py').read_text().split('queries={')[0]
exec(prefix)
def try_string(addr):
    try:return read(addr,160).split(b'\0')[0].decode('ascii',errors='replace')
    except ValueError:return '?'
def vec(addr):return struct.unpack('<4f',read(addr,16))
result={}
try:
    obj=ptr(base+0x3504500+31*8);state=ptr(obj+16);manager=ptr(state+0x58);effect=ptr(manager+16)
    result.update({'definition':try_string(state+8),'asset':integer(state+8+64),'effect':hex(effect),'groups':[],'parameters':[]})
    begin=ptr(effect+0xf8);end=ptr(effect+0x100)
    if not 0<=end-begin<=0x168*64:raise ValueError('group span')
    for group in range(begin,end,0x168):
        gb=ptr(group+0xf8);ge=ptr(group+0x100)
        row={'group':try_string(ptr(group+0x60)),'actions':[]}
        if 0<=ge-gb<=8*64:
            for a in range(gb,ge,8):
                action=ptr(a);row['actions'].append({'name':try_string(ptr(action+0x60))})
        result['groups'].append(row)
    handle=integer(state+0x60);node=ptr(manager+0x30)
    for _ in range(128):
        idx=integer(node+0x20)
        if idx==handle:break
        node=ptr(node+(8 if handle<idx else 0))
    inst=ptr(node+0x28);pb=ptr(inst+0x260);pe=ptr(inst+0x268)
    if not 0<=pe-pb<=0xd0*1024:raise ValueError('parameter span')
    result['parameter_count']=(pe-pb)//0xd0
    for q in range(pb,pe,0xd0):
        prop=ptr(q);name=try_string(ptr(prop+0x60))
        if 'Color' in name or 'Colour' in name:
            result['parameters'].append({'name':name,'property':hex(prop),'kind':integer(prop+0x3c),'stored_count':integer(prop+0x40),'value_ptr':hex(ptr(prop+0x18)),'instance_cache_hex':read(q,0xd0).hex()})
finally:k.CloseHandle(h)
dest=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010\palette_live.json')
dest.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
