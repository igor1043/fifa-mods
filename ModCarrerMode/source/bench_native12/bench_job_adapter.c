#define WIN32_LEAN_AND_MEAN
#include "bench_job_adapter.h"

static SIZE_T delta(const unsigned char *symbol)
{ return (SIZE_T)((uintptr_t)symbol-(uintptr_t)bench_job_template_begin); }

SIZE_T bench_job_code_size(void) { return delta(bench_job_template_end); }

BOOL bench_job_emit(uintptr_t page,uintptr_t native_flush,
                    const unsigned char original[7],unsigned int kind,volatile LONG64 *counter)
{
    SIZE_T size=bench_job_code_size();
    uintptr_t counter_address=(uintptr_t)counter;
    if (!page || !native_flush || !original || !counter || kind>=BENCH_JOB_ADAPTER_COUNT || size>0x300U ||
        delta(bench_job_original_instruction)+7U>size ||
        delta(bench_job_flush_pointer)+8U>size ||
        delta(bench_job_counter_pointer)+8U>size ||
        memcmp(bench_job_template_begin,"\x9C\x48\x81\xEC\xC0\x00\x00\x00",8U)!=0 ||
        memcmp(bench_job_owner_before,"\x48\x8B\x4C\x24\x28",5U)!=0 ||
        memcmp(bench_job_owner_after,"\x48\x8B\x4C\x24\x28",5U)!=0 ||
        bench_job_flags_restore[0]!=0x9D ||
        memcmp(bench_job_stack_release,"\x48\x8D\xA4\x24\xC0\x00\x00\x00",8U)!=0) return FALSE;
    memcpy((void *)page,bench_job_template_begin,size);
    memcpy((void *)(page+delta(bench_job_flush_pointer)),&native_flush,8U);
    memcpy((void *)(page+delta(bench_job_counter_pointer)),&counter_address,8U);
    memcpy((void *)(page+delta(bench_job_original_instruction)),original,7U);
    /* First producer keeps the queue in RCX; the second keeps it in R8.
     * Save/restore the caller's original RCX in both cases. */
    if (kind==1U) {
        *(unsigned char *)(page+delta(bench_job_owner_before)+4U)=0x38;
        *(unsigned char *)(page+delta(bench_job_owner_after)+4U)=0x38;
    }
    /* The two leaf producers have RSP=8 mod 16 at the original site.
     * The last one embeds this queue at caller object +20, with its record
     * count at CB0 rather than C90 relative to the caller object. */
    if (kind>=2U) {
        *(unsigned char *)(page+4U)=0xC8;
        *(unsigned char *)(page+delta(bench_job_stack_release)+4U)=0xC8;
    }
    if (kind==3U) {
        memcpy((void *)(page+delta(bench_job_owner_shift_before)),"\x48\x8D\x49\x20",4U);
        memcpy((void *)(page+delta(bench_job_owner_shift_after)),"\x48\x8D\x49\x20",4U);
    }
    return TRUE;
}

static BOOL read_self(uintptr_t address,void *out,SIZE_T size)
{
    SIZE_T received=0;
    return ReadProcessMemory(GetCurrentProcess(),(const void *)address,out,size,&received) &&
        received==size;
}

