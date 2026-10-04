#include "viewer_team.h"
#include <algorithm>
#include <cfloat>
#include <cmath>
#include <limits>
#include <stdexcept>
using namespace DirectX;
namespace studio {
thread_local bool team_editing=false,team_apply_edits=false;
thread_local std::vector<ActorEdit>team_edits;
thread_local std::vector<SceneActor>scene_actors;
thread_local std::unordered_map<const fifa_player::Model*,std::vector<BonePoint>>team_bones;

const ActorEdit*actor_edit(const std::vector<ActorEdit>&list,int player){
    auto at=std::find_if(list.begin(),list.end(),[&](const auto&e){return e.player==player;});
    return at==list.end()?nullptr:&*at;
}

std::shared_ptr<fifa_player::Model>edit_team_pose(const fifa_player::Model&source,std::shared_ptr<fifa_player::Model>posed,bool crouching,const fifa_player::PoseContacts*contacts,unsigned base_pose){
    auto*edit=actor_edit(team_edits,source.player_id);
    if(!edit||(edit->joints.empty()&&!edit->pose))return posed;
    auto custom=std::make_shared<fifa_player::Model>(source);
    struct ApplyGuard {ApplyGuard(){team_apply_edits=true;}~ApplyGuard(){team_apply_edits=false;}}guard;
    unsigned pose=edit->pose?edit->pose:base_pose;
    bool individual=edit->pose!=0;
    if(!fifa_player::apply_presentation_pose(*custom,individual?false:crouching,individual?nullptr:contacts,pose))
        throw std::runtime_error("Não foi possível ajustar a pose do jogador "+std::to_string(source.player_id));
    return custom;
}

void register_team_actor(fifa_player::Model&scene,const fifa_player::Model&posed,size_t part_begin,float x,float z){
    if(!team_editing)return;
    SceneActor actor;actor.player=model_actor_id(posed);actor.part_begin=part_begin;actor.part_end=scene.parts.size();actor.anchor={x,0,z};
    auto*edit=actor_edit(team_edits,actor.player);Vec3 move={},rotation={};float scale=1;
    if(edit){move=edit->translation;rotation=edit->rotation;scale=edit->scale;}
    auto rotate=XMMatrixRotationRollPitchYaw(XMConvertToRadians(rotation.x),XMConvertToRadians(rotation.y),XMConvertToRadians(rotation.z));
    auto transform=XMMatrixTranslation(-x,0,-z)*XMMatrixScaling(scale,scale,scale)*rotate*XMMatrixTranslation(x+move.x,move.y,z+move.z);
    auto point=[&](Vec3 p){XMFLOAT3 value;XMStoreFloat3(&value,XMVector3TransformCoord(XMVectorSet(p.x,p.y,p.z,1),transform));return Vec3{value.x,value.y,value.z};};
    actor.anchor=point(actor.anchor);
    Bounds b;b.low={FLT_MAX,FLT_MAX,FLT_MAX};b.high={-FLT_MAX,-FLT_MAX,-FLT_MAX};
    for(size_t i=part_begin;i<scene.parts.size();++i)for(auto&v:scene.parts[i].vertices){
        v.position=point(v.position);XMFLOAT3 n;XMStoreFloat3(&n,XMVector3TransformNormal(XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),rotate));v.normal={n.x,n.y,n.z};
        b.low={std::min(b.low.x,v.position.x),std::min(b.low.y,v.position.y),std::min(b.low.z,v.position.z)};
        b.high={std::max(b.high.x,v.position.x),std::max(b.high.y,v.position.y),std::max(b.high.z,v.position.z)};
    }
    b.center={(b.low.x+b.high.x)/2,(b.low.y+b.high.y)/2,(b.low.z+b.high.z)/2};auto d=Vec3{b.high.x-b.low.x,b.high.y-b.low.y,b.high.z-b.low.z};b.radius=std::sqrt(d.x*d.x+d.y*d.y+d.z*d.z)/2;actor.bounds=b;
    auto at=team_bones.find(&posed);
    if(at!=team_bones.end()){actor.bones=at->second;for(auto&bone:actor.bones){bone.point=point({bone.point.x+x,bone.point.y,bone.point.z+z});XMStoreFloat4x4(&bone.frame,bone_orientation(bone.frame)*rotate);bone.frame._41=bone.point.x;bone.frame._42=bone.point.y;bone.frame._43=bone.point.z;bone.units*=scale;}}
    scene_actors.push_back(std::move(actor));
}
int room_actor_kind(const std::string&s){if(s.find("seated-coach/source/")!=s.npos||s.find("coach-arrival/source/")!=s.npos)return 2;if(s.find("seated-player/source/")!=s.npos)return 1;return 0;}
void reindex_room_actors(const fifa_player::Model&scene){for(auto&a:scene_actors){a.part_begin=scene.parts.size();a.part_end=0;for(size_t i=0;i<scene.parts.size();++i)if(room_actor_kind(scene.parts[i].asset)==(a.player<0?2:1)){a.part_begin=std::min(a.part_begin,i);a.part_end=i+1;}}}

