#include "viewer_pose_hooks.h"
#include "viewer_animation.h"
#include "viewer_team.h"
#include <algorithm>
using namespace DirectX;
namespace studio {
thread_local std::vector<JointEdit>pose_edits;
thread_local std::vector<BonePoint>pose_bones;
thread_local int pose_player=0;
thread_local bool pose_coach=false;
static bool selected(const fifa_player::Model&m){return m.skeleton&&((pose_coach&&m.skeleton->names.size()==31)||(!pose_coach&&m.player_id==pose_player));}
int model_actor_id(const fifa_player::Model&m){return m.skeleton&&m.skeleton->names.size()==31?-m.team_id:m.player_id;}
XMMATRIX bone_orientation(const XMFLOAT4X4&m){auto out=XMLoadFloat4x4(&m);for(int k=0;k<3;++k)out.r[k]=XMVector3Normalize(out.r[k]);out.r[3]=XMVectorSet(0,0,0,1);return out;}
JointEdit edit_from_gizmo(const BonePoint&bone,const JointEdit&old,const XMFLOAT4X4&next,bool translate){
    auto euler=XMMatrixRotationRollPitchYaw(XMConvertToRadians(old.rotation.x),XMConvertToRadians(old.rotation.y),XMConvertToRadians(old.rotation.z));
    auto basis=XMMatrixInverse(nullptr,euler)*bone_orientation(bone.frame);auto result=old;
    if(translate){auto delta=XMVectorSet(next._41-bone.point.x,next._42-bone.point.y,next._43-bone.point.z,0);delta=XMVector3TransformNormal(delta,XMMatrixInverse(nullptr,basis))/std::max(.001f,bone.units);result.translation.x+=XMVectorGetX(delta);result.translation.y+=XMVectorGetY(delta);result.translation.z+=XMVectorGetZ(delta);}
    else{XMFLOAT4X4 r;XMStoreFloat4x4(&r,bone_orientation(next)*XMMatrixInverse(nullptr,basis));float pitch=asinf(std::clamp(-r._32,-1.f,1.f)),yaw=0,roll;
        if(fabsf(cosf(pitch))>.001f){yaw=atan2f(r._31,r._33);roll=atan2f(r._12,r._22);}else{pitch=copysignf(XM_PIDIV2,pitch);roll=atan2f(-r._21,r._11);}
        result.rotation={XMConvertToDegrees(pitch),XMConvertToDegrees(yaw),XMConvertToDegrees(roll)};
    }return result;
}
void apply_overrides(const fifa_player::Model&m,const std::vector<XMFLOAT4X4>&rest,std::vector<XMFLOAT4X4>&pose){
    const std::vector<JointEdit>*edits=&pose_edits;
    if(team_editing){auto*actor=actor_edit(team_edits,model_actor_id(m));if(!team_apply_edits||!actor)return;edits=&actor->joints;}
    else{if(!selected(m))return;retarget(m,rest,pose);}
    auto&rig=*m.skeleton;
    auto ordered=*edits;std::stable_sort(ordered.begin(),ordered.end(),[&](const auto&a,const auto&b){return std::find(rig.names.begin(),rig.names.end(),a.name)<std::find(rig.names.begin(),rig.names.end(),b.name);});
    for(auto&e:ordered){auto it=std::find(rig.names.begin(),rig.names.end(),e.name);if(it==rig.names.end())continue;size_t joint=size_t(it-rig.names.begin());auto pivot=pose[joint];auto orientation=bone_orientation(pivot);auto rotation=XMMatrixInverse(nullptr,orientation)*XMMatrixRotationRollPitchYaw(XMConvertToRadians(e.rotation.x),XMConvertToRadians(e.rotation.y),XMConvertToRadians(e.rotation.z))*orientation;auto offset=XMVector3TransformNormal(XMVectorSet(e.translation.x,e.translation.y,e.translation.z,0),orientation);auto scale=XMMatrixScaling(e.scale,e.scale,e.scale);auto transform=XMMatrixTranslation(-pivot._41,-pivot._42,-pivot._43)*scale*rotation*XMMatrixTranslation(pivot._41+XMVectorGetX(offset),pivot._42+XMVectorGetY(offset),pivot._43+XMVectorGetZ(offset));
        for(size_t i=joint;i<pose.size();++i){size_t p=i;while(p!=joint&&rig.parents[p]!=0xffff)p=rig.parents[p];if(p==joint)XMStoreFloat4x4(&pose[i],XMLoadFloat4x4(&pose[i])*transform);}
    }
}
void capture_bones(const fifa_player::Model&m,const std::vector<XMFLOAT4X4>&pose,float floor,float scale){if(!team_editing&&!selected(m))return;std::vector<BonePoint>captured;captured.reserve(pose.size());for(size_t i=0;i<pose.size();++i){auto&p=pose[i];BonePoint bone{m.skeleton->names[i],m.skeleton->parents[i]==0xffff?-1:int(m.skeleton->parents[i]),{p._41*scale,p._42*scale-floor,p._43*scale}};XMStoreFloat4x4(&bone.frame,bone_orientation(p));bone.frame._41=bone.point.x;bone.frame._42=bone.point.y;bone.frame._43=bone.point.z;bone.units=scale;captured.push_back(bone);}if(team_editing)team_bones[&m]=std::move(captured);else pose_bones=std::move(captured);}
}
