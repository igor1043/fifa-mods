"""Exercise the native celebration with authored club meshes, not mock bones."""
import hashlib,json,struct,tempfile,unittest
from pathlib import Path
import mascot_animation,mascot_worker,portable_paths
from native_assets import convert
from static_stream import prepare
from rx3 import Rx3,VERTEX

class MascotAnimationTests(unittest.TestCase):
 def test_club_meshes_keep_native_pose_uvs_sources_and_cancel_before_publish(self):
  game=portable_paths.GAME
  clip=Path(__file__).resolve().parents[2]/'data/club_browser/mascot_celebration.json'
  for club in (1043,111046,1629):
   with self.subTest(club=club),tempfile.TemporaryDirectory() as temp:
    paths=mascot_worker.package(game,club)
    self.assertIsNotNone(paths)
    source=[p.read_bytes() for p in paths];folder=Path(temp);blob,_=mascot_worker.model_bytes(*source)
    (folder/'model.ff3d').write_bytes(blob)
    convert(folder/'model.ff3d',folder/'native',portable_paths.read_asset)
    prepare(folder/'native',portable_paths.read_asset)
    geometry=(folder/'native/geometry.rx3').read_bytes();buffers=Rx3(geometry).get(VERTEX)
    meta=mascot_animation.prepare(source[0],clip,folder/'native')
    raw=(folder/'native/animation.bin').read_bytes();parts,count,player,duration=struct.unpack_from('<IIIf',raw,8)
    self.assertEqual(raw[:8],b'FFPVTX01');self.assertEqual(player,0);self.assertGreaterEqual(count,12)
    self.assertLessEqual(count,64);self.assertLessEqual(len(raw),mascot_animation.MAX_BYTES);self.assertGreater(duration,7)
    at=24
    for _ in range(parts):
     slot,n=struct.unpack_from('<II',raw,at);at+=8;size=n*20;frames=raw[at:at+size*count];at+=size*count
     original=buffers[slot][16:16+size]
     self.assertEqual(frames[:size],original);self.assertEqual(frames[-size:],original)
     self.assertNotEqual(frames[size*(count//2):size*(count//2+1)],original)
     for frame in range(count):
      self.assertEqual(b''.join(frames[frame*size+i*20+16:frame*size+i*20+20] for i in range(n)),b''.join(original[i*20+16:i*20+20] for i in range(n)))
    self.assertEqual(at,len(raw));self.assertEqual(meta['celebration'],1)
    with self.assertRaises(InterruptedError):mascot_animation.prepare(source[0],clip,folder/'native',lambda:True)
    self.assertEqual((folder/'native/animation.bin').read_bytes(),raw)
    self.assertEqual((folder/'native/geometry.rx3').read_bytes(),geometry)
    self.assertEqual([p.read_bytes() for p in paths],source)

if __name__=='__main__':unittest.main()
