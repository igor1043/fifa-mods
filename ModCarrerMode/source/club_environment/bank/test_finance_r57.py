import portable_paths as portable
import unittest,copy,json,sys,struct
from loans import *
import bank_ui_r60 as ui
from formats import BigFile,AptFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from test_finance_live_ui import BankInputVM as NativeVM

class FinanceTests(unittest.TestCase):
 def test_unavailable_career_date_builds_disabled_view(self):
  for value in (None,0,20260000,20260230):
   ui.build({'date':value,'club':0,'budget':0,'used':0,'ready':True,'can_borrow':True,'nonce':'UNSAFE','schedule':[],'active':None})
   self.assertFalse(ui.VIEW['ready']);self.assertFalse(ui.VIEW['can_borrow']);self.assertEqual(ui.VIEW['nonce'],'DISABLED')
   self.assertEqual(ui.due_date(value,1),'Não disponível')
 def loan(self,state,today,ident):return borrow(state,request_id=ident,club=1043,today=today,budget=20_000_000,bank=0,amount=AMOUNTS[0],months=6)
 def test_four_contracts_with_two_calendar_months_between_them(self):
  state=empty(1043,20260101)
  for ident,day in zip('abcd',(20260101,20260301,20260501,20260701)):
   state,budget,_=self.loan(state,day,ident)
  self.assertEqual(len(state['contracts']),4)
  with self.assertRaisesRegex(ValueError,'quatro'):self.loan(state,20260901,'e')
  for ident in 'abcd':state,budget,_=pay(state,request_id='pay-'+ident,club=1043,today=20260702,budget=budget,settle=True,contract_id=ident)
  with self.assertRaisesRegex(ValueError,'quatro'):self.loan(state,20260901,'e')
  fresh,_,_=self.loan(state,20270101,'e');self.assertEqual(len(fresh['contracts']),5)
 def test_manual_payment_does_not_double_debit_on_due_date(self):
  state,budget,_=self.loan(empty(1043,20260131),20260131,'a');original=copy.deepcopy(state)
  state,budget,events=pay(state,request_id='p',club=1043,today=20260201,budget=budget)
  self.assertEqual(original['contracts'][0]['paid'],0);self.assertEqual(state['contracts'][0]['paid'],1)
  repeated,b2,e=pay(state,request_id='p',club=1043,today=20260201,budget=budget);self.assertEqual(b2,budget);self.assertFalse(e)
  due,b2,e=advance(state,club=1043,today=20260228,budget=budget);self.assertEqual(b2,budget);self.assertFalse(e)
  self.assertEqual(presentation(due,20260228,b2)['schedule'][0]['status'],'Paga')
  with self.assertRaises(ValueError):pay(state,request_id='poor',club=1043,today=20260201,budget=0,settle=True)
 def test_native_ui_scoped_requests_and_payment_confirmation(self):
  from test_finance_live_ui import open_screen
  state,budget,_=self.loan(empty(1043,20260101),20260101,'a')
  view=presentation(state,20260101,budget,nonce='TEST57',ready=True)
  vm,screen,calls=open_screen(view)
  self.assertEqual(screen.get('page'),0)
  self.assertEqual(screen.get('focus'),1) # New credit is disabled during the two-month interval.
  vm.invoke(screen.get('homeContracts').get('onRollOver'),screen.get('homeContracts'))
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),7)
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),3)
  screen.set('focus',len(view['schedule']))
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),4)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),5)
  request=vm.global_.get('Server16BankRequestV2')
  self.assertIn('TEST57',request);self.assertIn('|1|7|0|1|20260101|a|END_S16BANK',request)
  self.assertFalse(any(name in ('StartCalendarSim','Save') for name,args in calls))
  vm.invoke(screen.get('OnExitScreen'),screen)
  count=len(calls);vm.invoke(screen.get('OnExitScreen'),screen);vm.invoke(screen.get('OnAnimateInComplete'),screen)
  self.assertEqual(len(calls),count)

if __name__=='__main__':unittest.main(verbosity=2)
