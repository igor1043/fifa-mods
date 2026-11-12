#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <algorithm>
#include <cmath>
namespace managerface {
struct Choice{int asset=0;std::string coach,name,image;int club=0;std::string clubName;int country=0,nation=0,league=0,leagueOrder=0;std::string countryName="Sem clube",leagueName="Sem liga";};
inline bool load(std::istream& input,std::vector<Choice>& rows){
 std::vector<Choice> pending{{0,"", "Padrão do FIFA", ""}};std::string line;
 while(std::getline(input,line)){
  if(!line.empty()&&line.back()=='\r')line.pop_back();
  if(line.size()>1000||pending.size()>256)return false;
  std::istringstream in(line);std::vector<std::string> v;std::string field;while(std::getline(in,field,'\t'))v.push_back(field);
  if(v.size()!=4&&v.size()!=6&&v.size()!=12)return false;Choice c;
  try{size_t used=0;c.asset=std::stoi(v[0],&used);if(used!=v[0].size()||c.asset<1||c.asset>200000)return false;}catch(...){return false;}
  c.coach=v[1];c.name=v[2];c.image=v[3];
  if(v.size()>=6){try{size_t used=0;c.club=std::stoi(v[4],&used);if(used!=v[4].size()||c.club<0||c.club>200000)return false;}catch(...){return false;}c.clubName=v[5];}
  if(v.size()==12){try{auto number=[&](int i){size_t used=0;int n=std::stoi(v[i],&used);if(used!=v[i].size()||n<0||n>2000000)throw 1;return n;};c.country=number(6);c.nation=number(7);c.league=number(8);c.leagueOrder=number(9);}catch(...){return false;}c.countryName=v[10];c.leagueName=v[11];if(c.countryName.empty()||c.leagueName.empty())return false;}
  if(c.coach.rfind("COACH-",0)!=0||c.coach.find_first_not_of("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-")!=std::string::npos||c.name.empty()||c.image.rfind("minifaces/",0)!=0||c.image.find("..")!=std::string::npos||c.image.find('\\')!=std::string::npos)return false;
  for(const auto& old:pending)if(old.coach==c.coach)return false;pending.push_back(std::move(c));
 }
 if(pending.size()<2)return false;rows=std::move(pending);return true;
}
inline int step(int selected,int delta,int count){return count?std::clamp(selected+delta,0,count-1):0;}
inline int firstVisible(int selected,int first,int count){first=std::clamp(first,0,std::max(0,count-7));if(selected<first)first=selected;if(selected>=first+7)first=selected-6;return first;}
// Index zero remains the unconfirmed FIFA fallback, never a visible choice.
// Filters hold indices into the immutable catalog, so changing filters cannot
// change the saved coach or invalidate an outstanding model request.
struct Filter{
 bool grouped=false;int country=0,league=0,focus=3;
 std::vector<int> visible(const std::vector<Choice>& rows)const{
  std::vector<int> out;for(int i=1;i<int(rows.size());++i)if(!grouped||(rows[i].country==country&&rows[i].league==league))out.push_back(i);return out;
 }
 std::vector<int> options(const std::vector<Choice>& rows,int kind)const{
  std::vector<int> out;for(int i=1;i<int(rows.size());++i){if(kind&&rows[i].country!=country)continue;int key=kind?rows[i].league:rows[i].country;
   if(std::none_of(out.begin(),out.end(),[&](int old){return (kind?rows[old].league:rows[old].country)==key;}))out.push_back(i);}
  std::stable_sort(out.begin(),out.end(),[&](int a,int b){return kind?rows[a].leagueOrder<rows[b].leagueOrder:rows[a].countryName<rows[b].countryName;});return out;
 }
 void follow(const std::vector<Choice>&rows,int selected){if(selected>0&&selected<int(rows.size())){country=rows[selected].country;league=rows[selected].league;}}
 int cycle(const std::vector<Choice>&rows,int kind,int delta){auto out=options(rows,kind);if(out.empty())return 0;int at=0;for(int j=0;j<int(out.size());++j)if((kind?rows[out[j]].league:rows[out[j]].country)==(kind?league:country)){at=j;break;}
  int index=out[(at+delta%int(out.size())+int(out.size()))%int(out.size())];follow(rows,index);return index;
 }
};
inline int visiblePosition(const std::vector<int>& rows,int selected){auto p=std::find(rows.begin(),rows.end(),selected);return p==rows.end()?0:int(p-rows.begin());}
inline int scrollFirst(int at,int first,int count,int page){first=std::clamp(first,0,std::max(0,count-page));return at<first?at:at>=first+page?at-page+1:first;}
// The native row supplies transformed coordinates, including ultrawide layout.
struct ValueRect {int x=0,y=0,w=0,h=0;bool valid=false;
 bool parse(const std::string& wire){
  if(wire.rfind("row:",0)!=0||wire.size()>31)return false;
  std::istringstream in(wire.substr(4));int X,Y,W,H;char a,b,c,extra;
  if(!(in>>X>>a>>Y>>b>>W>>c>>H)||a!=','||b!=','||c!=','||(in>>extra))return false;
  if(X<0||X>1280||Y<0||Y>720||W<16||W>1280||H<8||H>90||X+W>1280||Y+H>720)return false;
  x=X;y=Y;w=W;h=H;valid=true;return true;
 }
};
struct Camera {float angle=0,pan=0,zoom=1;
 void update(float turn,float vertical,float magnify,float wheel,float dt){
  dt=std::clamp(dt,0.f,.06f);angle+=turn*dt*2.8f;
  pan=std::clamp(pan+std::clamp(vertical,-1.f,1.f)*dt*.6f,-.45f,.65f);
  zoom=std::clamp(zoom*std::exp(magnify*dt+wheel*.001f),.65f,2.8f);
 }
};
}
