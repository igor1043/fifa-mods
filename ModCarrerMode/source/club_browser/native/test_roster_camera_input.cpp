#include "roster_camera_input.h"
#include <cassert>
#include <iostream>
int main(){
 for(unsigned r=0;r<=30;++r)for(unsigned l=0;l<=30;++l)assert(clubs::rosterTriggerZoom(r,l)==0.f);
 assert(clubs::rosterTriggerZoom(255,0)==1.f&&clubs::rosterTriggerZoom(0,255)==-1.f);
 for(unsigned v=0;v<=255;++v){assert(clubs::rosterTriggerZoom(v,v)==0.f);assert(clubs::rosterTriggerZoom(v,0)>=0.f&&clubs::rosterTriggerZoom(v,0)<=1.f);}
 assert(clubs::rosterFramingHeight==180.f);
 std::cout<<"PASS roster camera: neutral triggers do not zoom; intentional inputs preserve direction; stable framing across player selection\n";
}
