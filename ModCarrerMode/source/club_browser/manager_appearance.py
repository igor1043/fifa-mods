"""Small appearance snapshots next to each career DATA; never edits native saves."""
from pathlib import Path
from contextlib import closing
import hashlib,json,sqlite3

NAME='server16_manager_appearance.sqlite3'
SCHEMA='''CREATE TABLE IF NOT EXISTS appearances(
 digest TEXT PRIMARY KEY,coach TEXT NOT NULL,asset INTEGER NOT NULL,
 saved_club INTEGER NOT NULL,io_tick INTEGER NOT NULL);
PRAGMA user_version=1;'''


def snapshot(save):
    path=Path(save);before=path.stat();digest=hashlib.sha256(path.read_bytes()).hexdigest();after=path.stat()
    if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise InterruptedError('Carreira sendo gravada')
    return digest


def load_record(save,digest):
    file=Path(save).parent/NAME
    if not file.is_file():return None
    with closing(sqlite3.connect(file.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        row=db.execute('SELECT coach,asset FROM appearances WHERE digest=?',(digest,)).fetchone()
    return dict(coach=row[0],asset=row[1]) if row else None


def load(save,digest):
    record=load_record(save,digest)
    return record if record and record['asset']>0 else None


def save(save,digest,choice,club,tick):
    if len(digest)!=64 or (choice and not 0<int(choice['asset'])<=200000):raise ValueError('Invalid appearance snapshot')
    file=Path(save).parent/NAME
    with closing(sqlite3.connect(file,timeout=2)) as db:
        db.executescript(SCHEMA)
        with db:
            db.execute('INSERT OR REPLACE INTO appearances VALUES(?,?,?,?,?)',(digest,choice['coach'] if choice else '',int(choice['asset']) if choice else 0,int(club),int(tick)))
            db.execute('DELETE FROM appearances WHERE digest NOT IN (SELECT digest FROM appearances ORDER BY io_tick DESC LIMIT 128)')
    return file


def selected(draft,*,pid,created,event_tick,operation,allowed):
    """Only a confirmed, armed creation may bind to its first complete save."""
    try:
        asset=int(draft['asset']);coach=draft['coach']
        if (int(draft['schema'])!=1 or int(draft['pid'])!=pid or int(draft['created'])!=created
            or draft.get('phase')!='initializing' or draft.get('confirmed')!='1' or operation!='write'
            or not 0<int(draft['armed_tick'])<event_tick or allowed.get(coach)!=asset):return None
        return dict(coach=coach,asset=asset)
    except (KeyError,TypeError,ValueError):return None


def actor(game,club,scope):
    """Read only the current, scoped visual override; not an AI appointment."""
    try:
        from manager_market.model_assets import catalog,installed
        root=Path(game)/'ModCarrerMode/runtime/user_manager'
        state=json.loads((root/'active.json').read_text(encoding='utf8'))
        normal=lambda path:str(path).removeprefix('\\\\?\\').replace('\\','/').casefold()
        if (state['pid']!=scope['pid'] or state['created']!=scope['created'] or state['context']!=scope['context_address']
            or state['epoch']!=scope['context_epoch'] or state['club']!=club or normal(state['path'])!=normal(scope['save_path'])):return None
        row=catalog(game).get(state['coach'])
        if not installed(game,row) or row['assetId']!=state['asset']:return None
        return dict(coachId=row['coachId'],assetId=row['assetId'],appointment='user',base=f'data/sceneassets/slc/specificmanager_{row["assetId"]}_0_0')
    except (OSError,ValueError,KeyError,TypeError):return None
