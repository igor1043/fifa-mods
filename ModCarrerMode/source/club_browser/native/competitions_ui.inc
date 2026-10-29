// This screen never creates a player or touches the native FCE database.
#include "competitions_model.h"
#include "competitions_layout.h"
struct CompetitionView{
 clubcomp::Data data;int selected=0,group=0,round=0,scroll=0,stat=0,statScroll=0;bool bracket=false,ready=false,expanded=false;float canvasZoom=1,canvasPanX=0,canvasPanY=0,canvasCenterX=0,canvasCenterY=0;ID3D11RasterizerState*canvasClip=nullptr;uint64_t submitted=0,retry=0,checked=0;int currentClub=0;fs::file_time_type publication{};
 std::array<clubgfx::Texture,2048>labels;std::map<std::string,clubgfx::Texture>images;int label=0;ID3D11Device* device=nullptr;
 void clearTextures(){clubgfx::release(canvasClip);for(auto&t:labels)t.clear();for(auto&it:images)it.second.clear();images.clear();device=nullptr;}
 void resetSelection(){group=round=scroll=statScroll=0;bracket=false;if(data.competitions.empty())return;auto&c=data.competitions[selected];for(size_t i=0;i<c.groups.size();++i)for(auto&t:c.groups[i].rows)if(t.id==data.club)group=int(i);bracket=c.groups.empty();for(size_t i=0;i<c.rounds.size();++i)for(auto&t:c.rounds[i].ties)if(t.home==data.club||t.away==data.club)round=int(i);}
 void enter(int club){data={};selected=0;ready=false;expanded=false;currentClub=club;submitted=retry=checked=0;clearTextures();request();}
 void request(){if(currentClub<=0)return;lineup.request(currentClub,"competitions");submitted=lineup.sequence;retry=GetTickCount64()+3000;}
 void poll(){
  auto now=GetTickCount64();int liveClub=careerClub();if(liveClub>0&&liveClub!=currentClub){enter(liveClub);return;}if(!submitted&&!ready){if(liveClub){currentClub=liveClub;request();}return;}if(submitted)lineup.poll(renderer.device);
  if(lineup.sequence==submitted&&lineup.status=="ready"){
   std::ifstream input(lineup.folder/L"competitions.tsv",std::ios::binary);clubcomp::Data next;
   if(clubcomp::parse(input,submitted,currentClub,next)){int oldRoot=ready&&!data.competitions.empty()?data.competitions[selected].root:0;data=std::move(next);if(!ready){selected=0;resetSelection();}else{auto it=std::find_if(data.competitions.begin(),data.competitions.end(),[&](auto&c){return c.root==oldRoot;});selected=it==data.competitions.end()?0:int(it-data.competitions.begin());if(it==data.competitions.end())resetSelection();}ready=true;submitted=0;checked=now+1000;std::error_code ec;publication=fs::last_write_time(art.game/L"ModCarrerMode/runtime/career_fce_snapshot.json",ec);}
   else{lineup.status="error";lineup.lastValues["retry"]="1";lineup.message="Os dados da competição mudaram. Reabrindo a leitura...";}
  }
  if(lineup.status=="error"&&submitted&&now>=retry&&lineup.lastValues["retry"]=="1")request();
  if(ready&&!submitted&&now>=checked){checked=now+1000;std::error_code ec;auto stamp=fs::last_write_time(art.game/L"ModCarrerMode/runtime/career_fce_snapshot.json",ec);int club=careerClub();if(club&&club!=currentClub){enter(club);return;}if(!ec&&stamp!=publication){publication=stamp;request();}}
 }
 void command(const std::string&s){if(s=="comp_refresh"){request();return;}if(!ready||data.competitions.empty())return;auto&c=data.competitions[selected];
  if(s=="comp_bracket"){expanded=true;fitBracket();return;}if(s=="comp_close"){expanded=false;return;}if(s=="comp_center"){fitBracket();return;}if(expanded)return;
  if(s=="comp_prev"||s=="comp_next"){int d=s=="comp_prev"?-1:1;selected=(selected+d+int(data.competitions.size()))%int(data.competitions.size());resetSelection();}
  else if(s=="comp_stat_prev"||s=="comp_stat_next"){stat=1-stat;statScroll=0;}
  else if(s=="comp_mode"){if(c.format=="cup"){bracket=!bracket;scroll=0;}}
  else if(s=="comp_left"||s=="comp_right"){int d=s=="comp_left"?-1:1;if(c.format=="cup"){int count=int(bracket?c.rounds.size():c.groups.size());if(count){int&index=bracket?round:group;index=(index+d+count)%count;scroll=0;}}}
  else if(s=="comp_up"||s=="comp_down"){int d=s=="comp_up"?-1:1;int count=bracket?(c.rounds.empty()?0:int(c.rounds[(std::min)(round,int(c.rounds.size())-1)].ties.size())):c.groups.empty()?0:int(c.groups[(std::min)(group,int(c.groups.size())-1)].rows.size());scroll=std::clamp(scroll+d,0,(std::max)(0,count-(bracket?4:20)));}
  else if(s=="comp_stat_up"||s=="comp_stat_down")statScroll=std::clamp(statScroll+(s=="comp_stat_up"?-1:1),0,(std::max)(0,int(c.leaders[stat].size())-6));
 }
 void controls(HWND window,float w,float h){
  DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId())return;if(expanded){bracketControls(window,w,h);return;}
  static bool keys[256]{};auto key=[&](int code){bool held=(GetAsyncKeyState(code)&0x8000)!=0,edge=held&&!keys[code];keys[code]=held;return edge;};
  XINPUT_STATE pad{};if(readPad)for(DWORD i=0;i<4;++i)if(readPad(i,&pad)==ERROR_SUCCESS)break;static WORD previous=0;WORD edges=pad.Gamepad.wButtons&~previous;previous=pad.Gamepad.wButtons;
  static bool lt=false,rt=false;bool l=pad.Gamepad.bLeftTrigger>120,r=pad.Gamepad.bRightTrigger>120;
  if(key('X')||(edges&XINPUT_GAMEPAD_LEFT_SHOULDER))command("comp_prev");if(key('C')||(edges&XINPUT_GAMEPAD_RIGHT_SHOULDER))command("comp_next");
  if(key('W')||(l&&!lt))command("comp_stat_prev");if(key('E')||(r&&!rt))command("comp_stat_next");lt=l;rt=r;
  bool left=(GetAsyncKeyState(VK_LEFT)&0x8000)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX< -16000;
  bool right=(GetAsyncKeyState(VK_RIGHT)&0x8000)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>16000;
  bool up=(GetAsyncKeyState(VK_UP)&0x8000)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>16000;
  bool down=(GetAsyncKeyState(VK_DOWN)&0x8000)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY< -16000;
  int direction=left?1:right?2:up?3:down?4:0;static int before=0;static uint64_t repeat=0;auto now=GetTickCount64();if(direction&&(direction!=before||now>=repeat)){command(direction==1?"comp_left":direction==2?"comp_right":direction==3?"comp_up":"comp_down");repeat=now+(direction!=before?350:140);}before=direction;
  static int statDir=0;static uint64_t statRepeat=0;int dir=pad.Gamepad.sThumbRY>16000?-1:pad.Gamepad.sThumbRY< -16000?1:0;if(dir&&(dir!=statDir||now>=statRepeat)){command(dir<0?"comp_stat_up":"comp_stat_down");statRepeat=now+(dir!=statDir?350:140);}statDir=dir;
  POINT p{};GetCursorPos(&p);ScreenToClient(window,&p);float fit=(std::min)(w/1600,h/900),mx=(p.x-(w-1600*fit)/2)/fit,my=(p.y-(h-900*fit)/2)/fit;
  if(key(VK_LBUTTON)){
   if(my>=20&&my<100){if(mx<130)command("comp_prev");else if(mx>1470)command("comp_next");}
   else if(my>=100&&my<142&&ready&&!data.competitions.empty()){int n=int(data.competitions.size()),i=std::clamp(int((mx-48)/(1504.f/n)),0,n-1);selected=i;resetSelection();}
   else if(mx>=clubcomp::leadersArea.x&&mx<clubcomp::leadersArea.x+clubcomp::leadersArea.w&&my>=155&&my<215)command("comp_stat_next");
   else if(mx>=60&&mx<742&&my>=155&&my<216&&!(mx>=500&&mx<690)){if(mx>690)command("comp_right");else if(mx<110)command("comp_left");else command("comp_mode");}
  }
  int wheel=wheelDelta.exchange(0);if(wheel)command(mx>=clubcomp::leadersArea.x&&mx<clubcomp::leadersArea.x+clubcomp::leadersArea.w?(wheel>0?"comp_stat_up":"comp_stat_down"):(wheel>0?"comp_up":"comp_down"));
 }
 void text(ID3D11DeviceContext*c,const std::string&value,float x,float y,int w,int h,int size,COLORREF ink=RGB(25,52,76),bool center=false){if(label>=int(labels.size()))return;auto&t=labels[label++];clubgfx::text(renderer.device,t,wide(value),w,h,size,ink,center);renderer.normal(c);renderer.quad(c,x,y,float(w),float(h),t.view);}
 static std::string num(int n){return n<0?"—":std::to_string(n);}
 void image(ID3D11DeviceContext*c,const std::string&kind,int id,float x,float y,float w,float h){if(id<=0)return;std::string key=kind+std::to_string(id);if(images.size()>512&&!images.count(key)){for(auto&it:images)it.second.clear();images.clear();}auto&t=images[key];std::string i=std::to_string(id);std::vector<std::string>paths=kind=="head"?std::vector<std::string>{"data/ui/imgAssets/heads/p"+i+".dds","data/ui/imgAssets/heads/p0.dds"}:kind=="comp"?std::vector<std::string>{"data/ui/imgAssets/careerCompetitionIcons/"+i+".png","data/ui/imgAssets/league/light/l"+i+".dds","data/ui/imgAssets/league/dark/l"+i+".dds"}:std::vector<std::string>{"data/ui/imgAssets/crest/light/l"+i+".dds","data/ui/imgAssets/crest/dark/l"+i+".dds"};clubgfx::gameImage(renderer.device,t,art,paths);if(!t.view||!t.w||!t.h)return;float fit=(std::min)(w/t.w,h/t.h);renderer.normal(c);renderer.quad(c,x+(w-t.w*fit)/2,y+(h-t.h*fit)/2,t.w*fit,t.h*fit,t.view);}
 unsigned color(const std::string&v,unsigned fallback=0xffd6e0e5){if(v.size()!=7||v[0]!='#')return fallback;try{return 0xff000000|unsigned(std::stoul(v.substr(1),nullptr,16));}catch(...){return fallback;}}
 void arrow(ID3D11DeviceContext*c,float x,float y,int dir,unsigned ink=uitheme::accent()){renderer.primitive(c,{{x-4,y+dir*3.f},{x+4,y+dir*3.f},{x,y-dir*4.f}},ink,true);}
 void rounded(ID3D11DeviceContext*c,float x,float y,float w,float h,float radius,unsigned fill){
  auto&r=renderer;if(w<=0||h<=0)return;float rad=(std::min)(radius,(std::min)(w,h)*.5f);if(rad<=0){r.rectangle(c,x,y,w,h,fill);return;}std::vector<std::array<float,2>>points,triangles;const float centres[4][2]={{x+rad,y+rad},{x+w-rad,y+rad},{x+w-rad,y+h-rad},{x+rad,y+h-rad}};
  for(int corner=0;corner<4;++corner)for(int i=0;i<=4;++i){float a=3.14159265f+(corner*4+i)*1.57079633f/4;points.push_back({centres[corner][0]+rad*std::cos(a),centres[corner][1]+rad*std::sin(a)});}
  for(size_t i=0;i<points.size();++i){triangles.push_back({x+w/2,y+h/2});triangles.push_back(points[i]);triangles.push_back(points[(i+1)%points.size()]);}r.primitive(c,triangles,fill,true);
 }
 void panel(ID3D11DeviceContext*c,float x,float y,float w,float h){rounded(c,x,y+2,w,h,10,0x0c193348);rounded(c,x,y,w,h,10,0xffe0eaf2);rounded(c,x+1,y+1,w-2,h-2,9,0xfff9fbfe);}
 void table(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;panel(c,60,155,682,635);
  if(comp.groups.empty()){text(c,"Aguardando a composição dos grupos",90,370,620,65,24,RGB(116,138,150),true);return;}
  group=std::clamp(group,0,int(comp.groups.size())-1);auto&g=comp.groups[group];
  r.line(c,74,207,728,207,0xffe5edf3);text(c,comp.format=="league"?"CLASSIFICAÇÃO":g.name+"  ·  "+std::to_string(group+1)+" / "+std::to_string(comp.groups.size()),82,165,565,31,23);if(comp.format=="cup"){text(c,"Ver chaveamento",500,168,187,27,18,uitheme::accentInk(),true);text(c,"‹",69,165,30,31,27,uitheme::accentInk(),true);text(c,"›",695,165,30,31,27,uitheme::accentInk(),true);}
  text(c,"CLUBE",143,208,224,26,14);text(c,"#",75,208,26,26,14);text(c,"ÚLTIMAS 5",329,208,62,26,12,RGB(116,138,150),true);const char*heads[]={"J","V","E","D","GP","GC","SG","PTS"};for(int i=0;i<8;++i)text(c,heads[i],393+i*42.f,208,40,26,14,RGB(116,138,150),true);
  int rows=(std::min)(20,int(g.rows.size())-scroll);for(int i=0;i<rows;++i){auto&t=g.rows[scroll+i];float y=235+i*24.4f;bool own=t.id==data.club;unsigned bg=own?0xff005db9:(i%2?0xffeaf1f8:0xfff4f8fc);r.rectangle(c,68,y,666,24,bg);auto ink=own?uitheme::selectedText():RGB(36,66,94);if(!t.color.empty())r.rectangle(c,68,y,4,24,color(t.color));text(c,std::to_string(t.rank),76,y,25,24,16,ink,true);if(t.movement){arrow(c,110,y+12,t.movement>0?1:-1,t.movement>0?0xff55a65b:0xffcf6164);}else r.rectangle(c,106,y+11,7,2,own?0xffd6e7ee:0xffaebdc5);image(c,"crest",t.id,118,y+1,23,23);text(c,t.name,147,y,187,24,17,ink);for(size_t f=0;f<t.form.size()&&f<5;++f){unsigned shade=t.form[f]=='V'?0xff4c9b63:t.form[f]=='D'?0xffca6468:0xff9daeb7;rounded(c,341+float(f)*8,y+9,6,6,3,shade);}
   int values[]={t.games,t.wins,t.draws,t.losses,t.gf,t.ga,(t.gf<0||t.ga<0)?-1000:t.gf-t.ga,t.points};for(int j=0;j<8;++j)text(c,j==6?(values[j]==-1000?"—":std::to_string(values[j])):num(values[j]),393+j*42.f,y,40,24,16,ink,true);
  }
  float lx=79,ly=735;for(auto&z:g.legend){int width=(std::min)(320,25+int(z.second.size())*8);if(lx+width>733){lx=79;ly+=22;}if(ly>765)break;rounded(c,lx,ly+8,8,8,4,color(z.first));text(c,z.second,lx+15,ly,width-15,24,14,RGB(116,138,150));lx+=width;}
  if(g.rows.size()>20)text(c,std::to_string(scroll+1)+"–"+std::to_string(scroll+rows)+" de "+std::to_string(g.rows.size()),80,771,630,18,13,RGB(116,138,150),true);
 }
 void cup(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;panel(c,60,155,682,635);r.line(c,74,207,728,207,0xffe5edf3);text(c,"‹",69,165,30,31,27,uitheme::accentInk(),true);text(c,"›",695,165,30,31,27,uitheme::accentInk(),true);text(c,"CHAVEAMENTO",106,165,370,31,23);text(c,"Ver chaveamento",500,168,187,27,18,uitheme::accentInk(),true);
  if(comp.rounds.empty()){text(c,"Aguardando os confrontos do mata-mata",82,355,638,55,23,RGB(116,138,150),true);text(c,"O sorteio aparecerá quando estiver registrado na carreira.",82,413,638,50,18,RGB(116,138,150),true);return;}
  round=std::clamp(round,0,int(comp.rounds.size())-1);
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
 void leaders(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;const auto box=clubcomp::leadersArea;const float x=box.x,w=box.w;panel(c,x,box.y,w,box.h);
  text(c,"‹",x+6,165,30,32,26,uitheme::accentInk(),true);text(c,stat?"ASSISTÊNCIAS":"ARTILHEIROS",x+38,165,int(w)-76,32,23,RGB(22,49,74),true);text(c,"›",x+w-36,165,30,32,26,uitheme::accentInk(),true);r.line(c,x+12,207,x+w-12,207,0xffe5edf3);
  auto&list=comp.leaders[stat];statScroll=std::clamp(statScroll,0,(std::max)(0,int(list.size())-6));
  for(int i=0;i<6&&statScroll+i<int(list.size());++i){
   auto&p=list[statScroll+i];const float y=222+i*85.f,copy=x+118,value=x+w-51;const int copyWidth=int(value-copy-11);
   rounded(c,x+10,y,w-20,78,8,i%2?0xffedf4f9:0xfff1f6fa);rounded(c,x+19,y+25,23,29,4,0xffdfeaf3);text(c,std::to_string(statScroll+i+1),x+19,y+25,23,29,18,RGB(63,94,119),true);
   image(c,"head",p.id,x+46,y+5,60,70);image(c,"crest",p.club,x+87,y+53,21,22);
   text(c,p.name,copy,y+9,copyWidth,25,19,RGB(27,54,78));
   if(!p.position.empty())text(c,p.position,copy,y+34,copyWidth,19,13,RGB(100,125,148));
   text(c,p.clubName,copy,y+53,copyWidth,18,13,RGB(100,125,148));text(c,std::to_string(p.value),value,y+21,40,36,29,uitheme::accentInk(),true);
  }
  if(list.empty())text(c,"Sem registros nesta competição",x+20,355,int(w)-40,60,18,RGB(116,138,150),true);
  for(int i=0;i<2;++i)rounded(c,x+w/2-26+i*32.f,745,21,5,2.5f,i==stat?uitheme::accent():0xffc8d8e6);
  text(c,list.empty()?"":std::to_string(statScroll+1)+"–"+std::to_string((std::min)(statScroll+6,int(list.size())))+" de "+std::to_string(list.size()),x+20,761,int(w)-40,23,14,RGB(109,132,152),true);
 }
 void pitch(ID3D11DeviceContext*c,clubcomp::Competition&comp){
  auto&r=renderer;const auto box=clubcomp::pitchArea;panel(c,box.x,box.y,box.w,box.h);text(c,"TIME DO CAMPEONATO",box.x+16,167,286,30,22,RGB(22,49,74));
  rounded(c,box.x+box.w-82,167,66,29,6,0xffedf4f9);text(c,comp.formation.empty()?"—":comp.formation,box.x+box.w-80,169,62,25,16,RGB(37,70,101),true);text(c,"Média das notas nas partidas da competição",box.x+16,201,int(box.w)-32,22,14,RGB(109,132,152));
  const auto field=clubcomp::fieldArea;float x=field.x,y=field.y,w=field.w,h=field.h;rounded(c,x-1,y-1,w+2,h+2,9,0xff96b69b);rounded(c,x,y,w,h,8,0xff22582c);
  for(int i=0;i<10;++i)if(i%2)r.rectangle(c,x+1,y+i*h/10+1,w-2,h/10-2,0xff286330);
  unsigned line=0xff81a783;float left=x+8,right=x+w-8,top=y+8,bottom=y+h-8;
  r.line(c,left,top,right,top,line);r.line(c,left,bottom,right,bottom,line);r.line(c,left,top,left,bottom,line);r.line(c,right,top,right,bottom,line);r.line(c,left,y+h/2,right,y+h/2,line);
  auto area=[&](float width,float depth){float xx=x+(w-width)/2;for(int side=0;side<2;++side){float edge=side?bottom:top,inner=side?bottom-depth:top+depth;r.line(c,xx,edge,xx,inner,line);r.line(c,xx+width,edge,xx+width,inner,line);r.line(c,xx,inner,xx+width,inner,line);}};area(w*.55f,66);area(w*.27f,24);
  for(int i=0;i<36;++i){float a=float(i)*6.2831853f/36,b=float(i+1)*6.2831853f/36;r.line(c,x+w/2+43*std::cos(a),y+h/2+43*std::sin(a),x+w/2+43*std::cos(b),y+h/2+43*std::sin(b),line);}
  if(comp.starters.size()!=11){rounded(c,x+16,y+176,w-32,133,7,0xc0143822);text(c,"Aguardando notas das partidas",x+24,y+185,int(w)-48,50,21,RGB(255,255,255),true);text(c,"Seleção pelo desempenho na carreira.",x+24,y+244,int(w)-48,40,15,RGB(224,238,225),true);}
  for(auto&place:clubcomp::placeCompetitionXI(comp.starters)){
   auto&p=comp.starters[place.player];float xx=place.x,yy=place.y;image(c,"head",p.id,xx-26,yy,52,58);
   rounded(c,xx-37,yy+51,74,18,4,0xe0123021);image(c,"crest",p.club,xx-34,yy+51,17,18);text(c,p.rating,xx-12,yy+50,44,20,15,RGB(255,255,255),true);
   auto name=p.name;auto last=name.find_last_of(' ');if(last!=std::string::npos)name=name.substr(last+1);rounded(c,xx-place.width/2,yy+71,place.width,18,4,0x8a133820);text(c,name,xx-place.width/2+2,yy+70,int(place.width)-4,20,14,RGB(255,255,255),true);
  }
  text(c,comp.starters.empty()?"":"Seleção por posição · notas reais da carreira",box.x+16,753,int(box.w)-32,26,14,RGB(109,132,152),true);
 }
 #include "competitions_bracket.inc"
 void draw(ID3D11DeviceContext*c){
  auto&r=renderer;if(device!=r.device){clearTextures();device=r.device;}label=0;r.normal(c);r.rectangle(c,40,20,1520,790,0xffedf2f5);
  if(!ready){text(c,"COMPETIÇÕES DA CARREIRA",80,65,1440,65,35);text(c,lineup.status=="error"?lineup.message:"Carregando as competições desta carreira...",80,350,1440,90,25,RGB(116,138,150),true);return;}
  if(data.competitions.empty()){text(c,"Nenhuma competição registrada para este clube",80,350,1440,90,25,RGB(116,138,150),true);return;}
  selected=std::clamp(selected,0,int(data.competitions.size())-1);auto&comp=data.competitions[selected];if(expanded){drawExpanded(c,comp);return;}r.rectangle(c,40,20,1520,80,0xfff8fbfc);image(c,"comp",comp.asset,136,32,60,57);text(c,"‹",68,35,56,53,44,uitheme::accentInk(),true);text(c,"›",1477,35,56,53,44,uitheme::accentInk(),true);text(c,comp.name,214,29,1100,45,31);text(c,comp.status+" · "+data.clubName+" · "+std::to_string(data.date/10000),216,71,1100,25,16,RGB(116,138,150));if(comp.rank>0)text(c,std::to_string(comp.rank)+"º  ·  "+num(comp.points)+" PTS",1298,35,168,47,23,uitheme::accentInk(),true);
  float tabWidth=1504.f/data.competitions.size();for(size_t i=0;i<data.competitions.size();++i){float xx=48+i*tabWidth;r.rectangle(c,xx,102,tabWidth-5,40,i==selected?uitheme::accent():0xffdde6eb);text(c,data.competitions[i].name,xx+8,106,int(tabWidth)-21,32,15,i==selected?uitheme::selectedText():RGB(52,77,90),true);}
  if(comp.format=="cup"&&bracket)cup(c,comp);else table(c,comp);leaders(c,comp);pitch(c,comp);r.normal(c);
 }
} competitions;
