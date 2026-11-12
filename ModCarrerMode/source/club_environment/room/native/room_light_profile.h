#pragma once
#include "../../../native_mods/frontend_stadium/menu_page.h"

namespace room_light_profile {
// The unobstructed idle panorama needs less light than the career hub. Keep
// the room's shared SH, ceiling spots and shadow sources; attenuate their
// combined result rather than adding another screen overlay.
inline constexpr float idleGain=.72f;
inline float gain(bool background,frontend_stadium::PageKind page){
 return background&&page==frontend_stadium::PageKind::IdlePanorama?idleGain:1.f;
}
template<class Coefficients> Coefficients apply(Coefficients light,float gain){
 for(auto& coefficient:light)coefficient*=gain;
 return light;
}
}
