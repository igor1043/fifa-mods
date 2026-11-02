import copy,json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'club_environment/manager_market'))
from derived_campaigns import augment,ready
from global_performance import project

class DerivedCampaignsTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.game=self.root/'game';self.save=self.root/'saves/slot/DATA';self.save.parent.mkdir(parents=True);self.save.write_bytes(b'validated-career-A');self.raw=self.save.read_bytes()
  self.path=self.game/'ModCarrerMode/runtime/career_fce_snapshot.json';self.path.parent.mkdir(parents=True)
  nodes=[[932,-1,3,53,0],[933,932,4,-1,0],[934,933,5,-1,0],[11,-1,3,999,0],[12,11,4,-1,0],[13,12,5,-1,0]]
  self.base=dict(date=20260810,nodes=nodes,fixtures=[],stats=[],standings=[[3099,934,241,0,0,0,0,0,0,0],[3100,934,242,0,0,0,0,0,0,0],[90,13,777,0,0,0,0,0,0,0]])
  stat=self.save.stat();self.pub=dict(self.base,schema=3,pid=55,processCreated100ns=123,savePath=str(self.save),saveSize=stat.st_size,saveWriteTime100ns=stat.st_mtime_ns//100+116444736000000000,derivedStandings=[[3099,934,241,3,0,0,2,0,0,5,9,0,4,1],[90,13,777,1,1,0,0,1,1,4,4,1,2,3]])
 def tearDown(self):self.tmp.cleanup()
 def write(self):self.path.write_text(json.dumps(self.pub),encoding='utf8')
 def test_all_competitions_and_saved_cache_without_running_process(self):
  self.write();result=augment(self.game,self.save,self.raw,self.base,20260810,55,123)
  self.assertEqual([5,0,4],[r[9] for r in result['standings']]);self.assertEqual([9,0,4,1],result['standingGoals']['3099'])
  p=project(result,[],{241:53,242:53,777:999},[],20260810,20260109,20260810)
  barca=next(r for r in p['performance'] if r['club']==241);self.assertEqual((5,3,2,13),(barca['played'],barca['hw'],barca['aw'],barca['hgf']+barca['agf']))
  self.path.unlink();self.assertEqual(result,augment(self.game,self.save,self.raw,self.base))
 def test_wrong_process_save_and_future_date_cannot_leak(self):
  for key,value in [('pid',999),('date',20260811),('saveSize',999),('processCreated100ns',999),('savePath',str(self.root/'other/DATA'))]:
   with self.subTest(key=key):
    previous=self.pub[key];self.pub[key]=value;self.write();self.assertEqual(self.base,augment(self.game,self.save,self.raw,self.base,20260810,55,123));self.pub[key]=previous
 def test_bad_or_conflicting_slot_rejects_whole_supplement(self):
  for row in [[3099,934,666,3,0,0,2,0,0,5,9,0,4,1],[3099,934,241,3,0,0,2,0,0,6,9,0,4,1]]:
   self.pub['derivedStandings']=[row];self.write();self.assertEqual(self.base,augment(self.game,self.save,self.raw,self.base,20260810,55,123))
 def test_rollback_and_other_career_have_distinct_cache(self):
  self.write();augment(self.game,self.save,self.raw,self.base,20260810,55,123);self.path.unlink();self.save.write_bytes(b'validated-career-B')
  self.assertEqual(self.base,augment(self.game,self.save,self.save.read_bytes(),self.base))
  self.assertEqual(dict(self.base,date=20260701),augment(self.game,self.save,self.raw,dict(self.base,date=20260701)))
 def test_background_publication_requires_same_native_context(self):
  rows=self.pub.pop('derivedStandings');self.pub['derivedStandings']=[];self.pub['fceContextEpoch']=8;self.write()
  extra=self.path.with_name('career_derived_standings.json')
  extra.write_text(json.dumps(dict(schema=1,pid=55,created=123,epoch=7,date=20260810,rows=rows)))
  self.assertEqual([],augment(self.game,self.save,self.raw,self.base,20260810,55,123)['derived_slots'])
  extra.write_text(json.dumps(dict(schema=1,pid=55,created=123,epoch=8,date=20260810,rows=rows)))
  self.assertEqual([3099,90],list(map(lambda r:r[0],[r for r in augment(self.game,self.save,self.raw,self.base,20260810,55,123)['standings'] if r[9]])))
 def test_ready_requires_completed_batch_for_this_career_not_previous_process(self):
  self.pub['fceContextEpoch']=8;self.write();saved=dict(path=str(self.save),pid=55,process_created_100ns=123);profile=dict(context_epoch=8)
  self.assertFalse(ready(self.game,saved,profile,20260810,self.pub))
  extra=self.path.with_name('career_derived_standings.json');state=dict(schema=1,pid=55,created=123,epoch=8,date=20260810,rows=[]);extra.write_text(json.dumps(state))
  self.assertTrue(ready(self.game,saved,profile,20260810,self.pub))
  for key,value in [('pid',54),('epoch',9),('date',20260809),('created',124)]:
   changed=dict(state);changed[key]=value;extra.write_text(json.dumps(changed));self.assertFalse(ready(self.game,saved,profile,20260810,self.pub))
 def test_current_career_may_add_competitions_and_slots_after_last_save(self):
  self.pub['nodes']+= [[200,-1,3,1234,0],[201,200,4,-1,0],[202,201,5,-1,0]]
  self.pub['standings']+=[[999,202,888,1,0,0,0,1,0,2]]
  self.pub['fixtures']=[[700,202,202,20260809,1600,888,889,2,0,1,1]]
  self.pub['derivedStandings']+=[[999,202,888,1,0,0,0,1,0,2,2,0,1,1]]
  self.write();result=augment(self.game,self.save,self.raw,self.base,20260810,55,123)
  self.assertEqual('save_bound_native',result['source'])
  self.assertIn(999,result['derived_slots']);self.assertEqual(700,result['fixtures'][0][0])
 def test_current_fixtures_do_not_wait_for_optional_foreign_supplement(self):
  self.pub.pop('derivedStandings');self.pub['fixtures']=[[700,934,934,20260809,1600,241,242,2,0,1,1]]
  self.pub['fceContextEpoch']=8;self.write()
  result=augment(self.game,self.save,self.raw,self.base,20260810,55,123,8)
  self.assertEqual(700,result['fixtures'][0][0]);self.assertEqual([],result['derived_slots'])
  self.assertEqual(self.base,augment(self.game,self.save,self.raw,self.base,20260810,55,123,9))
 def test_live_identity_failure_cannot_fall_back_to_previous_unsaved_session_cache(self):
  self.pub['fceContextEpoch']=8;self.write()
  self.assertEqual('save_bound_native',augment(self.game,self.save,self.raw,self.base,20260810,55,123,8)['source'])
  self.pub['pid']=56;self.write()
  self.assertEqual(self.base,augment(self.game,self.save,self.raw,self.base,20260810,55,123,8))

if __name__=='__main__':unittest.main()
