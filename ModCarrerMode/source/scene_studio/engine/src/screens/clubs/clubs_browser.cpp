#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "clubs_browser.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include "../player/player_profile_view.h"
#include "../../ui/common/native_loc_names.h"
#include "../transfers/transfer_center_screen.h"
#include <mutex>
#include <memory>
#include <algorithm>
#include <cstring>
#include <string>
#include <vector>

namespace {
std::mutex guard;
std::vector<ClubBrowserRow> published,visible;
unsigned revision=0,shown_revision=~0u,token=0,waiting_token=0;
unsigned context_epoch=0,render_epoch=0;
int own=0,selected=0,focus=1,preferred_team=0;
bool waiting=false,child=false;
volatile LONG catalog_request=0;
int roster_request=0,ready_club=0;
unsigned request_token=0,ready_token=0;
std::vector<ClubPlayerRow> ready_rows;
std::string ready_name,root,message;
DWORD input_at=0,repeat_at=0,wait_at=0;
WORD previous=0;
int icon_team=0,icon_league=0,icon_nation=0;
unsigned icon_serial=0,display_serial=0;
HANDLE event=nullptr;
void(*logger)(const char*)=nullptr;
ID3D11Device*device=nullptr;
ID3D11ShaderResourceView*crest=nullptr,*flag=nullptr,*league_logo=nullptr;
ImVec2 centers[4]={};
struct Icons {unsigned serial=0;fifa_player::Texture crest,flag,league;std::string country,division;};
std::shared_ptr<const Icons> ready_icons,shown_icons;
void clear_icons(){screen_visuals::release(crest);screen_visuals::release(flag);screen_visuals::release(league_logo);shown_icons.reset();display_serial=0;}
DWORD WINAPI worker(void*){
    fifa_player::Assets assets(root);native_loc::Names names(root);
    for(;;){WaitForSingleObject(event,INFINITE);int t,l,n;unsigned serial;
        {std::lock_guard<std::mutex>lock(guard);t=icon_team;l=icon_league;n=icon_nation;serial=icon_serial;}
        if(t<=0)continue;auto out=std::make_shared<Icons>();out->serial=serial;
        assets.crest(t,out->crest);assets.nationality_flag(n,out->flag);assets.competition_icon(l,out->league);
        out->country=names.nation(n);out->division=names.league(l);
        {std::lock_guard<std::mutex>lock(guard);if(serial==icon_serial)ready_icons=out;}
    }
}
DWORD WINAPI guarded_worker(void*){try{return worker(nullptr);}catch(...){if(logger)logger("OtherClubs: asset worker failed; native selector stays usable");return 1;}}
void queue_icons(){if(visible.empty())return;const auto&r=visible[selected];
    {std::lock_guard<std::mutex>lock(guard);icon_team=r.team;icon_league=r.league;icon_nation=r.nation;++icon_serial;ready_icons.reset();}
    if(event)SetEvent(event);
}
void sync_icons(){std::shared_ptr<const Icons>next;{std::lock_guard<std::mutex>lock(guard);if(ready_icons&&ready_icons->serial==icon_serial)next=ready_icons;}
    if(!device||!next||next==shown_icons)return;clear_icons();shown_icons=next;display_serial=next->serial;
    crest=screen_visuals::upload(device,next->crest);flag=screen_visuals::upload(device,next->flag);league_logo=screen_visuals::upload(device,next->league);
}
void sync_catalog(){int old=selected>=0&&(size_t)selected<visible.size()?visible[selected].team:0;bool changed=false;
    {std::lock_guard<std::mutex>lock(guard);if(revision!=shown_revision){visible=published;shown_revision=revision;changed=true;if(!old)old=own;}}
    if(!changed)return;selected=0;int wanted=preferred_team>0?preferred_team:old;for(size_t i=0;i<visible.size();++i)if(visible[i].team==wanted){selected=(int)i;break;}queue_icons();
}
void cancel_wait(){std::lock_guard<std::mutex>lock(guard);++token;waiting=false;waiting_token=0;roster_request=0;ready_rows.clear();ready_token=0;}
void open_selected(){if(visible.empty()||waiting)return;const auto&r=visible[selected];
    {std::lock_guard<std::mutex>lock(guard);waiting=true;waiting_token=++token;roster_request=r.team;request_token=waiting_token;ready_rows.clear();ready_token=0;}
    wait_at=GetTickCount();message.clear();clubs_browser_request_native_refresh();
}
void sync_roster(){if(!waiting)return;std::vector<ClubPlayerRow>rows;std::string name;int club=0;unsigned serial=0;
    {std::lock_guard<std::mutex>lock(guard);if(ready_token==waiting_token){rows=std::move(ready_rows);name=ready_name;club=ready_club;serial=ready_token;ready_token=0;}}
    if(serial){waiting=false;if(!visible.empty()&&club==visible[selected].team&&!rows.empty())child=club_player_begin_embedded(rows.data(),rows.size(),club,name.c_str());
        if(!child)message="Elenco indisponível para este clube. Tente novamente.";input_at=GetTickCount()+250;
    }else if((DWORD)(GetTickCount()-wait_at)>12000){cancel_wait();message="Não foi possível carregar o elenco. Volte à Central e tente novamente.";}
}
BOOL back(void*){if((LONG)(GetTickCount()-input_at)<0)return TRUE;
    if(child){if(club_player_back_embedded())return TRUE;club_player_end_embedded();child=false;input_at=GetTickCount()+250;return TRUE;}
    if(waiting){cancel_wait();input_at=GetTickCount()+250;return TRUE;}return FALSE;
}
void opened(void*){child=false;waiting=false;focus=1;previous=0;message.clear();shown_revision=~0u;visible.clear();input_at=GetTickCount()+250;
    InterlockedExchange(&catalog_request,1);clubs_browser_request_native_refresh();sync_catalog();
    if(logger)logger("OtherClubs: opened by native card; Hub retained, owned catalog requested");
}
void closed(void*){club_player_end_embedded();child=false;cancel_wait();clear_icons();visible.clear();preferred_team=0;
    std::lock_guard<std::mutex>lock(guard);++icon_serial;ready_icons.reset();icon_team=0;
}
std::vector<int> options(int field){std::vector<int>out;if(visible.empty())return out;const auto&current=visible[selected];
    for(size_t i=0;i<visible.size();++i){const auto&r=visible[i];if(field==0){if(std::find(out.begin(),out.end(),r.nation)==out.end())out.push_back(r.nation);}
        else if(field==2){if(r.nation==current.nation&&std::find(out.begin(),out.end(),r.league)==out.end())out.push_back(r.league);}
        else if(r.nation==current.nation&&r.league==current.league)out.push_back((int)i);}
    return out;
}
void move(int field,int delta){auto choices=options(field);if(choices.empty())return;
    const auto current=visible[selected];int value=field==0?current.nation:field==2?current.league:selected;
    auto at=std::find(choices.begin(),choices.end(),value);int index=at==choices.end()?0:(int)(at-choices.begin());index=(index+delta+(int)choices.size())%(int)choices.size();
    if(field==1)selected=choices[index];else for(size_t i=0;i<visible.size();++i)if(field==0?visible[i].nation==choices[index]:visible[i].nation==current.nation&&visible[i].league==choices[index]){selected=(int)i;break;}
    message.clear();queue_icons();
}
void centered(const char*text,ImVec2 at,float width,float y,float scale=1){auto*draw=ImGui::GetWindowDrawList();float size=ImGui::GetFontSize()*scale;
    auto len=ImGui::GetFont()->CalcTextSizeA(size,FLT_MAX,0,text);draw->AddText(nullptr,size,{at.x+(width-len.x)*.5f,at.y+y},IM_COL32(33,83,118,255),text);}
void stars(ImVec2 at,float width,float y,int prestige){auto*d=ImGui::GetWindowDrawList();float radius=14,step=36,start=at.x+width*.5f-2*step;
    for(int i=0;i<5;++i){ImVec2 p[10];for(int j=0;j<10;++j){float angle=-1.5707963f+j*3.14159265f/5,r=j%2?radius*.44f:radius;p[j]={start+i*step+cosf(angle)*r,at.y+y+sinf(angle)*r};}
        d->AddConcavePolyFilled(p,10,IM_COL32(224,232,238,255));
        float fill=prestige<0?0:std::clamp(prestige/4.f-i,0.f,1.f);
        if(fill>0){d->PushClipRect({start+i*step-radius-1,at.y+y-radius-1},{start+i*step-radius+2*radius*fill,at.y+y+radius+1},true);
            d->AddConcavePolyFilled(p,10,IM_COL32(13,103,168,255));d->PopClipRect();}
        d->AddPolyline(p,10,IM_COL32(65,121,158,255),ImDrawFlags_Closed,1);}
}
void image_fit(ID3D11ShaderResourceView*v,const fifa_player::Texture&t,ImVec2 at,ImVec2 box){if(!v||!t.width||!t.height)return;
    float k=std::min(box.x/t.width,box.y/t.height),w=t.width*k,h=t.height*k;ImGui::GetWindowDrawList()->AddImage((ImTextureID)(intptr_t)v,{at.x+(box.x-w)*.5f,at.y+(box.y-h)*.5f},{at.x+(box.x+w)*.5f,at.y+(box.y+h)*.5f});}
void draw(void*){
    unsigned epoch;{std::lock_guard<std::mutex>lock(guard);epoch=context_epoch;}
    if(epoch!=render_epoch){club_player_end_embedded();child=false;cancel_wait();render_epoch=epoch;clear_icons();message.clear();}
    sync_catalog();if(preferred_team>0&&!visible.empty()&&visible[selected].team==preferred_team){preferred_team=0;open_selected();}
    sync_roster();if(child){club_player_draw_embedded();return;}sync_icons();screen_visuals::LightTheme theme;
    auto&io=ImGui::GetIO();DWORD now=GetTickCount();XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD press=pad.Gamepad.wButtons&~previous;previous=pad.Gamepad.wButtons;bool active=(LONG)(now-input_at)>=0;
    if(active&&(ImGui::IsKeyPressed(ImGuiKey_Escape)||(press&XINPUT_GAMEPAD_B))){mod_screen_request_back();return;}
    int movement=0,field=focus;bool activate=false;
    if(active&&!waiting&&!visible.empty()){
        if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)||(press&XINPUT_GAMEPAD_DPAD_UP))focus=(focus+2)%3;
        if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)||(press&XINPUT_GAMEPAD_DPAD_DOWN)||ImGui::IsKeyPressed(ImGuiKey_Tab))focus=(focus+1)%3;
        if(abs(pad.Gamepad.sThumbLY)>16000&&(LONG)(now-repeat_at)>=0){focus=(focus+(pad.Gamepad.sThumbLY>0?2:1))%3;repeat_at=now+220;}
        field=focus;
        if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(press&XINPUT_GAMEPAD_DPAD_LEFT))movement=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(press&XINPUT_GAMEPAD_DPAD_RIGHT))movement=1;
        if(abs(pad.Gamepad.sThumbLX)>16000&&(LONG)(now-repeat_at)>=0){movement=pad.Gamepad.sThumbLX>0?1:-1;repeat_at=now+180;}
        if(press&XINPUT_GAMEPAD_LEFT_SHOULDER){field=0;movement=-1;}if(press&XINPUT_GAMEPAD_RIGHT_SHOULDER){field=0;movement=1;}
        if(ImGui::IsKeyPressed(ImGuiKey_Q)){field=2;movement=-1;}if(ImGui::IsKeyPressed(ImGuiKey_E)){field=2;movement=1;}
        if(movement)move(field,movement);
        activate=ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space)||(press&XINPUT_GAMEPAD_A);
    }
    screen_visuals::begin_fullscreen("Outros clubes##Browser",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.5f);ImGui::TextUnformatted("Outros clubes");ImGui::SetWindowFontScale(1);
    ImGui::TextUnformatted("Escolha um país, uma liga e um clube para conhecer a equipe.");ImGui::Spacing();
    if(visible.empty()){ImGui::TextUnformatted("Carregando clubes da carreira...");if(ImGui::Button("Voltar (B/Esc)"))mod_screen_request_back();ImGui::End();return;}
    const auto&r=visible[selected];bool icons_current=shown_icons&&display_serial==icon_serial;
    auto country=icons_current&&!shown_icons->country.empty()?shown_icons->country:player_profile::utf8(r.nation_name);
    auto division=icons_current&&!shown_icons->division.empty()?shown_icons->division:player_profile::utf8(r.league_name);
    float w=std::min(500.f,ImGui::GetContentRegionAvail().x*.52f),h=std::max(350.f,ImGui::GetContentRegionAvail().y-66);
    ImVec2 base=ImGui::GetCursorScreenPos();auto*d=ImGui::GetWindowDrawList();float heights[3]={h*.20f,h*.59f,h*.21f};float top=0;
    ImGui::BeginDisabled(waiting||!active);
    for(int i=0;i<3;++i){ImVec2 at={base.x,base.y+top};float height=heights[i];centers[i]={at.x+w*.5f,at.y+height*.5f};
        d->AddRectFilled(at,{at.x+w,at.y+height-4},i==1?IM_COL32(224,239,248,255):IM_COL32(251,252,254,255),5);
        d->AddRect(at,{at.x+w,at.y+height-4},focus==i?IM_COL32(5,101,172,255):IM_COL32(180,199,214,255),5,0,focus==i?3.f:1.f);
        ImGui::SetCursorScreenPos({at.x+8,at.y+height*.5f-16});ImGui::PushID(i);
        if(ImGui::Button("<",{32,32})){focus=i;move(i,-1);}ImGui::SetCursorScreenPos({at.x+w-40,at.y+height*.5f-16});
        if(ImGui::Button(">",{32,32})){focus=i;move(i,1);}
        // The center is its own action; arrows do not accidentally open a club.
        ImGui::SetCursorScreenPos({at.x+48,at.y+4});if(ImGui::InvisibleButton("Centro",{w-96,height-12})){focus=i;if(i==1)activate=true;}
        if(i==0){centered(country.empty()?"Outros países":country.c_str(),at,w,10,1.12f);if(icons_current)image_fit(flag,shown_icons->flag,{at.x+48,at.y+38},{w-96,height-50});}
        if(i==1){auto name=player_profile::utf8(r.name);float scale=std::min(1.5f,(w-40)/std::max(1.f,ImGui::CalcTextSize(name.c_str()).x));centered(name.c_str(),at,w,10,scale);
            if(icons_current)image_fit(crest,shown_icons->crest,{at.x+50,at.y+45},{w-100,height*.48f});
            stars(at,w,height*.67f,r.prestige);centered("REPUTAÇÃO",at,w,height*.73f,.78f);
            const char*labels[]={"ATA","MEI","DEF"};int values[]={r.attack,r.midfield,r.defense};
            for(int k=0;k<3;++k){ImVec2 column={at.x+w*(.16f+k*.225f),at.y};float cw=w*.225f;centered(labels[k],column,cw,height*.81f,.9f);char value[12];if(values[k]>=0&&values[k]<=99)sprintf_s(value,"%d",values[k]);else strcpy_s(value,"—");centered(value,column,cw,height*.875f,1.5f);}}
        if(i==2){float scale=std::min(1.12f,(w-36)/std::max(1.f,ImGui::CalcTextSize(division.c_str()).x));centered(division.empty()?"Liga":division.c_str(),at,w,10,scale);
            if(icons_current)image_fit(league_logo,shown_icons->league,{at.x+48,at.y+38},{w-96,height-50});}
        ImGui::PopID();top+=height;
    }
    ImGui::SetCursorScreenPos({base.x+w+28,base.y+18});ImGui::BeginChild("Resumo",{0,h-20},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.35f);ImGui::TextWrapped("%s",player_profile::utf8(r.name).c_str());ImGui::SetWindowFontScale(1);
    ImGui::Spacing();ImGui::TextWrapped("%s",division.c_str());ImGui::TextWrapped("%s",country.c_str());ImGui::Spacing();ImGui::Separator();ImGui::Spacing();
    ImGui::TextWrapped("Conheça o técnico e os 11 titulares. Abra o elenco completo para ver titulares, reservas e os perfis dos jogadores.");
    ImGui::Spacing();ImGui::TextWrapped("O modelo 3D do técnico aparece quando estiver disponível para o clube.");ImGui::Spacing();
    centers[3]=ImGui::GetCursorScreenPos();centers[3].x+=120;centers[3].y+=22;
    if(ImGui::Button("Ver clube (A/Enter)",{240,44}))activate=true;
    ImGui::EndChild();ImGui::EndDisabled();
    ImGui::SetCursorScreenPos({base.x,base.y+h+6});if(waiting)ImGui::TextUnformatted("Carregando informações do clube...");else if(!message.empty())ImGui::TextWrapped("%s",message.c_str());
    ImGui::SetWindowFontScale(.86f);ImGui::TextWrapped("Cima/baixo: país, clube ou liga | Esquerda/direita: mudar seleção | LB/RB: país | Q/E: liga | A/Enter: ver clube | B/Esc: voltar");ImGui::SetWindowFontScale(1);
    ImGui::SetCursorScreenPos({base.x+w+28,base.y+h-46});if(ImGui::Button(waiting?"Cancelar (B/Esc)":"Voltar (B/Esc)",{190,32}))mod_screen_request_back();
    ImGui::End();if(activate&&active&&!waiting)open_selected();
}
}
extern "C" BOOL clubs_browser_take_catalog_request(){return InterlockedExchange(&catalog_request,0)!=0;}
extern "C" BOOL clubs_browser_take_roster_request(int*club,unsigned*serial){if(!club||!serial)return FALSE;std::lock_guard<std::mutex>lock(guard);if(!roster_request)return FALSE;
    *club=roster_request;*serial=request_token;roster_request=0;return TRUE;}
