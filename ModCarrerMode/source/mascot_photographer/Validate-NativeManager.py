"""Read-only export audit against working native FIFA 16 manager packages.

Structural validation cannot prove runtime compatibility or diagnose a crash.
"""
from pathlib import Path
import argparse,json,struct,sys,hashlib
import numpy as np

p=argparse.ArgumentParser();p.add_argument('--package',required=True);p.add_argument('--native-model',required=True);p.add_argument('--reference-model',required=True);p.add_argument('--tools',required=True);p.add_argument('--output',required=True)
a=p.parse_args();sys.path.insert(0,str(Path(a.tools)/'vendor/rx3tools'))
from rx3 import Rx3,read_model,FORMAT,VERTEX,INDEX,TEXTURE

def inspect(path):
    rx=Rx3(Path(path).read_bytes());parts,bind=read_model(rx)
    if len(parts)!=1 or len(bind)!=31:raise ValueError('Expected one native manager mesh and 31 bind entries')
    part=parts[0];j=np.array(part['joints']).reshape(-1,4);w=np.array(part['weights']).reshape(-1,4);xyz=np.array(part['positions']).reshape(-1,3)
    assert np.all(w.sum(1)==255) and np.isfinite(xyz).all()
    palette=rx.get(0x0f3861a2)[0];count=struct.unpack_from('<I',palette,4)[0];order=list(palette[272:272+count]);used=set(j[w>0].tolist())
    assert len(set(order))==count and used==set(order)
    assert all(palette[16+bone]==slot for slot,bone in enumerate(order))
    assert len(palette)==528 and len(rx.get(0xdf9aec1e)[0])==2000
    vb,ib=rx.get(VERTEX)[0],rx.get(INDEX)[0];vn,stride=struct.unpack_from('<2I',vb,4);n,width=struct.unpack_from('<2I',ib,4)
    assert vn==len(xyz) and 16+vn*stride<=len(vb) and 16+n*width<=len(ib)
    assert max(part['indices'])<vn and min(part['indices'])>=0
    instance=rx.get(0x22b2be36)[0];bufferBytes,indexCount,indexWidth=struct.unpack_from('<3I',instance,16)
    assert bufferBytes==struct.unpack_from('<I',ib,0)[0] and indexCount==n and indexWidth==width
    return rx,dict(vertices=vn,triangles=len(part['indices'])//3,bindBones=len(bind),activeBones=count,activeBoneSet=sorted(used),vertexStride=stride,bytes=Path(path).stat().st_size)

native,nativeInfo=inspect(a.native_model);reference,referenceInfo=inspect(a.reference_model)
root=Path(a.package);reports=[]
for weather in (0,1):
    path=root/f'specificmanager_1035_0_{weather}.rx3';rx,info=inspect(path)
    assert rx.version==native.version==reference.version
    assert rx.get(FORMAT)==native.get(FORMAT)==reference.get(FORMAT)
    assert rx.get(0xdf9aec1e)==native.get(0xdf9aec1e)==reference.get(0xdf9aec1e)
    assert rx.get(0x0f3861a2)==native.get(0x0f3861a2)
    assert info['activeBoneSet']==nativeInfo['activeBoneSet']==referenceInfo['activeBoneSet']
    texPath=root/f'specificmanager_1035_0_{weather}_textures.rx3';tex=Rx3(texPath.read_bytes());textures=tex.get(TEXTURE)
    names=[name for kind,name in tex.names() if kind==TEXTURE]
    assert len(textures)==len(names)==3
    assert {name.rsplit('_',1)[-1] for name in names}=={'cm','nm','coeff'}
    tables=tex.get(0x6bd085dc)
    if len(tables)!=1:raise ValueError('Missing or duplicated texture-info table')
    table=tables[0];count=struct.unpack_from('<I',table,0)[0]
    if count!=len(textures) or len(table)!=16+16*count:raise ValueError('Texture-info count or size differs from payloads')
    for i,section in enumerate(textures):
        if table[16+i*16:32+i*16]!=section[:16]:
            raise ValueError(f'Texture-info descriptor differs from payload {i} ({names[i]}): unsafe buffer format/size')
    for section in textures:
        w,h,depth,levels=struct.unpack_from('<4H',section,8);fmt=section[5];assert fmt in (0,1,2) and w>0 and h>0 and depth==1
        block=8 if fmt==0 else 16;at=16
        for level in range(levels):
            pitch,rows,size,_=struct.unpack_from('<4I',section,at)
            assert pitch==max(1,(w+3)//4)*block and rows==max(1,(h+3)//4) and size==pitch*rows
            at+=16+size;w=max(1,w//2);h=max(1,h//2)
        assert 0<=len(section)-at<16
    reports.append(dict(weather=weather,model=info,modelSha256=hashlib.sha256(path.read_bytes()).hexdigest(),textureSha256=hashlib.sha256(texPath.read_bytes()).hexdigest(),textureNames=names))
report=dict(structuralChecksPassed=True,runtimeValidated=False,crashCauseConfirmed=False,textureInfoMatchesPayloads=True,activeBonePaletteMatchesNativeByteForByte=True,referenceManager=referenceInfo,genericManager=nativeInfo,variants=reports)
Path(a.output).write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))
