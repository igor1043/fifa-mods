from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
s=(p/'flamengo_pyro_v12.cpp').read_text().replace('flamengo_v12','flamengo_v13').replace('flamengo_pyro_v12.log','flamengo_pyro_v13.log').replace('installed v12','installed v13')
idx=s.index('static bool scene_match(')
s=s[:idx]+'''// Read only stadium metadata, without waiting for player tables.
static bool stadium_match(uintptr_t& key) {
    uintptr_t lua=0; LuaValue globals={},db={},stadiums={};
    if(!get(image+0x3613fd0,lua) || !get(lua+0x78,globals) || globals.tag!=5 ||
        !lua_field((uintptr_t)globals.bits,"db",db) || db.tag!=5 ||
        !lua_field((uintptr_t)db.bits,"stadium",stadiums) || stadiums.tag!=5)return false;
    for(int i=0;i<4;++i) {
        LuaValue row={},h={},a={};double home=0,away=0;
        if(!lua_index((uintptr_t)stadiums.bits,i,row) || row.tag!=5 ||
            !lua_field((uintptr_t)row.bits,"homeTeamID",h) || h.tag!=3 ||
            !lua_field((uintptr_t)row.bits,"awayTeamID",a) || a.tag!=3)continue;
        memcpy(&home,&h.bits,8);memcpy(&away,&a.bits,8);
        if(home!=1043 && away!=1043)continue;
        clubSide=home==1043?0:1;key=(uintptr_t)row.bits;return key!=0;
    }
    return false;
}
'''+s[idx:]
s=s.replace('if (scene_match(sceneKey))','if (stadium_match(sceneKey) || scene_match(sceneKey))')
# Reacquire only the exclusive definition belonging to this version after a native reload.
old='''        !get(s+8,definition) || definition[0] ||
        !get(s+0x268,task) || task || !get(s+0x58,m) || !m ||
        !get(s+0x50,resource) || !resource) return false;'''
new='''        !get(s+8,definition) ||
        !get(s+0x268,task) || task || !get(s+0x58,m) || !m ||
        !get(s+0x50,resource) || !resource) return false;
    if (!memcmp(definition,effectName,sizeof(effectName))) {
        int assetId=0;memcpy(&assetId,definition+64,4);
        if(assetId!=1043)return false;
        activeObject=p;activeState=s;activeManager=m;activeEffect=0;configured=true;
        for(int i=0;i<emitterCount;++i) {
            int handle=-1;
            if(!get(s+0x60+i*4,handle)) {forget_resource();return false;}
            const uintptr_t instance=handle<0?0:instance_for(m,handle);
            if(handle>=0 && !instance) {forget_resource();return false;}
            handles[i]=handle;activeInstances[i]=instance;
        }
        log_event("OWN_DEFINITION_RECOVERED after_native_resource_reload");return true;
    }
    if(definition[0])return false;'''
assert old in s;s=s.replace(old,new)
s=s.replace('if (now-candidateSince<750) return;','if (now-candidateSince<100) return;')
(p/'flamengo_pyro_v13.cpp').write_text(s)
(p/'build_v13.cmd').write_text((p/'build_v12.cmd').read_text().replace('flamengo_pyro_v12','flamengo_pyro_v13'))
tree=E.parse(out/'flamengo_v12_1043.lnx');tree.getroot().find('particleEffect').set('name','flamengo_v13')
tree.write(out/'flamengo_v13_1043.lnx',encoding='utf-8')
(out/'flamengo_v13_1043.rx3').write_bytes((out/'flamengo_v12_1043.rx3').read_bytes())
(p/'verify_v13.py').write_text((p/'verify_v12.py').read_text().replace('flamengo_v12','flamengo_v13').replace('flamengo_pyro_v12','flamengo_pyro_v13'))
(p/'install_v13.py').write_text((p/'install_v12.py').read_text().replace('v12_teste','v13_teste').replace('flamengo_pyro_v12','flamengo_pyro_v13').replace('flamengo_v12','flamengo_v13').replace('pyro v12','pyro v13').replace('Installed v12','Installed v13'))
print('Prepared v13: recover exclusively owned resource; earlier stadium metadata; substitutions untouched')
