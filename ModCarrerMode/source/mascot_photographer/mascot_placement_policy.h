#pragma once
#include <stdint.h>
static float mascot_lateral_from_seed(uint32_t seed){
 seed^=seed<<13;seed^=seed>>17;seed^=seed<<5;
 if(seed%100<75)return 3150.0f;
 const float alternatives[]={900.0f,1500.0f,2100.0f,2700.0f};return alternatives[(seed/100)%4];
}
struct MascotPlacementChoice{
 uintptr_t key=0;int home=-1,stadium=-1;bool ready=false;float lateral=3150.0f;
 bool update(uintptr_t nextKey,int nextHome,int nextStadium,uint32_t seed){
  if(ready && home==nextHome && stadium==nextStadium && (!key || !nextKey || key==nextKey)){
   if(!key)key=nextKey;return false;
  }
  key=nextKey;home=nextHome;stadium=nextStadium;ready=true;lateral=mascot_lateral_from_seed(seed);return true;
 }
};
