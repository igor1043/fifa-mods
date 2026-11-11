#pragma once
#include <array>
#include <cmath>
#include "../../room/native/room_spotlight_r79.h"
#include "../../../common/gallery_lights.h"
namespace gallery_light {
inline float safeIntensity(float value,float fallback=1.f){
 return std::isfinite(value)?std::clamp(value,.5f,3.f):fallback;
}
// Same SH basis, neutral fill and soft-cone response as the dressing room.
// Sources match this room's ceiling tracks and illuminated display shelves.
inline room_spotlight_r79::Result evaluate(float x,float y,float z,float power=1.35f){
 using namespace room_spotlight_r79;Result result;float sum=0,dx=0,dy=0,dz=0;
 auto source=[&](float lx,float ly,float lz){
  const float vx=lx-x,vy=ly-y,vz=lz-z,d2=vx*vx+vy*vy+vz*vz;
  if(d2<1||d2>=kRange*kRange)return;
  const float distance=std::sqrt(d2),cone=smooth(kOuterCos,kInnerCos,vy/distance);
  const float range=1-smooth(kRange*.68f,kRange,distance),energy=cone*range*range;
  sum+=energy;dx+=vx/distance*energy;dy+=vy/distance*energy;dz+=vz/distance*energy;
 };
 for(unsigned i=0;i<gallery_lights::count;++i){const auto&s=gallery_lights::sources[i];source(s.x,s.y,s.z);}
 result.energy=std::clamp(sum*power,0.f,2.2f);const float length=std::sqrt(dx*dx+dy*dy+dz*dz);
 if(length>1e-5f){result.x=dx/length;result.y=dy/length;result.z=dz/length;}return result;
}
inline std::array<float,28> coefficients(float x,float y,float z,float intensity=1.f){
 using namespace room_spotlight_r79;std::array<float,28> sh{};const auto spot=evaluate(x,y,z);
 for(int c=0;c<3;++c){const float tint=c==0?1.f:c==1?.99f:.97f;const int at=c*9;
  sh[at]=(1.15f+spot.energy*.35f)*tint/kInvSH0;
  sh[at+1]=spot.energy*.65f*spot.x*tint/kInvSH1;
  sh[at+2]=(.14f+spot.energy*.65f*spot.y)*tint/kInvSH1;
  sh[at+3]=spot.energy*.65f*spot.z*tint/kInvSH1;
 }
 const auto gain=safeIntensity(intensity);for(auto& value:sh)value*=gain;
 return sh;
}
}
