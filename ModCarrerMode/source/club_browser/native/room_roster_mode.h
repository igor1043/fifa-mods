#pragma once
#include <atomic>
#include <cstring>
#include <array>
#include <algorithm>
#include <cmath>
namespace clubs {
inline bool isDressingRoomPage(const char* name){return name&&!std::strcmp(name,"game/screens/career/server16/DressingRoom");}
struct RoomRosterMode {
 std::atomic<int> club{0};
 bool open(const char* page,int career){if(!isDressingRoomPage(page)||career<=0||career>=500000)return false;club=career;return true;}
 void close(){club=0;}
 bool visible(const char* page,int career)const{return isDressingRoomPage(page)&&career>0&&club.load()==career;}
};
inline RoomRosterMode roomRosterMode;
struct RosterOrigin{float x,y,z;};
// Free floor in front of the central furniture, not the table's centre.
// Camera and actor must use the same origin, including on player changes.
inline RosterOrigin rosterOrigin(bool indoor){return indoor?RosterOrigin{100000.f,1000.f,530.f}:RosterOrigin{0,0,0};}
inline float rosterMinimumZoom(bool indoor){return indoor?.95f:.65f;}
// FIFA packs spherical harmonics as R[9], G[9], B[9], one pad float.
// Broad neutral ceiling fill plus a weak, fixed front/top key preserves form
// without camera-dependent light, emissive textures or excessive specular.
inline constexpr float rosterIndoorLightDefault=2.3f;
inline bool validRosterIndoorLight(float value){return std::isfinite(value)&&value>=.45f&&value<=3.f;}
inline std::array<float,28> rosterIndoorLight(float ambient){
 // These are linear irradiance units, not a display RGB value limited to 1.
 // Keep enough headroom for the native prop material's diffuse response.
 std::array<float,28> sh{};if(!std::isfinite(ambient))ambient=rosterIndoorLightDefault;ambient=std::clamp(ambient,.45f,3.f);
 for(int channel=0;channel<3;++channel){
  const float tint=channel==0?1.f:channel==1?.985f:.965f;
  sh[channel*9]=ambient*tint/.2820947918f;
  sh[channel*9+1]=ambient*.18f*tint/.4886025119f;
  sh[channel*9+2]=ambient*.11f*tint/.4886025119f;
 }
 return sh;
}
}
