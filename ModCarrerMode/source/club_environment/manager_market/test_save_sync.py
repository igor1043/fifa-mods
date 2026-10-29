from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib,json,shutil,sys,tempfile,unittest,zlib
import test_screen
sys.path.insert(0,str(test_screen.SOURCE/'club_browser'))
from test_engine import catalog,context,matches
from engine import Market
from save_sync import bind_pending

class SaveSyncTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'cat.db');self.m=Market(self.root/'market.db',self.root/'cat.db');self.m.open_save('initial','DATA',context());self.events=self.root/'ModCarrerMode/runtime/manager_market/save_events';self.events.mkdir(parents=True);self.save=self.root/'slots/slot1/DATA';self.save.parent.mkdir(parents=True);(self.save.parent/'INDEX').write_bytes(b'index')
  raw=bytearray(160)+b'unique saved career';raw[116:132]=b'SaveType_Career\0';raw[136:140]=(56).to_bytes(4,'little');raw[132:136]=zlib.crc32(raw[160:]).to_bytes(4,'little');self.save.write_bytes(raw);self.digest=hashlib.sha256(raw).hexdigest();self.crc=zlib.crc32(raw[160:]);self.saved_date=20260120;self.saved_club=3
 def tearDown(self):self.m.close();self.tmp.cleanup()
 def event(self,tick=200,name='save',**overrides):
  row=dict(pid=10,process_created_100ns=20,access_tick_ms=tick,operation='write',complete_file=1,save_type='SaveType_Career',path=str(self.save),size_bytes=self.save.stat().st_size,payload_crc32=self.crc,context='1e',epoch=2);row.update(overrides);(self.events/(name+'.tsv')).write_text(''.join(str(k)+'='+str(v)+'\n' for k,v in row.items()))
 def bind(self):
  def rows(name,fields):return [{'currdate':self.saved_date}] if name=='career_calendar' else [{'clubteamid':self.saved_club}]
  fake=SimpleNamespace(tables={'career_calendar':{},'career_users':{}},rows=rows)
  with patch('lineup_data.databases',return_value=[fake]),self.m.db:return bind_pending(self.m,self.root)
 def capture(self,tick=100,**overrides):
  with self.m.db:
   self.m.advance(context(overrides.pop('date',20260120),matches(5)));self.m.capture_session(10,20,30,overrides.pop('epoch',2),tick)
 def test_save_survives_immediate_read_and_process_restart(self):
  self.capture();self.m.leave(self.m.active(club=1),20260120,'dismissal','Teste');self.m.hire(self.m.one('clubs','club_id',1),20260120,'seed')
  with self.m.db:self.m.capture_session(10,20,30,2,150)
  expected=self.m.snapshot();self.event();self.capture(300,date=20260220);self.m.close();self.m=Market(self.root/'market.db',self.root/'cat.db');self.assertEqual(1,len(self.bind()));self.m.open_save(self.digest,self.save,context(20260120));actual=json.loads(zlib.decompress(self.m.snapshot()));want=json.loads(zlib.decompress(expected));actual['info'].update(id=want['info']['id'],kind=want['info']['kind']);self.assertEqual(want,actual)
 def test_repeated_save_with_same_bytes_updates_sql_snapshot(self):
  self.capture();self.event();self.bind();self.m.leave(self.m.active(club=1),20260120,'dismissal','Teste');self.m.hire(self.m.one('clubs','club_id',1),20260120,'seed')
  with self.m.db:self.m.capture_session(10,20,30,2,300)
  coach=self.m.active(club=1)['coach_id'];self.event(400,'repeat');self.assertEqual(1,len(self.bind()));self.m.open_save(self.digest,self.save,context(20260120));self.assertEqual(coach,self.m.active(club=1)['coach_id']);self.assertEqual(1,len(self.m.rows('movements',"kind='dismissal'")))
 def test_loading_older_save_discards_future_without_changing_checkpoint(self):
  self.capture();self.event();self.bind();self.capture(300,date=20260220);self.assertEqual([],self.bind());self.m.open_save(self.digest,self.save,context(20260120));self.assertEqual(20260120,self.m.info()['game_date']);self.assertEqual(5,len(self.m.rows('results')))
 def test_different_pid_epoch_context_crc_or_club_is_not_bound(self):
  self.capture()
  for fields in ({'pid':11},{'epoch':3},{'context':'1f'},{'payload_crc32':0},{'complete_file':0},{'operation':'read'}):
   self.event(**fields);self.assertEqual([],self.bind())
  self.event();self.saved_club=1;self.assertEqual([],self.bind());self.saved_club=3;self.saved_date=20260110;self.assertEqual([],self.bind())
 def test_slot_copy_keeps_same_market_and_does_not_mutate_game_files(self):
  self.capture();self.event();before=self.save.read_bytes();index=(self.save.parent/'INDEX').read_bytes();self.bind();copy=self.root/'slots/slot2/DATA';copy.parent.mkdir();shutil.copy2(self.save,copy);self.m.open_save(self.digest,copy,context(20260120));self.assertEqual(5,len(self.m.rows('results')));self.assertEqual(before,self.save.read_bytes());self.assertEqual(index,(self.save.parent/'INDEX').read_bytes())
 def test_epoch_change_is_captured_even_when_state_is_identical(self):
  self.capture();self.capture(150,epoch=3);self.event(epoch=3);self.assertEqual(1,len(self.bind()))
 def test_receipt_logging_cannot_collide_with_the_event_name_or_rollback_checkpoint(self):
  import worker
  self.capture();self.event();receipts=self.bind()
  with patch.object(worker,'ROOT',self.root/'logs'):
   for receipt in receipts:worker.log('save_checkpoint_bound',receipt_id=receipt['event'],**{k:v for k,v in receipt.items() if k!='event'})
  value=json.loads((self.root/'logs/service.log').read_text(encoding='utf8'));self.assertEqual('save_checkpoint_bound',value['event']);self.assertEqual('save',value['receipt_id']);self.assertEqual(1,self.m.db.execute('SELECT count(*) FROM save_receipts').fetchone()[0]);self.m.open_save(self.digest,self.save,context(20260120));self.assertEqual(5,len(self.m.rows('results')))

if __name__=='__main__':unittest.main()
