#define WIN32_LEAN_AND_MEAN
#include "bench_import_adapter.h"
#include <tlhelp32.h>

#define BENCH_PATCH_MAX_THREADS 512U

/* A seven-byte detour is not an atomic write. Collect handles before
 * suspending, then keep the protected write window short. Never allocate,
 * log, wait for the game or call a native game function while suspended.
 */
typedef struct PatchThreads {
    HANDLE handles[BENCH_PATCH_MAX_THREADS];
    size_t count;
    size_t suspended;
} PatchThreads;

static void release_threads(PatchThreads *threads)
{
    size_t index;
    for (index=threads->suspended;index>0U;--index)
        (void)ResumeThread(threads->handles[index-1U]);
    for (index=0;index<threads->count;++index)
        CloseHandle(threads->handles[index]);
    threads->suspended=0;threads->count=0;
}

static BOOL pause_threads(PatchThreads *threads, uintptr_t site)
{
    THREADENTRY32 entry;
    HANDLE snapshot;
    const DWORD process=GetCurrentProcessId(), current=GetCurrentThreadId();
    size_t index;
    BOOL ok=TRUE;
    memset(threads,0,sizeof(*threads));
    snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD,0);
    if (snapshot==INVALID_HANDLE_VALUE) return FALSE;
    memset(&entry,0,sizeof(entry));entry.dwSize=sizeof(entry);
    if (!Thread32First(snapshot,&entry)) ok=FALSE;
    while (ok) {
        if (entry.th32OwnerProcessID==process && entry.th32ThreadID!=current) {
            HANDLE thread;
            if (threads->count==BENCH_PATCH_MAX_THREADS) { ok=FALSE;break; }
            thread=OpenThread(THREAD_SUSPEND_RESUME|THREAD_GET_CONTEXT|
                              THREAD_QUERY_INFORMATION,FALSE,entry.th32ThreadID);
            if (!thread) {
                /* A thread that already exited cannot execute this patch. */
                if (GetLastError()!=ERROR_INVALID_PARAMETER) { ok=FALSE;break; }
            } else threads->handles[threads->count++]=thread;
        }
        entry.dwSize=sizeof(entry);
        if (!Thread32Next(snapshot,&entry)) {
            if (GetLastError()!=ERROR_NO_MORE_FILES) ok=FALSE;
            break;
        }
    }
    CloseHandle(snapshot);
    if (!ok) { release_threads(threads);return FALSE; }
    for (index=0;index<threads->count;++index) {
        CONTEXT context;
        if (SuspendThread(threads->handles[index])==(DWORD)-1) {
            release_threads(threads);return FALSE;
        }
        ++threads->suspended;
        memset(&context,0,sizeof(context));context.ContextFlags=CONTEXT_CONTROL;
        if (!GetThreadContext(threads->handles[index],&context) ||
            (context.Rip>=site && context.Rip<site+BENCH_IMPORT_SITE_SIZE)) {
            release_threads(threads);return FALSE;
        }
    }
    return TRUE;
}

static BOOL copy_read(uintptr_t address, void *out, SIZE_T size)
{
    SIZE_T received=0;
    return ReadProcessMemory(GetCurrentProcess(),(const void *)address,out,size,&received) &&
        received==size;
}

