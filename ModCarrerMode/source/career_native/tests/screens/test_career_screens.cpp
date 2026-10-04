/* WARP uses actual native assets with explicitly offline retirement flags and
 * trophy counts. The supplied career DATA is read-only; QA launch is disabled. */
#define CLUB_PLAYER_SCREEN_QA
#include "../render/test_club_player_3d.cpp"
#include "../../src/screens/operations/career_operations.h"
#include "../../src/features/operations/career_operations_io.h"
#include "../../src/screens/trophies/trophy_room_screen.h"
#include "../../src/screens/sponsors/sponsor_screen.h"
#include "../../src/ui/common/native_loc_names.h"
#include "../../src/platform/overlay/mod_overlay_screens.h"
#include "../../src/platform/input/mod_xinput_gate.h"
#include "../../third_party/imgui/imgui.h"
#include "../../third_party/imgui/backends/imgui_impl_dx11.h"
static XINPUT_STATE pad={};
static unsigned native_refreshes=0;
extern "C" void career_operations_request_native_refresh(void){++native_refreshes;}
extern "C" DWORD WINAPI mod_xinput_read_raw(DWORD index,XINPUT_STATE*out){if(index)return ERROR_DEVICE_NOT_CONNECTED;*out=pad;return ERROR_SUCCESS;}
static void log_line(const char*s){puts(s);}
static void frame(ID3D11DeviceContext*c,ID3D11RenderTargetView*target){mod_screen_sync_lifecycle();ImGui_ImplDX11_NewFrame();ImGui::NewFrame();
    auto before=ImGui::GetStyle();mod_screen_draw();require(!memcmp(before.Colors,ImGui::GetStyle().Colors,sizeof(before.Colors)),"screen theme never leaks");
    ImGui::Render();float bg[4]={.01f,.08f,.14f,1};c->OMSetRenderTargets(1,&target,nullptr);c->ClearRenderTargetView(target,bg);ImGui_ImplDX11_RenderDrawData(ImGui::GetDrawData());Sleep(15);}
static void button(WORD b,ID3D11DeviceContext*c,ID3D11RenderTargetView*t){pad.Gamepad.wButtons=b;frame(c,t);pad={};frame(c,t);}
static std::vector<ClubPlayerRow>roster(const char*path){FILE*f=nullptr;require(!fopen_s(&f,path,"rb")&&f,"offline roster fixture");char magic[8],name[128];uint32_t n,club,stride;
    require(fread(magic,1,8,f)==8&&!memcmp(magic,"C3DQA003",8)&&fread(&n,4,1,f)==1&&fread(&club,4,1,f)==1&&fread(&stride,4,1,f)==1&&n>=11&&n<=100&&stride==sizeof(ClubPlayerRow),"owned bounded fixture schema");
    std::vector<ClubPlayerRow>rows(n);require(fread(name,1,128,f)==128&&fread(rows.data(),stride,n,f)==n&&fgetc(f)==EOF,"exact fixture bytes");fclose(f);return rows;}
