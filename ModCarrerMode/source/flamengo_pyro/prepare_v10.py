from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v9.cpp').read_text().replace('flamengo_v9','flamengo_v10').replace('flamengo_pyro_v9.log','flamengo_pyro_v10.log').replace('installed v9','installed v10')
s=s.replace('matrix[12]=(float)((i/2-2)*1800);','matrix[12]=(i%2==0)?-5850.0f:5850.0f;')
s=s.replace('matrix[14]=(i%2==0)?-3650.0f:3650.0f;','matrix[14]=(float)((i/2-2)*1200);')
s=s.replace('ten_emitters_paired_both_sidelines','ten_emitters_paired_behind_both_goals')
(p/'flamengo_pyro_v10.cpp').write_text(s)
(p/'build_v10.cmd').write_text((p/'build_v9.cmd').read_text().replace('flamengo_pyro_v9','flamengo_pyro_v10'))
tree=E.parse(out/'flamengo_v9_1043.lnx');tree.getroot().find('particleEffect').set('name','flamengo_v10')
tree.write(out/'flamengo_v10_1043.lnx',encoding='utf-8')
(out/'flamengo_v10_1043.rx3').write_bytes((out/'flamengo_v9_1043.rx3').read_bytes())
v=(p/'verify_v9.py').read_text().split('# Emitters must form')[0].replace('flamengo_v9','flamengo_v10').replace('flamengo_pyro_v9','flamengo_pyro_v10')
v+='''
positions=[(-5850 if i%2==0 else 5850,(i//2-2)*1200) for i in range(10)]
assert len(set(positions))==10
assert len([x for x,z in positions if x<0])==len([x for x,z in positions if x>0])==5
assert all(abs(x)>5500 and abs(z)<=2400 for x,z in positions)
for i in range(0,10,2):assert positions[i][0]==-positions[i+1][0] and positions[i][1]==positions[i+1][1]
assert 'matrix[12]=(i%2==0)?-5850.0f:5850.0f;' in source
assert 'matrix[14]=(float)((i/2-2)*1200);' in source
print('Ten unique emitters, five behind each goal, simultaneous opposed pairs: PASS')
'''
(p/'verify_v10.py').write_text(v)
(p/'install_v10.py').write_text((p/'install_v9.py').read_text().replace('v9_teste','v10_teste').replace('flamengo_pyro_v9','flamengo_pyro_v10').replace('flamengo_v9','flamengo_v10').replace('pyro v9','pyro v10').replace('Installed v9','Installed v10'))
print('Prepared v10: positions moved behind both goals; density, automatic triggers and duration unchanged')
