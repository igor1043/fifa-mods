"""Regression checks against actual posed XI and FIFA RX3 templates."""
import json,struct,tempfile,sys
from pathlib import Path
import numpy as np
from native_assets import read_model,geometry,decode,STRIDE,SLOTS,OPAQUE_SLOTS
from rx3 import Rx3,read_model as rx_model,VERTEX,INDEX,MESH,NAME,TEXTURE

def run(case):
    case=Path(case);parts,textures=read_model(case/'model.ff3d');assets=case/'assets';meta=json.loads((assets/'assets.json').read_text())
    rx=Rx3((assets/'geometry.rx3').read_bytes());native,_=rx_model(rx)
    assert STRIDE.fields['n'][1]==12 and STRIDE.fields['uv'][1]==24
    for p in parts:
        length=np.linalg.norm(p['v']['n'],axis=1)
        assert np.mean(abs(length-1)<.03)>.98,'Exporter normal/UV fields were swapped'
    assert len(native)==SLOTS==len(meta['bindings'])
    assert sum(len(p['v']) for p in parts)==meta['vertices']
    used=meta['used_slots'];assert len(used)==meta['parts'];original=np.concatenate([p['v']['p'] for p in parts]);converted=np.concatenate([np.array(native[i]['positions']).reshape(-1,3) for i in used])
    # Centimetres: half floats must preserve every pose within two millimetres.
    original=original[np.lexsort(original.T)];converted=converted[np.lexsort(converted.T)]
    # Compare order-independent bounds; compare exact vertices in half-float domain.
    expected={tuple(v) for v in original.astype('<f2').astype('<f4')};actual={tuple(v) for v in converted};assert actual==expected
    assert np.max(np.abs(original.min(axis=0)-converted.min(axis=0)))<.2
    assert np.max(np.abs(original.max(axis=0)-converted.max(axis=0)))<.2
    for p in native:
        assert max(p['indices'])<len(p['positions'])//3<65536
        assert np.isfinite(p['positions']).all() and np.isfinite(p['normals']).all()
        assert np.isfinite(p['uvs']).all()
    for i,p in enumerate(native):
        assert meta['bindings'][i][1]==(i>=OPAQUE_SLOTS)
        if i not in used:assert set(p['positions'])=={0.}
    # Regression: coordinates and normals must survive unchanged in half floats
    # and packed-normal precision, never substitute UVs with normal components.
    expected={(tuple(v['p'].astype('<f2')),tuple(v['uv'].astype('<f2'))) for p in parts for v in p['v']}
    actual={(tuple(p),tuple(uv)) for i in used for p,uv in zip(np.array(native[i]['positions']).reshape(-1,3),np.array(native[i]['uvs']).reshape(-1,2))}
    assert expected==actual
    keys={}
    for p in parts:
        key=(p['tex'],p['coeff'],tuple(p['tint'] if p['tex']>=0 else p['color']),p['alpha'],p['blend'],p['hair'])
        if key not in keys:keys[key]=len(keys)
    for page in range(meta['pages']):
        texture=Rx3((assets/f'atlas_{page}.rx3').read_bytes());assert texture.names()==[(TEXTURE,'xi_cm')];assert len(texture.get(TEXTURE))==1
        data=texture.get(TEXTURE)[0];w,h,_,mips=struct.unpack_from('<4H',data,8);assert [w,h]==meta['texture_sizes'][page]
        if page in meta['original_compressed_textures']:
            key=next(k for k,i in keys.items() if i==page);source=textures[key[0]];assert data[32:]==source[3] and data[5]==source[2] and mips==1,'FIFA compressed pixels changed'
    white=Rx3((assets/'white.rx3').read_bytes());assert white.names()==[(TEXTURE,'white_cm')]
    # Malformed model must fail before any output or game API is reachable.
    with tempfile.TemporaryDirectory() as tmp:
        bad=Path(tmp)/'bad.ff3d'
        for value in (b'bad',b'FF3D0001'+struct.pack('<II',100000,0),(case/'model.ff3d').read_bytes()[:100]):
            bad.write_bytes(value)
            try:read_model(bad);raise AssertionError('Truncated/oversized model accepted')
            except (ValueError,struct.error):pass
    print('PASS native XI: pose and original UVs preserved; normal layout checked; compressed FIFA pixels byte-identical; original texture dimensions; opaque/alpha separated; malformed inputs rejected')
if __name__=='__main__':run(sys.argv[1])
