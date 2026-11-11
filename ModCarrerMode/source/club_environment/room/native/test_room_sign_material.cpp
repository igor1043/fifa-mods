#include "room_sign_material.h"
#include <cassert>
#include <cstring>
#include <iostream>
int main(){
 const char* matte="data/sceneassets/server16_dressing_room_v3/sign_aux_v1.rx3";
 const char* original="data/sceneassets/prop/prop_102_textures.rx3";
 for(const char* key:{"v3_fascia_left_0","v3_fascia_back_left","v3_fascia_right_1"})assert(!std::strcmp(roomComponentAuxTexture(key),matte));
 for(const char* key:{"jersey_0","shoe_7","balls","loading_slate","v3_feature_wall","v3_floor_crest","plate_10","v3_table_wood","medical_metal","cooler_glass"})assert(!std::strcmp(roomComponentAuxTexture(key),original));
 std::cout<<"PASS verified FIFA auxiliary maps on furnishings and native kits, dedicated fascia maps preserved\n";
}
