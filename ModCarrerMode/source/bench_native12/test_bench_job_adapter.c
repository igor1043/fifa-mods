#define WIN32_LEAN_AND_MEAN
#include <stdio.h>
#include "bench_job_adapter.h"

typedef struct Capture {
    uint64_t rax,rcx,rdx,r8,r9,r10,r11,flags,rsp;
    unsigned char simd[6][16];
} Capture;
extern void test_job_bridge(void *queue,void *adapter,unsigned int kind,Capture *out);
extern void test_job_resume(void);
extern void test_job_flush_clobber(void);
static unsigned char queue[0xC98U+48U*192U+64U];
static unsigned int completed[2048],calls,errors;
static volatile LONG64 batches;

static uint32_t get32(size_t offset) { uint32_t v;memcpy(&v,queue+offset,4U);return v; }
static uint64_t get64(size_t offset) { uint64_t v;memcpy(&v,queue+offset,8U);return v; }
static void put32(size_t offset,uint32_t v) { memcpy(queue+offset,&v,4U); }
static void put64(size_t offset,uint64_t v) { memcpy(queue+offset,&v,8U); }

/* Separate test process only. Model the confirmed intrusive queue layout
 * and wait-for-completion semantics; not real FIFA actor/resource tasks.
 */
void test_job_drain(void *owner,uintptr_t callback_stack)
{
    uint32_t count=get32(0xC7C),i;
    ++calls;
    if (owner!=queue || callback_stack%16U || count>192U || get32(0xC78)!=count ||
        get64(0xC38)!=0x1111222233334444ULL ||
        get64(0xC40)!=(uint64_t)(uintptr_t)queue) { ++errors;return; }
    for (i=0;i<count;++i) {
        uintptr_t record=(uintptr_t)get64(0x20U+16U*i);
        uint32_t id=0;
        if (record<(uintptr_t)queue+0xC98U || record>(uintptr_t)queue+sizeof(queue)-4U) {
            ++errors;continue;
        }
        memcpy(&id,(const void *)record,4U);
        if (id>=2048U) ++errors;
        else ++completed[id];
    }
    put32(0xC78,0);put32(0xC7C,0);put32(0xC80,0);
}

static void reset(void)
{
    memset(queue,0,sizeof(queue));memset(completed,0,sizeof(completed));
    calls=errors=0;batches=0;
    put64(0xC38,0x1111222233334444ULL);
    put64(0xC40,(uint64_t)(uintptr_t)queue);put32(0xC80,1);
}

static int arguments(const Capture *out,unsigned int kind,uint32_t index)
{
    unsigned int i,j;
    if (out->rax!=0x1111 || out->rdx!=0x3333 || out->r9!=0x4444 ||
        out->r11!=0x6666 || (out->flags&0xCD5U)!=0x44U || out->rsp%16U) return 1;
    if (kind!=1U && (out->rcx!=(uint64_t)(uintptr_t)queue-(kind==3U ? 0x20U : 0U) ||
        out->r8!=0x7777 || out->r10!=index)) return 2;
    if (kind==1U && (out->rcx!=index || out->r8!=(uint64_t)(uintptr_t)queue || out->r10!=0x5555)) return 3;
    for (i=0;i<6U;++i) for(j=0;j<16U;++j) if(out->simd[i][j]!=0x5A) return 4;
    return 0;
}

