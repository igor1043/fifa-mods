#pragma once
#include <array>
#include <cmath>
#include <algorithm>
#include <cstdint>
namespace room_projection {
// Scene camera distances are in centimetres. Stadium clipping (~83 cm) hides
// nearby indoor geometry, independently of the camera's position or animation.
inline float nearPlane(float current,float farPlane){
 if(!std::isfinite(current)||!std::isfinite(farPlane)||current<=0||farPlane<=1000||current>=farPlane)return current;
 return (std::min)(current,5.f);
}
// Offsets relative to scene+0x40. Far clipping (+0x54) belongs to FIFA.
inline constexpr std::array<std::array<unsigned,2>,4> ownedRanges{{{{0,64}},{{0x48,8}},{{0x70,1}},{{0x7c,8}}}};
// A single projection owner serves the room tour, free walk and roster views.
// Roster rendering keeps ownership of its transform, never of this field.
struct BorrowedNear {
 uintptr_t scene=0;float original=0,written=0;
 template<class Read,class Write> void restore(uintptr_t current,Read read,Write write){
  float value=0;
  if(scene&&scene==current&&read(scene+0x90,&value,4)&&value==written)write(scene+0x90,&original,4);
  scene=0;
 }
 template<class Read,class Write> bool apply(uintptr_t current,Read read,Write write){
  if(scene&&scene!=current)restore(current,read,write);
  float value=0,farPlane=0;
  if(!current||!read(current+0x90,&value,4)||!read(current+0x94,&farPlane,4)||!std::isfinite(value)||!std::isfinite(farPlane)||value<=0||farPlane<=1000||value>=farPlane)return false;
  if(scene!=current||value!=written){scene=current;original=value;}
  written=nearPlane(value,farPlane);return write(current+0x90,&written,4);
 }
};
}
