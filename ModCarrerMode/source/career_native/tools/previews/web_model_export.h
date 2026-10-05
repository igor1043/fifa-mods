#pragma once
static bool export_web_model(const Model&model,const fs::path&target){
 std::ofstream file(target,std::ios::binary);if(!file)return false;
 auto integer=[&](uint32_t v){file.write((const char*)&v,4);};
 auto scalar=[&](float v){file.write((const char*)&v,4);};
 file.write("FF3D0001",8);integer((uint32_t)model.parts.size());integer((uint32_t)model.textures.size());
 for(const auto&p:model.parts){integer((uint32_t)p.vertices.size());integer((uint32_t)p.indices.size());integer((uint32_t)p.texture);integer(p.blend?1:0);scalar(p.alpha_scale);for(float v:{p.color.x,p.color.y,p.color.z,p.tint.x,p.tint.y,p.tint.z})scalar(v);
  for(const auto&v:p.vertices)for(float value:{v.position.x,v.position.y,v.position.z,v.normal.x,v.normal.y,v.normal.z,v.u,v.v})scalar(value);
  file.write((const char*)p.indices.data(),p.indices.size()*4);
 }
 for(const auto&t:model.textures){integer(t.width);integer(t.height);integer(t.format);integer((uint32_t)t.bytes.size());file.write((const char*)t.bytes.data(),t.bytes.size());}
 if(model.scene_camera_valid){file.write("FFCAM001",8);for(float v:{model.scene_camera_position.x,model.scene_camera_position.y,model.scene_camera_position.z,model.scene_camera_yaw,model.scene_camera_pitch,model.scene_camera_fov})scalar(v);}
 file.write("FFMAT001",8);integer((uint32_t)model.parts.size());
 for(const auto&p:model.parts){integer(p.asset.find("/hair/")!=std::string::npos?1:0);integer((uint32_t)p.hair_coeff_texture);}
 return !!file;
}
