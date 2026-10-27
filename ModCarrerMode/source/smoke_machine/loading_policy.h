#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>
inline bool machine_guard_matches(const unsigned char* found,const unsigned char* expected,std::size_t length){
    return found && expected && length>0 && length<=16 && !std::memcmp(found,expected,length);
}
