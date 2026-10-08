#ifndef BENCH_RENDER_PLAN_H
#define BENCH_RENDER_PLAN_H
#include <stdint.h>
#include <string.h>

typedef struct BenchRenderRoster {
    uint32_t count[2];
    uint32_t id[2][23];
    uint32_t role[2][23];
} BenchRenderRoster;
typedef struct BenchRenderPlan {
    uintptr_t owner;
    uint64_t sum[2], bits[2];
    uint32_t count[2], extra_count[2], extra[2][5];
    int valid;
} BenchRenderPlan;

/* Native render slots 30..53 contain substitutes, in a DIFFERENT order from
 * the team list. Freeze the five additional IDs at initial load. Keep that
 * decision through native substitutions, which change roles/order. Render
 * slots may be reused: the native SetPlayerList bench/starter flag, rather
 * than a slot number alone, determines whether this ID can be hidden. */
static __inline int bench_render_refresh(BenchRenderPlan *plan, uintptr_t owner,
                                        const BenchRenderRoster *roster)
{
    BenchRenderPlan next;
    unsigned int side, index, bench;
    memset(&next,0,sizeof(next)); next.owner=owner;
    if (!plan || !owner || !roster) return 0;
    for (side=0;side<2U;++side) {
        if (roster->count[side]<11U || roster->count[side]>23U) return 0;
        next.count[side]=roster->count[side];
        for (index=0;index<roster->count[side];++index) {
            const uint32_t id=roster->id[side][index];
            uint64_t mixed;
            unsigned int prior;
            if (!id || id>=10000000U || roster->role[side][index]>29U) return 0;
            for (prior=0;prior<index;++prior) if (roster->id[side][prior]==id) return 0;
            mixed=(uint64_t)id*0x9E3779B185EBCA87ULL;
            mixed^=mixed>>31; mixed*=0xC2B2AE3D27D4EB4FULL; mixed^=mixed>>29;
            next.sum[side]+=mixed; next.bits[side]^=mixed;
        }
    }
    if (plan->valid && plan->owner==owner &&
        memcmp(plan->sum,next.sum,sizeof(next.sum))==0 &&
        memcmp(plan->bits,next.bits,sizeof(next.bits))==0 &&
        memcmp(plan->count,next.count,sizeof(next.count))==0) return 1;
    for (side=0;side<2U;++side) {
        bench=0;
        for (index=0;index<roster->count[side];++index) if (roster->role[side][index]==28U) {
            if (bench>=12U) return 0;
            if (bench>=7U) next.extra[side][next.extra_count[side]++]=roster->id[side][index];
            ++bench;
        }
    }
    next.valid=1; *plan=next; return 1;
}
static __inline int bench_render_hide(const BenchRenderPlan *plan, unsigned int slot,
                                      int is_bench, int32_t id, int32_t side)
{
    unsigned int index;
    if (!plan || !plan->valid || !is_bench || slot<8U || slot>=54U || id<=0 || side<0 || side>1) return 0;
    for (index=0;index<plan->extra_count[side];++index)
        if (plan->extra[side][index]==(uint32_t)id) return 1;
    return 0;
}
#endif
