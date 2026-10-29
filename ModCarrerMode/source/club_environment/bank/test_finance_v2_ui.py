import unittest
import finance_ui as ui
from test_club_finance_ui import view,open_finance
from finance_dashboard import model
from club_finance import SWITCHES
from runtime import requests_in

class FinanceV2UI(unittest.TestCase):
 def test_right_stick_pages_months_without_financial_request_or_rebuilding(self):
  v=view();v['date']=20261123
  scenes=ui.scenes(v);index={s['key']:i for i,s in enumerate(scenes)}
  vm,s,calls=open_finance(v);vm.invoke(s.get('Go'),s,[index['monthly']])
  vm.invoke(s.get('LocalEventHandler'),s,[12,None]);self.assertEqual(s.get('page'),index['monthly:1'])
  vm.invoke(s.get('LocalEventHandler'),s,[11,None]);self.assertEqual(s.get('page'),index['monthly'])
  self.assertIn(('RAS_UD','Rolar lista'),vm.invoke(s.get('getHelpContext'),s))
  self.assertFalse(any(n=='SendSystemEvent' and a[1]=='Server16SubmitBank' for n,a in calls))
 def test_all_new_switches_use_original_wire_indexes_and_immediate_visual_state(self):
  self.assertEqual(SWITCHES[4],'loans')
  for kind in ('sponsor','staff','match_costs'):
   v=view();vm,s,calls=open_finance(v)
   settings=next(i for i,p in enumerate(ui.scenes(v)) if p['key']=='settings')
   vm.invoke(s.get('Go'),s,[settings]);at=SWITCHES.index(kind);s.set('focus',len(ui.TABS)+at)
   vm.invoke(s.get('Select'),s)
   wire=next(a[2] for n,a in calls if n=='SendSystemEvent' and a[1]=='Server16SubmitBank')
   self.assertEqual(next(iter(requests_in(wire.encode(),v['nonce'])))[1:5],(2,at,0,0))
   self.assertFalse(s.get('setting'+str(at)))
   self.assertFalse(s.get('scene'+str(settings)).get('switchOn'+str(at)).get('_visible'))
 def test_every_money_field_uses_selected_native_save_currency(self):
  for currency in (0,1,2):
   v=view();v['currency']=currency
   scenes=ui.scenes(v);vm,s,calls=open_finance(v)
   for i,page in enumerate(scenes):vm.invoke(s.get('Go'),s,[i])
   currency_calls=[a for n,a in calls if n=='LocalizeCurrencyWithType']
   self.assertTrue(currency_calls)
   self.assertTrue(any(a[0] is True for a in currency_calls),'Chart axes must use native compact currency formatting too')
   self.assertTrue(all(a[2]==currency for a in currency_calls))
   for i,page in enumerate(scenes):
    for n in page['nodes']:
     if 'amount' in n:self.assertEqual(s.get('scene'+str(i)).get(n['name']).get('text'),f'MOEDA{currency} {n["amount"]}')
 def test_operating_totals_include_staff_sponsor_costs_but_not_loan_principal(self):
  v=dict(date=20261123,months=[dict(month=202611,tv=100,tickets=200,sponsor=300,coach=-10,staff=-80,match_costs=-60,interest=-20,loans=-500,loan_credit=10000)])
  m=model(v);self.assertEqual((m['income'],m['expense'],m['result']),(600,170,430))
 def test_settings_and_ticket_navigation_fit_native_content_viewport(self):
  v=view();scenes=ui.scenes(v)
  settings=next(s for s in scenes if s['key']=='settings')
  toggles=[a for a in settings['actions'] if a['target'].startswith('toggle:')]
  self.assertEqual(len(toggles),len(SWITCHES))
  for a in toggles:self.assertLessEqual(a['y']+a['h'],804)
  receipts=next(s for s in scenes if s['key']=='receipts')
  self.assertIn('tickets',[a['target'] for a in receipts['actions']])

if __name__=='__main__':unittest.main()
