/* Reduce only the local ground-trajectory query's speed, before the original
 * engine solves it. No ball velocity, player frame, input, target or shared
 * attribute is written. All scene pointers are freshly checked via safe reads.
 */
#include "core.h"
#include <string.h>
#include <math.h>
#ifndef F16_LAYOUT_TEST
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif
static uint64_t q(const void *p,unsigned o){uint64_t v;memcpy(&v,(const char*)p+o,8);return v;}
static int i(const void *p,unsigned o){int v;memcpy(&v,(const char*)p+o,4);return v;}
static float f(const void *p,unsigned o){float v;memcpy(&v,(const char*)p+o,4);return v;}
static void pi(void *p,unsigned o,int v){memcpy((char*)p+o,&v,4);}
static void pf(void *p,unsigned o,float v){memcpy((char*)p+o,&v,4);}
static void count(void *p,unsigned o){uint64_t v=q(p,o)+1;memcpy((char*)p+o,&v,8);}
static int read_at(uint64_t a,void *p,size_t n){
 if(a<0x10000 || a>0x00007fffffffffffULL-n)return 0;
#ifdef F16_LAYOUT_TEST
 extern int f16_layout_test_read(uint64_t,void*,size_t);
 return f16_layout_test_read(a,p,n);
#else
 SIZE_T got=0;
 return ReadProcessMemory(GetCurrentProcess(),(void*)(uintptr_t)a,p,n,&got)&&got==n;
#endif
}
static int close_to(float x,float y,float tolerance){return isfinite(x)&&isfinite(y)&&fabsf(x-y)<=tolerance;}

