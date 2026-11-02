import unittest
import finance_ui as ui
from test_club_finance_ui import view,open_finance


class OverviewTests(unittest.TestCase):
 def test_right_stick_scrolls_all_income_and_expense_cards_without_money_request(self):
  v=view();v['date']=20261201
  pages=ui.scenes(v);keys={p['key']:i for i,p in enumerate(pages)}
  vm,s,calls=open_finance(v)
  vm.invoke(s.get('LocalEventHandler'),s,[12,None])
  self.assertEqual(s.get('page'),keys['overview:details'])
  vm.invoke(s.get('LocalEventHandler'),s,[12,None])
  self.assertEqual(s.get('page'),keys['overview:details:1'])
  vm.invoke(s.get('LocalEventHandler'),s,[11,None])
  self.assertEqual(s.get('page'),keys['overview:details'])
  self.assertFalse(any(n=='SendSystemEvent' and a[1]=='Server16SubmitBank' for n,a in calls))

 def test_zero_transfer_loan_categories_and_unknown_native_awards_remain_visible(self):
  pages=ui.scenes(view())
  nodes=[n for p in pages if p['key'].startswith('overview:') for n in p['nodes']]
  labels={n.get('text') for n in nodes}
  for label in ('Vendas de jogadores','Compras de jogadores','Amortização de empréstimos','Juros dos empréstimos','Premiações','Bônus e premiações pagos'):
   self.assertIn(label,labels)
  self.assertTrue(any(n.get('amount')==0 for n in nodes))
  self.assertIn('Não obtido',labels)
  for page in (p for p in pages if p['key'].startswith('overview:')):
   for a in page['actions']:self.assertLessEqual(a['y']+a['h'],870)


if __name__=='__main__':unittest.main()
