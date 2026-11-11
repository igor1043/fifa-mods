#pragma once
namespace clubs {
// Resting trigger noise must never change the camera while browsing players.
inline float rosterTriggerZoom(unsigned right,unsigned left){
 auto active=[](unsigned value){return value<=30?0.f:float(value-30)/225.f;};
 return active(right)-active(left);
}
inline constexpr float rosterFramingHeight=180.f;
}
