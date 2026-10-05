"""Save-derived club data and static renders from the native FIFA 16 renderer."""
from __future__ import annotations

import hashlib
import configparser
import re
import struct
import subprocess
import tempfile
import datetime, os, sys
from pathlib import Path

from PIL import Image

ATTRIBUTE_FIELDS = (
    'acceleration', 'sprintspeed', 'agility', 'reactions', 'balance', 'shotpower',
    'finishing', 'longshots', 'volleys', 'penalties', 'vision', 'crossing',
    'shortpassing', 'longpassing', 'curve', 'freekickaccuracy', 'ballcontrol',
    'dribbling', 'strength', 'stamina', 'jumping', 'aggression', 'interceptions',
    'positioning', 'marking', 'standingtackle', 'slidingtackle', 'headingaccuracy',
    'gkdiving', 'gkhandling', 'gkkicking', 'gkpositioning', 'gkreflexes', 'potential',
)
APPEARANCE_FIELDS = (
    'headtypecode', 'headclasscode', 'hairtypecode', 'haircolorcode', 'skintonecode',
    'skintypecode', 'facialhairtypecode', 'facialhaircolorcode', 'shoetypecode',
    'shoedesigncode', 'gender', 'height', 'weight', 'bodytypecode', 'eyecolorcode',
    'eyebrowcode', 'sideburnscode', 'jerseysleevelengthcode', 'jerseyfit',
    'jerseystylecode', 'socklengthcode', 'shortstyle', 'gkglovetypecode',
)
POSITION_LABELS = (
    'GOL', 'LIB', 'ALA D', 'LD', 'ZAG D', 'ZAG', 'ZAG E', 'LE', 'ALA E',
    'VOL D', 'VOL', 'VOL E', 'MD', 'MC D', 'MC', 'MC E', 'ME', 'MEI D',
    'MEI', 'MEI E', 'SA D', 'SA', 'SA E', 'PD', 'ATA D', 'ATA', 'ATA E', 'PE',
)


def _value(row, key, default=0):
    value = row.get(key, default)
    return default if value is None else value


def _display_name(player, names, edited):
    custom = edited.get(player['playerid'], {})
    for key in ('playerjerseyname', 'commonname'):
        if custom.get(key):
            return custom[key]
    common = names.get(player.get('commonnameid')) if player.get('commonnameid') else ''
    if common:
        return common
    first = custom.get('firstname') or names.get(player.get('firstnameid'), '')
    last = custom.get('surname') or names.get(player.get('lastnameid'), '')
    return ' '.join(part for part in (first, last) if part) or f"Jogador {player['playerid']}"


def _pitch(slot):
    points = (
        (.50, .91), (.50, .79), (.90, .66), (.84, .75), (.67, .75), (.50, .75),
        (.33, .75), (.16, .75), (.10, .66), (.67, .61), (.50, .61), (.33, .61),
        (.86, .48), (.67, .48), (.50, .48), (.33, .48), (.14, .48), (.67, .34),
        (.50, .34), (.33, .34), (.67, .23), (.50, .23), (.33, .23), (.86, .15),
        (.67, .10), (.50, .10), (.33, .10), (.14, .15),
    )
    return points[slot]


def _line(slot):
    if slot == 0:
        return 6
    if slot == 1:
        return 5
    if 2 <= slot <= 8:
        return 4
    if 9 <= slot <= 11:
        return 3
    if 12 <= slot <= 16:
        return 2
    if 17 <= slot <= 22:
        return 1
    return 0


def _layout_starters(rows):
    grouped = {}
    for slot, player in rows:
        grouped.setdefault(_line(slot), []).append((_pitch(slot)[0], slot, player))
    result = {}
    bands = sorted(grouped, reverse=True)
    for rank, band in enumerate(bands):
        members = sorted(grouped[band])
        spread = min(.8, .32 * (len(members) - 1))
        for column, (_, slot, player) in enumerate(members):
            x = .5 if len(members) == 1 else .5 + spread * (column / (len(members) - 1) - .5)
            y = .13 + .77 * rank / max(1, len(bands) - 1)
            result[slot] = (x, y)
    # The written formation is the count of occupied native pitch bands,
    # from the back line through the forward line, with the keeper omitted.
    shape = [len(grouped[band]) for band in bands if band != 6]
    formation = '-'.join(str(n) for n in shape) if shape else ''
    return result, formation


