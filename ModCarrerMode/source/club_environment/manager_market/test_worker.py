from pathlib import Path
import json,shutil,tempfile,unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_screen  # Establish the same shipped runtime paths as the APT tests.
from test_engine import catalog,context,matches
import worker
from engine import Market

class WorkerRecoveryTest(unittest.TestCase):
 def test_ui_failure_does_not_replay_already_processed_load(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);root=game/'runtime';cat=game/'ModCarrerMode/data/manager_market/catalog.sqlite3';cat.parent.mkdir(parents=True);catalog(cat);snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True);save=game/'saves/slot/DATA';save.parent.mkdir(parents=True);save.write_bytes(b'unchanged');snapshot.write_text(json.dumps(dict(fixtures=[],standings=[])))
   current=dict(context(),digest='A');observed=dict(save=dict(path=str(save),pid=10,process_created_100ns=20),profile=dict(context_address=1,club_id=3,registry_address=123,context_epoch=2),signature=('A',20260101));io=dict(operation='read',access_tick_ms='1');calls=[]
   def build(g,p,m):
    calls.append(1)
    if len(calls)==1:raise ValueError('UI preparation failed')
    p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'APT')
   with patch.multiple(worker,GAME=game,ROOT=root,DEST=game/'screen.big'),patch.object(worker,'Inputs') as inputs,patch.object(worker,'io_event',return_value=io),patch.object(worker,'observe',return_value=observed),patch.object(worker,'build',side_effect=build),patch.object(worker,'log'):
    inputs.return_value.read.return_value=current;service=worker.Service()
    try:
     with self.assertRaisesRegex(ValueError,'UI preparation'):service.update(observed,None)
     publication=json.loads((root/'state_ready.json').read_text());self.assertEqual(service.market.branch,publication['branch']);self.assertEqual('A',publication['digest']);self.assertEqual(['read','1',str(save)],publication['io'])
     branch=service.market.branch;service.update(observed,None);self.assertEqual(branch,service.market.branch);self.assertEqual(1,service.market.db.execute('SELECT count(*) FROM branches').fetchone()[0])
    finally:
     if service.market:service.market.close()
 def test_hot_update_handoff_keeps_unsaved_progress_but_rejects_a_new_load(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);catalog(root/'cat.sqlite3');market=Market(root/'world.sqlite3',root/'cat.sqlite3');market.open_save('A','DATA',context());market.advance(context(20260120,matches(5)))
   observed=dict(save=dict(pid=10,process_created_100ns=20,path=str(root/'DATA')),profile=dict(context_address=30));current=dict(context(20260120),digest='A');token=('read','77',str(root/'DATA'));handoff=dict(schema=1,pid=10,created=20,save=str(root/'DATA'),digest='A',club=3,context=30,io=list(token),branch=market.branch,date=20260120);service=object.__new__(worker.Service);service.market=market;branch=market.branch;market.branch=None
   with patch.object(worker,'ROOT',root),patch.object(worker,'log'):
    (root/'handoff.json').write_text(json.dumps(handoff));self.assertTrue(service.resume_handoff(observed,current,token));self.assertEqual(branch,market.branch);self.assertEqual(5,len(market.rows('results')))
    market.branch=None;(root/'handoff.json').write_text(json.dumps(handoff));self.assertFalse(service.resume_handoff(observed,current,('read','78',str(root/'DATA'))));self.assertIsNone(market.branch)
   market.close()
 def test_ui_revision_invalidates_cached_package_with_identical_career_data(self):
  self.assertNotEqual(worker.package_key({'date':20260511},'old'),worker.package_key({'date':20260511},'new'))
  self.assertEqual(worker.package_key({'a':1,'b':2},'ui'),worker.package_key({'b':2,'a':1},'ui'))
 def test_attachment_uses_zero_argument_api_and_read_only_exact_pid(self):
  calls=[]
  class Memory:
   def __init__(self):self.kernel32=SimpleNamespace(OpenProcess=lambda *args:(calls.append(args),123)[1]);self.closed=False
   def _get_base_address(self,exe):self.exe=exe;return 0x140000000
   def read_process_memory(self,address,size):self.read=(address,size);return b'MZ'
   def close(self):self.closed=True
  with patch.object(worker,'Memory',Memory):
   m=worker.attach(SimpleNamespace(pid=77,exe=lambda:'FIFA16.exe'))
  self.assertEqual([(0x410,False,77)],calls);self.assertEqual(77,m.process_id);self.assertEqual((0x140000000,2),m.read);self.assertFalse(m.closed)
 def test_attachment_closes_handle_when_module_not_ready(self):
  class Memory:
   def __init__(self):self.kernel32=SimpleNamespace(OpenProcess=lambda *args:123);self.closed=False
   def _get_base_address(self,exe):return 0
   def close(self):self.closed=True
  m=Memory()
  with patch.object(worker,'Memory',return_value=m):
   with self.assertRaisesRegex(OSError,'carregar'):worker.attach(SimpleNamespace(pid=77,exe=lambda:'FIFA16.exe'))
  self.assertTrue(m.closed)
 def test_access_wait_does_not_escape_as_frozen_startup_exception(self):
  with patch.object(worker.portable,'session_process',return_value=SimpleNamespace(create_time=lambda:0)),patch.object(worker,'attach',side_effect=OSError('Aguardando FIFA')),patch.object(worker,'log') as log:
   worker.main()
  self.assertEqual('waiting',log.call_args.args[0])
 def test_native_save_checkpoint_restores_after_unsaved_future(self):
  with tempfile.TemporaryDirectory() as tmp:
   game=Path(tmp);root=game/'runtime';cat=game/'ModCarrerMode/data/manager_market/catalog.sqlite3';cat.parent.mkdir(parents=True);catalog(cat);snapshot=game/'ModCarrerMode/runtime/career_fce_snapshot.json';snapshot.parent.mkdir(parents=True);save=game/'saves/slot/DATA';save.parent.mkdir(parents=True);save.write_bytes(b'unchanged')
   io=dict(operation='read',access_tick_ms='1');current=dict(context(),digest='A',saved_date=20260101)
   def build(g,p,m):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'APT')
   observed=dict(save=dict(path=str(save),pid=10,process_created_100ns=20),profile=dict(context_address=1,club_id=3,registry_address=123,context_epoch=2),signature=('A',20260101))
   with patch.multiple(worker,GAME=game,ROOT=root,DEST=game/'screen.big'),patch.object(worker,'Inputs') as inputs,patch.object(worker,'io_event',side_effect=lambda s:io),patch.object(worker,'observe',side_effect=lambda m:observed),patch.object(worker,'build',side_effect=build),patch.object(worker,'log'):
    inputs.return_value.read.side_effect=lambda *a,**k:dict(current)
    service=worker.Service()
    def publish():snapshot.write_text(json.dumps(dict(fixtures=current['fixtures'],standings=[])));service.update(observed,None)
    publish();current.update(date=20260120,fixtures=matches(5));observed['signature']=('A',20260120);publish();self.assertEqual(5,len(service.market.rows('results')))
    io.update(operation='write',access_tick_ms='2');current.update(digest='B',saved_date=20260120);observed['signature']=('B',20260120);publish()
    current.update(date=20260220,fixtures=matches(15));observed['signature']=('B',20260220);publish();self.assertGreater(len(service.market.rows('results')),5)
    io.update(operation='read',access_tick_ms='3');current.update(date=20260120,fixtures=matches(5));observed['signature']=('B',20260120);publish();self.assertEqual(5,len(service.market.rows('results')));self.assertEqual(b'unchanged',save.read_bytes());service.market.close()

if __name__=='__main__':unittest.main()
