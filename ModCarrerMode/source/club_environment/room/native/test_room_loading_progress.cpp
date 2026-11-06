#include "room_loading_progress.h"
#include <cassert>
int main(){
 using room_loading::progress;
 for(unsigned t=0;t<12000;t+=37){auto p=progress(false,0,0,t);assert(!p.determinate&&p.scale==.2f&&p.offset>=0&&p.offset+p.scale<=1.0001f);}
 auto p=progress(false,0,9,0);assert(p.determinate&&p.scale==0);
 p=progress(true,4,9,0);assert(p.scale==.5f);
 p=progress(true,9,9,0);assert(p.scale==1.f);
 p=progress(true,50,9,0);assert(p.scale==1.f);
}
