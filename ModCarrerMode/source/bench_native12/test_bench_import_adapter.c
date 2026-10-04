#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include "bench_import_adapter.h"

typedef unsigned int (WINAPI *RequestFn)(unsigned char *settings);

static int code_and_data_test(void)
{
    static const unsigned char wrapper[] = {
        0x53,0x41,0x55,0x49,0x89,0xCD,
        0x41,0x8B,0x9D,0x10,0x0C,0x00,0x00,
        0x89,0xD8,0x41,0x5D,0x5B,0xC3
    };
    static const uint32_t inputs[]={0U,3U,7U,12U,UINT32_MAX};
    unsigned char *page=(unsigned char *)VirtualAlloc(NULL,0x1000U,
        MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    unsigned char settings[0xC18], before[0xC18], code[BENCH_IMPORT_CODE_SIZE];
    unsigned char site_patch[BENCH_IMPORT_SITE_SIZE];
    DWORD previous;
    RequestFn function;
    size_t index, byte;
    if (!page) return 1;
    memcpy(page,wrapper,sizeof(wrapper));
    if (!bench_import_emit((uintptr_t)page+6U,(uintptr_t)page+0x80U,code,site_patch)) return 2;
    memcpy(page+0x80,code,sizeof(code));memcpy(page+6,site_patch,sizeof(site_patch));
    if (!VirtualProtect(page,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),page,0x100U)) return 3;
    memcpy(&function,&page,sizeof(function));
    for (index=0;index<sizeof(inputs)/sizeof(inputs[0]);++index) {
        uint32_t policy=3U;
        memset(settings,0xA5,sizeof(settings));
        memcpy(settings+0xC10,&inputs[index],4U);memcpy(settings+0xC14,&policy,4U);
        memcpy(before,settings,sizeof(settings));
        if (function(settings)!=12U) return 4;
        for (byte=0;byte<sizeof(settings);++byte) {
            const unsigned char expected=byte>=0xC10U && byte<0xC14U ?
                (byte==0xC10U ? 12U : 0U) : before[byte];
            if (settings[byte]!=expected) return 5;
        }
    }
    if (!VirtualFree(page,0,MEM_RELEASE)) return 6;
    if (bench_import_emit((uintptr_t)0x100000000ULL,(uintptr_t)0x300000000ULL,
                          code,site_patch)) return 7;
    return 0;
}

