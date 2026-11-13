#include "model.h"
#include <cassert>
#include <iostream>
int main(int argc,char** argv){
 const char* row="54\tBrasil\t54\t30\t1\t2\tFederação Piauiense\t4\t0\t130248\tFIFA Friends\tBrasília\t-15.793889\t-47.882778\t70\t70\t70\t70";
 clubs::Model old;std::istringstream legacy(std::string(row)+"\n");assert(old.load(legacy));assert(old.club().divisionLabel.empty());
 clubs::Model current;std::istringstream extended(std::string(row)+"\tFederação estadual · PI\n");assert(current.load(extended));
 assert(current.club().divisionLabel=="Federação estadual · PI");assert(current.club().nation==54);assert(current.club().level==4);
 assert(std::abs(current.club().lat+15.793889f)<.001f&&std::abs(current.club().lon+47.882778f)<.001f);
 auto point=clubs::project(current.club().lat,current.club().lon,-current.club().lon*.01745329252f,current.club().lat*.01745329252f,1.3f);assert(point.visible);
 if(argc==2){
  clubs::Model installed;std::ifstream file(argv[1]);assert(installed.load(file));
  assert(installed.rows.size()==1657);assert(installed.choose(130248));assert(installed.club().city=="Brasília");
  assert(std::abs(installed.club().lat+15.793889f)<.001f&&std::abs(installed.club().lon+47.882778f)<.001f);
  assert(installed.choose(129923));assert(installed.club().nation==129&&installed.choices(2).size()==16);
  assert(installed.choose(130921));assert(installed.club().nation==7);
  assert(installed.choose(112254));assert(installed.club().nation==50&&installed.club().level==4);
  assert(installed.club().divisionLabel=="4ª divisão · Inglaterra");
  assert(installed.choose(121739));assert(installed.club().nation==198&&installed.club().world==137);
  assert(installed.choose(111393));assert(installed.club().nation==195&&installed.club().world==138);
  auto countries=installed.choices(0);for(int i=0;i<int(countries.size());++i)installed.step(0,1);
  std::cout<<"PASS: full installed catalog; 1657 clubs, Morocco 16, cross-border leagues, Brazil and world coordinates\n";
 }
 std::cout<<"PASS: legacy and configured globe catalogs; state labels and coordinates preserved\n";
}
