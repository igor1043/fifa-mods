import unittest
from finance_dashboard import model,budget_metrics
import finance_art as art

class FinanceDashboardTests(unittest.TestCase):
 def test_principal_and_previous_year_are_not_operating_income_or_expense(self):
  v=dict(date=20260511,months=[dict(month=202605,tv=1000,tickets=2000,coach=-100,interest=-50,loans=-500,loan_credit=9000),dict(month=202505,tv=999,tickets=999,coach=-999,interest=-999)])
  result=model(v)
  self.assertEqual((result['income'],result['expense'],result['result']),(3000,150,2850))
  self.assertEqual(result['series'][4],(3000,150,2850));self.assertEqual(len(result['series']),12)
 def test_empty_negative_and_single_month_chart_inputs_are_safe(self):
  for series in ([(0,0,0)]*12,[(0,100,-100)]*12,[(100,0,100)]*12):
   self.assertEqual(art.evolution(series,observed=1).size,(876,178))
  self.assertEqual(art.donut((0,0)).size,(170,170));self.assertEqual(art.donut((100,300)).mode,'RGBA')
 def test_budget_variation_is_not_claimed_as_spending_and_payroll_limit_uses_real_margin(self):
  metrics=budget_metrics(dict(budget_initial=100,budget=150,player_weekly=80,wage_margin=20))
  self.assertEqual((metrics['variation'],metrics['budget_ratio'],metrics['salary_limit'],metrics['salary_ratio']),(50,1.5,100,.8))
  self.assertIsNone(budget_metrics({})['salary_ratio'])
 def test_switch_and_progress_art_is_distinct_and_safe_at_empty_and_overflow(self):
  self.assertNotEqual(art.switch(True).tobytes(),art.switch(False).tobytes())
  for value in (-1,0,.5,2):self.assertEqual(art.progress(value).size,(309,9))

if __name__=='__main__':unittest.main()
