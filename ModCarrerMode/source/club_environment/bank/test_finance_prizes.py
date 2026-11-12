from copy import deepcopy
from pathlib import Path
import hashlib,json,struct,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
from finance_prizes import NativePrizes,receipt,merge,entries,project
from finance_report import categories,native_view
from finance_prize_ui import groups


class MemoryFixture:
 def __init__(self):
  self.process_id=42;self.base_module=0x140000000;self.blocks={}
  self.session=dict(club_id=1043,career_role=1,registry_address=0x5000,context_address=0xb000,context_epoch=7)
  code=bytearray(24);code[7:9]=b'\xc7\x01';struct.pack_into('<I',code,9,37);self.put(self.base_module+0x44565f0,code)
  self.put(0x5000+37*32+24,struct.pack('<Q',0x8000));self.put(0x8000,struct.pack('<Q',0x9000))
  self.manager=bytearray(0x170);struct.pack_into('<Q',self.manager,8,0x5000)
 def put(self,address,data):self.blocks[address]=bytes(data)
 def read_process_memory(self,address,size):
  for start,blob in self.blocks.items():
   if start<=address and address+size<=start+len(blob):return blob[address-start:address-start+size]
  raise RuntimeError('Read outside fixture')
 def add(self,index,day=20261218,amount=2016359,competition=99):
  raw=0x30000+index*0x2000;header=bytearray(0xa8);struct.pack_into('<I',header,8,1043)
  from finance_prizes import SUBJECT,BODY,VARIANTS
  self.put(raw+0x200,SUBJECT.encode()+b'\0');self.put(raw+0x300,BODY.encode()+b'\0')
  struct.pack_into('<Q',header,0x48,raw+0x200);struct.pack_into('<Q',header,0x58,raw+0x300)
  struct.pack_into('<Q',header,0x68,raw+0x400);struct.pack_into('<I',header,0x70,3);struct.pack_into('<I',header,0x90,day)
  previous=raw+0x60
  for i,(kind,value) in enumerate(zip(VARIANTS,(1043,amount,competition))):
   node=raw+0x400+i*0x40;next_=node+0x40 if i<2 else raw+0x60;payload=raw+0x800+i*0x40
   self.put(node,struct.pack('<QQQ',previous,next_,payload));self.put(payload,struct.pack('<QI',self.base_module+kind,value));previous=node
  self.put(raw,header);return raw
 def inbox(self,active,read=()):
  for offset,values,at in ((0x50,active,0xa000),(0x90,read,0xa800)):
   struct.pack_into('<QQ',self.manager,offset,at,at+len(values)*8);self.put(at,struct.pack('<'+'Q'*len(values),*values))
  self.put(0x9000,self.manager)
 def capture(self):
  with patch('server16_py.career_context.competition_session',return_value=self.session):
   return NativePrizes(self)._read(42,1043,20261230,7,0xb000)


