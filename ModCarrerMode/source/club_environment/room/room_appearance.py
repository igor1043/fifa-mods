"""Editable club art and visual preferences for the current dressing room."""
from pathlib import Path
import copy
import json
import os
import threading
from PIL import Image

_asset_health={}

ROOT = 'ModCarrerMode/data/club_environment/current_dressing_room'
PREFERENCES = 'ModCarrerMode/data/club_environment/room/v3-settings'
CATALOG = [
    ('style', 'Estilo do vestiário', [('default','Default',112),('custom','Custom do clube',113)]),
    ('finish', 'Composição dos armários', [('light','Branco',90),('dark','Preto',91),('gray','Cinza',92),('wood','Amadeirado',93),('wood_light','Amadeirado claro',99),('custom','Custom do clube',94)]),
    ('backs', 'Fundo dos nichos', [('light','Branco',95),('dark','Preto',96),('wood','Amadeirado',97),('wood_light','Amadeirado claro',106),('custom','Custom do clube',98)]),
    ('trim', 'Contorno dos armários', [('primary','Cor primária do clube',114),('secondary','Cor secundária do clube',115),('light','Branco',116),('dark','Preto',117),('wood','Amadeirado',118),('wood_light','Amadeirado claro',119)]),
    ('floor', 'Piso', [('rubber','Emborrachado',100),('light','Claro',101),('dark','Escuro',102),('stone','Cimento',103),('wood','Amadeirado',104),('custom','Custom do clube',105)]),
    ('logo', 'Escudo do clube', [('floor','Chão',110),('ceiling','Teto',111)]),
]
CODES={code:(key,value) for key,_,options in CATALOG for value,_,code in options}
# One mailbox command carries the whole draft. The six base-8 option indices
# occupy the low digits of a monotonically increasing, exactly represented ID.
APPLY_CODE=120
SEQUENCE_STRIDE=1_000_000


def decode_draft(game,club,sequence):
    packed=sequence%SEQUENCE_STRIDE
    selected={}
    for row in rows(game,club):
        packed,index=divmod(packed,8)
        if index>=len(row['options']):raise ValueError('Invalid dressing-room option')
        selected[row['key']]=row['options'][index]['value']
    if packed:raise ValueError('Invalid dressing-room draft')
    if selected['style']=='default' and any(selected[k]=='custom' for k in ('finish','backs','floor')):
        raise ValueError('Custom material requires the club style')
    return selected


def club_folder(game,club):return Path(game)/ROOT/'custom'/str(int(club))


def custom_profile(game,club):
    path=club_folder(game,club)/'profile.json'
    try:
        payload=json.loads(path.read_text(encoding='utf8'))
        return payload if isinstance(payload,dict) else {}
    except (OSError,ValueError):return {}


def asset(game,club,key):
    folder=club_folder(game,club).resolve()
    assets=custom_profile(game,club).get('assets',{})
    value=assets.get(key) if isinstance(assets,dict) else None
    # Optional per-club safe artwork uses a predictable filename; a profile
    # may override it when an existing pack uses a different asset name.
    if key=='locker_box_front' and not isinstance(value,str):value='locker-box-front.png'
    if not isinstance(value,str):return None
    path=(folder/value).resolve()
    if not path.is_relative_to(folder) or path.suffix.lower() not in ('.png','.dds') or not path.is_file():return None
    stat=path.stat();stamp=(str(path),stat.st_mtime_ns,stat.st_size)
    if stamp not in _asset_health:
        try:
            with Image.open(path) as image:
                _asset_health[stamp]=0<image.width*image.height<=16_777_216
        except (OSError,ValueError):_asset_health[stamp]=False
    if not _asset_health[stamp]:return None
    return path


def has_custom(game,club):
    return any(asset(game,club,key) for key in ('cabinet','backing','corner','floor','feature_wall','fascia',
                                             'fascia_back_left','fascia_back_right','fascia_left','fascia_right',
                                             'wall_mural','hydration_wall','sign_medical','sign_coach','sign_water','sign_exit'))


def rows(game,club):
    result=[]
    for key,title,items in CATALOG:
        available=[item for item in items if item[0]!='custom' or
                   (has_custom(game,club) if key=='style' else asset(game,club,{'finish':'cabinet','backs':'backing','floor':'floor'}[key]))]
        result.append({'key':key,'title':title,'options':[{'value':value,'label':label,'code':code} for value,label,code in available]})
    return result


