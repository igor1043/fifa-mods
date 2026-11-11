#include "../../common/trophy_shelf.h"
struct ShelfWin {unsigned year=0,club=0,date=0;std::string clubName;};
struct ShelfRow {unsigned trophy=0,competition=0,club=0,date=0,year=0,titles=1,firstYear=0,lastYear=0;std::string name,clubName,origin,thumbnail;std::vector<ShelfWin>wins;};
struct ShelfPublication {
 trophy_shelf::Status state{};std::vector<ShelfRow> rows;uint64_t next=0;
 bool matches(const trophy_shelf::Status&s)const{return state.pid==s.pid&&state.club==s.club&&state.epoch==s.epoch&&state.collection==s.collection&&state.generation==s.generation&&state.page==s.page&&state.list==s.list;}
 void update(const trophy_shelf::Status&s){
  if(!matches(s)){rows.clear();state=s;next=0;}
  if(GetTickCount64()<next)return;next=GetTickCount64()+250;
  std::ifstream f(art.game/(s.list?L"ModCarrerMode/runtime/trophy_room/cabinet.tsv":L"ModCarrerMode/runtime/trophy_room/detail-cards.tsv"));std::string magic;unsigned v,pid,id,ep,col,gen,total,page,pages,count;
  if(!(f>>magic>>v>>pid>>id>>ep>>col>>gen>>total>>page>>pages>>count)||magic!=(s.list?"S16CABINET":"S16TITLECARDS")||v!=2||pid!=s.pid||id!=s.club||ep!=s.epoch||col!=s.collection||gen!=s.generation||page!=s.page||total!=s.total||count>(s.list?trophy_shelf::capacity:30u))return;
  std::vector<ShelfRow> fresh;
  for(unsigned i=0;i<count;++i){ShelfRow r;if(!(f>>r.trophy>>r.competition>>r.club>>r.date>>r.year>>r.titles>>r.firstYear>>r.lastYear>>std::quoted(r.name)>>std::quoted(r.clubName)>>std::quoted(r.origin)>>std::quoted(r.thumbnail))||r.name.size()>320||r.clubName.size()>160||r.year<1900||r.year>9999||!r.titles||r.titles>10000)return;
   if(!r.thumbnail.empty()&&(r.thumbnail.rfind("data/sceneassets/server16_trophy_room/thumbnails/",0)!=0||r.thumbnail.find("..")!=r.thumbnail.npos))return;
   for(unsigned j=0;j<r.titles;++j){ShelfWin w;if(!(f>>w.year>>w.club>>w.date>>std::quoted(w.clubName))||w.clubName.size()>160||w.year<1900||w.year>9999)return;r.wins.push_back(std::move(w));}fresh.push_back(std::move(r));}
  rows=std::move(fresh);
 }
}shelfPublication,detailPublication;
std::array<clubgfx::Texture,trophy_shelf::capacity> shelfCups,shelfCrests;
void shelfRounded(ID3D11DeviceContext*c,float x,float y,float w,float h,unsigned fill){
 constexpr float rad=8;std::vector<std::array<float,2>>p,t;const float centres[4][2]={{x+rad,y+rad},{x+w-rad,y+rad},{x+w-rad,y+h-rad},{x+rad,y+h-rad}};
 for(int corner=0;corner<4;++corner)for(int i=0;i<=4;++i){float a=3.14159265f+(corner*4+i)*1.57079633f/4;p.push_back({centres[corner][0]+rad*std::cos(a),centres[corner][1]+rad*std::sin(a)});}
 for(size_t i=0;i<p.size();++i){t.push_back({x+w/2,y+h/2});t.push_back(p[i]);t.push_back(p[(i+1)%p.size()]);}renderer.primitive(c,t,fill,true);
}
void shelfViewTabs(ID3D11DeviceContext*c,int&label,bool list){
 for(int i=0;i<2;++i){const bool selected=list==(i==0);const float x=i?1320.f:1130.f;const int w=i?220:180;
  shelfRounded(c,x,55,float(w),46,selected?uitheme::accent():0xffe8ecee);
  renderer.label(c,label++,i?L"Sala 3D":L"Galeria",x,55,w,46,21,selected?uitheme::selectedText():RGB(54,72,81),true);
 }
}
std::pair<std::wstring,std::wstring> shelfLines(const std::string&text){
 auto value=wide(text);const size_t limit=25;if(value.size()<=limit)return {value,{}};
 auto at=value.rfind(L' ',limit);if(at==value.npos||!at)at=limit;return {value.substr(0,at),value.substr(at+(value[at]==L' '?1:0))};
}
void drawTrophyShelf(ID3D11DeviceContext*c,HMODULE module,const scene_loading::Status&loading,const std::wstring&clubName){
 using Query=BOOL(WINAPI*)(trophy_shelf::Status*);using Command=BOOL(WINAPI*)(const char*);
 const auto query=(Query)GetProcAddress(module,"Fifa16TrophyShelfStatus");const auto command=(Command)GetProcAddress(module,"Fifa16TrophyRoomCommand");trophy_shelf::Status s;
 if(!query||!query(&s)||s.version!=2||s.size!=sizeof s||s.pid!=GetCurrentProcessId()||!s.list)return;
 static ID3D11Device* cachedDevice=nullptr;if(cachedDevice!=renderer.device){for(auto&t:shelfCups)t.clear();for(auto&t:shelfCrests)t.clear();cachedDevice=renderer.device;}
 shelfPublication.update(s);const auto&rows=shelfPublication.rows;auto&r=renderer;int label=0;
 // Preserve the native BOOTFLOW artwork behind the single white gallery card.
 r.rectangle(c,32,28,1536,800,0xfff7f9fa);containImage(c,r.clubIcon,62,49,66,76);
 r.label(c,label++,L"GALERIA DE TROFÉUS",149,48,900,45,34,RGB(37,55,66));
 r.label(c,label++,clubName+(s.collection?L" · Carreira do treinador":L" · Conquistas do clube"),151,97,920,30,21,RGB(107,128,140));
 shelfViewTabs(c,label,true);
 for(int i=0;i<2;++i){const bool selected=s.collection==unsigned(i);const float x=i?282.f:60.f;const int w=i?230:210;
  shelfRounded(c,x,143,float(w),42,selected?uitheme::accent():0xffe3e9ed);r.label(c,label++,i?L"Treinador":L"Clube",x,143,w,42,21,selected?uitheme::selectedText():RGB(63,85,97),true);
 }
 std::wstring count=s.ready?std::to_wstring(s.total)+(s.total==1?L" taça":L" taças"):L"Atualizando conquistas…";
 const bool preview=std::any_of(rows.begin(),rows.end(),[](const ShelfRow&r){return r.origin=="preview";});if(preview)count+=L" · DEMONSTRAÇÃO";
 r.label(c,label++,count,850,146,670,34,22,RGB(126,104,65),false);
 if(rows.empty()){
  r.label(c,label++,s.ready?L"As próximas conquistas vão aparecer aqui":L"Aguarde, buscando os títulos desta carreira…",250,405,1100,50,30,RGB(73,93,105),true);
  r.label(c,label++,s.ready?L"Você também pode explorar a sala 3D.":L"Os dados são conferidos com o clube e o save atuais.",250,463,1100,36,22,RGB(113,133,144),true);
  if(!s.ready){scene_loading::Status pending;indoorProgress(c,pending,450,535,700,label);}
 }
 for(size_t i=0;i<rows.size();++i){
  const auto&row=rows[i];const float x=trophy_shelf::left+(i%6)*(trophy_shelf::cellWidth+trophy_shelf::gap),y=trophy_shelf::top+(i/6)*(trophy_shelf::cellHeight+trophy_shelf::gap),w=trophy_shelf::cellWidth,h=trophy_shelf::cellHeight;
  const bool selected=i==s.selected;shelfRounded(c,x,y+3,w,h,0x11283c48);shelfRounded(c,x,y,w,h,selected?uitheme::accent():0xffe0e6e9);shelfRounded(c,x+2,y+2,w-4,h-4,0xffffffff);
  r.rectangle(c,x+10,y+108,w-20,1,0xffece7dc);shelfRounded(c,x+11,y+10,55,27,0xfff0eadf);
  r.label(c,label++,std::to_wstring(row.year),x+12,y+10,54,27,17,RGB(128,103,60),true);
  if(row.titles>=3)r.label(c,label++,std::to_wstring(row.titles)+L"×",x+w-55,y+10,44,27,18,RGB(128,103,60),true);
  gameImage(r.device,shelfCups[i],art,{row.thumbnail,"data/ui/imgAssets/trophy/t"+std::to_string(row.trophy)+".dds","data/ui/imgAssets/trophy256x256/t"+std::to_string(row.trophy)+".dds","data/ui/imgAssets/league/l"+std::to_string(row.competition)+".dds"});
  containImage(c,shelfCups[i],x+52,y+8,w-104,96);
  if(!shelfCups[i].view)r.label(c,label++,L"Imagem indisponível",x+14,y+47,int(w-28),34,16,RGB(123,139,147),true);
  const auto lines=shelfLines(row.name);r.label(c,label++,lines.first,x+12,y+111,int(w-24),23,17,RGB(37,57,70),true);
  r.label(c,label++,lines.second,x+12,y+133,int(w-24),21,16,RGB(37,57,70),true);
  gameImage(r.device,shelfCrests[i],art,{"data/ui/imgAssets/crest/light/l"+std::to_string(row.club)+".dds"});containImage(c,shelfCrests[i],x+15,y+h-26,21,21);
  r.label(c,label++,wide(row.clubName),x+43,y+h-28,int(w-52),25,16,RGB(101,120,130));
 }
 const unsigned start=s.total?s.page*trophy_shelf::capacity+1:0,last=std::min(s.total,(s.page+1)*trophy_shelf::capacity);
 r.label(c,label++,std::to_wstring(start)+L"–"+std::to_wstring(last)+L" de "+std::to_wstring(s.total),60,790,480,30,18,RGB(112,132,143));
 r.label(c,label++,L"Página "+std::to_wstring(s.page+1)+L" de "+std::to_wstring(s.pages),1180,790,340,30,18,RGB(112,132,143),true);
 if(s.pages>1){const float track=576,thumb=std::max(32.f,track/s.pages);r.rectangle(c,1538,205,6,track,0xffdfe5e8);r.rectangle(c,1538,205+(track-thumb)*s.page/(s.pages-1),6,thumb,uitheme::accent());}
 POINT p{};DWORD pid=0;auto window=GetForegroundWindow();GetWindowThreadProcessId(window,&pid);static bool held=false,drag=false;
 if(pid==GetCurrentProcessId()&&GetCursorPos(&p)&&ScreenToClient(window,&p)){
  const float mx=(p.x-r.left)/r.scale,my=(p.y-r.top)/r.scale;const bool down=(GetAsyncKeyState(VK_LBUTTON)&0x8000)!=0;const bool click=down&&!held;held=down;
  if(command&&click){const int hit=trophy_shelf::hit(mx,my,unsigned(rows.size()));if(hit>=0){const auto text="shelf_open_"+std::to_string(hit);command(text.c_str());}drag=mx>=1532&&mx<=1555&&my>=205&&my<=781;}
  if(!down)drag=false;
  if(command&&drag&&s.pages>1){const unsigned target=unsigned(std::clamp((my-205)/576.f,0.f,.999f)*s.pages);if(target!=s.page){const auto text="shelf_page_"+std::to_string(target);command(text.c_str());}}
  const int wheel=wheelDelta.exchange(0);if(command&&wheel)command(wheel>0?"shelf_prev":"shelf_next");
 }else{held=false;drag=false;}
}
// Text stays in the UI pass: no atlas material, tint, lighting or green/blue
// surface can alter the history panel in the 3D scene.
bool drawTrophyHistory(ID3D11DeviceContext*c,HMODULE module){
 using Query=BOOL(WINAPI*)(trophy_shelf::Status*);using Command=BOOL(WINAPI*)(const char*);
 auto query=(Query)GetProcAddress(module,"Fifa16TrophyShelfStatus");auto command=(Command)GetProcAddress(module,"Fifa16TrophyRoomCommand");trophy_shelf::Status s;
 if(!query||!query(&s)||s.version!=2||s.size!=sizeof s||s.pid!=GetCurrentProcessId()||s.list||!s.detail||!s.ready)return false;
 detailPublication.update(s);if(s.selected>=detailPublication.rows.size())return false;const auto&row=detailPublication.rows[s.selected];auto&r=renderer;int label=12;
 shelfRounded(c,1070,213,474,572,0xfaffffff);r.rectangle(c,1092,235,4,46,uitheme::accent());
 auto lines=shelfLines(row.name);r.label(c,label++,lines.first,1112,233,408,31,23,RGB(38,55,65));r.label(c,label++,lines.second,1112,264,408,28,22,RGB(38,55,65));
 r.label(c,label++,std::to_wstring(row.titles)+(row.titles==1?L" conquista":L" conquistas"),1094,310,420,32,23,RGB(132,109,67));
 r.label(c,label++,L"ANO       CLUBE CAMPEÃO",1094,358,416,24,17,RGB(112,130,140));
 constexpr unsigned visible=7;const unsigned offset=std::min(s.detailScroll,row.titles>visible?row.titles-visible:0u);
 if(command&&s.detailScroll!=offset){const auto text="detail_scroll_"+std::to_string(offset);command(text.c_str());}
 static std::array<clubgfx::Texture,visible>crests;static ID3D11Device*cachedDevice=nullptr;
 if(cachedDevice!=r.device){for(auto&t:crests)t.clear();cachedDevice=r.device;}
 for(unsigned i=0;i<visible&&i+offset<row.wins.size();++i){const auto&w=row.wins[i+offset];float y=397+i*43.f;r.rectangle(c,1094,y+39,416,1,0xffe6eaed);
  r.label(c,label++,std::to_wstring(w.year),1094,y,65,32,21,RGB(44,63,76));gameImage(r.device,crests[i],art,{"data/ui/imgAssets/crest/light/l"+std::to_string(w.club)+".dds"});containImage(c,crests[i],1172,y+2,26,28);
  r.label(c,label++,wide(w.clubName),1210,y,300,32,21,RGB(44,63,76));}
 if(row.titles>visible){const float track=300,thumb=std::max(24.f,track*visible/row.titles);r.rectangle(c,1524,397,5,track,0xffe2e7eb);r.rectangle(c,1524,397+(track-thumb)*offset/(row.titles-visible),5,thumb,uitheme::accent());}
 r.label(c,label++,L"Cada título mantém seu ano e clube de origem",1094,741,422,28,17,RGB(113,130,140));
 POINT p{};auto window=GetForegroundWindow();DWORD pid=0;GetWindowThreadProcessId(window,&pid);
 if(command&&pid==GetCurrentProcessId()&&GetCursorPos(&p)&&ScreenToClient(window,&p)){float x=(p.x-r.left)/r.scale,y=(p.y-r.top)/r.scale;int wheel=wheelDelta.exchange(0);if(wheel)command(trophy_shelf::historyContains(x,y)?(wheel>0?"detail_up":"detail_down"):(wheel>0?"zoom_in":"zoom_out"));
  static bool held=false,drag=false;const bool down=(GetAsyncKeyState(VK_LBUTTON)&0x8000)!=0;
  if(down&&!held)drag=x>=1515&&x<=1536&&y>=397&&y<=697;held=down;if(!down)drag=false;
  if(drag&&row.titles>visible){unsigned desired=unsigned(std::clamp((y-397)/300.f,0.f,1.f)*(row.titles-visible));const auto text="detail_scroll_"+std::to_string(desired);command(text.c_str());}
 }
 return true;
}
