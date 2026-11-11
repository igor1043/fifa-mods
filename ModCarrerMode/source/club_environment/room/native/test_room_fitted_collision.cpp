#include <cassert>
#include <fstream>
#include <iostream>
#include "room_free_camera.h"
int main(int argc,char**argv){
 assert(argc==2);std::ifstream source(argv[1]);assert(source);
 room_cinema::Tour tour;room_cinema::Box box;
 while(source>>box.lo.x>>box.lo.y>>box.lo.z>>box.hi.x>>box.hi.y>>box.hi.z)tour.obstacles.push_back(box);
 assert(tour.obstacles.size()>100&&tour.obstacles.size()<1024);
 room_free::Walk body;
 for(auto p:std::array<panorama::Vec,5>{{{0,165,140},{-280,165,335},{0,165,-515},{-790,165,0},{790,165,0}}})assert(!body.clear(p,tour));
 for(auto p:std::array<panorama::Vec,3>{{{0,165,750},{180,165,1520},{-545,165,1520}}})assert(body.clear(p,tour));
 unsigned checked=0;
 for(const auto& b:tour.obstacles){
  if(b.lo.y>165||b.hi.y<30)continue;
  auto center=(b.lo+b.hi)*.5f;center.y=165;assert(!body.clear(center,tour));++checked;
 }
 assert(checked>50);
 // Walk through each real door in both directions at different frame rates.
 for(float x:{180.f,-545.f})for(int fps:{30,120}){
  panorama::Pose start{{x,165,1440},{x,165,1800},70};room_free::Walk walk;assert(walk.enter(start,tour));
  for(int i=0;i<fps*2;++i)walk.tick({1,0,0,0,false},1.f/fps,tour);
  assert(walk.position.z>1700&&walk.position.z<1781);
  for(int i=0;i<fps*2;++i)walk.tick({-1,0,0,0,false},1.f/fps,tour);
  assert(walk.position.z<1460);
 }
 std::cout<<"PASS current V3 collision: "<<tour.obstacles.size()<<" bounds, "<<checked<<" solid body checks, table/ball trolley/board/lockers and both service doorways at 30/120 FPS\n";
}