unsigned char *bench_adapter_near_page(uintptr_t image, SIZE_T image_size, uintptr_t site)
{
    SYSTEM_INFO system;
    MEMORY_BASIC_INFORMATION info;
    uintptr_t address, limit=site+(uintptr_t)INT32_MAX-0x10000U;
    GetSystemInfo(&system);
    address=(image+image_size+system.dwAllocationGranularity-1U)&
        ~((uintptr_t)system.dwAllocationGranularity-1U);
    while (address<limit) {
        uintptr_t end;
        if (!VirtualQuery((const void *)address,&info,sizeof(info))) return NULL;
        end=(uintptr_t)info.BaseAddress+info.RegionSize;
        if (end<=address) return NULL;
        if (info.State==MEM_FREE) {
            uintptr_t aligned=(address+system.dwAllocationGranularity-1U)&
                ~((uintptr_t)system.dwAllocationGranularity-1U);
            if (aligned<limit && aligned+0x1000U<=end) {
                unsigned char *page=(unsigned char *)VirtualAlloc((void *)aligned,0x1000U,
                    MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
                if (page) return page;
            }
        }
        address=end;
    }
    return NULL;
}

BOOL bench_adapter_write_site(uintptr_t address, const unsigned char *before,
    const unsigned char *after)
{
    unsigned char current[BENCH_IMPORT_SITE_SIZE];
    PatchThreads threads;
    DWORD previous=0, ignored=0;
    BOOL flushed, restored, matched, ok=FALSE;
    if (!copy_read(address,current,sizeof(current)) ||
        memcmp(current,before,sizeof(current))!=0) return FALSE;
    if (!pause_threads(&threads,address)) return FALSE;
    if (!copy_read(address,current,sizeof(current)) ||
        memcmp(current,before,sizeof(current))!=0 ||
        !VirtualProtect((void *)address,sizeof(current),PAGE_EXECUTE_READWRITE,&previous))
        goto finish;
    /* Installed only at startup, before real players load, with existing
     * threads paused. The game never resumes on a half-written instruction.
     */
    memcpy((void *)address,after,sizeof(current));
    flushed=FlushInstructionCache(GetCurrentProcess(),(const void *)address,sizeof(current));
    matched=copy_read(address,current,sizeof(current)) &&
        memcmp(current,after,sizeof(current))==0;
    if (!flushed || !matched) {
        memcpy((void *)address,before,sizeof(current));
        (void)FlushInstructionCache(GetCurrentProcess(),(const void *)address,sizeof(current));
    }
    restored=VirtualProtect((void *)address,sizeof(current),previous,&ignored);
    ok=flushed && matched && restored;
finish:
    release_threads(&threads);
    return ok;
}

BOOL bench_import_remove(BenchImportAdapter *adapter)
{
    unsigned char current[BENCH_IMPORT_SITE_SIZE];
    const uintptr_t site=adapter ? adapter->image+BENCH_IMPORT_RVA : 0;
    if (!adapter) return FALSE;
    if (adapter->installed) {
        if (!copy_read(site,current,sizeof(current))) return FALSE;
        if (memcmp(current,bench_import_original,sizeof(current))!=0 &&
            !bench_adapter_write_site(site,adapter->site_patch,bench_import_original)) return FALSE;
        adapter->installed=FALSE;
    }
    if (adapter->registered) {
        if (!RtlDeleteFunctionTable(&adapter->runtime)) return FALSE;
        adapter->registered=FALSE;
    }
    if (adapter->page && !VirtualFree(adapter->page,0,MEM_RELEASE)) return FALSE;
    adapter->page=NULL;
    return TRUE;
}

BOOL bench_import_install(BenchImportAdapter *adapter, uintptr_t image, SIZE_T image_size)
{
    unsigned char current[BENCH_IMPORT_SITE_SIZE], header[4];
    RUNTIME_FUNCTION original;
    PRUNTIME_FUNCTION found;
    DWORD64 original_base=0;
    DWORD previous=0;
    uintptr_t offset;
    const uintptr_t site=image+BENCH_IMPORT_RVA;
    if (!adapter || adapter->page || adapter->installed ||
        !copy_read(site,current,sizeof(current)) ||
        memcmp(current,bench_import_original,sizeof(current))!=0) return FALSE;
    found=RtlLookupFunctionEntry(site,&original_base,NULL);
    if (!found || original_base!=image || !copy_read((uintptr_t)found,&original,sizeof(original)) ||
        original.BeginAddress>BENCH_IMPORT_RVA || original.EndAddress<=BENCH_IMPORT_RVA ||
        !copy_read(image+original.UnwindData,header,sizeof(header)) ||
        memcmp(header,"\x19\x2A\x0B\x00",4U)!=0) return FALSE;
    adapter->image=image;
    adapter->page=bench_adapter_near_page(image,image_size,site);
    if (!adapter->page) return FALSE;
    offset=(uintptr_t)adapter->page-image;
    if (offset>UINT32_MAX-0x50U ||
        !bench_import_emit(site,(uintptr_t)adapter->page,adapter->page,adapter->site_patch))
        goto fail;
    /* Chained unwind inherits the already-executed native importer frame.
     * The adapter itself has no prologue, stack adjustment or register save.
     */
    memcpy(adapter->page+0x40,"\x21\x00\x00\x00",4U);
    memcpy(adapter->page+0x44,&original,sizeof(original));
    adapter->runtime.BeginAddress=(DWORD)offset;
    adapter->runtime.EndAddress=(DWORD)(offset+BENCH_IMPORT_CODE_SIZE);
    adapter->runtime.UnwindData=(DWORD)(offset+0x40U);
    if (!VirtualProtect(adapter->page,0x1000U,PAGE_EXECUTE_READ,&previous) ||
        !FlushInstructionCache(GetCurrentProcess(),adapter->page,0x50U)) goto fail;
    if (!RtlAddFunctionTable(&adapter->runtime,1U,image)) goto fail;
    adapter->registered=TRUE;
    /* Mark before writing: a failed protection restore/readback must not
     * free code that a partially installed entry could still reference.
     */
    adapter->installed=TRUE;
    if (!bench_adapter_write_site(site,bench_import_original,adapter->site_patch)) goto fail;
    return TRUE;
fail:
    (void)bench_import_remove(adapter);
    return FALSE;
}
