"""Static draw data must preserve the pose and use the player's material input."""
from pathlib import Path
import hashlib,json,struct,tempfile,unittest
from unittest.mock import patch
import static_stream
from rx3 import Rx3,VERTEX
from native_assets import player_coefficient

class StaticStreamTests(unittest.TestCase):
 def source(self,root):
  # A three-vertex slot is valid geometry too; the other slot is a dummy.
  import numpy as np
  from native_assets import STRIDE,geometry
  import portable_paths
  v=np.zeros(3,dtype=STRIDE);v['p']=[[1,0,0],[0,2,0],[0,0,3]];v['n']=[0,1,0];v['uv']=[[0,0],[1,0],[0,1]]
  raw=geometry([(v,np.array([0,1,2],dtype='<u4'))],portable_paths.read_asset('data/sceneassets/prop/prop_102.rx3'))
  (root/'geometry.rx3').write_bytes(raw);(root/'assets.json').write_text(json.dumps(dict(used_slots=[0],pages=1)))
  return portable_paths.read_asset
 def test_constant_stream_preserves_every_vertex_byte_and_original_geometry(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);read=self.source(root);original=(root/'geometry.rx3').read_bytes()
   meta=static_stream.prepare(root,read);raw=(root/'animation.bin').read_bytes()
   self.assertEqual(raw[:8],b'FFPVTX01');self.assertEqual(struct.unpack_from('<IIIf',raw,8),(1,2,0,1.))
   self.assertEqual(struct.unpack_from('<II',raw,24),(0,3))
   frame=Rx3(original).get(VERTEX)[0][16:16+60]
   self.assertEqual(raw[32:],frame+frame)
   self.assertEqual((root/'geometry.rx3').read_bytes(),original)
   self.assertEqual((root/'neutral_coeff.rx3').read_bytes(),player_coefficient(read('data/sceneassets/prop/prop_102_textures.rx3')))
   self.assertEqual(meta['stable_geometry_stream'],'constant_frames_v1')
 def test_invalid_slots_are_refused_before_publishing_a_stream(self):
  for slots in ([],[1],[0,0],[-1],['0']):
   with self.subTest(slots=slots),tempfile.TemporaryDirectory() as temp:
    root=Path(temp);read=self.source(root);(root/'assets.json').write_text(json.dumps(dict(used_slots=slots)))
    with self.assertRaises(ValueError):static_stream.prepare(root,read)
    self.assertFalse((root/'animation.bin').exists())
if __name__=='__main__':unittest.main()
