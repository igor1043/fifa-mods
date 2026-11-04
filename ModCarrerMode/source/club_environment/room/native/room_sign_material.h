#pragma once
#include <string>
// Keep original material maps on jerseys, player models and other furnishings.
// Only the V3 upper sign planes receive flat normals and a matte coefficient.
inline const char* roomComponentAuxTexture(const std::string& key){
 return key.rfind("v3_fascia_",0)==0
  ? "data/sceneassets/server16_dressing_room_v3/sign_aux_v1.rx3"
  : "data/sceneassets/prop/prop_102_textures.rx3";
}