void F16_LAYOUT_ABI f16_goalpass_adjust(unsigned char *ctx,void *subsystem,void *query,void *alternate){
 int percent=i(ctx,0x1668),state;
 if(i(ctx,0x1000)!=1 || i(ctx,F16_GOAL+0x1008)!=1 || percent<50 || percent>=100 ||
    !read_at(q(ctx,0x1010),&state,4) || state!=6)return;
 count(ctx,0x1670);
 int stage=10;
 unsigned char sub[0x8c4],kicker[0xb8],receiver[0xb8],team[0x90],form[0x19dc],geo[0x28];
 uint64_t image=q(ctx,0x1008),team_ptr,form_ptr,table,player;
 if(!read_at((uintptr_t)subsystem,sub,sizeof sub) || q(sub,0)!=image+0x233ab10 ||
    q(query,0)!=image+0x2314850||q(alternate,0)!=image+0x2314850)goto reject;
 /* Exclude lob, driven, through and special ground variants. A deliberately
  * held (>75%) power input retains the original stronger-pass calculation. */
 for(unsigned n=0x848;n<=0x84c;n++)if(sub[n])goto reject;
 stage=11;float power=f(sub,0x24);
 if(!isfinite(power)||power<0||power>0.75f)goto reject;
 stage=20;
 if(!read_at(q(sub,0x498),kicker,sizeof kicker)||!read_at(q(sub,0x10),receiver,sizeof receiver))goto reject;
 team_ptr=q(kicker,0x88);
 if(q(receiver,0x88)!=team_ptr || q(sub,0x498)==q(sub,0x10) ||
    !read_at(team_ptr,team,sizeof team))goto reject;
 int side=i(team,0x58),ks=i(kicker,0xa8),rs=i(receiver,0xa8),world_side;
 if(side<0||side>1||ks<side*18||ks>side*18+10||rs<side*18||rs>side*18+10||
    !read_at(q(team,0x80)+0x58,&world_side,4)||world_side!=side||
    !read_at(q(team,0x38)+0x68,&table,8)||
    !read_at(table+8*(unsigned)ks,&player,8)||player!=q(sub,0x498)||
    !read_at(table+8*(unsigned)rs,&player,8)||player!=q(sub,0x10))goto reject;
 stage=30;form_ptr=q(team,0x88);
 if(!read_at(form_ptr,form,sizeof form)||q(form,0x70)!=team_ptr||
    i(form,0x94)!=side||i(form,0xd0)!=side||i(form,0xc4)!=4||i(form,0xc8)!=1||
    i(form,0x268)!=11||form[0x19d8])goto reject;
 int kr=i(form,0x1190+ks*4),rr=i(form,0x1190+rs*4);
 if(kr<0||kr>10||rr<0||rr>10||kr==rr||i(form,0x270+kr*0x160+0x20)!=-1)goto reject;
 stage=40;
 int lo=-1,hi=-1,ncb=0;unsigned seen=0;
 for(int row=0;row<11;row++){
  unsigned off=0x270+row*0x160;int col=i(form,off+0x24);
  if(i(form,off+0x20)!=1||col<2||col>4)continue;
  if(seen&(1u<<col))goto reject;
  seen|=1u<<col;ncb++;
  if(lo<0||col<i(form,0x270+lo*0x160+0x24))lo=row;
  if(hi<0||col>i(form,0x270+hi*0x160+0x24))hi=row;
 }
 if(ncb<2||ncb>3||lo==hi||(rr!=lo&&rr!=hi)||
    i(form,0x270+lo*0x160+0x38)!=-1||i(form,0x270+hi*0x160+0x38)!=-1||
    i(form,0x270+lo*0x160+4)==i(form,0x270+hi*0x160+4)||
    i(form,0x270+rr*0x160+4)!=rs)goto reject;
 stage=50;
 float dir=f(form,0x98);
 if((dir!=1&&dir!=-1)||!read_at(q(form,0x58),geo,sizeof geo))goto reject;
 float half=f(geo,0xc)*0.5f,depth=f(geo,0x1c),width=f(geo,0x18)*0.5f,pdepth=f(geo,0x14);
 if(!isfinite(half)||half<140||half>210||!isfinite(depth)||depth<12||depth>24||
    !isfinite(width)||width<20||width>40||!isfinite(pdepth)||pdepth<40||pdepth>65)goto reject;
 float tx=dir*(half-depth-6),tz=dir*(width+6)*(rr==lo?1:-1);
 unsigned off=0x270+rr*0x160;
 if(!close_to(f(form,off+0x40),tx,0.5f)||!close_to(f(form,off+0x48),tz,0.5f)||
    !close_to(f(form,off+0xb0),tx,0.5f)||!close_to(f(form,off+0xb8),tz,0.5f))goto reject;
 stage=60;float pos[4];
 if(!read_at(q(receiver,0x48)+0x330,pos,sizeof pos)||
    !close_to(pos[0],tx,12)||!close_to(pos[2],tz,12)||!close_to(pos[1],0,5))goto reject;
 stage=70;
 float sx=f(query,0x10),sy=f(query,0x14),sz=f(query,0x18);
 float dx=f(query,0x20),dy=f(query,0x24),dz=f(query,0x28);
 if(!close_to(sx,dir*(half-depth*0.5f),depth*0.5f+8)||!close_to(sz,0,width+8)||
    !close_to(sy,0,5)||!close_to(dy,0,5)||!close_to(dx,pos[0],12)||!close_to(dz,pos[2],12)||
    dx*dir<half-pdepth||dx*dir>half||fabsf(dz)>width+18)goto reject;
 stage=80;
 float dist2=(dx-sx)*(dx-sx)+(dz-sz)*(dz-sz),speed=f(query,0x50);
 if(!isfinite(dist2)||dist2<9||dist2>75*75||!isfinite(speed)||speed<1||speed>300||f(alternate,0x50)!=speed)goto reject;
 float soft=speed*((float)percent/100.0f);
 pf(query,0x50,soft);
 pf(alternate,0x50,soft);
 pf(ctx,0x1680,speed);pf(ctx,0x1684,soft);pf(ctx,0x1688,sqrtf(dist2));pi(ctx,0x168c,rs);
 count(ctx,0x1678);stage=0;
reject:
 pi(ctx,0x166c,stage);
}
