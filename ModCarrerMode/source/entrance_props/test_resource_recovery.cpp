// Exercise the production resource/retirement function. All native addresses
// below belong to this test's private allocation; no FIFA process is opened.
#include "entrance_props.cpp"
#include <cassert>

int main(){
    auto fake=(unsigned char*)VirtualAlloc(nullptr,0x4400000,MEM_RESERVE,PAGE_NOACCESS);
    assert(fake&&VirtualAlloc(fake+0x43b4000,4096,MEM_COMMIT,PAGE_EXECUTE_READWRITE));
    image=(uintptr_t)fake;
    // Native-like accessors and callbacks use prototype->state at +0x10.
    const unsigned char initialized[]={0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x4a,0xc3};
    const unsigned char loaded[]={0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x48,0xc3};
    const unsigned char lods[]={0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x74,0xc3};
    const unsigned char initialize[]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x4a,0x01,0xc3};
    const unsigned char load[]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xff,0x40,0x70,0xc3};
    const unsigned char notify[]={0x48,0x8b,0x41,0x10,0xc6,0x40,0x48,0x01,0xc3};
    std::memcpy(fake+0x43b4500,initialized,sizeof(initialized));
    std::memcpy(fake+0x43b4520,loaded,sizeof(loaded));
    std::memcpy(fake+0x43b43e0,lods,sizeof(lods));
    std::memcpy(fake+0x43b4640,initialize,sizeof(initialize));
    std::memcpy(fake+0x43b4530,load,sizeof(load));
    std::memcpy(fake+0x43b47c0,notify,sizeof(notify));
    assert(FlushInstructionCache(GetCurrentProcess(),fake+0x43b4000,4096));
    alignas(16) unsigned char prototype[32]{},state[128]{},vtable[64]{};
    uintptr_t value=(uintptr_t)vtable;std::memcpy(prototype,&value,8);
    value=(uintptr_t)state;std::memcpy(prototype+16,&value,8);
    value=image+0x43b4530;std::memcpy(vtable+0x38,&value,8);
    selectionAvailable=true;validFixture=false;resourceFault=false;
    resourceRequested=false;resourceReadyLogged=false;retireBeforeReload=true;
    resourceFixture=123;atlasFixture=0;state[0x48]=1;state[0x4a]=0;state[0x74]=1;
    const bool recovered=ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false);
#ifdef EXPECT_BASELINE
    assert(!recovered&&retireBeforeReload&&!resourceRequested&&state[0x4a]==0);
    std::puts("BASELINE REPRODUCED: unloaded old actor blocks retirement and the new resource request");
#else
    assert(recovered&&!retireBeforeReload&&resourceRequested&&state[0x4a]==1&&state[0x70]==1);
    assert(resourceFixture==0&&atlasFixture==0);
    assert(ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(state[0x70]==1); // No repeated load after readiness.

    // The engine unloads the same prototype between fixtures, retaining loaded=1.
    state[0x4a]=0;state[0x48]=1;atlasFixture=456;
    assert(ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(state[0x70]==2&&atlasFixture==0&&!retireBeforeReload);

    // A retry cleared the request boolean, but an old initialized actor still
    // needs one hidden submission. Do not block it or reload its model first.
    retireBeforeReload=true;resourceRequested=false;modelCycle=SceneResourceCycle{};
    assert(ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(retireBeforeReload&&state[0x70]==2);

    // A slow pending load is allowed to finish instead of restarting per frame.
    retireBeforeReload=false;resourceRequested=resourceReadyLogged=false;
    modelCycle=SceneResourceCycle{};state[0x4a]=state[0x48]=state[0x74]=0;
    assert(!ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    const unsigned loads=state[0x70];
    for(unsigned i=0;i<120;++i)
        assert(!ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(state[0x70]==loads);state[0x74]=1;
    assert(ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));

    // Loss of the loaded flag is a resource boundary even when the prototype
    // remains initialized. With fixture callbacks disabled in this fixture,
    // native completion restores the loaded flag without another load call.
    state[0x48]=0;
    assert(ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(resourceRequested&&state[0x48]==1&&state[0x70]==loads);

    // Removing the selection must never load a new model to clear old state.
    selectionAvailable=false;retireBeforeReload=true;state[0x4a]=0;
    const unsigned before=state[0x70];
    assert(!ready_prototype((uintptr_t)prototype,resourceRequested,resourceReadyLogged,false));
    assert(!retireBeforeReload&&state[0x70]==before);
    std::puts("PASS actual entrance loader: unloaded retirement released, same-pointer resource cycles recovered, slow load not restarted, initialized old actor retired, disabled selection preserved");
#endif
    assert(VirtualFree(fake,0,MEM_RELEASE));
}
