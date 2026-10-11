from pathlib import Path
import struct,re,json
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
p=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation')
b=(p/'fifa16.image.bin').read_bytes();base=0x140000000;cs=Cs(CS_ARCH_X86,CS_MODE_64)
targets=(0x222cd18,0x222cd28,)
for target in targets:
 print('TARGET',hex(target),b[target:b.find(b'\0',target)])
 for m in re.finditer(re.escape(struct.pack('<Q',base+target)),b):
  at=m.start();print('POINTER',hex(at),[hex(v-base) for v in struct.unpack_from('<8Q',b,at)])
 for m in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',b):
  at=m.start()
  if at+7+struct.unpack_from('<i',b,at+3)[0]==target:
   print('LEA',hex(at));print('\n'.join(f'{i.address:x} {i.mnemonic} {i.op_str}' for i in cs.disasm(b[at:at+120],at)))
