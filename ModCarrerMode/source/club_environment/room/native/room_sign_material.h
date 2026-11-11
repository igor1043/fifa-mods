#pragma once
#include <string>
// Preserve the verified FIFA normal/coefficient layout. Zero-filled generated
// coefficient maps are not interchangeable with these native material maps.
inline const char* roomComponentAuxTexture(const std::string& key){
 return key.rfind("v3_fascia_",0)==0
  ? "data/sceneassets/server16_dressing_room_v3/sign_aux_v1.rx3"
  : "data/sceneassets/prop/prop_102_textures.rx3";
}
