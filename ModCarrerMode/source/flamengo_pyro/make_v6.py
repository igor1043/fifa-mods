from pathlib import Path
p=Path(__file__).parent
s=(p/'flamengo_pyro_v5.cpp').read_text()
s=s.replace('emitterCount=36','emitterCount=6').replace('durationMs=90000','durationMs=30000').replace('flamengo_v5','flamengo_v6')
s=s.replace('static char logPath[MAX_PATH];','static char logPath[MAX_PATH], configPath[MAX_PATH];\nstatic bool enabled=false, automatic=false, f7Down=false, f9Down=false;\nstatic uintptr_t activeEffect=0, activeInstances[emitterCount]={};\nstatic ULONGLONG kickoffSince=0, assetSince=0;\nstatic bool showing=false;')
a=s.index('static bool owned()')
b=s.index('static bool configure()',a)
s=s[:a]+'''// Never pass a handle to the native tree helpers until the exact instance is
// found. Those helpers dereference the sentinel for missing IDs.
static uintptr_t instance_for(uintptr_t manager,int handle) {
    uintptr_t node=0;
    if (handle<0 || !get(manager+0x30,node)) return 0;
    for (int depth=0;node && depth<128;++depth) {
        int id=-1; uintptr_t child=0,instance=0;
        if (!get(node+0x20,id)) return 0;
        if (id==handle) return get(node+0x28,instance)?instance:0;
        if (!get(node+(handle<id?8:0),child) || child==node) return 0;
        node=child;
    }
    return 0;
}
static bool owned() {
    uintptr_t p=0,s=0,m=0,effect=0; char name[32]={};
    return configured && get(image+0x3504500+31*8,p) && p==activeObject &&
        same(p,image+0x2209f70) && get(p+0x10,s) && s==activeState &&
        get(s+0x58,m) && m==activeManager && get(s+8,name) &&
        !memcmp(name,effectName,sizeof(effectName)) && get(m+0x10,effect) &&
        (!activeEffect || effect==activeEffect);
}
static bool valid_slot(int i) {
    int current=-1;
    return owned() && handles[i]>=0 && get(activeState+0x60+i*4,current) &&
        current==handles[i] && instance_for(activeManager,handles[i])==activeInstances[i] && activeInstances[i];
}
static void forget_resource() {
    configured=false; activeEffect=0; showing=false; deadline=0;
    for (int i=0;i<emitterCount;++i) { handles[i]=-1; activeInstances[i]=0; }
}
static void cleanup() {
    if (owned()) {
        for (int i=0;i<emitterCount;++i) if (valid_slot(i)) {
            ((Slot)(image+0x441c720))((void*)activeManager,handles[i]);
            ((Slot)(image+0x441c940))((void*)activeManager,handles[i]);
        }
        // Keep definition, asset and instances alive until native scene teardown.
        // Do not emit replay-recorded Delete/Hide/SetDefinition/Reload commands.
        if (showing) log_event("SHOW_STOPPED emission_disabled asset_retained_for_replay");
    } else if (configured) {
        log_event("RESOURCE_CHANGED discarded_stale_handles_without_native_calls");
        forget_resource();
    }
    showing=false; deadline=0;
}
''' + s[b:]
s=s.replace('    memcpy(savedDefinition,definition,68);','    memcpy(savedDefinition,definition,68);')
a=s.index('static bool emit()')
b=s.index('static void __fastcall draw_hook',a)
s=s[:a]+'''static bool emit() {
    uintptr_t resource=0,effect=0;
    if (!owned() || !get(activeState+0x50,resource) || !resource) return false;
    if (!((unsigned char (__fastcall*)(void*))(image+0x4383e30))((void*)activeObject) ||
        !get(activeManager+0x10,effect) || !effect) return false;
    activeEffect=effect;
    for (int i=0;i<emitterCount;++i) {
        int current=-1;
        if (!get(activeState+0x60+i*4,current)) return false;
        if (handles[i]<0) {
            if (current!=-1) return false;
            // Direct manager Create: no replay-recorded renderer command.
            handles[i]=((int (__fastcall*)(void*,float,float,float,float,float,float))(image+0x441bce0))
                ((void*)activeManager,0,0,0,0,0,0);
            activeInstances[i]=instance_for(activeManager,handles[i]);
            if (handles[i]<0 || !activeInstances[i]) return false;
            *(int*)(activeState+0x60+i*4)=handles[i];
        }
        if (!valid_slot(i)) return false;
        __declspec(align(16)) float matrix[16]={1,0,0,0, 0,1,0,0, 0,0,1,0, 0,35,0,1};
        matrix[12]=(float)((i%3-1)*2500);
        matrix[14]=i<3?-3650.0f:3650.0f;
        ((void (__fastcall*)(void*,int,const float*))(image+0x441cd90))((void*)activeManager,handles[i],matrix);
        ((Slot)(image+0x441ce00))((void*)activeManager,handles[i]);
        ((Slot)(image+0x441c8d0))((void*)activeManager,handles[i]);
    }
    *(unsigned char*)(activeState+4)=0;
    log_event("SHOW_STARTED six_spaced_emitters max_ms=30000 kickoff_tail_ms=8000"); return true;
}
static bool gameplay_present() {
    uintptr_t manager=0,world=0,game=0,registry=0;
    return get(image+0x3517420,manager) && same(manager,image+0x2226730) &&
        get(manager+8,world) && same(world,image+0x2225d90) &&
        get(world+0x10,game) && same(game,image+0x2309370) &&
        get(game+0x20,registry) && registry;
}
static void tick(void* batch) {
    const ULONGLONG now=GetTickCount64();
    if (now-lastSample<100 && !stopping) return;
    lastSample=now;
    uintptr_t impl=0;
    if (!same((uintptr_t)batch,image+0x2214500) || !get((uintptr_t)batch+0x10,impl) || !impl) return;
    ((One)(image+0x43f31d0))((void*)impl);
    if (stopping) { cleanup(); return; }
    // Default opt-in. Reload config on F7; F7 arms/disarms, F8 starts, F9 stops.
    const bool seven=(GetAsyncKeyState(VK_F7)&0x8000)!=0;
    const bool eight=(GetAsyncKeyState(VK_F8)&0x8000)!=0;
    const bool nine=(GetAsyncKeyState(VK_F9)&0x8000)!=0;
    if (seven && !f7Down) {
        enabled=!enabled;
        WritePrivateProfileStringA("pyro","enabled",enabled?"1":"0",configPath);
        automatic=GetPrivateProfileIntA("pyro","automatic",0,configPath)!=0;
        log_event(enabled?"F7 enabled":"F7 disabled");
        if (!enabled) { cleanup(); consumed=true; }
    }
    f7Down=seven;
    const bool request=(eight && !keyDown) || InterlockedExchange(&replayRequested,0);
    const bool cancel=nine && !f9Down; keyDown=eight; f9Down=nine;
    if (cancel) { cleanup(); consumed=true; log_event("F9 stopped"); }
    uintptr_t key=0; bool zero=false;
    if (!match(key,zero)) {
        cleanup();
        if (lastValid && now-lastValid>2000) { sessionKey=0; consumed=false; candidateSince=0; kickoffSince=0; }
        return;
    }
    lastValid=now;
    if (key!=sessionKey) {
        cleanup(); sessionKey=key; consumed=!automatic || !zero;
        candidateSince=now; kickoffSince=0;
    }
    if (configured && !owned()) { forget_resource(); consumed=true; return; }
    if (request && enabled) {
        cleanup(); consumed=false; candidateSince=now; kickoffSince=0;
        log_event("F8 start_requested");
    }
    if (!enabled) return;
    if (showing) {
        if (!kickoffSince && gameplay_present()) kickoffSince=now;
        if (now>=deadline || (kickoffSince && now-kickoffSince>=8000)) { cleanup(); consumed=true; }
        return;
    }
    if (consumed) return;
    if (!configured) {
        if (now-candidateSince<750) return;
        if (!configure()) {
            if (now-candidateSince>15000) { consumed=true; log_event("SLOT_UNAVAILABLE no_show"); }
            return;
        }
        assetSince=now;
    }
    if (emit()) {
        consumed=true; showing=true; deadline=now+durationMs;
        kickoffSince=gameplay_present()?now:0;
    } else if (now-assetSince>15000) { cleanup(); consumed=true; log_event("ASSET_TIMEOUT"); }
}
''' + s[b:]
s=s.replace(' || !strcmp(name+1,"flamengo_pyro_v4.dll")',' || !strcmp(name+1,"flamengo_pyro_v4.dll") || !strcmp(name+1,"flamengo_pyro_v5.dll")')
s=s.replace('installed v5 native_particle_pipeline 36_emitters 90_seconds F8_replay','installed v6 six_emitters opt_in F7_enable F8_start F9_stop no_instance_delete')
s=s.replace('flamengo_pyro_v5.log','flamengo_pyro_v6.log')
needle='    for (int& handle:handles) handle=-1;'
s=s.replace(needle,'''    _snprintf_s(configPath,MAX_PATH,_TRUNCATE,"%s\\\\flamengo_pyro\\\\pyro.ini",root);
    enabled=GetPrivateProfileIntA("pyro","enabled",0,configPath)!=0;
    automatic=GetPrivateProfileIntA("pyro","automatic",0,configPath)!=0;
    for (int& handle:handles) handle=-1;''')
(p/'flamengo_pyro_v6.cpp').write_text(s)
build=(p/'build_v5.cmd').read_text().replace('flamengo_pyro_v2.cpp','flamengo_pyro_v6.cpp').replace('flamengo_pyro_v5.dll','flamengo_pyro_v6.dll')
(p/'build_v6.cmd').write_text(build)
print('v6 source generated')
