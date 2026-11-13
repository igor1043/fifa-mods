#pragma once
#include <algorithm>
#include <cmath>
namespace clubcomp {
// Keep legacy integer commands while retaining fractional stick/wheel input.
// Only the displayed position is eased; bounds and drag targets are immediate.
struct ScrollMotion {
 float position=0,target=0;int published=0;
 void reset(){position=target=0;published=0;}
 void sync(int&value,float maximum){
  maximum=(std::max)(0.f,maximum);
  if(value!=published)target=float(value);
  target=std::clamp(target,0.f,maximum);position=std::clamp(position,0.f,maximum);
  value=published=int(std::lround(target));
 }
 void set(float value,int&legacy,float maximum,bool immediate=false){
  sync(legacy,maximum);target=std::clamp(value,0.f,(std::max)(0.f,maximum));
  legacy=published=int(std::lround(target));if(immediate)position=target;
 }
 void move(float delta,int&legacy,float maximum){sync(legacy,maximum);set(target+delta,legacy,maximum);}
 void tick(int&legacy,float maximum,float dt){
  sync(legacy,maximum);dt=std::clamp(dt,0.f,.05f);
  position+=(target-position)*(1-std::exp(-18.f*dt));
  if(std::abs(target-position)<.002f)position=target;
 }
 static float axis(int value){float magnitude=float(std::abs(value));return magnitude<=8000?0.f:std::copysign((magnitude-8000)/(32768.f-8000),float(value));}
};
struct ScrollTrack {
 float top=0,length=0,viewport=0,maximum=0;
 float thumb()const{return maximum>0?(std::max)(32.f,length*viewport/(viewport+maximum)):length;}
 float offset(float position)const{return maximum>0?(length-thumb())*std::clamp(position/maximum,0.f,1.f):0;}
 float position(float cursor,float grab)const{return maximum>0&&length>thumb()?std::clamp((cursor-top-grab)/(length-thumb()),0.f,1.f)*maximum:0;}
};
}
