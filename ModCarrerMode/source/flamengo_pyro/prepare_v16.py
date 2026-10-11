from pathlib import Path
import xml.etree.ElementTree as E
p=Path(__file__).parent;out=p/'build'/'assets'
# Restore known-working manager instance APIs; no recorder wrappers or ready-flag writes.
s=(p/'flamengo_pyro_v14.cpp').read_text().replace('flamengo_v14','flamengo_v16').replace('flamengo_pyro_v14.log','flamengo_pyro_v16.log').replace('installed v14','installed v16')
s=s.replace('    } else if (configured) {\n        log_event("RESOURCE_CHANGED', '    } else if (configured && !owned()) {\n        log_event("RESOURCE_CHANGED')
# Prime only our exclusive spare renderer before waiting for club/player metadata.
# The native ready routine polls its asynchronous init task and owns byte(state+5).
marker='static bool read_score(int& home,int& away) {'
helper='''static ULONGLONG lastPreload=0,lastDiagnostic=0;
static void preload(ULONGLONG now) {
    if(now-lastPreload<500)return;lastPreload=now;
    if(configured && !owned()) { forget_resource(); assetSince=0; }
    if(!configured) {
        if(!configure())return;
        assetSince=now;log_event("EARLY_PRELOAD configured_before_team_detection");
    }
    uintptr_t resource=0,effect=0;
    if(!get(activeState+0x50,resource) || !resource)return;
    const bool ready=((unsigned char (__fastcall*)(void*))(image+0x4383e30))((void*)activeObject)!=0;
    if(ready && get(activeManager+0x10,effect) && effect && !activeEffect) {
        activeEffect=effect;log_event("EARLY_PRELOAD ready_native_initialization_completed");
    }
    if(!ready && now-lastDiagnostic>=5000) {
        lastDiagnostic=now; unsigned char fileReady=0,nativeReady=0;uintptr_t task=0;
        get(resource+0x10,fileReady);get(activeState+5,nativeReady);get(activeState+0x268,task);
        char event[144];_snprintf_s(event,sizeof(event),_TRUNCATE,"LOAD_STATE file_ready=%u native_ready=%u task=%llx",fileReady,nativeReady,(unsigned long long)task);
        log_event(event);
    }
}
'''
assert marker in s;s=s.replace(marker,helper+marker)
s=s.replace('    // Fully automatic: keyboard input cannot arm, cancel or restart the show.','''    // Preload in the first available batch while the player tables are still loading.
    if(!showing)preload(now);
    // Fully automatic: keyboard input cannot arm, cancel or restart the show.''')
# A resource rebuild during a running intro must re-arm the intro, not silently consume it.
s=s.replace('if (configured && (showing || !consumed) && !owned()) { forget_resource(); consumed=!zero; candidateSince=now; }','''if (configured && (showing || !consumed) && !owned()) {
        const bool wasIntro=showing && !goalShow;
        forget_resource(); consumed=wasIntro?false:!zero; candidateSince=now;assetSince=0;
        log_event("RESOURCE_REBUILD rearm_pending_show_without_stale_pointers");
    }''')
# No initialization retries or job waits once idle resource is ready.
s=s.replace('if(!configured) {\n        if(!configure())return;', 'if(!configured) {\n        if(!configure())return;',1)
s=s.replace('    uintptr_t resource=0,effect=0;\n    if(!get(activeState+0x50,resource)', '    if(activeEffect)return;\n    uintptr_t resource=0,effect=0;\n    if(!get(activeState+0x50,resource)',1)
(p/'flamengo_pyro_v16.cpp').write_text(s)
(p/'build_v16.cmd').write_text((p/'build_v14.cmd').read_text().replace('flamengo_pyro_v14','flamengo_pyro_v16'))
tree=E.parse(out/'flamengo_v15_1043.lnx');tree.getroot().find('particleEffect').set('name','flamengo_v16')
tree.write(out/'flamengo_v16_1043.lnx',encoding='utf-8')
(out/'flamengo_v16_1043.rx3').write_bytes((out/'flamengo_v15_1043.rx3').read_bytes())
v=(p/'verify_v14.py').read_text().replace('flamengo_v14','flamengo_v16').replace('flamengo_pyro_v14','flamengo_pyro_v16').replace('capacity<37000','capacity<48000')
v+='''
assert 'ensure_visibility' not in source
assert 'state+5)=1' not in source and 'activeState+5)=1' not in source
assert 'EARLY_PRELOAD' in source and 'if(activeEffect)return;' in source
assert 'configured && !owned()' in cleanup
assert source.index('if(!showing)preload(now);')<source.index('cachedMatch=match(key,zero)')
print('Native-ready flag is engine-owned; preloading precedes team detection; valid idle resource retained: PASS')
'''
(p/'verify_v16.py').write_text(v)
(p/'install_v16.py').write_text((p/'install_v14.py').read_text().replace('v14_teste','v16_teste').replace('flamengo_pyro_v14','flamengo_pyro_v16').replace('flamengo_v14','flamengo_v16').replace('pyro v14','pyro v16').replace('Installed v14','Installed v16'))
print('Prepared v16: restore working emit API; no ready flag writes; early native preload, more diagnostic detail')
