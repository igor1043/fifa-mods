#pragma once
#include <algorithm>
#include <array>
#include <cmath>

// Soft, position-aware ceiling spots projected into each room component's
// native FIFA spherical-harmonic buffer. Nothing touches stadium lighting.
namespace room_spotlight_r79 {
struct Result { float energy=0.f,x=0.f,y=1.f,z=0.f; };
struct Source { float x,y,z; };
inline constexpr float kInvSH0=0.2820947918f;
inline constexpr float kInvSH1=0.4886025119f;
inline constexpr float kOuterCos=0.50f; // 60 degree soft cone
inline constexpr float kInnerCos=0.78f; // 38 degree full-strength cone
inline constexpr float kRange=620.f;
inline constexpr std::array<Source,39> kSources={{
 // Emit below the lowest retained ceiling skin, avoiding blocked room lights.
 // Main room
 {-450.f,310.f,-300.f},
 {-450.f,310.f,240.f},
 {-450.f,310.f,780.f},
 {-450.f,310.f,1320.f},
 {30.f,310.f,-300.f},
 {30.f,310.f,240.f},
 {30.f,310.f,780.f},
 {30.f,310.f,1320.f},
 {450.f,310.f,-300.f},
 {450.f,310.f,240.f},
 {450.f,310.f,780.f},
 {450.f,310.f,1320.f},
 // Medical recovery wing
 // Additional ceiling row over the enlarged white treatment area.
 {-1360.f,315.f,1770.f},
 {-1360.f,315.f,2190.f},
 {-1360.f,315.f,2610.f},
 {-960.f,315.f,1710.f},
 {-960.f,315.f,1950.f},
 {-960.f,315.f,2190.f},
 {-960.f,315.f,2430.f},
 {-960.f,315.f,2670.f},
 {-720.f,315.f,1710.f},
 {-720.f,315.f,1950.f},
 {-720.f,315.f,2190.f},
 {-720.f,315.f,2430.f},
 {-720.f,315.f,2670.f},
 {-480.f,315.f,1710.f},
 {-480.f,315.f,1950.f},
 {-480.f,315.f,2190.f},
 {-480.f,315.f,2430.f},
 {-480.f,315.f,2670.f},
 // Coach office
 {-150.f,315.f,1710.f},
 {-150.f,315.f,2070.f},
 {-150.f,315.f,2430.f},
 {210.f,315.f,1710.f},
 {210.f,315.f,2070.f},
 {210.f,315.f,2430.f},
 {570.f,315.f,1710.f},
 {570.f,315.f,2070.f},
 {570.f,315.f,2430.f},
}};

inline float smooth(float lo,float hi,float x){
 const float t=std::clamp((x-lo)/(hi-lo),0.f,1.f);return t*t*(3.f-2.f*t);
}

inline Result evaluate(const float* sphere,float power){
 Result result;
 if(!sphere||!std::isfinite(power)||power<=0.f)return result;
 float x=sphere[0],y=sphere[1],z=sphere[2];
 if(!std::isfinite(x)||!std::isfinite(y)||!std::isfinite(z))return result;
 // Some FIFA renderables report their local room coordinates while others
 // carry the isolated scene origin applied by the room owner.
 if(x>50000.f){x-=100000.f;if(y>500.f)y-=1000.f;}
 if(std::abs(x)>1600.f||y< -20.f||y>450.f||z< -1000.f||z>3400.f)return result;
 float sum=0.f,dx=0.f,dy=0.f,dz=0.f;
 for(const auto&source:kSources){
  const float vx=source.x-x,vy=source.y-y,vz=source.z-z;
  const float d2=vx*vx+vy*vy+vz*vz;
  if(d2<1.f||d2>=kRange*kRange)continue;
  const float distance=std::sqrt(d2),cosDown=std::clamp(vy/distance,-1.f,1.f);
  const float cone=smooth(kOuterCos,kInnerCos,cosDown);
  const float range=1.f-smooth(kRange*.68f,kRange,distance);
  const float energy=cone*range*range;
  if(energy<=.0001f)continue;
  sum+=energy;dx+=vx/distance*energy;dy+=vy/distance*energy;dz+=vz/distance*energy;
 }
 result.energy=std::clamp(sum*power,0.f,2.2f);
 const float length=std::sqrt(dx*dx+dy*dy+dz*dz);
 if(length>1e-5f){result.x=dx/length;result.y=dy/length;result.z=dz/length;}
 return result;
}

inline Result addToSH(std::array<float,28>& sh,float power,const float* sphere){
 const Result spot=evaluate(sphere,power);
 for(int channel=0;channel<3;++channel){
  const float tint=channel==0?1.f:channel==1?.99f:.97f;
  const int at=channel*9;
  sh[at]+=spot.energy*.35f*tint/kInvSH0;
  sh[at+1]+=spot.energy*.65f*spot.x*tint/kInvSH1;
  sh[at+2]+=spot.energy*.65f*spot.y*tint/kInvSH1;
  sh[at+3]+=spot.energy*.65f*spot.z*tint/kInvSH1;
 }
 return spot;
}

inline std::array<float,28> coefficients(float ambient,float power,const float* sphere){
 std::array<float,28> sh{};
 if(!std::isfinite(ambient))ambient=.9f;
 ambient=std::clamp(ambient,.2f,1.2f);
 for(int channel=0;channel<3;++channel){
  const float tint=channel==0?1.f:channel==1?.99f:.97f;
  const int at=channel*9;
  // A soft ceiling hemisphere and reflected floor/wall fill. These static
  // room terms are isolated from stadium lighting and preserve useful contrast.
  const float ceilingFill=ambient*.14f;
  sh[at]=ambient*tint/kInvSH0;
  sh[at+2]=ceilingFill*tint/kInvSH1;
 }
 addToSH(sh,power,sphere);
 return sh;
}
}
