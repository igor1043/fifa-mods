from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v16.cpp').read_text().replace('flamengo_v16','flamengo_v17').replace('flamengo_pyro_v16.log','flamengo_pyro_v17.log').replace('installed v16','installed v17')
s=s.replace('#include "goal_v11.h"','#include "goal_v11.h"\n#include "lifecycle_v17.h"')
marker='static bool gameplay_present() {'
helper='''static PyroLifecycle lifecycle;
static ULONGLONG lastLifecycleSample=0;
template<size_t N> static bool chain(uintptr_t rva,const unsigned int (&offsets)[N],uintptr_t& out) {
    uintptr_t p=0;if(!get(image+rva,p) || !p)return false;
    for(size_t i=0;i+1<N;++i)if(!get(p+offsets[i],p) || !p)return false;
    out=p+offsets[N-1];return true;
}
static bool restarted(ULONGLONG now) {
    if(now-lastLifecycleSample<250)return false;lastLifecycleSample=now;
    uintptr_t stats=0,pageAddress=0;int clock=0,h=0,a=0;char page[192]={};
    const unsigned int pageOffsets[]={232,192,136,472,0};
    const bool valid=get(image+56299464,stats) && stats && get(stats+5500,clock) &&
        clock>=0 && clock<100000000 && read_score(h,a);
    bool replay=false;
    const bool pageKnown=chain(58757168,pageOffsets,pageAddress) && get(pageAddress,page);
    if(pageKnown) {
        page[sizeof(page)-1]=0;
        for(char* c=page;*c;++c)if(*c>='A' && *c<='Z')*c=(char)(*c+32);
        replay=strstr(page,"replay")!=nullptr;
    }
    return lifecycle.sample(valid,clock,h,a,!pageKnown || replay,now);
}
'''
assert marker in s;s=s.replace(marker,helper+marker)
s=s.replace('    bool pendingGoal=false;','''    if(sessionKey && restarted(now)) {
        // Ensure any old show is stopped on the render thread before resetting.
        uintptr_t impl=0;
        if(!same((uintptr_t)batch,image+0x2214500) || !get((uintptr_t)batch+0x10,impl) || !impl)return;
        batchImpl=impl;cleanup();
        goals=PyroGoals{};sessionKey=0;consumed=false;goalShow=false;
        kickoffSince=0;candidateSince=now;showStarted=0;deadline=0;
        lastMatchSample=0;cachedMatch=false;cachedZero=false;
        for(int i=0;i<emitterCount;++i)emitterStarted[i]=false;
        log_event("MATCH_RESTART_CONFIRMED reset_intro_and_goal_baseline");
    }
    bool pendingGoal=false;''',1)
# More paper on goals without another asset/manager: two additional rear cannons.
s=s.replace('active_count() { return goalShow?6:10; }','active_count() { return goalShow?8:10; }')
s=s.replace('goalShow?(float)((i/2-1)*1800)', 'goalShow?((float)(i/2)-1.5f)*1400.0f')
s=s.replace('candidateSince=now; kickoffSince=0; goals=PyroGoals{}; goalShow=false;', 'candidateSince=now; kickoffSince=0; goals=PyroGoals{}; goalShow=false; lifecycle=PyroLifecycle{};')
s=s.replace('intro_six_sideline_four_goal_or_goal_six','intro_six_sideline_four_goal_or_goal_eight')
(p/'flamengo_pyro_v17.cpp').write_text(s)
b=(p/'build_v16.cmd').read_text().replace('flamengo_pyro_v16','flamengo_pyro_v17')
b=b.replace('cl /nologo /std:c++17 /W4 /WX /O2 /MT /LD', 'cl /nologo /std:c++17 /W4 /WX /O2 /MT lifecycle_v17_test.cpp /Fobuild\\ /Febuild\\lifecycle_v17_test.exe /link /NOLOGO\nif errorlevel 1 exit /b 1\nbuild\\lifecycle_v17_test.exe\nif errorlevel 1 exit /b 1\ncl /nologo /std:c++17 /W4 /WX /O2 /MT /LD')
(p/'build_v17.cmd').write_text(b)
tree=E.parse(out/'flamengo_v16_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v17')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    if not g.get('name','').startswith('confetti_'):continue
    em=g.find("particleAction[@className='ParticleActionEmitBox']")
    setp(g,'iNumParticlesMax',1200);setp(em,'iEmitRate',2000);setp(em,'iEmitDurationMs',450);setp(em,'iEmitDelayMs',4050)
tree.write(out/'flamengo_v17_1043.lnx',encoding='utf-8')
(out/'flamengo_v17_1043.rx3').write_bytes((out/'flamengo_v16_1043.rx3').read_bytes())
v=(p/'verify_v16.py').read_text().replace('flamengo_v16','flamengo_v17').replace('flamengo_pyro_v16','flamengo_pyro_v17').replace('capacity<48000','capacity<54000').replace('return goalShow?6:10','return goalShow?8:10')
v+='''
assert 'MATCH_RESTART_CONFIRMED' in source
assert 'goals=PyroGoals{};sessionKey=0;consumed=false;goalShow=false;' in source
assert 'if(now-lastLifecycleSample<250)' in source
print('Restart resets opening, goal baseline and timers with retained validated resources: PASS')
'''
(p/'verify_v17.py').write_text(v)
(p/'install_v17.py').write_text((p/'install_v16.py').read_text().replace('v16_teste','v17_teste').replace('flamengo_pyro_v16','flamengo_pyro_v17').replace('flamengo_v16','flamengo_v17').replace('pyro v16','pyro v17').replace('Installed v16','Installed v17'))
print('Prepared v17: restart lifecycle from Server16 clock+score, replay UI guard, 8 goal emitters and more confetti')
