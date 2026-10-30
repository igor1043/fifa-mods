#include "coach_profile.h"
#include <cassert>
#include <fstream>
#include <iostream>
#include <filesystem>
int main(int argc,char**argv){
 if(argc==3&&std::string(argv[1])=="--catalog"){
  int count=0,played=0;for(const auto&file:std::filesystem::directory_iterator(argv[2]))if(file.path().extension()==".tsv"){
   int club=std::stoi(file.path().stem().string());std::ifstream input(file.path(),std::ios::binary);clubcoach::Profile p;
   if(!clubcoach::parse(input,club,p)){std::cerr<<"INVALID club "<<club<<"\n";return 1;}++count;if(p.stats.at("total")[0]>0)++played;
  }assert(count>1000);std::cout<<"PASS installed catalog: "<<count<<" clubs, "<<played<<" with recorded games\n";return 0;
 }
 if(argc==4){std::ifstream input(argv[1],std::ios::binary);clubcoach::Profile p;assert(clubcoach::parse(input,std::stoi(argv[2]),p));assert(p.stats.at("total")[0]==std::stoi(argv[3]));std::cout<<"PASS actual career club "<<p.club<<": "<<p.stats.at("total")[0]<<" games\n";return 0;}
 if(argc==1){
  assert(clubcoach::portraitFile("minifaces/000183.png")=="minifaces/000183.png");
  for(const char*path:{"—","C:/other.png","minifaces/../other.png","minifaces/folder/photo.png","minifaces/face.jpg"})assert(clubcoach::portraitFile(path)=="minifaces/NOTFOUND_DEFAULT.png");
  std::string text="S16COACH1\t1043\tClub\nF\tname\tCoach\nS\ttotal\t1\t1\t0\t0\t2\t0\t3\nS\thome\t1\t1\t0\t0\t2\t0\t3\nS\taway\t0\t0\t0\t0\t0\t0\t0\n";clubcoach::Profile p;std::istringstream valid(text);assert(clubcoach::parse(valid,1043,p));assert(p.coachStats.at("total")[0]==-1);std::istringstream foreign(text);assert(!clubcoach::parse(foreign,1629,p));std::istringstream duplicate(text+"F\tname\tOther\n");assert(!clubcoach::parse(duplicate,1043,p));std::istringstream broken(text+"S\tbogus\t0\t0\t0\t0\t0\t0\t0\n");assert(!clubcoach::parse(broken,1043,p));
  std::string trainer="T\ttotal\t0\t0\t0\t0\t0\t0\t0\nT\thome\t0\t0\t0\t0\t0\t0\t0\nT\taway\t0\t0\t0\t0\t0\t0\t0\n";std::istringstream separate(text+trainer);assert(clubcoach::parse(separate,1043,p));assert(p.stats.at("total")[0]==1&&p.coachStats.at("total")[0]==0);std::istringstream duplicatedTrainer(text+trainer+trainer);assert(!clubcoach::parse(duplicatedTrainer,1043,p));std::istringstream incomplete(text+"T\ttotal\t0\t0\t0\t0\t0\t0\t0\n");assert(!clubcoach::parse(incomplete,1043,p));
  std::string partial="S16COACH1\t130017\tDinamo Zagreb\nF\tname\tCoach\nS\ttotal\t8\t3\t3\t2\t-1\t-1\t12\nS\thome\t5\t3\t2\t0\t-1\t-1\t11\nS\taway\t3\t0\t1\t2\t-1\t-1\t1\nT\ttotal\t8\t3\t3\t2\t-1\t-1\t12\nT\thome\t5\t3\t2\t0\t-1\t-1\t11\nT\taway\t3\t0\t1\t2\t-1\t-1\t1\nC\t224\tEuropa\t8\t3\t3\t2\t-1\t-1\t12\tEm andamento\n";
  std::istringstream simulated(partial);assert(clubcoach::parse(simulated,130017,p));assert(p.stats.at("total")[0]==8&&p.stats.at("total")[4]==-1&&p.coachStats.at("total")[1]==3);
  auto badPartial=partial;auto pos=badPartial.find("S\taway\t3");badPartial.replace(pos,8,"S\taway\t4");std::istringstream inconsistent(badPartial);assert(!clubcoach::parse(inconsistent,130017,p));
  std::cout<<"PASS coach protocol: independent club/spell totals, legacy compatibility, scoped identity, duplicate and malformed rejection\n";return 0;
 }
 assert(argc==3);for(int i=1;i<3;++i){std::ifstream in(argv[i],std::ios::binary);std::string text((std::istreambuf_iterator<char>(in)),{});clubcoach::Profile p;std::istringstream source(text);assert(clubcoach::parse(source,i==1?1043:1629,p));assert(p.starters.empty());assert(p.stats.at("total")[0]==p.stats.at("home")[0]+p.stats.at("away")[0]);assert(p.coachStats.at("total")[0]==p.coachStats.at("home")[0]+p.coachStats.at("away")[0]);assert(!p.competitions.empty());std::istringstream foreign(text);assert(!clubcoach::parse(foreign,9999,p));auto corrupt=text;auto at=corrupt.find("S\ttotal\t");assert(at!=corrupt.npos);corrupt.replace(at,7,"S\tbogus");std::istringstream broken(corrupt);assert(!clubcoach::parse(broken,p.club,p));}std::cout<<"PASS coach profile: real two-club data, separate coach/club venue totals and cross-club rejection\n";
}
