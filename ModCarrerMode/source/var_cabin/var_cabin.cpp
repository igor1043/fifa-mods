#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <math.h>
#include "../common/scene_lua.h"
#include "../common/preload_status.h"
using BuildFn=void(__fastcall*)(void*);
static uintptr_t image;
static BuildFn nextBuild;
static LONG started,stopping,busy,luaReady;
static char logPath[MAX_PATH],iniPath[MAX_PATH],luaPath[MAX_PATH];
static bool enabled=true,resourceRequested=false,shadowRequested=false,fault=false,placed=false,requireEntrance=false;
static SceneLuaLifecycle luaLifecycle;
static uint64_t nextCreate=0;
static LONG sceneContentions;
static uintptr_t owner=0,prototype=0,shadow=0,prototypeState=0;
static float xCm=800,zCm=-3800,yCm=2,yaw=0;
static uint64_t nextConfig=0,nextDiagnostic=0;
static uint64_t nextCompetition=0;
static int competitionId=-1;
alignas(16) static unsigned char scratch[129*0x50],record[0x50];
static unsigned char expectedCall[5],appliedCall[5];
static void event(const char* msg){FILE* f=nullptr;if(!fopen_s(&f,logPath,"ab")&&f){fprintf(f,"%llu pid=%lu thread=%lu %s\n",GetTickCount64(),GetCurrentProcessId(),GetCurrentThreadId(),msg);fclose(f);}}
template<class T>static bool get(uintptr_t a,T& v){SIZE_T n=0;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,&v,sizeof(v),&n)&&n==sizeof(v);}
static bool bytes(uintptr_t a,void* b,size_t size){SIZE_T n=0;return a&&ReadProcessMemory(GetCurrentProcess(),(void*)a,b,size,&n)&&n==size;}
struct Vector{uintptr_t begin,end,capacity;};
static bool vector(uintptr_t at,size_t stride,Vector& v,size_t& n){
    if(!get(at,v))return false;
    if(!v.begin&&!v.end&&!v.capacity){n=0;return true;}
    if(v.begin<0x10000||v.end<v.begin||v.capacity<v.end||(v.end-v.begin)%stride||(v.capacity-v.begin)%stride||(v.capacity-v.begin)/stride>1024)return false;
    n=(v.end-v.begin)/stride;return n<=128;
}
static float setting(const char* name,float fallback,float limit){char b[64];GetPrivateProfileStringA("var_cabin",name,"",b,sizeof(b),iniPath);if(!b[0])return fallback;float v=(float)atof(b);return isfinite(v)&&fabsf(v)<=limit?v:fallback;}
static void config(){
    const uint64_t now=GetTickCount64();if(now<nextConfig)return;nextConfig=now+1000;
    enabled=GetPrivateProfileIntA("var_cabin","enabled",1,iniPath)!=0;
    xCm=setting("x_cm",800,5500);zCm=setting("z_cm",-3800,7000);yCm=setting("ground_lift_cm",2,20);yaw=setting("yaw_radians",0,7);
}
static bool console(const char* script,size_t size){
    uintptr_t lua=0,globals=0;int tag=0;
    if(!get(image+0x3613fd0,lua)||!get(lua+0x80,tag)||tag!=5||!get(lua+0x78,globals)||!globals)return false;
    __try{((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,size,"var_cabin_native");return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){event("lua_console_fault");return false;}
}
static bool activateLua(){
    static char script[16384];FILE* f=nullptr;
    if(fopen_s(&f,luaPath,"rb")||!f)return false;
    const char prefix[]="if not FIFA16_VAR_CABIN_LUA_V4 then ";memcpy(script,prefix,sizeof(prefix)-1);
    const size_t n=fread(script+sizeof(prefix)-1,1,sizeof(script)-256,f);const bool ok=!ferror(f)&&feof(f);fclose(f);if(!ok)return false;
    const char suffix[]="\nend; if FIFA16_VAR_CABIN_LUA_V4 then FIFA16_VAR_CABIN_HOOK_READY=true end";
    memcpy(script+sizeof(prefix)-1+n,suffix,sizeof(suffix));return console(script,sizeof(prefix)-1+n+sizeof(suffix)-1);
}
static bool luaMarkers(uintptr_t globals){
    return globals&&scene_lua_flag(globals,"FIFA16_VAR_CABIN_LUA_V4")&&scene_lua_flag(globals,"FIFA16_VAR_CABIN_HOOK_READY");
}
static void refreshLua(){
    const uint64_t now=GetTickCount64();if(now<luaLifecycle.nextCheck)return;
    const auto snapshot=scene_lua_snapshot(image);
    const bool changed=snapshot.vm!=luaLifecycle.current.vm||snapshot.globals!=luaLifecycle.current.globals;
    const bool known=luaMarkers(snapshot.globals),lost=luaLifecycle.ready&&!known;
    luaLifecycle.sample(now,snapshot);
    if(changed||lost){
        owner=prototype=shadow=prototypeState=0;resourceRequested=shadowRequested=fault=placed=false;
        nextCreate=nextCompetition=0;competitionId=-1;
        event(changed?"lua_context_changed scene_resources_rearmed":"lua_markers_lost scene_resources_rearmed");
    }
    if(luaLifecycle.should_activate(now,known)){
        activateLua();const auto after=scene_lua_snapshot(image);
        luaLifecycle.ready=after.vm==snapshot.vm&&after.globals==snapshot.globals&&luaMarkers(after.globals);
        if(luaLifecycle.ready)event("lua_ready scene_thread verified_markers");
    }
    InterlockedExchange(&luaReady,luaLifecycle.ready?1:0);
}
// Lua 5.1 layout already used by the mascot mod. Read only on the SLE scene
// thread, bound every table scan, and reject missing or malformed data.
struct LuaValue{uint64_t bits;int tag,padding;};
struct LuaNode{LuaValue value,key;uintptr_t next;};
static_assert(sizeof(LuaValue)==16&&sizeof(LuaNode)==40,"Lua 5.1 x64 layout");
static uintptr_t luaField(uintptr_t table,const char* key){
    unsigned char type=0,power=0;uintptr_t nodes=0;
    if(!get(table+8,type)||type!=5||!get(table+11,power)||power>16||!get(table+32,nodes)||!nodes)return 0;
    const size_t length=strlen(key),count=(size_t)1<<power;if(length>=64)return 0;
    for(size_t i=0;i<count;++i){
        LuaNode node{};size_t textLength=0;char text[64];const uintptr_t at=nodes+i*sizeof(node);
        if(!get(at,node))return 0;
        if(node.key.tag!=4||!get((uintptr_t)node.key.bits+16,textLength)||textLength!=length)continue;
        if(bytes((uintptr_t)node.key.bits+24,text,length)&&!memcmp(text,key,length))return at;
    }
    return 0;
}
static uintptr_t luaTable(uintptr_t value){LuaValue v{};return get(value,v)&&v.tag==5?(uintptr_t)v.bits:0;}
static uintptr_t luaRow(uintptr_t table,unsigned index){
    int size=0;uintptr_t array=0;LuaValue item{};
    if(index>=176||!get(table+56,size)||size<0||size>4096)return 0;
    if(index>0&&index<=(unsigned)size&&get(table+24,array)&&array&&get(array+(index-1)*16,item)&&item.tag==5)return (uintptr_t)item.bits;
    unsigned char power=0;uintptr_t nodes=0;
    if(!get(table+11,power)||power>16||!get(table+32,nodes)||!nodes)return 0;
    for(size_t i=0;i<((size_t)1<<power);++i){
        LuaNode node{};double key=0;if(!get(nodes+i*sizeof(node),node))return 0;
        if(node.key.tag!=3||node.value.tag!=5)continue;memcpy(&key,&node.key.bits,8);
        if(key==(double)index)return (uintptr_t)node.value.bits;
    }
    return 0;
}
static int luaInteger(uintptr_t table,const char* key){
    LuaValue v{};double number=0;const uintptr_t field=luaField(table,key);
    if(!field||!get(field,v)||v.tag!=3)return -1;memcpy(&number,&v.bits,8);
    return isfinite(number)&&number>=-1&&number<=1000000&&number==floor(number)?(int)number:-1;
}
static int readCompetition(unsigned index){
    uintptr_t lua=0,globals=0;int tag=0;
    if(!get(image+0x3613fd0,lua)||!get(lua+0x80,tag)||tag!=5||!get(lua+0x78,globals))return -1;
    const uintptr_t db=luaTable(luaField(globals,"db")),sles=luaTable(luaField(db,"sle"));
    const uintptr_t row=luaRow(sles,index);
    return luaInteger(row,"isVarCabin")==1?luaInteger(row,"varCabinCompetitionId"):-1;
}
static bool competitionAllowed(int id){return id==7||id==83;}
static void refreshCompetition(uintptr_t state){
    const uint64_t now=GetTickCount64();if(now<nextCompetition)return;nextCompetition=now+1000;
    competitionId=-1;unsigned index=0;if(!get(state+0x4c,index)||index>=176)return;
    char script[128];const int size=_snprintf_s(script,sizeof(script),_TRUNCATE,"FIFA16_VAR_CABIN_REFRESH_COMPETITION(%u)",index);
    if(size>0&&console(script,(size_t)size))competitionId=readCompetition(index);
}
static bool ownPrototype(void* self,uintptr_t& p,uintptr_t& state,uintptr_t& base){
    Vector v{};size_t n=0;uint16_t type=0,variation=0;unsigned rna=0;
    if(!vector((uintptr_t)self+0x30*4,8,v,n)||n!=2||!get(v.begin,base)||!get(v.begin+8,p)||p==base)return false;
    if(!get(base+12,type)||type!=3||!get(base+14,variation)||variation!=0)return false;
    return get(p+12,type)&&type==3&&get(p+14,variation)&&variation==1&&get(p+16,state)&&get(state+0x4c,rna)&&rna<176;
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
            if(!initialized||p==prototype){
                uintptr_t vt=0,load=0;if(!get(p,vt)||!get(vt+0x38,load)||load!=image+0x43b4530)return false;
                // The engine may have initialized our variation before its Lua
                // gate was set. Refresh that private resource on this callback.
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
static void position(float h){const float p[4]={xCm,h,zCm,yaw};memcpy(record+0x20,p,16);memcpy(record+0x30,p,16);}
static void __fastcall buildHook(void* self){
    if(InterlockedCompareExchange(&busy,1,0)){
        if(InterlockedIncrement(&sceneContentions)==1)event("scene_callback_overlap_or_reentry observed");
        nextBuild(self);return;
    }
    Vector saved{},temporary{};size_t n=0,normalBytes=0;unsigned mask=0;bool swapped=false,maskSaved=false;float submitted=-3000;
    ScenePreloadState loadState=ScenePreloadState::Waiting;
    const uintptr_t list=(uintptr_t)self+0x30*(3+0x2f),maskAt=(uintptr_t)self+0x4f604;
    __try{
        config();refreshLua();
        uintptr_t p=0,s=0,b=0;
        bool hasPrototype=luaReady&&ownPrototype(self,p,s,b);
        if(luaReady&&!hasPrototype&&GetTickCount64()>=nextCreate){
            nextCreate=GetTickCount64()+500;
            // The same factory/AddSubObject path as normal startup, on the render
            // thread. No copied native resources and no concurrent vector mutation.
            static const char create[]="FIFA16_VAR_CABIN_CREATE_LIVE()";
            console(create,sizeof(create)-1);
            hasPrototype=ownPrototype(self,p,s,b);
        }
        if(hasPrototype&&vector(list,0x50,saved,n)&&n<=127){
            normalBytes=n*0x50;
            if(!normalBytes||bytes(saved.begin,scratch,normalBytes)){
                // Any native random use of the reserved appearance keeps the
                // original platform camera. The private record alone uses cabin.
                for(size_t i=0;i<n;++i){auto r=scratch+i*0x50;if(r[0x42]==1){r[0x42]=0;r[0x40]=r[0x41]=0xff;r[0x45]=0;}}
                if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
                if(owner!=(uintptr_t)self||prototype!=p||prototypeState!=s||shadow!=b){
                    owner=(uintptr_t)self;prototype=p;prototypeState=s;shadow=b;resourceRequested=shadowRequested=fault=placed=false;
                    competitionId=-1;nextCompetition=0;
                    memset(record,0,sizeof(record));record[0x40]=record[0x41]=0xff;record[0x42]=1;event("static_prototype_confirmed type=3 variation=1");
                    unsigned rna=0;char update[96];
                    if(get(s+0x4c,rna)&&rna<176){
                        const int length=_snprintf_s(update,sizeof(update),_TRUNCATE,"SleUpdate(%u)",rna);
                        if(length>0)console(update,(size_t)length);
                    }
                }
                refreshCompetition(s);
                const bool a=ready(p,resourceRequested,"model_texture_requested");const bool c=ready(b,shadowRequested,"shadow_dependency_requested");
                loadState=a&&c?ScenePreloadState::Ready:ScenePreloadState::Loading;
                if(a&&c&&get(maskAt,mask)){
                    submitted=enabled&&!stopping&&competitionAllowed(competitionId)?yCm:-3000;position(submitted);memcpy(scratch+normalBytes,record,0x50);
                    temporary={(uintptr_t)scratch,(uintptr_t)scratch+normalBytes+0x50,(uintptr_t)scratch+sizeof(scratch)};
                    memcpy((void*)list,&temporary,sizeof(temporary));swapped=true;*(unsigned*)maskAt=mask|(1u<<3);maskSaved=true;
                }
            }
        }
        nextBuild(self);
    }__finally{
        if(swapped){
            if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
            memcpy(record,scratch+normalBytes,0x50);position(submitted);memcpy((void*)list,&saved,sizeof(saved));
            uint16_t binding=0xffff;memcpy(&binding,record+0x40,2);
            if(binding!=0xffff&&!placed){event("cabin_placed native_binding_assigned resources_ready");placed=true;}
            const uint64_t now=GetTickCount64();if(now>=nextDiagnostic){nextDiagnostic=now+5000;char msg[240];_snprintf_s(msg,sizeof(msg),_TRUNCATE,"position_cm=%g,%g,%g yaw=%g binding=%u normal_platforms=%zu enabled=%u competition_id=%d competition_allowed=%u",xCm,submitted,zCm,yaw,binding,n,(unsigned)enabled,competitionId,(unsigned)competitionAllowed(competitionId));event(msg);}
        }
        if(maskSaved)*(unsigned*)maskAt=mask;
        scene_preload_publish(2,!enabled?ScenePreloadState::Skipped:fault?ScenePreloadState::Failed:loadState);
        InterlockedExchange(&busy,0);
    }
}
static bool signatures(){
    struct Guard{uintptr_t rva;unsigned char bytes[16];};
    const Guard guards[]={
        {0x43b43e0,{0x48,0x8b,0x51,0x10,0xb0,0x01,0x41,0xb8,0x0f,0x0b,0x4e,0xc3,0x48,0x83,0xc2,0x20}},
        {0x43b4640,{0x57,0x48,0x83,0xec,0x70,0x48,0x8b,0x05,0x14,0x3e,0xee,0xfe,0x48,0x31,0xe0,0x48}},
        {0x4ac35e0,{0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x30,0x48}}
    };
    for(const auto& g:guards){unsigned char a[16];if(!bytes(image+g.rva,a,16)||memcmp(a,g.bytes,16))return false;}
    const unsigned char notification[9]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xc3};unsigned char actualNotification[9];
    if(!bytes(image+0x43b47c0,actualNotification,9)||memcmp(actualNotification,notification,9))return false;
    unsigned char call[16];const unsigned char tail[11]={0xe8,0xb3,0xc8,0x71,0,0x48,0x8d,0x4c,0x24,0x30,0xe8};
    if(!bytes(image+0x43ac173,call,16)||call[0]!=0xe8||memcmp(call+5,tail,11))return false;
    int32_t delta=0;memcpy(&delta,call+1,4);uintptr_t target=image+0x43ac178+delta;
    if(target==image+0x43a8bf0&&requireEntrance)return false;
    if(target!=image+0x43a8bf0){
        unsigned char jump[6];const unsigned char j[6]={0xff,0x25,0,0,0,0};
        if(!bytes(target,jump,6)||memcmp(jump,j,6)||!get(target+6,target))return false;
        HMODULE module=nullptr;char path[MAX_PATH];
        if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)target,&module)||!GetModuleFileNameA(module,path,MAX_PATH))return false;
        const char* leaf=strrchr(path,'\\');if(!leaf||strncmp(leaf+1,"entrance_props",14))return false;
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
        if(!signatures()){Sleep(200);continue;}
        auto relay=(unsigned char*)allocateNear(image+0x43ac173);if(!relay){event("relay_allocation_failed");return 0;}
        const unsigned char jump[6]={0xff,0x25,0,0,0,0};const uintptr_t target=(uintptr_t)buildHook;memcpy(relay,jump,6);memcpy(relay+6,&target,8);
        DWORD ignored=0;if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&ignored)){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        const int64_t rel=(int64_t)(uintptr_t)relay-(int64_t)(image+0x43ac178);if(rel<INT32_MIN||rel>INT32_MAX){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        appliedCall[0]=0xe8;const int32_t d=(int32_t)rel;memcpy(appliedCall+1,&d,4);
        if(!patch()){VirtualFree(relay,0,MEM_RELEASE);Sleep(200);continue;}
        event("installed var_cabin v4 scene_thread_lua verified_readiness retry_context competition_filter=7,83");return 0;
    }event("signature_conflict_or_timeout");return 0;
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* root){
    if(!root||InterlockedCompareExchange(&started,1,0))return FALSE;
    scene_preload_publish(2,ScenePreloadState::Waiting);
    _snprintf_s(logPath,MAX_PATH,_TRUNCATE,"%s\\..\\logs\\var_cabin.log",root);
    _snprintf_s(iniPath,MAX_PATH,_TRUNCATE,"%s\\var_cabin\\var_cabin.ini",root);
    _snprintf_s(luaPath,MAX_PATH,_TRUNCATE,"%s\\var_cabin\\var_cabin.lua",root);
    // The mod loader starts workers asynchronously. When entrance props are
    // enabled, wait for their hook before chaining so neither module can win
    // a startup race and prevent the other from installing.
    char enabledPath[MAX_PATH];_snprintf_s(enabledPath,MAX_PATH,_TRUNCATE,"%s\\enabled.txt",root);
    FILE* listFile=nullptr;
    if(!fopen_s(&listFile,enabledPath,"rb")&&listFile){char line[512];while(fgets(line,sizeof(line),listFile)){char* p=line;while(*p==' '||*p=='\t')++p;if(*p!='#'&&strstr(p,"entrance_props\\")){requireEntrance=true;break;}}fclose(listFile);}
    image=(uintptr_t)GetModuleHandleA(nullptr);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
    if(!get(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||!get(image+(uintptr_t)dos.e_lfanew,nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return FALSE;
    HMODULE pinned=nullptr;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
    HANDLE h=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!h)return FALSE;CloseHandle(h);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){InterlockedExchange(&stopping,1);event("stop_requested cabin_hidden_until_restart");return TRUE;}
BOOL WINAPI DllMain(HINSTANCE dll,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(dll);return TRUE;}
