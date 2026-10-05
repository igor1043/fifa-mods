#pragma once
#include <iostream>
#include <unordered_map>
static int web_model_worker(const fs::path&game){
 if(FAILED(CoInitializeEx(nullptr,COINIT_MULTITHREADED)))return 1;
 {Assets assets(game.string());std::unordered_map<uint64_t,std::shared_ptr<Model>>cache;std::string line;
 while(std::getline(std::cin,line)){
  bool ok=false;try{auto a=line.find('\t'),b=a==line.npos?line.npos:line.find('\t',a+1);if(b!=line.npos){auto fixture=fs::u8path(line.substr(0,a)),target=fs::u8path(line.substr(a+1,b-a-1));int pose=std::stoi(line.substr(b+1));std::vector<ClubPlayerRow>rows;int club=0;unsigned colors[3]={};
   if(pose>=301&&pose<=304){if(read_fixture(fixture,rows,club,colors,true)&&(pose==302?rows.size()<=64:rows.size()==11)){std::vector<std::shared_ptr<const Model>>players;for(auto&row:rows){auto model=std::make_shared<Model>(assets.load(row));if(model->parts.empty())throw std::runtime_error("Missing room actor");players.push_back(model);}ClubPlayerRow identity{};identity.team_id=club;identity.club_colors_valid=1;std::copy(std::begin(colors),std::end(colors),std::begin(identity.club_colors));auto coach=assets.coach(identity);const ClubRoomKind kinds[]={RoomPress,RoomDressing,RoomGym,RoomTraining};auto scene=build_new_experience_room(assets,game.string(),players,rows,coach,kinds[pose-301]);if(!scene.parts.empty())ok=export_web_model(scene,target);}std::cout<<"FF_READY "<<(ok?0:1)<<std::endl;continue;}
   if((pose>=1&&pose<=7)||pose==120){if(read_fixture(fixture,rows,club,colors,true)&&!rows.empty()){std::vector<std::shared_ptr<const Model>>players;for(auto&row:rows){auto model=std::make_shared<Model>(assets.load(row));if(model->parts.empty())throw std::runtime_error("Missing team actor");players.push_back(model);}Model scene;if(pose==120){auto coach=assets.coach(rows.front());if(!coach.model)throw std::runtime_error("Missing team coach");scene=build_full_squad_photo(players,coach.model);}else scene=assemble_starting_eleven(players,pose);if(!scene.parts.empty())ok=export_web_model(scene,target);}std::cout<<"FF_READY "<<(ok?0:1)<<std::endl;continue;}
   bool coach=pose>=200;const auto*recipe=presentation_pose_find(pose);if(recipe&&(recipe->modes&(coach?PoseStandingCoach:PoseIndividual))&&read_fixture(fixture,rows,club,colors,true)&&rows.size()==1){uint64_t hash=1469598103934665603ULL;std::ifstream source(fixture,std::ios::binary);char byte;while(source.get(byte)){hash^=(unsigned char)byte;hash*=1099511628211ULL;}
    if(coach)hash^=0xbafca123a322dd10ULL;auto found=cache.find(hash);std::shared_ptr<Model>base;if(found!=cache.end())base=found->second;else{if(coach){auto assigned=assets.coach(rows.front());if(!assigned.model)throw std::runtime_error("Coach unavailable");base=std::make_shared<Model>(*assigned.model);}else base=std::make_shared<Model>(assets.load(rows.front()));if(cache.size()>=8)cache.erase(cache.begin());cache.emplace(hash,base);}Model posed=*base;if(!posed.parts.empty()){if(coach)apply_coach_pose(posed,pose);else apply_presentation_pose(posed,false,nullptr,pose);ok=export_web_model(posed,target);}}
  }}catch(...){ok=false;}
  std::cout<<"FF_READY "<<(ok?0:1)<<std::endl;
 }}CoUninitialize();return 0;
}
