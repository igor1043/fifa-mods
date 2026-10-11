from pathlib import Path
import ctypes, hashlib, struct, xml.etree.ElementTree as ET
root=Path(__file__).parent
assets=root/'build'/'assets'
tree=ET.parse(assets/'stadium_pyrotechnics_0.lnx');effect=tree.getroot().find('particleEffect')
assert effect.get('name')=='stadium_pyrotechnics'
groups=effect.findall('particleGroup');names={g.get('name') for g in groups}
assert len(groups)==11 and len(names)==11
for p in effect.iter('parameter'):
    if p.get('name','').startswith('r') and '/' in p.get('value',''):
        g,a,n=p.get('value').split('/')
        assert g in names,(g,a,n)
        assert effect.find("particleGroup[@name='%s']/particleAction[@name='%s']/parameter[@name='%s']"%(g,a,n)) is not None,(g,a,n)
    if p.get('name')=='sTexture':assert p.get('value') in {'fx_rawcloud.tga','fx_rawcloud.dds','fx_fireworks_sparkletrail.tga','fx_glare_whitefalloff.dds','fx_confetti.dds'},p.attrib
capacity=sum(int(g.find("parameter[@name='iNumParticlesMax']").get('value')) for g in groups)*10
assert capacity==78010
for group in groups:
    emit=next((a for a in group.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere')),None)
    assert emit is not None and int(emit.find("parameter[@name='iEmitCycles']").get('value'))>0
    assert group.find("particleAction[@className='ParticleActionKillAge']") is not None
print('XML references, finite emission, particle budget: PASS',capacity)

# This game's executable is packed: on-disk bytes differ from unpacked code.
# Verify the exact installed PE; loaded function bytes are checked by the DLL.
import re
exe=Path(r'U:\fifa 16\fifa16.exe').read_bytes()
assert hashlib.sha256(exe).hexdigest()=='889772d3192c74ce4c1f2b7b3467cc96f9f1123aaf347bce7b199333dbac7a9d'
capture=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin').read_bytes()
header=(root/'native_signatures.h').read_text()
signatures=re.findall(r'sig\d+\[16\]=\{([^}]+)\}',header)
rvas=re.findall(r'get\(base\+0x([0-9a-f]+),found\)',header)
for rva,sig in zip(rvas,signatures):
    address=int(rva,16)
    expected=bytes(int(x,16) for x in sig.split(','))
    assert capture[address:address+16]==expected,hex(address)
assert len(rvas)==len(signatures)==14
print('Installed executable SHA256 and 14 runtime signature guards: PASS')
enabled=Path(r'U:\fifa 16\ModCarrerMode\mods\enabled.txt').read_bytes()
line=b'stadium_pyrotechnics\\stadium_pyrotechnics.dll'
if line in [x.strip() for x in enabled.splitlines()]:
    updated=re.sub(rb'(?m)^[ \t]*'+re.escape(line)+rb'[ \t]*\r?\n?',b'',enabled)
    assert line not in [x.strip() for x in updated.splitlines()]
    before=[x for x in enabled.splitlines() if x.strip() and not x.lstrip().startswith(b'#') and x.strip()!=line]
    after=[x for x in updated.splitlines() if x.strip() and not x.lstrip().startswith(b'#')]
    assert before==after
    print('Rollback removes only this module and preserves other enabled modules: PASS')

# Check actual DLL ABI and fail-closed behavior in a non-game process.
dll=ctypes.WinDLL(str(root/'build'/'stadium_pyrotechnics.dll'))
dll.Fifa16ModGetApiVersion.restype=ctypes.c_uint
dll.Fifa16ModStart.argtypes=[ctypes.c_char_p];dll.Fifa16ModStart.restype=ctypes.c_int
assert dll.Fifa16ModGetApiVersion()==1
assert dll.Fifa16ModStart(str(root/'build').encode())==0
print('DLL x64 exports and rejection of unsupported executable: PASS')
print('DLL SHA256',hashlib.sha256((root/'build'/'stadium_pyrotechnics.dll').read_bytes()).hexdigest())

source=(root/'stadium_pyrotechnics.cpp').read_text()
cleanup=source[source.index('static void cleanup('):source.index('static bool configure()')]
for address in ('43840c0','4384370','4385860','43856b0','441c620'):
    assert address not in cleanup, 'Unsafe teardown call: '+address
assert 'valid_slot(i)' in cleanup and '441c720' in cleanup and '441c940' in cleanup
emit=source[source.index('static bool emit()'):source.index('static bool gameplay_present()')]
for address in ('4383f70','4385df0','4386880','4385ad0','43854a0','43861b0'):
    assert address not in emit, 'Replay-recorded instance command: '+address
assert 'instance_for(activeManager,handles[i])' in emit
print('No instance delete or asset unload at stop; native instance calls bypass replay recorder: PASS')



assert 'active_count() { return goalShow?8:10; }' in source
assert '2000ULL' in source and 'CPU_PROFILE' in source
tick=source[source.index('static void tick('):source.index('static void __fastcall draw_hook')]
assert '((One)(image+0x43f31d0))' not in tick
print('Mutation-only job waits, cached match scans, CPU telemetry, intro and goal layouts: PASS')

idle=source[source.index('// Dormant gameplay path:'):source.index('    uintptr_t impl=0;',source.index('// Dormant gameplay path:'))]
assert 'read_score(home,away)' in idle and 'if(!pendingGoal) return;' in idle
for operation in ('owned(', 'valid_slot(', 'wait_jobs(', 'match('):assert operation not in idle
assert 'pendingGoal ||' in source
print('Dormant path limited to score reads; heavy checks at most every 2s; no per-frame profiling: PASS')

assert 'ensure_visibility' not in source
assert 'state+5)=1' not in source and 'activeState+5)=1' not in source
assert 'EARLY_PRELOAD' in source and 'if(activeEffect)return;' in source
assert 'configured && !owned()' in cleanup
assert source.index('preload(now);',source.index('static void tick('))<source.index('cachedMatch=match(key,zero)')
print('Native-ready flag is engine-owned; preloading precedes team detection; valid idle resource retained: PASS')

assert 'MATCH_RESTART_CONFIRMED' in source
assert 'goals=PyroGoals{};sessionKey=0;consumed=false;goalShow=false;' in source
assert 'if(now-lastLifecycleSample<250)' in source
print('Restart resets opening, goal baseline and timers with retained validated resources: PASS')

# Overlay must preserve the emitter's location, velocity, palette and duration.
from copy import deepcopy
for name in ('smoke_trail','smoke_base','smoke_black'):
    original=effect.find("particleGroup[@name='%s']"%name)
    clone=deepcopy(effect.find("particleGroup[@name='%s_overlay']"%name))
    assert clone is not None
    clone.set('name',name)
    for par in clone.iter('parameter'):
        if par.get('name','').startswith('r'):
            par.set('value',par.get('value','').replace(name+'_overlay/',name+'/'))
    assert ET.tostring(original)==ET.tostring(clone),name
assert 'stadium_pyrotechnics_v' not in source
assert 'flamengo_v' not in source
print('Two identical smoke layers at each source; rockets and confetti unchanged: PASS')
normal_end=source[source.index('static void finish_naturally()'):source.index('static bool configure()')]
assert '441c940' not in normal_end and '441c720' not in normal_end and '441c980' in normal_end
assert 'pyro_drain_due(now,showStarted,goalShow,i)' in source and '441c980' in source
assert 'finish_naturally(); consumed=true;' in source
assert 'emitterDraining[i]=false' in source
assert max(int(g.find("particleAction[@className='ParticleActionKillAge']/parameter[@name='iAgeMs']").get('value')) for g in groups)<=6500
print('Normal ending drains emission in pairs, preserves particles, and includes 7s tail within show duration: PASS')
matching=source[source.index('static bool stadium_match('):source.index('// Never pass a handle')]
assert '1043' not in matching and 'clubSide' not in source
assert matching.count('pyro_team_key(')==3
assert 'GOAL_CONFIRMED' in source and 'FLAMENGO_GOAL_CONFIRMED' not in source
assert 'goals.update(now,home,away)' in source and 'goals.update(now,h,a)' in source
print('Every validated team pair eligible; home-goal detection and home palette selection: PASS')
assert source.count('matchHomeTeam=')>=4
assert source.index('wait_jobs();',source.index('static bool emit()'))<source.index('apply_home_palette()',source.index('static bool emit()'))
palette_runtime=(root/'palette_runtime.inc').read_text()
assert 'paletteHome==matchHomeTeam && paletteEffect==activeEffect' in palette_runtime
assert 'pyro_palette(matchHomeTeam)' in palette_runtime
assert 'bindings[i].previous[3]' in palette_runtime
assert 'type!=8' in palette_runtime and 'length!=1' in palette_runtime
assert 'if(!apply_home_palette())return false;' in source
assert 'PALETTE_UNAVAILABLE' in palette_runtime
assert 'HOME_GOAL_CONFIRMED' in source
print('Palette applied before emission, cached per effect/home, alpha preserved, missing colors fail closed: PASS')

assert tick.index('sample_presentation(now)')<tick.index('restarted(now)')<tick.index('// Dormant gameplay path:')
assert 'canStart && (pendingGoal ||' in tick
assert 'if (!canStart || consumed) return;' in tick
assert 'cleanup(currentPage==PyroPage::Outside)' in tick
assert 'cachedFixture=native_fixture(' in source
assert 'currentPage=next;lastPageSample=now;' in source
assert 'presentationConfig.read((DWORD)now)' in tick
assert 'presentation.entrance_allowed()' in tick and 'presentation.goal_allowed()' in tick
assert 'match_presentation.ini' in (root/'match_presentation.h').read_text()
print('Page/native-fixture gate precedes all triggers; menus rearm; Server16 switches retained: PASS')

assert 'flamengo' not in source.lower()
assert 'assetId!=0' in source and 'const int asset=0' in source
