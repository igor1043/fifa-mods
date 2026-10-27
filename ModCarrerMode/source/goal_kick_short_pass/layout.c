/* Photograph-inspired kickoff layout. Called only from the existing kickoff
 * initial/preparation clones. No player-frame writes and no goal-kick changes.
 * Runtime object reads fail closed; only private cache/target data is written.
 */
#include "core.h"
#include <string.h>
#include <math.h>
#include <limits.h>
#ifndef F16_LAYOUT_TEST
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

typedef struct { uint64_t player; float pos[5]; } Entry;
typedef struct {
 uint64_t team, first, second, generation;
 unsigned valid;
 Entry entries[11];
} Layout;
static Layout layout;
static uint64_t u64(const void *p,unsigned o){uint64_t v;memcpy(&v,(const char*)p+o,8);return v;}
static int i32(const void *p,unsigned o){int v;memcpy(&v,(const char*)p+o,4);return v;}
static float f32(const void *p,unsigned o){float v;memcpy(&v,(const char*)p+o,4);return v;}
static void putf(void *p,unsigned o,float v){memcpy((char*)p+o,&v,4);}
static void count(unsigned char *p,unsigned o){uint64_t n=u64(p,o)+1;memcpy(p+o,&n,8);}
static int read_object(uint64_t at,void *out,size_t n){
 if(at<0x10000 || at>0x00007fffffffffffULL-n)return 0;
#ifdef F16_LAYOUT_TEST
 extern int f16_layout_test_read(uint64_t,void*,size_t);
 return f16_layout_test_read(at,out,n);
#else
 SIZE_T got=0;
 return ReadProcessMemory(GetCurrentProcess(),(void*)(uintptr_t)at,out,n,&got)&&got==n;
#endif
}
static int bits(unsigned n){int c=0;for(;n;n&=n-1)c++;return c;}
static void position(Entry *e,float x,float z,float direction){
 e->pos[0]=x*direction;e->pos[1]=0;e->pos[2]=z*direction;e->pos[3]=0;
 e->pos[4]=atan2f(-e->pos[2],-e->pos[0]);
}

