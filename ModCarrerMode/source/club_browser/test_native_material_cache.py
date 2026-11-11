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
from rx3 import Rx3,TEXTURE,INDEX

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
 def test_exterior_restores_source_hair_edges_without_reusing_indoor_cache(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);mask=fixture(root/'model.ff3d');cache=root/'cache'
   indoor=assets.convert(root/'model.ff3d',root/'indoor',portable_paths.read_asset,cache,animated=True,hair_profile='indoor')
   classic=assets.convert(root/'model.ff3d',root/'classic',portable_paths.read_asset,cache,animated=True,hair_profile='classic')
   image=Image.new('RGBA',(8,8),(80,60,40,255));image.putalpha(Image.fromarray(mask))
   expected=assets.texture(image,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm')
   for slot in (0,1):self.assertEqual((root/f'classic/atlas_{slot}.rx3').read_bytes(),expected)
   self.assertNotEqual((root/'indoor/atlas_0.rx3').read_bytes(),expected)
   self.assertEqual(classic['hair_cap_slots'],[]);self.assertTrue(all(classic['bindings'][i][1] for i in classic['used_slots']))
   self.assertEqual(indoor['hair_cap_slots'],[]);self.assertEqual(classic['triangle_winding'],'authored_fifa')
   assets.convert(root/'model.ff3d',root/'classic-warm',portable_paths.read_asset,cache,animated=True,hair_profile='classic')
   self.assertEqual((root/'classic-warm/atlas_0.rx3').read_bytes(),expected)
 def test_player_request_keeps_presentation_scoped_to_this_selection(self):
  from lineup_worker import request
  with TemporaryDirectory() as temp:
   path=Path(temp)/'request.tsv';base='schema=1\npid=77\nseq=1\nclub=1043\nkind=player\nplayer=158023\n'
   for mode in ('room','classic'):
    path.write_text(base+'presentation='+mode+'\n');self.assertEqual(request(path,77)['presentation'],mode)
   path.write_text(base);self.assertNotIn('presentation',request(path,77))
   path.write_text(base+'presentation=invalid\n')
   with self.assertRaises(ValueError):request(path,77)
 def test_folded_faces_keep_authored_indices_instead_of_following_smoothed_normals(self):
  v=np.zeros(3,dtype=assets.STRIDE);v['p']=[[0,0,0],[1,0,0],[0,1,0]];v['n']=[0,0,-1]
  # The opposite smooth normal is intentional: it must not reverse a cloth
  # face under backface culling. UV/material seams remain separate vertices.
  indices=np.array([0,1,2],dtype='<u4');blob=assets.geometry([(v,indices)],portable_paths.read_asset('data/sceneassets/prop/prop_102.rx3'),preserve_winding=True)
  native=Rx3(blob).get(INDEX)[0];self.assertEqual(np.frombuffer(native,dtype='<u2',count=3,offset=16).tolist(),[0,1,2])
  from player_animation import encode
  self.assertEqual(encode(v,indices,preserve_winding=True),Rx3(blob).get(__import__('rx3').VERTEX)[0][16:76])
 def test_hair_core_keeps_real_cutouts_and_strands_keep_source_coverage(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);mask=fixture(root/'model.ff3d');out=root/'output';assets.convert(root/'model.ff3d',out,portable_paths.read_asset,root/'cache',animated=True)
   expected_mask=np.tile(np.array([0,15,40,100,165,180,230,255],dtype='u1'),(8,1))
   image=Image.new('RGBA',(8,8),(80,60,40,255));image.putalpha(Image.fromarray(expected_mask));expected=assets.texture(image,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm')
   self.assertEqual((out/'atlas_1.rx3').read_bytes(),expected)
   cap=Image.new('RGBA',(8,8),(80,60,40,255));cap.putalpha(assets.hair_core_opacity(Image.fromarray(mask)));self.assertEqual((out/'atlas_0.rx3').read_bytes(),assets.texture(cap,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm'))
   import json
   meta=json.loads((out/'assets.json').read_text());self.assertEqual(meta['hair_cap_slots'],[]);self.assertEqual(meta['bindings'][64],[0,True]);self.assertIn([1,True],meta['bindings'][64:])
 def test_opacity_preserves_background_thin_strands_and_binary_masks(self):
  values=np.arange(256,dtype='u1')[None,:];result=np.array(assets.hair_opacity(Image.fromarray(values)))[0]
  self.assertTrue(np.all(result[:33]==values[0,:33]))
  np.testing.assert_array_equal(result,values[0])
  self.assertTrue(np.all(np.diff(result.astype(int))>=0))
  self.assertTrue(np.all(result[1:]>0))
  binary=Image.fromarray(np.array([[0,255],[255,0]],dtype='u1'))
  np.testing.assert_array_equal(np.array(assets.hair_opacity(binary)),np.array(binary))
 def test_authored_diffuse_hair_alpha_uses_same_coverage_without_recolouring(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);fixture(root/'model.ff3d');parts,textures=assets.read_model(root/'model.ff3d')
   source=np.tile(np.array([0,15,40,100,165,180,230,255],dtype='u1'),(8,1))
   rgba=np.full((8,8,4),(80,60,40,255),dtype='u1');rgba[:,:,3]=source
   parts[0].update(coeff=-1,blend=True);parts[1].update(coeff=-1,blend=True)
   textures[0]=(8,8,3,rgba.tobytes());textures[1]=textures[0]
   with patch.object(assets,'read_model',return_value=(parts,textures)):
    meta=assets.convert(root/'model.ff3d',root/'out',portable_paths.read_asset,animated=True)
   expected=Image.fromarray(rgba);expected.putalpha(Image.fromarray(np.tile(np.array([0,15,40,100,165,180,230,255],dtype='u1'),(8,1))))
   self.assertEqual((root/'out/atlas_0.rx3').read_bytes(),assets.texture(expected,portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm'))
   self.assertEqual(meta['original_compressed_textures'],[])
 def test_non_hair_materials_keep_original_pixels(self):
  with TemporaryDirectory() as temp:
   root=Path(temp);fixture(root/'model.ff3d');parts,textures=assets.read_model(root/'model.ff3d')
   for p in parts:p.update(hair=False,coeff=-1,blend=True)
   with patch.object(assets,'read_model',return_value=(parts,textures)):
    meta=assets.convert(root/'model.ff3d',root/'out',portable_paths.read_asset,animated=True)
   self.assertEqual(meta['original_compressed_textures'],[0,1])
   for i in range(2):self.assertEqual((root/f'out/atlas_{i}.rx3').read_bytes(),assets.original_texture(textures[i],portable_paths.read_asset('data/sceneassets/prop/prop_102_textures.rx3'),'xi_cm'))
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
