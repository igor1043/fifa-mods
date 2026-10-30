#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <set>
#include <algorithm>
#include <cmath>
#include <cstdint>
namespace worldrank {
struct Match{int date=0;std::string opponent,score;double delta=0,weight=0;};
struct Row{int id=0,nation=0,confed=0,rank=0,movement=0,games=0,wins=0,draws=0,losses=0,titles=0,campaignGames=0;double points=0,initial=0,matchPoints=0,titlePoints=0,campaignPoints=0;std::string name,country,league,form;std::vector<Match>recent;};
struct Data{int club=0,national=0,coachMine=0,date=0,matches=0,years=0,reference=0,leagues=0,clubsWithGames=0,coachMatches=0,coachBranchDate=0;std::string clubName;std::vector<Row>rows[3];};
inline bool parse(std::istream&in,uint64_t seq,int club,Data&out){
 Data next;std::string line;size_t bytes=0,count=0;std::set<std::pair<int,int>>seen;
 try{while(std::getline(in,line)){if(++count>40000||(bytes+=line.size())>6*1024*1024||line.size()>4096)throw 1;
  std::vector<std::string>v;std::istringstream s(line);std::string x;while(std::getline(s,x,'\t'))v.push_back(x);if(!line.empty()&&line.back()=='\t')v.emplace_back();if(v.empty())continue;
  auto n=[&](int i){size_t used=0;int a=std::stoi(v.at(i),&used);if(used!=v.at(i).size())throw 1;return a;};
  auto d=[&](int i){size_t used=0;double a=std::stod(v.at(i),&used);if(used!=v.at(i).size()||!std::isfinite(a))throw 1;return a;};
  if(v[0]=="H"){if(count!=1||(v.size()!=10&&v.size()!=14&&v.size()!=15)||n(1)!=1||std::stoull(v[2])!=seq||n(3)!=club)throw 1;next.club=club;next.date=n(4);next.national=n(5);next.clubName=v[6];next.matches=n(7);next.years=n(8);next.reference=n(9);if(v.size()>=14){next.leagues=n(10);next.clubsWithGames=n(11);next.coachMatches=n(12);next.coachMine=n(13);}if(v.size()==15)next.coachBranchDate=n(14);}
  else if(v[0]=="T"){if((v.size()!=20&&v.size()!=22)||next.club!=club)throw 1;int kind=v[1]=="clubs"?0:v[1]=="nations"?1:v[1]=="coaches"?2:-1;if(kind<0)throw 1;auto&rows=next.rows[kind];if(rows.size()>=10000||!seen.emplace(kind,n(2)).second)throw 1;Row r;r.id=n(2);r.nation=n(3);r.confed=n(4);r.rank=n(5);r.movement=n(6);r.name=v[7];r.country=v[8];r.league=v[9];r.points=d(10);r.initial=d(11);r.matchPoints=d(12);r.titlePoints=d(13);r.games=n(14);r.wins=n(15);r.draws=n(16);r.losses=n(17);r.titles=n(18);r.form=v[19];if(v.size()==22){r.campaignPoints=d(20);r.campaignGames=n(21);}if(r.wins<0||r.draws<0||r.losses<0||r.campaignGames<0||r.campaignGames>r.games)throw 1;if(r.id<=0||r.rank!=int(rows.size())+1||r.games<0||r.wins+r.draws+r.losses!=r.games||r.form.size()>5||r.name.empty())throw 1;rows.push_back(r);}
  else if(v[0]=="M"){if(v.size()!=8)throw 1;int kind=v[1]=="clubs"?0:v[1]=="nations"?1:v[1]=="coaches"?2:-1;if(kind<0)throw 1;auto&rows=next.rows[kind];if(rows.empty()||rows.back().id!=n(2)||rows.back().recent.size()>=5)throw 1;Match m;m.date=n(3);m.opponent=v[4];m.score=v[5];m.delta=d(6);m.weight=d(7);rows.back().recent.push_back(m);}
  else throw 1;
 }}catch(...){return false;}if(next.club!=club||next.date<20000101||next.date>22001231||next.rows[0].empty()||next.rows[1].empty()||!in.eof())return false;out=std::move(next);return true;
}
struct Selection{
 int mode=0,selected=0,scroll=0,filter=0;std::string country,league;std::vector<size_t>visible;
 void rebuild(const Data&d,int preferred=0){visible.clear();const auto&rows=d.rows[mode];for(size_t i=0;i<rows.size();++i)if((country.empty()||rows[i].country==country)&&(league.empty()||rows[i].league==league))visible.push_back(i);selected=0;for(size_t i=0;i<visible.size();++i)if(rows[visible[i]].id==preferred)selected=int(i);adjust();}
 void adjust(){selected=std::clamp(selected,0,(std::max)(0,int(visible.size())-1));scroll=std::clamp(scroll,0,(std::max)(0,int(visible.size())-14));if(selected<scroll)scroll=selected;if(selected>=scroll+14)scroll=selected-13;}
 const Row* row(const Data&d)const{return visible.empty()?nullptr:&d.rows[mode][visible[selected]];}
 void mine(const Data&d){country.clear();league.clear();rebuild(d,mode==0?d.club:mode==1?d.national:d.coachMine);}
 void top(const Data&d){country.clear();league.clear();scroll=0;rebuild(d);}
 void switchMode(const Data&d,int direction=1){mode=(mode+direction%3+3)%3;mine(d);}
 void move(int n){selected+=n;adjust();}
 void cycle(const Data&d,int delta){std::set<std::string>names;for(auto&r:d.rows[mode])if(filter==0||country.empty()||r.country==country)names.insert(filter?r.league:r.country);std::vector<std::string>options(1);options.insert(options.end(),names.begin(),names.end());std::string&value=filter?league:country;auto it=std::find(options.begin(),options.end(),value);int i=it==options.end()?0:int(it-options.begin());value=options[(i+delta+int(options.size()))%int(options.size())];if(!filter)league.clear();rebuild(d);}
};
}
