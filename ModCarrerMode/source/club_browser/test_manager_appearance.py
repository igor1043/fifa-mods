"""Per-save identity and completed-save binding, without modifying FIFA DATA."""
from pathlib import Path,PureWindowsPath
from contextlib import closing
import tempfile,unittest
from unittest.mock import patch
import json
import manager_appearance as a

class Appearance(unittest.TestCase):
 def test_extended_windows_save_path_is_read_only_and_never_a_question_mark_authority(self):
  for path,expected in ((r'\\?\C:\Users\Robson\save #1\aparência.sqlite3','file:///C:/Users/Robson/save%20%231/apar%C3%AAncia.sqlite3?mode=ro'),
                        (r'\\?\UNC\server\share\save\appearance.sqlite3','file:////server/share/save/appearance.sqlite3?mode=ro')):
   with patch.object(Path,'resolve',return_value=PureWindowsPath(path)):
    self.assertEqual(a.readonly_uri(path),expected)
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'save #1 aparência'/'DATA';save.parent.mkdir();save.write_bytes(b'native save')
   digest=a.snapshot(save);choice=dict(coach='COACH-X',asset=1)
   database=a.save(save,digest,choice,1,100)
   with patch.object(Path,'resolve',return_value=Path('\\\\?\\'+str(database.resolve()))):
    self.assertEqual(a.load(save,digest),choice)
   import sqlite3
   with closing(sqlite3.connect(a.readonly_uri(database),uri=True)) as db:
    with self.assertRaises(sqlite3.OperationalError):db.execute('DELETE FROM appearances')
 def test_two_careers_same_club_are_independent_and_native_data_unchanged(self):
  with tempfile.TemporaryDirectory() as folder:
   files=[]
   for name in ('one','two'):
    save=Path(folder)/name/'DATA';save.parent.mkdir();save.write_bytes(b'career-'+name.encode());files.append(save)
   one,two=files;before=one.read_bytes();digest=a.snapshot(one)
   choice=dict(coach='COACH-TITE',asset=1043)
   a.save(one,digest,choice,1,100)
   self.assertEqual(a.load(one,digest),choice);self.assertIsNone(a.load(two,a.snapshot(two)))
   self.assertEqual(one.read_bytes(),before)
   # A transfer/new native save keeps the same human appearance, not its club.
   one.write_bytes(b'new-club');next_digest=a.snapshot(one);a.save(one,next_digest,choice,2,200)
   self.assertEqual(a.load(one,next_digest),choice);self.assertEqual(a.load(one,digest),choice)
   a.save(one,next_digest,None,2,300);self.assertIsNone(a.load(one,next_digest))
   self.assertEqual(a.load_record(one,next_digest),dict(coach='',asset=0));self.assertIsNone(a.load_record(two,a.snapshot(two)))

 def test_only_confirmed_creation_binds_after_completed_write(self):
  draft=dict(schema='1',pid='42',created='101',phase='initializing',confirmed='1',armed_tick='300',coach='COACH-TITE',asset='1043')
  args=dict(pid=42,created=101,event_tick=301,operation='write',allowed={'COACH-TITE':1043})
  self.assertEqual(a.selected(draft,**args),dict(coach='COACH-TITE',asset=1043))
  for change in ({'pid':'43'},{'created':'102'},{'phase':'preferences'},{'phase':'abandoned'},{'confirmed':'0'},{'asset':'1'},{'armed_tick':'302'}):
   self.assertIsNone(a.selected(dict(draft,**change),**args),change)
  self.assertIsNone(a.selected(draft,**dict(args,operation='read')))
  self.assertIsNone(a.selected(draft,**dict(args,event_tick=300)))

 def test_snapshot_index_is_bounded(self):
  with tempfile.TemporaryDirectory() as folder:
   save=Path(folder)/'DATA';save.write_bytes(b'original')
   for i in range(132):a.save(save,f'{i:064x}',None,1,i)
   self.assertIsNone(a.load(save,f'{0:064x}'))
   import sqlite3
   with closing(sqlite3.connect(save.parent/a.NAME)) as db:self.assertEqual(db.execute('SELECT count(*) FROM appearances').fetchone()[0],128)

 def test_actor_rejects_other_save_or_reused_pid(self):
  with tempfile.TemporaryDirectory() as folder:
   file=Path(folder)/'ModCarrerMode/runtime/user_manager/active.json';file.parent.mkdir(parents=True)
   state=dict(pid=7,created=42,context=1000,epoch=9,club=1,path='C:/saves/one/DATA',coach='COACH-X',asset=517)
   file.write_text(json.dumps(state));scope=dict(pid=7,created=42,context_address=1000,context_epoch=9,save_path='C:/saves/one/DATA')
   row=dict(coachId='COACH-X',assetId=517)
   with patch('manager_market.model_assets.catalog',return_value={'COACH-X':row}),patch('manager_market.model_assets.installed',return_value=True):
    self.assertEqual(a.actor(folder,1,scope)['assetId'],517)
    for change in (dict(created=43),dict(context_epoch=10),dict(save_path='C:/saves/two/DATA')):self.assertIsNone(a.actor(folder,1,dict(scope,**change)))
    self.assertIsNone(a.actor(folder,2,scope))

if __name__=='__main__':unittest.main()
