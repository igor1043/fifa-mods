#pragma once
#include "competitions_model.h"
#include <array>
namespace clubcomp {
struct Area {float x,y,w,h;bool contains(float X,float Y)const{return X>=x&&X<x+w&&Y>=y&&Y<y+h;}};
inline constexpr Area tableArea{60,155,682,635},leadersArea{757,155,352,635},pitchArea{1124,155,416,635},fieldArea{1140,231,384,500};
inline constexpr float pitchBundleHeight=90;
inline constexpr float detailContentHeight=1125,detailViewportHeight=635,detailMaximumScroll=detailContentHeight-detailViewportHeight;
inline constexpr Area goalsArea{757,155,352,310},assistsArea{757,480,352,310},roundsButton{500,166,190,31};
inline unsigned medalColor(int rank){return rank==1?0xfffff1c9:rank==2?0xffe6ecf3:rank==3?0xfff5e3d5:0xffedf4f9;}
inline unsigned medalInk(int rank){return rank==1?0xffa67d21:rank==2?0xff718497:rank==3?0xffa26c48:0xff66839b;}
struct DashboardNavigation{
 int focus=0,leaders[2]{0,0},detail=0,matchday=0,matchScroll=0,fullList=-1,listSelected=0,listScroll=0;bool rounds=false;
 void reset(){*this=DashboardNavigation{};}
 void moveFocus(int delta){focus=(focus+delta+4)%4;}
 void scroll(int delta,int tableCount,int&tableScroll,const Competition&c){
  if(fullList>=0){int count=int(c.leaders[fullList].size());listSelected=std::clamp(listSelected+delta,0,(std::max)(0,count-1));if(listSelected<listScroll)listScroll=listSelected;else if(listSelected>=listScroll+12)listScroll=listSelected-11;}
  else if(rounds){int count=c.matchdays.empty()?0:int(c.matchdays[std::clamp(matchday,0,int(c.matchdays.size())-1)].matches.size());matchScroll=std::clamp(matchScroll+delta,0,(std::max)(0,count-12));}
  else if(focus==0)tableScroll=std::clamp(tableScroll+delta,0,(std::max)(0,tableCount-20));
  else if(focus==3)detail=std::clamp(detail+delta*38,0,int(detailMaximumScroll));
  else pageLeader(focus-1,delta,c);
 }
 int pages(int kind,const Competition&c)const{return (std::min)(3,(int(c.leaders[kind].size())+2)/3);}
 void pageLeader(int kind,int delta,const Competition&c){int count=pages(kind,c);leaders[kind]=count?((leaders[kind]+delta)%count+count)%count:0;}
 void openList(int kind){fullList=std::clamp(kind,0,1);rounds=false;listSelected=listScroll=0;}
 void stepRound(int delta,const Competition&c){if(!c.matchdays.empty()){matchday=(matchday+delta+int(c.matchdays.size()))%int(c.matchdays.size());matchScroll=0;}}
};
struct PitchPlacement{size_t player;float x,y,width;};
inline std::vector<PitchPlacement> placeCompetitionXI(const std::vector<Player>&players){
 bool defensive=false,attacking=false;for(auto&p:players){defensive|=p.slot>=9&&p.slot<=11;attacking|=p.slot>=17&&p.slot<=19;}bool split=defensive&&attacking;
 std::array<std::vector<size_t>,5>bands;for(size_t i=0;i<players.size();++i){int s=players[i].slot;int row=s==0?4:s<=8?3:s>=20?0:split?(s>=17?1:2):2;bands[row].push_back(i);}
 auto lateral=[](int s){switch(s){case 2:case 3:return 90;case 4:return 68;case 6:return 32;case 7:case 8:return 10;case 9:return 66;case 11:return 34;case 12:return 90;case 13:return 70;case 15:return 30;case 16:return 10;case 17:case 20:case 24:return 70;case 19:case 22:case 26:return 30;case 23:return 90;case 27:return 10;default:return 50;}};
 std::vector<PitchPlacement>out;
 for(int row=0;row<5;++row){auto&band=bands[row];std::stable_sort(band.begin(),band.end(),[&](size_t a,size_t b){return lateral(players[a].slot)<lateral(players[b].slot);});float py=row==0?.04f:row==1?.225f:row==2?(split?.425f:.35f):.61f;
  for(size_t i=0;i<band.size();++i){float px=(float(i)+.5f)/float(band.size()),y=row==4?fieldArea.y+fieldArea.h-pitchBundleHeight-7:fieldArea.y+fieldArea.h*py;float width=(std::min)(96.f,fieldArea.w/float(band.size())-8);out.push_back({band[i],fieldArea.x+fieldArea.w*px,y,width});}
 }
 return out;
}
}
