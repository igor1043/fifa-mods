from pathlib import Path
p=Path(__file__).parent
s=(p/'verify_v5.py').read_text()
for a,b in [('flamengo_pyro_v5.dll','flamengo_pyro_v6.dll'),('flamengo_v5','flamengo_v6'),(')*36',')*6'),('capacity<10000','capacity<5000'),('native_signatures.h','native_signatures_v6.h'),('==13','==11'),('13 runtime','11 runtime')]:s=s.replace(a,b)
s=s.replace('emit=group.find("particleAction[@className=\'ParticleActionEmitBox\']")',"emit=next((a for a in group.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere')),None)")
s+='''
source=(root/'flamengo_pyro_v6.cpp').read_text()
cleanup=source[source.index('static void cleanup()'):source.index('static bool configure()')]
for address in ('43840c0','4384370','4385860','43856b0','441c620'):
    assert address not in cleanup, 'Unsafe teardown call: '+address
assert 'valid_slot(i)' in cleanup and '441c720' in cleanup and '441c940' in cleanup
emit=source[source.index('static bool emit()'):source.index('static bool gameplay_present()')]
for address in ('4383f70','4385df0','4386880','4385ad0','43854a0','43861b0'):
    assert address not in emit, 'Replay-recorded instance command: '+address
assert 'instance_for(activeManager,handles[i])' in emit
print('No instance delete or asset unload at stop; native instance calls bypass replay recorder: PASS')
'''
(p/'verify_v6.py').write_text(s)