BOOL bench_job_code_ready(uintptr_t image)
{
    static const struct {
        uintptr_t rva; SIZE_T size; unsigned char expected[32];
    } guards[]={
        {0x49AA8B0U,12U,{0x53,0x48,0x83,0xEC,0x20,0x4C,0x63,0x91,0x90,0x0C,0,0}},
        {0x49AC29BU,11U,{0x4C,0x8B,0x40,0x50,0x49,0x63,0x88,0x90,0x0C,0,0}},
        {0x49AA904U,7U,{0xF0,0xFF,0x81,0x78,0x0C,0,0}},
        {0x49AA916U,8U,{0xF0,0x0F,0xC1,0x81,0x7C,0x0C,0,0}},
        {0x49AA921U,4U,{0x48,0x8D,0x53,0x18}},
        {0x49AA940U,11U,{0x48,0xC7,0x02,0,0,0,0,0x4C,0x89,0x1C,0xC3}},
        {0x49AC2D8U,8U,{0xF0,0x41,0xFF,0x80,0x78,0x0C,0,0}},
        {0x49AC2EBU,9U,{0xF0,0x41,0x0F,0xC1,0x80,0x7C,0x0C,0,0}},
        {0x49AC30FU,15U,{0x49,0x89,0x14,0xC0,0x4D,0x01,0xC1,0x49,0xC7,0x41,0x18,0,0,0,0}},
        {0x49AD1E0U,27U,{0x48,0x89,0x5C,0x24,8,0x57,0x48,0x83,0xEC,0x20,0x31,0xFF,
            0x48,0x89,0xCB,0x89,0xB9,0x80,0x0C,0,0,0x8B,0x81,0x78,0x0C,0,0}},
        {0x49AD1FFU,5U,{0xE8,0xDC,0xF6,0xFF,0xFF}},
        {0x49AD234U,6U,{0x89,0xBB,0x7C,0x0C,0,0}},
        {0x49AC982U,32U,{0x48,0x89,0x2A,0x48,0x8B,0x52,8,0x48,0x8B,0x8B,0x40,0x0C,0,0,
            0xFF,0x93,0x38,0x0C,0,0,0xF0,0xFF,0x8B,0x78,0x0C,0,0,0xE9,0x7B,0xFF,0xFF,0xFF}},
        {0x49AA820U,10U,{0x4C,0x63,0x91,0x90,0x0C,0,0,0x49,0x89,0xCB}},
        {0x49AA837U,14U,{0x4C,0x8D,0x91,0x98,0x0C,0,0,0x48,0xC1,0xE0,5,0x49,1,0xC2}},
        {0x49AA859U,7U,{0xF0,0xFF,0x81,0x78,0x0C,0,0}},
        {0x49AA86BU,8U,{0xF0,0x0F,0xC1,0x81,0x7C,0x0C,0,0}},
        {0x49AA895U,11U,{0x48,0xC7,2,0,0,0,0,0x4D,0x89,0x14,0xC3}},
        {0x49AA960U,15U,{0x4C,0x63,0x91,0xB0,0x0C,0,0,0x4F,0x8D,0x9C,0x12,0x97,1,0,0}},
        {0x49AA973U,14U,{0x89,0x81,0xB0,0x0C,0,0,0x4D,1,0xD3,0x4E,0x8D,0x1C,0xD9,0x4D}},
        {0x49AA98BU,12U,{0x4C,0x8D,0x41,0x20,0xF0,0x41,0xFF,0x80,0x78,0x0C,0,0}},
        {0x49AA9A2U,9U,{0xF0,0x41,0x0F,0xC1,0x80,0x7C,0x0C,0,0}},
        {0x49AA9CAU,11U,{0x48,0xC7,2,0,0,0,0,0x4D,0x89,0x1C,0xC0}}
    };
    unsigned char raw[32];
    SIZE_T index;
    for (index=0;index<sizeof(guards)/sizeof(guards[0]);++index) {
        if (!read_self(image+guards[index].rva,raw,guards[index].size) ||
            memcmp(raw,guards[index].expected,guards[index].size)!=0) return FALSE;
    }
    return TRUE;
}

BOOL bench_job_remove(BenchJobAdapter *adapter)
{
    BenchImportAdapter *entry;
    unsigned char current[7];
    if (!adapter) return FALSE;
    entry=&adapter->entry;
    if (entry->installed) {
        const uintptr_t site=entry->image+adapter->rva;
        if (!read_self(site,current,7U)) return FALSE;
        if (memcmp(current,adapter->original,7U)!=0 &&
            !bench_adapter_write_site(site,entry->site_patch,adapter->original)) return FALSE;
        entry->installed=FALSE;
    }
    /* A thread may be inside native_flush with a return address in this
     * page. After ever publishing a CALL, retain its page and unwind table
     * until process exit, even after restoring the native instruction.
     * The mod host retains this successful-start module for that lifetime.
     */
    if (adapter->published) return TRUE;
    if (entry->registered && !RtlDeleteFunctionTable(adapter->runtime)) return FALSE;
    entry->registered=FALSE;
    if (entry->page && !VirtualFree(entry->page,0,MEM_RELEASE)) return FALSE;
    entry->page=NULL;
    return TRUE;
}