def _manager_name(manager, game, club_id):
    if manager:
        first = str(manager.get('firstname') or '').strip()
        last = str(manager.get('surname') or '').strip()
        if first.casefold() in {'téc.', 'tec.', 'coach', 'manager'}:
            first = ''
        name = ' '.join(part for part in (first, last) if part)
        if name:
            return name
    fallback = game / 'ModCarrerMode/data/catalogs/club_manager_fallback.tsv'
    try:
        for line in fallback.read_text(encoding='utf-8-sig').splitlines():
            fields = line.split('|')
            if len(fields) >= 2 and fields[0].strip() == str(club_id):
                return fields[1].strip()
    except OSError:
        pass
    return ''


def _coach_identity(mod_root, club_id, name, base_db):
    identity = {}
    source = mod_root / 'data/catalogs/coach_identity.tsv'
    try:
        for line in source.read_text(encoding='utf-8-sig').splitlines():
            fields = line.strip().split('|')
            if len(fields) != 3 or fields[0].strip() != str(club_id):
                continue
            if fields[1].strip().casefold() != name.casefold():
                continue
            try:
                nation_id = int(fields[2].strip())
            except ValueError:
                continue
            nations = {row['nationid']: row for row in base_db.rows(
                'nations', ['nationid', 'nationname', 'isocountrycode'])}
            nation = nations.get(nation_id)
            if nation:
                identity = {
                    'country': nation.get('nationname') or '',
                    'countryCode': nation.get('isocountrycode') or '',
                    'nationId': nation_id,
                }
            break
    except OSError:
        pass
    return identity


def _kit_image(root,game,club,kind,variant=0):
    source=game/'data/ui/imgAssets/kits'/f'j{kind}_{club}_{variant}.dds'
    if not source.is_file():source=game/'data/ui/imgAssets/kits'/f'j{kind}_{club}_0.dds'
    if not source.is_file():return ''
    target=root/'assets/kits'/f'{club}-{kind}-{variant}.webp';target.parent.mkdir(parents=True,exist_ok=True)
    try:
        with Image.open(source) as original:
            image=original.convert('RGBA');image.thumbnail((500,500),Image.Resampling.LANCZOS);image.save(target,format='WEBP',quality=90)
        return target.relative_to(root).as_posix()
    except (OSError,ValueError):return ''


def _stadium_image(root, game, club_id):
    key = '';physical_name=''
    settings = game / 'FSW/settings.ini'
    if settings.is_file():
        config = configparser.ConfigParser(interpolation=None)
        try:
            config.read(settings, encoding='utf-8-sig')
            key = config.get('stadium', str(club_id), fallback='').split(',', 1)[0].strip()
        except (configparser.Error, OSError):
            key = ''
    if not key:
        fallback = game / 'ModCarrerMode/data/catalogs/club_stadium_fallback.tsv'
        try:
            for line in fallback.read_text(encoding='utf-8-sig').splitlines():
                fields = line.split('|')
                if len(fields) >= 5 and fields[0].strip() == str(club_id):
                    key = fields[4].strip();physical_name=fields[3].strip()
                    break
        except OSError:
            pass
    folder = game / 'StadiumGBD/render/thumbnail/stadium'
    if not key and physical_name:
        import unicodedata
        normalize=lambda text:''.join(c for c in unicodedata.normalize('NFD',text.casefold()) if not unicodedata.combining(c))
        name=normalize(physical_name.split(' - ')[0].strip())
        if len(name)>=6:
            matches=[path for path in folder.glob('*') if name in normalize(path.stem)]
            if len(matches)==1:key=matches[0].stem
    if not key:return ''
    keys = [key]
    stripped = re.sub(r'\d+$', '', key).rstrip(' _-')
    if stripped and stripped != key:
        keys.append(stripped)
    target = root / 'assets/stadiums' / f'{club_id}.webp'
    for candidate in keys:
        for ext in ('.png', '.jpg', '.jpeg', '.dds'):
            source = folder / f'{candidate}{ext}'
            if not source.is_file():
                continue
            try:
                with Image.open(source) as original:
                    image = original.convert('RGB')
                    image.thumbnail((720, 360), Image.Resampling.LANCZOS)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target, format='WEBP', quality=80, method=4)
                return target.relative_to(root).as_posix()
            except (OSError, ValueError):
                continue
    return ''


