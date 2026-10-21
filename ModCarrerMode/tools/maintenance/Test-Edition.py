"""Regression checks for the two editions, without opening FIFA or changing saves."""
from pathlib import Path
import configparser
import hashlib
import re
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[3]
config = configparser.ConfigParser()
config.read(repo / 'ModCarrerMode/config/edition.ini', encoding='utf-8')
edition = config['edition']['id']
assert edition in ('v12', 'new-experience')
root = ET.parse(repo / 'data/ui/layout/careermanagerhubcfg.xml').getroot()
native = repo / 'ModCarrerMode/source/career_native'
nav = (repo / 'data/ui/nav/careermode/mainmenuhubflow.nav').read_text(encoding='utf-8-sig')

def tile(panel, name):
    return next(t for t in root.find(panel).findall('tile') if t.find('tileid').get('NAME') == name)

next_card = tile('panel_0', 'NEXT_MATCH_CENTRAL')
club = tile('panel_7', 'MY_TEAM_CLUB')
retirement = tile('panel_3', 'SETTINGS')
subtiles = [c for c in next_card if c.tag.startswith('subtile')]
assert int(next_card.find('number_of_subtiles').get('LENGTH')) == len(subtiles)
assert root.find('panel_7') is not None and root.find('panel_5') is not None
for required in ('MY_TEAM_LEADERS', 'MY_TEAM_CARDS', 'MY_TEAM_INJURIES', 'MY_TEAM_CLUB'):
    tile('panel_7', required)

binary = (repo / 'dinput8.dll').read_bytes()
actions = (b'FifaModsOpenRanking', b'FifaModsOpenMyOffice', b'FifaModsOpenClubPlayers', b'FifaModsOpenRetirement')
if edition == 'v12':
    assert next_card.find('settings').get('ENABLE_CYCLING') == 'TRUE'
    registered_types = {e.get('TILE_NAME') for e in root.find('hub_settings').findall('tile_path')}
    assert all(s.get('SUBTILE_TYPE') in registered_types for s in subtiles)
    assert any(s.get('DATAPROVIDERID') == 'CM_EXTENDED_NEWS_DP' for s in subtiles)
    assert len([s for s in subtiles if s.get('DATAPROVIDERID') == 'CM_DEALS_DP']) == 2
    # The full-size Central carousel must own its entire screen region.
    # Independent contextual tiles in that rectangle paint over its pages.
    bounds = next_card.find('settings')
    x, y, width, height = (int(bounds.get(k)) for k in ('X', 'Y', 'WIDTH', 'HEIGHT'))
    panel = root.find('panel_0')
    assert int(panel.find('entries').get('numberoftiles')) == len(panel.findall('tile'))
    for other in panel.findall('tile'):
        if other is next_card:
            continue
        settings = other.find('settings')
        ox, oy, ow, oh = (int(settings.get(k)) for k in ('X', 'Y', 'WIDTH', 'HEIGHT'))
        assert not (x < ox + ow and ox < x + width and y < oy + oh and oy < y + height), other.find('tileid').get('NAME')
    assert next_card.find('main_tile').get('DESTINATION') == ''
    assert club.find('main_tile').get('DESTINATION') == ''
    assert not any(e.get('DESTINATION', '').startswith('FifaModsOpen') for e in root.iter())
    assert 'FifaModsOpen' not in nav
    # V12 manages retirement in the Server16 panel; keep native Settings intact.
    assert retirement.find('main_tile').get('DESTINATION') == 'EnterGameSettings'
    assert retirement.find('number_of_subtiles').get('LENGTH') == '0'
    for event in ('RetirementRemove', 'RetirementResetAge'):
        transition = re.search(r'\{\s*"event"\s*:\s*"' + event + r'"[^{}]*\}', nav)
        assert transition and '"targets"' in transition.group(0) and event + 'Flow' in transition.group(0)
        flow = (repo / f'data/ui/nav/{event.lower()}flow.nav').read_text(encoding='utf-8')
        assert 'DoAutoSave' in flow
    for path in ('src/screens', 'src/render', 'third_party', 'src/platform/overlay'):
        assert not (native / path).exists(), path
    assert all(action not in binary for action in actions), 'New Experience action leaked into V12 DLL'
    assert not (repo / 'ModCarrerMode/career_operations_worker.exe').exists()
    retirement_source = (native / 'src/features/retirement/retirement_engine.c').read_text(encoding='utf-8')
    assert 'saia do save sem salvar' in retirement_source.lower()