extern "C" void clubs_browser_publish_catalog(const ClubBrowserRow*rows,size_t count,int own_club){std::vector<ClubBrowserRow>next;
    if(rows&&count<=CLUB_BROWSER_CAPACITY)for(size_t i=0;i<count;++i){auto r=rows[i];if(r.team<=0||r.team>200000||r.league<=0||r.league>4096||r.nation<0||r.nation>255)continue;
        if(std::any_of(next.begin(),next.end(),[&](const auto&x){return x.team==r.team;}))continue;
        r.name[127]=r.league_name[127]=r.nation_name[127]=0;if(!r.name[0])continue;
        if(r.prestige<0||r.prestige>20)r.prestige=-1;next.push_back(r);}
    std::stable_sort(next.begin(),next.end(),[](const auto&a,const auto&b){int n=_stricmp(a.nation_name,b.nation_name);if(n)return n<0;if(a.nation!=b.nation)return a.nation<b.nation;
        int l=_stricmp(a.league_name,b.league_name);if(l)return l<0;if(a.league!=b.league)return a.league<b.league;return _stricmp(a.name,b.name)<0;});
    transfer_center_screen_publish_league_catalog(next.data(),next.size(),own_club);
    std::lock_guard<std::mutex>lock(guard);published=std::move(next);own=own_club;++revision;
}
extern "C" size_t clubs_browser_copy_catalog(ClubBrowserRow*out,size_t capacity,unsigned*catalog_revision){
    std::lock_guard<std::mutex>lock(guard);if(catalog_revision)*catalog_revision=revision;
    size_t copied=std::min(capacity,published.size());if(out&&copied)memcpy(out,published.data(),copied*sizeof(*out));return published.size();
}
extern "C" void clubs_browser_request_catalog(){InterlockedExchange(&catalog_request,1);clubs_browser_request_native_refresh();}
extern "C" BOOL clubs_browser_open_team(int team){if(team<=0||!mod_screen_push_action(FIFA16_CLUBS_BROWSER_ACTION))return FALSE;
    preferred_team=team;InterlockedExchange(&catalog_request,1);clubs_browser_request_native_refresh();return TRUE;}
