#pragma once
#include "../assets/fifa_player_assets.h"
namespace fifa_player {
Model build_new_experience_room(Assets&,const std::string&,const std::vector<std::shared_ptr<const Model>>&,const std::vector<ClubPlayerRow>&,const CoachAsset&,ClubRoomKind);
}
