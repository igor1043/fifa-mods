#pragma once
#include "../../room/native/motions.h"
#include <vector>
#include <string>
#include <cstring>
namespace gallery_tour {
using panorama::Pose;using panorama::Vec;
struct Visit {unsigned slot=0;Pose wide{},detail{};};
inline Pose overview(){return {{0,166,660},{0,155,-380},70};}
inline Pose blend(Pose a,Pose b,float t){
 t=std::clamp(t,0.f,1.f);if(t<=0)return a;if(t>=1)return b;
 const auto da=a.target-a.eye,db=b.target-b.eye;
 const float ya=std::atan2(da.x,-da.z),yb=std::atan2(db.x,-db.z);
 const float pa=std::atan2(da.y,std::hypot(da.x,da.z)),pb=std::atan2(db.y,std::hypot(db.x,db.z));
 const float yaw=ya+std::remainder(yb-ya,6.28318530718f)*t,pitch=pa+(pb-pa)*t;
 const auto eye=panorama::mix(a.eye,b.eye,t);
 const float distance=std::sqrt(panorama::dot(da,da))*(1-t)+std::sqrt(panorama::dot(db,db))*t;
 const Vec forward{std::sin(yaw)*std::cos(pitch),std::sin(pitch),-std::cos(yaw)*std::cos(pitch)};
 return {eye,eye+forward*std::max(1.f,distance),a.fov+(b.fov-a.fov)*t};
}
// The publication assigns slots from newest conquest to oldest. Pedestal
// position must never reverse that order or change the gallery selection.
inline void publicationOrder(std::vector<Visit>&visits){
 std::stable_sort(visits.begin(),visits.end(),[](const Visit&a,const Visit&b){return a.slot<b.slot;});
}
inline bool valid(Pose p){for(float v:{p.eye.x,p.eye.y,p.eye.z,p.target.x,p.target.y,p.target.z,p.fov})if(!std::isfinite(v))return false;return p.fov>=25&&p.fov<=85&&std::abs(p.eye.x)<=600&&std::abs(p.eye.z)<=850&&p.eye.y>=70&&p.eye.y<=300;}
struct Tour {
 std::vector<Visit> visits;int index=-1;bool detail=false,automatic=false;uint64_t changed=0,duration=0;Pose from=overview();
 void reset(std::vector<Visit> next,uint64_t now){publicationOrder(next);visits=std::move(next);index=visits.empty()?-1:0;detail=!visits.empty();automatic=false;changed=now;duration=0;from=target();}
 void replace(std::vector<Visit> next,uint64_t now){
  const auto current=pose(now);const int slot=selected();const auto remaining=duration&&now<changed+duration?changed+duration-now:0;
  publicationOrder(next);visits=std::move(next);index=-1;automatic=false;
  for(unsigned i=0;i<visits.size();++i)if(int(visits[i].slot)==slot){index=int(i);break;}
  if(index<0){index=visits.empty()?-1:0;detail=!visits.empty();duration=0;from=target();}
  else{duration=remaining;from=remaining?current:target();}changed=now;
 }
 Pose target()const{return index<0||visits.empty()?overview():(detail?visits[index].detail:visits[index].wide);}
 Pose pose(uint64_t now)const{return duration?gallery_tour::blend(from,target(),panorama::smooth(now>=changed?float(now-changed)/float(duration):0.f)):target();}
 void transition(Pose current,uint64_t now){from=current;changed=now;const auto distance=target().eye-current.eye;duration=uint64_t(std::clamp(350.f+std::sqrt(panorama::dot(distance,distance))*.35f,350.f,850.f));}
 void step(int delta,uint64_t now,bool=true){
  automatic=false;if(visits.empty())return;
  const int next=index<0?(delta>0?0:int(visits.size())-1):std::clamp(index+delta,0,int(visits.size())-1);
  if(next==index){if(!detail)details(true,now);return;}const auto current=pose(now);index=next;detail=true;transition(current,now);
 }
 void details(bool on,uint64_t now){automatic=false;if(visits.empty())return;if(index<0)index=0;detail=on;from=target();changed=now;duration=0;}
 void select(int next,uint64_t now){if(next<0||next>=int(visits.size()))return;automatic=false;index=next;detail=true;from=target();changed=now;duration=0;}
 void tick(uint64_t){} // Manual selection only; elapsed time never changes cups.
 int selected()const{return index>=0&&!visits.empty()?int(visits[index].slot):-1;}
};
inline int pick(const std::vector<Visit>&visits,Pose camera,float aspect,float nx,float ny){
 if(nx<0||nx>1||ny<.18f||ny>.80f||aspect<=0)return -1;
 auto forward=camera.target-camera.eye;if(!panorama::unit(forward))return -1;
 auto right=panorama::cross(forward,{0,1,0});if(!panorama::unit(right))return -1;auto up=panorama::cross(right,forward);
 const float fy=std::tan(camera.fov*.00872664626f),fx=fy*aspect;int selected=-1;float best=1e10f;
 for(unsigned i=0;i<visits.size();++i)for(int plaque=0;plaque<2;++plaque){
  auto point=visits[i].wide.target;if(plaque){point.x=std::copysign(std::max(0.f,std::abs(point.x)-71.f),point.x);point.y=93;}
  const auto d=point-camera.eye;const float depth=panorama::dot(forward,d);if(depth<20)continue;
  const float x=.5f+panorama::dot(right,d)/(2*depth*fx),y=.5f-panorama::dot(up,d)/(2*depth*fy);
  // A physical hit area around the cup/plaque shrinks correctly with distance.
  const float radius=std::clamp(55.f/(2*depth*fy),.025f,.12f);
  const float distance=(nx-x)*(nx-x)*aspect*aspect+(ny-y)*(ny-y);
  if(distance<radius*radius&&depth<best){selected=int(i);best=depth;}
 }
 return selected;
}
// These are the same attribulator classes selected by FIFA's assets/trophy.lua.
// Custom RX3 mesh names retain their native material token when present.
inline const char* material(const std::string& submesh){
 for(const char* v:{"trophy_coloredmetal","trophy_ribbon_colored","trophy_wood","trophy_plastic","trophy_ribbon","trophy_glass","trophy_metal"})if(submesh.find(v)!=submesh.npos)return v;
 return "trophy_metal";
}
}
