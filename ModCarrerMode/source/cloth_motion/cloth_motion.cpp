#include "call_patch.h"
#include "cloth_profile.h"
#include "native_particles.h"
#include "live_control.h"
#include <cstdio>
#include <cstdarg>
#include <cstdlib>
#include <memory>

using namespace cloth_motion;
using SetParameters=void*(__fastcall*)(void*,const Parameters*);
using Solve=void(__fastcall*)(void*,float,float);
using Skin=void(__fastcall*)(void*,const void*,unsigned,const void*);
static SetParameters nativeSet;
static Solve nativeSolve;
static Skin nativeSkin;
static uintptr_t image;
static volatile LONG started=0,stopping=0,mode=0;
static char logPath[MAX_PATH]{},iniPath[MAX_PATH]{},statePath[MAX_PATH]{};
static SRWLOCK configLock=SRWLOCK_INIT,registryLock=SRWLOCK_INIT;
static cloth_particles::Config config;
static volatile LONG64 jerseyUpdates=0,shortsUpdates=0,otherUpdates=0,solveUpdates=0;
static volatile LONG64 customSteps=0,customResets=0,bindFailures=0,nativeFallbacks=0;
static volatile LONG64 pairedSolves=0,waistContacts=0;
static volatile LONG64 bodySolves=0,bodyContacts=0,edgeContacts=0,bodyReadFailures=0;
static volatile LONG64 armSolves=0,armContacts=0,armEdgeContacts=0;
static volatile LONG64 hemFoldContacts=0,hemSelfContacts=0,waistFallbacks=0;
static volatile LONG64 sampledMicros[2]{},sampledCounts[2]{};
static LARGE_INTEGER performanceFrequency{};
struct ParticleRuntime {
    SRWLOCK lock=SRWLOCK_INIT;
    cloth_particles::Mesh mesh;
    cloth_particles::State state;
    cloth_particles::View view;
    std::vector<cloth_particles::Vec> target,normals;
    std::vector<cloth_particles::Point> output,previous;
    std::vector<cloth_particles::BodyCapsule> body;
    uintptr_t definition=0,data=0,rest=0;
    bool reported=false,failureReported=false;
    unsigned sampleCounter=0;
    cloth_particles::Piece piece=cloth_particles::Piece::Generic;
};
struct Entry { uintptr_t instance=0,owner=0;Garment kind=Garment::Other;uint64_t stamp=0;std::shared_ptr<ParticleRuntime> runtime;uintptr_t actor=0;unsigned bones=0; };
static Entry entries[256];
static uint64_t registryStamp=0;
static char firstOther[64]{};
struct ContactCacheEntry {
    uintptr_t actor=0;unsigned bones=0;uint64_t stamp=0;
    std::shared_ptr<const cloth_particles::ContactSurface> surface;
};
static SRWLOCK contactLock=SRWLOCK_INIT;
static ContactCacheEntry contacts[128];
static std::shared_ptr<const cloth_particles::ContactSurface> contact_for(uintptr_t actor,unsigned bones) {
    if(!actor||!bones)return {};
    const uint64_t now=GetTickCount64();std::shared_ptr<const cloth_particles::ContactSurface> result;
    AcquireSRWLockShared(&contactLock);
    for(const auto& slot:contacts)if(slot.actor==actor&&slot.bones==bones&&now-slot.stamp<=250){result=slot.surface;break;}
    ReleaseSRWLockShared(&contactLock);return result;
}
static void publish_contact(uintptr_t actor,unsigned bones,std::shared_ptr<const cloth_particles::ContactSurface> surface) {
    if(!actor||!bones)return;
    AcquireSRWLockExclusive(&contactLock);
    ContactCacheEntry* destination=nullptr;auto* oldest=&contacts[0];
    for(auto& slot:contacts) {
        if(slot.actor==actor&&slot.bones==bones){destination=&slot;break;}
        if(!slot.actor&&!destination)destination=&slot;
        if(slot.stamp<oldest->stamp)oldest=&slot;
    }
    if(!destination)destination=oldest;
    *destination={actor,bones,GetTickCount64(),std::move(surface)};
    ReleaseSRWLockExclusive(&contactLock);
}

