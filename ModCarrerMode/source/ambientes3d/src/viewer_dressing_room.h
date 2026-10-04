#pragma once
#include "viewer_core.h"
#include <array>

namespace studio {
constexpr float dressing_entrance_shift=160; // Extra depth behind the tactical-analysis wall.
struct KitNumberSet {std::array<fifa_player::Texture,10>digits;std::array<bool,10>available={};std::string asset;};
struct DressingPrints {
    std::map<int,KitNumberSet>kits;
    std::map<int,KitPrintInfo>metadata;
    std::map<int,std::vector<uint8_t>>name_fonts;
    fifa_player::Model ball;
    std::string ball_asset,ball_league;
    int ball_league_id=0;
};
DressingPrints load_dressing_prints(fifa_player::Assets&,const fs::path&game,int club,int competition=0);
// Independent viewer-only dressing-room architecture. FIFA files are read-only.
fifa_player::Model build_dressing_room(
    const std::vector<std::shared_ptr<const fifa_player::Model>>& players,
    const std::vector<ClubPlayerRow>& roster,const DressingPrints&prints);
void dressing_camera_view(Camera&,int view);
void edit_dressing_objects(fifa_player::Model&,const std::vector<ObjectEdit>&);
void open_dressing_room(fifa_player::Model&);
}
