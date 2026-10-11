from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v11.cpp').read_text().replace('flamengo_v11','flamengo_v12').replace('flamengo_pyro_v11.log','flamengo_pyro_v12.log').replace('installed v11','installed v12')
s=s.replace('    uintptr_t impl=0;\n    if (!same((uintptr_t)batch', '''    if(!enabled && !stopping) return;
    bool pendingGoal=false;
    // Dormant gameplay path: no renderer validation, tree walk, or job wait.
    if(!stopping && !showing && consumed && sessionKey && cachedMatch &&
        now-lastMatchSample<2000) {
        int home=0,away=0;
        pendingGoal=read_score(home,away) && goals.update(now,home,away,clubSide);
        if(!pendingGoal) return;
    }
    uintptr_t impl=0;
    if (!same((uintptr_t)batch''')
s=s.replace('now-lastMatchSample>=500','now-lastMatchSample>=(showing || !consumed ? 500ULL : 2000ULL)')
s=s.replace('if (configured && !owned())','if (configured && (showing || !consumed) && !owned())')
s=s.replace('if (read_score(h,a) && goals.update(now,h,a,clubSide) && enabled)','if ((pendingGoal || (read_score(h,a) && goals.update(now,h,a,clubSide))) && enabled)')
s=s.replace('if (phase==0 && !faulted && !InterlockedCompareExchange','if (phase==0 && (stopping || GetTickCount64()-lastSample>=100) && !faulted && !InterlockedCompareExchange')
# Profile the sampled calls only, rather than all phase-0 frames.
(p/'flamengo_pyro_v12.cpp').write_text(s)
(p/'build_v12.cmd').write_text((p/'build_v11.cmd').read_text().replace('flamengo_pyro_v11','flamengo_pyro_v12'))
tree=E.parse(out/'flamengo_v10_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v12')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    name=g.get('name');em=next(a for a in g.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere'))
    if name.startswith('smoke'):
        setp(g,'iNumParticlesMax',350);setp(em,'iEmitRate',60)
        render=g.find("particleAction[@className='ParticleActionRender']")
        setp(render,'bUseColorMult',1)
        setp(render,'vColorMult','{ 0.055, 0.055, 0.055, 0.85 }' if name=='smoke_black' else '{ 0.7, 0.012, 0.025, 0.8 }')
    elif name=='ordinance':setp(em,'iTimeStartedMs',0)
    elif name=='burst':setp(em,'iTimeStartedMs',1800)
tree.write(out/'flamengo_v12_1043.lnx',encoding='utf-8')
(out/'flamengo_v12_1043.rx3').write_bytes((out/'flamengo_v10_1043.rx3').read_bytes())
v=(p/'verify_v11.py').read_text().replace('flamengo_v11','flamengo_v12').replace('flamengo_pyro_v11','flamengo_pyro_v12').replace('capacity<14000','capacity<27000').replace("'now-lastMatchSample>=500'","'2000ULL'")
v+='''
idle=source[source.index('// Dormant gameplay path:'):source.index('    uintptr_t impl=0;',source.index('// Dormant gameplay path:'))]
assert 'read_score(home,away)' in idle and 'if(!pendingGoal) return;' in idle
for operation in ('owned(', 'valid_slot(', 'wait_jobs(', 'match('):assert operation not in idle
assert 'pendingGoal ||' in source
print('Dormant path limited to score reads; heavy checks at most every 2s; no per-frame profiling: PASS')
'''
(p/'verify_v12.py').write_text(v)
(p/'install_v12.py').write_text((p/'install_v11.py').read_text().replace('v11_teste','v12_teste').replace('flamengo_pyro_v11','flamengo_pyro_v12').replace('flamengo_v11','flamengo_v12').replace('pyro v11','pyro v12').replace('Installed v11','Installed v12'))
print('Prepared v12: richer particles during effects; dormant gameplay score-only path')
