"""One independent coach world beside each FIFA career's DATA and INDEX.

The old shared store is consulted read-only, by the exact DATA digest, solely
to import a saved checkpoint. No native save bytes are ever modified here.
"""
from contextlib import closing
from pathlib import Path
import json,sqlite3,zlib
import os,uuid

NAME='server16_manager_market.sqlite3'

def normal(path):
 value=str(path)
 if value.startswith('\\\\?\\UNC\\'):value='\\\\'+value[8:]
 elif value.startswith('\\\\?\\'):value=value[4:]
 return Path(value).resolve()

def database_path(save):return normal(save).parent/NAME
def settings_path(save):return normal(save).parent.parent/'server16_manager_market_settings.json'

def retain_checkpoints(market,save):
 """Bound superseded copies of this slot, not the history inside its world."""
 if normal(market.path)!=database_path(save):return
 market.db.execute('DELETE FROM save_checkpoints WHERE rowid NOT IN (SELECT rowid FROM save_checkpoints ORDER BY rowid DESC LIMIT 8)')

def readonly(path):
 db=sqlite3.connect(normal(path).as_uri()+'?mode=ro',uri=True,timeout=1)
 db.row_factory=sqlite3.Row;db.execute('PRAGMA query_only=ON');return db

def import_checkpoint(target,save,digest,previous=None):
 """Import only an exact saved world; never choose by date, club or newest row."""
 if target.db.execute('SELECT 1 FROM save_checkpoints WHERE save_hash=?',(digest,)).fetchone():return False
 from durable_store import sources as durable_sources
 sources=[previous,normal(save).parent.parent/NAME,*durable_sources(save)]
 seen={normal(target.path)}
 for path in sources:
  if not path:continue
  path=normal(path)
  if path in seen or not path.is_file():continue
  seen.add(path)
  with closing(readonly(path)) as db:
   db.execute('BEGIN')
   row=db.execute('SELECT * FROM save_checkpoints WHERE save_hash=?',(digest,)).fetchone()
   if not row:continue
   if not row['state']:raise ValueError('Checkpoint antigo sem snapshot; preserve o banco original para recuperação')
   state=bytes(row['state']);info=json.loads(zlib.decompress(state))['info']
   if info['game_date']!=row['game_date']:raise ValueError('Data do snapshot de migração incompatível')
   target.checkpoint(digest,save,state=state)
   import_awards(target.path,path,digest=digest)
   receipts=db.execute('SELECT * FROM save_receipts WHERE save_hash=?',(digest,)).fetchall()
   target.db.executemany('INSERT OR IGNORE INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',[tuple(r) for r in receipts])
  return True
 return False

def store_receipt(market,save,digest,payload,receipt):
 """A Save As/autosave owns its snapshot even if that slot is never opened."""
 target_path=database_path(save)
 if market.path.name!=NAME or normal(market.path)==target_path:
  market.checkpoint(digest,save,replace=True,state=payload);return
 try:from .engine import Market
 except ImportError:from engine import Market
 full=market.journal.materialize(payload)
 target=Market(target_path,market.catalog)
 try:
  with target.db:
   newer=target.db.execute('SELECT 1 FROM save_receipts WHERE save_hash=? AND created=? AND write_ms>?',(digest,receipt[5],receipt[6])).fetchone()
   if not newer:
    target.checkpoint(digest,save,replace=True,state=full)
    info=json.loads(zlib.decompress(full))['info']
    import_awards(target.path,market.path,branch=info['id'],digest=digest,through=info['game_date'])
   target.db.execute('INSERT OR IGNORE INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',receipt)
 finally:target.close()

