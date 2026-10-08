#define WIN32_LEAN_AND_MEAN
#include <intrin.h>
#include "bench_render_adapter.h"
#include "bench_render_plan.h"
#include "bench_import_adapter.h"

typedef unsigned char (__fastcall *NativeLoad)(void *,const void *);
typedef void (__fastcall *NativeVisibility)(void *);
typedef void (__fastcall *NativeActivity)(void *,unsigned char);
static uintptr_t game_image;
static unsigned char *load_page;
static unsigned char load_patch[5];
static unsigned char *activity_page;
static unsigned char activity_patch[5];
static const unsigned char activity_original[5]={0xE8,0xAB,0x35,0x02,0x00};
static const unsigned char load_original[5]={0xE8,0xE8,0xD1,0x01,0x00};
static BOOL call_installed,show_installed,activity_installed;
static NativeLoad native_load;
static NativeVisibility native_show,native_hide;
static NativeActivity native_activity;
static SRWLOCK plan_lock=SRWLOCK_INIT;
static BenchRenderPlan plan;
static volatile LONG64 hidden_loads,hidden_shows,released_models;
static volatile LONG render_policy[58],hidden_by_us[58];
static volatile LONG active_by_update[58];
static volatile LONG64 extra_identity[58];

static BOOL read_value(uintptr_t address,void *out,SIZE_T size)
{
    SIZE_T received=0;
    return address && ReadProcessMemory(GetCurrentProcess(),(const void *)address,out,size,&received) && received==size;
}
static uintptr_t pointer_at(uintptr_t address)
{
    uintptr_t result=0; (void)read_value(address,&result,sizeof(result)); return result;
}

/* Game-thread callbacks only perform native renderer operations. The worker
 * never calls show/hide and never writes a player, ANT record or coordinate. */
