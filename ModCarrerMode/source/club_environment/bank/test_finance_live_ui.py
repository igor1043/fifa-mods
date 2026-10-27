import json,unittest
from unittest.mock import patch
import ctypes
import bank_ui_r60 as ui
import runtime as bridge
from loans import empty,borrow,request_loan,presentation,AMOUNTS
from formats import AptFile,BigFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM

def text(screen,field):
 # The inspection reader exposes raw APT UTF-8 bytes through Latin-1.
 value=screen.get(field).get('text')
 return value.encode('latin1').decode('utf8')

class BankInputVM(NativeVM):
 def invoke(self,function,owner,args=()):
  if self.depth==0:self.steps=0
  return super().invoke(function,owner,args)

def open_screen(view,globals_=None,currency_formatter=None):
 ui.build(view);apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'));actions=Actions(apt).read_all()
 assert not actions.errors
 calls=[]
 def native(name,obj,args):
  calls.append((name,args))
  if name in ('Create','CreateHelpTickerItem'):return tuple(args)
  if name=='GetScreenStaticData':return Object({'SCREEN_CONTROLLER_ID':'Calendar'})
  if name=='GetEvents':return Object({'BACK':'Back'})
  if name=='LocalizeCurrencyWithType':return currency_formatter(*args) if currency_formatter else f'{args[1]:,}'.replace(',','.')
 vm=BankInputVM(native)
 if globals_ is not None:vm.global_=globals_
 manager={k:Object({n:Native(n) for n in ns}) for k,ns in {'InputManager':['SetLocalEventHandler','DisableCurrentLocalEventHandler'],'ScreenManager':['SetOnExitScreenCallback','BeginAnimateIn'],'HelpManager':['Update','Clear']}.items()}
 manager['InputCodes']=Object({'ADVANCE':2,'BACK':1,'UP':3,'DOWN':4,'LEFT':5,'RIGHT':6})
 vm.global_.set('game',Object({'globalClasses':Object(manager)}))
 vm.global_.set('ION_CareerMode',Object({n:Native(n) for n in ('GetScreenStaticData','GetEvents','SendEvent','SendSystemEvent')}))
 vm.global_.set('ION_Localization',Object({'LocalizeCurrencyWithType':Native('LocalizeCurrencyWithType')}))
 vm.global_.set('cafe',Object({'utility':Object({'Delegate':Object({'Create':Native('Create')})})}))
 vm.global_.set('ion',Object({'screen':Object({'BaseScreen':Object({'prototype':Object({'Initialize':Native('Initialize'),'Shutdown':Native('Shutdown')})})}),'manager':Object({'HelpItem':Object({'CreateHelpTickerItem':Native('CreateHelpTickerItem')})})}))
 blocks=list(actions.cache.values());vm.pending_packages={ui.b.FULL:blocks[0]};vm.run(blocks[1],vm.global_,vm.global_);klass=vm.path(ui.b.FULL)
 stage={p.depth:p for p in apt.characters[9].frames[0] if isinstance(p,Placement)}
 assert len(stage)==len([p for p in apt.characters[9].frames[0] if isinstance(p,Placement)]),'Native APT depth collision'
 screen=Object({p.name:Object() for p in stage.values() if p.name},klass.get('prototype'))
 for name,*_ in ui.BUTTONS:
  for child in ('label','hint','selected','selection','less','more'):screen.get(name).set(child,Object())
  for side in ('less','more'):screen.get(name).get(side).set('glyph',Object())
 vm.invoke(klass,screen);vm.invoke(screen.get('WaitButtons'),screen)
 return vm,screen,calls

