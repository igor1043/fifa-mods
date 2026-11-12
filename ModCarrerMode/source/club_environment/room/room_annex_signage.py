"""One fitted sign per annex entrance; retain the original wall and sign artwork."""
from functools import lru_cache
from pathlib import Path
import hashlib,os
import numpy as np
from rx3 import Rx3,VERTEX
from room_visual_r68 import read_mesh,replace_mesh

PREFIX='data/sceneassets/server16_dressing_room_v3/'
OUTPUT=PREFIX+'annex_signage/'


def medical_backing(vertices,indices):
    points=vertices['p'][indices.reshape(-1,3)]
    # The red lintel duplicates the white structural wall behind it. Its
    # exposed margins look like a second plaque beneath the atlas sign.
    return ((points>=[-615.01,1239.99,1544.99]) &
            (points<=[-474.99,1320.01,1555.01])).all((1,2))


def clean_interior(rx):
    if len(rx.get(VERTEX))<=25:return 0
    vertices,indices=read_mesh(rx,25);tri=indices.reshape(-1,3)
    drop=medical_backing(vertices,indices)
    if int(drop.sum())!=12 or drop.all():return 0
    used,inverse=np.unique(tri[~drop],return_inverse=True)
    replace_mesh(rx,25,vertices[used],inverse.reshape(-1).astype('<u2'))
    return 12


def fit_supports(rx):
    if len(rx.get(VERTEX))<2:return 0
    vertices,indices=read_mesh(rx,1);vertices=vertices.copy();changed=0
    for center in (-545.,180.):
        points=vertices['p']
        selected=((points>=[center-66.61,1243.89,1542.59]) &
                  (points<=[center+66.61,1278.11,1545.31])).all(1)
        # One closed box, with separate face normals. Do not alter the lintel,
        # jambs, door leaves, hardware or the main printed plaque.
        if int(selected.sum())!=24 or int(selected[indices.reshape(-1,3)].all(1).sum())!=12:continue
        p=points[selected].copy()
        if not (np.allclose(p.min(0),[center-66.6,1243.9,1542.6],atol=.002) and
                np.allclose(p.max(0),[center+66.6,1278.1,1545.3],atol=.002)):continue
        p[:,0]=center+(p[:,0]-center)*66./66.6
        p[:,1]=1261.+(p[:,1]-1261.)*33./34.2
        points[selected]=p;changed+=24
    if changed:replace_mesh(rx,1,vertices,indices)
    return changed


def model_path(game,model):
    if not model.startswith(PREFIX) or model.startswith(OUTPUT):return model
    stem=Path(model).stem
    kind='interior' if stem=='interior' or stem.startswith('interior_') else 'door' if stem.startswith('exit_door_') or stem=='exit_door' else None
    if kind is None:return model
    path=Path(game)/model;stat=path.stat()
    return _model(str(Path(game).resolve()),model,stat.st_mtime_ns,stat.st_size,kind)


@lru_cache(maxsize=16)
def _model(game,model,modified,size,kind):
    game=Path(game);rx=Rx3((game/model).read_bytes())
    if not (clean_interior(rx) if kind=='interior' else fit_supports(rx)):return model
    payload=rx.build();name=OUTPUT+kind+'_'+hashlib.sha256(payload).hexdigest()[:16]+'.rx3'
    path=game/name
    if not path.is_file():
        path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_suffix('.'+str(os.getpid())+'.new');temporary.write_bytes(payload);os.replace(temporary,path)
    return name
