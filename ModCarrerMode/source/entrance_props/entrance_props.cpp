#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <intrin.h>
#include "entrance_policy.h"
#include "club_atlas.h"
#include "entrance_bounds.h"

// The native SLE builder is called after mascot selection. Its temporary
// placement vector has private storage; the engine-owned vector is restored
// before returning. No resource is cloned or freed by this module.
using BuildFn=void(__fastcall*)(void*);
static uintptr_t image;
static BuildFn originalBuild;
static LONG started,stopping,busy,luaGateReady;
static char logPath[MAX_PATH],configPath[MAX_PATH];
static bool enabled=true;
static float heightCm=2;
static EntrancePolicy policy;
static EntranceIntroLifetime introLifetime;
static SRWLOCK lineupLock=SRWLOCK_INIT;
static EntranceLineups lineups;
static bool lastLineupFinished=false;
alignas(16) static unsigned char scratch[(EntranceMaxOriginals+1)*EntranceRecordBytes];
alignas(16) static unsigned char extra[EntranceRecordBytes];
static uintptr_t extraOwner=0,extraPrototype=0,extraState=0,shadowPrototype=0;
static uintptr_t resourceFixture=0;
static uintptr_t atlasFixture=0;
static char gameRoot[MAX_PATH]={};
static bool resourceRequested=false,resourceFault=false,resourceReadyLogged=false,lastShowing=false,placedLogged=false;
static bool retireBeforeReload=false;
static bool shadowRequested=false,shadowReadyLogged=false;
static bool lastDrawDeferred=false;
static uint64_t nextSample=0,nextDiagnostic=0;
static uint64_t nextPrototypeDiagnostic=0;
static uintptr_t fixture=0,fixtureRegistry=0;
static int clockValue=0;
static int nativePhase=-1,sportsState=-1;
static int introPhase=-1;
static int kickoffPhase=-1,kickoffState=-1,contextPhase=-1;
static bool kickoffOrganisation=false;
static bool introSampleKnown=false,introSampleCompleted=false;
static uintptr_t observedIntroAssignment=0,observedIntroRegistry=0;
static bool validFixture=false,knownClock=false,paused=false,replay=false,outside=true,nativeNis=false,choreoIntro=false,gameplayCamera=false;
static bool stadiumPanPage=false,nativeStateValid=false,nativePresentationKnown=false;
static EntranceAnthem anthem=EntranceAnthem::Unknown;
static uintptr_t audioSnapshot=0;
static char camera[96]={};
static DWORD activeBuildThread=0;
static uintptr_t activeBuildOwner=0;
static unsigned activePlacementIndex=0;
static float activeHeight=EntranceHiddenHeight;
static bool boundsLogged=false;
static EntranceCatalog::Asset selectedAsset;
static bool selectionAvailable=false;
static uintptr_t selectionFixture=0;
static uint64_t nextSelection=0,lastValidatedKey=0;
static unsigned selectedCompetition=0,selectedRound=0;
static char selectionRequest[81]={};
static FILETIME modelWrite{},textureWrite{},metadataWrite{};
static unsigned selectedModelBytes=0,selectedTextureBytes=0;
static char presentationPath[MAX_PATH]={},catalogPath[MAX_PATH]={};
using BoundsGatherFn=void(__fastcall*)(void*,int,float*,void*,void*,const float*,const float*,unsigned char,float);
using BoundsCullFn=void(__fastcall*)(void*,float*,int,void*);
static BoundsGatherFn originalBoundsGather;
static BoundsCullFn originalBoundsCull;

