import unittest
from unittest.mock import patch
from loans import empty,borrow,pay,advance,presentation
from bank_design import N
from test_finance_live_ui import open_screen,text
from formats import AptFile,BigFile,Placement
import bank_ui_r60 as ui

class LoanNavigationTests(unittest.TestCase):
 def view(self):return presentation(empty(517,20260208),20260208,24_500_000,ready=True,nonce='VIEWS',club_name='Botafogo',wage_budget=100_000)
 def history(self):
  state,budget,_=borrow(empty(517,20260101),request_id='old',club=517,today=20260101,budget=24_500_000,bank=3,amount=1_000_000,months=6)
  state,budget,_=pay(state,request_id='settled',club=517,today=20260102,budget=budget,settle=True)
  # Preserve a pre-policy contract history to check old statement rendering.
  with patch('loans.borrowing_date',return_value=0):
   state,budget,_=borrow(state,request_id='active',club=517,today=20260201,budget=budget,bank=7,amount=3_000_000,months=12)
  state,budget,_=advance(state,club=517,today=20260301,budget=budget)
  return presentation(state,20260301,budget,ready=True,nonce='HISTORY',club_name='Botafogo',wage_budget=100_000)
 def press(self,vm,screen,method,*args):return vm.invoke(screen.get(method),screen,args)

 def test_native_stage_depths_are_unique_and_panels_are_below_labels_and_actions(self):
  vm,screen,_=open_screen(self.view())
  apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'))
  stage=[p for p in apt.characters[9].frames[0] if isinstance(p,Placement)]
  self.assertEqual(len(stage),len({p.depth for p in stage}))
  named={p.name:p for p in stage if p.name}
  for panel,label,button in (('overviewPanel','overviewState','homeNew'),('bankHero','bankHeading','bankTile0'),('statementPanel','statementHeading','payNext')):
   self.assertLess(named[panel].depth,named[label].depth);self.assertLess(named[label].depth,named[button].depth)
  self.assertLess(named['tableRow0'].depth,named['cell1_0'].depth)

 def test_back_from_fields_and_onscreen_back_return_to_selected_bank_with_amount_and_term_preserved(self):
  vm,screen,_=open_screen(self.view());screen.set('page',1);screen.set('focus',4);self.press(vm,screen,'Refresh')
  self.press(vm,screen,'Select');self.assertEqual(screen.get('focus'),N)
  self.press(vm,screen,'Shift',2);self.press(vm,screen,'MoveFocus',1);self.press(vm,screen,'Shift',1)
  bank=screen.get('bank');amount=screen.get('amountIndex');term=screen.get('termIndex')
  self.press(vm,screen,'Back');self.assertEqual((screen.get('page'),screen.get('focus')),(1,4))
  self.assertEqual((screen.get('bank'),screen.get('amountIndex'),screen.get('termIndex')),(bank,amount,term))
  screen.set('focus',N+3);self.press(vm,screen,'Refresh');button=screen.get('formBack')
  vm.invoke(button.get('onRelease'),button);self.assertEqual((screen.get('page'),screen.get('focus')),(1,4))
  self.press(vm,screen,'Back');self.assertEqual(screen.get('page'),0)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

 def test_each_contract_has_its_own_schedule_and_a_paid_contract_cannot_pay_the_active_one(self):
  view=self.history();vm,screen,_=open_screen(view)
  screen.set('focus',1);self.press(vm,screen,'Select');self.assertEqual(screen.get('page'),7)
  self.assertIn('Banrisul',text(screen,'contractHeading'));self.press(vm,screen,'Select')
  self.assertEqual(screen.get('page'),3);self.assertEqual(text(screen,'cell1_0'),'01 / 12')
  self.assertEqual(text(screen,'cell1_1'),'01/03/2026');self.assertTrue(screen.get('payNext').get('_visible'))
  self.press(vm,screen,'Back');self.press(vm,screen,'MoveFocus',1);self.press(vm,screen,'Select')
  self.assertEqual(text(screen,'cell1_0'),'01 / 6');self.assertEqual(text(screen,'cell1_1'),'01/02/2026')
  self.assertIn('Quitado',text(screen,'statementHeading'))
  self.assertFalse(screen.get('payNext').get('_visible'));self.assertFalse(screen.get('payAll').get('_visible'))
  self.assertEqual(screen.get('cell1_3').get('textColor'),0x26744a)
  screen.set('focus',6);self.press(vm,screen,'Select');self.assertEqual(screen.get('page'),7)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
  self.press(vm,screen,'Back');self.assertEqual(screen.get('page'),0)

 def test_page_changes_do_not_leave_panels_headers_or_scrollbars_from_other_views(self):
  vm,screen,_=open_screen(self.view())
  for page in (1,0,7,3,0,1,7):
   screen.set('page',page);screen.set('focus',0);self.press(vm,screen,'Refresh')
   if page!=1:
    for name in ('bankHero','optionsPanel','simulationPanel','ratePanel'):self.assertFalse(screen.get(name).get('_visible'),(page,name))
   if page!=0:self.assertFalse(screen.get('overviewPanel').get('_visible'))
   if page in (0,1,7,3):
    for name in ('tableHeader','scrollTrack','scrollThumb'):self.assertFalse(screen.get(name).get('_visible'),(page,name))
  self.assertEqual(text(screen,'pageInfo'),'')

 def test_no_contract_uses_an_explanatory_card_instead_of_an_empty_table(self):
  vm,screen,_=open_screen(self.view());screen.set('focus',1);self.press(vm,screen,'Select')
  self.assertEqual(screen.get('page'),7);self.assertIn('Nenhum contrato',text(screen,'contractHeading'))
  self.assertFalse(screen.get('tableHeader').get('_visible'));self.assertFalse(screen.get('scrollTrack').get('_visible'))
  self.assertEqual(text(screen,'pageInfo'),'');self.assertEqual(text(screen,'contractListInfo'),'')
  self.press(vm,screen,'Select');self.assertEqual(screen.get('page'),1)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

 def test_mouse_hover_in_a_scrolled_statement_keeps_the_row_under_the_pointer(self):
  state,budget,_=borrow(empty(517,20260101),request_id='long',club=517,today=20260101,budget=24_500_000,bank=7,amount=1_000_000,months=24)
  vm,screen,_=open_screen(presentation(state,20260101,budget,ready=True,nonce='SCROLL'))
  screen.set('page',3);screen.set('focus',0);self.press(vm,screen,'Refresh')
  for _ in range(16):self.press(vm,screen,'MoveFocus',1)
  before=screen.get('tableRow2').get('index');row=screen.get('tableRow2')
  vm.invoke(row.get('onRollOver'),row);self.assertEqual(row.get('index'),before)
  vm.invoke(row.get('onRelease'),row);self.assertEqual(screen.get('focus'),before)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


 def test_contract_history_scrolls_with_the_pad_and_preserves_the_selected_item_on_mouse_click(self):
  state=empty(517,20200101);budget=24_500_000
  for i in range(7):
   today=(2020+i)*10000+101
   state,budget,_=borrow(state,request_id='loan'+str(i),club=517,today=today,budget=budget,bank=3+i%6,amount=1_000_000,months=6)
   state,budget,_=pay(state,request_id='pay'+str(i),club=517,today=today,budget=budget,settle=True)
  vm,screen,_=open_screen(presentation(state,20260101,budget,ready=True,nonce='LIST_SCROLL'))
  screen.set('focus',1);self.press(vm,screen,'Select')
  for _ in range(6):self.press(vm,screen,'MoveFocus',1)
  self.assertEqual(screen.get('contractOffset'),2)
  row=screen.get('contractTile1');before=row.get('index')
  vm.invoke(row.get('onRollOver'),row);self.assertEqual(row.get('index'),before)
  vm.invoke(row.get('onRelease'),row);self.assertEqual(screen.get('page'),3)
  self.assertEqual(screen.get('contractIndex'),before);self.assertIn('Quitado',text(screen,'statementHeading'))
  self.press(vm,screen,'Back');self.assertEqual(screen.get('page'),7);self.assertEqual(screen.get('focus'),before)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


 def test_pending_application_in_the_contract_list_keeps_original_dates_and_does_not_offer_duplicate_credit(self):
  from loans import request_loan
  state,budget,_=request_loan(empty(517,20260208),request_id='pending',club=517,today=20260208,budget=24_500_000,bank=7,amount=1_000_000,months=12)
  view=presentation(state,20260208,budget,ready=True,nonce='PENDING_LIST')
  vm,screen,_=open_screen(view);screen.set('focus',1);self.press(vm,screen,'Select')
  self.assertEqual(screen.get('page'),7)
  self.assertIn('08/02/2026',text(screen,'contractLine0'));self.assertIn('10/02/2026',text(screen,'contractLine1'))
  self.press(vm,screen,'Select');self.assertEqual(screen.get('page'),7)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
