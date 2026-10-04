#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "player_search_screen.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include "../../render/assets/fifa_player_assets.h"
#include "player_profile_view.h"
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <mutex>
#include <memory>
#include <string>
#include <vector>
#include <unordered_map>

namespace {
std::mutex guard;
std::vector<PlayerSearchIndexRow> published;
unsigned revision=0,visible_revision=~0u;
volatile LONG index_request=0,index_request_serial=0;
volatile LONG detail_request=0,detail_request_player=0,detail_request_team=0;
volatile LONG detail_request_number=-1,detail_request_position=-1,detail_request_serial=0;
unsigned active_index_serial=0,active_detail_serial=0;
bool index_ready=false,index_loading=false,detail_ready=false,detail_found=false;
PlayerSearchDetail detail_result={};unsigned detail_result_serial=0;
std::vector<PlayerSearchIndexRow> visible;
std::vector<size_t> filtered;
int selected=0,pending_player=0,pending_team=0,pending_number=-1,pending_position=-1;
bool waiting_detail=false,keyboard=false;
int keyboard_index=0;
char query[128]={};std::string last_query,message,root;
DWORD input_at=0,repeat_at=0;WORD previous=0;
HANDLE visual_event=nullptr;unsigned visual_serial=0;
std::vector<unsigned>requested_players;std::vector<int>requested_teams;
struct VisualBatch {unsigned serial=0;std::unordered_map<unsigned,fifa_player::Texture>faces;std::unordered_map<int,fifa_player::Texture>crests;};
std::shared_ptr<const VisualBatch>visual_ready,visual_shown;
ID3D11Device*device=nullptr;
std::unordered_map<unsigned,ID3D11ShaderResourceView*>face_views;
std::unordered_map<int,ID3D11ShaderResourceView*>crest_views;
ImVec2 result_centers[12]={};
void(*logger)(const char*)=nullptr;

std::string fold(const std::string&s){
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),nullptr,0);
    if(!n)return s;std::vector<wchar_t>w(n);MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),(int)s.size(),w.data(),n);
    int count=LCMapStringEx(LOCALE_NAME_INVARIANT,LCMAP_LOWERCASE,w.data(),n,nullptr,0,nullptr,nullptr,0);
    if(!count)return s;std::vector<wchar_t>lower(count);LCMapStringEx(LOCALE_NAME_INVARIANT,LCMAP_LOWERCASE,w.data(),n,lower.data(),count,nullptr,nullptr,0);
    for(auto&c:lower){if(wcschr(L"àáâãäå",c))c=L'a';else if(wcschr(L"èéêë",c))c=L'e';else if(wcschr(L"ìíîï",c))c=L'i';
        else if(wcschr(L"òóôõö",c))c=L'o';else if(wcschr(L"ùúûü",c))c=L'u';else if(c==L'ç')c=L'c';else if(c==L'ñ')c=L'n';}
    int bytes=WideCharToMultiByte(CP_UTF8,0,lower.data(),count,nullptr,0,nullptr,nullptr);std::string out(bytes,'\0');
    if(bytes)WideCharToMultiByte(CP_UTF8,0,lower.data(),count,&out[0],bytes,nullptr,nullptr);return out;
}
void refilter(){
    filtered.clear();std::string needle=fold(player_profile::utf8(query));
    if(needle.size()<2){selected=0;last_query=query;return;}
    for(size_t i=0;i<visible.size();++i){const auto&r=visible[i];
        if(fold(player_profile::utf8(r.name)).find(needle)!=std::string::npos||
           fold(player_profile::utf8(r.team_name)).find(needle)!=std::string::npos)filtered.push_back(i);}
    selected=std::max(0,std::min(selected,(int)filtered.size()-1));last_query=query;
}
void request_index(){
    unsigned serial=(unsigned)InterlockedIncrement(&index_request_serial);
    {std::lock_guard<std::mutex>lock(guard);active_index_serial=serial;index_loading=true;index_ready=false;message.clear();}
    InterlockedExchange(&index_request,1);player_search_screen_request_native_refresh();
}
void request_profile(){
    if(filtered.empty()||waiting_detail)return;selected=std::max(0,std::min(selected,(int)filtered.size()-1));
    const auto&r=visible[filtered[selected]];pending_player=r.player_id;pending_team=r.team_id;pending_number=r.number;pending_position=r.position;
    unsigned serial=(unsigned)InterlockedIncrement(&detail_request_serial);{std::lock_guard<std::mutex>lock(guard);active_detail_serial=serial;detail_ready=false;}
    waiting_detail=true;message="Carregando perfil do jogador...";
    InterlockedExchange(&detail_request_player,pending_player);InterlockedExchange(&detail_request_team,pending_team);
    InterlockedExchange(&detail_request_number,pending_number);InterlockedExchange(&detail_request_position,pending_position);
    InterlockedExchange(&detail_request,1);player_search_screen_request_native_refresh();
}
void clear_visuals(){
    for(auto&x:face_views)screen_visuals::release(x.second);face_views.clear();
    for(auto&x:crest_views)screen_visuals::release(x.second);crest_views.clear();visual_shown.reset();
}
void request_visuals(const std::vector<unsigned>&players,const std::vector<int>&teams){
    {std::lock_guard<std::mutex>lock(guard);if(players==requested_players&&teams==requested_teams)return;
        requested_players=players;requested_teams=teams;++visual_serial;visual_ready.reset();}
    if(visual_event)SetEvent(visual_event);
}
DWORD WINAPI visual_worker(void*){
    fifa_player::Assets assets(root);
    for(;;){if(WaitForSingleObject(visual_event,INFINITE)!=WAIT_OBJECT_0)return 0;
        std::vector<unsigned>players;std::vector<int>teams;unsigned serial;
        {std::lock_guard<std::mutex>lock(guard);players=requested_players;teams=requested_teams;serial=visual_serial;}
        auto batch=std::make_shared<VisualBatch>();batch->serial=serial;bool cancelled=false;
        for(unsigned id:players){
            {std::lock_guard<std::mutex>lock(guard);if(serial!=visual_serial){cancelled=true;break;}}
            fifa_player::Texture texture;if(assets.portrait((int)id,texture))batch->faces.emplace(id,std::move(texture));
        }
        if(cancelled){assets.clear_portrait_cache();continue;}
        for(int id:teams)if(id>0){fifa_player::Texture texture;if(assets.crest(id,texture))batch->crests.emplace(id,std::move(texture));}
        assets.clear_portrait_cache();
        {std::lock_guard<std::mutex>lock(guard);if(serial==visual_serial)visual_ready=std::move(batch);}
    }
}
DWORD WINAPI guarded_visual_worker(void*p){try{return visual_worker(p);}catch(...){if(logger)logger("PlayerSearch: asset worker failed; list remains available without images");return 1;}}
void sync_visuals(){
    std::shared_ptr<const VisualBatch>next;{std::lock_guard<std::mutex>lock(guard);if(visual_ready&&visual_ready->serial==visual_serial)next=visual_ready;}
    if(!device||!next||next==visual_shown)return;clear_visuals();visual_shown=next;
    for(const auto&i:next->faces)if(auto*v=screen_visuals::upload(device,i.second))face_views.emplace(i.first,v);
    for(const auto&i:next->crests)if(auto*v=screen_visuals::upload(device,i.second))crest_views.emplace(i.first,v);
}
void sync_index(){
    std::lock_guard<std::mutex>lock(guard);
    if(visible_revision!=revision){visible=published;visible_revision=revision;index_loading=false;selected=0;last_query.clear();refilter();}
}
void sync_detail(){
    if(!waiting_detail)return;
    PlayerSearchDetail d={};bool found=false;unsigned serial=0;
    {std::lock_guard<std::mutex>lock(guard);if(detail_ready&&detail_result_serial==active_detail_serial){d=detail_result;found=detail_found;serial=detail_result_serial;detail_ready=false;}}
    if(!serial)return;waiting_detail=false;
    if(!found||d.player.player_id!=pending_player){message="Não foi possível abrir o perfil deste jogador.";return;}
    d.player.number=pending_number;d.player.squad_position=pending_position;
    if(!club_player_screen_open_search_profile(&d.player,d.team_name)){message="Não foi possível abrir o perfil agora. Tente novamente.";return;}
    message.clear();
}
BOOL back(void*){
    if((LONG)(GetTickCount()-input_at)<0)return TRUE;
    if(keyboard){keyboard=false;input_at=GetTickCount()+200;return TRUE;}
    if(waiting_detail){waiting_detail=false;message.clear();unsigned serial=(unsigned)InterlockedIncrement(&detail_request_serial);
        {std::lock_guard<std::mutex>lock(guard);active_detail_serial=serial;detail_ready=false;}input_at=GetTickCount()+200;return TRUE;}
    return FALSE;
}
void opened(void*){
    previous=0;input_at=GetTickCount()+250;waiting_detail=false;message.clear();keyboard=false;
    sync_index();if(!index_ready)request_index();
}
void closed(void*){
    waiting_detail=false;keyboard=false;unsigned serial=(unsigned)InterlockedIncrement(&detail_request_serial);clear_visuals();
    {std::lock_guard<std::mutex>lock(guard);active_detail_serial=serial;detail_ready=false;++visual_serial;visual_ready.reset();requested_players.clear();requested_teams.clear();}
}
void add_character(const char*s){if(!s)return;size_t n=strlen(query),m=strlen(s);if(n+m<sizeof(query)-1){strcat_s(query,s);last_query.clear();refilter();}}
void erase_character(){size_t n=strlen(query);if(n){do{--n;}while(n&&(query[n]&0xc0)==0x80);query[n]=0;last_query.clear();refilter();}}
const char*keyboard_keys[]={"A","B","C","D","E","F","G","H","I","J","K","L","M","N","O","P","Q","R","S","T","U","V","W","X","Y","Z","0","1","2","3","4","5","6","7","8","9","Á","É","Í","Ó","Ú","Ã","Õ","Ç","ESPAÇO","APAGAR","OK"};
void draw(void*){
    sync_index();sync_detail();sync_visuals();
    auto&io=ImGui::GetIO();DWORD now=GetTickCount();XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD pressed=pad.Gamepad.wButtons&~previous;previous=pad.Gamepad.wButtons;bool active=(LONG)(now-input_at)>=0;
    if(active&&ImGui::IsKeyPressed(ImGuiKey_Escape)){if(keyboard){keyboard=false;input_at=now+200;}else mod_screen_request_back();return;}
    if(active&&(pressed&XINPUT_GAMEPAD_B)){if(keyboard){keyboard=false;input_at=now+200;}else mod_screen_request_back();return;}
    if(active&&keyboard){
        int dx=(pressed&XINPUT_GAMEPAD_DPAD_RIGHT)?1:(pressed&XINPUT_GAMEPAD_DPAD_LEFT)?-1:0;
        int dy=(pressed&XINPUT_GAMEPAD_DPAD_DOWN)?1:(pressed&XINPUT_GAMEPAD_DPAD_UP)?-1:0;
        if((dx||dy)&&(LONG)(now-repeat_at)>=0){keyboard_index=(keyboard_index+dy*9+dx+(int)std::size(keyboard_keys))%(int)std::size(keyboard_keys);repeat_at=now+160;}
        if(pressed&XINPUT_GAMEPAD_A){if(keyboard_index==std::size(keyboard_keys)-1)keyboard=false;else if(keyboard_index==std::size(keyboard_keys)-2)erase_character();else add_character(keyboard_keys[keyboard_index]);}
    }else if(active&&!waiting_detail){
        int step=0;if(pressed&XINPUT_GAMEPAD_DPAD_UP)step=-1;if(pressed&XINPUT_GAMEPAD_DPAD_DOWN)step=1;
        if(abs(pad.Gamepad.sThumbLY)>16000&&(LONG)(now-repeat_at)>=0){step=pad.Gamepad.sThumbLY>0?-1:1;repeat_at=now+150;}
        if(step&&!filtered.empty())selected=(selected+step+(int)filtered.size())%(int)filtered.size();
        if((pressed&(XINPUT_GAMEPAD_X|XINPUT_GAMEPAD_Y))!=0)keyboard=true;
        if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)&&!filtered.empty())selected=(selected+(int)filtered.size()-1)%(int)filtered.size();
        if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)&&!filtered.empty())selected=(selected+1)%(int)filtered.size();
        if(ImGui::IsKeyPressed(ImGuiKey_Enter)&&!filtered.empty())request_profile();
        if((pressed&XINPUT_GAMEPAD_A)&&!filtered.empty())request_profile();
    }
    if(strcmp(query,last_query.c_str())!=0)refilter();
    screen_visuals::LightTheme theme;
    screen_visuals::begin_fullscreen("Buscar jogador##PlayerSearch",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.42f);ImGui::TextUnformatted("Buscar jogador");ImGui::SetWindowFontScale(1);
    ImGui::TextUnformatted("Pesquise na base de dados e selecione um jogador para abrir o perfil.");
    ImGui::Spacing();ImGui::SetNextItemWidth(std::min(560.f,ImGui::GetContentRegionAvail().x-150));
    if(ImGui::InputText("##Nome do jogador",query,sizeof(query))){last_query.clear();refilter();}
    ImGui::SameLine();if(ImGui::Button(keyboard?"Fechar teclado (Y)":"Teclado (Y)",{136,0}))keyboard=!keyboard;
    if(index_loading)ImGui::TextUnformatted("Carregando jogadores da base do jogo...");
    else if(!index_ready)ImGui::TextUnformatted("A base de jogadores ainda não foi carregada.");
    else if(strlen(query)<2)ImGui::Text("%zu jogadores indexados. Digite ao menos 2 caracteres.",visible.size());
    else ImGui::Text("Resultados: %zu",filtered.size());
    float list_height=std::max(90.f,ImGui::GetContentRegionAvail().y-66);
    if(ImGui::BeginChild("Resultados da busca",ImVec2(0,list_height),true,ImGuiWindowFlags_NoNavInputs)){
        ImGui::TextColored(ImVec4(.20f,.38f,.50f,1),"FOTO       CLUBE       JOGADOR                                                       IDADE");ImGui::Separator();
        if(strlen(query)<2)ImGui::TextUnformatted("Comece digitando o nome do jogador.");
        else if(filtered.empty())ImGui::TextUnformatted("Nenhum jogador encontrado com esse nome.");
        else {
            const float row_h=62.f;ImGuiListClipper clip;clip.Begin((int)filtered.size(),row_h);std::vector<unsigned>face_ids;std::vector<int>club_ids;
            while(clip.Step()){ImGui::SetCursorPosY(clip.DisplayStart*row_h);for(int n=clip.DisplayStart;n<clip.DisplayEnd;++n){
                const auto&r=visible[filtered[n]];ImGui::PushID(r.player_id);
                ImVec2 at=ImGui::GetCursorScreenPos();float w=ImGui::GetContentRegionAvail().x;
                bool is_selected=n==selected;ImGui::InvisibleButton("##linha",ImVec2(w,row_h-4));bool hovered=ImGui::IsItemHovered();
                if(hovered&&ImGui::IsMouseClicked(ImGuiMouseButton_Left)){selected=n;request_profile();}
                auto*dl=ImGui::GetWindowDrawList();dl->AddRectFilled(at,{at.x+w,at.y+row_h-4},is_selected?IM_COL32(225,239,248,255):IM_COL32(247,249,250,255),4);
                dl->AddRect(at,{at.x+w,at.y+row_h-4},is_selected?IM_COL32(6,98,160,255):IM_COL32(221,228,232,255),4,0,is_selected?2.f:1.f);
                auto face=face_views.find((unsigned)r.player_id);if(face!=face_views.end()&&face->second)dl->AddImage((ImTextureID)(intptr_t)face->second,{at.x+8,at.y+5},{at.x+48,at.y+55});
                else {dl->AddCircleFilled({at.x+28,at.y+19},8,IM_COL32(177,190,197,255));dl->AddRectFilled({at.x+15,at.y+29},{at.x+41,at.y+52},IM_COL32(177,190,197,255),8);}
                auto crest=crest_views.find(r.team_id);if(r.team_id>0&&crest!=crest_views.end()&&crest->second)dl->AddImage((ImTextureID)(intptr_t)crest->second,{at.x+57,at.y+14},{at.x+87,at.y+44});
                float tx=at.x+98;std::string name=player_profile::utf8(r.name),club=player_profile::utf8(r.team_name);
                dl->PushClipRect({tx,at.y},{at.x+w-72,at.y+row_h},true);dl->AddText({tx,at.y+9},IM_COL32(28,75,104,255),name.c_str());
                dl->AddText({tx,at.y+33},IM_COL32(97,119,130,255),club.empty()?"Sem clube":club.c_str());dl->PopClipRect();
                char age[24];if(r.age>=0&&r.age<=100)sprintf_s(age,"%d anos",r.age);else strcpy_s(age,"—");
                ImVec2 age_size=ImGui::CalcTextSize(age);dl->AddText({at.x+w-age_size.x-14,at.y+22},IM_COL32(40,76,98,255),age);
                result_centers[n%12]={at.x+w*.5f,at.y+row_h*.5f};face_ids.push_back((unsigned)r.player_id);if(r.team_id>0)club_ids.push_back(r.team_id);ImGui::PopID();
            }}
            request_visuals(face_ids,club_ids);
        }
    }ImGui::EndChild();
    if(waiting_detail)ImGui::TextUnformatted("Carregando perfil do jogador...");else if(!message.empty())ImGui::TextWrapped("%s",message.c_str());
    if(keyboard){ImGui::Separator();ImGui::TextUnformatted("Teclado virtual — A seleciona, B fecha, setas navegam");
        for(int i=0;i<(int)std::size(keyboard_keys);++i){if(i%9)ImGui::SameLine();bool focus=i==keyboard_index;
            if(focus){ImGui::PushStyleColor(ImGuiCol_Button,IM_COL32(10,93,153,255));ImGui::PushStyleColor(ImGuiCol_Text,IM_COL32(255,255,255,255));}
            if(ImGui::Button(keyboard_keys[i],ImVec2(63,25))){keyboard_index=i;if(i==(int)std::size(keyboard_keys)-1)keyboard=false;else if(i==(int)std::size(keyboard_keys)-2)erase_character();else add_character(keyboard_keys[i]);}
            if(focus)ImGui::PopStyleColor(2);}
    }
    ImGui::Separator();ImGui::TextUnformatted("Digite para pesquisar | Cima/baixo: jogador | A/Enter/clique: abrir perfil | X/Y: teclado | B/Esc: voltar");
    ImGui::SameLine();if(ImGui::Button("Voltar (B/Esc)"))mod_screen_request_back();ImGui::End();
}
}
extern "C" BOOL player_search_screen_take_index_request(unsigned*serial){if(!serial||!InterlockedExchange(&index_request,0))return FALSE;*serial=(unsigned)InterlockedCompareExchange(&index_request_serial,0,0);return *serial!=0;}
extern "C" void player_search_screen_publish_index(const PlayerSearchIndexRow*rows,size_t count,unsigned serial,int valid){
    std::vector<PlayerSearchIndexRow>next;if(rows&&count<=PLAYER_SEARCH_RESULT_CAPACITY)next.assign(rows,rows+count);
    std::stable_sort(next.begin(),next.end(),[](const auto&a,const auto&b){int order=_stricmp(a.name,b.name);return order?order<0:a.player_id<b.player_id;});
    std::lock_guard<std::mutex>lock(guard);if(serial!=active_index_serial)return;published=std::move(next);++revision;index_ready=valid!=0;index_loading=false;
}
extern "C" BOOL player_search_screen_take_detail_request(int*player,int*team,int*number,int*position,unsigned*serial){
    if(!player||!team||!number||!position||!serial||!InterlockedExchange(&detail_request,0))return FALSE;
    *player=(int)InterlockedCompareExchange(&detail_request_player,0,0);*team=(int)InterlockedCompareExchange(&detail_request_team,0,0);
    *number=(int)InterlockedCompareExchange(&detail_request_number,0,0);*position=(int)InterlockedCompareExchange(&detail_request_position,0,0);
    *serial=(unsigned)InterlockedCompareExchange(&detail_request_serial,0,0);return *player>0&&*serial!=0;
}
extern "C" void player_search_screen_publish_detail(const PlayerSearchDetail*detail,unsigned serial,int found){
    std::lock_guard<std::mutex>lock(guard);if(serial!=active_detail_serial)return;detail_found=found!=0;detail_result=detail?*detail:PlayerSearchDetail{};
    detail_result_serial=serial;detail_ready=true;
}
extern "C" void player_search_screen_invalidate(void){
    InterlockedExchange(&index_request,0);unsigned serial=(unsigned)InterlockedIncrement(&index_request_serial);
    std::lock_guard<std::mutex>lock(guard);published.clear();++revision;active_index_serial=serial;index_ready=false;index_loading=false;
}
bool player_search_screen_register(const char*game_root,void(*log)(const char*)){
    root=game_root?game_root:"";logger=log;visual_event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!visual_event)return false;
    HANDLE t=CreateThread(nullptr,0,guarded_visual_worker,nullptr,0,nullptr);if(!t){CloseHandle(visual_event);visual_event=nullptr;return false;}CloseHandle(t);
    const ModOverlayScreen screen={"player-search",FIFA16_PLAYER_SEARCH_ACTION,opened,draw,closed,nullptr,back};return mod_screen_register(&screen)!=FALSE;
}
void player_search_screen_set_device(ID3D11Device*d){if(d==device)return;clear_visuals();if(device)device->Release();device=d;if(d)d->AddRef();}
