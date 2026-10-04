#define NOMINMAX
#include "next_match_screen.h"
#include "../../render/stadium_thumbnails/stadium_preview.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/lineup_pitch.h"
#include "../../../third_party/imgui/imgui.h"
#include <mutex>
#include <algorithm>
#include <memory>
#include <cmath>
#include <unordered_map>
#include <cfloat>
namespace {
std::mutex gate;
NextMatchSnapshot published={},visible={};
unsigned revision=0,shown_revision=~0u,serial=0;
LONG refresh=0;
HANDLE event=nullptr;
std::string root;
void(*logger)(const char*)=nullptr;
struct Batch {
    unsigned serial=0;NextMatchSnapshot match={};
    unsigned team_pose[2]={},coach_pose[2]={};
    std::vector<ClubPlayerRow>xi[2];
    std::vector<lineup_pitch::Player>pitch[2];
    std::unordered_map<int,fifa_player::Texture>portraits[2];
    std::shared_ptr<const fifa_player::Model>team[2];
    fifa_player::CoachAsset coach[2];
    fifa_player::Texture crest[2],stadium;
    std::string stadium_source;
};
std::shared_ptr<const Batch>ready,shown;
fifa_player::Renderer team_render[2],coach_render[2];
ID3D11Device*device=nullptr;
ID3D11ShaderResourceView*crests[2]={},*stadium=nullptr;
std::unordered_map<int,ID3D11ShaderResourceView*>portrait_views[2];
unsigned pose_seed=0,team_poses[2]={},coach_poses[2]={};
int view=0;WORD prior=0;DWORD input_at=0;
float zoom=1,pan_x=0,pan_y=0,yaw=0;
/* Local, balanced theme scope. Never change ImGui's global theme: the club,
 * player and ranking screens share the same context. */
struct LightTheme {
    int colors=0;
    void color(ImGuiCol id,ImVec4 value){ImGui::PushStyleColor(id,value);++colors;}
    LightTheme(){
        color(ImGuiCol_WindowBg,ImVec4(.94f,.95f,.95f,1));
        color(ImGuiCol_ChildBg,ImVec4(.98f,.98f,.98f,1));
        color(ImGuiCol_PopupBg,ImVec4(.98f,.98f,.98f,1));
        color(ImGuiCol_Text,ImVec4(.20f,.27f,.29f,1));
        color(ImGuiCol_TextDisabled,ImVec4(.43f,.48f,.50f,1));
        color(ImGuiCol_Border,ImVec4(.68f,.73f,.75f,1));
        color(ImGuiCol_Separator,ImVec4(.73f,.77f,.78f,1));
        color(ImGuiCol_Button,ImVec4(.81f,.87f,.91f,1));
        color(ImGuiCol_ButtonHovered,ImVec4(.64f,.77f,.87f,1));
        color(ImGuiCol_ButtonActive,ImVec4(.48f,.68f,.82f,1));
        color(ImGuiCol_FrameBg,ImVec4(.86f,.89f,.90f,1));
        color(ImGuiCol_FrameBgHovered,ImVec4(.78f,.85f,.90f,1));
        color(ImGuiCol_FrameBgActive,ImVec4(.69f,.79f,.86f,1));
        color(ImGuiCol_ScrollbarBg,ImVec4(.88f,.90f,.90f,1));
        color(ImGuiCol_ScrollbarGrab,ImVec4(.56f,.63f,.66f,1));
        color(ImGuiCol_ScrollbarGrabHovered,ImVec4(.40f,.51f,.57f,1));
        color(ImGuiCol_ScrollbarGrabActive,ImVec4(.28f,.43f,.52f,1));
        color(ImGuiCol_NavHighlight,ImVec4(0,.32f,.62f,1));
        ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,ImVec2(20,16));
        ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,0);
        ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding,2);
    }
    ~LightTheme(){ImGui::PopStyleVar(3);ImGui::PopStyleColor(colors);}
};
int current_condition(const NextMatchSide&side,int player) {
    for(int i=0;i<side.count;++i)if(side.rows[i].player_id==player)
        return side.condition_valid[i]&&side.condition[i]>=0&&side.condition[i]<=100?side.condition[i]:-1;
    return -1;
}
const char*position_name(int slot) {
    static const char*names[]={"GOL","LIB","ALA D","LD","ZAG D","ZAG","ZAG E","LE","ALA E","VOL D","VOL","VOL E","MD","MC D","MC","MC E","ME","MEI D","MEI","MEI E","SA D","SA","SA E","PD","ATA D","ATA","ATA E","PE"};
    return slot>=0&&slot<28?names[slot]:"-";
}
unsigned random_pose(unsigned mode,unsigned previous) {
    if(!pose_seed){LARGE_INTEGER counter;QueryPerformanceCounter(&counter);
        pose_seed=(unsigned)counter.QuadPart^(unsigned)(counter.QuadPart>>32)^GetTickCount()^GetCurrentProcessId();
        if(!pose_seed)pose_seed=0x92d68ca2u;}
    pose_seed^=pose_seed<<13;pose_seed^=pose_seed>>17;pose_seed^=pose_seed<<5;
    std::vector<unsigned>eligible;
    for(size_t i=0;i<fifa_player::presentation_pose_count(mode);++i) {
        const auto*info=fifa_player::presentation_pose_at(i,mode);
        eligible.push_back(info->id);
    }
    if(eligible.size()>1)eligible.erase(std::remove(eligible.begin(),eligible.end(),previous),eligible.end());
    return eligible.empty()?0:eligible[pose_seed%eligible.size()];
}
void resample_poses() {
    /* Called only under gate: once per opening/new fixture, never per frame,
     * tab switch, device reset or refresh of the same match. */
    for(int s=0;s<2;++s){team_poses[s]=random_pose(fifa_player::PoseGroup,team_poses[s]);coach_poses[s]=random_pose(fifa_player::PoseStandingCoach,coach_poses[s]);}
}
std::string text(const char*s) {
    if(!s)return {};if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,nullptr,0))return s;
    int count=MultiByteToWideChar(CP_ACP,0,s,-1,nullptr,0);if(!count)return {};
    std::vector<wchar_t>w(count);MultiByteToWideChar(CP_ACP,0,s,-1,w.data(),count);
    int bytes=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);std::string out(bytes,'\0');
    if(bytes){WideCharToMultiByte(CP_UTF8,0,w.data(),-1,&out[0],bytes,nullptr,nullptr);out.pop_back();}return out;
}
std::vector<ClubPlayerRow>starting_xi(const NextMatchSide&side) {
    std::vector<ClubPlayerRow>rows;int keepers=0;
    for(int i=0;i<side.count;++i){const auto&r=side.rows[i];
        if(r.squad_position<0||r.squad_position>=28)continue;
        if(r.team_id!=side.team||r.player_id<=0||r.player_id>524287)return {};
        for(const auto&old:rows)if(old.player_id==r.player_id)return {};
        rows.push_back(r);if(r.squad_position==0)++keepers;
    }
    if(!side.roster_valid||rows.size()!=11||keepers!=1)return {};
    std::stable_sort(rows.begin(),rows.end(),[](const auto&a,const auto&b){return a.squad_position<b.squad_position;});return rows;
}
bool cancelled(unsigned value){std::lock_guard<std::mutex>g(gate);return value!=serial;}
DWORD WINAPI worker(void*) {
    fifa_player::Assets assets(root);
    for(;;){if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;
        auto b=std::make_shared<Batch>();
        {std::lock_guard<std::mutex>g(gate);b->serial=serial;b->match=published;
            for(int s=0;s<2;++s){b->team_pose[s]=team_poses[s];b->coach_pose[s]=coach_poses[s];}}
        if(!b->match.valid)continue;
        try {
            for(int s=0;s<2&&!cancelled(b->serial);++s){const auto&side=b->match.sides[s];
                assets.crest(side.team,b->crest[s]);b->xi[s]=starting_xi(side);
                b->pitch[s]=lineup_pitch::layout(b->xi[s]);
                for(const auto&r:b->xi[s]){if(cancelled(b->serial))break;
                    fifa_player::Texture face;if(assets.portrait(r.player_id,face))b->portraits[s].emplace(r.player_id,std::move(face));}
                ClubPlayerRow identity={};identity.team_id=side.team;
                for(int i=0;i<side.count;++i)if(side.rows[i].team_id==side.team){identity=side.rows[i];break;}
                b->coach[s]=assets.coach(identity);
                if(b->coach[s].model){auto posed=std::make_shared<fifa_player::Model>(*b->coach[s].model);
                    if(fifa_player::apply_coach_pose(*posed,b->coach_pose[s]))b->coach[s].model=posed;else b->coach[s].model.reset();}
                std::vector<std::shared_ptr<const fifa_player::Model>>models;
                for(const auto&r:b->xi[s]){if(cancelled(b->serial))break;models.push_back(std::make_shared<fifa_player::Model>(assets.load(r)));}
                if(cancelled(b->serial))break;
                if(models.size()==11)b->team[s]=std::make_shared<fifa_player::Model>(fifa_player::assemble_starting_eleven(models,b->team_pose[s]));
            }
            if(cancelled(b->serial))continue;
            stadium_preview::load(root,b->match.stadium_key,b->stadium,b->stadium_source);
        }catch(...){if(logger)logger("NextMatch: asset load failed safely; data remains read-only");}
        {std::lock_guard<std::mutex>g(gate);if(b->serial!=serial)continue;ready=b;}
        if(logger){char line[256];sprintf_s(line,"NextMatch: fixture=%d home=%d away=%d xi=%zu/%zu coach=%d/%d stadium_image=%d",b->match.fixture,
            b->match.sides[0].team,b->match.sides[1].team,b->xi[0].size(),b->xi[1].size(),b->coach[0].model!=nullptr,b->coach[1].model!=nullptr,!b->stadium_source.empty());logger(line);
            if(!b->stadium_source.empty())logger(("NextMatch stadium source: "+b->stadium_source).c_str());}
        if(logger){char line[256];sprintf_s(line,"NextMatch: random poses team=%u/%u coach=%u/%u portraits=%zu/%zu pitch=%zu/%zu",b->team_pose[0],b->team_pose[1],b->coach_pose[0],b->coach_pose[1],b->portraits[0].size(),b->portraits[1].size(),b->pitch[0].size(),b->pitch[1].size());logger(line);}
    }
}
DWORD WINAPI guarded_worker(void*context){try{return worker(context);}catch(...){if(logger)logger("NextMatch: worker stopped safely; no game/save mutation");return 0;}}
void clear_views(){for(auto&v:crests)if(v){v->Release();v=nullptr;}if(stadium){stadium->Release();stadium=nullptr;}
    for(auto&views:portrait_views){for(auto&face:views)if(face.second)face.second->Release();views.clear();}
    shown.reset();for(auto&r:team_render)r.clear();for(auto&r:coach_render)r.clear();}