static unsigned int render_slot(void *object)
{
    uintptr_t table[58];
    unsigned int index;
    if (!object || pointer_at((uintptr_t)object)!=game_image+0x2207230U ||
        !read_value(game_image+BENCH_RENDER_TABLE,table,sizeof(table))) return 58U;
    for (index=0;index<58U;++index) if (table[index]==(uintptr_t)object) return index;
    return 58U;
}
static BOOL hide_descriptor(unsigned int slot,const void *descriptor,unsigned char is_bench)
{
    BenchRenderRoster roster;
    unsigned char records[23U*0x330U];
    uintptr_t engine;
    int32_t identity[2];
    unsigned int index,side;
    BOOL hide=FALSE;
    /* R12b in this verified SetPlayerList loop means descriptor index >=
     * active-player count. The render object index itself can stay >=30
     * after a substitution, so it cannot be used as the bench/pitch flag. */
    if (!is_bench || slot<8U || slot>=54U || !descriptor ||
        !read_value((uintptr_t)descriptor+0x24U,&identity[0],4U) ||
        !read_value((uintptr_t)descriptor+0x10U,&identity[1],4U) ||
        identity[0]<=0 || identity[1]<0 || identity[1]>1) return FALSE;
    engine=pointer_at(game_image+0x37477B0U);
    if (!engine || pointer_at(engine)!=game_image+0x22D2CF0U) return FALSE;
    memset(&roster,0,sizeof(roster));
    for (side=0;side<2U;++side) {
        const uintptr_t team=engine+0xBC0U+side*0x4B60U;
        if (!read_value(team+0x4B40U,&roster.count[side],4U) ||
            roster.count[side]<11U || roster.count[side]>23U) return FALSE;
        if (!read_value(team+0x1F4U,records,roster.count[side]*0x330U)) return FALSE;
        for (index=0;index<roster.count[side];++index) {
            memcpy(&roster.id[side][index],records+index*0x330U,4U);
            memcpy(&roster.role[side][index],records+index*0x330U+0xCU,4U);
        }
    }
    AcquireSRWLockExclusive(&plan_lock);
    if (bench_render_refresh(&plan,engine,&roster))
        hide=bench_render_hide(&plan,slot,is_bench,identity[0],identity[1]);
    ReleaseSRWLockExclusive(&plan_lock);
    return hide;
}
static unsigned char __fastcall load_wrapper(void *object,const void *descriptor,unsigned char is_bench)
{
    const unsigned int slot=render_slot(object);
    BOOL hide=hide_descriptor(slot,descriptor,is_bench);
    int32_t id=0,side=-1;
    uint64_t identity=0;
    unsigned char result;
    if (descriptor && read_value((uintptr_t)descriptor+0x24U,&id,4U) &&
        read_value((uintptr_t)descriptor+0x10U,&side,4U) && id>0 && side>=0 && side<=1)
        identity=((uint64_t)(uint32_t)side<<32U)|(uint32_t)id;
    if (slot<58U) {
        const uint64_t previous=(uint64_t)InterlockedCompareExchange64(&extra_identity[slot],0,0);
        if (previous && previous!=identity) {
            InterlockedExchange64(&extra_identity[slot],0);InterlockedExchange(&active_by_update[slot],0);
        }
        if (hide && identity) {
            InterlockedExchange64(&extra_identity[slot],(LONG64)identity);
            /* Native match updates can activate a player without loading the
             * descriptor again. Do not restore an obsolete bench hide later. */
            if (InterlockedCompareExchange(&active_by_update[slot],0,0)) hide=FALSE;
        }
        InterlockedExchange(&render_policy[slot],hide ? 1 : 2);
        /* Undo only a hide applied by this mod. Restore it before the native
         * loader, so subsequent native cutscene/camera decisions still win. */
        if (!hide && InterlockedExchange(&hidden_by_us[slot],0)) {
            native_show(object);InterlockedIncrement64(&released_models);
        }
    }
    /* Preserve the original loader, descriptor and AL return value. */
    result=native_load(object,descriptor);
    if (result && hide) {
        native_hide(object); InterlockedExchange(&hidden_by_us[slot],1);
        InterlockedIncrement64(&hidden_loads);
    }
    return result;
}
static void __fastcall activity_wrapper(void *object,unsigned char inactive)
{
    const unsigned int slot=render_slot(object);
    const uintptr_t parameters=pointer_at((uintptr_t)object+0x18U);
    uint32_t previous_flags=0;
    const BOOL read_flags=read_value(parameters+0x80U,&previous_flags,4U);
    /* This is the unchanged native render-state setter used by the actual
     * match update (packet flag 0x40). It changes flags, not actor movement. */
    native_activity(object,inactive);
    if (slot<8U || slot>=54U || !read_flags ||
        !InterlockedCompareExchange64(&extra_identity[slot],0,0)) return;
    if (!inactive && ((previous_flags&8U)!=0U ||
        InterlockedCompareExchange(&active_by_update[slot],0,0))) {
        InterlockedExchange(&active_by_update[slot],1);
        InterlockedExchange(&render_policy[slot],2);
        if (InterlockedExchange(&hidden_by_us[slot],0)) {
            native_show(object);InterlockedIncrement64(&released_models);
        }
    } else if (inactive) {
        InterlockedExchange(&active_by_update[slot],0);
        InterlockedExchange(&render_policy[slot],1);
        if (!InterlockedExchange(&hidden_by_us[slot],1)) native_hide(object);
    }
}
static void __fastcall show_wrapper(void *object)
{
    const unsigned int slot=render_slot(object);
    if (slot<58U && InterlockedCompareExchange(&render_policy[slot],0,0)==1) {
        native_hide(object); InterlockedExchange(&hidden_by_us[slot],1);
        InterlockedIncrement64(&hidden_shows);
    } else native_show(object);
}

