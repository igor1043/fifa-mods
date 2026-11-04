#include "room_sign_material.h"
#include <cassert>
#include <cstring>
#include <iostream>
int main(){
 const char* sign="data/sceneassets/server16_dressing_room_v3/sign_aux_v1.rx3";
 const char* original="data/sceneassets/prop/prop_102_textures.rx3";
 for(const char* key:{"v3_fascia_left_0","v3_fascia_back_left","v3_fascia_right_1"})assert(!std::strcmp(roomComponentAuxTexture(key),sign));
 for(const char* key:{"jersey_0","v3_bay_wood","v3_feature_wall","v3_floor_crest","plate_10","v3_furniture_walnut","loading_slate","old_v3_fascia_left"})assert(!std::strcmp(roomComponentAuxTexture(key),original));
 std::cout<<"PASS isolated native sign-material bindings; other components unchanged\n";
}
