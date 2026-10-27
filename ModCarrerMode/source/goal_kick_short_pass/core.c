#include "core.h"
#include <string.h>
#include <limits.h>
static void put64(unsigned char *p,size_t n,uint64_t v){memcpy(p+n,&v,8);}
static void put32(unsigned char *p,size_t n,uint32_t v){memcpy(p+n,&v,4);}
static int range(int64_t d){return d>=INT32_MIN&&d<=INT32_MAX;}
int f16_bounds(uint64_t image,uint64_t min,uint64_t max,uint64_t *low,uint64_t *high){
 if(image<0x10000||image>0x00007fff00000000ULL||min<0x10000||max>0x00007fffffffffffULL||max<min+F16_SIZE)return 0;
 int64_t lo=min,hi=max-F16_SIZE+1;
 for(size_t i=0;i<f16_nclones;i++)for(size_t j=0;j<f16_clones[i].nfix;j++){
  const Clone *s=&f16_clones[i];const Fixup *f=&s->fix[j];
  int64_t anchor=image+f->target-s->offset-f->end;
  if(lo<anchor-INT32_MAX)lo=anchor-INT32_MAX;
  if(hi>anchor-(int64_t)INT32_MIN)hi=anchor-(int64_t)INT32_MIN;
 }
 int64_t anchor=image+0x4d41b44-0xd00;
 if(lo<anchor+INT32_MIN)lo=anchor+INT32_MIN;
 if(hi>anchor+INT32_MAX)hi=anchor+INT32_MAX;
 if(lo>hi)return 0;
 *low=lo;*high=hi;return 1;
}
int f16_build(unsigned char *out,uint64_t image,uint64_t allocation){
 uint64_t lo,hi;if(!out||!f16_bounds(image,0x10000,0x7fffffffffffULL,&lo,&hi)||allocation<lo||allocation>hi)return 0;
 memcpy(out,f16_kickoff,0x9000);memcpy(out+F16_GOAL,f16_goal,0x6000);
 for(size_t i=0;i<f16_nclones;i++){
  const Clone *s=&f16_clones[i];unsigned char *b=out+s->offset;
  if(s->offset+s->length>F16_SIZE)return 0;
  memcpy(b,s->bytes,s->length);
  for(size_t j=0;j<s->nfix;j++){
   const Fixup *f=&s->fix[j];int64_t d=image+f->target-(allocation+s->offset+f->end);
   if(f->pos+4>s->length||!range(d))return 0;
   put32(b,f->pos,(uint32_t)(int32_t)d);
  }
  for(size_t j=0;j<s->npatch;j++){
   const Patch *p=&s->patch[j];int64_t d=(int64_t)p->to-(s->offset+p->pos+5);
   if(p->span<5||p->pos+p->span>s->length||!range(d))return 0;
   memset(b+p->pos,0x90,p->span);b[p->pos]=(unsigned char)p->opcode;put32(b,p->pos+1,(uint32_t)(int32_t)d);
  }
 }
 const uint32_t k[][2]={{0x1008,0},{0x1010,0x3293d28},{0x1038,0x51cda20},{0x1040,0x526ca10},{0x1048,0x526c140},{0x1050,0x5270430},{0x1058,0x4d39de0},{0x1070,0x2314990},{0x1480,0x52e5860},{0x1520,0x4d3fa50},{0x1528,0x4d1d7d0},{0x1588,0x44ac6e0},{0x1590,0x4d3cc40}};
 for(size_t i=0;i<sizeof k/sizeof k[0];i++)put64(out,k[i][0],image+k[i][1]);
 put64(out,0x1488,allocation+0x8000);put32(out,0x1500,1);put32(out,0x1000,0);
 // Initial placement selects actual team, players and direction. No scene
 // heap addresses are retained at startup.
 put32(out,0x1658,1);put64(out,0x1620,(uintptr_t)f16_layout_init);put64(out,0x1628,(uintptr_t)f16_layout_target);
 put64(out,0x1660,(uintptr_t)f16_goalpass_adjust);put32(out,0x1668,75);
 const uint32_t g[][2]={{0x1040,0x517c430},{0x1048,0x4e4d890},{0x1050,0x3293d28},{0x1078,0x4d39de0},{0x1138,0x51c957e},{0x4000,0x50588d0},{0x4008,0x231c530},{0x4010,0x2314b88},{0x4018,0x2314990}};
 for(size_t i=0;i<sizeof g/sizeof g[0];i++)put64(out+F16_GOAL,g[i][0],image+g[i][1]);
 put64(out+F16_GOAL,0x1120,allocation+F16_GOAL+0x2489);put64(out+F16_GOAL,0x1128,allocation+F16_GOAL+0x2482);put32(out+F16_GOAL,0x1008,0);
 return 1;
}
int f16_plan(Hook *h,uint64_t image,uint64_t allocation){
 const uint32_t map[9][3]={{0x2330d20,0x51cda20,0},{0x2336288,0x526ca10,0x100},{0x2336290,0x526c140,0x200},{0x2336270,0x5270430,0x300},{0x233a3d0,0x52e5860,0xb00},{0x33ec880,0x517c430,F16_GOAL},{0x22fc908,0x4e4d890,F16_GOAL+0x300},{0x2330a60,0x51cce30,F16_GOAL+0x2000},{0x231c548,0x50588d0,F16_GOAL+0x3000}};
 memset(h,0,sizeof(Hook)*F16_HOOKS);
 for(size_t i=0;i<9;i++){h[i].rva=map[i][0];h[i].width=8;h[i].original=image+map[i][1];h[i].replacement=allocation+map[i][2];}
 int64_t d=allocation+0xd00-(image+0x4d41b44);if(!range(d))return 0;
 h[9].rva=0x4d41b40;h[9].width=4;h[9].original=(uint32_t)(0x4d3fa50-0x4d41b44);h[9].replacement=(uint32_t)(int32_t)d;
 h[10].rva=0x233ab28;h[10].width=8;h[10].original=image+0x5309b50;h[10].replacement=allocation+0x8200;
 return 1;
}
int f16_rollback(Hook *h,F16CAS cas,void *ctx){
 int ok=1;for(int i=F16_HOOKS-1;i>=0;i--)if(h[i].changed){
  // Leave a hook alone if another module has subsequently taken ownership.
  if(cas(ctx,h[i].rva,h[i].width,h[i].replacement,h[i].original))h[i].changed=0;else ok=0;
 }return ok;
}
int f16_publish(Hook *h,F16CAS cas,void *ctx){
 for(int i=0;i<F16_HOOKS;i++){
  if(!cas(ctx,h[i].rva,h[i].width,h[i].original,h[i].replacement)){f16_rollback(h,cas,ctx);return 0;}
  h[i].changed=1;
 }return 1;
}
