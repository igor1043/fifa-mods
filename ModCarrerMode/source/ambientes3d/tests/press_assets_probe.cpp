#include "viewer_press_room.h"
#include <iostream>
#include <cstring>
#include <cfloat>
#include <map>
#include "viewer_team.h"
#include <fstream>
using namespace studio;
using namespace fifa_player;
int main(){Assets assets("U:/fifa 16");
 for(int a=1;a<=6;a++)for(int b=0;b<8;b++){auto n="data/sceneassets/crowd/crowd_"+std::to_string(a)+"_"+std::to_string(b)+"_1_0.rx3";if(assets.exists(n))std::cout<<"CROWD "<<n<<"\n";}
 for(auto path:{"data/sceneassets/crowd/crowd_1_0_0_0_textures.rx3","data/sceneassets/crowd/crowd_2_0_0_0_textures.rx3","data/sceneassets/crowd/crowd_1_1_0_0_textures.rx3","data/sceneassets/slc/ballboy_0_0_0_0_textures.rx3"}){std::vector<uint8_t>raw;if(assets.read(path,raw))for(auto&n:texture_names(raw)){Texture t;if(read_texture(raw,n,t))std::cout<<"TEXTURE "<<path<<" "<<n<<" "<<t.width<<"x"<<t.height<<"\n";}}
 for(auto prefix:{"data/sceneassets/crowd/crowd_","data/sceneassets/crowdmodel/crowd_","data/sceneassets/crowdmesh/crowd_","data/sceneassets/slc/ballboy_","data/sceneassets/slc/steward_"})std::cout<<"FIRST "<<prefix<<" "<<assets.first(prefix,".rx3")<<"\n";
 for(auto name:{"data/sceneassets/crowd/crowd_1_0_1_0","data/sceneassets/crowd/crowd_2_0_1_0","data/sceneassets/crowd/crowd_1_0_2_0","data/sceneassets/crowd/crowd_2_0_2_0","data/sceneassets/crowd/crowd_1_0_3_0","data/sceneassets/crowd/crowd_2_0_3_0","data/sceneassets/crowd/crowd_1_0_4_0","data/sceneassets/crowd/crowd_2_0_4_0"}){
  std::vector<uint8_t>raw;Model m;Skeleton rig;std::cout<<"ASSET "<<name<<"\n";if(!assets.read(std::string(name)+".rx3",raw)||!read_mesh(raw,m.parts)){std::cout<<"absent\n";continue;}bool valid=read_coach_skeleton(raw,rig);std::cout<<"rig "<<valid<<"\n";
  if(valid){m.skeleton=std::make_shared<Skeleton>(rig);float floor=FLT_MAX;for(auto&p:m.parts)for(auto&v:p.vertices)floor=std::min(floor,v.position.y);m.bind_feet=floor;for(auto&p:m.parts)for(auto&v:p.vertices)v.position.y-=floor;team_editing=true;apply_coach_pose(m,205);team_editing=false;for(auto&bone:team_bones[&m])if(bone.name=="Hips"||bone.name=="Head"||bone.name=="RightFoot"||bone.name=="LeftHand")std::cout<<"bone "<<bone.name<<" "<<bone.point.x<<","<<bone.point.y<<","<<bone.point.z<<"\n";team_bones.erase(&m);}
  for(auto&p:m.parts){Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};for(auto&v:p.vertices)for(int k=0;k<3;k++){(&lo.x)[k]=std::min((&lo.x)[k],(&v.position.x)[k]);(&hi.x)[k]=std::max((&hi.x)[k],(&v.position.x)[k]);}std::cout<<p.name<<" verts "<<p.vertices.size()<<" skin "<<p.skinned<<" box "<<lo.x<<","<<lo.y<<","<<lo.z<<" / "<<hi.x<<","<<hi.y<<","<<hi.z<<"\n";}
  std::map<int,int>influences;for(auto&p:m.parts)for(auto&v:p.vertices){int best=0;for(int k=1;k<8;k++)if(v.weights[k]>v.weights[best])best=k;influences[v.joints[best]]++;}for(auto&pair:influences)std::cout<<"weight "<<pair.first<<" = "<<pair.second<<"\n";
  if(assets.read(std::string(name)+"_textures.rx3",raw))for(auto&n:texture_names(raw))std::cout<<"tex "<<n<<"\n";
 }
}
