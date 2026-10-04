#define NOMINMAX
#include "sponsor_screen.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../player/club_player_profile.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include <mutex>
#include <algorithm>
#include <cstring>
#include <cmath>

namespace {
constexpr unsigned neutral_pose=101;
struct Slot {const char*name;const char*description;float yaw;fifa_player::CameraFocus focus;};
const Slot slots[]={
    {"Master / peito","Área principal na frente da camisa.",0,{.73f,0,.34f}},
    {"Manga direita","Área da manga direita do jogador.",1.18f,{.80f,-.06f,.30f}},
    {"Manga esquerda","Área da manga esquerda do jogador.",-1.18f,{.80f,.06f,.30f}},
    {"Costas / omoplata","Parte superior das costas da camisa.",3.14159265f,{.79f,0,.35f}},
    {"Calção","Área frontal do calção.",0,{.44f,0,.33f}},
    {"Fornecedor esportivo","Área superior do peito, junto ao fornecedor do kit.",0,{.84f,0,.28f}}
};
std::mutex mutex;
std::string root,published_name,team;
std::vector<ClubPlayerRow>published,visible;
int published_club=0,club=0,player=0,selected=0;
unsigned revision=0,shown_revision=~0u,serial=0,random_state=0;
volatile LONG refresh_requested=0;
HANDLE event=nullptr;void(*logger)(const char*)=nullptr;
struct Request {unsigned serial=0;ClubPlayerRow row={};};
struct Batch {unsigned serial=0;int club=0,player=0;fifa_player::Texture crest,portrait;std::shared_ptr<const fifa_player::Model>model;};
Request request;std::shared_ptr<const Batch>ready,shown;
fifa_player::Renderer renderer;
ID3D11Device*device=nullptr;ID3D11ShaderResourceView*crest=nullptr,*portrait=nullptr;
DWORD input_after=0,repeat=0;
WORD previous_buttons=0;
float camera_yaw=0,camera_zoom=1;fifa_player::CameraFocus camera_focus=slots[0].focus;
bool full_view=false;
#ifdef CAREER_OPS_SCREEN_TEST
ImVec2 slot_centers[_countof(slots)]={};
#endif

void clear_views(){screen_visuals::release(crest);screen_visuals::release(portrait);renderer.clear();shown.reset();}
DWORD WINAPI worker(void*){
    fifa_player::Assets assets(root);
    for(;;){
        if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;
        Request r;{std::lock_guard<std::mutex>guard(mutex);r=request;}
        if(r.row.player_id<=0||r.row.team_id<=0)continue;
        auto b=std::make_shared<Batch>();b->serial=r.serial;b->club=r.row.team_id;b->player=r.row.player_id;
        try {
            auto model=std::make_shared<fifa_player::Model>(assets.load(r.row));
            if(!model->parts.empty()&&fifa_player::apply_presentation_pose(*model,false,nullptr,neutral_pose))b->model=model;
            assets.crest(b->club,b->crest);
            assets.portrait(b->player,b->portrait);
        }catch(...){if(logger)logger("Sponsors: native assets unavailable; no game/save mutation");}
        {std::lock_guard<std::mutex>guard(mutex);if(r.serial!=serial)continue;ready=b;}
        if(logger)logger(("Sponsors: club="+std::to_string(b->club)+" player="+std::to_string(b->player)+
            " pose=101 native_model="+std::to_string(bool(b->model))+"; six placeholder slots, read-only").c_str());
    }
}
DWORD WINAPI guarded_worker(void*p){try{return worker(p);}catch(...){if(logger)logger("Sponsors: asset worker stopped safely; no save writes");return 0;}}
void choose_player(){
    if(visible.empty()){player=0;return;}
    if(!random_state)random_state=GetTickCount()^GetCurrentProcessId()^0x9e3779b9u;
    random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;
    std::vector<const ClubPlayerRow*>eligible;
    for(const auto&r:visible)if(visible.size()==1||r.player_id!=player)eligible.push_back(&r);
    player=eligible.empty()?visible.front().player_id:eligible[random_state%eligible.size()]->player_id;
}
void queue(){
    auto it=std::find_if(visible.begin(),visible.end(),[](const auto&r){return r.player_id==player;});
    clear_views();std::lock_guard<std::mutex>guard(mutex);++serial;ready.reset();request={};request.serial=serial;
    if(it!=visible.end()){request.row=*it;SetEvent(event);}
}
void sync(){
    bool changed=false;int old_club=club;std::shared_ptr<const Batch>b;unsigned current;
    {std::lock_guard<std::mutex>guard(mutex);
        if(shown_revision!=revision){visible=published;club=published_club;team=published_name;shown_revision=revision;changed=true;}
        b=ready;current=serial;
    }
    if(changed){
        auto it=std::find_if(visible.begin(),visible.end(),[](const auto&r){return r.player_id==player;});
        if(old_club!=club||it==visible.end())choose_player();
        /* Rebuild only for changed owned data; never randomize during drawing. */
        queue();return;
    }
    if(device&&b&&b!=shown&&b->serial==current&&b->club==club&&b->player==player){
        clear_views();shown=b;crest=screen_visuals::upload(device,b->crest);portrait=screen_visuals::upload(device,b->portrait);
    }
}
void opened(void*){
    selected=0;repeat=0;previous_buttons=0;camera_yaw=0;camera_zoom=1;camera_focus=slots[0].focus;full_view=false;input_after=GetTickCount()+350;
    {std::lock_guard<std::mutex>guard(mutex);visible=published;club=published_club;team=published_name;shown_revision=revision;}
    choose_player();queue();InterlockedExchange(&refresh_requested,1);
}
void closed(void*){clear_views();std::lock_guard<std::mutex>guard(mutex);++serial;ready.reset();request={};}
void input(){
    XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD now=pad.Gamepad.wButtons,pressed=now&~previous_buttons;previous_buttons=now;DWORD tick=GetTickCount();if(tick<input_after)return;
    int move=0;
    if(tick>=repeat){
        if((now&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX<-18000)move=-1;
        if((now&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>18000)move=1;
        if((now&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>18000)move=-2;
        if((now&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY<-18000)move=2;
        if(move)repeat=tick+180;
    }
    if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow))move=-1;if(ImGui::IsKeyPressed(ImGuiKey_RightArrow))move=1;
    if(ImGui::IsKeyPressed(ImGuiKey_UpArrow))move=-2;if(ImGui::IsKeyPressed(ImGuiKey_DownArrow))move=2;
    int next=std::clamp(selected+move,0,(int)_countof(slots)-1);if(next!=selected){selected=next;full_view=false;camera_zoom=1;}
    if((pressed&XINPUT_GAMEPAD_Y)||ImGui::IsKeyPressed(ImGuiKey_F))full_view=!full_view;
    if((pressed&XINPUT_GAMEPAD_A)||ImGui::IsKeyPressed(ImGuiKey_Enter)){full_view=false;camera_zoom=1;}
    float dt=std::clamp(ImGui::GetIO().DeltaTime,0.f,.05f);
    camera_zoom=std::clamp(camera_zoom+(std::max(0,int(pad.Gamepad.bRightTrigger)-30)-std::max(0,int(pad.Gamepad.bLeftTrigger)-30))/225.f*dt*.6f,.65f,2.f);
}
void draw(void*){
    sync();input();screen_visuals::LightTheme theme;const auto size=ImGui::GetIO().DisplaySize;
    ImGui::SetNextWindowPos({size.x*.025f,size.y*.025f});ImGui::SetNextWindowSize({size.x*.95f,size.y*.95f});
    ImGui::Begin("Patrocinadores do clube",nullptr,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    if(crest){ImGui::Image((ImTextureID)(intptr_t)crest,{48,48});ImGui::SameLine();}
    ImGui::BeginGroup();ImGui::SetWindowFontScale(1.4f);ImGui::TextUnformatted("PATROCINADORES DO CLUBE");
    ImGui::SetWindowFontScale(1);ImGui::TextUnformatted(team.empty()?"Aguardando clube da carreira":team.c_str());ImGui::EndGroup();
    ImGui::Separator();
    ImVec2 area=ImGui::GetContentRegionAvail();float left=std::max(100.f,area.x*.42f),height=std::max(100.f,area.y-36);
    ImGui::BeginChild("Jogador do clube",{left,height},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    auto at=ImGui::GetCursorScreenPos();ImVec2 stage(left-16,std::max(40.f,height-74));auto*d=ImGui::GetWindowDrawList();
    ImVec4 pale(.94f,.95f,.95f,1);
    auto found=std::find_if(visible.begin(),visible.end(),[](const auto&r){return r.player_id==player;});
    if(found!=visible.end()&&found->club_colors_valid){unsigned rgb=found->club_colors[0];
        pale={.91f+.07f*((rgb>>16)&255)/255.f,.91f+.07f*((rgb>>8)&255)/255.f,.91f+.07f*(rgb&255)/255.f,1};}
    d->AddRectFilled(at,{at.x+stage.x,at.y+stage.y},ImGui::ColorConvertFloat4ToU32(pale),5);
    if(crest){float s=std::min(stage.x*.58f,220.f);d->AddImage((ImTextureID)(intptr_t)crest,
        {at.x+(stage.x-s)*.5f,at.y+stage.y*.12f},{at.x+(stage.x+s)*.5f,at.y+stage.y*.12f+s},{0,0},{1,1},IM_COL32(255,255,255,24));}
    float dt=std::clamp(ImGui::GetIO().DeltaTime,0.f,.05f),blend=1.f-expf(-dt*10.f);auto target=slots[selected].focus;
    float target_yaw=slots[selected].yaw;
    if((selected==1||selected==2)&&shown&&shown->model&&found!=visible.end()){
        const auto&shoulder=selected==1?shown->model->right_shoulder:shown->model->left_shoulder;
        if(std::isfinite(shoulder.x)&&std::isfinite(shoulder.z)&&fabsf(shoulder.x)>1){
            target_yaw=shoulder.x>0?-1.18f:1.18f;
            // Aim at the actual native sleeve, not the middle of the torso.
            target.horizontal_ratio=(shoulder.x*cosf(target_yaw)+shoulder.z*sinf(target_yaw))/std::max(130.f,(float)found->height);
        }
    }
    camera_yaw+=std::remainder((full_view?0:target_yaw)-camera_yaw,6.2831853f)*blend;
    camera_focus.height_ratio+=(target.height_ratio-camera_focus.height_ratio)*blend;
    camera_focus.horizontal_ratio+=(target.horizontal_ratio-camera_focus.horizontal_ratio)*blend;
    camera_focus.span_ratio+=(target.span_ratio-camera_focus.span_ratio)*blend;
    if(ImGui::IsMouseHoveringRect(at,{at.x+stage.x,at.y+stage.y}))camera_zoom=std::clamp(camera_zoom+ImGui::GetIO().MouseWheel*.08f,.65f,2.f);
    if(shown&&shown->model&&renderer.model(shown->model)&&renderer.render((UINT)stage.x,(UINT)stage.y,camera_yaw,camera_zoom,false,0,0,true,.50f,full_view?nullptr:&camera_focus))
        d->AddImage((ImTextureID)(intptr_t)renderer.image(),at,{at.x+stage.x,at.y+stage.y});
    else d->AddText({at.x+18,at.y+stage.y*.5f},IM_COL32(86,104,110,255),visible.empty()?"Aguardando elenco da carreira...":shown?"Modelo 3D indisponível":"Carregando jogador nativo...");
    ImGui::Dummy(stage);
    if(found!=visible.end()){
        if(portrait){ImGui::Image((ImTextureID)(intptr_t)portrait,{56,56});ImGui::SameLine(0,12);}
        ImGui::BeginGroup();ImGui::SetWindowFontScale(1.12f);ImGui::TextUnformatted(found->name);ImGui::SetWindowFontScale(1);
        if(found->number>0)ImGui::Text("%d  |  %s",found->number,club_profile::position(found->position));
        else ImGui::TextUnformatted(club_profile::position(found->position));ImGui::EndGroup();
    }
    ImGui::EndChild();ImGui::SameLine(0,16);
    ImGui::BeginChild("Espaços de patrocínio",{0,height},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("ESPAÇOS DE PATROCÍNIO");ImGui::Spacing();
    float width=std::max(30.f,(ImGui::GetContentRegionAvail().x-12)*.5f);
    float cell_height=std::max(50.f,std::min(140.f,(height-142)/3));
    for(int i=0;i<(int)_countof(slots);++i){if(i%2)ImGui::SameLine(0,12);ImGui::PushID(i);
        auto start=ImGui::GetCursorScreenPos();ImGui::InvisibleButton("Espaço",{width,cell_height});
#ifdef CAREER_OPS_SCREEN_TEST
        slot_centers[i]={start.x+width*.5f,start.y+cell_height*.5f};
#endif
        if(ImGui::IsItemClicked()){selected=i;full_view=false;camera_zoom=1;}
        auto*dl=ImGui::GetWindowDrawList();bool focus=selected==i;
        dl->AddRectFilled(start,{start.x+width,start.y+cell_height},focus?IM_COL32(229,239,248,255):IM_COL32(248,250,251,255),5);
        dl->AddRect(start,{start.x+width,start.y+cell_height},focus?IM_COL32(0,82,158,255):IM_COL32(186,199,205,255),5,0,focus?2.f:1.f);
        dl->AddText(nullptr,0,{start.x+14,start.y+14},IM_COL32(47,65,73,255),slots[i].name,nullptr,width-28);
        dl->AddText({start.x+14,start.y+cell_height-32},IM_COL32(110,125,131,255),"Espaço reservado");ImGui::PopID();}
    ImGui::Spacing();ImGui::Separator();ImGui::TextWrapped("%s",slots[selected].description);
    if(ImGui::Button(full_view?"Ver área selecionada (Y/F)":"Ver jogador completo (Y/F)"))full_view=!full_view;
    ImGui::EndChild();
    if(ImGui::Button("Voltar (B / Esc)"))mod_screen_request_back();ImGui::SameLine();
    ImGui::TextUnformatted("Setas / direcional / clique: área | A/Enter: enquadrar | LT/RT / roda: zoom | Y/F: corpo inteiro");ImGui::End();
}
}
extern "C" void sponsor_screen_publish(const ClubPlayerRow*rows,size_t count,int id,const char*name){
    if(count>CLUB_PLAYER_CAPACITY||(count&&!rows))return;
    std::vector<ClubPlayerRow>data;
    if(id>0)for(size_t i=0;i<count;++i){auto r=rows[i];
        if(r.team_id!=id||r.player_id<=0||r.player_id>524287||r.height<130||r.height>230)continue;
        if(std::find_if(data.begin(),data.end(),[&](const auto&old){return old.player_id==r.player_id;})!=data.end())continue;
        r.name[sizeof(r.name)-1]=0;data.push_back(r);}
    std::string label=name?name:"";std::lock_guard<std::mutex>guard(mutex);
    if(published_club==id&&label==published_name&&published.size()==data.size()&&
        (data.empty()||!memcmp(published.data(),data.data(),data.size()*sizeof(data[0]))))return;
    published=std::move(data);published_club=id;published_name=std::move(label);++revision;
}
extern "C" BOOL sponsor_screen_take_refresh_request(){return InterlockedExchange(&refresh_requested,0)!=0;}
bool sponsor_screen_register(const char*game_root,void(*log)(const char*)){
    root=game_root?game_root:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE thread=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"sponsors",FIFA16_SPONSOR_ACTION,opened,draw,closed,nullptr,nullptr};return mod_screen_register(&screen)!=FALSE;
}
void sponsor_screen_device(ID3D11Device*d){
    renderer.device(d);if(d==device)return;clear_views();if(device)device->Release();device=d;if(d)device->AddRef();
}
#ifdef CAREER_OPS_SCREEN_TEST
SponsorScreenTestView sponsor_screen_test_view(){return {club,player,shown&&shown->model?shown->model->player_id:0,selected,visible.size(),_countof(slots),shown&&bool(shown->model),shown&&shown->model?shown->model->presentation_pose_id:0,portrait!=nullptr,camera_yaw,camera_focus.height_ratio,camera_zoom,full_view};}
bool sponsor_screen_test_slot_center(int i,float&x,float&y){if(i<0||i>=(int)_countof(slots))return false;x=slot_centers[i].x;y=slot_centers[i].y;return x>0&&y>0;}
#endif
