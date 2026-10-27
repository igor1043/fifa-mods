#pragma once
#include <string>
#include <vector>
#include <sstream>
#include <fstream>
#include <algorithm>
#include <cmath>
namespace clubs {
struct GlobeView{static constexpr float x=470,y=24,w=1130,h=800,camera=3.8f,focal=2.3f;};
struct Point{float x=0,y=0;bool visible=false;};
inline Point project(float latitude,float longitude,float yaw,float pitch,float zoom){float lat=latitude*.01745329252f,lon=longitude*.01745329252f,x=cosf(lat)*sinf(lon),y=sinf(lat),z=cosf(lat)*cosf(lon);float xx=cosf(yaw)*x+sinf(yaw)*z,zz=-sinf(yaw)*x+cosf(yaw)*z,yy=cosf(pitch)*y-sinf(pitch)*zz,depth=sinf(pitch)*y+cosf(pitch)*zz,eye=GlobeView::camera/zoom,d=eye-depth;Point p;p.visible=depth>1/eye&&d>.01f;p.x=GlobeView::x+(xx*GlobeView::focal/(GlobeView::w/GlobeView::h)/d+1)*GlobeView::w/2;p.y=GlobeView::y+(1-yy*GlobeView::focal/d)*GlobeView::h/2;return p;}
struct Club {int country=0,nation=0,world=0,leagueOrder=0,league=0,level=1,order=0,id=0,attack=0,midfield=0,defense=0,overall=0;std::string countryName,leagueName,name,city;float lat=0,lon=0;};
struct Model {
 std::vector<Club> rows;size_t selected=0;int focus=2;float yaw=0,pitch=0,targetYaw=0,targetPitch=0,zoom=1.3f,targetZoom=1.3f;unsigned revision=1;bool detailOpen=false;
 bool activate(){if(detailOpen)return false;detailOpen=true;return true;}
 bool closeDetail(){if(!detailOpen)return false;detailOpen=false;return true;}
 bool load(std::istream& input){std::vector<Club> pending;std::string line;
  while(std::getline(input,line)){if(line.size()>4096||pending.size()>=3000)return false;std::vector<std::string> v;std::istringstream stream(line);std::string field;while(std::getline(stream,field,'\t'))v.push_back(field);if(v.size()!=18)return false;
   try{Club c;c.country=std::stoi(v[0]);c.countryName=v[1];c.nation=std::stoi(v[2]);c.world=std::stoi(v[3]);c.leagueOrder=std::stoi(v[4]);c.league=std::stoi(v[5]);c.leagueName=v[6];c.level=std::stoi(v[7]);c.order=std::stoi(v[8]);c.id=std::stoi(v[9]);c.name=v[10];c.city=v[11];c.lat=std::stof(v[12]);c.lon=std::stof(v[13]);c.attack=std::stoi(v[14]);c.midfield=std::stoi(v[15]);c.defense=std::stoi(v[16]);c.overall=std::stoi(v[17]);
    if(c.id<1||c.country<0||c.country>200||c.world<0||c.world>255||c.league<1||c.name.empty()||!std::isfinite(c.lat)||!std::isfinite(c.lon)||std::abs(c.lat)>90||std::abs(c.lon)>180)return false;pending.push_back(c);
   }catch(...){return false;}}
  if(pending.empty())return false;rows.swap(pending);selected=0;choose(1629);recenter(false);return true;
 }
 const Club& club()const{return rows[selected];}
 bool choose(int id){for(size_t i=0;i<rows.size();++i)if(rows[i].id==id){selected=i;++revision;recenter(false);return true;}return false;}
 std::vector<size_t> choices(int kind)const{std::vector<size_t> out;int previous=-99999;for(size_t i=0;i<rows.size();++i){const auto& c=rows[i];if(kind>0&&c.country!=club().country)continue;if(kind>1&&c.league!=club().league)continue;int key=kind==0?c.country:kind==1?c.league:c.id;if(key!=previous){out.push_back(i);previous=key;}}return out;}
 void step(int kind,int delta){if(rows.empty())return;focus=kind;auto options=choices(kind);if(options.empty())return;size_t current=0;for(size_t j=0;j<options.size();++j){const auto& c=rows[options[j]];if((kind==0&&c.country==club().country)||(kind==1&&c.league==club().league)||(kind==2&&c.id==club().id)){current=j;break;}}
  int next=(int(current)+delta+int(options.size()))%int(options.size());selected=options[next];++revision;recenter();
 }
 void moveFocus(int delta){focus=(focus+delta+3)%3;++revision;}
 void recenter(bool animate=true){if(rows.empty())return;targetYaw=-club().lon*.01745329252f;while(targetYaw-yaw>3.14159265f)targetYaw-=6.2831853f;while(targetYaw-yaw< -3.14159265f)targetYaw+=6.2831853f;targetPitch=club().lat*.01745329252f;if(!animate){yaw=targetYaw;pitch=targetPitch;}}
 void rotate(float dx,float dy){targetYaw+=dx;targetPitch=std::clamp(targetPitch+dy,-1.38f,1.38f);}
 void zoomBy(float value){targetZoom=std::clamp(targetZoom+value,.85f,2.2f);}
 void tick(float dt){float f=1-std::exp(-std::clamp(dt,0.f,.06f)*10);yaw+=(targetYaw-yaw)*f;pitch+=(targetPitch-pitch)*f;zoom+=(targetZoom-zoom)*f;}
};
inline bool isPage(const char* name){return name&&std::string(name)=="game/screens/career/server16/ClubBrowser";}
}