static void event(const char* message){
    FILE* f=nullptr;if(!fopen_s(&f,logPath,"ab")&&f){fprintf(f,"%llu %s\n",GetTickCount64(),message);fclose(f);}
}
template<class T>static bool get(uintptr_t at,T& out){
    SIZE_T n=0;return at && ReadProcessMemory(GetCurrentProcess(),(void*)at,&out,sizeof(T),&n)&&n==sizeof(T);
}
static bool read_bytes(uintptr_t at,void* out,size_t size){
    SIZE_T n=0;return at && ReadProcessMemory(GetCurrentProcess(),(void*)at,out,size,&n)&&n==size;
}
static bool same(uintptr_t at,uintptr_t expected){uintptr_t value=0;return get(at,value)&&value==expected;}
struct NativeVector{uintptr_t begin,end,capacity;};
static bool vector(uintptr_t at,size_t stride,NativeVector& out,size_t& count){
    if(!get(at,out))return false;
    if(!out.begin&&!out.end&&!out.capacity){count=0;return true;}
    if(out.begin<0x10000||out.end<out.begin||out.capacity<out.end||
       (out.end-out.begin)%stride||(out.capacity-out.begin)%stride||(out.capacity-out.begin)/stride>1024)return false;
    count=(out.end-out.begin)/stride;return count<=256;
}
static bool native_fixture(uintptr_t& key,uintptr_t& registryOut){
    uintptr_t manager=0,world=0,game=0,registry=0,pairs=0;int kind=0,count=0;
    if(!get(image+0x3517420,manager)||!same(manager,image+0x2226730)||
       !get(manager+8,world)||!same(world,image+0x2225d90)||
       !get(world+0x10,game)||!same(game,image+0x2309370)||!get(game+0x20,registry)||
       !get(registry+8+15*32,kind)||kind!=15||!get(registry+8+15*32+16,count)||count!=2||
       !get(registry+8+15*32+24,pairs))return false;
    uintptr_t teams[2]={};unsigned clubs[2]={};
    for(int i=0;i<2;++i){
        uintptr_t team=0,owner=0,stats=0;int side=-1,club=0;
        if(!get(pairs+i*16+8,team)||!same(team,image+0x22fe9f0)||!get(team+0x30,owner)||owner!=registry||
           !get(team+0x58,side)||side<0||side>1||teams[side]||!get(team+0x50,stats)||
           !get(stats+0x80,club)||club<=0||club>1000000)return false;
        teams[side]=team;clubs[side]=(unsigned)club;
    }
    // Renderer/resources may be rebuilt in pause. Club identity remains stable;
    // leaving the match and a confirmed clock rollback handle repeat fixtures.
    key=((uintptr_t)clubs[0]<<32)|clubs[1];registryOut=registry;return key!=0;
}
static void reset_lineups(){AcquireSRWLockExclusive(&lineupLock);lineups.reset();ReleaseSRWLockExclusive(&lineupLock);}
using LineupPostFn=unsigned char(__fastcall*)(void*,uintptr_t,uintptr_t,void*);
using OverlayShowFn=void(__fastcall*)(void*,int,const char*,int,int,int);
using OverlayRemoveFn=void(__fastcall*)(void*,int,int);
static LineupPostFn originalLineupPost;
static OverlayShowFn originalOverlayShow;
static OverlayRemoveFn originalOverlayRemove;
static bool lineup_scope(uintptr_t& key);
static void overlay_trace(const char*,void*,int,const char*);
static int lineup_payload_side(const char*,uintptr_t);
static bool read_page(char (&page)[64]);
using ServiceShowFn=int(__fastcall*)(void*,int,const char*,int,int,int,int);
using ServiceRemoveFn=void(__fastcall*)(void*,int,int,unsigned char);
using ServiceUpdateFn=int(__fastcall*)(void*,int,const char*,int,int,int);
static ServiceShowFn originalServiceShow;
static ServiceRemoveFn originalServiceRemove;
static ServiceUpdateFn originalServiceUpdate;
static bool formation_id(int id){return id>=0&&(id==18||id%1000==18);}
static void formation_shown(uintptr_t key,void* owner,int type,const char* data,int group){
    const int side=lineup_payload_side(data,key);if(side<0)return;
    AcquireSRWLockExclusive(&lineupLock);
    // A style can reuse the same panel and update its team payload. Closing
    // the first side is then the handover to the second, not a Remove call.
    if(lineups.fixture==key&&lineups.activeOwner==(uintptr_t)owner&&lineups.activeSide>=0&&lineups.activeSide!=side)
        lineups.removed_overlay((uintptr_t)owner);
    if(lineups.activeSide!=side||lineups.fixture!=key||lineups.activeOwner!=(uintptr_t)owner){
        lineups.post(key,(uintptr_t)owner,side);lineups.shown_overlay((uintptr_t)owner);
    }
    const unsigned shown=lineups.shown,closed=lineups.closed;
    ReleaseSRWLockExclusive(&lineupLock);
    char message[192];_snprintf_s(message,sizeof(message),_TRUNCATE,"formation_service_shown v18 id=%d side=%d group=%d shown=%u closed=%u",type,side,group,shown,closed);event(message);
}
static int __fastcall service_show_hook(void* owner,int type,const char* data,int duration,int group,int a,int b){
    uintptr_t key=0;const bool scoped=!stopping&&lineup_scope(key);
    if(scoped)overlay_trace("service_show",owner,type%1000,data);
    const int result=originalServiceShow(owner,type,data,duration,group,a,b);
    if(scoped&&formation_id(type))formation_shown(key,owner,type,data,group);
    return result;
}
static int __fastcall service_update_hook(void* owner,int type,const char* data,int mode,int group,int a){
    uintptr_t key=0;const bool scoped=!stopping&&lineup_scope(key);
    if(scoped)overlay_trace("service_update",owner,type%1000,data);
    const int result=originalServiceUpdate(owner,type,data,mode,group,a);
    if(scoped&&formation_id(type))formation_shown(key,owner,type,data,group);
    return result;
}
static void __fastcall service_remove_hook(void* owner,int type,int group,unsigned char immediate){
    uintptr_t key=0;const bool scoped=!stopping&&lineup_scope(key);
    if(scoped)overlay_trace("service_remove",owner,type%1000,nullptr);
    originalServiceRemove(owner,type,group,immediate);
    if(scoped&&formation_id(type)){
        char page[64]={};const bool pausePage=read_page(page)&&strstr(page,"StadiumPan");
        bool closed=false,finished=false;
        if(!pausePage){AcquireSRWLockExclusive(&lineupLock);closed=lineups.removed_overlay((uintptr_t)owner);finished=lineups.finished;ReleaseSRWLockExclusive(&lineupLock);}
        char message[160];_snprintf_s(message,sizeof(message),_TRUNCATE,"formation_service_remove v18 id=%d closed=%u finished=%u pause=%u",type,(unsigned)closed,(unsigned)finished,(unsigned)pausePage);event(message);
    }
}
static bool live_competition(unsigned& competition,unsigned& round){
    uintptr_t pointer=0;const unsigned offsets[4]={504,3544,1712,80};
    if(!get(image+56170408,pointer)||pointer<0x10000)return false;
    for(unsigned offset:offsets)if(!get(pointer+offset,pointer)||pointer<0x10000)return false;
    unsigned home=0,away=0;
    if(!get(pointer+276,home)||!get(pointer+280,away)||
       home!=(unsigned)(fixture>>32)||away!=(unsigned)fixture)return false;
    return get(pointer+40,competition)&&get(pointer+44,round)&&competition<1000000&&round<1000000;
}
static void sample_selection(){
    const uint64_t now=GetTickCount64();if(now<nextSelection)return;nextSelection=now+250;
    char option[16]={};GetPrivateProfileStringA("match","entrance_props","1",option,sizeof(option),presentationPath);
    const bool permit=!strcmp(option,"1")||!_stricmp(option,"true")||!_stricmp(option,"yes")||!_stricmp(option,"on");
    if(!validFixture||outside||!permit){
        selectionAvailable=false;selectionFixture=0;selectionRequest[0]=0;return;
    }
    unsigned competition=0,round=0;
    if(!live_competition(competition,round)){
        // A transient pointer gap cannot interrupt an already latched ceremony.
        if(selectionFixture!=fixture||!policy.armed)selectionAvailable=false;
        return;
    }
    char key[24],name[81]={};
    if(round){_snprintf_s(key,sizeof(key),_TRUNCATE,"%u",round);GetPrivateProfileStringA("competitions",key,"",name,sizeof(name),catalogPath);}
    if(!name[0]&&competition){_snprintf_s(key,sizeof(key),_TRUNCATE,"%u",competition);GetPrivateProfileStringA("competitions",key,"",name,sizeof(name),catalogPath);}
    if(!EntranceCatalog::slug(name)){
        if(selectionAvailable||selectionRequest[0])event("competition_props_skipped v18 unmapped_or_invalid_asset");
        selectionAvailable=false;selectionFixture=fixture;selectionRequest[0]=0;return;
    }
    char path[MAX_PATH];WIN32_FILE_ATTRIBUTE_DATA modelInfo{},textureInfo{},metadataInfo{};
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\model.rx3",gameRoot,name);
    const bool modelExists=GetFileAttributesExA(path,GetFileExInfoStandard,&modelInfo)!=0;
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\template.rx3",gameRoot,name);
    const bool textureExists=GetFileAttributesExA(path,GetFileExInfoStandard,&textureInfo)!=0;
    _snprintf_s(path,MAX_PATH,_TRUNCATE,"%s\\data\\sceneassets\\entrance_props\\competitions\\%s\\asset.ini",gameRoot,name);
    const bool metadataExists=GetFileAttributesExA(path,GetFileExInfoStandard,&metadataInfo)!=0;
    const bool sameRequest=selectionFixture==fixture&&selectedCompetition==competition&&selectedRound==round&&!strcmp(selectionRequest,name);
    if(sameRequest&&selectionAvailable&&modelExists&&textureExists&&metadataExists&&
       !modelInfo.nFileSizeHigh&&!textureInfo.nFileSizeHigh&&modelInfo.nFileSizeLow==selectedModelBytes&&textureInfo.nFileSizeLow==selectedTextureBytes&&
       !CompareFileTime(&modelWrite,&modelInfo.ftLastWriteTime)&&!CompareFileTime(&textureWrite,&textureInfo.ftLastWriteTime)&&!CompareFileTime(&metadataWrite,&metadataInfo.ftLastWriteTime))return;
    EntranceCatalog::Asset candidate{};
    const bool available=modelExists&&textureExists&&metadataExists&&EntranceCatalog::load(gameRoot,name,competition,round,candidate);
    selectionFixture=fixture;selectedCompetition=competition;selectedRound=round;strcpy_s(selectionRequest,name);
    if(available){
        selectedAsset=candidate;modelWrite=modelInfo.ftLastWriteTime;textureWrite=textureInfo.ftLastWriteTime;metadataWrite=metadataInfo.ftLastWriteTime;
        selectedModelBytes=modelInfo.nFileSizeLow;selectedTextureBytes=textureInfo.nFileSizeLow;
        const uint64_t keyValue=fixture^candidate.stamp;
        if(keyValue!=lastValidatedKey){
            retireBeforeReload=resourceRequested;
            resourceFault=false;atlasFixture=0;lastValidatedKey=keyValue;boundsLogged=false;
        }
    }
    selectionAvailable=available;
    if(!sameRequest||available){
        char message[224];_snprintf_s(message,sizeof(message),_TRUNCATE,"competition_props v18 competition=%u round=%u asset=%s validated=%u",competition,round,name,(unsigned)available);event(message);
    }
}
static bool read_clock(int& value);
static bool lineup_scope(uintptr_t& key){
    uintptr_t state=0,registry=0;int sports=-1,phase=-1,clock=0;
    return get(image+0x3517c10,state)&&same(state,image+0x20ff390)&&get(state+0x3c,sports)&&sports==2&&
        get(state+0x2254,phase)&&phase>=0&&phase<=4&&read_clock(clock)&&clock==0&&native_fixture(key,registry);
}
static unsigned char __fastcall lineup_post_hook(void* self,uintptr_t a,uintptr_t b,void* data){
    const unsigned char result=originalLineupPost(self,a,b,data);
    uintptr_t key=0,owner=0;int side=-1;
    if(!stopping&&result&&lineup_scope(key)&&get((uintptr_t)self+0x30,owner)&&get((uintptr_t)data,side)&&side>=0&&side<=1){
        AcquireSRWLockExclusive(&lineupLock);lineups.post(key,owner,side);ReleaseSRWLockExclusive(&lineupLock);
        char message[128];_snprintf_s(message,sizeof(message),_TRUNCATE,"lineup_post v18 side=%d owner=%p",side,(void*)owner);event(message);
    }
    return result;
}
static bool overlay_handle(uintptr_t owner,int& handle){uintptr_t table=0;return get(owner+0x21e0,table)&&get(table+18*4,handle);}
static void overlay_trace(const char* action,void* owner,int type,const char* data){
    uintptr_t key=0;if(stopping||type<0||type>40||!lineup_scope(key))return;
    char prefix[97]={};if(data){
        for(size_t i=0;i<sizeof(prefix)-1;++i){char c=0;if(!get((uintptr_t)data+i,c)||!c)break;prefix[i]=(c>=32&&c<=126)?c:'?';}
    }
    char message[192];_snprintf_s(message,sizeof(message),_TRUNCATE,"overlay_%s v18 type=%d owner=%p payload=%s",action,type,owner,prefix);event(message);
}
static int lineup_payload_side(const char* data,uintptr_t key){
    char prefix[32]={};if(!data||!read_bytes((uintptr_t)data,prefix,sizeof(prefix)-1))return -1;
    char* end=nullptr;const long first=strtol(prefix,&end,10);
    if(end==prefix||*end!='|')return -1;
    if(first==0||first==1)return (int)first;
    if(first==(long)(key>>32))return 0;
    if(first==(long)(key&0xffffffff))return 1;
    return -1;
}
static void __fastcall overlay_show_hook(void* owner,int type,const char* data,int priority,int a,int b){
    overlay_trace("show",owner,type,data);
    if(!stopping&&type==18){
        uintptr_t key=0;
        if(lineup_scope(key)){
            const int side=lineup_payload_side(data,key);
            if(side>=0){AcquireSRWLockExclusive(&lineupLock);lineups.post(key,(uintptr_t)owner,side);ReleaseSRWLockExclusive(&lineupLock);}
        }
    }
    originalOverlayShow(owner,type,data,priority,a,b);
    if(!stopping&&type==18){
        int handle=-1;bool accepted=false;int side=-1;unsigned shown=0;
        if(overlay_handle((uintptr_t)owner,handle)&&handle!=-1){
            AcquireSRWLockExclusive(&lineupLock);accepted=lineups.shown_overlay((uintptr_t)owner);side=lineups.activeSide;shown=lineups.shown;ReleaseSRWLockExclusive(&lineupLock);
        }
        if(accepted){char message[128];_snprintf_s(message,sizeof(message),_TRUNCATE,"lineup_shown v18 side=%d shown=%u handle=%d",side,shown,handle);event(message);}
    }
}
static void __fastcall overlay_remove_hook(void* owner,int type,int mode){
    overlay_trace("remove",owner,type,nullptr);
    int before=-1;const bool existed=type==18&&overlay_handle((uintptr_t)owner,before)&&before!=-1;
    originalOverlayRemove(owner,type,mode);
    int after=0;
    if(!stopping&&existed&&overlay_handle((uintptr_t)owner,after)&&after==-1){
        bool accepted=false,finished=false;unsigned closed=0;
        AcquireSRWLockExclusive(&lineupLock);accepted=lineups.removed_overlay((uintptr_t)owner);closed=lineups.closed;finished=lineups.finished;ReleaseSRWLockExclusive(&lineupLock);
        if(accepted){char message[128];_snprintf_s(message,sizeof(message),_TRUNCATE,"lineup_removed v18 closed=%u finished=%u old_handle=%d",closed,(unsigned)finished,before);event(message);}
    }
}
static bool read_page(char (&page)[64]){
    uintptr_t p=0;const unsigned offsets[]={232,192,136,472};
    if(!get(image+58757168,p)||!p)return false;
    for(unsigned off:offsets)if(!get(p+off,p)||!p)return false;
    return read_bytes(p,page,sizeof(page))&&memchr(page,0,sizeof(page));
}
static bool read_clock(int& value){
    uintptr_t stats=0;return get(image+56299464,stats)&&stats&&get(stats+5500,value)&&value>=0&&value<100000000;
}
static bool continuous_intro(){
    introPhase=-1;
    kickoffPhase=-1;kickoffState=-1;contextPhase=-1;kickoffOrganisation=false;
    // Verified ChoreoSystem (registry kind 92). Restrict to IntroScriptAssignment;
    // a kickoff setpiece also has type 4 and must never extend the presentation.
    introSampleKnown=false;introSampleCompleted=false;
    if(observedIntroRegistry!=fixtureRegistry){observedIntroAssignment=0;observedIntroRegistry=fixtureRegistry;}
    uintptr_t pairs=0,system=0;int kind=-1,count=0;
    const uintptr_t row=fixtureRegistry+8+92*32;
    if(!fixtureRegistry||!get(row,kind)||!get(row+16,count))return false;
    if(kind==92&&count==0){introSampleKnown=true;return false;}
    if(kind!=92||count!=1||!get(row+24,pairs)||!get(pairs+8,system)||!same(system,image+0x231a1b0))return false;
    NativeVector assignments{};size_t n=0;
    if(!vector(system+0x18,8,assignments,n)||n>32)return false;
    uintptr_t context=0;
    if(get(system+0x9b0,context)&&same(context,image+0x2319f10))get(context+0x68,contextPhase);
    bool foundIntro=false,readable=true;
    for(size_t i=0;i<n;++i){
        uintptr_t assignment=0;unsigned char complete=1;int type=-1;
        uintptr_t vt=0;
        if(!get(assignments.begin+i*8,assignment)||!get(assignment,vt)||!get(assignment+0x7c,complete)||!get(assignment+0x84,type)){readable=false;continue;}
        if(vt==image+0x231a350&&type==4){
            if(complete){introSampleCompleted|=assignment==observedIntroAssignment;continue;}
            observedIntroAssignment=assignment;
            int phase=-1;
            if(get(assignment+0x70,phase)&&phase>=0&&phase<=32)introPhase=phase;else readable=false;
            foundIntro=true;
        }else if(!complete&&vt==image+0x231a390&&type==5&&same(assignment+0x68,system)){
            if(get(assignment+0x70,kickoffPhase)&&get(assignment+0x74,kickoffState))
                kickoffOrganisation|=entrance_kickoff_assignment(kickoffPhase,kickoffState,contextPhase);
        }
    }introSampleKnown=readable;return foundIntro;
}
static EntranceAnthem native_anthem(){
    // Audio::AudioEventHandlerImpl stores the GameStates snapshot at +68.
    // NIS start callback 3ad98a0 sets category 2 to NIS_ANTHEM_LINEUP
    // for sequence kind 9. Read the existing state; never invoke audio APIs.
    if(!audioSnapshot || !same(audioSnapshot,image+0x21171d8)){
        audioSnapshot=0;
        uintptr_t services=0,audio=0,holder=0,framework=0,handler=0,snapshot=0;
        int active=0;
        if(!get(image+0x34e8500,services)||!same(services,image+0x2195610)||
           !get(services+0x3308,active)||active<0||active>1)return EntranceAnthem::Unknown;
        // Verified native service lookup 3d06910: two banks, 541 open-addressed
        // entries. Looking up the audio interface here avoids its AddRef call.
        const uintptr_t keys=services+(active?0x19a8:0x48);
        const uintptr_t values=services+(active?0x2220:0x8c0);
        const unsigned key=0x0a621c80;
        for(unsigned attempt=0;attempt<541;++attempt){
            const unsigned index=(key+attempt)%541;unsigned found=0;
            if(!get(keys+index*4,found)||!found)break;
            if(found==key){get(values+index*8,audio);break;}
        }
        if(!same(audio,image+0x21137e0)||!get(audio+0x18,holder)||!get(holder,framework)||
           !get(framework+0x718,handler)||!same(handler,image+0x2116c80)||
           !get(handler+0x68,snapshot)||!same(snapshot,image+0x21171d8))return EntranceAnthem::Unknown;
        audioSnapshot=snapshot;
    }
    uintptr_t state=0;
    // Native setter 3ae61c0 stores category n at +10+n*8: category 2 is +20.
    if(!get(audioSnapshot+0x20,state)||
       (state&&(state<image+0x2000000||state>=image+0x3400000)))return EntranceAnthem::Unknown;
    return state==image+0x2117590?EntranceAnthem::Active:EntranceAnthem::Inactive;
}
static void sample_native_scene(){
    nativeNis=false;choreoIntro=false;gameplayCamera=false;replay=false;nativeStateValid=false;nativePresentationKnown=false;
    nativePhase=-1;sportsState=-1;camera[0]=0;
    introPhase=-1;
    introSampleKnown=false;introSampleCompleted=false;
    kickoffPhase=-1;kickoffState=-1;contextPhase=-1;kickoffOrganisation=false;
    uintptr_t state=0,manager=0,presentation=0;unsigned char stateReady=0;
    if(get(image+0x3517c10,state)&&same(state,image+0x20ff390)){
        get(state+8,stateReady);
        get(state+0x39,replay);get(state+0x3a,gameplayCamera);
        get(state+0x3c,sportsState);get(state+0x2254,nativePhase);
        if(read_bytes(state+0xc4,camera,sizeof(camera)))camera[sizeof(camera)-1]=0;
        nativeStateValid=stateReady!=0;
    }
    if(get(image+0x3517420,manager)&&same(manager,image+0x2226730)&&
       get(manager+0x40,presentation)&&same(presentation,image+0x2290920)){
        nativePresentationKnown=get(presentation+0x10,nativeNis); // PresStartNISSequence / native sequence end
    }
    if(validFixture)choreoIntro=continuous_intro();
    anthem=validFixture?native_anthem():EntranceAnthem::Unknown;
    for(char& c:camera)if(c>='A'&&c<='Z')c=(char)(c+32);
}
static void sample(){
    const uint64_t now=GetTickCount64();
    int sampledClock=clockValue;
    if(read_clock(sampledClock)){clockValue=sampledClock;knownClock=true;}
    sample_native_scene();
    // The pause page must be sampled before policy decisions on every frame.
    // Fixture traversal remains throttled; a cached page could consume an intro.
    char page[64]={};const bool known=read_page(page);
    for(char& c:page)if(c>='A'&&c<='Z')c=(char)(c+32);
    const bool blank=known&&(!page[0]||!strncmp(page,"game/screens/tv/",16));
    if(known){
    stadiumPanPage=!strcmp(page,"game/screens/misc/stadiumpan");
    paused=(strstr(page,"game/screens/pause/")||strstr(page,"game/screens/instantreplay/")||
        !strcmp(page,"game/screens/fluxhub/fluxhub"));
    if(policy.fixture&&known&&(!strcmp(page,"game/screens/playnow/sideselect")||!strcmp(page,"game/screens/matchdetails/matchdetails")))paused=true;
    outside=!blank&&!paused&&!stadiumPanPage;
    if(outside){policy.leave();introLifetime.reset();reset_lineups();fixtureRegistry=0;validFixture=false;}
    }
    // Page/clock pointers can change for a frame when a lineup overlay swaps.
    // An unknown read does not hide an already verified, armed presentation.
    if(now<nextSample)return;nextSample=now+250;
    validFixture=!outside&&native_fixture(fixture,fixtureRegistry);
    sample_selection();
}
static bool visible(){
    sample();
    bool finished=false,newCycle=false;unsigned shownSides=0,closedSides=0;
    AcquireSRWLockExclusive(&lineupLock);
    if(validFixture&&!paused&&!replay&&clockValue==0&&policy.consumed&&policy.lastIntroPhase>=3&&introPhase>=0&&introPhase<=2&&lineups.finished&&!lineups.newCycle)
        lineups.reset();
    if(validFixture&&policy.fixture&&policy.fixture!=fixture&&lineups.fixture!=fixture)lineups.reset();
    finished=lineups.finished;newCycle=lineups.newCycle;lineups.newCycle=false;shownSides=lineups.shown;closedSides=lineups.closed;
    ReleaseSRWLockExclusive(&lineupLock);
    if(newCycle){policy.leave();introLifetime.reset();}
    lastLineupFinished=finished;
    EntranceScene scene=EntranceScene::Unknown;
    const bool nativeOrganisation=nativeStateValid&&nativePhase==0&&(sportsState==2||sportsState==15);
    const bool introEnded=validFixture&&introLifetime.observe(fixture,fixtureRegistry,GetTickCount64(),introSampleKnown,choreoIntro,introSampleCompleted,introPhase,paused,replay,nativeNis,nativeOrganisation);
    const bool skipEnded=entrance_skip_ended(nativeStateValid,nativePhase,sportsState,camera,choreoIntro,nativeNis,paused,replay);
    if(finished)scene=EntranceScene::ToKickoff;
    else if(introEnded||skipEnded)scene=EntranceScene::ToKickoff;
    else if(nativeNis||choreoIntro)scene=EntranceScene::Presentation;
    else if(gameplayCamera && nativeStateValid&&sportsState==15)scene=EntranceScene::Gameplay;
    else if(sportsState==2&&strstr(camera,"stadiumpan"))scene=EntranceScene::StadiumPan;
    // A valid presentation service only says the subsystem exists. It stays
    // valid after hymns and during transitions, so it cannot mark the end.
    // Keep the presentation armed through transient gaps in the choreo/NIS
    // flags; the native kickoff camera or confirmed gameplay ends it.
    else if(nativeStateValid&&nativePhase==0&&sportsState==15)scene=EntranceScene::Gameplay;
    const bool previouslyConsumed=policy.consumed;
    const bool ceremonyVisible=policy.visible(validFixture&&knownClock&&!outside,paused,replay,fixture,clockValue,scene,anthem,sportsState==2?introPhase:-1);
    const bool show=enabled&&!stopping&&selectionAvailable&&ceremonyVisible;
    if(previouslyConsumed&&!policy.consumed)event("intro_rearmed v18 native_opening_phase_or_match_restart");
    if(!previouslyConsumed&&policy.consumed){
        event(finished?"intro_cutoff v18 second_lineup_closed":introEnded?"intro_cutoff v18 intro_assignment_ended":skipEnded?"intro_cutoff v18 native_broadcast_after_skip":"intro_cutoff v18 gameplay");
    }
    if(show!=lastShowing){event(show?"intro_visible v18 native_presentation rotated_180 all_teams no_physics":"intro_hidden v18 native_cutoff_or_left_match");lastShowing=show;}
    const uint64_t now=GetTickCount64();
    if(validFixture&&now>=nextDiagnostic){
        nextDiagnostic=now+5000;char message[640];
        _snprintf_s(message,sizeof(message),_TRUNCATE,"scene v18 clock=%d phase=%d sports=%d intro_phase=%d kickoff_phase=%d kickoff_state=%d context_phase=%d lineups_shown=%u lineups_closed=%u lineup_finished=%u nis=%u choreo_intro=%u intro_known=%u intro_complete=%u intro_ended=%u anthem=%u gameplay_camera=%u pan_page=%u paused=%u replay=%u armed=%u consumed=%u camera=%s",
            clockValue,nativePhase,sportsState,introPhase,kickoffPhase,kickoffState,contextPhase,shownSides,closedSides,(unsigned)finished,(unsigned)nativeNis,(unsigned)choreoIntro,(unsigned)introSampleKnown,(unsigned)introSampleCompleted,(unsigned)introEnded,(unsigned)anthem,(unsigned)gameplayCamera,(unsigned)stadiumPanPage,(unsigned)paused,(unsigned)replay,(unsigned)policy.armed,(unsigned)policy.consumed,camera);
        event(message);
    }
    return show;
}
static int own_bounds_index(uintptr_t returnSlot,int count){
    if(activeBuildThread!=GetCurrentThreadId()||!activeBuildOwner||count<=0||count>208)return -1;
    // Exact guarded 43a8bf0 stack: RBP = caller RSP + 0x100.
    // The native gather writes (SLE type, placement index) at RBP + 0x33d0.
    // The caller's return slot is RSP - 8 at these two direct calls.
    unsigned char pairs[208*2];if(!read_bytes(returnSlot+0x34d8,pairs,(size_t)count*2))return -1;
    int found=-1;
    for(int i=0;i<count;++i)if(pairs[2*i]==6&&pairs[2*i+1]==activePlacementIndex){if(found!=-1)return -1;found=i;}
    return found;
}
static void full_actor_bounds(float* boxes,int index){
    float limits[8]={selectedAsset.minimum[0],selectedAsset.minimum[1]+activeHeight,selectedAsset.minimum[2],0,
        selectedAsset.maximum[0],selectedAsset.maximum[1]+activeHeight,selectedAsset.maximum[2],0};
    memcpy(boxes+(size_t)index*8,limits,sizeof(limits));
}
static void __fastcall bounds_gather_hook(void* service,int count,float* boxes,void* shadowGrid,void* out,
                                        const float* a,const float* b,unsigned char flag,float scale){
    const int index=own_bounds_index((uintptr_t)_AddressOfReturnAddress(),count);
    if(index>=0&&boxes==(float*)(activeBuildOwner+0x2c60)){
        full_actor_bounds(boxes,index);
        full_actor_bounds((float*)(activeBuildOwner+0xd20),index);
    }
    originalBoundsGather(service,count,boxes,shadowGrid,out,a,b,flag,scale);
}
static void __fastcall bounds_cull_hook(void* out,float* boxes,int count,void* cameraData){
    const int index=own_bounds_index((uintptr_t)_AddressOfReturnAddress(),count);
    if(index>=0&&boxes==(float*)(activeBuildOwner+0xd20)){
        full_actor_bounds(boxes,index);
        if(!boundsLogged){char message[160];_snprintf_s(message,sizeof(message),_TRUNCATE,"full_mesh_bounds v18 index=%d selected_mesh_and_crests",index);event(message);boundsLogged=true;}
    }
    originalBoundsCull(out,boxes,count,cameraData);
}
static bool own_prototype(void* self,uintptr_t& proto,uintptr_t& state,uintptr_t& basePrototype){
    NativeVector models{};size_t n=0;
    if(!vector((uintptr_t)self+0x30*(6+1),8,models,n)||n!=2||!get(models.begin+8,proto)||
       !get(models.begin,basePrototype)||basePrototype==proto)return false;
    uint16_t type=0,variant=0,baseType=0,baseVariant=1;unsigned rnaIndex=0;
    return get(basePrototype+12,baseType)&&baseType==6&&get(basePrototype+14,baseVariant)&&baseVariant==0&&
        get(proto+12,type)&&type==6&&get(proto+14,variant)&&variant==1&&
        get(proto+16,state)&&state&&get(state+0x4c,rnaIndex)&&rnaIndex<4096;
}
static bool fixture_atlas(){
    if(!validFixture||!fixture||!selectionAvailable)return false;
    const uintptr_t key=fixture^selectedAsset.stamp;if(atlasFixture==key)return true;
    char relative[MAX_PATH]={},modelFile[MAX_PATH]={},textureFile[MAX_PATH]={};
    const unsigned home=(unsigned)(fixture>>32),away=(unsigned)fixture;
    const bool prepared=ClubAtlas::prepare(gameRoot,selectedAsset,home,away,relative);
    if(prepared){_snprintf_s(modelFile,MAX_PATH,_TRUNCATE,"%smodel.rx3",relative);_snprintf_s(textureFile,MAX_PATH,_TRUNCATE,"%stextures.rx3",relative);}
    else if(!selectedAsset.slots){
        _snprintf_s(modelFile,MAX_PATH,_TRUNCATE,"data/sceneassets/entrance_props/competitions/%s/model.rx3",selectedAsset.slug);
        _snprintf_s(textureFile,MAX_PATH,_TRUNCATE,"data/sceneassets/entrance_props/competitions/%s/template.rx3",selectedAsset.slug);
    }else {event("club_atlas v18 generation_failed actor_not_requested");return false;}
    char script[1024];_snprintf_s(script,sizeof(script),_TRUNCATE,"FIFA16_ENTRANCE_MODEL_FILE='%s'; FIFA16_ENTRANCE_TEXTURE_FILE='%s'",modelFile,textureFile);
    ((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,strlen(script),"entrance_competition_club_atlas");
    atlasFixture=key;
    char message[384];_snprintf_s(message,sizeof(message),_TRUNCATE,"club_atlas v18 home=%u away=%u asset=%s slots=%u prepared=%u path=%s",home,away,selectedAsset.slug,selectedAsset.slots,(unsigned)prepared,textureFile);event(message);
    return true;
}
static bool ready_prototype(uintptr_t prototype,bool& requested,bool& logged,bool shadow){
    using Ready=unsigned char(__fastcall*)(void*);
    if(resourceFault)return false;
    __try{
    if(!shadow&&(!selectionAvailable||retireBeforeReload)){
        // Retire the already retained actor without requesting any missing asset.
        return requested&&((Ready)(image+0x43b43e0))((void*)prototype)!=0&&((Ready)(image+0x43b4520))((void*)prototype)!=0;
    }
    if(!shadow&&validFixture&&!fixture_atlas())return false;
    if(!requested){
        const bool initialized=((Ready)(image+0x43b4500))((void*)prototype)!=0;
        if(!initialized){
            const int parameters[5]={-1,-1,-1,0,-1};
            ((void(__fastcall*)(void*,const int*))(image+0x43b4640))((void*)prototype,parameters);
            uintptr_t vt=0,load=0;
            if(!get(prototype,vt)||!get(vt+0x38,load)||load<image||load>=image+0x9524000)return false;
            ((void(__fastcall*)(void*,int))load)((void*)prototype,0);
        }else if(!shadow&&validFixture){
            uintptr_t vt=0,load=0;
            if(!get(prototype,vt)||!get(vt+0x38,load)||load!=image+0x43b4530)return false;
            ((void(__fastcall*)(void*,int))load)((void*)prototype,1);
        }
        if(!shadow&&validFixture)resourceFixture=fixture^selectedAsset.stamp;
        requested=true;event(shadow?"native_shadow_dependency_requested v18":"native_static_resource_requested v18");
    }
    if(!shadow&&validFixture&&resourceFixture!=(fixture^selectedAsset.stamp)){
        // The prototype can survive a fixture change with identical appearance
        // parameters. Force the native callback to resolve the new clubs' DDS.
        uintptr_t vt=0,load=0;
        if(!get(prototype,vt)||!get(vt+0x38,load)||load!=image+0x43b4530)return false;
        ((void(__fastcall*)(void*,int))load)((void*)prototype,1);
        resourceFixture=fixture^selectedAsset.stamp;logged=false;
        event("native_club_badges_refreshed new_fixture");
    }
    const bool ready=((Ready)(image+0x43b43e0))((void*)prototype)!=0&&
        ((Ready)(image+0x43b4520))((void*)prototype)!=0;
    if(ready&&!logged){event(shadow?"native_shadow_dependency_ready v18":"native_static_resource_ready v18");logged=true;}
    return ready;
    }__except(EXCEPTION_EXECUTE_HANDLER){resourceFault=true;event("native_static_resource_fault v18 actor_disabled_for_scene");return false;}
}
static void __fastcall build_hook(void* self){
    if(InterlockedCompareExchange(&busy,1,0)){originalBuild(self);return;}
    NativeVector saved{},temporary{};size_t count=0;unsigned mask=0;
    const uintptr_t placement=(uintptr_t)self+0x30*(6+0x2f);
    const uintptr_t maskAddress=(uintptr_t)self+0x4f604;
    bool swapped=false,maskSaved=false;size_t normalBytes=0;float submittedHeight=EntranceHiddenHeight;
    __try{
        uintptr_t prototype=0,state=0,basePrototype=0;
        const bool show=visible(); // log scene state even if a prototype is absent
        if(!selectionAvailable&&atlasFixture&&InterlockedCompareExchange(&luaGateReady,0,0)){
            const char script[]="FIFA16_ENTRANCE_MODEL_FILE=nil; FIFA16_ENTRANCE_TEXTURE_FILE=nil";
            ((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,sizeof(script)-1,"entrance_competition_disabled");
            atlasFixture=0;
        }
        submittedHeight=entrance_render_height(show&&!retireBeforeReload,heightCm);
        const char* deferReason="prototype_or_placement_unavailable";
        const bool gateReady=InterlockedCompareExchange(&luaGateReady,0,0)!=0;
        if(own_prototype(self,prototype,state,basePrototype)&&vector(placement,EntranceRecordBytes,saved,count)&&count<=EntranceMaxOriginals){
            normalBytes=count*EntranceRecordBytes;
            deferReason="placement_records_unreadable";
            if(!normalBytes||read_bytes(saved.begin,scratch,normalBytes)){
                entrance_clean(scratch,count);
                // Clear the reserved appearance even when the introduction is over.
                if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
                if(extraOwner!=(uintptr_t)self||extraPrototype!=prototype||extraState!=state||shadowPrototype!=basePrototype){
                    extraOwner=(uintptr_t)self;extraPrototype=prototype;extraState=state;shadowPrototype=basePrototype;
                    resourceRequested=false;resourceFault=false;resourceReadyLogged=false;placedLogged=false;
                    resourceFixture=0;retireBeforeReload=false;
                    shadowRequested=false;shadowReadyLogged=false;
                    entrance_new_record(extra,heightCm);event("scene_static_prototype_confirmed generic_variation=1");
                }
                // Preload independently of visibility; loading must not depend
                // on the match clock or on leaving the initial stadium pan.
                const bool modelReady=gateReady&&ready_prototype(prototype,resourceRequested,resourceReadyLogged,false);
                // Native gather at 43a8fa7 separately tests prototype 0, whose
                // LOD 4 supplies the common shadow. Generic placements can be
                // empty, so native selection never requests it by itself.
                const bool shadowReady=gateReady&&(selectionAvailable||resourceRequested)&&ready_prototype(basePrototype,shadowRequested,shadowReadyLogged,true);
                const bool ready=modelReady&&shadowReady;
                deferReason=!modelReady?"static_resource_unready":!shadowReady?"shadow_resource_unready":"render_mask_unreadable";
                if(ready&&get(maskAddress,mask)){
                    // Submit the hidden transform too. Omitting the record can
                    // leave the renderer's previous static instance on the pitch.
                    entrance_static_position(extra,submittedHeight);
                    memcpy(scratch+normalBytes,extra,EntranceRecordBytes);
                    temporary={(uintptr_t)scratch,(uintptr_t)scratch+normalBytes+EntranceRecordBytes,(uintptr_t)scratch+sizeof(scratch)};
                    memcpy((void*)placement,&temporary,sizeof(temporary));swapped=true;
                    *(unsigned*)maskAddress=mask|(1u<<6);maskSaved=true;
                }
            }
        }
        if(show&&!swapped&&!lastDrawDeferred){
            char message[160];_snprintf_s(message,sizeof(message),_TRUNCATE,"draw_deferred v18 reason=%s intro_phase=%d organisation=%u",
                deferReason,introPhase,(unsigned)kickoffOrganisation);event(message);lastDrawDeferred=true;
        }else if(swapped&&lastDrawDeferred){event("draw_resumed v18 native_resources_and_placement_ready");lastDrawDeferred=false;}
        if(!prototype&&GetTickCount64()>=nextPrototypeDiagnostic){
            nextPrototypeDiagnostic=GetTickCount64()+5000;
            NativeVector models{};size_t modelCount=0;char message[128];
            const bool known=vector((uintptr_t)self+0x30*(6+1),8,models,modelCount);
            _snprintf_s(message,sizeof(message),_TRUNCATE,"native_prototype_unavailable v18 count=%zu known=%u lua_gate=%u",
                modelCount,(unsigned)known,(unsigned)gateReady);event(message);
        }
        activeBuildThread=GetCurrentThreadId();activeBuildOwner=swapped?(uintptr_t)self:0;
        activePlacementIndex=(unsigned)count;activeHeight=submittedHeight;
        originalBuild(self);
    }__finally{
        activeBuildOwner=0;activeBuildThread=0;
        if(swapped){
            // Native builder updates binding bytes synchronously. Keep those for
            // native actors and our private actor, without transferring ownership.
            if(normalBytes)memcpy((void*)saved.begin,scratch,normalBytes);
            memcpy(extra,scratch+normalBytes,EntranceRecordBytes);
            entrance_static_position(extra,submittedHeight);
            uint16_t binding=0xffff;memcpy(&binding,extra+0x40,sizeof(binding));
            if(binding!=0xffff&&!placedLogged){event("native_static_actor_placed v18 binding_assigned");placedLogged=true;}
            memcpy((void*)placement,&saved,sizeof(saved));
        }
        if(maskSaved)*(unsigned*)maskAddress=mask;
        if(swapped&&retireBeforeReload){
            retireBeforeReload=false;resourceRequested=false;resourceReadyLogged=false;
            event("old_competition_actor_retired v18 before_resource_reload");
        }
        InterlockedExchange(&busy,0);
    }
}
static const unsigned char callSaved[5]={0xe8,0x78,0xca,0xff,0xff};
static unsigned char callExpected[5]={0xe8,0x78,0xca,0xff,0xff};
static BOOL(WINAPI* previousStop)()=nullptr;
static HMODULE previousOwner=nullptr;
static uintptr_t previousRelay=0,lineupPostExpected=0;
static bool preserveOuterBuilder=false;
static uintptr_t previousEntry=0;
static unsigned char previousEntrySaved[14],previousEntryApplied[14];
static unsigned char callApplied[5];
struct OverlayCallPatch{uintptr_t rva;unsigned char bytes[16];bool show;unsigned char applied[5];unsigned char expected[5];};
#include "overlay_calls.h"

struct BoundsCallPatch{uintptr_t rva;unsigned char bytes[5],expected[5],applied[5];};
static BoundsCallPatch boundsCalls[]={
    {0x43a907c,{0xe8,0x7f,0x85,0xfc,0xff},{},{}},
    {0x43a909d,{0xe8,0xde,0xc9,0x76,0},{},{}}
};
static const uintptr_t serviceVtables[3]={0x228b430,0x228b438,0x228b440};
static const uintptr_t serviceNative[3]={0x487a6b0,0x487aa70,0x4878830};
static uintptr_t serviceExpected[3]={};

static bool compatible_builder_call(const unsigned char* actual){
    preserveOuterBuilder=false;previousEntry=0;
    if(!memcmp(actual,callSaved,5)){memcpy(callExpected,actual,5);previousStop=nullptr;previousOwner=nullptr;previousRelay=0;return true;}
    // Replace only our preceding pinned revision, preserving every other hook.
    if(actual[0]!=0xe8)return false;
    int32_t delta=0;memcpy(&delta,actual+1,4);
    const uintptr_t relay=image+0x43ac178+delta;
    unsigned char jump[6];uintptr_t target=0;
    const unsigned char expectedJump[6]={0xff,0x25,0,0,0,0};
    if(!read_bytes(relay,jump,6)||memcmp(jump,expectedJump,6)||!get(relay+6,target))return false;
    HMODULE owner=nullptr;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
                          (LPCSTR)target,&owner))return false;
    char path[MAX_PATH]={};
    if(!GetModuleFileNameA(owner,path,MAX_PATH))return false;
    const char* leaf=strrchr(path,'\\');
    if(!leaf)return false;
    uintptr_t selectedRelay=relay;
    if(!_stricmp(leaf+1,"var_cabin.dll")||!_stricmp(leaf+1,"var_cabin_v2.dll")||!_stricmp(leaf+1,"var_cabin_v3.dll")){
        // The VAR cabin wraps our old callback. Keep its native call intact
        // and forward the entry in our own pinned v16 DLL to the new builder.
        HMODULE old=GetModuleHandleA("entrance_props_v16.dll");if(!old)return false;
        unsigned char overlay[5];if(!read_bytes(image+0x490c8ad,overlay,5)||overlay[0]!=0xe8)return false;
        int32_t relative=0;memcpy(&relative,overlay+1,4);selectedRelay=image+0x490c8ad+5+relative-16;
        if(!read_bytes(selectedRelay,jump,6)||memcmp(jump,expectedJump,6)||!get(selectedRelay+6,previousEntry))return false;
        HMODULE entryOwner=nullptr;
        if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)previousEntry,&entryOwner)||entryOwner!=old)return false;
        IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
        if(!get((uintptr_t)old,dos)||!get((uintptr_t)old+dos.e_lfanew,nt)||previousEntry!=(uintptr_t)old+0x1a20)return false;
        if(!read_bytes(previousEntry,previousEntrySaved,14))return false;
        const unsigned char expectedPrologue[14]={0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57,0x41,0x54,0x41};
        if(memcmp(previousEntrySaved,expectedPrologue,14))return false;
        // Verify the outer module actually holds that callback in its data.
        IMAGE_DOS_HEADER outerDos{};IMAGE_NT_HEADERS64 outerNt{};
        if(!get((uintptr_t)owner,outerDos)||!get((uintptr_t)owner+outerDos.e_lfanew,outerNt)||outerNt.FileHeader.NumberOfSections>32)return false;
        auto headers=(uintptr_t)owner+outerDos.e_lfanew+24+outerNt.FileHeader.SizeOfOptionalHeader;bool chained=false;
        for(unsigned i=0;i<outerNt.FileHeader.NumberOfSections;++i){
            IMAGE_SECTION_HEADER section{};if(!get(headers+i*sizeof(section),section))return false;
            if(memcmp(section.Name,".data",5)||section.Misc.VirtualSize>1024*1024)continue;
            for(size_t at=0;at+8<=section.Misc.VirtualSize;at+=8){
                uintptr_t value=0;if(!get((uintptr_t)owner+section.VirtualAddress+at,value))continue;
                if(value==previousEntry){chained=true;break;}
                // VAR may retain the owned v14 entry already forwarded to v16.
                HMODULE ancestor=GetModuleHandleA("entrance_props_v14.dll");
                if(ancestor&&value==(uintptr_t)ancestor+0x17b0){
                    unsigned char forward[6];uintptr_t forwardedEntry=0;
                    if(read_bytes(value,forward,6)&&!memcmp(forward,expectedJump,6)&&get(value+6,forwardedEntry)&&forwardedEntry==previousEntry){chained=true;break;}
                }
            }
        }
        if(!chained)return false;
        owner=old;preserveOuterBuilder=true;
    }else if(_stricmp(leaf+1,"entrance_props_v16.dll"))return false;
    auto version=(unsigned(WINAPI*)())GetProcAddress(owner,"Fifa16ModGetApiVersion");
    auto stop=(BOOL(WINAPI*)())GetProcAddress(owner,"Fifa16ModStop");
    if(!version||!stop||version()!=1)return false;
    memcpy(callExpected,actual,5);previousStop=stop;previousOwner=owner;previousRelay=selectedRelay;return true;
}
static bool signatures(){
    struct Guard{uintptr_t rva;unsigned char bytes[16];};
    const Guard guards[]={
        {0x43ac173,{0xe8,0x78,0xca,0xff,0xff,0xe8,0xb3,0xc8,0x71,0,0x48,0x8d,0x4c,0x24,0x30,0xe8}},
        {0x43a8bf0,{0x48,0x89,0x5c,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x48,0x89,0x7c,0x24,0x20,0x55}},
        {0x43b43e0,{0x48,0x8b,0x51,0x10,0xb0,0x01,0x41,0xb8,0x0f,0x0b,0x4e,0xc3,0x48,0x83,0xc2,0x20}},
        {0x43b4640,{0x57,0x48,0x83,0xec,0x70,0x48,0x8b,0x05,0x14,0x3e,0xee,0xfe,0x48,0x31,0xe0,0x48}},
        {0x43b4530,{0x57,0x48,0x83,0xec,0x20,0x48,0x89,0xcf,0x48,0x8b,0x49,0x10,0x80,0x79,0x4a,0}},
        {0x4ac35e0,{0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x30,0x48}},
        {0x48b0990,{0xc6,0x41,0x10,0x00,0x48,0x8b,0x49,0x30,0x48,0x8b,0x89,0x40,0x07,0x00,0x00,0xe9}}
    };
    for(const auto& g:guards){
        unsigned char actual[16];if(!read_bytes(image+g.rva,actual,16))return false;
        if(g.rva==0x43ac173){
            if(memcmp(actual+5,g.bytes+5,11)||!compatible_builder_call(actual))return false;
        }else if(memcmp(actual,g.bytes,16))return false;
    }
    for(auto& p:overlayCalls){
        unsigned char actual[16];if(!read_bytes(image+p.rva,actual,16))return false;
        // Adjacent owned CALLs can occur within this 16-byte context.
        // Validate each CALL separately below, retaining every opcode and
        // every byte that is not the displacement of another owned CALL.
        for(size_t offset=5;offset<16;++offset){
            bool ownedDisplacement=false;
            for(const auto& other:overlayCalls){
                if(p.rva+offset>other.rva&&p.rva+offset<other.rva+5){ownedDisplacement=true;break;}
            }
            if(!ownedDisplacement&&actual[offset]!=p.bytes[offset])return false;
        }
        if(memcmp(actual,p.bytes,5)){
            if(!previousOwner||actual[0]!=0xe8)return false;
            int32_t displacement=0;memcpy(&displacement,actual+1,4);
            if(image+p.rva+5+displacement!=previousRelay+(p.show?16:32))return false;
        }
        memcpy(p.expected,actual,5);
    }
    for(auto& p:boundsCalls){
        if(!read_bytes(image+p.rva,p.expected,5))return false;
        if(memcmp(p.expected,p.bytes,5)){
            if(!previousOwner||p.expected[0]!=0xe8)return false;
            int32_t displacement=0;memcpy(&displacement,p.expected+1,4);
            const size_t index=(size_t)(&p-boundsCalls);
            if(image+p.rva+5+displacement!=previousRelay+(3+index)*16)return false;
        }
    }
    for(size_t i=0;i<3;++i){
        if(!get(image+serviceVtables[i],serviceExpected[i]))return false;
        if(serviceExpected[i]!=image+serviceNative[i]){
            HMODULE owner=nullptr;
            if(!previousOwner||!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCSTR)serviceExpected[i],&owner)||owner!=previousOwner)return false;
        }
    }
    if(!get(image+0x22933d8,lineupPostExpected))return false;
    if(lineupPostExpected!=image+0x48fe7f0){
        HMODULE owner=nullptr;
        if(!previousOwner||!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,
          (LPCSTR)lineupPostExpected,&owner)||owner!=previousOwner)return false;
    }
    return true;
}
static bool activate_lua_gate(){
    uintptr_t lua=0,globals=0;int tag=0;
    if(!get(image+0x3613fd0,lua)||!lua||!get(lua+0x80,tag)||tag!=5||!get(lua+0x78,globals)||!globals)return false;
    // The verified console entry acquires/releases the engine's Lua critical
    // section internally. This startup assignment calls no rendering/RNA API.
    static const char script[]="FIFA16_ENTRANCE_PROPS_HOOK_READY=true";
    __try{
        ((void(__fastcall*)(const char*,size_t,const char*))(image+0x4ac35e0))(script,sizeof(script)-1,"entrance_props_native_ready");
        return true;
    }__except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
static void* allocate_near(uintptr_t origin){
    SYSTEM_INFO info{};GetSystemInfo(&info);const uintptr_t step=info.dwAllocationGranularity,aligned=origin&~(step-1);
    for(uintptr_t d=step;d<0x70000000;d+=step)for(int side=0;side<2;++side){
        if(side&&aligned<d+0x10000)continue;
        void* p=VirtualAlloc((void*)(side?aligned-d:aligned+d),4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
        if(p)return p;
    }return nullptr;
}
static bool patch_call(){
    HANDLE handles[256]{};size_t count=0,suspended=0;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);if(snapshot==INVALID_HANDLE_VALUE)return false;
    THREADENTRY32 entry{};entry.dwSize=sizeof(entry);bool ok=true;
    for(BOOL found=Thread32First(snapshot,&entry);found;found=Thread32Next(snapshot,&entry)){
        if(entry.th32OwnerProcessID!=GetCurrentProcessId()||entry.th32ThreadID==GetCurrentThreadId())continue;
        if(count==256){ok=false;break;}
        HANDLE h=OpenThread(THREAD_SUSPEND_RESUME|THREAD_QUERY_LIMITED_INFORMATION|THREAD_GET_CONTEXT,FALSE,entry.th32ThreadID);
        if(!h){if(GetLastError()==ERROR_INVALID_PARAMETER)continue;ok=false;break;}handles[count++]=h;
    }CloseHandle(snapshot);
    constexpr size_t boundIndex=OverlayPatchCount+1,vtIndex=boundIndex+2,serviceIndex=vtIndex+1,siteCount=serviceIndex+3;
    void* sites[siteCount]{};SIZE_T sizes[siteCount]{};sites[0]=(void*)(preserveOuterBuilder?previousEntry:image+0x43ac173);sizes[0]=preserveOuterBuilder?14:5;
    for(size_t i=0;i<OverlayPatchCount;++i){sites[i+1]=(void*)(image+overlayCalls[i].rva);sizes[i+1]=5;}
    for(size_t i=0;i<2;++i){sites[boundIndex+i]=(void*)(image+boundsCalls[i].rva);sizes[boundIndex+i]=5;}
    sites[vtIndex]=(void*)(image+0x22933d8);sizes[vtIndex]=8;
    for(size_t i=0;i<3;++i){sites[serviceIndex+i]=(void*)(image+serviceVtables[i]);sizes[serviceIndex+i]=8;}
    DWORD protections[siteCount]{};size_t writable=0;DWORD ignored=0;
    for(;ok&&writable<siteCount;++writable)if(!VirtualProtect(sites[writable],sizes[writable],writable>=vtIndex?PAGE_READWRITE:PAGE_EXECUTE_READWRITE,&protections[writable])){ok=false;break;}
    if(ok)for(;suspended<count;++suspended)if(SuspendThread(handles[suspended])==(DWORD)-1){ok=false;break;}
    if(ok&&preserveOuterBuilder){
        for(size_t i=0;i<suspended&&ok;++i){CONTEXT context{};context.ContextFlags=CONTEXT_CONTROL;
            if(!GetThreadContext(handles[i],&context)||
               (context.Rip>previousEntry&&context.Rip<previousEntry+14))ok=false;
        }
    }
    if(ok){
        if(memcmp(sites[0],preserveOuterBuilder?previousEntrySaved:callExpected,sizes[0])||*(uintptr_t*)sites[vtIndex]!=lineupPostExpected)ok=false;
        if(preserveOuterBuilder&&memcmp((void*)(image+0x43ac173),callExpected,5))ok=false;
        for(size_t i=0;i<OverlayPatchCount&&ok;++i)if(memcmp(sites[i+1],overlayCalls[i].expected,5))ok=false;
    }
    if(ok){
        for(size_t i=0;i<2&&ok;++i)if(memcmp(sites[boundIndex+i],boundsCalls[i].expected,5))ok=false;
        for(size_t i=0;i<3&&ok;++i)if(*(uintptr_t*)sites[serviceIndex+i]!=serviceExpected[i])ok=false;
    }
    if(ok){
        memcpy(sites[0],preserveOuterBuilder?previousEntryApplied:callApplied,sizes[0]);
        for(size_t i=0;i<OverlayPatchCount;++i)memcpy(sites[i+1],overlayCalls[i].applied,5);
        for(size_t i=0;i<2;++i)memcpy(sites[boundIndex+i],boundsCalls[i].applied,5);
        InterlockedExchangePointer((void* volatile*)sites[vtIndex],(void*)lineup_post_hook);
        const uintptr_t services[3]={(uintptr_t)service_show_hook,(uintptr_t)service_update_hook,(uintptr_t)service_remove_hook};
        for(size_t i=0;i<3;++i)InterlockedExchangePointer((void* volatile*)sites[serviceIndex+i],(void*)services[i]);
        for(size_t i=0;i<vtIndex;++i)FlushInstructionCache(GetCurrentProcess(),sites[i],sizes[i]);
    }
    while(suspended)ResumeThread(handles[--suspended]);
    // Several call sites share one page: restore protections in reverse order.
    while(writable){--writable;VirtualProtect(sites[writable],sizes[writable],protections[writable],&ignored);}
    for(size_t i=0;i<count;++i)CloseHandle(handles[i]);return ok;
}
static DWORD WINAPI worker(void*){
    if(!enabled){event("disabled no_hook_or_reserved_model");return 0;}
    for(unsigned i=0;i<600&&!stopping;++i){
        if(!signatures()){Sleep(200);continue;}
        auto relay=(unsigned char*)allocate_near(image+0x43ac173);if(!relay){event("no_near_relay");return 0;}
        const unsigned char jmp[6]={0xff,0x25,0,0,0,0};
        const uintptr_t targets[5]={(uintptr_t)build_hook,(uintptr_t)overlay_show_hook,(uintptr_t)overlay_remove_hook,(uintptr_t)bounds_gather_hook,(uintptr_t)bounds_cull_hook};
        for(size_t k=0;k<5;++k){memcpy(relay+k*16,jmp,6);memcpy(relay+k*16+6,&targets[k],8);}
        DWORD ignored=0;
        if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&ignored)){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        const int64_t relative=(int64_t)(uintptr_t)relay-(int64_t)(image+0x43ac178);
        if(relative<INT32_MIN||relative>INT32_MAX){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        callApplied[0]=0xe8;const int32_t displacement=(int32_t)relative;memcpy(callApplied+1,&displacement,4);
        memcpy(previousEntryApplied,jmp,6);const uintptr_t builder=(uintptr_t)build_hook;memcpy(previousEntryApplied+6,&builder,8);
        bool ranges=true;
        for(auto& p:overlayCalls){
            const int64_t delta=(int64_t)(uintptr_t)(relay+(p.show?16:32))-(int64_t)(image+p.rva+5);
            if(delta<INT32_MIN||delta>INT32_MAX){ranges=false;break;}
            p.applied[0]=0xe8;const int32_t rel=(int32_t)delta;memcpy(p.applied+1,&rel,4);
        }
        for(size_t j=0;j<2;++j){
            const int64_t delta=(int64_t)(uintptr_t)(relay+(3+j)*16)-(int64_t)(image+boundsCalls[j].rva+5);
            if(delta<INT32_MIN||delta>INT32_MAX){ranges=false;break;}
            boundsCalls[j].applied[0]=0xe8;const int32_t relativeBounds=(int32_t)delta;memcpy(boundsCalls[j].applied+1,&relativeBounds,4);
        }
        if(!ranges){VirtualFree(relay,0,MEM_RELEASE);return 0;}
        originalBuild=(BuildFn)(image+0x43a8bf0);
        originalLineupPost=(LineupPostFn)(image+0x48fe7f0);
        originalOverlayShow=(OverlayShowFn)(image+0x48e9ae0);
        originalOverlayRemove=(OverlayRemoveFn)(image+0x48f2940);
        originalBoundsGather=(BoundsGatherFn)(image+0x4371600);
        originalBoundsCull=(BoundsCullFn)(image+0x4b15a80);
        originalServiceShow=(ServiceShowFn)(image+0x487a6b0);
        originalServiceUpdate=(ServiceUpdateFn)(image+0x487aa70);
        originalServiceRemove=(ServiceRemoveFn)(image+0x4878830);
        if(patch_call()){
            if(preserveOuterBuilder)event("outer_var_cabin_builder_preserved owned_v16_entry_forwarded");
            if(previousStop){previousStop();event("previous_revision_retired v18 owned_v16_hooks_replaced");}
            event("installed v18 experimental_static_rx3 preload_independent after_second_lineup_closed_hidden_transform yaw180 native_hook=43ac173 mascot_hook_preserved");
            for(unsigned attempt=0;attempt<600&&!stopping;++attempt){
                if(activate_lua_gate()){InterlockedExchange(&luaGateReady,1);event("lua_gate_ready dedicated_static_prototype_enabled");return 0;}
                Sleep(200);
            }
            event("lua_gate_unavailable normal_generic_models_preserved");return 0;
        }
        VirtualFree(relay,0,MEM_RELEASE);Sleep(200);
    }event("install_timeout_or_signature_conflict");return 0;
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* root){
    if(!root||InterlockedCompareExchange(&started,1,0))return FALSE;
    _snprintf_s(logPath,MAX_PATH,_TRUNCATE,"%s\\..\\logs\\entrance_props.log",root);
    _snprintf_s(configPath,MAX_PATH,_TRUNCATE,"%s\\entrance_props\\entrance_props.ini",root);
    enabled=GetPrivateProfileIntA("entrance_props","enabled",1,configPath)!=0;
    heightCm=(float)GetPrivateProfileIntA("entrance_props","ground_lift_cm",2,configPath);
    if(heightCm<0||heightCm>20)heightCm=2;
    _snprintf_s(presentationPath,MAX_PATH,_TRUNCATE,"%s\\..\\config\\match_presentation.ini",root);
    _snprintf_s(catalogPath,MAX_PATH,_TRUNCATE,"%s\\..\\config\\entrance_competitions.ini",root);
    image=(uintptr_t)GetModuleHandleA(nullptr);IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
    if(!GetModuleFileNameA((HMODULE)image,gameRoot,MAX_PATH))return FALSE;
    char* slash=strrchr(gameRoot,'\\');if(!slash)return FALSE;*slash=0;
    if(!get(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||
       !get(image+(uintptr_t)dos.e_lfanew,nt)||nt.Signature!=IMAGE_NT_SIGNATURE||
       nt.FileHeader.TimeDateStamp!=0x577de45c||nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64){event("unsupported_image");return FALSE;}
    HMODULE pinned=nullptr;if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,(LPCSTR)&started,&pinned))return FALSE;
    HANDLE h=CreateThread(nullptr,0,worker,nullptr,0,nullptr);if(!h)return FALSE;CloseHandle(h);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop(){
    InterlockedExchange(&stopping,1);event("stop_requested reserved_appearance_cleanup_retained_until_restart");return TRUE;
}
BOOL WINAPI DllMain(HINSTANCE dll,DWORD reason,LPVOID){if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(dll);return TRUE;}
