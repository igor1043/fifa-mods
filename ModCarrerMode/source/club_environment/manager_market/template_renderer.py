"""Compile career data while preserving immutable native artwork blocks.

APT pointers and grouped BIG resource order are unchanged. Padding the appended
controller by complete chunkzip blocks keeps all texture blocks aligned so the
already validated compressed bytes can be reused, even on the first opening.
"""
from pathlib import Path
from collections import OrderedDict
from types import SimpleNamespace
import hashlib,json,math,struct,zlib,time
from formats import BigFile
from apt_actions import Actions

_templates=OrderedDict()

def load(path,full_name):
 path=Path(path);manifest=path.with_suffix('.json')
 key=(str(path.resolve()),path.stat().st_mtime_ns,path.stat().st_size,manifest.stat().st_mtime_ns,manifest.stat().st_size,full_name)
 if key in _templates:
  _templates.move_to_end(key);return _templates[key]
 metadata=json.loads(manifest.read_bytes())
 if metadata.get('schema')!=1 or metadata.get('full_name')!=full_name:raise ValueError('Template APT incompatível')
 big=BigFile(path)
 if big.fingerprint!=metadata['sha256']:raise ValueError('Template APT incompleto')
 blocks={}
 if big.wrapper:
  size=struct.unpack_from('>I',big.wrapper,16)[0];cursor=40
  for offset in range(0,len(big.original),size):
   length,kind=struct.unpack_from('>II',big.disk_original,cursor)
   if kind!=1:raise ValueError('Bloco APT incompatível')
   blocks[hashlib.sha256(big.original[offset:offset+size]).digest()]=big.disk_original[cursor+8:cursor+8+length]
   cursor=((cursor+8+length+8+15)//16)*16-8
 value=(big,metadata,blocks);_templates[key]=value
 while len(_templates)>1:_templates.popitem(last=False)
 return value

def wrap(content,header,blocks):
 size=struct.unpack_from('>I',header,16)[0];out=bytearray(header)
 struct.pack_into('>I',out,12,len(content));struct.pack_into('>I',out,20,math.ceil(len(content)/size));reused=0
 for offset in range(0,len(content),size):
  raw=content[offset:offset+size];encoded=blocks.get(hashlib.sha256(raw).digest())
  if encoded is None:
   compressor=zlib.compressobj(1,zlib.DEFLATED,-15);encoded=compressor.compress(raw)+compressor.flush()
  else:reused+=1
  start=((len(out)+8+15)//16)*16-8;out.extend(bytes(start-len(out)));out.extend(struct.pack('>II',len(encoded),1));out.extend(encoded)
 return bytes(out),reused

def build(template,output,*,script_factory,full_name):
 started=time.perf_counter();big,meta,blocks=load(template,full_name)
 original=big.entries['0'].original;data=bytearray(original)
 start,registration=script_factory(data,[bytes.fromhex(v) for v in meta['dictionaries']],meta['scenes'])
 if data[:len(original)]!=original or min(start,registration)<len(original):raise ValueError('Atualização alterou a geometria APT')
 decoded=Actions(SimpleNamespace(big=big,data=data,width=8,entry=big.entries['0']))
 for offset in (start,registration):decoded.decode(offset)
 if decoded.errors:raise ValueError('Código APT inválido: '+str(decoded.errors[:3]))
 for at,target in zip(meta['action_pointers'],(start,registration)):struct.pack_into('<Q',data,at,target)
 if big.wrapper:
  size=struct.unpack_from('>I',big.wrapper,16)[0]
  data.extend(bytes(-(len(data)-len(original))%size))
 # Keep the same resource groups and physical alignment as the validated
 # template; no mutation of the cached BigFile or source textures is allowed.
 entries=[(name,data if name=='0' else entry.original) for name,entry in big.entries.items()]
 header=16+sum(9+len(name.encode('latin1')) for name,_ in entries);offset=(header+63)//64*64
 directory=bytearray();payload=bytearray(offset-header)
 for name,raw in entries:
  pad=-offset%64;payload.extend(bytes(pad));offset+=pad
  directory.extend(struct.pack('>II',offset,len(raw))+name.encode('latin1')+b'\0');payload.extend(raw);offset+=len(raw)
 content=b'BIGF'+struct.pack('<I',offset)+struct.pack('>II',len(entries),header)+directory+payload
 if len(content)>128*1024*1024:raise ValueError('Tela excedeu o limite nativo de 128 MiB')
 reused=0
 if big.wrapper:content,reused=wrap(content,big.wrapper,blocks)
 output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(content)
 return dict(path=str(output),bytes=len(content),scenes=len(meta['scenes']),characters=meta['characters'],template_cached=True,reused_blocks=reused,seconds=round(time.perf_counter()-started,3))