ID3D11ShaderResourceView*upload(const fifa_player::Texture&t) {
    if(!device||!t.width||!t.height||t.format>3||t.bytes.empty())return nullptr;
    D3D11_TEXTURE2D_DESC d={};d.Width=t.width;d.Height=t.height;d.MipLevels=d.ArraySize=1;d.SampleDesc.Count=1;
    d.Format=t.format==3?DXGI_FORMAT_R8G8B8A8_UNORM:t.format==0?DXGI_FORMAT_BC1_UNORM:t.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;
    d.BindFlags=D3D11_BIND_SHADER_RESOURCE;d.Usage=D3D11_USAGE_IMMUTABLE;
    D3D11_SUBRESOURCE_DATA data={t.bytes.data(),t.format==3?t.width*4:((t.width+3)/4)*(t.format?16:8),(UINT)t.bytes.size()};
    ID3D11Texture2D*texture=nullptr;ID3D11ShaderResourceView*v=nullptr;if(SUCCEEDED(device->CreateTexture2D(&d,&data,&texture))){device->CreateShaderResourceView(texture,nullptr,&v);texture->Release();}return v;
}
void sync() {
    std::shared_ptr<const Batch>b;unsigned value,current_serial;bool changed=false;
    {std::lock_guard<std::mutex>g(gate);value=revision;current_serial=serial;if(value!=shown_revision){visible=published;shown_revision=value;changed=true;}b=ready;}
    if(changed)clear_views();
    if(!visible.valid){clear_views();return;}
    if(!b||b==shown||b->match.fixture!=visible.fixture||b->serial!=current_serial)return;
    clear_views();shown=b;for(int i=0;i<2;++i){crests[i]=upload(b->crest[i]);for(const auto&face:b->portraits[i])if(auto*v=upload(face.second))portrait_views[i].emplace(face.first,v);}stadium=upload(b->stadium);
}
void opened(void*) {
    {std::lock_guard<std::mutex>g(gate);resample_poses();published={};++revision;++serial;ready.reset();}
    visible={};shown_revision=~0u;clear_views();view=0;zoom=1;pan_x=pan_y=yaw=0;prior=0;input_at=GetTickCount()+250;
    InterlockedExchange(&refresh,1);if(logger)logger("NextMatch: native card opened; awaiting current fixture + both live rosters");
}
void closed(void*) {
    {std::lock_guard<std::mutex>g(gate);++serial;ready.reset();published={};++revision;}
    clear_views();visible={};if(logger)logger("NextMatch: closed; shared modal release cooldown");
}
void draw_lineup_pitch(int side,ImVec2 size) {
    const auto&rows=shown->xi[side];const auto&players=shown->pitch[side];
    ImVec2 at=ImGui::GetCursorScreenPos();ImGui::InvisibleButton("Campo da escalação",size);
    auto*d=ImGui::GetWindowDrawList();bool hovered=ImGui::IsItemHovered();
    float w=std::max(1.f,size.x-20),h=std::max(1.f,size.y-12);
    auto point=[&](float x,float y){float width=.86f+.14f*y;return ImVec2(at.x+10+w*(.5f+(x-.5f)*width),at.y+6+h*y);};
    d->PushClipRect(at,ImVec2(at.x+size.x,at.y+size.y),true);
    for(int stripe=0;stripe<10;++stripe){float y0=stripe/10.f,y1=(stripe+1)/10.f;
        d->AddQuadFilled(point(0,y0),point(1,y0),point(1,y1),point(0,y1),stripe%2?IM_COL32(58,125,70,255):IM_COL32(76,149,80,255));}
    ImU32 white=IM_COL32(232,244,231,210);
    d->AddQuad(point(0,0),point(1,0),point(1,1),point(0,1),white,1.5f);
    d->AddLine(point(0,.5f),point(1,.5f),white,1.3f);
    auto box=[&](float x0,float y0,float x1,float y1){d->AddQuad(point(x0,y0),point(x1,y0),point(x1,y1),point(x0,y1),white,1.3f);};
    box(.22f,0,.78f,.18f);box(.37f,0,.63f,.065f);box(.22f,.82f,.78f,1);box(.37f,.935f,.63f,1);
    ImVec2 circle[49];for(int i=0;i<=48;++i){float angle=i*6.2831853f/48;circle[i]=point(.5f+cosf(angle)*.13f,.5f+sinf(angle)*.10f);}
    d->AddPolyline(circle,49,white,0,1.3f);d->AddCircleFilled(point(.5f,.5f),2,white);
    d->AddCircleFilled(point(.5f,.12f),1.5f,white);d->AddCircleFilled(point(.5f,.88f),1.5f,white);
    int bands=0;size_t largest=0;
    for(int band=0;band<7;++band){size_t count=std::count_if(players.begin(),players.end(),[&](const auto&p){return p.line==band;});if(count)++bands;largest=std::max(largest,count);}
    float row_height=bands>1?h*.77f/(bands-1):h;
    float ui_scale=std::max(.75f,std::min(2.5f,ImGui::GetIO().DisplaySize.y/800.f));
    float face_size=std::max(16.f*ui_scale,std::min({72.f*ui_scale,row_height*.74f,w/std::max(size_t(1),largest)*.67f}));
    float tag_h=std::max(18.f*ui_scale,std::min(23.f*ui_scale,row_height*.27f));
    float font_size=std::min({ImGui::GetFontSize(),13.f*ui_scale,tag_h*.72f});
    auto*font=ImGui::GetFont();
    for(const auto&p:players) {
        const auto&r=rows[p.row];ImVec2 center=point(p.x,p.y);
        ImVec2 face_lo(center.x-face_size*.5f,center.y-face_size),face_hi(center.x+face_size*.5f,center.y);
        auto photo=portrait_views[side].find(r.player_id);
        if(photo!=portrait_views[side].end())d->AddImage((ImTextureID)(intptr_t)photo->second,face_lo,face_hi);
        else { /* Neutral silhouette, never another player's photograph. */
            d->AddCircleFilled(ImVec2(center.x,center.y-face_size*.68f),face_size*.17f,IM_COL32(197,207,212,240));
            d->AddRectFilled(ImVec2(center.x-face_size*.28f,center.y-face_size*.43f),ImVec2(center.x+face_size*.28f,center.y-2),IM_COL32(160,174,184,240),face_size*.12f);
        }
        char number[8];if(r.number>0&&r.number<=99)sprintf_s(number,"%d",r.number);else strcpy_s(number,"-");
        float badge_h=std::max(13.f*ui_scale,std::min(18.f*ui_scale,face_size*.36f));
        auto number_size=font->CalcTextSizeA(badge_h*.8f,FLT_MAX,0,number);
        ImVec2 number_lo(face_hi.x-badge_h-2,face_hi.y-badge_h),number_hi(face_hi.x+2,face_hi.y);
        d->AddRectFilled(number_lo,number_hi,IM_COL32(0,82,158,255),2);
        d->AddText(font,badge_h*.8f,ImVec2(number_lo.x+(number_hi.x-number_lo.x-number_size.x)*.5f,number_lo.y+(badge_h-number_size.y)*.5f),IM_COL32_WHITE,number);
        size_t peers=std::count_if(players.begin(),players.end(),[&](const auto&v){return v.line==p.line;});
        float available=std::max(18.f*ui_scale,std::min(152.f*ui_scale,w*.90f/std::max(size_t(1),peers)-6*ui_scale));
        float score_w=std::min(24.f*ui_scale,available*.30f);
        char overall[8];if(r.overall>=0&&r.overall<=99)sprintf_s(overall,"%d",r.overall);else strcpy_s(overall,"-");
        std::string name=text(r.name);float text_width=std::max(0.f,available-score_w-8*ui_scale);
        if(font->CalcTextSizeA(font_size,FLT_MAX,0,name.c_str()).x>text_width) {
            size_t last=name.find_last_of(' ');
            if(last!=name.npos&&last+1<name.size()){size_t first=1;while(first<name.size()&&((unsigned char)name[first]&0xc0)==0x80)++first;name=name.substr(0,first)+". "+name.substr(last+1);}
        }
        /* Fit THIS caption, not a fixed-width row cell. Short names such as
         * Pedro no longer leave a large empty rectangle beside the text. */
        float name_w=font->CalcTextSizeA(font_size,FLT_MAX,0,name.c_str()).x;
        float width=std::min(available,score_w+std::min(name_w,text_width)+8*ui_scale);
        ImVec2 lo(center.x-width*.5f,center.y-1),hi(center.x+width*.5f,center.y+tag_h-1);
        d->AddRectFilled(lo,hi,IM_COL32(12,27,24,235),2);
        d->AddRectFilled(lo,ImVec2(lo.x+score_w,hi.y),IM_COL32(25,142,85,255),2);
        auto extent=font->CalcTextSizeA(font_size,FLT_MAX,0,overall);
        d->AddText(font,font_size,ImVec2(lo.x+(score_w-extent.x)*.5f,lo.y+(tag_h-extent.y)*.5f),IM_COL32_WHITE,overall);
        ImVec4 clip(lo.x+score_w+3,lo.y,hi.x-2,hi.y);
        d->AddText(font,font_size,ImVec2(clip.x,lo.y+(tag_h-font_size)*.5f),IM_COL32_WHITE,name.c_str(),nullptr,0,&clip);
        int condition=current_condition(shown->match.sides[side],r.player_id);char energy[24];
        if(condition>=0)sprintf_s(energy,"%d%%",condition);else strcpy_s(energy,"--");
        float energy_h=std::max(12.f*ui_scale,std::min(16.f*ui_scale,row_height*.20f));
        ImVec2 energy_hi(hi.x,hi.y+energy_h);
        ImU32 energy_color=condition<0?IM_COL32(128,142,148,255):condition<40?IM_COL32(182,68,47,255):condition<70?IM_COL32(186,139,30,255):IM_COL32(30,132,76,255);
        /* Slim energy track, directly on the pitch. No white rectangle under
         * every player. Hide unverified energy; tooltip explains its absence. */
        if(condition>=0){
            auto energy_size=font->CalcTextSizeA(energy_h*.74f,FLT_MAX,0,energy);
            float bar_w=std::max(8.f,width-energy_size.x-8);float bar_y=hi.y+energy_h*.45f;
            d->AddRectFilled(ImVec2(lo.x,bar_y),ImVec2(lo.x+bar_w,bar_y+3),IM_COL32(20,42,31,190),2);
            d->AddRectFilled(ImVec2(lo.x,bar_y),ImVec2(lo.x+bar_w*condition/100.f,bar_y+3),energy_color,2);
            ImVec2 energy_pos(hi.x-energy_size.x,hi.y+(energy_h-energy_size.y)*.5f);
            d->AddText(font,energy_h*.74f,ImVec2(energy_pos.x+1,energy_pos.y+1),IM_COL32(14,35,24,240),energy);
            d->AddText(font,energy_h*.74f,energy_pos,IM_COL32_WHITE,energy);
        }
        auto mouse=ImGui::GetIO().MousePos;
        if(hovered&&mouse.x>=lo.x&&mouse.x<=hi.x&&mouse.y>=face_lo.y&&mouse.y<=energy_hi.y)
            ImGui::SetTooltip("%s\nCamisa: %s | GER: %s | %s\nCondição física: %s",text(r.name).c_str(),number,overall,position_name(r.squad_position),condition>=0?energy:"indisponível na leitura atual");
    }
    d->PopClipRect();
}
void draw_side(int index,float width,float height) {
    const auto&side=visible.sides[index];ImGui::PushID(index);ImGui::BeginChild("Team",ImVec2(width,height),true,ImGuiWindowFlags_NoNavInputs);
    if(crests[index]){ImGui::Image((ImTextureID)(intptr_t)crests[index],ImVec2(48,48));ImGui::SameLine();}
    ImGui::BeginGroup();ImGui::SetWindowFontScale(1.2f);ImGui::TextUnformatted(text(side.name).c_str());ImGui::SetWindowFontScale(1);
    ImGui::TextUnformatted(index?"VISITANTE":"MANDANTE");ImGui::EndGroup();
    ImGui::TextWrapped("Formação provável: %s",side.formation[0]?text(side.formation).c_str():"indisponível");
    const auto*coach=shown?&shown->coach[index]:nullptr;
    ImGui::TextWrapped("Técnico: %s",coach&&!coach->name.empty()?text(coach->name.c_str()).c_str():side.manager[0]?text(side.manager).c_str():"indisponível");
    ImGui::Separator();
    if(view==1) {
        if(!shown||shown->xi[index].size()!=11)ImGui::TextWrapped("Aguardando 11 titulares válidos. Nenhuma escalação é inventada.");
        else {ImVec2 area=ImGui::GetContentRegionAvail();area.y=std::max(60.f,area.y);draw_lineup_pitch(index,area);}
    }else {
        auto model=shown?(view==2?shown->coach[index].model:shown->team[index]):nullptr;
        auto&r=view==2?coach_render[index]:team_render[index];ImVec2 area=ImGui::GetContentRegionAvail();area.y=std::max(60.f,area.y-25);
        if(model&&r.model(model)&&r.render((UINT)area.x,(UINT)area.y,view==2?yaw:0,zoom,false,view==2?0:pan_x,view==2?0:pan_y)){
            ImGui::Image((ImTextureID)(intptr_t)r.image(),area);if(ImGui::IsItemHovered()){
                zoom=std::max(.65f,std::min(2.f,zoom+ImGui::GetIO().MouseWheel*.08f));
                if(ImGui::IsMouseDragging(ImGuiMouseButton_Left)){if(view==2)yaw+=ImGui::GetIO().MouseDelta.x*.01f;
                    else {pan_x=std::max(-.45f,std::min(.45f,pan_x+ImGui::GetIO().MouseDelta.x/area.x));pan_y=std::max(-.35f,std::min(.35f,pan_y-ImGui::GetIO().MouseDelta.y/area.y));}}}
        }else ImGui::TextWrapped(!shown?"Carregando modelos do FIFA...":view==2?"Modelo do técnico não encontrado para este clube.":"11 titulares válidos ou modelos não disponíveis para este clube.");
    }
    ImGui::EndChild();ImGui::PopID();
}
void draw(void*) {
    sync();auto&io=ImGui::GetIO();XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD edge=pad.Gamepad.wButtons&~prior;prior=pad.Gamepad.wButtons;
    if((LONG)(GetTickCount()-input_at)>=0) {
        if(edge&XINPUT_GAMEPAD_B){mod_screen_request_back();return;}
        int step=0;if(ImGui::IsKeyPressed(ImGuiKey_Q)||(edge&XINPUT_GAMEPAD_LEFT_SHOULDER))step=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_E)||(edge&XINPUT_GAMEPAD_RIGHT_SHOULDER))step=1;
        if(step){view=(view+step+3)%3;zoom=1;pan_x=pan_y=yaw=0;}
        float trigger=(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f;zoom=std::max(.65f,std::min(2.f,zoom+trigger*io.DeltaTime*.7f));
        auto stick=[](SHORT v){return abs(v)<9000?0.f:v/32768.f;};
        if(view==2)yaw+=stick(pad.Gamepad.sThumbRX)*io.DeltaTime*1.7f;
        else {pan_x=std::max(-.45f,std::min(.45f,pan_x+stick(pad.Gamepad.sThumbRX)*io.DeltaTime*.28f));pan_y=std::max(-.35f,std::min(.35f,pan_y+stick(pad.Gamepad.sThumbRY)*io.DeltaTime*.28f));}
    }
    LightTheme theme;
    ImGui::GetBackgroundDrawList()->AddRectFilled(ImVec2(0,0),io.DisplaySize,IM_COL32(3,21,35,190));
    ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x*.025f,io.DisplaySize.y*.035f));ImGui::SetNextWindowSize(ImVec2(io.DisplaySize.x*.95f,io.DisplaySize.y*.93f));
    ImGui::Begin("Próxima partida##NextMatch",nullptr,ImGuiWindowFlags_NoTitleBar|ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoResize|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    auto*d=ImGui::GetWindowDrawList();auto pos=ImGui::GetWindowPos();auto size=ImGui::GetWindowSize();
    d->AddRectFilled(pos,ImVec2(pos.x+size.x,pos.y+66),IM_COL32(0,82,158,255));
    d->AddText(ImGui::GetFont(),ImGui::GetFontSize()*1.65f,ImVec2(pos.x+30,pos.y+9),IM_COL32_WHITE,"Próxima partida");
    d->AddText(ImVec2(pos.x+32,pos.y+43),IM_COL32(222,235,244,255),"PRÉVIA DA PARTIDA  |  EQUIPES E ESTÁDIO");
    ImGui::SetCursorPosY(78);
    if(!visible.valid)ImGui::TextWrapped("Aguardando a próxima partida da carreira. Sem partida disponível, nenhuma informação antiga será exibida.");
    else {
        ImGui::Text("%s | %02d/%02d/%04d",text(visible.competition).c_str(),visible.date%100,(visible.date/100)%100,visible.date/10000);
        ImGui::SameLine();if(visible.time>=0)ImGui::Text("| %02d:%02d",visible.time/100,visible.time%100);else ImGui::TextUnformatted("| Horário indisponível");
        const char*views[]={"Foto dos 11","Escalações prováveis","Técnicos 3D"};
        for(int i=0;i<3;++i){if(i)ImGui::SameLine();bool selected=i==view;
            if(selected){ImGui::PushStyleColor(ImGuiCol_Button,ImVec4(0,.32f,.62f,1));ImGui::PushStyleColor(ImGuiCol_Text,ImVec4(1,1,1,1));}
            if(ImGui::Button(views[i])){view=i;zoom=1;pan_x=pan_y=yaw=0;}
            if(selected)ImGui::PopStyleColor(2);
        }
        ImGui::SameLine();if(ImGui::Button("Atualizar"))InterlockedExchange(&refresh,1);
        float width=(ImGui::GetContentRegionAvail().x-10)*.5f,height=std::max(140.f,ImGui::GetContentRegionAvail().y-132);
        draw_side(0,width,height);ImGui::SameLine();draw_side(1,width,height);
        ImGui::Separator();
        if(stadium&&shown){float h=72,w=h*shown->stadium.width/shown->stadium.height;w=std::min(w,230.f);ImGui::Image((ImTextureID)(intptr_t)stadium,ImVec2(w,h));ImGui::SameLine();}
        ImGui::BeginGroup();ImGui::PushTextWrapPos(ImGui::GetCursorPosX()+ImGui::GetContentRegionAvail().x);
        ImGui::TextWrapped("Estádio: %s",visible.stadium[0]?text(visible.stadium).c_str():"indisponível");
        if(visible.capacity>0)ImGui::Text("Capacidade: %d",visible.capacity);
        if(visible.attendance>0&&visible.attendance<=100)ImGui::Text("Público estimado: %d%%",visible.attendance);
        if(visible.venue_note[0])ImGui::TextWrapped("%s",text(visible.venue_note).c_str());ImGui::PopTextWrapPos();ImGui::EndGroup();
    }
    ImGui::Separator();ImGui::TextWrapped(view==1?"Escalações prováveis | Barra: condição física | LB/RB ou Q/E: visão | Mouse: detalhes | B/Esc: voltar":"LB/RB ou Q/E: visão | LT/RT ou roda: zoom | Analógico direito/arraste: câmera | B/Esc: voltar");
    ImGui::SameLine();if(ImGui::Button("Voltar"))mod_screen_request_back();ImGui::End();
}
}
extern "C" BOOL next_match_take_refresh(){return InterlockedExchange(&refresh,0)!=0;}
extern "C" void next_match_publish(const NextMatchSnapshot*value) {
    NextMatchSnapshot safe={};if(value)safe=*value;
    safe.competition[127]=0;safe.stadium[511]=0;safe.stadium_key[255]=0;safe.venue_note[159]=0;
    for(int s=0;s<2;++s){auto&side=safe.sides[s];side.name[127]=side.manager[127]=side.formation[95]=0;
        if(side.count<0||side.count>CLUB_PLAYER_CAPACITY){side.count=0;side.roster_valid=0;}
        for(int i=0;i<side.count;++i){side.rows[i].name[127]=0;
            if(!side.condition_valid[i]||side.condition[i]<0||side.condition[i]>100){side.condition[i]=0;side.condition_valid[i]=0;}}
    }
    safe.valid=safe.valid&&safe.sides[0].team>0&&safe.sides[1].team>0&&safe.sides[0].team!=safe.sides[1].team;
    {std::lock_guard<std::mutex>g(gate);
        if(safe.valid&&(!team_poses[0]||(published.valid&&(safe.fixture!=published.fixture||safe.date!=published.date||safe.sides[0].team!=published.sides[0].team||safe.sides[1].team!=published.sides[1].team))))resample_poses();
        published=safe;++revision;++serial;ready.reset();}if(event)SetEvent(event);
}
bool next_match_register(const char*game,void(*log)(const char*)) {
    root=game?game:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE thread=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"next_match",FIFA_NEXT_MATCH_ACTION,opened,draw,closed,nullptr,nullptr};return mod_screen_register(&screen)!=FALSE;
}
void next_match_device(ID3D11Device*d){if(d==device)return;clear_views();for(auto&r:team_render)r.device(d);for(auto&r:coach_render)r.device(d);if(device)device->Release();device=d;if(d)d->AddRef();}
#ifdef NEXT_MATCH_SCREEN_TEST
NextMatchTestView next_match_test_view(){std::lock_guard<std::mutex>g(gate);bool current=shown&&shown->serial==serial;NextMatchTestView out={};out.view=view;out.ready=current;out.image=current&&stadium!=nullptr;
    for(int s=0;s<2;++s){out.teams[s]=visible.sides[s].team;if(current){out.xi[s]=shown->xi[s].size();out.team_pose[s]=shown->team[s]?shown->team[s]->presentation_pose_id:0;out.coach_pose[s]=shown->coach[s].model?shown->coach[s].model->presentation_pose_id:0;out.portraits[s]=portrait_views[s].size();out.pitch[s]=shown->pitch[s].size();out.team_players[s]=shown->team[s]?shown->team[s]->player_count:0;
        for(const auto&r:shown->xi[s]){if(current_condition(shown->match.sides[s],r.player_id)>=0)++out.conditions[s];if(r.number>0&&r.number<=99)++out.numbers[s];}}}return out;}
#endif
