#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "bench_render_adapter.h"
#include "bench_render_plan.h"
#include "test_native_activity_bytes.h"

static unsigned int loads,shows,hides;
static unsigned char load_result=1;
static const void *last_descriptor;
extern unsigned char test_bench_render_load_bridge(void *,const void *,unsigned char,void *);
static unsigned char __fastcall mock_load(void *object,const void *descriptor)
{ (void)object; ++loads;last_descriptor=descriptor;return load_result; }
static void __fastcall mock_show(void *object)
{ uintptr_t p=*(uintptr_t *)((unsigned char *)object+0x18U);if (p) *(uint32_t *)(p+0x80U)&=~2U;++shows; }
static void __fastcall mock_hide(void *object)
{ uintptr_t p=*(uintptr_t *)((unsigned char *)object+0x18U);if (p) *(uint32_t *)(p+0x80U)|=2U;++hides; }
static void set_u32(unsigned char *where,uint32_t value) { memcpy(where,&value,4U); }
static void set_ptr(unsigned char *where,uintptr_t value) { memcpy(where,&value,8U); }
static void make_roster(BenchRenderRoster *roster,unsigned int delta)
{
    unsigned int side,index;
    memset(roster,0,sizeof(*roster));
    for (side=0;side<2;++side) {
        roster->count[side]=23;
        for (index=0;index<23;++index) {
            roster->id[side][index]=100U+side*1000U+index+delta;
            roster->role[side][index]=index<11U ? index : 28U;
        }
    }
}
static int test_plan(void)
{
    BenchRenderRoster roster;
    BenchRenderPlan plan={0},before;
    unsigned int side,index;
    make_roster(&roster,0);
    if (!bench_render_refresh(&plan,0x10000,&roster)) return 1;
    for (side=0;side<2;++side) {
        for (index=11;index<18;++index)
            if (bench_render_hide(&plan,37U,1,roster.id[side][index],side)) return 2;
        for (index=18;index<23;++index) {
            if (!bench_render_hide(&plan,30U,1,roster.id[side][index],side)) return 3;
            if (bench_render_hide(&plan,30U,0,roster.id[side][index],side) ||
                bench_render_hide(&plan,54U,1,roster.id[side][index],side) ||
                bench_render_hide(&plan,0U,1,roster.id[side][index],side)) return 4;
        }
    }
    before=plan;
    /* Simulate native substitution and roster reordering with the same IDs. */
    roster.role[0][18]=0; roster.role[0][0]=28;
    { uint32_t id=roster.id[0][18]; roster.id[0][18]=roster.id[0][11]; roster.id[0][11]=id; }
    if (!bench_render_refresh(&plan,0x10000,&roster) || memcmp(&plan,&before,sizeof(plan))) return 5;
    if (!bench_render_hide(&plan,39,1,118,0) || bench_render_hide(&plan,39,0,118,0) ||
        bench_render_hide(&plan,39,1,100,0)) return 6;
    make_roster(&roster,200);
    if (!bench_render_refresh(&plan,0x10000,&roster) || bench_render_hide(&plan,39,1,118,0) ||
        !bench_render_hide(&plan,39,1,318,0)) return 7;
    before=plan;roster.id[0][0]=0;
    if (bench_render_refresh(&plan,0x10000,&roster) || memcmp(&plan,&before,sizeof(plan))) return 8;
    if (bench_render_hide(&plan,30,1,318,2) || bench_render_hide(&plan,30,1,-1,0)) return 9;
    make_roster(&roster,0);roster.count[0]=roster.count[1]=18;
    if (!bench_render_refresh(&plan,0x10000,&roster) || plan.extra_count[0] || plan.extra_count[1]) return 10;
    puts("Renderer plan: seven native IDs preserved per side; shuffled RNA slots, field/referee exclusion, substitutions, match changes and invalid input verified.");
    return 0;
}
static int test_callbacks(void)
{
    const SIZE_T image_size=0x4380000U;
    unsigned char *image=(unsigned char *)VirtualAlloc(NULL,image_size,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    unsigned char *engine=(unsigned char *)VirtualAlloc(NULL,0xB000U,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    unsigned char objects[7][40]={{0}};
    unsigned char parameters[7][0x900]={{0}};
    BenchRenderRoster roster;
    void *load;
    typedef void (__fastcall *ActivityFn)(void *,unsigned char);
    ActivityFn activity,original_activity;
    unsigned char descriptor[0x4B0]={0};
    BenchRenderVisibilityFn show;
    unsigned int side,index;
    uintptr_t show_original=(uintptr_t)image+BENCH_RENDER_SHOW_NATIVE;
    static const unsigned char context[13]={0x48,0x8B,0x54,0x24,0x78,0x4C,0x89,0xF9,0xE8,0xE8,0xD1,0x01,0};
    static const unsigned char load_head[12]={0x55,0x57,0x41,0x56,0x48,0x8D,0xAC,0x24,0x40,0xFF,0xFF,0xFF};
    static const unsigned char visibility_head[11]={0x48,0x89,0x5C,0x24,0x10,0x48,0x89,0x74,0x24,0x18,0x57};
    static const unsigned char bench_flag[13]={0x39,0xF3,0x41,0x0F,0x9D,0xD4,0x45,0x84,0xE4,0x74,0x0E,0x42,0x8D};
    static const unsigned char active_load_path[13]={0x45,0x84,0xE4,0x74,0x09,0x0F,0xB6,0x44,0x24,0x31,0x84,0xC0,0x74};
    static const unsigned char activity_context[15]={0x40,0xF6,0xC6,0x40,0x4C,0x89,0xF9,0x0F,0x9F,0xD2,0xE8,0xAB,0x35,0x02,0};
    if (!image || !engine) return 11;
    memcpy(image+0x436009BU,context,sizeof(context));
    memcpy(image+BENCH_RENDER_LOAD_NATIVE,load_head,sizeof(load_head));
    memcpy(image+BENCH_RENDER_SHOW_NATIVE,visibility_head,sizeof(visibility_head));
    memcpy(image+BENCH_RENDER_HIDE_NATIVE,visibility_head,sizeof(visibility_head));
    memcpy(image+0x435FFA5U,bench_flag,sizeof(bench_flag));
    memcpy(image+0x436008DU,active_load_path,sizeof(active_load_path));
    memcpy(image+0x435655BU,"\x45\x89\x4D\x10",4U);
    memcpy(image+0x435658DU,"\x45\x89\x7D\x24",4U);
    memcpy(image+0x4359826U,activity_context,sizeof(activity_context));
    memcpy(image+BENCH_RENDER_ACTIVITY_NATIVE,native_activity_instructions,sizeof(native_activity_instructions));
    { DWORD old;
      if (!VirtualProtect(image+0x437C000U,0x1000U,PAGE_EXECUTE_READ,&old) ||
          !FlushInstructionCache(GetCurrentProcess(),image+BENCH_RENDER_ACTIVITY_NATIVE,sizeof(native_activity_instructions))) return 24;
    }
    set_ptr(image+BENCH_RENDER_SHOW_SLOT,show_original);
    set_ptr(image+BENCH_RENDER_SHOW_SLOT+8U,(uintptr_t)image+BENCH_RENDER_HIDE_NATIVE);
    /* A conflicting instruction must reject installation without mutations. */
    image[BENCH_RENDER_LOAD_CALL]^=1;
    if (bench_render_code_ready((uintptr_t)image) || bench_render_install((uintptr_t)image,image_size) ||
        *(uintptr_t *)(image+BENCH_RENDER_SHOW_SLOT)!=show_original) return 12;
    image[BENCH_RENDER_LOAD_CALL]^=1;
    if (!bench_render_code_ready((uintptr_t)image) || !bench_render_install((uintptr_t)image,image_size)) return 13;
    bench_render_test_functions(mock_load,mock_show,mock_hide);
    set_ptr(image+0x37477B0U,(uintptr_t)engine);set_ptr(engine,(uintptr_t)image+0x22D2CF0U);
    make_roster(&roster,0);
    for (side=0;side<2;++side) {
        unsigned char *team=engine+0xBC0U+side*0x4B60U;
        set_u32(team+0x4B40U,23);
        for (index=0;index<23;++index) {
            set_u32(team+0x1F4U+index*0x330U,roster.id[side][index]);
            set_u32(team+0x200U+index*0x330U,roster.role[side][index]);
        }
    }
    for (index=0;index<7;++index) {
        set_ptr(objects[index],(uintptr_t)image+0x2207230U);
        set_ptr(objects[index]+0x18U,(uintptr_t)parameters[index]);
        set_u32(parameters[index]+0x80U,0x11U);
    }
    /* Original reserve deliberately occupies RNA slot 37; extra occupies 30. */
    set_ptr(image+BENCH_RENDER_TABLE+37U*8U,(uintptr_t)objects[0]);
    set_u32(image+BENCH_RENDER_IDENTITIES+37U*8U,111);set_u32(image+BENCH_RENDER_IDENTITIES+37U*8U+4U,0);
    set_ptr(image+BENCH_RENDER_TABLE+30U*8U,(uintptr_t)objects[1]);
    set_u32(image+BENCH_RENDER_IDENTITIES+30U*8U,118);set_u32(image+BENCH_RENDER_IDENTITIES+30U*8U+4U,0);
    set_ptr(image+BENCH_RENDER_TABLE+8U*8U,(uintptr_t)objects[2]);
    set_u32(image+BENCH_RENDER_IDENTITIES+8U*8U,118);set_u32(image+BENCH_RENDER_IDENTITIES+8U*8U+4U,0);
    set_ptr(image+BENCH_RENDER_TABLE+54U*8U,(uintptr_t)objects[3]);
    set_ptr(image+BENCH_RENDER_TABLE+53U*8U,(uintptr_t)objects[4]);
    set_u32(image+BENCH_RENDER_IDENTITIES+53U*8U,1122);set_u32(image+BENCH_RENDER_IDENTITIES+53U*8U+4U,1);
    load=bench_render_test_load_page();
    activity=(ActivityFn)bench_render_test_activity_page();
    original_activity=(ActivityFn)(image+BENCH_RENDER_ACTIVITY_NATIVE);
    show=*(BenchRenderVisibilityFn *)(image+BENCH_RENDER_SHOW_SLOT);
    set_u32(descriptor+0x24U,111);set_u32(descriptor+0x10U,0);
    if (!test_bench_render_load_bridge(objects[0],descriptor,1,load) || loads!=1 || hides!=0 || last_descriptor!=descriptor) return 14;
    set_u32(descriptor+0x24U,118);
    if (!test_bench_render_load_bridge(objects[1],descriptor,1,load) || loads!=2 || hides!=1) return 15;
    if (!test_bench_render_load_bridge(objects[2],descriptor,0,load) || hides!=1) return 16;
    show(objects[0]);show(objects[2]);show(objects[3]);
    if (shows!=3 || hides!=1) return 17;
    set_u32(descriptor+0x24U,1122);set_u32(descriptor+0x10U,1);
    if (!test_bench_render_load_bridge(objects[4],descriptor,1,load) || hides!=2) return 18;
    show(objects[1]);show(objects[4]);
    if (shows!=3 || hides!=4) return 21;
    /* Critical case: FIFA reuses the SAME RNA bench slot/object for the
     * substituted player. Source roles deliberately still say reserve. */
    set_u32(descriptor+0x24U,118);set_u32(descriptor+0x10U,0);
    if (!test_bench_render_load_bridge(objects[1],descriptor,0,load) || hides!=4 || shows!=4) return 22;
    show(objects[1]);
    if (shows!=5 || hides!=4) return 23;
    load_result=0;
    if (test_bench_render_load_bridge(objects[1],descriptor,0,load)!=0 || hides!=4 || loads!=6) return 19;
    /* Reproduce the ACTUAL failed v6 flow: no descriptor reload when the
     * reserve enters. The native packet changes inactive true -> false. */
    load_result=1;
    if (!test_bench_render_load_bridge(objects[1],descriptor,1,load) || hides!=5) return 25;
    activity(objects[1],1);
    if (*(uint32_t *)(parameters[1]+0x80U)!=0x1BU) return 26;
    activity(objects[1],0);
    if (*(uint32_t *)(parameters[1]+0x80U)!=0x11U || shows!=6 || hides!=5) return 27;
    show(objects[1]);
    if (shows!=7 || hides!=5 || *(uint32_t *)(parameters[1]+0x80U)!=0x11U) return 28;
    /* A later obsolete bench descriptor must not make the active model
     * invisible again; source roles are still unchanged at this point. */
    if (!test_bench_render_load_bridge(objects[1],descriptor,1,load) || hides!=5) return 29;
    /* The seven original models follow the exact unwrapped native setter. */
    memcpy(parameters[2],parameters[0],sizeof(parameters[0]));
    activity(objects[0],1);original_activity(objects[2],1);
    if (memcmp(parameters[0],parameters[2],sizeof(parameters[0])) || shows!=7 || hides!=5) return 30;
    activity(objects[0],0);original_activity(objects[2],0);
    if (memcmp(parameters[0],parameters[2],sizeof(parameters[0])) || shows!=7 || hides!=5) return 31;
    /* Apply the same activation case to the other side/additional ID. */
    activity(objects[4],1);activity(objects[4],0);
    if (*(uint32_t *)(parameters[4]+0x80U)!=0x11U || shows!=8 || hides!=5) return 32;
    activity(objects[1],1);
    if (*(uint32_t *)(parameters[1]+0x80U)!=0x1BU || hides!=6) return 33;
    activity(objects[1],1);
    if (hides!=6) return 34;
    /* Missed opening descriptor: the first Show arrives without a bench
     * load classification. Never hide an active extra, even with stale role. */
    set_ptr(image+BENCH_RENDER_TABLE+31U*8U,(uintptr_t)objects[5]);
    set_u32(image+BENCH_RENDER_IDENTITIES+31U*8U,119);
    set_u32(image+BENCH_RENDER_IDENTITIES+31U*8U+4U,0);
    show(objects[5]);
    if(shows!=9 || hides!=6)return 35;
    set_u32(parameters[5]+0x80U,0x19U);
    show(objects[5]);
    if(shows!=9 || hides!=7 || *(uint32_t *)(parameters[5]+0x80U)!=0x1BU)return 36;
    activity(objects[5],0);show(objects[5]);
    if(shows!=11 || hides!=7 || *(uint32_t *)(parameters[5]+0x80U)!=0x11U)return 37;
    /* A false opening bench flag also recovers after the native load, but
     * subsequent real activation still releases the SAME reused RNA model. */
    set_ptr(image+BENCH_RENDER_TABLE+32U*8U,(uintptr_t)objects[6]);
    set_u32(image+BENCH_RENDER_IDENTITIES+32U*8U,120);
    set_u32(image+BENCH_RENDER_IDENTITIES+32U*8U+4U,0);
    set_u32(parameters[6]+0x80U,0x19U);
    set_u32(descriptor+0x24U,120);set_u32(descriptor+0x10U,0);
    if(!test_bench_render_load_bridge(objects[6],descriptor,0,load) || hides!=8)return 38;
    activity(objects[6],0);
    if(shows!=12 || hides!=8 || *(uint32_t *)(parameters[6]+0x80U)!=0x11U)return 39;
    if (!bench_render_remove() ||
        memcmp(image+BENCH_RENDER_LOAD_CALL,context+8,5U) ||
        memcmp(image+BENCH_RENDER_ACTIVITY_CALL,activity_context+10,5U) ||
        *(uintptr_t *)(image+BENCH_RENDER_SHOW_SLOT)!=show_original) return 20;
    puts("Native renderer adapter: v6 cases retained; ACTUAL 262-byte native SetInactive executed via RX callback, activation without load releases hidden bit 0x13 -> 0x11, both sides covered, later stale descriptor cannot re-hide active model, originals match native memory exactly, rollback restores both CALLs/vtable.");
    VirtualFree(engine,0,MEM_RELEASE);VirtualFree(image,0,MEM_RELEASE);
    return 0;
}
int main(void)
{
    int result=test_plan();
    if (!result) result=test_callbacks();
    if (result) fprintf(stderr,"renderer adapter test failed: %d\n",result);
    return result;
}
