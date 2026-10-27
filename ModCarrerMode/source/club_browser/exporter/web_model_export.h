#pragma once
#include <DirectXMath.h>
#include <sstream>
static bool export_web_model(const Model&model,const fs::path&target){
 std::ofstream file(target,std::ios::binary);if(!file)return false;
 auto integer=[&](uint32_t v){file.write((const char*)&v,4);};
 auto scalar=[&](float v){file.write((const char*)&v,4);};
 file.write("FF3D0001",8);integer((uint32_t)model.parts.size());integer((uint32_t)model.textures.size());
 for(const auto&p:model.parts){integer((uint32_t)p.vertices.size());integer((uint32_t)p.indices.size());integer((uint32_t)p.texture);integer(p.blend?1:0);scalar(p.alpha_scale);for(float v:{p.color.x,p.color.y,p.color.z,p.tint.x,p.tint.y,p.tint.z})scalar(v);
  std::vector<float>vertices;vertices.reserve(p.vertices.size()*8);
  for(const auto&v:p.vertices)vertices.insert(vertices.end(),{v.position.x,v.position.y,v.position.z,v.normal.x,v.normal.y,v.normal.z,v.u,v.v});
  file.write((const char*)vertices.data(),vertices.size()*sizeof(float));
  file.write((const char*)p.indices.data(),p.indices.size()*4);
 }
 for(const auto&t:model.textures){integer(t.width);integer(t.height);integer(t.format);integer((uint32_t)t.bytes.size());file.write((const char*)t.bytes.data(),t.bytes.size());}
 if(model.scene_camera_valid){file.write("FFCAM001",8);for(float v:{model.scene_camera_position.x,model.scene_camera_position.y,model.scene_camera_position.z,model.scene_camera_yaw,model.scene_camera_pitch,model.scene_camera_fov})scalar(v);}
 file.write("FFMAT001",8);integer((uint32_t)model.parts.size());
 for(const auto&p:model.parts){integer(p.asset.find("/hair/")!=std::string::npos?1:0);integer((uint32_t)p.hair_coeff_texture);}
 if(model.room==RoomDressing){
  const float front=model.scene_camera_position.z+180;
  bool trophyAvailable=false;for(const auto&p:model.parts)if(p.asset.rfind("data/sceneassets/trophy/",0)==0&&!p.indices.empty())trophyAvailable=true;
  std::ostringstream extra;extra<<"{\"layoutVersion\":1,\"trophyAvailable\":"<<(trophyAvailable?"true":"false")<<",\"zones\":[";
  auto zone=[&](const char*id,const char*name,float x,float z,float yaw,bool comma){if(comma)extra<<",";extra<<"{\"id\":\""<<id<<"\",\"name\":\""<<name<<"\",\"position\":["<<x<<",177,"<<z<<"],\"yaw\":"<<yaw<<"}";};
  zone("locker","Vestiário",0,front-180,0,false);
  zone("tactics","Quadro tático",0,-180,0,true);
  zone("coach","Sala do treinador",190,front+130,3.14159265f,true);
  zone("lounge","Área de reunião",420,front+170,2.25f,true);
  zone("trophies","Vitrine do clube",520,front+550,3.14159265f,true);
  zone("medical","Departamento médico",-610,front+175,3.14159265f,true);
  extra<<"],\"lights\":[";bool comma=false;for(float x:{-470.f,0.f,470.f})for(float z=-400;z<front+800;z+=380){if(comma)extra<<",";comma=true;extra<<"["<<x<<",307,"<<z<<"]";}extra<<"],\"screens\":[";comma=false;
  for(const auto&p:model.parts)if(p.asset.rfind("studio/live/",0)==0){if(comma)extra<<",";comma=true;extra<<"{\"key\":\""<<p.asset.substr(12)<<"\",\"texture\":"<<p.texture<<"}";}
  extra<<"]}";const auto json=extra.str();file.write("FFROOM01",8);integer((uint32_t)json.size());file.write(json.data(),json.size());
 }
 file.flush();return !!file;
}
static bool export_web_skinned_model(const Model&model,const fs::path&target,const std::string&name){
 if(model.parts.empty()||!model.skeleton||model.skeleton->names.empty()||
    model.skeleton->names.size()!=model.skeleton->parents.size()||
    model.skeleton->names.size()!=model.skeleton->inverse_bind.size())return false;
 std::ofstream file(target,std::ios::binary|std::ios::trunc);if(!file)return false;
 auto integer=[&](uint32_t v){file.write((const char*)&v,4);};
 auto scalar=[&](float v){file.write((const char*)&v,4);};
 auto string=[&](const std::string&v){if(v.size()>4096)throw std::runtime_error("Nome FF3D inválido");integer((uint32_t)v.size());file.write(v.data(),(std::streamsize)v.size());};
 file.write("FF3D0003",8);integer((uint32_t)model.parts.size());integer((uint32_t)model.textures.size());
 integer((uint32_t)model.skeleton->names.size());integer((uint32_t)model.player_id);integer((uint32_t)model.height_cm);
 string(name.empty()?std::string("Treinador"):name);
 /* Keep the same grounded geometry and bind transform used by the FIFA rig exporter. */
 const float scale=model.bind_scale>0?model.bind_scale:1.f;
 const DirectX::XMMATRIX inverse_geometry=DirectX::XMMatrixScaling(1.f/scale,1.f/scale,1.f/scale)*DirectX::XMMatrixTranslation(0,model.bind_feet,0);
 for(size_t i=0;i<model.skeleton->names.size();++i){
  string(model.skeleton->names[i]);integer(model.skeleton->parents[i]==0xffff?UINT32_MAX:(uint32_t)model.skeleton->parents[i]);
  DirectX::XMFLOAT4X4 raw,adjusted;memcpy(&raw,model.skeleton->inverse_bind[i].data(),64);
  DirectX::XMStoreFloat4x4(&adjusted,inverse_geometry*DirectX::XMLoadFloat4x4(&raw));const float*values=&adjusted._11;
  for(int k=0;k<16;++k)scalar(values[k]);
 }
 for(const auto&part:model.parts){
  if(part.vertices.size()>5000000||part.indices.size()>15000000||part.indices.size()%3)return false;
  string(part.name);string(part.asset);integer((uint32_t)part.texture);integer(part.skinned?1:0);integer(part.blend?1:0);
  scalar(part.alpha_scale);integer((uint32_t)part.hair_coeff_texture);
  for(float v:{part.color.x,part.color.y,part.color.z,part.tint.x,part.tint.y,part.tint.z})scalar(v);
  integer((uint32_t)part.vertices.size());integer((uint32_t)part.indices.size());
  for(const auto&vertex:part.vertices){
   for(float v:{vertex.position.x,vertex.position.y,vertex.position.z,vertex.normal.x,vertex.normal.y,vertex.normal.z,vertex.u,vertex.v})scalar(v);
   file.write((const char*)vertex.joints,sizeof(vertex.joints));file.write((const char*)vertex.weights,sizeof(vertex.weights));
   if(part.skinned)for(int joint=0;joint<8;++joint)if(vertex.weights[joint]&&vertex.joints[joint]>=model.skeleton->names.size())return false;
  }
  if(!part.indices.empty())file.write((const char*)part.indices.data(),(std::streamsize)part.indices.size()*4);
 }
 for(const auto&texture:model.textures){integer(texture.width);integer(texture.height);integer(texture.format);integer((uint32_t)texture.bytes.size());file.write((const char*)texture.bytes.data(),(std::streamsize)texture.bytes.size());}
 file.flush();return !!file;
}