def preferences(game,club,default_finish=None):
    if default_finish is None:
        try:
            cfg=json.loads((Path(game)/'ModCarrerMode/data/club_environment/room/locker-system-v3.json').read_text(encoding='utf8'))
            default_finish=cfg['visual'].get('clubs',{}).get(str(club),{}).get('finish',cfg['visual'].get('fallback',{}).get('finish','light'))
        except (OSError,ValueError,KeyError,TypeError):default_finish='light'
    values={'style':'custom' if has_custom(game,club) else 'default','finish':default_finish,
            'backs':'dark' if default_finish=='dark' else 'light','trim':'primary','floor':'light','logo':'floor'}
    defaults=custom_profile(game,club).get('defaults',{})
    if isinstance(defaults,dict):values.update(defaults)
    path=Path(game)/PREFERENCES/f'{int(club)}.json'
    try:
        saved=json.loads(path.read_text(encoding='utf8'))
        if isinstance(saved,dict):values.update(saved)
    except (OSError,ValueError):pass
    for row in rows(game,club):
        permitted=[v['value'] for v in row['options']]
        if values.get(row['key']) not in permitted:values[row['key']]=permitted[0]
    if values['style']=='default':
        for key in ('finish','backs','floor'):
            if values[key]=='custom':values[key]='rubber' if key=='floor' else 'light'
    return values


def ui_data(game,club,default_finish='light'):
    values=preferences(game,club,default_finish)
    result=rows(game,club)
    saved_custom=values.get('_custom_choices',{})
    for row in result:
        row['selected']=next(i for i,item in enumerate(row['options']) if item['value']==values[row['key']])
        row['custom_selected']=next((i for i,item in enumerate(row['options']) if item['value']==saved_custom.get(row['key'])),row['selected'])
    return result


def stamp(game,club):
    paths=[Path(game)/PREFERENCES/f'{int(club)}.json']
    folder=club_folder(game,club)
    if folder.is_dir():paths.extend(sorted(p for p in folder.rglob('*') if p.is_file()))
    generic=Path(game)/ROOT/'generic/materials'
    if generic.is_dir():paths.extend(sorted(p for p in generic.iterdir() if p.is_file()))
    return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) if p.is_file() else (str(p),0,0) for p in paths)


def save_command(game,pid,wire):
    """Consume absolute option IDs already validated by the native event bridge."""
    parts=wire.split()
    if len(parts)!=7 or parts[:2]!=['S16ROOM','1']:return False
    try:session,club,sequence,code=int(parts[2]),int(parts[3]),int(parts[5]),int(parts[6])
    except ValueError:return False
    if session!=pid or sequence<=0 or sequence>9007199254740991 or (code not in CODES and code!=APPLY_CODE):return False
    root=Path(game)/'ModCarrerMode/runtime/club_environment/room/runtime'
    try:scope=(root/'room_control_scope.txt').read_text().split()
    except OSError:return False
    if scope!=['S16ROOMSCOPE','1',str(pid),str(club),parts[4]]:return False
    values=preferences(game,club)
    if code==APPLY_CODE:
        try:draft=decode_draft(game,club,sequence)
        except ValueError:return False
        if all(values[k]==v for k,v in draft.items()):return False
        if values['style']=='custom' and draft['style']=='default':
            values['_custom_choices']={key:values[key] for key in ('finish','backs','floor')}
        values.update(draft)
        return write_preferences(game,pid,club,parts[4],sequence,code,values)
    key,value=CODES[code]
    allowed={item['value'] for row in rows(game,club) if row['key']==key for item in row['options']}
    if value not in allowed:return False
    previous_style=values['style']
    if key=='style' and value=='default' and previous_style=='custom':
        values['_custom_choices']={other:values[other] for other in ('finish','backs','floor')}
    values[key]=value
    if key=='style' and value=='custom':
        values.update(values.get('_custom_choices',{}))
    if value=='custom' and key!='style':values['style']='custom'
    if key=='style' and value=='default':
        for other in ('finish','backs','floor'):
            if values[other]=='custom':values[other]='rubber' if other=='floor' else 'light'
    return write_preferences(game,pid,club,parts[4],sequence,code,values)


def write_preferences(game,pid,club,nonce,sequence,code,values):
    root=Path(game)/'ModCarrerMode/runtime/club_environment/room/runtime'
    path=Path(game)/PREFERENCES/f'{club}.json';path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf8');os.replace(temporary,path)
    (root/'appearance_ack.json').write_text(json.dumps({'pid':pid,'club':club,'nonce':nonce,'sequence':sequence,'code':code,'values':values}),encoding='utf8')
    return True


def start_service(game,pid,on_change=None):
    """Tiny file mailbox consumer; mesh preparation cannot block preferences."""
    stop=threading.Event()
    path=Path(game)/'ModCarrerMode/runtime/club_environment/room/runtime/room_camera_command.txt'
    def run():
        try:
            stat=path.stat();previous=(stat.st_mtime_ns,stat.st_size)
        except OSError:previous=None
        while not stop.wait(.01):
            try:
                stat=path.stat();current=(stat.st_mtime_ns,stat.st_size)
                if current==previous:continue
                wire=path.read_text();previous=current
                if save_command(game,pid,wire) and on_change:on_change()
            except (OSError,ValueError):continue
    threading.Thread(target=run,name='DressingRoomAppearance',daemon=True).start()
    return stop
