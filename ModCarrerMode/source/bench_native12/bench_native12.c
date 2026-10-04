#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <intrin.h>
#include <stdint.h>
#include <stdio.h>
#include <stdarg.h>
#include "bench_native12_core.h"
#include "bench_import_adapter.h"
#include "bench_job_adapter.h"
#include "../substitution_all7_rulescan_native/fifa16_mod_api.h"

static volatile LONG started;
static uintptr_t image_base;
static SIZE_T image_size;
static BenchImportAdapter import_adapter;
static BenchJobAdapter job_adapters[BENCH_JOB_ADAPTER_COUNT];
static char log_path[MAX_PATH];

static void log_event(const char *format, ...)
{
    FILE *file=NULL;
    SYSTEMTIME now;
    va_list args;
    if (!log_path[0] || fopen_s(&file,log_path,"ab") != 0 || !file) return;
    GetLocalTime(&now);
    fprintf(file,"%04u-%02u-%02u %02u:%02u:%02u ",now.wYear,now.wMonth,
        now.wDay,now.wHour,now.wMinute,now.wSecond);
    va_start(args,format); vfprintf(file,format,args); va_end(args);
    fputs("\r\n",file); fclose(file);
}

static BOOL read_memory(uintptr_t address, void *out, SIZE_T size)
{
    SIZE_T received=0;
    return address && out && size &&
        ReadProcessMemory(GetCurrentProcess(),(const void *)address,out,size,&received) &&
        received == size;
}

static BOOL supported_image(void)
{
    IMAGE_DOS_HEADER dos;
    IMAGE_NT_HEADERS64 nt;
    image_base=(uintptr_t)GetModuleHandleA(NULL);
    if (!read_memory(image_base,&dos,sizeof(dos)) || dos.e_magic != IMAGE_DOS_SIGNATURE ||
        dos.e_lfanew < 0 || dos.e_lfanew > 0x1000 ||
        !read_memory(image_base+(uintptr_t)dos.e_lfanew,&nt,sizeof(nt))) return FALSE;
    image_size=nt.OptionalHeader.SizeOfImage;
    return nt.Signature == IMAGE_NT_SIGNATURE && nt.FileHeader.Machine == IMAGE_FILE_MACHINE_AMD64 &&
        nt.FileHeader.TimeDateStamp == 0x577DE45CU &&
        nt.OptionalHeader.Magic == IMAGE_NT_OPTIONAL_HDR64_MAGIC &&
        (nt.OptionalHeader.SizeOfImage == 0x9524000U || nt.OptionalHeader.SizeOfImage == 0x9525000U);
}

/* Use the verified native singleton, not a scan of arbitrary values in RAM.
 * Do not change a match that has already constructed its real players.
 */
static int safe_before_player_load(void)
{
    uintptr_t engine=0, vtable=0;
    uint32_t count[2];
    unsigned int side;
    if (!read_memory(image_base+0x37477B0U,&engine,sizeof(engine))) return 0;
    if (!engine) return 1;
    if (!read_memory(engine,&vtable,sizeof(vtable)) || vtable != image_base+0x22D2CF0U) return 0;
    for (side=0; side<2U; ++side) {
        if (!read_memory(engine+0xBC0U+side*0x4B60U+0x4B40U,&count[side],4U)) return 0;
        if (count[side] > 1U) return -1;
    }
    return 1;
}

