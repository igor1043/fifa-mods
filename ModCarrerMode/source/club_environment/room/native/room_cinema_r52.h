#pragma once
#include "room_cinema_r51.h"
#include <random>
#include <numeric>
#include <limits>
namespace room_cinema {
inline Pose blend(const Pose&a,const Pose&b,double t){
 const float u=static_cast<float>(std::clamp(t,0.,1.));const float e=panorama::smooth(u);
 const auto eye=a.eye+(b.eye-a.eye)*e;
 const float y=yaw(a)+angle(yaw(b)-yaw(a))*e,p=pitch(a)+(pitch(b)-pitch(a))*e,c=std::cos(p);
 return {eye,eye+Vec{std::sin(y)*c,std::sin(p),std::cos(y)*c}*1000.f,a.fov+(b.fov-a.fov)*e};
}
inline double travelTime(const Pose&a,const Pose&b){
 const auto d=b.eye-a.eye;const double distance=std::sqrt(panorama::dot(d,d));
 const double turn=std::max(std::abs(angle(yaw(b)-yaw(a))),std::abs(pitch(b)-pitch(a)))*57.295779513;
 const bool medical=a.eye.z>942||b.eye.z>942;const double speed=medical?45.:55.,rotation=medical?10.:12.;
 return std::max({medical?2.5:1.8,distance*1.88/speed,turn*1.88/rotation,std::abs(b.fov-a.fov)*1.88/8.});
}
inline bool clearSegment(Vec a,Vec b,const Tour&t){
 const auto d=b-a;const int steps=std::max(1,static_cast<int>(std::ceil(std::sqrt(panorama::dot(d,d))/8.f)));
 for(int i=0;i<=steps;++i)if(collision(a+d*(static_cast<float>(i)/steps),t))return false;
 return true;
}
inline bool poseSafe(const Pose&p,const Tour&t){
 if(collision(p.eye,t))return false;
 auto forward=p.target-p.eye;const float length=std::sqrt(panorama::dot(forward,forward));if(length<1)return false;forward=forward*(1.f/length);
 Vec right{forward.z,0,-forward.x};const float r=std::sqrt(panorama::dot(right,right));if(r<.1f)return false;right=right*(1.f/r);
 Vec up{forward.y*right.z,forward.z*right.x-forward.x*right.z,-forward.y*right.x};
 const float height=40.f*std::tan(p.fov*.00872664626f),width=height*2.f;const auto center=p.eye+forward*40.f;
 for(float x:{-1.f,0.f,1.f})for(float y:{-1.f,0.f,1.f})if(collision(center+right*(x*width)+up*(y*height),t,8.f))return false;
 return true;
}
inline bool clearPoseSegment(const Pose&a,const Pose&b,const Tour&t){
 Tour local;const Vec lo{std::min(a.eye.x,b.eye.x)-100,std::min(a.eye.y,b.eye.y)-100,std::min(a.eye.z,b.eye.z)-100},hi{std::max(a.eye.x,b.eye.x)+100,std::max(a.eye.y,b.eye.y)+100,std::max(a.eye.z,b.eye.z)+100};
 for(const auto&box:t.obstacles)if(box.hi.x>=lo.x&&box.lo.x<=hi.x&&box.hi.y>=lo.y&&box.lo.y<=hi.y&&box.hi.z>=lo.z&&box.lo.z<=hi.z)local.obstacles.push_back(box);
 const auto d=b.eye-a.eye;const int steps=std::max(16,static_cast<int>(std::ceil(std::sqrt(panorama::dot(d,d))/6.f)));
 for(int i=0;i<=steps;++i)if(!poseSafe(blend(a,b,static_cast<double>(i)/steps),local))return false;
 return true;
}
// Route through collision-tested camera anchors. Random endpoints never imply
// travelling in a straight line through the table or a row of lockers.
inline std::vector<Pose> route(const Pose&from,const Pose&to,const Tour&t){
 if(!poseSafe(from,t)||!poseSafe(to,t))return {};
 std::vector<Pose> nodes{from,to};nodes.insert(nodes.end(),t.path.begin(),t.path.end());nodes.insert(nodes.end(),t.nav.begin(),t.nav.end());
 const size_t n=nodes.size();std::vector<double> cost(n,std::numeric_limits<double>::infinity());std::vector<int> previous(n,-1);std::vector<bool> done(n,false);cost[0]=0;
 for(size_t k=0;k<n;++k){size_t a=n;for(size_t i=0;i<n;++i)if(!done[i]&&(a==n||cost[i]<cost[a]))a=i;
  if(a==n||!std::isfinite(cost[a]))break;done[a]=true;if(a==1)break;
  for(size_t b=0;b<n;++b)if(!done[b]&&clearPoseSegment(nodes[a],nodes[b],t)){
   const auto d=nodes[b].eye-nodes[a].eye;const double c=cost[a]+std::sqrt(panorama::dot(d,d))+1;
   if(c<cost[b]){cost[b]=c;previous[b]=static_cast<int>(a);}
  }
 }
 if(previous[1]<0)return {};std::vector<Pose> result;
 for(int i=1;i>0;i=previous[static_cast<size_t>(i)])result.push_back(nodes[static_cast<size_t>(i)]);
 std::reverse(result.begin(),result.end());return result;
}
struct Director {
 Pose current{{0,187,750},{0,170,-275},74},from{},to{};
 std::vector<Pose> pending;std::vector<size_t> queue;
 std::mt19937 random{1};double elapsed=0,duration=0,hold=0;
 bool automatic=true,paused=false,moving=false,initialized=false,manualTravel=false;
 unsigned generation=0;int selected=-1,last=-1;
 void reset(const Tour&t,unsigned stamp,unsigned seed){
  generation=stamp;random.seed(seed);pending.clear();queue.clear();automatic=true;paused=false;moving=false;manualTravel=false;initialized=!t.sequence.empty();selected=-1;last=-1;hold=2.5;
  if(initialized)current=t.sequence.front().pose;
 }
 void refill(const Tour&t){
  std::vector<std::vector<size_t>> groups;
  const size_t first=t.path.empty()?0:1,stop=first+t.shirts.size();
  if(stop>first){std::vector<size_t> walk;for(size_t i=first;i<stop;++i)walk.push_back(i);groups.push_back(std::move(walk));}
  for(size_t i=0;i<t.sequence.size();++i)if((i<first||i>=stop)&&t.sequence[i].pose.eye.z<942)groups.push_back({i});
  std::shuffle(groups.begin(),groups.end(),random);
  if(groups.size()>1&&!groups.front().empty()&&static_cast<int>(groups.front().front())==last)std::swap(groups.front(),groups.back());
  queue.clear();for(const auto&g:groups)queue.insert(queue.end(),g.begin(),g.end());
 }
 bool choose(int index,const Tour&t){
  if(index<0||static_cast<size_t>(index)>=t.sequence.size())return false;
  auto next=route(current,t.sequence[static_cast<size_t>(index)].pose,t);if(next.empty())return false;
  pending=std::move(next);moving=false;selected=index;last=index;hold=t.sequence[static_cast<size_t>(index)].hold;return true;
 }
 bool command(int code,const Tour&t){
  if(code==-2){paused=true;return true;}if(code==-3){paused=false;return true;}
  if(code==-1){automatic=true;paused=false;manualTravel=false;pending.clear();moving=false;queue.clear();hold=0;return true;}
  if(code<0||static_cast<size_t>(code)>=t.sequence.size())return false;
  if(!choose(code,t))return false;queue.clear();automatic=false;paused=false;manualTravel=true;return true;
 }
 Pose tick(double dt,const Tour&t){
  if(!initialized||paused)return current;dt=std::clamp(dt,0.,.1);
  if(moving){elapsed+=dt;current=blend(from,to,elapsed/duration);if(elapsed>=duration){current=to;moving=false;}return current;}
  if(!pending.empty()){from=current;to=pending.front();pending.erase(pending.begin());elapsed=0;duration=manualTravel?std::clamp(travelTime(from,to)*.12,.45,2.4):travelTime(from,to)*.85;moving=true;return current;}
  if(hold>0){hold-=dt;return current;}if(!automatic)return current;
  if(queue.empty())refill(t);
  // An inaccessible anchor is skipped once, rather than retried forever.
  while(!queue.empty()){const auto next=queue.front();queue.erase(queue.begin());if(choose(static_cast<int>(next),t))break;}
  return current;
 }
};
}
