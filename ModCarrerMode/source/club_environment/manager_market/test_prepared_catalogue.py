from pathlib import Path
import copy,tempfile,unittest
from unittest.mock import patch
import test_screen
import asset_cache,prepared_catalogue

class PreparedCatalogueTest(unittest.TestCase):
 def model(self):return dict(people=[dict(image='minifaces/face.png',head='head_face',career=dict(titles=[]))],clubRows=[],hireRows=[],moveRows=[],leagues=[],countries=[])
 def test_sources_are_portable_and_changed_bytes_reject_the_bundle(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);a=root/'one';b=root/'different installation';model=self.model()
   for game in (a,b):
    folder=game/'ModCarrerMode/data/manager_market/minifaces';folder.mkdir(parents=True);(folder/'face.png').write_bytes(b'same face');(folder/'NOTFOUND_DEFAULT.png').write_bytes(b'default')
   with patch('portable_paths.read_asset',side_effect=FileNotFoundError):
    first=prepared_catalogue.fingerprint(a,model,'a');self.assertEqual(first,prepared_catalogue.fingerprint(b,model,'b'))
    (b/'ModCarrerMode/data/manager_market/minifaces/face.png').write_bytes(b'other face')
    self.assertNotEqual(first,prepared_catalogue.fingerprint(b,model,'changed'))
 def test_installed_competitions_keep_the_same_visual_pool_before_and_after_a_title(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);folder=game/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata';folder.mkdir(parents=True);(folder/'compobj.txt').write_text('1,3,C9,Cup,0\n2,3,C1009,Other cup,0\n')
   model=self.model();changed=copy.deepcopy(model);changed['people'][0]['career']['titles']=[dict(competition=1009)]
   self.assertEqual({9,1009},asset_cache.competition_ids(game,model));self.assertEqual(asset_cache.competition_ids(game,model),asset_cache.competition_ids(game,changed))
 def test_geometry_or_input_mismatch_rejects_a_distributed_template(self):
  import json
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);folder=game/'ModCarrerMode/data/manager_market/interface';folder.mkdir(parents=True);(folder/'recipe.json').write_text(json.dumps(dict(schema=1,geometry='g',sources='s')))
   with patch.object(prepared_catalogue,'fingerprint',return_value='s'):
    self.assertEqual(folder/'catalogue.big',prepared_catalogue.template(game,self.model(),'g','revision'))
    self.assertIsNone(prepared_catalogue.template(game,self.model(),'other code','revision'))
   with patch.object(prepared_catalogue,'fingerprint',return_value='other art'):self.assertIsNone(prepared_catalogue.template(game,self.model(),'g','revision'))
 def test_native_trophy_alias_is_cached_before_the_first_title(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);folder=game/'dlc/dlc_FootballCompEng/dlc/FootballCompEng/data/compdata';folder.mkdir(parents=True)
   (folder/'compobj.txt').write_text('1407,3,C100,TrophyName_Abbr15_1009,1384\n')
   model=self.model();changed=copy.deepcopy(model);changed['people'][0]['career']['titles']=[dict(competition=1009)]
   self.assertEqual({100,1009},asset_cache.competition_ids(game,model))
   self.assertEqual(asset_cache.revision(game,model),asset_cache.revision(game,changed))

if __name__=='__main__':unittest.main()
