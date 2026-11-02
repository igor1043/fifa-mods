from contextlib import closing
from pathlib import Path
import copy,json,sqlite3,tempfile,unittest,zlib
import competition_monthly as monthly

def snapshot(day=20260701,games=10,goals=3,rating=700):
 return dict(pid=123,processCreated100ns=456,club=11,date=day,nodes=[[100,0,3],[101,100,1]],stats=[[1,100,11,99,games,games*90,goals,2,rating,2]],fixtures=[])

class Monthly(unittest.TestCase):
 def test_root_totals_replace_child_stage_instead_of_double_counting(self):
  s=snapshot();s['stats']+=[[2,101,11,99,10,900,3,2,700,2],[3,100,11,99,9,810,2,1,630,2]]
  self.assertEqual(monthly.totals(s)['rows'],[[100,11,99,10,900,3,2,700,1]])
 def test_actual_monthly_delta_and_partial_history_label(self):
  before=monthly.totals(snapshot());s=snapshot(20260708,11,4,780);s['fixtures']=[[9,101,101,20260708,1900,11,22,2,0,1,1]]
  award=monthly.player_awards(before,monthly.totals(s),20260708,{99:{'name':'Atleta'}},lambda p:p['name'],{11:'Clube'})[100]
  self.assertEqual(award['games'],1);self.assertEqual(award['average'],8);self.assertEqual(award['goals'],1);self.assertTrue(award['partial']);self.assertEqual(award['month'],202607)
 def test_cross_month_calendar_jump_is_not_mislabeled_as_current_month(self):
  before=monthly.totals(snapshot(20260628));s=snapshot(20260708,12,4,860);s['fixtures']=[[8,101,101,20260630,1900,11,22,0,0,1,1],[9,101,101,20260708,1900,11,22,2,0,1,2]]
  self.assertEqual(monthly.player_awards(before,monthly.totals(s),20260708,{99:{}},lambda p:'Atleta',{}),{})
 def test_transfer_cumulative_history_cannot_win_one_month(self):
  before=monthly.totals(snapshot());before['rows']=[];s=snapshot(20260708,11,4,780);s['fixtures']=[[9,101,101,20260708,1900,11,22,2,0,1,1]]
  self.assertEqual(monthly.player_awards(before,monthly.totals(s),20260708,{99:{}},lambda p:'Atleta',{}),{})
 def test_same_day_before_and_after_match_are_both_retained(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'market.sqlite3';monthly.capture(path,'one',snapshot());monthly.capture(path,'one',snapshot(games=11,rating=780));monthly.capture(path,'one',snapshot(games=11,rating=780))
   with closing(sqlite3.connect(monthly.store_path(path))) as db:self.assertEqual(db.execute('SELECT count(*) FROM observations_v2').fetchone()[0],2)
 def test_saved_checkpoint_restores_evidence_without_future_or_other_career(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'market.sqlite3';monthly.capture(path,'old',snapshot(20260630));monthly.capture(path,'old',snapshot(20260708,11,4,780),'saved',checkpoint=True);monthly.capture(path,'old',snapshot(20260720,12,5,860))
   monthly.capture(path,'reloaded',snapshot(20260708,11,4,780),'saved');monthly.capture(path,'different',snapshot(20260708,11,4,780),'different-save')
   with closing(sqlite3.connect(monthly.store_path(path))) as db:
    self.assertEqual([r[0] for r in db.execute('SELECT day FROM observations_v2 WHERE branch=? ORDER BY day',('reloaded',))],[20260630,20260708])
    self.assertEqual(db.execute('SELECT count(*) FROM observations_v2 WHERE branch=?',('different',)).fetchone()[0],1)
   self.assertFalse(path.exists(),'Monthly capture must not modify the coach ledger or native save')
 def test_background_history_is_bounded_to_monthly_anchors(self):
  with tempfile.TemporaryDirectory() as t:
   path=Path(t)/'market.sqlite3';monthly.capture(path,'one',snapshot(20260630))
   for day in range(1,30):monthly.capture(path,'one',snapshot(20260700+day,games=10+day,rating=700+day*70))
   with closing(sqlite3.connect(monthly.store_path(path))) as db:self.assertEqual([r[0] for r in db.execute('SELECT day FROM observations_v2 ORDER BY day')],[20260630,20260701,20260729])
 def test_coach_award_uses_dated_coach_results_and_checks_session_identity(self):
  with tempfile.TemporaryDirectory() as t:
   game=Path(t);runtime=game/'ModCarrerMode/runtime/manager_market';runtime.mkdir(parents=True);save=game/'career.DATA';save.write_bytes(b'unchanged');database=game/'market.sqlite3'
   with closing(sqlite3.connect(database)) as db, db:
    db.executescript('CREATE TABLE coaches(branch TEXT,coach_id TEXT,name TEXT,image TEXT);CREATE TABLE results(branch TEXT,root INT,game_date INT,home INT,away INT,hg INT,ag INT,home_coach TEXT,away_coach TEXT);')
    db.execute('INSERT INTO coaches VALUES(?,?,?,?)',('branch','a','Técnico A','minifaces/a.png'));db.execute('INSERT INTO coaches VALUES(?,?,?,?)',('branch','b','Técnico B',''))
    db.executemany('INSERT INTO results VALUES(?,?,?,?,?,?,?,?,?)',[('branch',100,20260702,11,22,2,0,'a','b'),('branch',100,20260602,11,22,0,4,'a','b'),('branch',101,20260702,11,22,0,4,'a','b')])
   state=dict(pid=123,created=456,club=11,date=20260708,save=str(save),database=str(database),branch='branch');file=runtime/'state_ready.json';file.write_text(json.dumps(state))
   result=monthly.project(game,save,snapshot(20260708),[100],{},str,{11:'Clube'})[100]
   self.assertTrue(result['coach']['available']);self.assertEqual(result['coach']['name'],'Técnico A');self.assertEqual(result['coach']['games'],1);self.assertFalse(result['player']['available'])
   self.assertFalse(monthly.project(game,save,snapshot(20260708),[100],{},str,{},save_hash='different-save')[100]['coach']['available'])
   monthly.capture(database,'branch',snapshot(20260628))
   middle=snapshot(20260708,12,4,860);middle['fixtures']=[[8,101,101,20260630,1900,11,22,0,0,1,1],[9,101,101,20260708,1900,11,22,2,0,1,2]];monthly.capture(database,'branch',middle)
   latest=snapshot(20260716,13,5,940);latest['fixtures']=middle['fixtures']+[[10,101,101,20260716,1900,11,22,2,0,1,3]];monthly.capture(database,'branch',latest)
   award=monthly.project(game,save,latest,[100],{99:'Atleta'},str,{11:'Clube'})[100]['player'];self.assertTrue(award['available']);self.assertEqual(award['games'],1);self.assertTrue(award['partial']);self.assertEqual(award['fromDate'],20260708)
   state['created']=999;file.write_text(json.dumps(state));self.assertFalse(monthly.project(game,save,snapshot(20260708),[100],{},str,{})[100]['coach']['available']);self.assertEqual(save.read_bytes(),b'unchanged')

if __name__=='__main__':unittest.main(verbosity=2)