Ray camera_ray(const Camera&camera,float width,float height,float mx,float my){
    if(width<=0||height<=0)throw std::runtime_error("Área de seleção inválida");
    float nx=2*mx/width-1,ny=1-2*my/height,t=std::tan(XMConvertToRadians(camera.fov)/2);
    auto forward=camera.forward();Vec3 right={std::cos(camera.yaw),0,std::sin(camera.yaw)};
    Vec3 up={-std::sin(camera.yaw)*std::sin(camera.pitch),std::cos(camera.pitch),std::cos(camera.yaw)*std::sin(camera.pitch)};
    Vec3 d={forward.x+right.x*nx*t*width/height+up.x*ny*t,forward.y+up.y*ny*t,forward.z+right.z*nx*t*width/height+up.z*ny*t};
    float len=std::sqrt(d.x*d.x+d.y*d.y+d.z*d.z);return {camera.position,{d.x/len,d.y/len,d.z/len}};
}
static Vec3 subtract(Vec3 a,Vec3 b){return {a.x-b.x,a.y-b.y,a.z-b.z};}
static Vec3 cross(Vec3 a,Vec3 b){return {a.y*b.z-a.z*b.y,a.z*b.x-a.x*b.z,a.x*b.y-a.y*b.x};}
static float dot(Vec3 a,Vec3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static bool box_hit(const Bounds&b,const Ray&r,float limit){
    float entry=0,leave=limit;const float*o=&r.origin.x,*d=&r.direction.x,*lo=&b.low.x,*hi=&b.high.x;
    for(int i=0;i<3;++i){if(std::fabs(d[i])<1e-7f){if(o[i]<lo[i]||o[i]>hi[i])return false;}else{float a=(lo[i]-o[i])/d[i],z=(hi[i]-o[i])/d[i];if(a>z)std::swap(a,z);entry=std::max(entry,a);leave=std::min(leave,z);if(entry>leave)return false;}}
    return true;
}
static float triangle_hit(const Ray&r,Vec3 a,Vec3 b,Vec3 c){
    auto e1=subtract(b,a),e2=subtract(c,a),p=cross(r.direction,e2);float det=dot(e1,p);
    if(std::fabs(det)<1e-7f)return FLT_MAX;float inv=1/det;auto t=subtract(r.origin,a);float u=dot(t,p)*inv;if(u<0||u>1)return FLT_MAX;
    auto q=cross(t,e1);float v=dot(r.direction,q)*inv;if(v<0||u+v>1)return FLT_MAX;float distance=dot(e2,q)*inv;return distance>.001f?distance:FLT_MAX;
}
int pick_actor(const fifa_player::Model&model,const std::vector<SceneActor>&actors,const Ray&ray){
    float nearest=FLT_MAX;int selected=0;
    for(auto&actor:actors){if(!box_hit(actor.bounds,ray,nearest))continue;
        for(size_t i=actor.part_begin;i<actor.part_end&&i<model.parts.size();++i){auto&p=model.parts[i];for(size_t k=0;k+2<p.indices.size();k+=3){auto a=p.indices[k],b=p.indices[k+1],c=p.indices[k+2];if(a>=p.vertices.size()||b>=p.vertices.size()||c>=p.vertices.size())continue;float hit=triangle_hit(ray,p.vertices[a].position,p.vertices[b].position,p.vertices[c].position);if(hit<nearest){nearest=hit;selected=actor.player;}}}
    }
    return selected;
}
}
