"""Resolve career coaches to their original FIFA SLC manager models."""
from pathlib import Path
import struct

try:
    from .coach_registry import load as load_registry
except ImportError:
    from coach_registry import load as load_registry

_cache = {}


def catalog(game):
    """Load the editable roster; its model IDs point into FIFA's native SLC."""
    path = Path(game) / 'ModCarrerMode/data/manager_market/manager_registry.ini'
    result = {}
    for key, row in load_registry(path).items():
        if not row['model_enabled'] or not row['source_slc_club_id']:
            continue
        result[key] = dict(row, coachId=key, assetId=row['source_slc_club_id'])
    return result


def installed(game, row):
    """Check all native weather/model-texture variants without copying them."""
    if not row or not row.get('model_enabled'):
        return False
    try:
        slc_id = int(row['source_slc_club_id'])
        if not 0 < slc_id <= 200000:
            return False
        folder = Path(game) / 'data/sceneassets/slc'
        paths = [folder / f'specificmanager_{slc_id}_0_{weather}{suffix}.rx3'
                 for weather in (0, 1) for suffix in ('', '_textures')]
        stats = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
        signature = (str(folder.resolve()), slc_id, stats)
        if signature in _cache:
            return _cache[signature]
        valid = all(size >= 32 for size, _ in stats)
        if valid:
            for path in paths:
                with path.open('rb') as source:
                    if source.read(4) not in (b'RX3l', b'RX3b'):
                        valid = False
                        break
        _cache[signature] = valid
        return valid
    except (OSError, ValueError, TypeError, KeyError):
        return False


def actor(game, market):
    if not market:
        return None
    key = market.get('coach', {}).get('coach_id', '')
    row = catalog(game).get(key)
    if not installed(game, row):
        return None
    slc_id = row['source_slc_club_id']
    return dict(coachId=key, assetId=slc_id,
                appointment=market['appointment']['id'],
                base=f'data/sceneassets/slc/specificmanager_{slc_id}_0_0')


def fixture(original, selected):
    magic, club, *colors = struct.unpack('<8s4I', original)
    if magic != b'FFCOACH1' or not 0 < club <= 200000:
        raise ValueError('Invalid coach fixture')
    slc_id = int(selected['assetId'])
    if not 0 < slc_id <= 200000:
        raise ValueError('Invalid source SLC manager ID')
    return struct.pack('<8s5I', b'FFCOACH2', club, *colors, slc_id)


def publication(game, db, state):
    """Publish only the committed career branch's active club -> SLC map."""
    from preview_files import atomic
    branch = db.execute('SELECT game_date,user_club FROM branches WHERE id=?',
                        (state['branch'],)).fetchone()
    if (branch is None or int(branch['game_date']) != state['date']
            or int(branch['user_club']) != state['club']):
        raise ValueError('Uncommitted manager branch')
    choices = catalog(game)
    rows = db.execute(
        'SELECT club_id,coach_id FROM appointments WHERE branch=? AND end_date IS NULL AND start_date<=? ORDER BY club_id',
        (state['branch'], state['date'])).fetchall()
    seen = set()
    mapping = []
    for row in rows:
        club = int(row['club_id'])
        key = row['coach_id']
        if club in seen:
            raise ValueError('Ambiguous current coach')
        if not 0 < club <= 200000:
            continue
        seen.add(club)
        entry = choices.get(key)
        slc_id = entry['source_slc_club_id'] if installed(game, entry) else 0
        mapping.append((club, slc_id))
    operation, tick, path_value = state['io']
    fields = dict(schema=2, pid=state['pid'], created=state['created'],
                  context=state['context'], epoch=state['epoch'], club=state['club'],
                  date=state['date'], operation=operation, access_tick_ms=tick,
                  path=path_value, branch=state['branch'], digest=state['digest'],
                  revision=state['revision'])
    if operation not in ('read', 'write') or not str(tick).isdigit():
        raise ValueError('Incomplete native save event')
    lines = ['S16MGR2']
    for key, value in fields.items():
        value = str(value)
        if any(char in value for char in '\r\n\t'):
            raise ValueError('Invalid model scope')
        lines.append(key + '=' + value)
    lines.extend(f'row={club}|{slc_id}' for club, slc_id in mapping)
    blob = ('\n'.join(lines) + '\n').encode('utf8')
    target = Path(game) / 'ModCarrerMode/runtime/manager_market/models_ready.tsv'
    try:
        if target.read_bytes() == blob:
            return
    except OSError:
        pass
    atomic(target, blob)
