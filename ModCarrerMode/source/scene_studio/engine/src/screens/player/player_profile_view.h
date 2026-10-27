#pragma once
#include "club_player_profile.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../ui/common/screen_visuals.h"
#include "../../ui/common/profile_reputation.h"
#include <Xinput.h>
#include <algorithm>
#include <cmath>
#include <cstring>

/* Reusable presentation, not a career/team navigation bridge. Callers supply
 * one owned row, its exact assets and their own Back/pose lifecycle. No save,
 * native pointer, game input hook or player selection belongs in this view. */
namespace player_profile {
struct State {
    int page=0,section=0,view_tab=0;
    bool portrait=true,reset_scroll=true;
    float yaw=0,zoom=1,pan_y=0,scroll_delta=0,scroll_y=0,scroll_max=0;
    DWORD repeat_at=0;
    float competition_scroll_y=0,competition_scroll_max=0;
    ImVec2 tab_centers[3]={};
};
struct Visuals {
    ID3D11ShaderResourceView*face=nullptr,*crest=nullptr,*flag=nullptr;
    ID3D11ShaderResourceView*league_logo=nullptr;
    std::shared_ptr<const fifa_player::Model>model;
    int nationality=0,age=-1,foot=0,league=0;
    std::string league_name;
    float league_strength=-1;
    std::vector<fifa_player::CompetitionIdentity> competitions;
    std::unordered_map<int,ID3D11ShaderResourceView*>competition_icons;
    bool loading=false;
};
struct Actions {bool back=false,next_pose=false;unsigned pose=0;};
inline ImFont*& shirt_number_font_slot(){static ImFont*font=nullptr;return font;}
inline void set_shirt_number_font(ImFont*font){shirt_number_font_slot()=font;}
inline void reputation_stars(double rating,float size=18){
    int filled=profile_reputation::stars(rating);auto at=ImGui::GetCursorScreenPos();ImGui::Dummy({size*5+4*5,size});
    auto*d=ImGui::GetWindowDrawList();for(int i=0;i<5;++i){ImVec2 points[10];float cx=at.x+size*.5f+i*(size+5),cy=at.y+size*.5f;
        for(int k=0;k<10;++k){float angle=-1.5707963f+k*.62831853f,radius=size*(k%2?.215f:.48f);points[k]={cx+cosf(angle)*radius,cy+sinf(angle)*radius};}
        // Concave fill avoids internal antialias seams between triangles.
        ImU32 color=filled>=0&&i<filled?IM_COL32(9,103,171,255):IM_COL32(255,255,255,255);
        d->AddConcavePolyFilled(points,10,color);
        d->AddPolyline(points,10,IM_COL32(69,123,162,255),ImDrawFlags_Closed,1.2f);}
    if(ImGui::IsItemHovered()){if(filled<0)ImGui::SetTooltip("Reputação indisponível");else ImGui::SetTooltip("Reputação: %d de 5",filled);}
}
inline const char*const*pages(){static const char*names[]={"Visão geral","Físico","Ataque","Passe","Defesa","Goleiro"};return names;}
inline bool attribute_on_page(size_t i,int page){
    if(page==0)return true;
    if(page==1)return i<=4||(i>=18&&i<=20);
    if(page==2)return (i>=5&&i<=9)||i==15||i==16||i==17||i==23||i==27||i==33;
    if(page==3)return i>=10&&i<=14;
    if(page==4)return i==21||i==22||(i>=24&&i<=26);
    return i>=28&&i<=32;
}
inline void page(State&s,int step){s.page=(s.page+step+6)%6;s.reset_scroll=true;s.section=0;}
inline void view(State&s,int step){s.view_tab=(s.view_tab+step+3)%3;s.reset_scroll=true;s.section=s.view_tab==1?2:0;}
inline float stick(SHORT v){const float dead=9000.f;return abs(v)<=dead?0.f:(v>0?1.f:-1.f)*(abs(v)-dead)/(32768.f-dead);}
inline void input(State&s,const XINPUT_STATE&pad,WORD pressed,bool ready) {
    s.scroll_delta=0;if(!ready)return;
    auto&io=ImGui::GetIO();float dt=std::clamp(io.DeltaTime,0.f,.05f);
    if(!ImGui::IsAnyItemActive()) {
        int step=0,outer=0;
        if(ImGui::IsKeyPressed(ImGuiKey_Q)||(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER))outer=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_E)||(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER))outer=1;
        if(outer)view(s,outer);
        if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(pressed&XINPUT_GAMEPAD_DPAD_LEFT))step=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(pressed&XINPUT_GAMEPAD_DPAD_RIGHT))step=1;
        DWORD now=GetTickCount();
        if(!step&&abs(pad.Gamepad.sThumbLX)>16000&&(LONG)(now-s.repeat_at)>=0){step=pad.Gamepad.sThumbLX>0?1:-1;s.repeat_at=now+180;}
        if(step){if(s.view_tab==2)page(s,step);else view(s,step);}
        float scroll=-stick(pad.Gamepad.sThumbLY);
        if(ImGui::IsKeyDown(ImGuiKey_UpArrow)||ImGui::IsKeyDown(ImGuiKey_PageUp)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_UP))scroll=-1;
        if(ImGui::IsKeyDown(ImGuiKey_DownArrow)||ImGui::IsKeyDown(ImGuiKey_PageDown)||(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_DOWN))scroll=1;
        s.scroll_delta=scroll*dt*420;if(scroll)s.section=s.view_tab==1?2:1;
    }
    float triggers=(std::max(0,int(pad.Gamepad.bRightTrigger)-30)-std::max(0,int(pad.Gamepad.bLeftTrigger)-30))/225.f;
    s.zoom=std::clamp(s.zoom+triggers*dt*.8f,.65f,2.f);
    s.yaw+=stick(pad.Gamepad.sThumbRX)*dt*1.7f;
    s.pan_y=std::clamp(s.pan_y+stick(pad.Gamepad.sThumbRY)*dt*.28f,-.35f,.35f);
    if((pressed&XINPUT_GAMEPAD_RIGHT_THUMB)||ImGui::IsKeyPressed(ImGuiKey_R)){s.yaw=0;s.zoom=1;s.pan_y=0;}
}
inline std::string utf8(const char*s){if(!s)return {};if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s,-1,nullptr,0))return s;
    int n=MultiByteToWideChar(CP_ACP,0,s,-1,nullptr,0);if(!n)return {};std::vector<wchar_t>w(n);MultiByteToWideChar(CP_ACP,0,s,-1,w.data(),n);
    int bytes=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);std::string out(bytes,'\0');
    WideCharToMultiByte(CP_UTF8,0,w.data(),-1,&out[0],bytes,nullptr,nullptr);out.pop_back();return out;}
