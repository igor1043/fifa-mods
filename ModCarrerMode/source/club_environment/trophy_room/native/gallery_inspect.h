#pragma once
#include <array>
#include <algorithm>
#include <cmath>
#include "../../room/native/motions.h"
namespace gallery_inspect {
using Matrix=std::array<float,16>;
struct Controls {
 float yaw=0,tilt=0,zoom=0;
 void step(float turn,float lift,float magnify){
  if(std::isfinite(turn))yaw=std::remainder(yaw+turn,6.28318530718f);
  if(std::isfinite(lift))tilt=std::clamp(tilt+lift,-.45f,.65f);
  if(std::isfinite(magnify))zoom=std::clamp(zoom+magnify,-30.f,12.f);
 }
};
inline Matrix rotate(const Matrix& base,const float* center,float angle){
 Matrix result=base;const float c=std::cos(angle),s=std::sin(angle);
 for(unsigned col=0;col<3;++col){const auto at=col*4;result[at]=c*base[at]+s*base[at+2];result[at+2]=-s*base[at]+c*base[at+2];}
 const float x=base[12]-center[0],z=base[14]-center[2];result[12]=center[0]+c*x+s*z;result[14]=center[2]-s*x+c*z;return result;
}
// Aim the cup at the middle of the free viewport. UI panels use a centred
// 1600x900 canvas while the 3D camera covers the physical ultrawide viewport.
inline panorama::Pose frame(panorama::Pose p,float aspect){
 if(!std::isfinite(aspect)||aspect<=0)return p;
 auto forward=p.target-p.eye;const float distance=std::sqrt(panorama::dot(forward,forward));
 if(!panorama::unit(forward))return p;
 auto right=panorama::cross(forward,{0,1,0});if(!panorama::unit(right))return p;
 const float fit=std::min(1.f/1600,1.f/(900*aspect));
 const float screenX=.5f+(530.f-800)*fit;
 const float angle=-std::atan((screenX-.5f)*2*std::tan(p.fov*.00872664626f)*aspect);
 p.target=p.eye+(forward*std::cos(angle)+right*std::sin(angle))*distance;return p;
}
inline float triggerZoom(unsigned left,unsigned right){
 const auto axis=[](unsigned value){return value>30?float(std::min(value,255u)-30)/225.f:0.f;};
 return axis(left)-axis(right);
}
inline int slot(const float* center){
 const int row=int(std::round((center[2]+630.f)/90.f));if(row<0||row>=15||std::abs(center[2]-(-630.f+row*90.f))>3.f)return -1;
 return row+(center[0]<-100000.f?0:15);
}
}
