/* WARP renders using explicit offline rosters. The match/date are QA fixtures,
 * not a claim about the next fixture in the user's career. No save writes. */
#define CLUB_PLAYER_SCREEN_QA
#include "../render/test_club_player_3d.cpp"
#include "../../src/screens/club/club_player_screen.h"
#include "../../src/screens/next_match/next_match_screen.h"
#include "../../src/render/stadium_thumbnails/stadium_preview.h"
#include "../../src/ui/common/lineup_pitch.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../third_party/imgui/imgui.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
static XINPUT_STATE pad={};
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD index,XINPUT_STATE*out){if(index)return ERROR_DEVICE_NOT_CONNECTED;*out=pad;return ERROR_SUCCESS;}
static void log_line(const char*s){if(!strchr(s,'\n')&&strncmp(s,"Club3D asset:",13))puts(s);}
static void frame(ID3D11DeviceContext*c,ID3D11RenderTargetView*target){mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();
    ImGuiStyle before=ImGui::GetStyle();mod_screen_draw();
    require(!memcmp(before.Colors,ImGui::GetStyle().Colors,sizeof(before.Colors))&&before.WindowPadding.x==ImGui::GetStyle().WindowPadding.x&&before.WindowPadding.y==ImGui::GetStyle().WindowPadding.y&&before.WindowRounding==ImGui::GetStyle().WindowRounding&&before.ChildRounding==ImGui::GetStyle().ChildRounding,"light next-match theme never leaks into other screens");ImGui::Render();
    float bg[4]={.01f,.08f,.14f,1};c->OMSetRenderTargets(1,&target,nullptr);c->ClearRenderTargetView(target,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);}
static NextMatchSide roster(const char*path){NextMatchSide s={};FILE*f=nullptr;require(!fopen_s(&f,path,"rb")&&f,"read explicit roster fixture");char magic[8];uint32_t count=0,team=0,row_size=0;
    require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&fread(&team,4,1,f)==1&&fread(&row_size,4,1,f)==1&&count<=CLUB_PLAYER_CAPACITY&&row_size==sizeof(ClubPlayerRow),"bounded fixture schema");
    require(fread(s.name,1,128,f)==128&&fread(s.rows,sizeof(ClubPlayerRow),count,f)==count&&fgetc(f)==EOF,"exact owned roster bytes");fclose(f);s.count=count;s.team=team;s.roster_valid=1;return s;}
