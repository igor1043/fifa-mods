#include <cassert>
#include <iostream>
#include <string>
#include <fstream>
#include "room_free_camera.h"
#include "room_scene_command.h"
int main(int argc,char**argv){
 room_cinema::Tour tour; // Wall plus central furniture, units are centimetres.
 tour.obstacles={{{-500,0,-500},{500,320,-490}},{{-40,0,-40},{40,110,40}}};
 tour.path={{{0,165,250},{0,165,-200},70}};
 room_free::Walk camera;assert(camera.enter(tour.path[0],tour));assert(camera.active&&camera.position.y==165);
 for(int i=0;i<300;++i)camera.tick({1,0,0,0,true},1.f/60,tour);
 assert(camera.position.z>63&&camera.position.z<70); // no tunnelling through table
 auto before=camera.position;camera.tick({1,0,0,0,false},0,tour);assert(panorama::dot(camera.position-before,camera.position-before)==0);
 room_free::Walk diagonal,straight;auto start=tour.path[0];start.eye={300,165,350};start.target={300,165,500};
 assert(diagonal.enter(start,tour)&&straight.enter(start,tour));before=start.eye;
 diagonal.tick({1,1,0,0,false},.05f,tour);straight.tick({1,0,0,0,false},.05f,tour);
 assert(std::abs(std::hypot(diagonal.position.x-before.x,diagonal.position.z-before.z)-std::hypot(straight.position.x-before.x,straight.position.z-before.z))<.001);
 camera.tick({0,0,0,100,false},.05f,tour);assert(camera.tilt==1.25f);camera.tick({0,0,0,-100,false},.05f,tour);assert(camera.tilt==-1.25f);
 camera.tick({0,0,1000,0,false},.05f,tour);assert(std::abs(camera.heading)<=3.141593f);
 camera.position={0,165,-400};camera.heading=3.14159265f;
 for(int i=0;i<300;++i)camera.tick({1,0,0,0,true},1.f,tour);
 assert(camera.position.z>=-467);assert(camera.position.y==165);
 start.eye={0,165,0};assert(camera.enter(start,tour));assert(camera.position.z==250); // blocked entry chooses safe anchor
 // Compare movement to the actual FIFA camera matrix, not the heading formula.
 // This catches mirrored strafing/yaw even when positions otherwise look valid.
 room_cinema::Tour empty;
 for(int heading=0;heading<8;++heading){
  float angle=heading*.785398163f;
  panorama::Pose from{{0,165,400},{std::sin(angle)*1000,165,400+std::cos(angle)*1000},70};
  float matrix[16];assert(panorama::matrix(from,matrix));
  panorama::Vec viewRight{matrix[0],matrix[1],matrix[2]},forward{-matrix[8],-matrix[9],-matrix[10]};
  for(auto direction:std::array<std::array<float,2>,4>{{{{1,0}},{{-1,0}},{{0,1}},{{0,-1}}}}){
   room_free::Walk walk;assert(walk.enter(from,empty));auto origin=walk.position;
   walk.tick({direction[0],direction[1],0,0,false},.02f,empty);auto travelled=walk.position-origin;
   auto expected=forward*direction[0]+viewRight*direction[1];
   assert(panorama::dot(travelled,expected)>3.39f);
  }
  room_free::Walk look;assert(look.enter(from,empty));auto oldDirection=look.pose().target-look.pose().eye;
  look.tick({0,0,.1f,0,false},.02f,empty);auto newDirection=look.pose().target-look.pose().eye;
  assert(panorama::dot(newDirection-oldDirection,viewRight)>90.f);
 }
 room_free::Walk walking;start.eye={300,165,350};start.target={300,165,1000};assert(walking.enter(start,empty));
 float largestBob=0;before=walking.position;
 for(int i=0;i<60;++i){auto pose=walking.tick({1,0,0,0,false},1.f/60,empty);largestBob=(std::max)(largestBob,std::abs(pose.eye.y-165));assert(walking.position.y==165);}
 assert(std::abs(walking.position.z-before.z-170)<.02f);assert(largestBob>.6f&&largestBob<=.91f);
 auto direction=walking.pose().target-walking.pose().eye;
 assert(std::abs(direction.y)<.001f); // footsteps do not shake pitch/aim
 for(int i=0;i<90;++i)walking.tick({},1.f/60,empty);
 assert(walking.stepAmount==0&&walking.stepOffset.y==0&&walking.stepOffset.x==0&&walking.stepOffset.z==0);
 room_free::Walk lowFps,highFps;assert(lowFps.enter(start,empty)&&highFps.enter(start,empty));
 for(int i=0;i<30;++i)lowFps.tick({1,0,0,0,false},1.f/30,empty);
 for(int i=0;i<120;++i)highFps.tick({1,0,0,0,false},1.f/120,empty);
 assert(std::abs(lowFps.position.z-highFps.position.z)<.03f&&std::abs(lowFps.pose().eye.y-highFps.pose().eye.y)<.02f);
 assert(camera.stepAmount==0); // the earlier blocked walk settled its steps
 // Thin furniture between the former sample heights still blocks the body.
 room_cinema::Tour thin;thin.obstacles={{{-100,54,-1},{100,56,1}}};
 room_free::Walk body;assert(!body.clear({0,165,0},thin));assert(body.clear({0,165,30},thin));
 start.eye={0,165,80};start.target={0,165,-100};assert(body.enter(start,thin));
 for(int i=0;i<90;++i)body.tick({1,0,0,0,true},1.f/30,thin);
 assert(body.position.z>=24); // no tunnelling at low frame rates
 if(argc==3){
  auto load=[](const char*path){std::ifstream file(path);assert(file);room_cinema::Tour t;room_cinema::Box b;while(file>>b.lo.x>>b.lo.y>>b.lo.z>>b.hi.x>>b.hi.y>>b.hi.z)t.obstacles.push_back(b);assert(!t.obstacles.empty());return t;};
  auto old=load(argv[1]),corrected=load(argv[2]);room_free::Walk test;
  assert(!test.clear({180,165,1020},old));assert(test.clear({180,165,1020},corrected));
  for(float x:{165.f,180.f,195.f}){
   start={{x,165,850},{x,165,1300},70};assert(test.enter(start,corrected));
   for(int i=0;i<80;++i)test.tick({1,0,0,0,false},1.f/60,corrected);
   assert(test.position.z>1070); // through the real coach-room doorway
   for(int i=0;i<80;++i)test.tick({-1,0,0,0,false},1.f/60,corrected);
   assert(std::abs(test.position.z-850)<.1f);
  }
  assert(!test.clear({90,165,950},corrected)); // wall left of coach door
  assert(!test.clear({270,165,950},corrected)); // wall right of coach door
  assert(!test.clear({245,165,1010},corrected)); // actual open door leaf
 }
 room_command::Request request;
 for(int code:{-4,-5}){std::string wire="S16ROOM2|1043|0123456789abcdef|7|"+std::to_string(code)+"|ENDROOM";assert(room_command::parse(wire.c_str(),request)&&request.code==code);}
 assert(!room_command::parse("S16ROOM2|1043|0123456789abcdef|7|-6|ENDROOM",request));
 std::cout<<"PASS free camera: native movement axes, footsteps, 30/120 FPS, continuous capsule/thin furniture, real coach doorway entry/exit, solid walls/door leaf and scoped commands\n";
}