BOOL bench_job_install(BenchJobAdapter *adapter,uintptr_t image,SIZE_T image_size,
                      unsigned int kind)
{
    static const uintptr_t sites[4]={0x49AA8B5U,0x49AC29FU,0x49AA820U,0x49AA960U};
    static const unsigned char instructions[4][7]={
        {0x4C,0x63,0x91,0x90,0x0C,0x00,0x00},
        {0x49,0x63,0x88,0x90,0x0C,0x00,0x00},
        {0x4C,0x63,0x91,0x90,0x0C,0,0},{0x4C,0x63,0x91,0xB0,0x0C,0,0}
    };
    static const unsigned char unwind[12]={
        0x01,0x08,0x03,0x00,0x08,0x01,0x18,0x00,0x01,0x02,0x00,0x00
    };
    BenchImportAdapter *entry;
    RUNTIME_FUNCTION native;
    PRUNTIME_FUNCTION found;
    DWORD64 native_base=0;
    unsigned char current[7],patch[7];
    uintptr_t site,offset;
    int64_t distance;
    int32_t rel;
    DWORD previous;
    static const RUNTIME_FUNCTION expected_runtime[2]={
        {0x49AA8B0U,0x49AA960U,{0x30D52C8U}},
        {0x49AC129U,0x49AC3D6U,{0x3178F0CU}}
    };
    static const unsigned char native_headers[2][16]={
        {1,5,2,0,5,0x32,1,0x30},
        {0x21,0x0F,6,0,0x0F,0xE4,0x0A,0,0x0A,0xD4,0x0B,0,5,0xC4,0x0C,0}
    };
    unsigned char native_header[16];
    SIZE_T header_size=kind==0U ? 8U : 16U;
    if (!adapter || kind>=BENCH_JOB_ADAPTER_COUNT || adapter->entry.page) return FALSE;
    entry=&adapter->entry;adapter->rva=sites[kind];site=image+sites[kind];
    memcpy(adapter->original,instructions[kind],7U);
    if (!read_self(site,current,7U) || memcmp(current,instructions[kind],7U)!=0) return FALSE;
    found=RtlLookupFunctionEntry(site,&native_base,NULL);
    if (kind<2U) {
        if (!found || native_base!=image || !read_self((uintptr_t)found,&native,sizeof(native)) ||
            memcmp(&native,&expected_runtime[kind],sizeof(native))!=0 ||
            !read_self(image+native.UnwindData,native_header,header_size) ||
            memcmp(native_header,native_headers[kind],header_size)!=0) return FALSE;
    } else if (found) return FALSE; /* Exact supported leaf functions have no .pdata entry. */
    entry->image=image;entry->page=bench_adapter_near_page(image,image_size,site);
    if (!entry->page) return FALSE;
    offset=(uintptr_t)entry->page-image;
    distance=(int64_t)(uintptr_t)entry->page-(int64_t)(site+5U);
    if (offset>UINT32_MAX-0x1000U || distance<INT32_MIN || distance>INT32_MAX ||
        !bench_job_emit((uintptr_t)entry->page,image+0x49AD1E0U,
                        instructions[kind],kind,&adapter->batch_counter))
        goto fail;
    rel=(int32_t)distance;patch[0]=0xE8;memcpy(patch+1,&rel,4U);patch[5]=patch[6]=0x90;
    memcpy(entry->site_patch,patch,7U);
    /* A real CALL/RET creates an independent frame. Do not chain a newly
     * allocated stack frame into the game's inherited native unwind data.
     * Its return address is site+5, followed by two owned NOPs.
     */
    memcpy(entry->page+0x400,unwind,sizeof(unwind));
    if (kind>=2U) entry->page[0x406]=0x19; /* Allocate C8, rather than C0. */
    memcpy(entry->page+0x440,"\x01\x00\x01\x00\x00\x02\x00\x00",8U);
    adapter->runtime[0].BeginAddress=(DWORD)offset;
    adapter->runtime[0].EndAddress=(DWORD)(offset+delta(bench_job_flags_restore));
    adapter->runtime[0].UnwindData=(DWORD)(offset+0x400U);
    adapter->runtime[1].BeginAddress=adapter->runtime[0].EndAddress;
    adapter->runtime[1].EndAddress=(DWORD)(offset+delta(bench_job_flush_pointer));
    adapter->runtime[1].UnwindData=(DWORD)(offset+0x440U);
    if (!VirtualProtect(entry->page,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),entry->page,0x450U)) goto fail;
    if (!RtlAddFunctionTable(adapter->runtime,2U,image)) goto fail;
    entry->registered=TRUE;entry->installed=TRUE;
    adapter->published=TRUE;
    if (!bench_adapter_write_site(site,instructions[kind],patch)) goto fail;
    return TRUE;
fail:
    (void)bench_job_remove(adapter);
    return FALSE;
}
