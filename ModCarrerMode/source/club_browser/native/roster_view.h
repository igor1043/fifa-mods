#pragma once
#include <future>
#include <set>
namespace clubroster {
struct Player {int id=0,number=0,overall=-1,height=0,weight=0,age=-1,starter=-1,ordinal=0;std::string name,position,foot,nation;std::array<int,34> attributes{};std::array<int,4> performance{{-1,-1,-1,-1}};std::array<std::string,3> secondary;};
inline int integer(const std::string&s,int low,int high,int fallback=-1){try{size_t n;int v=std::stoi(s,&n);return n==s.size()&&v>=low&&v<=high?v:fallback;}catch(...){return fallback;}}
inline std::vector<std::string> split(const std::string&s,char sep='\t'){std::vector<std::string> out;std::istringstream in(s);std::string v;while(std::getline(in,v,sep))out.push_back(v);return out;}
inline bool parse(std::istream& input,int club,std::string& name,std::vector<Player>& result){
 std::string line;if(!std::getline(input,line)||line.size()>400)return false;auto h=split(line);if(h.size()!=3||(h[0]!="S16ROSTER1"&&h[0]!="S16ROSTER2")||integer(h[1],1,499999)!=club)return false;
 std::vector<Player> players;std::set<int> ids;
 while(std::getline(input,line)){if(line.empty())continue;if(line.size()>4096||players.size()>=100)return false;auto v=split(line);if(v.size()!=(h[0]=="S16ROSTER2"?52:43))return false;Player p;p.id=integer(v[0],1,199999999);p.name=v[1];p.number=integer(v[2],0,999,0);p.position=v[3];p.overall=integer(v[4],0,100);p.height=integer(v[5],130,230,0);p.weight=integer(v[6],0,300,0);p.foot=v[7];p.nation=v[8];if(p.id<1||p.name.empty()||p.name.size()>180||!p.height||!ids.insert(p.id).second)return false;for(int i=0;i<34;++i)p.attributes[i]=integer(v[9+i],0,100);p.ordinal=int(players.size());if(v.size()==52){p.age=integer(v[43],14,65);p.starter=integer(v[44],0,1);for(int i=0;i<4;++i)p.performance[i]=integer(v[45+i],0,100000);for(int i=0;i<3;++i)p.secondary[i]=v[49+i];}players.push_back(std::move(p));}
 if(players.empty())return false;name=h[2];result=std::move(players);return true;
}
struct View{
 std::vector<Player> players;std::string name,error;int club=0,selected=0,tab=0,scroll=0,sortMode=0;uint64_t consumed=0,selectedAt=0,submitted=0;bool ready=false,pending=false,sortFocus=false;std::future<std::shared_ptr<clubanim::Clip>> loadingClip;clubscene::Assets loadingAssets;std::array<int,96> loadingPages{};
 void clear(){players.clear();name.clear();error.clear();club=0;selected=tab=scroll=sortMode=0;consumed=submitted=0;ready=pending=sortFocus=false;}
 void request(clublineup::View& worker,int id,int career){clear();club=id;worker.career=career;worker.request(id,"roster");clubscene::intent(false,0);}
 const Player* player()const{return ready&&selected>=0&&size_t(selected)<players.size()?&players[selected]:nullptr;}
 void choose(int index){if(players.empty())return;selected=(index+int(players.size()))%int(players.size());scroll=std::clamp(scroll,0,(std::max)(0,int(players.size())-7));if(selected<scroll)scroll=selected;if(selected>=scroll+7)scroll=selected-6;if(!submitted)clubscene::playerHeight=float(player()?player()->height:180);selectedAt=GetTickCount64();pending=true;error.clear();clubscene::intent(false,0);}
 void setSort(int mode){if(players.empty())return;int keep=player()?player()->id:0;sortMode=(mode+4)%4;std::stable_sort(players.begin(),players.end(),[&](const Player&a,const Player&b){if(sortMode==1&&a.overall!=b.overall)return a.overall>b.overall;if(sortMode==2&&a.age!=b.age)return a.age<0?false:b.age<0?true:a.age<b.age;if(sortMode==3&&a.starter!=b.starter)return a.starter>b.starter;return a.ordinal<b.ordinal;});for(size_t i=0;i<players.size();++i)if(players[i].id==keep)selected=int(i);scroll=std::clamp(selected-3,0,(std::max)(0,int(players.size())-7));}
 void navigate(int direction){if(!ready)return;if(sortFocus){if(direction>0)sortFocus=false;return;}if(direction<0&&selected==0){sortFocus=true;return;}choose(std::clamp(selected+direction,0,int(players.size())-1));}
 void horizontal(int direction){if(sortFocus)setSort(sortMode+direction);}
 void poll(clublineup::View& worker,ID3D11Device* dev){
  if(pending&&GetTickCount64()-selectedAt>=120&&player()){pending=false;worker.request(club,"player",player()->id);}
  worker.poll(dev);
  if(worker.status=="error"){error=worker.message;return;}
  if(worker.status=="ready"&&worker.sequence!=consumed&&worker.club==club){
   consumed=worker.sequence;
   if(worker.kind=="roster"){
    std::error_code e;auto file=worker.folder/L"roster.tsv";auto bytes=std::filesystem::file_size(file,e);if(e||bytes>256000){error="Elenco indisponível.";return;}std::ifstream in(file,std::ios::binary);if(!parse(in,club,name,players)){error="Dados do elenco incompatíveis.";return;}ready=true;choose(0);
   }else if(worker.kind=="player"&&player()&&worker.player==player()->id){
    auto&v=worker.lastValues;clubscene::Assets a;a.sequence=worker.sequence;a.club=club;a.career=worker.career;a.player=worker.player;a.single=true;a.hash=v["hash"];a.pages=integer(v["pages"],1,96);if(!clubscene::validAssets(a)||v["renderer"]!="native"){error="Recursos do jogador incompatíveis.";return;}
    auto parts=split(v["bindings"],',');if(parts.size()!=96){error="Materiais incompletos.";return;}for(int i=0;i<96;++i){loadingPages[i]=integer(parts[i],0,a.pages-1);if(loadingPages[i]<0){error="Material inválido.";return;}}
    loadingAssets=a;auto path=worker.gameRoot/L"data/sceneassets/server16_club_xi"/std::to_wstring(GetCurrentProcessId())/a.hash/L"animation.bin";loadingClip=std::async(std::launch::async,[path,id=a.player](){return clubanim::load(path,id);});
   }
  }
  if(loadingClip.valid()&&loadingClip.wait_for(std::chrono::milliseconds(0))==std::future_status::ready){auto c=loadingClip.get();if(loadingAssets.sequence==worker.sequence&&player()&&loadingAssets.player==player()->id){if(!c){error="Animação nativa inválida.";return;}loadingAssets.animation=std::move(c);clubscene::submit(loadingAssets,loadingPages);submitted=loadingAssets.sequence;}}
 }
};
}
