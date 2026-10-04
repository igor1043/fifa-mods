/* Offscreen WARP QA. Explicit catalog fixture + native installed models.
 * No FIFA process manipulation, no database or save writes. */
#define CLUB_PLAYER_SCREEN_QA
#include "../render/test_club_player_3d.cpp"
#include "../../src/screens/clubs/clubs_browser.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../src/screens/coach/coach_profile_screen.h"
#include "../../src/screens/competitions/club_competitions_screen.h"
#include "../../src/screens/transfers/transfer_center_screen.h"
#include "../../third_party/imgui/imgui.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
static XINPUT_STATE pad={};static int refreshes=0;
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD n,XINPUT_STATE*out){if(n)return ERROR_DEVICE_NOT_CONNECTED;*out=pad;return ERROR_SUCCESS;}
extern "C" void clubs_browser_request_native_refresh(){++refreshes;}
void transfer_center_screen_publish_league_catalog(const ClubBrowserRow*,size_t,int){}
void transfer_center_screen_publish_roster(const ClubPlayerRow*,size_t,int,const char*){}
extern "C" int club_competitions_social_read(int,ClubCompetitionSocialSnapshot*out){if(out)*out={};return 0;}
void club_competitions_screen_draw_office(float,float,float,float,int,int,int,bool,bool){}
static void log_line(const char*s){if(!strncmp(s,"Club3D:",7)||!strncmp(s,"OtherClubs:",11))puts(s);}
int main(int argc,char**argv){
    require(argc==4,"usage: test_clubs_browser game_root fixture.bin output_directory");
    std::vector<ClubPlayerRow>rows;char name[128]={},magic[8];uint32_t count,club,size;FILE*f=nullptr;
    require(!fopen_s(&f,argv[2],"rb")&&f,"open offline native roster fixture");
    require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&fread(&club,4,1,f)==1&&fread(&size,4,1,f)==1&&size==sizeof(ClubPlayerRow)&&count>=11&&count<=100,"bounded native roster fixture");
    rows.resize(count);require(fread(name,1,128,f)==128&&fread(rows.data(),sizeof(ClubPlayerRow),count,f)==count,"owned fixture rows");fclose(f);
    ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)),"WARP renderer");
    D3D11_TEXTURE2D_DESC desc={};desc.Width=1428;desc.Height=800;desc.MipLevels=desc.ArraySize=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*rt=nullptr;ID3D11ShaderResourceView*srv=nullptr;
    require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"target");d->CreateRenderTargetView(t,nullptr,&rt);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();
    ImGui::CreateContext();auto&io=ImGui::GetIO();io.DisplaySize={1428,800};io.DeltaTime=1.f/60;io.IniFilename=nullptr;io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf",17);
    ImGui::StyleColorsDark();require(ImGui_ImplDX11_Init(d,c),"ImGui native host");
    require(club_player_screen_register(argv[1],log_line)&&coach_profile_register(argv[1],log_line)&&clubs_browser_register(argv[1],log_line),"native actions register");
    club_player_screen_set_device(d);coach_profile_device(d);clubs_browser_device(d);
    auto frame=[&](){mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();auto style=ImGui::GetStyle();mod_screen_draw();require(!memcmp(style.Colors,ImGui::GetStyle().Colors,sizeof(style.Colors)),"selector/children restore shared style");ImGui::Render();float bg[]={.015f,.09f,.16f,1};c->OMSetRenderTargets(1,&rt,nullptr);c->ClearRenderTargetView(rt,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);};
    auto key=[&](ImGuiKey k){io.AddKeyEvent(k,true);frame();io.AddKeyEvent(k,false);frame();};
    auto button=[&](WORD b){pad.Gamepad.wButtons=b;frame();pad={};frame();};
    auto capture=[&](const char*file){frame();image(d,c,srv,(std::string(argv[3])+"/"+file+".bmp").c_str());};
    ClubBrowserRow catalog[6]={};int teams[]={1043,1041,112716,112893,1,5},leagues[]={7,7,2028,39,13,13},nations[]={54,54,54,95,14,14};
    const char*clubs[]={"Flamengo","Botafogo","Clube de outra divisão","Inter Miami","Arsenal","Chelsea"};
    for(int i=0;i<6;++i){auto&r=catalog[i];r.team=teams[i];r.league=leagues[i];r.nation=nations[i];r.attack=78;r.midfield=80;r.defense=78;r.prestige=18;
        strcpy_s(r.name,clubs[i]);strcpy_s(r.league_name,i<2?"Brasileirão Betano":i==2?"Série B":i==3?"MLS":"Premier League");strcpy_s(r.nation_name,i<3?"Brasil":i==3?"Estados Unidos":"Inglaterra");}
    auto local=rows;for(auto&r:local)r.team_id=112893;club_player_screen_publish(local.data(),local.size(),112893,"Inter Miami");
    clubs_browser_publish_catalog(catalog,6,1043);require(mod_screen_open_action(FIFA16_CLUBS_BROWSER_ACTION),"open only through own native action");frame();Sleep(280);
    require(clubs_browser_take_catalog_request()&&!clubs_browser_take_catalog_request()&&refreshes==1,"one catalog request, queued provider refresh");
    for(int i=0;i<30;++i)frame();require(clubs_browser_test_view().team==1043&&clubs_browser_test_view().focus==1,"initial career club selected");capture("other-clubs-selector");
    key(ImGuiKey_LeftArrow);require(clubs_browser_test_view().team==1041,"keyboard switches club within league only");button(XINPUT_GAMEPAD_DPAD_RIGHT);require(clubs_browser_test_view().team==1043,"Xbox switches club");
    key(ImGuiKey_E);require(clubs_browser_test_view().league==2028,"keyboard selects exact next division");key(ImGuiKey_Q);require(clubs_browser_test_view().league==7,"return to original division");
    button(XINPUT_GAMEPAD_RIGHT_SHOULDER);require(clubs_browser_test_view().nation==95,"Xbox country navigation");button(XINPUT_GAMEPAD_LEFT_SHOULDER);require(clubs_browser_test_view().nation==54,"back to Brazil");
    pad.Gamepad.sThumbLY=24000;frame();pad={};frame();require(clubs_browser_test_view().focus==0,"left analog changes selector section");button(XINPUT_GAMEPAD_DPAD_DOWN);
    if(clubs_browser_test_view().team!=1043)key(ImGuiKey_RightArrow);
    button(XINPUT_GAMEPAD_A);int requested;unsigned serial;require(clubs_browser_take_roster_request(&requested,&serial)&&requested==1043,"A requests exact selected club, no borrowed roster");
    clubs_browser_publish_roster(1043,serial+1,rows.data(),rows.size(),"Flamengo");frame();require(clubs_browser_test_view().waiting&&!clubs_browser_test_view().child,"stale reply cannot open another club");
    clubs_browser_publish_roster(1043,serial,rows.data(),rows.size(),"Flamengo");for(int i=0;i<180;++i)frame();require(clubs_browser_test_view().child&&club_player_screen_test_view().home&&club_player_screen_test_view().starters==11,"selected club home and exact native XI open embedded");capture("other-clubs-flamengo");
    club_player_screen_publish(local.data(),local.size(),112893,"Inter Miami");frame();require(club_player_screen_test_view().starters==11&&club_player_screen_test_view().selected_id==rows[0].player_id&&club_player_screen_test_view().card_club==1043,"regular own-club refresh does not replace foreign roster or coach identity");
    Sleep(280);button(XINPUT_GAMEPAD_A);require(club_player_screen_test_view().coach_child,"foreign coach card opens generic coach profile inside browser modal");
    for(int i=0;i<30;++i)frame();capture("other-clubs-coach");Sleep(280);button(XINPUT_GAMEPAD_B);Sleep(280);
    Sleep(280);button(XINPUT_GAMEPAD_DPAD_RIGHT);button(XINPUT_GAMEPAD_A);for(int i=0;i<20;++i)frame();require(!club_player_screen_test_view().home&&club_player_screen_test_view().group,"XI card opens full selected club squad");Sleep(280);button(XINPUT_GAMEPAD_B);Sleep(280);button(XINPUT_GAMEPAD_B);
    require(!clubs_browser_test_view().child&&mod_screen_is_active("other-clubs")&&mod_screen_captures_input(),"B returns to selector without releasing modal focus");Sleep(280);
    float x,y;require(clubs_browser_test_center(3,x,y),"mouse action bounds");io.AddMousePosEvent(x,y);frame();io.AddMouseButtonEvent(0,true);frame();io.AddMouseButtonEvent(0,false);frame();require(clubs_browser_test_view().waiting&&clubs_browser_take_roster_request(&requested,&serial),"mouse uses exact same native roster workflow");
    button(XINPUT_GAMEPAD_B);clubs_browser_publish_roster(requested,serial,rows.data(),rows.size(),"stale");frame();require(!clubs_browser_test_view().child&&!clubs_browser_test_view().waiting,"B cancellation ignores late reply");Sleep(280);
    button(XINPUT_GAMEPAD_A);require(clubs_browser_take_roster_request(&requested,&serial),"new request after cancellation");clubs_browser_publish_roster(requested,serial,nullptr,0,"");frame();require(!clubs_browser_test_view().child&&!clubs_browser_test_view().waiting,"missing roster never substituted with another team");
    clubs_browser_device(nullptr);clubs_browser_device(d);frame();capture("other-clubs-device-reset");
    c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();rt->Release();desc.Width=1280;desc.Height=720;
    require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"720p target");d->CreateRenderTargetView(t,nullptr,&rt);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();io.DisplaySize={1280,720};capture("other-clubs-720p");
    clubs_browser_invalidate();frame();require(clubs_browser_test_view().count==0&&!clubs_browser_test_view().child,"save-context transition clears catalog/child");clubs_browser_publish_catalog(catalog,6,1043);frame();Sleep(280);
    button(XINPUT_GAMEPAD_B);require(!mod_screen_is_open()&&mod_screen_captures_input(),"final B release delay");
    require(mod_screen_open_action(FIFA16_CLUB_PLAYER_ACTION),"open original own club after browser");for(int i=0;i<300&&club_player_screen_test_view().card_club!=112893;++i)frame();require(club_player_screen_test_view().home&&club_player_screen_test_view().card_club==112893,"original Meu clube publication preserved");
    mod_screen_close();mod_screen_sync_lifecycle();clubs_browser_device(nullptr);club_player_screen_set_device(nullptr);coach_profile_device(nullptr);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();rt->Release();c->Release();d->Release();
    puts("PASS: native selector, country/league/club, keyboard/mouse/Xbox, exact roster tokens, modal children/back, cancellation, missing data, device reset and original club isolation; offline only");return 0;
}
