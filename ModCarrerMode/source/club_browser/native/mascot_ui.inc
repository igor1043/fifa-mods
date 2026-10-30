// Dedicated page; shares the native actor lifecycle, not roster selection.
clubmascot::View mascot;
void centreMascot(){clubscene::playerAngle=0;clubscene::playerZoom=1;clubscene::playerPan=0;}
void enterMascot(int club,int career){clubscene::mascotCamera=true;clubscene::rosterCamera=true;clubscene::roomView=false;clubscene::playerHeight=180;centreMascot();mascot.enter(lineup,club,career);}
void openMascot(){hubFocus=3;clubPage=ClubPage::Mascot;model.detailOpen=true;enterMascot(model.club().id,careerClub());}
void mascotControls(HWND window,float w,float h,float dt){
 DWORD pid=0;GetWindowThreadProcessId(GetForegroundWindow(),&pid);if(pid!=GetCurrentProcessId()||GetTickCount64()<enteredAt+250)return;
 auto held=[](int key){return (GetAsyncKeyState(key)&0x8000)!=0;};auto axis=[](SHORT v){return std::abs(int(v))>8000?v/32768.f:0.f;};
 XINPUT_STATE pad{};if(readPad)for(DWORD i=0;i<4;++i)if(readPad(i,&pad)==ERROR_SUCCESS)break;
 clubscene::playerAngle=clubscene::playerAngle.load()+(axis(pad.Gamepad.sThumbRX)+(held(VK_RIGHT)||held('L')?1.f:0.f)-(held(VK_LEFT)||held('J')?1.f:0.f))*dt*2.8f;
 clubscene::playerPan=std::clamp(clubscene::playerPan.load()+(axis(pad.Gamepad.sThumbRY)+(held(VK_UP)?1.f:0.f)-(held(VK_DOWN)?1.f:0.f))*dt*.6f,-.45f,.65f);
 float zoom=(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f+((pad.Gamepad.wButtons&XINPUT_GAMEPAD_RIGHT_SHOULDER)||held('E')||held(VK_ADD)||held(VK_OEM_PLUS)?1.f:0.f)-((pad.Gamepad.wButtons&XINPUT_GAMEPAD_LEFT_SHOULDER)||held('W')||held(VK_SUBTRACT)||held(VK_OEM_MINUS)?1.f:0.f);
 POINT p{};GetCursorPos(&p);ScreenToClient(window,&p);float fit=(std::min)(w/1600,h/900),mx=(p.x-(w-1600*fit)/2)/fit,my=(p.y-(h-900*fit)/2)/fit;
 int wheel=wheelDelta.exchange(0);if(mx<0||mx>1600||my<145||my>805)wheel=0;
 clubscene::playerZoom=std::clamp(clubscene::playerZoom.load()*std::exp(zoom*dt+wheel*.001f),.65f,2.8f);
 static bool wasDown=false,dragging=false;static float x=0,y=0;bool down=held(VK_LBUTTON);
 if(down&&!wasDown){dragging=mx>=0&&mx<1600&&my>=145&&my<805;x=mx;y=my;}
 if(dragging&&down){clubscene::playerAngle=clubscene::playerAngle.load()+(mx-x)*.012f;clubscene::playerPan=std::clamp(clubscene::playerPan.load()+(my-y)*.003f,-.45f,.65f);x=mx;y=my;}
 if(!down)dragging=false;wasDown=down;
}
void drawMascot(ID3D11DeviceContext*c){
 auto&r=renderer;r.normal(c);r.rectangle(c,0,0,1600,138,0x90132330);
 gameImage(r.device,r.clubIcon,art,{"data/ui/imgAssets/crest/light/l"+std::to_string(mascot.club)+".dds","data/ui/imgAssets/crest/dark/l"+std::to_string(mascot.club)+".dds"});containImage(c,r.clubIcon,60,55,58,65);
 r.label(c,0,L"TEMPORADA / OUTRAS LIGAS / VER CLUBES",62,19,1000,25,17,RGB(196,215,225));r.label(c,1,L"MASCOTE DO CLUBE",137,55,1040,47,37,RGB(255,255,255));
 r.label(c,2,model.club().id==mascot.club?wide(model.club().name):L"Clube da carreira",139,101,1110,27,20,RGB(211,226,234));
 if(!mascot.error.empty()||!mascot.ready||(mascot.submitted&&clubscene::readySequence!=mascot.submitted)){
  r.rectangle(c,420,705,760,83,0xc0122937);r.label(c,3,mascot.error.empty()?L"Preparando o mascote...":wide(mascot.error),440,721,720,52,23,RGB(255,255,255),true);
 }
}