static void event(const char* format,...) {
    FILE* file=nullptr;if(fopen_s(&file,logPath,"ab")||!file)return;
    std::fprintf(file,"%llu pid=%lu ",GetTickCount64(),GetCurrentProcessId());
    va_list args;va_start(args,format);std::vfprintf(file,format,args);va_end(args);
    std::fputc('\n',file);std::fclose(file);
}
static bool read_bytes(uintptr_t address,void* out,size_t size) {
    if(address<0x10000||size>131072||address>UINTPTR_MAX-size)return false;
    // These pointers belong to this DLL's host process. A guarded local copy
    // avoids thousands of cross-process API transitions per rendered frame.
    __try{std::memcpy(out,reinterpret_cast<const void*>(address),size);return true;}
    __except(EXCEPTION_EXECUTE_HANDLER){return false;}
}
template<class T>static bool read_value(uintptr_t address,T& out){return read_bytes(address,&out,sizeof(out));}
static cloth_particles::Config profile() {
    AcquireSRWLockShared(&configLock);const auto value=config;ReleaseSRWLockShared(&configLock);return value;
}
static float setting(const char* key,float fallback) {
    char value[64]{},defaultValue[64]{};
    sprintf_s(defaultValue,"%.9g",static_cast<double>(fallback));
    GetPrivateProfileStringA("cloth_motion",key,defaultValue,value,sizeof(value),iniPath);
    char* end=nullptr;const float result=std::strtof(value,&end);
    return end!=value&&!*end?result:fallback;
}
static void load_config() {
    cloth_particles::Config next{};
    next.stretch=setting("stretch_compliance",next.stretch);
    next.compression=setting("compression_compliance",next.compression);
    next.bend=setting("bend_compliance",next.bend);
    next.pin=setting("pin_compliance",next.pin);
    next.damping=setting("velocity_damping",next.damping);
    next.airDrag=setting("air_drag",next.airDrag);
    next.clearance=setting("cloth_clearance_m",next.clearance);
    next.collisionInset=setting("collision_inset_m",next.collisionInset);
    next.friction=setting("body_friction",next.friction);
    next.maxDistance=setting("max_distance_m",next.maxDistance);
    next.maxSpeed=setting("max_relative_speed",next.maxSpeed);
    next.restAdaptation=setting("rest_adaptation",next.restAdaptation);
    next.wind=setting("wind_speed_m_s",next.wind);
    next.motion=setting("motion_inertia",next.motion);
    next.shoulderInset=setting("shoulder_inset_m",next.shoulderInset);
    next.shortsInset=setting("shorts_fit_inset_m",next.shortsInset);
    next.shortsBodyInset=setting("shorts_body_inset_m",next.shortsBodyInset);
    next.shortsBend=setting("shorts_bend_compliance",next.shortsBend);
    next.shortsPinScale=setting("shorts_pin_scale",next.shortsPinScale);
    next.shortsGravity=setting("shorts_gravity_scale",next.shortsGravity);
    next.waistClearance=setting("waist_clearance_m",next.waistClearance);
    next.contactRadius=setting("waist_contact_radius_m",next.contactRadius);
    next.bodyMargin=setting("leg_collision_margin_m",next.bodyMargin);
    next.chestVolume=setting("chest_volume_m",next.chestVolume);
    next.hemFreedom=setting("jersey_hem_freedom",next.hemFreedom);
    next.hemDamping=setting("jersey_hem_damping_scale",next.hemDamping);
    next.foldInset=setting("jersey_fold_inset_m",next.foldInset);
    next.shortsHemLift=setting("shorts_hem_lift_m",next.shortsHemLift);
    next.jerseyFreedom=setting("jersey_fabric_freedom",next.jerseyFreedom);
    next.torsoInset=setting("jersey_torso_inset_m",next.torsoInset);
    next.chestStability=setting("jersey_chest_stability",next.chestStability);
    next.sleeveInset=setting("sleeve_collision_inset_m",next.sleeveInset);
    next.armMargin=setting("arm_collision_margin_m",next.armMargin);
    next.jerseyShrink=setting("jersey_size_reduction",next.jerseyShrink);
    next.chestMax=setting("jersey_chest_max_offset_m",next.chestMax);
    next.frequency=GetPrivateProfileIntA("cloth_motion","solver_hz",next.frequency,iniPath);
    next.iterations=GetPrivateProfileIntA("cloth_motion","solver_iterations",next.iterations,iniPath);
    next=cloth_particles::validate(next);
    AcquireSRWLockExclusive(&configLock);config=next;ReleaseSRWLockExclusive(&configLock);
    const bool enabled=cloth_control::read_enabled(iniPath)==1;
    InterlockedExchange(&mode,enabled?1:0);
    event("configuration version=0.8.2 solver=xpbd_cpu mode=%s stretch=%g compression=%g bend=%g damping=%.3f clearance_m=%.4f wind_m_s=%.3f hz=%u iterations=%u",
          enabled?"mod":"original",static_cast<double>(next.stretch),static_cast<double>(next.compression),
          static_cast<double>(next.bend),static_cast<double>(next.damping),static_cast<double>(next.clearance),
          static_cast<double>(next.wind),next.frequency,next.iterations);
}
static Garment register_instance(void* instance,const Parameters* source) {
    const uintptr_t key=reinterpret_cast<uintptr_t>(instance),owner=reinterpret_cast<uintptr_t>(source)-0x10;
    uintptr_t namePointer=0;char name[64]{};
    Garment kind=Garment::Other;
    if(read_value(owner+0x88,namePointer)&&read_bytes(namePointer,name,sizeof(name)-1))kind=garment(name);
    AcquireSRWLockExclusive(&registryLock);
    Entry* slot=nullptr;Entry* oldest=&entries[0];
    for(auto& entry:entries) {
        if(entry.instance==key) {
            if(entry.owner==owner&&entry.kind==kind) {
                entry.stamp=++registryStamp;
                ReleaseSRWLockExclusive(&registryLock);return kind;
            }
            // The engine can recycle an address for a different garment or
            // hair. Replace its identity instead of retaining a stale row.
            slot=&entry;break;
        }
        if(!entry.instance&&!slot)slot=&entry;
        if(entry.stamp<oldest->stamp)oldest=&entry;
    }
    if(!slot)slot=oldest;
    if(kind==Garment::Other&&!firstOther[0])strcpy_s(firstOther,name[0]?name:"unreadable");
    std::shared_ptr<ParticleRuntime> runtime;
    if(kind!=Garment::Other) {
        try{runtime=std::make_shared<ParticleRuntime>();}catch(...){runtime.reset();}
        if(runtime)runtime->piece=kind==Garment::Shorts?cloth_particles::Piece::Shorts:cloth_particles::Piece::Jersey;
    }
    *slot=Entry{key,owner,kind,++registryStamp,std::move(runtime)};
    ReleaseSRWLockExclusive(&registryLock);return kind;
}
static void* __fastcall parameters_hook(void* instance,const Parameters* source) {
    if(stopping)return nativeSet(instance,source);
    const auto kind=register_instance(instance,source);
    if(kind==Garment::Jersey)InterlockedIncrement64(&jerseyUpdates);
    else if(kind==Garment::Shorts)InterlockedIncrement64(&shortsUpdates);
    else InterlockedIncrement64(&otherUpdates);
    // Keep factory parameters byte-for-byte. F6 and unsupported assets use
    // the actual native solver, without the v0.1 tuning or periodic wind.
    return nativeSet(instance,source);
}
static void __fastcall skin_hook(void* instance,const void* bones,unsigned count,const void* transform) {
    nativeSkin(instance,bones,count,transform);
    if(stopping||!bones||!count||count>512)return;
    // Use the actual pose palette identity. Proximity cannot safely pair
    // two pieces when several players share the same model-space origin.
    AcquireSRWLockExclusive(&registryLock);
    for(auto& entry:entries)if(entry.instance==reinterpret_cast<uintptr_t>(instance)) {
        entry.actor=reinterpret_cast<uintptr_t>(bones);entry.bones=count;break;
    }
    ReleaseSRWLockExclusive(&registryLock);
}
static bool writable(uintptr_t address,size_t size) {
    if(address<0x10000||address>UINTPTR_MAX-size)return false;
    const uintptr_t end=address+size;
    while(address<end) {
        MEMORY_BASIC_INFORMATION info{};
        if(!VirtualQuery(reinterpret_cast<void*>(address),&info,sizeof(info))||info.State!=MEM_COMMIT||
           (info.Protect&(PAGE_GUARD|PAGE_NOACCESS))||
           !(info.Protect&(PAGE_READWRITE|PAGE_WRITECOPY|PAGE_EXECUTE_READWRITE|PAGE_EXECUTE_WRITECOPY)))return false;
        const uintptr_t regionEnd=reinterpret_cast<uintptr_t>(info.BaseAddress)+info.RegionSize;
        if(regionEnd<=address)return false;address=regionEnd;
    }
    return true;
}
static bool custom_solve(ParticleRuntime& runtime,void* instance,float dt,uintptr_t actor,unsigned bones) {
    auto reader=[](uintptr_t at,void* data,size_t size){return read_bytes(at,data,size);};
    if(!cloth_particles::view(reader,reinterpret_cast<uintptr_t>(instance),runtime.view)) {
        if(!runtime.failureReported){event("particle_binding_failed instance=%p stage=point_descriptors native_fallback=1",instance);runtime.failureReported=true;}
        InterlockedIncrement64(&bindFailures);runtime.state.ready=false;return false;
    }
    const auto& view=runtime.view;
    if(runtime.definition!=view.definition||runtime.data!=view.current.data||runtime.rest!=view.restHeader||runtime.mesh.rest.size()!=view.current.count) {
        if(!cloth_particles::build_mesh(reader,view,runtime.mesh,runtime.piece)) {
            if(!runtime.failureReported){event("particle_binding_failed instance=%p stage=mesh_constraints points=%u native_fallback=1",instance,view.current.count);runtime.failureReported=true;}
            InterlockedIncrement64(&bindFailures);runtime.state.ready=false;return false;
        }
        runtime.definition=view.definition;runtime.data=view.current.data;runtime.rest=view.restHeader;
        runtime.state.ready=false;runtime.reported=false;
    }
    cloth_particles::targets(view,runtime.target,runtime.normals);
    const auto partner=runtime.piece==cloth_particles::Piece::Jersey?contact_for(actor,bones):nullptr;
    const auto oldContacts=runtime.state.contacts;
    const auto oldBodyContacts=runtime.state.bodyContacts;
    const auto oldEdgeContacts=runtime.state.edgeContacts;
    const auto oldFolds=runtime.state.foldContacts,oldSelf=runtime.state.selfContacts,oldWaistFallbacks=runtime.state.waistFallbacks;
    if(!cloth_particles::body_capsules(reader,reinterpret_cast<uintptr_t>(instance),runtime.body)) {
        runtime.body.clear();InterlockedIncrement64(&bodyReadFailures);
    }
    cloth_particles::append_sleeve_proxies(runtime.mesh,runtime.target,runtime.body);
    const auto result=cloth_particles::step(runtime.mesh,runtime.state,runtime.target,runtime.normals,dt,profile(),partner.get(),
        runtime.body.empty()?nullptr:&runtime.body);
    if(result==cloth_particles::Result::Invalid)return false;
    if(result==cloth_particles::Result::Paused)return true;
    if(partner)InterlockedIncrement64(&pairedSolves);
    InterlockedAdd64(&waistContacts,static_cast<LONG64>(runtime.state.contacts-oldContacts));
    InterlockedAdd64(&hemFoldContacts,static_cast<LONG64>(runtime.state.foldContacts-oldFolds));
    InterlockedAdd64(&hemSelfContacts,static_cast<LONG64>(runtime.state.selfContacts-oldSelf));
    InterlockedAdd64(&waistFallbacks,static_cast<LONG64>(runtime.state.waistFallbacks-oldWaistFallbacks));
    if(runtime.piece==cloth_particles::Piece::Shorts) {
        if(!runtime.body.empty())InterlockedIncrement64(&bodySolves);
        InterlockedAdd64(&bodyContacts,static_cast<LONG64>(runtime.state.bodyContacts-oldBodyContacts));
        InterlockedAdd64(&edgeContacts,static_cast<LONG64>(runtime.state.edgeContacts-oldEdgeContacts));
    }else {
        if(!runtime.body.empty())InterlockedIncrement64(&armSolves);
        InterlockedAdd64(&armContacts,static_cast<LONG64>(runtime.state.bodyContacts-oldBodyContacts));
        InterlockedAdd64(&armEdgeContacts,static_cast<LONG64>(runtime.state.edgeContacts-oldEdgeContacts));
    }
    if(!cloth_particles::output(view,runtime.state,dt,runtime.output,runtime.previous))return false;
    const size_t size=runtime.output.size()*sizeof(cloth_particles::Point);
    std::shared_ptr<cloth_particles::ContactSurface> surface;
    if(runtime.piece==cloth_particles::Piece::Shorts&&actor&&bones) {
        surface=std::make_shared<cloth_particles::ContactSurface>();
        surface->samples.reserve(runtime.mesh.waistSamples.size());
        for(auto i:runtime.mesh.waistSamples)surface->samples.push_back({runtime.state.position[i],
            cloth_particles::contact_normal(runtime.mesh,runtime.state.position,runtime.normals,i)});
        surface->prepare();
    }
    if(!writable(view.current.data,size)||!writable(view.previous.data,size)||!writable(view.history.data,size))return false;
    std::memcpy(reinterpret_cast<void*>(view.current.data),runtime.output.data(),size);
    std::memcpy(reinterpret_cast<void*>(view.previous.data),runtime.previous.data(),size);
    // Native 4a9801b copies the animated pose into its history buffer. Keep
    // this handoff valid when F6 returns to native solving on the next frame.
    std::memcpy(reinterpret_cast<void*>(view.history.data),view.targets.data(),size);
    if(surface)publish_contact(actor,bones,std::move(surface));
    if(result==cloth_particles::Result::Reset)InterlockedIncrement64(&customResets);
    else InterlockedIncrement64(&customSteps);
    if(!runtime.reported) {
        event("particle_binding_active instance=%p points=%u edges=%zu body_capsules=%zu solver=xpbd_cpu factory_wrap_and_normals=retained",
              instance,view.current.count,runtime.mesh.edges.size(),runtime.body.size());runtime.reported=true;
    }
    runtime.failureReported=false;
    return true;
}
static void __fastcall solve_hook(void* instance,float dt,float previousDt) {
    std::shared_ptr<ParticleRuntime> runtime;
    uintptr_t actor=0;unsigned bones=0;
    if(!stopping) {
        AcquireSRWLockShared(&registryLock);
        for(const auto& entry:entries)if(entry.instance==reinterpret_cast<uintptr_t>(instance)) {runtime=entry.runtime;actor=entry.actor;bones=entry.bones;break;}
        ReleaseSRWLockShared(&registryLock);
    }
    if(runtime) {
        InterlockedIncrement64(&solveUpdates);
        AcquireSRWLockExclusive(&runtime->lock);
        bool handled=false;
        if(InterlockedCompareExchange(&mode,0,0)) {
            const bool sample=dt>1e-6f&&performanceFrequency.QuadPart>0&&((runtime->sampleCounter++&63u)==0);
            LARGE_INTEGER begin{};if(sample)QueryPerformanceCounter(&begin);
            try{handled=custom_solve(*runtime,instance,dt,actor,bones);}catch(...){runtime->state.ready=false;}
            if(sample&&handled) {
                LARGE_INTEGER end{};QueryPerformanceCounter(&end);
                const unsigned index=runtime->piece==cloth_particles::Piece::Shorts?1:0;
                InterlockedAdd64(&sampledMicros[index],(end.QuadPart-begin.QuadPart)*1000000/performanceFrequency.QuadPart);
                InterlockedIncrement64(&sampledCounts[index]);
            }
        }
        if(!handled)runtime->state.ready=false;
        ReleaseSRWLockExclusive(&runtime->lock);
        if(handled)return;
        InterlockedIncrement64(&nativeFallbacks);
    }
    nativeSolve(instance,dt,previousDt);
}
static bool code_ready() {
    static const unsigned char beforeParameters[]={0x48,0x8b,0x4e,0x08,0x48,0x8d,0x56,0x10,0x48,0x89,0xc7,0xe8,0xd7,0x34,0x68,0x00};
    static const unsigned char beforeSolve[]={0x48,0x8b,0x4e,0x08,0xf3,0x0f,0x10,0x96,0x00,0x03,0x00,0x00,0x41,0x0f,0x28,0xca,0x48,0x89,0xc3,0xe8,0x64,0x5a,0x68,0x00};
    static const unsigned char setter[]={0x48,0x83,0xc1,0x68,0xe9,0xd7,0x5a,0xff,0xff};
    static const unsigned char solver[]={0x48,0x89,0x5c,0x24,0x08,0x48,0x89,0x74,0x24,0x10,0x57,0x48,0x83,0xec,0x40};
    static const unsigned char skinCall[]={0x0f,0x29,0x4c,0x24,0x50,0xe8,0x48,0xe8,0x68,0x00};
    unsigned char skinBytes[sizeof(skinCall)]{};
    unsigned char a[sizeof(beforeParameters)]{},b[sizeof(beforeSolve)]{},c[sizeof(setter)]{},d[sizeof(solver)]{};
    return read_bytes(image+0x4412509,a,sizeof(a))&&!std::memcmp(a,beforeParameters,sizeof(a))&&
           read_bytes(image+0x44125e4,b,sizeof(b))&&!std::memcmp(b,beforeSolve,sizeof(b))&&
           read_bytes(image+0x4a959f0,c,sizeof(c))&&!std::memcmp(c,setter,sizeof(c))&&
           read_bytes(image+0x4a98060,d,sizeof(d))&&!std::memcmp(d,solver,sizeof(d))&&
           read_bytes(image+0x441257e,skinBytes,sizeof(skinBytes))&&!std::memcmp(skinBytes,skinCall,sizeof(skinCall));
}
static bool install() {
    auto* relay=static_cast<unsigned char*>(allocate_near(image+0x4412514));
    if(!relay){event("not_installed reason=relay_allocation");return false;}
    const uintptr_t targets[]={reinterpret_cast<uintptr_t>(&parameters_hook),reinterpret_cast<uintptr_t>(&solve_hook),reinterpret_cast<uintptr_t>(&skin_hook)};
    const unsigned char jump[]={0xff,0x25,0,0,0,0};
    for(size_t i=0;i<3;++i){std::memcpy(relay+i*16,jump,6);std::memcpy(relay+i*16+6,&targets[i],8);}
    DWORD old=0;
    if(!VirtualProtect(relay,4096,PAGE_EXECUTE_READ,&old)){VirtualFree(relay,0,MEM_RELEASE);return false;}
    FlushInstructionCache(GetCurrentProcess(),relay,4096);
    CallPatch patches[3]{};
    patches[0].address=image+0x4412514;patches[1].address=image+0x44125f7;patches[2].address=image+0x4412583;
    const unsigned char setCall[]={0xe8,0xd7,0x34,0x68,0x00},solveCall[]={0xe8,0x64,0x5a,0x68,0x00};
    std::memcpy(patches[0].expected,setCall,5);std::memcpy(patches[1].expected,solveCall,5);
    const unsigned char skinCall[]={0xe8,0x48,0xe8,0x68,0x00};std::memcpy(patches[2].expected,skinCall,5);
    if(!make_call(patches[0],reinterpret_cast<uintptr_t>(relay))||
       !make_call(patches[1],reinterpret_cast<uintptr_t>(relay+16))||
       !make_call(patches[2],reinterpret_cast<uintptr_t>(relay+32))||!install_calls(patches,3)) {
        VirtualFree(relay,0,MEM_RELEASE);return false;
    }
    return true;
}
static DWORD WINAPI worker(void*) {
    load_config();bool installed=false;
    for(unsigned i=0;i<600&&!stopping;++i) {
        if(code_ready()&&install()){installed=true;break;}
        Sleep(100);
    }
    if(!installed){event("not_installed reason=signature_or_thread_conflict no_native_code_changed");return 1;}
    event("installed version=0.8.2 native_frame_parameters=4412514 native_skin=4412583 native_solve=44125f7 solver=xpbd_cpu controls=F6_toggle_F7_reload gameplay_validation=pending");
    bool previousToggle=false,previousReload=false;
    int requestedMode=InterlockedCompareExchange(&mode,0,0);
    uint64_t nextStatus=0,nextControl=0,nextHeartbeat=0;
    while(!stopping) {
        const bool toggle=(GetAsyncKeyState(VK_F6)&0x8000)!=0,reload=(GetAsyncKeyState(VK_F7)&0x8000)!=0;
        DWORD foregroundPid=0;GetWindowThreadProcessId(GetForegroundWindow(),&foregroundPid);
        if(foregroundPid==GetCurrentProcessId()) {
            if(toggle&&!previousToggle) {
                const LONG value=InterlockedCompareExchange(&mode,0,0)?0:1;InterlockedExchange(&mode,value);
                if(WritePrivateProfileStringA("cloth_motion","enabled",value?"1":"0",iniPath))requestedMode=value;
                nextHeartbeat=0;
                event("comparison mode=%s",value?"mod":"original");
            }
            if(reload&&!previousReload){load_config();requestedMode=InterlockedCompareExchange(&mode,0,0);nextHeartbeat=0;}
        }
        previousToggle=toggle;previousReload=reload;
        const uint64_t now=GetTickCount64();
        if(now>=nextControl) {
            const int value=cloth_control::read_enabled(iniPath);
            if(value>=0&&value!=requestedMode) {
                requestedMode=value;InterlockedExchange(&mode,value);nextHeartbeat=0;
                event("server_control mode=%s",value?"mod":"original");
            }
            nextControl=now+250;
        }
        if(now>=nextHeartbeat){cloth_control::publish(statePath,InterlockedCompareExchange(&mode,0,0)!=0);nextHeartbeat=now+1000;}
        if(now>=nextStatus) {
            char other[64]{};AcquireSRWLockShared(&registryLock);strcpy_s(other,firstOther);ReleaseSRWLockShared(&registryLock);
            event("status mode=%s jersey_updates=%lld shorts_updates=%lld garment_solves=%lld other_updates=%lld xpbd_steps=%lld xpbd_resets=%lld binding_failures=%lld native_fallbacks=%lld paired_solves=%lld waist_contacts=%lld body_solves=%lld body_contacts=%lld edge_contacts=%lld body_read_failures=%lld arm_solves=%lld arm_contacts=%lld arm_edge_contacts=%lld first_other=%s",
                  InterlockedCompareExchange(&mode,0,0)?"mod":"original",
                  InterlockedCompareExchange64(&jerseyUpdates,0,0),InterlockedCompareExchange64(&shortsUpdates,0,0),
                  InterlockedCompareExchange64(&solveUpdates,0,0),InterlockedCompareExchange64(&otherUpdates,0,0),
                  InterlockedCompareExchange64(&customSteps,0,0),InterlockedCompareExchange64(&customResets,0,0),
                  InterlockedCompareExchange64(&bindFailures,0,0),InterlockedCompareExchange64(&nativeFallbacks,0,0),
                  InterlockedCompareExchange64(&pairedSolves,0,0),InterlockedCompareExchange64(&waistContacts,0,0),
                  InterlockedCompareExchange64(&bodySolves,0,0),InterlockedCompareExchange64(&bodyContacts,0,0),
                  InterlockedCompareExchange64(&edgeContacts,0,0),InterlockedCompareExchange64(&bodyReadFailures,0,0),
                  InterlockedCompareExchange64(&armSolves,0,0),InterlockedCompareExchange64(&armContacts,0,0),
                  InterlockedCompareExchange64(&armEdgeContacts,0,0),other);
            const auto jerseySamples=InterlockedCompareExchange64(&sampledCounts[0],0,0),shortsSamples=InterlockedCompareExchange64(&sampledCounts[1],0,0);
            event("hem fold_contacts=%lld self_contacts=%lld waist_outward_refinements=%lld timing_sample=1/64 jersey_samples=%lld jersey_mean_us=%.3f shorts_samples=%lld shorts_mean_us=%.3f",
                InterlockedCompareExchange64(&hemFoldContacts,0,0),InterlockedCompareExchange64(&hemSelfContacts,0,0),InterlockedCompareExchange64(&waistFallbacks,0,0),
                jerseySamples,jerseySamples?static_cast<double>(InterlockedCompareExchange64(&sampledMicros[0],0,0))/static_cast<double>(jerseySamples):0,
                shortsSamples,shortsSamples?static_cast<double>(InterlockedCompareExchange64(&sampledMicros[1],0,0))/static_cast<double>(shortsSamples):0);
            nextStatus=now+10000;
        }
        Sleep(20);
    }
    event("stopped native_forwarding_retained_until_exit");return 0;
}
extern "C" __declspec(dllexport) unsigned WINAPI Fifa16ModGetApiVersion(){return 1;}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char* root) {
    if(!root||!*root||InterlockedCompareExchange(&started,1,0))return FALSE;
    char logs[MAX_PATH]{};sprintf_s(logs,"%s\\..\\logs",root);CreateDirectoryA(logs,nullptr);
    sprintf_s(logPath,"%s\\cloth_motion.log",logs);
    sprintf_s(iniPath,"%s\\cloth_motion\\cloth_motion.ini",root);
    sprintf_s(statePath,"%s\\cloth_motion\\runtime_state.txt",root);
    image=reinterpret_cast<uintptr_t>(GetModuleHandleW(nullptr));
    QueryPerformanceFrequency(&performanceFrequency);
    IMAGE_DOS_HEADER dos{};IMAGE_NT_HEADERS64 nt{};
    if(!read_value(image,dos)||dos.e_magic!=IMAGE_DOS_SIGNATURE||dos.e_lfanew<=0||dos.e_lfanew>4096||
       !read_value(image+static_cast<uintptr_t>(dos.e_lfanew),nt)||nt.Signature!=IMAGE_NT_SIGNATURE||
       nt.FileHeader.Machine!=IMAGE_FILE_MACHINE_AMD64||nt.FileHeader.TimeDateStamp!=0x577de45c) {
        event("unsupported_executable no_patch");return FALSE;
    }
    nativeSet=reinterpret_cast<SetParameters>(image+0x4a959f0);
    nativeSolve=reinterpret_cast<Solve>(image+0x4a98060);
    nativeSkin=reinterpret_cast<Skin>(image+0x4aa0dd0);
    HMODULE pinned=nullptr;
    if(!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,reinterpret_cast<LPCSTR>(&image),&pinned))return FALSE;
    HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);
    if(!thread)return FALSE;CloseHandle(thread);return TRUE;
}
extern "C" __declspec(dllexport) BOOL WINAPI Fifa16ModStop() {
    InterlockedExchange(&stopping,1);return TRUE;
}
BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID) {
    if(reason==DLL_PROCESS_ATTACH)DisableThreadLibraryCalls(instance);return TRUE;
}
