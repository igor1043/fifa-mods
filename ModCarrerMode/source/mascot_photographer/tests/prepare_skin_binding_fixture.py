"""Prepare exact RX3 bind/feet fixtures and invalid-file cases for verify_locomotion."""
from pathlib import Path
import argparse,shutil,struct,sys,numpy as np

p=argparse.ArgumentParser()
p.add_argument('--packages',required=True)
p.add_argument('--renderer-inverse',required=True)
p.add_argument('--tools',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
from rx3 import Rx3,read_model
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
assert Path(a.renderer_inverse).stat().st_size==31*64
shutil.copy2(a.renderer_inverse,out/'renderer_inverse.bin')
packages=Path(a.packages)
for package in packages.iterdir():
    if not package.name.isdecimal():continue
    dest=out/'data/sceneassets/mascot'/package.name;dest.mkdir(parents=True,exist_ok=True)
    _,bind=read_model(Rx3((package/'model_animated.rx3').read_bytes()))
    assert len(bind)==31
    (dest/'bind.bin').write_bytes(np.asarray(bind,dtype='<f4').tobytes())
    for name in ['model_animated.rx3','locomotion_feet.bin']:shutil.copy2(package/name,dest/name)
raw=Rx3((packages/'1041/model_animated.rx3').read_bytes()).get(0xdf9aec1e)[0]
def file_bytes(payload=raw,section_id=0xdf9aec1e,offset=32):
    return b'RX3l'+struct.pack('<3I',4,32+len(payload),1)+struct.pack('<4I',section_id,offset,len(payload),0)+payload
cases={'valid':file_bytes(),'truncated':file_bytes()[:-1],'missing':file_bytes(section_id=1),'out_of_bounds':file_bytes(offset=0x7fffffff)}
for name in ['wrong_count','singular','nonfinite','wrong_affine']:
    payload=bytearray(raw)
    if name=='wrong_count':struct.pack_into('<I',payload,4,30)
    elif name=='singular':payload[16:80]=bytes(64)
    elif name=='nonfinite':struct.pack_into('<f',payload,16,float('nan'))
    else:struct.pack_into('<f',payload,16+15*4,2.0)
    cases[name]=file_bytes(payload)
cases['duplicate']=b'RX3l'+struct.pack('<3I',4,48+2*len(raw),2)+struct.pack('<4I',0xdf9aec1e,48,len(raw),0)+struct.pack('<4I',0xdf9aec1e,48+len(raw),len(raw),0)+raw+raw
for name,blob in cases.items():(out/f'bind_{name}.rx3').write_bytes(blob)
print('Prepared asset binds, captured renderer inverse and malformed RX3 cases:',out)
