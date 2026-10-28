#include <cassert>
#include <iostream>
#include <d3d11sdklayers.h>
#include "render.cpp"

int wmain(int argc,wchar_t** argv){
 _set_error_mode(_OUT_TO_STDERR);
 if(argc!=4)return 2;
 root=argv[1];logPath=std::filesystem::path(argv[3])/L"native_test.log";art.initialize(argv[2]);CoInitializeEx(nullptr,COINIT_MULTITHREADED);
 clubs::RoomRosterMode roomMode;assert(!roomMode.open("game/screens/fluxHub/FluxHub",1043));assert(!roomMode.open("game/screens/career/server16/DressingRoom",0));assert(roomMode.open("game/screens/career/server16/DressingRoom",1043));assert(roomMode.visible("game/screens/career/server16/DressingRoom",1043));assert(!roomMode.visible("game/screens/career/server16/DressingRoom",1629));assert(!roomMode.visible("game/screens/career/server16/ClubBrowser",1043));roomMode.close();assert(!roomMode.visible("game/screens/career/server16/DressingRoom",1043));
 auto indoor=clubs::rosterOrigin(true),outdoor=clubs::rosterOrigin(false);assert(indoor.x==100000&&indoor.y==1000&&indoor.z==530);assert(outdoor.x==0&&outdoor.y==0&&outdoor.z==0);
 // Indoor fill is private, finite and packed in FIFA's planar SH format.
 // Front/back and opposing normals remain lit, with soft directional shape.
 auto sh=clubs::rosterIndoorLight(.74f);assert(sh[27]==0);
 for(int channel=0;channel<3;++channel){
  const int at=channel*9;const float ambient=sh[at]*.2820947918f;
  const float directional=std::hypot(sh[at+1],sh[at+2])*.4886025119f;
  assert(ambient-directional>.55f&&ambient+directional<.9f);
  for(int term=3;term<9;++term)assert(sh[at+term]==0);
 }
 assert(clubs::rosterMinimumZoom(true)==.95f&&clubs::rosterMinimumZoom(false)==.65f);
 auto roomLight=clubs::rosterIndoorLight(clubs::rosterIndoorLightDefault);
 for(int channel=0;channel<3;++channel){
  int at=channel*9;float dc=roomLight[at]*.2820947918f;
  float contrast=std::hypot(roomLight[at+1],roomLight[at+2])*.4886025119f;
  assert(dc-contrast>1.7f&&dc+contrast<2.8f);
 }
 assert(clubs::validRosterIndoorLight(1.6f)&&clubs::validRosterIndoorLight(3.f));
 assert(!clubs::validRosterIndoorLight(0.f)&&!clubs::validRosterIndoorLight(3.1f)&&!clubs::validRosterIndoorLight(NAN));
 {
  auto previousGame=clubscene::game;auto previousLight=clubscene::indoorAmbient.load();
  clubscene::game=std::filesystem::path(argv[3])/L"indoor-light-fixture";
  auto settings=clubscene::game/L"ModCarrerMode/data/club_browser/indoor_player_light.txt";
  std::filesystem::create_directories(settings.parent_path());
  {std::ofstream f(settings);f<<"1.85\n";}clubscene::refreshIndoorLight();assert(clubscene::indoorAmbient==1.85f);
  for(auto invalid:{"", "nan", "-1", "99", "incomplete"}){
   {std::ofstream f(settings);f<<invalid;}clubscene::refreshIndoorLight();assert(clubscene::indoorAmbient==1.85f);
  }
  clubscene::game=previousGame;clubscene::indoorAmbient=previousLight;
 }
 auto reserved=reinterpret_cast<uintptr_t>(VirtualAlloc(nullptr,0x3518000,MEM_RESERVE,PAGE_NOACCESS));assert(reserved);assert(VirtualAlloc(reinterpret_cast<void*>(reserved+0x3517000),4096,MEM_COMMIT,PAGE_READWRITE));alignas(16) unsigned char fakeScene[512]{};*reinterpret_cast<uintptr_t*>(reserved+0x3517c10)=reinterpret_cast<uintptr_t>(fakeScene);*reinterpret_cast<unsigned*>(fakeScene+0x3c)=1;*reinterpret_cast<float*>(fakeScene+0x88)=1.78f;*reinterpret_cast<float*>(fakeScene+0x8c)=1;
 auto oldBase=clubscene::base;clubscene::base=reserved;clubscene::roomView=true;clubscene::rosterCamera=true;clubscene::playerZoom=1;clubscene::playerAngle=0;clubscene::playerHeight=180;clubscene::playerPan=0;clubscene::camera.apply();assert(std::abs(*reinterpret_cast<float*>(fakeScene+0x40+48)-99886)<1);assert(*reinterpret_cast<float*>(fakeScene+0x40+52)>1000);assert(*reinterpret_cast<float*>(fakeScene+0x40+56)>530);clubscene::playerAngle=1.57f;clubscene::camera.apply();assert(*reinterpret_cast<float*>(fakeScene+0x40+48)>100200);clubscene::camera.restore();clubscene::base=oldBase;clubscene::roomView=false;clubscene::rosterCamera=false;clubscene::playerAngle=0;VirtualFree(reinterpret_cast<void*>(reserved),0,MEM_RELEASE);std::cout<<"PASS room roster: scoped career entry, isolated indoor actor placement and orbit camera, no navigation departure\n";
 assert(loadCatalog());assert(model.rows.size()==1647);assert(model.choices(0).size()==49);assert(model.choose(1629));assert(model.club().name=="Grêmio");assert(model.choices(2).size()>=18);
 auto original=model.selected;model.step(2,1);assert(model.selected!=original);model.step(2,-1);assert(model.selected==original);
 for(int kind=0;kind<3;++kind){auto n=model.choices(kind).size();auto before=model.selected;for(size_t i=0;i<n;++i)model.step(kind,1);if(kind==2)assert(model.selected==before);}
 assert(model.choose(1629));model.zoomBy(10);assert(model.targetZoom==2.2f);model.zoomBy(-10);assert(model.targetZoom==.85f);model.zoom=model.targetZoom=1.3f;model.recenter(false);
 auto before=model.selected;assert(model.activate());assert(!model.activate());assert(model.closeDetail());assert(!model.closeDetail());assert(model.selected==before);
 // Default view fits; extra trigger magnification intentionally crops the
 // sphere against the screen, never against a small off-screen UI texture.
 float eye=clubs::GlobeView::camera/1.3f;float radius=clubs::GlobeView::focal/std::sqrt(eye*eye-1)*clubs::GlobeView::h/2;assert(radius<clubs::GlobeView::h/2-10);
 auto projected=clubs::project(0,0,0,0,1.3f);assert(projected.visible);assert(std::abs(projected.x-1035)<.01f);assert(std::abs(projected.y-424)<.01f);assert(!clubs::project(0,180,0,0,1.3f).visible);assert(!clubs::project(0,80,0,0,1.3f).visible);
 std::istringstream malformed("broken");auto count=model.rows.size();assert(!model.load(malformed)&&model.rows.size()==count);
 assert(clubs::isPage("game/screens/career/server16/ClubBrowser"));assert(clubs::isPage("game/screens/career/server16/DressingRoomPlayers"));assert(!clubs::isPage("game/screens/career/server16/DressingRoom"));assert(!clubs::isRoomPlayersPage("game/screens/career/server16/ClubBrowser"));assert(!clubs::isPage("game/screens/fluxHub/FluxHub"));
 auto a=art.asset("data/ui/imgAssets/crest/light/l1629.dds");assert(a.size()>128&&!memcmp(a.data(),"DDS ",4));
 auto flag=clubassets::texture(art.asset("data/ui/artassets/countryflags/f_54.big"));assert(flag.size()>128&&!memcmp(flag.data(),"DDS ",4));
 unsigned packed=0;for(const auto& e:art.index){if(std::filesystem::exists(art.game/e.first))continue;auto data=clubassets::texture(art.asset(e.first));if(data.size()>128&&!memcmp(data.data(),"DDS ",4)){++packed;if(packed==8)break;}}assert(packed==8);
 assert(art.asset("../FIFA16.exe").empty());assert(clubassets::unpack(clubassets::Bytes{'c','h','u','n','k','z','i','p'}).size()==8);
 ID3D11Device* device=nullptr;ID3D11DeviceContext* context=nullptr;auto hr=D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,&device,nullptr,&context);assert(SUCCEEDED(hr));assert(renderer.init(device,root.wstring()));
 D3D11_TEXTURE2D_DESC earthDesc{},atlasDesc{};renderer.earth.texture->GetDesc(&earthDesc);renderer.atlas.texture->GetDesc(&atlasDesc);
 assert(earthDesc.Width==8192&&earthDesc.Height==4096&&earthDesc.MipLevels==14&&earthDesc.Format==DXGI_FORMAT_BC1_UNORM);
 assert(atlasDesc.Width==8192&&atlasDesc.Height==4096&&atlasDesc.Format==DXGI_FORMAT_R8G8_UNORM);
 // Globe channels stay independent: exact country ID and linear distance.
 D3D11_TEXTURE2D_DESC probeDesc{};probeDesc.Width=probeDesc.Height=probeDesc.MipLevels=probeDesc.ArraySize=probeDesc.SampleDesc.Count=1;probeDesc.Format=DXGI_FORMAT_R8G8_UNORM;probeDesc.Usage=D3D11_USAGE_STAGING;probeDesc.CPUAccessFlags=D3D11_CPU_ACCESS_READ;
 ID3D11Texture2D* probe=nullptr;assert(SUCCEEDED(device->CreateTexture2D(&probeDesc,nullptr,&probe)));
 for(auto sample:std::array<std::array<float,3>,3>{{{{-15.8f,-47.9f,30}},{{48.8f,2.35f,44}},{{40.f,-100.f,5}}}}){
  UINT x=UINT((sample[1]+180)/360*8192),y=UINT((90-sample[0])/180*4096);D3D11_BOX box{x,y,0,x+1,y+1,1};context->CopySubresourceRegion(probe,0,0,0,0,renderer.atlas.texture,0,&box);D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(context->Map(probe,0,D3D11_MAP_READ,0,&mapped)));assert(((unsigned char*)mapped.pData)[0]==unsigned(sample[2]));context->Unmap(probe,0);
 }clubgfx::release(probe);
 D3D11_TEXTURE2D_DESC d{};d.Width=1600;d.Height=900;d.MipLevels=d.ArraySize=d.SampleDesc.Count=1;d.Format=DXGI_FORMAT_B8G8R8A8_UNORM;d.Usage=D3D11_USAGE_DEFAULT;d.BindFlags=D3D11_BIND_RENDER_TARGET;
 ID3D11Texture2D* output=nullptr;ID3D11RenderTargetView* target=nullptr;assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&output)));assert(SUCCEEDED(device->CreateRenderTargetView(output,nullptr,&target)));
 context->OMSetRenderTargets(1,&target,nullptr);const float color[]={.08f,.15f,.20f,1};context->ClearRenderTargetView(target,color);D3D11_VIEWPORT sentinel{11,22,800,450,.1f,.9f};context->RSSetViewports(1,&sentinel);
 clubgfx::Texture background;auto bg=std::filesystem::path(argv[3])/L"stadium_test.png";if(std::filesystem::exists(bg)){renderer.begin(context,target,1600,900);assert(clubgfx::image(device,background,bg.wstring()));renderer.normal(context);renderer.quad(context,0,0,1600,900,background.view);context->RSSetViewports(1,&sentinel);}context->PSSetShader(nullptr,nullptr,0);
 {
  clubgfx::SavedState state;state.save(context);renderer.begin(context,target,1600,900);drawContent(context);state.restore(context);
 }
 assert(renderer.countryIcon.view&&renderer.leagueIcon.view&&renderer.clubIcon.view);
 D3D11_VIEWPORT restored{};UINT size=1;context->RSGetViewports(&size,&restored);assert(!memcmp(&sentinel,&restored,sizeof sentinel));
 ID3D11RenderTargetView* restoredTarget=nullptr;context->OMGetRenderTargets(1,&restoredTarget,nullptr);assert(restoredTarget==target);clubgfx::release(restoredTarget);
 ID3D11PixelShader* restoredShader=nullptr;context->PSGetShader(&restoredShader,nullptr,nullptr);assert(restoredShader==nullptr);
 // Repeated opening/selection uses only the three current game-art textures.
 for(int id:{1043,1629,1,9,1629}){assert(model.choose(id));context->ClearRenderTargetView(target,color);clubgfx::SavedState state;state.save(context);renderer.begin(context,target,1600,900);if(background.view){renderer.normal(context);renderer.quad(context,0,0,1600,900,background.view);}drawContent(context);state.restore(context);}
 d.Usage=D3D11_USAGE_STAGING;d.BindFlags=0;d.CPUAccessFlags=D3D11_CPU_ACCESS_READ;ID3D11Texture2D* staging=nullptr;assert(SUCCEEDED(device->CreateTexture2D(&d,nullptr,&staging)));context->CopyResource(staging,output);
 auto capture=[&](const wchar_t* name){context->CopyResource(staging,output);D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(context->Map(staging,0,D3D11_MAP_READ,0,&mapped)));std::ofstream out(std::filesystem::path(argv[3])/name,std::ios::binary);for(unsigned y=0;y<900;++y)out.write((char*)mapped.pData+y*mapped.RowPitch,1600*4);out.close();context->Unmap(staging,0);};capture(L"native_preview.bgra");
 auto frame=[&](){context->ClearRenderTargetView(target,color);renderer.begin(context,target,1600,900);if(background.view){renderer.normal(context);renderer.quad(context,0,0,1600,900,background.view);}};
 auto pixels=[&](){context->CopyResource(staging,output);D3D11_MAPPED_SUBRESOURCE mapped{};assert(SUCCEEDED(context->Map(staging,0,D3D11_MAP_READ,0,&mapped)));std::vector<unsigned char> bytes(1600*900*4);for(unsigned y=0;y<900;++y)memcpy(bytes.data()+size_t(y)*1600*4,(char*)mapped.pData+y*mapped.RowPitch,1600*4);context->Unmap(staging,0);return bytes;};
 // A stationary selector must draw exactly the same dots at different times.
 std::vector<unsigned char> fixedPoints;
 {clubgfx::SavedState state;state.save(context);frame();drawContent(context);fixedPoints=pixels();state.restore(context);}
 Sleep(180);
 {clubgfx::SavedState state;state.save(context);frame();drawContent(context);assert(pixels()==fixedPoints);state.restore(context);}
 {clubgfx::SavedState state;state.save(context);frame();model.zoom=2.2f;drawContent(context);state.restore(context);}capture(L"native_preview_max_zoom.bgra");
 {clubgfx::SavedState state;state.save(context);frame();model.zoom=1.3f;model.yaw=-3.14159265f;model.pitch=0;drawContent(context);state.restore(context);}capture(L"native_preview_dateline.bgra");
 assert(model.choose(1));model.recenter(false);
 {clubgfx::SavedState state;state.save(context);frame();model.zoom=2.2f;drawContent(context);state.restore(context);}capture(L"native_preview_europe.bgra");
 assert(model.choose(1043));assert(model.activate());lineup.sequence=123;lineup.status="ready";clubscene::readySequence=123;
 {clubgfx::SavedState state;state.save(context);frame();drawLineup(context);state.restore(context);}capture(L"lineup_preview.bgra");
 assert(model.closeDetail());assert(model.club().id==1043);
 // Draw each coach tab through the same UI state guard used in the game.
 auto coachFile=std::filesystem::path(argv[3]).parent_path()/L"coach-1043.tsv";
 if(std::filesystem::exists(coachFile)){
  std::ifstream input(coachFile,std::ios::binary);assert(clubcoach::parse(input,1043,coach.profile));coach.ready=true;coach.club=1043;assert(model.choose(1043));lineup.status="ready";lineup.kind="test";clubPage=ClubPage::Coach;
  for(int tab=0;tab<3;++tab){coach.tab=tab;clubgfx::UiPass saved(context,renderer.uiPipeline);frame();drawCoach(context);saved.restore();capture((L"coach_tab_"+std::to_wstring(tab)+L".bgra").c_str());}
  assert(coachFlag.view&&coachLeague.view);coach.setTab(1);for(int i=0;i<50;++i)coach.navigate(1);assert(coach.scroll>=0);coach.setTab(0);assert(coach.scroll==0);goBack();assert(clubPage==ClubPage::Choice);goBack();assert(clubPage==ClubPage::Map);coach.clear();assert(model.choose(1629));
  std::cout<<"PASS coach native layout: original flag/competition artwork, three tabs, scrolling, nested back and isolated D3D state\n";
 }
 // Full-roster rendering must retain D3D state and return to the club choice.
 auto rosterFile=std::filesystem::path(argv[3]).parent_path()/L"roster-1043.tsv";
 if(std::filesystem::exists(rosterFile)){
  std::ifstream input(rosterFile,std::ios::binary);assert(clubroster::parse(input,1043,roster.name,roster.players));assert(roster.players.size()>11);roster.club=1043;roster.ready=true;roster.consumed=roster.submitted=lineup.sequence;roster.pending=false;clubPage=ClubPage::Roster;model.detailOpen=true;
  for(int tab=0;tab<3;++tab){roster.tab=tab;clubgfx::SavedState state;state.save(context);frame();drawRoster(context);state.restore(context);capture((L"roster_tab_"+std::to_wstring(tab)+L".bgra").c_str());}
  int hero=roster.player()->id;for(int mode=0;mode<4;++mode){roster.setSort(mode);assert(roster.player()->id==hero&&roster.submitted==lineup.sequence&&!roster.pending);for(size_t i=1;i<roster.players.size();++i){auto&a=roster.players[i-1];auto&b=roster.players[i];if(mode==1)assert(a.overall>=b.overall);if(mode==2&&a.age>=0&&b.age>=0)assert(a.age<=b.age);if(mode==3)assert(a.starter>=b.starter);}}roster.setSort(0);
  roster.selected=0;roster.pending=false;hero=roster.player()->id;roster.navigate(-1);assert(roster.sortFocus&&roster.player()->id==hero&&!roster.pending);roster.horizontal(1);assert(roster.sortMode==1&&roster.player()->id==hero&&!roster.pending);roster.navigate(1);assert(!roster.sortFocus&&roster.player()->id==hero&&!roster.pending);auto sequence=roster.submitted;openPlayerDetail();assert(clubPage==ClubPage::PlayerDetail&&roster.submitted==sequence&&!roster.pending);frame();drawRoster(context);capture(L"player_detail.bgra");goBack();assert(clubPage==ClubPage::Roster&&roster.submitted==sequence&&!roster.pending);roster.setSort(0);
  roster.choose(int(roster.players.size())-1);assert(roster.selected==int(roster.players.size())-1&&roster.scroll>0);roster.choose(int(roster.players.size()));assert(roster.selected==0&&roster.scroll==0);goBack();assert(clubPage==ClubPage::Choice&&model.detailOpen);goBack();assert(clubPage==ClubPage::Map&&!model.detailOpen);
  std::string oldName=roster.name;auto oldCount=roster.players.size();std::istringstream wrong("S16ROSTER1\t1629\tForeign club\n");assert(!clubroster::parse(wrong,1043,roster.name,roster.players)&&roster.name==oldName&&roster.players.size()==oldCount);
  std::ifstream valid(rosterFile,std::ios::binary);std::string blob((std::istreambuf_iterator<char>(valid)),{});auto first=blob.find('\n')+1,last=blob.find('\n',first);std::istringstream duplicate(blob+blob.substr(first,last-first)+"\n");assert(!clubroster::parse(duplicate,1043,roster.name,roster.players));
  std::cout<<"PASS native roster: full save roster, three rendered tabs, scrolling/wrapping, nested back, invalid/duplicate/foreign records rejected\n";
 }
 clubgfx::release(staging);background.clear();renderer.clear();context->ClearState();clubgfx::release(target);clubgfx::release(output);clubgfx::release(context);clubgfx::release(device);
 clubscene::Assets job;job.sequence=1;job.club=130285;job.career=1043;job.pages=3;job.hash=std::string(64,'a');assert(clubscene::validAssets(job));job.hash="../bad";assert(!clubscene::validAssets(job));job.hash=std::string(64,'a');clubscene::loadingPages.fill(0);auto lua=clubscene::bindScript(job,true,true);std::ofstream(std::filesystem::path(argv[3])/L"native_bind.lua")<<lua;
 assert(lua.find("ContextAddRenderable('gameplayprops'")!=std::string::npos);assert(lua.find("'xi_part_96'")!=std::string::npos);assert(lua.find("'prop_plastic'")!=std::string::npos);assert(lua.find("neutral_v2.rx3")!=std::string::npos);job.sequence=2;auto rebind=clubscene::bindScript(job,true,true);assert(clubscene::objectName(job)=="server16_native_club_xi_v5_2");assert(rebind.find("CreateMaterialFromAttribulator")!=std::string::npos);std::ofstream(std::filesystem::path(argv[3])/L"native_rebind.lua")<<rebind;
 {
  auto oldGame=clubscene::game;clubscene::game=std::filesystem::path(argv[3])/L"contact-shadow-fixture"/std::to_wstring(GetCurrentProcessId());
  auto modelFile=clubscene::game/clubscene::contactShadowModel,textureFile=clubscene::game/clubscene::contactShadowTexture;
  assert(!clubscene::indoorContactAvailable());std::filesystem::create_directories(modelFile.parent_path());
  {std::ofstream f(modelFile);f<<"fixture";}assert(!clubscene::indoorContactAvailable());
  std::filesystem::create_directories(textureFile.parent_path());{std::ofstream f(textureFile);f<<"fixture";}
  assert(clubscene::indoorContactAvailable());job.single=true;clubscene::roomView=true;
  for(int i=0;i<2;++i){job.sequence=3+i;auto indoorScript=clubscene::bindScript(job,true,true);
   assert(clubscene::contactShadowParts==2&&indoorScript.find("xi_floor_contact_2")!=std::string::npos);
   std::ofstream(std::filesystem::path(argv[3])/(i?L"native_indoor_rebind.lua":L"native_indoor_bind.lua"))<<indoorScript;
  }
  clubscene::roomView=false;assert(clubscene::bindScript(job,true,true).find("xi_floor_contact_")==std::string::npos);
  clubscene::roomView=true;job.single=false;assert(clubscene::bindScript(job,true,true).find("xi_floor_contact_")==std::string::npos);
  assert(clubscene::contactShadowParts==0);clubscene::roomView=false;clubscene::game=oldGame;
 }
 // Borrow/restore an artificial scene. No game is attached, no hook installed.
 auto fake=VirtualAlloc(nullptr,0x3600000,MEM_COMMIT|MEM_RESERVE,PAGE_READWRITE);assert(fake);clubscene::base=(uintptr_t)fake;alignas(16)unsigned char scene[0xd0]{};auto ptr=(uintptr_t)scene;memcpy((char*)fake+0x3517c10,&ptr,8);int enabled=1;memcpy(scene+0x3c,&enabled,4);float x=1,y=.5625f;memcpy(scene+0x88,&x,4);memcpy(scene+0x8c,&y,4);unsigned char sceneOriginal[sizeof scene];memcpy(sceneOriginal,scene,sizeof scene);clubscene::camera.apply();assert(clubscene::camera.scene==ptr);assert(memcmp(scene+0x40,sceneOriginal+0x40,64));clubscene::camera.restore();assert(!memcmp(scene,sceneOriginal,sizeof scene));
 clubscene::camera.apply();float other=42;memcpy(scene+0xbc,&other,4);clubscene::camera.restore();assert(clubscene::get<float>(ptr+0xbc)==42);assert(!memcmp(scene+0x40,sceneOriginal+0x40,64));
 // Regression observed in live FIFA: state 13 is a valid loaded stadium.
 for(int state:{1,13}){memcpy(scene,sceneOriginal,sizeof scene);memcpy(scene+0x3c,&state,4);unsigned char expected[sizeof scene];memcpy(expected,scene,sizeof scene);assert(clubscene::sceneAvailable());clubscene::camera.apply();assert(clubscene::camera.scene==ptr);assert(memcmp(scene+0x40,expected+0x40,64));clubscene::camera.restore();assert(!memcmp(scene,expected,sizeof scene));}
 for(int state:{0,2,8,12,-1}){memcpy(scene,sceneOriginal,sizeof scene);memcpy(scene+0x3c,&state,4);assert(!clubscene::sceneAvailable());clubscene::camera.apply();assert(!clubscene::camera.scene);}
 memcpy(scene,sceneOriginal,sizeof scene);int state=13;memcpy(scene+0x3c,&state,4);float invalid=0;memcpy(scene+0x8c,&invalid,4);assert(!clubscene::sceneAvailable());clubscene::camera.apply();assert(!clubscene::camera.scene);
 clubscene::base=0;VirtualFree(fake,0,MEM_RELEASE);
 // Exercise the actual room entry policy with a non-signaled owned handle.
 // No FIFA/Server process is started; request files live only in test output.
 roomEntry=true;assert(model.choose(1629));lineup.folder=std::filesystem::path(argv[3])/L"room-roster-entry";lineup.child=CreateEventW(nullptr,TRUE,FALSE,nullptr);assert(lineup.child);
 assert(syncRoomRoster(1043));assert(model.club().id==1043&&roster.club==1043&&lineup.career==1043&&clubPage==ClubPage::Roster);auto roomSequence=lineup.sequence;
 assert(!syncRoomRoster(1043)&&lineup.sequence==roomSequence);assert(syncRoomRoster(1629));assert(model.club().id==1629&&roster.club==1629&&lineup.career==1629);
 assert(!syncRoomRoster(0)&&roster.club==0&&!clubscene::requested);lineup.stop();roster.clear();roomEntry=false;
 std::cout<<"PASS room roster entry: live career club overrides old globe selection, unchanged club reuses request, career change reloads, missing club clears stale data\n";
 std::cout<<"PASS model: 1647 clubs, 49 regions; game art; WARP shaders; horizon/zoom; native scene job/script; camera states 1/13 and restoration; invalid scenes rejected; D3D state restoration\n";CoUninitialize();return 0;
}
