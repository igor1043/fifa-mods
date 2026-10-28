import unittest,tempfile,hashlib,json
from pathlib import Path
from copy import deepcopy
import club_finance as f
import save_sidecar as sql
from loans import empty,borrow,advance

def match(ident=1,day=20260512,home=1043,away=567,played=True,root=7,neutral=False):
 return dict(id=ident,date=day,home=home,away=away,played=played,root=root,neutral=neutral)
def context(day=20260511,fixtures=(),club=1043,season=20260101):
 return dict(club=club,date=day,season=season,coach_wage=38000,capacity=50000,fixtures=list(fixtures),
  competitions=[dict(root=7,asset=7,name='Liga nova',budgets=[10_000_000,20_000_000,30_000_000],prestige=10,level=1)])
def step(state,day=20260511,budget=10_000_000,fixtures=(),**kwargs):
 ctx=context(day,fixtures,**kwargs)
 return f.apply(state,club=ctx['club'],today=day,budget=budget,context=ctx)

class ClubFinanceTests(unittest.TestCase):
 def setUp(self):self.state,self.budget,_=step(empty(1043,20260511))
 def test_activation_never_pays_existing_results(self):
  s,b,e=step(empty(1043,20260511),fixtures=[match(day=20260510),match(2,day=20260511)])
  s,b,e=step(s,budget=b,fixtures=[match(day=20260510),match(2,day=20260511)])
  self.assertEqual(b,10_000_000);self.assertFalse(e);self.assertTrue(all(s['finance']['settings'].values()))
 def test_one_payment_per_completed_fixture_and_month_is_only_aggregation(self):
  s,b,e=step(self.state,20260512,self.budget,[match()]);first=b
  self.assertEqual({r['kind'] for r in e},{'tv','tickets'})
  for _ in range(5):s,b,e=step(s,20260512,b,[match()]);self.assertFalse(e)
  self.assertEqual(b,first);rows=f.monthly(s);self.assertEqual(rows[0]['income'],first-self.budget)
  self.assertEqual(self.state['finance']['entries'],[])
 def test_away_game_only_tv_and_unplayed_or_neutral_has_no_ticket(self):
  s,b,e=step(self.state,20260512,self.budget,[match(home=567,away=1043),match(2,played=False),match(3,neutral=True)])
  self.assertEqual([r['kind'] for r in e],['tv','tv']);self.assertEqual(len(s['finance']['entries']),2)
 def test_calendar_jump_pays_all_matches_and_month_ends_once(self):
  games=[match(),match(2,20260610),match(3,20260622,home=567,away=1043)]
  s,b,e=step(self.state,20260702,self.budget,games)
  self.assertEqual(sum(r['kind']=='tv' for r in e),3)
  payroll=[r for r in s['finance']['entries'] if r['kind']=='coach']
  self.assertEqual(len(payroll),2);self.assertEqual(payroll[0]['enabled_days'],21)
  self.assertEqual(payroll[1]['amount'],-164667)
  s,b2,e=step(s,20260702,b,games);self.assertEqual(b,b2);self.assertFalse(e)
 def test_tv_and_ticket_disabled_period_never_reappears_after_enabling(self):
  s=f.toggle(self.state,'tv',False,20260511);s=f.toggle(s,'tickets',False,20260511)
  s,b,e=step(s,20260512,self.budget,[match()]);self.assertFalse(e)
  self.assertTrue(all(r['status']=='disabled' for r in s['finance']['entries']))
  s=f.toggle(s,'tv',True,20260512);s=f.toggle(s,'tickets',True,20260512)
  s,b,e=step(s,20260513,b,[match(),match(2,20260513)]);self.assertEqual(len(e),2)
  self.assertTrue(all(r['fixture']==2 for r in s['finance']['entries'] if r['status']=='applied'))
 def test_master_switch_freezes_money_and_coach_does_not_charge_disabled_days(self):
  s=f.toggle(self.state,'enabled',False,20260511)
  s,b,e=step(s,20260531,self.budget,[match()]);self.assertFalse(e);self.assertEqual(b,self.budget)
  s=f.toggle(s,'enabled',True,20260531)
  s,b,e=step(s,20260630,b,[match()]);coach=[x for x in e if x['kind']=='coach']
  self.assertEqual(len(coach),1);self.assertEqual(coach[0]['amount'],-164667)
 def test_coach_subswitch_prorates_the_enabled_days(self):
  s=f.toggle(self.state,'coach',False,20260520);s=f.toggle(s,'coach',True,20260525)
  s,b,e=step(s,20260531,self.budget)
  payroll=s['finance']['entries'][0];self.assertEqual(payroll['enabled_days'],16)
  self.assertEqual(payroll['amount'],-round(38000*52/12*16/31))
 def test_pending_salary_waits_for_balance_and_is_not_marked_paid(self):
  s,b,e=step(self.state,20260531,0)
  self.assertEqual(b,0);self.assertFalse(e);self.assertEqual(s['finance']['entries'][0]['status'],'pending')
  s,b,e=step(s,20260601,1_000_000);self.assertEqual(len(e),1);self.assertEqual(e[0]['paid_date'],20260601)
 def test_unknown_coach_never_invents_or_deducts_salary(self):
  ctx=context(20260511);ctx['coach_wage']=None
  s,b,e=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=self.budget,context=ctx)
  ctx['date']=20260531;s,b,e=f.apply(s,club=1043,today=20260531,budget=b,context=ctx)
  self.assertFalse(e);self.assertFalse(s['finance']['entries'])
 def test_agreement_is_frozen_against_balance_rule_and_budget_changes(self):
  before=deepcopy(self.state['finance']['agreements'])
  ctx=context(20260512,[match()]);ctx['competitions'][0]['budgets']=[999_000_000]
  s,b,e=f.apply(self.state,club=1043,today=20260512,budget=500_000_000,context=ctx,policy={'tv_match_bps':200})
  self.assertEqual(s['finance']['agreements'],before)
 def test_new_competition_and_season_get_their_own_dynamic_contract(self):
  ctx=context(20270101,season=20270101);ctx['competitions'].append(dict(root=9999,asset=9999,name='Copa adicionada'))
  s,b,e=f.apply(self.state,club=1043,today=20270101,budget=self.budget,context=ctx)
  self.assertIn('20270101:9999',s['finance']['agreements']);self.assertIn('20260101:7',s['finance']['agreements'])
 def test_previous_season_results_never_pay_again(self):
  s,b,e=step(self.state,20260512,self.budget,[match()])
  s,b,e=step(s,20270101,b,[match()],season=20270101)
  self.assertFalse(any(x['kind']=='tv' for x in e))
 def test_rollback_and_wrong_club_are_rejected(self):
  with self.assertRaises(ValueError):step(self.state,20260510)
  with self.assertRaises(ValueError):step(self.state,club=567)
 def test_loan_state_survives_finance_and_interest_is_not_principal(self):
  s,b,_=borrow(self.state,request_id='loan',club=1043,today=20260511,budget=self.budget,bank=0,amount=1_000_000,months=12)
  s,b,_=step(s,20260611,b,[match()]);s,b,_=advance(s,club=1043,today=20260611,budget=b)
  row=f.monthly(s)[0];self.assertLess(row['loans'],row['interest']);self.assertEqual(s['contracts'][0]['paid'],1)
  self.assertIn('finance',s)
 def test_limits_and_custom_rules_are_validated(self):
  with self.assertRaises(ValueError):f.rules({'occupancy_max_bps':10001})
  s,b,e=step(self.state,20260512,f.MAX_BUDGET,[match()]);self.assertEqual(b,f.MAX_BUDGET)
  self.assertTrue(all(r['status']=='pending' for r in s['finance']['entries']))
 def test_sql_restoration_save_as_and_preferences_keep_native_save_untouched(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'DATA';p.write_bytes(b'native-file');digest=hashlib.sha256(p.read_bytes()).hexdigest()
   sql.bank_rows(p);policy=sql.finance_rules(p)
   self.assertTrue((p.parent/'server16_loans.before-finance-v1.sqlite3').is_file())
   s,b,e=step(self.state,20260512,self.budget,[match()]);s=f.toggle(s,'tickets',False,20260512)
   saved=dict(hash=digest,club=1043,date=20260512,budget=b)
   sql.save_session_club(p,digest,'session',1,s,[])
   sql.save_snapshot(p,saved,s,[],dict(operation='write',complete_file='1',access_tick_ms=2))
   restored=sql.load_snapshot(p,digest,1043)['state'];self.assertEqual(restored,s)
   with sql.connection(p) as db:
    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)
    self.assertEqual(db.execute('SELECT COUNT(*) FROM finance_entries WHERE checkpoint=?',(digest,)).fetchone()[0],2)
    self.assertFalse(json.loads(db.execute('SELECT settings_json FROM finance_preferences WHERE checkpoint=?',(digest,)).fetchone()[0])['tickets'])
   newer,b,_=step(s,20260630,b,[match(),match(2,20260615)])
   self.assertEqual(sql.load_snapshot(p,digest,1043)['state'],s)
   target=Path(folder)/'other'/'DATA';target.parent.mkdir();target.write_bytes(p.read_bytes())
   sql.save_snapshot(target,saved,s,[],dict(operation='write',complete_file='1'))
   self.assertEqual(sql.load_snapshot(target,digest,1043)['state'],s)
   self.assertEqual(p.read_bytes(),b'native-file');self.assertEqual(policy,f.DEFAULT_RULES)

if __name__=='__main__':unittest.main()
