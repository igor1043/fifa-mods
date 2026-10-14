#include "loading_policy.h"
#include "../common/scene_lua.h"
#include <cassert>
#include <cstdio>
int main(){
    const unsigned char code[16]={0x48,0x8b,0x41,0x10,0x0f,0xb6,0x40,0x4a,0xc3};
    unsigned char loaded[16];std::memcpy(loaded,code,16);
    for(int i=9;i<16;++i)loaded[i]=0x71;
    assert(machine_guard_matches(loaded,code,9));
    loaded[7]=0x49;assert(!machine_guard_matches(loaded,code,9));
    SceneLuaLifecycle lifecycle;
    assert(lifecycle.sample(1000,{0x10000,0x30000}));
    assert(lifecycle.should_activate(1000,false));
    assert(!lifecycle.should_activate(1100,false));
    assert(lifecycle.sample(2000,{0x10000,0x30000}));
    assert(lifecycle.should_activate(2000,false));
    assert(!lifecycle.should_activate(2001,true)&&lifecycle.ready);
    assert(lifecycle.sample(3000,{0x20000,0x30000}));
    assert(!lifecycle.ready&&lifecycle.should_activate(3000,false));
    assert(lifecycle.sample(4000,{}));
    assert(!lifecycle.ready&&!lifecycle.should_activate(4000,false));
    assert(lifecycle.sample(5000,{0x10000,0x30000})&&lifecycle.should_activate(5000,false));
    assert(!lifecycle.should_activate(5001,true)&&lifecycle.ready);
    assert(lifecycle.sample(5500,{0x10000,0x40000}));
    assert(!lifecycle.ready&&lifecycle.should_activate(5500,false));
    assert(!lifecycle.should_activate(5501,true)&&lifecycle.ready);
    assert(lifecycle.sample(6000,{0x10000,0x40000}));
    assert(!lifecycle.should_activate(6000,false)&&!lifecycle.ready);
    assert(lifecycle.sample(6500,{0x10000,0x40000})&&lifecycle.should_activate(6500,false));
    assert(!lifecycle.sample(6501,{0x10000,0x40000}));
    std::puts("Delayed Lua, VM/globals replacement, lost markers and bounded recovery: PASS");
}
