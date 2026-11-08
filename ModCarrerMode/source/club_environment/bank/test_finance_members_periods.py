import copy,unittest
from loans import empty
from test_club_finance import context
import club_finance as f
from finance_report import composition,categories,period_months
from finance_dashboard import model

class MembersAndPeriods(unittest.TestCase):
 def ctx(self,date=20260101,prestige=10):
  return dict(context(date),club_profile=dict(base_budget=20_000_000,prestige=prestige,league_budget=10_000_000,league_overall=70,league_prestige=8,level=1))
 def apply(self,state,date,budget=20_000_000):return f.apply(state,club=1043,today=date,budget=budget,context=self.ctx(date))
 def test_commercial_envelope_is_preserved_and_prestige_changes_membership_share(self):
  a=f.commercial(self.ctx(prestige=2),f.rules());b=f.commercial(self.ctx(prestige=20),f.rules())
  for row in (a,b):self.assertEqual(row['commercial_annual'],row['sponsor_annual']+row['members_annual'])
  self.assertLess(a['members_share_bps'],b['members_share_bps']);self.assertLess(a['members_annual'],b['members_annual'])
 def test_members_pay_once_per_month_and_switches_prevent_future_receipts(self):
  state,budget,_=self.apply(empty(1043,20260101),20260101)
  state,budget,events=self.apply(state,20260131,budget)
  rows=[r for r in events if r.get('kind')=='members'];self.assertEqual(len(rows),1);self.assertGreater(rows[0]['amount'],0)
  again,after,events=self.apply(state,20260131,budget);self.assertEqual(after,budget);self.assertFalse(events)
  again=f.toggle(again,'members',False,20260201);again,after,events=self.apply(again,20260228,after)
  self.assertFalse(any(e.get('kind')=='members' for e in events))
  month=f.monthly(state)[0];self.assertGreater(month['members'],0)
  self.assertEqual(month['income'],sum(month[k] for k in ('tv','tickets','sponsor','members')))
 def test_old_paid_entries_and_pre_update_membership_are_not_rewritten(self):
  state,budget,_=self.apply(empty(1043,20260101),20260101)
  state,budget,_=self.apply(state,20260131,budget)
  book=state['finance'];book['economy_version']=4
  for row in book['commercial'].values():row['sponsor_annual']+=row.pop('members_annual',0)
  for values in (book['settings'],book['settings_history'][0]['values']):values.pop('members',None)
  book['entries']=[r for r in book['entries'] if r['kind']!='members'];before=copy.deepcopy(book['entries'])
  updated,_,_=self.apply(state,20260315,budget)
  self.assertEqual(before,updated['finance']['entries'][:len(before)])
  self.assertFalse(any(r['kind']=='members' and r['status']=='applied' and r['amount'] for r in updated['finance']['entries']))
 def test_period_totals_include_native_deals_once_but_never_financing(self):
  view=dict(date=20260320,months=[dict(month=202603,tv=100,sponsor=200,members=50,tickets=400,coach=-100,loan_credit=10000,loans=-300,interest=-30)],
   transfers=[dict(date=20260301,direction='out',fee=5000,loan=False),dict(date=20260302,direction='in',fee=2000,loan=False),
              dict(date=20260201,direction='out',fee=9000,loan=False)])
  income=composition(view,'receipts',202603);expenses=composition(view,'expenses',202603)
  self.assertEqual(sum(r['value'] for r in income),5750);self.assertEqual(sum(r['value'] for r in expenses),2130)
  self.assertNotIn('loan',{r['key'] for r in income+expenses})
  self.assertEqual(model(view)['series'][2],(5750,2130,3620))
  self.assertEqual(period_months(view),[202603,202602,202601])
 def test_membership_policy_rejects_inverted_ranges(self):
  with self.assertRaises(ValueError):f.rules(dict(members_share_min_bps=4000,members_share_max_bps=1000))

if __name__=='__main__':unittest.main()