def _pack_fixture(club_id, club_name, team, player_rows, lineup_rows, names, edited):
    output = bytearray(struct.pack('<8sIII128s', b'C3DQA003', len(lineup_rows), club_id, 420,
                                   club_name.encode('utf-8')[:127].ljust(128, b'\0')))
    color = tuple(int(_value(team, f'teamcolor1{channel}')) for channel in 'rgb')
    packed_color = (color[0] << 16) | (color[1] << 8) | color[2]
    captain = int(_value(team, 'captainid', -1))
    for slot, link in lineup_rows:
        player = player_rows[link['playerid']]
        appearance = [int(_value(player, field, -1)) for field in APPEARANCE_FIELDS]
        if appearance[11] < 130 or appearance[11] > 230:
            raise ValueError(f"Altura incompatível no jogador {player['playerid']}")
        attributes = [int(_value(player, field, -1)) for field in ATTRIBUTE_FIELDS]
        name = _display_name(player, names, edited)
        name_bytes = name.encode('utf-8')[:127]
        while name_bytes:
            try:
                name_bytes.decode('utf-8')
                break
            except UnicodeDecodeError:
                name_bytes = name_bytes[:-1]
        number = int(_value(link, 'jerseynumber', 0))
        secondary = [int(_value(player, f'preferredposition{i}', -1)) for i in (2, 3, 4)]
        row = [int(player['playerid']), club_id, number,
               int(_value(player, 'preferredposition1', -1)), -1,
               int(_value(player, 'overallrating', -1)), *appearance]
        output.extend(struct.pack('<29i4I34i128s6i', *row, packed_color, packed_color,
                                  packed_color, 1, *attributes,
                                  name_bytes.ljust(128, b'\0'),
                                  int(player['playerid'] == captain), int(slot), *secondary, 1))
    return bytes(output)


