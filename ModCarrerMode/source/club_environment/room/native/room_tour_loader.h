#pragma once
#include <istream>
#include <cmath>
#include "room_cinema_r52.h"
namespace room_tour_loader {
// Parse into a temporary tour: a rejected file must never erase the resident
// collision map, nor mark an incomplete room generation as installed.
inline bool read(std::istream& f,unsigned expectedPid,unsigned club,unsigned generation,room_cinema::Tour& result){
 std::string magic;unsigned ver=0,pid=0,id=0,stamp=0,n=0,boxes=0,paths=0,details=0,shirts=0,nav=0,extra=0;
 if(!(f>>magic>>ver>>pid>>id>>stamp>>n>>boxes>>paths>>details>>shirts>>nav>>extra)||magic!="S16TOUR"||ver!=5||pid!=expectedPid||id!=club||stamp!=generation||n>2||boxes==0||boxes>1024||paths!=8||details!=1||shirts>35||nav>32||extra>64)return false;
 room_cinema::Tour tour;
 auto vec=[&f](panorama::Vec&v){return bool(f>>v.x>>v.y>>v.z)&&std::isfinite(v.x)&&std::isfinite(v.y)&&std::isfinite(v.z)&&std::abs(v.x)<2000&&std::abs(v.y)<500&&std::abs(v.z)<3000;};
 auto pose=[&](panorama::Pose& p){return vec(p.eye)&&vec(p.target)&&bool(f>>p.fov)&&std::isfinite(p.fov)&&p.fov>=40&&p.fov<=90;};
 for(unsigned i=0;i<n;++i){room_cinema::Focus q;if(!(f>>q.number)||(q.number!=9&&q.number!=10)||!vec(q.eye)||!vec(q.target))return false;tour.focus.push_back(q);}
 for(unsigned i=0;i<boxes;++i){room_cinema::Box b;if(!vec(b.lo)||!vec(b.hi)||b.lo.x>b.hi.x||b.lo.y>b.hi.y||b.lo.z>b.hi.z)return false;tour.obstacles.push_back(b);}
 for(unsigned i=0;i<paths+details;++i){panorama::Pose p;if(!pose(p))return false;(i<paths?tour.path:tour.details).push_back(p);}
 for(unsigned i=0;i<shirts;++i){room_cinema::Focus q;if(!(f>>q.number)||q.number>99||!vec(q.eye)||!vec(q.target))return false;tour.shirts.push_back(q);}
 for(unsigned i=0;i<nav+extra;++i){panorama::Pose p;if(!pose(p))return false;(i<nav?tour.nav:tour.extra).push_back(p);}
 f>>std::ws;if(!f.eof())return false;
 result=std::move(tour);return true;
}
}
