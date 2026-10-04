#define NOMINMAX
#include "leagues_browser.h"
#include "../../render/assets/fifa_player_assets.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/native_loc_names.h"
#include "../player/player_profile_view.h"
#include "../../ui/common/screen_visuals.h"
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

namespace {
struct LeagueOption {int id=0,nation=0,clubs=0;std::string name,country;};
struct Batch {
    unsigned serial=0;LeagueBrowserSnapshot data={};
    fifa_player::Texture flag,league;
    std::array<fifa_player::Texture,LEAGUE_BROWSER_CUP_CAPACITY>cups;
    std::array<fifa_player::Texture,LEAGUE_BROWSER_LEADER_CAPACITY>goals,assists;
    std::array<std::string,LEAGUE_BROWSER_CUP_CAPACITY>cup_names;
};
std::mutex gate;
LeagueBrowserSnapshot published={},visible={};
unsigned published_revision=0,shown_revision=~0u,catalog_revision=~0u,serial=0;
std::vector<LeagueOption>leagues;
std::vector<std::pair<int,std::string>>countries;
LONG requested_league=0;
bool waiting=false;
HANDLE event=nullptr;
std::string root;
void(*logger)(const char*)=nullptr;
std::shared_ptr<const Batch>ready,shown;
ID3D11Device*device=nullptr;
ID3D11ShaderResourceView*flag_view=nullptr,*league_view=nullptr;
std::array<ID3D11ShaderResourceView*,LEAGUE_BROWSER_CUP_CAPACITY>cup_views={};
std::array<ID3D11ShaderResourceView*,LEAGUE_BROWSER_LEADER_CAPACITY>goal_views={},assist_views={};
int selected_nation=0,selected_league=0,focus=0,table_scroll_focus=0;
DWORD input_at=0,repeat_at=0;WORD previous=0;float requested_scroll=0;

void clear_views(){screen_visuals::release(flag_view);screen_visuals::release(league_view);
    for(auto&v:cup_views)screen_visuals::release(v);for(auto&v:goal_views)screen_visuals::release(v);for(auto&v:assist_views)screen_visuals::release(v);shown.reset();}
const LeagueOption*selected_option(){for(const auto&v:leagues)if(v.id==selected_league&&v.nation==selected_nation)return &v;return nullptr;}
int country_index(int nation){for(size_t i=0;i<countries.size();++i)if(countries[i].first==nation)return (int)i;return -1;}
std::vector<const LeagueOption*>country_leagues(int nation){std::vector<const LeagueOption*>out;for(const auto&v:leagues)if(v.nation==nation)out.push_back(&v);return out;}
void request_data(int id){if(id<=0)return;selected_league=id;waiting=true;requested_scroll=0;InterlockedExchange(&requested_league,id);clubs_browser_request_native_refresh();}
void move_country(int delta){if(countries.empty())return;int i=country_index(selected_nation);if(i<0)i=0;i=(i+delta+(int)countries.size())%(int)countries.size();
    selected_nation=countries[i].first;auto choices=country_leagues(selected_nation);if(!choices.empty())request_data(choices.front()->id);}
void move_league(int delta){auto choices=country_leagues(selected_nation);if(choices.empty())return;int i=0;for(size_t n=0;n<choices.size();++n)if(choices[n]->id==selected_league){i=(int)n;break;}
    i=(i+delta+(int)choices.size())%(int)choices.size();request_data(choices[i]->id);}
void sync_catalog(){unsigned rev=0;size_t count=clubs_browser_copy_catalog(nullptr,0,&rev);if(rev==catalog_revision)return;
    std::vector<ClubBrowserRow>rows(count);if(count)count=clubs_browser_copy_catalog(rows.data(),rows.size(),&rev);rows.resize(count);
    std::vector<LeagueOption>next;for(const auto&r:rows){if(r.league<=0||r.nation<0)continue;auto it=std::find_if(next.begin(),next.end(),[&](const auto&x){return x.id==r.league&&x.nation==r.nation;});
        if(it==next.end()){LeagueOption x;x.id=r.league;x.nation=r.nation;x.name=player_profile::utf8(r.league_name);x.country=player_profile::utf8(r.nation_name);x.clubs=1;next.push_back(std::move(x));}else ++it->clubs;}
    std::stable_sort(next.begin(),next.end(),[](const auto&a,const auto&b){int n=_stricmp(a.country.c_str(),b.country.c_str());if(n)return n<0;n=_stricmp(a.name.c_str(),b.name.c_str());if(n)return n<0;return a.id<b.id;});
    std::vector<std::pair<int,std::string>>next_countries;for(const auto&v:next)if(std::none_of(next_countries.begin(),next_countries.end(),[&](const auto&c){return c.first==v.nation;}))next_countries.emplace_back(v.nation,v.country);
    int old_nation=selected_nation,old_league=selected_league;leagues=std::move(next);countries=std::move(next_countries);catalog_revision=rev;
    bool kept=false;for(const auto&v:leagues)if(v.id==old_league&&v.nation==old_nation){kept=true;break;}
    if(!kept){int own_league=clubs_browser_own_league();auto it=std::find_if(leagues.begin(),leagues.end(),[&](const auto&v){return v.id==own_league;});
        if(it!=leagues.end()){selected_nation=it->nation;request_data(it->id);}else if(!leagues.empty()){selected_nation=leagues.front().nation;request_data(leagues.front().id);}else{selected_nation=selected_league=0;waiting=true;}}
    if(logger&&leagues.empty())logger("OtherLeagues: waiting for the native league catalog");
}
void sync_snapshot(){LeagueBrowserSnapshot next={};unsigned rev=0;{std::lock_guard<std::mutex>g(gate);rev=published_revision;if(rev==shown_revision)return;next=published;}
    visible=next;shown_revision=rev;waiting=visible.league!=selected_league||!visible.league;}
void signal_assets(){std::lock_guard<std::mutex>g(gate);++serial;ready.reset();if(event)SetEvent(event);}
DWORD WINAPI worker(void*){fifa_player::Assets assets(root);native_loc::Names names(root);for(;;){if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;
        auto batch=std::make_shared<Batch>();{std::lock_guard<std::mutex>g(gate);batch->serial=serial;batch->data=published;}
        try{assets.nationality_flag(batch->data.nation,batch->flag);assets.competition_icon(batch->data.league,batch->league);
            for(size_t i=0;i<batch->data.cup_count&&i<batch->cups.size();++i){const auto&cup=batch->data.cups[i];assets.competition_icon(cup.asset>0?cup.asset:cup.competition,batch->cups[i]);
                batch->cup_names[i]=names.competition(cup.asset>0?cup.asset:cup.competition);if(batch->cup_names[i].empty())batch->cup_names[i]="Copa em andamento";}
            for(size_t i=0;i<batch->data.goals_count&&i<batch->goals.size();++i)assets.portrait(batch->data.goals[i].player,batch->goals[i]);
            for(size_t i=0;i<batch->data.assists_count&&i<batch->assists.size();++i)assets.portrait(batch->data.assists[i].player,batch->assists[i]);
        }catch(...){if(logger)logger("OtherLeagues: artwork worker stopped; text data remains available");}
        {std::lock_guard<std::mutex>g(gate);if(batch->serial==serial)ready=std::move(batch);}
    }}
DWORD WINAPI guarded_worker(void*){try{return worker(nullptr);}catch(...){if(logger)logger("OtherLeagues: asset worker failed; selector stays usable");return 1;}}
void sync_assets(){std::shared_ptr<const Batch>next;{std::lock_guard<std::mutex>g(gate);if(ready&&ready->serial==serial)next=ready;}if(!device||!next||next==shown)return;
    clear_views();shown=next;flag_view=screen_visuals::upload(device,next->flag);league_view=screen_visuals::upload(device,next->league);
    for(size_t i=0;i<cup_views.size();++i)cup_views[i]=screen_visuals::upload(device,next->cups[i]);
    for(size_t i=0;i<goal_views.size();++i){goal_views[i]=screen_visuals::upload(device,next->goals[i]);assist_views[i]=screen_visuals::upload(device,next->assists[i]);}}
void publish_header(const char*title){ImGui::SetWindowFontScale(1.4f);ImGui::TextUnformatted(title);ImGui::SetWindowFontScale(1);ImGui::SameLine();ImGui::TextDisabled("Selecione um país e uma liga para consultar a temporada.");ImGui::Separator();}
void draw_selector(int index,const char*label,const std::string&value,ID3D11ShaderResourceView*image,float width){
    ImVec2 at=ImGui::GetCursorScreenPos();float height=126;auto*d=ImGui::GetWindowDrawList();bool active=focus==index;
    d->AddRectFilled(at,{at.x+width,at.y+height},IM_COL32(250,252,253,255),7);d->AddRect(at,{at.x+width,at.y+height},active?IM_COL32(7,94,157,255):IM_COL32(193,207,216,255),7,0,active?2.5f:1.f);
    ImGui::SetCursorScreenPos({at.x+14,at.y+9});ImGui::TextDisabled("%s",label);
    ImGui::SetCursorScreenPos({at.x+10,at.y+45});if(ImGui::Button("‹",{36,42})){focus=index;if(index==0)move_country(-1);else move_league(-1);}
    ImGui::SetCursorScreenPos({at.x+width-46,at.y+45});if(ImGui::Button("›",{36,42})){focus=index;if(index==0)move_country(1);else move_league(1);}
    if(image){ImGui::SetCursorScreenPos({at.x+52,at.y+35});ImGui::Image((ImTextureID)(intptr_t)image,index==0?ImVec2(48,32):ImVec2(36,36));}
    ImGui::SetCursorScreenPos({at.x+52+(image?57:0),at.y+43});ImGui::PushTextWrapPos(at.x+width-52);
    ImGui::TextWrapped("%s",value.empty()?"Carregando...":value.c_str());ImGui::PopTextWrapPos();
    ImGui::SetCursorScreenPos({at.x,at.y+height+12});
}
void draw_table(const LeagueBrowserSnapshot&data,float height){
    ImGui::BeginChild("Classificação##OtherLeagues",ImVec2(0,height),true,ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("CLASSIFICAÇÃO");ImGui::Separator();
    const float widths[]={.07f,.39f,.07f,.07f,.07f,.07f,.08f,.08f,.10f};
    float width=ImGui::GetContentRegionAvail().x;ImVec2 origin=ImGui::GetCursorScreenPos();auto*d=ImGui::GetWindowDrawList();
    const char*headers[]={"#","CLUBE","J","V","E","D","GP","GC","PTS"};float x=origin.x;const float header_h=25,row_h=27;
    d->AddRectFilled(origin,{origin.x+width,origin.y+header_h},IM_COL32(221,234,243,255));
    for(int c=0;c<9;++c){float cell=width*widths[c];ImGui::SetCursorScreenPos({x+4,origin.y+5});ImGui::TextDisabled("%s",headers[c]);x+=cell;}
    ImGui::SetCursorScreenPos({origin.x,origin.y+header_h});
    if(!data.table_available||!data.table_count){ImGui::Spacing();ImGui::TextWrapped("A classificação desta liga ainda não está disponível no calendário carregado pela carreira.");ImGui::EndChild();return;}
    for(size_t i=0;i<data.table_count&&i<LEAGUE_BROWSER_TABLE_CAPACITY;++i){const auto&r=data.table[i];ImVec2 row=ImGui::GetCursorScreenPos();
        if(i%2==0)d->AddRectFilled(row,{row.x+width,row.y+row_h},IM_COL32(246,249,251,255));x=row.x;
        char values[9][128];sprintf_s(values[0],sizeof(values[0]),"%d",r.rank);lstrcpynA(values[1],player_profile::utf8(r.name).c_str(),(int)sizeof(values[1]));
        sprintf_s(values[2],sizeof(values[2]),"%d",r.played);sprintf_s(values[3],sizeof(values[3]),"%d",r.won);sprintf_s(values[4],sizeof(values[4]),"%d",r.drawn);sprintf_s(values[5],sizeof(values[5]),"%d",r.lost);
        sprintf_s(values[6],sizeof(values[6]),"%d",r.goals_for);sprintf_s(values[7],sizeof(values[7]),"%d",r.goals_against);sprintf_s(values[8],sizeof(values[8]),"%d",r.points);
        for(int c=0;c<9;++c){float cell=width*widths[c];ImGui::SetCursorScreenPos({x+4,row.y+5});ImGui::PushTextWrapPos(x+cell-2);ImGui::TextUnformatted(values[c]);ImGui::PopTextWrapPos();x+=cell;}
        ImGui::SetCursorScreenPos({row.x,row.y+row_h});
    }
    if(requested_scroll){ImGui::SetScrollY(std::max(0.f,ImGui::GetScrollY()+requested_scroll));requested_scroll=0;}
    ImGui::EndChild();
}
void draw_leaders(const char*title,const LeagueBrowserLeader*rows,size_t count,bool available,ID3D11ShaderResourceView**faces,float height){
    ImGui::TextUnformatted(title);ImGui::Separator();if(!available||!count){ImGui::TextDisabled("Sem estatísticas registradas nesta competição.");ImGui::Dummy({1,height-32});return;}
    float row_h=(height-32)/3.f;for(size_t i=0;i<count&&i<LEAGUE_BROWSER_LEADER_CAPACITY;++i){ImVec2 at=ImGui::GetCursorScreenPos();auto*d=ImGui::GetWindowDrawList();
        d->AddRectFilled(at,{at.x+ImGui::GetContentRegionAvail().x,at.y+row_h-4},i%2?IM_COL32(249,251,252,255):IM_COL32(237,243,247,255),4);
        const float row_width=ImGui::GetContentRegionAvail().x,row_start_x=ImGui::GetCursorPosX();
        ImGui::SetCursorScreenPos({at.x+6,at.y+5});if(faces[i])ImGui::Image((ImTextureID)(intptr_t)faces[i],{32,row_h-14});else ImGui::Dummy({32,row_h-14});
        ImGui::SameLine(0,6);ImGui::PushTextWrapPos(row_start_x+row_width-42);ImGui::BeginGroup();ImGui::TextWrapped("%s",player_profile::utf8(rows[i].name).c_str());ImGui::TextDisabled("%s",player_profile::utf8(rows[i].team_name).c_str());ImGui::EndGroup();ImGui::PopTextWrapPos();
        char value[16];sprintf_s(value,sizeof(value),"%d",rows[i].value);d->AddText({at.x+row_width-34,at.y+(row_h-ImGui::GetFontSize())*.5f},ImGui::GetColorU32(ImGuiCol_Text),value);
        ImGui::SetCursorScreenPos({at.x,at.y+row_h});}
}
void draw(void*){
    sync_catalog();sync_snapshot();sync_assets();auto&io=ImGui::GetIO();DWORD now=GetTickCount();XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD press=pad.Gamepad.wButtons&~previous;previous=pad.Gamepad.wButtons;bool active=(LONG)(now-input_at)>=0;
    if(active&&(ImGui::IsKeyPressed(ImGuiKey_Escape)||(press&XINPUT_GAMEPAD_B))){mod_screen_request_back();return;}
    if(active){int vertical=0,horizontal=0;if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)||(press&XINPUT_GAMEPAD_DPAD_UP))vertical=-1;if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)||(press&XINPUT_GAMEPAD_DPAD_DOWN))vertical=1;
        if((LONG)(now-repeat_at)>=0){if(!vertical&&abs(pad.Gamepad.sThumbLY)>16000)vertical=pad.Gamepad.sThumbLY>0?1:-1;if(!horizontal&&abs(pad.Gamepad.sThumbLX)>16000)horizontal=pad.Gamepad.sThumbLX>0?1:-1;if(vertical||horizontal)repeat_at=now+190;}
        if(vertical&&focus<2)focus=std::clamp(focus+vertical,0,1);else if(vertical&&focus==2)requested_scroll+=vertical*46.f;
        if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(press&XINPUT_GAMEPAD_DPAD_LEFT))horizontal=-1;if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(press&XINPUT_GAMEPAD_DPAD_RIGHT))horizontal=1;
        if(focus==0&&horizontal)move_country(horizontal);else if(focus==1&&horizontal)move_league(horizontal);
        if(press&XINPUT_GAMEPAD_LEFT_SHOULDER)move_country(-1);if(press&XINPUT_GAMEPAD_RIGHT_SHOULDER)move_country(1);
        if(ImGui::IsKeyPressed(ImGuiKey_Q))move_league(-1);if(ImGui::IsKeyPressed(ImGuiKey_E))move_league(1);
        if(ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space)||(press&XINPUT_GAMEPAD_A))focus=focus<2?2:1;
        if(fabsf(pad.Gamepad.sThumbRY)>6000)requested_scroll-=pad.Gamepad.sThumbRY/32767.f*18.f;
    }
    screen_visuals::begin_fullscreen("Outras ligas##LeagueBrowser",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    publish_header("Outras ligas");float full_w=ImGui::GetContentRegionAvail().x,full_h=ImGui::GetContentRegionAvail().y-34,left_w=std::clamp(full_w*.23f,270.f,355.f);
    ImVec2 base=ImGui::GetCursorScreenPos();ImGui::BeginChild("Seleção de liga##Left",{left_w,full_h},true,ImGuiWindowFlags_NoNavInputs);
    auto*option=selected_option();std::string country=country_index(selected_nation)>=0?countries[country_index(selected_nation)].second:"Carregando países...";
    std::string league_name=option?option->name:"Carregando ligas...";
    draw_selector(0,"PAÍS",country,flag_view,left_w-18);ImGui::Dummy({1,8});draw_selector(1,"LIGA",league_name,league_view,left_w-18);
    ImGui::Spacing();ImGui::Separator();ImGui::TextWrapped("%d clubes nesta liga",option?option->clubs:0);ImGui::Spacing();
    if(waiting||visible.league!=selected_league)ImGui::TextWrapped("Atualizando classificação, calendário e destaques da temporada...");
    else if(!leagues.empty())ImGui::TextWrapped("Dados da temporada atual da carreira. Use as setas para navegar por países e ligas.");
    ImGui::EndChild();ImGui::SameLine(0,14);
    float right_w=ImGui::GetContentRegionAvail().x;ImGui::BeginChild("Visão da liga##Right",{right_w,full_h},false,ImGuiWindowFlags_NoNavInputs);
    ImVec2 header_at=ImGui::GetCursorScreenPos();if(league_view){ImGui::Image((ImTextureID)(intptr_t)league_view,{46,46});ImGui::SameLine(0,12);}
    ImGui::BeginGroup();ImGui::SetWindowFontScale(1.22f);ImGui::TextWrapped("%s",league_name.c_str());ImGui::SetWindowFontScale(1);ImGui::Text("%s  ·  %d clubes",country.c_str(),option?option->clubs:0);ImGui::EndGroup();
    (void)header_at;ImGui::Separator();float body_h=ImGui::GetContentRegionAvail().y;float table_w=right_w*.61f;
    ImGui::BeginChild("Coluna da classificação",{table_w,body_h},false,ImGuiWindowFlags_NoNavInputs);draw_table(visible,body_h-4);
    ImGui::EndChild();ImGui::SameLine(0,12);
    ImGui::BeginChild("Copas e destaques",{0,body_h},true,ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("COPAS VIGENTES");ImGui::Separator();if(!visible.cups_available||!visible.cup_count)ImGui::TextDisabled("Nenhuma copa em andamento encontrada para este país.");
    else for(size_t i=0;i<visible.cup_count&&i<LEAGUE_BROWSER_CUP_CAPACITY;++i){if(cup_views[i])ImGui::Image((ImTextureID)(intptr_t)cup_views[i],{25,25});else ImGui::Dummy({25,25});ImGui::SameLine(0,8);
        auto name=shown?shown->cup_names[i]:std::string("Copa em andamento");ImGui::TextWrapped("%s",player_profile::utf8(name.c_str()).c_str());}
    ImGui::Spacing();float leader_h=std::max(166.f,(body_h-190)*.5f);ImGui::BeginChild("Gols##leaders",{0,leader_h},false,ImGuiWindowFlags_NoNavInputs);
    draw_leaders("MAIS GOLS",visible.goals,visible.goals_count,visible.goals_available,goal_views.data(),leader_h);ImGui::EndChild();
    ImGui::BeginChild("Assistências##leaders",{0,leader_h},false,ImGuiWindowFlags_NoNavInputs);
    draw_leaders("MAIS ASSISTÊNCIAS",visible.assists,visible.assists_count,visible.assists_available,assist_views.data(),leader_h);ImGui::EndChild();ImGui::EndChild();ImGui::EndChild();
    ImGui::SetCursorScreenPos({base.x,base.y+full_h+5});if(ImGui::Button("Voltar (B/Esc)",{170,29}))mod_screen_request_back();ImGui::SameLine(0,14);
    ImGui::SetWindowFontScale(.84f);ImGui::TextUnformatted("Setas: país/liga/tabela  |  LB/RB: país  |  Q/E: liga  |  analógico direito: rolar  |  A: focar tabela  |  B/Esc: voltar");ImGui::SetWindowFontScale(1);
    ImGui::End();
}
void opened(void*){previous=0;focus=0;input_at=GetTickCount()+300;waiting=true;visible={};shown_revision=~0u;selected_nation=selected_league=0;clubs_browser_request_catalog();}
void closed(void*){InterlockedExchange(&requested_league,0);waiting=false;clear_views();std::lock_guard<std::mutex>g(gate);++serial;ready.reset();published={};++published_revision;}
BOOL back(void*){return FALSE;}
}
extern "C" BOOL leagues_browser_take_data_request(int*league){if(!league)return FALSE;LONG value=InterlockedExchange(&requested_league,0);if(value<=0)return FALSE;*league=(int)value;return TRUE;}
extern "C" void leagues_browser_publish(const LeagueBrowserSnapshot*data){if(!data)return;std::lock_guard<std::mutex>g(gate);published=*data;++published_revision;}
bool leagues_browser_register(const char*game_root,void(*log)(const char*)){root=game_root?game_root:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE thread=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"other-leagues",FIFA16_LEAGUES_BROWSER_ACTION,opened,draw,closed,nullptr,back};return mod_screen_register(&screen)!=FALSE;}
void leagues_browser_device(ID3D11Device*d){if(d==device)return;clear_views();if(device)device->Release();device=d;if(d)d->AddRef();}
#ifdef LEAGUES_BROWSER_TEST
LeaguesBrowserTestView leagues_browser_test_view(){return {selected_nation,selected_league,focus,visible.table_count,visible.cup_count,visible.goals_count,visible.assists_count,waiting};}
bool leagues_browser_test_center(int i,float&x,float&y){(void)i;(void)x;(void)y;return false;}
#endif