int main(int argc,char**argv){require(argc==5,"usage GAME_ROOT FLAMENGO_FIXTURE MIAMI_FIXTURE OUTPUT_PREFIX");
    for(const std::vector<int>&slots:std::vector<std::vector<int>>{{0,3,4,6,7,12,13,15,16,24,26},{0,3,4,6,7,9,11,17,18,19,25},{0,3,4,6,7,13,14,15,23,25,27},{0,4,5,6,2,8,13,14,15,24,26},{0,3,4,6,7,12,13,14,15,16,25},{0,5,5,5,5,5,5,5,5,5,5}}) {
        std::vector<ClubPlayerRow>rows(11);for(size_t i=0;i<rows.size();++i)rows[i].squad_position=slots[i];
        auto layout=lineup_pitch::layout(rows);require(layout.size()==11,"all tactical formations retain all eleven nodes including repeated roles");
        bool seen[11]={};for(const auto&p:layout){require(p.row<11&&!seen[p.row]&&std::isfinite(p.x)&&std::isfinite(p.y)&&p.x>=.099f&&p.x<=.901f&&p.y>=.129f&&p.y<=.901f,"unique bounded dynamic pitch coordinates");seen[p.row]=true;
            for(const auto&q:layout)if(q.row!=p.row)require(fabsf(p.x-q.x)+fabsf(p.y-q.y)>.07f,"pitch nodes never occupy the same cell");
            if(rows[p.row].squad_position==0)require(p.x==.5f&&p.y>.89f,"goalkeeper at the goal, not preferred-position guesses");}
        rows.back().squad_position=29;require(lineup_pitch::layout(rows).empty(),"reserve/unknown slots never masquerade as a starter");
        rows.pop_back();require(lineup_pitch::layout(rows).empty(),"partial lineup does not invent missing photographs");
    }
    auto home=roster(argv[2]),away=roster(argv[3]);Assets assets(argv[1]);Texture preview;std::string source;
    require(stadium_preview::load(argv[1],"BRA - Maracana - Flamengo",preview,source)&&preview.format==3&&source.find(".jpg")!=source.npos,"direct JPEG decoded to memory, no DDS conversion/copy");
    require(!stadium_preview::load(argv[1],"../escape",preview,source)&&!stadium_preview::load(argv[1],"stadium-that-does-not-exist",preview,source)&&source.empty(),"unsafe and missing images hidden without generic fallback");
    auto player=assets.load(home.rows[0]);
    for(unsigned pose:{301u,302u}){auto posed=player;require(apply_presentation_pose(posed,false,nullptr,pose),"seated athlete uses own FIFA skeleton");
        require(posed.parts.size()==player.parts.size()&&posed.textures.size()==player.textures.size(),"seated pose preserves hair, kit, gloves and textures");
        for(const auto&p:posed.parts)for(const auto&v:p.vertices)require(std::isfinite(v.position.x)&&std::isfinite(v.position.y)&&std::isfinite(v.position.z)&&fabs(v.position.x)<250&&fabs(v.position.y)<250&&fabs(v.position.z)<250,"seated geometry finite and bounded");}
    auto coach=assets.coach(home.rows[0]);require(coach.model!=nullptr,"actual matching coach fixture available");
    auto pair=build_club_room({std::make_shared<Model>(player)},RoomPressPair,coach.model);
    require(pair.press_coach_present&&pair.press_player_id==home.rows[0].player_id&&pair.player_count==2,"conference includes exact club coach + player");
    auto wrong=std::make_shared<Model>(*coach.model);wrong->team_id=away.team;
    auto absent=build_club_room({std::make_shared<Model>(player)},RoomPressPair,wrong);
    require(!absent.press_coach_present&&absent.player_count==1,"never render an unrelated team's coach");
    ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)),"native WARP");
    D3D11_TEXTURE2D_DESC desc={};desc.Width=1428;desc.Height=800;desc.MipLevels=desc.ArraySize=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*target=nullptr;ID3D11ShaderResourceView*srv=nullptr;require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"target");d->CreateRenderTargetView(t,nullptr,&target);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();
    ImGui::CreateContext();auto&io=ImGui::GetIO();io.DisplaySize=ImVec2(1428,800);io.DeltaTime=1.f/60;io.IniFilename=nullptr;io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf",16);ImGui::StyleColorsDark();require(ImGui_ImplDX11_Init(d,c),"ImGui");
    require(club_player_screen_register(argv[1],log_line)&&next_match_register(argv[1],log_line),"independent native markers registered");club_player_screen_set_device(d);next_match_device(d);
    club_player_screen_publish(home.rows,home.count,home.team,home.name);
    require(mod_screen_open_action(FIFA16_PRESS_CONFERENCE_ACTION),"native press card opens custom scene only");
    for(int i=0;i<300&&!club_player_screen_test_press_rendered();++i)frame(c,target);
    int first=club_player_screen_test_press_player();require(first>0&&club_player_screen_test_press_rendered()==first,"random club athlete actually reaches rendered conference");
    for(int i=0;i<3;++i)frame(c,target);std::string prefix=argv[4];image(d,c,srv,(prefix+"-press.bmp").c_str());
    require(club_player_screen_test_resample_press_player(),"resample available");
    int next=club_player_screen_test_press_player();require(next!=first,"resample avoids same athlete when others exist");
    for(int i=0;i<300&&club_player_screen_test_press_rendered()!=next;++i)frame(c,target);
    require(club_player_screen_test_press_rendered()==next,"second random selection reaches geometry");
    mod_screen_close();frame(c,target);Sleep(300);require(!mod_screen_captures_input(),"press close restores shared input after cooldown");
    require(mod_screen_open_action(FIFA_NEXT_MATCH_ACTION),"next-match card marker opens own modal");frame(c,target);require(next_match_take_refresh(),"open asks provider for a fresh fixture");
    NextMatchSnapshot match={};match.valid=1;match.fixture=999001;match.date=20260128;match.time=2030;match.capacity=78838;match.attendance=59;
    strcpy_s(match.competition,"Partida de teste offline (não é a próxima partida do save)");strcpy_s(match.stadium,"Maracanã - prévia de teste");strcpy_s(match.stadium_key,"BRA - Maracana - Flamengo");
    match.sides[0]=home;match.sides[1]=away;strcpy_s(match.sides[0].formation,"Formação do elenco: prévia offline");strcpy_s(match.sides[1].formation,"Formação do elenco: prévia offline");next_match_publish(&match);
    for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    auto state=next_match_test_view();require(state.ready&&state.xi[0]==11&&state.xi[1]==11&&state.teams[0]==home.team&&state.teams[1]==away.team&&state.image,"two exact-club starting XIs + direct stadium JPEG rendered");
    require(state.team_players[0]==11&&state.team_players[1]==11&&state.pitch[0]==11&&state.pitch[1]==11&&state.portraits[0]>0&&state.portraits[1]>0,"both real formations and their own 2D faces reach the render batch");
    require(state.conditions[0]==0&&state.conditions[1]==0,"missing current energy never uses stamina or fabricates full fitness");
    require(state.numbers[0]==11&&state.numbers[1]==11,"native shirt numbers retained for all players");
    for(int s=0;s<2;++s){auto*p=presentation_pose_find(state.team_pose[s]);require(p&&(p->modes&PoseGroup),"random team recipe reaches actual eleven-player geometry");}
    auto*coach_pose=presentation_pose_find(state.coach_pose[0]);require(coach_pose&&(coach_pose->modes&PoseStandingCoach)&&!(coach_pose->modes&PosePressConferenceCoach),"coach randomization uses an actual standing pose, not a seated pose without furniture");
    for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-next-photos.bmp").c_str());
    pad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);pad={};frame(c,target);require(next_match_test_view().view==1,"LB/RB changes lineup view");image(d,c,srv,(prefix+"-next-lineups.bmp").c_str());
    pad.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);pad={};frame(c,target);require(next_match_test_view().view==2,"LB/RB changes coach view");image(d,c,srv,(prefix+"-next-coaches.bmp").c_str());
    require(next_match_test_view().team_pose[0]==state.team_pose[0]&&next_match_test_view().coach_pose[0]==state.coach_pose[0],"tab changes never reshuffle poses");
    next_match_publish(&match);for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().team_pose[0]==state.team_pose[0]&&next_match_test_view().team_pose[1]==state.team_pose[1]&&next_match_test_view().coach_pose[0]==state.coach_pose[0],"refresh of the same fixture keeps its poses stable");
    match.fixture++;next_match_publish(&match);for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().ready&&next_match_test_view().team_pose[0]!=state.team_pose[0]&&next_match_test_view().team_pose[1]!=state.team_pose[1]&&next_match_test_view().coach_pose[0]!=state.coach_pose[0],"a new fixture resamples both teams and the actual coach without immediate repeats");
    match.sides[1].rows[0].team_id=home.team;next_match_publish(&match);for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().ready&&next_match_test_view().xi[1]==0,"mixed-club XI rejected rather than displaying eleven invented athletes");
    match.sides[1]=away;match.sides[1].rows[0].player_id=524286;next_match_publish(&match);
    for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().ready&&next_match_test_view().xi[1]==11&&next_match_test_view().pitch[1]==11&&next_match_test_view().portraits[1]==state.portraits[1]-1,"missing 2D portrait keeps its slot without borrowing a face");
    pad.Gamepad.wButtons=XINPUT_GAMEPAD_LEFT_SHOULDER;frame(c,target);pad={};frame(c,target);
    image(d,c,srv,(prefix+"-next-missing-portrait.bmp").c_str());
    NextMatchSnapshot empty={};next_match_publish(&empty);frame(c,target);require(!next_match_test_view().ready&&!next_match_test_view().image,"no fixture clears stale teams and image");
    mod_screen_request_back();frame(c,target);Sleep(300);require(!mod_screen_captures_input(),"next-match closes and releases input");
    require(mod_screen_open_action(FIFA_NEXT_MATCH_ACTION),"next-match reopens independently");frame(c,target);
    require(next_match_take_refresh(),"reopen requests a fresh live fixture rather than stale geometry");
    match.sides[1]=away;next_match_publish(&match);for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().ready&&next_match_test_view().view==0&&next_match_test_view().portraits[1]==state.portraits[1],"reopen resets the view and restores only current own portraits");
    match.sides[0].condition[0]=0;match.sides[0].condition_valid[0]=1;
    match.sides[0].condition[1]=50;match.sides[0].condition_valid[1]=1;
    match.sides[0].condition[2]=100;match.sides[0].condition_valid[2]=1;
    match.sides[0].condition[3]=101;match.sides[0].condition_valid[3]=1;
    match.sides[0].condition[4]=-1;match.sides[0].condition_valid[4]=1;
    next_match_publish(&match);for(int i=0;i<500&&!next_match_test_view().ready;++i)frame(c,target);
    require(next_match_test_view().conditions[0]==3,"current condition supports exhausted/full states but rejects invalid percentages");
    mod_screen_request_back();frame(c,target);Sleep(300);require(!mod_screen_captures_input(),"reopened view releases focus again");
    puts("PASS: native XI pitch + 2D faces, shirt numbers, explicit current-condition validity, isolated light theme, tactical formations, stable random team/coach poses and resampling, direct JPG, Xbox views, missing data, close/focus. Offline fixtures only; no save written.");fflush(stdout);ExitProcess(0);
}
