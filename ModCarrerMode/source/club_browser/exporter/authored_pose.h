#pragma once
#include <DirectXMath.h>
#include <cmath>
#include <limits>
using namespace DirectX;
struct AuthoredPose {
 struct Slot {unsigned height;float reference_scale;XMFLOAT4X4 actor;std::vector<XMFLOAT4X4>local;};
 std::vector<std::string>names;std::vector<int>parents;std::vector<Slot>slots;
 static AuthoredPose read(const fs::path&path){
  AuthoredPose out;std::ifstream f(path,std::ios::binary);if(!f)throw std::runtime_error("Authored XI pose is missing");
  const auto size=fs::file_size(path);if(size>4*1024*1024)throw std::runtime_error("XI pose too large");
  auto take=[&](void*p,size_t n){if(!f.read((char*)p,n))throw std::runtime_error("Truncated XI pose");};
  auto integer=[&](){unsigned v;take(&v,4);return v;};
  auto matrix=[&](){XMFLOAT4X4 m;take(&m,64);for(float v:std::array<float,16>{m._11,m._12,m._13,m._14,m._21,m._22,m._23,m._24,m._31,m._32,m._33,m._34,m._41,m._42,m._43,m._44})if(!std::isfinite(v)||fabsf(v)>10000)throw std::runtime_error("Invalid XI matrix");if(fabsf(XMVectorGetX(XMMatrixDeterminant(XMLoadFloat4x4(&m))))<1e-9f)throw std::runtime_error("Singular XI matrix");return m;};
  char magic[8];take(magic,8);if(memcmp(magic,"FFPOSE02",8)||integer()!=11)throw std::runtime_error("Invalid XI pose version");unsigned count=integer();if(!count||count>1024)throw std::runtime_error("Invalid XI skeleton");
  for(unsigned i=0;i<count;++i){unsigned n=integer();if(!n||n>128)throw std::runtime_error("Invalid bone name");std::string name(n,'\0');take(name.data(),n);int parent;take(&parent,4);if(parent< -1||parent>=int(i))throw std::runtime_error("Invalid bone order");out.names.push_back(name);out.parents.push_back(parent);}
  for(unsigned i=0;i<11;++i){Slot slot;slot.height=integer();take(&slot.reference_scale,4);if(slot.height<130||slot.height>230||!std::isfinite(slot.reference_scale)||slot.reference_scale<.1f||slot.reference_scale>5)throw std::runtime_error("Invalid pose reference size");slot.actor=matrix();for(unsigned b=0;b<count;++b)slot.local.push_back(matrix());out.slots.push_back(std::move(slot));}
  if(f.peek()!=std::char_traits<char>::eof())throw std::runtime_error("Unknown XI pose extension");return out;
 }
 bool apply(Model&model,size_t slot_index)const{
  if(slot_index>=slots.size()||!model.skeleton||model.skeleton->names!=names||model.skeleton->parents.size()!=parents.size()||model.parts.empty())return false;
  const auto&s=slots[slot_index];const auto&rig=*model.skeleton;const float ratio=model.bind_scale/s.reference_scale;
  std::vector<XMFLOAT4X4>world(names.size()),delta(names.size()),normals(names.size());
  for(size_t i=0;i<names.size();++i){
   const int parent=rig.parents[i]==0xffff?-1:rig.parents[i];if(parent!=parents[i])return false;
   XMMATRIX local=XMLoadFloat4x4(&s.local[i]);if(parent<0)local=local*XMMatrixScaling(ratio,ratio,ratio);
   XMMATRIX posed=parent<0?local:local*XMLoadFloat4x4(&world[parent]);XMStoreFloat4x4(&world[i],posed);
   XMFLOAT4X4 inverse;memcpy(&inverse,rig.inverse_bind[i].data(),64);
   XMMATRIX adjusted=XMMatrixScaling(1/model.bind_scale,1/model.bind_scale,1/model.bind_scale)*XMMatrixTranslation(0,model.bind_feet,0)*XMLoadFloat4x4(&inverse);
   XMMATRIX d=adjusted*posed;XMStoreFloat4x4(&delta[i],d);XMStoreFloat4x4(&normals[i],XMMatrixTranspose(XMMatrixInverse(nullptr,d)));
  }
  float floor=std::numeric_limits<float>::max();
  for(auto&p:model.parts)for(auto&v:p.vertices){
   XMVECTOR source=XMVectorSet(v.position.x,v.position.y,v.position.z,1),original=XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),point=source,normal=original;
   if(p.skinned){point=normal=XMVectorZero();unsigned sum=0;for(unsigned k=0;k<8;++k)if(v.weights[k]){if(v.joints[k]>=delta.size())return false;point+=XMVector3TransformCoord(source,XMLoadFloat4x4(&delta[v.joints[k]]))*float(v.weights[k]);normal+=XMVector3TransformNormal(original,XMLoadFloat4x4(&normals[v.joints[k]]))*float(v.weights[k]);sum+=v.weights[k];}if(!sum)return false;point/=float(sum);}
   if(XMVectorGetX(XMVector3LengthSq(normal))<1e-12f)normal=XMVectorSet(0,1,0,0);normal=XMVector3Normalize(normal);
   v.position={XMVectorGetX(point),XMVectorGetY(point),XMVectorGetZ(point)};v.normal={XMVectorGetX(normal),XMVectorGetY(normal),XMVectorGetZ(normal)};
   if(!std::isfinite(v.position.x)||!std::isfinite(v.position.y)||!std::isfinite(v.position.z))return false;
   if(p.asset.find("/shoe/")!=p.asset.npos)floor=(std::min)(floor,v.position.y);
  }
  if(floor==std::numeric_limits<float>::max()||!std::isfinite(floor))return false;
  const auto actor=XMLoadFloat4x4(&s.actor),actor_normal=XMMatrixTranspose(XMMatrixInverse(nullptr,actor));
  for(auto&p:model.parts)for(auto&v:p.vertices){
   auto point=XMVector3TransformCoord(XMVectorSet(v.position.x,v.position.y-floor,v.position.z,1),actor);
   auto normal=XMVector3Normalize(XMVector3TransformNormal(XMVectorSet(v.normal.x,v.normal.y,v.normal.z,0),actor_normal));
   v.position={XMVectorGetX(point),XMVectorGetY(point),XMVectorGetZ(point)};v.normal={XMVectorGetX(normal),XMVectorGetY(normal),XMVectorGetZ(normal)};
  }
  model.presentation_pose=true;model.presentation_pose_id=1;model.diagnostic+="\nauthored_XI_pose=FFPOSE02 slot="+std::to_string(slot_index);return true;
 }
 Model assemble(const std::vector<std::shared_ptr<const Model>>&players)const{
  if(players.size()!=11||slots.size()!=11)throw std::runtime_error("Eleven actors required");
  auto pool=players;std::stable_sort(pool.begin(),pool.end(),[](const auto&a,const auto&b){return a->height_cm>b->height_cm;});
  std::vector<std::shared_ptr<const Model>>keepers,order;for(auto i=pool.begin();i!=pool.end()&&keepers.size()<2;)if((*i)->goalkeeper){keepers.push_back(*i);i=pool.erase(i);}else ++i;
  if(!keepers.empty())order.push_back(keepers.front());const size_t standing=6-keepers.size();
  for(size_t i=0;i<standing;++i)order.push_back(pool[i]);if(keepers.size()>1)order.push_back(keepers[1]);for(size_t i=standing;i<pool.size();++i)order.push_back(pool[i]);
  Model result;result.parts.clear();result.player_count=0;result.team_id=players.front()->team_id;result.presentation_pose=true;
  for(size_t i=0;i<11;++i){Model actor=*order[i];if(actor.team_id!=result.team_id||!apply(actor,i))throw std::runtime_error("Authored pose could not be applied to current club");std::vector<int>remap;
   for(const auto&t:actor.textures){size_t index=0;for(;index<result.textures.size();++index){const auto&v=result.textures[index];if(v.width==t.width&&v.height==t.height&&v.format==t.format&&v.bytes==t.bytes)break;}if(index==result.textures.size())result.textures.push_back(t);remap.push_back(int(index));}
   for(auto&p:actor.parts){if(p.texture>=0)p.texture=remap.at(p.texture);if(p.hair_coeff_texture>=0)p.hair_coeff_texture=remap.at(p.hair_coeff_texture);result.parts.push_back(std::move(p));}
   ++result.player_count;result.diagnostic+="slot="+std::to_string(i)+" player="+std::to_string(actor.player_id)+"\n";
  }return result;
 }
};
