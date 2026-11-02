"""Validate the running career, independently of its last on-disk game graph.

FIFA adds competition nodes and standing slots while simulating. The save file
identifies the loaded career; it is not a whitelist of its current RAM rows.
"""
import json
from pathlib import Path


def read(game, saved, today, *, epoch=None, club=None):
    try:
        path = Path(game) / 'ModCarrerMode/runtime/career_fce_snapshot.json'
        if path.stat().st_size > 32 * 1024 * 1024:
            return None
        value = json.loads(path.read_text(encoding='utf8'))
        save = Path(saved['path']).resolve()
        stat = save.stat()
        expected = dict(schema=3, pid=saved['pid'],
                        processCreated100ns=saved['process_created_100ns'],
                        date=today, saveSize=stat.st_size,
                        saveWriteTime100ns=stat.st_mtime_ns // 100 + 116444736000000000)
        if any(value.get(k) != v for k, v in expected.items()):
            return None
        if Path(value['savePath']).resolve() != save:
            return None
        if epoch is not None and value.get('fceContextEpoch') != epoch:
            return None
        if club is not None and value.get('club') != club:
            return None
        if any(not isinstance(value.get(k), list) for k in ('nodes', 'fixtures', 'standings', 'stats')):
            return None
        return value
    except (OSError, ValueError, KeyError, TypeError):
        return None
