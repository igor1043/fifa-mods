#include "../../../common/trophy_shelf.h"
#include <cassert>
#include <iostream>
int main(){
 using namespace trophy_shelf;State s;assert(s.pages()==1&&s.count()==0);s.step(12);s.turn(9);assert(s.page==0&&s.selected==0);
 s.total=41;s.step(17);assert(s.page==0&&s.selected==17);s.step(1);assert(s.page==1&&s.selected==0);s.step(6);assert(s.selected==6);
 s.step(100);assert(s.page==2&&s.selected==4);s.turn(1);assert(s.page==2);s.step(-100);assert(s.page==0&&s.selected==0);
 assert(hit(left+1,top+1,18)==0);assert(hit(left+cellWidth+gap+1,top+1,18)==1);
 assert(hit(left+cellWidth+2,top+1,18)==-1);assert(hit(left-1,top,18)==-1);assert(hit(left,top+(cellHeight+gap)*2+1,4)==-1);
 // Mouse and visual coordinates share the same centred canvas on ultrawide.
 const float scale=1080.f/900,leftMargin=(2560-1600*scale)/2;float physical=leftMargin+(left+cellWidth/2)*scale;
 assert(hit((physical-leftMargin)/scale,top+1,18)==0);
 std::cout<<"Trophy shelf navigation, bounds and centred input passed\n";
}
