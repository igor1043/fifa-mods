#pragma once
#include "../assets/fifa_player_assets.h"
namespace stadium_preview {
/* format=3 means RGBA8 for the overlay only. No conversion/file writes. */
bool load(const std::string&root,const std::string&key,fifa_player::Texture&,std::string&source);
bool load_file(const std::string&path,fifa_player::Texture&);
}
