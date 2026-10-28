#include "coach_profile.h"
#include <cassert>
#include <fstream>
#include <iostream>
int main(int argc,char**argv){
 if(argc==1){
  std::string text="S16COACH1\t1043\tClub\nF\tname\tCoach\nS\ttotal\t1\t1\t0\t0\t2\t0\t3\nS\thome\t1\t1\t0\t0\t2\t0\t3\nS\taway\t0\t0\t0\t0\t0\t0\t0\n";clubcoach::Profile p;std::istringstream valid(text);assert(clubcoach::parse(valid,1043,p));std::istringstream foreign(text);assert(!clubcoach::parse(foreign,1629,p));std::istringstream duplicate(text+"F\tname\tOther\n");assert(!clubcoach::parse(duplicate,1043,p));std::istringstream broken(text+"S\tbogus\t0\t0\t0\t0\t0\t0\t0\n");assert(!clubcoach::parse(broken,1043,p));std::cout<<"PASS coach protocol: scoped identity, valid totals, duplicate and malformed rejection\n";return 0;
 }
 assert(argc==3);for(int i=1;i<3;++i){std::ifstream in(argv[i],std::ios::binary);std::string text((std::istreambuf_iterator<char>(in)),{});clubcoach::Profile p;std::istringstream source(text);assert(clubcoach::parse(source,i==1?1043:1629,p));assert(p.starters.size()==11);assert(p.stats.at("total")[0]==p.stats.at("home")[0]+p.stats.at("away")[0]);assert(!p.competitions.empty());std::istringstream foreign(text);assert(!clubcoach::parse(foreign,9999,p));auto corrupt=text;auto at=corrupt.find("S\ttotal\t");assert(at!=corrupt.npos);corrupt.replace(at,7,"S\tbogus");std::istringstream broken(corrupt);assert(!clubcoach::parse(broken,p.club,p));}std::cout<<"PASS coach profile: real two-club data, identity, XI, venue totals and malformed/cross-club rejection\n";
}
