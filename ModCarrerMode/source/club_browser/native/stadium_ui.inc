// Included in the browser UI namespace. The engine consumes an immutable pose.
std::wstring stadiumTitle(int club){
 static fs::path catalogRoot;static bool catalogReady=false;static std::map<int,std::wstring> titles;
 static uint64_t nextCheck=0;static int lastClub=0;
 if(!catalogReady||catalogRoot!=art.game){
  titles.clear();std::ifstream input(art.game/L"ModCarrerMode/data/catalogs/club_stadium_fallback.tsv");
  for(const auto& entry:clubstadium::names(input))titles[entry.first]=wide(entry.second);
  catalogRoot=art.game;catalogReady=true;nextCheck=0;
 }
 auto now=GetTickCount64();if(now>=nextCheck||club!=lastClub){
  nextCheck=now+250;lastClub=club;
  auto host=GetModuleHandleW(L"frontend_stadium_native_v11.dll");if(!host)host=GetModuleHandleW(L"frontend_stadium.dll");
  auto name=reinterpret_cast<BOOL(WINAPI*)(DWORD,wchar_t*,DWORD)>(host?GetProcAddress(host,"Fifa16FrontendStadiumName"):nullptr);
  wchar_t text[256]{};if(name&&name(DWORD(club),text,256)&&text[0])titles[club]=text;
 }
 auto found=titles.find(club);return found==titles.end()?L"Estádio do clube":found->second;
}
clubstadium::View stadium;
int stadiumPhase=0;uint64_t stadiumPollAt=0,stadiumKeyboardAt=0,stadiumTickAt=0;bool stadiumF1=false,stadiumF2=false,stadiumMouse=false;POINT stadiumCursor{};
bool stadiumKey(int code){return (GetAsyncKeyState(code)&0x8000)!=0;}
bool stadiumMovementKeys(){return stadiumKey('W')||stadiumKey('A')||stadiumKey('S')||stadiumKey('D')||stadiumKey(VK_SPACE)||stadiumKey(VK_CONTROL);}
XINPUT_GAMEPAD stadiumPad(){
 XINPUT_STATE state{};
 if(readPad)for(DWORD index=0;index<4;++index)if(readPad(index,&state)==ERROR_SUCCESS)return state.Gamepad;
 return {};
}
void openStadium(){
 hubFocus=4;clubPage=ClubPage::Stadium;model.detailOpen=true;
 clubscene::intent(false,0);clubscene::rosterCamera=false;clubscene::mascotCamera=false;clubanim::activate({});
 stadium.enter(model.club().id);stadiumPhase=0;stadiumPollAt=stadiumKeyboardAt=stadiumTickAt=0;stadiumMouse=false;stadiumF1=stadiumKey(VK_F1);stadiumF2=stadiumKey(VK_F2);
 const auto config=art.game/L"ModCarrerMode/config/panorama_drone.ini";
 stadium.duration=float(std::clamp(int(GetPrivateProfileIntW(L"panorama_drone",L"duration_seconds",52,config.c_str())),20,120));
 stadium.gap=float(std::clamp(int(GetPrivateProfileIntW(L"panorama_drone",L"original_interval_seconds",24,config.c_str())),10,180));
 stadium.transition=float(std::clamp(int(GetPrivateProfileIntW(L"panorama_drone",L"transition_seconds",3,config.c_str())),1,8));
 stadium.heightLimit=float(std::clamp(int(GetPrivateProfileIntW(L"panorama_drone",L"height_limit_cm",11000,config.c_str())),1000,14000));
 stadium.scale=std::clamp(int(GetPrivateProfileIntW(L"panorama_drone",L"route_scale_percent",100,config.c_str())),60,100)*.01f;
 stadium.mask=0;for(unsigned i=0;i<panorama::motionCount;++i){wchar_t key[96]{};MultiByteToWideChar(CP_UTF8,0,panorama::motions[i].id,-1,key,96);if(GetPrivateProfileIntW(L"shots",key,1,config.c_str()))stadium.mask|=uint64_t{1}<<i;}
 if(!stadium.mask)stadium.mask=uint64_t{1}<<10;
 stadium.restartPanorama();
 clubscene::closeStadium();clubscene::stadiumClub=stadium.club;log("ENTER_CLUB_STADIUM");
}
void toggleStadium(){stadium.toggle();stadiumMouse=false;}
void toggleStadiumFree(){stadium.toggleFree();stadiumMouse=false;}
void toggleStadiumPad(bool freeCamera){
 // FIFA can map keyboard movement to the same FE actions as X and Y.
 const WORD button=freeCamera?XINPUT_GAMEPAD_X:XINPUT_GAMEPAD_Y;
 const bool pressed=(stadiumPad().wButtons&button)!=0;
 if(!clubstadium::acceptPadToggle(stadiumMovementKeys(),pressed,GetTickCount64(),stadiumKeyboardAt))return;
 if(freeCamera)toggleStadiumFree();else toggleStadium();
}
void stadiumControls(HWND window,float dt){
 const auto now=GetTickCount64();if(now>=stadiumPollAt){
  stadiumPollAt=now+200;DWORD team=0;int phase=0;
  auto host=GetModuleHandleW(L"frontend_stadium_native_v11.dll");if(!host)host=GetModuleHandleW(L"frontend_stadium.dll");
  auto status=reinterpret_cast<BOOL(WINAPI*)(DWORD*,int*)>(host?GetProcAddress(host,"Fifa16FrontendStadiumView"):nullptr);
  if(status&&status(&team,&phase)){
   stadiumPhase=team==DWORD(stadium.club)?phase:0;bool loaded=stadiumPhase==3;
   if(stadiumPhase==4)stadiumPhase=-1;
   if(loaded&&!stadium.ready){
    auto name=stadiumTitle(stadium.club);uint32_t hash=2166136261u;for(wchar_t letter:name){hash^=uint16_t(letter);hash*=16777619u;}
    wchar_t section[32]{};swprintf_s(section,L"stadium_%08X",hash);const auto config=art.game/L"ModCarrerMode/config/panorama_drone.ini";
    stadium.heightLimit=float(std::clamp(int(GetPrivateProfileIntW(section,L"height_limit_cm",int(stadium.heightLimit),config.c_str())),1000,14000));
    stadium.scale=std::clamp(int(GetPrivateProfileIntW(section,L"route_scale_percent",int(std::round(stadium.scale*100)),config.c_str())),60,100)*.01f;
    stadium.restartPanorama();stadiumTickAt=now;stadiumMouse=false;
   }
   stadium.ready=loaded;
  }else if(!status){stadium.ready=false;stadiumPhase=-1;}
 }
 DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);bool focused=pid==GetCurrentProcessId();
 if(focused&&stadiumMovementKeys())stadiumKeyboardAt=now;
 const bool f1=stadiumKey(VK_F1),f2=stadiumKey(VK_F2);
 if(focused&&f1&&!stadiumF1)toggleStadium();stadiumF1=f1;
 if(focused&&f2&&!stadiumF2)toggleStadiumFree();stadiumF2=f2;
 clubstadium::Input input;
 if(focused&&stadium.manual()){
  auto key=stadiumKey;
  input.forward=float(key('W'))-float(key('S'));input.side=float(key('D'))-float(key('A'));input.sprint=key(VK_SHIFT);
  const auto pad=stadiumPad();
  auto axis=[](SHORT v){float a=v/32768.f;return std::abs(a)>.22f?std::copysign((std::abs(a)-.22f)/.78f,a):0.f;};
  input.forward+=axis(pad.sThumbLY);input.side+=axis(pad.sThumbLX);
  input.yaw=(axis(pad.sThumbRX)*1.8f+float(key(VK_RIGHT))-float(key(VK_LEFT)))*dt;input.pitch=(axis(pad.sThumbRY)*1.5f+float(key(VK_UP))-float(key(VK_DOWN)))*dt;
  input.sprint=input.sprint||pad.bRightTrigger>128;
  if(stadium.flying){
   input.vertical=float(key(VK_SPACE))-float(key(VK_CONTROL));
   input.vertical+=float((pad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER)!=0)-float((pad.wButtons&XINPUT_GAMEPAD_LEFT_SHOULDER)!=0);
  }
  POINT cursor{};GetCursorPos(&cursor);bool mouse=key(VK_RBUTTON)&&GetForegroundWindow()==window;
  if(mouse&&stadiumMouse){input.yaw+=std::clamp(float(cursor.x-stadiumCursor.x),-150.f,150.f)*.003f;input.pitch-=std::clamp(float(cursor.y-stadiumCursor.y),-150.f,150.f)*.003f;}
  stadiumCursor=cursor;stadiumMouse=mouse;
 }else stadiumMouse=false;
 const float tourDt=stadiumTickAt&&now>=stadiumTickAt?float(now-stadiumTickAt)*.001f:0.f;stadiumTickAt=now;
 stadium.tick(tourDt,input,focused);
 clubscene::stadiumOpacity=stadium.opacity();
 if(stadium.ownsCamera())std::atomic_store(&clubscene::stadiumPose,std::make_shared<const panorama::Pose>(stadium.pose()));
 else std::atomic_store(&clubscene::stadiumPose,std::shared_ptr<const panorama::Pose>{});
}
void drawStadium(ID3D11DeviceContext*c){
 int label=0;auto&r=renderer;
 const wchar_t* mode=stadium.flying?L"Câmera livre":stadium.walking?L"Primeira pessoa":L"Panorâmica";
 rosterHeader(c,label,stadiumTitle(stadium.club),L"Visualizar estádio · "+wide(model.club().name)+L" · "+mode,false);
 if(!stadium.ready){r.rectangle(c,430,365,740,150,0xfff1f4f5);r.rectangle(c,430,365,740,4,uitheme::accent());r.label(c,label++,stadiumPhase<0?L"Não foi possível carregar este estádio":L"Carregando o estádio do clube...",455,390,690,45,28,RGB(45,67,81),true);r.label(c,label++,L"Você pode voltar a qualquer momento.",455,449,690,35,20,RGB(105,129,143),true);}

}
