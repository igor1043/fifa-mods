"""Verify the installed V3 floor round-trip without moving its geometry."""
from pathlib import Path
import json,tempfile,unittest
import numpy as np
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh
from room_v3 import align_floor_uv,FLOOR_TILE_CM,PREFIX
import portable_paths as portable

class FloorUV(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  root=portable.GAME/PREFIX;manifest=json.loads((root/'manifest.json').read_bytes())
  cls.original=(root/manifest['model_files']['room_roles.rx3']).read_bytes()
 def test_native_roundtrip_changes_only_floor_uvs(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'floor.rx3';path.write_bytes(self.original);before=Rx3(self.original)
   old,indices=read_mesh(before,2);align_floor_uv(path);after=Rx3(path.read_bytes());new,new_indices=read_mesh(after,2)
   for field in ('p','n','g'):np.testing.assert_array_equal(new[field],old[field])
   np.testing.assert_array_equal(indices,new_indices)
   expected=(new['p'][:,[0,2]].astype(float)/FLOOR_TILE_CM).astype(new['uv'].dtype)
   np.testing.assert_array_equal(new['uv'],expected)
   self.assertEqual(len(before.sections),len(after.sections));seen=0
   for a,b in zip(before.sections,after.sections):
    self.assertEqual(a[0],b[0])
    if a[0]==VERTEX:
     if seen==2:seen+=1;continue
     seen+=1
    self.assertEqual(a[1],b[1],'Unrelated native mesh/material/index section changed')
   once=path.read_bytes();align_floor_uv(path);self.assertEqual(path.read_bytes(),once)
 def test_main_room_and_both_annexes_share_the_same_tile_origin_and_scale(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'floor.rx3';path.write_bytes(self.original);align_floor_uv(path)
   v,ids=read_mesh(Rx3(path.read_bytes()),2);used=np.unique(ids);p=v['p'][used].astype(float);uv=v['uv'][used].astype(float)
   self.assertTrue((p[:,2]<1500).any());self.assertTrue((p[:,2]>1600).any())
   # Native half-float UV precision, at the retained original room scale.
   np.testing.assert_allclose(uv,p[:,[0,2]]/60,atol=.016,rtol=0)
   self.assertEqual(FLOOR_TILE_CM,60.)

if __name__=='__main__':unittest.main()