static int batch_case(unsigned int kind,unsigned int total)
{
    static const unsigned char original[4][7]={
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x49,0x63,0x88,0x90,0x0C,0,0},
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x4C,0x63,0x91,0xB0,0x0C,0,0}
    };
    unsigned char *page=(unsigned char *)VirtualAlloc(NULL,0x1000U,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    DWORD previous;
    unsigned int i;
    int result=0;
    const unsigned int stride=kind==0U ? 48U : kind==3U ? 24U : 32U;
    reset();
    if (!page || !bench_job_emit((uintptr_t)page,
            (uintptr_t)test_job_flush_clobber,original[kind],kind,&batches) ||
        !VirtualProtect(page,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),page,bench_job_code_size())) return 10;
    for (i=0;i<total;++i) {
        Capture out;
        uint32_t index=get32(0xC90),nodes;
        if (index>=192U) index=0;
        memset(&out,0,sizeof(out));test_job_bridge(queue,page,kind,&out);
        if (arguments(&out,kind,index)) { result=11;break; }
        nodes=get32(0xC7C);
        if (nodes>=192U || get32(0xC90)>=192U) { result=12;break; }
        memcpy(queue+0xC98U+stride*index,&i,4U);
        put64(0x18U+nodes*16U,0);
        put64(0x20U+nodes*16U,(uint64_t)(uintptr_t)(queue+0xC98U+stride*index));
        put32(0xC90,index+1U);put32(0xC7C,nodes+1U);put32(0xC78,nodes+1U);
    }
    if (!result) {
        test_job_drain(queue,0);
        if (errors || batches!=(LONG64)((total-1U)/192U) ||
            calls!=(total-1U)/192U+1U || get64(0xC38)!=0x1111222233334444ULL ||
            get64(0xC40)!=(uint64_t)(uintptr_t)queue) result=13;
        for (i=0;i<total;++i) if(completed[i]!=1U) result=14;
        for (;i<2048U;++i) if(completed[i]) result=15;
    }
    if (!VirtualFree(page,0,MEM_RELEASE)) return 16;
    return result;
}

static int original_overflow(void)
{
    unsigned int i;
    reset();
    for (i=0;i<203U;++i) {
        put64(0x18U+i*16U,0);
        put64(0x20U+i*16U,(uint64_t)(uintptr_t)(queue+0xC98U+48U*i));
    }
    /* Node 194 writes NEXT directly over callback +C38. */
    return get64(0xC38)==0x1111222233334444ULL ? 20 : 0;
}

static int independent_capacity_guards(unsigned int kind)
{
    static const unsigned char original[4][7]={
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x49,0x63,0x88,0x90,0x0C,0,0},
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x4C,0x63,0x91,0xB0,0x0C,0,0}
    };
    unsigned char *page=(unsigned char *)VirtualAlloc(NULL,0x1000U,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    DWORD previous;
    unsigned int scenario,i;
    if (!page || !bench_job_emit((uintptr_t)page,(uintptr_t)test_job_flush_clobber,
            original[kind],kind,&batches) ||
        !VirtualProtect(page,0x1000U,PAGE_EXECUTE_READ,&previous)) return 42;
    for (scenario=0;scenario<2U;++scenario) {
        Capture out;
        reset();
        if (!scenario) put32(0xC90,192U); /* Records full, all tasks already completed. */
        else {
            put32(0xC90,1);put32(0xC7C,192);put32(0xC78,192);
            put32(0xC98,7);
            for (i=0;i<192U;++i) put64(0x20U+16U*i,(uint64_t)(uintptr_t)(queue+0xC98));
        }
        memset(&out,0,sizeof(out));test_job_bridge(queue,page,kind,&out);
        if (arguments(&out,kind,0) || calls!=1 || batches!=1 || errors ||
            get32(0xC90) || get32(0xC7C) || get32(0xC78) || get32(0xC80)) return 43;
    }
    return VirtualFree(page,0,MEM_RELEASE) ? 0 : 44;
}

