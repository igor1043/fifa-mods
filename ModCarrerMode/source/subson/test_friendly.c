#include "subson_friendly.h"
#include <stdio.h>
#include <string.h>

typedef uintptr_t (__fastcall *Dispatch)(uintptr_t,unsigned,uintptr_t);
void subson_test_context(uintptr_t,unsigned);
unsigned subson_test_import(uintptr_t,unsigned);
unsigned subson_test_capacity(void);
void subson_test_dispatch(Dispatch);
uintptr_t subson_test_command(uintptr_t,unsigned,uintptr_t);
int subson_test_install(uintptr_t,unsigned);
int subson_test_remove(void);
static unsigned callback_count,callback_command;
static uintptr_t callback_state;
static uintptr_t __fastcall dispatch(uintptr_t state,unsigned command,uintptr_t output)
{
    uintptr_t settings=*(uintptr_t *)(state+0x340U);
    ++callback_count;callback_command=command;callback_state=state;
    *(unsigned *)(settings+0xC10U)=7U;
    *(unsigned *)output=command==0x6EU?7U:0x12345678U;
    return 0x123456789ULL;
}
static unsigned selected;
static unsigned __fastcall request_callback(uintptr_t settings,unsigned native)
{return *(unsigned *)(settings+0xC10U)==native?selected:0xFFFFFFFFU;}
static unsigned __fastcall cap_callback(void){return selected;}

