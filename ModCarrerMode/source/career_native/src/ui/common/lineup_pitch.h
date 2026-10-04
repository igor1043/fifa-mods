#pragma once
#include "../../screens/player/club_player_profile.h"
#include <algorithm>
#include <vector>

/* Read-only tactical slots, NOT preferred positions or a fixed club/formation.
 * Occupied lines share the available height; duplicates spread horizontally
 * without dropping a starter. Coordinates are normalized, attack at the top. */
namespace lineup_pitch {
struct Player {size_t row;float x,y;int line;};
inline int line(int slot) {
    if(slot==0)return 6;
    if(slot==1)return 5;
    if(slot>=2&&slot<=8)return 4;
    if(slot>=9&&slot<=11)return 3;
    if(slot>=12&&slot<=16)return 2;
    if(slot>=17&&slot<=22)return 1;
    if(slot>=23&&slot<=27)return 0;
    return -1;
}
inline std::vector<Player> layout(const std::vector<ClubPlayerRow>&rows) {
    std::vector<Player>out;std::vector<size_t>bands[7];
    if(rows.size()!=11)return out;
    for(size_t i=0;i<rows.size();++i) {
        int band=line(rows[i].squad_position);if(band<0)return {};
        bands[band].push_back(i);
    }
    int occupied=0;for(const auto&band:bands)if(!band.empty())++occupied;
    int rank=0;
    for(int band=0;band<7;++band)if(!bands[band].empty()) {
        auto&indices=bands[band];
        std::stable_sort(indices.begin(),indices.end(),[&](size_t a,size_t b){
            return club_profile::pitch_point(rows[a].squad_position).x<club_profile::pitch_point(rows[b].squad_position).x;
        });
        float y=occupied>1?.13f+.77f*rank/(occupied-1):.5f;
        float spread=std::min(.80f,.32f*float(indices.size()-1));
        for(size_t column=0;column<indices.size();++column) {
            float x=indices.size()>1?.5f+spread*(float(column)/(indices.size()-1)-.5f):.5f;
            out.push_back({indices[column],x,y,band});
        }
        ++rank;
    }
    return out;
}
}