else:
    assert len(subtiles) == 1 and subtiles[0].get('DESTINATION') == 'FifaModsOpenMyOffice'
    assert next_card.find('main_tile').get('DESTINATION') == 'FifaModsOpenNextMatch'
    assert club.find('main_tile').get('DESTINATION') == 'FifaModsOpenClubPlayers'
    assert retirement.find('subtile1').get('DESTINATION') == 'FifaModsOpenRetirement'
    assert all(action in binary for action in actions), 'New Experience action missing from DLL'
    for path in ('src/screens/office/my_office_view.inc', 'src/render/renderer/fifa_player_renderer.cpp'):
        assert (native / path).is_file(), path

entries = [line.strip() for line in (repo / 'ModCarrerMode/mods/enabled.txt').read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]
required_plugins = {'crowd/crowd_plugin.dll', 'subson/subson_bridge.dll', 'substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll', 'career_birthdate_2006/birthyear_range_2006_2012.dll'}
active_plugins={p.replace('\\', '/') for p in entries}
assert required_plugins <= active_plugins
if edition=='v12':
    required_v12={'mascot_single/mascot_goal_line.dll','multiball_visual/multiball_visual.dll',
                  'kickoff_modern/kickoff_modern.dll','stadium_pyrotechnics/stadium_pyrotechnics.dll',
                  'smoke_machine/smoke_machine.dll',
                  'entrance_props/entrance_props.dll','var_cabin/var_cabin.dll',
                  'career_ui_assets/career_ui_assets.dll','crowd_ultra_kits/crowd_ultra_kits.dll',
                  'tournament_compat_native/tournament_compat_native.dll',
                  'frontend_stadium/frontend_stadium_native_v11.dll',
                  'panorama_drone/panorama_drone_v5.dll',
                  'cloth_motion/cloth_motion.dll',
                  'goal_kick_short_pass/goal_kick_short_pass.dll'}
    assert active_plugins==required_plugins|required_v12
    assert not any(entry.startswith('extra_scenes/') for entry in active_plugins)
    assert entries.index('entrance_props\\entrance_props.dll')<entries.index('var_cabin\\var_cabin.dll')
for entry in entries:
    assert (repo / 'ModCarrerMode/mods' / entry.replace('\\', '/')).read_bytes()[:2] == b'MZ'
if edition == 'v12':
    frontend_config = configparser.ConfigParser()
    frontend_config.read(repo / 'ModCarrerMode/config/frontend_stadium.ini', encoding='utf-8')
    assert not frontend_config.getboolean('frontend_stadium', 'enabled')
    assert not frontend_config.has_section('frontend_stadium_clubs')
    assert (repo / 'ModCarrerMode/tools/frontend_stadium_prepare.exe').read_bytes()[:2] == b'MZ'
    for name in ('stadium.lua', 'crowd.lua'):
        assert 'server16_frontend_stadium.lua' in (repo / 'data/fifarna/lua/assets' / name).read_text(encoding='utf-8-sig')
    for slot in (176, 261):
        route = (repo / f'data/fifarna/lua/assets/server16_frontend_{slot}.lua').read_text(encoding='ascii')
        assert f'Server16FrontendRoutes[{slot}] = nil' in route
        assert 'model =' not in route
    assert '["background", "FIFA", "BOOTFLOW"]' in nav
    assert '["background", "FIFA", "BOOTFLOW"]' in (repo / 'data/ui/nav/mainfeflow.nav').read_text(encoding='utf-8-sig')
    extras_config = configparser.ConfigParser()
    extras_config.read(repo / 'ModCarrerMode/config/extra_scenes.ini', encoding='utf-8')
    assert not extras_config.getboolean('scenes', 'test_mode')
    assert not extras_config.getboolean('scenes', 'enabled')
    assert extras_config.getint('scenes', 'preview_serial') == 0
for rel in ('Server16Python.exe', 'ModCarrerMode/retirement_offline_worker.exe', 'ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe'):
    assert (repo / rel).read_bytes()[:2] == b'MZ', rel
payload = repo / 'ModCarrerMode/mods/career_birthdate_2006/payload/vpro_proinfo.big'
assert hashlib.sha256(payload.read_bytes()).hexdigest().upper() == 'B5CFF1DF25EAFE1453E11589CFD39675463DB3A63F80371C967CB47F88B342CE'
retirement_config = (repo / 'ModCarrerMode/config/career_retirement_background.ini').read_text(encoding='utf-8')
assert 'enabled=1' in retirement_config and 'defer_until_game_exit=0' in retirement_config
assert not (repo / 'dinput8_career_chain.dll').exists()
print(f'PASS: {edition}: cards, NAV, DLL edition, {len(active_plugins)} plugins and required runtime files')
