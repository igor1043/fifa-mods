/* Offscreen UI QA with real RX3 assets and explicit synthetic attribute rows.
 * Never inject these fixtures into FIFA or save them in its database. */
#define CLUB_PLAYER_SCREEN_QA
#include "../render/test_club_player_3d.cpp"
#include "../../src/screens/club/club_player_screen.h"
#include "../../src/screens/player/club_player_profile.h"
#include "../../src/ui/common/profile_reputation.h"
#include "../../src/screens/coach/coach_profile_screen.h"
#include "../../src/screens/office/career_news_feed.h"
#include "../../src/screens/competitions/club_competitions_screen.h"
#include "../../src/screens/office/office_social_feed.h"
#include "../../src/screens/operations/career_operations.h"
#include "../../src/screens/clubs/clubs_browser.h"
#include "../../src/screens/transfers/transfer_center_screen.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../third_party/imgui/imgui.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
#include <memory>
static XINPUT_STATE controller={};static volatile LONG last_player=0,last_group_count=0,last_pose=0,last_club=0,last_backdrop=0,last_group=-1,last_pose_id=0,last_coach_ready=0,last_coach_pose=0,last_room=0,last_room_pose=0;
static int last_requested_club=0;
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD index,XINPUT_STATE*out){if(index)return ERROR_DEVICE_NOT_CONNECTED;*out=controller;return ERROR_SUCCESS;}
extern "C" BOOL career_operations_get_transfer_context(CareerTransferUiContext*out){if(!out)return FALSE;*out={};out->club=1043;out->date=20261002;
    out->transfer_budget=184500000;out->wage_budget=63000000;out->first_window_end_mmdd=1231;out->second_window_end_mmdd=131;out->save_valid=out->window_ends_valid=1;return TRUE;}
extern "C" void clubs_browser_request_native_refresh(void){}
extern "C" void clubs_browser_request_catalog(void){}
extern "C" BOOL clubs_browser_open_team(int team){last_requested_club=team;return mod_screen_push_action("FifaModsOpenOtherClubs");}
static void log_line(const char*message){if(!strchr(message,'\n')&&strncmp(message,"Club3D asset:",13))puts(message);
    if(strstr(message,"Club3D: coach details ready")){InterlockedIncrement(&last_coach_ready);const char*p=strstr(message,"pose=");if(p)InterlockedExchange(&last_coach_pose,atoi(p+5));}
    int room=0;if(sscanf_s(message,"Club3D: room ready; room=%d",&room)==1){InterlockedExchange(&last_room,room);const char*p=strstr(message,"pose=");if(p)InterlockedExchange(&last_room_pose,atoi(p+5));}
    int id=0;if(sscanf_s(message,"Club3D: player=%d",&id)==1){
    InterlockedExchange(&last_player,id);const char*p=strstr(message,"players=");if(p&&strstr(message,"group=1"))InterlockedExchange(&last_group_count,atoi(p+8));
    p=strstr(message,"posed=");if(p)InterlockedExchange(&last_pose,atoi(p+6));
    p=strstr(message,"group=");if(p)InterlockedExchange(&last_group,atoi(p+6));
    p=strstr(message," pose=");if(p)InterlockedExchange(&last_pose_id,atoi(p+6));
    p=strstr(message,"team=");if(p)InterlockedExchange(&last_club,atoi(p+5));
    InterlockedExchange(&last_backdrop,strstr(message,"colors=1 crest=1")?1:0);}}
