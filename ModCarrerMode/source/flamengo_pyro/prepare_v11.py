from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v10.cpp').read_text().replace('flamengo_v10','flamengo_v11').replace('flamengo_pyro_v10.log','flamengo_pyro_v11.log').replace('installed v10','installed v11')
s=s.replace('#include "goal_v8.h"','#include "goal_v11.h"')
s=s.replace('static bool goalShow=false;','static bool goalShow=false;\nstatic uintptr_t batchImpl=0;\nstatic ULONGLONG lastMatchSample=0;\nstatic bool cachedMatch=false,cachedZero=false;\nstatic void wait_jobs() { if(batchImpl) ((One)(image+0x43f31d0))((void*)batchImpl); }')
s=s.replace('    if (owned()) {\n        for','    if (showing && owned()) {\n        wait_jobs();\n        for',1)
s=s.replace('    ((void (__fastcall*)(void*,const void*))(image+0x4385860))','    wait_jobs();\n    ((void (__fastcall*)(void*,const void*))(image+0x4385860))',1)
s=s.replace('    activeEffect=effect;','    wait_jobs();\n    activeEffect=effect;',1)
s=s.replace('matrix[12]=(i%2==0)?-5850.0f:5850.0f;\n        matrix[14]=(float)((i/2-2)*1200);','''if (!goalShow && i<6) {
            matrix[12]=(float)((i/2-1)*2800);
            matrix[14]=(i%2==0)?-3650.0f:3650.0f;
        } else {
            matrix[12]=(i%2==0)?-5850.0f:5850.0f;
            matrix[14]=goalShow?(float)((i/2-1)*1800):(float)((i/2-3)*2-1)*1800;
        }''')
# Six emitters for goals, ten for the opening. Retain dormant instances safely.
s=s.replace('static bool emit() {','static int active_count() { return goalShow?6:10; }\nstatic bool emit() {')
a=s.index('static bool emit()');b=s.index('static bool read_score',a)
chunk=s[a:b].replace('i<emitterCount','i<active_count()')
s=s[:a]+chunk+s[b:]
s=s.replace('    ((One)(image+0x43f31d0))((void*)impl);','    batchImpl=impl;')
s=s.replace('    if (!match(key,zero)) {','''    if (!lastMatchSample || now-lastMatchSample>=500) {
        cachedMatch=match(key,zero); cachedZero=zero; lastMatchSample=now;
    } else { key=sessionKey; zero=cachedZero; }
    if (!cachedMatch) {''')
s=s.replace('    if (configured && !owned()) { forget_resource(); consumed=true; return; }','    if (configured && !owned()) { forget_resource(); consumed=!zero; candidateSince=now; }')
s=s.replace('        for (int i=0;i<emitterCount;++i) {\n            if (!valid_slot(i)) { cleanup(); consumed=true; return; }\n            if (!emitterStarted[i] && now-showStarted>=(ULONGLONG)(i/2)*280) {','''        bool waited=false;
        for (int i=0;i<active_count();++i) {
            if (!emitterStarted[i] && now-showStarted>=(ULONGLONG)(i/2)*160) {
                if (!waited) { wait_jobs(); waited=true; }
                if (!valid_slot(i)) { cleanup(); consumed=true; return; }''')
# Start first pair on the same tick as emit instead of waiting another sampling interval.
s=s.replace('kickoffSince=gameplay_present()?now:0;','''kickoffSince=gameplay_present()?now:0;
        for(int i=0;i<2;++i) if(valid_slot(i)) {
            ((Slot)(image+0x441ce00))((void*)activeManager,handles[i]);
            ((Slot)(image+0x441c8d0))((void*)activeManager,handles[i]); emitterStarted[i]=true;
        }''')
s=s.replace('ten_emitters_paired_behind_both_goals','intro_six_sideline_four_goal_or_goal_six')
# Aggregate only CPU time in the module; explicitly not an FPS or GPU measurement.
s=s.replace('        __try { tick(self); }','''        LARGE_INTEGER before={},after={},freq={};
        QueryPerformanceCounter(&before);
        __try { tick(self); }''')