def recover_pending(target,game,save,context):
 """Recover Save As completed while the helper was stopped or restarting.

Only an exact durable write revision can select another slot's short journal.
This exceptional load-time handoff never consults/re-simulates other worlds.
"""
 try:from .save_sync import record,pending_checkpoint,bind_pending
 except ImportError:from save_sync import record,pending_checkpoint,bind_pending
 if not pending_checkpoint(target,game,save,context):return []
 revisions=[]
 folder=Path(game)/'ModCarrerMode/runtime/manager_market/save_events'
 for file in folder.glob('*.tsv'):
  try:
   event=record(file)
   if event.get('operation')!='write' or normal(event['path'])!=normal(save) or not event.get('market_revision'):continue
   revisions.append((int(event['pid']),int(event['process_created_100ns']),int(event['epoch']),event['market_revision'],int(event['market_context'],16)))
  except (OSError,KeyError,ValueError,TypeError):continue
 if not revisions:return []
 try:from .engine import Market
 except ImportError:from engine import Market
 found=[]
 from durable_store import sources as durable_sources
 candidates=[*normal(save).parent.parent.glob('*/'+NAME),*durable_sources(save),
             *normal(save).parent.parent.parent.glob('server16_deleted_save_data/*/'+NAME)]
 for path in dict.fromkeys(candidates):
  if normal(path)==normal(target.path):continue
  with closing(readonly(path)) as db:
   owned=any(db.execute('SELECT 1 FROM session_states WHERE pid=? AND created=? AND epoch=? AND state_hash=? AND context=? LIMIT 1',v).fetchone() for v in revisions)
  if not owned:continue
  source=Market(path,target.catalog)
  try:
   with source.db:found.extend(bind_pending(source,game))
  finally:source.close()
  if not pending_checkpoint(target,game,save,context):break
 return found

