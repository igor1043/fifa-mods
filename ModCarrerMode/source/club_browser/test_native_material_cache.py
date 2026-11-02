"""Exercise the actual converter with duplicate fingerprints and source alpha."""
from pathlib import Path
from tempfile import TemporaryDirectory
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import ctypes,os,struct,threading,unittest
import numpy as np
from PIL import Image
import native_assets as assets
import portable_paths
from rx3 import Rx3,TEXTURE

def fixture(path,blends=(0,1)):
    v=np.zeros(3,dtype=assets.STRIDE);v['p']=[[0,0,0],[1,0,0],[0,1,0]];v['n']=[0,0,1];v['uv']=[[0,0],[1,0],[0,1]];idx=np.array([0,1,2],dtype='<u4')
    rgb=bytes([80,60,40,255])*64;coverage=np.tile(np.array([0,15,40,100,165,180,230,255],dtype='u1'),(8,1));rgba=np.full((8,8,4),255,dtype='u1');rgba[:,:,0]=coverage
    textures=[rgb,rgb,rgba.tobytes(),rgba.tobytes()]
    with path.open('wb') as f:
        f.write(b'FF3D0001'+struct.pack('<II',2,4))
        for i in range(2):f.write(struct.pack('<IIii7f',3,3,i,blends[i],1.,1.,1.,1.,1.,1.,1.)+v.tobytes()+idx.tobytes())
        for data in textures:f.write(struct.pack('<4I',8,8,3,len(data))+data)
        f.write(b'FFMAT001'+struct.pack('<I',2)+struct.pack('<IiIi',1,2,1,3))
    return coverage

class NativeMaterialCache(unittest.TestCase):
 def test_hair_parts_keep_source_coverage_both_below_and_above_old_threshold(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);mask=fixture(root/'model.ff3d');out=root/'output';assets.convert(root/'model.ff3d',out,portable_paths.read_asset,root/'cache',animated=True)
   image=Image.new('RGBA',(8,8),(80,60,40,255));image.putalpha(Image.fromarray(mask));expected=assets.texture(image,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm')
   for i in range(2):self.assertEqual((out/f'atlas_{i}.rx3').read_bytes(),expected)
 def test_concurrent_identical_fingerprints_publish_without_replace(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);fixture(root/'model.ff3d',(0,0));barrier=threading.Barrier(2);texture=assets.texture;local=threading.local()
   def encode(*args,**kwargs):
    # Wait only for the two material encoder threads, not neutral maps.
    if threading.current_thread().name.startswith('xi-material') and not getattr(local,'waited',False):local.waited=True;barrier.wait(timeout=10)
    return texture(*args,**kwargs)
   with patch.object(assets,'texture',side_effect=encode),patch('preview_files.os.replace',side_effect=AssertionError('a shared cache inode was replaced')):
    assets.convert(root/'model.ff3d',root/'output',portable_paths.read_asset,root/'cache',animated=True)
   self.assertEqual(len(list((root/'cache').glob('*.rx3'))),1)
   self.assertEqual((root/'output/atlas_0.rx3').read_bytes(),(root/'output/atlas_1.rx3').read_bytes())
   self.assertEqual(list((root/'cache').glob('*.new')),[])
 def test_corrupt_cache_is_bypassed_without_replacing_a_shared_file(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);fixture(root/'model.ff3d');cache=root/'cache';assets.convert(root/'model.ff3d',root/'first',portable_paths.read_asset,cache,animated=True);expected={p.name:p.read_bytes() for p in (root/'first').glob('*.rx3')}
   damaged=next(cache.glob('*.rx3'));damaged.write_bytes(b'RX3l');assets.convert(root/'model.ff3d',root/'second',portable_paths.read_asset,cache,animated=True)
   for name,blob in expected.items():self.assertEqual(blob,(root/'second'/name).read_bytes())
   self.assertEqual(damaged.read_bytes(),b'RX3l')

if __name__=='__main__':unittest.main()
