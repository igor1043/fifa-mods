#include <cassert>
#include <cmath>
#include <iostream>
#include "competitions_layout.h"
int main(){
 using namespace clubcomp;assert(leadersArea.w>=350&&pitchArea.w<440);assert(tableArea.x+tableArea.w<leadersArea.x&&leadersArea.x+leadersArea.w<pitchArea.x);assert(pitchArea.x+pitchArea.w<=1540);assert(fieldArea.x>pitchArea.x&&fieldArea.x+fieldArea.w<pitchArea.x+pitchArea.w);
 const int formations[][11]={{0,3,4,6,7,13,14,15,23,25,27},{0,3,4,6,7,12,13,15,16,24,26},{0,3,4,6,7,9,11,17,18,19,25},{0,4,5,6,12,13,14,15,16,24,26},{0,2,4,5,6,8,13,14,15,24,26}};
 for(auto&slots:formations){std::vector<Player>players;for(int slot:slots){Player p;p.slot=slot;players.push_back(p);}auto positions=placeCompetitionXI(players);assert(positions.size()==11);std::vector<bool>seen(11);for(auto&p:positions){assert(p.player<11&&!seen[p.player]);seen[p.player]=true;assert(p.y>=fieldArea.y&&p.y+pitchBundleHeight<=fieldArea.y+fieldArea.h-6);assert(p.x-p.width/2>=fieldArea.x&&p.x+p.width/2<=fieldArea.x+fieldArea.w);}for(size_t i=0;i<positions.size();++i)for(size_t j=i+1;j<positions.size();++j){auto&a=positions[i];auto&b=positions[j];bool horizontal=std::abs(a.x-b.x)>=(a.width+b.width)/2;bool vertical=std::abs(a.y-b.y)>=pitchBundleHeight;assert(horizontal||vertical);}}
 // Removing or adding a leader field must not break the installed protocol.
 for(bool optional:{false,true}){std::istringstream file(std::string("H\t1\t123\t11\t20260101\tClube\nC\t1\t7\tLiga\tleague\tEm disputa\t1\t40\nS\t1\tgoals\t99\t11\tJogador\tClube\t8\t15")+(optional?"\tCentroavante\n":"\n"));Data d;assert(parse(file,123,11,d));assert(d.competitions[0].leaders[0][0].position==(optional?"Centroavante":""));}
 std::cout<<"PASS layout: wider leaders, narrower pitch, all XI labels inside field, no player overlap in five formations; old/new leaderboard protocol\n";
}
