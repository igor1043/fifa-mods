import json,tempfile,unittest
from pathlib import Path
from loans import BANKS,OFFERED_BANKS,AMOUNTS,empty,borrow,advance,presentation,quote
from loan_notifications import schedule_reminders,dispatch,payment_notice
from test_finance_live_ui import open_screen,text
from club_identity import club_name
from runtime import requests_in

class StatementTests(unittest.TestCase):
 def setUp(self):
  self.state,self.budget,_=borrow(empty(1629,20260102),request_id='loan',club=1629,today=20260102,budget=16_000_000,bank=0,amount=1_000_000,months=24)

 def test_pad_scrolls_all_rows_then_reaches_explicit_payment_without_issuing_a_request(self):
  state,budget,_=advance(self.state,club=1629,today=20260202,budget=self.budget)
  view=presentation(state,20260202,budget,ready=True,nonce='SCROLL',club_name='GrÃªmio')
  vm,screen,_=open_screen(view);screen.set('page',3);screen.set('focus',0);vm.invoke(screen.get('Refresh'),screen)
  self.assertIn('EMPR',text(screen,'title'));self.assertEqual(text(screen,'subtitle'),'1/4 empréstimos em 2026')
  self.assertEqual(screen.get('cell1_3').get('textColor'),0x26744a)
  for _ in range(23):vm.invoke(screen.get('MoveFocus'),screen,[1])
  self.assertEqual(screen.get('focus'),23);self.assertEqual(screen.get('statementOffset'),18)
  self.assertEqual(screen.get('cell6_0').get('text'),'24 / 24')
  vm.invoke(screen.get('Select'),screen);self.assertEqual(screen.get('page'),3)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))
  vm.invoke(screen.get('MoveFocus'),screen,[1]);vm.invoke(screen.get('Select'),screen)
  self.assertEqual(screen.get('page'),4);self.assertEqual(screen.get('action'),1)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

 def test_new_bank_ids_and_rates_leave_legacy_contract_unchanged(self):
  self.assertEqual([b['rate_bps'] for b in BANKS[:3]],[80,100,120])
  self.assertEqual(len(OFFERED_BANKS),10)
  for bank in OFFERED_BANKS:
   q=quote(bank,1_000_000,12);self.assertEqual(sum(p['principal'] for p in q['payments']),1_000_000)
   command=f'S16BANK_V3|TEST|1|0|{bank}|0|1|20260102|END_S16BANK'
   self.assertEqual(next(iter(requests_in(command.encode(),'TEST')))[2],bank)
  self.assertFalse(requests_in(b'S16BANK_V3|TEST|1|0|99|0|1|20260102|END_S16BANK','TEST'))

 def test_all_bank_images_are_embedded_and_master_is_visible_in_the_selected_card(self):
  from PIL import Image
  from formats import BigFile,AptFile,Placement
  import io,bank_ui_r60 as ui
  view=presentation(empty(1629,20260102),20260102,16_000_000,ready=True,nonce='ART')
  vm,screen,_=open_screen(view);screen.set('page',1);screen.set('bankIndex',9);screen.set('focus',9);screen.set('bank',8);vm.invoke(screen.get('Refresh'),screen)
  self.assertTrue(screen.get('bankLogo8').get('_visible'))
  self.assertTrue(screen.get('bankHeaderLogo8').get('_visible'))
  self.assertIn('Banco Master',text(screen,'bankHeading'))
  package=BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big')
  textures=[]
  for entry in package.entries.values():
   if entry.data.startswith(b'DDS '):
    image=Image.open(io.BytesIO(entry.data))
    if image.size==(128,64):textures.append(image.convert('RGBA').tobytes())
  self.assertEqual(len(textures),len(BANKS))
  self.assertEqual(len(set(textures[3:])),len(OFFERED_BANKS))

 def test_reminder_is_one_day_before_and_never_sent_after_due_or_payment(self):
  with tempfile.TemporaryDirectory() as d:
   folder=Path(d);out=folder/'out';out.mkdir();schedule_reminders(folder,self.state);schedule_reminders(folder,self.state)
   rows=json.loads((folder/'notifications.json').read_text());self.assertEqual(len(rows),24)
   self.assertEqual(rows[0]['due'],20260201)
   live=dict(club=1629,date=20260201,budget=self.budget,context_epoch=7)
   dispatch(folder,out,live,pid=12,context=0x1000,state=self.state);self.assertTrue((out/'native_mail_request.tsv').exists())
   live['date']=20260202;dispatch(folder,out,live,pid=12,context=0x1000,state=self.state)
   self.assertFalse((out/'native_mail_request.tsv').exists())
   state,budget,events=advance(self.state,club=1629,today=20260202,budget=self.budget)
   payment_notice(folder,state,live,budget,events);payment_notice(folder,state,live,budget,events)
   rows=json.loads((folder/'notifications.json').read_text());self.assertEqual(sum(r.get('kind')=='payment' for r in rows),1)
   self.assertIn(format(budget,',').replace(',','.'),rows[-1]['body'])

 def test_resolve_saved_club_name_from_local_room_context_without_exposing_id(self):
  with tempfile.TemporaryDirectory() as d:
   game=Path(d);p=game/'ModCarrerMode/runtime/club_environment/room/runtime/room_header.json';p.parent.mkdir(parents=True)
   p.write_text(json.dumps(dict(club=1629,name='GrÃªmio')))
   self.assertEqual(club_name(game,1629),'GrÃªmio');self.assertEqual(club_name(game,1043),'Clube')


 def test_mouse_can_reach_master_and_choose_a_bank_without_viewport_jumping_or_requesting_credit(self):
  view=presentation(empty(1629,20260102),20260102,16_000_000,ready=True,nonce='BANK_POINTER')
  vm,screen,_=open_screen(view);screen.set('page',1);screen.set('focus',0);vm.invoke(screen.get('Refresh'),screen)
  next_button=screen.get('bankNext')
  vm.invoke(next_button.get('onRelease'),next_button);vm.invoke(next_button.get('onRelease'),next_button)
  self.assertEqual(screen.get('bank'),8);self.assertEqual(screen.get('bankOffset'),4)
  row=screen.get('bankTile2');expected=row.get('index')
  vm.invoke(row.get('onRollOver'),row);self.assertEqual(row.get('index'),expected)
  vm.invoke(row.get('onRelease'),row)
  self.assertEqual(screen.get('focus'),10);self.assertEqual(screen.get('bank'),4)
  self.assertIsNone(vm.global_.get('Server16BankRequestV2'))

 def test_pad_traverses_every_bank_then_value_term_and_review_with_no_implicit_application(self):
  from bank_design import ORDER,N
  view=presentation(empty(1629,20260102),20260102,16_000_000,ready=True,nonce='BANK_PAD')
  vm,screen,_=open_screen(view);screen.set('page',1);screen.set('focus',0);vm.invoke(screen.get('Refresh'),screen)
  for index in range(N):
   vm.steps=0 # Each hardware input is a separate bounded native event.
   self.assertEqual(screen.get('bank'),ORDER[index]);self.assertIn(BANKS[ORDER[index]]['name'],text(screen,'bankHeading'))
   vm.invoke(screen.get('MoveFocus'),screen,[1])
  self.assertEqual(screen.get('focus'),N)
  vm.invoke(screen.get('Shift'),screen,[1]);self.assertEqual(AMOUNTS[screen.get('amountIndex')],2_000_000)
  vm.invoke(screen.get('MoveFocus'),screen,[1]);vm.invoke(screen.get('Shift'),screen,[1]);self.assertEqual(screen.get('termIndex'),2)
  vm.invoke(screen.get('MoveFocus'),screen,[1]);vm.invoke(screen.get('Select'),screen)
  self.assertEqual(screen.get('page'),2);self.assertIsNone(vm.global_.get('Server16BankRequestV2'))


 def test_help_uses_original_fifa_help_manager_and_native_numeric_columns_are_right_aligned(self):
  from formats import BigFile,AptFile,Placement
  import bank_ui_r60 as ui
  view=presentation(empty(1629,20260102),20260102,2_000_000_000,ready=True,nonce='FOOTER')
  vm,screen,calls=open_screen(view);screen.set('page',1);screen.set('focus',0);screen.set('amountIndex',3);screen.set('termIndex',2);vm.invoke(screen.get('Refresh'),screen)
  self.assertEqual(text(screen,'status'),'')
  help_items=vm.invoke(screen.get('getHelpContext'),screen)
  self.assertEqual(help_items,[('ADVANCE','Selecionar'),('BACK','Voltar')])
  apt=AptFile(BigFile(ui.b.HERE/'package/data/ui/game/screens/career/server16/bankloans.big'))
  fields={p.name:apt.characters[p.character] for p in apt.characters[9].frames[0] if isinstance(p,Placement) and p.name and p.character in apt.characters}
  for i in range(10):self.assertEqual(fields['summaryValue'+str(i)].alignment,1)
  self.assertEqual(text(screen,'summaryValue2'),'2.010.000.000')
