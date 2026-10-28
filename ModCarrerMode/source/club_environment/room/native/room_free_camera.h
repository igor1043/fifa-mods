#pragma once
#include "room_cinema_r52.h"
namespace room_free {
struct Input {float forward=0,right=0,yaw=0,pitch=0;bool sprint=false;};
struct Walk {
 panorama::Vec position{0,165,750};float heading=3.14159265f,tilt=0;bool active=false;
 float stepPhase=0,stepAmount=0;panorama::Vec stepOffset{};
 static constexpr float walkingSpeed=170.f,runningSpeed=280.f;
 bool clear(panorama::Vec p,const room_cinema::Tour&t)const{
  if(!std::isfinite(p.x)||!std::isfinite(p.z)||p.x< -1100||p.x>710||p.z< -555||p.z>1705)return false;
  // Continuous body capsule, rather than four separated spheres: thin table
  // tops and stretcher rails must also block the space between those samples.
  for(const auto&b:t.obstacles){
   float dx=p.x-std::clamp(p.x,b.lo.x,b.hi.x),dz=p.z-std::clamp(p.z,b.lo.z,b.hi.z);
   float dy=b.lo.y>165.f?b.lo.y-165.f:b.hi.y<30.f?30.f-b.hi.y:0.f;
   if(dx*dx+dy*dy+dz*dz<23.f*23.f)return false;
  }
  return true;
 }
 bool enter(const panorama::Pose&from,const room_cinema::Tour&t){
  auto start=from.eye;start.y=165;
  if(!clear(start,t)){
   bool found=false;for(const auto&p:t.path){start=p.eye;start.y=165;if(clear(start,t)){found=true;break;}}
   if(!found){start={0,165,750};if(!clear(start,t))return false;}
  }
  position=start;heading=room_cinema::yaw(from);tilt=std::clamp(room_cinema::pitch(from),-1.25f,1.25f);
  stepPhase=stepAmount=0;stepOffset={};active=true;return true;
 }
 panorama::Pose pose()const{
  float c=std::cos(tilt);auto eye=position+stepOffset;
  return {eye,eye+panorama::Vec{std::sin(heading)*c,std::sin(tilt),std::cos(heading)*c}*1000.f,70};
 }
 panorama::Pose tick(Input input,float dt,const room_cinema::Tour&t){
  if(!active)return pose();dt=std::clamp(dt,0.f,.06f);
  if(!std::isfinite(input.yaw)||!std::isfinite(input.pitch)||!std::isfinite(input.forward)||!std::isfinite(input.right))return pose();
  // FIFA's camera-to-world matrix uses right = up x (eye - target).
  // Positive heading turns towards screen-left, so right-look subtracts yaw.
  heading=room_cinema::angle(heading-input.yaw);tilt=std::clamp(tilt+input.pitch,-1.25f,1.25f);
  float length=std::hypot(input.forward,input.right);if(length>1){input.forward/=length;input.right/=length;}
  const float speed=input.sprint?runningSpeed:walkingSpeed;
  const panorama::Vec right{-std::cos(heading),0,std::sin(heading)};
  auto delta=(panorama::Vec{std::sin(heading),0,std::cos(heading)}*input.forward+right*input.right)*(dt*speed);
  const auto previous=position;
  const int steps=(std::max)(1,int(std::ceil(std::hypot(delta.x,delta.z)/6.f)));delta=delta*(1.f/steps);
  for(int i=0;i<steps;++i){auto next=position;next.x+=delta.x;if(clear(next,t))position=next;next=position;next.z+=delta.z;if(clear(next,t))position=next;}
  // Visual footsteps follow actual travel, so pushing against a wall cannot
  // keep bobbing. Only the eye moves; collision/body height stays at 165 cm.
  const float travelled=std::hypot(position.x-previous.x,position.z-previous.z);
  if(dt>0){
   const bool moving=travelled>.005f;
   if(moving)stepPhase=std::fmod(stepPhase+travelled*6.28318530718f/(input.sprint?170.f:142.f),6.28318530718f);
   const float target=moving?std::clamp(travelled/(dt*walkingSpeed),0.f,input.sprint?1.15f:1.f):0.f;
   stepAmount+=(target-stepAmount)*(1.f-std::exp(-dt*14.f));
   if(stepAmount<.001f)stepAmount=0;
   stepOffset=right*(std::sin(stepPhase)*.32f*stepAmount);
   stepOffset.y=std::sin(stepPhase*2.f)*.9f*stepAmount;
  }
  return pose();
 }
};
}
