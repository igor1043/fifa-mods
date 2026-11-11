#include "room_spotlight_r79.h"
#include <cassert>
#include <cmath>
#include <iostream>

int main(){
 float center[4]={100030.f,1100.f,780.f,30.f};
 assert(room_spotlight_r79::kSources.size()==36);
 for(const auto& light:room_spotlight_r79::kSources){
  float floorPoint[4]={100000+light.x,1010,light.z,0};
  assert(room_spotlight_r79::evaluate(floorPoint,1.35f).energy>0);
 }
 auto spot=room_spotlight_r79::evaluate(center,1.35f);
 assert(spot.energy>1.2f&&spot.energy<=1.36f);
 assert(spot.y>.98f&&std::abs(spot.x)<.05f&&std::abs(spot.z)<.05f);
 auto sh=room_spotlight_r79::coefficients(.9f,1.35f,center);
 for(float v:sh)assert(std::isfinite(v));
 assert(sh[2]>0.f&&sh[27]==0.f);
 float local[4]={30.f,100.f,780.f,30.f};
 auto localSpot=room_spotlight_r79::evaluate(local,1.35f);
 assert(std::abs(localSpot.energy-spot.energy)<.001f);
 float outside[4]={102000.f,1100.f,500.f,30.f};
 assert(room_spotlight_r79::evaluate(outside,1.35f).energy==0.f);
 float beyond[4]={100000.f,1100.f,5000.f,30.f};
 assert(room_spotlight_r79::evaluate(beyond,1.35f).energy==0.f);
 assert(room_spotlight_r79::evaluate(center,0.f).energy==0.f);
 std::cout<<"PASS room spotlight: soft ceiling cone, local/world coordinates, finite FIFA SH and zero spill outside room\n";
}