static BOOL code_ready(void)
{
    static const struct {
        uintptr_t rva; size_t size; unsigned char expected[12];
    } guards[] = {
        {0x415AEB0U,10U,{0x48,0x89,0x5C,0x24,0x08,0x48,0x89,0x6C,0x24,0x10}},
        {0x415AEDDU,7U,{0x48,0x8D,0xB2,0x04,0x01,0x00,0x00}},
        {0x415AEEBU,4U,{0x8B,0x4C,0x08,0x28}},
        {0x415AEEFU,10U,{0x83,0xE9,0x0B,0x44,0x39,0xF1,0x44,0x0F,0x4C,0xF1}},
        {0x415AF2DU,6U,{0xC7,0x00,0x1C,0x00,0x00,0x00}},
        {0x415AF43U,4U,{0x48,0x83,0xFA,0x34}},
        {0x414EB83U,7U,{0x41,0x8B,0x9D,0x10,0x0C,0x00,0x00}},
        {0x414EB4AU,3U,{0x49,0x89,0xCD}},
        {0x414EBB9U,5U,{0x42,0x89,0x5C,0x28,0x34}},
        {0x3D42150U,8U,{0x48,0x8B,0x05,0x91,0x7F,0x7A,0xFF,0xC3}},
        {0x4C0ED80U,5U,{0x48,0x8B,0x41,0x68,0xC3}}
    };
    unsigned char bytes[BENCH_NATIVE12_MAX_SIGNATURE];
    size_t index;
    for (index=0; index<sizeof(guards)/sizeof(guards[0]); ++index) {
        if (!read_memory(image_base+guards[index].rva,bytes,guards[index].size) ||
            memcmp(bytes,guards[index].expected,guards[index].size) != 0) return FALSE;
    }
    for (index=0; index<BENCH_NATIVE12_PATCH_COUNT; ++index) {
        const BenchNativePatch *patch=&bench_native12_patches[index];
        if (!read_memory(image_base+patch->rva,bytes,patch->size) ||
            !bench_native12_signature(patch,bytes,patch->size)) return FALSE;
    }
    return bench_job_code_ready(image_base);
}

static BOOL write_limit(const BenchNativePatch *patch, unsigned char value)
{
    unsigned char bytes[BENCH_NATIVE12_MAX_SIGNATURE];
    DWORD previous=0, ignored=0;
    uintptr_t address=image_base+patch->rva+patch->immediate;
    BOOL flushed, restored;
    if ((value != 7U && value != 12U) ||
        !read_memory(image_base+patch->rva,bytes,patch->size) ||
        !bench_native12_signature(patch,bytes,patch->size)) return FALSE;
    if (bytes[patch->immediate] == value) return TRUE;
    if (!VirtualProtect((void *)address,1U,PAGE_EXECUTE_READWRITE,&previous)) return FALSE;
    /* A single-byte instruction immediate; no detour/trampoline or partial
     * replacement of an opcode, pointer or seven-byte instruction.
     */
    (void)_InterlockedExchange8((volatile char *)address,(char)value);
    flushed=FlushInstructionCache(GetCurrentProcess(),(const void *)address,1U);
    restored=VirtualProtect((void *)address,1U,previous,&ignored);
    return flushed && restored && read_memory(image_base+patch->rva,bytes,patch->size) &&
        bench_native12_signature(patch,bytes,patch->size) && bytes[patch->immediate] == value;
}

static BOOL install_limits(void)
{
    unsigned char previous[BENCH_NATIVE12_PATCH_COUNT];
    unsigned char bytes[BENCH_NATIVE12_MAX_SIGNATURE];
    size_t index, applied=0;
    if (!code_ready() || safe_before_player_load() != 1) return FALSE;
    for (index=0; index<BENCH_NATIVE12_PATCH_COUNT; ++index) {
        const BenchNativePatch *patch=&bench_native12_patches[index];
        if (!read_memory(image_base+patch->rva,bytes,patch->size)) return FALSE;
        previous[index]=bytes[patch->immediate];
    }
    /* Install resource-queue protection before increasing any bench count.
     * Native tasks are completed in batches, never dropped or cloned.
     */
    for (index=0;index<BENCH_JOB_ADAPTER_COUNT;++index) {
        if (!bench_job_install(&job_adapters[index],image_base,image_size,(unsigned int)index)) {
            log_event("install_failed job_adapter=%llu error=%lu",(unsigned long long)index,GetLastError());
            goto rollback;
        }
    }
    for (index=0; index<BENCH_NATIVE12_PATCH_COUNT; ++index) {
        applied=index+1U; /* Include a failed write in rollback/readback. */
        if (!write_limit(&bench_native12_patches[index],12U)) {
            log_event("install_failed patch=%s error=%lu",bench_native12_patches[index].name,GetLastError());
            goto rollback;
        }
    }
    if (!bench_import_install(&import_adapter,image_base,image_size)) {
        log_event("install_failed coherent_native_import_request error=%lu",GetLastError());
        goto rollback;
    }
    log_event("installed version=3 coherent_import_request_rva=0x414EB83 FCE_immediate_rva=0x415AEDA late_copy_immediate_rva=0x44B434A job_sites=0x49AA8B5/0x49AC29F/0x49AA820/0x49AA960 native_drain=0x49AD1E0 batch_capacity=192 target=12 tasks_dropped=0 actor_clones=0 files_or_save_written=0 C14_or_substitution_rules_written=0");
    return TRUE;
rollback:
    while (applied) {
        --applied;
        if (!write_limit(&bench_native12_patches[applied],previous[applied]))
            log_event("rollback_failed patch=%s",bench_native12_patches[applied].name);
    }
    for (index=BENCH_JOB_ADAPTER_COUNT;index>0U;--index) {
        if (!bench_job_remove(&job_adapters[index-1U]))
            log_event("rollback_failed job_adapter=%llu",(unsigned long long)(index-1U));
    }
    return FALSE;
}

