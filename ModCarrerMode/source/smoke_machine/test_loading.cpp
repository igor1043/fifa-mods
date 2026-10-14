#include "loading_policy.h"
#include <cassert>
#include <cstdio>
int main(){
    const unsigned char code[16]={0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x4a,0xc3};
    unsigned char loaded[16];std::memcpy(loaded,code,16);
    for(int i=9;i<16;++i)loaded[i]=0x71;
    assert(machine_guard_matches(loaded,code,9));
    loaded[7]=0x49;assert(!machine_guard_matches(loaded,code,9));
    MachineLuaLifecycle lifecycle;
    assert(lifecycle.sample(1000,0x10000));
    assert(lifecycle.should_activate(1000,false));
    assert(!lifecycle.should_activate(1100,false));
    assert(lifecycle.sample(2000,0x10000));
    assert(lifecycle.should_activate(2000,false));
    assert(!lifecycle.should_activate(2001,true)&&lifecycle.ready);
    assert(lifecycle.sample(3000,0x20000));
    assert(!lifecycle.ready&&lifecycle.should_activate(3000,false));
    assert(lifecycle.sample(4000,0));
    assert(!lifecycle.ready&&!lifecycle.should_activate(4000,false));
    assert(lifecycle.sample(5000,0x10000)&&lifecycle.should_activate(5000,false));
    std::puts("Executed-byte guards tolerate padding only; delayed Lua and replacement VMs rearm bounded activation: PASS");
}
