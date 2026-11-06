// This screen never creates a player or touches the native FCE database.
#include "competitions_model.h"
#include "competitions_layout.h"
std::atomic<int> competitionPresentation{0};
struct CompetitionView{
 bool padHints=true;
 clubcomp::BracketScene bracketScene;clubcomp::BracketCamera viewport;bool bracketDirty=true,bracketDrag=false;int bracketPhase=-1;float bracketMouseX=0,bracketMouseY=0;uint64_t bracketLast=0;
 clubcomp::DashboardNavigation nav;bool controlReady=false,leftTriggerHeld=false,rightTriggerHeld=false;bool keyState[256]{};WORD previousPad=0;int repeatDirection=0,detailDirection=0;uint64_t repeatAt=0,detailAt=0;
 clubcomp::Data data;int selected=0,group=0,round=0,scroll=0,stat=0,statScroll=0;bool bracket=false,ready=false,expanded=false;float canvasZoom=1,canvasPanX=0,canvasPanY=0,canvasCenterX=0,canvasCenterY=0;ID3D11RasterizerState*canvasClip=nullptr;uint64_t submitted=0,retry=0,checked=0;int currentClub=0,mixedScroll=0;fs::file_time_type publication{};
 std::array<clubgfx::Texture,2048>labels;std::map<std::string,clubgfx::Texture>images;int label=0;ID3D11Device* device=nullptr;
 struct CachedText{clubgfx::Texture texture;uint64_t used=0;};std::map<std::wstring,CachedText>textCache;size_t textBytes=0;uint64_t textFrame=0,textMisses=0;
 void clearTextures(){clubgfx::release(canvasClip);for(auto&t:labels)t.clear();for(auto&it:images)it.second.clear();images.clear();for(auto&it:textCache)it.second.texture.clear();textCache.clear();textBytes=0;device=nullptr;}
 void resetSelection(){group=round=scroll=statScroll=mixedScroll=0;nav.reset();bracket=false;if(data.competitions.empty())return;auto&c=data.competitions[selected];for(size_t i=0;i<c.groups.size();++i)for(auto&t:c.groups[i].rows)if(t.id==data.club)group=int(i);bracket=c.groups.empty();for(size_t i=0;i<c.rounds.size();++i)for(auto&t:c.rounds[i].ties)if(t.home==data.club||t.away==data.club)round=int(i);int latest=0;for(size_t i=0;i<c.matchdays.size();++i)for(auto&m:c.matchdays[i].matches)if(m.played&&m.date>=latest){latest=m.date;nav.matchday=int(i);}}
 void enter(int club){data={};selected=0;ready=false;expanded=false;controlReady=false;nav.reset();currentClub=club;submitted=retry=checked=0;clearTextures();request();}
 void request(){if(currentClub<=0)return;lineup.request(currentClub,"competitions");submitted=lineup.sequence;retry=GetTickCount64()+3000;}
 void poll(){
  auto now=GetTickCount64();int liveClub=careerClub();if(liveClub>0&&liveClub!=currentClub){enter(liveClub);return;}if(!submitted&&!ready){if(liveClub){currentClub=liveClub;request();}return;}if(submitted)lineup.poll(renderer.device);
  if(lineup.sequence==submitted&&lineup.status=="ready"){
   std::ifstream input(lineup.folder/L"competitions.tsv",std::ios::binary);clubcomp::Data next;
   if(clubcomp::parse(input,submitted,currentClub,next)){int oldRoot=ready&&!data.competitions.empty()?data.competitions[selected].root:0;data=std::move(next);bracketDirty=true;if(!ready){selected=0;resetSelection();}else{auto it=std::find_if(data.competitions.begin(),data.competitions.end(),[&](auto&c){return c.root==oldRoot;});selected=it==data.competitions.end()?0:int(it-data.competitions.begin());if(it==data.competitions.end())resetSelection();}ready=true;submitted=0;checked=now+1000;std::error_code ec;publication=fs::last_write_time(art.game/L"ModCarrerMode/runtime/career_fce_snapshot.json",ec);}
   else{lineup.status="error";lineup.lastValues["retry"]="1";lineup.message="Os dados da competição mudaram. Reabrindo a leitura...";}
  }
  if(lineup.status=="error"&&submitted&&now>=retry&&lineup.lastValues["retry"]=="1")request();
  if(ready&&!submitted&&now>=checked){checked=now+1000;std::error_code ec;auto stamp=fs::last_write_time(art.game/L"ModCarrerMode/runtime/career_fce_snapshot.json",ec);int club=careerClub();if(club&&club!=currentClub){enter(club);return;}if(!ec&&stamp!=publication){publication=stamp;request();}}
 }
 void command(const std::string&s){if(s=="comp_refresh"){request();return;}if(!ready||data.competitions.empty())return;auto&c=data.competitions[selected];
  if(s=="comp_activate"&&(expanded||nav.rounds||nav.fullList>=0)){if(expanded&&nav.fullList<0)fitBracket();return;}
  if(s=="comp_activate"&&nav.focus>=3)return;
  if(s=="comp_activate"&&nav.focus==0&&c.format!="cup"){nav.rounds=true;nav.fullList=-1;nav.matchScroll=0;return;}
  if(s=="comp_activate"||s=="comp_goals"||s=="comp_assists"){
   if(s!="comp_activate"||nav.focus==1||nav.focus==2){nav.openList(s=="comp_assists"?1:s=="comp_goals"?0:nav.focus-1);expanded=true;return;}
   expanded=true;nav.rounds=false;nav.fullList=-1;bracketDirty=true;fitBracket(true);return;
  }
  if(s=="comp_rounds"&&c.format=="cup"){expanded=true;nav.rounds=false;nav.fullList=-1;bracketDirty=true;fitBracket(true);return;}if(s=="comp_rounds"){nav.rounds=true;expanded=false;nav.fullList=-1;nav.matchScroll=0;return;}if(s=="comp_bracket"){expanded=true;nav.rounds=false;nav.fullList=-1;bracketDirty=true;fitBracket(true);return;}if(s=="comp_close"){expanded=false;nav.rounds=false;nav.fullList=-1;return;}if(s=="comp_center"){if(nav.fullList>=0)nav.listSelected=nav.listScroll=0;else fitBracket();return;}
  if(nav.fullList>=0){if(s=="comp_prev"||s=="comp_next")nav.openList(1-nav.fullList);else if(s=="comp_up"||s=="comp_down")nav.scroll(s=="comp_up"?-1:1,0,scroll,c);return;}if(expanded)return;
  if(s=="comp_focus_left"||s=="comp_focus_right"){nav.moveSpatial(s=="comp_focus_left"?-1:1,0);return;}
  if(nav.rounds){if(s=="comp_prev"||s=="comp_left")nav.stepRound(-1,c);else if(s=="comp_next"||s=="comp_right")nav.stepRound(1,c);else if(s=="comp_up"||s=="comp_down")nav.scroll(s=="comp_up"?-1:1,0,scroll,c);return;}
  if(s=="comp_prev"||s=="comp_next"){int d=s=="comp_prev"?-1:1;selected=(selected+d+int(data.competitions.size()))%int(data.competitions.size());resetSelection();}
  else if(s=="comp_stat_prev"||s=="comp_stat_next"){nav.focus=s=="comp_stat_prev"?1:2;}
  else if(s=="comp_mode"){if(c.format=="cup"){bracket=!bracket;scroll=0;}}
  else if(s=="comp_left"||s=="comp_right"){int d=s=="comp_left"?-1:1;if(c.format=="cup"){bracket=true;int count=int(c.rounds.size());if(count){int&index=round;index=(index+d+count)%count;scroll=0;}}}
  else if(s=="comp_up"||s=="comp_down"){int d=s=="comp_up"?-1:1;if(nav.focus==0&&c.format=="cup"&&!c.groups.empty()){mixedScroll=std::clamp(mixedScroll+d*44,0,mixedMaximum(c));return;}int count=bracket?(c.rounds.empty()?0:int(c.rounds[(std::min)(round,int(c.rounds.size())-1)].ties.size())):c.groups.empty()?0:int(c.groups[(std::min)(group,int(c.groups.size())-1)].rows.size());if(nav.focus==0&&bracket)scroll=std::clamp(scroll+d,0,(std::max)(0,count-4));else nav.scroll(d,count,scroll,c);}
  else if(s=="comp_stat_up"||s=="comp_stat_down")statScroll=std::clamp(statScroll+(s=="comp_stat_up"?-1:1),0,(std::max)(0,int(c.leaders[stat].size())-6));
 }
 void scaledText(ID3D11DeviceContext*c,const std::string&value,float x,float y,int w,int h,int size,float scale,COLORREF ink=RGB(25,52,76),bool center=false,int raster=0){
  if(value.empty()||w<=0||h<=0||scale<=0)return;if(!raster)raster=std::clamp(int(std::ceil(renderer.scale*scale)),2,4);auto content=wide(value);auto key=content+L"#"+std::to_wstring(w)+L","+std::to_wstring(h)+L","+std::to_wstring(size)+L","+std::to_wstring(ink)+L","+std::to_wstring(center)+L","+std::to_wstring(raster);auto found=textCache.find(key);
  if(found==textCache.end()){
   size_t bytes=size_t(w)*h*raster*raster*4;constexpr size_t budget=192*1024*1024;
   while(!textCache.empty()&&(textBytes+bytes>budget||textCache.size()>=1024)){auto oldest=textCache.end();for(auto it=textCache.begin();it!=textCache.end();++it)if(it->second.used!=textFrame&&(oldest==textCache.end()||it->second.used<oldest->second.used))oldest=it;if(oldest==textCache.end())break;textBytes-=size_t(oldest->second.texture.w)*oldest->second.texture.h*4;oldest->second.texture.clear();textCache.erase(oldest);}
   if(textBytes+bytes>budget)return;CachedText next;if(!clubgfx::text(renderer.device,next.texture,content,w*raster,h*raster,size*raster,ink,center))return;next.used=textFrame;textBytes+=bytes;found=textCache.emplace(std::move(key),std::move(next)).first;++textMisses;
  }
  found->second.used=textFrame;renderer.normal(c);renderer.quad(c,x,y,w*scale,h*scale,found->second.texture.view);
 }
 void text(ID3D11DeviceContext*c,const std::string&value,float x,float y,int w,int h,int size,COLORREF ink=RGB(25,52,76),bool center=false){scaledText(c,value,x,y,w,h,size,1,ink,center);}
 static std::string num(int n){return n<0?"—":std::to_string(n);}
 void image(ID3D11DeviceContext*c,const std::string&kind,int id,float x,float y,float w,float h){
  if(id<=0)return;std::string key=kind+std::to_string(id);if(images.size()>512&&!images.count(key)){for(auto&it:images)it.second.clear();images.clear();}
  auto&t=images[key];std::string i=std::to_string(id);std::vector<std::string>paths;
  if(kind=="flag")paths={"data/ui/imgAssets/flags512x512/f_"+i+".dds","data/ui/artassets/countryflags/f_"+i+".big"};
  else if(kind=="league")paths={"data/ui/imgAssets/league/light/l"+i+".dds","data/ui/imgAssets/league/dark/l"+i+".dds"};
  else if(kind=="trophy")paths={"data/ui/imgAssets/trophy256x256/t"+i+".dds","data/ui/imgAssets/trophy128x128/t"+i+".dds"};
  else if(kind=="head")paths={"data/ui/imgAssets/heads/p"+i+".dds","data/ui/imgAssets/heads/p0.dds"};
  else if(kind=="comp")paths={"data/ui/imgAssets/careerCompetitionIcons/"+i+".png","data/ui/imgAssets/league/light/l"+i+".dds","data/ui/imgAssets/league/dark/l"+i+".dds"};
  else paths={"data/ui/imgAssets/crest/light/l"+i+".dds","data/ui/imgAssets/crest/dark/l"+i+".dds"};
  clubgfx::gameImage(renderer.device,t,art,paths);if(!t.view||!t.w||!t.h)return;float fit=(std::min)(w/t.w,h/t.h);renderer.normal(c);renderer.quad(c,x+(w-t.w*fit)/2,y+(h-t.h*fit)/2,t.w*fit,t.h*fit,t.view);
 }
 unsigned color(const std::string&v,unsigned fallback=0xffd6e0e5){if(v.size()!=7||v[0]!='#')return fallback;try{return 0xff000000|unsigned(std::stoul(v.substr(1),nullptr,16));}catch(...){return fallback;}}
 void arrow(ID3D11DeviceContext*c,float x,float y,int dir,unsigned ink=uitheme::accent()){renderer.primitive(c,{{x-4,y+dir*3.f},{x+4,y+dir*3.f},{x,y-dir*4.f}},ink,true);}
 void rounded(ID3D11DeviceContext*c,float x,float y,float w,float h,float radius,unsigned fill){
  auto&r=renderer;if(w<=0||h<=0)return;float rad=(std::min)(radius,(std::min)(w,h)*.5f);if(rad<=0){r.rectangle(c,x,y,w,h,fill);return;}std::vector<std::array<float,2>>points,triangles;const float centres[4][2]={{x+rad,y+rad},{x+w-rad,y+rad},{x+w-rad,y+h-rad},{x+rad,y+h-rad}};
  for(int corner=0;corner<4;++corner)for(int i=0;i<=4;++i){float a=3.14159265f+(corner*4+i)*1.57079633f/4;points.push_back({centres[corner][0]+rad*std::cos(a),centres[corner][1]+rad*std::sin(a)});}
  for(size_t i=0;i<points.size();++i){triangles.push_back({x+w/2,y+h/2});triangles.push_back(points[i]);triangles.push_back(points[(i+1)%points.size()]);}r.primitive(c,triangles,fill,true);
 }
 void panel(ID3D11DeviceContext*c,float x,float y,float w,float h){bool active=!expanded&&!nav.rounds&&nav.fullList<0&&((nav.focus==0&&x==60&&y==155)||(nav.focus==1&&x==757&&y==155)||(nav.focus==2&&x==757&&y==480)||(nav.focus==3&&x==1124&&y==155)||(nav.focus==4&&x==60&&y==810)||(nav.focus==5&&x==808&&y==810));float border=active?3.f:1.f;rounded(c,x,y+2,w,h,10,0x0c193348);rounded(c,x,y,w,h,10,active?uitheme::accent():0xffe6edf3);rounded(c,x+border,y+border,w-2*border,h-2*border,8,0xfff9fbfe);}
 void table(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;panel(c,60,155,682,635);
  if(comp.groups.empty()){text(c,"Aguardando a composição dos grupos",90,370,620,65,24,RGB(116,138,150),true);return;}
  group=std::clamp(group,0,int(comp.groups.size())-1);auto&g=comp.groups[group];scroll=std::clamp(scroll,0,(std::max)(0,int(g.rows.size())-20));
  r.line(c,74,207,728,207,0xffe5edf3);text(c,comp.format=="league"?"CLASSIFICAÇÃO":g.name+"  ·  "+std::to_string(group+1)+" / "+std::to_string(comp.groups.size()),82,165,405,31,23);if(comp.format=="league")text(c,"Ver rodadas  ›",500,168,187,27,18,uitheme::accentInk(),true);else{text(c,"Ver chaveamento  ›",500,168,187,27,18,uitheme::accentInk(),true);text(c,"‹",69,165,30,31,27,uitheme::accentInk(),true);text(c,"›",695,165,30,31,27,uitheme::accentInk(),true);}
  text(c,"CLUBE",143,208,224,26,14);text(c,"#",75,208,26,26,14);text(c,"ÚLTIMAS 5",329,208,62,26,12,RGB(116,138,150),true);const char*heads[]={"J","V","E","D","GP","GC","SG","PTS"};for(int i=0;i<8;++i)text(c,heads[i],393+i*42.f,208,40,26,14,RGB(116,138,150),true);
  int rows=(std::min)(20,int(g.rows.size())-scroll);for(int i=0;i<rows;++i){auto&t=g.rows[scroll+i];float y=235+i*24.4f;bool own=t.id==data.club;unsigned bg=own?0xff005db9:(i%2?0xffeaf1f8:0xfff4f8fc);r.rectangle(c,68,y,666,24,bg);auto ink=own?uitheme::selectedText():RGB(36,66,94);if(!t.color.empty())r.rectangle(c,68,y,4,24,color(t.color));text(c,std::to_string(t.rank),76,y,25,24,16,ink,true);if(t.movement){arrow(c,110,y+12,t.movement>0?1:-1,t.movement>0?0xff55a65b:0xffcf6164);}else r.rectangle(c,106,y+11,7,2,own?0xffd6e7ee:0xffaebdc5);image(c,"crest",t.id,118,y+1,23,23);text(c,t.name,147,y,187,24,17,ink);for(size_t f=0;f<t.form.size()&&f<5;++f){unsigned shade=t.form[f]=='V'?0xff4c9b63:t.form[f]=='D'?0xffca6468:0xff9daeb7;rounded(c,341+float(f)*8,y+9,6,6,3,shade);}
   int values[]={t.games,t.wins,t.draws,t.losses,t.gf,t.ga,(t.gf<0||t.ga<0)?-1000:t.gf-t.ga,t.points};for(int j=0;j<8;++j)text(c,j==6?(values[j]==-1000?"—":std::to_string(values[j])):num(values[j]),393+j*42.f,y,40,24,16,ink,true);
  }
  float lx=79,ly=735;for(auto&z:g.legend){int width=(std::min)(320,25+int(z.second.size())*8);if(lx+width>733){lx=79;ly+=22;}if(ly>765)break;rounded(c,lx,ly+8,8,8,4,color(z.first));text(c,z.second,lx+15,ly,width-15,24,14,RGB(116,138,150));lx+=width;}
  if(g.rows.size()>20)text(c,std::to_string(scroll+1)+"–"+std::to_string(scroll+rows)+" de "+std::to_string(g.rows.size()),80,771,630,18,13,RGB(116,138,150),true);
 }
 void cup(ID3D11DeviceContext*c,clubcomp::Competition&comp,bool embedded=false){
  auto&r=renderer;if(!embedded){panel(c,60,155,682,635);r.line(c,74,207,728,207,0xffe5edf3);text(c,"‹",69,165,30,31,27,uitheme::accentInk(),true);text(c,"›",695,165,30,31,27,uitheme::accentInk(),true);text(c,"CHAVEAMENTO",106,165,370,31,23);text(c,"Ver chaveamento  ›",500,168,187,27,18,uitheme::accentInk(),true);}
  if(comp.rounds.empty()){text(c,"Aguardando os confrontos do mata-mata",82,355,638,55,23,RGB(116,138,150),true);text(c,"O sorteio aparecerá quando estiver registrado na carreira.",82,413,638,50,18,RGB(116,138,150),true);return;}
  round=std::clamp(round,0,int(comp.rounds.size())-1);
  int total=int(comp.rounds[round].ties.size());if(total>4){float thumb=496.f*4/total;rounded(c,733,252,5,496,2,0xffdce6ee);rounded(c,733,252+(496-thumb)*scroll/(total-4),5,thumb,2,uitheme::accent());}
  for(int col=0;col<2;++col){int index=round+col;if(index>=int(comp.rounds.size()))break;auto&phase=comp.rounds[index];float x=78+col*338.f;int start=col?scroll/2:scroll;start=(std::min)(start,(std::max)(0,int(phase.ties.size())-4));int count=(std::min)(4,int(phase.ties.size())-start);
   text(c,phase.name,x,212,310,30,22,uitheme::accentInk());if(phase.ties.empty()){r.rectangle(c,x,379,310,118,0xffedf3f6);text(c,"A definir",x+16,395,278,36,23,RGB(116,138,150),true);text(c,"Aguardando o sorteio desta fase",x+16,438,278,35,16,RGB(116,138,150),true);}for(int j=0;j<count;++j){auto&t=phase.ties[start+j];float y=252+j*127.f;unsigned border=(t.home==data.club||t.away==data.club)?uitheme::accent():0xffc9d8e1;r.rectangle(c,x,y,310,118,border);r.rectangle(c,x+2,y+2,306,114,0xffedf3f6);
    for(int side=0;side<2;++side){int id=side?t.away:t.home;float yy=y+7+side*28;image(c,"crest",id,x+8,yy,24,24);text(c,side?t.awayName:t.homeName,x+40,yy,220,24,18,id==t.winner?uitheme::accentInk():RGB(52,77,90));text(c,num(side?t.a:t.h),x+266,yy,35,24,21,uitheme::accentInk(),true);}
    std::string detail=t.legs.size()>1?"Agregado · ida e volta":"Jogo único";text(c,detail,x+10,y+66,290,20,13,RGB(116,138,150));
    for(size_t k=0;k<t.legs.size()&&k<2;++k){auto&l=t.legs[k];std::string date=std::to_string(l.date);date=date.size()==8?date.substr(6,2)+"/"+date.substr(4,2):"A definir";std::string score=l.h<0?"a disputar":std::to_string(l.h)+"–"+std::to_string(l.a);text(c,date+"  "+(t.legs.size()>1?(k?"Volta  ":"Ida  "):"")+score,x+10,y+86+float(k)*14,290,16,12,RGB(116,138,150));}
    // Connect only ties which actually share a registered participant.
    if(col==0&&round+1<int(comp.rounds.size())){auto&next=comp.rounds[round+1];for(int k=0;k<(std::min)(4,int(next.ties.size())-(std::min)(scroll/2,(std::max)(0,int(next.ties.size())-4)));++k){auto&n=next.ties[(std::min)(scroll/2,(std::max)(0,int(next.ties.size())-4))+k];if(t.home==n.home||t.home==n.away||t.away==n.home||t.away==n.away){float target=252+k*127.f+58;r.line(c,x+310,y+58,x+324,y+58,0xffa8bdc9);r.line(c,x+324,y+58,x+324,target,0xffa8bdc9);r.line(c,x+324,target,x+338,target,0xffa8bdc9);}}}
   }
   text(c,phase.ties.empty()?"Sorteio pendente":std::to_string(start+1)+"–"+std::to_string(start+count)+" de "+std::to_string(phase.ties.size())+" confrontos",x,765,310,24,14,RGB(116,138,150),true);
  }
 }
 int mixedMaximum(const clubcomp::Competition&comp)const{int height=0;for(auto&g:comp.groups)height+=55+int(g.rows.size())*28;return (std::max)(0,height+625-561);}
 void mixed(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;panel(c,60,155,682,635);text(c,comp.knockoutFirst?"FASE ELIMINATÓRIA":"FASE DE GRUPOS",82,165,390,31,23);text(c,"Ver chaveamento  ›",490,168,204,27,18,uitheme::accentInk(),true);r.line(c,74,207,728,207,0xffe5edf3);
  mixedScroll=std::clamp(mixedScroll,0,mixedMaximum(comp));
  if(!canvasClip){D3D11_RASTERIZER_DESC desc{};r.raster->GetDesc(&desc);desc.ScissorEnable=TRUE;r.device->CreateRasterizerState(&desc,&canvasClip);}if(!canvasClip)return;
  ID3D11RasterizerState*oldRaster=nullptr;c->RSGetState(&oldRaster);D3D11_RECT old[16]{};UINT count=16;c->RSGetScissorRects(&count,old);D3D11_RECT clip{LONG(r.left+64*r.scale),LONG(r.top+212*r.scale),LONG(r.left+728*r.scale),LONG(r.top+779*r.scale)};if(count){clip.left=(std::max)(clip.left,old[0].left);clip.top=(std::max)(clip.top,old[0].top);clip.right=(std::min)(clip.right,old[0].right);clip.bottom=(std::max)(clip.top,(std::min)(clip.bottom,old[0].bottom));}c->RSSetState(canvasClip);c->RSSetScissorRects(1,&clip);
  float y=218.f-mixedScroll;
  auto knockout=[&](){float oldTop=r.top;r.top+=(y-212)*r.scale;if(y<779&&y+578>212)cup(c,comp,true);r.top=oldTop;y+=578;};
  if(comp.knockoutFirst){knockout();r.line(c,82,y,710,y,uitheme::accent());text(c,"FASE DE GRUPOS",86,y+9,610,28,20,uitheme::accentInk());y+=47;}
  for(auto&g:comp.groups){float height=55.f+g.rows.size()*28.f;
   if(y+height>=212&&y<779){rounded(c,74,y,642,height-12,7,0xffedf3f8);text(c,g.name,86,y+5,290,27,20,uitheme::accentInk());text(c,"J     V     E     D     SG     PTS",397,y+8,308,22,13,RGB(109,132,152),true);
    for(size_t i=0;i<g.rows.size();++i){auto&t=g.rows[i];float yy=y+36+i*28.f;if(yy+27<212||yy>779)continue;bool own=t.id==data.club;r.rectangle(c,79,yy,632,26,own?uitheme::accent():i%2?0xffe8f0f6:0xfff8fbfd);auto ink=own?uitheme::selectedText():RGB(36,66,94);text(c,std::to_string(t.rank),86,yy,26,26,16,ink,true);image(c,"crest",t.id,118,yy+1,23,24);text(c,t.name,150,yy,238,26,17,ink);int values[]={t.games,t.wins,t.draws,t.losses,t.gf<0||t.ga<0?-1:t.gf-t.ga,t.points};for(int j=0;j<6;++j)text(c,j==4?(t.gf<0||t.ga<0?"—":std::to_string(values[j])):num(values[j]),398+j*50.f,yy,48,26,16,ink,true);}
   }y+=height;
  }
  if(!comp.knockoutFirst){r.line(c,82,y,710,y,uitheme::accent());text(c,"FASE ELIMINATÓRIA",86,y+9,610,28,20,uitheme::accentInk());y+=47;knockout();}
  c->RSSetState(oldRaster);clubgfx::release(oldRaster);c->RSSetScissorRects(count,old);
  float track=553,content=float(mixedMaximum(comp)+561),thumb=(std::max)(40.f,track*561/content);rounded(c,733,218,5,track,2.5f,0xffdce6ee);rounded(c,733,218+(track-thumb)*mixedScroll/(std::max)(1,mixedMaximum(comp)),5,thumb,2.5f,uitheme::accent());
 }
 void pitch(ID3D11DeviceContext*c,clubcomp::Competition&comp,float offset=0){
  auto&r=renderer;auto box=clubcomp::pitchArea;box.y-=offset;panel(c,box.x,box.y,box.w,box.h);text(c,"TIME DO CAMPEONATO",box.x+16,167-offset,286,30,22,RGB(22,49,74));
  rounded(c,box.x+box.w-82,167-offset,66,29,6,0xffedf4f9);text(c,comp.formation.empty()?"—":comp.formation,box.x+box.w-80,169-offset,62,25,16,RGB(37,70,101),true);text(c,"Média das notas nas partidas da competição",box.x+16,201-offset,int(box.w)-32,22,14,RGB(109,132,152));
  const auto field=clubcomp::fieldArea;float x=field.x,y=field.y-offset,w=field.w,h=field.h;rounded(c,x-1,y-1,w+2,h+2,9,0xff96b69b);rounded(c,x,y,w,h,8,0xff22582c);
  for(int i=0;i<10;++i)if(i%2)r.rectangle(c,x+1,y+i*h/10+1,w-2,h/10-2,0xff286330);
  unsigned line=0xff81a783;float left=x+8,right=x+w-8,top=y+8,bottom=y+h-8;
  r.line(c,left,top,right,top,line);r.line(c,left,bottom,right,bottom,line);r.line(c,left,top,left,bottom,line);r.line(c,right,top,right,bottom,line);r.line(c,left,y+h/2,right,y+h/2,line);
  auto area=[&](float width,float depth){float xx=x+(w-width)/2;for(int side=0;side<2;++side){float edge=side?bottom:top,inner=side?bottom-depth:top+depth;r.line(c,xx,edge,xx,inner,line);r.line(c,xx+width,edge,xx+width,inner,line);r.line(c,xx,inner,xx+width,inner,line);}};area(w*.55f,66);area(w*.27f,24);
  for(int i=0;i<36;++i){float a=float(i)*6.2831853f/36,b=float(i+1)*6.2831853f/36;r.line(c,x+w/2+43*std::cos(a),y+h/2+43*std::sin(a),x+w/2+43*std::cos(b),y+h/2+43*std::sin(b),line);}
  if(comp.starters.size()!=11){rounded(c,x+16,y+176,w-32,133,7,0xc0143822);text(c,"Aguardando notas das partidas",x+24,y+185,int(w)-48,50,21,RGB(255,255,255),true);text(c,"Seleção pelo desempenho na carreira.",x+24,y+244,int(w)-48,40,15,RGB(224,238,225),true);}
  for(auto&place:clubcomp::placeCompetitionXI(comp.starters)){
   auto&p=comp.starters[place.player];float xx=place.x,yy=place.y-offset;image(c,"head",p.id,xx-26,yy,52,58);
   rounded(c,xx-37,yy+51,74,18,4,0xe0123021);image(c,"crest",p.club,xx-34,yy+51,17,18);text(c,p.rating,xx-12,yy+50,44,20,15,RGB(255,255,255),true);
   auto name=p.name;auto last=name.find_last_of(' ');if(last!=std::string::npos)name=name.substr(last+1);rounded(c,xx-place.width/2,yy+71,place.width,18,4,0x8a133820);text(c,name,xx-place.width/2+2,yy+70,int(place.width)-4,20,14,RGB(255,255,255),true);
  }
  text(c,comp.starters.empty()?"":"Seleção por posição · notas reais da carreira",box.x+16,753-offset,int(box.w)-32,26,14,RGB(109,132,152),true);
 }
 #include "competitions_dashboard.inc"
 #include "competitions_bracket.inc"
 void draw(ID3D11DeviceContext*c){
  auto&r=renderer;if(device!=r.device){clearTextures();device=r.device;}label=0;++textFrame;r.normal(c);r.rectangle(c,40,20,1520,790,0xffedf2f5);
  if(!ready){text(c,"COMPETIÇÕES DA CARREIRA",80,65,1440,65,35);text(c,lineup.status=="error"?lineup.message:"Carregando as competições desta carreira...",80,350,1440,90,25,RGB(116,138,150),true);return;}
  if(data.competitions.empty()){text(c,"Nenhuma competição registrada para este clube",80,350,1440,90,25,RGB(116,138,150),true);return;}
  selected=std::clamp(selected,0,int(data.competitions.size())-1);auto&comp=data.competitions[selected];if(nav.fullList>=0){drawFullLeaders(c,comp);return;}if(expanded){drawExpanded(c,comp);return;}if(nav.rounds){drawMatchdays(c,comp);return;}r.rectangle(c,40,20,1520,80,0xfff8fbfc);image(c,"comp",comp.asset,136,32,60,57);text(c,"‹",68,35,56,53,44,uitheme::accentInk(),true);text(c,"›",1477,35,56,53,44,uitheme::accentInk(),true);text(c,comp.name,214,29,1100,45,31);text(c,comp.status+" · "+data.clubName+" · "+std::to_string(data.date/10000),216,71,1100,25,16,RGB(116,138,150));if(comp.rank>0)text(c,std::to_string(comp.rank)+"º  ·  "+num(comp.points)+" PTS",1298,35,168,47,23,uitheme::accentInk(),true);
  float tabWidth=1504.f/data.competitions.size();for(size_t i=0;i<data.competitions.size();++i){float xx=48+i*tabWidth;r.rectangle(c,xx,102,tabWidth-5,40,i==selected?uitheme::accent():0xffdde6eb);text(c,data.competitions[i].name,xx+8,106,int(tabWidth)-21,32,15,i==selected?uitheme::selectedText():RGB(52,77,90),true);}
  dashboardBody(c,comp);r.normal(c);
 }
} competitions;
