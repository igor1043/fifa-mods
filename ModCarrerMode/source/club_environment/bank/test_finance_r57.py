import portable_paths as portable
import unittest,copy,json,sys,struct
from loans import *
import bank_ui_r60 as ui
from formats import BigFile,AptFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from apt_test_vm import NativeVM

class FinanceTests(unittest.TestCase):
 def loan(self,state,today,ident):return borrow(state,request_id=ident,club=1043,today=today,budget=20_000_000,bank=0,amount=AMOUNTS[0],months=6)
 def test_two_contracts_per_year_and_only_one_active(self):
  state,budget,_=self.loan(empty(1043,20260101),20260101,'a')
  with self.assertRaises(ValueError):self.loan(state,20260101,'b')
  state,budget,_=pay(state,request_id='pay-a',club=1043,today=20260101,budget=budget,settle=True)
  state,budget,_=self.loan(state,20260201,'b');state,budget,_=pay(state,request_id='pay-b',club=1043,today=20260201,budget=budget,settle=True)
  with self.assertRaises(ValueError):self.loan(state,20260301,'c')
  fresh,_,_=self.loan(state,20270101,'c');self.assertEqual(len(fresh['contracts']),3)
 def test_manual_payment_does_not_double_debit_on_due_date(self):
  state,budget,_=self.loan(empty(1043,20260131),20260131,'a');original=copy.deepcopy(state)
  state,budget,events=pay(state,request_id='p',club=1043,today=20260201,budget=budget)
  self.assertEqual(original['contracts'][0]['paid'],0);self.assertEqual(state['contracts'][0]['paid'],1)
  repeated,b2,e=pay(state,request_id='p',club=1043,today=20260201,budget=budget);self.assertEqual(b2,budget);self.assertFalse(e)
  due,b2,e=advance(state,club=1043,today=20260228,budget=budget);self.assertEqual(b2,budget);self.assertFalse(e)
  self.assertEqual(presentation(due,20260228,b2)['schedule'][0]['status'],'Paga')
  with self.assertRaises(ValueError):pay(state,request_id='poor',club=1043,today=20260201,budget=0,settle=True)
 def test_native_ui_scoped_requests_and_payment_confirmation(self):
  state,budget,_=self.loan(empty(1043,20260101),20260101,'a');view=presentation(state,20260101,budget,nonce='TEST57')
  ui.build(view);apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'));actions=Actions(apt).read_all();self.assertFalse(actions.errors)
  calls=[]
  def native(name,obj,args):
   calls.append((name,args))
   if name=='Create':return tuple(args)
   if name=='GetScreenStaticData':return Object({'SCREEN_CONTROLLER_ID':'Calendar'})
   if name=='GetEvents':return Object({'BACK':'Back'})
   if name=='GetVisibleWidth':return 1702
   if name=='GetVisibleHeight':return 180
   if name=='GridControlData':return Object()
  vm=NativeVM(native);manager={k:Object({n:Native(n) for n in ns}) for k,ns in {'InputManager':['SetLocalEventHandler','DisableCurrentLocalEventHandler'],'ScreenManager':['SetOnExitScreenCallback','AddItemToAnimateIn','BeginAnimateIn'],'HelpManager':['Update','Clear'],'StyleManager':[]}.items()}
  manager['InputCodes']=Object({'ADVANCE':2,'BACK':1,'UP':3,'DOWN':4,'LEFT':5,'RIGHT':6,'SQUARE':7})
  vm.global_.set('game',Object({'globalClasses':Object(manager),'components':Object({'GridControlData':Native('GridControlData'),'GridControl':Object({'CELL_GAP':10,'STYLE_TILES':1})})}))
  vm.global_.set('ION_CareerMode',Object({n:Native(n) for n in ['GetScreenStaticData','GetEvents','SendEvent','SendSystemEvent']}));vm.global_.set('cafe',Object({'utility':Object({'Delegate':Object({'Create':Native('Create')})})}));vm.global_.set('ion',Object({'screen':Object({'BaseScreen':Object({'prototype':Object({'Initialize':Native('Initialize'),'Shutdown':Native('Shutdown')})})}),'manager':Object({'HelpItem':Object({'CreateHelpTickerItem':Native('CreateHelpTickerItem')})})}))
  blocks=list(actions.cache.values());vm.pending_packages={ui.b.FULL:blocks[0]};vm.run(blocks[1],vm.global_,vm.global_);klass=vm.path(ui.b.FULL)
  screen=Object({p.name:Object() for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name},klass.get('prototype'))
  grid=screen.get('mcGridControl')
  for n in ('GetVisibleWidth','GetVisibleHeight','Init','EnableMouseButton','Shutdown','LocalEventHandler'):grid.set(n,Native(n))
  for name in [f'row{i}' for i in range(5)]+['payNext','payAll','ledgerBack','previousStatement','nextStatement']:
   obj=screen.get(name)
   for child in ('label','hint','selected','less','more'):obj.set(child,Object())
  vm.invoke(klass,screen);self.assertEqual(screen.get('page'),0);self.assertEqual(screen.get('focus'),1)
  def export(name):
   def plain(o):
    if isinstance(o,Object):return {str(k):plain(v) for k,v in o.values.items() if k not in ('owner','staticData','navEvents') and not callable(v) and not hasattr(v,'body')}
    if isinstance(o,(str,int,float,bool)) or o is None:return o
    return None
   (ui.b.HERE/'runtime'/('render_focus_'+name+'.json')).write_text(json.dumps(plain(screen),ensure_ascii=False,indent=2),encoding='utf8')
  export('home')
  vm.invoke(screen.get('WaitButtons'),screen)
  # Mouse hover/click and the pad use the same focus/selection methods.
  vm.invoke(screen.get('row1').get('onRollOver'),screen.get('row1'));self.assertEqual(screen.get('focus'),1)
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),3)
  export('ledger')
  # Every action in the statement is reached with the same D-pad focus.
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));self.assertEqual(screen.get('focus'),1)
  vm.invoke(screen.get('LocalEventHandler'),screen,(3,0));self.assertEqual(screen.get('focus'),0)
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),4)
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),5);self.assertIn('|1|0|0|1|END_S16BANK',vm.global_.get('Server16BankRequestV2'))
  # On a new-credit view, all three fields can be changed without losing
  # focus; only the explicit review confirmation publishes a request.
  ui.VIEW['active']=None;ui.VIEW['can_borrow']=True
  screen.set('page',1);screen.set('focus',0);vm.global_.set('Server16BankRequestV2',None)
  vm.invoke(screen.get('LocalEventHandler'),screen,(6,0));self.assertEqual(screen.get('bank'),1)
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));self.assertEqual(screen.get('focus'),1)
  vm.invoke(screen.get('LocalEventHandler'),screen,(6,0));self.assertEqual(screen.get('amountIndex'),1)
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));vm.invoke(screen.get('LocalEventHandler'),screen,(6,0));self.assertEqual(screen.get('termIndex'),2)
  export('form')
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),2);self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertEqual(screen.get('page'),6)
  vm.invoke(screen.get('LocalEventHandler'),screen,(6,0));self.assertEqual(screen.get('statementPage'),1);self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
  self.assertEqual(screen.get('cell1_0').get('text'),'09');self.assertIn('2026',screen.get('cell1_1').get('text'));self.assertEqual(screen.get('cell1_3').get('text'),'Prevista')
  vm.invoke(screen.get('LocalEventHandler'),screen,(1,0));self.assertEqual(screen.get('page'),2)
  vm.invoke(screen.get('LocalEventHandler'),screen,(4,0));self.assertEqual(screen.get('focus'),0)
  vm.invoke(screen.get('LocalEventHandler'),screen,(2,0));self.assertIn('|0|1|1|2|END_S16BANK',vm.global_.get('Server16BankRequestV2'))
  self.assertFalse(any(name in ('StartCalendarSim','Save') for name,args in calls))

if __name__=='__main__':unittest.main(verbosity=2)
