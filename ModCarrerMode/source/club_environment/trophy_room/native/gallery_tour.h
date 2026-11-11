#pragma once
#include "../../room/native/motions.h"
#include <vector>
#include <string>
#include <cstring>
namespace gallery_tour {
using panorama::Pose;using panorama::Vec;
struct Visit {unsigned slot=0;Pose wide{},detail{};};
inline Pose overview(){return {{0,166,660},{0,155,-380},70};}
inline Pose blend(Pose a,Pose b,float t){return {panorama::mix(a.eye,b.eye,t),panorama::mix(a.target,b.target,t),a.fov+(b.fov-a.fov)*t};}
// Left bays run front-to-back on screen; right bays run back-to-front.
// Preserve the physical slot ID for plaques, cup picking and gallery links.
inline void spatialOrder(std::vector<Visit>&visits){
 std::stable_sort(visits.begin(),visits.end(),[](const Visit&a,const Visit&b){
  const auto key=[](unsigned slot){return slot<15?14-slot:slot;};return key(a.slot)<key(b.slot);
 });
}
inline bool valid(Pose p){for(float v:{p.eye.x,p.eye.y,p.eye.z,p.target.x,p.target.y,p.target.z,p.fov})if(!std::isfinite(v))return false;return p.fov>=25&&p.fov<=85&&std::abs(p.eye.x)<=600&&std::abs(p.eye.z)<=850&&p.eye.y>=70&&p.eye.y<=300;}
struct Tour {
 std::vector<Visit> visits;int index=-1;bool detail=false,automatic=true;uint64_t changed=0;Pose from=overview();
 void reset(std::vector<Visit> next,uint64_t now){spatialOrder(next);visits=std::move(next);index=-1;detail=false;automatic=true;changed=now;from=overview();}
 void replace(std::vector<Visit> next,uint64_t now){
  const auto current=pose(now);const int slot=selected();spatialOrder(next);visits=std::move(next);index=-1;
  for(unsigned i=0;i<visits.size();++i)if(int(visits[i].slot)==slot){index=int(i);break;}
  if(index<0)detail=false;from=current;changed=now;
 }
 Pose target()const{return index<0||visits.empty()?overview():(detail?visits[index].detail:visits[index].wide);}
 Pose pose(uint64_t now)const{return gallery_tour::blend(from,target(),panorama::smooth(float(now-changed)/1300.f));}
 void step(int delta,uint64_t now,bool manual=true){if(manual)automatic=false;if(visits.empty())return;from=pose(now);index=index<0?(delta>0?0:int(visits.size())-1):(index+delta+int(visits.size()))%int(visits.size());changed=now;}
 void details(bool on,uint64_t now){if(on)automatic=false;if(visits.empty())return;from=pose(now);if(index<0)index=0;detail=on;changed=now;}
 void select(int next,uint64_t now){if(next<0||next>=int(visits.size()))return;automatic=false;from=pose(now);index=next;detail=true;changed=now;}
 void tick(uint64_t now){if(automatic&&!detail&&now-changed>=9000)step(1,now,false);}
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