extern "C" int clubs_browser_own_league(){std::lock_guard<std::mutex>lock(guard);
    for(const auto&r:published)if(r.team==own)return r.league;return 0;}
extern "C" void clubs_browser_publish_roster(int club,unsigned serial,const ClubPlayerRow*rows,size_t count,const char*name){std::lock_guard<std::mutex>lock(guard);
    if(serial!=waiting_token)return;ready_rows.clear();if(rows&&count<=CLUB_PLAYER_CAPACITY)for(size_t i=0;i<count;++i){auto row=rows[i];if(row.team_id!=club||row.player_id<=0||row.player_id>524287){ready_rows.clear();break;}row.name[127]=0;ready_rows.push_back(row);}
    ready_club=club;ready_name=name?std::string(name,strnlen(name,127)):std::string{};ready_token=serial;
}
extern "C" void clubs_browser_invalidate(){std::lock_guard<std::mutex>lock(guard);published.clear();++revision;ready_rows.clear();ready_token=0;roster_request=0;
    // Invalidate in-flight roster replies too. Render thread owns child cleanup.
    waiting_token=++token;++context_epoch;own=0;}
bool clubs_browser_register(const char*game_root,void(*log)(const char*)){root=game_root?game_root:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE t=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!t){CloseHandle(event);event=nullptr;return false;}CloseHandle(t);
    const ModOverlayScreen s={"other-clubs",FIFA16_CLUBS_BROWSER_ACTION,opened,draw,closed,nullptr,back};return mod_screen_register(&s)!=FALSE;}
void clubs_browser_device(ID3D11Device*d){if(d==device)return;clear_icons();if(device)device->Release();device=d;if(d)d->AddRef();}
#ifdef CLUBS_BROWSER_TEST
ClubsBrowserTestView clubs_browser_test_view(){const ClubBrowserRow*r=visible.empty()?nullptr:&visible[selected];return {r?r->team:0,r?r->league:0,r?r->nation:0,focus,visible.size(),child,waiting};}
bool clubs_browser_test_center(int i,float&x,float&y){if(i<0||i>3)return false;x=centers[i].x;y=centers[i].y;return x>0&&y>0;}
#endif
