/* Preview/QA only: real native SLC and explicit demonstration statistics.
 * This executable has no FIFA process handle and no save writer. */
#define CLUB_PLAYER_SCREEN_QA
#include "../render/test_club_player_3d.cpp"
#include "../../src/screens/coach/coach_profile_data.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../third_party/imgui/imgui.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
static XINPUT_STATE pad={};
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD i,XINPUT_STATE*out){if(i)return ERROR_DEVICE_NOT_CONNECTED;*out=pad;return ERROR_SUCCESS;}
static void log_line(const char*s){puts(s);}
static void frame(ID3D11DeviceContext*c,ID3D11RenderTargetView*t){
    mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();auto before=ImGui::GetStyle();mod_screen_draw();
    require(!memcmp(before.Colors,ImGui::GetStyle().Colors,sizeof(before.Colors)),"profile restores shared theme");
    require(before.ItemSpacing.x==ImGui::GetStyle().ItemSpacing.x&&before.ItemSpacing.y==ImGui::GetStyle().ItemSpacing.y,"local spacing restored");
    auto&io=ImGui::GetIO();ImGui::GetForegroundDrawList()->AddText({24,io.DisplaySize.y-26},IM_COL32(245,248,252,255),"PRÉVIA OFFLINE | Modelo nativo FIFA 16 | Estatísticas de demonstração");
    ImGui::Render();float bg[]={.015f,.065f,.11f,1};c->OMSetRenderTargets(1,&t,nullptr);c->ClearRenderTargetView(t,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);
}
static void button(WORD b,ID3D11DeviceContext*c,ID3D11RenderTargetView*t){pad.Gamepad.wButtons=b;frame(c,t);pad={};frame(c,t);}
static CoachCareerRow row(int key,int team,int season,const char*name,CoachMatchStats s){CoachCareerRow r={};r.key=key;r.team=team;r.season=season;r.season_valid=1;r.total=s;strcpy_s(r.team_name,name);return r;}
int main(int argc,char**argv){require(argc==3,"usage GAME_ROOT OUTPUT_DIRECTORY (offline only)");
    using namespace coach_profile;
    require(efficiency({10,5,3,2,20,10})==60&&win_rate({10,5,3,2,20,10})==50,"points efficiency differs from win percentage");
    require(efficiency({})<0,"zero games percentage is absent");
    std::vector<CoachCareerRow>rows={row(1,1043,0,"Flamengo",{20,12,5,3,38,17}),row(2,1043,1,"Flamengo",{24,15,5,4,47,23}),
        row(3,112893,2,"Inter Miami",{18,10,4,4,31,18}),row(4,1043,3,"Flamengo",{6,4,1,1,11,5}),row(5,1357,3,"Brasil",{4,3,1,0,9,2})};
    rows[0].league_titles=1;rows[1].domestic_titles=1;rows[2].league_titles=1;rows[4].team_kind=COACH_TEAM_NATIONAL;
    auto before=rows;auto spells=passages(rows,COACH_TEAM_CLUB);
    require(spells.size()==3&&spells[0].total.games==44&&spells[2].total.games==6,"separate returning spell and national appointment, aggregate consecutive seasons");
    FceFixture fixtures[7]={};for(int i=0;i<6;++i){auto&f=fixtures[i];f.id=i+1;f.home=i%2?7:1043;f.away=i%2?1043:7;f.date_raw=20260101+i;f.played_raw=1;
        int gf[]={2,3,1,2,1,2},ga[]={0,1,1,0,2,1};f.home_score=i%2?ga[i]:gf[i];f.away_score=i%2?gf[i]:ga[i];}
    fixtures[6]=fixtures[0];bind_splits(rows.data(),rows.size(),fixtures,7,20260110,1043,3);
    require(rows[3].splits_valid&&rows[3].home.games==3&&rows[3].away.games==3,"duplicate fixture counted once and exact coherent current-spell split");
    CoachCareerRow current={};require(current_club_row(fixtures,7,1043,20260110,"Flamengo",current),"build current-club record from fixtures");
    require(current.total.games==6&&current.home.games==3&&current.away.games==3&&!current.season_valid,"current club record separates home and away without inventing a season label");
    require(efficiency(current.total)>72.2&&efficiency(current.total)<72.3&&win_rate(current.total)>66.6&&win_rate(current.total)<66.7,"points efficiency differs from wins as a share of games");
    auto malformed=before;fixtures[6].home_score=10;bind_splits(malformed.data(),malformed.size(),fixtures,7,20260110,1043,3);
    require(!malformed[3].splits_valid,"conflicting duplicate never fabricates split");fixtures[6]=fixtures[0];
    auto partial=before;bind_splits(partial.data(),partial.size(),fixtures,3,20260110,1043,3);require(!partial[3].splits_valid,"partial live schedule is not total history");
    CoachProfileContext context={};context.valid=1;context.kind=COACH_CLUB_MANAGER;context.id=context.club=1043;context.history_valid=1;context.stats_scope=COACH_STATS_CAREER;
    context.nationality=38;context.national_team=1357;context.season=3;context.reputation=920;context.confidence=86;context.wage=-1;
    coach_profile_bind_form(&context,fixtures,7,20260110);require(context.recent_valid&&context.recent_games==5&&context.recent_points==10,"latest five games, deduplicated and sorted");
    auto bad_form=context;fixtures[6].home_score=10;coach_profile_bind_form(&bad_form,fixtures,7,20260110);require(!bad_form.recent_valid,"conflicting schedule does not fabricate form");fixtures[6]=fixtures[0];
    auto rating=context;rating.league_strength_valid=1;rating.league_strength=100;rating.recent_valid=1;rating.recent_games=5;rating.recent_points=0;rating.reputation=0;
    double high_league=reputation_score(rating);rating.league_strength=30;rating.recent_points=15;rating.reputation=1501;
    require(high_league>reputation_score(rating),"league outweighs perfect winning streak and native points");
    rating.league_strength=100;require(reputation_stars(rating)==5,"five stars maximum");rating.league_strength_valid=0;require(reputation_stars(rating)==-1,"missing league is unknown, not zero stars");
    require(profile_reputation::player(100,40)>profile_reputation::player(30,99)&&profile_reputation::stars(profile_reputation::player(100,99))==5,"player league dominates OVR, five-star limit");
    require(profile_reputation::player(-1,90)<0&&profile_reputation::player(80,-1)<0,"missing league or OVR not fabricated");
    strcpy_s(context.name,"Leonardo Jardim");strcpy_s(context.club_name,"Flamengo");strcpy_s(context.national_name,"Brasil");
    context.colors_valid=1;context.colors[0]=0xb60019;context.colors[1]=0x151515;context.colors[2]=0xffffff;
    CoachProfileContext owned={};std::vector<CoachCareerRow>copied;
    auto duplicate=rows;duplicate.push_back(rows[0]);require(copy(&context,duplicate.data(),duplicate.size(),owned,copied)&&copied.size()==5,"duplicate key identical row ignored");
    duplicate.back().total.goals_for++;require(!copy(&context,duplicate.data(),duplicate.size(),owned,copied),"conflicting manager history rejected");
    ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)),"WARP device");
    D3D11_TEXTURE2D_DESC desc={};desc.Width=1428;desc.Height=800;desc.MipLevels=desc.ArraySize=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;
    desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*target=nullptr;ID3D11ShaderResourceView*srv=nullptr;
    require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"UI target");d->CreateRenderTargetView(t,nullptr,&target);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();
    ImGui::CreateContext();auto&io=ImGui::GetIO();io.DisplaySize={1428,800};io.DeltaTime=1.f/60;io.IniFilename=nullptr;
    io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf",17);ImGui::StyleColorsDark();require(ImGui_ImplDX11_Init(d,c),"ImGui renderer");
    require(coach_profile_register(argv[1],log_line),"generic coach action registered");coach_profile_device(d);
    require(coach_profile_open(&context,rows.data(),rows.size()),"open explicit club trainer");
    for(int i=0;i<300&&!coach_profile_test_view().model;++i)frame(c,target);
    require(coach_profile_test_view().model&&coach_profile_test_view().external&&coach_profile_test_view().rows==5,"real matching SLC model plus owned generic history");
    auto shot=[&](const char*name){std::string file=std::string(argv[2])+"/"+name+".bmp";for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,file.c_str());};
    shot("coach-summary");Sleep(360);
    for(int page=1;page<5;++page){button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(coach_profile_test_view().page==page,"Xbox shoulder controls every coach tab");
        const char*names[]={"coach-summary","coach-performance","coach-clubs","coach-nations","coach-titles"};shot(names[page]);}
    auto camera=coach_profile_test_view();pad.Gamepad.bRightTrigger=255;for(int i=0;i<10;++i)frame(c,target);pad={};frame(c,target);
    require(coach_profile_test_view().zoom>camera.zoom&&coach_profile_test_view().page==4,"RT zooms without tab navigation");
    pad.Gamepad.sThumbRX=23000;pad.Gamepad.sThumbRY=23000;for(int i=0;i<10;++i)frame(c,target);pad={};frame(c,target);
    require(coach_profile_test_view().yaw>camera.yaw&&coach_profile_test_view().pan>camera.pan,"right stick rotates and raises camera");
    button(XINPUT_GAMEPAD_RIGHT_THUMB,c,target);require(coach_profile_test_view().yaw==0&&coach_profile_test_view().zoom==1,"R3 resets camera");
    button(XINPUT_GAMEPAD_DPAD_LEFT,c,target);require(coach_profile_test_view().page==3,"directional tab navigation");
    io.AddKeyEvent(ImGuiKey_Q,true);frame(c,target);io.AddKeyEvent(ImGuiKey_Q,false);frame(c,target);require(coach_profile_test_view().page==2,"keyboard tab navigation");
    float x,y;require(coach_profile_test_tab_center(0,x,y),"tab hit area");io.AddMousePosEvent(x,y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    require(coach_profile_test_view().page==0,"mouse clicks exact same summary tab");
    auto resize=[&](UINT w,UINT h){c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();target->Release();desc.Width=w;desc.Height=h;
        require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"resolution target");d->CreateRenderTargetView(t,nullptr,&target);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();io.DisplaySize={(float)w,(float)h};};
    resize(1280,720);shot("coach-720p");resize(1920,1080);shot("coach-1080p");resize(1428,800);
    require(mod_screen_captures_input(),"shared exclusive input retained");mod_screen_request_back();frame(c,target);
    require(!mod_screen_is_open()&&mod_screen_captures_input(),"return closes and retains release debounce");
    auto user=context;user.kind=COACH_CAREER_USER;user.id=0;strcpy_s(user.name,"Treinador personalizado");user.history_valid=0;
    coach_profile_publish_career(&user,nullptr,0);require(mod_screen_open_action(FIFA16_COACH_PROFILE_ACTION),"career card action");
    for(int i=0;i<300&&!coach_profile_test_view().model;++i)frame(c,target);require(coach_profile_test_view().kind==COACH_CAREER_USER&&!coach_profile_test_view().external&&coach_profile_test_view().model&&coach_profile_test_view().rows==0,"custom career manager uses the club's assigned 3D model without borrowing club history");
    require(coach_profile_take_refresh()&&!coach_profile_take_refresh(),"card requests one native capture");shot("coach-career-club-model");
    coach_profile_publish_career(nullptr,nullptr,0);frame(c,target);require(coach_profile_test_view().club==0&&coach_profile_test_view().rows==0,"career reset clears previous trainer");
    mod_screen_close();frame(c,target);auto club_context=context;club_context.stats_scope=COACH_STATS_CURRENT_CLUB;club_context.history_valid=1;club_context.nationality=0;
    club_context.national_team=0;club_context.confidence=club_context.reputation=club_context.wage=-1;club_context.recent_valid=0;
    strcpy_s(club_context.name,"Treinador do clube");require(coach_profile_open(&club_context,&current,1),"open a club manager using club fixtures");
    for(int i=0;i<300&&!coach_profile_test_view().model;++i)frame(c,target);shot("coach-current-club-summary");Sleep(360);button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);
    require(coach_profile_test_view().page==1,"club performance tab is selectable");shot("coach-current-club-performance");
    mod_screen_close();frame(c,target);require(coach_profile_open(&context,rows.data(),rows.size()),"generic reopen");
    for(int i=0;i<300&&!coach_profile_test_view().model;++i)frame(c,target);require(coach_profile_test_view().model,"reopen assets");
    coach_profile_device(nullptr);coach_profile_device(d);for(int i=0;i<3;++i)frame(c,target);require(coach_profile_test_view().model,"device reset restores assets");
    mod_screen_close();mod_screen_sync_lifecycle();coach_profile_device(nullptr);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
    puts("PASS: owned trainer identities, history aggregation, match splits, real native model, all tabs, mouse/keyboard/Xbox, modal release and device reset; offline only");return 0;
}
