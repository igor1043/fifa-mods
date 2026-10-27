#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "engine/src/render/assets/fifa_player_assets.h"
#include <windows.h>
#include <objbase.h>
#include <algorithm>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <set>
using namespace fifa_player;namespace fs=std::filesystem;
#include "fixture.h"
#include "web_model_export.h"
#include "authored_pose.h"
static bool generate(Assets&assets,const fs::path&game,const fs::path&fixture,const fs::path&target,int pose,const fs::path&override_pose={}){
 std::vector<ClubPlayerRow>rows;int club=0;unsigned colors[3]{};
 if(pose==401){
  if(!read_fixture(fixture,rows,club,colors,true)||rows.size()!=1)throw std::runtime_error("Invalid individual-player request");
  auto model=assets.load(rows[0]);if(model.parts.empty()||!model.skeleton||model.player_id!=rows[0].player_id||model.team_id!=club)throw std::runtime_error("Incomplete individual player");
  return export_web_skinned_model(model,target,rows[0].name);
 }
 if(pose!=1||!read_fixture(fixture,rows,club,colors)||rows.size()!=11)throw std::runtime_error("Invalid starting-XI request");
 std::vector<std::shared_ptr<const Model>>players;std::set<int>identities;
 for(const auto&row:rows){auto m=std::make_shared<Model>(assets.load(row));if(m->parts.empty()||!m->skeleton||m->team_id!=club||!identities.insert(m->player_id).second)throw std::runtime_error("Incomplete or mixed starting XI");players.push_back(m);}
 auto path=override_pose.empty()?game/L"ModCarrerMode/data/club_browser/poses/starting_eleven.pose":override_pose;
 auto group=fs::exists(path)?AuthoredPose::read(path).assemble(players):assemble_starting_eleven(players,1);
 if(group.parts.empty()||group.player_count!=11)throw std::runtime_error("Incomplete posed XI");
 std::cout<<"FF_POSE "<<(fs::exists(path)?"authored-FFPOSE02":"legacy")<<" club="<<club<<" players=11\n"<<group.diagnostic;
 return export_web_model(group,target);
}
int wmain(int argc,wchar_t**argv){
 if(argc<3)return 2;CoInitializeEx(nullptr,COINIT_MULTITHREADED);int code=0;
 try{const fs::path game=argv[2];Assets assets(game.string());
  if(std::wstring(argv[1])==L"--web-worker"){
   std::string line;while(std::getline(std::cin,line)){bool ok=false;try{auto a=line.find('\t'),b=a==line.npos?line.npos:line.find('\t',a+1);if(b==line.npos)throw std::runtime_error("Invalid request framing");ok=generate(assets,game,fs::u8path(line.substr(0,a)),fs::u8path(line.substr(a+1,b-a-1)),std::stoi(line.substr(b+1)));}catch(const std::exception&e){std::cout<<"FF_ERROR "<<e.what()<<"\n";}std::cout<<"FF_READY "<<(ok?0:1)<<std::endl;}
  }else if(std::wstring(argv[1])==L"--web-model"&&(argc==6||argc==7))code=generate(assets,game,argv[3],argv[4],_wtoi(argv[5]),argc==7?fs::path(argv[6]):fs::path{})?0:1;
  else code=2;
 }catch(const std::exception&e){std::cerr<<e.what()<<std::endl;code=1;}CoUninitialize();return code;
}
