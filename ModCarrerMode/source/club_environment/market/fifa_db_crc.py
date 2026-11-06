"""Validate T3DB checksums using physical table spans from its directory.

CRC locations cannot be inferred from record/string lengths: files may contain
padding between that payload and the checksum. Never mutate the input file.
"""
import struct
from dataclasses import dataclass

def _lookup():
 result=[]
 for byte in range(256):
  value=byte<<24
  for _ in range(8):value=((value<<1)^(0x04c11db7 if value&0x80000000 else 0))&0xffffffff
  result.append(value)
 return tuple(result)
_TABLE=_lookup()

def crc32(data):
 value=0xffffffff
 for byte in data:value=((value<<8)&0xffffffff)^_TABLE[(value>>24)^byte]
 return value

@dataclass(frozen=True)
class Region:
 table:str
 kind:str
 start:int
 end:int
 checksum:int

def regions(data):
 if len(data)<28 or data[:4]!=b'DB\0\x08':raise ValueError('T3DB signature unsupported')
 length,count=struct.unpack_from('<I',data,8)[0],struct.unpack_from('<I',data,16)[0]
 if length!=len(data) or not 1<=count<=512:raise ValueError('T3DB file/directory bounds invalid')
 base=28+count*8
 if base>len(data):raise ValueError('T3DB directory truncated')
 entries=[]
 for i in range(count):
  short,offset=struct.unpack_from('<4sI',data,24+i*8);start=base+offset
  try:name=short.decode('ascii')
  except UnicodeDecodeError:raise ValueError('T3DB table identifier invalid') from None
  if start<base or start+36>len(data) or entries and start<=entries[-1][1]:raise ValueError('T3DB table order/bounds invalid')
  entries.append((name,start))
 result=[Region('','file',0,20,20),Region('','directory',24,base-4,base-4)]
 for i,(name,start) in enumerate(entries):
  end=entries[i+1][1]-4 if i+1<len(entries) else len(data)-4
  fields=data[start+24];stride,strings=struct.unpack_from('<I',data,start+4)[0],struct.unpack_from('<I',data,start+12)[0]
  allocated,valid=struct.unpack_from('<HH',data,start+16)
  if valid>allocated or start+36+16*fields+allocated*stride+strings>end:raise ValueError('T3DB table payload out of bounds')
  result.extend((Region(name,'header',start,start+32,start+32),Region(name,'data',start+36,end,end)))
 return result

def issues(data):
 errors=[]
 for r in regions(data):
  expected=crc32(memoryview(data)[r.start:r.end]);stored=struct.unpack_from('<I',data,r.checksum)[0]
  if stored!=expected:errors.append(dict(table=r.table,kind=r.kind,offset=r.checksum,stored=stored,expected=expected))
 return errors

def update_tables(data,tables):
 """Return a corrected copy; reject pre-existing unrelated inconsistencies."""
 selected=set(tables);parts=regions(data);names={r.table for r in parts if r.table}
 if not selected or not selected<=names:raise ValueError('T3DB table selection invalid')
 errors=issues(data)
 if any(e['table'] not in selected for e in errors):raise ValueError('Unrelated T3DB checksum mismatch')
 out=bytearray(data)
 for r in parts:
  if r.table in selected:struct.pack_into('<I',out,r.checksum,crc32(memoryview(out)[r.start:r.end]))
 return bytes(out)
