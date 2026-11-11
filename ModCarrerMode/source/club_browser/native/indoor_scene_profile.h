#pragma once
#include "../../common/room_shadow_bridge.h"
#include "../../common/gallery_lights.h"
#include "../../club_environment/room/native/room_spotlight_r79.h"
namespace indoor_profile {
inline bool gallery(unsigned flags){return (flags&room_shadow_bridge::Gallery)!=0;}
inline float originX(unsigned flags){return gallery(flags)?-100000.f:100000.f;}
inline unsigned lightCount(unsigned flags){return gallery(flags)?gallery_lights::count:unsigned(room_spotlight_r79::kSources.size());}
inline room_spotlight_r79::Source source(unsigned index,unsigned flags){
 if(gallery(flags)){const auto&s=gallery_lights::sources[index];return {s.x,s.y,s.z};}
 return room_spotlight_r79::kSources[index];
}
// A visible gallery takes priority over a retained career backdrop.
struct Ownership {
 unsigned owner=0;
 bool accept(unsigned next,bool visible){
  if(next!=room_shadow_bridge::DressingRoom&&next!=room_shadow_bridge::TrophyGallery)return false;
  if(!visible){if(owner!=next)return false;owner=0;return true;}
  if(owner==room_shadow_bridge::TrophyGallery&&next==room_shadow_bridge::DressingRoom)return false;
  owner=next;return true;
 }
};
}
