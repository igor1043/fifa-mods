#include "photo_refresh.h"
#include <cassert>
#include <cstdio>
int main(){
 gallery_background::Refresh r;
 for(unsigned i=0;i<3;++i)assert(!r.tick(true,true,10+i));
 assert(r.tick(true,true,13));
 // The queue accepted the request but never delivered the factory callback.
 for(unsigned now=14;now<1013;now+=30)assert(!r.tick(true,true,now));
 assert(r.tick(true,true,1013));assert(r.tick(true,true,2013));
 r.observed(true);assert(!r.tick(true,true,4000));
 // A list/3D transition requires its own acknowledgement, not the old one.
 for(unsigned i=0;i<3;++i)assert(!r.tick(true,false,5000+i));
 assert(r.tick(true,false,5003));r.observed(true);
 assert(r.tick(true,false,6003));r.observed(false);assert(!r.tick(true,false,7003));
 assert(!r.tick(false,false,8000));
 for(unsigned i=0;i<3;++i)assert(!r.tick(true,true,9000+i));
 assert(r.tick(true,true,9003));r.observed(true);assert(!r.tick(true,true,11003));
 puts("PASS: background refresh waits for factory delivery, retries cancelled jobs, preserves loading cover and re-arms on entry");
}
