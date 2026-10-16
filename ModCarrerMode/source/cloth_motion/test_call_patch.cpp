#include "call_patch.h"
#include <cstdio>
using namespace cloth_motion;
#define CHECK(condition) do { if(!(condition)){std::fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#condition);return 1;} } while(false)
int main() {
    auto* code=static_cast<unsigned char*>(VirtualAlloc(nullptr,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE));
    CHECK(code);
    const unsigned char caller[]={0x48,0x83,0xec,0x28,0xe8,0,0,0,0,0x48,0x83,0xc4,0x28,0xc3};
    CallPatch patches[3]{};
    for(size_t i=0;i<3;++i) {
        const size_t offset=i*32;
        std::memcpy(code+offset,caller,sizeof(caller));
        patches[i].address=reinterpret_cast<uintptr_t>(code+offset+4);
        // Original and replacement code stubs exercise the actual E8 bridge.
        for(size_t n=0;n<2;++n) {
            auto* stub=code+128+i*16+n*64;stub[0]=0xb8;
            const uint32_t value=static_cast<uint32_t>((n?33:11)+i*11);
            std::memcpy(stub+1,&value,4);stub[5]=0xc3;
        }
        CallPatch initial=patches[i];
        CHECK(make_call(initial,reinterpret_cast<uintptr_t>(code+128+i*16)));
        std::memcpy(code+offset+4,initial.applied,5);
        std::memcpy(patches[i].expected,initial.applied,5);
        CHECK(make_call(patches[i],reinterpret_cast<uintptr_t>(code+192+i*16)));
    }
    DWORD old=0;CHECK(VirtualProtect(code,4096,PAGE_EXECUTE_READ,&old));
    FlushInstructionCache(GetCurrentProcess(),code,4096);
    using Function=int(*)();const auto first=reinterpret_cast<Function>(code),second=reinterpret_cast<Function>(code+32);
    const auto third=reinterpret_cast<Function>(code+64);
    CHECK(first()==11&&second()==22&&third()==33);
    CallPatch bad[3]={patches[0],patches[1],patches[2]};bad[2].expected[1]^=1;
    CHECK(!install_calls(bad,3));
    CHECK(first()==11&&second()==22&&third()==33); // Refuse all three if any signature differs.
    CHECK(install_calls(patches,3));
    CHECK(first()==33&&second()==44&&third()==55);
    MEMORY_BASIC_INFORMATION memory{};CHECK(VirtualQuery(code,&memory,sizeof(memory))==sizeof(memory));
    CHECK(memory.Protect==PAGE_EXECUTE_READ);
    CallPatch outOfRange{};outOfRange.address=reinterpret_cast<uintptr_t>(code);
    CHECK(!make_call(outOfRange,outOfRange.address+0x90000000ull));
    CHECK(VirtualFree(code,0,MEM_RELEASE));
    std::puts("native call bridge: executable calls, atomic signature refusal, same-page protection restoration passed");
    return 0;
}
