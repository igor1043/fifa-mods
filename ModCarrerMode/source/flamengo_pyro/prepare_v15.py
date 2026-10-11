from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v14.cpp').read_text().replace('flamengo_v14','flamengo_v15').replace('flamengo_pyro_v14.log','flamengo_pyro_v15.log').replace('installed v14','installed v15').replace('native_signatures_v6.h','native_signatures_v15.h')
# Record creation exactly once per missing slot. Never delete/recreate a live slot.
old='''            handles[i]=((int (__fastcall*)(void*,float,float,float,float,float,float))(image+0x441bce0))
                ((void*)activeManager,0,0,0,0,0,0);
            activeInstances[i]=instance_for(activeManager,handles[i]);'''
new='''            ((void (__fastcall*)(void*,int,float,float,float,float,float,float))(image+0x4383f70))
                ((void*)activeObject,i,0,0,0,0,0,0);
            if(!get(activeState+0x60+i*4,handles[i]))return false;
            activeInstances[i]=instance_for(activeManager,handles[i]);'''
assert old in s;s=s.replace(old,new)
s=s.replace('((void (__fastcall*)(void*,int,const float*))(image+0x441cd90))((void*)activeManager,handles[i],matrix);','((void (__fastcall*)(void*,int,const float*))(image+0x4385df0))((void*)activeObject,i,matrix);')
# Public trigger/enable record native replay commands; slots checked first.
s=s.replace('((Slot)(image+0x441ce00))((void*)activeManager,handles[i]);','((Slot)(image+0x4386880))((void*)activeObject,i);')
s=s.replace('((Slot)(image+0x441c8d0))((void*)activeManager,handles[i]);','((void (__fastcall*)(void*,int,unsigned char))(image+0x4385ad0))((void*)activeObject,i,1);')
s=s.replace('((Slot)(image+0x441c720))((void*)activeManager,handles[i]);','((void (__fastcall*)(void*,int,unsigned char))(image+0x4385ad0))((void*)activeObject,i,0);')
s=s.replace('    *(unsigned char*)(activeState+4)=0;','''    *(unsigned char*)(activeState+5)=1;
    ((One)(image+0x43861b0))((void*)activeObject);''')
# While resource is valid, preserve visibility in intro and replay as well as live gameplay.
idx=s.index('static bool swap(')
helper='''static void ensure_visibility() {
    // Read current object/state every call. No stored pointer is written after teardown.
    uintptr_t object=0,state=0;char name[32]={};
    if(!configured || !get(image+0x3504500+31*8,object) || object!=activeObject ||
       !same(object,image+0x2209f70) || !get(object+0x10,state) || state!=activeState ||
       !get(state+8,name) || memcmp(name,effectName,sizeof(effectName)))return;
    *(unsigned char*)(state+4)=0; *(unsigned char*)(state+5)=1;
}
'''
# Forward declaration: called before native batch's visibility gate.
s=s[:idx]+helper+s[idx:]
s=s.replace('static void __fastcall draw_hook(', 'static void ensure_visibility();\nstatic void __fastcall draw_hook(')
s=s.replace('    original(self,phase);','''    if(phase==0 && configured && !faulted && !stopping) {
        __try { ensure_visibility(); }
        __except(EXCEPTION_EXECUTE_HANDLER) { InterlockedExchange(&faulted,1);log_event("VISIBILITY_FAULT"); }
    }
    original(self,phase);''')
s=s.replace('Direct manager Create: no replay-recorded renderer command.','Native recorder Create only for an empty slot; instances retained through replay.')
s=s.replace('Do not emit replay-recorded Delete/Hide/SetDefinition/Reload commands.','Record emission disable only; never Delete/Hide/SetDefinition/Reload at stop.')
s=s.replace('no_instance_delete','record_native_replay_commands no_instance_delete')
(p/'flamengo_pyro_v15.cpp').write_text(s)
(p/'build_v15.cmd').write_text((p/'build_v14.cmd').read_text().replace('flamengo_pyro_v14','flamengo_pyro_v15'))
capture=Path(r'J:\mods\fifa 16\01_Projetos\mascotes\mod\diagnostics\20261007_102226_826631_mascot_native_observation\fifa16.image.bin').read_bytes()
header=(p/'native_signatures_v6.h').read_text()
add=[]
for i,rva in enumerate((0x4383f70,0x4385df0,0x4386880,0x4385ad0,0x43861b0),11):
    add.append('    const unsigned char sig%d[16]={%s};'%(i,','.join('0x%02x'%v for v in capture[rva:rva+16])))
    add.append('    if (!get(base+0x%x,found) || memcmp(found,sig%d,16)) return false;'%(rva,i))
(p/'native_signatures_v15.h').write_text(header.replace('    return true;','\n'.join(add)+'\n    return true;'))
tree=E.parse(out/'flamengo_v14_1043.lnx');effect=tree.getroot().find('particleEffect');effect.set('name','flamengo_v15')
def setp(node,name,value):
    par=node.find("parameter[@name='%s']"%name);assert par is not None,name;par.set('value',str(value))
for g in effect.findall('particleGroup'):
    name=g.get('name')
    if not name.startswith('smoke'):continue
    em=g.find("particleAction[@className='ParticleActionEmitBox']");render=g.find("particleAction[@className='ParticleActionRender']")
    setp(g,'iNumParticlesMax',850);setp(em,'iEmitRate',150)
    setp(render,'vColorMult','{ 0.055, 0.055, 0.055, 0.98 }' if name=='smoke_black' else '{ 0.7, 0.012, 0.025, 0.95 }')
    ramps=render.findall("parameter[@name='vColorRamp']")
    for ramp in ramps:
        index=int(ramp.get('index','0'))
        if index==1:ramp.set('value','{ 1, 1, 1, 0.95 }')
        if index==2:ramp.set('value','{ 1, 1, 1, 0.75 }')
    setp(g.find("particleAction[@className='ParticleActionKillAge']"),'iAgeMs',6500)
    if name!='smoke_trail':
        setp(em,'vVelocityMean','{ 55, 280, 15 }');setp(em,'vVelocitySpread','{ 60, 100, 40 }');setp(em,'fSizeMean',380)
tree.write(out/'flamengo_v15_1043.lnx',encoding='utf-8')
(out/'flamengo_v15_1043.rx3').write_bytes((out/'flamengo_v14_1043.rx3').read_bytes())
v=(p/'verify_v14.py').read_text().replace('flamengo_v14','flamengo_v15').replace('flamengo_pyro_v14','flamengo_pyro_v15').replace('native_signatures_v6.h','native_signatures_v15.h').replace('==11','==16').replace('11 runtime','16 runtime').replace('capacity<37000','capacity<48000')
v=v.replace("'441c720' in cleanup","'4385ad0' in cleanup")
start=v.index('for address in (\'4383f70\'');end=v.index("print('No instance delete",start)
v=v[:start]+'''assert 'if (current!=-1) return false;' in emit
for address in ('4383f70','4385df0','43861b0'):assert address in emit
assert '4386880' in source and '4385ad0' in source
assert 'state+5)=1' in source
'''+v[end:]
v=v.replace('native instance calls bypass replay recorder','native replay commands recorded with retained assets and instances')
(p/'verify_v15.py').write_text(v)
(p/'install_v15.py').write_text((p/'install_v14.py').read_text().replace('v14_teste','v15_teste').replace('flamengo_pyro_v14','flamengo_pyro_v15').replace('flamengo_v14','flamengo_v15').replace('pyro v14','pyro v15').replace('Installed v14','Installed v15'))
print('Prepared v15: visibility bytes 4/5, native replay recording without deletes, denser taller smoke')
