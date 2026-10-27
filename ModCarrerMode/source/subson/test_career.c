#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>
int main(void)
{
    /* Same R14D eligible count / RDX rules / ECX output as the captured FCE site. */
    static const unsigned char wrapper[]={0x41,0x56,0x48,0x83,0xEC,0x28,0x41,0x89,0xD6,0x48,0x89,0xCA,
        0x8B,0x8A,0x94,0,0,0,0x89,0xC8,0x48,0x83,0xC4,0x28,0x41,0x5E,0xC3};
    typedef unsigned (__fastcall *Fn)(unsigned char*,unsigned);
    unsigned char *page=VirtualAlloc(NULL,4096,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);
    unsigned char rules[0x100],original[0x100];DWORD old;int32_t relative;unsigned eligible,native;
    if(!page)return 1;
    memcpy(page,wrapper,sizeof(wrapper));
    if(!subson_emit_career(page+0x100,(uintptr_t)page+18))return 2;
    page[12]=0xE9;relative=0x100-17;memcpy(page+13,&relative,4);page[17]=0x90;
    if(!VirtualProtect(page,4096,PAGE_EXECUTE_READ,&old))return 3;
    FlushInstructionCache(GetCurrentProcess(),page,4096);
    for(native=0;native<=15;++native)for(eligible=0;eligible<=101;++eligible){
        unsigned want=native;
        memset(rules,0xA5,sizeof(rules));memcpy(rules+0x94,&native,4);memcpy(original,rules,sizeof(rules));
        if(native<=12 && eligible>=11 && eligible<=100 && want>eligible-11)want=eligible-11;
        if(((Fn)(void*)page)(rules,eligible)!=want || memcmp(rules,original,sizeof(rules)))return 4;
    }
    VirtualFree(page,0,MEM_RELEASE);
    puts("PASS: native FCE bench request, 1632 cases; 11->0, 12->1, 22->11, 23+->12; competition rules unchanged; <11 minimum guard preserved");return 0;
}