class LiveFinanceTests(unittest.TestCase):
 def view(self):return presentation(empty(1043,20260101),20260101,20_000_000,nonce='TEST_LIVE',ready=True)
 def submit(self,vm,screen):
  screen.set('page',2);screen.set('focus',0);vm.invoke(screen.get('Select'),screen)
 def test_first_open_waits_for_context_without_sending_a_loan(self):
  view=self.view();view.update(date=None,ready=False,can_borrow=False,nonce='DISABLED')
  vm,screen,calls=open_screen(view)
  for _ in range(90):vm.invoke(screen.get('PollResult'),screen)
  self.assertIn(('SendSystemEvent',['Calendar','Server16RefreshBank','']),calls)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
 def test_pending_reload_then_verified_result_and_live_statement(self):
  before=self.view();vm,screen,calls=open_screen(before);self.submit(vm,screen)
  request=vm.global_.get('Server16BankRequestV2');self.assertEqual(len(bridge.requests_in(request.encode(),before['nonce'])),1)
  self.assertIn('|20260101|END_S16BANK',request)
  self.assertEqual(text(screen,'section'),'Registrando solicitação...')
  for _ in range(90):vm.invoke(screen.get('PollResult'),screen)
  self.assertIn(('SendSystemEvent',['Calendar','Server16RefreshBank','']),calls)
  self.assertEqual(vm.global_.get('Server16BankRequestV2'),request)
  state,budget,_=borrow(empty(1043,20260101),request_id='test',club=1043,today=20260101,budget=20_000_000,bank=0,amount=AMOUNTS[0],months=12)
  after=presentation(state,20260101,budget,nonce='TEST_LIVE',ready=True,result={'sequence':1,'ok':True,'budget':budget,'message':'Crédito aplicado. Salve a carreira no FIFA.'})
  vm.invoke(screen.get('OnExitScreen'),screen)
  vm,screen,calls=open_screen(after,vm.global_)
  self.assertEqual(screen.get('page'),5);self.assertIsNone(vm.global_.get('Server16BankPendingNonce'))
  self.assertEqual(text(screen,'section'),'Operação aplicada')
  self.assertIn('21.000.000',screen.get('detail2').get('text'))
  vm.invoke(screen.get('Select'),screen);self.assertEqual(screen.get('page'),3)
  self.assertEqual(screen.get('cell1_0').get('text'),'01 / 12');self.assertEqual(screen.get('cell1_1').get('text'),'01/02/2026')
  vm.invoke(screen.get('Back'),screen);self.assertEqual(screen.get('page'),7)
  vm.invoke(screen.get('Back'),screen);self.assertEqual(screen.get('page'),0)
  screen.set('focus',0);vm.invoke(screen.get('Select'),screen);self.assertEqual(screen.get('page'),1)
  self.assertEqual(vm.global_.get('Server16BankRequestV2'),request)
 def test_wrong_sequence_does_not_claim_success_and_refusal_shows_reason(self):
  view=self.view();vm,screen,_=open_screen(view);self.submit(vm,screen)
  view['result']={'sequence':99,'ok':True,'message':'WRONG'}
  vm,screen,_=open_screen(view,vm.global_);self.assertEqual(text(screen,'section'),'Registrando solicitação...')
  view['result']={'sequence':1,'ok':False,'message':'Saldo insuficiente.'}
  vm,screen,_=open_screen(view,vm.global_);self.assertEqual(text(screen,'section'),'Operação não aplicada')
  self.assertEqual(screen.get('detail0').get('text'),'Saldo insuficiente.');self.assertIn('20.000.000',screen.get('detail2').get('text'))
 def test_registered_application_shows_response_date_and_blocks_duplicate(self):
  view=self.view();vm,screen,_=open_screen(view);self.submit(vm,screen)
  state,budget,_=request_loan(empty(1043,20260101),request_id='pending',club=1043,today=20260101,budget=20_000_000,bank=0,amount=AMOUNTS[0],months=12)
  view=presentation(state,20260101,budget,nonce='TEST_LIVE',ready=True,result={'sequence':1,'ok':True,'kind':'loan_requested','decision_date':20260102})
  vm,screen,_=open_screen(view,vm.global_)
  self.assertEqual(text(screen,'section'),'Solicitação registrada');self.assertIn('02/01/2026',text(screen,'detail2'))
  self.assertIn('20.000.000',text(screen,'detail6'));self.assertNotIn('21.000.000',text(screen,'detail6'))
  vm.invoke(screen.get('Select'),screen);self.assertEqual(screen.get('page'),0)
  self.assertIn('02/01/2026',text(screen,'overviewLine1'))
  screen.set('focus',0);vm.invoke(screen.get('Select'),screen);self.assertEqual(screen.get('page'),0)
  for day in (20260102,20260103):
   view['date']=day;vm,screen,_=open_screen(view);screen.set('page',0);vm.invoke(screen.get('Refresh'),screen)
   self.assertIn('01/01/2026',text(screen,'overviewLine0'));self.assertIn('02/01/2026',text(screen,'overviewLine1'))
 def test_budget_readback_precedes_success_response(self):
  for readback_ok in (True,False):
   b=bridge.Bridge.__new__(bridge.Bridge);b.apply=True;b.session='test';b.scope='test';b.state={};b.result=None;b.process=type('P',(),{'pid':1})();b.write_handle=1
   before={'club':1043,'address':0x1234,'budget':20,'date':20260101,'page':bridge.PAGE};b.live=lambda:before;b.io_tick=1
   class Kernel:
    def WriteProcessMemory(self,handle,address,data,size,written):
     self.payload=ctypes.string_at(data,size);ctypes.cast(written,ctypes.POINTER(ctypes.c_size_t))[0]=size;return True
   k=Kernel();b.memory=type('M',(),{'kernel32':k,'read_uint32':lambda _,at:21 if readback_ok else 20})()
   shown=[];b.flush_notifications=lambda live:shown.append((live,b.result))
   b.publish_view=lambda _:self.fail('Rendering must not block notification publication')
   with patch.object(bridge,'write_json'),patch.object(bridge,'log'),patch.object(bridge.time,'sleep'),patch.object(bridge.loan_notifications,'record') as record:
    if readback_ok:
     state,_,_=borrow(empty(1043,20260101),request_id='verified',club=1043,today=20260101,budget=20,bank=0,amount=1_000_000,months=12)
     b.publish(before,state,21,[{'type':'credit'}],'loan_confirmed',{'sequence':1,'action':0})
     self.assertTrue(shown[0][1]['ok']);self.assertEqual(shown[0][0]['budget'],21)
     self.assertEqual(record.call_count,1)
    else:
     with self.assertRaises(RuntimeError):b.publish(before,{},21,[],'loan_confirmed',{'sequence':1})
     self.assertFalse(shown);self.assertIsNone(b.result)
     record.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
