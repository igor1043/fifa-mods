"""Install or upgrade Cloth Motion; no UI control and no game/process launch."""
import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct

HERE=Path(__file__).resolve().parent
STUDY=Path(r'J:\mods\fifa 16\estudos fifa 16\70_CLOTH_PROTOTYPE_20261015')
MODULE_LINE=b'cloth_motion\\cloth_motion.dll'
MARKER_BEGIN=b'\t-- CLOTH_MOTION_BEGIN'
MARKER_END=b'\t-- CLOTH_MOTION_END'
VERSION='0.8.2'

def digest(data):return hashlib.sha256(data).hexdigest()

def assert_game_closed():
    kernel=C.WinDLL('kernel32',use_last_error=True)
    class PROCESS(C.Structure):
        _fields_=[('size',W.DWORD),('usage',W.DWORD),('pid',W.DWORD),('heap',C.c_size_t),
                  ('module',W.DWORD),('threads',W.DWORD),('parent',W.DWORD),('priority',W.LONG),
                  ('flags',W.DWORD),('name',W.WCHAR*260)]
    kernel.CreateToolhelp32Snapshot.argtypes=[W.DWORD,W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=W.HANDLE
    kernel.Process32FirstW.argtypes=[W.HANDLE,C.POINTER(PROCESS)]
    kernel.Process32NextW.argtypes=[W.HANDLE,C.POINTER(PROCESS)]
    kernel.CloseHandle.argtypes=[W.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle==C.c_void_p(-1).value:raise OSError('Cannot verify game process state')
    item=PROCESS();item.size=C.sizeof(item)
    try:
        found=kernel.Process32FirstW(handle,C.byref(item))
        while found:
            if item.name.lower()=='fifa16.exe':raise RuntimeError('Feche o FIFA 16 antes de instalar ou remover o modulo.')
            found=kernel.Process32NextW(handle,C.byref(item))
    finally:kernel.CloseHandle(handle)

def regular_fit(lua):
    if b'CLOTH_MOTION_BEGIN' in lua:
        if lua.count(b'CLOTH_MOTION_BEGIN')!=2:raise ValueError('Unexpected existing cloth markers')
        return lua
    pattern=rb'(?m)^([ \t]*db\.player\[idx\]\.jerseyfit = getKitFit\([^\r\n]+\)\r?\n)'
    newline=b'\r\n' if b'\r\n' in lua else b'\n'
    block=newline.join([MARKER_BEGIN,
        b'\t-- Native jersey cloth requires its matching regular render mesh.',
        b'\tdb.player[idx].jerseyfit = 0',MARKER_END,b''])
    result,count=re.subn(pattern,lambda match:match[1]+block,lua)
    if count!=2:raise ValueError(f'Expected two kit fit assignments, found {count}; no installation performed')
    return result

def remove_fit(lua):
    return re.sub(rb'(?m)^\t-- CLOTH_MOTION_BEGIN\r?\n.*?^\t-- CLOTH_MOTION_END\r?\n',b'',lua,flags=re.S)

def updated_list(data,enable):
    newline=b'\r\n' if b'\r\n' in data else b'\n'
    if enable:
        if any(line.strip().lower()==MODULE_LINE for line in data.splitlines()):return data
        return data+(b'' if not data or data.endswith(b'\n') else newline)+MODULE_LINE+newline
    return b''.join(line for line in data.splitlines(keepends=True) if line.strip().lower()!=MODULE_LINE)

def write_atomic(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f'.cloth-motion-{os.getpid()}.tmp')
    try:
        temporary.write_bytes(data)
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def configuration_payload(source,current=None,reset_disabled=False):
    """Default off; retain an explicit saved choice on subsequent upgrades."""
    value=b'0'
    if current is not None and not reset_disabled:
        text=current.decode('utf-8-sig')
        section=re.search(r'(?mis)^\s*\[cloth_motion\][^\r\n]*(?:\r?\n|$)(.*?)(?=^\s*\[|\Z)',text)
        enabled=re.search(r'(?mi)^[ \t]*enabled[ \t]*=[ \t]*([^;#\r\n]+)',section[1]) if section else None
        if enabled and enabled[1].strip()=='1':value=b'1'
    result,count=re.subn(rb'(?m)^(enabled=)[01](\r?)$',lambda m:m[1]+value+m[2],source)
    if count!=1:raise ValueError('Expected one default enabled flag in source configuration')
    return result

def verify_routing(game):
    big=game/'data_startup.big';bh=game/'data_startup.bh'
    with big.open('rb') as stream:
        header=stream.read(16)
        if header[:4] not in (b'BIG4',b'BIGF'):raise ValueError('Unsupported startup package')
        count,size=struct.unpack_from('>II',header,8)
        if count>100000 or not 16<=size<64000000:raise ValueError('Invalid startup directory')
        index=stream.read(size-16)
    at=0;found=[]
    for number in range(count):
        end=index.index(0,at+8);name=index[at+8:end].replace(b'\\',b'/').lower();at=end+1
        if name==b'data/fifarna/lua/assets/player.lua':found.append(28+20*number)
    if len(found)!=1:raise ValueError('Native player Lua route not uniquely identified')
    raw=bh.read_bytes();pos=found[0]
    if raw[pos:pos+8]!=bytes(8):raise ValueError('Player Lua external route is not enabled; no installation performed')
    return dict(file=str(bh),hash_offset=pos,hash=raw[pos:pos+8].hex())

def upgrade(manifest_path,game,plan):
    record=json.loads(manifest_path.read_text(encoding='utf-8'))
    if record.get('state')!='installed' or Path(record['game']).resolve()!=game:
        raise ValueError('Upgrade requires an installed module in this game')
    payload=[row for row in plan if row[2]=='payload']
    indexed={Path(row['path']).resolve():row for row in record['files']}
    for path,_,_ in payload:
        item=indexed[path.resolve()]
        if not path.is_file() or (path.suffix.lower()!='.ini' and digest(path.read_bytes())!=item['after_sha256']):
            raise ValueError(f'Installed payload changed since installation: {path}')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=STUDY.parent/'80_CLOTH_SHORTS_DEFAULT_OFF_20261016'/'upgrade_backups'/stamp
    backup.mkdir(parents=True)
    original_manifest=manifest_path.read_bytes();(backup/'installation_before.json').write_bytes(original_manifest)
    saved=[]
    for i,(path,data,_) in enumerate(payload):
        previous=path.read_bytes();saved_path=backup/f'{i:02d}_{path.name}';saved_path.write_bytes(previous)
        saved.append(dict(path=str(path),backup=str(saved_path),before_sha256=digest(previous),after_sha256=digest(data)))
    try:
        for path,data,_ in payload:
            write_atomic(path,data)
            if path.read_bytes()!=data:raise OSError(f'Upgrade verification failed: {path}')
            item=indexed[path.resolve()];item['after_sha256']=digest(data);item['bytes']=len(data)
        record.setdefault('upgrades',[]).append(dict(from_version=record['version'],to_version=VERSION,created_utc=stamp,files=saved))
        record['version']=VERSION;record['gameplay_validation']='pending_user_test'
        write_atomic(manifest_path,json.dumps(record,indent=2).encode('utf-8'))
    except Exception:
        for row in saved:write_atomic(Path(row['path']),Path(row['backup']).read_bytes())
        write_atomic(manifest_path,original_manifest)
        raise
    print(json.dumps(dict(state='upgraded',version=VERSION,backup=str(backup),files=saved,gameplay_validation='pending_user_test'),indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,default=Path(r'U:\fifa 16'))
    parser.add_argument('--rollback',action='store_true')
    parser.add_argument('--verify-only',action='store_true')
    parser.add_argument('--upgrade',action='store_true')
    parser.add_argument('--reset-disabled',action='store_true',help='Explicitly reset the saved cloth choice to off')
    args=parser.parse_args();game=args.game.resolve()
    if sum((args.rollback,args.verify_only,args.upgrade))>1:parser.error('Choose one operation')
    if args.reset_disabled and (args.rollback or args.verify_only):parser.error('Reset is only available during installation or upgrade')
    mods=(game/'ModCarrerMode/mods').resolve()
    if mods!=(HERE.parent.parent/'mods').resolve():raise ValueError('Game mod junction does not point to this development package')
    manifest_path=STUDY/'installation.json'
    if args.rollback:
        assert_game_closed()
        record=json.loads(manifest_path.read_text(encoding='utf-8'))
        if Path(record['game']).resolve()!=game:raise ValueError('Rollback belongs to a different installation')
        items=record['files']
        # Refuse conflicting payload edits before changing any installed files.
        for item in items:
            if item['kind']=='lua' and Path(item['path']).read_bytes().count(b'CLOTH_MOTION_BEGIN')!=2:
                raise ValueError('Lua markers changed; restore backup manually')
            if item['kind']=='payload':
                target=Path(item['path'])
                if target.suffix.lower()!='.ini' and target.exists() and digest(target.read_bytes())!=item['after_sha256']:
                    raise ValueError(f'Payload edited after installation: {target}')
        for item in reversed(items):
            target=Path(item['path'])
            if item['kind']=='list':
                write_atomic(target,updated_list(target.read_bytes(),False))
            elif item['kind']=='lua':
                current=target.read_bytes()
                if current.count(b'CLOTH_MOTION_BEGIN')!=2:raise ValueError('Lua markers changed; restore backup manually')
                write_atomic(target,remove_fit(current))
            elif item['existed']:
                write_atomic(target,Path(item['backup']).read_bytes())
            elif target.exists():target.unlink()
        record['state']='rolled_back';manifest_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
        print('Cloth Motion removido; outras entradas e edicoes foram preservadas.')
        return
    executable=game/'fifa16.exe'
    with executable.open('rb') as stream:header=stream.read(4096)
    offset=struct.unpack_from('<I',header,60)[0]
    if header[:2]!=b'MZ' or header[offset:offset+4]!=b'PE\0\0' or struct.unpack_from('<HI',header,offset+4)[0]!=0x8664:
        raise ValueError('Expected FIFA 16 x64')
    timestamp=struct.unpack_from('<I',header,offset+8)[0]
    if timestamp!=0x577de45c:raise ValueError(f'Unsupported FIFA build: {timestamp:08x}')
    route=verify_routing(game)
    player=game/'data/fifarna/lua/assets/player.lua';enabled=mods/'enabled.txt'
    dll=HERE/'build/cloth_motion.dll'
    if not dll.is_file():raise ValueError('Build the DLL before installation')
    installed_ini=mods/'cloth_motion/cloth_motion.ini'
    ini=configuration_payload((HERE/'cloth_motion.ini').read_bytes(),installed_ini.read_bytes() if installed_ini.exists() else None,args.reset_disabled)
    plan=[(mods/'cloth_motion/cloth_motion.dll',dll.read_bytes(),'payload'),
          (installed_ini,ini,'payload'),
          (mods/'cloth_motion/README.md',(HERE/'README.md').read_bytes(),'payload'),
          (player,regular_fit(player.read_bytes()),'lua'),
          (enabled,updated_list(enabled.read_bytes(),True),'list')]
    if args.verify_only:
        result={'route':route,'files':[{'path':str(path),'bytes':len(data),'already_matches':path.exists() and path.read_bytes()==data} for path,data,_ in plan]}
        print(json.dumps(result,indent=2));return
    assert_game_closed()
    if args.upgrade:
        upgrade(manifest_path,game,plan);return
    if manifest_path.exists():
        old=json.loads(manifest_path.read_text(encoding='utf-8'))
        if old.get('state')=='installed':raise ValueError('Already installed; verify or roll back before installing again')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup=STUDY/'backups'/stamp;backup.mkdir(parents=True)
    entries=[]
    for number,(path,data,kind) in enumerate(plan):
        exists=path.exists();saved=backup/f'{number:02d}_{path.name}'
        before=path.read_bytes() if exists else None
        if exists:saved.write_bytes(before)
        entries.append(dict(path=str(path),kind=kind,existed=exists,backup=str(saved) if exists else None,
                            before_sha256=digest(before) if exists else None,after_sha256=digest(data),bytes=len(data)))
    record=dict(version=VERSION,state='prepared',game=str(game),mods=str(mods),route=route,
                created_utc=stamp,gameplay_validation='pending_user_test',files=entries)
    manifest_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    written=[]
    try:
        for entry,(path,data,_) in zip(entries,plan):
            write_atomic(path,data);written.append(entry)
            if digest(path.read_bytes())!=entry['after_sha256']:raise OSError(f'Written hash mismatch: {path}')
    except Exception:
        for entry in reversed(written):
            path=Path(entry['path'])
            if entry['existed']:write_atomic(path,Path(entry['backup']).read_bytes())
            elif path.exists():path.unlink()
        record['state']='failed_restored';manifest_path.write_text(json.dumps(record,indent=2),encoding='utf-8');raise
    record['state']='installed';manifest_path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'state':'installed','dll':str(plan[0][0]),'sha256':entries[0]['after_sha256'],
                      'regular_jersey_fit_sites':2,'backup':str(backup),'gameplay_validation':'pending_user_test'},indent=2))

if __name__=='__main__':main()
