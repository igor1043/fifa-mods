#include "cloth_motion.cpp"

static unsigned setCalls=0,solveCalls=0;
static void* __fastcall fake_set(void* instance,const Parameters* parameters) {
    ++setCalls;auto* destination=static_cast<unsigned char*>(instance)+0x68;
    std::memcpy(destination,parameters,sizeof(*parameters));return destination;
}
static void __fastcall fake_solve(void*,float,float){++solveCalls;}
static unsigned skinCalls=0;
static void __fastcall fake_skin(void*,const void*,unsigned,const void*){++skinCalls;}
template<class T>static void link(unsigned char* block,size_t offset,T* pointer) {
    const uintptr_t address=reinterpret_cast<uintptr_t>(pointer);std::memcpy(block+offset,&address,8);
}
#define CHECK(condition) do {if(!(condition)){std::fprintf(stderr,"FAIL native frame line %d: %s\n",__LINE__,#condition);return 1;}}while(false)
int main() {
    using namespace cloth_particles;
    CHECK(GetFullPathNameA("cloth_motion.ini",MAX_PATH,iniPath,nullptr)>0);
    load_config();CHECK(config.stretch==1e-7f&&config.wind==0&&config.frequency==120&&config.iterations==1);
    CHECK(InterlockedCompareExchange(&mode,0,0)==0);
    char actualIni[MAX_PATH]{};strcpy_s(actualIni,iniPath);
    char temporary[MAX_PATH]{};CHECK(GetTempPathA(MAX_PATH,temporary)>0&&GetTempFileNameA(temporary,"clt",0,iniPath));
    // An unconfigured installation stays off; a saved explicit choice survives
    // repeated config loads, as it does across a fresh game instance.
    load_config();CHECK(InterlockedCompareExchange(&mode,0,0)==0);
    CHECK(WritePrivateProfileStringA("cloth_motion","enabled","1",iniPath));
    load_config();CHECK(InterlockedCompareExchange(&mode,0,0)==1);
    load_config();CHECK(InterlockedCompareExchange(&mode,0,0)==1);
    CHECK(WritePrivateProfileStringA("cloth_motion","enabled","0",iniPath));
    load_config();CHECK(InterlockedCompareExchange(&mode,0,0)==0);
    CHECK(DeleteFileA(iniPath));strcpy_s(iniPath,actualIni);load_config();
    InterlockedExchange(&mode,1); // Exercise the opt-in simulation below.
    CHECK(garment("simhair_jersey")==Garment::Other&&garment("SHORTSCLOTH")==Garment::Shorts);
    nativeSet=fake_set;nativeSolve=fake_solve;nativeSkin=fake_skin;
    alignas(16) unsigned char owner[0x100]{},instance[0x108]{},hairOwner[0x100]{},definition[0x120]{};
    char jerseyName[64]="jersey",hairName[64]="hair";
    link(owner,0x88,jerseyName);link(hairOwner,0x88,hairName);
    auto* source=reinterpret_cast<Parameters*>(owner+0x10);
    source->number(4,-200);source->number(Damping,.065f);source->number(Fold,.4f);source->number(AnchorFactor,1);
    const Parameters baseline=*source;
    Point bind[4]={{-5,150,0,0},{5,150,0,0},{-5,130,0,1},{5,130,0,1}};
    Point current[4],previous[4],posed[4],history[4]{},normals[4];
    std::memcpy(current,bind,sizeof(bind));std::memcpy(previous,bind,sizeof(bind));std::memcpy(posed,bind,sizeof(bind));
    for(auto& p:normals)p={0,0,1,1};
    const auto descriptor=[](Point* p){return PointSet{reinterpret_cast<uintptr_t>(p),4,4,64,0};};
    auto currentSet=descriptor(current),previousSet=descriptor(previous),bindSet=descriptor(bind),posedSet=descriptor(posed),normalSet=descriptor(normals),historySet=descriptor(history);
    NativeEdge structural[]={{0,1,10},{0,2,20},{1,3,20},{2,3,10}};
    NativeEdge shear[]={{0,3,std::sqrt(500.0f)},{1,2,std::sqrt(500.0f)}};
    NativeEdge bend[]={{0,3,std::sqrt(500.0f)}};
    ConstraintSet sets[]={{reinterpret_cast<uintptr_t>(structural),4,4},{reinterpret_cast<uintptr_t>(shear),2,4},{reinterpret_cast<uintptr_t>(bend),1,4}};
    link(instance,0,&currentSet);link(instance,8,&previousSet);link(instance,0x10,definition);
    link(instance,0xf0,&posedSet);link(instance,0xf8,&historySet);link(instance,0x100,&normalSet);link(definition,0x90,&bindSet);link(definition,0x98,&normalSet);
    for(unsigned i=0;i<3;++i)link(definition,0xa0+i*8,&sets[i]);
    CHECK(parameters_hook(instance,source)==instance+0x68);
    skin_hook(instance,owner,32,nullptr);CHECK(skinCalls==1);
    CHECK(entries[0].actor==reinterpret_cast<uintptr_t>(owner)&&entries[0].bones==32);
    auto surface=std::make_shared<ContactSurface>();surface->samples.push_back({{0,1,0},{0,0,1}});
    publish_contact(reinterpret_cast<uintptr_t>(owner),32,surface);
    CHECK(contact_for(reinterpret_cast<uintptr_t>(owner),32)==surface);
    CHECK(!contact_for(reinterpret_cast<uintptr_t>(hairOwner),32)&&!contact_for(reinterpret_cast<uintptr_t>(owner),31));
    contacts[0].stamp=GetTickCount64()-251;CHECK(!contact_for(reinterpret_cast<uintptr_t>(owner),32));
    CHECK(!std::memcmp(instance+0x68,&baseline,sizeof(baseline)));
    solve_hook(instance,1.0f/60,1.0f/60);
    CHECK(setCalls==1&&solveCalls==0&&customResets==1);
    for(unsigned frame=1;frame<=60;++frame) {
        posed[2].z=posed[3].z=static_cast<float>(frame)*.05f;
        parameters_hook(instance,source);solve_hook(instance,1.0f/60,1.0f/60);
    }
    CHECK(customSteps==60&&bindFailures==0&&solveCalls==0);
    CHECK(!std::memcmp(history,posed,sizeof(posed)));
    CHECK(current[0].y==150&&current[0].w==0&&current[2].w==1&&previous[2].w==1);
    CHECK(std::abs(current[2].z-posed[2].z)>.0001f);
    Point paused[4];std::memcpy(paused,current,sizeof(current));
    solve_hook(instance,0,1.0f/60);CHECK(!std::memcmp(current,paused,sizeof(paused)));
    InterlockedExchange(&mode,0);solve_hook(instance,1.0f/60,1.0f/60);CHECK(solveCalls==1);
    InterlockedExchange(&mode,1);solve_hook(instance,1.0f/60,1.0f/60);CHECK(customResets==2&&solveCalls==1);
    auto* hairSource=reinterpret_cast<Parameters*>(hairOwner+0x10);*hairSource=baseline;
    parameters_hook(instance,hairSource);solve_hook(instance,1.0f/60,1.0f/60);CHECK(solveCalls==2);
    char shortsName[64]="shorts";link(owner,0x88,shortsName);
    NativeCapsule capsule{};capsule.fields[1]=130;capsule.fields[3]=7;capsule.fields[5]=1;capsule.fields[7]=5;
    ColliderSet bodySet{1,4,reinterpret_cast<uintptr_t>(&capsule)};link(instance,0x40,&bodySet);
    parameters_hook(instance,source);solve_hook(instance,1.0f/60,1.0f/60);
    CHECK(bodySolves==1&&bodyContacts+edgeContacts>0&&bodyReadFailures==0&&solveCalls==2);
    CHECK(current[2].w==1&&previous[2].w==1);
    link(owner,0x88,jerseyName);
    // Exercise arm volume reading through the real DLL callback, rather than
    // only passing a capsule directly to the standalone particle solver.
    for(auto& p:bind){p.x+=30;p.y-=12;}
    std::memcpy(current,bind,sizeof(bind));std::memcpy(previous,bind,sizeof(bind));std::memcpy(posed,bind,sizeof(bind));
    capsule.fields[0]=30;capsule.fields[1]=118;capsule.fields[3]=4;
    capsule.fields[4]=1;capsule.fields[5]=0;capsule.fields[7]=5;
    parameters_hook(instance,source);solve_hook(instance,1.0f/60,1.0f/60);
    CHECK(armSolves==1&&armContacts+armEdgeContacts>0&&bodySolves==1&&solveCalls==2);
    CHECK(current[0].w==0&&current[2].w==1);
    parameters_hook(instance,source);currentSet.capacity=0;
    std::memcpy(paused,current,sizeof(current));solve_hook(instance,1.0f/60,1.0f/60);
    CHECK(solveCalls==3&&bindFailures==1&&!std::memcmp(current,paused,sizeof(paused)));
    InterlockedExchange(&stopping,1);parameters_hook(instance,source);solve_hook(instance,1.0f/60,1.0f/60);
    CHECK(solveCalls==4&&!std::memcmp(source,&baseline,sizeof(baseline)));
    std::puts("DLL callbacks: particle output, native fallback, hair exclusion, pause, F6 comparison, recycled identity and stop passed");
    return 0;
}
