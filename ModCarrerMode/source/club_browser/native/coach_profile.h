#pragma once
#include <array>
#include <map>
#include <set>
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
namespace clubcoach {
inline constexpr std::array<int,3> tabX{0,146,322},tabWidth{142,172,115};
inline int tabAt(float x){return x<146?0:x<322?1:2;}
inline std::string portraitFile(const std::string&path){
 constexpr const char*fallback="minifaces/NOTFOUND_DEFAULT.png";
 if(path.rfind("minifaces/",0)!=0||path.size()<15||path.size()>120||path.substr(path.size()-4)!=".png"||path.find("..")!=std::string::npos)return fallback;
 for(size_t i=10;i<path.size();++i){char c=path[i];if(!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||(c>='0'&&c<='9')||c=='_'||c=='-'||c=='.'))return fallback;}
 return path;
}
inline int number(const std::string&s,int low=-1,int high=100000000,int fallback=-1){try{size_t n=0;int v=std::stoi(s,&n);return n==s.size()&&v>=low&&v<=high?v:fallback;}catch(...){return fallback;}}
inline std::vector<std::string> fields(const std::string&s){std::vector<std::string>v;std::istringstream f(s);std::string t;while(std::getline(f,t,'\t'))v.push_back(t);return v;}
using Stats=std::array<int,7>;
struct Competition{int asset=0;std::string name,status;Stats stats{};};
struct History{int season=0,rank=-1,titles=0;Stats stats{};};
struct Starter{int id=0,number=0,position=-1,overall=-1;std::string name;};
struct Profile{
 int club=0;std::string name;std::map<std::string,std::string> values;std::map<std::string,Stats> stats,coachStats;std::vector<Competition> competitions;std::vector<History> history;std::vector<Starter> starters;
 std::string get(const std::string&key)const{auto i=values.find(key);return i==values.end()?"—":i->second;}
 int value(const std::string&key)const{return number(get(key));}
};
inline bool readStats(const std::vector<std::string>&v,int at,Stats&out){for(int i=0;i<7;++i){out[i]=number(v[at+i],-1,1000000,-2);if(out[i]<-1)return false;}bool unknown=std::all_of(out.begin(),out.end(),[](int n){return n==-1;});return unknown||(std::all_of(out.begin(),out.end(),[](int n){return n>=0;})&&out[1]+out[2]+out[3]==out[0]);}
inline bool parse(std::istream&in,int club,Profile&out){
 Profile p;std::string line;if(!std::getline(in,line)||line.size()>400)return false;auto h=fields(line);if(h.size()!=3||h[0]!="S16COACH1"||number(h[1],1,499999)!=club||h[2].empty())return false;p.club=club;p.name=h[2];std::set<int> players;
 while(std::getline(in,line)){
  if(line.size()>2048)return false;auto v=fields(line);if(v.empty())return false;
  if(v[0]=="F"&&v.size()==3){if(p.values.size()>=64||v[1].empty()||v[1].size()>40||v[2].size()>180||!p.values.emplace(v[1],v[2]).second)return false;}
  else if(v[0]=="S"&&v.size()==9){Stats s;if((v[1]!="total"&&v[1]!="home"&&v[1]!="away")||!readStats(v,2,s)||!p.stats.emplace(v[1],s).second)return false;}
  else if(v[0]=="T"&&v.size()==9){Stats s;if((v[1]!="total"&&v[1]!="home"&&v[1]!="away")||!readStats(v,2,s)||!p.coachStats.emplace(v[1],s).second)return false;}
  else if(v[0]=="C"&&v.size()==11){Competition c;c.asset=number(v[1],0,65535,0);c.name=v[2];c.status=v[10];if(p.competitions.size()>=64||c.name.empty()||!readStats(v,3,c.stats))return false;p.competitions.push_back(c);}
  else if(v[0]=="H"&&v.size()==11){History r;r.season=number(v[1],1,200,0);r.rank=number(v[2],-1,1000);r.titles=number(v[10],0,1000);if(p.history.size()>=200||!r.season||!readStats(v,3,r.stats))return false;p.history.push_back(r);}
  else if(v[0]=="X"&&v.size()==6){Starter r;r.id=number(v[1],1,199999999,0);r.number=number(v[2],0,999,0);r.name=v[3];r.position=number(v[4],0,99);r.overall=number(v[5],0,100);if(p.starters.size()>=11||!r.id||r.name.empty()||!players.insert(r.id).second)return false;p.starters.push_back(r);}
  else return false;
 }
 if(p.get("name")=="—"||p.stats.size()!=3||(!p.starters.empty()&&p.starters.size()!=11))return false;
 const auto&t=p.stats.at("total"),&a=p.stats.at("home"),&b=p.stats.at("away");if(t[0]>=0)for(int i=0;i<7;++i)if(a[i]<0||b[i]<0||a[i]+b[i]!=t[i])return false;
 if(p.coachStats.empty())for(const auto*key:{"total","home","away"})p.coachStats[key]=Stats{-1,-1,-1,-1,-1,-1,-1};
 if(p.coachStats.size()!=3)return false;
 const auto&ct=p.coachStats.at("total"),&ca=p.coachStats.at("home"),&cb=p.coachStats.at("away");if(ct[0]>=0)for(int i=0;i<7;++i)if(ca[i]<0||cb[i]<0||ca[i]+cb[i]!=ct[i])return false;
 out=std::move(p);return true;
}
}
