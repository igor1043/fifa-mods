#pragma once
#include "viewer_pose_hooks.h"
#include "ufbx.h"
namespace studio {
struct ImportedBone {std::string name;DirectX::XMFLOAT4X4 bind={},animated={};Vec3 bind_position={},position={};int parent=-1;};
class FbxClip {
    std::shared_ptr<ufbx_scene>scene_;
public:
    fs::path file;
    std::vector<std::string>names,takes;
    double start=0,duration=0;
    int take=0;
    void load(const fs::path&);
    void select_take(int);
    std::vector<ImportedBone>sample(double)const;
    bool valid()const{return bool(scene_);}
};
struct AnimationJoint {std::string name;DirectX::XMFLOAT4X4 bind={},animated={};Vec3 root_translation={},bind_direction={},bind_secondary={};std::string child;};
extern thread_local std::vector<AnimationJoint>animation_frame;
extern thread_local std::map<int,float>manual_floors;
extern thread_local bool capture_manual_floor;
void retarget(const fifa_player::Model&,const std::vector<DirectX::XMFLOAT4X4>&rest,std::vector<DirectX::XMFLOAT4X4>&pose);
float animation_floor(const fifa_player::Model&,float computed);
std::vector<BoneMapping>auto_map(const std::vector<std::string>&targets,const std::vector<std::string>&sources);
std::vector<AnimationJoint>retarget_frame(const std::vector<ImportedBone>&,const std::vector<BoneMapping>&,bool root_motion);
std::vector<JointEdit>sample_keys(const std::vector<Keyframe>&,float);
struct NativeResource {std::string name,archive;uint64_t bytes=0;};
std::vector<NativeResource>native_resources(const fs::path&game);
}
