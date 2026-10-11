from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v13.cpp').read_text().replace('flamengo_v13','flamengo_v14').replace('flamengo_pyro_v13.log','flamengo_pyro_v14.log').replace('installed v13','installed v14')
s=s.replace('#include "timing_v6.h"','#include "timing_v14.h"').replace('durationMs=30000','durationMs=60000')
s=s.replace('goalShow ? (now<showStarted || now-showStarted>=8000) : pyro_expired(now,showStarted,kickoffSince)','pyro_show_expired(now,showStarted,goalShow)')
s=s.replace('max_ms=30000 kickoff_tail_ms=8000','intro_ms=60000 goal_ms=25000 test_extended')
(p/'flamengo_pyro_v14.cpp').write_text(s)
b=(p/'build_v13.cmd').read_text().replace('flamengo_pyro_v13','flamengo_pyro_v14').replace('timing_v6_test','timing_v14_test')
(p/'build_v14.cmd').write_text(b)
tree=E.parse(out/'flamengo_v13_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v14')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    name=g.get('name');em=next(a for a in g.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere'))
    if name.startswith('smoke'):
        setp(g,'iNumParticlesMax',500);setp(em,'iEmitRate',90);setp(em,'iEmitDurationMs',60000)
    elif name=='sparkle_trail':setp(em,'iEmitDurationMs',60000)
    elif name.startswith('confetti_'):
        setp(g,'iNumParticlesMax',900);setp(em,'iEmitRate',1400);setp(em,'iEmitCycles',14)
    elif name in ('ordinance','burst'):
        setp(em,'iEmitCycles',20)
        if name=='burst':setp(g,'iNumParticlesMax',200);setp(em,'iEmitDurationMs',200);setp(em,'iEmitDelayMs',2800)
tree.write(out/'flamengo_v14_1043.lnx',encoding='utf-8')
(out/'flamengo_v14_1043.rx3').write_bytes((out/'flamengo_v13_1043.rx3').read_bytes())
(p/'verify_v14.py').write_text((p/'verify_v13.py').read_text().replace('flamengo_v13','flamengo_v14').replace('flamengo_pyro_v13','flamengo_pyro_v14').replace('capacity<27000','capacity<37000'))
install=(p/'install_v13.py').read_text().replace('v13_teste','v14_teste').replace('flamengo_pyro_v13','flamengo_pyro_v14').replace('flamengo_v13','flamengo_v14').replace('pyro v13','pyro v14').replace('Installed v13','Installed v14').replace('maximo 30s; ate 8s depois da deteccao do gameplay.','Teste: abertura 60s; gols 25s.').replace('max 30 seconds.','opening 60 seconds; goals 25 seconds.')
(p/'install_v14.py').write_text(install)
print('Prepared v14: opening 60s regardless of kickoff, goal 25s; sustained larger smoke and bursts')
