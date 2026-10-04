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
    assert not subtiles
    assert next_card.find('main_tile').get('DESTINATION') == ''
    assert club.find('main_tile').get('DESTINATION') == ''
    assert not any(e.get('DESTINATION', '').startswith('FifaModsOpen') for e in root.iter())
    assert 'FifaModsOpen' not in nav
    assert retirement.find('subtile1').get('DESTINATION') == 'RetirementRemove'
    assert retirement.find('subtile2').get('DESTINATION') == 'RetirementResetAge'
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
    assert 'Feche o FIFA completamente' in retirement_source
else:
    assert len(subtiles) == 1 and subtiles[0].get('DESTINATION') == 'FifaModsOpenMyOffice'
    assert next_card.find('main_tile').get('DESTINATION') == 'FifaModsOpenNextMatch'
    assert club.find('main_tile').get('DESTINATION') == 'FifaModsOpenClubPlayers'
    assert retirement.find('subtile1').get('DESTINATION') == 'FifaModsOpenRetirement'
    assert all(action in binary for action in actions), 'New Experience action missing from DLL'
    for path in ('src/screens/office/my_office_view.inc', 'src/render/renderer/fifa_player_renderer.cpp'):
        assert (native / path).is_file(), path

entries = [line.strip() for line in (repo / 'ModCarrerMode/mods/enabled.txt').read_text(encoding='utf-8').splitlines() if line.strip() and not line.lstrip().startswith('#')]
required_plugins = {'crowd/crowd_plugin.dll', 'bench_native12/bench_native12.dll', 'substitution_all7_rulescan_native/substitution_all7_rulescan_native.dll', 'career_birthdate_2006/birthyear_range_2006_2012.dll'}
assert {p.replace('\\', '/') for p in entries} == required_plugins
for entry in entries:
    assert (repo / 'ModCarrerMode/mods' / entry.replace('\\', '/')).read_bytes()[:2] == b'MZ'
for rel in ('Server16Python.exe', 'ModCarrerMode/retirement_offline_worker.exe', 'ModCarrerMode/mods/career_birthdate_2006/dist/Fifa16BirthdateWatcher2006.exe'):
    assert (repo / rel).read_bytes()[:2] == b'MZ', rel
payload = repo / 'ModCarrerMode/mods/career_birthdate_2006/payload/vpro_proinfo.big'
assert hashlib.sha256(payload.read_bytes()).hexdigest().upper() == 'B5CFF1DF25EAFE1453E11589CFD39675463DB3A63F80371C967CB47F88B342CE'
retirement_config = (repo / 'ModCarrerMode/config/career_retirement_background.ini').read_text(encoding='utf-8')
assert 'enabled=1' in retirement_config and 'defer_until_game_exit=1' in retirement_config
assert not (repo / 'dinput8_career_chain.dll').exists()
print(f'PASS: {edition}: cards, NAV, DLL edition, four shared plugins and required runtime files')
