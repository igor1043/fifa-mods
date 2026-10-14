"""Validate the published particle resource, including repeatable home goals."""
from pathlib import Path
import xml.etree.ElementTree as E

root = Path(__file__).resolve().parent
effect = E.parse(root / 'assets/stadium_pyrotechnics_0.lnx').getroot().find('particleEffect')
assert effect.get('name') == 'stadium_pyrotechnics'
groups = effect.findall('particleGroup')
assert len(groups) == 11
for group in groups:
    actions = [a for a in group.findall('particleAction')
               if a.get('className') in ('ParticleActionEmitBox', 'ParticleActionEmitSphere')]
    assert len(actions) == 1, group.get('name')
    params = {p.get('name'): p.get('value') for p in actions[0].findall('parameter')}
    assert params.get('bRespectExternalTrigger') == '1', group.get('name')
    assert int(params['iEmitCycles']) > 0, group.get('name')
    assert group.find("particleAction[@className='ParticleActionKillAge']") is not None
    for p in group.iter('parameter'):
        if p.get('name', '').startswith('r') and '/' in p.get('value', ''):
            target_group, action, name = p.get('value').split('/')
            target = effect.find(f"particleGroup[@name='{target_group}']/particleAction[@name='{action}']/parameter[@name='{name}']")
            assert target is not None, p.attrib
print('PASS: all 11 finite emitters restart on external triggers; particle references resolve.')
