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
 puts("Kickoff spacing and mirrored kicker orientation toward receiver passed.");return 0;
}
