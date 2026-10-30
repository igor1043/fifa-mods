"""Queries must preserve the ledger and expose each recorded receipt once."""
import copy,unittest
from finance_pages import ticket_rows,match_revenue_rows,sponsor_parts
from career_currency import format_money,currency_symbol
from test_club_finance_ui import view,open_finance
import finance_ui

class ReceiptDetails(unittest.TestCase):
 def receipts(self):
  entries=[]
  for ident,home,away,kind,amount in ((1,55,66,'tickets',111),(1,55,66,'tv',25),(2,66,55,'tv',30),(3,55,66,'tickets',200)):
   entries.append(dict(id=f'{kind}:20260101:7:{ident}:{home}:{away}',kind=kind,date=20260511+ident,fixture=ident,home=home,away=away,home_name='Clube '+str(home),away_name='Clube '+str(away),competition_asset=7,description='Liga',amount=amount,status='disabled' if ident==3 else 'applied'))
  return dict(club=55,entries=entries)
 def test_queries_do_not_reprice_or_repost_and_tv_away_is_not_lost(self):
  v=self.receipts();original=copy.deepcopy(v)
  self.assertEqual([r['gross'] for r in ticket_rows(v)],[0,111])
  self.assertEqual(sum(r['gross'] for r in match_revenue_rows(v,'tv','home')),25)
  self.assertEqual(sum(r['gross'] for r in match_revenue_rows(v,'tv','away')),30)
  self.assertEqual(sum(r['gross'] for r in match_revenue_rows(v,'tv')),55)
  self.assertEqual(v,original)
 def test_mock_sponsor_categories_preserve_every_integer(self):
  for total in (0,1,99,100,123456789):self.assertEqual(sum(r[2] for r in sponsor_parts(total)),total)
 def test_historical_operation_projection_is_labelled_and_never_rewrites_cash(self):
  v=self.receipts();before=copy.deepcopy(v);rows=ticket_rows(v)
  row=next(r for r in rows if r['gross']==111)
  self.assertEqual((row['cost'],row['net']),(0,111))
  self.assertEqual((row['display_cost'],row['display_net']),(44,67))
  self.assertTrue(row['cost_estimated']);self.assertIn('não debitada',row['cost_note']);self.assertEqual(v,before)
 def test_actual_disabled_and_pending_costs_are_distinct_from_missing_history(self):
  for status in ('applied','pending','disabled'):
   v=self.receipts();v['entries'].append(dict(id='match_costs:20260101:7:1:55:66',kind='match_costs',amount=-44,date=20260512,status=status))
   row=next(r for r in ticket_rows(v) if r['gross']==111)
   self.assertFalse(row['cost_estimated'])
   self.assertEqual(row['cost'],44 if status=='applied' else 0)
   self.assertEqual(row['display_cost'],0 if status=='disabled' else 44)
   self.assertEqual(row['display_net'],111-row['display_cost'])
 def test_currency_prefix_follows_patch_labels_without_conversion(self):
  labels=dict(CM_DollarCurrency='Real',CM_EuroCurrency='Dólares',CM_PoundsCurrency='Euros')
  for slot,symbol in ((0,'R$'),(1,'US$'),(2,'€')):
   self.assertEqual(currency_symbol(slot,labels),symbol)
   self.assertEqual(format_money(1234567,slot,labels=labels),symbol+' 1.234.567')
  self.assertEqual(format_money(-1000,0,labels=labels),'−R$ 1.000')
 def test_each_receipt_link_opens_its_page_and_back_returns_to_receipts(self):
  v=view();v.update(self.receipts());vm,s,calls=open_finance(v);items=finance_ui.scenes(v);keys={r['key']:i for i,r in enumerate(items)}
  for root in ('tv','tickets','sponsors'):
   vm.invoke(s.get('Go'),s,[keys['receipts']]);row=items[keys['receipts']]
   s.set('focus',next(i for i,a in enumerate(row['actions']) if a['target']==root));vm.invoke(s.get('Select'),s)
   self.assertEqual(s.get('page'),keys[root]);vm.invoke(s.get('Back'),s);self.assertEqual(s.get('page'),keys['receipts'])
  self.assertFalse(any(n=='SendSystemEvent' and a[1]=='Server16SubmitBank' for n,a in calls))

if __name__=='__main__':unittest.main()
