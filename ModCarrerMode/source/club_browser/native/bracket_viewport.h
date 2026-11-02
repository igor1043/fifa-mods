#pragma once
#include "competitions_model.h"
#include <cmath>
#include <array>
namespace clubcomp {
struct BracketPosition{int id=0,round=0;float x=0,y=0;bool final=false;};
struct BracketScene{
 int root=0,finalRound=-1;std::vector<BracketPosition>nodes;
 float x0=-200,x1=200,y0=-260,y1=320;
 void build(const Competition&c){
  *this=BracketScene{};root=c.root;int final=c.finalNode;
  if(!final)for(auto&n:c.nodes)if(c.rounds[n.round].kind==10&&n.id>final)final=n.id;
  for(auto&n:c.nodes)if(n.id==final)finalRound=n.round;
  int end=finalRound>=0?finalRound:(std::max)(0,int(c.rounds.size())-1);
  std::map<std::pair<int,int>,std::vector<const BracketNode*>>columns;
  for(auto&n:c.nodes){if(n.id==final){nodes.push_back({n.id,n.round,0,180,true});continue;}int side=n.x>0?1:-1;columns[{n.round,side}].push_back(&n);}
  for(auto&column:columns){auto&list=column.second;std::sort(list.begin(),list.end(),[](auto*a,auto*b){return a->y!=b->y?a->y<b->y:a->id<b->id;});float x=column.first.second*(std::max)(1,end-column.first.first)*286.f;
   for(size_t i=0;i<list.size();++i){float y=(float(i)-(list.size()-1)*.5f)*138;nodes.push_back({list[i]->id,list[i]->round,x,y,false});x0=(std::min)(x0,x-135);x1=(std::max)(x1,x+135);y0=(std::min)(y0,y-70);y1=(std::max)(y1,y+70);}
  }
 }
 const BracketPosition*find(int id)const{for(auto&n:nodes)if(n.id==id)return &n;return nullptr;}
};
struct BracketCamera{
 float x=0,y=0,zoom=1,targetX=0,targetY=0,targetZoom=1;
 static float axis(int value){float s=value/32767.f,a=std::abs(s);return a<=.22f?0:std::copysign((std::min)(1.f,(a-.22f)/.78f),s);}
 void focus(float X,float Y,float z,bool snap=false){targetX=X;targetY=Y;targetZoom=std::clamp(z,.16f,2.5f);if(snap){x=X;y=Y;zoom=targetZoom;}}
 void zoomAt(float amount,float sx=800,float sy=434){float next=std::clamp(targetZoom*std::exp(amount),.16f,2.5f);targetX+=(sx-800)*(1/targetZoom-1/next);targetY+=(sy-434)*(1/targetZoom-1/next);targetZoom=next;}
 void pan(float dx,float dy,float dt){float norm=(std::max)(1.f,std::sqrt(dx*dx+dy*dy));targetX+=dx/norm*650*dt/targetZoom;targetY+=dy/norm*650*dt/targetZoom;}
 void drag(float dx,float dy){targetX-=dx/zoom;targetY-=dy/zoom;x=targetX;y=targetY;}
 void tick(float dt,const BracketScene&s){targetX=std::clamp(targetX,s.x0-160,s.x1+160);targetY=std::clamp(targetY,s.y0-160,s.y1+160);float blend=1-std::exp(-14*std::clamp(dt,0.f,.05f));x+=(targetX-x)*blend;y+=(targetY-y)*blend;zoom+=(targetZoom-zoom)*blend;}
 float X(float world)const{return 800+(world-x)*zoom;}
 float Y(float world)const{return 434+(world-y)*zoom;}
};
}
