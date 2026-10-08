#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "bench_native12_core.h"
extern unsigned int test_native_role_bridge(uint32_t *roles,unsigned int count,void *instructions);
int main(void)
{
    uint32_t source[23],target[23];
    unsigned char *instructions=(unsigned char *)VirtualAlloc(NULL,0x1000U,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    unsigned int index;
    DWORD previous;
    if (!instructions || bench_native12_targets[0]!=12 || bench_native12_targets[1]!=12) return 1;
    for (index=0;index<23;++index) source[index]=index<11 ? index : 28U;
    memcpy(target,source,sizeof(target));
    memcpy(instructions,bench_native12_patches[1].before,20U);instructions[20]=0xC3;
    if (!VirtualProtect(instructions,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),instructions,21U)) return 2;
    if (test_native_role_bridge(target,23,instructions)!=12U) return 3;
    for (index=0;index<23;++index) {
        uint32_t expected=index<11 ? index : index<18 ? 28U : 29U;
        if (target[index]!=expected || source[index]!=(index<11 ? index : 28U)) return 4;
    }
    /* Reproduce the former expansion: all twelve become scene reserves. */
    if (!VirtualProtect(instructions,0x1000U,PAGE_READWRITE,&previous)) return 5;
    instructions[10]=12;
    if (!VirtualProtect(instructions,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),instructions,21U)) return 6;
    memcpy(target,source,sizeof(target));
    if (test_native_role_bridge(target,23,instructions)!=12U || memcmp(target,source,sizeof(source))) return 7;
    VirtualFree(instructions,0,MEM_RELEASE);
    puts("Exact native instructions: baseline 7 and restored v3 12/12 verified; extra actors remain actual reserves. Substitution activation still needs gameplay validation.");
    return 0;
}