static void frame(ID3D11DeviceContext *c,ID3D11RenderTargetView*target) {
    mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();auto before=ImGui::GetStyle();mod_screen_draw();
    require(!memcmp(before.Colors,ImGui::GetStyle().Colors,sizeof(before.Colors)),"club/child screen restores shared theme");
    auto&io=ImGui::GetIO();auto*qa=ImGui::GetForegroundDrawList();qa->AddRectFilled({18,io.DisplaySize.y-29},{590,io.DisplaySize.y-8},IM_COL32(3,19,30,230));qa->AddText({24,io.DisplaySize.y-26},IM_COL32(245,248,252,255),"PRÉVIA OFFLINE | Recursos nativos FIFA 16 | Dados da base de teste");ImGui::Render();
    float bg[4]={.01f,.09f,.17f,1};c->OMSetRenderTargets(1,&target,nullptr);c->ClearRenderTargetView(target,bg);
    ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);
}
/* A real render comparison, not a composite/edit of saved screenshots. */
static void pose_gallery(ID3D11Device*d,ID3D11DeviceContext*c,ID3D11RenderTargetView*target,ID3D11ShaderResourceView*srv,
    const std::vector<std::shared_ptr<const Model>>&models,const std::vector<const PresentationPoseInfo*>&poses,const char*title,const char*file) {
    require(!models.empty()&&models.size()==poses.size(),"compatible native render gallery");
    const bool coach_sheet=std::all_of(poses.begin(),poses.end(),[](const auto*p){return (p->modes&PoseCoachAny)!=0;});
    size_t seated_count=std::count_if(poses.begin(),poses.end(),[](const auto*p){return (p->modes&PoseSeatedCoach)!=0;}),standing_count=poses.size()-seated_count;
    std::vector<std::unique_ptr<Renderer>>renders;
    for(size_t i=0;i<models.size();++i){bool seated=coach_sheet&&(poses[i]->modes&PoseSeatedCoach);
        float width=(1428.f-32)/(coach_sheet?(seated?seated_count:standing_count):models.size())-8,height=coach_sheet?(seated?250.f:350.f):650.f;
        auto r=std::make_unique<Renderer>();r->device(d);require(r->model(models[i])&&r->render((UINT)width,(UINT)height,0,1),"gallery uses same native model, shader and renderer");renders.push_back(std::move(r));}
    ImGui_ImplDX11_NewFrame();ImGui::NewFrame();ImGui::SetNextWindowPos(ImVec2(0,0));ImGui::SetNextWindowSize(ImVec2(1428,800));
    ImGui::Begin("Render gallery",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.4f);ImGui::TextUnformatted(title);ImGui::SetWindowFontScale(1);
    ImGui::TextUnformatted("Prévia nativa offline | RX3 do FIFA | Poses do mod | Sem Blender");
    for(size_t i=0;i<models.size();++i){
        bool seated=coach_sheet&&(poses[i]->modes&PoseSeatedCoach);
        float width=(1428.f-32)/(coach_sheet?(seated?seated_count:standing_count):models.size())-8,height=coach_sheet?(seated?250.f:350.f):650.f;
        size_t column=0;for(size_t p=0;p<i;++p)if(!coach_sheet||bool(poses[p]->modes&PoseSeatedCoach)==seated)++column;
        float x=16+column*(width+8),y=seated?475.f:75.f;
        ImGui::SetCursorPos(ImVec2(x,y));ImGui::Image((ImTextureID)(intptr_t)renders[i]->image(),ImVec2(width,height));
        ImGui::SetCursorPos(ImVec2(x,y+height+10));ImGui::PushTextWrapPos(x+width);ImGui::TextWrapped("%u - %s",poses[i]->id,poses[i]->name);ImGui::PopTextWrapPos();
    }
    ImGui::End();ImGui::Render();float bg[]={.02f,.07f,.10f,1};c->OMSetRenderTargets(1,&target,nullptr);c->ClearRenderTargetView(target,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());image(d,c,srv,file);
}
int main(int argc,char**argv) {
    require(argc==3||argc==4||(argc==5&&(!strcmp(argv[4],"--profile-only")||!strcmp(argv[4],"--hub-only")||!strcmp(argv[4],"--office-only")||!strcmp(argv[4],"--office-social-only")||!strcmp(argv[4],"--transfer-only"))),"usage: test_club_player_screen game_root output.bmp [offline-club-fixture.bin] [--profile-only|--hub-only|--office-only|--office-social-only|--transfer-only]");
    bool profile_only=(argc==4&&!strcmp(argv[3],"--profile-only"))||(argc==5&&!strcmp(argv[4],"--profile-only"));
    bool hub_only=(argc==4&&!strcmp(argv[3],"--hub-only"))||(argc==5&&!strcmp(argv[4],"--hub-only"));
    bool office_only=(argc==4&&!strcmp(argv[3],"--office-only"))||(argc==5&&!strcmp(argv[4],"--office-only"));
    bool office_social_only=(argc==4&&!strcmp(argv[3],"--office-social-only"))||(argc==5&&!strcmp(argv[4],"--office-social-only"));
    bool transfer_only=(argc==4&&!strcmp(argv[3],"--transfer-only"))||(argc==5&&!strcmp(argv[4],"--transfer-only"));
    bool competition_only=(argc==4&&!strcmp(argv[3],"--competition-only"))||(argc==5&&!strcmp(argv[4],"--competition-only"));
    bool office_test=office_only||office_social_only||competition_only;
    bool has_fixture=argc>=4&&strcmp(argv[3],"--profile-only")&&strcmp(argv[3],"--hub-only")&&strcmp(argv[3],"--office-only")&&strcmp(argv[3],"--office-social-only")&&strcmp(argv[3],"--transfer-only")&&strcmp(argv[3],"--competition-only");
    require(office_social::fan_lines().size()==11&&office_social::fan_lines()[0].size()==8&&office_social::desk_lines().size()==11&&office_social::desk_lines()[0].size()==4&&
        office_social::first_names().size()*office_social::last_names().size()==120,
        "social content corpus has 88 fan lines, 44 fictional newsroom lines and 120 generated fan identities");
    std::vector<ClubPlayerRow>squad_summary_rows(36);int summary_id=1,cursor=0;
    const int summary_positions[4]={0,1,9,23},summary_counts[4]={4,11,9,11};
    for(int group=0;group<4;++group)for(int n=0;n<summary_counts[group];++n){auto&r=squad_summary_rows[cursor++];r.player_id=summary_id++;r.position=summary_positions[group];r.age=26;r.overall=73;}
    squad_summary_rows[35]=squad_summary_rows[0];
    auto squad_test=club_office_test_squad_summary(squad_summary_rows.data(),squad_summary_rows.size());
    require(squad_test.players==35&&squad_test.average_age==26&&squad_test.average_overall==73&&squad_test.goalkeepers==4&&
        squad_test.defenders==11&&squad_test.midfielders==9&&squad_test.attackers==11,
        "office roster card derives player total, rounded age/overall averages and FIFA position groups without double-counting IDs");
    office_social::Signals social_test={};social_test.club=1043;social_test.competition=7;social_test.table_valid=true;social_test.rank=1;social_test.teams=20;
    social_test.played=10;social_test.wins=8;social_test.draws=1;social_test.losses=1;social_test.goals_for=25;social_test.goals_against=7;
    social_test.league_strength=80;social_test.average_overall=78;social_test.club_name="Flamengo";social_test.league_name="Brasileirão Betano";
    social_test.cup_state=1;social_test.coach_recent_valid=true;social_test.coach_recent_games=5;social_test.coach_recent_points=13;social_test.coach_name="Técnico do Save";
    for(int i=0;i<18;++i)social_test.players.push_back({2000+i,"Atleta social "+std::to_string(i+1)});
    social_test.last_valid=1;social_test.last_home=1;social_test.last_goals_for=2;social_test.last_goals_against=1;social_test.last_opponent="Palmeiras";
    social_test.next_valid=1;social_test.next_home=1;social_test.next_opponent="São Paulo";social_test.next_date=20260117;social_test.next_rivalry=78;social_test.next_opponent_rank=4;
    social_test.recent_games=5;social_test.recent_wins=3;social_test.recent_draws=1;social_test.recent_losses=1;social_test.recent_goals_for=9;social_test.recent_goals_against=5;
    social_test.table_points=25;social_test.table_leader_points=27;social_test.goals_leader_valid=1;social_test.goals_leader_goals=9;social_test.goals_leader_name="Atleta social 1";
    social_test.assists_leader_valid=1;social_test.assists_leader_assists=6;social_test.assists_leader_name="Atleta social 2";
    social_test.form[0]=social_test.form[1]=social_test.form[2]=1;social_test.form[3]=0;social_test.form[4]=1;
    office_social::Runtime social_runtime;social_runtime.update(social_test);int supporters=0,media=0,players=0,club=0;bool unique=true;
    for(size_t i=0;i<social_runtime.posts.size();++i){const auto&p=social_runtime.posts[i];supporters+=p.source==office_social::Supporter;media+=p.source==office_social::Press;
        players+=p.source==office_social::PlayerVoice;club+=p.source==office_social::ClubVoice;if(p.text.empty()||p.text.find('$')!=std::string::npos)unique=false;
        for(size_t j=0;j<i;++j)if(p.identity==social_runtime.posts[j].identity)unique=false;}
    require(unique&&supporters==1&&media==1&&players==2&&club==1,"feed generates five distinct posts with player, club, supporter and media voices");
    bool result_detail=false,fixture_detail=false,player_detail=false;
    for(const auto&p:social_runtime.posts){if(p.source==office_social::Press&&p.text.find("Palmeiras")!=std::string::npos&&p.text.find("2 x 1")!=std::string::npos)result_detail=true;
        if(p.text.find("São Paulo")!=std::string::npos&&p.text.find("17/01/2026")!=std::string::npos)fixture_detail=true;
        if(p.source==office_social::PlayerVoice&&(p.text.find("9 gols")!=std::string::npos||p.text.find("6 assistências")!=std::string::npos))player_detail=true;}
    require(result_detail&&fixture_detail&&player_detail,"story posts use the exact last score, next opponent/date and verified squad leaders instead of generic filler");
    office_social::Signals result_story={};result_story.club=1043;result_story.club_name="Flamengo";result_story.last_valid=1;result_story.last_home=1;
    result_story.last_goals_for=2;result_story.last_goals_against=1;result_story.last_opponent="Palmeiras";result_story.table_valid=true;result_story.rank=3;result_story.played=8;
    office_social::Runtime result_runtime;result_runtime.update(result_story);bool supporter_score=false,press_score=false,club_score=false;
    for(const auto&p:result_runtime.posts){if(p.text.find("Palmeiras")!=std::string::npos&&p.text.find("2 x 1")!=std::string::npos){supporter_score|=p.source==office_social::Supporter;press_score|=p.source==office_social::Press;club_score|=p.source==office_social::ClubVoice;}}
    require(supporter_score&&press_score&&club_score,"supporter, newsroom and official-club voices each react to the same exact result in distinct formats");
    social_test.played=11;social_runtime.update(social_test);social_test.played=12;social_runtime.update(social_test);
    require(social_runtime.leader_rounds==3,"leadership streak advances only when a new league match appears");
    auto popular=office_social::followers(social_test);social_test.rank=20;
    require(office_social::followers(social_test)<popular,"estimated followers respond to a verified table-position change");
    ClubPlayerRow probe={};int spots[4];
    int birth95=(int)(club_profile::civil_days(1995,1,10)-club_profile::civil_days(1582,10,14));
    require(club_profile::age_at(birth95,20260109)==30&&club_profile::age_at(birth95,20260110)==31,"age changes on birthday, using career date and FIFA Gregorian epoch");
    int leap=(int)(club_profile::civil_days(2000,2,29)-club_profile::civil_days(1582,10,14));
    require(club_profile::age_at(leap,20240228)==23&&club_profile::age_at(leap,20240229)==24,"leap birthdays follow native date semantics");
    require(club_profile::age_at(birth95,20260230)==-1&&club_profile::age_at(-1,20260110)==-1&&club_profile::age_at(birth95,0)==-1,"missing or corrupt date is never replaced by PC date");
    player_profile_publish_career_date(20260110); /* Explicit offline career date, not a game-memory write. */
    probe.position=18;
    require(club_profile::positions(probe,spots)==1&&spots[0]==18,"old/absent secondary source cannot add zero-filled goalkeeper positions");
    probe.secondary_positions_valid=1;probe.secondary_positions[0]=14;probe.secondary_positions[1]=18;probe.secondary_positions[2]=31;
    require(club_profile::positions(probe,spots)==2&&spots[0]==18&&spots[1]==14,"preferred positions deduplicate, reject FIFA sentinel 31 and retain primary order");
    probe.secondary_positions[0]=0;probe.secondary_positions[1]=-1;probe.secondary_positions[2]=27;
    require(club_profile::positions(probe,spots)==3,"explicit preferred GOL zero is not confused with missing or negative positions");
    probe.position=-1;probe.secondary_positions_valid=0;require(!club_profile::positions(probe,spots),"unknown position never becomes an invented pitch marker");
    for(int p=0;p<28;++p){auto point=club_profile::pitch_point(p);require(point.x>0&&point.x<1&&point.y>0&&point.y<1,"all 28 native position codes fit pitch");}
    for(int&i:probe.attributes)i=-1;require(club_profile::summary(probe,0)==-1,"unknown summary stays absent rather than fake zero");
    for(int&i:probe.attributes)i=81;probe.attributes[0]=50;probe.attributes[1]=70;
    require(club_profile::summary(probe,0)==60&&club_profile::summary(probe,5)==81,"category summary uses only documented members, not trailing zero indices");
    probe.position=0;probe.attributes[28]=73;require(club_profile::summary(probe,0)==73,"keeper summary uses actual keeper attributes instead of outfield averages");
    probe.club_colors_valid=1;probe.club_colors[0]=0xffffff;probe.club_colors[1]=0x111111;probe.club_colors[2]=0xeeaacb;
    require(club_profile::theme_color(probe)==0xeeaacb,"white primary kits use actual coloured identity, not hard-coded club theme");
    ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;
    require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)),"WARP UI");
    D3D11_TEXTURE2D_DESC desc={};desc.Width=1428;desc.Height=800;desc.MipLevels=desc.ArraySize=1;
    desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;
    ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*target=nullptr;ID3D11ShaderResourceView*srv=nullptr;
    require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"UI target");d->CreateRenderTargetView(t,nullptr,&target);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();
    ImGui::CreateContext();ImGuiIO&io=ImGui::GetIO();io.DisplaySize=ImVec2(1428,800);io.DeltaTime=1.f/60;
    io.IniFilename=nullptr;char windows_dir[MAX_PATH],bold_font_path[MAX_PATH];
    UINT path_length=GetWindowsDirectoryA(windows_dir,(UINT)sizeof(windows_dir));
    ImFont*number_font=nullptr;
    if(path_length&&path_length<sizeof(windows_dir)){
        _snprintf_s(bold_font_path,sizeof(bold_font_path),_TRUNCATE,"%s\\Fonts\\segoeuib.ttf",windows_dir);
        io.Fonts->AddFontFromFileTTF(bold_font_path,16);
        static const ImWchar number_glyph_ranges[]={0x0020,0x0039,0};
        number_font=io.Fonts->AddFontFromFileTTF(bold_font_path,56,nullptr,number_glyph_ranges);
    }
    require(number_font!=nullptr,"high-resolution bold shirt-number font loads before atlas build");
    club_player_screen_set_number_font(number_font);
    ImGui::StyleColorsDark();require(ImGui_ImplDX11_Init(d,c),"ImGui renderer");
    require(club_player_screen_register(argv[1],log_line),"register Club action");club_player_screen_set_device(d);
    require(mod_screen_has_action(FIFA16_FULL_SQUAD_ACTION),"register dedicated full-squad photo action");
    require(coach_profile_register(argv[1],log_line),"register generic coach child");coach_profile_device(d);
    std::vector<ClubPlayerRow> rows(11);rows[0].player_id=158023;rows[0].team_id=112893;rows[0].height=170;rows[0].weight=72;
    rows[0].skin_tone=3;rows[0].shoe_type=15;rows[0].overall=90;rows[0].position=24;rows[0].age=39;
    rows[0].number=15; /* Exercise the profile's club-colored upper-left shirt number. */
    rows[0].club_colors_valid=1;rows[0].club_colors[0]=0xf7b5cd;rows[0].club_colors[1]=0x18181b;rows[0].club_colors[2]=0xeeeeee;
    rows[0].captain=1;
    strcpy_s(rows[0].name,"Messi - teste de interface");for(int&i:rows[0].attributes)i=80;
    const int ids[11]={158023,20801,190871,176580,177003,189511,194765,212616,224458,241651,167495};
    for(int i=1;i<11;++i){rows[i]=rows[0];rows[i].player_id=ids[i];rows[i].height=158+i*5;
        rows[i].captain=0;
        rows[i].sock_length=i%3;rows[i].jersey_style=i%2;rows[i].jersey_fit=i%2;rows[i].sleeve_length=i%5;
        rows[i].shoe_type=i%3==0?1:i%3==1?10:15;
        sprintf_s(rows[i].name,"Atleta %d (ID %d) - teste",i+1,ids[i]);}
    rows[10].position=0;rows[10].glove_type=1;rows[10].height=193;
    strcpy_s(rows[10].name,"Goleiro (ID 167495) - teste");
    for(int i=0;i<10;++i)rows[i].squad_position=i+3;rows[10].squad_position=0;
    std::rotate(rows.begin(),rows.end()-1,rows.end()); /* Match provider's tactical ordering. */
    int initial_club=112893;char club_name[128]="Equipe de teste - atributos de interface";
    if(has_fixture) {
        FILE*f=nullptr;require(!fopen_s(&f,argv[3],"rb")&&f,"open explicit offline club fixture");
        char magic[8];uint32_t count=0,club=0,row_size=0;
        require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&
            fread(&club,4,1,f)==1&&fread(&row_size,4,1,f)==1&&count>=11&&count<=512&&row_size==sizeof(ClubPlayerRow),"bounded compatible fixture header");
        rows.resize(count);
        require(fread(club_name,1,128,f)==128&&fread(rows.data(),sizeof(ClubPlayerRow),count,f)==count&&fgetc(f)==EOF,"exact-size full-roster fixture");
        fclose(f);club_name[127]=0;initial_club=(int)club;
        // Fixture provenance belongs outside the game interface, in the QA footer.
        if(char*description=strstr(club_name," - escalação da base offline"))*description=0;
        for(const auto&r:rows)require(r.team_id==initial_club&&r.player_id>0,"all fixture players belong to requested club");
    } else if(office_test||transfer_only) {
        initial_club=1043;strcpy_s(club_name,"Flamengo - prévia offline");
        for(auto&r:rows){r.team_id=initial_club;r.club_colors_valid=1;r.club_colors[0]=0xb60019;r.club_colors[1]=0x151515;r.club_colors[2]=0xffffff;}
    }
    {fifa_player::Assets identity_assets(argv[1]);fifa_player::Texture flag;
        fifa_player::Texture movement_up,movement_down;
        require(identity_assets.competition_movement_icon(true,movement_up)&&identity_assets.competition_movement_icon(false,movement_down),
            "league table loads the exact FIFA green-up and red-down sprites from data_front_end.big");
        int nation=identity_assets.nationality(rows[0].player_id);
        printf("Native identity player=%d nationality=%d\n",rows[0].player_id,nation);
        require(identity_assets.player_age(rows[0].player_id)>=15&&identity_assets.player_age(rows[0].player_id)<=100,"installed native birthdate fills an absent offline row age");
        require(identity_assets.preferred_foot(158023)==2&&identity_assets.preferred_foot(20801)==1,"FIFA enum and range-low decode: Messi left, Cristiano right");
        std::string league_name;int league=identity_assets.league(initial_club,league_name);fifa_player::Texture league_icon;
        printf("Native club=%d league=%d name=%s\n",initial_club,league,league_name.c_str());
        require(league>0&&!league_name.empty(),"native club league relation owns its exact division name, not its cup name");
        float strength=identity_assets.league_strength(initial_club);printf("League strength=%.2f, player reputation=%.2f\n",strength,profile_reputation::player(strength,80));
        require(strength>=0&&strength<=100,"native league tier and all member clubs provide reputation input");
        require(profile_reputation::player(strength,90)>profile_reputation::player(strength,70),"same league, higher current OVR raises player reputation");
        if(initial_club==1043){require(identity_assets.competition_icon(league,league_icon),"installed Flamengo division has its exact native logo");
            fifa_player::Texture cup_icon;require(identity_assets.trophy_icon(1003,cup_icon),"installed Libertadores has its exact native trophy icon");}
        if(initial_club==112893)require(league==39&&league_name!="MLS Cup","league name is never substituted by the related trophy name; missing logo may stay hidden");
        player_profile_publish_league(199999,13,"Premier League");require(identity_assets.league(199999,league_name)==13&&league_name=="Premier League","live league publication overrides installed division");
        player_profile_publish_league(199999,0,"");require(identity_assets.league(199999,league_name)==0&&league_name.empty(),"ambiguous live league hides stale base relation");
        player_profile_publish_league(199999,league,league_name.c_str());player_profile_publish_league_strength(199999,league,42);
        require(identity_assets.league_strength(199999)==42,"live league strength overrides offline club membership");
        player_profile_publish_league_strength(199999,league,-1);require(identity_assets.league_strength(199999)<0,"missing live strength never reuses offline reputation");
        require(nation>0&&nation<=3000&&identity_assets.nationality_flag(nation,flag),"exact nationality flag comes from native player ID, not club nationality");
        require(!identity_assets.nationality_flag(3001,flag)&&!identity_assets.nationality(524288),"invalid nationality/player never reuse another flag");
        player_profile_publish_nationality(524287,49);require(identity_assets.nationality(524287)==49,"owned live nationality sidecar includes players absent from base DB");
        player_profile_publish_nationality(524287,0);require(identity_assets.nationality(524287)==0,"explicit missing live nationality never invents a fallback");}
    club_player_screen_publish(rows.data(),rows.size(),initial_club,club_name);
    if(transfer_only){require(transfer_center_screen_register(argv[1]),"register transfer center for isolated screen preview");
        transfer_center_screen_device(d);transfer_center_screen_publish_roster(rows.data(),rows.size(),initial_club,club_name);
        ClubBrowserRow test_league={};test_league.team=initial_club;test_league.league=7;strcpy_s(test_league.league_name,"Brasileirão Betano");
        transfer_center_screen_publish_league_catalog(&test_league,1,initial_club);}
    if(hub_only||office_test){CoachProfileContext coach={};coach.valid=1;coach.kind=COACH_CAREER_USER;coach.id=0;coach.club=initial_club;coach.nationality=38;
        coach.confidence=86;coach.reputation=920;coach.wage=-1;strcpy_s(coach.name,"Leonardo Jardim");strcpy_s(coach.club_name,club_name);
        if(office_test)strcpy_s(coach.name,"Treinador criado na carreira");
        coach.colors_valid=rows[0].club_colors_valid;memcpy(coach.colors,rows[0].club_colors,sizeof(coach.colors));coach_profile_publish_career(&coach,nullptr,0);
        if(office_test){CareerNewsManagerFacts manager={};manager.club_id=initial_club;manager.valid=1;manager.confidence=72;manager.reputation=1100;manager.season_record_valid=1;
            manager.games=20;manager.wins=12;manager.draws=4;manager.losses=4;manager.goals_for=35;manager.goals_against=20;strcpy_s(manager.name,"Treinador criado na carreira");career_news_publish_manager(&manager);
            CareerNewsFacts news={};news.club_id=initial_club;news.calendar_date=20260110;news.last_valid=1;news.last_date=20260108;news.last_home=1;news.last_goals_for=2;news.last_goals_against=1;
            strcpy_s(news.last_opponent_name,"Botafogo");news.recent_games=5;news.recent_wins=3;news.recent_draws=1;news.recent_losses=1;news.recent_goals_for=9;news.recent_goals_against=5;news.recent_points=10;
            news.table_valid=1;news.table_rank=1;news.table_count=20;news.table_played=20;news.table_points=43;news.table_leader_points=43;
            news.next_valid=1;news.next_date=20260112;news.next_home=0;news.next_opponent_rank=4;news.next_rivalry=74;strcpy_s(news.next_opponent_name,"Fluminense");
            news.goals_leader_valid=1;news.goals_leader_goals=9;strcpy_s(news.goals_leader_name,"Pedro");news.assists_leader_valid=1;news.assists_leader_assists=6;strcpy_s(news.assists_leader_name,"Arrascaeta");
            career_news_publish_facts(&news);}}
    const auto gallery_rows=rows;
    require(mod_screen_open_action(transfer_only?FIFA_TRANSFER_MARKET_ACTION:office_test?FIFA16_MY_OFFICE_ACTION:hub_only?FIFA16_CLUB_PLAYER_ACTION:FIFA16_CLUB_SQUAD_ACTION),"open exclusively through registered native marker");
    mod_screen_sync_lifecycle();if(transfer_only){require(mod_screen_is_active("transfer-market"),"open the market directly without depending on office rendering");
        Sleep(800);for(int i=0;i<12;++i)frame(c,target);image(d,c,srv,argv[2]);
        require(mod_screen_push_action(FIFA_TRANSFER_LEAGUES_ACTION)&&mod_screen_is_active("transfer-leagues"),"market exposes the leagues page through its transfer route");
        Sleep(800);for(int i=0;i<4;++i)frame(c,target);image(d,c,srv,"transfer-leagues-screen.bmp");
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad={};frame(c,target);
        require(mod_screen_is_active("transfer-league-detail"),"controller opens the selected league market detail");
        frame(c,target);image(d,c,srv,"transfer-league-detail-screen.bmp");controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
        require(mod_screen_is_active("transfer-leagues"),"league detail Back returns to the league list");controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
        transfer_center_screen_device(nullptr);mod_screen_close();mod_screen_sync_lifecycle();club_player_screen_set_device(nullptr);coach_profile_device(nullptr);
        ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
        puts("PASS: transfer dashboard and league flow render; no simulated transfer records");return 0;}
    require(club_player_screen_take_refresh_request()&&!club_player_screen_take_refresh_request(),"Clube open requests exactly one fresh provider capture");
    for(int i=0;i<300 && last_group_count!=11;++i)frame(c,target);
    require(last_group_count==11,"eleven simultaneous real RX3 models");frame(c,target);frame(c,target);image(d,c,srv,argv[2]);
    require(last_pose==1,"all eleven deform the native skeleton, including thermal kit and gloves");
    require(last_club==initial_club&&last_backdrop==1,"current club crest and colours reach the rendered scene");
    if(office_test){
        office_social::Signals transfer_fixture={};transfer_fixture.club=1043;transfer_fixture.club_name="Flamengo";transfer_fixture.played=12;transfer_fixture.wins=7;
        transfer_fixture.draws=2;transfer_fixture.table_valid=true;transfer_fixture.rank=2;transfer_fixture.teams=20;
        for(int i=0;i<18;++i)transfer_fixture.players.push_back({1000+i,"Atleta de teste "+std::to_string(i+1)});
        office_social::Runtime transfer_runtime;transfer_runtime.update(transfer_fixture);
        require(transfer_runtime.posts[0].source==office_social::PlayerVoice||transfer_runtime.posts[1].source==office_social::PlayerVoice,
            "simulated social feed contains own-roster voices before transfer events");
        transfer_fixture.players.push_back({1999,"Novo Reforço"});transfer_runtime.update(transfer_fixture);require(transfer_runtime.movement_type==0,"a one-frame partial roster change is not called a transfer");
        transfer_runtime.update(transfer_fixture);
        require(transfer_runtime.movement_type==1&&transfer_runtime.movement_in=="Novo Reforço","a single new roster member triggers an arrival story");
        require(std::any_of(transfer_runtime.posts.begin(),transfer_runtime.posts.end(),[](const auto&p){return p.text.find("Novo Reforço")!=std::string::npos;}),
            "arrival reactions resolve the real roster name without an invented fee or destination");
        transfer_fixture.players.pop_back();transfer_runtime.update(transfer_fixture);require(transfer_runtime.movement_type==1,"departure is not announced on the first changed roster snapshot");
        transfer_runtime.update(transfer_fixture);
        require(transfer_runtime.movement_type==2&&transfer_runtime.movement_out=="Novo Reforço"&&
            std::any_of(transfer_runtime.posts.begin(),transfer_runtime.posts.end(),[](const auto&p){return p.text.find("Novo Reforço")!=std::string::npos;}),
            "a single removed roster member triggers departure reactions with the player's name");
        // The competitions route gets a deterministic offline snapshot so the
        // standings table and its group carousel are rendered in this QA pass.
        const ModOverlayScreen ranking={"ranking","FifaModsOpenRanking",nullptr,[](void*){},nullptr,nullptr,nullptr};
        const ModOverlayScreen browser={"other-clubs","FifaModsOpenOtherClubs",nullptr,[](void*){},nullptr,nullptr,nullptr};
        const ModOverlayScreen leagues={"other-leagues","FifaModsOpenLeagues",nullptr,[](void*){},nullptr,nullptr,nullptr};
        const ModOverlayScreen trophies={"trophy-room","FifaModsOpenTrophyRoom",nullptr,[](void*){},nullptr,nullptr,nullptr};
        const ModOverlayScreen loans={"loans","FifaModsOpenLoans",nullptr,[](void*){},nullptr,nullptr,nullptr};
        auto demo_storage=std::make_unique<ClubCompetitionsSnapshot>();auto&demo=*demo_storage;demo.club=initial_club;demo.date=20261002;demo.count=3;auto&entry=demo.entries[0];
        entry.competition=1003;entry.asset=1003;entry.trophy_asset=1003;entry.current_stage=501;entry.current_stage_kind=2;entry.is_cup=1;entry.has_group_phase=1;entry.preferred_group=0;entry.group_count=2;
        entry.previous={1,502,1,initial_club,100,20260420,2100,1,1,0};entry.next={1,502,2,100,initial_club,20260427,2100,0,0,0};
        entry.aggregate_visible=1;entry.aggregate_for=1;entry.aggregate_against=0;
        auto set_group=[&](ClubCompetitionGroup&group,int index,bool current_group){group.stage=501+index;group.current=current_group?1:0;group.row_count=4;group.classification_count=2;
            const int teams[2][4]={{initial_club,77,88,99},{100,101,102,103}};
            const char*names[2][4]={{"Flamengo","Palmeiras","Bahia","Cruzeiro"},{"Santos","Corinthians","São Paulo","Grêmio"}};
            for(int row=0;row<4;++row){auto&r=group.rows[row];r.team=teams[index][row];r.rank=row+1;r.played=4-row/3;r.won=3-row;r.drawn=row==2?1:0;r.lost=r.played-r.won-r.drawn;
                r.goals_for=8-row*2;r.goals_against=2+row*2;r.points=r.won*3+r.drawn;r.status=r.team==initial_club?2:row<2?1:-1;
                r.zone=row<2?CLUB_COMPETITION_ZONE_ADVANCE:CLUB_COMPETITION_ZONE_OUTSIDE;r.last_match_valid=1;r.last_match_result=row==0?1:row==1?0:-1;
                r.last_goals_for=row==0?2:row==1?1:0;r.last_goals_against=row==0?1:row==1?1:2;strcpy_s(r.name,names[index][row]);
                for(int form=0;form<CLUB_COMPETITION_FORM_SIZE;++form)r.form[form]=form<4-row?1:form==4-row?0:2;}};
        set_group(entry.groups[0],0,true);set_group(entry.groups[1],1,false);
        auto add_bracket_team=[&](int id,const char*name){auto&t=entry.bracket_teams[entry.bracket_team_count++];t.id=id;strcpy_s(t.name,name);};
        add_bracket_team(initial_club,"Flamengo");add_bracket_team(77,"Palmeiras");add_bracket_team(88,"Bahia");add_bracket_team(99,"Cruzeiro");
        add_bracket_team(100,"Santos");add_bracket_team(101,"Corinthians");add_bracket_team(102,"São Paulo");add_bracket_team(103,"Grêmio");
        auto add_bracket_tie=[&](int stage,int kind,int round,int a,int b,int ida_a,int ida_b,int volta_b,int volta_a){
            auto&t=entry.bracket_ties[entry.bracket_tie_count++];t.stage=stage;t.stage_kind=kind;t.round=round;t.team_a=a;t.team_b=b;t.leg_count=2;
            t.legs[0]={1,stage,round,a,b,20260701,2100,1,ida_a,ida_b,stage*100+round};
            t.legs[1]={1,stage,round+1,b,a,20260708,2100,1,volta_b,volta_a,stage*100+round+1};};
        add_bracket_tie(610,6,1,initial_club,77,2,0,1,1);add_bracket_tie(610,6,1,88,99,0,0,1,0);
        add_bracket_tie(610,6,1,100,101,1,1,0,1);add_bracket_tie(610,6,1,102,103,0,2,1,1);
        add_bracket_tie(611,7,2,initial_club,88,1,0,0,1);add_bracket_tie(611,7,2,100,102,2,1,1,0);
        add_bracket_tie(612,8,3,initial_club,100,1,1,0,2);add_bracket_tie(613,10,4,initial_club,77,2,1,0,0);
        entry.bracket_ties[entry.bracket_tie_count-1].leg_count=1;
        auto&league=demo.entries[1];league.competition=13;league.asset=13;league.current_stage=601;league.table_available=1;league.table_count=4;
        const int league_teams[4]={initial_club,77,88,99};const char*league_names[4]={"Flamengo","Palmeiras","Bahia","Cruzeiro"};
        for(int row=0;row<4;++row){auto&r=league.table[row];r.team=league_teams[row];r.rank=row+1;r.played=8;r.won=5-row;r.drawn=row==1?2:1;r.lost=r.played-r.won-r.drawn;
            r.goals_for=15-row*3;r.goals_against=7+row*2;r.points=r.won*3+r.drawn;r.movement=row==0?1:row==1?-1:row==2?0:CLUB_COMPETITION_MOVEMENT_UNKNOWN;
            r.zone=row==0?CLUB_COMPETITION_ZONE_PRIMARY:row==1?CLUB_COMPETITION_ZONE_SECONDARY:row==2?CLUB_COMPETITION_ZONE_SAFE:CLUB_COMPETITION_ZONE_RELEGATION;
            r.last_match_valid=1;r.last_match_result=row==0?1:row==1?-1:row==2?0:1;r.last_goals_for=row==1?1:2;r.last_goals_against=row==0?1:row==1?2:row==2?2:0;strcpy_s(r.name,league_names[row]);
            for(int form=0;form<CLUB_COMPETITION_FORM_SIZE;++form)r.form[form]=form<3?1:form==3?0:-1;}
        require(league.table[0].movement==1&&league.table[1].movement==-1&&league.table[2].movement==0&&
            league.table[3].movement==CLUB_COMPETITION_MOVEMENT_UNKNOWN,"league snapshot distinguishes up, down, stable and unavailable movement");
        auto&advanced=demo.entries[2];advanced.competition=2003;advanced.current_stage=701;advanced.current_stage_kind=3;advanced.is_cup=1;advanced.has_group_phase=1;advanced.group_count=1;
        advanced.groups[0].classification_count=2;advanced.groups[0].row_count=4;
        for(int row=0;row<4;++row){auto&r=advanced.groups[0].rows[row];r.team=league_teams[row];r.rank=row+1;r.played=6;r.name[0]=0;strcpy_s(r.name,league_names[row]);}
        club_competitions_publish(&demo);ClubCompetitionSocialSnapshot social_snapshot={};
        require(club_competitions_social_read(initial_club,&social_snapshot)&&social_snapshot.rank==1&&social_snapshot.played==8&&social_snapshot.goals_for==15,
            "office social engine reads only the exact current club row from the published league table");
        require(social_snapshot.cup_state==1&&social_snapshot.cup_competition==2003,"group completion beyond the group stage confirms advancement from exact saved standings");
        demo.entries[2].groups[0].rows[0].rank=3;club_competitions_publish(&demo);
        require(club_competitions_social_read(initial_club,&social_snapshot)&&social_snapshot.cup_state==-1,"completed group standings outside qualification places confirm elimination");
        demo.entries[2].groups[0].rows[0].rank=1;club_competitions_publish(&demo);
        if(competition_only){mod_screen_close();mod_screen_sync_lifecycle();
            require(club_competitions_screen_register(argv[1],log_line),"direct competition screen registers for visual QA");club_competitions_screen_device(d);
            require(mod_screen_open_action(FIFA16_CLUB_COMPETITIONS_ACTION),"directly open the native competition screen");mod_screen_sync_lifecycle();Sleep(650);
            for(int i=0;i<24;++i)frame(c,target);std::string folder=argv[2];folder=folder.substr(0,folder.find_last_of("/\\")+1);
            image(d,c,srv,(folder+"club-competitions-group-final.bmp").c_str());
            auto click_competition=[&](float x,float y){io.AddMousePosEvent(x,y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);};
            click_competition(150,155);for(int i=0;i<24;++i)frame(c,target);image(d,c,srv,(folder+"club-competitions-league-final.bmp").c_str());
            require(mod_screen_is_active("club-competitions")&&mod_screen_captures_input(),"league table remains in the same native modal after selecting its row");
            puts("PASS: competition screen native arrows, table, club badges, form icons and bottom legends");return 0;}
        require(mod_screen_register(&ranking)&&mod_screen_register(&browser)&&mod_screen_register(&leagues)&&mod_screen_register(&trophies)&&mod_screen_register(&loans)&&
            transfer_center_screen_register(argv[1]),"office destination routes register independently");
        transfer_center_screen_device(d);transfer_center_screen_publish_roster(rows.data(),rows.size(),initial_club,club_name);
        require(club_competitions_screen_register(argv[1],log_line),"real club competitions screen registers for offline visual QA");club_competitions_screen_device(d);
        auto button=[&](WORD b){controller.Gamepad.wButtons=b;frame(c,target);controller.Gamepad={};frame(c,target);};
        auto key=[&](ImGuiKey k){io.AddKeyEvent(k,true);frame(c,target);io.AddKeyEvent(k,false);frame(c,target);};
        auto click=[&](float x,float y){io.AddMousePosEvent(x,y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);};
        auto resize=[&](UINT w,UINT h){c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();target->Release();desc.Width=w;desc.Height=h;ID3D11Texture2D*texture=nullptr;
            require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&texture))&&SUCCEEDED(d->CreateRenderTargetView(texture,nullptr,&target))&&SUCCEEDED(d->CreateShaderResourceView(texture,nullptr,&srv)),"office resolution target");texture->Release();io.DisplaySize={(float)w,(float)h};};
        require(club_office_test_view().active&&club_office_test_view().coach_scene,"office has native arrival coach and exact XI");
        require(club_office_test_view().social_posts==5&&club_office_test_view().followers>0&&club_office_test_view().social_table,
            "office social card has five save-aware posts and a deterministic follower estimate");
        int player_posts=club_office_test_social_source_count(office_social::PlayerVoice),club_posts=club_office_test_social_source_count(office_social::ClubVoice),
            supporter_posts=club_office_test_social_source_count(office_social::Supporter),press_posts=club_office_test_social_source_count(office_social::Press);
        require(player_posts==2&&club_posts==1&&supporter_posts==1&&press_posts==1,
            "social carousel prioritizes two own-player voices alongside club, supporters and fictional press");
        require(club_player_screen_test_view().card_coach_model,"coach detail card keeps the club model even when the career-manager name differs");
        float x,y;require(club_office_test_center(10,x,y),"right-hand roster summary card exposes a focus target");
        frame(c,target);image(d,c,srv,"my-office.bmp");resize(1280,720);frame(c,target);image(d,c,srv,"my-office-720p.bmp");resize(1920,1080);frame(c,target);image(d,c,srv,"my-office-1080p.bmp");resize(1428,800);frame(c,target);Sleep(270);
        button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().focus==8,"down reaches the social card from the coach column");
        int social_before=club_office_test_view().social_index;button(XINPUT_GAMEPAD_DPAD_RIGHT);
        require(club_office_test_view().social_index==(social_before+1)%5,"controller left/right selects a social dot directly");button(XINPUT_GAMEPAD_DPAD_LEFT);
        require(club_office_test_view().social_index==social_before,"controller can return to the preceding social dot");button(XINPUT_GAMEPAD_RIGHT_SHOULDER);
        require(club_office_test_view().social_index==(social_before+1)%5,"LB/RB navigates the five-post social carousel when focused");
        button(XINPUT_GAMEPAD_A);require(club_office_test_view().social_index==(social_before+1)%5,"A keeps the currently selected social post in view");
        require(club_office_test_center(8,x,y),"social card has a keyboard and mouse focus target");io.AddMousePosEvent(x,y);frame(c,target);
        require(club_office_test_view().focus==8,"mouse hover gives the entire social card visible keyboard focus");
        image(d,c,srv,"my-office-social-focused.bmp");
        require(club_office_test_social_next_center(x,y),"social carousel arrow target is exposed to mouse input");click(x,y);
        require(club_office_test_view().social_index==(social_before+2)%5,"mouse arrow advances only the social carousel");
        require(club_office_test_social_dot_center(1,x,y),"five social dots expose mouse targets");click(x,y);
        require(club_office_test_view().social_index==1,"mouse dot selects its matching social post");
        auto manager_view=club_office_test_view();require(manager_view.manager_valid&&manager_view.manager_games==20&&manager_view.manager_wins==12&&manager_view.manager_draws==4&&
            manager_view.manager_losses==4&&manager_view.manager_confidence==72&&manager_view.manager_reputation==1100,
            "manager card consumes the save's current-season record, board confidence and native reputation");
        button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().focus==9,"down reaches the manager performance card below the center column");
        require(club_office_test_center(9,x,y),"manager performance card exposes controller/mouse focus bounds");click(x,y);
        require(club_office_test_view().focus==9,"mouse focus highlights the entire manager performance card");image(d,c,srv,"my-office-manager-focused.bmp");
        button(XINPUT_GAMEPAD_DPAD_UP);require(club_office_test_view().focus==7,"up from manager performance returns to the central card");
        button(XINPUT_GAMEPAD_DPAD_LEFT);require(club_office_test_view().focus==6,"left reaches the coach card");
        button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().focus==8,"down reaches the followers card");
        button(XINPUT_GAMEPAD_DPAD_UP);button(XINPUT_GAMEPAD_DPAD_UP);require(club_office_test_view().focus==0,"up returns from lower office cards to the office header");Sleep(270);
        button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_RIGHT);button(XINPUT_GAMEPAD_DPAD_RIGHT);
        require(club_office_test_view().focus==10,"controller traverses from the coach and XI to the roster summary card");button(XINPUT_GAMEPAD_A);
        require(!club_office_test_view().active&&club_player_screen_test_view().group,"A on the roster summary opens the same full roster screen");Sleep(270);
        button(XINPUT_GAMEPAD_B);require(club_office_test_view().active,"controller-opened roster Back restores office");
        require(club_office_test_center(10,x,y),"roster summary card is available to mouse input");io.AddMousePosEvent(x,y);frame(c,target);
        image(d,c,srv,"my-office-roster-focused.bmp");click(x,y);
        require(!club_office_test_view().active&&club_player_screen_test_view().group,"mouse click opens the full roster screen");Sleep(270);
        button(XINPUT_GAMEPAD_B);require(club_office_test_view().active,"mouse-opened roster Back restores office");
        if(office_social_only){puts("PASS: office summary metrics, roster-card focus, controller/mouse roster routing and social carousel");return 0;}
        auto before=club_player_screen_test_view();controller.Gamepad.sThumbRX=24000;controller.Gamepad.sThumbRY=24000;controller.Gamepad.bRightTrigger=255;io.AddMouseWheelEvent(0,2);
        for(int i=0;i<8;++i)frame(c,target);controller={};frame(c,target);auto after=club_player_screen_test_view();
        require(before.zoom==after.zoom&&before.yaw==after.yaw&&before.card_coach_zoom==after.card_coach_zoom&&before.pan_y==after.pan_y,"office has no interactive scene cameras");
        for(int i=0;i<3;++i)button(XINPUT_GAMEPAD_DPAD_RIGHT);button(XINPUT_GAMEPAD_A);
        require(club_office_test_view().menu==3&&club_office_test_view().item==0,"Xbox opens anchored office submenu");
        frame(c,target);image(d,c,srv,"my-office-menu.bmp");
        require(club_office_test_center(2,x,y),"database header bounds while coach submenu is open");click(x,y);
        require(club_office_test_view().menu==2&&club_office_test_view().focus==2,"one click switches directly from coach submenu to database");
        click(x,y);require(club_office_test_view().menu==-1&&mod_screen_is_active("my-office"),"clicking the active header closes only its submenu");
        require(club_office_test_center(3,x,y),"coach header remains available after toggle");click(x,y);require(club_office_test_view().menu==3,"coach submenu reopens on its first click");
        button(XINPUT_GAMEPAD_B);require(club_office_test_view().menu==-1&&mod_screen_is_active("my-office"),"B closes submenu locally without replacing the office screen");Sleep(270);
        require(club_office_test_center(0,x,y),"team management header bounds");click(x,y);require(club_office_test_view().menu==0,"team management submenu opens immediately");
        require(club_office_test_menu_center(0,x,y),"formation submenu bounds");click(x,y);require(mod_screen_is_active("club_squad"),"team management > formation opens squad view");
        mod_screen_request_back();frame(c,target);require(mod_screen_is_active("my-office"),"formation Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(4,x,y),"transfers header bounds");click(x,y);require(club_office_test_view().menu==4,"transfers submenu opens on first click");
        require(club_office_test_menu_center(0,x,y),"market submenu bounds");click(x,y);require(mod_screen_is_active("transfer-market"),"Transfers > market opens market screen");
        Sleep(360);for(int i=0;i<8;++i)frame(c,target);image(d,c,srv,"market-screen.bmp");button(XINPUT_GAMEPAD_B);
        require(mod_screen_is_active("my-office"),"market Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(4,x,y),"transfers header remains usable");click(x,y);button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().item==1,"controller selects My Transfers");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("my-transfers"),"Transfers > My Transfers opens the personal ledger screen");Sleep(360);for(int i=0;i<8;++i)frame(c,target);image(d,c,srv,"my-transfers-screen.bmp");button(XINPUT_GAMEPAD_B);
        require(mod_screen_is_active("my-office"),"My Transfers Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_RIGHT);
        require(club_office_test_view().focus==7,"navigation returns to the central scene after opening child screens");key(ImGuiKey_E);
        require(club_office_test_view().slide==1&&club_office_test_view().active,"keyboard advances the office carousel without replacing its page");key(ImGuiKey_Enter);
        require(club_office_test_view().active,"news carousel cards remain informational");key(ImGuiKey_Q);
        require(club_office_test_view().slide==0,"keyboard returns the carousel to the starting XI");
        button(XINPUT_GAMEPAD_DPAD_LEFT);require(club_office_test_view().focus==6,"left moves focus from XI to coach card");
        button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().focus==8,"down moves focus from coach to the new social card");
        require(club_office_test_center(6,x,y),"coach scene bounds");io.AddMousePosEvent(x,y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);
        io.AddMousePosEvent(x+25,y+8);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
        require(club_office_test_view().active&&!club_player_screen_test_view().coach_child,"drag neither moves scene nor activates card");
        click(x,y);require(club_player_screen_test_view().coach_child&&!club_office_test_view().active,"mouse coach card opens generic coach profile");
        for(int i=0;i<20;++i)frame(c,target);image(d,c,srv,"my-office-coach-details.bmp");Sleep(360);button(XINPUT_GAMEPAD_B);require(club_office_test_view().active&&mod_screen_captures_input(),"coach Back returns to office with capture");Sleep(270);
        require(club_office_test_center(2,x,y),"database header bounds");click(x,y);require(club_office_test_view().menu==2,"mouse database menu");
        frame(c,target);image(d,c,srv,"my-office-database.bmp");require(club_office_test_menu_center(0,x,y),"database submenu bounds");click(x,y);
        require(mod_screen_is_active("ranking")&&mod_screen_captures_input(),"database Ranking Mundial opens ranking screen without input leak");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("my-office"),"ranking Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(2,x,y),"database header remains usable");click(x,y);button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().item==1,"Xbox selects Ver outros times");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("other-clubs")&&mod_screen_captures_input(),"database second route reaches club selector");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("my-office"),"other clubs Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(2,x,y),"database header remains available for other leagues");click(x,y);button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_DOWN);
        require(club_office_test_view().item==2,"Xbox selects Ver outras ligas");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("other-leagues")&&mod_screen_captures_input(),"database third route opens the league browser");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("my-office"),"other leagues Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(2,x,y),"database menu remains usable for club competitions");click(x,y);button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_DPAD_DOWN);
        require(club_office_test_view().item==3,"Xbox selects Competições do meu clube");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("club-competitions")&&mod_screen_captures_input(),"fourth database route opens club competitions without input leak");
        for(int i=0;i<24;++i)frame(c,target);std::string competition_image=argv[2];competition_image=competition_image.substr(0,competition_image.find_last_of("/\\")+1)+"club-competitions.bmp";image(d,c,srv,competition_image.c_str());
        button(XINPUT_GAMEPAD_A);button(XINPUT_GAMEPAD_DPAD_RIGHT);for(int i=0;i<24;++i)frame(c,target);
        image(d,c,srv,(competition_image.substr(0,competition_image.find_last_of('.'))+"-knockout.bmp").c_str());
        button(XINPUT_GAMEPAD_A);controller.Gamepad.sThumbRX=26000;controller.Gamepad.sThumbRY=12000;controller.Gamepad.bRightTrigger=180;
        for(int i=0;i<12;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        image(d,c,srv,(competition_image.substr(0,competition_image.find_last_of('.'))+"-knockout-controller.bmp").c_str());
        button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_X);button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("other-clubs")&&last_requested_club==99,"controller selects a specific bracket tie and opens the selected club");
        mod_screen_request_back();frame(c,target);require(mod_screen_is_active("club-competitions"),"bracket club Back restores its knockout view");
        click(435,111);button(XINPUT_GAMEPAD_A);click(610,157);for(int i=0;i<24;++i)frame(c,target);
        image(d,c,srv,(competition_image.substr(0,competition_image.find_last_of('.'))+"-group-b.bmp").c_str());click(500,255);
        require(mod_screen_is_active("other-clubs")&&last_requested_club==100,"selecting a standings row opens that exact club's existing screen");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("club-competitions"),"club details Back restores the selected competition");click(150,155);for(int i=0;i<24;++i)frame(c,target);
        image(d,c,srv,(competition_image.substr(0,competition_image.find_last_of('.'))+"-league-movement.bmp").c_str());Sleep(360);button(XINPUT_GAMEPAD_B);
        require(mod_screen_is_active("my-office"),"club competitions Back restores office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(3,x,y),"office header bounds");click(x,y);button(XINPUT_GAMEPAD_DPAD_DOWN);require(club_office_test_view().item==1,"Xbox selects trophy submenu item");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("trophy-room")&&mod_screen_captures_input(),"trophy route keeps modal capture");mod_screen_request_back();frame(c,target);require(mod_screen_is_active("my-office"),"trophy Back returns to office");
        for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        require(club_office_test_center(3,x,y),"header stays usable after child returns");click(x,y);button(XINPUT_GAMEPAD_A);
        require(club_player_screen_test_view().coach_child,"statistics submenu reaches same generic coach profile");Sleep(360);button(XINPUT_GAMEPAD_B);Sleep(270);
        require(club_office_test_center(5,x,y),"finance header bounds");click(x,y);require(club_office_test_view().menu==5,"finance opens its anchored submenu");
        require(club_office_test_menu_center(0,x,y),"finance loan submenu bounds");click(x,y);
        require(mod_screen_is_active("loans")&&mod_screen_captures_input(),"Finance > Empréstimos opens the existing loan screen");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("my-office"),"loan screen Back returns to office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        button(XINPUT_GAMEPAD_DPAD_LEFT);button(XINPUT_GAMEPAD_DPAD_LEFT);button(XINPUT_GAMEPAD_DPAD_RIGHT);button(XINPUT_GAMEPAD_DPAD_RIGHT);
        require(club_office_test_view().focus==5,"Xbox navigation reaches Finance");button(XINPUT_GAMEPAD_A);
        require(club_office_test_view().menu==5&&club_office_test_view().item==0,"Xbox opens the single Finance submenu item");button(XINPUT_GAMEPAD_A);
        require(mod_screen_is_active("loans"),"Xbox confirms Empréstimos route");mod_screen_request_back();frame(c,target);
        require(mod_screen_is_active("my-office"),"Xbox loan screen Back returns to office");for(int i=0;i<300&&!club_office_test_view().coach_scene;++i)frame(c,target);Sleep(270);
        key(ImGuiKey_DownArrow);key(ImGuiKey_Enter);require(!club_office_test_view().active&&club_player_screen_test_view().group,"central populated XI opens the full squad screen");Sleep(270);button(XINPUT_GAMEPAD_B);require(club_office_test_view().active,"squad Back restores office");
        club_player_screen_set_device(nullptr);coach_profile_device(nullptr);club_player_screen_set_device(d);coach_profile_device(d);for(int i=0;i<4;++i)frame(c,target);
        require(club_office_test_view().coach_scene&&club_office_test_view().active,"device reset restores office scene");
        if(initial_club==1043&&has_fixture){std::string path=argv[3];path=path.substr(0,path.find_last_of("/\\")+1)+"miami_preview.bin";
            FILE*f=nullptr;require(!fopen_s(&f,path.c_str(),"rb")&&f,"open second actual offline club fixture");
            char magic[8],name[128];uint32_t count=0,club=0,size=0;
            require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&count,4,1,f)==1&&fread(&club,4,1,f)==1&&fread(&size,4,1,f)==1&&size==sizeof(ClubPlayerRow)&&count>=11&&count<=CLUB_PLAYER_CAPACITY,"second roster ABI and bounds");
            std::vector<ClubPlayerRow>second(count);require(fread(name,1,128,f)==128&&fread(second.data(),sizeof(ClubPlayerRow),count,f)==count&&fgetc(f)==EOF,"second roster exact ownership");fclose(f);name[127]=0;
            coach_profile_publish_career(nullptr,nullptr,0);club_player_screen_publish(second.data(),second.size(),(int)club,name);frame(c,target);
            require(!club_office_test_view().coach_scene,"club switch immediately clears old coach scene");
            for(int i=0;i<400&&(last_club!=(LONG)club||club_player_screen_test_view().card_club!=(int)club);++i)frame(c,target);
            require(last_club==(LONG)club&&club_player_screen_test_view().card_club==(int)club&&club_player_screen_test_view().starters==11,"office dynamically reloads exact second club roster, crest and primary color");
            frame(c,target);image(d,c,srv,"my-office-miami.bmp");
        }
        Sleep(270);button(XINPUT_GAMEPAD_B);
        require(!mod_screen_is_open()&&mod_screen_captures_input(),"office exit has shared release debounce");
        club_player_screen_publish(nullptr,0,0,"");coach_profile_publish_career(nullptr,nullptr,0);mod_screen_open_action(FIFA16_MY_OFFICE_ACTION);frame(c,target);
        require(club_office_test_view().active&&!club_office_test_view().coach_scene&&club_player_screen_test_view().starters==0,"missing club cannot borrow old office resources");
        mod_screen_close();mod_screen_sync_lifecycle();transfer_center_screen_device(nullptr);club_competitions_screen_device(nullptr);coach_profile_device(nullptr);club_player_screen_set_device(nullptr);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
        puts("PASS: dynamic office, static native coach arrival + XI, anchored menus, reserved carousel, Xbox/keyboard/mouse, child routes and Back capture, device reset; offline only");return 0;
    }
    if(hub_only){
        auto button=[&](WORD b){controller.Gamepad.wButtons=b;frame(c,target);controller.Gamepad={};frame(c,target);};
        auto key=[&](ImGuiKey k){io.AddKeyEvent(k,true);frame(c,target);io.AddKeyEvent(k,false);frame(c,target);};
        for(int i=0;i<100&&!club_player_screen_test_view().card_coach_model;++i)frame(c,target);
        auto view=club_player_screen_test_view();require(view.home&&!view.coach_child&&view.focus==0&&view.card_coach_model,"native Clube opens coach and exact XI cards, not the squad list");
        frame(c,target);image(d,c,srv,"club-home-cards.bmp");Sleep(270);
        auto resize=[&](UINT w,UINT h){c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();target->Release();desc.Width=w;desc.Height=h;ID3D11Texture2D*texture=nullptr;
            require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&texture))&&SUCCEEDED(d->CreateRenderTargetView(texture,nullptr,&target))&&SUCCEEDED(d->CreateShaderResourceView(texture,nullptr,&srv)),"hub resolution target");texture->Release();io.DisplaySize={(float)w,(float)h};};
        resize(1280,720);frame(c,target);image(d,c,srv,"club-home-720p.bmp");resize(1920,1080);frame(c,target);image(d,c,srv,"club-home-1080p.bmp");resize(1428,800);frame(c,target);
        controller.Gamepad.sThumbRX=20000;controller.Gamepad.bRightTrigger=255;for(int i=0;i<8;++i)frame(c,target);controller={};frame(c,target);
        auto moved=club_player_screen_test_view();require(moved.card_coach_yaw>view.card_coach_yaw&&moved.card_coach_zoom>view.card_coach_zoom&&moved.zoom==view.zoom&&moved.pan_x==view.pan_x,"focused coach camera never moves the XI");
        button(XINPUT_GAMEPAD_RIGHT_THUMB);button(XINPUT_GAMEPAD_DPAD_RIGHT);view=club_player_screen_test_view();require(view.focus==1,"Xbox directional card focus");
        controller.Gamepad.sThumbRX=20000;controller.Gamepad.sThumbRY=18000;controller.Gamepad.bRightTrigger=255;for(int i=0;i<8;++i)frame(c,target);controller={};frame(c,target);
        moved=club_player_screen_test_view();require(moved.zoom>view.zoom&&moved.pan_x>view.pan_x&&moved.card_coach_yaw==view.card_coach_yaw&&moved.card_coach_zoom==view.card_coach_zoom&&moved.yaw==0,"focused XI zoom/pan, photograph never rotates and coach remains still");
        button(XINPUT_GAMEPAD_RIGHT_THUMB);key(ImGuiKey_LeftArrow);require(club_player_screen_test_view().focus==0,"keyboard card focus");key(ImGuiKey_Enter);
        require(club_player_screen_test_view().coach_child&&!club_player_screen_test_view().home&&mod_screen_is_active("club_players"),"coach opens generic detailed profile inside same modal, no host navigation bridge");
        for(int i=0;i<30;++i)frame(c,target);image(d,c,srv,"club-home-coach-details.bmp");Sleep(360);button(XINPUT_GAMEPAD_B);
        require(club_player_screen_test_view().home&&mod_screen_captures_input(),"B from coach returns to cards without releasing game input");Sleep(270);
        key(ImGuiKey_RightArrow);key(ImGuiKey_Enter);require(!club_player_screen_test_view().home&&club_player_screen_test_view().group,"XI opens separate full squad view");
        frame(c,target);image(d,c,srv,"club-home-squad.bmp");Sleep(270);button(XINPUT_GAMEPAD_DPAD_DOWN);button(XINPUT_GAMEPAD_A);
        for(int i=0;i<100&&last_group!=0;++i)frame(c,target);require(!club_player_screen_test_view().group,"squad entry opens exact player profile");Sleep(270);button(XINPUT_GAMEPAD_B);
        require(club_player_screen_test_view().group&&!club_player_screen_test_view().home,"player Back returns to full squad");Sleep(270);button(XINPUT_GAMEPAD_B);
        require(club_player_screen_test_view().home&&mod_screen_is_open(),"squad Back returns to cards");Sleep(270);
        float x,y;require(club_player_screen_test_card_center(1,x,y),"card mouse bounds");io.AddMousePosEvent(x,y);frame(c,target);auto mouse_before=club_player_screen_test_view();
        io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMousePosEvent(x+30,y+10);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
        require(club_player_screen_test_view().home&&club_player_screen_test_view().pan_x!=mouse_before.pan_x,"mouse drag pans focused card and does not activate it on release");
        require(club_player_screen_test_card_center(0,x,y),"coach mouse bounds");io.AddMousePosEvent(x,y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
        require(club_player_screen_test_view().coach_child,"mouse click opens same coach details as keyboard/Xbox");Sleep(370);button(XINPUT_GAMEPAD_B);Sleep(270);
        club_player_screen_set_device(nullptr);coach_profile_device(nullptr);club_player_screen_set_device(d);coach_profile_device(d);for(int i=0;i<4;++i)frame(c,target);
        require(club_player_screen_test_view().home&&club_player_screen_test_view().card_coach_model,"device reset restores both cards");
        CoachProfileContext missing={};missing.valid=1;missing.kind=COACH_CAREER_USER;missing.id=0;missing.club=initial_club;missing.confidence=missing.reputation=missing.wage=-1;strcpy_s(missing.name,"Treinador sem modelo associado");
        coach_profile_publish_career(&missing,nullptr,0);frame(c,target);
        require(!club_player_screen_test_view().card_coach_model,"new coach identity immediately invalidates old matching 3D");
        for(int i=0;i<200&&club_player_screen_test_view().card_club!=initial_club;++i)frame(c,target);
        require(club_player_screen_test_view().card_club==initial_club&&!club_player_screen_test_view().card_coach_model,"custom coach never borrows club sideline model");
        auto switched=rows;for(auto&r:switched)r.team_id=112893;coach_profile_publish_career(nullptr,nullptr,0);club_player_screen_publish(switched.data(),switched.size(),112893,"Inter Miami");frame(c,target);
        require(club_player_screen_test_view().card_club==0,"club change clears old card identity before resources arrive");
        for(int i=0;i<300&&club_player_screen_test_view().card_club!=112893;++i)frame(c,target);
        require(club_player_screen_test_view().card_club==112893&&club_player_screen_test_view().card_nationality==0&&club_player_screen_test_view().starters==11,"dynamic second club, no borrowed nationality, exact XI still required");
        button(XINPUT_GAMEPAD_B);require(!mod_screen_is_open()&&mod_screen_captures_input(),"final Back closes modal with release debounce");
        club_player_screen_publish(nullptr,0,0,"");coach_profile_publish_career(nullptr,nullptr,0);require(mod_screen_open_action(FIFA16_CLUB_PLAYER_ACTION),"reopen missing resources");frame(c,target);
        require(club_player_screen_test_view().home&&!club_player_screen_test_view().card_coach_model&&club_player_screen_test_view().starters==0,"empty club never borrows old coach or lineup");
        mod_screen_close();mod_screen_sync_lifecycle();
        club_player_screen_publish(rows.data(),rows.size(),initial_club,club_name);
        require(mod_screen_open_action(FIFA16_FULL_SQUAD_ACTION),"open complete-roster screen from its dedicated action");
        for(int i=0;i<500&&last_group_count!=rows.size()+1;++i)frame(c,target);
        auto full_view=club_player_screen_test_view();
        require(full_view.group&&full_view.room==RoomFullSquadPhoto&&last_group_count==rows.size()+1,
            "dedicated full-squad action renders all current players plus the exact-club coach with its own scene mode");
        mod_screen_close();mod_screen_sync_lifecycle();coach_profile_device(nullptr);club_player_screen_set_device(nullptr);ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
        puts("PASS: two native club cards, exclusive focused cameras, mouse/keyboard/Xbox activation, generic coach child, squad/player/parent Back, device reset and missing resources; offline only");return 0;
    }
    if(profile_only) {
        const auto unchanged_rows=rows;
        Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad={};frame(c,target);
        for(int i=0;i<300&&last_group!=0;++i)frame(c,target);
        require(last_group==0&&last_player==rows[0].player_id,"profile-only QA uses actual chosen player and native assets");
        require(club_player_screen_test_select_pose(104),"stable profile render pose");
        for(int i=0;i<300&&last_pose_id!=104;++i)frame(c,target);
        for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,"player-profile-keeper.bmp");
        Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
        Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_DOWN;frame(c,target);controller.Gamepad={};frame(c,target);
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad={};frame(c,target);
        for(int i=0;i<300&&last_player!=rows[1].player_id;++i)frame(c,target);
        require(last_player==rows[1].player_id&&club_player_screen_test_view().selected==1,"selection belongs to roster, not profile tabs");
        require(club_player_screen_test_select_pose(104),"outfield profile recipe");
        for(int i=0;i<300&&last_pose_id!=104;++i)frame(c,target);
        for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,argv[2]);
        Sleep(260);
        for(int main=1;main<3;++main){controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);controller.Gamepad={};frame(c,target);require(club_player_screen_test_view().profile_view==main,"LB/RB cycles summary/performance/attributes");}
        for(int page=1;page<6;++page){controller.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_RIGHT;frame(c,target);controller.Gamepad={};frame(c,target);
            require(club_player_screen_test_view().page==page,"D-pad navigates every read-only attribute subsection");
            frame(c,target);char file[80];sprintf_s(file,"player-profile-page-%d.bmp",page);image(d,c,srv,file);}
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_RIGHT;frame(c,target);controller.Gamepad={};frame(c,target);
        auto trigger_before=club_player_screen_test_view();controller.Gamepad.bRightTrigger=255;for(int i=0;i<10;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().zoom>trigger_before.zoom&&club_player_screen_test_view().page==trigger_before.page&&club_player_screen_test_view().scroll_y==trigger_before.scroll_y,"RT zooms model only, never attributes or tabs");
        controller.Gamepad.bLeftTrigger=255;for(int i=0;i<10;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().zoom<trigger_before.zoom+.01f,"LT zooms out with independent deadzone");
        auto tab_before=club_player_screen_test_view();controller.Gamepad.sThumbLX=24000;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().page==(tab_before.page+1)%6&&club_player_screen_test_view().selected_id==tab_before.selected_id,"left-stick X switches subsection, never player");
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_LEFT;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().page==0,"D-pad switches back to overview");
        for(int i=0;i<3;++i)frame(c,target);auto scroll_before=club_player_screen_test_view();controller.Gamepad.sThumbLY=-24000;
        for(int i=0;i<20;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().scroll_y>scroll_before.scroll_y&&club_player_screen_test_view().page==0,"left-stick Y scrolls only current attribute subsection");
        auto pan_before=club_player_screen_test_view();controller.Gamepad.sThumbRY=23000;for(int i=0;i<10;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().profile_pan_y>pan_before.profile_pan_y&&club_player_screen_test_view().page==pan_before.page,"right-stick Y moves camera without changing tabs");
        auto initial=club_player_screen_test_view();controller.Gamepad.sThumbRX=23000;for(int i=0;i<10;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().yaw!=initial.yaw,"profile renderer still rotates with Xbox right stick");
        auto key_before=club_player_screen_test_view();io.AddKeyEvent(ImGuiKey_E,true);frame(c,target);io.AddKeyEvent(ImGuiKey_E,false);frame(c,target);
        require(club_player_screen_test_view().profile_view==(key_before.profile_view+1)%3&&club_player_screen_test_view().selected_id==key_before.selected_id,"Q/E changes main view, not player or camera");
        io.AddKeyEvent(ImGuiKey_Q,true);frame(c,target);io.AddKeyEvent(ImGuiKey_Q,false);frame(c,target);
        io.AddMousePosEvent(250,300);for(int i=0;i<2;++i)frame(c,target);auto mouse_before=club_player_screen_test_view();
        io.AddMouseWheelEvent(0,1);frame(c,target);frame(c,target);
        require(club_player_screen_test_view().zoom>mouse_before.zoom&&club_player_screen_test_view().page==mouse_before.page,"mouse wheel over model zooms only model");
        io.AddMouseButtonEvent(ImGuiMouseButton_Left,true);frame(c,target);io.AddMousePosEvent(275,320);frame(c,target);io.AddMouseButtonEvent(ImGuiMouseButton_Left,false);frame(c,target);
        require(club_player_screen_test_view().yaw!=mouse_before.yaw&&club_player_screen_test_view().profile_pan_y!=mouse_before.profile_pan_y,"mouse drag rotates and shifts camera inside model subsection");
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_THUMB;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().yaw==0&&club_player_screen_test_view().zoom==1&&club_player_screen_test_view().profile_pan_y==0,"R3 resets only profile camera");
        auto resize_target=[&](UINT w,UINT h){c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();target->Release();
            desc.Width=w;desc.Height=h;ID3D11Texture2D*resized=nullptr;
            require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&resized))&&SUCCEEDED(d->CreateRenderTargetView(resized,nullptr,&target))&&SUCCEEDED(d->CreateShaderResourceView(resized,nullptr,&srv)),"actual resolution-sized UI target");
            resized->Release();io.DisplaySize=ImVec2((float)w,(float)h);};
        resize_target(1280,720);for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,"player-profile-720p.bmp");
        resize_target(1920,1080);for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,"player-profile-1080p.bmp");
        resize_target(1428,800);for(int i=0;i<3;++i)frame(c,target);
        require(!memcmp(rows.data(),unchanged_rows.data(),rows.size()*sizeof(ClubPlayerRow)),"profile and controller never mutate provided player rows");
        require(mod_screen_captures_input(),"exclusive modal input retained throughout profile navigation");
        Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().group&&mod_screen_captures_input(),"B returns to team without leaking input to FIFA");
        for(int i=0;i<300&&last_group!=1;++i)frame(c,target);
        require(last_group==1&&last_group_count==11,"transparent profile mode does not alter team photograph scene");
        mod_screen_close();mod_screen_sync_lifecycle();club_player_screen_set_device(nullptr);
        ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
        puts("PASS: light player profile, native positions/keeper attributes, themes, all pages, 720p/1080p layout, real RX3 models and Xbox/back/modal guard; no player data writes");return 0;
    }
    require(club_player_screen_test_view().roster==rows.size()&&club_player_screen_test_view().valid,"full roster remains visible but only tactical positions define the starting XI");
    if(argc==4&&initial_club==1043)require(club_player_screen_test_view().portraits==rows.size(),"all Flamengo fixture players have separate uploaded 2D portraits");
    const char*preview_name=argc==4?(initial_club==1043?"flamengo":initial_club==112893?"miami":"club"):"synthetic";
    for(const auto&r:rows)require(club_player_screen_test_starter(r.player_id)==(r.squad_position>=0&&r.squad_position<28),"bench/reserves do not enter the collective photo by rating or list order");
    Sleep(260);frame(c,target);
    for(unsigned pose=1;pose<=presentation_pose_count(PoseGroup);++pose) {
        if(pose>1){controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);controller.Gamepad={};frame(c,target);}
        for(int i=0;i<300&&(last_group!=1||last_pose_id!=(LONG)pose);++i)frame(c,target);
        require(last_group==1&&last_pose_id==(LONG)pose&&last_group_count==11,"LB/RB selects a complete collective pose with the same eleven starters");
        frame(c,target);frame(c,target);char file[100];sprintf_s(file,"club-%s-pose-%u.bmp",preview_name,pose);image(d,c,srv,file);
    }
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);controller.Gamepad={};frame(c,target);
    for(int i=0;i<300&&last_pose_id!=1;++i)frame(c,target);require(last_pose_id==1,"collective catalog wraps without changing lineup");
    require(!club_player_screen_test_select_room(-1)&&!club_player_screen_test_select_room(3),"unknown scene cannot replace the photograph");
    for(int kind=1;kind<=2;++kind) {
        last_room=0;
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);controller.Gamepad={};frame(c,target);
        for(int i=0;i<300&&last_room!=kind;++i)frame(c,target);
        require(last_room==kind&&club_player_screen_test_view().room==kind&&club_player_screen_test_view().group&&club_player_screen_test_view().starters==11,"X opens each dynamic room without changing lineup");
        frame(c,target);frame(c,target);char file[100];sprintf_s(file,"club-%s-room-%d.bmp",preview_name,kind);image(d,c,srv,file);
        if(kind==1&&initial_club==1043){
            require(last_room_pose==205,"default press room uses seated coach");
            controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_SHOULDER;frame(c,target);controller.Gamepad={};frame(c,target);
            for(int i=0;i<300&&last_room_pose!=206;++i)frame(c,target);
            require(last_room_pose==206&&club_player_screen_test_view().pose==1,"press-room LB/RB changes seated coach without changing the group photo pose");
            frame(c,target);frame(c,target);image(d,c,srv,"club-flamengo-room-seated-206.bmp");
        }
        require(!club_player_screen_take_refresh_request(),"room/pose changes do not re-query FIFA from the graphics thread");
    }
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);controller.Gamepad={};frame(c,target);
    for(int i=0;i<300&&last_pose_id!=1;++i)frame(c,target);
    require(club_player_screen_test_view().room==0,"X returns to original team photograph");
    if(rows.size()>11) {
        controller.Gamepad.sThumbLY=-24000;
        for(int i=0;i<400&&club_player_screen_test_view().selected!=11;++i)frame(c,target);
        controller.Gamepad={};frame(c,target);require(club_player_screen_test_view().selected==11,"left-stick navigation reaches and scrolls into the bench without changing the XI");
        char file[100];sprintf_s(file,"club-%s-bench.bmp",preview_name);image(d,c,srv,file);
        controller.Gamepad.sThumbLY=24000;
        for(int i=0;i<400&&club_player_screen_test_view().selected!=0;++i)frame(c,target);
        controller.Gamepad={};frame(c,target);require(club_player_screen_test_view().selected==0,"left-stick navigation returns to the first starter");
    }
    auto initial_view=club_player_screen_test_view();
    controller.Gamepad.sThumbRX=24000;controller.Gamepad.sThumbRY=18000;controller.Gamepad.bRightTrigger=255;
    for(int i=0;i<25;++i)frame(c,target);controller.Gamepad={};frame(c,target);
    auto view=club_player_screen_test_view();
    require(view.group&&view.yaw==0&&view.pan_x>initial_view.pan_x&&view.pan_y>initial_view.pan_y&&view.zoom>initial_view.zoom,"right stick pans the group photograph, RT zooms, no rotation");
    image(d,c,srv,argc==4?"club-flamengo-photo-zoom.bmp":"club-screen-photo-zoom.bmp");
    controller.Gamepad.bLeftTrigger=255;for(int i=0;i<15;++i)frame(c,target);controller.Gamepad={};frame(c,target);
    require(club_player_screen_test_view().zoom<view.zoom,"LT zooms the photograph out");
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_RIGHT_THUMB;frame(c,target);controller.Gamepad={};frame(c,target);
    view=club_player_screen_test_view();require(view.zoom==1&&view.pan_x==0&&view.pan_y==0,"right-stick click restores the initial framing");
    io.AddMousePosEvent(900,450);frame(c,target);io.AddMouseWheelEvent(0,1);frame(c,target);
    require(club_player_screen_test_view().zoom>1,"mouse wheel zooms the photograph");
    io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMousePosEvent(940,470);frame(c,target);
    io.AddMouseButtonEvent(0,false);frame(c,target);
    view=club_player_screen_test_view();require(view.pan_x>0&&view.pan_y<0&&view.yaw==0,"mouse drag pans the photograph without turning models");
    io.AddKeyEvent(ImGuiKey_R,true);frame(c,target);io.AddKeyEvent(ImGuiKey_R,false);frame(c,target);
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad.wButtons=0;frame(c,target);
    for(int i=0;i<150 && last_group!=0;++i)frame(c,target);
    require(last_group==0&&last_player==rows[0].player_id,"Xbox A opens the selected player's detail screen");
    frame(c,target);frame(c,target);image(d,c,srv,argc==4?"club-flamengo-individual.bmp":"club-screen-individual.bmp");
    Sleep(260);frame(c,target);view=club_player_screen_test_view();
    controller.Gamepad.sThumbRX=24000;for(int i=0;i<15;++i)frame(c,target);controller.Gamepad.sThumbRX=0;frame(c,target);
    require(club_player_screen_test_view().yaw!=view.yaw,"right stick still rotates an individual player");
    int main_view=view.profile_view;controller.Gamepad.sThumbLX=24000;frame(c,target);controller.Gamepad.sThumbLX=0;frame(c,target);
    require(club_player_screen_test_view().profile_view!=(int)main_view,"left stick navigates main views, not players, from summary");
    unsigned previous_pose=club_player_screen_test_view().pose;
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);controller.Gamepad.wButtons=0;frame(c,target);
    require(club_player_screen_test_view().pose!=previous_pose,"X changes the individual pose, not lineup selection");
    Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
    Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_DPAD_DOWN;frame(c,target);controller.Gamepad={};frame(c,target);
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad={};frame(c,target);
    for(int i=0;i<150 && last_player!=rows[1].player_id;++i)frame(c,target);
    require(last_player==rows[1].player_id&&last_group==0,"roster selection opens another player without mixing profile tab navigation");
    require(!club_player_screen_test_select_pose(1)&&!club_player_screen_test_select_pose(999999),"individual selector rejects collective and unknown recipes");
    for(size_t index=0;index<presentation_pose_count(PoseIndividual);++index) {
        const auto*info=presentation_pose_at(index,PoseIndividual);
        require(club_player_screen_test_select_pose(info->id),"same individual selector accepts all fourteen recipes");
        for(int i=0;i<300&&(last_pose_id!=(LONG)info->id||last_group!=0);++i)frame(c,target);
        require(last_pose_id==(LONG)info->id&&last_group==0&&last_player==rows[1].player_id,"individual pose catalog preserves the chosen player and read-only detail view");
        frame(c,target);frame(c,target);char file[100];sprintf_s(file,"club-%s-individual-%u.bmp",preview_name,info->id);image(d,c,srv,file);
    }
    Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);frame(c,target);
    for(int i=0;i<25;++i)frame(c,target);
    require(mod_screen_is_open()&&mod_screen_captures_input()&&club_player_screen_test_view().group,"holding B returns to the group exactly once and retains modal input focus");
    controller.Gamepad.wButtons=0;frame(c,target);
    for(int i=0;i<150 && last_group!=1;++i)frame(c,target);
    if(initial_club==1043) {
        require(club_player_screen_test_view().coach,"real club coach appears only with matching model and name");
        Sleep(260);controller.Gamepad.sThumbLY=-24000;
        for(int i=0;i<500&&!club_player_screen_test_view().coach_selected;++i)frame(c,target);
        controller.Gamepad={};frame(c,target);
        view=club_player_screen_test_view();require(view.coach_selected&&view.selected==(int)rows.size()&&view.roster==rows.size()&&view.starters==11,"coach is a separate navigable staff row, not a player or starter");
        frame(c,target);image(d,c,srv,"club-flamengo-staff-list.bmp");
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_A;frame(c,target);controller.Gamepad={};frame(c,target);
        for(int i=0;i<150&&!last_coach_ready;++i)frame(c,target);
        require(last_coach_ready&&club_player_screen_test_view().coach_selected&&!club_player_screen_test_view().group,"Xbox A opens the actual sideline coach in a separate read-only detail view");
        frame(c,target);frame(c,target);image(d,c,srv,"club-flamengo-coach-details.bmp");
        Sleep(260);view=club_player_screen_test_view();
        controller.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().pose!=view.pose&&club_player_screen_test_view().page==0&&!club_player_screen_test_select_pose(104)&&!club_player_screen_test_select_pose(4),"coach selects only staff poses, never player attributes or player rig");
        for(size_t i=0;i<presentation_pose_count(PoseStandingCoach);++i) {
            unsigned id=presentation_pose_at(i,PoseStandingCoach)->id;
            require(club_player_screen_test_select_pose(id),"own coach pose selector");
            for(int frame_id=0;frame_id<300&&last_coach_pose!=(LONG)id;++frame_id)frame(c,target);
            require(last_coach_pose==(LONG)id,"each coach recipe reaches the real worker/model");
            frame(c,target);frame(c,target);char file[100];sprintf_s(file,"club-flamengo-coach-%u.bmp",id);image(d,c,srv,file);
        }
        controller.Gamepad.sThumbRX=22000;controller.Gamepad.bRightTrigger=255;
        for(int i=0;i<15;++i)frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().yaw!=view.yaw&&club_player_screen_test_view().zoom>view.zoom,"coach model supports controller rotation and zoom");
        club_player_screen_publish(rows.data(),rows.size(),initial_club,club_name);frame(c,target);
        require(club_player_screen_test_view().coach_selected,"provider refresh preserves coach selection without indexing beyond player rows");
        Sleep(260);controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad={};frame(c,target);
        require(club_player_screen_test_view().group&&club_player_screen_test_view().starters==11&&mod_screen_captures_input(),"B returns from coach to unchanged eleven-player photo and retains modal focus");
        for(int i=0;i<150&&last_group!=1;++i)frame(c,target);
        Sleep(260);frame(c,target);io.AddMousePosEvent(190,681);frame(c,target);
        io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
        require(!club_player_screen_test_view().group&&club_player_screen_test_view().coach_selected,"mouse click on visible staff row also opens coach details");
        Sleep(260);mod_screen_request_back();frame(c,target);
        require(club_player_screen_test_view().group,"Escape/back returns from mouse-opened coach details");
        Sleep(260);controller.Gamepad.sThumbLY=24000;
        for(int i=0;i<500&&club_player_screen_test_view().selected!=1;++i)frame(c,target);
        controller.Gamepad={};frame(c,target);require(club_player_screen_test_view().selected==1,"staff navigation returns safely to players");
        puts("PASS: dynamic sideline coach row, separate model/details, no player attributes, controller navigation, refresh and back/focus");
    }
    controller.Gamepad.sThumbLY=-24000;Sleep(260);frame(c,target);controller.Gamepad.sThumbLY=0;frame(c,target);
    require(club_player_screen_test_view().selected==2,"left stick navigates players in group view");
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_X;frame(c,target);controller.Gamepad.wButtons=0;frame(c,target);
    io.AddKeyEvent(ImGuiKey_Space,true);frame(c,target);io.AddKeyEvent(ImGuiKey_Space,false);frame(c,target);
    require(last_group_count==11&&club_player_screen_test_view().group,"X/Space never toggle a player's participation in the photograph");
    require(club_player_screen_test_select_room(0),"restore photograph after room hotkey QA");frame(c,target);
    io.AddKeyEvent(ImGuiKey_Enter,true);frame(c,target);io.AddKeyEvent(ImGuiKey_Enter,false);frame(c,target);
    require(!club_player_screen_test_view().group,"Enter opens the highlighted player's details");
    Sleep(260);mod_screen_request_back();frame(c,target);require(club_player_screen_test_view().group,"queued native Escape/Back returns to team, not game");
    Sleep(260);io.AddMousePosEvent(175,223);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    require(!club_player_screen_test_view().group&&club_player_screen_test_view().selected==0,"clicking a roster name opens that player's details");
    Sleep(260);mod_screen_request_back();frame(c,target);require(club_player_screen_test_view().group,"mouse-opened details also return to group");
    if(rows.size()>11) {
        auto changed=rows;auto bench=std::find_if(changed.begin(),changed.end(),[](const auto&r){return r.squad_position==28;});
        require(bench!=changed.end(),"fixture includes actual bench");int reserve=bench->player_id,out=changed[1].player_id;
        bench->squad_position=changed[1].squad_position;changed[1].squad_position=28;
        club_player_screen_publish(changed.data(),changed.size(),initial_club,club_name);frame(c,target);
        require(club_player_screen_test_starter(reserve)&&!club_player_screen_test_starter(out)&&club_player_screen_test_view().starters==11,"changing the provided tactical lineup swaps the photo automatically");
        club_player_screen_publish(rows.data(),rows.size(),initial_club,club_name);frame(c,target);
        require(!club_player_screen_test_starter(reserve)&&club_player_screen_test_starter(out),"restoring the lineup does not retain a manually chosen XI");
    }
    auto invalid_rows=rows;invalid_rows[1].squad_position=0;
    club_player_screen_publish(invalid_rows.data(),invalid_rows.size(),initial_club,club_name);frame(c,target);
    require(!club_player_screen_test_view().valid&&club_player_screen_test_view().starters==0,"ambiguous XI never falls back to first eleven or best overall");
    club_player_screen_publish(rows.data(),rows.size(),initial_club,club_name);frame(c,target);
    int next_club=initial_club==1043?112893:1043;
    for(auto&r:rows){r.team_id=next_club;r.club_colors[0]=next_club==1043?0xdb142a:0xf7b5cd;r.club_colors[1]=0x111111;r.club_colors[2]=0xffffff;}
    club_player_screen_publish(rows.data(),rows.size(),next_club,"Outro clube - teste de invalidação do cache");
    for(int i=0;i<300&&last_club!=next_club;++i)frame(c,target);
    require(last_club==next_club&&last_group_count==11&&last_backdrop==1,"club switch refreshes roster selection, colours and crest without reopening");
    if(next_club==112893)require(!club_player_screen_test_view().coach,"club without a matching coach mesh hides staff instead of borrowing another team's model");
    frame(c,target);frame(c,target);image(d,c,srv,argc==4?"club-fixture-cache-change.bmp":"club-screen-changed-club.bmp");
    controller.Gamepad.wButtons=XINPUT_GAMEPAD_B;frame(c,target);controller.Gamepad.wButtons=0;
    frame(c,target);require(!mod_screen_is_open() && mod_screen_captures_input(),"B closes and preserves input release guard");mod_screen_sync_lifecycle();
    club_player_screen_publish(nullptr,0,0,"");require(mod_screen_open_action(FIFA16_CLUB_SQUAD_ACTION),"reopen empty roster");frame(c,target);
    require(club_player_screen_take_refresh_request()&&!club_player_screen_take_refresh_request(),"reopening empty roster still requests one fresh native capture");
    mod_screen_close();mod_screen_sync_lifecycle();club_player_screen_set_device(nullptr);
    if(initial_club==1043){
        Assets assets(argv[1]);auto coach=assets.coach(gallery_rows[0]);
        std::vector<std::shared_ptr<const Model>>models;std::vector<const PresentationPoseInfo*>poses;
        for(size_t i=0;i<presentation_pose_count(PoseCoachAny);++i){auto info=presentation_pose_at(i,PoseCoachAny);auto model=std::make_shared<Model>(*coach.model);
            if(info->modes&PoseSeatedCoach)*model=build_club_room({coach.model},RoomPress,coach.model,info->id);
            else require(apply_coach_pose(*model,info->id),"coach gallery pose");
            require(model->presentation_pose_id==info->id,"coach gallery seated views use the actual conference room");models.push_back(model);poses.push_back(info);}
        pose_gallery(d,c,target,srv,models,poses,"Treinador - poses em pé e na coletiva","club-flamengo-coaches-gallery.bmp");
        models.clear();poses.clear();auto player=assets.load(gallery_rows[1]);
        for(unsigned id=108;id<=114;++id){auto model=std::make_shared<Model>(player);require(apply_presentation_pose(*model,false,nullptr,id),"new individual gallery pose");models.push_back(model);poses.push_back(presentation_pose_find(id));}
        pose_gallery(d,c,target,srv,models,poses,"Jogador - novas poses individuais","club-flamengo-players-gallery.bmp");
    }
    ImGui_ImplDX11_Shutdown();ImGui::DestroyContext();srv->Release();target->Release();c->Release();d->Release();
    puts("PASS: Club3D UI, tactical XI/bench, 7 team/14 player/6 coach poses, seated press room, 2 dynamic room prototypes, mouse/controller, B/focus, roster refresh/cache and close/reopen/empty");return 0;
}