BOOL bench_render_code_ready(uintptr_t image)
{
    unsigned char bytes[16];
    static const unsigned char context[13]={0x48,0x8B,0x54,0x24,0x78,0x4C,0x89,0xF9,0xE8,0xE8,0xD1,0x01,0};
    static const unsigned char load_head[12]={0x55,0x57,0x41,0x56,0x48,0x8D,0xAC,0x24,0x40,0xFF,0xFF,0xFF};
    static const unsigned char visibility_head[11]={0x48,0x89,0x5C,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57};
    static const unsigned char bench_flag[13]={0x39,0xF3,0x41,0x0F,0x9D,0xD4,0x45,0x84,0xE4,0x74,0x0E,0x42,0x8D};
    static const unsigned char active_load_path[13]={0x45,0x84,0xE4,0x74,0x09,0x0F,0xB6,0x44,0x24,0x31,0x84,0xC0,0x74};
    static const unsigned char side_store[4]={0x45,0x89,0x4D,0x10};
    static const unsigned char id_store[4]={0x45,0x89,0x7D,0x24};
    static const unsigned char activity_context[15]={0x40,0xF6,0xC6,0x40,0x4C,0x89,0xF9,0x0F,0x9F,0xD2,0xE8,0xAB,0x35,0x02,0};
    static const unsigned char activity_head[12]={0x48,0x8B,0x41,0x18,0x84,0xD2,0x0F,0x84,0x9B,0,0,0};
    static const unsigned char activity_active[8]={0x83,0xA0,0x80,0,0,0,0xF7,0xC3};
    return image && read_value(image+0x4359826U,bytes,sizeof(activity_context)) && memcmp(bytes,activity_context,sizeof(activity_context))==0 &&
        read_value(image+BENCH_RENDER_ACTIVITY_NATIVE,bytes,sizeof(activity_head)) && memcmp(bytes,activity_head,sizeof(activity_head))==0 &&
        read_value(image+0x437CEDEU,bytes,sizeof(activity_active)) && memcmp(bytes,activity_active,sizeof(activity_active))==0 &&
        read_value(image+0x435FFA5U,bytes,sizeof(bench_flag)) && memcmp(bytes,bench_flag,sizeof(bench_flag))==0 &&
        read_value(image+0x436008DU,bytes,sizeof(active_load_path)) && memcmp(bytes,active_load_path,sizeof(active_load_path))==0 &&
        read_value(image+0x435655BU,bytes,sizeof(side_store)) && memcmp(bytes,side_store,sizeof(side_store))==0 &&
        read_value(image+0x435658DU,bytes,sizeof(id_store)) && memcmp(bytes,id_store,sizeof(id_store))==0 &&
        read_value(image+0x436009BU,bytes,sizeof(context)) && memcmp(bytes,context,sizeof(context))==0 &&
        read_value(image+BENCH_RENDER_LOAD_NATIVE,bytes,sizeof(load_head)) && memcmp(bytes,load_head,sizeof(load_head))==0 &&
        read_value(image+BENCH_RENDER_SHOW_NATIVE,bytes,sizeof(visibility_head)) && memcmp(bytes,visibility_head,sizeof(visibility_head))==0 &&
        read_value(image+BENCH_RENDER_HIDE_NATIVE,bytes,sizeof(visibility_head)) && memcmp(bytes,visibility_head,sizeof(visibility_head))==0 &&
        pointer_at(image+BENCH_RENDER_SHOW_SLOT)==image+BENCH_RENDER_SHOW_NATIVE &&
        pointer_at(image+BENCH_RENDER_SHOW_SLOT+8U)==image+BENCH_RENDER_HIDE_NATIVE;
}
static BOOL exchange_show(uintptr_t before,uintptr_t after)
{
    DWORD previous=0,ignored=0;
    uintptr_t seen;
    BOOL changed,restored;
    void *volatile *slot=(void *volatile *)(game_image+BENCH_RENDER_SHOW_SLOT);
    if (!VirtualProtect((void *)slot,8U,PAGE_READWRITE,&previous)) return FALSE;
    seen=(uintptr_t)InterlockedCompareExchangePointer(slot,(void *)after,(void *)before);
    changed=seen==before || seen==after;
    restored=VirtualProtect((void *)slot,8U,previous,&ignored);
    return changed && restored && pointer_at((uintptr_t)slot)==after;
}
BOOL bench_render_remove(void)
{
    BOOL ok=TRUE;
    if (activity_installed) {
        unsigned char current[5];
        if (read_value(game_image+BENCH_RENDER_ACTIVITY_CALL,current,5U) &&
            (memcmp(current,activity_original,5U)==0 ||
             bench_adapter_write_bytes(game_image+BENCH_RENDER_ACTIVITY_CALL,activity_patch,activity_original,5U))) activity_installed=FALSE;
        else ok=FALSE;
    }
    if (call_installed) {
        unsigned char current[5];
        if (read_value(game_image+BENCH_RENDER_LOAD_CALL,current,5U) &&
            (memcmp(current,load_original,5U)==0 ||
             bench_adapter_write_bytes(game_image+BENCH_RENDER_LOAD_CALL,load_patch,load_original,5U))) call_installed=FALSE;
        else ok=FALSE;
    }
    if (show_installed) {
        if (exchange_show((uintptr_t)&show_wrapper,game_image+BENCH_RENDER_SHOW_NATIVE)) show_installed=FALSE;
        else ok=FALSE;
    }
    /* Retain the RX leaf page if any callback could already be in flight.
     * The hosting DLL is pinned by Fifa16ModStart. */
    return ok;
}
BOOL bench_render_install(uintptr_t image,SIZE_T size)
{
    int64_t displacement;
    int32_t relative;
    DWORD old;
    uintptr_t target=(uintptr_t)&load_wrapper;
    if (load_page || call_installed || show_installed || !bench_render_code_ready(image)) return FALSE;
    game_image=image;
    native_load=(NativeLoad)(image+BENCH_RENDER_LOAD_NATIVE);
    native_show=(NativeVisibility)(image+BENCH_RENDER_SHOW_NATIVE);
    native_hide=(NativeVisibility)(image+BENCH_RENDER_HIDE_NATIVE);
    native_activity=(NativeActivity)(image+BENCH_RENDER_ACTIVITY_NATIVE);
    load_page=bench_adapter_near_page(image,size,image+BENCH_RENDER_LOAD_CALL);
    if (!load_page) return FALSE;
    displacement=(int64_t)(uintptr_t)load_page-(int64_t)(image+BENCH_RENDER_LOAD_CALL+5U);
    if (displacement<INT32_MIN || displacement>INT32_MAX) return FALSE;
    relative=(int32_t)displacement;
    load_patch[0]=0xE8; memcpy(load_patch+1,&relative,4U);
    /* Native CALL -> capture verified R12b into volatile R8d -> tail JMP to
     * the compiler-generated C callback. Preserve R12 and the native frame. */
    memcpy(load_page,"\x45\x0F\xB6\xC4\xFF\x25\x00\x00\x00\x00",10U);
    memcpy(load_page+10,&target,8U);
    if (!VirtualProtect(load_page,0x1000U,PAGE_EXECUTE_READ,&old) ||
        !FlushInstructionCache(GetCurrentProcess(),load_page,18U)) return FALSE;
    activity_page=bench_adapter_near_page(image,size,image+BENCH_RENDER_ACTIVITY_CALL);
    if (!activity_page) return FALSE;
    displacement=(int64_t)(uintptr_t)activity_page-(int64_t)(image+BENCH_RENDER_ACTIVITY_CALL+5U);
    if (displacement<INT32_MIN || displacement>INT32_MAX) return FALSE;
    relative=(int32_t)displacement;
    activity_patch[0]=0xE8;memcpy(activity_patch+1,&relative,4U);
    target=(uintptr_t)&activity_wrapper;
    memcpy(activity_page,"\xFF\x25\x00\x00\x00\x00",6U);memcpy(activity_page+6,&target,8U);
    if (!VirtualProtect(activity_page,0x1000U,PAGE_EXECUTE_READ,&old) ||
        !FlushInstructionCache(GetCurrentProcess(),activity_page,14U)) return FALSE;
    show_installed=TRUE;
    if (!exchange_show(image+BENCH_RENDER_SHOW_NATIVE,(uintptr_t)&show_wrapper)) goto fail;
    call_installed=TRUE;
    if (!bench_adapter_write_bytes(image+BENCH_RENDER_LOAD_CALL,load_original,load_patch,5U)) goto fail;
    activity_installed=TRUE;
    if (!bench_adapter_write_bytes(image+BENCH_RENDER_ACTIVITY_CALL,activity_original,activity_patch,5U)) goto fail;
    return TRUE;
fail:
    (void)bench_render_remove(); return FALSE;
}
void bench_render_reset_if_unloaded(void)
{
    uintptr_t engine=pointer_at(game_image+0x37477B0U);
    uint32_t count[2];
    if (engine && (pointer_at(engine)!=game_image+0x22D2CF0U ||
        !read_value(engine+0xBC0U+0x4B40U,&count[0],4U) ||
        !read_value(engine+0xBC0U+0x4B60U+0x4B40U,&count[1],4U) ||
        count[0]>1U || count[1]>1U)) return;
    {
        unsigned int index;
        AcquireSRWLockExclusive(&plan_lock); memset(&plan,0,sizeof(plan)); ReleaseSRWLockExclusive(&plan_lock);
        for (index=0;index<58U;++index) {
            InterlockedExchange(&render_policy[index],0);InterlockedExchange(&hidden_by_us[index],0);
            InterlockedExchange(&active_by_update[index],0);InterlockedExchange64(&extra_identity[index],0);
        }
    }
}
void bench_render_counters(LONG64 *loads,LONG64 *blocked_shows,LONG64 *released)
{
    *loads=InterlockedCompareExchange64(&hidden_loads,0,0);
    *blocked_shows=InterlockedCompareExchange64(&hidden_shows,0,0);
    *released=InterlockedCompareExchange64(&released_models,0,0);
}
#ifdef BENCH_RENDER_TEST
void bench_render_test_functions(BenchRenderLoadFn load,BenchRenderVisibilityFn show,BenchRenderVisibilityFn hide)
{ native_load=load; native_show=show; native_hide=hide; }
void *bench_render_test_load_page(void) { return load_page; }
void *bench_render_test_activity_page(void) { return activity_page; }
#endif