def _render_native_assets(root, career_native, game, club_id, club_name, team,
                          player_rows, lineup_rows, names, edited, roster_links, asset_revision=None):
    if len(lineup_rows) != 11 or len({row['playerid'] for _, row in lineup_rows}) != 11:
        return {}
    target_dir = root / 'assets' / 'runtime-cache' / 'renders' / str(asset_revision) if asset_revision else root / 'assets'
    lineup_target = target_dir / 'lineups' / f'{club_id}.webp'
    coach_portrait_target = target_dir / 'coaches' / f'{club_id}-portrait.webp'
    coach_model_target = target_dir / 'coaches' / f'{club_id}-3d.webp'
    script = career_native / 'scripts/previews/build_club_details_preview.cmd'
    installed_executable=root / 'native/generate_club_details_preview.exe'
    if not script.is_file() and not installed_executable.is_file():
        return {}
    try:
        fixture_bytes = _pack_fixture(club_id, club_name, team, player_rows,
                                      lineup_rows, names, edited)
        with tempfile.TemporaryDirectory(prefix='fifa-club-detail-') as temp:
            temp = Path(temp)
            fixture = temp / 'lineup.bin'
            raw_paths = [temp / 'lineup.png', temp / 'coach-portrait.png', temp / 'coach-3d.png']
            fixture.write_bytes(fixture_bytes)
            roster_fixture=temp / 'roster.bin'
            roster_fixture.write_bytes(_pack_fixture(club_id,club_name,team,player_rows,[(int(_value(link,'position',29)),link) for link in roster_links if link['playerid'] in player_rows],names,edited))
            flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
            executable = career_native / 'build/previews/generate_club_details_preview/generate_club_details_preview.exe'
            if not script.is_file():executable=installed_executable
            dependencies=[career_native / 'tools/previews/web_model_export.h',career_native / 'tools/previews/web_model_worker.h',career_native / 'tools/previews/generate_club_details_preview.cpp', career_native / 'src/render/scenes/new_experience_rooms.cpp', career_native / 'src/render/renderer/fifa_player_renderer.cpp', script]
            if script.is_file() and (not executable.is_file() or executable.stat().st_mtime < max(p.stat().st_mtime for p in dependencies)):
                compiled = subprocess.run(['cmd.exe', '/d', '/c', script.name],
                    cwd=script.parent, capture_output=True, text=True,
                    encoding='utf-8', errors='replace', timeout=180, creationflags=flags)
                if compiled.returncode:
                    raise OSError((compiled.stdout + compiled.stderr)[-1500:])
            command = [str(executable), str(game), str(fixture),
                       *(str(path) for path in raw_paths), str(temp), str(roster_fixture)]
            result = subprocess.run(command, cwd=script.parent if script.is_file() else root, capture_output=True,
                                    text=True, encoding='utf-8', errors='replace',
                                    timeout=180, creationflags=flags)
            if result.returncode:
                print('Native 3D preview incompleta:', (result.stdout + result.stderr).strip()[-900:])
            outputs = {}
            for source, target in zip(raw_paths, (lineup_target, coach_portrait_target, coach_model_target)):
                if not source.is_file():
                    continue
                with Image.open(source) as rendered:
                    image = rendered.convert('RGBA')
                    image.thumbnail((1500, 720) if 'lineups' in target.parts else (620, 760),
                                    Image.Resampling.LANCZOS)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target, format='WEBP', quality=87, method=5)
                outputs['lineup' if target == lineup_target else
                        'coachPortrait' if target == coach_portrait_target else 'coachModel'] = target.relative_to(root).as_posix()
            for kind in ('press', 'locker', 'gym', 'training'):
                source = temp / f'{kind}.png'
                if source.is_file():
                    target = target_dir / 'rooms' / f'{club_id}-{kind}.webp'
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with Image.open(source) as image:
                        image.save(target, format='WEBP', quality=90, method=5)
                    outputs[kind] = target.relative_to(root).as_posix()
            for source in (temp / 'players').glob('*.png'):
                target=target_dir / 'player-models' / f'{club_id}-{source.stem}.webp'
                target.parent.mkdir(parents=True,exist_ok=True)
                with Image.open(source) as image:
                    box=image.convert('RGBA').getchannel('A').getbbox();image.crop(box or (0,0,image.width,image.height)).save(target,format='WEBP',quality=88,method=5)
            return outputs
    except (OSError, ValueError, struct.error, subprocess.TimeoutExpired) as error:
        print(f'Native 3D preview não gerada para o clube {club_id}: {error}')
        return {}


