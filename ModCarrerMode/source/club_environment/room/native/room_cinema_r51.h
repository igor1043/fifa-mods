#pragma once
#include "motions.h"
#include <vector>
#include <array>
namespace room_cinema {
using panorama::Vec;using panorama::Pose;
struct Box {Vec lo,hi;};
struct Focus {unsigned number=0;Vec eye,target;};
struct Shot {Pose pose;double hold=0,travel=0;};
struct Tour {std::vector<Box> obstacles;std::vector<Focus> focus,shirts;std::vector<Pose> path,details,nav,extra;std::vector<Shot> sequence;double duration=0;};
inline bool collision(Vec p,const Tour&tour,float radius=40.f){
 for(const auto&b:tour.obstacles){const Vec q{std::clamp(p.x,b.lo.x,b.hi.x),std::clamp(p.y,b.lo.y,b.hi.y),std::clamp(p.z,b.lo.z,b.hi.z)};const auto v=p-q;if(panorama::dot(v,v)<radius*radius)return true;}return false;
}
inline float yaw(const Pose&p){const auto v=p.target-p.eye;return std::atan2(v.x,v.z);}
inline float pitch(const Pose&p){const auto v=p.target-p.eye;return std::atan2(v.y,std::sqrt(v.x*v.x+v.z*v.z));}
inline float angle(float value){while(value>3.14159265f)value-=6.2831853f;while(value< -3.14159265f)value+=6.2831853f;return value;}
inline void compile(Tour&tour){
 tour.sequence.clear();tour.duration=0;
 auto add=[&](Pose p,double hold){tour.sequence.push_back({p,hold,0});};
 if(!tour.path.empty())add(tour.path[0],2.5);
 // The helper orders real lockers physically around the room, rather than
 // crossing from left to right at every roster index.
 for(const auto&s:tour.shirts)add({s.eye,s.target,54},s.number==9||s.number==10?2.8:1.);
 for(const auto&p:tour.details)add(p,5.);
 for(const auto&f:tour.focus)add({f.eye,f.target,47},4.);
 for(size_t i=1;i<tour.path.size();++i)add(tour.path[i],2.);
 for(const auto&p:tour.extra)add(p,5.);
 for(size_t i=0;i<tour.sequence.size();++i){auto&a=tour.sequence[i];const auto&b=tour.sequence[(i+1)%tour.sequence.size()];auto delta=b.pose.eye-a.pose.eye;
  const double distance=std::sqrt(panorama::dot(delta,delta));const double turn=std::max(std::abs(angle(yaw(b.pose)-yaw(a.pose))),std::abs(pitch(b.pose)-pitch(a.pose)))*57.295779513;
  // Quintic interpolation has a maximum derivative of 1.875. These budgets
  // bound translation, rotation and zoom even on the long scene transitions.
  a.travel=std::max({3.,distance*1.88/55.,turn*1.88/12.,std::abs(b.pose.fov-a.pose.fov)*1.88/8.});tour.duration+=a.hold+a.travel;
 }
}
inline Pose sample(double elapsed,const Tour&tour={}){
 if(tour.sequence.empty()||tour.duration<=0)return {{0,187,750},{0,170,-275},74};
 double t=std::fmod(std::max(0.,elapsed),tour.duration);
 for(size_t i=0;i<tour.sequence.size();++i){const auto&a=tour.sequence[i];const auto&b=tour.sequence[(i+1)%tour.sequence.size()];
  if(t>=a.hold+a.travel){t-=a.hold+a.travel;continue;}
  if(t<a.hold)return a.pose;
  const float u=static_cast<float>((t-a.hold)/a.travel);const float ease=u*u*u*(10.f+u*(-15.f+6.f*u));
  const auto eye=a.pose.eye+(b.pose.eye-a.pose.eye)*ease;
  const float y=yaw(a.pose)+angle(yaw(b.pose)-yaw(a.pose))*ease,p=pitch(a.pose)+(pitch(b.pose)-pitch(a.pose))*ease,c=std::cos(p);
  return {eye,eye+Vec{std::sin(y)*c,std::sin(p),std::cos(y)*c}*1000.f,a.pose.fov+(b.pose.fov-a.pose.fov)*ease};
 }
 return tour.sequence.front().pose;
}
}