inline ImVec4 ink(){return {.025f,.30f,.53f,1};}
inline void value(const char*label,int v,const char*unit,float width){
    ImGui::BeginGroup();ImGui::TextColored({.27f,.42f,.53f,1},"%s",label);ImGui::SetWindowFontScale(1.02f);
    if(v>=0)ImGui::Text("%d%s",v,unit);else ImGui::TextUnformatted("-");ImGui::SetWindowFontScale(.92f);ImGui::Dummy({width,0});ImGui::EndGroup();}
inline void text_value(const char*label,const std::string&text,float width){
    ImGui::BeginGroup();ImGui::TextColored({.27f,.42f,.53f,1},"%s",label);ImGui::SetWindowFontScale(1.02f);
    ImGui::TextWrapped("%s",text.c_str());ImGui::SetWindowFontScale(.92f);ImGui::Dummy({width,0});ImGui::EndGroup();}
inline std::string grouped_amount(int amount){
    if(amount<0)return "—";char digits[32];sprintf_s(digits,"%d",amount);std::string out;
    for(size_t i=0;digits[i];++i){if(i&&(strlen(digits)-i)%3==0)out+='.';out+=digits[i];}return out;
}
inline void finance_card(const char*label,const std::string&text,ImVec2 p,float width){
    auto*d=ImGui::GetWindowDrawList();d->AddRectFilled(p,{p.x+width,p.y+47},IM_COL32(235,243,249,255),5);
    d->AddText(ImGui::GetFont(),ImGui::GetFontSize()*.76f,{p.x+9,p.y+5},IM_COL32(77,117,147,255),label);
    d->AddText(ImGui::GetFont(),ImGui::GetFontSize()*.94f,{p.x+9,p.y+23},IM_COL32(6,79,134,255),text.c_str(),nullptr,width-18);
}
inline void identity_line(ID3D11ShaderResourceView*icon,float size,const char*text){
    ImGui::BeginGroup();float y=ImGui::GetCursorPosY();
    if(icon){ImGui::Image((ImTextureID)(intptr_t)icon,{size,size});ImGui::SameLine(0,6);
        ImGui::SetCursorPosY(y+std::max(0.f,(size-ImGui::GetFontSize())*.5f));}
    ImGui::TextWrapped("%s",text);ImGui::EndGroup();
}
inline void sole(ImDrawList*d,ImVec2 at,ImVec2 size,bool right,ImU32 color){
    /* Mirrored continuous sole silhouettes, not disconnected circles. The
     * large toe faces the other foot and the inner arch stays concave. */
    const ImVec2 curves[7][4]={
        {{.78f,.03f},{.99f,0},{1.05f,.19f},{.91f,.32f}},
        {{.91f,.32f},{.68f,.49f},{.58f,.55f},{.70f,.70f}},
        {{.70f,.70f},{.82f,.87f},{.68f,1},{.47f,1}},
        {{.47f,1},{.23f,1},{.18f,.91f},{.18f,.75f}},
        {{.18f,.75f},{.18f,.61f},{.07f,.49f},{.08f,.31f}},
        {{.08f,.31f},{.09f,.13f},{.18f,.04f},{.31f,.03f}},
        {{.31f,.03f},{.47f,.02f},{.60f,.01f},{.78f,.03f}}};
    ImVec2 points[56];
    for(int i=0;i<7;++i)for(int j=0;j<8;++j){float t=j/8.f,u=1-t;auto*c=curves[i];
        float x=u*u*u*c[0].x+3*u*u*t*c[1].x+3*u*t*t*c[2].x+t*t*t*c[3].x;
        float y=u*u*u*c[0].y+3*u*u*t*c[1].y+3*u*t*t*c[2].y+t*t*t*c[3].y;
        points[i*8+j]={at.x+(right?1-x:x)*size.x,at.y+y*size.y};}
    /* Preserve clockwise winding after mirroring, including the AA fringe;
     * omit the repeated closing point to avoid degenerate triangles. */
    if(right)std::reverse(points,points+56);
    d->AddConcavePolyFilled(points,56,color);
}
inline void technical_panel(const ClubPlayerRow&r,const Visuals&v,ImVec2 size){
    ImGui::TextUnformatted("PERFIL TÉCNICO");ImVec2 at=ImGui::GetCursorScreenPos();ImGui::Dummy(size);auto*d=ImGui::GetWindowDrawList();
    d->AddRectFilled(at,{at.x+size.x,at.y+size.y},IM_COL32(255,255,255,255),8);
    float left=std::min(68.f,size.x*.18f),pitch_width=std::min(130.f,size.x*.32f),radar_width=size.x-left-pitch_width-12;
    ImU32 blue=IM_COL32(5,82,143,255),muted=IM_COL32(100,130,150,255);
    const char*pos=club_profile::position(r.position);auto label=ImGui::CalcTextSize(pos);
    d->AddRectFilled({at.x+8,at.y+10},{at.x+8+label.x+12,at.y+34},IM_COL32(229,241,249,255),4);
    d->AddText({at.x+14,at.y+14},blue,pos);
    char over[8];if(r.overall>=0&&r.overall<=99)sprintf_s(over,"%d",r.overall);else strcpy_s(over,"-");
    ImFont*overall_font=shirt_number_font_slot();
    float overall_size=ImGui::GetFontSize()*(size.y<145?1.75f:2.3f);
    d->AddText(overall_font?overall_font:ImGui::GetFont(),overall_size,
        {at.x+10,at.y+40},blue,over);
    /* FIFA preferredfoot: 1=right, 2=left. Both soles are visible; only the
     * actual dominant foot is highlighted. Unknown does not select either. */
    float sole_height=std::min(30.f,size.y*.16f),sole_y=at.y+size.y-sole_height-29;
    for(int foot=0;foot<2;++foot){float x=at.x+(left-46)*.5f+foot*28;
        bool dominant=v.foot==(foot==0?2:1);ImU32 color=dominant?IM_COL32(17,152,199,255):IM_COL32(203,214,223,255);
        sole(d,{x,sole_y},{18,sole_height},foot==1,color);
        const char*side=foot?"D":"E";float fs=ImGui::GetFontSize()*.72f;
        auto t=ImGui::GetFont()->CalcTextSizeA(fs,FLT_MAX,0,side);
        d->AddText(ImGui::GetFont(),fs,{x+(18-t.x)*.5f,sole_y+sole_height+2},dominant?blue:muted,side);}
    const char*foot_label=v.foot==1?"Direito":v.foot==2?"Esquerdo":"-";
    float foot_font=ImGui::GetFontSize()*.8f;auto foot_text=ImGui::GetFont()->CalcTextSizeA(foot_font,FLT_MAX,0,foot_label);
    d->AddText(ImGui::GetFont(),foot_font,{at.x+(left-foot_text.x)*.5f,at.y+size.y-18},muted,foot_label);
    ImVec2 center(at.x+left+radar_width*.5f,at.y+size.y*.50f);float radius=std::min(radar_width*.30f,size.y*.32f);
    ImVec2 axes[6],poly[6];const char*outfield[]={"CHU","PAS","FIS","DEF","RIT","DRI"},*keeper[]={"MAN","REP","REA","REF","MER","POS"};const int order[]={1,2,5,4,0,3};
    bool valid=true;
    for(int i=0;i<6;++i){float a=-1.5707963f+i*1.0471976f;axes[i]={cosf(a),sinf(a)};
        int value=club_profile::summary(r,order[i]);if(value<0)valid=false;float f=std::max(0,value)/99.f;poly[i]={center.x+axes[i].x*radius*f,center.y+axes[i].y*radius*f};}
    for(int ring=1;ring<=3;++ring){ImVec2 points[6];for(int i=0;i<6;++i)points[i]={center.x+axes[i].x*radius*ring/3,center.y+axes[i].y*radius*ring/3};
        d->AddPolyline(points,6,IM_COL32(219,230,238,255),ImDrawFlags_Closed,1);}
    for(int i=0;i<6;++i){d->AddLine(center,{center.x+axes[i].x*radius,center.y+axes[i].y*radius},IM_COL32(231,238,244,255));
        const char*name=r.position==0?keeper[i]:outfield[i];auto t=ImGui::CalcTextSize(name);
        d->AddText({center.x+axes[i].x*(radius+13)-t.x*.5f,center.y+axes[i].y*(radius+13)-t.y*.5f},muted,name);}
    if(valid){for(int i=0;i<6;++i)d->AddTriangleFilled(center,poly[i],poly[(i+1)%6],IM_COL32(39,169,203,65));d->AddPolyline(poly,6,IM_COL32(16,145,186,255),ImDrawFlags_Closed,1.6f);}
    ImVec2 lo(at.x+size.x-pitch_width+6,at.y+10),hi(at.x+size.x-8,at.y+size.y-10);float w=hi.x-lo.x,h=hi.y-lo.y,cx=(lo.x+hi.x)*.5f,cy=(lo.y+hi.y)*.5f;
    d->AddRectFilled(lo,hi,IM_COL32(246,250,252,255),2);
    int roles[4];int count=club_profile::positions(r,roles);
    for(int i=count-1;i>=0;--i){auto p=club_profile::pitch_point(roles[i]);int col=std::min(2,(int)(p.x*3)),row=std::min(4,(int)(p.y*5));bool main=roles[i]==r.position;
        ImVec2 a(lo.x+col*w/3,lo.y+row*h/5),b(a.x+w/3,a.y+h/5);d->AddRectFilled(a,b,main?IM_COL32(105,192,226,255):IM_COL32(202,237,248,255));}
    ImU32 line=IM_COL32(151,179,196,255);d->AddRect(lo,hi,line,0,0,1.2f);
    for(int i=1;i<3;++i)d->AddLine({lo.x+w*i/3,lo.y},{lo.x+w*i/3,hi.y},IM_COL32(207,222,231,255));
    for(int i=1;i<5;++i)d->AddLine({lo.x,lo.y+h*i/5},{hi.x,lo.y+h*i/5},IM_COL32(207,222,231,255));
    d->AddLine({lo.x,cy},{hi.x,cy},line);d->AddCircle({cx,cy},w*.16f,line,28);
    for(int end=0;end<2;++end){float y=end?hi.y:lo.y;d->AddRect({cx-w*.30f,end?y-h*.16f:y},{cx+w*.30f,end?y:y+h*.16f},line);
        d->AddRect({cx-w*.14f,end?y-h*.06f:y},{cx+w*.14f,end?y:y+h*.06f},line);}
}
inline void centered(const char*text){float x=ImGui::GetCursorPosX(),width=ImGui::GetContentRegionAvail().x;
    ImGui::SetCursorPosX(x+std::max(0.f,(width-ImGui::CalcTextSize(text).x)*.5f));ImGui::TextUnformatted(text);}