def build_detail(root, career_native, game, saved_db, base_db, club_id,
                 saved_manager=None, history_records=None, render_native=True, asset_revision=None):
    if not club_id or not {'teams', 'teamplayerlinks', 'players'} <= saved_db.tables.keys():
        return None
    fields = ['teamid', 'teamname', 'domesticprestige', 'attackrating', 'midfieldrating',
              'defenserating', 'overallrating', 'teamcolor1r', 'teamcolor1g', 'teamcolor1b',
              'captainid']
    team = next((row for row in saved_db.rows('teams', fields) if row['teamid'] == club_id), None)
    if not team:
        return None

    link_fields = ['teamid', 'playerid', 'position', 'jerseynumber']
    roster_links = [row for row in saved_db.rows('teamplayerlinks', link_fields)
                    if row['teamid'] == club_id]
    lineup_rows = sorted(((row['position'], row) for row in roster_links
                          if row['playerid'] and row['position'] is not None
                          and 0 <= row['position'] <= 27), key=lambda pair: pair[0])
    if len(lineup_rows) != 11 or len({slot for slot, _ in lineup_rows}) != 11 or \
            len({row['playerid'] for _, row in lineup_rows}) != 11:
        lineup_rows = []
    player_ids = {row['playerid'] for row in roster_links if row['playerid']}
    player_fields = ['playerid', 'commonnameid', 'firstnameid', 'lastnameid',
                     'birthdate', 'playerjointeamdate', 'overallrating', 'preferredposition1', 'preferredposition2',
                     'preferredposition3', 'preferredposition4', 'nationality', 'preferredfoot', *APPEARANCE_FIELDS,
                     *ATTRIBUTE_FIELDS]
    player_rows = {row['playerid']: row for row in saved_db.rows('players', player_fields)
                   if row['playerid'] in player_ids}
    base_names = {row['nameid']: row['name'] for row in
                  base_db.rows('playernames', ['nameid', 'name'])}
    if 'dcplayernames' in saved_db.tables:
        base_names.update({row['nameid']: row['name'] for row in
                           saved_db.rows('dcplayernames', ['nameid', 'name']) if row['name']})
    edited = {}
    if 'editedplayernames' in saved_db.tables:
        edited = {row['playerid']: row for row in saved_db.rows(
            'editedplayernames', ['playerid', 'firstname', 'surname', 'commonname', 'playerjerseyname'])}

    def display(player):
        return _display_name(player, base_names, edited)

    slots, formation = _layout_starters(lineup_rows) if lineup_rows else ({}, '')
    def player_image(player_id, bounds=(160, 160)):
        source = game / 'data/ui/imgAssets/heads' / f'p{player_id}.dds'
        target = root / 'assets/players' / f'{player_id}.webp'
        if target.is_file():
            return target.relative_to(root).as_posix()
        if not source.is_file():
            return ''
        try:
            with Image.open(source) as original:
                image = original.convert('RGBA')
                image.thumbnail(bounds, Image.Resampling.LANCZOS)
                target.parent.mkdir(parents=True, exist_ok=True)
                image.save(target, format='WEBP', quality=82, method=4)
            return target.relative_to(root).as_posix()
        except (OSError, ValueError):
            return ''

    starters = []
    for slot, link in lineup_rows:
        player = player_rows.get(link['playerid'])
        if not player:
            continue
        x, y = slots[slot]
        starters.append({
            'id': player['playerid'], 'slot': slot, 'name': display(player),
            'position': POSITION_LABELS[slot], 'overall': _value(player, 'overallrating'),
            'portrait': player_image(player['playerid']), 'x': x, 'y': y,
        })
    if len(starters) != 11:
        starters = []
        formation = ''

    roster_ids = set(player_rows)
    ratings = [row for row in player_rows.values() if row.get('overallrating') is not None]
    highlights = []
    for player in sorted(ratings, key=lambda row: row['overallrating'], reverse=True)[:5]:
        position = int(_value(player, 'preferredposition1', -1))
        highlights.append({
            'id': player['playerid'], 'name': display(player),
            'position': POSITION_LABELS[position] if 0 <= position < len(POSITION_LABELS) else 'JOG',
            'overall': player.get('overallrating') or 0,
            'portrait': player_image(player['playerid']),
        })

    name = str(team.get('teamname') or '')
    native_assets = _render_native_assets(root, career_native, game, club_id, name,
                                          team, player_rows, lineup_rows, base_names, edited, roster_links, asset_revision) if render_native else {}
    for key,path in [('lineup',f'assets/lineups/{club_id}.webp'),('coachPortrait',f'assets/coaches/{club_id}-portrait.webp'),('coachModel',f'assets/coaches/{club_id}-3d.webp'),*[(key,f'assets/rooms/{club_id}-{key}.webp') for key in ('press','locker','gym','training')]]:
        if asset_revision:
            path=path.replace('assets/',f'assets/runtime-cache/renders/{asset_revision}/',1)
        if (root/path).is_file():native_assets.setdefault(key,path)

    coach_name = _manager_name(saved_manager, game, club_id)
    coach_identity = _coach_identity(game / 'ModCarrerMode', club_id, coach_name, base_db) if coach_name else {}
    coach_photo = ''
    coach_photo_dir = game / 'ModCarrerMode/portraits/coaches'
    for suffix in ('.png', '.jpg', '.jpeg', '.dds'):
        source = coach_photo_dir / f'club_{club_id}{suffix}'
        if source.is_file():
            target = root / 'assets/coaches' / f'{club_id}-photo.webp'
            try:
                with Image.open(source) as original:
                    image = original.convert('RGBA')
                    image.thumbnail((420, 520), Image.Resampling.LANCZOS)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    image.save(target, format='WEBP', quality=85, method=4)
                coach_photo = target.relative_to(root).as_posix()
                break
            except (OSError, ValueError):
                continue
    if not coach_photo:
        coach_photo = native_assets.get('coachPortrait', '')
    coach = {
        'name': coach_name,
        'country': coach_identity.get('country', ''),
        'countryCode': coach_identity.get('countryCode', ''), 'nationId':coach_identity.get('nationId'),
        'photo': coach_photo,
        'photoKind': 'official' if coach_photo and coach_photo.endswith('-photo.webp') else 'game-model-render',
        'model': native_assets.get('coachModel', ''),
        'modelKind': 'native-static-render',
        'confidence':saved_manager.get('boardconfidence') if saved_manager else None,
    }

    stadium_id = next((row['stadiumid'] for row in base_db.rows(
        'teamstadiumlinks', ['teamid', 'stadiumid']) if row['teamid'] == club_id), None)
    stadium = None
    if stadium_id:
        stadium_row = next((row for row in base_db.rows(
            'stadiums', ['stadiumid', 'name', 'capacity']) if row['stadiumid'] == stadium_id), None)
        if stadium_row:
            stadium = {'id': stadium_id, 'name': stadium_row['name'],
                       'capacity': stadium_row['capacity'],
                       'image': _stadium_image(root, game, club_id)}

    kit_rows = [row for row in base_db.rows(
        'teamkits', ['teamtechid', 'teamkitid', 'teamkittypetechid', 'year',
                     'teamcolorprimr', 'teamcolorprimg', 'teamcolorprimb',
                     'teamcolorsecr', 'teamcolorsecg', 'teamcolorsecb',
                     'teamcolortertr', 'teamcolortertg', 'teamcolortertb'])
        if row['teamtechid'] == club_id]
    # Some FIFA metadata calls the final channel "teamcolortertb"; keep the
    # field list exactly aligned with that installed database spelling.
    kits = []
    for kind, label in ((2, 'Goleiro'), (0, 'Mandante'), (1, 'Visitante')):
        candidates = [row for row in kit_rows if row['teamkittypetechid'] == kind]
        if not candidates:
            continue
        kit = next((row for row in candidates if row['year'] == 0), candidates[0])
        kits.append({
            'id': kit['teamkitid'], 'name': label, 'image':_kit_image(root,game,club_id,kind,kit.get('year') or 0),
            'primary': [kit['teamcolorprimr'], kit['teamcolorprimg'], kit['teamcolorprimb']],
            'secondary': [kit['teamcolorsecr'], kit['teamcolorsecg'], kit['teamcolorsecb']],
            'tertiary': [kit['teamcolortertr'], kit['teamcolortertg'], kit['teamcolortertb']],
        })

    history = []
    for row in history_records or []:
        if row.get('teamid') != club_id:
            continue
        history.append({
            'season': int(_value(row, 'season', -1)) + 1,
            'leagueId': _value(row, 'leagueid', 0),
            'games': _value(row, 'games_played'), 'wins': _value(row, 'wins'),
            'draws': _value(row, 'draws'), 'losses': _value(row, 'losses'),
            'goalsFor': _value(row, 'goals_for'), 'goalsAgainst': _value(row, 'goals_against'),
            'points': _value(row, 'points'),
            'tablePosition': row.get('tableposition') if _value(row, 'tableposition', 0) > 0 else None,
            'leagueTrophies': _value(row, 'leaguetrophies'),
            'domesticTrophies': _value(row, 'domesticcuptrophies'),
            'continentalTrophies': _value(row, 'continentaltrophies'),
        })
    history.sort(key=lambda item: item['season'], reverse=True)
    season = history[0] if history else None
    nations={row['nationid']:row['nationname'] for row in base_db.rows('nations',['nationid','nationname'])}
    links_by_id={row['playerid']:row for row in roster_links}
    career_date=None
    try:
        import birthdate_editor
        cfg=configparser.ConfigParser();cfg.read(root/'clubes.ini',encoding='utf-8-sig')
        path=Path(os.environ['USERPROFILE'])/'Documents/FIFA 16/0/FIFA16'/cfg['fifa']['sample_save_slot']/'DATA'
        data=path.read_bytes()
        for database in birthdate_editor.find_databases(data):
            raw_date=birthdate_editor.current_date_value(data,database)
            if raw_date:career_date=datetime.datetime.strptime(str(raw_date),'%Y%m%d').date();break
    except (OSError,ValueError,KeyError,ImportError):pass
    profile_players=[]
    for row in sorted(player_rows.values(),key=lambda row:_value(row,'overallrating'),reverse=True):
        pid=row['playerid'];position=int(_value(row,'preferredposition1',-1));model=(root / 'assets/runtime-cache/renders' / asset_revision / 'player-models' if asset_revision else root / 'assets/player-models') / f'{club_id}-{pid}.webp'
        profile_players.append({'id':pid,'name':display(row),'overall':_value(row,'overallrating'),'position':POSITION_LABELS[position] if 0<=position<len(POSITION_LABELS) else 'JOG','portrait':player_image(pid),'model':model.relative_to(root).as_posix() if model.is_file() else '', 'height':_value(row,'height',-1),'weight':_value(row,'weight',-1),'foot':_value(row,'preferredfoot',0),'potential':_value(row,'potential',-1),'number':_value(links_by_id.get(pid,{}),'jerseynumber',0),'nationName':nations.get(row.get('nationality'),'') or '', 'squadPosition':links_by_id.get(pid,{}).get('position'), 'nationId':row.get('nationality'), 'positionId':position, 'secondaryPositionIds':[row.get(f'preferredposition{i}') for i in (2,3,4) if row.get(f'preferredposition{i}') is not None and 0<=row[f'preferredposition{i}']<28], 'secondaryPositions':[POSITION_LABELS[row[f'preferredposition{i}']] for i in (2,3,4) if row.get(f'preferredposition{i}') is not None and 0<=row[f'preferredposition{i}']<28], 'attributes':{key:_value(row,key,-1) for key in ATTRIBUTE_FIELDS}})
    for p in profile_players:
        row=player_rows[p['id']]
        raw=row.get('birthdate')
        if raw is not None and 0<=raw<=1048575:
            born=datetime.date(1582,10,14)+datetime.timedelta(days=raw)
            if 1900<=born.year<=2500:
                p['birthDate']=born.strftime('%d/%m/%Y')
                if career_date:p['age']=career_date.year-born.year-((career_date.month,career_date.day)<(born.month,born.day))
        raw=row.get('playerjointeamdate')
        if raw is not None and 0<=raw<=1048575:
            joined=datetime.date(1582,10,14)+datetime.timedelta(days=raw)
            if joined.year>=1900:p['joinDate']=joined.strftime('%d/%m/%Y')
    memberships=saved_db.rows('leagueteamlinks',['teamid','leagueid','secondarytable']) if 'leagueteamlinks' in saved_db.tables else []
    leagues={row['leagueid']:row for row in base_db.rows('leagues',['leagueid','leaguename','level'])}
    active_leagues=[leagues[row['leagueid']] for row in memberships if row['teamid']==club_id and not row.get('secondarytable') and row['leagueid'] in leagues]
    if active_leagues:coach['league']=min(active_leagues,key=lambda row:row.get('level') or 99).get('leaguename')
    colors = [team.get('teamcolor1r'), team.get('teamcolor1g'), team.get('teamcolor1b')]
    return {
        'clubId': club_id, 'name': name,
        'overall': team.get('overallrating') or 0,
        'reputation': team.get('domesticprestige') or 0,
        'attack': team.get('attackrating') or 0,
        'midfield': team.get('midfieldrating') or 0,
        'defense': team.get('defenserating') or 0,
        'primary': colors, 'starters': starters, 'formation': formation,
        'lineupScene': native_assets.get('lineup', ''),
        'rooms': {key: native_assets.get(key, '') for key in ('press', 'locker', 'gym', 'training')},
        'highlights': highlights,
        'players': profile_players,
        'coach': coach, 'season': season, 'history': history,
        'competitions':[{'root':entry['leagueid'],'asset':entry['leagueid'],'name':entry['leaguename'],'games':0,'wins':0,'draws':0,'losses':0,'recorded':False} for entry in {entry['leagueid']:entry for entry in active_leagues}.values()],
        'stadium': stadium, 'kits': kits,
    }
