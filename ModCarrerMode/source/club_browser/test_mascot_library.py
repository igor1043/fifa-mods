import hashlib,json,struct,tempfile,unittest
from pathlib import Path
import mascot_animation,mascot_worker,portable_paths
from native_assets import convert
from static_stream import prepare
from rx3 import Rx3,VERTEX

class MascotLibraryTests(unittest.TestCase):
 def test_four_native_crowd_reactions_share_one_bounded_stream(self):
  library=Path(__file__).resolve().parents[2]/'data/club_browser/mascot_celebrations.json'
  records=json.loads(library.read_text(encoding='utf8'))['clips']
  self.assertEqual({108,129,121,109},{r['native_clip'] for r in records})
  for club in (1043,1629):
   with self.subTest(club=club),tempfile.TemporaryDirectory() as folder:
    paths=mascot_worker.package(portable_paths.GAME,club);original=[p.read_bytes() for p in paths];model,texture=original
    raw,_=mascot_worker.model_bytes(model,texture);root=Path(folder);(root/'model.ff3d').write_bytes(raw)
    convert(root/'model.ff3d',root/'native',portable_paths.read_asset,root/'materials');prepare(root/'native',portable_paths.read_asset)
    meta=mascot_animation.prepare(model,library,root/'native');blob=(root/'native/animation.bin').read_bytes()
    self.assertLessEqual(len(blob),mascot_animation.MAX_BYTES);self.assertEqual(4,len(meta['animation_variants']))
    lines=(root/'native/variants.tsv').read_text().splitlines();self.assertEqual('S16MASCOTCLIPS 1 4',lines[0]);ranges=[tuple(map(float,l.split())) for l in lines[1:]]
    parts,count,_,seconds=struct.unpack_from('<IIIf',blob,8);self.assertLessEqual(count,64);self.assertLessEqual(seconds,20)
    buffers=Rx3((root/'native/geometry.rx3').read_bytes()).get(VERTEX);at=24
    for _ in range(parts):
     slot,vertices=struct.unpack_from('<II',blob,at);at+=8;size=vertices*20;initial=buffers[slot][16:16+size]
     for first,last,duration in ranges:
      self.assertEqual(initial,blob[at+int(first)*size:at+(int(first)+1)*size]);self.assertEqual(initial,blob[at+int(last)*size:at+(int(last)+1)*size])
     at+=size*count
    self.assertEqual(len(blob),at);self.assertEqual(original,[p.read_bytes() for p in paths])

if __name__=='__main__':unittest.main()