static void observe_batches(LONG64 previous[BENCH_JOB_ADAPTER_COUNT])
{
    unsigned int index;
    for (index=0;index<BENCH_JOB_ADAPTER_COUNT;++index) {
        const LONG64 count=InterlockedCompareExchange64(&job_adapters[index].batch_counter,0,0);
        if (count!=previous[index]) {
            previous[index]=count;
            log_event("resource_batch producer=%u total_drains=%lld capacity=192 tasks_dropped=0",index,count);
        }
    }
}

static void observe_loaded_lineup(uint32_t *previous_hash)
{
    uintptr_t engine=0, vtable=0;
    uint32_t count[2], bench[2]={0,0}, hash=2166136261U;
    unsigned int side, slot;
    if (!read_memory(image_base+0x37477B0U,&engine,sizeof(engine)) || !engine ||
        !read_memory(engine,&vtable,sizeof(vtable)) || vtable != image_base+0x22D2CF0U) return;
    for (side=0; side<2U; ++side) {
        const uintptr_t team=engine+0xBC0U+side*0x4B60U;
        if (!read_memory(team+0x4B40U,&count[side],4U) || count[side] > 23U) return;
        hash=(hash^count[side])*16777619U;
        for (slot=0; slot<count[side]; ++slot) {
            uint32_t id=0, role=0;
            if (!read_memory(team+0x1F4U+slot*0x330U,&id,4U) || !id || id >= 10000000U ||
                !read_memory(team+0x200U+slot*0x330U,&role,4U) || role > 29U) return;
            if (role == 28U) ++bench[side];
            hash=(hash^id)*16777619U; hash=(hash^role)*16777619U;
        }
    }
    if (hash == *previous_hash) return;
    *previous_hash=hash;
    log_event("native_input players=%lu/%lu bench_roles=%lu/%lu actor_resources_or_extra_substitution_verified=0",
        (unsigned long)count[0],(unsigned long)count[1],(unsigned long)bench[0],(unsigned long)bench[1]);
}

