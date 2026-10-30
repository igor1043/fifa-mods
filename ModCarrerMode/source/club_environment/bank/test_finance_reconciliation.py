import copy,unittest
from unittest.mock import patch
import club_finance as f
from loans import empty
from test_club_finance import context,match

class FinancialReconciliation(unittest.TestCase):
 def test_unreconciled_batch_never_reaches_a_ram_write(self):
  from runtime import Bridge
  bridge=Bridge.__new__(Bridge)
  with self.assertRaisesRegex(ValueError,'não conciliam'):
   bridge.publish(dict(budget=20),{},21,[dict(event='finance',amount=2)],'club_finance')
 def test_fast_calendar_does_not_rebuild_hidden_screens_each_day(self):
  import runtime as r
  bridge=r.Bridge.__new__(r.Bridge)
  live=dict(club=1043,date=20260501,budget=10_000_000,page='game/screens/career/calendar')
  with patch.object(r.time,'monotonic',side_effect=[0,.2,.8,1.9]):
   self.assertFalse(bridge.ui_stable(live,r.FINANCE_PAGE))
   self.assertFalse(bridge.ui_stable(dict(live,date=20260502),r.FINANCE_PAGE))
   self.assertFalse(bridge.ui_stable(dict(live,date=20260503),r.FINANCE_PAGE))
   self.assertTrue(bridge.ui_stable(dict(live,date=20260503),r.FINANCE_PAGE))
  self.assertTrue(bridge.ui_stable(dict(live,page=r.FINANCE_PAGE),r.FINANCE_PAGE))
  self.assertFalse(bridge.ui_stable(dict(live,page=r.FINANCE_PAGE),r.PAGE))
 def test_calendar_jump_keeps_month_of_origin_and_reconciles_real_cash(self):
  ctx=context(20260401);state,budget,_=f.apply(empty(1043,20260401),club=1043,today=20260401,budget=20_000_000,context=ctx)
  ctx=context(20260824,[match(1,20260520),match(2,20260620,home=567,away=1043)])
  state,after,events=f.apply(state,club=1043,today=20260824,budget=budget,context=ctx)
  self.assertEqual(after-budget,f.cash_delta(events))
  months={r['month']:r for r in f.monthly(state)}
  self.assertLess(months[202605]['coach'],0);self.assertLess(months[202606]['staff'],0)
  self.assertGreater(months[202605]['tickets'],0);self.assertEqual(months[202606]['tickets'],0)
  self.assertEqual(sum(r['cash_result'] for r in months.values()),after-budget)
  settled=f.monthly(state,settlement=True)
  self.assertEqual([r['month'] for r in settled],[202608]);self.assertEqual(settled[0]['cash_result'],after-budget)
  self.assertTrue(all(e['paid_date']==20260824 for e in state['finance']['entries']))
  again,same,events=f.apply(state,club=1043,today=20260824,budget=after,context=ctx)
  self.assertEqual(same,after);self.assertFalse(events)
 def test_stronger_league_increases_all_income_and_relegation_decreases_it(self):
  weak=dict(prestige=9,base_budget=8_000_000,level=2,league_budget=5_000_000,league_prestige=3,league_overall=65)
  strong=dict(weak,level=1,league_budget=30_000_000,league_prestige=12,league_overall=78)
  p=f.rules();comp=context()['competitions'][0]
  self.assertGreater(f.agreement(comp,20260101,20260101,p,strong)['per_match'],f.agreement(comp,20260101,20260101,p,weak)['per_match'])
  self.assertGreater(f.commercial(dict(context(),club_profile=strong),p)['sponsor_annual'],f.commercial(dict(context(),club_profile=weak),p)['sponsor_annual'])
  self.assertGreater(f.ticket_projection(40000,9,p,strong)['gross'],f.ticket_projection(40000,9,p,weak)['gross'])
 def test_economy_revision_never_reposts_or_reprices_applied_entries(self):
  ctx=context();state,budget,_=f.apply(empty(1043,20260511),club=1043,today=20260511,budget=20_000_000,context=ctx)
  ctx=context(20260512,[match()]);state,budget,_=f.apply(state,club=1043,today=20260512,budget=budget,context=ctx)
  old=copy.deepcopy(state['finance']['entries'])
  ctx['club_profile']=dict(prestige=20,base_budget=20_000_000,level=1,league=8,league_budget=40_000_000,league_overall=80)
  state,after,events=f.apply(state,club=1043,today=20260512,budget=budget,context=ctx)
  self.assertEqual(after,budget);self.assertFalse(events);self.assertEqual(old,state['finance']['entries'])

if __name__=='__main__':unittest.main()
