#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <map>
#include <algorithm>
namespace clubcomp {
struct Team{int id=0,rank=0,games=0,wins=0,draws=0,losses=0,gf=-1,ga=-1,points=0,movement=0;std::string name,form,color;};
struct Group{int id=0;std::string name;std::vector<Team>rows;std::vector<std::pair<std::string,std::string>>legend;};
struct Leg{int date=0,home=0,away=0,h=-1,a=-1;std::string time;};
struct Tie{int home=0,away=0,h=-1,a=-1,winner=0;bool complete=false;std::string homeName,awayName;std::vector<Leg>legs;};
struct Round{int stage=0,kind=0;std::string name;std::vector<Tie>ties;};
struct Player{int id=0,club=0,value=0,games=0,slot=0;std::string name,clubName,rating,position;};
struct MatchResult{int id=0,date=0,home=0,away=0,h=-1,a=-1;bool played=false;std::string time,homeName,awayName;};
struct Matchday{int number=0,played=0;std::string name;std::vector<MatchResult>matches;};
struct MonthlyAward{int month=0,id=0,club=0;bool available=false;std::string name,image,metric,note,clubName;};
struct BracketNode{int id=0,round=0,tie=-1,x=0,y=0;};
struct BracketEdge{int source=0,destination=0,rank=1,slot=0;};
struct Insight{int id=0,club=0,other=0;std::string name,clubName,value,detail;bool available=false;};
struct Competition{int root=0,asset=0,rank=-1,points=-1,finalNode=0;bool knockoutFirst=false;std::string name,format,status,formation;std::vector<Group>groups;std::vector<Round>rounds;std::vector<Player>leaders[2],starters;std::vector<Matchday>matchdays;MonthlyAward awards[2];Insight insights[6];std::vector<BracketNode>nodes;std::vector<BracketEdge>edges;};
struct Data{int club=0,date=0;std::string clubName;std::vector<Competition>competitions;};
inline int integer(const std::string&s,int missing=0){if(s.empty())return missing;size_t n=0;int v=std::stoi(s,&n);if(n!=s.size())throw 1;return v;}
inline bool parse(std::istream&in,unsigned long long seq,int club,Data&out){
 Data next;std::string line;std::map<int,size_t> roots;size_t count=0,bytes=0;
 auto comp=[&](int root)->Competition&{if(!roots.count(root))throw 1;return next.competitions[roots[root]];};
 try{while(std::getline(in,line)){
  bytes+=line.size();if(++count>40000||bytes>4*1024*1024||line.size()>4096)throw 1;
  std::vector<std::string>v;std::istringstream fields(line);std::string value;while(std::getline(fields,value,'\t'))v.push_back(value);if(!line.empty()&&line.back()=='\t')v.emplace_back();if(v.empty())continue;
  auto n=[&](size_t i,int fallback=0){return integer(v.at(i),fallback);};
  if(v[0]=="H"){if(count!=1||v.size()!=6||n(1)!=1||std::stoull(v[2])!=seq||n(3)!=club)throw 1;next.club=n(3);next.date=n(4);next.clubName=v[5];}
  else if(v[0]=="C"){if(v.size()!=8||next.competitions.size()>=64||roots.count(n(1)))throw 1;Competition c;c.root=n(1);c.asset=n(2);c.name=v[3];c.format=v[4];c.status=v[5];c.rank=n(6,-1);c.points=n(7,-1);roots[c.root]=next.competitions.size();next.competitions.push_back(c);}
  else if(v[0]=="P"){if(v.size()!=3||v[2]!="knockout-first")throw 1;comp(n(1)).knockoutFirst=true;}
  else if(v[0]=="G"){auto&c=comp(n(1));if(v.size()!=4||c.groups.size()>=128)throw 1;Group g;g.id=n(2);g.name=v[3];c.groups.push_back(g);}
  else if(v[0]=="T"||v[0]=="Z"){
   auto&c=comp(n(1));auto g=std::find_if(c.groups.begin(),c.groups.end(),[&](auto&x){return x.id==n(2);});if(g==c.groups.end())throw 1;
   if(v[0]=="T"){if(v.size()!=16||g->rows.size()>=128)throw 1;Team t;t.id=n(3);t.rank=n(4);t.name=v[5];t.games=n(6);t.wins=n(7);t.draws=n(8);t.losses=n(9);t.gf=n(10,-1);t.ga=n(11,-1);t.points=n(12);t.movement=n(13);t.form=v[14];t.color=v[15];g->rows.push_back(t);}
   else{if(v.size()!=5||g->legend.size()>=12)throw 1;g->legend.emplace_back(v[3],v[4]);}
  }else if(v[0]=="R"){auto&c=comp(n(1));if(v.size()!=6||n(2)!=int(c.rounds.size())||c.rounds.size()>=64)throw 1;Round r;r.stage=n(3);r.kind=n(4);r.name=v[5];c.rounds.push_back(r);}
  else if(v[0]=="K"){auto&c=comp(n(1));auto&r=c.rounds.at(n(2));if(v.size()!=12||n(3)!=int(r.ties.size())||r.ties.size()>=256)throw 1;Tie t;t.home=n(4);t.away=n(5);t.homeName=v[6];t.awayName=v[7];t.h=n(8,-1);t.a=n(9,-1);t.winner=n(10);t.complete=n(11)!=0;r.ties.push_back(t);}
  else if(v[0]=="L"){auto&t=comp(n(1)).rounds.at(n(2)).ties.at(n(3));if(v.size()!=10||t.legs.size()>=8)throw 1;Leg l;l.date=n(4);l.time=v[5];l.home=n(6);l.away=n(7);l.h=n(8,-1);l.a=n(9,-1);t.legs.push_back(l);}
  else if(v[0]=="S"){auto&c=comp(n(1));if((v.size()!=9&&v.size()!=10)||(v[2]!="goals"&&v[2]!="assists"))throw 1;auto&list=c.leaders[v[2]=="assists"];if(list.size()>=10000)throw 1;Player p;p.id=n(3);p.club=n(4);p.name=v[5];p.clubName=v[6];p.value=n(7);p.games=n(8);if(v.size()==10)p.position=v[9];list.push_back(p);}
  else if(v[0]=="F"){auto&c=comp(n(1));if(v.size()!=4)throw 1;c.formation=v[2];}
  else if(v[0]=="D"){auto&c=comp(n(1));if(v.size()!=6||n(2)!=int(c.matchdays.size())||c.matchdays.size()>=2048)throw 1;Matchday d;d.number=n(3);d.name=v[4];d.played=n(5);if(d.number<=0)throw 1;c.matchdays.push_back(d);}
  else if(v[0]=="M"){auto&d=comp(n(1)).matchdays.at(n(2));if(v.size()!=13||d.matches.size()>=256)throw 1;MatchResult m;m.id=n(3);m.date=n(4);m.time=v[5];m.home=n(6);m.away=n(7);m.homeName=v[8];m.awayName=v[9];m.h=n(10,-1);m.a=n(11,-1);m.played=n(12)!=0;if(m.home<=0||m.away<=0||m.home==m.away||m.date<20000101||m.date>22001231||(m.played&&(m.h<0||m.a<0||m.date>next.date)))throw 1;d.matches.push_back(m);}
  else if(v[0]=="A"){auto&c=comp(n(1));if(v.size()!=12||(v[2]!="player"&&v[2]!="coach"))throw 1;auto&a=c.awards[v[2]=="coach"];a.month=n(3);a.available=n(4)!=0;a.id=n(5);a.club=n(6);a.name=v[7];a.image=v[8];a.metric=v[9];a.note=v[10];a.clubName=v[11];if(a.image.find("..")!=std::string::npos||a.image.find(':')!=std::string::npos||(!a.image.empty()&&a.image.rfind("minifaces/",0)!=0))throw 1;}
  else if(v[0]=="X"){auto&c=comp(n(1));if(v.size()!=7||c.starters.size()>=11)throw 1;Player p;p.slot=n(2);p.id=n(3);p.club=n(4);p.name=v[5];p.rating=v[6];c.starters.push_back(p);}
  else if(v[0]=="N"){auto&c=comp(n(1));if(v.size()!=7||c.nodes.size()>=2048)throw 1;BracketNode node;node.id=n(2);node.round=n(3);node.tie=n(4,-1);node.x=n(5);node.y=n(6);if(node.round<0||node.round>=int(c.rounds.size())||node.tie>=int(c.rounds[node.round].ties.size()))throw 1;c.nodes.push_back(node);}
  else if(v[0]=="E"){auto&c=comp(n(1));if(v.size()!=6||c.edges.size()>=4096)throw 1;BracketEdge edge;edge.source=n(2);edge.destination=n(3);edge.rank=n(4);edge.slot=n(5);c.edges.push_back(edge);}
  else if(v[0]=="B"){if(v.size()!=3)throw 1;comp(n(1)).finalNode=n(2);}
  else if(v[0]=="I"){if(v.size()!=10)throw 1;auto&c=comp(n(1));const char*kinds[]={"biggestWin","scorer","assists","goalkeeper","defense","attack"};int index=-1;for(int k=0;k<6;++k)if(v[2]==kinds[k])index=k;if(index<0)throw 1;auto&a=c.insights[index];a.id=n(3);a.club=n(4);a.name=v[5];a.clubName=v[6];a.value=v[7];a.detail=v[8];a.other=n(9);a.available=a.club>0&&!a.name.empty();}
  else throw 1;
 }}catch(...){return false;}
 if(next.club!=club||next.date<20000101||next.date>22001231||!in.eof())return false;out=std::move(next);return true;
}
}
