"""Shared installation paths; no drive letters, usernames or external runtimes."""
from pathlib import Path
import os,sys
import server16_py

GAME=Path(os.environ['SERVER16_GAME_ROOT']).resolve()
SOURCES=GAME/'ModCarrerMode/source/club_environment'
BASE=GAME/'ModCarrerMode/runtime/club_environment'
ROOM=BASE/'room';BANK=BASE/'bank';PREVIEW=BASE/'preview'
OFFSETS=Path(server16_py.__file__).resolve().parent/'offsets.json'
FONTS=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
for path in (ROOM/'runtime',ROOM/'assets',BANK/'runtime',PREVIEW/'runtime'):
    path.mkdir(parents=True,exist_ok=True)

def session_process():
    import psutil
    if '--pid' in sys.argv:
        process=psutil.Process(int(sys.argv[sys.argv.index('--pid')+1]))
        if process.name().casefold()=='fifa16.exe' and Path(process.exe()).resolve().parent==GAME:return process
        raise RuntimeError('Sessao do FIFA nao pertence a esta instalacao')
    matches=[]
    for process in psutil.process_iter(['name','exe']):
        try:
            if (process.info['name'] or '').casefold()=='fifa16.exe' and process.info['exe'] and Path(process.info['exe']).resolve().parent==GAME:matches.append(process)
        except (psutil.NoSuchProcess,psutil.AccessDenied):continue
    if len(matches)!=1:raise RuntimeError('Nenhuma sessao unica do FIFA nesta instalacao')
    return matches[0]

_index=None
_priority=('data_patch.big','data_front_end.big','data_graphic1_extra.big','data_graphic2_extra.big','data_graphic3_extra.big','data_graphic1.big','data_graphic2.big','data_graphic3.big','data_front_end_extra.big','data_default.big','data/ui/imgAssets/heads/2dheads0_extra.big','data/ui/imgAssets/heads/2dheads0.big')

def read_asset(relative):
    """Read loose files first, otherwise only the requested BIG entry, not its archive."""
    from containers import big_entries,unpack
    global _index
    relative=str(relative).replace('\\','/');path=GAME/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:raise ValueError('Asset outside game')
    if path.is_file():return path.read_bytes()
    if _index is None:
        _index={}
        for archive in _priority:
            file=GAME/archive
            if not file.is_file():continue
            for name,offset,length in big_entries(file):
                _index.setdefault(name.replace('\\','/').casefold(),(file,offset,length))
    entry=_index.get(relative.casefold())
    if entry is None:raise FileNotFoundError(relative)
    archive,offset,length=entry
    if not 0<length<=128*1024*1024 or offset+length>archive.stat().st_size:raise ValueError('Invalid BIG entry')
    with archive.open('rb') as handle:handle.seek(offset);blob=handle.read(length)
    return unpack(blob) if blob[:2]==b'\x10\xfb' or blob[:8] in (b'chunkzip',b'chunkref') else blob

def materialize(relative):
    """Provide a cached file for native APT image embedding and DDS decoders."""
    import hashlib
    direct=GAME/relative
    if direct.is_file():return direct
    data=read_asset(relative)
    target=BASE/'asset_cache'/hashlib.sha256(relative.casefold().encode()).hexdigest()[:20]/Path(relative).name
    if not target.exists():
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    return target
