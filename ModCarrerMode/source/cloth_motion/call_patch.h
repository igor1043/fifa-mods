#pragma once
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <tlhelp32.h>
#include <cstdint>
#include <cstring>

namespace cloth_motion {
struct CallPatch {
    uintptr_t address=0;
    unsigned char expected[5]{};
    unsigned char applied[5]{};
};
inline bool make_call(CallPatch& patch,uintptr_t destination) {
    const int64_t delta=static_cast<int64_t>(destination)-static_cast<int64_t>(patch.address+5);
    if(delta<INT32_MIN||delta>INT32_MAX)return false;
    patch.applied[0]=0xe8;
    const int32_t offset=static_cast<int32_t>(delta);
    std::memcpy(patch.applied+1,&offset,4);
    return true;
}
inline void* allocate_near(uintptr_t origin) {
    SYSTEM_INFO info{};GetSystemInfo(&info);
    const uintptr_t step=info.dwAllocationGranularity,aligned=origin&~(step-1);
    for(uintptr_t distance=step;distance<0x70000000;distance+=step) {
        for(unsigned side=0;side<2;++side) {
            if(side&&aligned<distance+0x10000)continue;
            void* allocation=VirtualAlloc(reinterpret_cast<void*>(side?aligned-distance:aligned+distance),4096,
                                         MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
            if(allocation)return allocation;
        }
    }
    return nullptr;
}
inline bool install_calls(CallPatch* patches,size_t count) {
    if(!count||count>8)return false;
    HANDLE threads[512]{};size_t handles=0,suspended=0;
    HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);
    if(snapshot==INVALID_HANDLE_VALUE)return false;
    THREADENTRY32 item{};item.dwSize=sizeof(item);bool okay=true;
    for(BOOL found=Thread32First(snapshot,&item);found;found=Thread32Next(snapshot,&item)) {
        if(item.th32OwnerProcessID!=GetCurrentProcessId()||item.th32ThreadID==GetCurrentThreadId())continue;
        if(handles==512){okay=false;break;}
        HANDLE thread=OpenThread(THREAD_SUSPEND_RESUME|THREAD_GET_CONTEXT|THREAD_QUERY_LIMITED_INFORMATION,FALSE,item.th32ThreadID);
        if(!thread){if(GetLastError()==ERROR_INVALID_PARAMETER)continue;okay=false;break;}
        threads[handles++]=thread;
    }
    CloseHandle(snapshot);
    DWORD protections[8]{};size_t writable=0;
    for(;okay&&writable<count;++writable) {
        if(!VirtualProtect(reinterpret_cast<void*>(patches[writable].address),5,PAGE_EXECUTE_READWRITE,&protections[writable])) {
            okay=false;break;
        }
    }
    if(okay)for(;suspended<handles;++suspended)if(SuspendThread(threads[suspended])==DWORD(-1)){okay=false;break;}
    if(okay)for(size_t i=0;i<suspended&&okay;++i) {
        CONTEXT context{};context.ContextFlags=CONTEXT_CONTROL;
        if(!GetThreadContext(threads[i],&context)){okay=false;break;}
        for(size_t j=0;j<count;++j)if(context.Rip>=patches[j].address&&context.Rip<patches[j].address+5)okay=false;
    }
    if(okay)for(size_t i=0;i<count;++i)if(std::memcmp(reinterpret_cast<void*>(patches[i].address),patches[i].expected,5))okay=false;
    if(okay)for(size_t i=0;i<count;++i) {
        std::memcpy(reinterpret_cast<void*>(patches[i].address),patches[i].applied,5);
        FlushInstructionCache(GetCurrentProcess(),reinterpret_cast<void*>(patches[i].address),5);
    }
    while(suspended)ResumeThread(threads[--suspended]);
    // Both sites can occupy the same page. Restore protections in reverse.
    while(writable) { --writable;DWORD ignored=0;
        VirtualProtect(reinterpret_cast<void*>(patches[writable].address),5,protections[writable],&ignored);
    }
    for(size_t i=0;i<handles;++i)CloseHandle(threads[i]);
    return okay;
}
}
