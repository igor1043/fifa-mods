#pragma once
#include "viewer_dressing_room.h"

namespace studio {
struct PressResources {
    DressingPrints prints;
    fifa_player::Model trophy;
    fifa_player::Texture competition_icon;
    std::vector<fifa_player::Texture>sponsors;
    std::vector<fifa_player::Model>crowd;
    int competition=0;
    std::string league_name,diagnostic;
};
PressResources load_press_resources(fifa_player::Assets&,const fs::path&game,int club,int competition);
fifa_player::Model build_press_room(const std::vector<std::shared_ptr<const fifa_player::Model>>&,
    const fifa_player::CoachAsset&,const PressResources&,const Settings&);
void press_camera_view(Camera&,int view);
void open_press_room(fifa_player::Model&);
}