inline void stats_cells(const PlayerCompetitionRow&r,bool clean){char text[32];
    for(int column=1;column<(clean?6:5);++column){ImGui::TableSetColumnIndex(column);
        if(column==1)sprintf_s(text,"%d",r.games);else if(column==2)sprintf_s(text,"%d",r.goals);else if(column==3)sprintf_s(text,"%d",r.assists);
        else if(clean&&column==4){if(r.valid&1)sprintf_s(text,"%d",r.clean_sheets);else strcpy_s(text,"—");}
        else {double avg=player_competitions::average(r);if(avg>=0)sprintf_s(text,"%.1f",avg);else strcpy_s(text,"—");}
        if((column==1&&r.games<0)||(column==2&&r.goals<0)||(column==3&&r.assists<0))strcpy_s(text,"—");
        centered(text);}
}
inline void competition_table(const ClubPlayerRow&r,State&s,const Visuals&v,float height){
    auto stats=fifa_player::profile_competitions(r.player_id,r.team_id);bool clean=r.position>=0&&r.position<=8;
    ImGui::TextUnformatted("DESEMPENHO POR COMPETIÇÃO");
    if(!stats.available||stats.rows.empty()){ImGui::TextDisabled(stats.available?"Ainda sem jogos registrados nesta temporada.":"Estatísticas indisponíveis.");return;}
    const int cols=clean?6:5;float width=ImGui::GetContentRegionAvail().x,num=std::clamp(width*.095f,45.f,72.f);
    auto setup=[&](){ImGui::TableSetupColumn("Competição",ImGuiTableColumnFlags_WidthStretch);
        ImGui::TableSetupColumn("Jogos",ImGuiTableColumnFlags_WidthFixed,num);ImGui::TableSetupColumn("Gols",ImGuiTableColumnFlags_WidthFixed,num);
        ImGui::TableSetupColumn("Assist.",ImGuiTableColumnFlags_WidthFixed,num);if(clean)ImGui::TableSetupColumn("Sem sofrer",ImGuiTableColumnFlags_WidthFixed,num+14);
        ImGui::TableSetupColumn("Média",ImGuiTableColumnFlags_WidthFixed,num);};
    ImGui::PushStyleVar(ImGuiStyleVar_CellPadding,{8,4});
    ImGui::PushStyleColor(ImGuiCol_TableHeaderBg,ink());ImGui::PushStyleColor(ImGuiCol_TableRowBg,{1,1,1,1});ImGui::PushStyleColor(ImGuiCol_TableRowBgAlt,{.92f,.96f,.985f,1});
    float footer_width=width;
    float row_height=std::max(20.f,ImGui::GetFontSize())+8;
    height=std::min(height,row_height*(std::min(size_t(6),stats.rows.size())+1));
    if(ImGui::BeginTable("Competições do jogador",cols,ImGuiTableFlags_RowBg|ImGuiTableFlags_ScrollY|ImGuiTableFlags_SizingStretchProp,{0,height})){
        setup();ImGui::TableSetupScrollFreeze(0,1);ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});
        ImGui::TableNextRow(ImGuiTableRowFlags_Headers);const char*head[]={"Competição","Jogos","Gols","Assist.",clean?"Sem sofrer":"Média","Média"};
        for(int c=0;c<cols;++c){ImGui::TableSetColumnIndex(c);if(!c)ImGui::TextUnformatted(head[c]);else centered(head[c]);
            if(clean&&c==4&&ImGui::IsItemHovered())ImGui::SetTooltip("Jogos sem sofrer gols");}
        ImGui::PopStyleColor();
        if(s.section==2&&s.scroll_delta)ImGui::SetScrollY(std::clamp(ImGui::GetScrollY()+s.scroll_delta,0.f,ImGui::GetScrollMaxY()));
        s.competition_scroll_y=ImGui::GetScrollY();s.competition_scroll_max=ImGui::GetScrollMaxY();
        for(auto&row:stats.rows){ImGui::TableNextRow();ImGui::TableSetColumnIndex(0);auto icon=v.competition_icons.find(row.root);
            if(icon!=v.competition_icons.end()&&icon->second){ImGui::Image((ImTextureID)(intptr_t)icon->second,{20,20});ImGui::SameLine(0,6);}
            auto name=std::find_if(v.competitions.begin(),v.competitions.end(),[&](auto&i){return i.root==row.root;});
            std::string label=name!=v.competitions.end()?name->name:"Competição "+std::to_string(row.root);
            ImGui::TextWrapped("%s",utf8(label.c_str()).c_str());stats_cells(row,clean);}
        if(ImGui::GetScrollMaxY()>0)footer_width-=ImGui::GetStyle().ScrollbarSize;
        ImGui::EndTable();}
    /* Separate aligned footer remains visible when many competitions scroll. */
    if(ImGui::BeginTable("Totais das competições",cols,ImGuiTableFlags_SizingStretchProp,{footer_width,0})){setup();ImGui::TableNextRow();ImGui::TableSetBgColor(ImGuiTableBgTarget_RowBg0,IM_COL32(218,235,247,255));
        ImGui::TableSetColumnIndex(0);ImGui::TextUnformatted("TOTAL");stats_cells(player_competitions::total(stats),clean);ImGui::EndTable();}
    ImGui::PopStyleColor(3);ImGui::PopStyleVar();
}
inline Actions draw(const ClubPlayerRow&r,const char*team,State&s,const Visuals&v,fifa_player::Renderer&renderer,unsigned current_pose=0,bool allow_poses=true) {
    Actions action;screen_visuals::LightTheme theme;ImGui::PushStyleColor(ImGuiCol_Text,ink());
    ImGui::PushStyleColor(ImGuiCol_ChildBg,{0,0,0,0});ImGui::PushStyleColor(ImGuiCol_Button,{.98f,.99f,1,1});ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding,6.f);
    ImGui::SetWindowFontScale(1.1f);ImGui::TextUnformatted("Perfil de jogador");ImGui::SetWindowFontScale(1);
    /* Navigation/pose controls live in the host input lifecycle. No command
     * toolbar or pose-name selector above the player's identity. */
    (void)current_pose;(void)allow_poses;
    ImGui::Spacing();float width=ImGui::GetContentRegionAvail().x,height=std::max(180.f,ImGui::GetContentRegionAvail().y-44),model_width=width*.35f;
    ImGui::BeginChild("Modelo do perfil",{model_width,height},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    ImVec2 at=ImGui::GetCursorScreenPos(),area=ImGui::GetContentRegionAvail();auto*d=ImGui::GetWindowDrawList();unsigned rgb=club_profile::theme_color(r);
    ImU32 tint=IM_COL32(233+((rgb>>16)&255)/16,233+((rgb>>8)&255)/16,233+(rgb&255)/16,255);
    d->AddRectFilledMultiColor(at,{at.x+area.x,at.y+area.y},IM_COL32(249,250,251,255),tint,tint,IM_COL32(240,245,248,255));
    if(v.crest)d->AddImage((ImTextureID)(intptr_t)v.crest,{at.x+area.x*.18f,at.y+area.y*.17f},{at.x+area.x*.82f,at.y+area.y*.17f+area.x*.64f},{0,0},{1,1},IM_COL32(255,255,255,22));
    area.y=std::max(60.f,area.y-8);
    /* The profile shows a single large 3D player. Render this view above its
     * displayed pixel size so the model edges stay clean on high-DPI screens;
     * keep the UI panel dimensions unchanged and avoid affecting other scenes. */
    UINT render_width=(UINT)std::clamp(std::ceil(area.x*1.5f),1.f,4096.f);
    UINT render_height=(UINT)std::clamp(std::ceil(area.y*1.5f),1.f,4096.f);
    if(v.model&&renderer.model(v.model)&&renderer.render(render_width,render_height,s.yaw,s.zoom,s.portrait,0,s.pan_y,true)){
        ImGui::Image((ImTextureID)(intptr_t)renderer.image(),area);
        if(r.number>0&&r.number<=99){
            /* Match the marked upper-left slot: this is just the shirt number,
             * not a second name/number card. Use the club's primary identity
             * color so it reads like part of the profile rather than a control. */
            ImVec2 lo=ImGui::GetItemRectMin();auto*draw=ImGui::GetWindowDrawList();
            char jersey[8];sprintf_s(jersey,"%d",r.number);
            float number_size=std::clamp(ImGui::GetFontSize()*3.7f,42.f,56.f);
            ImU32 color=IM_COL32((rgb>>16)&255,(rgb>>8)&255,rgb&255,255);
            ImVec2 at={lo.x+12.f,lo.y+8.f};
            ImFont*number_font=shirt_number_font_slot();
            draw->AddText(number_font?number_font:ImGui::GetFont(),number_size,at,color,jersey);
        }
        if(ImGui::IsItemHovered()){if(ImGui::IsMouseDragging(ImGuiMouseButton_Left)){s.yaw+=ImGui::GetIO().MouseDelta.x*.012f;s.pan_y=std::clamp(s.pan_y-ImGui::GetIO().MouseDelta.y*.0015f,-.35f,.35f);}
            s.zoom=std::clamp(s.zoom+ImGui::GetIO().MouseWheel*.08f,.65f,2.f);}
    }else ImGui::TextWrapped(v.loading?"Carregando jogador 3D...":"Modelo 3D indisponível.");
    ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("Informações do perfil",{0,height},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(.92f);
    if(v.face)ImGui::Image((ImTextureID)(intptr_t)v.face,{48,48});else {ImVec2 p=ImGui::GetCursorScreenPos();ImGui::Dummy({48,48});auto*dl=ImGui::GetWindowDrawList();dl->AddCircleFilled({p.x+24,p.y+14},8,IM_COL32(145,169,188,255));dl->AddRectFilled({p.x+8,p.y+27},{p.x+40,p.y+46},IM_COL32(145,169,188,255),10);}
    ImGui::SameLine();float identity_width=ImGui::GetContentRegionAvail().x;
    if(ImGui::BeginTable("Identidade do perfil",2,ImGuiTableFlags_SizingStretchSame)){
    ImGui::TableNextColumn();ImGui::SetWindowFontScale(1.16f);ImGui::TextWrapped("%s",utf8(r.name).c_str());ImGui::SetWindowFontScale(.92f);
    ImGui::PushStyleVar(ImGuiStyleVar_ItemSpacing,{ImGui::GetStyle().ItemSpacing.x,2});ImGui::SetWindowFontScale(.9f);
    if(v.flag){ImGui::Image((ImTextureID)(intptr_t)v.flag,{24,16});ImGui::SameLine(0,6);}ImGui::TextUnformatted("Nacionalidade");
    ImGui::SetWindowFontScale(.92f);ImGui::PopStyleVar();ImGui::TableNextColumn();
    if(r.number>0&&r.number<1000){char shirt[24];sprintf_s(shirt,"Camisa %d",r.number);centered(shirt);}
    ImGui::PushStyleVar(ImGuiStyleVar_ItemSpacing,{ImGui::GetStyle().ItemSpacing.x,2});ImGui::SetWindowFontScale(.9f);
    std::string club=team&&*team?utf8(team):"Clube não informado";if(r.captain==1)club+=" · Capitão";
    identity_line(v.crest,16,club.c_str());
    if(v.league>0)identity_line(v.league_logo,16,v.league_name.empty()?"Liga não informada":utf8(v.league_name.c_str()).c_str());
    ImGui::SetWindowFontScale(.92f);ImGui::PopStyleVar();ImGui::EndTable();}ImGui::Spacing();(void)identity_width;
    reputation_stars(profile_reputation::player(v.league_strength,r.overall),12);ImGui::SameLine();ImGui::TextUnformatted("Reputação");ImGui::Spacing();
    const char*views[]={"Resumo","Desempenho","Atributos"};float vw=std::min(170.f,(ImGui::GetContentRegionAvail().x-12)/3);
    for(int i=0;i<3;++i){if(i)ImGui::SameLine(0,6);bool active=s.view_tab==i;
        if(active){ImGui::PushStyleColor(ImGuiCol_Button,ink());ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});}
        if(ImGui::Button(views[i],{vw,28})){s.view_tab=i;s.section=i==1?2:0;s.reset_scroll=true;}
        auto a=ImGui::GetItemRectMin(),b=ImGui::GetItemRectMax();s.tab_centers[i]={(a.x+b.x)*.5f,(a.y+b.y)*.5f};if(active)ImGui::PopStyleColor(2);}
    ImGui::Spacing();
    if(s.view_tab==0){
    float available=ImGui::GetContentRegionAvail().x,pw=available*.55f,bio=available-pw-ImGui::GetStyle().ItemSpacing.x,ph=std::clamp(height*.29f,156.f,196.f);
    ImGui::BeginChild("Dados pessoais",{bio,ph+22},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    ImGui::Text("%s",club_profile::position(r.position));
    int roles[4];int n=club_profile::positions(r,roles);std::string alternatives;for(int i=0;i<n;++i)if(roles[i]!=r.position){if(!alternatives.empty())alternatives+=" / ";alternatives+=club_profile::position(roles[i]);}
    ImGui::TextWrapped("Outras posições: %s",alternatives.empty()?"-":alternatives.c_str());ImGui::Spacing();float cell=bio*.40f;
    value("IDADE",r.age>=0?r.age:v.age," anos",cell);ImGui::SameLine();value("ALTURA",r.height>0?r.height:-1," cm",cell);
    value("PESO",r.weight>0?r.weight:-1," kg",cell);ImGui::SameLine();value("POTENCIAL",r.attributes[33]>=0&&r.attributes[33]<=99?r.attributes[33]:-1,"",cell);
    std::string birth=r.career_data_valid?club_profile::raw_date_label(r.birthdate_raw):"—";
    std::string retirement=!r.career_data_valid||r.retiring<0?"—":r.retiring?"Aposentando":"Ativo";
    text_value("NASCIMENTO",birth,cell);ImGui::SameLine();text_value("SITUAÇÃO",retirement,cell);
    std::string joined=r.career_data_valid?club_profile::raw_date_label(r.join_team_date_raw):"—";
    std::string tenure=r.career_data_valid?club_profile::club_tenure_label(r.join_team_date_raw,r.career_date):"—";
    std::string club_since=joined;if(tenure!="—")club_since+=" · "+tenure;
    text_value("NO CLUBE DESDE",club_since,bio*.91f);ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("Posições do perfil",{0,ph+22},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);technical_panel(r,v,{pw-8,ph});ImGui::EndChild();
    }
    if(s.view_tab==1){
        competition_table(r,s,v,std::max(90.f,ImGui::GetContentRegionAvail().y-68));
    }
    if(s.view_tab!=1){
    const char*summary[]={"RITMO","CHUTE","PASSE","DRIBLE","DEFESA","FÍSICO"};const char*keeper[]={"MERG.","MANEJO","REPOS.","POSIÇÃO","REFLEX.","REAÇÃO"};
    ImGui::TextColored({.27f,.42f,.53f,1},"RESUMO DE ATRIBUTOS");
    float gap=6,card_width=(ImGui::GetContentRegionAvail().x-gap*5)/6;
    for(int i=0;i<6;++i){if(i)ImGui::SameLine(0,gap);ImGui::PushID(i);ImVec2 p=ImGui::GetCursorScreenPos();ImGui::Dummy({card_width,54});auto*dl=ImGui::GetWindowDrawList();
        dl->AddRectFilled(p,{p.x+card_width,p.y+54},IM_COL32(235,243,249,255),6);
        const char*name=r.position==0?keeper[i]:summary[i];ImVec2 label=ImGui::CalcTextSize(name);dl->AddText({p.x+(card_width-label.x)*.5f,p.y+5},IM_COL32(46,88,119,255),name);
        int summary_value=club_profile::summary(r,i);char number[8];if(summary_value>=0)sprintf_s(number,"%d",summary_value);else strcpy_s(number,"-");
        float fs=ImGui::GetFontSize()*1.45f;ImVec2 ns=ImGui::GetFont()->CalcTextSizeA(fs,FLT_MAX,0,number);
        dl->AddText(ImGui::GetFont(),fs,{p.x+(card_width-ns.x)*.5f,p.y+21},IM_COL32(6,79,134,255),number);
        dl->AddRectFilled({p.x+8,p.y+49},{p.x+card_width-8,p.y+51},IM_COL32(205,222,234,255),1);
        if(summary_value>=0)dl->AddRectFilled({p.x+8,p.y+49},{p.x+8+(card_width-16)*summary_value/99.f,p.y+51},IM_COL32(29,111,164,255),1);
        if(ImGui::IsItemHovered())ImGui::SetTooltip(r.position==0?"%s: atributo nativo do goleiro.":"%s: média dos atributos detalhados; não altera o geral.",name);ImGui::PopID();}
    ImGui::Spacing();
    }
    if(s.view_tab==0){
        ImGui::TextColored({.27f,.42f,.53f,1},"INFORMAÇÕES FINANCEIRAS");
        float gap=6,width=ImGui::GetContentRegionAvail().x,card=(width-gap*2)/3;
        std::string wage=r.weekly_wage>=0?grouped_amount(r.weekly_wage)+" / semana":"—";
        std::string tenure=r.career_data_valid?club_profile::club_tenure_label(r.join_team_date_raw,r.career_date):"—";
        ImVec2 origin=ImGui::GetCursorScreenPos();
        finance_card("VALOR DE MERCADO","Indisponível na base",origin,card);
        finance_card("SALÁRIO SEMANAL",wage,{origin.x+card+gap,origin.y},card);
        finance_card("TEMPO NO CLUBE",tenure,{origin.x+(card+gap)*2,origin.y},card);
        ImGui::Dummy({width,53});
    }
    if(s.view_tab==2){
    float tw=(ImGui::GetContentRegionAvail().x-ImGui::GetStyle().ItemSpacing.x*5)/6;
    for(int i=0;i<6;++i){if(i)ImGui::SameLine();bool active=s.page==i;if(active){ImGui::PushStyleColor(ImGuiCol_Button,ink());ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});}
        if(ImGui::Button(pages()[i],{tw,30})){s.page=i;s.reset_scroll=true;s.section=0;}if(active)ImGui::PopStyleColor(2);}
    ImGui::PushStyleColor(ImGuiCol_Border,{.45f,.65f,.79f,1});
    ImGui::BeginChild("Atributos do perfil",{0,0},s.section==1,ImGuiWindowFlags_NoNavInputs);
    if(s.reset_scroll){ImGui::SetScrollY(0);s.reset_scroll=false;}else if(s.scroll_delta&&s.section!=2)ImGui::SetScrollY(std::clamp(ImGui::GetScrollY()+s.scroll_delta,0.f,ImGui::GetScrollMaxY()));
    s.scroll_y=ImGui::GetScrollY();s.scroll_max=ImGui::GetScrollMaxY();
    static const char*labels[]={"Aceleração","Velocidade","Agilidade","Reação","Equilíbrio","Força do chute","Finalização","Chutes de longe","Voleios","Pênaltis","Visão","Cruzamento","Passe curto","Passe longo","Curva","Cobrança de falta","Controle de bola","Drible","Força","Resistência","Impulsão","Agressividade","Interceptação","Posicionamento","Marcação","Desarme em pé","Carrinho","Cabeceio","Mergulho (GOL)","Manejo (GOL)","Reposição (GOL)","Posição (GOL)","Reflexos (GOL)","Potencial"};
    ImGui::PushStyleColor(ImGuiCol_PlotHistogram,ink());ImGui::PushStyleColor(ImGuiCol_FrameBg,{.84f,.89f,.93f,1});
    if(ImGui::BeginTable("Habilidades do perfil",2,ImGuiTableFlags_SizingStretchSame)){for(size_t i=0;i<CLUB_PLAYER_ATTRIBUTE_COUNT;++i)if(attribute_on_page(i,s.page)){
        ImGui::TableNextColumn();ImGui::PushID((int)i);ImGui::TextUnformatted(labels[i]);ImGui::SameLine(ImGui::GetCursorPosX()+ImGui::GetContentRegionAvail().x-32);
        if(r.attributes[i]>=0&&r.attributes[i]<=99){ImGui::Text("%d",r.attributes[i]);ImGui::ProgressBar(r.attributes[i]/99.f,{-1,3},"");}else ImGui::TextUnformatted("-");ImGui::Spacing();ImGui::PopID();}ImGui::EndTable();}
    ImGui::PopStyleColor(2);ImGui::EndChild();ImGui::PopStyleColor();}
    ImGui::SetWindowFontScale(1);ImGui::EndChild();ImGui::SetWindowFontScale(.80f);
    ImGui::TextWrapped("LB/RB · Q/E: abas | Esquerdo / setas: categoria e lista | Direito / arraste: câmera | LT/RT: zoom | X/P: pose | Y/F: retrato | B/Esc: voltar");ImGui::SetWindowFontScale(1);
    ImGui::PopStyleVar();ImGui::PopStyleColor(3);return action;
}
}
