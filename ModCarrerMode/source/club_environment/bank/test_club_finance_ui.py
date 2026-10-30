import tempfile,unittest,json,struct,xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch
import finance_ui as ui
import finance_package as package
import runtime as bridge
import club_finance as finance
from test_club_finance import context
from loans import empty
from formats import AptFile,BigFile,Placement
from apt_actions import Actions
from apt_vm import Object,Native
from test_finance_live_ui import BankInputVM,text

def view():
 state,budget,_=finance.apply(empty(1043,20260511),club=1043,today=20260511,budget=20_000_000,context=context())
 book=state['finance']
 return dict(ready=True,club=1043,club_name='Flamengo',date=20260511,start=20260511,budget=budget,
  months=[],agreements=list(book['agreements'].values()),coach_monthly=164667,settings=book['settings'],currency=0,currency_labels={'CM_DollarCurrency':'Real','CM_EuroCurrency':'Dólares','CM_PoundsCurrency':'Euros'},nonce='B57_123_1043_TEST',ack=0)

def open_finance(payload,globals_=None):
 with tempfile.TemporaryDirectory() as folder:
  file=Path(folder)/'screen.big';ui.build(payload,file);apt=AptFile(BigFile(file));actions=Actions(apt).read_all()
 if actions.errors:raise AssertionError(actions.errors)
 calls=[]
 def native(name,obj,args):
  calls.append((name,args))
  if name in ('Create','CreateHelpTickerItem'):return tuple(args)
  if name=='GetScreenStaticData':return Object({'SCREEN_CONTROLLER_ID':'Calendar'})
  if name=='GetEvents':return Object({'BACK':'Back'})
  if name=='LocalizeCurrencyWithType':return f'MOEDA{args[2]} {args[1]}'
 vm=BankInputVM(native)
 if globals_ is not None:vm.global_=globals_
 managers={k:Object({n:Native(n) for n in ns}) for k,ns in {'InputManager':['SetLocalEventHandler','DisableCurrentLocalEventHandler'],'ScreenManager':['SetOnExitScreenCallback','BeginAnimateIn'],'HelpManager':['Update','Clear']}.items()}
 managers['InputCodes']=Object({'ADVANCE':2,'BACK':1,'UP':3,'DOWN':4,'LEFT':5,'RIGHT':6,'LAS_UP':7,'LAS_DOWN':8,'L2':9,'R2':10,'RAS_UP':11,'RAS_DOWN':12})
 vm.global_.set('game',Object({'globalClasses':Object(managers)}))
 vm.global_.set('ION_CareerMode',Object({n:Native(n) for n in ('GetScreenStaticData','GetEvents','SendEvent','SendSystemEvent')}))
 vm.global_.set('ION_Localization',Object({'LocalizeCurrencyWithType':Native('LocalizeCurrencyWithType')}))
 vm.global_.set('cafe',Object({'utility':Object({'Delegate':Object({'Create':Native('Create')})})}))
 vm.global_.set('ion',Object({'screen':Object({'BaseScreen':Object({'prototype':Object({'Initialize':Native('Initialize'),'Shutdown':Native('Shutdown')})})}),'manager':Object({'HelpItem':Object({'CreateHelpTickerItem':Native('CreateHelpTickerItem')})})}))
 blocks=list(actions.cache.values());vm.pending_packages={ui.FULL:blocks[0]};vm.run(blocks[1],vm.global_,vm.global_);klass=vm.path(ui.FULL)
 named={p.name:p for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name}
 screen=Object({n:Object() for n in named},klass.get('prototype'))
 for name,part in named.items():
  for p in apt.characters[part.character].frames[0]:
   if isinstance(p,Placement) and p.name:screen.get(name).set(p.name,Object({'selected':Object()}))
 vm.invoke(klass,screen);vm.invoke(screen.get('WaitClips'),screen)
 return vm,screen,calls

