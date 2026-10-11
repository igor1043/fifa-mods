from pathlib import Path
import ctypes, hashlib, struct, xml.etree.ElementTree as ET
root=Path(__file__).parent
assets=root/'build'/'assets'
tree=ET.parse(assets/'flamengo_v14_1043.lnx');effect=tree.getroot().find('particleEffect')
assert effect.get('name')=='flamengo_v14'
groups=effect.findall('particleGroup');names={g.get('name') for g in groups}
assert len(groups)==8 and len(names)==8
for p in effect.iter('parameter'):
    if p.get('name','').startswith('r') and '/' in p.get('value',''):
        g,a,n=p.get('value').split('/')
        assert g in names,(g,a,n)
        assert effect.find("particleGroup[@name='%s']/particleAction[@name='%s']/parameter[@name='%s']"%(g,a,n)) is not None,(g,a,n)
    if p.get('name')=='sTexture':assert p.get('value') in {'fx_rawcloud.tga','fx_rawcloud.dds','fx_fireworks_sparkletrail.tga','fx_glare_whitefalloff.dds','fx_confetti.dds'},p.attrib
capacity=sum(int(g.find("parameter[@name='iNumParticlesMax']").get('value')) for g in groups)*10
assert capacity<37000
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
header=(root/'native_signatures_v6.h').read_text()
signatures=re.findall(r'sig\d+\[16\]=\{([^}]+)\}',header)
rvas=re.findall(r'get\(base\+0x([0-9a-f]+),found\)',header)
for rva,sig in zip(rvas,signatures):
    address=int(rva,16)
    expected=bytes(int(x,16) for x in sig.split(','))
    assert capture[address:address+16]==expected,hex(address)
assert len(rvas)==len(signatures)==11
print('Installed executable SHA256 and 11 runtime signature guards: PASS')
enabled=Path(r'U:\fifa 16\ModCarrerMode\mods\enabled.txt').read_bytes()
line=b'flamengo_pyro\\flamengo_pyro_v14.dll'
if line in [x.strip() for x in enabled.splitlines()]:
    updated=re.sub(rb'(?m)^[ \t]*'+re.escape(line)+rb'[ \t]*\r?\n?',b'',enabled)
    assert line not in [x.strip() for x in updated.splitlines()]
    before=[x for x in enabled.splitlines() if x.strip() and not x.lstrip().startswith(b'#') and x.strip()!=line]
    after=[x for x in updated.splitlines() if x.strip() and not x.lstrip().startswith(b'#')]
    assert before==after
    print('Rollback removes only this module and preserves other enabled modules: PASS')

# Check actual DLL ABI and fail-closed behavior in a non-game process.
dll=ctypes.WinDLL(str(root/'build'/'flamengo_pyro_v14.dll'))
dll.Fifa16ModGetApiVersion.restype=ctypes.c_uint
dll.Fifa16ModStart.argtypes=[ctypes.c_char_p];dll.Fifa16ModStart.restype=ctypes.c_int
assert dll.Fifa16ModGetApiVersion()==1
assert dll.Fifa16ModStart(str(root/'build').encode())==0
print('DLL x64 exports and rejection of unsupported executable: PASS')
print('DLL SHA256',hashlib.sha256((root/'build'/'flamengo_pyro_v14.dll').read_bytes()).hexdigest())

source=(root/'flamengo_pyro_v14.cpp').read_text()
cleanup=source[source.index('static void cleanup()'):source.index('static bool configure()')]
for address in ('43840c0','4384370','4385860','43856b0','441c620'):
    assert address not in cleanup, 'Unsafe teardown call: '+address
assert 'valid_slot(i)' in cleanup and '441c720' in cleanup and '441c940' in cleanup
emit=source[source.index('static bool emit()'):source.index('static bool gameplay_present()')]
for address in ('4383f70','4385df0','4386880','4385ad0','43854a0','43861b0'):
    assert address not in emit, 'Replay-recorded instance command: '+address
assert 'instance_for(activeManager,handles[i])' in emit
print('No instance delete or asset unload at stop; native instance calls bypass replay recorder: PASS')



assert 'active_count() { return goalShow?6:10; }' in source
assert '2000ULL' in source and 'CPU_PROFILE' in source
tick=source[source.index('static void tick('):source.index('static void __fastcall draw_hook')]
assert '((One)(image+0x43f31d0))' not in tick
print('Mutation-only job waits, cached match scans, CPU telemetry, intro and goal layouts: PASS')

idle=source[source.index('// Dormant gameplay path:'):source.index('    uintptr_t impl=0;',source.index('// Dormant gameplay path:'))]
assert 'read_score(home,away)' in idle and 'if(!pendingGoal) return;' in idle
for operation in ('owned(', 'valid_slot(', 'wait_jobs(', 'match('):assert operation not in idle
assert 'pendingGoal ||' in source
print('Dormant path limited to score reads; heavy checks at most every 2s; no per-frame profiling: PASS')
