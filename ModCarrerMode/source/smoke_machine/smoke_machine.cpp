#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "launch_sites.h"
#include "presentation.h"
#include "loading_policy.h"
using BuildFn=void(__fastcall*)(void*);
static uintptr_t image;
static BuildFn nextBuild;
static LONG started,stopping,busy,luaReady;
static char logPath[MAX_PATH],iniPath[MAX_PATH],luaPath[MAX_PATH];
static bool enabled=true,createdLive=false,resourceRequested=false,shadowRequested=false,fault=false,placed=false,requireEntrance=false,requireVar=false;
static uintptr_t owner=0,prototype=0,shadow=0,prototypeState=0;
static float yCm=2;
static bool matchVisible=false;
static PyroMatchSession matchSession;
static uint64_t nextConfig=0,nextDiagnostic=0;
static uint64_t nextScene=0,nextCreate=0;
static MachineLuaLifecycle luaLifecycle;
static uintptr_t lastLuaGlobals=0;
static char presentationPath[MAX_PATH],pyroPath[MAX_PATH];
alignas(16) static unsigned char scratch[(128+machineCount)*0x50],records[machineCount][0x50];
static unsigned char expectedCall[5],appliedCall[5];
static void event(const char* msg){FILE* f=nullptr;if(!fopen_s(&f,logPath,"ab")&&f){fprintf(f,"%llu %s\n",GetTickCount64(),msg);fclose(f);}}
template<class T>static bool get(uintptr_t a,T& v){SIZE_T n=0;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,&v,sizeof(v),&n)&&n==sizeof(v);}
static bool bytes(uintptr_t a,void* b,size_t size){SIZE_T n=0;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,b,size,&n)&&n==size;}
struct Vector{uintptr_t begin,end,capacity;};
static bool vector(uintptr_t at,size_t stride,Vector& v,size_t& n){
    if(!get(at,v))return false;
    if(!v.begin&&!v.end&&!v.capacity){n=0;return true;}
    if(v.begin<0x10000||v.end<v.begin||v.capacity<v.end||(v.end-v.begin)%stride||(v.capacity-v.begin)%stride||(v.capacity-v.begin)/stride>1024)return false;
    n=(v.end-v.begin)/stride;return n<=128;
}
static float setting(const char* name,float fallback,float limit){char b[64];GetPrivateProfileStringA("smoke_machine",name,"",b,sizeof(b),iniPath);if(!b[0])return fallback;float v=(float)atof(b);return isfinite(v)&&fabsf(v)<=limit?v:fallback;}
static void config(){
    const uint64_t now=GetTickCount64();if(now<nextConfig)return;nextConfig=now+1000;
    enabled=GetPrivateProfileIntA("smoke_machine","enabled",1,iniPath)!=0;
    yCm=setting("ground_lift_cm",2,20);
}
static bool console(const char* script,size_t size){
    uintptr_t lua=0,globals=0;int tag=0;
    if(!get(image+0x3613fd0,lua)||!get(lua+0x80,tag)||tag!=5||!get(lua+0x78,globals)||!globals)return false;
    __try{((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,size,"smoke_machine_native");return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){event("lua_console_fault");return false;}
}
static bool activateLua(){
    static char script[16384];FILE* f=nullptr;
    if(fopen_s(&f,luaPath,"rb")||!f)return false;
    const char prefix[]="if not FIFA16_SMOKE_MACHINE_LUA_V2 then ";memcpy(script,prefix,sizeof(prefix)-1);
    const size_t n=fread(script+sizeof(prefix)-1,1,sizeof(script)-256,f);const bool ok=!ferror(f)&&feof(f);fclose(f);if(!ok)return false;
    const char suffix[]="\nFIFA16_SMOKE_MACHINE_LUA_V2=true end; FIFA16_SMOKE_MACHINE_HOOK_READY=true";
    memcpy(script+sizeof(prefix)-1+n,suffix,sizeof(suffix));return console(script,sizeof(prefix)-1+n+sizeof(suffix)-1);
}
struct LuaValue{uint64_t bits;int tag,padding;};
static bool luaFlag(uintptr_t table,const char* key){
    unsigned char tag=0,power=0;uintptr_t nodes=0;
    if(!get(table+8,tag)||tag!=5||!get(table+11,power)||power>12||!get(table+32,nodes)||!nodes)return false;
    const size_t length=strlen(key);
    struct Node{LuaValue value,key;uintptr_t next;};
    for(unsigned i=0;i<(1u<<power);++i){
        Node n{};size_t len=0;char text[64]={};
        if(!get(nodes+i*40,n))return false;
        if(n.key.tag!=4||!get((uintptr_t)n.key.bits+16,len)||len!=length||len>=sizeof(text))continue;
        if(bytes((uintptr_t)n.key.bits+24,text,len)&&!memcmp(text,key,len))return n.value.tag==1&&n.value.bits!=0;
    }
    return false;
}
static void refreshLua(){
    const uint64_t now=GetTickCount64();
    if(now<luaLifecycle.nextCheck)return;
    uintptr_t vm=0;LuaValue globals{};
    const bool valid=get(image+0x3613fd0,vm)&&vm&&get(vm+0x78,globals)&&globals.tag==5;
    const bool sameLua=valid&&luaLifecycle.vm==vm&&lastLuaGlobals==(uintptr_t)globals.bits;
    luaLifecycle.sample(now,valid?vm:0);
    if(sameLua&&luaLifecycle.ready){InterlockedExchange(&luaReady,1);return;}
    lastLuaGlobals=valid?(uintptr_t)globals.bits:0;
    const bool known=valid&&luaFlag((uintptr_t)globals.bits,"FIFA16_SMOKE_MACHINE_LUA_V2")&&luaFlag((uintptr_t)globals.bits,"FIFA16_SMOKE_MACHINE_HOOK_READY");
    if(luaLifecycle.should_activate(now,known)){
        // Lua callbacks and native factory calls belong to the scene thread.
        activateLua();
        if(get(vm+0x78,globals)&&globals.tag==5)luaLifecycle.ready=luaFlag((uintptr_t)globals.bits,"FIFA16_SMOKE_MACHINE_LUA_V2");
        if(luaLifecycle.ready)event("lua_ready scene_thread verified_marker");
    }
    InterlockedExchange(&luaReady,luaLifecycle.ready?1:0);
}
static void scene() {
    const uint64_t now=GetTickCount64();if(now<nextScene)return;nextScene=now+250;
    char page[64]={};uintptr_t p=0;const unsigned offsets[]={232,192,136,472};
    bool known=get(image+58757168,p)&&p;
    for(unsigned off:offsets)if(known)known=get(p+off,p)&&p;
    known=known&&get(p,page)&&memchr(page,0,sizeof(page));
    const auto kind=pyro_page(page,known,matchSession.key!=0);
    matchVisible=false;
    if(kind==PyroPage::Outside){matchSession=PyroMatchSession{};return;}
    if(kind==PyroPage::Unreadable)return;
    uintptr_t manager=0,world=0,game=0,registry=0,pairs=0;int k=0,count=0;
    if(!get(image+0x3517420,manager)||!get(manager,p)||p!=image+0x2226730||
       !get(manager+8,world)||!get(world,p)||p!=image+0x2225d90||
       !get(world+0x10,game)||!get(game,p)||p!=image+0x2309370||
       !get(game+0x20,registry)||!registry||!get(registry+8+15*32,k)||k!=15||
       !get(registry+8+15*32+16,count)||count!=2||!get(registry+8+15*32+24,pairs))return;
    int clubs[2]={};uintptr_t teams[2]={};
    for(int i=0;i<2;++i){
        uintptr_t team=0,stats=0,ownerTeam=0;int side=-1,club=0;
        if(!get(pairs+i*16+8,team)||!get(team,p)||p!=image+0x22fe9f0||
           !get(team+0x30,ownerTeam)||ownerTeam!=registry||!get(team+0x58,side)||side<0||side>1||teams[side]||
           !get(team+0x50,stats)||!get(stats+0x80,club)||club<=0||club>1000000)return;
        teams[side]=team;clubs[side]=club;
    }
    if(kind==PyroPage::Match)matchSession.observe(registry,clubs[0],clubs[1]);
    if(!matchSession.key||matchSession.home!=clubs[0]||matchSession.away!=clubs[1])return;
    const bool permit=GetPrivateProfileIntA("match","pyrotechnics",0,presentationPath)!=0&&
                      GetPrivateProfileIntA("pyro","enabled",1,pyroPath)!=0;
    matchVisible=permit&&pyro_can_continue(kind,true,true);
}
static bool ownPrototype(void* self,uintptr_t& p,uintptr_t& state,uintptr_t& base){
    Vector v{};size_t n=0;uint16_t type=0,variation=0;unsigned rna=0;
    if(!vector((uintptr_t)self+0x30*17,8,v,n)||n!=2||!get(v.begin,base)||!get(v.begin+8,p)||p==base)return false;
    if(!get(base+12,type)||type!=16||!get(base+14,variation)||variation!=0)return false;
    return get(p+12,type)&&type==16&&get(p+14,variation)&&variation==1&&get(p+16,state)&&get(state+0x4c,rna)&&rna<176;
}
static bool ready(uintptr_t p,bool& requested,const char* message){
    using Ready=unsigned char(__fastcall*)(void*);
    if(fault)return false;
    __try{
        if(!requested){
            const bool initialized=((Ready)(image+0x43b4500))((void*)p)!=0;
            if(!initialized){
                const int parameters[5]={-1,-1,-1,0,-1};((void(__fastcall*)(void*,const int*))(image+0x43b4640))((void*)p,parameters);
            }
            if(!initialized || p==prototype){
                uintptr_t vt=0,load=0;if(!get(p,vt)||!get(vt+0x38,load)||load!=image+0x43b4530)return false;
                // Startup can have prepared this reserved appearance as an official
                // before the Lua gate became ready. Reload ONLY our private model.
                ((void(__fastcall*)(void*,int))load)((void*)p,p==prototype?1:0);
            }
            requested=true;event(message);
        }
        const bool allLodsReady=((Ready)(image+0x43b43e0))((void*)p)!=0;
        // A renderable created after the initial batch misses the startup
        // notification. Complete its native flag only after all five resource
        // composites confirm readiness; never force an unprepared asset.
        if(allLodsReady&&!((Ready)(image+0x43b4520))((void*)p)){
            ((void(__fastcall*)(void*))(image+0x43b47c0))((void*)p);
            event("native_loaded_notification all_five_lods_ready");
        }
        return allLodsReady&&((Ready)(image+0x43b4520))((void*)p)!=0;
    }__except(EXCEPTION_EXECUTE_HANDLER){fault=true;event("native_resource_fault_disabled");return false;}
}
static void position(size_t i,float h){
    const auto& site=machineSites[i];const float p[4]={site.x,h,site.z,site.yaw};
    memcpy(records[i]+0x20,p,16);memcpy(records[i]+0x30,p,16);
}
static void __fastcall buildHook(void* self){
    if(InterlockedCompareExchange(&busy,1,0)){nextBuild(self);return;}
    Vector saved{},temporary{};size_t n=0,normalBytes=0;unsigned mask=0;bool swapped=false,maskSaved=false;float submitted=-3000;
    const uintptr_t list=(uintptr_t)self+0x30*(16+0x2f),maskAt=(uintptr_t)self+0x4f604;
    __try{
        config();scene();refreshLua();
        uintptr_t p=0,s=0,b=0;
        bool hasPrototype=luaReady&&ownPrototype(self,p,s,b);
        if(luaReady&&!hasPrototype&&GetTickCount64()>=nextCreate){
            nextCreate=GetTickCount64()+500;
            // The same factory/AddSubObject path as normal startup, on the render
            // thread. No copied native resources and no concurrent vector mutation.
            static const char create[]="FIFA16_SMOKE_MACHINE_CREATE_LIVE()";
            console(create,sizeof(create)-1);
            hasPrototype=ownPrototype(self,p,s,b);
        }
        if(hasPrototype&&vector(list,0x50,saved,n)&&n<=128){
            createdLive=true;normalBytes=n*0x50;
            if(!normalBytes||bytes(saved.begin,scratch,normalBytes)){
                // Any native random use of the reserved appearance keeps the
                // original platform camera. The private record alone uses cabin.
                for(size_t i=0;i<n;++i){auto r=scratch+i*0x50;if(r[0x42]==1){r[0x42]=0;r[0x40]=r[0x41]=0xff;r[0x45]=0;}}
                if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
                if(owner!=(uintptr_t)self||prototype!=p||prototypeState!=s||shadow!=b){
                    owner=(uintptr_t)self;prototype=p;prototypeState=s;shadow=b;resourceRequested=shadowRequested=fault=placed=false;

                    memset(records,0,sizeof(records));
                    for(size_t i=0;i<machineCount;++i){records[i][0x40]=records[i][0x41]=0xff;records[i][0x42]=1;}
                    event("static_prototype_confirmed type=16 variation=1 machines=20");
                    unsigned rna=0;char update[96];
                    if(get(s+0x4c,rna)&&rna<176){
                        const int length=_snprintf_s(update,sizeof(update),_TRUNCATE,"SleUpdate(%u)",rna);
                        if(length>0)console(update,(size_t)length);
                    }
                }

                const bool a=ready(p,resourceRequested,"model_texture_requested");const bool c=ready(b,shadowRequested,"shadow_dependency_requested");
                if((!a||!c)&&GetTickCount64()>=nextDiagnostic){
                    nextDiagnostic=GetTickCount64()+5000;char message[160];
                    _snprintf_s(message,sizeof(message),_TRUNCATE,"model_deferred reason=resources_not_ready model=%u shadow=%u",(unsigned)a,(unsigned)c);event(message);
                }
                if(a&&c&&get(maskAt,mask)){
                    submitted=enabled&&!stopping&&matchVisible?yCm:-3000;
                    for(size_t i=0;i<machineCount;++i){position(i,submitted);memcpy(scratch+normalBytes+i*0x50,records[i],0x50);}
                    temporary={(uintptr_t)scratch,(uintptr_t)scratch+normalBytes+machineCount*0x50,(uintptr_t)scratch+sizeof(scratch)};
                    memcpy((void*)list,&temporary,sizeof(temporary));swapped=true;*(unsigned*)maskAt=mask|(1u<<16);maskSaved=true;
                }
            }
        }
        if(!hasPrototype&&GetTickCount64()>=nextDiagnostic){
            nextDiagnostic=GetTickCount64()+5000;
            char message[144];_snprintf_s(message,sizeof(message),_TRUNCATE,"model_deferred reason=%s vm=%p",luaReady?"prototype_missing_or_incompatible":"lua_not_ready",(void*)luaLifecycle.vm);event(message);
        }
        nextBuild(self);
    }__finally{
        if(swapped){
            if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
            bool bound=true;
            for(size_t i=0;i<machineCount;++i){
                memcpy(records[i],scratch+normalBytes+i*0x50,0x50);position(i,submitted);
                uint16_t binding=0xffff;memcpy(&binding,records[i]+0x40,2);bound=bound&&binding!=0xffff;
            }
            memcpy((void*)list,&saved,sizeof(saved));
            if(bound&&!placed){event("machines_placed count=20 native_bindings_assigned resources_ready");placed=true;}
            const uint64_t now=GetTickCount64();if(now>=nextDiagnostic){
                nextDiagnostic=now+5000;char msg[160];
                _snprintf_s(msg,sizeof(msg),_TRUNCATE,"machines=20 height_cm=%g originals=%zu visible=%u bound=%u",submitted,n,(unsigned)(submitted>-1000),(unsigned)bound);event(msg);
            }
        }
        if(maskSaved)*(unsigned*)maskAt=mask;
        InterlockedExchange(&busy,0);
    }
}
static bool signatures(){
    struct Guard{uintptr_t rva;unsigned char bytes[16];size_t length;};
    const Guard guards[]={
        {0x43b4500,{0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x4a,0xc3},9},
        {0x43b4520,{0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x48,0xc3},9},
        {0x43b4530,{0x57,0x48,0x83,0xec,0x20,0x48,0x89,0xcf,0x48,0x8b,0x49,0x10,0x80,0x79,0x4a,0x00},16},
        {0x43b43e0,{0x48,0x8b,0x51,0x10,0xb0,0x01,0x41,0xb8,0x0f,0x0b,0x4e,0xc3,0x48,0x83,0xc2,0x20},16},
        {0x43b4640,{0x57,0x48,0x83,0xec,0x70,0x48,0x8b,0x05,0x14,0x3e,0xee,0xfe,0x48,0x31,0xe0,0x48},16},
        {0x4ac35e0,{0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x30,0x48},16}
    };
    for(const auto& g:guards){unsigned char a[16];if(!bytes(image+g.rva,a,g.length)||!machine_guard_matches(a,g.bytes,g.length))return false;}
    const unsigned char notification[9]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xc3};unsigned char actualNotification[9];
    if(!bytes(image+0x43b47c0,actualNotification,9)||memcmp(actualNotification,notification,9))return false;
    unsigned char call[16];const unsigned char tail[11]={0xe8,0xb3,0xc8,0x71,0,0x48,0x8d,0x4c,0x24,0x30,0xe8};
    if(!bytes(image+0x43ac173,call,16)||call[0]!=0xe8||memcmp(call+5,tail,11))return false;
    int32_t delta=0;memcpy(&delta,call+1,4);uintptr_t target=image+0x43ac178+delta;
    if(target==image+0x43a8bf0&&(requireEntrance||requireVar))return false;
    if(target!=image+0x43a8bf0){
        unsigned char jump[6];const unsigned char j[6]={0xff,0x25,0,0,0,0};
        if(!bytes(target,jump,6)||memcmp(jump,j,6)||!get(target+6,target))return false;
        HMODULE module=nullptr;char path[MAX_PATH];
        if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)target,&module)||!GetModuleFileNameA(module,path,MAX_PATH))return false;
        const char* leaf=strrchr(path,'\\');if(!leaf)return false;
        const bool isVar=!strncmp(leaf+1,"var_cabin",9),isEntrance=!strncmp(leaf+1,"entrance_props",14);
        if((requireVar&&!isVar)||(!isVar&&!isEntrance))return false;
        auto api=(unsigned(WINAPI*)())GetProcAddress(module,"Fifa16ModGetApiVersion");if(!api||api()!=1)return false;
        event("existing_entrance_callback_chained");
    }
    nextBuild=(BuildFn)target;memcpy(expectedCall,call,5);return true;
}
static void* allocateNear(uintptr_t origin){SYSTEM_INFO info{};GetSystemInfo(&info);const uintptr_t step=info.dwAllocationGranularity,a=origin&~(step-1);for(uintptr_t d=step;d<0x70000000;d+=step)for(int side=0;side<2;++side){if(side&&a<d+0x10000)continue;void* p=VirtualAlloc((void*)(side?a-d:a+d),4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);if(p)return p;}return nullptr;}
static bool patch(){
    HANDLE hs[256]{};size_t count=0,suspended=0;bool ok=true;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
    THREADENTRY32 e{};e.dwSize=sizeof(e);
    for(BOOL more=Thread32First(snapshot,&e);more;more=Thread32Next(snapshot,&e)){
        if(e.th32OwnerProcessID!=GetCurrentProcessId()||e.th32ThreadID==GetCurrentThreadId())continue;
        if(count==256){ok=false;break;}HANDLE h=OpenThread(THREAD_SUSPEND_RESUME,FALSE,e.th32ThreadID);if(!h){if(GetLastError()==ERROR_INVALID_PARAMETER)continue;ok=false;break;}hs[count++]=h;
    }CloseHandle(snapshot);
    void* at=(void*)(image+0x43ac173);DWORD old=0,ignored=0;bool writable=false;
    if(ok){writable=VirtualProtect(at,5,PAGE_EXECUTE_READWRITE,&old)!=0;ok=writable;}
    if(ok)for(;suspended<count;++suspended)if(SuspendThread(hs[suspended])==(DWORD)-1){ok=false;break;}
    if(ok&&memcmp(at,expectedCall,5))ok=false;
    if(ok){memcpy(at,appliedCall,5);FlushInstructionCache(GetCurrentProcess(),at,5);}
    while(suspended)ResumeThread(hs[--suspended]);if(writable)VirtualProtect(at,5,old,&ignored);
    for(size_t i=0;i<count;++i)CloseHandle(hs[i]);return ok;
}
static DWORD WINAPI worker(void*){
    for(unsigned i=0;i<600&&!stopping;++i){
        if(!signatures()){
            if(i%25==0){char message[192];_snprintf_s(message,sizeof(message),_TRUNCATE,"hook_pending entrance_required=%u var_required=%u reason=native_code_or_previous_builder_not_ready",(unsigned)requireEntrance,(unsigned)requireVar);event(message);}
            Sleep(200);continue;
        }
        auto relay=(unsigned char*)allocateNear(image+0x43ac173);if(!relay){event("relay_allocation_failed");return 0;}
        const unsigned char jump[6]={0xff,0x25,0,0,0,0};const uintptr_t target=(uintptr_t)buildHook;memcpy(relay,jump,6);memcpy(relay+6,&target,8);
        DWORD ignored=0;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&ignored)){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        const int64_t rel=(int64_t)(uintptr_t)relay-(int64_t)(image+0x43ac178);if(rel<INT32_MIN||rel>INT32_MAX){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        appliedCall[0]=0xe8;const int32_t d=(int32_t)rel;memcpy(appliedCall+1,&d,4);
        if(!patch()){VirtualFree(relay,0,MEM_RELEASE);Sleep(200);continue;}
        event("installed smoke_machine static_rx3 machines=20 native_builder_chain dedicated_type16 appearance1");
        // Lua availability is retried on the scene thread, including future VMs.
        return 0;
    }event("signature_conflict_or_timeout");return 0;
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* root){
    if(!root||InterlockedCompareExchange(&started,1,0))return FALSE;
    _snprintf_s(logPath,MAX_PATH,_TRUNCATE,"%s\\..\\logs\\smoke_machine.log",root);
    _snprintf_s(iniPath,MAX_PATH,_TRUNCATE,"%s\\smoke_machine\\smoke_machine.ini",root);
    _snprintf_s(luaPath,MAX_PATH,_TRUNCATE,"%s\\smoke_machine\\smoke_machine.lua",root);
    // The mod loader starts workers asynchronously. When entrance props are
    // enabled, wait for their hook before chaining so neither module can win
    // a startup race and prevent the other from installing.
    char enabledPath[MAX_PATH];_snprintf_s(enabledPath,MAX_PATH,_TRUNCATE,"%s\\enabled.txt",root);
    FILE* listFile=nullptr;
    if(!fopen_s(&listFile,enabledPath,"rb")&&listFile){char line[512];while(fgets(line,sizeof(line),listFile)){char* p=line;while(*p==' '||*p=='\t')++p;for(char* c=p;*c;++c)if(*c=='/')*c='\\';if(*p!='#'&&strstr(p,"entrance_props\\"))requireEntrance=true;if(*p!='#'&&strstr(p,"var_cabin\\"))requireVar=true;}fclose(listFile);}
    event("loading_policy lua_activation=scene_thread retry_vm=1 retry_missing_prototype=1 padding_guard=executed_bytes");
    _snprintf_s(presentationPath,MAX_PATH,_TRUNCATE,"%s\\..\\config\\match_presentation.ini",root);
    _snprintf_s(pyroPath,MAX_PATH,_TRUNCATE,"%s\\stadium_pyrotechnics\\pyro.ini",root);
    char gameFile[MAX_PATH]={};
    if(GetModuleFileNameA(nullptr,gameFile,MAX_PATH)){
        char* end=strrchr(gameFile,'\\');if(end){
            *end=0;char modelPath[MAX_PATH],texturePath[MAX_PATH],message[160];
            _snprintf_s(modelPath,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\smoke_machine\\model.rx3",gameFile);
            _snprintf_s(texturePath,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\smoke_machine\\textures.rx3",gameFile);
            _snprintf_s(message,sizeof(message),_TRUNCATE,"asset_files model=%u textures=%u",GetFileAttributesA(modelPath)!=INVALID_FILE_ATTRIBUTES,GetFileAttributesA(texturePath)!=INVALID_FILE_ATTRIBUTES);event(message);
        }
    }
    image=(uintptr_t)GetModuleHandleA(nullptr);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
    if(!get(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||!get(image+(uintptr_t)dos.e_lfanew,nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return FALSE;
    HMODULE pinned=nullptr;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
    HANDLE h=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!h)return FALSE;CloseHandle(h);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){InterlockedExchange(&stopping,1);event("stop_requested machines_hidden_until_restart");return TRUE;}
BOOL WINAPI DllMain(HINSTANCE dll,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(dll);return TRUE;}
