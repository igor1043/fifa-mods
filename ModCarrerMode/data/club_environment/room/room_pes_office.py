"""Optional, versioned office furniture; native saves and source room assets stay intact."""
from pathlib import Path
from functools import lru_cache
import json

PREFIX = 'data/sceneassets/server16_dressing_room_v3/pes_office/'


def content_stamp(game):
    file = Path(game) / PREFIX / 'office.json'
    return (str(file), file.stat().st_mtime_ns, file.stat().st_size) if file.is_file() else None


@lru_cache(maxsize=4)
def _read(file, modified, size):
    return json.loads(Path(file).read_text(encoding='utf8'))


def specification(game):
    stamp = content_stamp(game)
    return _read(*stamp) if stamp else None


def model_path(game, model):
    spec = specification(game)
    return spec.get('replacements', {}).get(model, model) if spec else model

def merge_main_shell(approved,new_shell):
    """Rebase an updated main room without resurrecting old office furniture.

    Models keep the original submesh layout. The established coach annex is
    retained triangle-for-triangle; only the separated main-room side changes.
    """
    import numpy as np
    from rx3 import VERTEX
    from room_visual_r68 import read_mesh,replace_mesh,join
    from room_v3 import MAIN_END,split_at_z
    if len(approved.get(VERTEX))!=len(new_shell.get(VERTEX)):
        raise ValueError('Office variant submesh layout changed')
    for slot in range(len(approved.get(VERTEX))):
        pieces=[]
        for rx,main in ((new_shell,True),(approved,False)):
            v,idx=split_at_z(*read_mesh(rx,slot),MAIN_END)
            tri=idx.reshape(-1,3);inside=(v['p'][tri][:,:,2]<=MAIN_END+.001).all(1)
            tri=tri[inside if main else ~inside]
            if len(tri):
                used,inverse=np.unique(tri,return_inverse=True)
                pieces.append((v[used],inverse.reshape(-1).astype('<u2')))
        if pieces:
            vertices,indices=join(pieces)
            if len(vertices)>=65536:raise ValueError('Rebased office exceeds native vertex budget')
            replace_mesh(approved,slot,vertices,indices)
    return approved


def prepare(game, add, identity):
    spec = specification(game)
    if not spec:
        return False
    for binding in spec['bindings']:
        add(binding['key'], binding['model'], binding['texture'], binding.get('texname','office_cm'), identity,
            binding['alpha'], binding['submesh'])
    return True


def scene_pose(game, label, original):
    spec=specification(game)
    if spec and label in spec.get('scene_poses',{}):
        return spec['scene_poses'][label]
    if label == 'Sala do treinador · visão geral' and spec:
        return spec.get('overview_pose',[215,190,1710,215,125,2120,83])
    return original


def obstacles(game, items):
    spec = specification(game)
    if not spec:
        return items
    # Only R76 furniture is replaced. Boundary walls and every doorway remain.
    old_furniture = ('mesa', 'cadeira', 'armário de apoio', 'estante de arquivos', 'vaso')
    result = [item for item in items if not (
        item['name'].startswith('Sala do treinador R76 / ') and
        item['name'].split(' / ', 1)[1] in old_furniture)]
    return result + spec['obstacles']
