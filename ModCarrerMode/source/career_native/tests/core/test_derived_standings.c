#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "../../src/core/fce_runtime.h"
struct FceLiveSnapshot {FceModel model;};
static struct FceLiveSnapshot fixture;
static unsigned char *module;
static char runtime_log_dir[MAX_PATH];
static char log_path[MAX_PATH];
static volatile LONG generation=1;
static unsigned char fixture_iface[64],fixture_hub[64],fixture_connector[64],fixture_manager[16],clock_data[80],fixture_list[32];
static void *clocks[1];static unsigned simulations,refreshes;
FceLiveSnapshot *fce_runtime_cached_acquire(void){return &fixture;}
void fce_runtime_release(FceLiveSnapshot *s){(void)s;}
int fce_runtime_is_stable(void){return 1;}
void fce_runtime_request_refresh(void){++refreshes;}
static void report(const char *s,int ok,const FceModel *m,ULONGLONG time){(void)s;(void)ok;(void)m;(void)time;assert(0);}
static int copy_table(void *m,size_t offset,FceRawTable *t) {
    size_t i;unsigned char *p=calloc(2,64);assert(m==fixture_manager && offset==0x48);
    t->bytes=p;t->count=2;t->stride=64;
    for(i=0;i<2;++i){p[i*64+10]=1;p[i*64+0x12]=4;p[i*64+0x10]=(unsigned char)(i?22:12);memcpy(p+i*64+0x1c,"FCE_League_Stage",16);}return 1;
}
static void native_free(void *a,void *p,size_t n){(void)a;(void)n;free(p);}
static void *allocator_methods[4]={0,0,0,(void *)native_free};
static void **allocator=allocator_methods;
static void gather(void *c,int stage,void *out);
static void calculate(void *w,int stage,int date,void *out);
#define DERIVED_ALLOCATOR() (&allocator)
#define DERIVED_GATHER(c,s,v) gather(c,s,v)
#define DERIVED_CALCULATE(w,s,d,v) calculate(w,s,d,v)
#define DERIVED_PHASE_IS_LEAGUE(s) ((s)==12 || (s)==22)
#include "../../src/core/derived_standings.inc"
static void set(unsigned char *p,size_t offset,int v){memcpy(p+offset,&v,4);}
static void gather(void *c,int stage,void *out) {
    DerivedNativeVector *v=out;size_t i;assert(c==fixture_connector);
    v->begin=calloc(2,0x9c);v->end=v->capacity=v->begin+2*0x9c;
    for(i=0;i<2;++i){set(v->begin+i*0x9c,0,stage*10+(int)i);set(v->begin+i*0x9c,4,stage*100+(int)i);}
}
static void calculate(void *w,int stage,int date,void *out) {
    void **wr=w;DerivedNativeVector *v=out;size_t i;
    assert(wr[0]==fixture_connector && wr[1]==clock_data && wr[2]==fixture_hub);assert(date==fixture.model.date);++simulations;
    for(i=0;i<2;++i){set(v->begin+i*0x9c,0x74,stage==12?3:1);set(v->begin+i*0x9c,0x88,2);set(v->begin+i*0x9c,0x80,9);set(v->begin+i*0x9c,0x94,4);}
}
static void run(void){int i;for(i=0;i<4;++i){derived_next=0;derived_tick(fixture_iface);}}
int main(void) {
    FceCompNode nodes[]={{11,-1,3,100,0},{12,11,4,-1,0},{13,12,5,-1,0},{21,-1,3,200,0},{22,21,4,-1,0},{23,22,5,-1,0}};
    FceStanding standings[]={{120,13,1200,0,0,0,0,0,0,0},{121,13,1201,0,0,0,0,0,0,0},{220,23,2200,0,0,0,0,0,0,0},{221,23,2201,0,0,0,0,0,0,0}};
    FceDerivedStanding out[4];
    *(void **)(fixture_iface+0x18)=fixture_hub;*(void **)(fixture_hub+0x28)=fixture_connector;*(void **)(fixture_hub+0x20)=fixture_list;*(void **)(fixture_connector+0x18)=fixture_manager;
    clocks[0]=clock_data;*(void ***)(fixture_list+8)=clocks;*(void ***)(fixture_list+0x10)=clocks+1;*(int *)(clock_data+0x20)=5;
    fixture.model.nodes=nodes;fixture.model.node_count=6;fixture.model.standings=standings;fixture.model.standing_count=4;fixture.model.date=20260810;
    run();assert(simulations==2 && refreshes==1);assert(fce_runtime_derived_copy(out,4,20260810)==4);assert(out[0].standing.played==5 && out[2].standing.played==3);assert(out[0].home_gf+out[0].away_gf==13);
    run();assert(simulations==2);++generation;assert(fce_runtime_derived_copy(out,4,20260810)==0);
    fixture.model.date=20260811;run();assert(simulations==4 && fce_runtime_derived_copy(out,4,20260810)==0);
    standings[0].home_wins=standings[0].played=1;run();assert(simulations==5 && fce_runtime_derived_copy(out,4,20260811)==2);
    free(derived_rows);return 0;
}
