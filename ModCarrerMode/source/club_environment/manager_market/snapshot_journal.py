"""Immutable monthly chunks for the rolling journal; save files stay unchanged.

Completed save checkpoints are still self-contained legacy snapshots. Only the
temporary session journal uses references, materialized before a save binds.
Dirty partitions are tracked by SQL triggers in the same transaction as facts.
"""
import hashlib,json,zlib

DATED={'results','reviews','movements','honours','trophy_history','cup_exits','salary_events','reputation_events','performance_evidence','appointment_campaigns','approaches'}

def partition(table,alias=''):
 prefix=alias+'.' if alias else ''
 if table in DATED:return f'CAST({prefix}game_date / 100 AS INTEGER)'
 if table=='annual_campaigns':return prefix+'year'
 if table=='appointment_baselines':return f'CAST({prefix}season / 10000 AS INTEGER)'
 if table=='appointments':return f'CASE WHEN {prefix}end_date IS NULL THEN 0 ELSE CAST({prefix}end_date / 100 AS INTEGER) END'
 if table=='progress':return f'CAST({prefix}last_review / 100 AS INTEGER)'
 return '0'

def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).encode('utf8')

class Journal:
 def __init__(self,db,tables):
  self.db=db;self.tables=tables;self.layouts={};self.stats={}
  # REPLACE must invalidate the deleted row's old month as well as the new
  # one. Otherwise a summary moving months could appear in both snapshots.
  db.execute('PRAGMA recursive_triggers=ON')
  db.executescript('''
CREATE TABLE IF NOT EXISTS state_chunk_meta(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS state_chunk_versions(branch TEXT,table_name TEXT,part INT,version INT,PRIMARY KEY(branch,table_name,part));
CREATE TABLE IF NOT EXISTS state_chunk_heads(branch TEXT,table_name TEXT,part INT,version INT,object_hash TEXT,row_count INT,PRIMARY KEY(branch,table_name,part));
CREATE TABLE IF NOT EXISTS state_chunk_objects(hash TEXT PRIMARY KEY,payload BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS state_chunk_suspended(branch TEXT PRIMARY KEY);
''')
  with db:
   for table in tables:
    schema=list(db.execute('PRAGMA table_info('+table+')'))
    columns=[r[1] for r in schema if r[1]!='branch'];order=[r[1] for r in sorted(schema,key=lambda r:r[5]) if r[5] and r[1]!='branch']
    self.layouts[table]=(columns,order)
    expression=partition(table)
    if expression!='0':db.execute(f'CREATE INDEX IF NOT EXISTS journal_part_{table} ON {table}(branch,({expression}))')
    def touch(alias):
     return f"INSERT INTO state_chunk_versions VALUES({alias}.branch,'{table}',{partition(table,alias)},1) ON CONFLICT(branch,table_name,part) DO UPDATE SET version=version+1;"
    for event,aliases in [('INSERT',('NEW',)),('UPDATE',('OLD','NEW')),('DELETE',('OLD',))]:
     owner='OLD' if event=='DELETE' else 'NEW'
     db.execute(f"CREATE TRIGGER IF NOT EXISTS journal_{table}_{event.lower()} AFTER {event} ON {table} WHEN NOT EXISTS(SELECT 1 FROM state_chunk_suspended WHERE branch={owner}.branch) BEGIN {''.join(touch(a) for a in aliases)} END")
    signature=json.dumps(columns);key='columns:'+table
    old=db.execute('SELECT value FROM state_chunk_meta WHERE key=?',(key,)).fetchone()
    if old is None or old[0]!=signature:
     grouping='branch' if expression=='0' else 'branch,'+expression
     db.execute(f"INSERT OR IGNORE INTO state_chunk_versions SELECT branch,'{table}',{expression},1 FROM {table} GROUP BY {grouping}")
     db.execute('DELETE FROM state_chunk_heads WHERE table_name=?',(table,))
     db.execute('INSERT OR REPLACE INTO state_chunk_meta VALUES(?,?)',(key,signature))

 def capture(self,info):
  branch=info['id'];rows_encoded=0;bytes_encoded=0;changed=0
  dirty=self.db.execute('''SELECT v.table_name,v.part,v.version FROM state_chunk_versions v
LEFT JOIN state_chunk_heads h ON h.branch=v.branch AND h.table_name=v.table_name AND h.part=v.part
WHERE v.branch=? AND (h.version IS NULL OR h.version<>v.version) ORDER BY v.table_name,v.part''',(branch,)).fetchall()
  for table,part,version in dirty:
   if table not in self.layouts:raise ValueError('Unknown journal table')
   columns,order=self.layouts[table]
   query='SELECT '+','.join(columns)+' FROM '+table+' WHERE branch=? AND ('+partition(table)+')=? ORDER BY '+','.join(order)
   rows=[list(r) for r in self.db.execute(query,(branch,part))]
   raw=encoded(dict(columns=columns,rows=rows));digest=hashlib.sha256(raw).hexdigest()
   if not self.db.execute('SELECT 1 FROM state_chunk_objects WHERE hash=?',(digest,)).fetchone():
    self.db.execute('INSERT INTO state_chunk_objects VALUES(?,?)',(digest,zlib.compress(raw,6)));changed+=1
   self.db.execute('INSERT OR REPLACE INTO state_chunk_heads VALUES(?,?,?,?,?,?)',(branch,table,part,version,digest,len(rows)))
   rows_encoded+=len(rows);bytes_encoded+=len(raw)
  tables={table:dict(columns=self.layouts[table][0],chunks=[]) for table in self.tables}
  for table,digest in self.db.execute('SELECT table_name,object_hash FROM state_chunk_heads WHERE branch=? AND row_count>0 ORDER BY table_name,part',(branch,)):
   if table in tables:tables[table]['chunks'].append(digest)
  self.stats=dict(partitions_checked=len(dirty),objects_created=changed,rows_encoded=rows_encoded,bytes_encoded=bytes_encoded,references=sum(len(t['chunks']) for t in tables.values()))
  return zlib.compress(encoded(dict(journal=1,info=info,tables=tables)),6)

 def materialize(self,payload):
  state=json.loads(zlib.decompress(payload))
  if state.get('journal')!=1:return payload
  tables={}
  for table,manifest in state['tables'].items():
   if table not in self.layouts:raise ValueError('Unknown journal table')
   columns=manifest['columns'];rows=[]
   for digest in manifest['chunks']:
    found=self.db.execute('SELECT payload FROM state_chunk_objects WHERE hash=?',(digest,)).fetchone()
    if found is None:raise ValueError('Missing immutable journal object')
    raw=zlib.decompress(found[0])
    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError('Journal object checksum mismatch')
    chunk=json.loads(raw)
    if chunk['columns']!=columns:raise ValueError('Journal column mismatch')
    rows.extend(chunk['rows'])
   # Preserve the same canonical key order used by a full legacy snapshot.
   keys=[columns.index(c) for c in self.layouts[table][1] if c in columns]
   rows.sort(key=lambda row:tuple((row[i] is not None,row[i]) for i in keys))
   tables[table]=dict(columns=columns,rows=rows)
  return zlib.compress(encoded(dict(info=state['info'],tables=tables)),6)

 def suspend(self,branch):self.db.execute('INSERT OR IGNORE INTO state_chunk_suspended VALUES(?)',(branch,))
 def collect(self,limit=128):
  """Bounded removal of unreachable temporary chunks, never career history.

  Save checkpoints are self-contained; live heads and ALL retained journal
  manifests pin their immutable chunks, including past/discarded branches.
  Caller holds the same SQLite write transaction as the session publication.
  """
  keep={r[0] for r in self.db.execute('SELECT DISTINCT object_hash FROM state_chunk_heads')}
  for payload, in self.db.execute('SELECT state FROM session_states'):
   if not zlib.decompressobj().decompress(payload,32).startswith(b'{"journal":1,'):continue
   manifest=json.loads(zlib.decompress(payload))
   for table in manifest['tables'].values():keep.update(table['chunks'])
  removed=0
  for digest, in self.db.execute('SELECT hash FROM state_chunk_objects'):
   if digest in keep:continue
   self.db.execute('DELETE FROM state_chunk_objects WHERE hash=?',(digest,));removed+=1
   if removed>=limit:break
  return removed
 def export_legacy_sessions(self):
  """Rollback bridge: preserve native revision IDs and every saved fact."""
  count=0
  cursor=self.db.execute('SELECT pid,created,context,captured_ms,state FROM session_states')
  for pid,created,context,captured,payload in cursor:
   if not zlib.decompressobj().decompress(payload,32).startswith(b'{"journal":1,'):continue
   full=self.materialize(payload)
   self.db.execute('UPDATE session_states SET state=? WHERE pid=? AND created=? AND context=? AND captured_ms=?',(full,pid,created,context,captured));count+=1
  return count
 def discarded(self,branch):
  for table in ('state_chunk_heads','state_chunk_versions','state_chunk_suspended'):self.db.execute('DELETE FROM '+table+' WHERE branch=?',(branch,))
