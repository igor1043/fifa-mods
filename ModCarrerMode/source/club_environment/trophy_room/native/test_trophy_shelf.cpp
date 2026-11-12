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
 Status current;current.list=0;current.total=3;assert(position(current)==L"1 / 3");current.selected=2;assert(position(current)==L"3 / 3");
 current.total=37;current.page=1;current.selected=0;assert(position(current)==L"31 / 37");current.total=0;assert(position(current)==L"0 / 0");
 assert(wonDate(20261017)==L"17/10/2026"&&wonDate(20260224)==L"24/02/2026");
 assert(wonDate(20240229)==L"29/02/2024"&&wonDate(20260229)==L"--/--/----");
 assert(historyHeight(1)==420&&historyHeight(1,true)==446);
 assert(historyHeight(2)<historyHeight(3)&&historyHeight(50)==historyHeight(5)&&historyHeight(50)<=572);
 assert(historyContains(1200,630,float(historyHeight(1)))&&!historyContains(1200,640,float(historyHeight(1))));
 std::cout<<"Trophy shelf navigation, bounds and centred input passed\n";
}
