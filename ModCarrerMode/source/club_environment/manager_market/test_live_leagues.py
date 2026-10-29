from pathlib import Path
import tempfile,unittest
from live_leagues import read,FIELDS
from global_performance import project

class LiveLeagueTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'live.tsv';self.observed=dict(save=dict(pid=10,process_created_100ns=20),profile=dict(club_id=3,context_address=30,registry_address=40,context_epoch=2),date=20260401)
  self.headers=dict(schema=1,pid=10,process_created_100ns=20,epoch=2,context='1e',registry='28',club=3,date=20260401,captured_ms=1000,complete=1)
  self.rows=[dict(teamid=i,leagueid=100,secondarytable=0,nummatchesplayed=12,points=18,homewins=2,homedraws=3,homelosses=1,awaywins=2,awaydraws=3,awaylosses=1,homegf=8,homega=9,awaygf=8,awayga=9,currenttableposition=i) for i in (1,2,3)]
 def tearDown(self):self.tmp.cleanup()
 def write(self):
  self.path.write_text(''.join(f'{k}={v}\n' for k,v in self.headers.items())+''.join('league='+','.join(str(r[k]) for k in FIELDS)+'\n' for r in self.rows),encoding='ascii')
 def test_current_native_rows_enable_global_tables_without_saving(self):
  self.write();live=read(self.path,self.observed,1010);projection=project(dict(nodes=[],standings=[]),[],{1:100,2:100,3:100},live['rows'],live['date'],20260101,20260401,'live_league')
  self.assertTrue(projection['coverage']['live_database']);self.assertEqual(1,projection['coverage']['live_league_tables']);self.assertEqual(20260401,projection['table_dates']['100']);self.assertTrue(all(r['source']=='live_league' for r in projection['performance']))
 def test_other_pid_session_club_epoch_date_and_incomplete_snapshots_are_rejected(self):
  for key in ('schema','pid','process_created_100ns','epoch','club','date','complete'):
   previous=self.headers[key];self.headers[key]=previous+1;self.write()
   with self.assertRaises(ValueError):read(self.path,self.observed,1010)
   self.headers[key]=previous
  self.headers['context']='ff';self.write()
  with self.assertRaises(ValueError):read(self.path,self.observed,1010)
 def test_stale_oversized_and_duplicate_snapshots_are_rejected(self):
  self.write()
  with self.assertRaises(ValueError):read(self.path,self.observed,14000)
  self.rows.append(self.rows[0]);self.write()
  with self.assertRaises(ValueError):read(self.path,self.observed,1010)
  self.path.write_bytes(b'x'*(4*1024*1024+1))
  with self.assertRaises(ValueError):read(self.path,self.observed,1010)
 def test_capture_heartbeat_does_not_rebuild_unchanged_data(self):
  self.write();one=read(self.path,self.observed,1010);self.headers['captured_ms']=1100;self.write();two=read(self.path,self.observed,1110);self.assertEqual(one['revision'],two['revision']);self.rows[0]['homewins']+=1;self.write();three=read(self.path,self.observed,1110);self.assertNotEqual(two['revision'],three['revision'])

if __name__=='__main__':unittest.main()
