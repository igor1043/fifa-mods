from pathlib import Path
import copy, sys, struct, xml.etree.ElementTree as E
p=Path(__file__).parent
study=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010')
out=p/'build'/'assets'
sys.path.insert(0,r'J:\mods\fifa 16\01_Projetos\mascotes\visualizador\tools')
from containers import big_entries
from rx3 import Rx3, TEXTURE, NAME
tree=E.parse(out/'flamengo_v6_1043.lnx')
effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v7')
native=E.parse(study/'confetticannon_0.lnx').find(".//particleGroup[@name='one_color']")
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name)
    if par is None:par=E.SubElement(node,'parameter',name=name,index='0')
    par.set('value',str(value))
for name,color,offset in [('confetti_primary','{ 0.85, 0.012, 0.025, 1 }',-70),('confetti_secondary','{ 0.035, 0.035, 0.035, 1 }',70)]:
    g=copy.deepcopy(native);g.set('name',name)
    for par in g.iter('parameter'):
        if par.get('value','').startswith('one_color/'):
            par.set('value',par.get('value').replace('one_color/',name+'/'))
    setp(g,'iNumParticlesMax',650)
    em=g.find("particleAction[@className='ParticleActionEmitBox']")
    # One local origin, six transformed cannons; do not retain the native +/-500 origins.
    for par in list(em.findall("parameter[@name='vCenter']")):
        if par.get('index')!='0':em.remove(par)
    for key,value in [('vCenter',f'{{ {offset}, 80, 0 }}'),('vDimensions','{ 30, 30, 30 }'),('iAgeSpreadMs',0),('iEmitRate',900),('iEmitCycles',6),('iEmitDurationMs',350),('iEmitDelayMs',4150),('iTimeStartedMs',0),('fSizeMean',10),('fSizeSpread',4),('vVelocityMean','{ 75, 1100, 0 }'),('vVelocitySpread','{ 340, 250, 320 }')]:setp(em,key,value)
    setp(g.find("particleAction[@className='ParticleActionKillAge']"),'iAgeMs',4300)
    setp(g.find("particleAction[@className='ParticleActionAccelerate']"),'vAcceleration','{ 35, -400, 15 }')
    render=g.find("particleAction[@className='ParticleActionRender']")
    for key,value in [('bUseColorMult',1),('vColorMult',color),('vColorMultSpread','{ 0, 0, 0, 0 }'),('iUseCustomColor',0),('fFadeDistance',100),('bDepthSort',1)]:setp(render,key,value)
    effect.append(g)
E.indent(tree,space='\t');tree.write(out/'flamengo_v7_1043.lnx',encoding='utf-8')
# RX3 texture dictionary: preserve all roof textures and append native confetti texture,
# together with its matching 16-byte texture descriptor and name, in the same order.
roof=Rx3((out/'flamengo_v6_1043.rx3').read_bytes())
big=Path(r'U:\fifa 16\data_graphic2.big')
_,off,size=next(x for x in big_entries(big) if x[0].replace('\\','/').endswith('/confetticannon_0.rx3'))
with big.open('rb') as f:f.seek(off);conf=Rx3(f.read(size))
assert roof.version==conf.version
header_type=0x6bd085dc
rh=next(s for s in roof.sections if s[0]==header_type)
ch=next(s for s in conf.sections if s[0]==header_type)
assert struct.unpack_from('<I',rh[1])[0]==len(roof.get(TEXTURE))==3
assert len(rh[1])==16+16*3 and len(ch[1])==16+16*3
conf_names=[n for t,n in conf.names() if t==TEXTURE]
idx=conf_names.index('fx_confetti')
tex=[s for s in conf.sections if s[0]==TEXTURE][idx]
rh[1]=struct.pack('<I',4)+rh[1][4:]+ch[1][16+16*idx:32+16*idx]
roof.sections.insert(next(i for i,s in enumerate(roof.sections) if s[0]==NAME),copy.deepcopy(tex))
roof.set_names(roof.names()+[(TEXTURE,'fx_confetti')])
raw=roof.build();(out/'flamengo_v7_1043.rx3').write_bytes(raw)
check=Rx3(raw)
assert len(check.get(TEXTURE))==len(check.names())==4
assert check.get(TEXTURE)[-1]==tex[1]
assert check.get(header_type)[0][64:80]==ch[1][16+16*idx:32+16*idx]
source=(p/'flamengo_pyro_v6.cpp').read_text().replace('flamengo_v6','flamengo_v7').replace('flamengo_pyro_v6.log','flamengo_pyro_v7.log').replace('installed v6','installed v7 confetti_red_black').replace('SHOW_STARTED six_spaced_emitters','SHOW_STARTED confetti_red_black six_spaced_emitters')
(p/'flamengo_pyro_v7.cpp').write_text(source)
(p/'build_v7.cmd').write_text((p/'build_v6.cmd').read_text().replace('flamengo_pyro_v6','flamengo_pyro_v7'))
verify=(p/'verify_v6.py').read_text().replace('flamengo_v6','flamengo_v7').replace('flamengo_pyro_v6','flamengo_pyro_v7').replace('len(groups)==6 and len(names)==6','len(groups)==8 and len(names)==8').replace("'fx_glare_whitefalloff.dds'","'fx_glare_whitefalloff.dds','fx_confetti.dds'").replace('capacity<5000','capacity<13000')
(p/'verify_v7.py').write_text(verify)
install=(p/'install_v6.py').read_text().replace('v6_teste','v7_teste').replace('flamengo_pyro_v6','flamengo_pyro_v7').replace('flamengo_v6','flamengo_v7').replace('pyro v6','pyro v7').replace('Installed v6','Installed v7')
(p/'install_v7.py').write_text(install)
print('v7: 8 groups, 4 validated texture descriptors; confetti 2 colors x 315 papers x 6 cannons per volley, 6 volleys; maximum capacity',sum(int(g.find("parameter[@name='iNumParticlesMax']").get('value')) for g in effect.findall('particleGroup'))*6)
