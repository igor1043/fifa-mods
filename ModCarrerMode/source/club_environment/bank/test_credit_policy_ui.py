import unittest
from loans import empty,presentation,AMOUNTS
from credit_policy import offers
from test_credit_policy import profile
from test_finance_live_ui import open_screen,text
from bank_design import ORDER,N

class CreditScreen(unittest.TestCase):
 def test_small_club_cannot_select_large_offer_and_amounts_cycle_in_value_order(self):
  state=empty(1043,20260301);view=presentation(state,20260301,20_000_000,ready=True,nonce='CREDIT_UI',currency=0,credit=offers(state,profile(2),20260301))
  vm,screen,_=open_screen(view);screen.set('page',1);screen.set('focus',ORDER.index(10));screen.set('amountIndex',8)
  vm.invoke(screen.get('Refresh'),screen)
  self.assertEqual(AMOUNTS[screen.get('amountIndex')],10_000_000)
  screen.set('focus',N);vm.invoke(screen.get('Shift'),screen,(1,))
  self.assertEqual(AMOUNTS[screen.get('amountIndex')],100_000)
  vm.invoke(screen.get('Shift'),screen,(1,));self.assertEqual(AMOUNTS[screen.get('amountIndex')],250_000)
  self.assertIn('R$',text(screen,'summaryValue0'))
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
 def test_refused_bank_cannot_open_confirmation_but_other_bank_can(self):
  state=empty(1043,20260301);state['applications']=[dict(id='old',bank=7,status='refused',decided_date=20260228)]
  view=presentation(state,20260301,20_000_000,ready=True,nonce='COOLDOWN_UI',credit=offers(state,profile(2),20260301))
  vm,screen,_=open_screen(view);screen.set('page',1);screen.set('focus',ORDER.index(7));vm.invoke(screen.get('Refresh'),screen)
  screen.set('focus',N+2);vm.invoke(screen.get('Select'),screen)
  self.assertEqual(screen.get('page'),1);self.assertIn('28/03/2026',text(screen,'status'))
  screen.set('focus',ORDER.index(10));vm.invoke(screen.get('Refresh'),screen)
  screen.set('focus',N+2);vm.invoke(screen.get('Select'),screen)
  self.assertEqual(screen.get('page'),2);self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

if __name__=='__main__':unittest.main()
