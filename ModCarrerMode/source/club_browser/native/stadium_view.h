#pragma once
#include "../../club_environment/room/native/motions.h"
#include "../../common/panorama_director.h"

namespace clubstadium {
inline bool acceptPadToggle(bool keyboardMovement,bool padButton,uint64_t now,uint64_t lastKeyboard){return padButton||(!keyboardMovement&&(!lastKeyboard||now-lastKeyboard>250));}
// Presentation only: no match, career, database or profile writes.
struct Input {float forward=0,side=0,yaw=0,pitch=0;bool sprint=false;};
struct View {
 int club=0;bool walking=false,ready=false;unsigned shot=36;float elapsed=0;
 float heading=0,tilt=0,steps=0,duration=52,heightLimit=11000,scale=1,gap=24,transition=3;
 uint64_t mask=panorama::allMotionsMask;
 panorama::Director director;panorama::Decision cinema;bool panoramaStarted=false;
 panorama::Vec position{0,170,0};
 void enter(int id){*this=View{};club=id;}
 panorama::Settings settings()const{panorama::Settings cfg;cfg.duration=duration;cfg.heightLimit=heightLimit;cfg.scale=scale;cfg.mask=mask;cfg.gap=gap;cfg.transition=transition;return cfg;}
 void nextShot(){cinema=director.begin(settings());panoramaStarted=true;shot=cinema.motion;elapsed=0;}
 void restartPanorama(){director.reset();nextShot();}
 bool ownsCamera()const{return ready&&(walking||cinema.active);}
 float opacity()const{return ready&&!walking?cinema.opacity:0.f;}
 void toggle(){if(!ready)return;walking=!walking;if(walking){position={0,170,0};heading=tilt=steps=0;}}
 void tick(float dt,const Input& input={},bool focused=true){
  if(!ready)return;
  // Automatic tours follow the normal director's clock, even in a background
  // window. Walking keeps the original foreground-only, bounded input step.
  if(!walking){if(!panoramaStarted)restartPanorama();cinema=director.tick(dt,true,settings());shot=cinema.motion;elapsed=cinema.progress*panorama::duration(shot,duration);return;}
  if(!focused)return;dt=std::clamp(dt,0.f,.06f);
  heading+=input.yaw;tilt=std::clamp(tilt+input.pitch,-1.3f,1.3f);
  float forward=std::clamp(input.forward,-1.f,1.f),side=std::clamp(input.side,-1.f,1.f);
  float length=std::sqrt(forward*forward+side*side);if(length>1){forward/=length;side/=length;}
  float travel=(input.sprint?650.f:340.f)*dt;
  // FIFA pitch length is along X. Start at centre, looking toward a goal.
  position.x+=travel*(std::cos(heading)*forward-std::sin(heading)*side);
  position.z+=travel*(std::sin(heading)*forward+std::cos(heading)*side);
  // Keep the visitor at ground level in the pitch/runoff area, out of stands.
  position.x=std::clamp(position.x,-5750.f,5750.f);position.z=std::clamp(position.z,-3900.f,3900.f);
  if(length>.01f)steps+=travel*.018f;else steps=0;
 }
 panorama::Pose pose()const{
  if(!walking)return panorama::sample(cinema.motion,cinema.progress,heightLimit,scale);
  auto eye=position;eye.y+=std::sin(steps)*1.5f;
  panorama::Vec direction{std::cos(heading)*std::cos(tilt),std::sin(tilt),std::sin(heading)*std::cos(tilt)};
  return {eye,eye+direction*1000.f,70};
 }
};
}
