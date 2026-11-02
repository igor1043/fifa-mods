"""Career coach identity -> immutable, installed model pair; no club rewrites."""
from pathlib import Path
import hashlib,json,re,struct

KEY=re.compile(r'COACH-[0-9a-f]{16}\Z')
_cache={}

def catalog(game):
    path=Path(game)/'ModCarrerMode/data/manager_market/manager_models.json'
    try:
        data=json.loads(path.read_text(encoding='utf8'))
        if data.get('schema')!=2 or data.get('runtimeOverrideEnabled') is not True:return {}
        rows=data['coaches'];result={};ids=set()
        for row in rows:
            key=row['coachId'];number=row['assetId']
            if not KEY.fullmatch(key) or type(number)!=int or not 1<=number<=200000 or key in result or number in ids:return {}
            result[key]=row;ids.add(number)
        return result
    except (OSError,ValueError,KeyError,TypeError):return {}

def installed(game,row):
    if not row:return False
    try:
        base=Path(game)/'data/sceneassets/manager_market'/str(row['assetId']);paths=[base/f'model_{weather}{suffix}.rx3' for weather in (0,1) for suffix in ('','_textures')]
        expected=row['files'];signature=(str(base),tuple((p.stat().st_size,p.stat().st_mtime_ns,expected[p.name]) for p in paths))
        if signature in _cache:return _cache[signature]
        # This registry is generated only from structurally validated native
        # SLC pairs. Check immutable payload hashes before allowing either
        # geometry or textures; never mix a new coach with a predecessor.
        valid=all(hashlib.sha256(p.read_bytes()).hexdigest()==expected[p.name] for p in paths)
        _cache[signature]=valid;return valid
    except (OSError,KeyError,ValueError,TypeError):return False

def actor(game,market):
    if not market:return None
    key=market.get('coach',{}).get('coach_id','');row=catalog(game).get(key)
    if not installed(game,row):return None
    return dict(coachId=key,assetId=row['assetId'],appointment=market['appointment']['id'],base=f'data/sceneassets/manager_market/{row["assetId"]}/model_0')

def fixture(original,selected):
    magic,club,*colors=struct.unpack('<8s4I',original)
    if magic!=b'FFCOACH1' or not 0<club<=200000:raise ValueError('Invalid coach fixture')
    return struct.pack('<8s5I',b'FFCOACH2',club,*colors,selected['assetId'])

def publication(game,db,state):
    """Called after the exact market branch has committed for this owner/save."""
    from preview_files import atomic
    branch=db.execute('SELECT game_date,user_club FROM branches WHERE id=?',(state['branch'],)).fetchone()
    if branch is None or int(branch['game_date'])!=state['date'] or int(branch['user_club'])!=state['club']:raise ValueError('Uncommitted manager branch')
    choices=catalog(game);rows=db.execute('SELECT club_id,coach_id FROM appointments WHERE branch=? AND end_date IS NULL AND start_date<=? ORDER BY club_id',(state['branch'],state['date'])).fetchall();seen=set();mapping=[]
    for row in rows:
        club=int(row['club_id']);key=row['coach_id']
        if club in seen:raise ValueError('Ambiguous current coach')
        if not 0<club<=200000:continue
        seen.add(club);entry=choices.get(key);mapping.append((club,entry['assetId'] if installed(game,entry) else 0))
    operation,tick,path=state['io'];fields=dict(schema=1,pid=state['pid'],created=state['created'],context=state['context'],epoch=state['epoch'],club=state['club'],date=state['date'],operation=operation,access_tick_ms=tick,path=path,branch=state['branch'],digest=state['digest'],revision=state['revision'])
    if operation not in ('read','write') or not str(tick).isdigit():raise ValueError('Incomplete native save event')
    lines=['S16MGR1']
    for key,value in fields.items():
        value=str(value)
        if any(c in value for c in '\r\n\t'):raise ValueError('Invalid model scope')
        lines.append(key+'='+value)
    lines.extend(f'row={club}|{asset}' for club,asset in mapping);blob=('\n'.join(lines)+'\n').encode('utf8');path=Path(game)/'ModCarrerMode/runtime/manager_market/models_ready.tsv'
    try:
        if path.read_bytes()==blob:return
    except OSError:pass
    atomic(path,blob)
