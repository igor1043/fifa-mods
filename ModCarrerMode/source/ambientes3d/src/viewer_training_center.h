#pragma once
#include "viewer_dressing_room.h"

namespace studio {
// Private viewer kinds; do not change the enum or assets in the game/Dev.
inline constexpr auto RoomGym=static_cast<fifa_player::ClubRoomKind>(9);
inline constexpr auto RoomTraining=static_cast<fifa_player::ClubRoomKind>(10);
struct TrainingResources {fifa_player::Model ball;std::string ball_asset;};
TrainingResources load_training_resources(fifa_player::Assets&,const fs::path&,int club);
fifa_player::Model build_training_center(const fifa_player::Model&club,const TrainingResources&,bool exterior);
void training_camera_view(Camera&,int environment,int view);
void open_training_center(fifa_player::Model&);
}
