#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "stand_layout.h"
#include "stand_assets.h"
#include "../common/scene_lua.h"
#include "../common/scene_resource_cycle.h"
#include "../stadium_pyrotechnics/presentation.h"
#pragma comment(lib,"bcrypt.lib")

using BuildFn=void(__fastcall*)(void*);
static uintptr_t image;
static BuildFn nextBuild;
static LONG stopping,busy,ballHeightUnits=111252;
static char logPath[MAX_PATH],iniPath[MAX_PATH],luaPath[MAX_PATH],gameRoot[MAX_PATH],contextPath[MAX_PATH];
static bool enabled=true,visible=false,fault=false,placed=false,retiring=false;
static const char* requiredBuilder=nullptr;
static uintptr_t owner=0,prototype=0,shadow=0,prototypeState=0;
static SceneResourceCycle modelCycle,shadowCycle;
static SceneLuaLifecycle luaLifecycle;
static PyroMatchSession session;
static int desired=-1,loaded=-1;
static unsigned competition=0,roundId=0,serial=0;
static uint64_t nextConfig=0,nextScene=0,nextCreate=0,nextDiagnostic=0;
static bool validated[sizeof(standAssets)/sizeof(standAssets[0])];
static uint64_t nextAssetCheck[sizeof(standAssets)/sizeof(standAssets[0])];
alignas(16) static unsigned char scratch[(128+SPARE_BALLS)*0x50],records[SPARE_BALLS][0x50];
static unsigned char expectedCall[5],appliedCall[5];

