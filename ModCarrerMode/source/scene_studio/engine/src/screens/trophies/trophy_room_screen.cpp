#define NOMINMAX
#include "trophy_room_screen.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/screen_visuals.h"
#include "../../ui/common/native_loc_names.h"
#include <mutex>
#include <algorithm>
#include <memory>
#include <cfloat>
#include <cmath>
namespace {
std::mutex gate;std::vector<TrophyRoomRow>published,visible;ClubPlayerRow club={};
int known=0,unresolved=0;unsigned revision=0,shown_revision=~0u,serial=0;
std::string root;void(*logger)(const char*)=nullptr;HANDLE event=nullptr;
struct Item {TrophyRoomRow row={};fifa_player::Texture icon;std::shared_ptr<const fifa_player::Model>model;std::string diagnostic,name;};
struct Batch {unsigned serial=0;std::vector<Item>items;};
std::shared_ptr<const Batch>ready,shown;
fifa_player::Renderer cards[6],detail_renderer;
ID3D11Device*device=nullptr;std::vector<ID3D11ShaderResourceView*>icons;
WORD previous=0;DWORD input_after=0,repeat=0;
int selected=0,page=0;bool detail=false;float zoom=1,yaw=0;
void clear_views(){for(auto*&v:icons)screen_visuals::release(v);icons.clear();shown.reset();for(auto&r:cards)r.clear();detail_renderer.clear();}
/* Uniformly center the real native RX3, preserving its exact proportions. The
 * only generated geometry is the rectangular exhibition plinth beneath it. */
std::shared_ptr<const fifa_player::Model>display(const fifa_player::Model&cup){
    if(cup.parts.empty())return {};
    auto model=std::make_shared<fifa_player::Model>(cup);model->room=fifa_player::RoomArtifact;model->player_count=0;
    fifa_player::Vec3 lo={FLT_MAX,FLT_MAX,FLT_MAX},hi={-FLT_MAX,-FLT_MAX,-FLT_MAX};
    for(const auto&p:cup.parts)for(const auto&v:p.vertices){lo.x=std::min(lo.x,v.position.x);lo.y=std::min(lo.y,v.position.y);lo.z=std::min(lo.z,v.position.z);
        hi.x=std::max(hi.x,v.position.x);hi.y=std::max(hi.y,v.position.y);hi.z=std::max(hi.z,v.position.z);}
    if(hi.y-lo.y<.01f)return {};float scale=135.f/(hi.y-lo.y);
    for(auto&p:model->parts)for(auto&v:p.vertices){v.position.x=(v.position.x-(lo.x+hi.x)*.5f)*scale;
        v.position.y=12+(v.position.y-lo.y)*scale;v.position.z=(v.position.z-(lo.z+hi.z)*.5f)*scale;}
    fifa_player::Part base;base.name="exhibition-rectangular-plinth";base.color={.24f,.29f,.34f};
    const fifa_player::Vec3 points[8]={{-57,0,-40},{57,0,-40},{57,12,-40},{-57,12,-40},{-57,0,40},{57,0,40},{57,12,40},{-57,12,40}};
    const int faces[6][4]={{4,5,6,7},{1,0,3,2},{0,4,7,3},{5,1,2,6},{3,7,6,2},{0,1,5,4}};
    const fifa_player::Vec3 normals[6]={{0,0,1},{0,0,-1},{-1,0,0},{1,0,0},{0,1,0},{0,-1,0}};
    for(int f=0;f<6;++f){uint32_t start=(uint32_t)base.vertices.size();for(int i=0;i<4;++i){fifa_player::Vertex v={};v.position=points[faces[f][i]];v.normal=normals[f];base.vertices.push_back(v);}
        for(int i:{0,1,2,0,2,3})base.indices.push_back(start+i);}
    base.native_normals=true;model->parts.push_back(std::move(base));return model;
}
DWORD WINAPI work(void*){fifa_player::Assets assets(root);native_loc::Names names(root);
    for(;;){if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;
        auto b=std::make_shared<Batch>();std::vector<TrophyRoomRow>data;
        {std::lock_guard<std::mutex>lock(gate);data=published;b->serial=serial;}
        for(const auto&r:data){
            {std::lock_guard<std::mutex>lock(gate);if(b->serial!=serial)break;}
            Item item;item.row=r;item.name=r.name;
            if(item.name.empty())item.name=names.competition(r.title_asset>0?r.title_asset:r.competition);
            if(item.name.empty())item.name="Competição "+std::to_string(r.competition);
            assets.competition_icon(r.logo,item.icon);auto cup=assets.trophy(r.trophy);item.diagnostic=cup.diagnostic;item.model=display(cup);b->items.push_back(std::move(item));
        }
        {std::lock_guard<std::mutex>lock(gate);if(b->serial!=serial)continue;ready=b;}
        if(logger)logger(("Trophy room: competitions="+std::to_string(b->items.size())+"; one native mesh per competition; read-only").c_str());
    }
}
DWORD WINAPI guarded_work(void*p){try{return work(p);}catch(...){if(logger)logger("Trophy room asset worker failed safely; no save writes");return 0;}}
void queue(){std::lock_guard<std::mutex>lock(gate);++serial;ready.reset();SetEvent(event);}
void sync(){
    unsigned value,current;std::shared_ptr<const Batch>b;bool changed=false;
    {std::lock_guard<std::mutex>lock(gate);value=revision;current=serial;b=ready;if(value!=shown_revision){visible=published;shown_revision=value;changed=true;}}
    if(changed){clear_views();detail=false;zoom=1;yaw=0;}
    if(b&&b!=shown&&b->serial==current){clear_views();shown=b;icons.resize(b->items.size());for(size_t i=0;i<icons.size();++i)icons[i]=screen_visuals::upload(device,b->items[i].icon);}
    selected=std::max(0,std::min(selected,(int)visible.size()-1));page=selected/6;
}
void opened(void*){selected=page=0;detail=false;zoom=1;yaw=0;previous=0;input_after=GetTickCount()+350;shown_revision=~0u;clear_views();queue();}
void closed(void*){detail=false;clear_views();}
BOOL back(void*){if(!detail)return FALSE;detail=false;zoom=1;yaw=0;input_after=GetTickCount()+350;return TRUE;}
void open_detail(){if(visible.empty())return;detail=true;zoom=1;yaw=0;input_after=GetTickCount()+300;detail_renderer.clear();}
void input(){
    XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD now=pad.Gamepad.wButtons,pressed=(WORD)(now&~previous);previous=now;DWORD tick=GetTickCount();if(tick<input_after)return;
    auto&io=ImGui::GetIO();
    if(detail){if(abs(pad.Gamepad.sThumbRX)>8000)yaw+=pad.Gamepad.sThumbRX/32767.f*io.DeltaTime*1.6f;
        zoom=std::clamp(zoom+(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f*io.DeltaTime,.65f,2.f);
        if(ImGui::IsKeyDown(ImGuiKey_LeftArrow))yaw-=io.DeltaTime;if(ImGui::IsKeyDown(ImGuiKey_RightArrow))yaw+=io.DeltaTime;
        if(ImGui::IsKeyDown(ImGuiKey_UpArrow))zoom=std::min(2.f,zoom+io.DeltaTime);if(ImGui::IsKeyDown(ImGuiKey_DownArrow))zoom=std::max(.65f,zoom-io.DeltaTime);
        return;}
    int move=0;
    if(tick>=repeat){if((now&XINPUT_GAMEPAD_DPAD_LEFT)||pad.Gamepad.sThumbLX<-18000)move=-1;
        if((now&XINPUT_GAMEPAD_DPAD_RIGHT)||pad.Gamepad.sThumbLX>18000)move=1;
        if((now&XINPUT_GAMEPAD_DPAD_UP)||pad.Gamepad.sThumbLY>18000)move=-3;
        if((now&XINPUT_GAMEPAD_DPAD_DOWN)||pad.Gamepad.sThumbLY<-18000)move=3;if(move)repeat=tick+180;}
    if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow))move=-1;if(ImGui::IsKeyPressed(ImGuiKey_RightArrow))move=1;
    if(ImGui::IsKeyPressed(ImGuiKey_UpArrow))move=-3;if(ImGui::IsKeyPressed(ImGuiKey_DownArrow))move=3;
    if(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER)move=6;if(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER)move=-6;
    selected=std::max(0,std::min((int)visible.size()-1,selected+move));page=selected/6;
    if((pressed&XINPUT_GAMEPAD_A)||ImGui::IsKeyPressed(ImGuiKey_Enter))open_detail();
}
void title(const Item&item){ImGui::TextWrapped("%s",item.name.c_str());if(item.row.count>=0)ImGui::Text("Títulos conquistados: %d",item.row.count);else ImGui::TextUnformatted("Títulos: histórico não identificado");}
void draw(void*){
    sync();input();screen_visuals::LightTheme theme;auto size=ImGui::GetIO().DisplaySize;
    ImGui::SetNextWindowPos({size.x*.025f,size.y*.025f});ImGui::SetNextWindowSize({size.x*.95f,size.y*.95f});
    ImGui::Begin("Sala de troféus",nullptr,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.3f);
    ImGui::TextUnformatted(detail?"SALA DE TROFÉUS / VISUALIZAÇÃO 3D":"SALA DE TROFÉUS / COMPETIÇÕES DO CLUBE");
    ImGui::SetWindowFontScale(1);
    int history,unknown;{std::lock_guard<std::mutex>lock(gate);history=known;unknown=unresolved;}
    if(!history)ImGui::TextUnformatted("Histórico indisponível: conquistas não serão inventadas.");
    if(unknown)ImGui::Text("%d títulos sem atribuição segura à competição.",unknown);
    ImGui::Separator();
    if(detail){
        if(ImGui::Button("Voltar às taças (B / Esc)"))mod_screen_request_back();
        if(shown&&selected<(int)shown->items.size()){
            const auto&item=shown->items[selected];ImGui::SameLine();title(item);
            auto area=ImGui::GetContentRegionAvail();area.y=std::max(50.f,area.y-35);
            if(item.model&&detail_renderer.model(item.model)&&detail_renderer.render((UINT)area.x,(UINT)area.y,yaw,zoom,false,0,0,true)){
                ImGui::Image((ImTextureID)(intptr_t)detail_renderer.image(),area);
                if(ImGui::IsItemHovered()){zoom=std::clamp(zoom+ImGui::GetIO().MouseWheel*.08f,.65f,2.f);
                    if(ImGui::IsMouseDragging(ImGuiMouseButton_Left))yaw+=ImGui::GetIO().MouseDelta.x*.012f;}
            }else {ImGui::TextWrapped("Modelo 3D exato não encontrado. %s",item.diagnostic.c_str());}
        }else ImGui::TextUnformatted("Carregando taça nativa...");
        ImGui::TextUnformatted("Analógico direito / arraste / setas horizontais: girar | LT/RT / roda / setas verticais: zoom | B/Esc: lista");
    }else{
        int pages=std::max(1,((int)visible.size()+5)/6);
        ImGui::Text("%zu competições | página %d/%d",visible.size(),page+1,pages);
        if(visible.empty())ImGui::TextUnformatted("Aguardando competições da carreira atual.");
        float width=(ImGui::GetContentRegionAvail().x-24)/3,height=std::max(100.f,(ImGui::GetContentRegionAvail().y-42)/2);
        for(int cell=0;cell<6;++cell){int index=page*6+cell;if(index>=(int)visible.size())break;
            if(cell%3)ImGui::SameLine(0,12);ImGui::PushID(index);ImGui::BeginChild("Taça",{width,height},true,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
            ImVec2 at=ImGui::GetCursorScreenPos(),area(width-18,std::max(30.f,height-94));
            auto*d=ImGui::GetWindowDrawList();
            if(index==selected)d->AddRect(ImGui::GetWindowPos(),{ImGui::GetWindowPos().x+width,ImGui::GetWindowPos().y+height},IM_COL32(0,82,158,255),0,0,3);
            if(shown&&index<(int)shown->items.size()){
                const auto&item=shown->items[index];auto&r=cards[cell];
                if(item.model&&r.model(item.model)&&r.render((UINT)area.x,(UINT)area.y,0,1,false,0,0,true))d->AddImage((ImTextureID)(intptr_t)r.image(),at,{at.x+area.x,at.y+area.y});
                else d->AddText({at.x+16,at.y+area.y*.5f},IM_COL32(105,114,121,255),item.model?"Carregando...":"3D indisponível");
                ImGui::InvisibleButton("Selecionar taça",area);if(ImGui::IsItemClicked()){selected=index;open_detail();}
                ImVec2 plaque=ImGui::GetCursorScreenPos();d->AddRectFilled(plaque,{plaque.x+area.x,plaque.y+74},IM_COL32(224,229,232,255),2);
                ImGui::SetCursorScreenPos({plaque.x+6,plaque.y+6});
                if(index<(int)icons.size()&&icons[index]){ImGui::Image((ImTextureID)(intptr_t)icons[index],{36,36});ImGui::SameLine();}
                ImGui::BeginGroup();ImGui::PushTextWrapPos(ImGui::GetCursorPosX()+area.x-58);title(item);ImGui::PopTextWrapPos();ImGui::EndGroup();
                if(ImGui::IsWindowHovered()&&ImGui::IsMouseClicked(ImGuiMouseButton_Left)&&!ImGui::IsAnyItemHovered()){selected=index;open_detail();}
            }else{ImGui::TextWrapped("Carregando modelo e ícone da competição...");}
            ImGui::EndChild();ImGui::PopID();
        }
        ImGui::TextUnformatted("Direcional / analógico esquerdo / setas: selecionar | LB/RB: páginas | A/Enter / clique: ampliar | B/Esc: voltar");
    }
    ImGui::End();
}
}
extern "C" void trophy_room_publish(const TrophyRoomRow*data,size_t count,const ClubPlayerRow*identity,int valid,int unknown){
    if(count>64||(count&&!data))return;std::lock_guard<std::mutex>lock(gate);
    bool same=identity&&count==published.size()&&known==valid&&unresolved==unknown&&!memcmp(&club,identity,sizeof(club))&&(!count||!memcmp(published.data(),data,count*sizeof(*data)));
    if(same)return;published.clear();
    for(size_t i=0;i<count;++i)if(data[i].competition>0&&data[i].count>=-1&&data[i].count<=2048){
        bool duplicate=false;for(const auto&r:published)if(r.competition==data[i].competition)duplicate=true;
        if(!duplicate){published.push_back(data[i]);published.back().name[127]=0;}}
    club=identity?*identity:ClubPlayerRow{};known=valid;unresolved=unknown;++revision;++serial;ready.reset();if(event)SetEvent(event);
}
bool trophy_room_register(const char*game_root,void(*log)(const char*)){
    root=game_root?game_root:"";logger=log;
    if(!event){event=CreateEventA(nullptr,FALSE,FALSE,nullptr);if(!event)return false;HANDLE t=CreateThread(nullptr,0,guarded_work,nullptr,0,nullptr);if(!t)return false;CloseHandle(t);}
    const ModOverlayScreen s={"trophy-room",FIFA_TROPHY_ROOM_ACTION,opened,draw,closed,nullptr,back};return mod_screen_register(&s);
}
void trophy_room_device(ID3D11Device*d){if(device==d)return;clear_views();for(auto&r:cards)r.device(d);detail_renderer.device(d);device=d;}
#ifdef CAREER_OPS_SCREEN_TEST
TrophyRoomTestView trophy_room_test_view(){size_t models=0;if(shown)for(const auto&i:shown->items)if(i.model)++models;return {visible.size(),models,selected,page,detail,yaw,zoom};}
#endif