class PrizeReceipts(unittest.TestCase):
 def test_native_values_include_both_inbox_vectors_and_deduplicate_the_same_object(self):
  m=MemoryFixture();a=m.add(0);b=m.add(1,20261108,6497420,1620);m.inbox([a],[a,b])
  r=m.capture();self.assertTrue(r['available']);self.assertEqual(sum(v['amount'] for v in r['entries']),8513779)
  self.assertEqual(len(r['entries']),2)
 def test_different_identical_native_payments_are_preserved_and_addresses_do_not_define_identity(self):
  m=MemoryFixture();a=m.add(0);b=m.add(1);m.inbox([a,b]);first=m.capture()['entries']
  self.assertEqual(len(first),2);self.assertNotEqual(first[0]['id'],first[1]['id'])
  m2=MemoryFixture();c=m2.add(5);d=m2.add(6);m2.inbox([d,c]);self.assertEqual(first,m2.capture()['entries'])
 def test_zero_prize_notice_does_not_block_other_real_receipts(self):
  m=MemoryFixture();a=m.add(0);b=m.add(1,amount=0);m.inbox([a,b])
  rows=m.capture()['entries'];self.assertEqual(len(rows),1);self.assertEqual(rows[0]['amount'],2016359)
 def test_foreign_career_and_changed_native_argument_type_are_rejected(self):
  m=MemoryFixture();a=m.add(0);m.inbox([a]);m.session['club_id']=567
  with self.assertRaises(ValueError):m.capture()
  m.session['club_id']=1043;m.put(a+0x840,struct.pack('<QI',m.base_module+0xdead,123))
  with self.assertRaises(ValueError):m.capture()
 def test_receipts_are_monthly_native_income_and_not_a_second_cash_posting(self):
  rows=[receipt(1043,20261218,2016359,99),receipt(1043,20261108,6497420,1620)]
  native=native_view(None,club=1043,season=20260109,today=20261230,prizes=dict(available=True,entries=rows))
  view=dict(club=1043,date=20261230,native_finance=native,months=[],transfers=[]);before=deepcopy(view)
  self.assertEqual(next(r for r in categories(view)['revenues'] if r['key']=='prize')['value'],8513779)
  r=next(r for r in categories(view,202612)['revenues'] if r['key']=='prize');self.assertEqual(r['value'],2016359);self.assertEqual(r['target'],'prizes:month:202612')
  self.assertEqual(view,before)
 def test_inbox_deletion_and_temporary_unavailability_cannot_erase_the_saved_history(self):
  row=receipt(1043,20261218,2016359,99);old=merge({},dict(entries=[row]),club=1043,year=2026)
  for incoming in ({},{'prizes':None},{'entries':[]}):
   new=merge(old,incoming,club=1043,year=2026);self.assertEqual(new['prizes'],2016359);self.assertEqual(len(new['entries']),1)
  self.assertEqual(merge(old,dict(entries=[row]),club=1043,year=2026)['prizes'],2016359)
 def test_groups_show_competition_totals_without_combining_another_club(self):
  a=dict(receipt(1043,20261108,100,1620),name='Copa do Brasil',asset=229)
  b=dict(receipt(1043,20261206,200,1620),name='Copa do Brasil',asset=229)
  c=dict(receipt(1043,20261218,50,99),name='Intercontinental',asset=73)
  native=dict(entries=[a,b,c,receipt(567,20261218,999,99)])
  grouped=groups(entries(native,1043,2026));self.assertEqual([(g['name'],g['amount']) for g in grouped],[('Copa do Brasil',300),('Intercontinental',50)])
 def test_year_rollover_keeps_previous_receipts_and_budget_identical(self):
  import club_finance as f
  from loans import empty
  from test_club_finance import context
  row=receipt(1043,20260511,123456,7);ctx=context();ctx['native_finance']=dict(entries=[row],prizes=123456)
  initial=empty(1043,ctx['date']);s,b,events=f.apply(initial,club=1043,today=ctx['date'],budget=10_000_000,context=ctx)
  self.assertFalse(events);self.assertEqual(b,10_000_000);self.assertEqual(s['finance']['entries'],[])
  old=deepcopy(s['finance']['years']['2026']);nextctx=dict(context(20270101),native_finance={})
  s,_,_=f.apply(s,club=1043,today=20270101,budget=b,context=nextctx)
  self.assertEqual(s['finance']['years']['2026'],old)
  self.assertEqual(project(s['finance'],{},club=1043,today=20261230)['prizes'],123456)
 def test_native_save_checkpoint_restores_only_that_save_without_modifying_DATA(self):
  import save_sidecar as sql
  from loans import empty
  with tempfile.TemporaryDirectory() as temp:
   save=Path(temp)/'DATA';save.write_bytes(b'native-save-fixture');digest=hashlib.sha256(save.read_bytes()).hexdigest()
   row=receipt(1043,20261218,2016359,99)
   # Use the actual versioned state layout and snapshot writer.
   from test_club_finance import context
   import club_finance as f
   state,_,_=f.apply(empty(1043,20261230),club=1043,today=20261230,budget=10_000_000,context=dict(context(20261230),native_finance=dict(entries=[row],prizes=row['amount'])))
   sql.save_snapshot(save,dict(hash=digest,club=1043,date=20261230,budget=10_000_000),state,[],dict(operation='write',complete_file='1',access_tick_ms=1))
   restored=sql.load_snapshot(save,digest,1043)['state'];self.assertEqual(restored['finance']['years']['2026']['native_finance']['prizes'],2016359)
   self.assertIsNone(sql.load_snapshot(save,'f'*64,1043));self.assertEqual(save.read_bytes(),b'native-save-fixture')
 def test_native_screen_has_competition_groups_drilldown_and_current_currency(self):
  import finance_ui as ui
  from test_club_finance_ui import view,open_finance
  v=view();v['date']=20261230
  rows=[dict(receipt(1043,20261108,6497420,1620),name='Copa do Brasil',asset=229),
   dict(receipt(1043,20261218,2016359,99),name='Intercontinental',asset=73)]
  v['native_finance']=dict(entries=rows,prizes=8513779)
  items=ui.scenes(v);keys={row['key']:i for i,row in enumerate(items)}
  for key in ('prizes','prizes:competition:1620','prizes:competition:99','prizes:month:202612','prizes:month:202612:competition:99'):self.assertIn(key,keys)
  vm,screen,calls=open_finance(v)
  from career_currency import format_money
  for key in ('prizes','prizes:competition:99','prizes:month:202612:competition:99'):
   vm.invoke(screen.get('Go'),screen,[keys[key]]);self.assertEqual(screen.get('page'),keys[key])
   for node in items[keys[key]]['nodes']:
    if 'amount' in node:
     actual=screen.get('scene'+str(keys[key])).get(node['name']).get('text').encode('latin1').decode('utf8')
     self.assertEqual(actual,format_money(node['amount'],v['currency'],labels=v['currency_labels']))
  self.assertFalse(any(name=='LocalizeCurrencyWithType' for name,args in calls))
  self.assertFalse(any(name=='SendSystemEvent' and 'finance' in str(args).lower() for name,args in calls))

if __name__=='__main__':unittest.main()
