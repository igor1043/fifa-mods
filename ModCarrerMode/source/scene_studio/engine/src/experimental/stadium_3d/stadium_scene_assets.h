#pragma once
#include "../../render/assets/fifa_player_assets.h"
namespace stadium_scene {
struct Preview {std::shared_ptr<const fifa_player::Model>model;std::string name,location,key,source,error;int capacity=0,stadium=0;};
/* Owned, read-only bytes. Called only by an asset worker, never Present. */
Preview load(const std::string&root,int club,const std::string&preferred_key="");
Preview original(const std::string&root,int stadium);
}
