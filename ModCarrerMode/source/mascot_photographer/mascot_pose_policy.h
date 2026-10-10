#pragma once
#include <math.h>
static float mascot_joint_distance(const float pose[31][16],unsigned int a,unsigned int b){
 const float x=pose[a][12]-pose[b][12],y=pose[a][13]-pose[b][13],z=pose[a][14]-pose[b][14];return sqrtf(x*x+y*y+z*z);
}
static bool mascot_pose_upright(const float pose[31][16]){
 const float thighA=mascot_joint_distance(pose,3,4),thighB=mascot_joint_distance(pose,7,8);
 const float legA=thighA+mascot_joint_distance(pose,4,5),legB=thighB+mascot_joint_distance(pose,8,9);
 if(thighA<1 || thighB<1 || legA<2 || legB<2)return false;
 const float foot=fminf(pose[5][13],pose[9][13]);
 if(pose[2][13]-foot<.78f*(legA+legB)*.5f)return false;
 if(pose[3][13]-pose[4][13]<.35f*thighA && pose[7][13]-pose[8][13]<.35f*thighB)return false;
 return true;
}
