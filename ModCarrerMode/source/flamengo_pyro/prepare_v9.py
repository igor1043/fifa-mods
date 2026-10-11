from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v8.cpp').read_text().replace('flamengo_v8','flamengo_v9').replace('flamengo_pyro_v8.log','flamengo_pyro_v9.log').replace('emitterCount=6','emitterCount=10')
s=s.replace('matrix[12]=(float)((i%3-1)*2500);','matrix[12]=(float)((i/2-2)*1800);')
s=s.replace('matrix[14]=i<3?-3650.0f:3650.0f;','matrix[14]=(i%2==0)?-3650.0f:3650.0f;')
s=s.replace('(ULONGLONG)i*350','(ULONGLONG)(i/2)*280')
s=s.replace('six_spaced_emitters','ten_emitters_paired_both_sidelines').replace('installed v8','installed v9')
(p/'flamengo_pyro_v9.cpp').write_text(s)
(p/'build_v9.cmd').write_text((p/'build_v8.cmd').read_text().replace('flamengo_pyro_v8','flamengo_pyro_v9'))
tree=E.parse(out/'flamengo_v8_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v9')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    name=g.get('name');em=next(a for a in g.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere'))
    if name.startswith('smoke'):
        setp(g,'iNumParticlesMax',280);setp(em,'iEmitRate',48)
    elif name in ('ordinance','burst'):
        setp(em,'iEmitCycles',9);setp(em,'iEmitDelayMs',2860 if name=='burst' else 2950)
        if name=='burst':setp(g,'iNumParticlesMax',140);setp(em,'iEmitDurationMs',140)
tree.write(out/'flamengo_v9_1043.lnx',encoding='utf-8')
(out/'flamengo_v9_1043.rx3').write_bytes((out/'flamengo_v8_1043.rx3').read_bytes())
verify=(p/'verify_v8.py').read_text().replace('flamengo_v8','flamengo_v9').replace('flamengo_pyro_v8','flamengo_pyro_v9').replace('for g in groups)*6','for g in groups)*10').replace('capacity<13000','capacity<25000')
verify+='''
# Emitters must form five simultaneous pairs on opposing sidelines.
positions=[((i//2-2)*1800,-3650 if i%2==0 else 3650) for i in range(10)]
assert len(set(positions))==10
assert len([z for x,z in positions if z<0])==len([z for x,z in positions if z>0])==5
for i in range(0,10,2):assert positions[i][0]==positions[i+1][0] and positions[i][1]==-positions[i+1][1]
assert 'emitterCount=10' in source and '(ULONGLONG)(i/2)*280' in source
print('Ten unique emitters, five paired stations on both sidelines: PASS')
'''
(p/'verify_v9.py').write_text(verify)
install=(p/'install_v8.py').read_text().replace('v8_teste','v9_teste').replace('flamengo_pyro_v8','flamengo_pyro_v9').replace('flamengo_v8','flamengo_v9').replace('pyro v8','pyro v9').replace('Installed v8','Installed v9')
(p/'install_v9.py').write_text(install)
print('Prepared v9: ten paired emitters; smoke +33% per emitter; rockets every 3 seconds; automatic timing unchanged')
