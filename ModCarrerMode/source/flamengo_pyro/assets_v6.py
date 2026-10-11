from pathlib import Path
import sys,copy,xml.etree.ElementTree as E,json
p=Path(__file__).parent;out=p/'build'/'assets';out.mkdir(exist_ok=True)
study=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010')
tree=E.parse(study/'rooffireworks_0.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v6')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name)
    if par is None:par=E.SubElement(node,'parameter',name=name,index='0')
    par.set('value',str(value))
def action(g,cls):return g.find("particleAction[@className='%s']"%cls)
groups={g.get('name'):g for g in effect.findall('particleGroup')}
black=copy.deepcopy(groups['smoke_base']);black.set('name','smoke_black')
for par in black.iter('parameter'):
    if par.get('value','').startswith('smoke_base/'):par.set('value',par.get('value').replace('smoke_base/','smoke_black/'))
effect.append(black);groups['smoke_black']=black
for name,g in groups.items():
    em=action(g,'ParticleActionEmitBox');render=action(g,'ParticleActionRender')
    for kill in list(g.findall("particleAction[@className='ParticleActionKillPlane']")):g.remove(kill)
    setp(g,'iInstancing',1)
    if name=='ordinance':
        setp(g,'iNumParticlesMax',1)
        for n,v in [('iEmitCycles',6),('iEmitDurationMs',50),('iEmitDelayMs',4450),('iTimeStartedMs',500),('iEmitRate',1000),('fSizeMean',45),('vVelocityMean','{ 80, 1180, 0 }'),('vVelocitySpread','{ 80, 110, 40 }')]:setp(em,n,v)
        setp(action(g,'ParticleActionAccelerate'),'vAcceleration','{ 35, -490, 10 }')
        setp(action(g,'ParticleActionKillAge'),'iAgeMs',2300)
        setp(render,'vColorMult','{ 2.0, 1.1, 0.6, 0.85 }')
    else:
        setp(g,'iNumParticlesMax',200 if name.startswith('smoke') else 100)
        setp(em,'iEmitCycles',1);setp(em,'iEmitDurationMs',24000);setp(em,'iEmitDelayMs',0)
        setp(em,'iEmitRate',36 if name.startswith('smoke') else 25)
        if name.startswith('smoke'):
            setp(render,'sTechnique','AlphaBlend');setp(render,'bDepthSort',1)
            setp(render,'vColorMult','{ 0.06, 0.06, 0.06, 0.5 }' if name=='smoke_black' else '{ 0.7, 0.012, 0.025, 0.45 }')
            setp(em,'fSizeMean',210 if name=='smoke_trail' else 320)
            setp(em,'fSizeSpread',100)
            setp(em,'vVelocitySpread','{ 55, 55, 30 }')
            if name!='smoke_trail':
                setp(em,'vVelocityMean','{ 60, 120, 20 }')
                setp(em,'vCenter','{ -120, 100, 0 }' if name=='smoke_black' else '{ 120, 100, 0 }')
            setp(action(g,'ParticleActionKillAge'),'iAgeMs',5500)

# Use the game's native spherical burst instead of the old cubic spray.
sky=E.parse(study/'skyfireworks_0.lnx')
sphere=sky.find(".//particleGroup[@name='burst_blue']/particleAction[@className='ParticleActionEmitSphere']")
assert sphere is not None
burst=copy.deepcopy(groups['ordinance']);burst.set('name','burst')
for a in list(burst.findall('particleAction')):
    if a.get('className') in ('ParticleActionCopyToParameter','ParticleActionEmitBox'):burst.remove(a)
em=copy.deepcopy(sphere);burst.insert(1,em)
em.find("parameter[@name='vCenter']").set('numElements','1')
for par in burst.iter('parameter'):
    if par.get('value','').startswith('ordinance/'):par.set('value',par.get('value').replace('ordinance/','burst/'))
setp(burst,'iNumParticlesMax',100)
for n,v in [('iEmitRate',1000),('fSizeMean',22),('fSizeSpread',12),('vCenter','{ 200, 1500, 0 }'),('vVelocityMean','{ 0, 0, 0 }'),('vVelocitySpread','{ 700, 700, 700 }'),('iEmitCycles',6),('iEmitDurationMs',100),('iEmitDelayMs',4400),('iTimeStartedMs',2300)]:setp(em,n,v)
setp(action(burst,'ParticleActionKillAge'),'iAgeMs',1900)
setp(action(burst,'ParticleActionAccelerate'),'vAcceleration','{ 35, -240, 10 }')
setp(action(burst,'ParticleActionRender'),'vColorMult','{ 2.0, 1.1, 0.65, 0.85 }')
effect.append(burst)
E.indent(tree,space='\t');tree.write(out/'flamengo_v6_1043.lnx',encoding='utf-8')
sys.path.insert(0,r'J:\mods\fifa 16\01_Projetos\mascotes\visualizador\tools')
from containers import big_entries
big=Path(r'U:\fifa 16\data_graphic2.big')
name,off,size=next(x for x in big_entries(big) if x[0].replace('\\','/').endswith('/rooffireworks_0.rx3'))
with big.open('rb') as f:f.seek(off);raw=f.read(size)
(out/'flamengo_v6_1043.rx3').write_bytes(raw)
report={}
for filename in ('rooffireworks_0.lnx','skyfireworks_0.lnx','breath_0.lnx'):
    t=E.parse(study/filename)
    report[filename]=[{'group':g.get('name'),'actions':[a.get('className') for a in g.findall('particleAction')],'textures':[x.get('value') for x in g.findall(".//parameter[@name='sTexture']")]} for g in t.findall('.//particleGroup')]
(study/'native_effect_variations.json').write_text(json.dumps(report,indent=2))
print('v6 capacity',sum(int(g.find("parameter[@name='iNumParticlesMax']").get('value')) for g in effect.findall('particleGroup'))*6)
image=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin').read_bytes()
rvas=[0x43f14e0,0x43f31d0,0x4385860,0x43856b0,0x4383e30,0x441bce0,0x441cd90,0x441ce00,0x441c8d0,0x441c720,0x441c940]
lines=['// Guards for every native function used by v6.','static bool check_signatures(uintptr_t base) {','    unsigned char found[16];']
for i,rva in enumerate(rvas):
    lines.append('    const unsigned char sig%d[16]={%s};'%(i,','.join('0x%02x'%x for x in image[rva:rva+16])))
    lines.append('    if (!get(base+0x%x,found) || memcmp(found,sig%d,16)) return false;'%(rva,i))
lines+=['    return true;','}']
(p/'native_signatures_v6.h').write_text('\n'.join(lines)+'\n')
