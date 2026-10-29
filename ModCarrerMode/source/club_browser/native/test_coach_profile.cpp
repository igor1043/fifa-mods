#include "coach_profile.h"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
 if(argc==1){
  assert(clubcoach::portraitFile("minifaces/000183.png")=="minifaces/000183.png");
  for(const char*path:{"—","C:/other.png","minifaces/../other.png","minifaces/folder/photo.png","minifaces/face.jpg"})assert(clubcoach::portraitFile(path)=="minifaces/NOTFOUND_DEFAULT.png");
  std::string text="S16COACH1\t1043\tClub\nF\tname\tCoach\nS\ttotal\t1\t1\t0\t0\t2\t0\t3\nS\thome\t1\t1\t0\t0\t2\t0\t3\nS\taway\t0\t0\t0\t0\t0\t0\t0\n";clubcoach::Profile p;std::istringstream valid(text);assert(clubcoach::parse(valid,1043,p));assert(p.coachStats.at("total")[0]==-1);std::istringstream foreign(text);assert(!clubcoach::parse(foreign,1629,p));std::istringstream duplicate(text+"F\tname\tOther\n");assert(!clubcoach::parse(duplicate,1043,p));std::istringstream broken(text+"S\tbogus\t0\t0\t0\t0\t0\t0\t0\n");assert(!clubcoach::parse(broken,1043,p));
  std::string trainer="T\ttotal\t0\t0\t0\t0\t0\t0\t0\nT\thome\t0\t0\t0\t0\t0\t0\t0\nT\taway\t0\t0\t0\t0\t0\t0\t0\n";std::istringstream separate(text+trainer);assert(clubcoach::parse(separate,1043,p));assert(p.stats.at("total")[0]==1&&p.coachStats.at("total")[0]==0);std::istringstream duplicatedTrainer(text+trainer+trainer);assert(!clubcoach::parse(duplicatedTrainer,1043,p));std::istringstream incomplete(text+"T\ttotal\t0\t0\t0\t0\t0\t0\t0\n");assert(!clubcoach::parse(incomplete,1043,p));
  std::cout<<"PASS coach protocol: independent club/spell totals, legacy compatibility, scoped identity, duplicate and malformed rejection\n";return 0;
 }
 assert(argc==3);for(int i=1;i<3;++i){std::ifstream in(argv[i],std::ios::binary);std::string text((std::istreambuf_iterator<char>(in)),{});clubcoach::Profile p;std::istringstream source(text);assert(clubcoach::parse(source,i==1?1043:1629,p));assert(p.starters.empty());assert(p.stats.at("total")[0]==p.stats.at("home")[0]+p.stats.at("away")[0]);assert(p.coachStats.at("total")[0]==p.coachStats.at("home")[0]+p.coachStats.at("away")[0]);assert(!p.competitions.empty());std::istringstream foreign(text);assert(!clubcoach::parse(foreign,9999,p));auto corrupt=text;auto at=corrupt.find("S\ttotal\t");assert(at!=corrupt.npos);corrupt.replace(at,7,"S\tbogus");std::istringstream broken(corrupt);assert(!clubcoach::parse(broken,p.club,p));}std::cout<<"PASS coach profile: real two-club data, separate coach/club venue totals and cross-club rejection\n";
}