def import_live(target,source,branch,save,session_limit=128,new_branch=None):
 """Installation handoff: carry the exact current world, not a fresh simulation.

Unrelated branches and unreachable temporary chunks are not copied. Retained
native save revisions keep their original hashes and their referenced objects.
Caller stops the worker and owns the destination transaction.
"""
 try:from .engine import TABLES
 except ImportError:from engine import TABLES
 destination=new_branch or branch
 if target.db.execute('SELECT 1 FROM branches WHERE id=?',(destination,)).fetchone():raise ValueError('Mundo de destino já existe')
 with closing(readonly(source)) as db:
  db.execute('BEGIN');row=db.execute('SELECT * FROM branches WHERE id=?',(branch,)).fetchone()
  if row is None:raise ValueError('Mundo ativo não encontrado')
  info=dict(row);info['id']=destination
  target.db.execute('INSERT INTO branches VALUES(?,?,?,?,?,?,?,?)',tuple(info.values()))
  available={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  for table in TABLES:
   if table in ('trophy_history','trophy_national_tenures') and table not in available:continue
   rows=db.execute('SELECT * FROM '+table+' WHERE branch=?',(branch,)).fetchall()
   if rows:
    # Older schemas added birthplace at the end; SELECT * is not portable
    # between those layouts. Bind every fact by its actual column name.
    columns=rows[0].keys()
    values=[tuple(destination if key=='branch' else r[key] for key in columns) for r in rows]
    target.db.executemany('INSERT INTO '+table+' ('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',values)
  for row in db.execute('SELECT * FROM save_checkpoints'):
   if normal(row['save_path'])!=normal(save):continue
   target.db.execute('INSERT OR IGNORE INTO save_checkpoints VALUES(?,?,?,?,?)',tuple(row))
  refs=set()
  for row in db.execute('SELECT * FROM session_states WHERE branch=? ORDER BY created DESC,captured_ms DESC LIMIT ?',(branch,session_limit)):
   existing=target.db.execute('SELECT state_hash FROM session_states WHERE pid=? AND created=? AND context=? AND captured_ms=?',(row['pid'],row['created'],row['context'],row['captured_ms'])).fetchone()
   if existing and existing[0]!=row['state_hash']:raise ValueError('Revisão nativa conflitante no destino')
   target.db.execute('INSERT OR IGNORE INTO session_states VALUES(?,?,?,?,?,?,?,?,?)',tuple(row))
   state=json.loads(zlib.decompress(row['state']))
   if state.get('journal')==1:
    for table in state['tables'].values():refs.update(table['chunks'])
   observation=db.execute('SELECT * FROM session_observations WHERE pid=? AND created=? AND context=? AND captured_ms=?',(row['pid'],row['created'],row['context'],row['captured_ms'])).fetchone()
   if observation:target.db.execute('INSERT OR IGNORE INTO session_observations VALUES(?,?,?,?,?)',tuple(observation))
  for ref in refs:
   row=db.execute('SELECT * FROM state_chunk_objects WHERE hash=?',(ref,)).fetchone()
   if row is None:raise ValueError('Snapshot temporário incompleto')
   target.db.execute('INSERT OR IGNORE INTO state_chunk_objects VALUES(?,?)',tuple(row))
  for row in db.execute('SELECT * FROM save_receipts WHERE save_hash IN (SELECT save_hash FROM save_checkpoints)'):
   if target.db.execute('SELECT 1 FROM save_checkpoints WHERE save_hash=?',(row['save_hash'],)).fetchone():target.db.execute('INSERT OR IGNORE INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',tuple(row))
 target.branch=destination
 import_awards(target.path,source,branch=branch,into=destination)
 for row in target.db.execute('SELECT save_hash FROM save_checkpoints'):
  import_awards(target.path,source,digest=row[0])

def import_awards(target,source,branch=None,digest=None,through=None,into=None):
 """Monthly-award observations follow the same save, never the shared world."""
 name='competition_monthly.sqlite3';source=normal(source).with_name(name);target=normal(target).with_name(name)
 if source==target or not source.is_file():return
 with closing(readonly(source)) as old:
  schemas={r['name']:r['sql'] for r in old.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name IN ('observations_v2','checkpoints')")}
  if len(schemas)!=2:return
  rows=old.execute('SELECT * FROM observations_v2 WHERE branch=?'+(' AND day<=?' if through else ''),(branch,through) if through else (branch,)).fetchall() if branch else []
  saved=old.execute('SELECT payload FROM checkpoints WHERE save_hash=?',(digest,)).fetchone() if digest else None
  with closing(sqlite3.connect(target)) as new,new:
   for schema in schemas.values():new.execute(schema.replace('CREATE TABLE ','CREATE TABLE IF NOT EXISTS ',1))
   new.executemany('INSERT OR IGNORE INTO observations_v2 VALUES(?,?,?,?)',[(into or r['branch'],r['day'],r['signature'],r['payload']) for r in rows])
   if digest:
    payload=saved[0] if saved else zlib.compress(json.dumps([json.loads(zlib.decompress(r['payload'])) for r in sorted(rows,key=lambda r:r['day'])],separators=(',',':')).encode())
    new.execute('INSERT OR IGNORE INTO checkpoints VALUES(?,?)',(digest,payload))

def quarantine_deleted(save_root):
 """After FIFA exits, detach only mod databases of fully deleted native slots.

Keep a recoverable copy outside the native save tree; never delete DATA/INDEX.
A partial save (either file remains), a symlink or an unknown SQL is untouched.
"""
 root=normal(save_root);moved=[]
 for database in root.glob('*/'+NAME):
  slot=database.parent
  if slot.is_symlink() or normal(slot).parent!=root or len(slot.name)!=8 or any(c not in '0123456789abcdef' for c in slot.name.lower()):continue
  if (slot/'DATA').exists() or (slot/'INDEX').exists():continue
  try:
   with closing(readonly(database)) as db:
    if db.execute('PRAGMA user_version').fetchone()[0]!=5 or not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='save_checkpoints'").fetchone():continue
   target=root.parent/'server16_deleted_save_data'/(slot.name+'-'+uuid.uuid4().hex)
   target.mkdir(parents=True,exist_ok=False)
   for name in (NAME,'competition_monthly.sqlite3'):
    for suffix in ('','-wal','-shm','-journal'):
     file=slot/(name+suffix)
     if file.is_file():os.replace(file,target/file.name)
   moved.append(str(target))
  except (OSError,sqlite3.Error):continue
 return moved