class ClubFinanceUITests(unittest.TestCase):
 def registered_buttons(self,screen,items):
  return [(i,screen.get('scene'+str(i)).get('action'+str(j)))
   for i,row in enumerate(items) for j,_ in enumerate(row['actions'])
   if screen.get('scene'+str(i)).get('action'+str(j)).get('onRelease') is not None
    or screen.get('scene'+str(i)).get('action'+str(j)).get('onRollOver') is not None]
 def test_mouse_listeners_follow_only_the_visible_page_and_release_owner_cycles(self):
  payload=view();items=ui.scenes(payload);vm,s,_=open_finance(payload)
  for page,row in enumerate(items):
   vm.invoke(s.get('Go'),s,[page]);buttons=self.registered_buttons(s,items)
   self.assertEqual([i for i,_ in buttons],[page]*len(row['actions']))
   for i,other in enumerate(items):
    self.assertEqual(bool(s.get('scene'+str(i)).get('_visible')),i==page)
    for j,_ in enumerate(other['actions']):
     owner=s.get('scene'+str(i)).get('action'+str(j)).get('owner')
     self.assertIs(owner,s if i==page else None)
  vm.invoke(s.get('OnExitScreen'),s)
  self.assertEqual(self.registered_buttons(s,items),[])
  for i,row in enumerate(items):
   for j,_ in enumerate(row['actions']):self.assertIsNone(s.get('scene'+str(i)).get('action'+str(j)).get('owner'))
 def test_long_receipt_history_and_native_reload_stay_below_the_512_button_pool(self):
  from datetime import date,timedelta
  payload=view();payload.update(club=55,date=20261130,entries=[])
  for ident in range(80):
   home,away=(55,66) if ident%2==0 else (66,55)
   stamp=int((date(2026,5,11)+timedelta(days=ident)).strftime('%Y%m%d'))
   for kind in (('tv','tickets') if home==55 else ('tv',)):
    payload['entries'].append(dict(id=f'{kind}:20260511:7:{ident}:{home}:{away}',kind=kind,date=stamp,
     fixture=ident,home=home,away=away,home_name='Clube '+str(home),away_name='Clube '+str(away),
     competition_asset=7,description='Liga',amount=1000,status='applied'))
  items=ui.scenes(payload);self.assertGreater(sum(len(row['actions']) for row in items),512)
  vm,s,_=open_finance(payload)
  for page in (0,next(i for i,row in enumerate(items) if row['key']=='tv:all'),len(items)-1):
   vm.invoke(s.get('Go'),s,[page]);self.assertLess(len(self.registered_buttons(s,items)),128)
  for _ in range(2):
   old=s;vm.invoke(old.get('OnExitScreen'),old)
   vm,s,_=open_finance(payload,vm.global_)
   self.assertEqual(self.registered_buttons(old,items),[])
   self.assertLess(len(self.registered_buttons(s,items)),128)
   self.assertEqual(vm.errors,[])
 def test_native_charts_use_block_aligned_dxt5_surfaces(self):
  with tempfile.TemporaryDirectory() as folder:
   path=Path(folder)/'finance.big';ui.build(view(),path);assets=BigFile(path)
   textures=[bytes(row.data) for row in assets.entries.values() if bytes(row.data[:4])==b'DDS ']
   self.assertGreater(len(textures),10)
   for texture in textures:
    h,w=struct.unpack_from('<II',texture,12)
    self.assertEqual((w%4,h%4),(0,0));self.assertEqual(texture[84:88],b'DXT5')
 def test_native_currency_help_and_no_financial_request_on_open(self):
  vm,s,calls=open_finance(view())
  self.assertEqual(s.get('scene0').get('money0').get('text'),'R$ 20.000.000')
  help_=vm.invoke(s.get('getHelpContext'),s)
  self.assertIn(('L2R2','Abas'),help_)
  self.assertFalse(any(n=='SendSystemEvent' and args[1]=='Server16SubmitBank' for n,args in calls))
  self.assertTrue(any(n=='BeginAnimateIn' for n,args in calls),'FIFA must release the native view presentation gate')
 def test_shoulders_switch_tabs_mouse_and_up_select_switches(self):
  vm,s,calls=open_finance(view());vm.invoke(s.get('LocalEventHandler'),s,[10,None])
  self.assertEqual(ui.scenes(view())[s.get('page')]['key'],'receipts')
  settings=next(i for i,v in enumerate(ui.scenes(view())) if v['key']=='settings')
  vm.invoke(s.get('Go'),s,[settings]);s.set('focus',len(ui.TABS));vm.invoke(s.get('Select'),s)
  wire=next(args[2] for n,args in calls if n=='SendSystemEvent' and args[1]=='Server16SubmitBank')
  rows=bridge.requests_in(wire.encode(),view()['nonce']);self.assertEqual(next(iter(rows))[1:5],(2,0,0,0))
  self.assertEqual(s.get('onEnterFrame'),s.get('Poll'))
  for _ in range(90):vm.invoke(s.get('Poll'),s)
  self.assertNotIn(('SendSystemEvent',['Calendar','Server16RefreshClubFinance','']),calls)
  vm.invoke(s.get('OnExitScreen'),s)
  updated=view();updated['ack']=1;updated['settings']['enabled']=False;updated['setting_result']=dict(sequence=1,ok=True,message='Configuração aplicada.')
  vm,s,calls=open_finance(updated,vm.global_);self.assertEqual(s.get('page'),settings);self.assertIsNone(s.get('onEnterFrame'))
  self.assertEqual(s.get('focus'),len(ui.TABS))
  self.assertEqual(text(s.get('scene'+str(settings)),'settingsFeedback'),'Configuração aplicada.')
 def test_switch_changes_immediately_blocks_duplicate_click_and_confirms_without_manual_exit(self):
  payload=view();items=ui.scenes(payload);settings=next(i for i,r in enumerate(items) if r['key']=='settings')
  vm,s,calls=open_finance(payload);vm.invoke(s.get('Go'),s,[settings]);s.set('focus',len(ui.TABS)+1)
  button=s.get('scene'+str(settings)).get('action'+str(len(ui.TABS)+1));vm.invoke(button.get('onRelease'),button)
  clip=s.get('scene'+str(settings));self.assertFalse(clip.get('switchOn1').get('_visible'));self.assertTrue(clip.get('switchOff1').get('_visible'))
  self.assertEqual(clip.get('switchState1').get('text'),'Desativado');self.assertIn('Aplicando',clip.get('settingsFeedback').get('text'))
  vm.invoke(button.get('onRelease'),button)
  events=[args for n,args in calls if n=='SendSystemEvent' and args[1]=='Server16SubmitBank'];self.assertEqual(len(events),1)
  self.assertEqual(next(iter(bridge.requests_in(events[0][2].encode(),payload['nonce'])))[1:5],(2,1,0,0))
  vm.invoke(s.get('OnExitScreen'),s);pending_globals=vm.global_
  vm,s,calls=open_finance(payload,pending_globals);self.assertTrue(s.get('waitingSetting'));self.assertFalse(s.get('setting1'))
  vm.invoke(s.get('OnExitScreen'),s);payload['ack']=1;payload['settings']['tv']=False;payload['setting_result']=dict(sequence=1,ok=True,message='Configuração aplicada.')
  vm,s,calls=open_finance(payload,vm.global_);self.assertFalse(s.get('waitingSetting'))
  s.set('focus',len(ui.TABS)+1);vm.invoke(s.get('Select'),s)
  event=next(args for n,args in calls if n=='SendSystemEvent' and args[1]=='Server16SubmitBank')
  self.assertEqual(next(iter(bridge.requests_in(event[2].encode(),payload['nonce'])))[1:5],(2,1,1,0))
  self.assertTrue(s.get('scene'+str(settings)).get('switchOn1').get('_visible'))
 def test_failed_switch_confirmation_restores_backend_state_and_message(self):
  payload=view();items=ui.scenes(payload);settings=next(i for i,r in enumerate(items) if r['key']=='settings')
  vm,s,calls=open_finance(payload);vm.invoke(s.get('Go'),s,[settings]);s.set('focus',len(ui.TABS));vm.invoke(s.get('Select'),s)
  vm.invoke(s.get('OnExitScreen'),s);payload['ack']=1;payload['setting_result']=dict(sequence=1,ok=False,message='Configuração recusada.')
  vm,s,calls=open_finance(payload,vm.global_)
  self.assertTrue(s.get('setting0'));self.assertFalse(s.get('waitingSetting'))
  self.assertEqual(text(s.get('scene'+str(settings)),'settingsFeedback'),'Configuração recusada.')
 def test_selecting_each_tab_stops_dispatch_after_the_first_navigation(self):
  for label,target in ui.TABS[1:]:
   vm,s,calls=open_finance(view());s.set('focus',next(i for i,(k,_) in enumerate(ui.TABS) if k==label))
   vm.invoke(s.get('Select'),s)
   expected=next(i for i,row in enumerate(ui.scenes(view())) if row['key']==label)
   self.assertEqual(s.get('page'),expected,label)
 def test_mouse_each_header_and_shoulders_wrap_without_falling_through(self):
  payload=view();items=ui.scenes(payload);vm,s,calls=open_finance(payload)
  for j,(target,_) in enumerate(ui.TABS):
   button=s.get('scene'+str(s.get('page'))).get('action'+str(j))
   vm.invoke(button.get('onRelease'),button)
   self.assertEqual(items[s.get('page')]['key'],target)
   self.assertEqual(s.get('focus'),j)
  for j in range(len(ui.TABS)):
   vm.invoke(s.get('LocalEventHandler'),s,[10,None])
   self.assertEqual(items[s.get('page')]['key'],ui.TABS[j][0])
  vm.invoke(s.get('LocalEventHandler'),s,[9,None])
  self.assertEqual(items[s.get('page')]['key'],'budget')
 def test_contracts_continue_from_receipts_with_shoulders_and_budget_opens_statement(self):
  items=ui.scenes(view());vm,s,calls=open_finance(view())
  vm.invoke(s.get('Go'),s,[next(i for i,r in enumerate(items) if r['key']=='contracts')])
  vm.invoke(s.get('LocalEventHandler'),s,[10,None])
  self.assertEqual(items[s.get('page')]['key'],'expenses')
  vm.invoke(s.get('Go'),s,[next(i for i,r in enumerate(items) if r['key']=='budget')])
  s.set('focus',len(ui.TABS));vm.invoke(s.get('Select'),s)
  self.assertEqual(items[s.get('page')]['key'],'statement')
 def test_back_returns_to_overview_then_original_controller(self):
  vm,s,calls=open_finance(view());vm.invoke(s.get('ChangeTab'),s,[1]);vm.invoke(s.get('Back'),s)
  self.assertEqual(s.get('page'),0);vm.invoke(s.get('Back'),s)
  self.assertIn(('SendEvent',['Calendar','Back','']),calls)
 def test_office_and_navigation_patch_preserves_other_features_and_is_idempotent(self):
  root=ET.fromstring((ui.portable.GAME/package.XML).read_bytes())
  tile=next(t for t in root.find('panel_3').findall('tile') if t.find('tileid').get('NAME')=='REQUEST_FUNDS')
  # Restore the before-feature input even after a local installation. Preserve
  # every other real slide and test creation, rather than installed vs itself.
  for node in list(tile):
   if node.get('DESTINATION')==package.EVENT:tile.remove(node)
  tile.find('number_of_subtiles').set('LENGTH',str(sum(n.tag.startswith('subtile') for n in tile)))
  raw=ET.tostring(root,encoding='utf-8',xml_declaration=True);changed=package.layout(raw)
  before=ET.fromstring(raw);after=ET.fromstring(changed)
  self.assertEqual(len(list(before.iter('tile'))),len(list(after.iter('tile'))))
  old={n.get('DESTINATION') for n in before.iter() if n.get('DESTINATION')}
  new={n.get('DESTINATION') for n in after.iter() if n.get('DESTINATION')}
  self.assertEqual(new-old,{package.EVENT});self.assertEqual(package.layout(changed),changed)
  nav=package.navigation((ui.portable.GAME/package.NAV).read_bytes())
  self.assertEqual(package.navigation(nav),nav)
  self.assertEqual(package.flow()['states'][0]['onEnter'][2],['loadView',['screen',ui.PAGE]])
 def test_waiting_screen_retries_without_sending_money(self):
  data=view();data.update(ready=False,nonce='DISABLED')
  vm,s,calls=open_finance(data)
  self.assertEqual(s.get('onEnterFrame'),s.get('Poll'))
  for _ in range(90):vm.invoke(s.get('Poll'),s)
  self.assertNotIn(('SendSystemEvent',['Calendar','Server16RefreshClubFinance','']),calls)
  self.assertFalse(any(n=='SendSystemEvent' and args[1]=='Server16SubmitBank' for n,args in calls))

if __name__=='__main__':unittest.main()
