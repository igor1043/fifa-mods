import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from cup_title_receipts import completed,unique_matches
from engine import Market
from title_history import record
from test_engine import catalog,context

FORMATS={11:dict(root=10,asset=229,kind=8,mode='KO2LEGS',last_day=310),
         12:dict(root=10,asset=229,kind=10,mode='KO1LEG',last_day=339)}

def game(stage,day,home,away,hg,ag):
 return dict(root=10,asset=229,stage=stage,date=day,home=home,away=away,homeScore=hg,awayScore=ag,played=True)

def semis():
 return [game(11,20261101,1,2,2,1),game(11,20261108,2,1,0,1),
         game(11,20261101,3,4,1,0),game(11,20261108,4,3,1,2)]

def fact(**changes):
 return dict(dict(compobjid=10,stageid=12,season=1,teamid=1,hasteamwon=0,cup_objective_result=1,compshortname='C229'),**changes)

class CupReceiptTests(unittest.TestCase):
 def recover(self,rows,progress,today=20271215,definitions=FORMATS):
  return completed(rows,progress,definitions,today,20260101,lambda asset:'Cup '+str(asset))
 def test_old_runner_up_and_both_proven_finalists_recover_the_actual_winner(self):
  rows=self.recover(semis(),[fact()]);self.assertEqual(1,len(rows))
  self.assertEqual((3,229,20260101,'saved_final_outcome:season'),tuple(rows[0][k] for k in ('club','asset','season','evidence_source')))
  self.assertNotIn('hg',rows[0]);self.assertNotIn('ag',rows[0])
 def test_semifinals_alone_do_not_grant_a_trophy(self):
  self.assertEqual([],self.recover(semis(),[]));self.assertEqual([],self.recover(semis(),[fact(stageid=11)]))
  self.assertEqual([],self.recover(semis()[:-1],[fact()]))
 def test_current_pending_final_is_not_a_confirmed_runner_up(self):
  self.assertEqual([],self.recover(semis(),[fact()],20261120))
 def test_native_final_outcome_resolves_a_penalty_final_without_guessing_the_score(self):
  rows=self.recover([game(12,20261205,1,3,1,1)],[fact(hasteamwon=1)],20261206)
  self.assertEqual([(1,20261205,'saved_final_outcome:exact')],[(r['club'],r['date'],r['evidence_source']) for r in rows])
  self.assertEqual([],self.recover([game(12,20261205,1,3,1,1)],[],20261206))
 def test_cpu_penalty_winner_uses_the_exact_native_final_group(self):
  formats={**FORMATS,12:dict(FORMATS[12],groups=[13])};match=game(12,20261205,1,3,1,1)
  perf=[dict(key='fce:10:13',club=1,season=20260109,date=20261205,source='native_view',hw=0,hd=0,hl=1,aw=0,ad=0,al=0),
        dict(key='fce:10:13',club=3,season=20260109,date=20261205,source='native_view',hw=0,hd=0,hl=0,aw=1,ad=0,al=0)]
  rows=completed([match],[],formats,20261206,20260101,str,perf)
  self.assertEqual([3],[r['club'] for r in rows]);self.assertEqual((1,1),(match['homeScore'],match['awayScore']))
  for wrong in ([dict(r,key='fce:10:99') for r in perf],[dict(r,date=20261204) for r in perf],perf[:1], [dict(r,source='saved_league') for r in perf]):
   self.assertEqual([],completed([match],[],formats,20261206,20260101,str,wrong))
  reset=[dict(r,hw=0,hl=0,aw=0) for r in perf]
  self.assertEqual([],completed([match],[],formats,20261206,20260101,str,perf+reset))
 def test_two_leg_final_uses_both_legs_and_ignores_third_place(self):
  formats={**FORMATS,12:dict(FORMATS[12],mode='KO2LEGS'),13:dict(root=10,asset=229,kind=9,mode='KO1LEG')}
  legs=[game(12,20261129,1,3,1,0),game(12,20261205,3,1,2,0),game(13,20261205,2,4,4,0)]
  self.assertEqual([3],[r['club'] for r in self.recover(legs,[],definitions=formats)])
  self.assertEqual([],self.recover(legs[:1],[],definitions=formats))
 def test_journal_survives_a_draw_reset_and_deduplicates_legacy_season_keys(self):
  m=game(12,20261205,1,3,2,0);duplicate=dict(m,season=20260109)
  rows=self.recover([m,duplicate],[]);self.assertEqual(1,len(rows));self.assertEqual(1,rows[0]['club'])
 def test_score_conflicts_and_wrong_competition_identity_are_not_awarded(self):
  m=game(12,20261205,1,3,2,0);self.assertEqual([],self.recover([m,dict(m,homeScore=0)],[]))
  self.assertEqual([],self.recover(semis(),[fact(compshortname='C999')]))
 def test_final_scores_take_priority_over_an_old_saved_outcome(self):
  rows=self.recover([*semis(),game(12,20261205,1,3,2,0)],[fact()]);self.assertEqual([1],[r['club'] for r in rows])
 def test_every_cup_uses_its_own_dynamic_asset_and_stages(self):
  for asset in (229,1003,1007,28,224,9999):
   formats={k:dict(v,asset=asset) for k,v in FORMATS.items()}
   rows=[dict(m,asset=asset) for m in semis()]
   won=self.recover(rows,[fact(compshortname='C'+str(asset))],definitions=formats)
   self.assertEqual([(asset,3)],[(r['asset'],r['club']) for r in won])

class CupPersistenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db')
  self.market=Market(self.root/'world.db',self.root/'catalog.db');c=context();c['career_start_date']=20260109
  self.market.open_save('INITIAL','DATA',c)
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def test_old_final_outcome_keeps_its_original_coach_after_reload_and_next_season(self):
  t=completed(semis(),[fact()],FORMATS,20271215,20260101,str)[0];c=context(20271215)
  # The native calendar startdate now belongs to 2027. It cannot reject a
  # trophy from the original 2026 tenure recorded in this same career.
  c.update(title_start=20260101,career_start_date=20270108)
  with patch('cup_title_receipts.receipts',return_value=[t]):
   with self.market.db:record(self.market,c)
  self.assertEqual('USER-42',self.market.rows('trophy_history')[0]['coach_id'])
  self.assertEqual([],self.market.rows('honours'))
  self.market.checkpoint('WON','DATA');self.market.open_save('WON','DATA',c)
  self.assertEqual(20260101,self.market.rows('trophy_history')[0]['season'])
  before=self.market.rows('trophy_history')
  with patch('cup_title_receipts.receipts',return_value=[t]):
   with self.market.db:record(self.market,dict(c,date=20280102,career_start_date=20280107))
  self.assertEqual(before,self.market.rows('trophy_history'))
 def test_recovered_champion_is_not_assigned_to_a_late_replacement(self):
  a=self.market.active(club=3);self.market.leave(a,20261201,'user_move','Test')
  self.market.hire(self.market.one('clubs','club_id',3),20261202,'seed')
  t=completed(semis(),[fact()],FORMATS,20271215,20260101,str)[0]
  with patch('cup_title_receipts.receipts',return_value=[t]):
   with self.market.db:record(self.market,dict(context(20271215),title_start=20260101))
  self.assertIsNone(self.market.rows('trophy_history')[0]['coach_id'])

if __name__=='__main__':unittest.main()
