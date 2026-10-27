#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>
size_t subson_emit_match_gate(unsigned char*,uintptr_t);
int subson_gate_test_install(uintptr_t,SIZE_T);
int subson_gate_test_remove(uintptr_t);
static unsigned __fastcall native_check(const unsigned *eligible,unsigned team,unsigned subs,unsigned extra)
{
    if(team!=130347U||extra!=0x12345678U)return 99;
    return *eligible<11U+subs?4U:0U;
}
static int tail_call(void)
{
    typedef unsigned (__fastcall *Check)(const unsigned*,unsigned,unsigned,unsigned);
    unsigned char *page=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    DWORD old;unsigned eligible,requested;Check gate;
    if(!page||subson_emit_match_gate(page,(uintptr_t)native_check)!=20)return 1;
    if(!VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old))return 2;
    FlushInstructionCache(GetCurrentProcess(),page,4096);gate=(Check)(void*)page;
    for(eligible=0;eligible<=101;++eligible)for(requested=0;requested<=15;++requested){
        unsigned original=eligible;
        if(gate(&eligible,130347,requested,0x12345678)!=(eligible<11?4U:0U)||eligible!=original)return 3;
    }
    VirtualFree(page,0,MEM_RELEASE);return 0;
}
static int flags_arguments_and_stack(void)
{
    /* Recorder observes flags and register arguments on entry, before any
     * operation which changes them. A direct CALL and a redirected CALL must
     * have identical stack layout and arguments except numSubs in R8D.
     */
    static const unsigned char recorder[]={0x9C,0x58,0x48,0x89,0x01,0x48,0x89,0x51,8,
        0x4C,0x89,0x41,16,0x4C,0x89,0x49,24,0x48,0x89,0xE0,0x48,0x89,0x41,32,0xC3};
    static const unsigned char wrapper[]={0x48,0x83,0xEC,0x28,0xF9,0xE8,0,0,0,0,
        0x48,0x83,0xC4,0x28,0xC3};
    typedef void (__fastcall *Fn)(uint64_t*,uint64_t,uint64_t,uint64_t);
    unsigned char *page=VirtualAlloc(NULL,4096,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    uint64_t observed[5],native[5];DWORD old;int32_t offset;
    if(!page)return 10;
    memcpy(page,wrapper,sizeof(wrapper));memcpy(page+0x100,recorder,sizeof(recorder));
    subson_emit_match_gate(page+0x200,(uintptr_t)page+0x100);
    offset=0x100-10;memcpy(page+6,&offset,4);
    if(!VirtualProtect(page,4096,PAGE_EXECUTE_READWRITE,&old))return 11;
    FlushInstructionCache(GetCurrentProcess(),page,4096);
    ((Fn)(void*)page)(native,130347,12,0x1234567812345678ULL);
    offset=0x200-10;memcpy(page+6,&offset,4);FlushInstructionCache(GetCurrentProcess(),page,4096);
    ((Fn)(void*)page)(observed,130347,12,0x1234567812345678ULL);
    if(!(observed[0]&1)||observed[0]!=native[0]||observed[1]!=native[1]||observed[2]!=0||
       observed[3]!=native[3]||observed[4]!=native[4])return 12;
    VirtualFree(page,0,MEM_RELEASE);return 0;
}
static int installation(void)
{
    static const unsigned rvas[]={0x59105B6,0x59105CC,0x59586BD};
    static const unsigned char original[3][5]={{0xE8,0xD5,0x43,0x33,0},{0xE8,0xBF,0x43,0x33,0},{0xE8,0xCE,0xC2,0x2E,0}};
    RUNTIME_FUNCTION parents[2]={{0x5910500,0x5910673,{0x4000}},{0x5957DE0,0x595876B,{0x4100}}};
    unsigned char *image=VirtualAlloc(NULL,0x9525000,MEM_RESERVE,PAGE_NOACCESS);
    unsigned i;DWORD old;
    if(!image||!VirtualAlloc(image+0x4000,0x1000,MEM_COMMIT,PAGE_READWRITE)||
       !VirtualAlloc(image+0x5910000,0x1000,MEM_COMMIT,PAGE_READWRITE)||
       !VirtualAlloc(image+0x5958000,0x1000,MEM_COMMIT,PAGE_READWRITE)||
       !VirtualAlloc(image+0x5C44000,0x1000,MEM_COMMIT,PAGE_READWRITE))return 20;
    memcpy(image+0x4000,"\x01\x14\x0A\0",4);memcpy(image+0x4100,"\x19\x2A\x0B\0",4);
    memcpy(image+0x5910569,"\x8B\x98\x94\0\0\0",6);memcpy(image+0x5C449AC,"\x44\x89\xC5",3);
    for(i=0;i<3;++i)memcpy(image+rvas[i],original[i],5);
    if(!RtlAddFunctionTable(parents,2,(uintptr_t)image))return 21;
    image[0x59586BD]=0x90;
    if(subson_gate_test_install((uintptr_t)image,0x9525000)||memcmp(image+0x59105B6,original[0],5))return 22;
    image[0x59586BD]=0xE8;
    image[0x591056C]=0x90; /* Reject the retired partial-instruction patch. */
    if(subson_gate_test_install((uintptr_t)image,0x9525000))return 23;
    image[0x591056C]=0;
    if(!VirtualProtect(image+0x5910000,4096,PAGE_EXECUTE_READ,&old)||
       !VirtualProtect(image+0x5958000,4096,PAGE_EXECUTE_READ,&old))return 24;
    if(!subson_gate_test_install((uintptr_t)image,0x9525000))return 25;
    for(i=0;i<3;++i){int32_t distance;uintptr_t target;unsigned char code[20],expected[20];
        if(image[rvas[i]]!=0xE8)return 26;
        memcpy(&distance,image+rvas[i]+1,4);target=(uintptr_t)((int64_t)(uintptr_t)(image+rvas[i]+5)+distance);
        memcpy(code,(void*)target,20);subson_emit_match_gate(expected,(uintptr_t)image+0x5C44990);
        if(memcmp(code,expected,20))return 27;
    }
    if(memcmp(image+0x5910569,"\x8B\x98\x94\0\0\0",6)||memcmp(image+0x5C449AC,"\x44\x89\xC5",3))return 28;
    if(!subson_gate_test_remove((uintptr_t)image))return 29;
    for(i=0;i<3;++i)if(memcmp(image+rvas[i],original[i],5))return 30;
    RtlDeleteFunctionTable(parents);VirtualFree(image,0,MEM_RELEASE);return 0;
}
int main(void)
{
    int result=tail_call();if(!result)result=flags_arguments_and_stack();if(!result)result=installation();
    if(result){printf("FAIL match gate %d\n",result);return result;}
    puts("PASS: 1632 validation cases; 11 starters and optional reserves; flags/register arguments/stack preserved; three exact CALLs; conflict rejection and rollback; original shared checker and six-byte load unchanged");return 0;
}
