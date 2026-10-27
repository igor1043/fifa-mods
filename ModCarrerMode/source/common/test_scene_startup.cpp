#define WIN32_LEAN_AND_MEAN
#include "scene_startup.h"
#include <cassert>
#include <cstdio>

int main(){
    SceneStartupRecovery startup;
    assert(!startup.poll(0,true,false,false)); // Loading/menu is not the stadium.
    assert(!startup.poll(100,true,true,false));
    assert(!startup.poll(599,true,true,false));
    assert(startup.poll(600,true,true,false));
    assert(startup.attempts==1&&!startup.confirm(false));
    assert(!startup.poll(1599,true,true,false));
    assert(startup.poll(1600,true,true,false));
    assert(startup.confirm(true));
    for(uint64_t now=1601;now<20000;now+=16)assert(!startup.poll(now,true,true,false));
    // A paused panorama and a transient failed read cannot rearm a success.
    assert(!startup.poll(20000,true,false,true));
    assert(!startup.poll(20001,false,false,false));
    assert(!startup.poll(20002,true,true,false));
    assert(!startup.poll(20003,true,false,false));
    assert(!startup.poll(21000,true,true,false)); // Genuine restart/new match.
    assert(startup.poll(21500,true,true,false));
    assert(startup.poll(22500,true,true,false));
    assert(startup.poll(24500,true,true,false));
    assert(!startup.poll(26500,true,true,false));
    assert(!startup.poll(27000,true,true,false));
    assert(!startup.pending&&!startup.confirm(true)&&startup.attempts==3&&startup.expired);
    // A machine that stalls past the deadline must not receive a late reload.
    SceneStartupRecovery stalled;
    assert(!stalled.poll(100,true,true,false));
    assert(!stalled.poll(6100,true,true,false));
    assert(!stalled.poll(6500,true,true,false));
    SceneStartupRecovery paused;
    assert(!paused.poll(10,true,true,false));
    assert(!paused.poll(510,true,false,true));
    assert(paused.poll(1010,true,true,false));
    assert(!paused.poll(1020,true,false,false)); // Kickoff closes immediately.
    assert(!paused.pending);

    unsigned char records[4][0x50],before[4][0x50];
    std::memset(records,0x36,sizeof(records));std::memcpy(before,records,sizeof(records));
    scene_startup_rebind(&records[1][0],2);
    for(unsigned i=0;i<4;++i)for(unsigned j=0;j<0x50;++j){
        const bool owned=i==1||i==2;
        const unsigned char expected=owned&&(j==0x40||j==0x41)?0xff:owned&&j==0x45?0:before[i][j];
        assert(records[i][j]==expected);
    }

    // Exercise the production native sampler using only private committed pages.
    auto fake=(unsigned char*)VirtualAlloc(nullptr,0x4000000,MEM_RESERVE,PAGE_NOACCESS);assert(fake);
    const size_t offsets[]={0x3517c10,56299464,58757168};
    for(size_t offset:offsets)assert(VirtualAlloc(fake+(offset&~size_t(4095)),4096,MEM_COMMIT,PAGE_READWRITE));
    unsigned char state[0x40]{},stats[5504]{},ui[5][768]{};
    const uintptr_t image=(uintptr_t)fake,statePtr=(uintptr_t)state,statsPtr=(uintptr_t)stats;
    const uintptr_t expectedVtable=image+0x20ff390,uiPtr=(uintptr_t)ui[0];
    std::memcpy(fake+0x3517c10,&statePtr,8);std::memcpy(state,&expectedVtable,8);
    std::memcpy(fake+56299464,&statsPtr,8);std::memcpy(fake+58757168,&uiPtr,8);
    const unsigned uiOffsets[]={232,192,136,472};
    for(unsigned i=0;i<4;++i){const uintptr_t next=(uintptr_t)ui[i+1];std::memcpy(ui[i]+uiOffsets[i],&next,8);}
    auto page=(char*)ui[4];strcpy_s(page,768,"game/screens/misc/stadiumpan");
    state[8]=1;int sports=2,clock=0;
    std::memcpy(state+0x3c,&sports,4);std::memcpy(stats+5500,&clock,4);
    auto sample=scene_startup_sample(image);assert(sample.known&&sample.opening&&!sample.suspended);
    SceneStartupProbe probe;
    assert(!probe.poll(image,0));assert(probe.poll(image,500));
    assert(!probe.poll(image,501));assert(probe.confirm(true));
    probe.recovery.expired=true;assert(probe.take_timeout());assert(!probe.take_timeout());
    strcpy_s(page,768,"game/screens/pause/pause");
    sample=scene_startup_sample(image);assert(sample.known&&sample.suspended);
    strcpy_s(page,768,"game/screens/tv/broadcast");state[0x39]=1;
    sample=scene_startup_sample(image);assert(sample.suspended);
    state[0x39]=0;clock=1;std::memcpy(stats+5500,&clock,4);
    sample=scene_startup_sample(image);assert(sample.known&&!sample.opening);
    clock=0;std::memcpy(stats+5500,&clock,4);sports=15;std::memcpy(state+0x3c,&sports,4);
    sample=scene_startup_sample(image);assert(sample.known&&!sample.opening);
    sports=2;std::memcpy(state+0x3c,&sports,4);strcpy_s(page,768,"game/screens/playnow/sideselect");
    sample=scene_startup_sample(image);assert(sample.known&&!sample.opening);
    const uintptr_t invalid=1;std::memcpy(fake+58757168,&invalid,8);
    assert(!scene_startup_sample(image).known);
    assert(VirtualFree(fake,0,MEM_RELEASE));
    std::puts("Startup recovery: bounded attempts, slow load, completion, restart, pause/replay/gameplay guards, private bindings and native sampler: PASS");
}
