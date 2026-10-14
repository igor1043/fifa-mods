"""Syntax and integration audit for code-only releases, without game control."""
from pathlib import Path
import ast,configparser,json,subprocess,sys
import importlib.util

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('code_export',Path(__file__).with_name('Export-Code.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
errors=[];python_files=0
for relative in module.candidates(ROOT):
    if relative.suffix=='.py':
        try:ast.parse((ROOT/relative).read_text(encoding='utf-8-sig'),filename=str(relative));python_files+=1
        except (SyntaxError,UnicodeError) as e:errors.append(str(e))
catalog=json.loads((ROOT/'ModCarrerMode/docs/implementations.json').read_text(encoding='utf8'))
for feature in catalog['features']:
    if not (ROOT/feature['source']).exists():errors.append('Missing source: '+feature['source'])
entries=[s.strip().replace('\\','/') for s in (ROOT/'ModCarrerMode/mods/enabled.txt').read_text().splitlines() if s.strip() and not s.startswith('#')]
assert len(entries)==len(set(entries))==14
assert entries.index('entrance_props/entrance_props.dll')<entries.index('var_cabin/var_cabin.dll')
for entry in entries:
    path=ROOT/'ModCarrerMode/mods'/entry
    if not path.exists() or path.read_bytes()[:2]!=b'MZ':errors.append('Missing DLL: '+entry)
assert not (ROOT/'ModCarrerMode/mods/entrance_props/source').exists()
assert (ROOT/'ModCarrerMode/source/entrance_props/club_atlas.h').is_file()
assert (ROOT/'ModCarrerMode/source/entrance_props/crest_mesh.h').is_file()
assert (ROOT/'ModCarrerMode/mods/var_cabin/var_cabin.lua').read_bytes()==(ROOT/'ModCarrerMode/source/var_cabin/var_cabin.lua').read_bytes()
assert (ROOT/'ModCarrerMode/mods/smoke_machine/smoke_machine.lua').read_bytes()==(ROOT/'ModCarrerMode/source/smoke_machine/smoke_machine.lua').read_bytes()
configuration=configparser.ConfigParser();configuration.read(ROOT/'ModCarrerMode/config/match_presentation.ini')
assert configuration.getboolean('match','entrance_props')
for relative in ('README.md','ModCarrerMode/source/entrance_props/README.md','ModCarrerMode/source/var_cabin/README.md'):
    assert 'entrance_props_v18.dll' not in (ROOT/relative).read_text(encoding='utf8')
result={'python_sources_parsed':python_files,'features_catalogued':len(catalog['features']),'active_plugins':len(entries),'source_integration_errors':errors}
print(json.dumps(result,ensure_ascii=False,indent=2));sys.exit(bool(errors))
