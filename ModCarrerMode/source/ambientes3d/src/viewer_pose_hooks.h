#pragma once
#include "viewer_core.h"
#include <DirectXMath.h>
namespace studio {
struct BonePoint {std::string name; int parent=-1; fifa_player::Vec3 point={};DirectX::XMFLOAT4X4 frame={};float units=1;};
extern thread_local std::vector<JointEdit> pose_edits;
extern thread_local std::vector<BonePoint> pose_bones;
extern thread_local int pose_player;
extern thread_local bool pose_coach;
void apply_overrides(const fifa_player::Model&,const std::vector<DirectX::XMFLOAT4X4>&,std::vector<DirectX::XMFLOAT4X4>&);
void capture_bones(const fifa_player::Model&,const std::vector<DirectX::XMFLOAT4X4>&,float floor,float scale);
DirectX::XMMATRIX bone_orientation(const DirectX::XMFLOAT4X4&);
JointEdit edit_from_gizmo(const BonePoint&,const JointEdit&,const DirectX::XMFLOAT4X4&,bool translate);
int model_actor_id(const fifa_player::Model&);
}
