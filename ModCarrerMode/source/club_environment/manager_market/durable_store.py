"""Per-slot recovery journals outside the directories managed/deleted by FIFA.

Copy immutable revisions before advertising them to the native save hook. An
immediate Save As/exit can then recover that exact revision, even if FIFA removes
the original slot. Unsaved revisions are never selected without a write receipt.
"""
from pathlib import Path
import hashlib,json,zlib


def root(save):
    from save_database import normal
    return normal(save).parent.parent.parent/'server16_manager_market_recovery'


def path(save):
    from save_database import normal,NAME
    return root(save)/normal(save).parent.name/NAME


def sources(save):
    from save_database import NAME
    return sorted(root(save).glob('*/'+NAME))


def persist(market,save,revision=None,*,checkpoints=False,full=False,keep_open=False):
    from engine import Market
    destination=path(save)
    if destination.resolve()==market.path.resolve():return dict(states=0,objects=0,checkpoints=0)
    sql='SELECT * FROM session_states'
    args=()
    if revision and not full:sql+=' WHERE state_hash=?';args=(revision,)
    rows=market.db.execute(sql+' ORDER BY created DESC,captured_ms DESC LIMIT 128',args).fetchall()
    saved=market.db.execute('SELECT * FROM save_checkpoints ORDER BY rowid DESC LIMIT 8').fetchall() if checkpoints else []
    if not rows and not saved:return dict(states=0,objects=0,checkpoints=0)
    mirror=getattr(market,'_durable_mirror',None) if keep_open else None
    if mirror and mirror.path.resolve()!=destination.resolve():mirror.close();mirror=None
    if mirror is None:mirror=Market(destination,market.catalog)
    if keep_open:market._durable_mirror=mirror
    counts=dict(states=0,objects=0,checkpoints=0)
    try:
        with mirror.db:
            references=set()
            for row in rows:
                old=mirror.db.execute('SELECT state_hash FROM session_states WHERE pid=? AND created=? AND context=? AND captured_ms=?',
                    tuple(row[k] for k in ('pid','created','context','captured_ms'))).fetchone()
                if old:
                    if old[0]!=row['state_hash']:raise ValueError('Conflicting durable coach revision')
                    continue
                payload=bytes(row['state'])
                if hashlib.sha256(payload).hexdigest()!=row['state_hash']:raise ValueError('Invalid coach revision hash')
                state=json.loads(zlib.decompress(payload))
                if state.get('journal')==1:
                    for table in state['tables'].values():references.update(table['chunks'])
                mirror.db.execute('INSERT INTO session_states VALUES(?,?,?,?,?,?,?,?,?)',tuple(row))
                observation=market.db.execute('SELECT * FROM session_observations WHERE pid=? AND created=? AND context=? AND captured_ms=?',
                    tuple(row[k] for k in ('pid','created','context','captured_ms'))).fetchone()
                if observation:mirror.db.execute('INSERT OR REPLACE INTO session_observations VALUES(?,?,?,?,?)',tuple(observation))
                counts['states']+=1
            known={r[0] for r in mirror.db.execute('SELECT hash FROM state_chunk_objects')}
            missing=sorted(references-known)
            for offset in range(0,len(missing),500):
                chunk=missing[offset:offset+500]
                objects=market.db.execute('SELECT * FROM state_chunk_objects WHERE hash IN ('+','.join('?' for _ in chunk)+')',chunk).fetchall()
                if len(objects)!=len(chunk):raise ValueError('Incomplete durable coach journal')
                mirror.db.executemany('INSERT INTO state_chunk_objects VALUES(?,?)',[tuple(r) for r in objects]);counts['objects']+=len(objects)
            for row in saved:
                if not row['state']:continue
                old=mirror.db.execute('SELECT state FROM save_checkpoints WHERE save_hash=?',(row['save_hash'],)).fetchone()
                if old and bytes(old[0])==bytes(row['state']):continue
                mirror.db.execute('INSERT OR REPLACE INTO save_checkpoints VALUES(?,?,?,?,?)',tuple(row));counts['checkpoints']+=1
            for row in market.db.execute('SELECT * FROM save_receipts'):
                mirror.db.execute('INSERT OR IGNORE INTO save_receipts VALUES(?,?,?,?,?,?,?,?)',tuple(row))
            mirror.db.execute('DELETE FROM session_states WHERE rowid NOT IN (SELECT rowid FROM session_states ORDER BY created DESC,captured_ms DESC LIMIT 128)')
            mirror.db.execute('DELETE FROM session_observations WHERE NOT EXISTS (SELECT 1 FROM session_states s WHERE s.pid=session_observations.pid AND s.created=session_observations.created AND s.context=session_observations.context AND s.captured_ms=session_observations.captured_ms)')
            mirror.db.execute('DELETE FROM save_checkpoints WHERE rowid NOT IN (SELECT rowid FROM save_checkpoints ORDER BY rowid DESC LIMIT 8)')
            mirror.journal.collect(limit=512)
        return counts
    finally:
        if not keep_open:mirror.close()


def approved_reset(game,save,context):
    """An explicit recovery waiver is tied to one DATA digest and its receipts."""
    from save_database import normal
    if not context or not context.get('digest'):return set()
    name=hashlib.sha256(str(normal(save)).encode('utf8')).hexdigest()
    file=Path(game)/'ModCarrerMode/runtime/manager_market/recovery_resets'/(name+'.json')
    try:
        value=json.loads(file.read_bytes())
        if value.get('schema')!=1 or value.get('digest')!=context['digest'] or normal(value['save'])!=normal(save):return set()
        return set(value['receipts'])
    except (OSError,ValueError,KeyError,TypeError):return set()
