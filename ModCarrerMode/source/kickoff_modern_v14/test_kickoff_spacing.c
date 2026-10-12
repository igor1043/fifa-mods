#include <stdio.h>
#include <string.h>
#include "kickoff_spacing.h"
static int unchanged(uint32_t role,uint32_t side,uint32_t kicking_side,int special,float x,float y,float z) {
 float v[4]={x,y,z,17.0f},before[4];memcpy(before,v,sizeof(v));
 return !kickoff_space_other(role,side,kicking_side,special,v) && memcmp(before,v,sizeof(v))==0;
}
int main(void) {
 float v[4]={23.8244f,0.0f,-1.54077f,17.0f};
 if(!kickoff_space_other(18,0,0,0,v) || fabsf(hypotf(v[0],v[2])-33.6282f)>0.001f || v[0]<=0 || v[2]>=0 || v[3]!=17.0f)return 1;
 v[0]=-23.8244f;v[2]=1.54077f;
 if(!kickoff_space_other(18,1,1,0,v) || fabsf(hypotf(v[0],v[2])-33.6282f)>0.001f || v[0]>=0 || v[2]<=0)return 2;
 if(!unchanged(28,0,0,0,24,0,0) || !unchanged(18,1,0,0,-24,0,0) || !unchanged(18,0,0,1,24,0,0))return 3;
 if(!unchanged(18,0,0,0,31,0,0) || !unchanged(18,0,0,0,24,1,0) || !unchanged(18,0,0,0,NAN,0,0) || !unchanged(18,0,0,0,0,0,0))return 4;
 v[0]=0;v[1]=0;v[2]=30.01932f;
 if(!kickoff_space_other(18,0,0,0,v) || fabsf(v[2]-33.6282f)>0.001f)return 5;
 {
  float p[4]={0,0,0,1},target[4]={36.0888f,0,13.1232f,1},yaw=0;
  if(!kickoff_face_receiver(p,target,&yaw) || cosf(yaw)<0.9f || -sinf(yaw)<0.3f)return 6;
  target[0]=-target[0];target[2]=-target[2];
  if(!kickoff_face_receiver(p,target,&yaw) || cosf(yaw)>-0.9f || -sinf(yaw)>-0.3f)return 7;
  p[0]=4;if(kickoff_face_receiver(p,target,&yaw))return 8;
  p[0]=NAN;if(kickoff_face_receiver(p,target,&yaw))return 9;
 }
 {
  float p[4]={0,0,0,1},defence[4]={36.0888f,0,0,1},yaw=1;
  if(!kickoff_face_receiver(p,defence,&yaw) || fabsf(yaw)>0.001f)return 10;
  defence[0]=-defence[0];
  if(!kickoff_face_receiver(p,defence,&yaw) || cosf(yaw)>-0.999f || fabsf(sinf(yaw))>0.001f)return 11;
  p[0]=0.9f;p[2]=-5;
  if(kickoff_central_receiver_sign(p)!=1)return 12;
  p[0]=-0.9f;p[2]=5;
  if(kickoff_central_receiver_sign(p)!=-1)return 13;
  p[0]=36.0888f;if(kickoff_central_receiver_sign(p))return 14;
  p[0]=0.9f;p[1]=1;if(kickoff_central_receiver_sign(p))return 15;
  p[1]=0;p[2]=NAN;if(kickoff_central_receiver_sign(p))return 16;
 }
 {
  float charge=123;
  if(!kickoff_soften_charge(1,&charge) || fabsf(charge-0.75f)>0.00001f)return 17;
  if(!kickoff_soften_charge(0.4f,&charge) || fabsf(charge-0.3f)>0.00001f)return 18;
  charge=123;
  if(kickoff_soften_charge(0,&charge) || kickoff_soften_charge(-1,&charge) ||
     kickoff_soften_charge(1.01f,&charge) || kickoff_soften_charge(NAN,&charge) ||
     kickoff_soften_charge(INFINITY,&charge) || charge!=123)return 19;
 }
 {
  float velocity[4]={60,0,80,17},before=0,after=0;
  if(!kickoff_limit_velocity(velocity,&before,&after) || fabsf(before-100)>0.001f || fabsf(after-26.2464f)>0.001f ||
     fabsf(velocity[0]/velocity[2]-0.75f)>0.001f || velocity[3]!=17)return 20;
  velocity[0]=-12;velocity[1]=0;velocity[2]=16;
  if(!kickoff_limit_velocity(velocity,&before,&after) || fabsf(after-11)>0.001f || velocity[0]>=0 || velocity[2]<=0)return 21;
  velocity[0]=NAN;if(kickoff_limit_velocity(velocity,&before,&after))return 22;
  velocity[0]=0;velocity[2]=0;if(kickoff_limit_velocity(velocity,&before,&after))return 23;
 }
 puts("Spacing, mirrored defence facing, central pose guards and 25 percent charge reduction passed.");return 0;
}