static void observe_native_request(uint32_t *previous_hash)
{
    uintptr_t main=0, controller=0, stack=0;
    unsigned char header[0x28];
    int32_t active=-1;
    uint32_t hash=2166136261U;
    unsigned int index;
    if (!read_memory(image_base+0x34EA0E8U,&main,sizeof(main)) || !main ||
        !read_memory(main+0x68U,&controller,sizeof(controller)) || !controller ||
        !read_memory(controller,&stack,sizeof(stack)) || !stack ||
        !read_memory(stack,header,sizeof(header))) return;
    memcpy(&active,header+0x20,4U);
    if (active<0 || active>3) return;
    for (index=0;index<=(unsigned int)active;++index) {
        uintptr_t state=0, vtable=0, settings=0;
        uint32_t request=0,policy=0,phase=0,bench[2]={0,0};
        unsigned int side,slot;
        memcpy(&state,header+index*8U,8U);
        if (!state || !read_memory(state,&vtable,sizeof(vtable)) ||
            (vtable!=image_base+0x21A5020U && vtable!=image_base+0x21A66D0U &&
             vtable!=image_base+0x21A4E90U)) continue;
        if (!read_memory(state+0x340U,&settings,sizeof(settings)) || !settings ||
            !read_memory(state+0x440U,&phase,4U) ||
            !read_memory(settings+0xC10U,&request,4U) ||
            !read_memory(settings+0xC14U,&policy,4U)) return;
        for (side=0;side<2U;++side) {
            uint32_t count=0;
            if (!read_memory(settings+side*0x458U+0x28U,&count,4U) || count>60U) return;
            for (slot=0;slot<count;++slot) {
                uint32_t role=0;
                if (!read_memory(settings+side*0x458U+0x140U+slot*4U,&role,4U)) return;
                if (role==28U) ++bench[side];
            }
        }
        hash=(hash^phase)*16777619U;hash=(hash^request)*16777619U;
        hash=(hash^policy)*16777619U;hash=(hash^bench[0])*16777619U;
        hash=(hash^bench[1])*16777619U;
        if (hash!=*previous_hash) {
            *previous_hash=hash;
            log_event("native_request phase=%lu requested=%lu settings_bench_roles=%lu/%lu C14_raw=%lu observer_writes=0 atomic_snapshot=0",
                (unsigned long)phase,(unsigned long)request,(unsigned long)bench[0],
                (unsigned long)bench[1],(unsigned long)policy);
        }
    }
}

static DWORD WINAPI worker(void *unused)
{
    unsigned int attempt;
    uint32_t previous_hash=0, request_hash=0;
    LONG64 batch_counts[BENCH_JOB_ADAPTER_COUNT]={0};
    (void)unused;
    if (!supported_image()) { log_event("not_installed unsupported_native_build"); return 0; }
    for (attempt=0; attempt<600U; ++attempt) {
        if (code_ready()) {
            const int state=safe_before_player_load();
            if (state < 0) { log_event("not_installed real_match_already_loaded restart_required=1"); return 0; }
            if (state == 1) {
                if (!install_limits()) return 0;
                for (;;) {
                    observe_loaded_lineup(&previous_hash);
                    observe_native_request(&request_hash);
                    observe_batches(batch_counts);
                    Sleep(1000U);
                }
            }
        }
        Sleep(200U);
    }
    log_event("not_installed code_not_ready_or_conflicting_patch");
    return 0;
}

__declspec(dllexport) unsigned int WINAPI Fifa16ModGetApiVersion(void)
{ return FIFA16_MOD_API_VERSION; }

__declspec(dllexport) BOOL WINAPI Fifa16ModStart(const char *mods_root)
{
    HANDLE thread;
    HMODULE pinned=NULL;
    char logs_dir[MAX_PATH];
    if (!mods_root || !mods_root[0]) return FALSE;
    if (InterlockedCompareExchange(&started,1,0) != 0) return TRUE;
    _snprintf_s(logs_dir,sizeof(logs_dir),_TRUNCATE,"%s\\..\\logs",mods_root);
    CreateDirectoryA(logs_dir,NULL);
    _snprintf_s(log_path,sizeof(log_path),_TRUNCATE,"%s\\bench_native12.log",logs_dir);
    log_event("candidate_start version=3 coherent_native_import_request_and_FCE_and_copy=12 bounded_native_resource_batches=192 no_UI_count_forgery=1");
    /* Registered runtime tables and counters may outlive a rolled-back
     * CALL whose in-flight native task still returns to our RX page. */
    if (!GetModuleHandleExA(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_PIN,
                          (LPCSTR)&started,&pinned)) {
        log_event("not_installed module_lifetime_pin_failed error=%lu",GetLastError());
        InterlockedExchange(&started,0);return FALSE;
    }
    thread=CreateThread(NULL,0,worker,NULL,0,NULL);
    if (!thread) { InterlockedExchange(&started,0); return FALSE; }
    CloseHandle(thread); return TRUE;
}

BOOL WINAPI DllMain(HINSTANCE instance,DWORD reason,LPVOID reserved)
{
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) DisableThreadLibraryCalls(instance);
    return TRUE;
}