int main(int argc,char**argv){require(argc==5,"usage GAME_ROOT ORIGINAL_DATA OUTPUT_PREFIX OFFLINE_CLUB_FIXTURE (no save writes)");
    auto real=roster(argv[4]);native_loc::Names names(argv[1]);require(names.competition(13)=="Premier League","strict native UTF-8/Huffman LOC name agrees with independent reader");
    require(!names.competition(1615).empty(),"custom installed competition name fallback");
    ID3D11Device*d=nullptr;ID3D11DeviceContext*c=nullptr;require(SUCCEEDED(D3D11CreateDevice(nullptr,D3D_DRIVER_TYPE_WARP,nullptr,0,nullptr,0,D3D11_SDK_VERSION,&d,nullptr,&c)),"WARP");
    D3D11_TEXTURE2D_DESC desc={};desc.Width=1428;desc.Height=800;desc.MipLevels=desc.ArraySize=1;desc.Format=DXGI_FORMAT_R8G8B8A8_UNORM;desc.SampleDesc.Count=1;
    desc.BindFlags=D3D11_BIND_RENDER_TARGET|D3D11_BIND_SHADER_RESOURCE;ID3D11Texture2D*t=nullptr;ID3D11RenderTargetView*target=nullptr;ID3D11ShaderResourceView*srv=nullptr;
    require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&t)),"target");d->CreateRenderTargetView(t,nullptr,&target);d->CreateShaderResourceView(t,nullptr,&srv);t->Release();
    ImGui::CreateContext();auto&io=ImGui::GetIO();io.DisplaySize={1428,800};io.DeltaTime=1.f/60;io.IniFilename=nullptr;
    auto resize=[&](UINT w,UINT h){c->OMSetRenderTargets(0,nullptr,nullptr);srv->Release();target->Release();desc.Width=w;desc.Height=h;ID3D11Texture2D*texture=nullptr;
        require(SUCCEEDED(d->CreateTexture2D(&desc,nullptr,&texture))&&SUCCEEDED(d->CreateRenderTargetView(texture,nullptr,&target))&&SUCCEEDED(d->CreateShaderResourceView(texture,nullptr,&srv)),"UI resolution target");texture->Release();io.DisplaySize={(float)w,(float)h};};
    io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/segoeuib.ttf",17);ImGui::StyleColorsDark();require(ImGui_ImplDX11_Init(d,c),"ImGui");
    require(career_operations_register(argv[1],log_line)&&trophy_room_register(argv[1],log_line),"independent screens, no navigation bridge");
    career_operations_device(d);trophy_room_device(d);
    require(sponsor_screen_register(argv[1],log_line),"sponsor independent action registration");sponsor_screen_device(d);
    std::vector<unsigned char>data;CareerLoanSnapshot s={};std::string message;require(career_ops::read_save(argv[2],data,s,message),"read-only save finance");
    player_profile_publish_career_date((int)s.date); /* QA reads date, never patches DATA. */
    career_operations_note_access(argv[2],"read");career_operations_publish_context((int)s.club,(int)s.date);
    for(int i=0;i<150&&!career_operations_test_view().snapshot_valid;++i)Sleep(20);require(career_operations_test_view().snapshot_valid,"async finance");
    std::string prefix=argv[3];
    require(mod_screen_open_action(FIFA_LOANS_ACTION),"loan card");for(int i=0;i<30;++i)frame(c,target);
    image(d,c,srv,(prefix+"-loans.bmp").c_str());
    resize(1280,720);frame(c,target);image(d,c,srv,(prefix+"-loans-720p.bmp").c_str());resize(1920,1080);frame(c,target);image(d,c,srv,(prefix+"-loans-1080p.bmp").c_str());resize(1428,800);frame(c,target);
    button(XINPUT_GAMEPAD_DPAD_RIGHT,c,target);require(career_operations_test_view().plan==1,"Xbox selects next offer");
    Sleep(210);button(XINPUT_GAMEPAD_DPAD_DOWN,c,target);require(career_operations_test_view().plan==4,"Xbox navigates second row of six offers");
    io.AddKeyEvent(ImGuiKey_LeftArrow,true);frame(c,target);io.AddKeyEvent(ImGuiKey_LeftArrow,false);frame(c,target);require(career_operations_test_view().plan==3,"keyboard selects offer");
    button(XINPUT_GAMEPAD_A,c,target);require(career_operations_test_view().confirm,"offer review without writing save");
    auto reviewed=career_operations_test_view().plan;button(XINPUT_GAMEPAD_DPAD_RIGHT,c,target);require(career_operations_test_view().plan==reviewed,"review freezes the selected loan");
    image(d,c,srv,(prefix+"-loan-review.bmp").c_str());mod_screen_request_back();frame(c,target);require(!career_operations_test_view().confirm&&mod_screen_is_active("loans"),"Back dismisses review only");
    Sleep(360);float lx=0,ly=0;require(career_operations_test_loan_center(2,lx,ly),"loan card hitbox");io.AddMousePosEvent(lx,ly);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    require(career_operations_test_view().plan==2&&!career_operations_test_view().confirm,"mouse selects loan without signing");button(XINPUT_GAMEPAD_A,c,target);require(career_operations_test_view().confirm,"mouse selection can be reviewed by Xbox");
    button(XINPUT_GAMEPAD_A,c,target);require(!career_operations_test_view().queued&&!career_operations_test_view().confirm,"QA confirmation never launches worker or writes real save");
    mod_screen_close();frame(c,target);Sleep(350);
    career_operations_publish_context((int)s.club,20261340);require(mod_screen_open_action(FIFA_LOANS_ACTION),"invalid date loan view");for(int i=0;i<30;++i)frame(c,target);button(XINPUT_GAMEPAD_A,c,target);
    require(!career_operations_test_view().confirm,"invalid career calendar cannot compute due date or request credit");mod_screen_close();frame(c,target);Sleep(350);career_operations_publish_context((int)s.club,(int)s.date);
    require(mod_screen_open_action(FIFA_RETIREMENT_ACTION),"retirement card");frame(c,target);
    std::vector<RetirementUiPlayer>rows(real.size());size_t eligible=0,own=0;
    for(size_t i=0;i<real.size();++i){rows[i].id=real[i].player_id;rows[i].age=real[i].age;rows[i].in_club=i<11;rows[i].retiring=i%3==0;
        rows[i].team_id=real[i].team_id;strcpy_s(rows[i].club_name,"Flamengo");strcpy_s(rows[i].name,real[i].name);if(rows[i].retiring){++eligible;if(rows[i].in_club)++own;}}
    retirement_screen_publish(rows.data(),rows.size(),(int)s.club,(int)s.date,1);
    for(int i=0;i<40;++i)frame(c,target);require(career_operations_test_view().filtered==own,"own tab only retiring players");
    require(career_operations_test_ids(nullptr,0)==0,"own tab never implicitly selects every retiring player");
    require(career_operations_test_view().portraits>0,"actual native player photographs");
    image(d,c,srv,(prefix+"-retirement-club.bmp").c_str());
    resize(1280,720);frame(c,target);image(d,c,srv,(prefix+"-retirement-720p.bmp").c_str());resize(1920,1080);frame(c,target);image(d,c,srv,(prefix+"-retirement-1080p.bmp").c_str());resize(1428,800);frame(c,target);
    button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(career_operations_test_view().filtered==eligible,"world tab excludes all active players");
    require(career_operations_test_ids(nullptr,0)==0&&career_operations_test_view().scope==1,"two tabs; global listing never targets unmarked players");
    button(XINPUT_GAMEPAD_A,c,target);require(career_operations_test_view().selected==1&&!career_operations_test_view().profile,"A marks instead of opening profile");
    button(XINPUT_GAMEPAD_DPAD_DOWN,c,target);button(XINPUT_GAMEPAD_A,c,target);require(career_operations_test_view().selected==2,"multiple retirement selection");
    image(d,c,srv,(prefix+"-retirement-selected.bmp").c_str());button(XINPUT_GAMEPAD_START,c,target);require(career_operations_test_view().confirm&&career_operations_test_ids(nullptr,0)==2,"review exact selected IDs only");image(d,c,srv,(prefix+"-retirement-review.bmp").c_str());mod_screen_request_back();frame(c,target);Sleep(360);
    button(XINPUT_GAMEPAD_A,c,target);require(career_operations_test_view().selected==1,"A toggles off only focused player");Sleep(120);button(XINPUT_GAMEPAD_DPAD_UP,c,target);
    unsigned ids[100]={};require(career_operations_test_ids(ids,100)==1,"only checked retiring ID");
    require(career_operations_test_set_search("nao-existe-no-fixture"),"search input");frame(c,target);require(career_operations_test_view().filtered==0&&career_operations_test_ids(nullptr,0)==1,"search is a view filter and preserves explicit selection");career_operations_test_set_search("");frame(c,target);
    auto refresh_before=native_refreshes;
    button(XINPUT_GAMEPAD_X,c,target);require(career_operations_test_view().profile&&native_refreshes==refresh_before+1,"X opens exact player details and queues native provider immediately, preserves checks");
    unsigned id=0;int club,date;require(retirement_profile_take_request(&id,&club,&date)&&id==ids[0]&&club==(int)s.club&&date==(int)s.date&&!retirement_profile_take_request(&id,&club,&date),"single owned profile request");
    auto found=std::find_if(real.begin(),real.end(),[&](const auto&r){return r.player_id==(int)id;});require(found!=real.end(),"selected exact player");
    auto player=*found;retirement_profile_publish(&player,"Flamengo (fixture offline)",club+1,date,1);
    require(!career_operations_test_view().profile_valid,"wrong career profile rejected");
    /* Clearly synthetic statistics for UI QA, never read as this save's stats. */
    PlayerCompetitionInput competitions[]={{(int)id,player.team_id,10,10,7,12,1,2,6,900,3},{(int)id,player.team_id,20,20,100,5,0,1,3,390,3},{(int)id,player.team_id,30,30,13,3,0,0,1,210,3}};
    player_profile_publish_competitions(competitions,std::size(competitions),club,date,1);
    auto stats=fifa_player::profile_competitions((int)id,player.team_id);require(stats.available&&stats.rows.size()==3&&player_competitions::total(stats).games==20,"copied exact player competitions");
    auto changed=competitions[0];changed.games=13;changed.rating_sum=970;player_profile_publish_competitions(&changed,1,club,date,2);
    require(player_competitions::total(fifa_player::profile_competitions((int)id,player.team_id)).games==13,"new snapshot invalidates cached statistics");
    player_profile_publish_competitions(nullptr,0,0,0,3);require(!fifa_player::profile_competitions((int)id,player.team_id).available,"unloaded career cannot borrow old statistics");
    player_profile_publish_competitions(competitions,std::size(competitions),club,date,4);
    retirement_profile_publish(&player,"Flamengo",club,date,1);
    for(int i=0;i<250&&!career_operations_test_view().profile_model;++i)frame(c,target);require(career_operations_test_view().profile_model,"selected player's actual native RX3");
    for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-retirement-profile.bmp").c_str());
    resize(1280,720);for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-retirement-profile-720p.bmp").c_str());
    resize(1920,1080);for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-retirement-profile-1080p.bmp").c_str());resize(1428,800);frame(c,target);
    require(career_operations_test_view().profile_view==0,"generic profile opens compact summary");
    Sleep(350);button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(career_operations_test_view().profile_view==1,"RB opens performance without changing player");
    for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-profile-performance.bmp").c_str());
    resize(1280,720);for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-profile-performance-720p.bmp").c_str());resize(1428,800);frame(c,target);
    std::vector<PlayerCompetitionInput>many;for(int i=0;i<10;++i)many.push_back({(int)id,player.team_id,40+i,40+i,7,2,0,0,1,150,3});
    player_profile_publish_competitions(many.data(),many.size(),club,date,5);for(int i=0;i<3;++i)frame(c,target);
    auto stat_scroll_before=career_operations_test_view();pad.Gamepad.sThumbLY=-24000;for(int i=0;i<30;++i)frame(c,target);pad={};frame(c,target);
    require(career_operations_test_view().competition_scroll>stat_scroll_before.competition_scroll&&career_operations_test_view().profile_scroll==stat_scroll_before.profile_scroll,"performance scroll captures left stick without moving attributes");
    player_profile_publish_competitions(competitions,std::size(competitions),club,date,6);for(int i=0;i<3;++i)frame(c,target);
    button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(career_operations_test_view().profile_view==2,"RB opens dedicated attributes");
    for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-profile-attributes.bmp").c_str());
    button(XINPUT_GAMEPAD_DPAD_RIGHT,c,target);require(career_operations_test_view().profile_category==1&&career_operations_test_view().profile_view==2,"D-pad changes attribute subsection, not main page or player");
    button(XINPUT_GAMEPAD_DPAD_LEFT,c,target);auto scroll_before=career_operations_test_view();pad.Gamepad.sThumbLY=-24000;for(int i=0;i<30;++i)frame(c,target);pad={};frame(c,target);
    require(career_operations_test_view().profile_scroll>scroll_before.profile_scroll,"left stick scrolls detailed attributes only");
    float tx=0,ty=0;require(career_operations_test_profile_tab_center(0,tx,ty),"main tab mouse hitbox");io.AddMousePosEvent(tx,ty);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    require(career_operations_test_view().profile_view==0&&career_operations_test_view().selected==1,"mouse switches summary without losing retirement checks");
    io.AddKeyEvent(ImGuiKey_E,true);frame(c,target);io.AddKeyEvent(ImGuiKey_E,false);frame(c,target);require(career_operations_test_view().profile_view==1,"keyboard cycles top-level views");
    Sleep(350);auto previous=career_operations_test_view();pad.Gamepad.sThumbRX=23000;pad.Gamepad.bRightTrigger=255;
    for(int i=0;i<12;++i)frame(c,target);pad={};frame(c,target);auto after=career_operations_test_view();
    require(after.yaw!=previous.yaw&&after.zoom>previous.zoom,"Xbox profile rotation + trigger zoom");
    button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(career_operations_test_view().profile,"attribute navigation retains modal");
    mod_screen_request_back();frame(c,target);require(!career_operations_test_view().profile&&career_operations_test_view().selected==1&&mod_screen_is_active("retirement"),"profile Back preserves checked list and captures game input");
    Sleep(360);float rx=0,ry=0;require(career_operations_test_row_center(0,rx,ry),"retirement row mouse hitbox");io.AddMousePosEvent(rx,ry);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);require(career_operations_test_view().selected==0&&!career_operations_test_view().profile,"row click toggles selection without releasing drawn photos");
    io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);require(career_operations_test_view().selected==1,"mouse reselects exact player");
    require(career_operations_test_row_center(0,rx,ry,true),"independent details button");io.AddMousePosEvent(rx,ry);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);frame(c,target);
    require(career_operations_test_view().profile&&career_operations_test_view().selected==1,"mouse profile is deferred until next frame, no same-frame SRV release");
    require(retirement_profile_take_request(&id,&club,&date)&&id==ids[0],"deferred profile keeps exact ID");retirement_profile_publish(&player,"Flamengo",club,date,1);for(int i=0;i<60;++i)frame(c,target);mod_screen_request_back();frame(c,target);
    Sleep(350);button(XINPUT_GAMEPAD_Y,c,target);require(career_operations_test_view().keyboard,"controller name search");
    mod_screen_request_back();frame(c,target);require(!career_operations_test_view().keyboard&&mod_screen_is_active("retirement"),"keyboard Back keeps list");
    retirement_screen_publish(nullptr,0,(int)s.club,(int)s.date,1);frame(c,target);
    require(career_operations_test_view().filtered==0&&career_operations_test_view().selected==0&&career_operations_test_ids(nullptr,0)==0,"valid empty roster clears stale checks and never targets everyone");
    retirement_screen_publish(rows.data(),rows.size(),(int)s.club,(int)s.date,1);for(int i=0;i<30;++i)frame(c,target);
    image(d,c,srv,(prefix+"-retirement-world.bmp").c_str());mod_screen_close();frame(c,target);Sleep(350);require(!mod_screen_captures_input(),"release cooldown returns input");
    sponsor_screen_publish(real.data(),real.size(),real[0].team_id,"Flamengo");
    require(mod_screen_open_action(FIFA16_SPONSOR_ACTION),"sponsors native card action");
    require(!mod_screen_open_action(FIFA_LOANS_ACTION)&&mod_screen_captures_input(),"sponsors exclusively owns focus, no underlying screen navigation");
    for(int i=0;i<300&&!sponsor_screen_test_view().model;++i)frame(c,target);
    auto sv=sponsor_screen_test_view();require(sv.model&&sv.roster==real.size()&&sv.slots==6&&sv.player==sv.rendered_player&&sv.pose==101,"sponsors exact native random roster player, six empty slots, fixed neutral pose");
    require(sv.portrait,"sponsors footer displays this player's exact native 2D face");
    image(d,c,srv,(prefix+"-sponsors.bmp").c_str());
    for(int i=0;i<20;++i)frame(c,target);require(sponsor_screen_test_view().player==sv.player,"random player remains fixed across frames");
    Sleep(210);button(XINPUT_GAMEPAD_DPAD_RIGHT,c,target);require(sponsor_screen_test_view().selected==1,"sponsor slots Xbox horizontal navigation");
    Sleep(210);button(XINPUT_GAMEPAD_DPAD_DOWN,c,target);require(sponsor_screen_test_view().selected==3,"sponsor slots Xbox vertical grid navigation");
    io.AddKeyEvent(ImGuiKey_LeftArrow,true);frame(c,target);io.AddKeyEvent(ImGuiKey_LeftArrow,false);frame(c,target);
    require(sponsor_screen_test_view().selected==2,"sponsor slots keyboard navigation");
    float slot_x=0,slot_y=0;require(sponsor_screen_test_slot_center(3,slot_x,slot_y),"rendered sponsor slot hitbox");
    io.AddMousePosEvent(slot_x,slot_y);frame(c,target);io.AddMouseButtonEvent(ImGuiMouseButton_Left,true);frame(c,target);
    io.AddMouseButtonEvent(ImGuiMouseButton_Left,false);frame(c,target);require(sponsor_screen_test_view().selected==3,"sponsor slots mouse selection");
    for(int i=0;i<45;++i)frame(c,target);require(fabsf(fabsf(sponsor_screen_test_view().yaw)-3.14159265f)<.04f,"omoplata slot rotates native model to its back");
    image(d,c,srv,(prefix+"-sponsors-back.bmp").c_str());
    require(sponsor_screen_test_slot_center(0,slot_x,slot_y),"master slot bounds");io.AddMousePosEvent(slot_x,slot_y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    for(int i=0;i<45;++i)frame(c,target);require(fabsf(sponsor_screen_test_view().yaw)<.04f&&fabsf(sponsor_screen_test_view().height-.73f)<.02f,"master slot returns to front chest");image(d,c,srv,(prefix+"-sponsors-master.bmp").c_str());
    require(sponsor_screen_test_slot_center(4,slot_x,slot_y),"shorts slot bounds");io.AddMousePosEvent(slot_x,slot_y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
    for(int i=0;i<40;++i)frame(c,target);require(fabsf(sponsor_screen_test_view().height-.44f)<.02f,"shorts uses body-height-normalized camera, not chest crop");image(d,c,srv,(prefix+"-sponsors-shorts.bmp").c_str());
    button(XINPUT_GAMEPAD_Y,c,target);require(sponsor_screen_test_view().full_view,"Y restores complete fixed neutral pose");button(XINPUT_GAMEPAD_A,c,target);require(!sponsor_screen_test_view().full_view,"A re-centers the selected sponsor area");
    auto zoom_before=sponsor_screen_test_view().zoom;pad.Gamepad.bRightTrigger=255;for(int i=0;i<10;++i)frame(c,target);pad={};frame(c,target);require(sponsor_screen_test_view().zoom>zoom_before,"sponsor trigger inspection zoom");
    for(int area:{1,2,5}){require(sponsor_screen_test_slot_center(area,slot_x,slot_y),"remaining sponsor area bounds");io.AddMousePosEvent(slot_x,slot_y);frame(c,target);io.AddMouseButtonEvent(0,true);frame(c,target);io.AddMouseButtonEvent(0,false);frame(c,target);
        for(int i=0;i<45;++i)frame(c,target);auto inspected=sponsor_screen_test_view();float expected_yaw=area==1?1.18f:area==2?-1.18f:0;
        require(inspected.selected==area&&fabsf(inspected.yaw-expected_yaw)<.04f&&inspected.player==sv.player&&inspected.pose==101,"sleeve/supplier camera preserves exact player and neutral rig");image(d,c,srv,(prefix+"-sponsors-area-"+std::to_string(area)+".bmp").c_str());}
    sponsor_screen_device(nullptr);sponsor_screen_device(d);frame(c,target);require(sponsor_screen_test_view().model,"sponsor D3D reset restores CPU batch");
    sponsor_screen_publish(nullptr,0,0,"");frame(c,target);require(!sponsor_screen_test_view().player&&!sponsor_screen_test_view().model,"empty/invalid career clears previous club player immediately");
    auto foreign=real;for(auto&r:foreign)r.team_id+=1;
    sponsor_screen_publish(foreign.data(),foreign.size(),real[0].team_id,"wrong club");frame(c,target);
    require(sponsor_screen_test_view().roster==0,"foreign club roster never borrowed");
    sponsor_screen_publish(real.data(),real.size(),real[0].team_id,"Flamengo");
    for(int i=0;i<300&&!sponsor_screen_test_view().model;++i)frame(c,target);require(sponsor_screen_test_view().model,"career roster recovery");
    int first=sponsor_screen_test_view().player;mod_screen_request_back();frame(c,target);
    require(!mod_screen_is_open()&&mod_screen_captures_input(),"sponsors Back closes only modal, keeps release delay");Sleep(350);
    require(!mod_screen_captures_input()&&mod_screen_open_action(FIFA16_SPONSOR_ACTION),"sponsors can reopen without navigation bridge");
    frame(c,target);require(sponsor_screen_test_view().player!=first,"new visit randomizes player without repeating immediately");
    std::string fixture_path=argv[4];auto split=fixture_path.find_last_of("/\\");
    auto second_club=roster((fixture_path.substr(0,split+1)+"miami_preview.bin").c_str());
    require(second_club[0].team_id!=real[0].team_id,"two independent native club fixtures");
    sponsor_screen_publish(second_club.data(),second_club.size(),second_club[0].team_id,"Inter Miami");frame(c,target);
    require(!sponsor_screen_test_view().model,"club switch immediately drops previous 3D kit/player");
    for(int i=0;i<300&&!sponsor_screen_test_view().model;++i)frame(c,target);sv=sponsor_screen_test_view();
    require(sv.model&&sv.club==second_club[0].team_id&&sv.player==sv.rendered_player&&sv.pose==101,"second club uses its own native player and kit, still neutral");
    require(std::find_if(second_club.begin(),second_club.end(),[&](const auto&r){return r.player_id==sv.player;})!=second_club.end(),"second club player belongs to new roster");
    image(d,c,srv,(prefix+"-sponsors-miami.bmp").c_str());
    mod_screen_close();frame(c,target);Sleep(350);
    TrophyRoomRow cups[8]={};int cup_ids[]={13,14,10,11,12,15,107,65535};
    for(int i=0;i<8;++i){cups[i].competition=cup_ids[i];cups[i].trophy=cup_ids[i];cups[i].logo=cup_ids[i];cups[i].title_asset=cup_ids[i];cups[i].count=i==0?3:i==6?-1:0;}
    trophy_room_publish(cups,8,&real[0],1,2);require(mod_screen_open_action(FIFA_TROPHY_ROOM_ACTION),"trophy native card");
    for(int i=0;i<250&&trophy_room_test_view().models<7;++i)frame(c,target);
    for(int i=0;i<3;++i)frame(c,target);auto tv=trophy_room_test_view();require(tv.rows==8&&tv.models==7,"one mesh per competition, includes zero titles; missing exact model preserved");
    image(d,c,srv,(prefix+"-trophies.bmp").c_str());
    button(XINPUT_GAMEPAD_A,c,target);require(trophy_room_test_view().detail,"Xbox A opens selected trophy");
    for(int i=0;i<3;++i)frame(c,target);image(d,c,srv,(prefix+"-trophy-detail.bmp").c_str());
    Sleep(350);auto old_trophy=trophy_room_test_view();pad.Gamepad.sThumbRX=23000;pad.Gamepad.bRightTrigger=255;
    for(int i=0;i<15;++i)frame(c,target);pad={};frame(c,target);tv=trophy_room_test_view();
    require(tv.yaw!=old_trophy.yaw&&tv.zoom>old_trophy.zoom,"real trophy rotates + zooms by Xbox");
    io.AddMousePosEvent(650,350);frame(c,target);io.AddMouseWheelEvent(0,1);frame(c,target);
    require(trophy_room_test_view().zoom>tv.zoom,"trophy wheel zoom");
    mod_screen_request_back();frame(c,target);require(!trophy_room_test_view().detail&&mod_screen_is_active("trophy-room"),"B/Esc returns to trophy collection, not game");
    Sleep(350);button(XINPUT_GAMEPAD_RIGHT_SHOULDER,c,target);require(trophy_room_test_view().page==1,"LB/RB second collection page");
    image(d,c,srv,(prefix+"-trophies-missing.bmp").c_str());
    io.AddMousePosEvent(650,200);frame(c,target);io.AddMouseButtonEvent(ImGuiMouseButton_Left,true);frame(c,target);
    io.AddMouseButtonEvent(ImGuiMouseButton_Left,false);frame(c,target);
    require(trophy_room_test_view().detail&&trophy_room_test_view().selected==7,"mouse selects missing exact cup without substituting another trophy");
    image(d,c,srv,(prefix+"-trophy-missing-detail.bmp").c_str());mod_screen_request_back();frame(c,target);
    career_operations_device(nullptr);trophy_room_device(nullptr);career_operations_device(d);trophy_room_device(d);frame(c,target);
    require(trophy_room_test_view().rows==8,"D3D reset restores gallery data");
    mod_screen_close();frame(c,target);Sleep(350);require(!mod_screen_captures_input(),"trophy closes with shared cooldown");
    puts("PASSED: strict retirement filters + exact photos/profile, six loan cards, trophies, dynamic sponsors in two clubs + Xbox/keyboard/mouse + isolated styles. Offline fixtures; no save writes.");fflush(stdout);ExitProcess(0);
}
