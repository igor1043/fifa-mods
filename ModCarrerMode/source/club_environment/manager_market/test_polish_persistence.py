from pathlib import Path
import json,sqlite3,tempfile,unittest,zlib
from unittest.mock import patch
from test_engine import catalog,context,matches
from engine import Market,DEFAULTS,dismissal_probability,dismissal_policy
from catalog_meta import Labels
from competition_labels import resolve
from live_sampler import Sampler,replay

class PersistenceAndPolish(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.sqlite3');self.m=Market(self.root/'market.db',self.root/'catalog.sqlite3');self.m.open_save('A','DATA',context())
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def test_discard_removes_unsaved_session_rows_but_keeps_the_native_checkpoint(self):
  with self.m.db:self.m.advance(context(20260401,matches(10)))
  abandoned=self.m.branch;self.assertTrue(self.m.rows('results'))
  self.m.open_save('A','DATA',context());self.assertEqual([],self.m.rows('results'));self.assertIsNone(self.m.db.execute('SELECT id FROM branches WHERE id=?',(abandoned,)).fetchone())
  self.assertEqual(0,self.m.db.execute('SELECT count(*) FROM results WHERE branch=?',(abandoned,)).fetchone()[0]);self.assertIsNotNone(self.m.db.execute("SELECT state FROM save_checkpoints WHERE save_hash='A'").fetchone())
 def test_saved_results_reload_and_discard_future_year_and_transfers(self):
  with self.m.db:self.m.advance(context(20260401,matches(10)));self.m.checkpoint('B','DATA')
  saved=self.m.snapshot();saved_coach=self.m.active(club=1)['coach_id']
  with self.m.db:self.m.advance(context(20261201,matches(30)))
  abandoned=self.m.branch;self.m.open_save('B','DATA',context(20260401));self.assertEqual(saved_coach,self.m.active(club=1)['coach_id']);self.assertEqual(10,len(self.m.rows('results')))
  self.assertFalse(self.m.db.execute('SELECT 1 FROM branches WHERE id=?',(abandoned,)).fetchone())
  before=json.loads(zlib.decompress(saved));after=json.loads(zlib.decompress(self.m.snapshot()));self.assertEqual(before['tables'],after['tables'])
 def test_primary_nationality_is_one_country_instead_of_a_source_country_list(self):
  labels=Labels(self.root/'catalog.sqlite3');self.assertEqual('Alemanha',labels.nationality('Germany;Australia')[0]);self.assertEqual('Argentina',labels.nationality('Argentina;China PR')[0])
 def test_trophy_name_uses_localization_and_not_same_id_league_name(self):
  game=self.root/'game';loc=game/'data/loc/por_br.db';loc.parent.mkdir(parents=True);loc.write_bytes(b'loc')
  cache=game/'ModCarrerMode/runtime/club_environment/preview/runtime/competition_labels_r57.json';cache.parent.mkdir(parents=True);cache.write_text(json.dumps(dict(revision=3,stamp=[loc.stat().st_mtime_ns,loc.stat().st_size],names={'LeagueName_1009':'Argentina Clausura','TrophyName_1009':'CONMEBOL Recopa Sudamericana'})),encoding='utf8')
  self.assertEqual('CONMEBOL Recopa Sudamericana',resolve(game,1009,'Competição 1009'))
 def test_brazil_has_a_higher_risk_and_a_shorter_minimum_tenure(self):
  br=dict(country='Brasil');other=dict(country='Portugal')
  self.assertGreater(dismissal_probability(br,50,DEFAULTS),dismissal_probability(other,50,DEFAULTS));self.assertLess(dismissal_policy(br,DEFAULTS)['days'],dismissal_policy(other,DEFAULTS)['days'])
 def test_sampler_keeps_dated_evidence_and_clears_it_on_a_different_save_load(self):
  sampler=Sampler(None,None,None,None,None,None,None,None,None);observed=dict(date=20261201,save=dict(pid=1,process_created_100ns=2,path='DATA'),profile=dict(context_address=3,context_epoch=4,club_id=5));token=('read','1','DATA')
  sampler.retain(observed,token,dict(date=20260301,rows=[{'played':8}]));sampler.retain(observed,token,dict(date=20260401,rows=[{'played':12}]))
  rows=sampler.drain(observed,token,20260101);self.assertEqual([20260301,20260401],[r['date'] for r in rows]);self.assertEqual([],sampler.drain(observed,token,20260101))
  sampler.retain(observed,token,dict(date=20261201,rows=[]));self.assertEqual([],sampler.drain(observed,('read','2','DATA'),20260101))
 def test_replay_uses_the_real_observation_dates_without_inventing_matches(self):
  c=context(20261201);c['clubs']=[dict(club_id=1,league_id=100)]
  sample=dict(date=20260401,rows=[])
  with patch('global_performance.project',return_value=dict(performance=[],tables={},club_tables={},table_dates={})) as project,patch.object(self.m,'advance') as advance:replay(self.m,c,[sample])
  self.assertEqual(20260401,advance.call_args.args[0]['date']);self.assertEqual([],advance.call_args.args[0]['fixtures']);self.assertEqual(20260401,project.call_args.args[4])
 def test_midyear_observations_trigger_reviews_in_their_months_not_only_december(self):
  def rows(n):
   out=[]
   for club in (1,2,3):
    win=n if club==2 else n//2 if club==3 else 0;loss=n-win
    out.append(dict(teamid=club,leagueid=100,secondarytable=0,nummatchesplayed=n,points=win*3,homewins=win,homedraws=0,homelosses=loss,awaywins=0,awaydraws=0,awaylosses=0,homegf=win,homega=loss,awaygf=0,awayga=0))
   return out
  c=context(20261201);c['clubs']=self.m.rows('clubs')
  with patch('engine.draw',return_value=9999),self.m.db:replay(self.m,c,[dict(date=20260301,rows=rows(8)),dict(date=20260501,rows=rows(12))])
  self.assertEqual([20260301,20260501],[r['game_date'] for r in self.m.rows('reviews','club_id=1')]);self.assertEqual([],self.m.rows('results'))

if __name__=='__main__':unittest.main()
