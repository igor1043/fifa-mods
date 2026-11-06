import json,tempfile,unittest,zlib
from pathlib import Path
from test_engine import catalog,context,matches
from engine import Market

class SnapshotJournalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);catalog(self.root/'catalog.db');self.market=Market(self.root/'world.db',self.root/'catalog.db');self.market.open_save('initial','DATA',context())
 def tearDown(self):self.market.close();self.tmp.cleanup()
 def capture(self,tick=100):
  revision=self.market.capture_session(10,20,30,2,tick)
  return self.market.db.execute('SELECT state FROM session_states WHERE state_hash=?',(revision,)).fetchone()[0]
 def assert_exact(self,payload):self.assertEqual(self.market.snapshot(),self.market.journal.materialize(payload))

 def test_monthly_chunks_reuse_cold_years_and_materialize_exact_checkpoint(self):
  m=self.market
  with m.db:
   for year in range(2020,2027):
    for month in range(1,13):m.add('reviews',dict(club_id=1,game_date=year*10000+month*100+10,pressure=25,position=2,expected_position=1,reason='Histórico',decision='retained'))
   original=self.capture();self.assert_exact(original)
   self.assertGreater(m.journal.stats['rows_encoded'],80)
   m.add('reviews',dict(club_id=1,game_date=20270110,pressure=5,position=1,expected_position=1,reason='Atual',decision='retained'))
   current=self.capture(200);self.assert_exact(current)
   self.assertEqual(1,m.journal.stats['rows_encoded']);self.assertEqual(1,m.journal.stats['partitions_checked'])
   m.checkpoint('saved','DATA',state=current)
  saved=m.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',('saved',)).fetchone()[0]
  self.assertNotIn('journal',json.loads(zlib.decompress(saved)))
  self.assertEqual(m.snapshot(),saved)
  self.assertNotEqual(m.journal.materialize(original),saved)

 def test_replace_moving_summary_month_invalidates_old_partition(self):
  m=self.market
  def update(date):
   m.db.execute('INSERT OR REPLACE INTO performance_evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(m.branch,20260101,'league',1,date,2,1,0,1,1,0,'native'))
  with m.db:
   update(20260120);previous=self.capture();update(20260220);current=self.capture(200);self.assert_exact(current)
  self.assertEqual(2,m.journal.stats['partitions_checked'])
  state=json.loads(zlib.decompress(m.journal.materialize(current)));self.assertEqual(1,len(state['tables']['performance_evidence']['rows']))
  old=json.loads(zlib.decompress(m.journal.materialize(previous)))['tables']['performance_evidence']
  self.assertEqual(20260120,old['rows'][0][old['columns'].index('game_date')])

 def test_delete_and_late_historical_correction_do_not_corrupt_older_snapshots(self):
  m=self.market
  with m.db:
   m.ingest(matches(3),20260120);before=self.capture()
   m.db.execute('UPDATE results SET hg=7 WHERE branch=?',(m.branch,));after=self.capture(200);self.assert_exact(after)
   m.db.execute('DELETE FROM results WHERE branch=?',(m.branch,));empty=self.capture(300);self.assert_exact(empty)
  self.assertEqual(3,len(json.loads(zlib.decompress(m.journal.materialize(before)))['tables']['results']['rows']))
  self.assertEqual(3,len(json.loads(zlib.decompress(m.journal.materialize(after)))['tables']['results']['rows']))

 def test_transaction_rollback_restores_versions_heads_and_objects_together(self):
  m=self.market
  with m.db:before=self.capture()
  with self.assertRaises(RuntimeError):
   with m.db:
    m.ingest(matches(3),20260120);self.capture(200);raise RuntimeError('rollback')
  with m.db:after=self.capture(300)
  self.assertEqual(before,after);self.assert_exact(after);self.assertEqual(0,m.journal.stats['rows_encoded'])

 def test_discarded_branch_manifest_can_still_bind_its_original_save(self):
  m=self.market
  with m.db:m.ingest(matches(3),20260120);payload=self.capture();full=m.snapshot()
  old=m.branch;m.open_save('other','OTHER',context())
  self.assertIsNone(m.db.execute('SELECT 1 FROM branches WHERE id=?',(old,)).fetchone())
  self.assertEqual(full,m.journal.materialize(payload))
  with m.db:m.checkpoint('saved','DATA',state=payload)
  m.open_save('saved','DATA',context());self.assertEqual(3,len(m.rows('results')))

 def test_missing_object_rejects_binding_without_overwriting_existing_checkpoint(self):
  m=self.market
  with m.db:payload=self.capture();m.checkpoint('saved','DATA',state=payload)
  original=m.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',('saved',)).fetchone()[0]
  digest=next(t['chunks'][0] for t in json.loads(zlib.decompress(payload))['tables'].values() if t['chunks'])
  with m.db:m.db.execute('DELETE FROM state_chunk_objects WHERE hash=?',(digest,))
  with self.assertRaisesRegex(ValueError,'Missing immutable'):
   with m.db:m.checkpoint('saved','DATA',replace=True,state=payload)
  self.assertEqual(original,m.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',('saved',)).fetchone()[0])

 def test_legacy_database_bootstraps_existing_rows_once(self):
  m=self.market
  with m.db:m.ingest(matches(3),20260120)
  self.market.close()
  import sqlite3
  with sqlite3.connect(self.root/'world.db') as db:
   triggers=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'journal_%'")]
   for trigger in triggers:db.execute('DROP TRIGGER '+trigger)
   for table in ['state_chunk_versions','state_chunk_heads','state_chunk_objects','state_chunk_suspended','state_chunk_meta']:db.execute('DROP TABLE '+table)
  db.close()
  self.market=Market(self.root/'world.db',self.root/'catalog.db');self.market.open_save('initial','DATA',context())
  # Restore the same legacy snapshot path, then capture it using the journal.
  with self.market.db:self.market.ingest(matches(3),20260120);payload=self.capture();self.assert_exact(payload)
  self.assertEqual(3,len(self.market.rows('results')))

 def test_working_campaign_cache_survives_commit_but_not_external_write_or_rollback(self):
  from appointment_campaign import capture
  import sqlite3
  m=self.market
  with m.db,m.db.read_batch():capture(m,context());original=m.db.campaign_state
  with m.db,m.db.read_batch():capture(m,context());self.assertIs(original,m.db.campaign_state)
  external=sqlite3.connect(m.path)
  with external:external.execute('UPDATE appointments SET monthly_wage=monthly_wage+1 WHERE branch=?',(m.branch,))
  external.close()
  with m.db,m.db.read_batch():capture(m,context());self.assertIsNot(original,m.db.campaign_state)
  with self.assertRaises(RuntimeError):
   with m.db,m.db.read_batch():
    m.db.cursor().execute('UPDATE appointments SET monthly_wage=monthly_wage+1 WHERE branch=?',(m.branch,));capture(m,context());raise RuntimeError('rollback')
  self.assertIsNone(m.db.campaign_state)
  with m.db,m.db.read_batch():capture(m,context());before=m.db.campaign_state
  with m.db,m.db.read_batch():
   m.db.cursor().execute('UPDATE appointments SET monthly_wage=monthly_wage+1 WHERE branch=?',(m.branch,));capture(m,context());self.assertIsNot(before,m.db.campaign_state)

 def test_rollback_export_keeps_exact_revision_and_complete_state(self):
  m=self.market
  with m.db:
   m.ingest(matches(3),20260120);payload=self.capture();expected=m.journal.materialize(payload)
   row=m.db.execute('SELECT state_hash FROM session_states').fetchone();revision=row[0]
   self.assertEqual(1,m.journal.export_legacy_sessions())
   row=m.db.execute('SELECT state_hash,state FROM session_states').fetchone()
   self.assertEqual(revision,row[0]);self.assertEqual(expected,row[1]);self.assertEqual(0,m.journal.export_legacy_sessions())

 def test_garbage_collection_preserves_journal_for_discarded_branch_and_saved_history(self):
  m=self.market
  with m.db:m.ingest(matches(3),20260120);payload=self.capture();expected=m.journal.materialize(payload);m.checkpoint('saved','DATA',state=payload)
  m.open_save('other','OTHER',context())
  with m.db:
   m.journal.collect();self.assertEqual(expected,m.journal.materialize(payload))
   m.db.execute('DELETE FROM session_states');self.assertGreater(m.journal.collect(limit=128),0)
   state=m.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',('saved',)).fetchone()[0];self.assertEqual(expected,state)
  m.open_save('saved','DATA',context());self.assertEqual(3,len(m.rows('results')))

if __name__=='__main__':unittest.main()
