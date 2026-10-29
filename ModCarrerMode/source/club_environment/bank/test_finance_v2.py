"""Regression cases for prospective finances, currency UI and home matchday cash."""
import copy,hashlib,json,sqlite3,tempfile,unittest
from pathlib import Path
import club_finance as f
import save_sidecar as sql
from loans import empty
from test_club_finance import context,match
from finance_pages import ticket_rows

class FinanceV2(unittest.TestCase):
 def apply(self,state,day,games=(),budget=20_000_000,policy=None):
  ctx=context(day,games);ctx['club_profile']=dict(base_budget=28_000_000,prestige=20)
  return f.apply(state,club=1043,today=day,budget=budget,context=ctx,policy=policy)
 def test_home_gross_cost_net_and_no_away_income(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  s,b,events=self.apply(s,20260512,[match(),match(2,home=567,away=1043)],b)
  kinds=[e['kind'] for e in events]
  self.assertEqual(kinds.count('tv'),2);self.assertEqual(kinds.count('tickets'),1);self.assertEqual(kinds.count('match_costs'),1)
  tickets=next(e for e in events if e['kind']=='tickets');cost=next(e for e in events if e['kind']=='match_costs')
  self.assertEqual(cost['amount'],-tickets['amount']*4000//10000)
  view=dict(club=1043,entries=s['finance']['entries'],fixtures=[])
  rows=ticket_rows(view);self.assertEqual(len(rows),1)
  self.assertEqual(rows[0]['net'],tickets['amount']+cost['amount']);self.assertEqual(rows[0]['opponent'],567)
 def test_one_sponsor_per_club_month_despite_multiple_competitions(self):
  ctx=context();ctx['competitions']*=3
  s,b,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=20_000_000,context=ctx)
  ctx['date']=20260702
  s,b,events=f.apply(s,club=1043,today=20260702,budget=b,context=ctx)
  self.assertEqual(sum(e['kind']=='sponsor' for e in events),2)
  self.assertEqual(sum(e['kind']=='staff' for e in events),2)
  self.assertEqual(len(s['finance']['commercial']),1)
  s,b2,again=f.apply(s,club=1043,today=20260702,budget=b,context=ctx)
  self.assertEqual(b,b2);self.assertFalse(again)
 def test_strength_increases_sponsorship_and_staff_without_using_live_cash(self):
  p=f.rules();small=context();small['club_profile']=dict(base_budget=2_000_000,prestige=4)
  big=context();big['club_profile']=dict(base_budget=28_000_000,prestige=20)
  a=f.commercial(small,p);b=f.commercial(big,p)
  self.assertLess(a['sponsor_annual'],b['sponsor_annual']);self.assertLess(a['staff_annual'],b['staff_annual'])
  self.assertEqual(b['sponsor_annual'],7_000_000);self.assertEqual(b['staff_annual'],8_400_000)
 def test_season_rollover_does_not_lose_unprocessed_previous_months(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  ctx=context(20270131,season=20270101);ctx['club_profile']=dict(base_budget=28_000_000,prestige=20)
  s,b,e=f.apply(s,club=1043,today=20270131,budget=b,context=ctx)
  self.assertEqual(sum(x['kind']=='sponsor' for x in e),9)
  self.assertEqual(sum(x['kind']=='staff' for x in e),9)
  self.assertEqual(len(s['finance']['commercial']),2)
  again,b2,e=f.apply(s,club=1043,today=20270131,budget=b,context=ctx)
  self.assertEqual(b,b2);self.assertFalse(e)
 def test_home_cost_waits_when_matching_credit_cannot_fit_budget(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  s,b,e=self.apply(s,20260512,[match()],f.MAX_BUDGET)
  self.assertEqual(b,f.MAX_BUDGET);self.assertFalse(e)
  self.assertTrue(all(r['status']=='pending' for r in s['finance']['entries']))
 def test_legacy_upgrade_does_not_retroactively_take_or_give_money(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  book=s['finance'];book['schema']=1
  for k in ('commercial','expanded_start'):book.pop(k,None)
  old=next(iter(book['agreements'].values()));old.update(per_match=150000,rules=dict(f.LEGACY_RULES))
  old_entry=dict(id='tickets:20260101:7:90:1043:567',kind='tickets',date=20260520,amount=1_000_000,status='applied',paid_date=20260520,fixture=90,description='Liga')
  book['entries']=[old_entry];book['last_date']=20261123;s['last_date']=20261123
  # Existing historical events remain exact even when today's rule is lower.
  upgraded,_,events=self.apply(s,20261123,budget=b)
  self.assertEqual(upgraded['finance']['entries'][0],old_entry)
  self.assertFalse(any(e['kind'] in ('sponsor','staff') for e in events))
  upgraded,b,events=self.apply(upgraded,20261130,budget=b)
  new=next(e for e in upgraded['finance']['entries'] if e['kind']=='sponsor')
  self.assertEqual(new['enabled_days'],8)
  self.assertEqual(f.match_terms(old,20261122)['per_match'],150000)
 def test_new_switches_proportion_days_and_match_costs_follow_tickets(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  for k in ('sponsor','staff','tickets'):s=f.toggle(s,k,False,20260511)
  s,b,events=self.apply(s,20260531,[match()],b)
  self.assertEqual([e['kind'] for e in events],['tv','coach'])
  self.assertTrue(all(e['status']=='disabled' for e in s['finance']['entries'] if e['kind'] in ('tickets','match_costs','staff','sponsor')))
 def test_pending_expense_is_only_applied_once_when_cash_returns(self):
  s,b,_=self.apply(empty(1043,20260511),20260511)
  s=f.toggle(s,'sponsor',False,20260511)
  s,b,events=self.apply(s,20260531,budget=0)
  self.assertFalse(events);self.assertTrue(any(e['kind']=='staff' and e['status']=='pending' for e in s['finance']['entries']))
  s,b,events=self.apply(s,20260601,budget=5_000_000)
  self.assertEqual({e['kind'] for e in events},{'staff','coach'})
  _,same,again=self.apply(s,20260601,budget=b);self.assertEqual(same,b);self.assertFalse(again)
 def test_sql_policy_migration_retains_custom_values_and_native_save_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'DATA';p.write_bytes(b'unchanged native save')
   sql.bank_rows(p)
   with sql.connection(p) as db:
    sql.finance_schema(db);db.executemany('INSERT INTO finance_rules VALUES(?,?)',f.LEGACY_RULES.items())
    db.execute("UPDATE finance_rules SET value=13 WHERE key='ticket_price'")
   policy=sql.finance_rules(p)
   self.assertEqual(policy['ticket_price'],13);self.assertEqual(policy['tv_match_bps'],150)
   self.assertEqual(sql.finance_rules(p),policy);self.assertEqual(p.read_bytes(),b'unchanged native save')
 def test_save_checkpoint_preserves_new_categories_and_can_restore_old_checkpoint(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'DATA';p.write_bytes(b'save one');sql.finance_rules(p)
   s,b,_=self.apply(empty(1043,20260511),20260511)
   old=copy.deepcopy(s);s,b,_=self.apply(s,20260630,[match()],b)
   stamp=dict(hash=hashlib.sha256(p.read_bytes()).hexdigest(),club=1043,date=20260630,budget=b)
   sql.save_snapshot(p,stamp,s,[],dict(operation='write',complete_file='1'))
   self.assertEqual(sql.load_snapshot(p,stamp['hash'],1043)['state'],s)
   with sql.connection(p) as db:
    self.assertEqual(db.execute('SELECT COUNT(*) FROM finance_commercial WHERE checkpoint=?',(stamp['hash'],)).fetchone()[0],1)
   p.write_bytes(b'save two');stamp.update(hash=hashlib.sha256(p.read_bytes()).hexdigest())
   sql.save_snapshot(p,stamp,old,[],dict(operation='write',complete_file='1'))
   self.assertEqual(sql.load_snapshot(p,stamp['hash'],1043)['state'],old)

if __name__=='__main__':unittest.main()
