"""Install only the gallery's files; preserve the other career views and modules."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,sys,xml.etree.ElementTree as ET
import psutil


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def copy(source,target,records):
    source,target=Path(source),Path(target)
    if source.resolve()==target.resolve():return
    payload=source.read_bytes();target.parent.mkdir(parents=True,exist_ok=True)
    previous=sha(target) if target.is_file() else None
    temporary=target.with_name(target.name+'.gallery-new');temporary.write_bytes(payload);os.replace(temporary,target)
    assert target.read_bytes()==payload
    records.append(dict(path=str(target),bytes=len(payload),before=previous,sha256=sha(target)))


def tree(source,target,records):
    for file in Path(source).rglob('*'):
        if file.is_file() and '__pycache__' not in file.parts and file.suffix not in ('.obj','.exp','.lib','.pyc'):
            copy(file,Path(target)/file.relative_to(source),records)


def install(game,dev,package,module,host):
    game,dev,package=map(lambda p:Path(p).resolve(),(game,dev,package))
    for process in psutil.process_iter(['name','exe']):
        if (process.info['name'] or '').lower()=='fifa16.exe' and Path(process.info['exe']).resolve().parent==game:
            raise RuntimeError('Feche o FIFA antes de instalar a biblioteca nativa')
    if not (game/'fifa16.exe').is_file():raise ValueError('Instalação do FIFA não encontrada')
    old=ET.parse(game/'data/ui/layout/careermanagerhubcfg.xml');new=ET.parse(package/'data/ui/layout/careermanagerhubcfg.xml')
    for panel in old.getroot():
        if panel.tag!='panel_7':
            assert ET.tostring(panel)==ET.tostring(new.find(panel.tag)),panel.tag
    old_club=next(t for t in old.findall('panel_7/tile') if t.find('tileid').get('NAME')=='MY_TEAM_CLUB')
    new_club=next(t for t in new.findall('panel_7/tile') if t.find('tileid').get('NAME')=='MY_TEAM_CLUB')
    assert ET.tostring(old_club.find('main_tile'))==ET.tostring(new_club.find('main_tile'))
    assert ET.tostring(old_club.find('subtile1'))==ET.tostring(new_club.find('subtile1'))
    assert new_club.find('subtile2').get('DESTINATION')=='Server16EnterTrophyRoom'
    records=[];source=dev/'ModCarrerMode/source/club_environment/trophy_room'
    tree(source,game/'ModCarrerMode/source/club_environment/trophy_room',records)
    support=['ModCarrerMode/source/career_native/src/host/career_bank_input.inc',
             'ModCarrerMode/source/career_native/src/host/career_background_refresh.inc',
             'ModCarrerMode/source/club_environment/room/prepare_native_room_components_r46_20261022.py',
             'ModCarrerMode/source/career_native/tests/providers/test_career_bank_mail.c',
             'ModCarrerMode/source/career_native/tests/providers/test_background_refresh_queue.c','README.md']
    for rel in support:copy(dev/rel,game/rel,records)
    # The generated static room already lives in the game; mirror only this room.
    for rel in ('data/sceneassets/server16_trophy_room','ModCarrerMode/data/trophy_room'):
        tree(game/rel,dev/rel,records)
    for root in (game,dev):
        tree(package,root,records)
        copy(module,root/'ModCarrerMode/mods/trophy_room/trophy_room.dll',records)
        copy(host,root/'dinput8.dll',records)
        enabled=root/'ModCarrerMode/mods/enabled.txt';text=enabled.read_text(encoding='utf8')
        entry='trophy_room\\trophy_room.dll'
        if entry not in text.replace('/','\\'):
            enabled.write_text(text.rstrip()+'\n\n# Native club trophy gallery.\n'+entry+'\n',encoding='utf8')
    assert sha(game/'dinput8.dll')==sha(dev/'dinput8.dll')
    report=dict(schema=1,feature='trophy_room',records=records,menu='Meu time > Clube > Sala de troféus',
                custom_wall=str(game/'ModCarrerMode/data/trophy_room/custom/1043/identity-wall.png'),
                save_writes=False,database_writes=False,game_visual_validation=False)
    path=game/'ModCarrerMode/runtime/trophy_room/install.json';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    return path


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('game','dev','package','module','host'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();print(install(a.game,a.dev,a.package,a.module,a.host))