static int unwind_test(void)
{
    static const unsigned char original_unwind[28]={
        0x01,0x2A,0x0B,0x00,0x1C,0x34,0x29,0x00,
        0x1C,0x01,0x1E,0x00,0x10,0xF0,0x0E,0xE0,
        0x0C,0xD0,0x0A,0xC0,0x08,0x70,0x07,0x60,0x06,0x50,0x00,0x00
    };
    unsigned char *page=(unsigned char *)VirtualAlloc(NULL,0x1000U,
        MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    RUNTIME_FUNCTION original={0x300U,0x400U,{0x200U}};
    RUNTIME_FUNCTION table={0x80U,0x97U,{0x40U}};
    PRUNTIME_FUNCTION found;
    DECLSPEC_ALIGN(16) uint64_t stack[80];
    CONTEXT context;
    DWORD64 base=0,establisher=0;
    PVOID handler=NULL;
    size_t index;
    if (!page) return 10;
    memset(stack,0,sizeof(stack));memset(&context,0,sizeof(context));
    memcpy(page+0x40,"\x21\0\0\0",4U);
    memcpy(page+0x44,&original,sizeof(original));
    memcpy(page+0x200,original_unwind,sizeof(original_unwind));
    for (index=0;index<7U;++index) stack[0xF0U/8U+index]=0xB000U+index;
    stack[0x128U/8U]=0x12345678U;
    stack[0x148U/8U]=0xBCBCU;
    context.ContextFlags=CONTEXT_FULL;
    context.Rip=(DWORD64)(uintptr_t)page+0x92U;
    context.Rsp=(DWORD64)(uintptr_t)stack;
    if (!RtlAddFunctionTable(&table,1U,(DWORD64)(uintptr_t)page)) return 11;
    found=RtlLookupFunctionEntry(context.Rip,&base,NULL);
    if (found!=&table || base!=(DWORD64)(uintptr_t)page) return 12;
    (void)RtlVirtualUnwind(UNW_FLAG_NHANDLER,base,context.Rip,found,&context,
                          &handler,&establisher,NULL);
    if (context.Rip!=0x12345678U || context.Rsp!=(DWORD64)(uintptr_t)stack+0x130U ||
        context.Rbx!=0xBCBCU || context.R15!=0xB000U || context.R14!=0xB001U ||
        context.R13!=0xB002U || context.R12!=0xB003U || context.Rdi!=0xB004U ||
        context.Rsi!=0xB005U || context.Rbp!=0xB006U) return 13;
    if (!RtlDeleteFunctionTable(&table) || !VirtualFree(page,0,MEM_RELEASE)) return 14;
    return 0;
}

static DWORD WINAPI idle_thread(void *unused)
{
    HANDLE stop=(HANDLE)unused;
    (void)WaitForSingleObject(stop,INFINITE);
    return 0;
}

/* Exercise the actual installation/removal and short thread-pause window
 * in this test process, never in FIFA. The reserved image supplies only a
 * synthetic code page and exact native unwind header.
 */
static int install_remove_test(void)
{
    static const unsigned char wrapper[]={
        0x53,0x41,0x55,0x49,0x89,0xCD,
        0x41,0x8B,0x9D,0x10,0x0C,0x00,0x00,
        0x89,0xD8,0x41,0x5D,0x5B,0xC3
    };
    static const unsigned char unwind[]={
        0x19,0x2A,0x0B,0x00,0x1C,0x34,0x29,0x00,
        0x1C,0x01,0x1E,0x00,0x10,0xF0,0x0E,0xE0,
        0x0C,0xD0,0x0A,0xC0,0x08,0x70,0x07,0x60,0x06,0x50,0x00,0x00
    };
    const SIZE_T size=BENCH_IMPORT_RVA+0x2000U;
    unsigned char *image=(unsigned char *)VirtualAlloc(NULL,size,MEM_RESERVE,PAGE_NOACCESS);
    unsigned char *entry;
    RUNTIME_FUNCTION table={BENCH_IMPORT_RVA-6U,BENCH_IMPORT_RVA+13U,{0x4000U}};
    BenchImportAdapter adapter;
    RequestFn function;
    HANDLE stop=NULL,thread=NULL;
    unsigned char settings[0xC18];
    uint32_t request=7U,policy=0x12345678U,actual=0;
    DWORD previous;
    BOOL registered=FALSE;
    int result=20;
    memset(&adapter,0,sizeof(adapter));
    if (!image) return result;
    if (!VirtualAlloc(image+(BENCH_IMPORT_RVA&~0xFFFU),0x1000U,
                      MEM_COMMIT,PAGE_READWRITE) ||
        !VirtualAlloc(image+0x4000U,0x1000U,MEM_COMMIT,PAGE_READWRITE)) goto finish;
    entry=image+BENCH_IMPORT_RVA-6U;
    memcpy(entry,wrapper,sizeof(wrapper));memcpy(image+0x4000U,unwind,sizeof(unwind));
    if (!VirtualProtect(image+(BENCH_IMPORT_RVA&~0xFFFU),0x1000U,
                        PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),entry,sizeof(wrapper))) goto finish;
    if (!RtlAddFunctionTable(&table,1U,(DWORD64)(uintptr_t)image)) goto finish;
    registered=TRUE;
    /* Unknown original bytes and unwind metadata must fail closed. */
    image[0x4000U]=0x01;
    if (bench_import_install(&adapter,(uintptr_t)image,size)) { result=21;goto finish; }
    image[0x4000U]=0x19;
    stop=CreateEventA(NULL,TRUE,FALSE,NULL);
    if (!stop) goto finish;
    thread=CreateThread(NULL,0,idle_thread,stop,0,NULL);
    if (!thread) goto finish;
    if (!bench_import_install(&adapter,(uintptr_t)image,size)) { result=22;goto finish; }
    if (!adapter.installed || !adapter.registered ||
        memcmp(image+BENCH_IMPORT_RVA,adapter.site_patch,BENCH_IMPORT_SITE_SIZE)!=0) {
        result=23;goto finish;
    }
    memset(settings,0xA5,sizeof(settings));
    memcpy(settings+0xC10U,&request,4U);memcpy(settings+0xC14U,&policy,4U);
    memcpy(&function,&entry,sizeof(function));
    if (function(settings)!=12U) { result=24;goto finish; }
    memcpy(&actual,settings+0xC14U,4U);
    if (actual!=policy || !bench_import_remove(&adapter) ||
        memcmp(image+BENCH_IMPORT_RVA,bench_import_original,BENCH_IMPORT_SITE_SIZE)!=0) {
        result=25;goto finish;
    }
    memcpy(settings+0xC10U,&request,4U);
    if (function(settings)!=7U) { result=26;goto finish; }
    result=0;
finish:
    if (adapter.page && !bench_import_remove(&adapter)) return 27;
    if (stop) SetEvent(stop);
    if (thread) {
        if (WaitForSingleObject(thread,5000U)!=WAIT_OBJECT_0) return 28;
        CloseHandle(thread);
    }
    if (stop) CloseHandle(stop);
    if (registered && !RtlDeleteFunctionTable(&table)) return 29;
    if (!VirtualFree(image,0,MEM_RELEASE)) return 30;
    return result;
}

int main(void)
{
    const int code=code_and_data_test();
    const int unwind=code ? 0 : unwind_test();
    const int transaction=(code || unwind) ? 0 : install_remove_test();
    if (code || unwind || transaction) {
        printf("bench import adapter failed code=%d unwind=%d transaction=%d\n",code,unwind,transaction);
        return 1;
    }
    puts("bench import adapter: 5 native request/data cases, branch bounds, chained unwind and guarded install/remove passed; gameplay not tested");
    return 0;
}
