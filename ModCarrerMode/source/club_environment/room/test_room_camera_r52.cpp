#include <iostream>
#include <fstream>
#include "native/room_cinema_r52.h"
int main(int argc,char**argv){
 if(argc!=2)return 1;std::ifstream f(argv[1]);std::string magic;unsigned v,pid,club,generation,n,boxes,paths,details,shirts,nav,extra;
 if(!(f>>magic>>v>>pid>>club>>generation>>n>>boxes>>paths>>details>>shirts>>nav>>extra)||v!=5||shirts>35)return 2;
 room_cinema::Tour tour;
 auto focus=[&](auto&dest,unsigned count){for(unsigned i=0;i<count;++i){room_cinema::Focus q;f>>q.number>>q.eye.x>>q.eye.y>>q.eye.z>>q.target.x>>q.target.y>>q.target.z;dest.push_back(q);}};
 focus(tour.focus,n);
 for(unsigned i=0;i<boxes;++i){room_cinema::Box b;f>>b.lo.x>>b.lo.y>>b.lo.z>>b.hi.x>>b.hi.y>>b.hi.z;tour.obstacles.push_back(b);}
 for(unsigned i=0;i<paths+details;++i){panorama::Pose p;f>>p.eye.x>>p.eye.y>>p.eye.z>>p.target.x>>p.target.y>>p.target.z>>p.fov;(i<paths?tour.path:tour.details).push_back(p);}
 focus(tour.shirts,shirts);for(unsigned i=0;i<nav+extra;++i){panorama::Pose p;f>>p.eye.x>>p.eye.y>>p.eye.z>>p.target.x>>p.target.y>>p.target.z>>p.fov;(i<nav?tour.nav:tour.extra).push_back(p);}
 if(!f)return 3;room_cinema::compile(tour);
 room_cinema::Director director;director.reset(tour,generation,12345);
 director.refill(tour);for(auto index:director.queue)if(tour.sequence[index].pose.eye.z>=942)return 13;
 unsigned visited=0;for(size_t i=0;i<tour.sequence.size();++i){if(!director.choose(static_cast<int>(i),tour)){std::cout<<"Unreachable scene "<<i<<"\n";return 7;}++visited;}
 director.reset(tour,generation,12345);auto previous=director.current;float maximumSpeed=0,maximumTurn=0;unsigned collisions=0;
 for(unsigned i=0;i<120000;++i){auto p=director.tick(.04,tour);if(!room_cinema::poseSafe(p,tour))++collisions;auto delta=p.eye-previous.eye;maximumSpeed=std::max(maximumSpeed,std::sqrt(panorama::dot(delta,delta))/.04f);maximumTurn=std::max(maximumTurn,std::abs(room_cinema::angle(room_cinema::yaw(p)-room_cinema::yaw(previous)))*57.2957795f/.04f);previous=p;}
 director.command(-2,tour);auto paused=director.current;director.tick(.1,tour);if(panorama::dot(director.current.eye-paused.eye,director.current.eye-paused.eye)>0)return 8;
 director.command(-3,tour);if(director.command(999,tour))return 9;
 std::cout<<"scenes="<<visited<<" collisions="<<collisions<<" max_cm_s="<<maximumSpeed<<" max_yaw_deg_s="<<maximumTurn<<"\n";
 // A manual request cancels the old path and settles at the selected anchor.
 director.command(-1,tour);for(int i=0;i<100;++i)director.tick(.04,tour);
 const int destination=static_cast<int>(tour.sequence.size())-1;
 if(!director.command(destination,tour)||director.automatic||director.paused||director.moving)return 10;
 for(int i=0;i<1500;++i){auto p=director.tick(.04,tour);if(!room_cinema::poseSafe(p,tour))return 11;}
 const auto offset=director.current.eye-tour.sequence.back().pose.eye;
 if(panorama::dot(offset,offset)>.01f||director.moving||!director.pending.empty())return 12;
 return collisions||maximumSpeed>65.1f||maximumTurn>14.3f?6:0;
}