void F16_LAYOUT_ABI f16_layout_init(unsigned char *ctx){
 /* Clear before reading: a new restart can never reuse an old lineup. */
 int stage=1;
 layout.valid=0;
 if(i32(ctx,0x1000)!=1 || i32(ctx,0x1500)!=1 || i32(ctx,0x1658)!=1)return;
 unsigned char team[0x90], form[0x1210], world[0x60];
 uint64_t players[29], manager, formptr, table;
 Layout next={0};
 next.team=u64(ctx,0x1508);next.first=u64(ctx,0x1028);next.second=u64(ctx,0x1030);
 next.generation=u64(ctx,0x1608);
 if(!read_object(next.team,team,sizeof team))goto reject;
 stage=2;int side=i32(team,0x58);
 if(side<0 || side>1 || !read_object(u64(team,0x80),world,sizeof world) ||
    i32(world,0x58)!=side || i32(world,0x5c)!=side)goto reject;
 stage=3;manager=u64(team,0x38);formptr=u64(team,0x88);
 if(!read_object(manager+0x68,&table,8) || !read_object(table,players,sizeof players) ||
    !read_object(formptr,form,sizeof form))goto reject;
 stage=4;float direction=f32(form,0x98);
 if(u64(form,0x70)!=next.team || i32(form,0x94)!=side ||
    i32(form,0xc4)!=1 || i32(form,0xc8)!=1 || i32(form,0x268)!=11 ||
    (direction!=1 && direction!=-1))goto reject;
 int lines[11],columns[11],remaining[8],nr=0,gk=-1,first=-1,second=-1;
 unsigned seen=0;
 for(int i=0;i<11;i++){
  stage=10+i;int slot=side*18+i, row=i32(form,0x1190+slot*4);
  unsigned char ai[0x28];unsigned char inactive;
  if(row<0 || row>10 || (seen&(1u<<row)))goto reject;
  seen|=1u<<row;
  if(!read_object(players[slot]+0x88,ai,sizeof ai) ||
     !read_object(players[slot]+0x1f32,&inactive,1) || inactive ||
     u64(ai,0)!=next.team || i32(ai,0x20)!=slot)goto reject;
  unsigned record=0x270+row*0x160;
  lines[i]=i32(form,record+0x20);columns[i]=i32(form,record+0x24);
  if(lines[i]<-1 || lines[i]>5 || columns[i]<0 || columns[i]>6)goto reject;
  next.entries[i].player=players[slot];
  if(players[slot]==next.first)first=i;
  if(players[slot]==next.second)second=i;
  if(lines[i]==-1){if(gk!=-1)goto reject;gk=i;}
 }
 stage=30;
 if(first<0 || second<0 || first==second || gk<0 || gk==first || gk==second)goto reject;
 for(int i=0;i<11;i++)if(i!=gk && i!=first && i!=second){
  if(nr==8)goto reject;
  remaining[nr++]=i;
 }
 if(nr!=8)goto reject;
 /* Game units (~feet). Camera perspective is not a measured field survey.
  * The two off-camera wide positions are inferred from the visible shape.
  * Role/column matching keeps defenders deeper and wide roles on their side.
  * Pair and keeper are reserved; exact 8-way minimum-cost matching avoids
  * overlapping targets with different formations or reordered player slots.
  */
 static const struct {float x,z;int line,col;} spots[8]={
  {46,-17,1,4},{52,24,1,2},
  {30,-96,1,5},{30,96,1,1},
  {26,-22,2,4},
  {3,-34,3,5},{3,48,3,3},{3,76,3,1}
 };
 int costs[256],chosen[256];
 for(int i=0;i<256;i++){costs[i]=INT_MAX/4;chosen[i]=-1;}costs[0]=0;
 for(unsigned mask=0;mask<255;mask++){
  int p=remaining[bits(mask)];
  for(int s=0;s<8;s++)if(!(mask&(1u<<s))){
   int dl=lines[p]-spots[s].line,dc=columns[p]-spots[s].col;
   int cost=costs[mask]+90*dl*dl+20*dc*dc;
   unsigned m=mask|(1u<<s);
   if(cost<costs[m]){costs[m]=cost;chosen[m]=s;}
  }
 }
 unsigned mask=255;
 for(int n=7;n>=0;n--){
  int s=chosen[mask];if(s<0)goto reject;
  position(&next.entries[remaining[n]],spots[s].x,spots[s].z,direction);
  mask^=1u<<s;
 }
 position(&next.entries[gk],96,0,direction);
 position(&next.entries[first],0,0,direction);
 position(&next.entries[second],22,22,direction);
 /* The engine's existing pass solver still targets the receiver's live frame.
  * Synchronize placement/preparation/kick animation with the new diagonal. */
 memcpy(ctx+0x1060,next.entries[second].pos,16);
 putf(ctx,0x1530,next.entries[second].pos[4]);
 putf(ctx,0x1560,atan2f(next.entries[second].pos[2],next.entries[second].pos[0]));
 stage=0;memcpy(ctx+0x1650,&stage,4);next.valid=1;layout=next;count(ctx,0x1630);return;
reject:
 memcpy(ctx+0x1650,&stage,4);count(ctx,0x1638);
}

int F16_LAYOUT_ABI f16_layout_target(unsigned char *ctx,void *team,void *player,float *out){
 if(!layout.valid || i32(ctx,0x1000)!=1 || i32(ctx,0x1504)!=1 ||
    layout.team!=(uintptr_t)team || layout.team!=u64(ctx,0x1508) ||
    layout.generation!=u64(ctx,0x1608) || layout.first!=u64(ctx,0x1028) ||
    layout.second!=u64(ctx,0x1030) || (uintptr_t)player==layout.first ||
    (uintptr_t)player==layout.second)return 0;
 /* Do not follow cached heap pointers. Bridges pass live AI objects, and their
  * addresses are compared only; a complete generation is invalidated on init. */
 for(int i=0;i<11;i++)if(layout.entries[i].player==(uintptr_t)player){
  memcpy(out,layout.entries[i].pos,5*sizeof(float));return 1;
 }
 return 0;
}