static int install_unwind_remove(void)
{
    const SIZE_T size=0x49AD300U;
    unsigned char *image=(unsigned char *)VirtualAlloc(NULL,size,MEM_RESERVE,PAGE_NOACCESS);
    static const RUNTIME_FUNCTION native[2]={
        {0x49AA8B0U,0x49AA960U,{0x30D52C8U}},{0x49AC129U,0x49AC3D6U,{0x3178F0CU}}
    };
    static const unsigned char original[4][7]={
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x49,0x63,0x88,0x90,0x0C,0,0},
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x4C,0x63,0x91,0xB0,0x0C,0,0}
    };
    static const unsigned char headers[2][8]={
        {1,5,2,0,5,0x32,1,0x30},{1,5,2,0,5,0x32,1,0x30}
    };
    RUNTIME_FUNCTION table[2];
    unsigned int kind,stage;
    DWORD previous;
    int result=30;
    if (!image) return result;
    memcpy(table,native,sizeof(table));
    /* Installation is also checked separately with the real chained header;
     * virtual unwind below uses a simple inherited 0x28-byte test frame.
     */
    for (kind=0;kind<4U;++kind) {
        const uintptr_t sites[4]={0x49AA8B5U,0x49AC29FU,0x49AA820U,0x49AA960U};
        uintptr_t rva=sites[kind];
        BenchJobAdapter adapter;
        memset(&adapter,0,sizeof(adapter));
        if (!VirtualAlloc(image+(rva&~0xFFFU),0x1000U,MEM_COMMIT,PAGE_READWRITE)) goto finish;
        if (!VirtualProtect(image+(rva&~0xFFFU),0x1000U,PAGE_READWRITE,&previous)) goto finish;
        memcpy(image+rva,original[kind],7U);
        if (kind<2U) {
            if (!VirtualAlloc(image+(native[kind].UnwindData&~0xFFFU),0x1000U,MEM_COMMIT,PAGE_READWRITE)) goto finish;
            memcpy(image+rva-5U,"\x53\x48\x83\xEC\x20",5U);
            if (!kind) memcpy(image+native[kind].UnwindData,headers[kind],8U);
            else memcpy(image+native[kind].UnwindData,
                    "\x21\x0F\x06\x00\x0F\xE4\x0A\x00\x0A\xD4\x0B\x00\x05\xC4\x0C\x00",16U);
        }
        memcpy(image+rva+7U,kind==1U ? "\x48\x89\xC8" : "\x4C\x89\xD0",3U);
        memcpy(image+rva+10U,kind<2U ? "\x48\x83\xC4\x20\x5B\xC3" : "\xC3",kind<2U ? 6U : 1U);
        if (!VirtualProtect(image+(rva&~0xFFFU),0x1000U,PAGE_EXECUTE_READ,&previous) ||
            (kind<2U && !RtlAddFunctionTable(&table[kind],1U,(DWORD64)(uintptr_t)image))) goto finish;
        if (kind<2U) image[native[kind].UnwindData]=0;
        else {
            if (!VirtualProtect(image+(rva&~0xFFFU),0x1000U,PAGE_EXECUTE_READWRITE,&previous)) goto finish;
            image[rva]=0;
        }
        if (bench_job_install(&adapter,(uintptr_t)image,size,kind)) return 31;
        if (kind<2U) image[native[kind].UnwindData]=kind ? 0x21 : 1;
        else image[rva]=original[kind][0];
        if (!bench_job_install(&adapter,(uintptr_t)image,size,kind)) return 32;
        {
            typedef uint64_t (WINAPI *Synthetic)(void *,void *,void *);
            Synthetic call;
            unsigned char *fn=image+rva-(kind<2U ? 5U : 0U);
            memcpy(&call,&fn,sizeof(call));
            reset();put32(0xC90,7U);
            if (call(kind==3U ? (void *)((uintptr_t)queue-0x20U) : queue,NULL,queue)!=7U) return 39;
        }
        if (kind<2U) memcpy(image+native[kind].UnwindData,headers[kind],8U);
        for (stage=0;stage<6U;++stage) {
            DECLSPEC_ALIGN(16) uint64_t stack[80];
            CONTEXT ctx;
            DWORD64 base=0,establisher=0;
            PVOID handler=NULL;
            PRUNTIME_FUNCTION found;
            const size_t full=kind<2U ? 0xC8U : 0xD0U;
            const size_t extras[6]={0,8,full,full,8U,0};
            const size_t offsets[6]={0,1,8,16U,
                (size_t)((uintptr_t)bench_job_flags_restore-(uintptr_t)bench_job_template_begin),
                (size_t)((uintptr_t)bench_job_flags_restore-(uintptr_t)bench_job_template_begin)+1U};
            const size_t extra=extras[stage];
            memset(stack,0,sizeof(stack));memset(&ctx,0,sizeof(ctx));
            stack[extra/8U]=(uint64_t)(uintptr_t)image+rva+5U;
            if (kind<2U) {
                stack[(extra+8U+0x20U)/8U]=0xBCBCBCU;
                stack[(extra+8U+0x28U)/8U]=0x12345678U;
            } else stack[(extra+8U)/8U]=0x12345678U;
            ctx.Rbx=0xABCDU;
            ctx.Rip=(DWORD64)(uintptr_t)adapter.entry.page+offsets[stage];
            ctx.Rsp=(DWORD64)(uintptr_t)stack;
            found=RtlLookupFunctionEntry(ctx.Rip,&base,NULL);
            if (found!=&adapter.runtime[stage<4U ? 0U : 1U]) return 33;
            (void)RtlVirtualUnwind(UNW_FLAG_NHANDLER,base,ctx.Rip,found,&ctx,&handler,&establisher,NULL);
            if (ctx.Rip!=(DWORD64)(uintptr_t)image+rva+5U ||
                ctx.Rsp!=(DWORD64)(uintptr_t)stack+extra+8U) return 34;
            found=RtlLookupFunctionEntry(ctx.Rip,&base,NULL);
            if (kind<2U) {
                if (found!=&table[kind]) return 37;
                (void)RtlVirtualUnwind(UNW_FLAG_NHANDLER,base,ctx.Rip,found,&ctx,&handler,&establisher,NULL);
            } else {
                if (found) return 45;
                ctx.Rip=*(const uint64_t *)(uintptr_t)ctx.Rsp;ctx.Rsp+=8U;
            }
            if (ctx.Rip!=0x12345678U || ctx.Rsp!=(DWORD64)(uintptr_t)stack+extra+(kind<2U ? 0x38U : 0x10U) ||
                ctx.Rbx!=(kind<2U ? 0xBCBCBCU : 0xABCDU)) return 38;
        }
        if (!bench_job_remove(&adapter) || memcmp(image+rva,original[kind],7U)!=0 ||
            (kind<2U && !RtlDeleteFunctionTable(&table[kind]))) return 35;
        if (!adapter.published || !adapter.entry.registered || !adapter.entry.page) return 40;
        /* Test process has no concurrent calls; explicitly dispose retained
         * code after testing the real rollback retention policy. */
        if (!RtlDeleteFunctionTable(adapter.runtime) ||
            !VirtualFree(adapter.entry.page,0,MEM_RELEASE)) return 41;
    }
    result=0;
finish:
    if (!VirtualFree(image,0,MEM_RELEASE)) return 36;
    return result;
}

int main(void)
{
    static const unsigned int totals[]={1,191,192,193,203,500,1024};
    unsigned int kind=0,i=0;
    int result=original_overflow();
    for (kind=0;!result && kind<4U;++kind) {
        for (i=0;!result && i<sizeof(totals)/sizeof(totals[0]);++i)
            result=batch_case(kind,totals[i]);
    }
    for (kind=0;!result && kind<4U;++kind) result=independent_capacity_guards(kind);
    if (!result) result=install_unwind_remove();
    if (result) { printf("job adapter failed=%d kind=%u case=%u\n",result,kind,i);return 1; }
    puts("job adapter: original overflow reproduced; 28 batch/ABI cases (24/32/48-byte, embedded queue and both stack alignments) and 8 independent capacity guards preserve all tasks, callback/context, GPR/SIMD/flags; guarded install/CALL, 24 independent-frame/caller unwind states and safe rollback retention passed; gameplay not tested");
    return 0;
}