static int thunks(void)
{
    static const unsigned char request[]={
        0x53,0x41,0x55,0x48,0x83,0xEC,0x28,0x49,0x89,0xCD,
        0x41,0x8B,0x9D,0x10,0x0C,0,0,
        0x89,0xD8,0x48,0x83,0xC4,0x28,0x41,0x5D,0x5B,0xC3};
    static const unsigned char capacity[]={
        0x53,0x57,0x41,0x56,0x48,0x83,0xEC,0x20,0x89,0xCF,
        0x44,0x8D,0x77,7,0x89,0xFB,
        0x44,0x89,0xF0,0x48,0x83,0xC4,0x20,0x41,0x5E,0x5F,0x5B,0xC3};
    typedef unsigned (__fastcall *RequestFn)(unsigned char *);
    typedef unsigned (__fastcall *CapacityFn)(unsigned);
    unsigned char *page=VirtualAlloc(NULL,0x1000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    unsigned char settings[0xC18],before[0xC18];
    unsigned native,initial;size_t byte;int32_t delta;DWORD old;RequestFn rf;CapacityFn cf;
    if(!page)return 1;
    memcpy(page,request,sizeof(request));memcpy(page+0x400,capacity,sizeof(capacity));
    if(!subson_emit_import(page+0x100,(uintptr_t)request_callback,(uintptr_t)page+17) ||
       !subson_emit_capacity(page+0x500,(uintptr_t)cap_callback,(uintptr_t)page+0x410))return 2;
    page[10]=0xE9;delta=0x100-15;memcpy(page+11,&delta,4);page[15]=page[16]=0x90;
    page[0x40A]=0xE9;delta=0x500-0x40F;memcpy(page+0x40B,&delta,4);page[0x40F]=0x90;
    if(!VirtualProtect(page,0x1000,PAGE_EXECUTE_READ,&old))return 3;
    FlushInstructionCache(GetCurrentProcess(),page,0x1000);
    rf=(RequestFn)(void *)page;cf=(CapacityFn)(void *)(page+0x400);
    for(selected=7;selected<=12;++selected){
        for(native=0;native<=12;++native){
            memset(settings,0xA5,sizeof(settings));memcpy(settings+0xC10,&native,4);memcpy(before,settings,sizeof(settings));
            if(rf(settings)!=selected)return 4;
            for(byte=0;byte<sizeof(settings);++byte){
                unsigned char want=(byte>=0xC10 && byte<0xC14)?(byte==0xC10?(unsigned char)selected:0):before[byte];
                if(settings[byte]!=want)return 5;
            }
        }
        for(initial=0;initial<6;++initial)if(cf(initial)!=selected+initial)return 6;
    }
    if(!VirtualFree(page,0,MEM_RELEASE))return 7;
    return 0;
}
static int unwind_test(void)
{
    unsigned char data[24];RUNTIME_FUNCTION parent={0x300,0x400,{0x500}};
    unsigned char *page=VirtualAlloc(NULL,0x1000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    RUNTIME_FUNCTION record={0,0x200,{0x300}};
    CONTEXT context;DECLSPEC_ALIGN(16) uint64_t stack[64];
    PVOID handler=NULL;DWORD64 establisher=0;KNONVOLATILE_CONTEXT_POINTERS pointers;
    if(!page)return 10;
    subson_unwind(data,&parent);memcpy(page+0x300,data,24);
    memset(page+0x500,0,4);page[0x500]=1;
    memset(&context,0,sizeof(context));memset(stack,0,sizeof(stack));memset(&pointers,0,sizeof(pointers));
    stack[30]=0x123456789ULL;context.Rsp=(DWORD64)(uintptr_t)&stack[0];
    context.Rip=(DWORD64)(uintptr_t)page+0x80;
    (void)RtlVirtualUnwind(UNW_FLAG_NHANDLER,(DWORD64)(uintptr_t)page,context.Rip,&record,&context,&handler,&establisher,&pointers);
    if(context.Rip!=0x123456789ULL || context.Rsp!=(DWORD64)(uintptr_t)&stack[31])return 11;
    VirtualFree(page,0,MEM_RELEASE);return 0;
}
static int installation(unsigned char *base,uintptr_t state,uintptr_t settings)
{
    static const unsigned char wrapper[]={
        0x53,0x41,0x55,0x48,0x83,0xEC,0x28,0x49,0x89,0xCD,
        0x41,0x8B,0x9D,0x10,0x0C,0,0,
        0x89,0xD8,0x48,0x83,0xC4,0x28,0x41,0x5D,0x5B,0xC3};
    RUNTIME_FUNCTION parents[2]={{0x414EB20,0x414F15F,{0x4000}},{0x415AEB0,0x415AF8B,{0x4100}}};
    typedef unsigned (__fastcall *Fn)(unsigned char *);
    Fn fn;DWORD old;unsigned native=7;
    if(!VirtualAlloc(base+0x4000,0x1000,MEM_COMMIT,PAGE_READWRITE) ||
       !VirtualAlloc(base+0x21A6000,0x1000,MEM_COMMIT,PAGE_READWRITE) ||
       !VirtualAlloc(base+0x414E000,0x2000,MEM_COMMIT,PAGE_READWRITE) ||
       !VirtualAlloc(base+0x415A000,0x1000,MEM_COMMIT,PAGE_READWRITE))return 30;
    memcpy(base+0x4000,"\x19\x2A\x0B\0",4);memcpy(base+0x4100,"\x01\x1A\x0A\0",4);
    memcpy(base+0x414EB83-10,wrapper,sizeof(wrapper));
    memcpy(base+0x415AED7,"\x44\x8D\x77\x07\x89\xFB",6);
    *(uintptr_t *)(base+0x21A66D8)=(uintptr_t)base+0x3D8FD70;
    if(!VirtualProtect(base+0x414E000,0x2000,PAGE_EXECUTE_READ,&old) ||
       !VirtualProtect(base+0x415A000,0x1000,PAGE_EXECUTE_READ,&old) ||
       !VirtualProtect(base+0x21A6000,0x1000,PAGE_READONLY,&old) ||
       !RtlAddFunctionTable(parents,2,(DWORD64)(uintptr_t)base))return 31;
    base[0x4100]=0;
    if(subson_test_install((uintptr_t)base,12) || base[0x414EB83]!=0x41 ||
       *(uintptr_t *)(base+0x21A66D8)!=(uintptr_t)base+0x3D8FD70)return 32;
    base[0x4100]=1;
    if(!subson_test_install((uintptr_t)base,12) || base[0x414EB83]!=0xE9 ||
       base[0x415AED7]!=0xE9 || *(uintptr_t *)(base+0x21A66D8)==(uintptr_t)base+0x3D8FD70)return 33;
    *(uintptr_t *)state=(uintptr_t)base+0x21A66D0;
    *(unsigned *)(settings+0xC10)=native;*(unsigned *)(settings+0xC14)=0xA5A5A5A5;
    fn=(Fn)(void *)(base+0x414EB83-10);
    if(fn((unsigned char *)settings)!=12 || *(unsigned *)(settings+0xC14)!=0xA5A5A5A5)return 34;
    *(uintptr_t *)state=(uintptr_t)base+0x21A5020;*(unsigned *)(settings+0xC10)=7;
    if(fn((unsigned char *)settings)!=7)return 35;
    if(!subson_test_remove() || base[0x414EB83]!=0x41 || base[0x415AEDA]!=7 ||
       *(uintptr_t *)(base+0x21A66D8)!=(uintptr_t)base+0x3D8FD70)return 36;
    if(fn((unsigned char *)settings)!=7 || !RtlDeleteFunctionTable(parents))return 37;
    return 0;
}
int main(void)
{
    unsigned char *base=VirtualAlloc(NULL,0x9525000,MEM_RESERVE,PAGE_NOACCESS);
    unsigned char *objects=VirtualAlloc(NULL,0x6000,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    uintptr_t main,controller,stack,state,settings,other;
    unsigned bench,native,mode,command,output;size_t i;unsigned char before[0xC18];int error;
    if(!base || !objects || !VirtualAlloc(base+0x34EA000,0x1000,MEM_COMMIT,PAGE_READWRITE))return 20;
    main=(uintptr_t)objects;controller=main+0x1000;stack=main+0x2000;
    state=main+0x3000;settings=main+0x4000;other=main+0x5000;
    *(uintptr_t *)(base+0x34EA0E8)=main;*(uintptr_t *)(main+0x68)=controller;
    *(uintptr_t *)controller=stack;*(uintptr_t *)stack=state;*(int32_t *)(stack+0x20)=0;
    *(uintptr_t *)(state+0x340)=settings;*(unsigned *)(state+0x440)=0;
    subson_test_dispatch(dispatch);
    for(bench=7;bench<=12;++bench)for(mode=0;mode<4;++mode){
        const unsigned vtables[]={0x21A66D0,0x21A5020,0x21A4E90,0x123456};
        subson_test_context((uintptr_t)base,bench);*(uintptr_t *)state=(uintptr_t)base+vtables[mode];
        if(subson_test_capacity()!=(mode==0?bench:7))return 21;
        for(native=0;native<16;++native){
            unsigned expected=mode==0 && native>=5 && native<=12?bench:native;
            if(subson_test_import(settings,native)!=expected || subson_test_import(other,native)!=native)return 22;
        }
        for(command=0;command<300;++command){
            uintptr_t result;unsigned want;
            memset((void *)settings,0xA5,0xC18);*(unsigned *)(settings+0xC10)=7;
            memcpy(before,(void *)settings,sizeof(before));callback_count=0;output=0;
            result=subson_test_command(state,command,(uintptr_t)&output);
            want=command==0x6E?(mode==0?bench:7):0x12345678U;
            if(result!=0x123456789ULL || callback_count!=1 || callback_command!=command ||
               callback_state!=state || output!=want || *(unsigned *)(settings+0xC10)!=(mode==0?bench:7))return 23;
            for(i=0;i<sizeof(before);++i)
                if((i<0xC10 || i>=0xC14) && ((unsigned char *)settings)[i]!=before[i])return 24;
        }
    }
    *(int32_t *)(stack+0x20)=-1;if(subson_test_capacity()!=7)return 25;
    *(int32_t *)(stack+0x20)=4;if(subson_test_capacity()!=7)return 26;
    error=thunks();if(error){printf("thunk failure %d\n",error);return error;}
    error=unwind_test();if(error){printf("unwind failure %d\n",error);return error;}
    *(int32_t *)(stack+0x20)=0;
    error=installation(base,state,settings);if(error){printf("installation failure %d\n",error);return error;}
    VirtualFree(objects,0,MEM_RELEASE);VirtualFree(base,0,MEM_RELEASE);
    puts("PASS: 7200 native command cases; 768 import scope cases; 78 executable import thunks; 36 executable capacity thunks; chained unwind; guarded install/remove; all non-C10 bytes including C14 preserved");
    return 0;
}
