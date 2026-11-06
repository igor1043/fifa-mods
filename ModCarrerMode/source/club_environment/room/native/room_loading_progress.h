#pragma once
#include <algorithm>
#include <cmath>
namespace room_loading {
struct Bar { float scale=0,offset=0; bool determinate=false; };
inline Bar progress(bool mainReady,unsigned loaded,unsigned total,unsigned long long elapsed){
 if(total)return {std::clamp((float(loaded)+(mainReady?1.f:0.f))/float(total+1),0.f,1.f),0,true};
 // Unknown work has no percentage: a moving segment indicates activity.
 const float offset=(1.f+std::sin(float(elapsed%4000)*.001570796327f))*.4f;
 return {.2f,offset,false};
}
}
