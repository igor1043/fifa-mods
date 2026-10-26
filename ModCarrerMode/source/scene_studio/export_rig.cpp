#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "engine/src/render/assets/fifa_player_assets.h"
#include <windows.h>
#include <objbase.h>
#include <DirectXMath.h>
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <set>
#include <sstream>
using namespace fifa_player;
namespace fs=std::filesystem;
#include "fixture.h"
#include "web_model_export.h"
std::string quoted(const std::string&s){std::string out="\"";for(unsigned char c:s){if(c=='"'||c=='\\')out+='\\';if(c>=32)out+=c;}return out+'"';}
int wmain(int argc,wchar_t**argv){
 if(argc!=4)return 2;CoInitializeEx(nullptr,COINIT_MULTITHREADED);
 fs::path game=argv[1],fixture=argv[2],out=argv[3];fs::create_directories(out);
 std::vector<ClubPlayerRow>rows;int club=0;unsigned colors[3]{};
 if(!read_fixture(fixture,rows,club,colors)||rows.size()!=11)return 3;
 Assets assets(game.string());std::vector<std::shared_ptr<const Model>>players;
 for(const auto&r:rows){auto m=std::make_shared<Model>(assets.load(r));
  if(m->parts.empty()||!m->skeleton)return 4;
  auto path=out/("player-"+std::to_string(r.player_id)+".ff3d");
  if(!export_web_skinned_model(*m,path,r.name))return 5;
  players.push_back(m);std::cout<<"RIG "<<r.player_id<<" "<<m->skeleton->names.size()<<" bones"<<std::endl;
 }
 std::ofstream json(out/"scene.json");json<<std::setprecision(9)<<"{\"schema\":1,\"club\":"<<club<<",\"source\":\"FIFA models; offline only\",\"variants\":[";
 for(int variant=0;variant<2;++variant){
  Model group=assemble_starting_eleven(players,variant?8:1);
  if(group.editor_actors.size()!=11||group.formation.size()!=11)return 6;
  if(!export_web_model(group,out/(variant?"candidate.ff3d":"baseline.ff3d")))return 7;
  if(variant)json<<",";json<<"{\"id\":"<<quoted(variant?"candidate":"baseline")<<",\"label\":"<<quoted(variant?"Ajuste de bracos":"Pose atual")<<",\"players\":[";
  for(size_t i=0;i<11;++i){const auto&m=*group.editor_actors[i];const auto&p=group.formation[i];
   if(m.editor_pose_world.size()!=m.skeleton->names.size())return 8;
   auto row=std::find_if(rows.begin(),rows.end(),[&](const ClubPlayerRow&r){return r.player_id==m.player_id;});
   if(i)json<<",";json<<"{\"id\":"<<m.player_id<<",\"name\":"<<quoted(row->name)<<",\"number\":"<<row->number<<",\"slot\":"<<i<<",\"crouching\":"<<(p.crouching?"true":"false")<<",\"position\":["<<p.x<<",0,"<<p.z<<"],\"poseWorld\":[";
   for(size_t j=0;j<m.editor_pose_world.size();++j){if(j)json<<",";json<<"[";for(int k=0;k<16;++k){if(k)json<<",";json<<m.editor_pose_world[j][k];}json<<"]";}
   json<<"]}";
  }
  json<<"]}";std::cout<<"EXPORTED "<<(variant?"candidate":"baseline")<<std::endl;
 }
 json<<"]}\n";json.close();CoUninitialize();return json?0:9;
}
