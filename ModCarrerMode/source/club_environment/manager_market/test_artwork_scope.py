from pathlib import Path
from tempfile import TemporaryDirectory
import copy,unittest
from asset_cache import revision

class ArtworkScopeTest(unittest.TestCase):
 def test_saved_month_titles_and_formation_do_not_invalidate_installed_artwork(self):
  with TemporaryDirectory() as tmp:
   game=Path(tmp);folder=game/'data/ui/imgAssets/careerCompetitionIcons';folder.mkdir(parents=True);(folder/'1009.png').write_bytes(b'installed icon')
   model=dict(people=[dict(image='face.png',formation='4-3-3',head='head_a',career=dict(titles=[]))],clubRows=[],hireRows=[],moveRows=[],leagues=[],countries=[])
   changed=copy.deepcopy(model);changed['people'][0].update(formation='4-4-2',career=dict(titles=[dict(competition=1009)]))
   self.assertEqual(revision(game,model),revision(game,changed))
   before=revision(game,model);(folder/'1009.png').write_bytes(b'new installed icon');self.assertNotEqual(before,revision(game,model))

if __name__=='__main__':unittest.main()