static void event(const char* message){FILE* f=nullptr;if(!fopen_s(&f,logPath,"ab")&&f){fprintf(f,"%llu pid=%lu thread=%lu %s\n",GetTickCount64(),GetCurrentProcessId(),GetCurrentThreadId(),message);fclose(f);}}
template<class T>static bool get(uintptr_t at,T& value){SIZE_T n=0;return at&&ReadProcessMemory(GetCurrentProcess(),(void*)at,&value,sizeof(value),&n)&&n==sizeof(value);}
static bool bytes(uintptr_t at,void* out,size_t size){SIZE_T n=0;return at&&ReadProcessMemory(GetCurrentProcess(),(void*)at,out,size,&n)&&n==size;}
struct Vector{uintptr_t begin,end,capacity;};
static bool vector(uintptr_t at,size_t stride,Vector& v,size_t& n){
 if(!get(at,v))return false;
 if(!v.begin&&!v.end&&!v.capacity){n=0;return true;}
 if(v.begin<0x10000||v.end<v.begin||v.capacity<v.end||(v.end-v.begin)%stride||(v.capacity-v.begin)%stride||(v.capacity-v.begin)/stride>1024)return false;
 n=(v.end-v.begin)/stride;return n<=128;
}
static void ground(){InterlockedExchange(&ballHeightUnits,111252);}
extern "C" float standball_height(){return (float)InterlockedCompareExchange(&ballHeightUnits,0,0)/10000.0f;}
static int asset(const char* slug){for(unsigned i=0;i<sizeof(standAssets)/sizeof(standAssets[0]);++i)if(!strcmp(slug,standAssets[i].slug))return (int)i;return -1;}
static bool checkFile(const char* slug,const char* name,unsigned size,const char* expected){
 char path[MAX_PATH];if(_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\standball\\%s\\%s",gameRoot,slug,name)<0)return false;
 FILE* f=nullptr;if(fopen_s(&f,path,"rb")||!f)return false;
 BCRYPT_ALG_HANDLE algorithm=nullptr;BCRYPT_HASH_HANDLE hash=nullptr;unsigned char digest[32],block[65536];
 bool ok=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)>=0;
 if(ok)ok=BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)>=0;
 unsigned total=0;size_t n=0;
 while(ok&&(n=fread(block,1,sizeof(block),f))!=0){
  if(!total&&(n<16||memcmp(block,"RX3l",4))){ok=false;break;}
  total+=(unsigned)n;if(total>size){ok=false;break;}
  ok=BCryptHashData(hash,block,(ULONG)n,0)>=0;
 }
 ok=ok&&!ferror(f)&&total==size;if(ok)ok=BCryptFinishHash(hash,digest,sizeof(digest),0)>=0;
 if(hash)BCryptDestroyHash(hash);if(algorithm)BCryptCloseAlgorithmProvider(algorithm,0);fclose(f);
 if(ok){char actual[65];for(unsigned i=0;i<32;++i)sprintf_s(actual+i*2,3,"%02x",digest[i]);ok=!strcmp(actual,expected);}
 return ok;
}
static bool validate(int index){
 if(index<0)return false;if(validated[index])return true;
 const uint64_t now=GetTickCount64();if(now<nextAssetCheck[index])return false;nextAssetCheck[index]=now+5000;
 const auto& a=standAssets[index];
 const bool ok=checkFile(a.slug,"model.rx3",a.modelBytes,a.modelHash)&&checkFile(a.slug,"textures.rx3",a.textureBytes,a.textureHash);
 validated[index]=ok;if(!ok){char message[128];_snprintf_s(message,sizeof(message),_TRUNCATE,"asset_rejected variant=%s missing_or_hash_mismatch balls_remain_on_ground",a.slug);event(message);}
 return ok;
}
static bool console(const char* script,size_t length){
 const auto context=scene_lua_snapshot(image);if(!context.vm||!context.globals)return false;
 __try{((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,length,"standball_scene");return true;}
 __except(EXCEPTION_EXECUTE_HANDLER){event("lua_console_fault");return false;}
}
static void resetRecords(){memset(records,0,sizeof(records));for(unsigned i=0;i<SPARE_BALLS;++i){records[i][0x40]=records[i][0x41]=0xff;records[i][0x42]=1;stand_position(records[i],i,-3000);}placed=false;ground();}
static void refreshLua(){
 const uint64_t now=GetTickCount64();if(now<luaLifecycle.nextCheck)return;
 const auto context=scene_lua_snapshot(image);
 const bool changed=context.vm!=luaLifecycle.current.vm||context.globals!=luaLifecycle.current.globals;
 const bool marked=scene_lua_flag(context.globals,"FIFA16_STANDBALL_LUA_V1")&&scene_lua_flag(context.globals,"FIFA16_STANDBALL_HOOK_READY");
 const bool lost=luaLifecycle.ready&&!marked;luaLifecycle.sample(now,context);
 if(changed||lost){owner=prototype=shadow=prototypeState=0;modelCycle=shadowCycle=SceneResourceCycle{};loaded=-1;fault=retiring=false;nextCreate=0;resetRecords();event("lua_context_rearmed");}
 if(luaLifecycle.should_activate(now,marked)){
  // A future native startup can invoke CreateSleVariations before our builder.
  // Publish only a verified default before exposing the Lua resource redirects.
  const int initial=desired>=0?desired:asset("generic1");if(!validate(initial))return;
  char script[16384];FILE* f=nullptr;
  if(!fopen_s(&f,luaPath,"rb")&&f){
   const size_t n=fread(script,1,sizeof(script)-128,f);const bool complete=!ferror(f)&&feof(f);fclose(f);
   if(complete){char suffix[128];const int length=_snprintf_s(suffix,sizeof(suffix),_TRUNCATE,"\nif FIFA16_STANDBALL_LUA_V1 then FIFA16_STANDBALL_VARIANT='%s';FIFA16_STANDBALL_HOOK_READY=true end",standAssets[initial].slug);if(length>0){memcpy(script+n,suffix,(size_t)length);console(script,n+(size_t)length);}}
  }
  const auto after=scene_lua_snapshot(image);
  luaLifecycle.ready=after.vm==context.vm&&after.globals==context.globals&&scene_lua_flag(after.globals,"FIFA16_STANDBALL_LUA_V1")&&scene_lua_flag(after.globals,"FIFA16_STANDBALL_HOOK_READY");
  if(luaLifecycle.ready)event("lua_ready verified_scene_thread");
 }
}
static bool liveCompetition(unsigned home,unsigned away,unsigned& comp,unsigned& round){
 uintptr_t p=0;const unsigned offsets[]={504,3544,1712,80};
 if(!get(image+56170408,p)||p<0x10000)return false;
 for(unsigned offset:offsets)if(!get(p+offset,p)||p<0x10000)return false;
 unsigned h=0,a=0;return get(p+276,h)&&get(p+280,a)&&h==home&&a==away&&get(p+40,comp)&&get(p+44,round)&&comp<1000000&&round<1000000;
}
static unsigned friendlyCompetition(unsigned home,unsigned away){
 WIN32_FILE_ATTRIBUTE_DATA file{};FILETIME created{},exited{},kernel{},user{};
 if(!GetFileAttributesExA(contextPath,GetFileExInfoStandard,&file)||!GetProcessTimes(GetCurrentProcess(),&created,&exited,&kernel,&user)||CompareFileTime(&file.ftLastWriteTime,&created)<0)return 0;
 if(GetPrivateProfileIntA("selection","schema",0,contextPath)!=1||GetPrivateProfileIntA("selection","process_id",0,contextPath)!=GetCurrentProcessId()||
    GetPrivateProfileIntA("selection","home",0,contextPath)!=home||GetPrivateProfileIntA("selection","away",0,contextPath)!=away||
    GetPrivateProfileIntA("selection","competition",1,contextPath)||GetPrivateProfileIntA("selection","round",1,contextPath))return 0;
 char mode[64];GetPrivateProfileStringA("selection","mode","",mode,sizeof(mode),contextPath);
 return !strcmp(mode,"friendly_same_league")?GetPrivateProfileIntA("selection","asset",0,contextPath):0;
}
static int mapped(unsigned id){
 if(!id)return -1;char key[16],slug[32];_snprintf_s(key,sizeof(key),_TRUNCATE,"%u",id);
 GetPrivateProfileStringA("competitions",key,"",slug,sizeof(slug),iniPath);return asset(slug);
}
static void scene(){
 const uint64_t now=GetTickCount64();if(now<nextScene)return;nextScene=now+250;
 if(now>=nextConfig){nextConfig=now+1000;enabled=GetPrivateProfileIntA("standball","enabled",1,iniPath)!=0;}
 char page[64]={};uintptr_t p=0;const unsigned offsets[]={232,192,136,472};bool known=get(image+58757168,p)&&p;
 for(unsigned offset:offsets)if(known)known=get(p+offset,p)&&p;
 known=known&&get(p,page)&&memchr(page,0,sizeof(page));const auto kind=pyro_page(page,known,session.key!=0);
 visible=false;
 if(kind==PyroPage::Outside){session=PyroMatchSession{};desired=-1;ground();return;}
 if(kind==PyroPage::Unreadable)return;
 uintptr_t manager=0,world=0,game=0,registry=0,pairs=0;int key=0,count=0;
 if(!get(image+0x3517420,manager)||!get(manager,p)||p!=image+0x2226730||!get(manager+8,world)||!get(world,p)||p!=image+0x2225d90||
    !get(world+0x10,game)||!get(game,p)||p!=image+0x2309370||!get(game+0x20,registry)||!registry||
    !get(registry+8+15*32,key)||key!=15||!get(registry+8+15*32+16,count)||count!=2||!get(registry+8+15*32+24,pairs))return;
 int clubs[2]={};
 for(int i=0;i<2;++i){uintptr_t team=0,stats=0,teamOwner=0;int side=-1,club=0;
  if(!get(pairs+i*16+8,team)||!get(team,p)||p!=image+0x22fe9f0||!get(team+0x30,teamOwner)||teamOwner!=registry||
     !get(team+0x58,side)||side<0||side>1||clubs[side]||!get(team+0x50,stats)||!get(stats+0x80,club)||club<=0||club>1000000)return;
  clubs[side]=club;
 }
 if(kind==PyroPage::Match&&session.observe(registry,clubs[0],clubs[1]))++serial;
 if(!session.key||session.home!=clubs[0]||session.away!=clubs[1])return;
 unsigned comp=0,round=0;if(!liveCompetition((unsigned)clubs[0],(unsigned)clubs[1],comp,round))return;
 if(!comp&&!round)comp=friendlyCompetition((unsigned)clubs[0],(unsigned)clubs[1]);
 int choice=mapped(round);if(choice<0)choice=mapped(comp);
 if(choice<0){const unsigned variant=GetPrivateProfileIntA("standball","generic_variant",0,iniPath);choice=asset(variant==1?"generic1":variant==2?"generic2":serial%2?"generic1":"generic2");}
 if(choice!=desired||comp!=competition||round!=roundId){
  desired=choice;competition=comp;roundId=round;char message[192];
  _snprintf_s(message,sizeof(message),_TRUNCATE,"selection competition=%u round=%u variant=%s count=13",comp,round,standAssets[choice].slug);event(message);
 }
 visible=enabled&&pyro_can_continue(kind,true,true);
}
static bool ownPrototype(void* self,uintptr_t& p,uintptr_t& state,uintptr_t& base){
 Vector v{};size_t n=0;uint16_t type=0,variation=0;unsigned rna=0;
 if(!vector((uintptr_t)self+0x30*18,8,v,n)||n!=2||!get(v.begin,base)||!get(v.begin+8,p)||p==base)return false;
 if(!get(base+12,type)||type!=17||!get(base+14,variation)||variation!=0)return false;
 return get(p+12,type)&&type==17&&get(p+14,variation)&&variation==1&&get(p+16,state)&&state&&get(state+0x4c,rna)&&rna<176;
}
static bool ready(uintptr_t p,SceneResourceCycle& cycle,bool model){
 using Ready=unsigned char(__fastcall*)(void*);if(fault)return false;
 __try{
  const bool initialized=((Ready)(image+0x43b4500))((void*)p)!=0,loadedFlag=((Ready)(image+0x43b4520))((void*)p)!=0;
  if(cycle.refresh(initialized,loadedFlag)){resetRecords();if(model)loaded=-1;event("native_resource_cycle_rearmed");}
  if(!cycle.requested){
   if(model){
    if(desired<0||!validate(desired))return false;
    unsigned rna=0;if(!get(prototypeState+0x4c,rna)||rna>=176)return false;
    char script[160];const int n=_snprintf_s(script,sizeof(script),_TRUNCATE,"FIFA16_STANDBALL_VARIANT='%s';SleUpdate(%u)",standAssets[desired].slug,rna);
    if(n<=0||!console(script,(size_t)n))return false;loaded=desired;
   }
   if(!initialized){const int parameters[5]={-1,-1,-1,0,-1};((void(__fastcall*)(void*,const int*))(image+0x43b4640))((void*)p,parameters);}
   if(!initialized||model){
    uintptr_t vt=0,load=0;if(!get(p,vt)||!get(vt+0x38,load)||load!=image+0x43b4530)return false;
    ((void(__fastcall*)(void*,int))load)((void*)p,model&&initialized?1:0);
   }
   cycle.requested=true;event(model?"stand_model_and_textures_requested":"base_shadow_requested");
  }
  const bool lods=((Ready)(image+0x43b43e0))((void*)p)!=0;
  if(lods&&!((Ready)(image+0x43b4520))((void*)p))((void(__fastcall*)(void*))(image+0x43b47c0))((void*)p);
  const bool initNow=((Ready)(image+0x43b4500))((void*)p)!=0;
  const bool complete=initNow&&lods&&((Ready)(image+0x43b4520))((void*)p)!=0;cycle.complete(initNow,complete);return complete;
 }__except(EXCEPTION_EXECUTE_HANDLER){fault=true;ground();event("native_resource_fault supports_disabled_for_scene");return false;}
}
static void __fastcall buildHook(void* self){
 if(InterlockedCompareExchange(&busy,1,0)){nextBuild(self);return;}
 Vector saved{},temporary{};size_t n=0,normalBytes=0;unsigned mask=0;bool swapped=false,maskSaved=false,show=false;
 const uintptr_t list=(uintptr_t)self+0x30*(17+0x2f),maskAt=(uintptr_t)self+0x4f604;
 __try{
  scene();refreshLua();uintptr_t p=0,s=0,b=0;bool has=luaLifecycle.ready&&ownPrototype(self,p,s,b);
  if(luaLifecycle.ready&&!has&&!stopping&&GetTickCount64()>=nextCreate){nextCreate=GetTickCount64()+500;const char script[]="FIFA16_STANDBALL_CREATE_LIVE()";console(script,sizeof(script)-1);has=ownPrototype(self,p,s,b);}
  if(has&&vector(list,0x50,saved,n)){
   normalBytes=n*0x50;
   if(!normalBytes||bytes(saved.begin,scratch,normalBytes)){
    for(size_t i=0;i<n;++i){auto r=scratch+i*0x50;if(r[0x42]==1){r[0x42]=0;r[0x40]=r[0x41]=0xff;r[0x45]=0;}}
    if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
    if(owner!=(uintptr_t)self||prototype!=p||prototypeState!=s||shadow!=b){
     owner=(uintptr_t)self;prototype=p;prototypeState=s;shadow=b;modelCycle=shadowCycle=SceneResourceCycle{};fault=retiring=false;loaded=-1;resetRecords();event("private_static_prototype type=17 variation=1");
    }
    const bool a=ready(p,modelCycle,true),c=ready(b,shadowCycle,false);
    retiring=a&&loaded!=desired;
    if(a&&c&&get(maskAt,mask)){
     show=visible&&!stopping&&!retiring&&loaded>=0;
     for(unsigned i=0;i<SPARE_BALLS;++i){stand_position(records[i],i,show?0.0f:-3000.0f);memcpy(scratch+normalBytes+i*0x50,records[i],0x50);}
     temporary={(uintptr_t)scratch,(uintptr_t)scratch+normalBytes+SPARE_BALLS*0x50,(uintptr_t)scratch+sizeof(scratch)};
     memcpy((void*)list,&temporary,sizeof(temporary));swapped=true;*(unsigned*)maskAt=mask|(1u<<17);maskSaved=true;
    }
   }
  }
  if(!swapped)ground();nextBuild(self);
 }__finally{
  if(swapped){
   if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);bool bound=true;
   for(unsigned i=0;i<SPARE_BALLS;++i){memcpy(records[i],scratch+normalBytes+i*0x50,0x50);uint16_t binding=0xffff;memcpy(&binding,records[i]+0x40,2);bound=bound&&binding!=0xffff;}
   memcpy((void*)list,&saved,sizeof(saved));
   if(show&&bound){InterlockedExchange(&ballHeightUnits,(LONG)lroundf(standAssets[loaded].ballHeight*10000));if(!placed){char message[160];_snprintf_s(message,sizeof(message),_TRUNCATE,"stands_placed count=13 variant=%s ball_center_cm=%.4f",standAssets[loaded].slug,standAssets[loaded].ballHeight);event(message);placed=true;}}
   else ground();
   if(retiring){modelCycle=SceneResourceCycle{};loaded=-1;retiring=false;resetRecords();event("previous_supports_hidden_before_variant_reload");}
  }
  if(maskSaved)*(unsigned*)maskAt=mask;
  const uint64_t now=GetTickCount64();if(now>=nextDiagnostic){nextDiagnostic=now+5000;char message[160];_snprintf_s(message,sizeof(message),_TRUNCATE,"supports visible=%u lua=%u submitted=%u loaded=%d desired=%d fault=%u",(unsigned)show,(unsigned)luaLifecycle.ready,(unsigned)swapped,loaded,desired,(unsigned)fault);event(message);}
  InterlockedExchange(&busy,0);
 }
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
static bool signatures(){
 struct Guard{uintptr_t rva;unsigned char code[16];size_t length;};
 const Guard guards[]={
  {0x43b4500,{0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x4a,0xc3},9},
  {0x43b4520,{0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x48,0xc3},9},
  {0x43b4530,{0x57,0x48,0x83,0xec,0x20,0x48,0x89,0xcf,0x48,0x8b,0x49,0x10,0x80,0x79,0x4a,0x00},16},
  {0x43b43e0,{0x48,0x8b,0x51,0x10,0xb0,0x01,0x41,0xb8,0x0f,0x0b,0x4e,0xc3,0x48,0x83,0xc2,0x20},16},
  {0x43b4640,{0x57,0x48,0x83,0xec,0x70,0x48,0x8b,0x05,0x14,0x3e,0xee,0xfe,0x48,0x31,0xe0,0x48},16},
  {0x43b47c0,{0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xc3},9},
  {0x4ac35e0,{0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x30,0x48},16}
 };
 for(const auto& g:guards){unsigned char actual[16];if(!bytes(image+g.rva,actual,g.length)||memcmp(actual,g.code,g.length))return false;}
 unsigned char call[16];const unsigned char tail[11]={0xe8,0xb3,0xc8,0x71,0,0x48,0x8d,0x4c,0x24,0x30,0xe8};
 if(!bytes(image+0x43ac173,call,sizeof(call))||call[0]!=0xe8||memcmp(call+5,tail,sizeof(tail)))return false;
 int32_t delta=0;memcpy(&delta,call+1,4);uintptr_t target=image+0x43ac178+delta;
 if(target==image+0x43a8bf0){if(requiredBuilder)return false;}
 else{
  unsigned char actual[6];const unsigned char jump[6]={0xff,0x25,0,0,0,0};
  if(!bytes(target,actual,6)||memcmp(actual,jump,6)||!get(target+6,target))return false;
  HMODULE module=nullptr;char path[MAX_PATH];
  if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)target,&module)||!GetModuleFileNameA(module,path,MAX_PATH))return false;
  const char* name=strrchr(path,'\\');if(!name)return false;++name;
  if(requiredBuilder){if(strcmp(name,requiredBuilder))return false;}
  else if(strcmp(name,"smoke_machine.dll")&&strcmp(name,"var_cabin.dll")&&strcmp(name,"entrance_props.dll"))return false;
  auto api=(unsigned(WINAPI*)())GetProcAddress(module,"Fifa16ModGetApiVersion");if(!api||api()!=1)return false;
 }
 nextBuild=(BuildFn)target;memcpy(expectedCall,call,5);return true;
}
static DWORD WINAPI worker(void*){
 for(unsigned i=0;i<600&&!stopping;++i){
  if(!signatures()){Sleep(200);continue;}
  auto relay=(unsigned char*)allocateNear(image+0x43ac173);if(!relay){event("relay_allocation_failed");return 0;}
  const unsigned char jump[6]={0xff,0x25,0,0,0,0};const uintptr_t target=(uintptr_t)buildHook;
  memcpy(relay,jump,6);memcpy(relay+6,&target,8);DWORD ignored=0;
  if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&ignored)){VirtualFree(relay,0,MEM_RELEASE);return 0;}
  const int64_t rel=(int64_t)(uintptr_t)relay-(int64_t)(image+0x43ac178);
  if(rel<INT32_MIN||rel>INT32_MAX){VirtualFree(relay,0,MEM_RELEASE);return 0;}
  appliedCall[0]=0xe8;const int32_t d=(int32_t)rel;memcpy(appliedCall+1,&d,4);
  if(!patch()){VirtualFree(relay,0,MEM_RELEASE);Sleep(200);continue;}
  event("installed standball v1 native_builder_chain type=17 variation=1 supports=13");return 0;
 }event("signature_conflict_or_builder_timeout supports_unavailable");return 0;
}
extern "C" unsigned char standball_start(const char* root){
 if(!root)return false;
 _snprintf_s(logPath,MAX_PATH,_TRUNCATE,"%s\\..\\logs\\standball.log",root);
 _snprintf_s(iniPath,MAX_PATH,_TRUNCATE,"%s\\multiball_visual\\standball.ini",root);
 _snprintf_s(luaPath,MAX_PATH,_TRUNCATE,"%s\\multiball_visual\\standball.lua",root);
 if(!GetModuleFileNameA(nullptr,gameRoot,MAX_PATH))return false;char* slash=strrchr(gameRoot,'\\');if(!slash)return false;*slash=0;
 _snprintf_s(contextPath,MAX_PATH,_TRUNCATE,"%s\\runtime\\entrance_props_context.ini",gameRoot);
 char path[MAX_PATH];_snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\enabled.txt",root);FILE* f=nullptr;
 bool smoke=false,var=false,entrance=false;
 if(!fopen_s(&f,path,"rb")&&f){char line[512];while(fgets(line,sizeof(line),f)){
  char* p=line;while(*p==' '||*p=='\t')++p;if(*p=='#')continue;for(char* c=p;*c;++c)if(*c=='/')*c='\\';
  smoke=smoke||strstr(p,"smoke_machine\\")!=nullptr;var=var||strstr(p,"var_cabin\\")!=nullptr;entrance=entrance||strstr(p,"entrance_props\\")!=nullptr;
 }fclose(f);}
 requiredBuilder=smoke?"smoke_machine.dll":var?"var_cabin.dll":entrance?"entrance_props.dll":nullptr;
 image=(uintptr_t)GetModuleHandleA(nullptr);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
 if(!get(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||!get(image+(uintptr_t)dos.e_lfanew,nt)||nt.Signature!=IMAGE_NT_SIGNATURE||nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64)return false;
 resetRecords();HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!thread)return false;CloseHandle(thread);event("start competition_supports five_fbx_variants");return true;
}
extern "C" void standball_stop(){InterlockedExchange(&stopping,1);ground();event("stop_requested supports_hidden");}
