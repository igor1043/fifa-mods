#pragma once
#include <windows.h>
#include <cstdint>
#include <cstring>
namespace extra {
// Scene pointers can become sentinels or be unmapped during teardown. A failed
// probe must not raise a first-chance AV inside FIFA's exception handlers.
inline bool sceneRead(uintptr_t at,void* out,size_t size){
 if(!out||!size||at<0x10000||at>UINTPTR_MAX-size||
    at==UINT32_MAX||at==UINTPTR_MAX)return false;
 SIZE_T copied=0;
 if(ReadProcessMemory(GetCurrentProcess(),reinterpret_cast<const void*>(at),out,size,&copied)&&copied==size)return true;
 std::memset(out,0,size);return false;
}
}