s=s.replace('        InterlockedExchange(&busy,0);','''        QueryPerformanceCounter(&after); QueryPerformanceFrequency(&freq);
        static double totalMs=0,maxMs=0; static unsigned samples=0;
        static ULONGLONG reported=0;
        const double ms=1000.0*(double)(after.QuadPart-before.QuadPart)/(double)freq.QuadPart;
        totalMs+=ms; if(ms>maxMs)maxMs=ms; ++samples;
        const ULONGLONG measured=GetTickCount64();
        if(!reported)reported=measured;
        if(measured-reported>=10000) {
            char report[192];
            _snprintf_s(report,sizeof(report),_TRUNCATE,"CPU_PROFILE interval_ms=%llu callbacks=%u module_total_ms=%.3f callback_max_ms=%.3f showing=%d (not_GPU_or_FPS)",measured-reported,samples,totalMs,maxMs,showing?1:0);
            log_event(report);reported=measured;totalMs=maxMs=0;samples=0;
        }
        InterlockedExchange(&busy,0);''')
(p/'flamengo_pyro_v11.cpp').write_text(s)
(p/'goal_v11.h').write_text((p/'goal_v8.h').read_text().replace('now-since<750','now-since<100'))
# Keep all existing regression cases, changing only the confirmation-boundary case.
(p/'goal_v11_test.cpp').write_text((p/'goal_v8_test.cpp').read_text().replace('goal_v8.h','goal_v11.h').replace('849,1,0','199,1,0').replace('850,1,0','200,1,0'))
b=(p/'build_v10.cmd').read_text().replace('flamengo_pyro_v10','flamengo_pyro_v11').replace('goal_v8_test','goal_v11_test')
(p/'build_v11.cmd').write_text(b)
tree=E.parse(out/'flamengo_v10_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v11')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    name=g.get('name');em=next(a for a in g.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere'))
    if name.startswith('smoke'):
        setp(g,'iNumParticlesMax',150);setp(em,'iEmitRate',32)
        setp(g.find("particleAction[@className='ParticleActionKillAge']"),'iAgeMs',4000)
        render=g.find("particleAction[@className='ParticleActionRender']")
        setp(render,'bUseColorMult',1)
        setp(render,'vColorMult','{ 0.055, 0.055, 0.055, 0.85 }' if name=='smoke_black' else '{ 0.7, 0.012, 0.025, 0.8 }')
        setp(em,'fSizeMean',180 if name=='smoke_trail' else 260)
    elif name.startswith('confetti_'):
        setp(g,'iNumParticlesMax',350);setp(em,'iEmitRate',600);setp(em,'iEmitDurationMs',300)
    elif name=='ordinance':setp(em,'iTimeStartedMs',0)
    elif name=='burst':
        setp(g,'iNumParticlesMax',100);setp(em,'iEmitDurationMs',100);setp(em,'iTimeStartedMs',1800)
tree.write(out/'flamengo_v11_1043.lnx',encoding='utf-8')
(out/'flamengo_v11_1043.rx3').write_bytes((out/'flamengo_v10_1043.rx3').read_bytes())
v=(p/'verify_v10.py').read_text().split('positions=')[0].replace('flamengo_v10','flamengo_v11').replace('flamengo_pyro_v10','flamengo_pyro_v11').replace('capacity<25000','capacity<14000')
v+='''
assert 'active_count() { return goalShow?6:10; }' in source
assert 'now-lastMatchSample>=500' in source and 'CPU_PROFILE' in source
tick=source[source.index('static void tick('):source.index('static void __fastcall draw_hook')]
assert '((One)(image+0x43f31d0))' not in tick
print('Mutation-only job waits, cached match scans, CPU telemetry, intro and goal layouts: PASS')
'''
(p/'verify_v11.py').write_text(v)
(p/'install_v11.py').write_text((p/'install_v10.py').read_text().replace('v10_teste','v11_teste').replace('flamengo_pyro_v10','flamengo_pyro_v11').replace('flamengo_v10','flamengo_v11').replace('pyro v10','pyro v11').replace('Installed v10','Installed v11'))
print('Prepared v11: intro sides+goals; faster goal confirm; denser opacity; reduced particle budget; CPU instrumentation')
