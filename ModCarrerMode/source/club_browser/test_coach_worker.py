"""Publication policy: missing coach assets must not hide the club's profile."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch,Mock
import unittest
import coach_worker as worker

class CoachWorker(unittest.TestCase):
 def setup_job(self,temp):
  game=Path(temp);folder=game/'runtime';folder.mkdir();tool=game/'ModCarrerMode/tools/club_browser/generate_lineup.exe';tool.parent.mkdir(parents=True);tool.write_bytes(b'tool');clip=game/'ModCarrerMode/data/club_browser/animations/coach_crossed.json';clip.parent.mkdir(parents=True);clip.write_bytes(b'clip')
  req=dict(schema=1,pid=42,seq=9,club=1043,kind='coach');saved=dict(path=str(game/'READ_ONLY_SAVE'),size=200,mtime_ns=100)
  data=dict(club=1043,fixture=b'FFCOACH1',fields={},stats={},competitions=[],history=[],starters=[],club_name='Club')
  return game,folder,req,saved,data
 def test_missing_own_coach_preserves_profile_without_cross_club_fallback(self):
  with TemporaryDirectory() as temp:
   game,folder,req,saved,data=self.setup_job(temp);publish=Mock();exporter=Mock()
   with patch.object(worker,'observe',return_value=(saved,(1,2,1043))),patch.object(worker,'competition_session',return_value={}),patch.object(worker,'season_current',return_value=None),patch.object(worker,'project',return_value=data),patch.object(worker,'tsv',return_value=b'profile'),patch.object(worker,'request',return_value=req),patch.object(worker,'publish',publish),patch.object(worker.portable_paths,'read_asset',return_value=b'') as asset:
    self.assertTrue(worker.generate(game,folder,req,Mock(),exporter,Mock()))
   self.assertEqual((folder/'coach.tsv').read_bytes(),b'profile');exporter.run.assert_not_called()
   publish.assert_called_once();self.assertEqual(publish.call_args.kwargs['actor'],0);self.assertEqual(publish.call_args.kwargs['kind'],'coach')
   self.assertEqual(asset.call_args.args[0],'data/sceneassets/slc/specificmanager_1043_0_0.rx3')
 def test_career_change_cannot_publish_old_profile_or_model(self):
  with TemporaryDirectory() as temp:
   game,folder,req,saved,data=self.setup_job(temp);publish=Mock();exporter=Mock()
   with patch.object(worker,'observe',side_effect=[(saved,(1,2,1043)),(saved,(1,3,1629))]),patch.object(worker,'competition_session',return_value={}),patch.object(worker,'season_current',return_value=None),patch.object(worker,'project',return_value=data),patch.object(worker,'request',return_value=req),patch.object(worker,'publish',publish):
    self.assertFalse(worker.generate(game,folder,req,Mock(),exporter,Mock()))
   publish.assert_not_called();exporter.run.assert_not_called();self.assertFalse((folder/'coach.tsv').exists())

if __name__=='__main__':unittest.main()
