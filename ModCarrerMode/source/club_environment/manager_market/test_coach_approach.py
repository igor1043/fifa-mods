import json,tempfile,unittest,zlib
from pathlib import Path
from unittest.mock import patch
from test_engine import catalog,context
import engine as e
from model import project
from market_balance import dismissal_risk

class CoachApproachTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db');self.m=e.Market(self.root/'world.db',self.root/'catalog.db');self.m.open_save('seed','DATA',context())
  with self.m.db:
   self.m.db.execute("UPDATE coaches SET eligible=CASE WHEN coach_id='2' THEN 1 ELSE 0 END WHERE branch=?",(self.m.branch,))
   self.m.leave(self.m.active(club=1),20260401,'dismissal','Teste de vaga')
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def hire(self):
  with self.m.db:return self.m.hire(self.m.one('clubs','club_id',1),20260401,'seed')
 def test_unsuitable_free_market_triggers_buyout_and_balanced_ledger(self):
  original=self.m.active(club=2)
  with patch.object(e,'draw',return_value=0):self.assertTrue(self.hire())
  self.assertEqual('2',self.m.active(club=1)['coach_id']);self.assertIsNone(self.m.active(club=2));self.assertEqual(1,len(self.m.rows('approaches')))
  deal=self.m.rows('approaches')[0];self.assertEqual('completed',deal['status']);self.assertEqual(original['monthly_wage']*3,deal['fee'])
  ledger=self.m.rows('salary_events',"kind IN ('coach_buyout_paid','coach_buyout_received')")
  self.assertEqual(2,len(ledger));self.assertEqual(0,sum(r['amount']*(1 if r['kind']=='coach_buyout_received' else -1) for r in ledger))
  self.assertEqual(1,len(self.m.rows('salary_events',"kind='severance'"))) # Only the earlier firing, never the poached coach.
  data=project(self.m,lightweight=True)
  self.assertEqual('Saída com multa',next(r for r in data['moveRows'] if r[0]=='Clube 2')[3]);row=next(r for r in data['hireRows'] if r[0]=='Clube 1');self.assertEqual('Pagou multa',row[12]);self.assertIn('Clube 2',row[2]);self.assertIn('/ mês',row[3])
  before=len(ledger)
  with patch.object(e,'draw',return_value=0):self.assertFalse(self.hire())
  self.assertEqual(before,len(self.m.rows('salary_events',"kind IN ('coach_buyout_paid','coach_buyout_received')")))
  with patch.object(e,'draw',return_value=0),self.m.db:self.m.advance(context(20260402))
  self.assertIsNotNone(self.m.active(club=2));self.assertEqual(before,len(self.m.rows('salary_events',"kind IN ('coach_buyout_paid','coach_buyout_received')")))

 def test_suitable_free_coach_is_preferred_without_touching_employed_coach(self):
  with self.m.db:self.m.db.execute("UPDATE coaches SET eligible=1,reputation=8 WHERE branch=? AND coach_id='4'",(self.m.branch,))
  with patch.object(e,'draw',return_value=0):self.hire()
  self.assertEqual('4',self.m.active(club=1)['coach_id']);self.assertEqual('2',self.m.active(club=2)['coach_id']);self.assertEqual([],self.m.rows('approaches'))

 def test_refused_or_unaffordable_approach_does_not_move_coach_or_charge_fee(self):
  with self.m.db:self.m.db.execute("UPDATE market_rules SET value=1 WHERE branch=? AND key='approach_fee_budget_bps'",(self.m.branch,))
  with patch.object(e,'draw',return_value=0):self.hire()
  self.assertEqual('2',self.m.active(club=2)['coach_id']);self.assertTrue(self.m.active(club=1)['coach_id'].startswith('INTERIM-'))
  self.assertEqual('rejected',self.m.rows('approaches')[0]['status']);self.assertEqual([],self.m.rows('salary_events',"kind LIKE 'coach_buyout_%'"))

 def test_coach_can_decline_a_financially_possible_offer(self):
  def draw(seed,*parts):return 9999 if parts[0]=='approach_accept' else 0
  with patch.object(e,'draw',side_effect=draw):self.hire()
  self.assertEqual('2',self.m.active(club=2)['coach_id']);self.assertEqual('rejected',self.m.rows('approaches')[0]['status']);self.assertIn('recusou',self.m.rows('approaches')[0]['reason'])

 def test_user_coach_and_short_tenure_are_never_approached(self):
  with self.m.db:
   self.m.db.execute('UPDATE appointments SET start_date=20260330 WHERE branch=? AND club_id=2',(self.m.branch,));self.m.db.execute("UPDATE coaches SET eligible=1 WHERE branch=? AND coach_id LIKE 'USER-%'",(self.m.branch,))
  with patch.object(e,'draw',return_value=0):self.hire()
  self.assertEqual([],self.m.rows('approaches'));self.assertEqual('USER-42',self.m.active(club=3)['coach_id'])

 def test_saved_buyout_survives_journal_restart_without_duplicate_payment(self):
  with patch.object(e,'draw',return_value=0):self.hire()
  with self.m.db:
   self.m.capture_session(10,20,30,2,100);payload=self.m.db.execute('SELECT state FROM session_states').fetchone()[0];self.m.checkpoint('saved','DATA',state=payload)
  self.m.close();self.m=e.Market(self.root/'world.db',self.root/'catalog.db');self.m.open_save('saved','DATA',context())
  self.assertEqual('2',self.m.active(club=1)['coach_id']);self.assertEqual('completed',self.m.rows('approaches')[0]['status']);self.assertEqual(2,len(self.m.rows('salary_events',"kind LIKE 'coach_buyout_%'")))

 def test_brazilian_risk_rises_only_for_bad_campaigns(self):
  for percentage in (20,35,40,45,49):
   campaign=dict(games=20,losses=8,percentage=percentage)
   br=dismissal_risk(7000,dict(reputation=8,country='Brasil'),campaign);eu=dismissal_risk(7000,dict(reputation=8,country='Espanha'),campaign)
   self.assertGreater(br,eu)
  for country in ('Brasil','Espanha'):
   self.assertEqual(0,dismissal_risk(7000,dict(reputation=8,country=country),dict(games=20,losses=0,percentage=80)))
   self.assertLessEqual(dismissal_risk(7000,dict(reputation=8,country=country),dict(games=20,losses=5,percentage=55)),25)

 def test_native_movement_cards_show_paid_buyout_and_departure_distinctly(self):
  with patch.object(e,'draw',return_value=0):self.hire()
  with self.m.db:self.m.db.execute('UPDATE branches SET game_date=20260401 WHERE id=?',(self.m.branch,))
  data=project(self.m,lightweight=True)
  import test_screen
  from screen import script_factory,FULL,stars
  from manager_layout import scenes_for
  from native_review_vm import open_native
  import native_screen
  from PIL import Image
  assets={'head_NOTFOUND_DEFAULT':Image.new('RGBA',(64,64),'gray'),**{'stars_'+str(i):stars(i) for i in range(11)}}
  path=self.root/'movement.big';native_screen.build(test_screen.GAME,path,scenes_for(data,assets),assets,script_factory=script_factory(data,assets),full_name=FULL)
  vm,state,_,_=open_native(path,full=FULL);test_screen.load_data(vm,state);vm.invoke(state.get('Command'),state,(1,))
  root=state.get('scene3');self.assertEqual('Pagou multa',root.get('status0').get('text'))
  # The inspection VM exposes raw constant-pool UTF-8 as Latin-1; the FIFA
  # font renderer decodes that text. Normalize only for this display assertion.
  def displayed(value):
   try:return value.encode('latin1').decode('utf8')
   except (AttributeError,UnicodeError):return value
  statuses=[displayed(root.get('status'+str(i)).get('text')) for i in range(4,8)]
  self.assertIn('Saída com multa',statuses);self.assertFalse(vm.errors)

if __name__=='__main__':unittest.main()
