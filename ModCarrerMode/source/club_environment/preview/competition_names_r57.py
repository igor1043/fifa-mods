import portable_paths as portable
"""Competition labels from the installed FIFA language database; read only."""
from pathlib import Path
import xml.etree.ElementTree as ET,json
from functools import lru_cache

@lru_cache(maxsize=1)
def language_names():
    import projection as p
    root=portable.GAME;db=root/'data/loc/por_br.db';meta=root/'data/loc/por_br-meta.xml'
    stamp=[db.stat().st_mtime_ns,db.stat().st_size];cache=portable.PREVIEW/'runtime/competition_labels_r57.json'
    try:
        state=json.loads(cache.read_text(encoding='utf8'))
        if state['stamp']==stamp and state.get('revision')==3:return state['names']
    except (OSError,KeyError,ValueError):pass
    from server16_py.fifa_db import _find_python32,_find_dll
    import subprocess
    output=subprocess.run([str(_find_python32()),str(Path(__file__).with_name('competition_names_worker_r57.py')),str(_find_dll()),str(db),str(meta)],capture_output=True,check=True,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
    names=json.loads(output.stdout)
    cache.write_text(json.dumps({'revision':3,'stamp':stamp,'names':names},ensure_ascii=False),encoding='utf8');return names

def competition_name(ident,rows):
    labels=language_names()
    for key in (f'TrophyName_{ident}',f'TrophyName_Abbr15_{ident}',f'LeagueName_{ident}',f'LEAGUE_NAME_{ident}',f'CompetitionName_{ident}',f'TournamentName_{ident}'):
        if labels.get(key) and '\ufffd' not in labels[key]:return labels[key]
    # Several legacy localizations store accented single-byte text. The
    # installed presentation catalog also names these custom competitions.
    from server16_py.competition_catalog import nodes,settings_text
    import configparser,re
    game=portable.GAME;objects=nodes(game);matches=[node for node,row in objects.items() if row[0]==3 and row[1]=='C'+str(ident)]
    if len(matches)==1:
        ini=configparser.ConfigParser(strict=False,interpolation=None);ini.read_string(settings_text(game/'FSW/settings.ini'))
        for section in ('comp','movies'):
            name=ini.get(section,str(matches[0]),fallback='').strip()
            if name and '\ufffd' not in name:return re.sub(r'^[A-Z]{2,5}\s*-\s*','',name).replace('***','').strip()
    for row in rows('leagues'):
        if 'leagueid' in row.fields and row.value('leagueid')==ident:
            for field in ('leaguename','name'):
                if field in row.fields and row.value(field):return str(row.value(field))
    return 'Calendário da carreira' if not ident else 'Competição da carreira'
