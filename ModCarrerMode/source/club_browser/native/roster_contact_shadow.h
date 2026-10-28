#pragma once
// Contact meshes belong to the same native actor. Visibility, placement and
// retirement therefore cannot leave a shadow in an empty dressing room.
inline constexpr const wchar_t* contactShadowModel=L"data/sceneassets/server16_club_xi/player_contact_shadow_r1.rx3";
inline constexpr const wchar_t* contactShadowTexture=L"data/sceneassets/server16_dressing_room_20261022/contact_shadow_r51.rx3";
inline std::atomic<unsigned> contactShadowParts{0};
inline bool indoorContactAvailable(){
 std::error_code e;
 if(!std::filesystem::is_regular_file(game/contactShadowModel,e))return false;
 return std::filesystem::is_regular_file(game/contactShadowTexture,e);
}
inline void bindIndoorContact(std::ostringstream& s,bool single){
 contactShadowParts=0;
 if(!single||!roomView||!indoorContactAvailable())return;
 s<<"gr:AddAsset(o,lod,'room_contact_color','data/sceneassets/server16_dressing_room_20261022/contact_shadow_r51.rx3');"
    "gr:AddAsset(o,lod,'room_contact_aux','data/sceneassets/prop/prop_102_textures.rx3');";
 for(int i=1;i<=2;++i){
  const auto part="xi_floor_contact_"+std::to_string(i);
  s<<"do local part='"<<part<<"';gr:AddAsset(o,lod,part,'data/sceneassets/server16_club_xi/player_contact_shadow_r1.rx3');"
     "gr:CreateMaterialFromAttribulator(o,lod,part,'prop_material','prop_alpha');gr:SetSubMesh(o,lod,part,part);"
     "gr:SetTexture(o,lod,part,'textures','diffuseTexture','room_contact_color','shadow_cm');"
     "gr:SetTexture(o,lod,part,'textures','normalMap','room_contact_aux','_nm');"
     "gr:SetTexture(o,lod,part,'textures','coeffMap','room_contact_aux','_coeff');"
     "gr:SetTexture(o,lod,part,'textures','envDiffuseTexture','charcmn','envd_');"
     "gr:SetTexture(o,lod,part,'textures','envSpecTexture','charcmn','envs_');"
     "gr:SetTexture(o,lod,part,'textures','coverageMap','coverage','white_cm');end;";
 }
 contactShadowParts=2;
}
