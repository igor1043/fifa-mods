#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
inline bool machine_guard_matches(const unsigned char* found,const unsigned char* expected,std::size_t length){
    return found && expected && length>0 && length<=16 && !std::memcmp(found,expected,length);
}
struct MachineLuaLifecycle {
    uintptr_t vm=0;
    bool ready=false;
    uint64_t nextCheck=0,nextAttempt=0;
    bool sample(uint64_t now,uintptr_t current){
        if(now<nextCheck)return false;
        nextCheck=now+500;
        if(vm!=current){vm=current;ready=false;nextAttempt=0;}
        return true;
    }
    bool should_activate(uint64_t now,bool markerReady){
        ready=markerReady;
        if(!vm || ready || now<nextAttempt)return false;
        nextAttempt=now+1000;return true;
    }
};
