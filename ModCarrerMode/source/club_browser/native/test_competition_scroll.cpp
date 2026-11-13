#include "competition_scroll.h"
#include <cassert>
#include <iostream>
int main(){
 using namespace clubcomp;
 assert(ScrollMotion::axis(7000)==0&&ScrollMotion::axis(-8000)==0);
 assert(ScrollMotion::axis(32767)>.99f&&ScrollMotion::axis(-32768)==-1);
 for(int fps:{30,60,144}){
  ScrollMotion motion;int legacy=0;float dt=1.f/fps;
  for(int i=0;i<fps;++i){motion.move(520.f*dt,legacy,1000);motion.tick(legacy,1000,dt);}
  assert(std::abs(motion.target-520)<.01f&&legacy==520);
  assert(motion.position>470&&motion.position<520);
  float previous=motion.position;for(int i=0;i<fps;++i){motion.tick(legacy,1000,dt);assert(motion.position>=previous&&motion.position<=520.01f);previous=motion.position;}
  assert(std::abs(motion.position-520)<.01f);
  motion.move(-10000,legacy,1000);motion.tick(legacy,1000,dt);assert(legacy==0&&motion.position>=0);
  motion.set(900,legacy,1000,true);assert(motion.position==900);
  motion.tick(legacy,100,dt);assert(legacy==100&&motion.position==100);
 }
 // Small trackpad/stick movements must accumulate instead of rounding away.
 {ScrollMotion rows;int legacy=0;for(int i=0;i<100;++i)rows.move(.01f,legacy,4);assert(legacy==1&&std::abs(rows.target-1)<.001f);legacy=4;rows.tick(legacy,4,.016f);assert(rows.target==4);rows.tick(legacy,0,.016f);assert(!legacy&&!rows.position);}
 for(auto track:{ScrollTrack{218,553,561,2048},ScrollTrack{235,488,488,97.6f},ScrollTrack{171,603,635,256}}){
  for(int i=0;i<=100;++i){float p=track.maximum*i/100,grab=track.thumb()*.35f;assert(std::abs(track.position(track.top+track.offset(p)+grab,grab)-p)<.001f);}
  assert(track.position(-9999,0)==0&&track.position(99999,0)==track.maximum);
 }
 ScrollTrack empty{218,553,561,0};assert(empty.thumb()==553&&empty.position(100,10)==0&&empty.offset(0)==0);
 std::cout<<"PASS smooth scrolling: frame-independent 30/60/144 FPS, fractional input, bounded motion and inverse scrollbar dragging\n";
}
