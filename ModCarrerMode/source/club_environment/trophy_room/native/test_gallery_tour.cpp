#include "gallery_tour.h"
#include "gallery_light.h"
#include "gallery_inspect.h"
#include <cassert>
#include <iostream>
int main(){
 using namespace gallery_tour;
 Visit a{0,{{-230,165,-555},{-465,140,-590},54},{{-275,148,-576},{-465,140,-655},55}};
 Visit b{15,{{230,165,-555},{465,140,-590},54},{{275,148,-576},{465,140,-525},55}};
 Tour t;t.reset({b,a},100);assert(t.selected()==0&&t.detail&&!t.automatic);
 t.tick(9099);t.tick(9100);t.tick(999999);assert(t.selected()==0&&t.detail);
 assert(valid(t.pose(100)));assert(t.pose(100).eye.x==a.detail.eye.x);
 t.details(false,11000);assert(t.pose(11000).eye.x==a.wide.eye.x);
 t.details(true,11001);assert(t.pose(11001).eye.x==a.detail.eye.x);
 t.step(1,100000);assert(t.selected()==15&&t.detail);
 const auto begin=t.pose(100000);assert(begin.eye.x==a.detail.eye.x);
 const auto midway=t.pose(100000+t.duration/2);assert(midway.eye.x>a.detail.eye.x&&midway.eye.x<b.detail.eye.x);
 assert(t.pose(100000+t.duration).eye.x==b.detail.eye.x);
 t.details(false,101500);assert(!t.detail);t.tick(110500);assert(t.selected()==15&&!t.automatic);
 // Neither entry, refresh nor elapsed time starts a trophy animation.
 t.replace({a,b},110600);t.tick(200000);assert(t.selected()==15&&!t.automatic);
 t.reset({a,b},200000);assert(!t.automatic&&t.selected()==0);t.tick(209000);assert(t.selected()==0);
 t.tick(218000);assert(t.selected()==0);
 t.step(1,219000);assert(t.selected()==15&&!t.automatic);t.tick(400000);assert(t.selected()==15);
 t.reset({a,b},0);t.step(-1,1);assert(t.selected()==0&&!t.duration);
 t.reset({},0);t.tick(90000);t.details(true,90001);assert(t.selected()==-1&&!t.detail);
 t.reset({a,b},0);t.step(1,1);t.details(true,1400);const auto before=t.pose(2800);
 t.replace({a,b},2800);assert(t.selected()==15&&t.detail);const auto after=t.pose(2800);
 assert(after.eye.x==before.eye.x&&after.eye.z==before.eye.z);
 t.replace({},2801);assert(!t.detail&&t.selected()==-1);
 assert(!valid({{0,10,0},{0,0,0},50}));assert(!valid({{0,160,0},{0,0,0},100}));
 assert(std::string(material("trophy_metal_mat:custom_lod.000"))=="trophy_metal");
 assert(std::string(material("trophy_wood"))=="trophy_wood");
 assert(std::string(material("trophy_glass"))=="trophy_glass");
 assert(std::string(material("trophy_ribbon_colored"))=="trophy_ribbon_colored");
 for(float x:{-565.f,565.f})for(int i=0;i<15;++i){auto sh=gallery_light::coefficients(x,150,-630.f+i*90);for(float v:sh)assert(std::isfinite(v));assert(sh[0]>.6f/.2821f);}
 auto centerLight=gallery_light::coefficients(0,150,0);assert(centerLight[2]>0);assert(std::abs(centerLight[1])<1e-4);
 auto leftLight=gallery_light::coefficients(-430,150,0),rightLight=gallery_light::coefficients(430,150,0);
 assert(std::abs(leftLight[1]+rightLight[1])<1e-4);assert(std::abs(leftLight[0]-rightLight[0])<1e-4);
 gallery_inspect::Controls inspect;inspect.step(100,100,-100);assert(inspect.tilt==.65f&&inspect.zoom==-30.f&&std::abs(inspect.yaw)<3.15f);
 gallery_inspect::Matrix base{1,0,0,0,0,1,0,0,0,0,1,0,-100465,1102,-630,1};float pivot[]={-100465,1142,-630};
 const auto rotated=gallery_inspect::rotate(base,pivot,1.57f);assert(rotated[12]==base[12]&&rotated[13]==base[13]&&rotated[14]==base[14]);
 assert(gallery_inspect::slot(pivot)==0);pivot[0]=-99535;pivot[2]=630;assert(gallery_inspect::slot(pivot)==29);
 auto c=overview();Visit center{3,{{0,160,200},{0,155,-200},55},{{0,160,200},{0,155,-200},55}};
 assert(pick({center},c,16.f/9,.5f,.5f)==0);assert(pick({center},c,16.f/9,.5f,.95f)==-1);assert(pick({center},c,16.f/9,.02f,.5f)==-1);
 // Plaque hit areas follow their cups when the display cases move outward.
 for(float side:{-1.f,1.f}){
  Visit widened{unsigned(side<0?0:15),{{side*330,165,35},{side*565,150,0},54},{{side*375,158,14},{side*565,150,0},55}};
  assert(valid(widened.wide)&&valid(widened.detail));
  auto forward=c.target-c.eye;assert(panorama::unit(forward));auto right=panorama::cross(forward,{0,1,0});assert(panorama::unit(right));auto up=panorama::cross(right,forward);
  const auto delta=panorama::Vec{side*494,93,0}-c.eye;const float depth=panorama::dot(forward,delta),fy=std::tan(c.fov*.00872664626f);
  const float nx=.5f+panorama::dot(right,delta)/(2*depth*fy*(16.f/9)),ny=.5f-panorama::dot(up,delta)/(2*depth*fy);
  assert(pick({widened},c,16.f/9,nx,ny)==0);
 }
 // The chronological publication order is retained across both case walls.
 Visit l0=a,l1=a,r0=b,r1=b;l0.slot=0;l1.slot=1;r0.slot=15;r1.slot=16;
 t.reset({r1,l1,r0,l0},0);assert(t.selected()==0);t.step(1,1);assert(t.selected()==1);t.step(1,2);assert(t.selected()==15);t.step(1,3);assert(t.selected()==16);t.step(1,4);assert(t.selected()==16);t.step(-1,5);assert(t.selected()==15);
 // A refresh preserves an in-flight manual transition rather than jumping
 // to another cup or restarting at the room overview.
 t.reset({a,b},1000);t.step(1,1100);const auto moving=t.pose(1250);const auto finish=t.changed+t.duration;
 t.replace({a,b},1250);assert(t.selected()==15&&t.detail&&t.changed+t.duration==finish);
 assert(std::abs(t.pose(1250).eye.x-moving.eye.x)<.001f);
 // Opposing showcase orientations keep a nonzero look direction throughout
 // the transition. Linear target interpolation used to flip at the centre.
 Pose p0{{-275,150,0},{-465,145,0},55},p1{{275,150,0},{465,145,0},55};
 float previousYaw=std::atan2((p0.target-p0.eye).x,-(p0.target-p0.eye).z);
 for(int i=0;i<=100;++i){auto p=gallery_tour::blend(p0,p1,float(i)/100);auto d=p.target-p.eye;assert(panorama::unit(d));
  const float yaw=std::atan2(d.x,-d.z);assert(std::abs(std::remainder(yaw-previousYaw,6.28318530718f))<.1f);previousYaw=yaw;assert(valid(p));}
 // A detail stays beside the right history panel at each display aspect and
 // zoom level; projecting the actual cup checks its visible screen position.
 for(float aspect:{16.f/9,21.f/9,32.f/9})for(float side:{-1.f,1.f})for(float fov:{25.f,55.f,75.f}){
  panorama::Pose centered{{side*275,150,14},{side*465,142,0},fov};
  const auto framed=gallery_inspect::frame(centered,aspect);auto forward=framed.target-framed.eye;assert(panorama::unit(forward));
  auto right=panorama::cross(forward,{0,1,0});assert(panorama::unit(right));
  const auto delta=centered.target-framed.eye;const float depth=panorama::dot(forward,delta);
  const float x=.5f+panorama::dot(right,delta)/(2*depth*std::tan(fov*.00872664626f)*aspect);
  const float expected=.5f+(530.f-800)*std::min(1.f/1600,1.f/(900*aspect));
  assert(depth>0&&std::abs(x-expected)<.004f);assert(framed.eye.x==centered.eye.x&&framed.eye.z==centered.eye.z);
 }
 assert(gallery_inspect::triggerZoom(0,0)==0&&gallery_inspect::triggerZoom(30,30)==0);
 assert(gallery_inspect::triggerZoom(255,0)==1&&gallery_inspect::triggerZoom(0,255)==-1);
 assert(gallery_inspect::triggerZoom(255,255)==0);
 std::cout<<"Gallery: consecutive bounded selection, short manual transitions, continuous camera orientation and no automatic tour OK\n";
}
