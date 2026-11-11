"""Validate actual room geometry centers and the small auxiliary material assets."""
import tempfile,unittest,json
from pathlib import Path
import numpy as np
from rx3 import Rx3,TEXTURE
import portable_paths as portable
from room_lighting_assets import geometry_probe,ensure_materials,PROFILES
from room_texture_tools import color_image

class LightingAssetsTests(unittest.TestCase):
 def test_current_room_submeshes_have_finite_distinct_centers(self):
  path=portable.ROOM/'runtime/native_components_v2.txt'
  import shlex
  lines=iter(path.read_text().splitlines());header=next(lines).split();version=int(header[1]);centers=[]
  for _ in range(int(header[-1])):
   fields=shlex.split(next(lines),posix=True)
   center=geometry_probe(fields[1],fields[2],portable.read_asset)
   self.assertEqual(len(center),4);self.assertTrue(np.isfinite(center).all());self.assertGreater(center[3],0)
   centers.append(center[:3])
   if version>=4:next(lines)
   for _ in range(int(fields[6])):next(lines)
  self.assertGreater(len(centers),100)
  self.assertGreater(np.ptp(np.asarray(centers)[:,2]),1000)
  with self.assertRaises(ValueError):geometry_probe(fields[1],'missing-room-submesh',portable.read_asset)

 def test_materials_are_small_complete_and_repeatable(self):
  with tempfile.TemporaryDirectory() as folder:
   paths=[Path(p) for p in ensure_materials(folder)]
   original=[p.read_bytes() for p in paths];ensure_materials(folder)
   self.assertEqual(original,[p.read_bytes() for p in paths]);self.assertEqual(len(paths),4)
   self.assertLess(sum(p.stat().st_size for p in paths),16384)
   for (name,rgba),data in zip(PROFILES.items(),original):
    self.assertEqual(Rx3(data).names(),[(TEXTURE,'_nm'),(TEXTURE,'_coeff')])
    normal=np.asarray(color_image(data,'_nm')).astype(int);coeff=np.asarray(color_image(data,'_coeff')).astype(int)
    self.assertTrue(np.all(abs(normal[:,:,:3]-[128,128,255])<=4))
    self.assertTrue(np.all(abs(coeff[:,:,:3]-rgba[:3])<=4),name)

if __name__=='__main__':unittest.main()
