from pathlib import Path
import copy, struct, sys, xml.etree.ElementTree as ET

root=Path(__file__).parent
study=Path(r'J:\mods\fifa 16\estudos fifa 16\19_FLAMENGO_PYRO_20261010')
out=root/'build'/'assets'
out.mkdir(parents=True,exist_ok=True)
image=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin').read_bytes()
rvas=[0x43f14e0,0x43f31d0,0x4385860,0x43856b0,0x4383e30,0x4383f70,0x43840c0,0x4384370,0x4385df0,0x4385ad0,0x43854a0,0x4386880,0x43861b0]
lines=['// Generated from the independently captured supported executable.','static bool check_signatures(uintptr_t base) {','    unsigned char found[16];']
for n,rva in enumerate(rvas):
    sig=image[rva:rva+16]
    assert len(sig)==16 and any(sig)
    lines.append('    const unsigned char sig%d[16]={%s};'%(n,','.join('0x%02x'%x for x in sig)))
    lines.append('    if (!get(base+0x%x,found) || memcmp(found,sig%d,16)) return false;'%(rva,n))
lines+=['    return true;','}']
(root/'native_signatures.h').write_text('\n'.join(lines)+'\n')

tree=ET.parse(study/'rooffireworks_0.lnx')
effect=tree.getroot().find('particleEffect')
effect.set('name','flamengo_v5')
def setp(node,name,value):
    p=node.find("parameter[@name='%s']"%name)
    if p is None:p=ET.SubElement(node,'parameter',name=name,index='0')
    p.set('value',str(value))
groups={g.get('name'):g for g in effect.findall('particleGroup')}
black=copy.deepcopy(groups['smoke_base']);black.set('name','smoke_black')
for p in black.iter('parameter'):
    if p.get('value','').startswith('smoke_base/'):
        p.set('value',p.get('value').replace('smoke_base/','smoke_black/'))
effect.append(black)
groups['smoke_black']=black
for name,g in groups.items():
    emit=g.find("particleAction[@className='ParticleActionEmitBox']")
    for kill in list(g.findall("particleAction[@className='ParticleActionKillPlane']")):g.remove(kill)
    if name=='ordinance':
        setp(g,'iNumParticlesMax',2)
        setp(emit,'iEmitCycles',62);setp(emit,'iEmitDurationMs',100);setp(emit,'iEmitDelayMs',1300)
        setp(emit,'fSizeMean',110);setp(emit,'vVelocityMean','{ 0, 1250, 0 }')
    else:
        setp(g,'iNumParticlesMax',60 if name in ('smoke_trail','sparkle_trail') else 35)
        setp(emit,'iEmitRate',24 if name=='smoke_trail' else 18 if name=='sparkle_trail' else 12)
        setp(emit,'iEmitCycles',1);setp(emit,'iEmitDurationMs',86000);setp(emit,'iEmitDelayMs',0)
        setp(g,'iInstancing',1)
        if name.startswith('smoke'):
            render=g.find("particleAction[@className='ParticleActionRender']")
            setp(render,'sTechnique','AlphaBlend');setp(render,'bDepthSort',1)
            setp(render,'vColorMult','{ 0.035, 0.035, 0.035, 0.65 }' if name=='smoke_black' else '{ 0.85, 0.008, 0.02, 0.55 }')
            setp(emit,'fSizeMean',150 if name=='smoke_trail' else 250)
            if name!='smoke_trail':
                setp(emit,'vVelocityMean','{ 0, 130, 0 }')
                setp(emit,'vCenter','{ -80, 80, 0 }' if name=='smoke_black' else '{ 80, 80, 0 }')
            age=g.find("particleAction[@className='ParticleActionKillAge']")
            setp(age,'iAgeMs',4000)

# Local bursts use the already available glare sprite: no new shader or texture.
burst=copy.deepcopy(groups['ordinance']);burst.set('name','burst')
for a in list(burst.findall('particleAction')):
    if a.get('className')=='ParticleActionCopyToParameter':burst.remove(a)
for p in burst.iter('parameter'):
    if p.get('value','').startswith('ordinance/'):
        p.set('value',p.get('value').replace('ordinance/','burst/'))
setp(burst,'iNumParticlesMax',60)
setp(burst.find("particleAction[@className='ParticleActionKillAge']"),'iAgeMs',1200)
em=burst.find("particleAction[@className='ParticleActionEmitBox']")
for name,value in [('iEmitRate',1200),('fSizeMean',65),('vCenter','{ 0, 1900, 0 }'),('vVelocityMean','{ 0, 0, 0 }'),('vVelocitySpread','{ 650, 650, 650 }'),('iEmitCycles',62),('iEmitDurationMs',100),('iEmitDelayMs',1300),('iTimeStartedMs',1800)]:setp(em,name,value)
effect.append(burst)
ET.indent(tree,space='\t')
tree.write(out/'flamengo_v5_1043.lnx',encoding='utf-8',xml_declaration=False)

sys.path.insert(0,r'J:\mods\fifa 16\01_Projetos\mascotes\visualizador\tools')
from containers import big_entries,unpack
big=Path(r'U:\fifa 16\data_graphic2.big')
rows=big_entries(big)
name,offset,length=next(row for row in rows if row[0].replace('\\','/').endswith('/rooffireworks_0.rx3'))
with big.open('rb') as f:f.seek(offset);raw=f.read(length)
# Preserve the game's container encoding, including its texture name table.
(out/'flamengo_v5_1043.rx3').write_bytes(raw)
decoded=unpack(raw)
assert decoded[:3]==b'RX3'
max_particles=sum(int(g.find("parameter[@name='iNumParticlesMax']").get('value')) for g in effect.findall('particleGroup'))*36
print('Assets generated; total particle capacity',max_particles,'texture bytes',len(raw))
