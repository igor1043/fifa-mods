#pragma once
#include <algorithm>
#include <cmath>
namespace room_loading {
struct Bar { float scale=0,offset=0; bool determinate=false; };
struct Activity { float cosine=1,sine=0,badgeScale=1,badgeLift=0; };
inline Activity activity(unsigned long long elapsed){
 const float angle=float(elapsed%2400)*.002617993878f;
 return {std::cos(angle),std::sin(angle),1.f+.0275f*(1.f-std::cos(angle)),std::sin(angle)*1.1f};
}
inline Bar progress(bool mainReady,unsigned loaded,unsigned total,unsigned long long elapsed){
 if(total)return {std::clamp((float(loaded)+(mainReady?1.f:0.f))/float(total+1),0.f,1.f),0,true};
 // Unknown work has no percentage: a moving segment indicates activity.
 const float offset=(1.f+std::sin(float(elapsed%4000)*.001570796327f))*.4f;
 return {.2f,offset,false};
}
inline unsigned stage(bool mainReady,unsigned loaded,unsigned total){return !mainReady?0:!total||loaded<total?1:2;}
struct Dot{float scale,lift;};
inline Dot dot(unsigned long long elapsed,unsigned index){float phase=float((elapsed+1400-index%3*160)%1400)/1400.f;float wave=(std::max)(0.f,std::sin(phase*6.28318530718f));return {.8f+.35f*wave,3.3f*wave};}
inline Bar sweep(Bar bar,unsigned long long elapsed){float scale=(std::min)(.13f,bar.scale*.55f);return {scale,bar.offset+(bar.scale-scale)*float(elapsed%1800)/1800.f,bar.determinate};}
struct Motion{
 bool shown=false;unsigned long long began=0,last=0;float dt=0,fraction=0,stagePosition=0;
 void tick(bool show,unsigned long long now){if(show&&!shown){began=now;last=now;fraction=stagePosition=0;}dt=std::clamp(float(now-last)*.001f,0.f,.08f);last=now;shown=show;}
 Bar smooth(Bar value){if(!value.determinate)return value;fraction=(std::min)(value.scale,fraction+(value.scale-fraction)*(1-std::exp(-dt*12)));value.scale=fraction;return value;}
 float focus(unsigned target){stagePosition+=(float(target)-stagePosition)*(1-std::exp(-dt*10));return stagePosition;}
};
}
