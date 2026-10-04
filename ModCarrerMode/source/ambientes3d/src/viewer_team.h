#pragma once
#include "viewer_pose_hooks.h"
#include <unordered_map>

namespace studio {
struct SceneActor {
    int player=0;
    size_t part_begin=0,part_end=0;
    Vec3 anchor={};
    Bounds bounds;
    std::vector<BonePoint>bones;
};

extern thread_local bool team_editing,team_apply_edits;
extern thread_local std::vector<ActorEdit>team_edits;
extern thread_local std::vector<SceneActor>scene_actors;
extern thread_local std::unordered_map<const fifa_player::Model*,std::vector<BonePoint>>team_bones;

// The generated adapter uses the existing formation/contact recipes unchanged.
fifa_player::Model assemble_editable_team(const std::vector<std::shared_ptr<const fifa_player::Model>>&,unsigned);
std::shared_ptr<fifa_player::Model>edit_team_pose(const fifa_player::Model&source,std::shared_ptr<fifa_player::Model>posed,bool crouching,const fifa_player::PoseContacts*,unsigned);
void register_team_actor(fifa_player::Model&scene,const fifa_player::Model&posed,size_t part_begin,float x,float z);
int room_actor_kind(const std::string&);
void reindex_room_actors(const fifa_player::Model&);

struct Ray {Vec3 origin={},direction={};};
Ray camera_ray(const Camera&,float viewport_width,float viewport_height,float mouse_x,float mouse_y);
int pick_actor(const fifa_player::Model&,const std::vector<SceneActor>&,const Ray&);
const ActorEdit*actor_edit(const std::vector<ActorEdit>&,int player);
}
