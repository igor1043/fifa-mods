import hashlib,json,sqlite3,tempfile,unittest,zlib
from pathlib import Path
from engine import Market
from test_engine import catalog,context,matches
from save_database import NAME,database_path,import_checkpoint,import_live,normal,store_receipt

class PerSaveTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.cat=self.root/'cat.db';catalog(self.cat)
  self.a=self.root/'slots/A/DATA';self.b=self.root/'slots/B/DATA'
  for save in (self.a,self.b):save.parent.mkdir(parents=True);save.write_bytes(b'native save');(save.parent/'INDEX').write_bytes(b'native index')
  self.source=Market(self.root/'slots'/NAME,self.cat);self.source.open_save('initial',self.a,context())
 def tearDown(self):self.source.close();self.tmp.cleanup()
 def test_import_exact_digest_and_fork_independent_worlds(self):
  with self.source.db:self.source.advance(context(20260120,matches(5)));self.source.checkpoint('saved',self.a)
  before=self.source.path.read_bytes();native=self.a.read_bytes();targets=[]
  try:
   for save in (self.a,self.b):
    m=Market(database_path(save),self.cat);targets.append(m)
    with m.db:
     self.assertFalse(import_checkpoint(m,save,'foreign'));self.assertTrue(import_checkpoint(m,save,'saved'));m.open_save('saved',save,context(20260120))
    self.assertEqual(5,len(m.rows('results')))
   a,b=targets
   with a.db:a.leave(a.active(club=1),20260120,'dismissal','Independent A')
   self.assertIsNotNone(b.active(club=1));self.assertEqual([],b.rows('movements',"reason='Independent A'"))
   self.assertEqual(before,self.source.path.read_bytes());self.assertEqual(native,self.a.read_bytes())
  finally:
   for m in targets:m.close()
 def test_save_as_has_own_snapshot_before_slot_is_opened(self):
  m=Market(database_path(self.a),self.cat)
  try:
   with m.db:
    m.open_save('a',self.a,context());m.advance(context(20260120,matches(5)));revision=m.capture_session(10,20,30,2,100)
    payload=m.db.execute('SELECT state FROM session_states WHERE state_hash=?',(revision,)).fetchone()[0]
    store_receipt(m,self.b,'b',payload,('write-b','b',m.branch,20260120,10,20,200,'native_write_v2'))
   target=Market(database_path(self.b),self.cat)
   try:
    target.open_save('b',self.b,context(20260120));self.assertEqual(5,len(target.rows('results')))
    self.assertEqual(1,target.db.execute('SELECT count(*) FROM save_receipts').fetchone()[0])
    self.assertIsNone(m.db.execute('SELECT 1 FROM save_checkpoints WHERE save_hash=?',('b',)).fetchone())
   finally:target.close()
  finally:m.close()
 def test_live_handoff_preserves_all_facts_and_native_revision(self):
  m=self.source
  with m.db:
   m.advance(context(20260120,matches(5)));revision=m.capture_session(10,20,30,2,100);m.checkpoint('saved',self.a)
  before=m.snapshot();target=Market(database_path(self.a),self.cat)
  try:
   with target.db:import_live(target,m.path,m.branch,self.a)
   self.assertEqual(before,target.snapshot());row=target.db.execute('SELECT state FROM session_states WHERE state_hash=?',(revision,)).fetchone();self.assertEqual(before,target.journal.materialize(row[0]));self.assertEqual('ok',target.db.execute('PRAGMA integrity_check').fetchone()[0])
  finally:target.close()
 def test_rolling_journal_is_bounded_across_game_restarts(self):
  m=self.source
  with m.db:
   for process in range(3):
    for tick in range(60):m.capture_session(process+1,process+100,30,2,tick)
   # Identical states are intentionally deduplicated within a process.
   for tick in range(150):
    m.db.execute('UPDATE branches SET user_club=? WHERE id=?',(tick,m.branch));m.capture_session(99,999,30,2,tick)
  self.assertEqual(128,m.db.execute('SELECT count(*) FROM session_states').fetchone()[0]);self.assertEqual(128,m.db.execute('SELECT count(*) FROM session_observations').fetchone()[0]);self.assertEqual(2,m.db.execute('PRAGMA auto_vacuum').fetchone()[0])
 def test_extended_windows_path_has_same_slot(self):
  self.assertEqual(database_path(self.a),database_path('\\\\?\\'+str(self.a)))

 def test_migration_uses_column_names_from_upgraded_legacy_schema(self):
  m=self.source;columns=[r[1] for r in m.db.execute('PRAGMA table_info(coaches)') if r[1]!='birthplace']+['birthplace']
  with m.db:
   m.db.execute('CREATE TABLE coach_legacy AS SELECT '+','.join(columns)+' FROM coaches')
   m.db.execute('DROP TABLE coaches');m.db.execute('ALTER TABLE coach_legacy RENAME TO coaches')
  target=Market(database_path(self.a),self.cat)
  try:
   with target.db:import_live(target,m.path,m.branch,self.a)
   for person in m.rows('coaches'):self.assertEqual(person,target.one('coaches','coach_id',person['coach_id']))
  finally:target.close()

 def test_deleted_slot_cleanup_keeps_partial_native_saves_and_is_recoverable(self):
  from save_database import quarantine_deleted
  slot=self.root/'cleanup/12345678';slot.mkdir(parents=True);m=Market(slot/NAME,self.cat);m.close()
  (slot/'INDEX').write_bytes(b'partial');self.assertEqual([],quarantine_deleted(slot.parent));self.assertTrue((slot/NAME).exists())
  (slot/'INDEX').unlink();moved=quarantine_deleted(slot.parent)
  self.assertEqual(1,len(moved));self.assertTrue((Path(moved[0])/NAME).exists());self.assertFalse((slot/NAME).exists())

 def test_repeated_overwrites_bound_old_copies_without_losing_world_history(self):
  m=Market(database_path(self.a),self.cat)
  try:
   with m.db:
    m.open_save('first',self.a,context());m.advance(context(20260120,matches(5)))
    for n in range(20):m.checkpoint('save-'+str(n),self.a)
   self.assertEqual(8,m.db.execute('SELECT count(*) FROM save_checkpoints').fetchone()[0])
   m.open_save('save-19',self.a,context(20260120));self.assertEqual(5,len(m.rows('results')))
  finally:m.close()

 def test_saved_monthly_awards_follow_the_slot_and_survive_new_load_branch(self):
  from contextlib import closing
  with self.source.db:self.source.checkpoint('saved',self.a)
  payload=zlib.compress(b'[{"date":20260101,"rows":[],"games":[]}]')
  with closing(sqlite3.connect(self.source.path.with_name('competition_monthly.sqlite3'))) as db,db:
   db.executescript('CREATE TABLE observations_v2(branch TEXT,day INT,signature TEXT,payload BLOB,PRIMARY KEY(branch,day,signature));CREATE TABLE checkpoints(save_hash TEXT PRIMARY KEY,payload BLOB);')
   db.execute('INSERT INTO checkpoints VALUES(?,?)',('saved',payload))
  target=Market(database_path(self.a),self.cat)
  try:
   with target.db:import_live(target,self.source.path,self.source.branch,self.a)
   with closing(sqlite3.connect(target.path.with_name('competition_monthly.sqlite3'))) as db:self.assertEqual(payload,db.execute('SELECT payload FROM checkpoints WHERE save_hash=?',('saved',)).fetchone()[0])
  finally:target.close()

