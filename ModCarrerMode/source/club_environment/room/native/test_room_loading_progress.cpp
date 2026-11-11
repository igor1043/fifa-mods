#include "room_loading_progress.h"
#include <cassert>
int main(){
 using room_loading::progress;
 for(unsigned t=0;t<12000;t+=37){auto p=progress(false,0,0,t);assert(!p.determinate&&p.scale==.2f&&p.offset>=0&&p.offset+p.scale<=1.0001f);}
 auto p=progress(false,0,9,0);assert(p.determinate&&p.scale==0);
 p=progress(true,4,9,0);assert(p.scale==.5f);
 p=progress(true,9,9,0);assert(p.scale==1.f);
 p=progress(true,50,9,0);assert(p.scale==1.f);
 for(unsigned t=0;t<30000;t+=17){
  auto a=room_loading::activity(t);assert(std::isfinite(a.cosine)&&std::isfinite(a.sine));
  assert(std::abs(a.cosine*a.cosine+a.sine*a.sine-1.f)<.0001f);
  assert(a.badgeScale>=1.f&&a.badgeScale<=1.05501f);
  for(unsigned i=0;i<3;++i){auto d=room_loading::dot(t,i);assert(d.scale>=.8f&&d.scale<=1.151f&&d.lift>=0&&d.lift<=3.301f);}
  for(unsigned n=0;n<=100;++n){auto bar=progress(true,n,100,t);auto band=room_loading::sweep(bar,t);assert(band.offset>=bar.offset&&band.offset+band.scale<=bar.offset+bar.scale+.0001f);}
 }
 auto a=room_loading::activity(2400),b=room_loading::activity(0);assert(a.cosine==b.cosine&&a.sine==b.sine);
 assert(room_loading::stage(false,0,0)==0&&room_loading::stage(true,3,10)==1&&room_loading::stage(true,10,10)==2);
 room_loading::Motion state;state.tick(true,1000);for(unsigned t=1001;t<3000;++t){state.tick(true,t);auto p=state.smooth({.6f,0,true});assert(p.scale<=.6f);}
 assert(state.fraction>.59f);state.tick(false,3000);state.tick(true,4000);assert(state.began==4000&&state.fraction==0);
}
