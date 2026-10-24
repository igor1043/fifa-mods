"""Resolve the club's actual name from its native saved teams table, read-only."""
from functools import lru_cache
from pathlib import Path
import json
from server16_py.career_read import CareerRead

@lru_cache(maxsize=8)
def _saved_name(path,size,modified,metadata,club):
    career=CareerRead(Path(path).read_bytes(),Path(metadata))
    return career.one('teams','teamid',club).GetStringField('teamname').strip()

def club_name(game,club,save=None):
    game=Path(game)
    if save:
        try:
            p=Path(save);s=p.stat()
            name=_saved_name(str(p),s.st_size,s.st_mtime_ns,str(game/'data/db/fifa_ng_db-meta.xml'),club)
            if name:return name
        except (OSError,ValueError,KeyError,RuntimeError):pass
    for relative in ('room/runtime/room_context_r46.json','room/runtime/room_header.json'):
        try:
            row=json.loads((game/'ModCarrerMode/runtime/club_environment'/relative).read_text(encoding='utf8'))
            if row.get('club')==club and (name:=row.get('club_name') or row.get('name')):return name
        except (OSError,ValueError):pass
    return 'Clube'
