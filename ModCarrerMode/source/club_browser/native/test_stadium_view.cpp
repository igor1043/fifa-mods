#include <cassert>
#include <iostream>
#include "stadium_view.h"
#include "stadium_names.h"
#include <set>
#include <sstream>
int main(){
 assert(!clubstadium::acceptPadToggle(true,false,1000,0));
 assert(!clubstadium::acceptPadToggle(false,false,1100,1000));
 assert(clubstadium::acceptPadToggle(false,false,1400,1000));
 assert(clubstadium::acceptPadToggle(true,true,1100,1000));
 // Automatic camera time must match at 20 and 6.7 FPS and keep advancing
 // without foreground focus. Walking must keep its foreground-only rule.
 clubstadium::View fast,slow;fast.ready=slow.ready=true;
 for(int i=0;i<120;++i)fast.tick(.05f,{},false);
 for(int i=0;i<40;++i)slow.tick(.15f,{},false);
 assert(std::abs(fast.elapsed-slow.elapsed)<.001f&&fast.elapsed>5.99f);
 auto a=fast.pose(),b=slow.pose();assert(std::abs(a.eye.z-b.eye.z)<.1f);
 assert(std::abs(a.eye.z-panorama::sample(36,0).eye.z)>100);
 std::set<unsigned> shots;clubstadium::View tour;tour.restartPanorama();
 for(unsigned i=0;i<panorama::motionCount;++i){shots.insert(tour.shot);if(i<3)assert(tour.shot==36+i);tour.nextShot();}
 assert(shots.size()==panorama::motionCount);
 tour.heightLimit=1000;tour.restartPanorama();assert(tour.shot==38);
 std::istringstream catalog("1043|192|78838|Maracanã|custom|20|14\n243|2|81044|Santiago Bernabéu||20|20\nbad|1|2|Wrong||0|0\n4|261|4|AO VIVO||0|0\n");
 auto names=clubstadium::names(catalog);assert(names.size()==2&&names[1043]=="Maracanã"&&names[243]=="Santiago Bernabéu");
 clubstadium::View view;view.enter(1043);
 view.tick(.05f,{1,1,1,1,true});assert(view.position.x==0&&view.elapsed==0);view.toggle();view.toggleFree();assert(!view.manual());
 view.ready=true;view.tick(.05f);assert(view.elapsed>0);auto shot=view.pose();float matrix[16]{};assert(panorama::matrix(shot,matrix));
 view.toggle();assert(view.walking&&view.position.x==0&&view.position.z==0&&view.position.y==170);
 view.tick(.05f,{1,0,1,0,false},false);assert(view.position.x==0&&view.heading==0);
 view.tick(.05f,{1,0,0,0,false});assert(view.position.x>0&&view.position.z==0);float distance=view.position.x;
 view.tick(.05f,{0,1,0,0,false});assert(view.position.x==distance&&view.position.z>0);
 for(int i=0;i<20000;++i)view.tick(.05f,{1,1,0,1,true});
 assert(view.position.x<=5750&&view.position.z<=3900&&view.position.y==170&&view.tilt<=1.3f);
 assert(panorama::matrix(view.pose(),matrix));view.toggle();assert(!view.manual());
 const auto tourEye=view.pose().eye;
 const float tourTime=view.elapsed;
 view.toggleFree();assert(view.flying&&!view.walking&&view.ownsCamera()&&view.opacity()==0);
 assert(view.position.x==tourEye.x&&view.position.y==tourEye.y&&view.position.z==tourEye.z);
 view.tick(.05f,{0,0,0,0,false,1},false);assert(view.position.y==tourEye.y);
 view.tick(.05f,{0,0,0,0,false,1});assert(view.position.y>tourEye.y&&view.elapsed==tourTime);
 view.tick(.05f,{0,0,0,0,false,-1});assert(view.position.y==tourEye.y);
 view.heading=view.tilt=0;
 for(int i=0;i<2000;++i)view.tick(.05f,{1,1,0,0,true,1});
 assert(view.position.x==view.flightRadius&&view.position.z==view.flightRadius&&view.position.y==view.flightCeiling);
 for(int i=0;i<2000;++i)view.tick(.05f,{0,0,0,0,true,-1});
 assert(view.position.y==view.flightFloor&&panorama::matrix(view.pose(),matrix));
 view.toggleFree();view.tick(.05f);assert(!view.manual()&&view.elapsed>tourTime);
 view.toggle();view.tick(.05f,{1,0,0,0,false});
 const float walkingX=view.position.x;view.toggleFree();assert(view.flying&&view.position.x==walkingX&&view.position.y==170);
 view.toggle();assert(view.walking&&!view.flying&&view.position.x==0);view.toggle();
 view.restartPanorama();view.ready=true;bool nativeWindow=false,returnToMod=false,transition=false;
 for(int i=0;i<1800;++i){view.tick(.2f,{},false);transition|=view.opacity()>0;if(!view.ownsCamera()&&view.opacity()==0)nativeWindow=true;if(nativeWindow&&view.ownsCamera()&&view.shot==37){returnToMod=true;break;}}
 assert(nativeWindow&&returnToMod&&transition);
 view.enter(131);assert(view.club==131&&!view.ready&&!view.manual()&&view.elapsed==0);
 std::cout<<"PASS stadium tour: panorama, walking and free flight, loading gate, timing, position and bounds, focus and club reset\n";
}
