#include "room_spotlight_r79.h"
#include "room_light_profile.h"
#include <cassert>
#include <iostream>

int main(){
 using frontend_stadium::PageKind;
 // Only a room serving the idle panorama is attenuated. Leaving that page,
 // opening the room card or rendering another scene restores the base light.
 for(auto page:{PageKind::Transition,PageKind::Menu,PageKind::Hub,PageKind::IdlePanorama,
               PageKind::ClubBrowser,PageKind::PlayerCareer,PageKind::Other,
               PageKind::ManagerFace,PageKind::ManagerPreferences,PageKind::DressingRoom,PageKind::TrophyRoom}){
  assert(room_light_profile::gain(false,page)==1.f);
  assert(room_light_profile::gain(true,page)==(page==PageKind::IdlePanorama?.72f:1.f));
 }
 // Scale the completed light, including saturated spots, uniformly. Direction,
 // warm tint and the ratio of ambient fill to focused light stay intact.
 for(const auto& source:room_spotlight_r79::kSources){
  float sphere[4]={100000.f+source.x,1100.f,source.z,30.f};
  const auto base=room_spotlight_r79::coefficients(1.f,1.35f,sphere);
  const auto idle=room_light_profile::apply(base,room_light_profile::gain(true,PageKind::IdlePanorama));
  assert(room_light_profile::apply(base,room_light_profile::gain(true,PageKind::Hub))==base);
  assert(room_light_profile::apply(base,room_light_profile::gain(false,PageKind::DressingRoom))==base);
  for(unsigned i=0;i<base.size();++i)assert(std::isfinite(idle[i])&&std::abs(idle[i]-base[i]*.72f)<.000001f);
 }
 std::cout<<"PASS idle panorama light: 72% of shared room lighting; career hub, interactive room, light directions and shadow sources preserved\n";
}
