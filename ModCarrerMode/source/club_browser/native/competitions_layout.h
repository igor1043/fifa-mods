#pragma once
#include "competitions_model.h"
#include <array>
namespace clubcomp {
struct Area {float x,y,w,h;bool contains(float X,float Y)const{return X>=x&&X<x+w&&Y>=y&&Y<y+h;}};
inline constexpr Area tableArea{60,155,682,635},leadersArea{757,155,352,635},pitchArea{1124,155,416,635},fieldArea{1140,231,384,500};
inline constexpr float pitchBundleHeight=90;
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
