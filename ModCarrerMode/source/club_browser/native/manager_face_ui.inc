// Creation owns a draft only. The background observer attaches it to the
// actual completed native save event; no team asset or DATA file is replaced.
#include "manager_face_model.h"
#include "native_value_font.h"
std::mutex managerFaceCommandMutex;std::vector<std::string> managerFaceCommands;
XINPUT_STATE managerFacePad(){
 if(!readPad){auto module=GetModuleHandleW(L"xinput1_4.dll");if(!module)module=GetModuleHandleW(L"xinput1_3.dll");if(module)readPad=reinterpret_cast<ReadPad>(GetProcAddress(module,"XInputGetState"));}
 // A connected idle/virtual pad in slot zero must not hide the controller
 // actually moving the camera. Keep the active slot while it rests.
 static DWORD active=0;XINPUT_STATE pads[4]{};bool connected[4]{};int best=0;
 if(readPad)for(DWORD i=0;i<4;++i){connected[i]=readPad(i,&pads[i])==ERROR_SUCCESS;if(!connected[i])continue;const auto&p=pads[i].Gamepad;
  int score=(std::abs(int(p.sThumbLX))>8000?std::abs(int(p.sThumbLX)):0)+(std::abs(int(p.sThumbLY))>8000?std::abs(int(p.sThumbLY)):0)+(std::abs(int(p.sThumbRX))>8000?std::abs(int(p.sThumbRX)):0)+(std::abs(int(p.sThumbRY))>8000?std::abs(int(p.sThumbRY)):0)+(p.wButtons?32768:0)+p.bLeftTrigger+p.bRightTrigger;
  if(score>best){best=score;active=i;}}
 if(connected[active])return pads[active];for(DWORD i=0;i<4;++i)if(connected[i]){active=i;return pads[i];}return {};
}
struct ManagerFaceCameraAxes{float turn=0,vertical=0,zoom=0;};
ManagerFaceCameraAxes managerFaceCameraAxes(const XINPUT_GAMEPAD& pad){
 auto axis=[](SHORT value){return std::abs(int(value))>8000?value/32768.f:0.f;};
 return {axis(pad.sThumbRX),axis(pad.sThumbRY),clubs::rosterTriggerZoom(pad.bRightTrigger,pad.bLeftTrigger)};
}
struct ManagerFaceView{
 std::vector<managerface::Choice> choices;int selected=0,confirmed=0,first=0,requested=-1,direction=0;uint64_t nonce=0,armed=0,repeatAt=0,serviceRetry=0,consumed=0,submitted=0,selectionAt=0;
 std::string phase="preferences",message;fs::path game;clublineup::View service;std::future<std::shared_ptr<clubanim::Clip>> clip;clubscene::Assets loading;std::array<int,96> bindings{};std::vector<clubgfx::Texture> photos,badges;bool mouseWasDown=false,dragging=false;float mouseX=0,mouseY=0;
 managerface::ValueRect valueRect;bool valueHighlighted=false;
 std::wstring valueFamily=L"EA HelveticaNeue Med";
 managerface::Filter filter;clubgfx::Texture countryIcon,leagueIcon;
 int pageSize()const{return filter.grouped?5:7;}
 float listTop()const{return filter.grouped?325.f:190.f;}
 std::vector<int> visible()const{return filter.visible(choices);}
 void fitList(){auto rows=visible();first=managerface::scrollFirst(managerface::visiblePosition(rows,selected),first,int(rows.size()),pageSize());}
 void mode(bool grouped){filter.grouped=grouped;filter.follow(choices,selected);filter.focus=grouped?1:3;first=0;fitList();}
 void horizontal(int delta){if(filter.focus==0){mode(delta>0);return;}if(filter.grouped&&(filter.focus==1||filter.focus==2)){select(filter.cycle(choices,filter.focus-1,delta));first=0;fitList();}}
 void vertical(int delta){auto rows=visible();int pos=managerface::visiblePosition(rows,selected);
  if(filter.focus==3){if(delta<0&&pos==0){filter.focus=filter.grouped?2:0;return;}if(delta>0&&pos+1==int(rows.size())){filter.focus=4;return;}if(!rows.empty())select(rows[managerface::step(pos,delta,int(rows.size()))]);}
  else if(filter.focus==4){if(delta<0)filter.focus=3;}
  else if(delta<0)filter.focus=std::max(0,filter.focus-1);
  else filter.focus=filter.focus==0?(filter.grouped?1:3):filter.focus+1;
 }
 void configure(const fs::path& value){game=value;service.workerFlag=L"SERVER16_MANAGER_APPEARANCE_WORKER=1";service.configure(game);
  auto path=game/L"data/ui/fonts/eahelveticaneuemed-mod.ttf";std::ifstream font(path,std::ios::binary|std::ios::ate);
  if(font&&font.tellg()>0&&font.tellg()<=4*1024*1024){std::vector<unsigned char> bytes(size_t(font.tellg()));font.seekg(0);font.read(reinterpret_cast<char*>(bytes.data()),std::streamsize(bytes.size()));auto family=managerface::valueFontFamily(bytes);if(!family.empty()&&AddFontResourceExW(path.c_str(),FR_PRIVATE,nullptr)>0)valueFamily=family;}
 }
 void serviceTick(){if(game.empty()||GetTickCount64()<serviceRetry||service.running())return;serviceRetry=GetTickCount64()+15000;service.startWorker(game);}
 bool catalog(){if(choices.empty()){std::ifstream in(game/L"ModCarrerMode/data/manager_face_selector/catalog.tsv",std::ios::binary);if(!in||!managerface::load(in,choices))return false;}photos.resize(choices.size());badges.resize(choices.size());return true;}
 void begin(){
  std::ifstream file(game/L"ModCarrerMode/runtime/user_manager/draft.tsv");std::string row;bool bound=false;
  while(std::getline(file,row))if(row=="phase=bound"||row=="phase=initializing"||row=="phase=abandoned")bound=true;
  if(!nonce||bound){nonce=GetTickCount64();armed=0;selected=confirmed=first=0;phase="preferences";}
 }
 bool draft(bool active){
  if(!catalog())return false;auto folder=game/L"ModCarrerMode/runtime/user_manager";std::error_code ec;fs::create_directories(folder,ec);if(ec)return false;
  FILETIME created,exit,kernel,user;if(!GetProcessTimes(GetCurrentProcess(),&created,&exit,&kernel,&user))return false;auto born=(uint64_t(created.dwHighDateTime)<<32)|created.dwLowDateTime;
  auto& c=choices[confirmed];auto target=folder/L"draft.tsv",temp=folder/L"draft.new";
  {std::ofstream out(temp,std::ios::binary);out<<"schema=1\npid="<<GetCurrentProcessId()<<"\ncreated="<<born<<"\nnonce="<<nonce<<"\narmed_tick="<<armed<<"\nphase="<<phase<<"\nactive="<<active<<"\nconfirmed="<<(confirmed>0)<<"\ncoach="<<c.coach<<"\nasset="<<c.asset<<"\n";if(!out)return false;}
  return MoveFileExW(temp.c_str(),target.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=FALSE;
 }
 void command(const std::string& value){
  if(value=="row_hide"){valueRect.valid=false;return;}
  if(value=="row_focus"||value=="row_blur"){valueHighlighted=value=="row_focus";return;}
  if(value.rfind("row:",0)==0){valueRect.parse(value);return;}
  if(value=="begin"){begin();draft(false);return;}
  if(value=="open"){
   begin();if(!catalog())return;selected=confirmed>0?confirmed:1;filter.follow(choices,selected);filter.focus=3;first=0;fitList();requested=-1;submitted=consumed=selectionAt=0;phase="preview";draft(true);clubs::managerFacePreview=true;clubscene::playerAngle=0;clubscene::playerZoom=1;clubscene::playerPan=0;return;
  }
  if(value=="confirm"){if(!clubs::managerFacePreview||!catalog())return;confirmed=selected;phase="preferences";draft(false);clubs::managerFacePreview=false;clubscene::intent(false,0);return;}
  if(value=="exit"&&!clubs::managerFacePreview)return;
  if(value=="cancel"||value=="exit"){selected=confirmed;phase="preferences";draft(false);clubs::managerFacePreview=false;clubscene::intent(false,0);return;}
  if(value=="abandon"){confirmed=selected=0;phase="abandoned";draft(false);clubs::managerFacePreview=false;return;}
  if(value=="arm"){begin();phase="initializing";armed=GetTickCount64();draft(false);return;}
  if(!clubs::managerFacePreview)return;
  // FIFA already translates the left stick into native UI navigation.
  // Only the right stick is read by the continuous camera controls.
  if(value=="up")vertical(-1);else if(value=="down")vertical(1);else if(value=="left")horizontal(-1);else if(value=="right")horizontal(1);else if(value=="mode")mode(!filter.grouped);else if(value=="mode_all")mode(false);else if(value=="mode_league")mode(true);
  else if(value=="page_up"||value=="page_down"){auto rows=visible();if(!rows.empty())select(rows[managerface::step(managerface::visiblePosition(rows,selected),value=="page_up"?-pageSize():pageSize(),int(rows.size()))]);}
  else if(value=="center"){clubscene::playerAngle=0;clubscene::playerZoom=1;clubscene::playerPan=0;}
 }
 void select(int index){if(choices.size()<2)return;int next=std::clamp(index,1,int(choices.size())-1);if(next==selected)return;selected=next;selectionAt=GetTickCount64();fitList();requested=-1;submitted=consumed=0;clubscene::intent(false,0);}
 void poll(ID3D11Device* device){
  if(!catalog())return;
  // Never destroy/overwrite a running std::async future on the render thread:
  // its destructor waits, freezing input until the old animation finishes.
  if(clip.valid()){
   if(clip.wait_for(std::chrono::milliseconds(0))!=std::future_status::ready)return;
   auto result=clip.get();if(result&&requested==selected&&loading.sequence==lineup.sequence&&loading.club==choices[selected].asset){loading.animation=std::move(result);clubscene::submit(loading,bindings);submitted=loading.sequence;}
  }
  if(requested!=selected&&selectionAt&&GetTickCount64()-selectionAt<120)return;
  if(requested!=selected){requested=selected;submitted=consumed=0;clubscene::intent(false,0);message.clear();if(choices[selected].asset){lineup.lastCoach=choices[selected].coach;lineup.career=0;lineup.request(choices[selected].asset,"manager_face");}}
  if(!choices[selected].asset)return;lineup.poll(device);
  if(lineup.status=="error"){message=lineup.message;return;}
  if(lineup.status=="ready"&&lineup.kind=="manager_face"&&lineup.lastValues["coach_id"]==choices[selected].coach&&consumed!=lineup.sequence){
   consumed=lineup.sequence;auto& v=lineup.lastValues;message=v["message"];if(v["actor"]!="1")return;
   try{
    clubscene::Assets a;a.creation=true;a.career=0;a.club=choices[selected].asset;a.sequence=lineup.sequence;a.single=true;a.player=100000000+a.club;a.hash=v["hash"];a.pages=std::stoi(v["pages"]);if(!clubscene::validAssets(a))return;
    auto parts=clubroster::split(v["bindings"],',');if(parts.size()!=96)return;for(int i=0;i<96;++i){bindings[i]=std::stoi(parts[i]);if(bindings[i]<0||bindings[i]>=a.pages)return;}
    clubscene::playerHeight=float(std::clamp(std::stoi(v["height"]),130,230));loading=a;
    if(v["animated"]=="1"){auto path=lineup.gameRoot/L"data/sceneassets/server16_club_xi"/std::to_wstring(GetCurrentProcessId())/a.hash/L"animation.bin";clip=std::async(std::launch::async,[path,id=a.player](){return clubanim::load(path,id);});}
    else{clubscene::submit(a,bindings);submitted=a.sequence;}
   }catch(...){message="Modelo 3D indisponível.";}
  }
 }
 void controls(HWND window,float width,float height,float dt){
  if(GetForegroundWindow()!=window)return;POINT point{};GetCursorPos(&point);ScreenToClient(window,&point);float scale=(std::min)(width/1600,height/900),x=(point.x-(width-1600*scale)/2)/scale,y=(point.y-(height-900*scale)/2)/scale;
  bool down=(GetAsyncKeyState(VK_LBUTTON)&0x8000)!=0;
  if(down&&!mouseWasDown){
   if(x>=62&&x<492&&y>=143&&y<178)mode(x>=277);
   else if(filter.grouped&&x>=62&&x<492&&y>=194&&y<310){filter.focus=y<252?1:2;horizontal(x<277?-1:1);}
   else if(x>=65&&x<491&&y>=listTop()&&y<listTop()+pageSize()*74){auto rows=visible();int at=first+int((y-listTop())/74);if(at<int(rows.size())){filter.focus=3;select(rows[at]);}}
   else if(x>530&&y>130&&y<790){dragging=true;mouseX=x;mouseY=y;}}
  if(dragging&&down){clubscene::playerAngle=clubscene::playerAngle.load()+float(x-mouseX)*.012f;clubscene::playerPan=std::clamp(clubscene::playerPan.load()+float(y-mouseY)*.003f,-.45f,.65f);mouseX=x;mouseY=y;}if(!down)dragging=false;mouseWasDown=down;
  int wheel=wheelDelta.exchange(0);if(wheel&&x<520){int delta=wheel>0?-1:1;if(filter.grouped&&y>=194&&y<310){filter.focus=y<252?1:2;horizontal(delta);}else{auto rows=visible();if(!rows.empty())select(rows[managerface::step(managerface::visiblePosition(rows,selected),delta,int(rows.size()))]);filter.focus=3;}wheel=0;}
  auto pad=managerFacePad();auto axes=managerFaceCameraAxes(pad.Gamepad);
  const auto held=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};
  float turn=axes.turn+held('L')-held('J');
  float vertical=axes.vertical+held('I')-held('K');
  float zoom=axes.zoom+held('E')+held(VK_ADD)+held(VK_OEM_PLUS)-held('W')-held(VK_SUBTRACT)-held(VK_OEM_MINUS);
  managerface::Camera camera{clubscene::playerAngle.load(),clubscene::playerPan.load(),clubscene::playerZoom.load()};camera.update(turn,vertical,zoom,float(wheel),dt);
  clubscene::playerAngle=camera.angle;clubscene::playerPan=camera.pan;clubscene::playerZoom=camera.zoom;
 }
 std::wstring preferenceName(){return catalog()?wide(choices[confirmed].name):L"Padrão do FIFA";}
 void drawPreference(ID3D11DeviceContext* c){
  if(!valueRect.valid||clubs::managerFacePreview)return;
  float x=valueRect.x*1.25f,y=valueRect.y*1.25f;int w=int(valueRect.w*1.25f),h=int(valueRect.h*1.25f);
  // The original preference row uses a 20px font on the 1280x720 UI stage.
  int size=25;auto name=preferenceName();
  renderer.label(c,0,name,x,y,w,h,size,valueHighlighted?RGB(255,255,255):RGB(48,72,86),false,valueFamily);
 }
 void draw(ID3D11DeviceContext* c){
  auto&r=renderer;int label=0;auto ink=RGB(48,72,86),muted=RGB(105,129,143);r.rectangle(c,40,32,480,790,0xfff3f6f7);r.rectangle(c,40,32,480,4,uitheme::accent());
  r.label(c,label++,L"FACE DO TREINADOR",62,55,436,43,29,ink);r.label(c,label++,L"Escolha a aparência do seu manager",62,108,436,30,18,muted);
  if(!catalog()){r.label(c,label++,L"Catálogo de modelos indisponível.",65,208,420,72,22,ink);return;}
  auto rows=visible();
  for(int i=0;i<2;++i){bool on=filter.grouped==(i==1);r.rectangle(c,62.f+i*215,143,210,35,on?uitheme::accent():0xffe5edf1);r.label(c,label++,i?L"Por liga":L"Todos",67.f+i*215,148,200,25,18,on?uitheme::selectedText():ink,true);}
  if(filter.focus==0){r.rectangle(c,62,179,430,2,uitheme::focus());}
  if(filter.grouped){const auto& cur=choices[selected];
   for(int i=0;i<2;++i){float y=194.f+i*58;bool focused=filter.focus==i+1;r.rectangle(c,62,y,430,54,focused?uitheme::accent():0xffe5edf1);auto color=focused?uitheme::selectedText():ink;
    r.label(c,label++,i?L"LIGA":L"PAÍS / REGIÃO",98,y+2,346,18,12,color);r.label(c,label++,L"‹",66,y+13,23,35,28,color,true);r.label(c,label++,L"›",462,y+13,23,35,28,color,true);
    r.label(c,label++,wide(i?cur.leagueName:cur.countryName),142,y+23,306,28,i?17:21,color);
    auto&icon=i?leagueIcon:countryIcon;if(i&&cur.league&&cur.league!=1000000)clubgfx::gameImage(r.device,icon,art,{"data/ui/imgAssets/league/light/l"+std::to_string(cur.league)+".dds"});
    else if(!i&&cur.nation)clubgfx::gameImage(r.device,icon,art,{"data/ui/imgAssets/flags512x512/f_"+std::to_string(cur.nation)+".dds"});else icon.clear();containImage(c,icon,98,y+21,34,29);
   }
  }
  float top=listTop();
  for(int slot=0;slot<pageSize()&&first+slot<int(rows.size());++slot){int index=rows[first+slot];auto& choice=choices[index];float y=top+slot*74.f;bool active=index==selected;r.rectangle(c,62,y,430,68,active?uitheme::accent():0xffe5edf1);
   if(active&&filter.focus==3)r.rectangle(c,62,y,3,68,uitheme::focus());
   if(choice.asset){clubgfx::image(r.device,photos[index],(game/L"ModCarrerMode/data/manager_market"/wide(choice.image)).wstring());containImage(c,photos[index],68,y+3,63,63);}
   if(choice.asset){
    r.label(c,label++,wide(choice.name),143,y+5,choice.club?290:332,31,21,active?uitheme::selectedText():ink);
    r.label(c,label++,wide(choice.club>0?choice.clubName:"Sem clube"),143,y+36,choice.club?290:332,24,15,active?uitheme::selectedText():muted);
    if(choice.club>0){auto id=std::to_string(choice.club);clubgfx::gameImage(r.device,badges[index],art,{"data/ui/imgAssets/crest/light/l"+id+".dds","data/ui/imgAssets/crest/dark/l"+id+".dds"});containImage(c,badges[index],445,y+16,36,39);}
   }else r.label(c,label++,wide(choice.name),78,y+15,400,38,22,active?uitheme::selectedText():ink);
  }
  float track=pageSize()*74.f-6;if(int(rows.size())>pageSize()){r.rectangle(c,501,top,5,track,0xffdce5e9);float h=track*pageSize()/rows.size(),y=top+(track-h)*first/(rows.size()-pageSize());r.rectangle(c,501,y,5,h,uitheme::accent());}
  r.label(c,label++,std::to_wstring(managerface::visiblePosition(rows,selected)+1)+L" / "+std::to_wstring(rows.size())+L" técnicos",62,718,430,25,16,muted,true);
  r.rectangle(c,62,754,430,53,uitheme::accent());if(filter.focus==4)r.rectangle(c,62,754,430,3,uitheme::focus());r.label(c,label++,L"Confirmar",78,766,398,29,23,uitheme::selectedText(),true);
  const auto& current=choices[selected];r.rectangle(c,1125,38,430,current.club?85.f:60.f,0xb0172934);
  if(current.club>0){auto id=std::to_string(current.club);clubgfx::gameImage(r.device,badges[selected],art,{"data/ui/imgAssets/crest/light/l"+id+".dds","data/ui/imgAssets/crest/dark/l"+id+".dds"});containImage(c,badges[selected],1140,52,48,56);r.label(c,label++,wide(current.name),1200,45,340,39,26,RGB(255,255,255));r.label(c,label++,wide(current.clubName),1200,87,340,26,17,RGB(215,228,236));}
  else r.label(c,label++,wide(current.name),1140,48,400,39,27,RGB(255,255,255),true);
  if(!choices[selected].asset){r.rectangle(c,650,610,850,116,0xd0172934);r.label(c,label++,L"Mantém a aparência definida nas preferências do FIFA.",675,630,800,72,25,RGB(255,255,255),true);}
  else if(!submitted||clubscene::readySequence!=submitted){r.rectangle(c,825,690,690,85,0xd0172934);r.label(c,label++,wide(message.empty()?"Preparando o modelo 3D...":message),845,705,650,55,23,RGB(255,255,255),true);}
 }
}managerFace;
void drainManagerFaceCommands(){if(managerFace.game.empty())return;std::vector<std::string> pending;{std::lock_guard<std::mutex>guard(managerFaceCommandMutex);pending.swap(managerFaceCommands);}for(auto& c:pending)managerFace.command(c);if(clubs::managerFacePreview){char page[128]{};if(!readPage(page)||!clubs::isManagerPreferences(page))managerFace.command("exit");}managerFace.serviceTick();}
