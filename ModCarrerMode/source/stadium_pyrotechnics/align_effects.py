"""Anchor the existing effect groups to the 55cm machine outlet, preserving density."""
from pathlib import Path
import xml.etree.ElementTree as E
import shutil
root=Path(__file__).resolve().parent
path=root/'assets/stadium_pyrotechnics_0.lnx'
tree=E.parse(path)
def setp(action,name,value):
    p=action.find("parameter[@name='%s']"%name)
    if p is None:p=E.SubElement(action,'parameter',name=name,index='0')
    p.set('value',str(value))
for g in tree.findall('.//particleGroup'):
    name=g.get('name')
    emit=next(a for a in g.findall('particleAction') if a.get('className') in ('ParticleActionEmitBox','ParticleActionEmitSphere'))
    # Native Trigger clears the instance clock. The emit action only rebases
    # its retained iTimeStartedMs when it respects that external trigger.
    # Without this, reused opening instances eventually emit nothing on goals.
    setp(emit,'bRespectExternalTrigger','1')
    render=g.find("particleAction[@className='ParticleActionRender']")
    if name.startswith('smoke_base') or name.startswith('smoke_black'):
        setp(emit,'vCenter','{ 0, 0, 0 }')
        setp(emit,'vVelocityMean','{ 0, 280, 15 }')
        # Keep the dense 3.8m developed cloud, but begin at a 15cm nozzle plume.
        setp(render,'vSizeRamp','{ 0.04, 0.33, 0.66, 1.0 }')
        setp(render,'vPivotShift','{ 0, 0, 0 }')
    elif name=='ordinance':
        setp(emit,'vCenter','{ 0, 0, 0 }')
        setp(emit,'fSizeMean','12')
        setp(emit,'vVelocityMean','{ 0, 1180, 80 }')
        setp(emit,'vVelocitySpread','{ 40, 110, 60 }')
        # The overlay must follow each rocket too; its old copy target was omitted.
        action=g.find("particleAction[@name='MachineTrailOverlayCopy']")
        if action is None:action=E.SubElement(g,'particleAction',name='MachineTrailOverlayCopy',className='ParticleActionCopyToParameter')
        setp(action,'rPositionDest','smoke_trail_overlay/ParticleActionEmitBox/vCenter')
        setp(action,'iStride','0');setp(action,'iShiftInc','0')
    elif name.startswith('confetti_'):
        setp(emit,'vCenter','{ 0, 0, 0 }');setp(emit,'vDimensions','{ 6, 6, 6 }')
        setp(emit,'fSizeMean','3');setp(emit,'fSizeSpread','1')
        setp(emit,'vVelocityMean','{ 0, 1100, 75 }')
        # Paper used to stay invisible for ~1.4s after leaving the cannon.
        for p in render.findall("parameter[@name='vColorRamp']"):
            p.set('value','{ 1, 1, 1, %s }'%('0' if p.get('index')=='3' else '1'))
    elif name=='sparkle_trail':setp(emit,'fSizeMean','20')
E.indent(tree,space='\t')
tree.write(path,encoding='utf-8')
shutil.copy2(path,root/'build/assets'/path.name)
print('Outlet-centered smoke/rockets/paper; paired rocket trail overlays; paper immediately visible; rates/duration/dense smoke retained')
