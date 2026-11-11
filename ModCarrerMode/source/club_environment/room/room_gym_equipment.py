"""Optional imported rehabilitation props, using the room's native renderer."""
from functools import lru_cache
from pathlib import Path
import json

PREFIX='data/sceneassets/server16_dressing_room_v3/rehab_equipment/'


def content_stamp(game):
    file=Path(game)/PREFIX/'equipment.json'
    return (str(file),file.stat().st_mtime_ns,file.stat().st_size) if file.is_file() else None


@lru_cache(maxsize=4)
def _read(path,modified,size):
    return json.loads(Path(path).read_text(encoding='utf8'))


def specification(game):
    stamp=content_stamp(game)
    if not stamp:return None
    spec=_read(*stamp)
    # Activate geometry and collision replacement together, only for a complete pack.
    required=[*spec['required'],*(b['model'] for b in spec['bindings']),*(b['texture'] for b in spec['bindings'])]
    return spec if all((Path(game)/p).is_file() for p in required) else None


def prepare(game,add,identity):
    spec=specification(game)
    if not spec:return False
    for b in spec['bindings']:
        add(b['key'],b['model'],b['texture'],'equipment_cm',identity,False,submesh=b['submesh'])
    return True


def obstacles(game,items):
    spec=specification(game)
    if not spec:return items
    replaced={'estação de cabos','banco de exercícios','halteres','bola de estabilidade'}
    result=[p for p in items if not (p['name'].startswith('Departamento médico R77 / ') and p['name'].split(' / ',1)[1] in replaced)]
    return result+spec['obstacles']
