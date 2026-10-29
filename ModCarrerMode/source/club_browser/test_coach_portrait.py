from pathlib import Path
import sqlite3,tempfile,unittest
from contextlib import closing
from coach_portrait import portrait,installed,DEFAULT
from coach_data import attach_market,tsv

class CoachPortrait(unittest.TestCase):
 def fixture(self,temp):
  game=Path(temp);folder=game/'ModCarrerMode/data/manager_market';(folder/'minifaces').mkdir(parents=True)
  for name in ('000183.png','other.png','NOTFOUND_DEFAULT.png'):(folder/'minifaces'/name).write_bytes(b'unchanged artwork')
  db=sqlite3.connect(folder/'catalog.sqlite3');db.execute('CREATE TABLE coaches(name TEXT,image TEXT)')
  db.executemany('INSERT INTO coaches VALUES(?,?)',[('Abel Braga','minifaces/000183.png'),('José Coach','minifaces/other.png')]);db.commit();db.close()
  return game,folder
 def test_saved_identity_uses_existing_catalogue_without_duplicate_assets(self):
  with tempfile.TemporaryDirectory() as temp:
   game,folder=self.fixture(temp);before={str(p):p.read_bytes() for p in folder.rglob('*') if p.is_file()}
   self.assertEqual(portrait(game,'ABEL BRAGA'),'minifaces/000183.png')
   self.assertEqual(portrait(game,'Jose  Coach'),'minifaces/other.png')
   self.assertEqual({str(p):p.read_bytes() for p in folder.rglob('*') if p.is_file()},before)
 def test_active_appointment_is_authoritative_even_with_renamed_coach(self):
  with tempfile.TemporaryDirectory() as temp:
   game,_=self.fixture(temp)
   self.assertEqual(portrait(game,'Different display name',dict(image='minifaces/other.png')),'minifaces/other.png')
   self.assertEqual(portrait(game,'Abel Braga',dict(image='minifaces/missing.png')),DEFAULT)
 def test_missing_and_ambiguous_identity_never_borrow_another_coachs_photo(self):
  with tempfile.TemporaryDirectory() as temp:
   game,folder=self.fixture(temp)
   self.assertEqual(portrait(game,'Not registered'),DEFAULT)
   with closing(sqlite3.connect(folder/'catalog.sqlite3')) as db,db:db.execute("INSERT INTO coaches VALUES('Abel Braga','minifaces/other.png')")
   self.assertEqual(portrait(game,'Abel Braga'),DEFAULT)
 def test_external_paths_and_nested_paths_are_rejected(self):
  with tempfile.TemporaryDirectory() as temp:
   game,folder=self.fixture(temp)
   for path in ('C:/outside.png','../outside.png','minifaces/../outside.png','minifaces/folder/photo.png','minifaces/other.jpg',None):
    self.assertIsNone(installed(folder,path));self.assertEqual(portrait(game,'Abel Braga',dict(image=path)),DEFAULT)
 def test_absent_catalogue_has_a_safe_placeholder(self):
  with tempfile.TemporaryDirectory() as temp:self.assertEqual(portrait(temp,'Abel Braga'),DEFAULT)
 def test_profile_refresh_replaces_photo_together_with_current_coach(self):
  with tempfile.TemporaryDirectory() as temp:
   game,_=self.fixture(temp)
   data=dict(club=567,club_name='Club',fields=dict(date=20261123),stats={},coach_stats={},competitions=[],history=[],starters=[])
   market=dict(coach=dict(coach_id='USER-1',name='Human',nationality='',image='minifaces/000183.png'),appointment=dict(monthly_wage=100),start=20261123,appointments=['a'],initial=True,results=[])
   attach_market(data,market,None,game)
   self.assertEqual(data['fields']['portrait'],'minifaces/000183.png')
   market['coach']['image']='minifaces/other.png';attach_market(data,market,None,game)
   self.assertEqual(data['fields']['portrait'],'minifaces/other.png')
   self.assertIn(b'F\tportrait\tminifaces/other.png',tsv(data))

if __name__=='__main__':unittest.main()
