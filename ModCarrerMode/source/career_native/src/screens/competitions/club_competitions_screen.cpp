#define NOMINMAX
#include "club_competitions_screen.h"
#include "../clubs/clubs_browser.h"
#include "../../render/assets/fifa_player_assets.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/native_loc_names.h"
#include "../../ui/common/screen_visuals.h"
extern "C" {
#include "../../core/fce_contracts.h"
}
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <array>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>

namespace {
struct Batch {
    unsigned serial=0,revision=0;int competition_index=0,group_index=0;
    ClubCompetitionsSnapshot data={};std::array<fifa_player::Texture,CLUB_COMPETITIONS_CAPACITY>competition_icons,trophy_icons;
    fifa_player::Texture movement_up,movement_down;
    std::array<std::string,CLUB_COMPETITIONS_CAPACITY>names;std::unordered_map<int,fifa_player::Texture>crests;
};
std::mutex guard;ClubCompetitionsSnapshot published={},visible={};unsigned revision=0,shown_revision=~0u,serial=0;
int selected=0,selected_group=0,selected_row=0,asset_selected=0,asset_group=0,focus=0,mode=0,bracket_selected_tie=0,bracket_selected_side=0;
float knockout_zoom=.68f;DWORD input_after=0,repeat_at=0;WORD previous_buttons=0;
HANDLE event=nullptr;std::string game_root;void(*logger)(const char*)=nullptr;
std::shared_ptr<const Batch>ready,shown;ID3D11Device*device=nullptr;
std::array<ID3D11ShaderResourceView*,CLUB_COMPETITIONS_CAPACITY>competition_views={};
std::array<ID3D11ShaderResourceView*,CLUB_COMPETITIONS_CAPACITY>trophy_views={};
ID3D11ShaderResourceView*movement_up_view=nullptr,*movement_down_view=nullptr;
std::unordered_map<int,ID3D11ShaderResourceView*>crest_views;

const ClubCompetitionEntry*current(){return selected>=0&&(size_t)selected<visible.count?visible.entries+selected:nullptr;}
int selected_stage_index(const ClubCompetitionEntry*entry){if(!entry||!entry->group_count)return -1;return std::clamp(selected_group,0,(int)entry->group_count-1);}
const ClubCompetitionTableRow*visible_rows(const ClubCompetitionEntry*entry,size_t*count){
    if(count)*count=0;if(!entry)return nullptr;
    if(entry->has_group_phase&&mode==0){int i=selected_stage_index(entry);if(i<0)return nullptr;if(count)*count=entry->groups[i].row_count;return entry->groups[i].rows;}
    if(entry->table_available&&mode==0){if(count)*count=entry->table_count;return entry->table;}return nullptr;
}
void release_views(){for(auto&v:competition_views)screen_visuals::release(v);for(auto&v:trophy_views)screen_visuals::release(v);screen_visuals::release(movement_up_view);screen_visuals::release(movement_down_view);for(auto&v:crest_views)screen_visuals::release(v.second);crest_views.clear();shown.reset();}
void request_assets(){std::lock_guard<std::mutex>lock(guard);asset_selected=selected;asset_group=selected_group;++serial;ready.reset();if(event)SetEvent(event);}
void sync_snapshot(){unsigned rev=0;bool changed=false;int keep=0,old_id=current()?current()->competition:0;{
        std::lock_guard<std::mutex>lock(guard);rev=revision;if(rev==shown_revision)return;visible=published;shown_revision=rev;}
    for(size_t i=0;i<visible.count&&i<CLUB_COMPETITIONS_CAPACITY;++i)if(old_id&&visible.entries[i].competition==old_id){keep=(int)i;break;}
    if(selected!=keep)changed=true;selected=keep;selected_row=0;bracket_selected_tie=0;bracket_selected_side=0;const ClubCompetitionEntry*entry=current();
    if(entry&&entry->group_count){int preferred=entry->preferred_group>=0?entry->preferred_group:0;preferred=std::clamp(preferred,0,(int)entry->group_count-1);
        if(selected_group!=(entry->preferred_group>=0?preferred:0))changed=true;selected_group=preferred;}
    else{if(selected_group!=0)changed=true;selected_group=0;}
    mode=entry&&entry->has_group_phase&&entry->current_stage_kind>FCE_STAGE_GROUP?1:0;
    (void)changed;request_assets();
}
void copy_crest(fifa_player::Assets&assets,int id,std::unordered_map<int,fifa_player::Texture>&out){
    if(id<=0||out.count(id))return;fifa_player::Texture tex;if(assets.crest(id,tex))out.emplace(id,std::move(tex));
}
DWORD WINAPI worker(void*){fifa_player::Assets assets(game_root);native_loc::Names names(game_root);for(;;){
        if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;unsigned token=0,rev=0;int comp=0,group=0;auto batch=std::make_shared<Batch>();
        {std::lock_guard<std::mutex>lock(guard);token=serial;rev=revision;batch->data=published;comp=std::clamp(asset_selected,0,(int)(batch->data.count?batch->data.count-1:0));group=asset_group;}
        const ClubCompetitionsSnapshot&data=batch->data;batch->serial=token;batch->revision=rev;batch->competition_index=comp;batch->group_index=group;
        try{assets.competition_movement_icon(true,batch->movement_up);assets.competition_movement_icon(false,batch->movement_down);
            for(size_t i=0;i<data.count&&i<CLUB_COMPETITIONS_CAPACITY;++i){const auto&e=data.entries[i];
                if(e.asset>0)assets.competition_icon(e.asset,batch->competition_icons[i]);
                if(e.trophy_asset>0)assets.trophy_icon(e.trophy_asset,batch->trophy_icons[i]);batch->names[i]=names.competition(e.asset>0?e.asset:e.competition);
                if(batch->names[i].empty())batch->names[i]="Competição";}
            if(comp>=0&&(size_t)comp<data.count){const auto&e=data.entries[comp];const ClubCompetitionTableRow*rows=nullptr;size_t count=0;
                if(e.has_group_phase&&e.group_count){int gi=std::clamp(group,0,(int)e.group_count-1);rows=e.groups[gi].rows;count=e.groups[gi].row_count;}
                else if(e.table_available){rows=e.table;count=e.table_count;}
                for(size_t i=0;rows&&i<count&&i<CLUB_COMPETITION_TABLE_CAPACITY;++i)copy_crest(assets,rows[i].team,batch->crests);
                if(e.previous.visible){copy_crest(assets,e.previous.home_team,batch->crests);copy_crest(assets,e.previous.away_team,batch->crests);}
                if(e.next.visible){copy_crest(assets,e.next.home_team,batch->crests);copy_crest(assets,e.next.away_team,batch->crests);}}
            if(comp>=0&&(size_t)comp<data.count){const auto&e=data.entries[comp];for(size_t i=0;i<e.bracket_team_count&&i<CLUB_COMPETITION_BRACKET_TEAM_CAPACITY;++i)copy_crest(assets,e.bracket_teams[i].id,batch->crests);}
        }catch(...){if(logger)logger("ClubCompetitions: artwork worker failed; text data remains available");}
        {std::lock_guard<std::mutex>lock(guard);if(batch->serial==serial&&batch->revision==revision)ready=std::move(batch);}
    }}
DWORD WINAPI guarded_worker(void*){try{return worker(nullptr);}catch(...){if(logger)logger("ClubCompetitions: asset worker stopped; screen stays usable");return 1;}}
void sync_assets(){std::shared_ptr<const Batch>next;{std::lock_guard<std::mutex>lock(guard);if(ready&&ready->serial==serial&&ready->revision==revision)next=ready;}
    if(!device||!next||next==shown)return;release_views();shown=next;
    for(size_t i=0;i<competition_views.size();++i){competition_views[i]=screen_visuals::upload(device,next->competition_icons[i]);trophy_views[i]=screen_visuals::upload(device,next->trophy_icons[i]);}
    movement_up_view=screen_visuals::upload(device,next->movement_up);movement_down_view=screen_visuals::upload(device,next->movement_down);
    for(const auto&item:next->crests){auto*view=screen_visuals::upload(device,item.second);if(view)crest_views.emplace(item.first,view);}}
ID3D11ShaderResourceView*crest(int team){auto i=crest_views.find(team);return i==crest_views.end()?nullptr:i->second;}
ImU32 form_color(int result){return result>0?IM_COL32(43,169,91,255):result<0?IM_COL32(232,65,58,255):result==0?IM_COL32(151,153,160,255):IM_COL32(210,214,218,255);}
void draw_form_mark(ImDrawList*dl,ImVec2 center,int result,float radius){const ImU32 white=IM_COL32(255,255,255,255);
    if(result>0){dl->AddLine({center.x-radius*.48f,center.y},{center.x-radius*.12f,center.y+radius*.34f},white,1.6f);dl->AddLine({center.x-radius*.12f,center.y+radius*.34f},{center.x+radius*.5f,center.y-radius*.38f},white,1.6f);}
    else if(result<0){dl->AddLine({center.x-radius*.33f,center.y-radius*.33f},{center.x+radius*.33f,center.y+radius*.33f},white,1.5f);dl->AddLine({center.x+radius*.33f,center.y-radius*.33f},{center.x-radius*.33f,center.y+radius*.33f},white,1.5f);}
    else if(result==0)dl->AddLine({center.x-radius*.4f,center.y},{center.x+radius*.4f,center.y},white,1.6f);
}
void draw_form(const ClubCompetitionTableRow&row){ImVec2 start=ImGui::GetCursorScreenPos();auto*dl=ImGui::GetWindowDrawList();
    for(int i=0;i<CLUB_COMPETITION_FORM_SIZE;++i){int result=row.form[i];ImVec2 center={start.x+8+i*19.f,start.y+8};dl->AddCircleFilled(center,6.7f,form_color(result));
        if(result!=2)draw_form_mark(dl,center,result,6.7f);if(i==CLUB_COMPETITION_FORM_SIZE-1&&result!=2)dl->AddCircle(center,8.2f,form_color(result),0,1.25f);}
    ImGui::Dummy({CLUB_COMPETITION_FORM_SIZE*19.f,18});}
ImU32 zone_color(int zone){switch(zone){case CLUB_COMPETITION_ZONE_PRIMARY:case CLUB_COMPETITION_ZONE_ADVANCE:return IM_COL32(53,145,255,255);
    case CLUB_COMPETITION_ZONE_SECONDARY:return IM_COL32(244,126,26,255);case CLUB_COMPETITION_ZONE_SAFE:return IM_COL32(43,171,87,255);
    case CLUB_COMPETITION_ZONE_RELEGATION:case CLUB_COMPETITION_ZONE_OUTSIDE:return IM_COL32(239,57,53,255);default:return 0;}}
void draw_movement_cell(const ClubCompetitionTableRow&row){ID3D11ShaderResourceView*icon=row.movement>0?movement_up_view:row.movement<0?movement_down_view:nullptr;
    ImVec2 p=ImGui::GetCursorScreenPos();ImVec2 hit_max={p.x+19,p.y+23};if(icon)ImGui::Image((ImTextureID)(intptr_t)icon,{13,13});else ImGui::Dummy({13,13});
    if(icon&&ImGui::IsMouseHoveringRect(p,hit_max)){ImGui::BeginTooltip();ImGui::TextUnformatted(row.movement>0?"Subiu desde a rodada anterior":"Desceu desde a rodada anterior");ImGui::EndTooltip();}}
void draw_legend_zone_item(float x,float y,ImU32 color,const char*label){auto*dl=ImGui::GetWindowDrawList();dl->AddRectFilled({x,y+3},{x+7,y+10},color);ImGui::SetCursorScreenPos({x+14,y});ImGui::TextDisabled("%s",label);}
void draw_legend_form_item(float x,float y,int result,const char*label){auto*dl=ImGui::GetWindowDrawList();ImVec2 center={x+7,y+8};dl->AddCircleFilled(center,6,form_color(result));draw_form_mark(dl,center,result,6);
    ImGui::SetCursorScreenPos({x+19,y});ImGui::TextDisabled("%s",label);}
void draw_table_legend(bool group_table){ImVec2 start=ImGui::GetCursorScreenPos();ImVec2 avail=ImGui::GetContentRegionAvail();const float h=104.f;
    auto*dl=ImGui::GetWindowDrawList();dl->AddRectFilled(start,{start.x+avail.x,start.y+h},IM_COL32(246,247,248,255),4.f);dl->AddRect(start,{start.x+avail.x,start.y+h},IM_COL32(207,211,214,255),4.f);
    const float left=start.x+14.f,right=start.x+avail.x*.51f;ImGui::SetCursorScreenPos({left,start.y+8});ImGui::Text("%s",group_table?"Classificação do grupo":"Qualificação/Rebaixamento");
    if(group_table){draw_legend_zone_item(left,start.y+31,zone_color(CLUB_COMPETITION_ZONE_ADVANCE),"Avança para a fase eliminatória");
        draw_legend_zone_item(left,start.y+51,zone_color(CLUB_COMPETITION_ZONE_OUTSIDE),"Fora da faixa de classificação");}
    else{draw_legend_zone_item(left,start.y+29,zone_color(CLUB_COMPETITION_ZONE_PRIMARY),"Fase de grupos da competição principal");
        draw_legend_zone_item(left,start.y+46,zone_color(CLUB_COMPETITION_ZONE_SECONDARY),"Qualificatórias da competição principal");
        draw_legend_zone_item(left,start.y+63,zone_color(CLUB_COMPETITION_ZONE_SAFE),"Vaga em competição continental adicional");
        draw_legend_zone_item(left,start.y+80,zone_color(CLUB_COMPETITION_ZONE_RELEGATION),"Rebaixamento");}
    ImGui::SetCursorScreenPos({right,start.y+8});ImGui::TextUnformatted("Últimas 5 partidas");
    draw_legend_form_item(right,start.y+31,1,"Vitórias");draw_legend_form_item(right,start.y+51,0,"Empates");draw_legend_form_item(right,start.y+71,-1,"Derrotas");
    ImGui::SetCursorScreenPos({start.x,start.y+h+4});}
void draw_table(const ClubCompetitionEntry&entry){size_t count=0;const ClubCompetitionTableRow*rows=visible_rows(&entry,&count);
    if(!rows||!count){ImGui::SetCursorPosY(ImGui::GetCursorPosY()+24);ImGui::TextDisabled("A classificação ou o grupo ainda não foi disponibilizado nesta temporada.");return;}
    const bool group_table=entry.has_group_phase&&mode==0;const bool show_movement=!entry.is_cup&&!entry.has_group_phase&&entry.table_available&&mode==0;
    const int columns=show_movement?14:13;const float legend_h=108.f;float table_h=std::max(125.f,ImGui::GetContentRegionAvail().y-legend_h-4.f);
    ImGui::PushStyleVar(ImGuiStyleVar_ChildRounding,0.f);ImGui::PushStyleVar(ImGuiStyleVar_ChildBorderSize,0.f);
    ImGui::PushStyleColor(ImGuiCol_ChildBg,{1.f,1.f,1.f,1.f});ImGui::PushStyleColor(ImGuiCol_Border,{1.f,1.f,1.f,0.f});
    ImGui::BeginChild("Tabela de classificação",ImVec2(0,table_h),false,ImGuiWindowFlags_NoNavInputs);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{0.f,0.f});ImGui::PushStyleVar(ImGuiStyleVar_CellPadding,{5.f,3.f});
    ImGui::PushStyleColor(ImGuiCol_TableHeaderBg,{1.f,1.f,1.f,1.f});ImGui::PushStyleColor(ImGuiCol_TableRowBg,{1.f,1.f,1.f,1.f});
    ImGui::PushStyleColor(ImGuiCol_TableRowBgAlt,{1.f,1.f,1.f,1.f});ImGui::PushStyleColor(ImGuiCol_TableBorderStrong,{.78f,.79f,.80f,1.f});
    ImGui::PushStyleColor(ImGuiCol_TableBorderLight,{.86f,.87f,.88f,1.f});ImGui::PushStyleColor(ImGuiCol_Text,{.12f,.15f,.18f,1.f});
    ImGuiTableFlags flags=ImGuiTableFlags_BordersInnerH|ImGuiTableFlags_RowBg|ImGuiTableFlags_SizingStretchProp|ImGuiTableFlags_ScrollY;
    if(ImGui::BeginTable("ClubCompetitionTable",columns,flags,ImVec2(0,0))){
        ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,27);ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,8);
        if(show_movement)ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,18);
        ImGui::TableSetupColumn("",ImGuiTableColumnFlags_WidthFixed,25);ImGui::TableSetupColumn("Clube",ImGuiTableColumnFlags_WidthStretch,2.7f);
        ImGui::TableSetupColumn("Pts",ImGuiTableColumnFlags_WidthFixed,35);ImGui::TableSetupColumn("PJ",ImGuiTableColumnFlags_WidthFixed,31);
        ImGui::TableSetupColumn("VIT",ImGuiTableColumnFlags_WidthFixed,31);ImGui::TableSetupColumn("E",ImGuiTableColumnFlags_WidthFixed,23);
        ImGui::TableSetupColumn("DER",ImGuiTableColumnFlags_WidthFixed,32);ImGui::TableSetupColumn("GM",ImGuiTableColumnFlags_WidthFixed,32);
        ImGui::TableSetupColumn("GC",ImGuiTableColumnFlags_WidthFixed,32);ImGui::TableSetupColumn("SG",ImGuiTableColumnFlags_WidthFixed,32);
        ImGui::TableSetupColumn("Últimas 5",ImGuiTableColumnFlags_WidthStretch,1.45f);ImGui::TableHeadersRow();
        const int crest_col=show_movement?3:2,club_col=crest_col+1,points_col=club_col+1;
        for(size_t i=0;i<count&&i<CLUB_COMPETITION_TABLE_CAPACITY;++i){const auto&r=rows[i];ImGui::TableNextRow(ImGuiTableRowFlags_None,27);
            if(r.team==visible.club)ImGui::TableSetBgColor(ImGuiTableBgTarget_RowBg0,IM_COL32(234,244,252,255));
            ImGui::TableSetColumnIndex(0);ImVec2 row_start=ImGui::GetCursorScreenPos();ImGui::PushStyleColor(ImGuiCol_Header,{.90f,.94f,.96f,1.f});ImGui::PushStyleColor(ImGuiCol_HeaderHovered,{.86f,.92f,.96f,1.f});
            ImGui::PushID(r.team);bool activate=ImGui::Selectable("##clube",focus==2&&i==(size_t)selected_row,ImGuiSelectableFlags_SpanAllColumns,ImVec2(0,23));ImGui::PopID();ImGui::PopStyleColor(2);ImGui::SetCursorScreenPos(row_start);
            if(activate){focus=2;selected_row=(int)i;clubs_browser_open_team(r.team);}
            ImGui::Text("%d",r.rank);
            ImGui::TableSetColumnIndex(1);if(ImU32 color=zone_color(r.zone)){ImVec2 p=ImGui::GetCursorScreenPos();ImGui::GetWindowDrawList()->AddRectFilled({p.x+1,p.y+1},{p.x+5,p.y+23},color);}
            ImGui::Dummy({8,22});if(show_movement){ImGui::TableSetColumnIndex(2);draw_movement_cell(r);}
            ImGui::TableSetColumnIndex(crest_col);if(auto*v=crest(r.team))ImGui::Image((ImTextureID)(intptr_t)v,{20,20});else ImGui::Dummy({20,20});
            ImGui::TableSetColumnIndex(club_col);ImGui::TextUnformatted(r.name[0]?r.name:"Clube");if(ImGui::IsItemHovered())ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
            ImGui::TableSetColumnIndex(points_col);ImGui::Text("%d",r.points);ImGui::TableSetColumnIndex(points_col+1);ImGui::Text("%d",r.played);
            ImGui::TableSetColumnIndex(points_col+2);ImGui::Text("%d",r.won);ImGui::TableSetColumnIndex(points_col+3);ImGui::Text("%d",r.drawn);
            ImGui::TableSetColumnIndex(points_col+4);ImGui::Text("%d",r.lost);ImGui::TableSetColumnIndex(points_col+5);ImGui::Text("%d",r.goals_for);
            ImGui::TableSetColumnIndex(points_col+6);ImGui::Text("%d",r.goals_against);ImGui::TableSetColumnIndex(points_col+7);ImGui::Text("%d",r.goals_for-r.goals_against);
            ImGui::TableSetColumnIndex(points_col+8);draw_form(r);
        }ImGui::EndTable();}
    ImGui::PopStyleColor(6);ImGui::PopStyleVar(2);ImGui::EndChild();ImGui::PopStyleColor(2);ImGui::PopStyleVar(2);
    draw_table_legend(group_table);
}
std::string team_name(const ClubCompetitionEntry&e,int id){for(size_t i=0;i<e.table_count;++i)if(e.table[i].team==id)return e.table[i].name;
    for(size_t g=0;g<e.group_count;++g)for(size_t i=0;i<e.groups[g].row_count;++i)if(e.groups[g].rows[i].team==id)return e.groups[g].rows[i].name;
    for(size_t i=0;i<e.bracket_team_count;++i)if(e.bracket_teams[i].id==id)return e.bracket_teams[i].name;
    return id>0?"Clube":"A definir";}
struct BracketColumn {int stage_kind=FCE_STAGE_UNKNOWN;std::vector<int>ties;int slots=0;};
const char*bracket_stage_name(int kind){switch(kind){case FCE_STAGE_ROUND_1:return "1ª fase";case FCE_STAGE_ROUND_2:return "2ª fase";
    case FCE_STAGE_ROUND_32:return "Fase de 32";case FCE_STAGE_ROUND_16:return "Oitavas";case FCE_STAGE_QUARTER_FINAL:return "Quartas";
    case FCE_STAGE_SEMI_FINAL:return "Semifinal";case FCE_STAGE_FINAL:return "Final";default:return "Mata-mata";}}
std::vector<BracketColumn>bracket_columns(const ClubCompetitionEntry&e){
    static const int order[]={FCE_STAGE_ROUND_1,FCE_STAGE_ROUND_2,FCE_STAGE_ROUND_32,FCE_STAGE_ROUND_16,FCE_STAGE_QUARTER_FINAL,FCE_STAGE_SEMI_FINAL,FCE_STAGE_FINAL};
    std::vector<BracketColumn>out;int first=FCE_STAGE_FINAL;
    for(size_t i=0;i<e.bracket_tie_count&&i<CLUB_COMPETITION_BRACKET_TIE_CAPACITY;++i)if(e.bracket_ties[i].stage_kind>=FCE_STAGE_ROUND_1&&e.bracket_ties[i].stage_kind<=FCE_STAGE_FINAL)first=std::min(first,e.bracket_ties[i].stage_kind);
    if(first==FCE_STAGE_FINAL&&!e.bracket_tie_count)return out;
    int previous_slots=0;bool started=false;
    for(int kind:order){if(kind<first)continue;BracketColumn column;column.stage_kind=kind;
        for(size_t i=0;i<e.bracket_tie_count&&i<CLUB_COMPETITION_BRACKET_TIE_CAPACITY;++i)if(e.bracket_ties[i].stage_kind==kind)column.ties.push_back((int)i);
        if(!started&&column.ties.empty())continue;started=true;
        column.slots=!column.ties.empty()?(int)column.ties.size():std::max(1,(previous_slots+1)/2);
        previous_slots=column.slots;out.push_back(std::move(column));}
    return out;
}
std::vector<int>bracket_navigation_indices(const ClubCompetitionEntry&e){std::vector<int>out;for(const auto&column:bracket_columns(e))out.insert(out.end(),column.ties.begin(),column.ties.end());return out;}
int score_for_team(const ClubCompetitionMatch&m,int team,bool*valid){
    bool ok=m.visible&&m.played&&m.home_score>=0&&m.away_score>=0&&(m.home_team==team||m.away_team==team);
    if(valid)*valid=ok;if(!ok)return 0;return m.home_team==team?m.home_score:m.away_score;
}
std::string score_label(int value,bool valid){return valid?std::to_string(value):"–";}
void draw_bracket_team(ImDrawList*dl,const ClubCompetitionEntry&e,const ClubCompetitionBracketTie&tie,int team,int side,
    float x,float y,float zoom,float width,float heading_y,bool selected,bool active_side){
    const float row_h=22.f*zoom;float name_right=x+width-116.f*zoom;
    if(selected&&active_side)dl->AddRectFilled({x+4*zoom,y-2*zoom},{x+width-4*zoom,y+row_h-2*zoom},IM_COL32(222,239,250,255),4*zoom);
    if(auto*image=crest(team))dl->AddImageRounded((ImTextureID)(intptr_t)image,{x+8*zoom,y},{x+26*zoom,y+18*zoom},ImVec2(0,0),ImVec2(1,1),IM_COL32_WHITE,3*zoom);
    else dl->AddRectFilled({x+8*zoom,y+1*zoom},{x+26*zoom,y+19*zoom},IM_COL32(219,228,235,255),3*zoom);
    std::string name=team_name(e,team);dl->PushClipRect({x+30*zoom,y},{name_right,y+row_h},true);
    dl->AddText(ImGui::GetFont(),std::max(10.f,ImGui::GetFontSize()*zoom),{x+31*zoom,y+2*zoom},IM_COL32(36,58,79,255),name.c_str());dl->PopClipRect();
    bool ida_ok=false,volta_ok=false;int ida=0,volta=0,total=0;
    if(tie.leg_count>0)ida=score_for_team(tie.legs[0],team,&ida_ok);
    if(tie.leg_count>1)volta=score_for_team(tie.legs[1],team,&volta_ok);
    bool total_ok=ida_ok||volta_ok;if(total_ok)total=(ida_ok?ida:0)+(volta_ok?volta:0);
    const bool single=tie.stage_kind==FCE_STAGE_FINAL&&tie.leg_count<2;
    const char*first_label=single?"JOGO":tie.leg_count>1?"IDA":"JOGO";
    const float score_start=x+width-111*zoom;const float col_w=36*zoom;
    auto score_text=[&](int col,const std::string&text,ImU32 color){ImVec2 size=ImGui::GetFont()->CalcTextSizeA(std::max(10.f,ImGui::GetFontSize()*zoom),FLT_MAX,0,text.c_str());
        dl->AddText(ImGui::GetFont(),std::max(10.f,ImGui::GetFontSize()*zoom),{score_start+col*col_w+(col_w-size.x)*.5f,y+2*zoom},color,text.c_str());};
    (void)side;(void)heading_y;
    score_text(0,score_label(ida,ida_ok),ida_ok?IM_COL32(28,54,78,255):IM_COL32(147,159,171,255));
    score_text(1,single?"–":score_label(volta,volta_ok),volta_ok?IM_COL32(28,54,78,255):IM_COL32(147,159,171,255));
    std::string total_text=score_label(total,total_ok);if(total_ok&&!single&&!volta_ok)total_text+="*";
    score_text(2,total_text,total_ok?IM_COL32(7,91,155,255):IM_COL32(147,159,171,255));
}
void draw_bracket_tie(ImDrawList*dl,const ClubCompetitionEntry&e,const ClubCompetitionBracketTie&tie,int tie_index,
    ImVec2 origin,float x,float y,float zoom,bool selected,int selected_side,bool active){
    const float width=280*zoom,height=84*zoom;ImVec2 min={origin.x+x,origin.y+y},max={min.x+width,min.y+height};
    dl->AddRectFilled(min,max,selected?IM_COL32(255,255,255,255):IM_COL32(255,255,255,248),6*zoom);
    dl->AddRect(min,max,selected?IM_COL32(18,105,163,255):IM_COL32(208,219,228,255),6*zoom,0,selected?2*zoom:1*zoom);
    const char*first_label=tie.stage_kind==FCE_STAGE_FINAL&&tie.leg_count<2?"FINAL":tie.leg_count>1?"IDA":"JOGO";
    const float score_x=min.x+width-111*zoom,col_w=36*zoom;float head_size=std::max(9.f,ImGui::GetFontSize()*.68f);
    const char*labels[]={first_label,tie.leg_count>1?"VOLTA":"—","TOTAL"};
    for(int i=0;i<3;++i){ImVec2 s=ImGui::GetFont()->CalcTextSizeA(head_size,FLT_MAX,0,labels[i]);dl->AddText(ImGui::GetFont(),head_size,{score_x+i*col_w+(col_w-s.x)*.5f,min.y+5*zoom},IM_COL32(103,123,142,255),labels[i]);}
    draw_bracket_team(dl,e,tie,tie.team_a,0,min.x,min.y+24*zoom,zoom,width,min.y+5*zoom,selected,selected_side==0);
    draw_bracket_team(dl,e,tie,tie.team_b,1,min.x,min.y+52*zoom,zoom,width,min.y+5*zoom,selected,selected_side==1);
    if(active){for(int side=0;side<2;++side){ImVec2 row_min={min.x,min.y+(side?49.f:21.f)*zoom},row_max={max.x,min.y+(side?77.f:49.f)*zoom};
            if(ImGui::IsMouseHoveringRect(row_min,row_max)){ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);if(ImGui::IsMouseClicked(ImGuiMouseButton_Left)){bracket_selected_tie=tie_index;bracket_selected_side=side;focus=3;}
                if(ImGui::IsMouseDoubleClicked(ImGuiMouseButton_Left)){bracket_selected_tie=tie_index;bracket_selected_side=side;clubs_browser_open_team(side?tie.team_b:tie.team_a);}}}}
}
void draw_bracket_placeholder(ImDrawList*dl,ImVec2 origin,float x,float y,float zoom){const float width=280*zoom,height=84*zoom;ImVec2 min={origin.x+x,origin.y+y},max={min.x+width,min.y+height};
    dl->AddRectFilled(min,max,IM_COL32(249,251,253,255),6*zoom);dl->AddRect(min,max,IM_COL32(218,226,234,255),6*zoom,0,1*zoom);
    const char*label="Aguardando definição";ImVec2 size=ImGui::GetFont()->CalcTextSizeA(std::max(10.f,ImGui::GetFontSize()*zoom),FLT_MAX,0,label);
    dl->AddText(ImGui::GetFont(),std::max(10.f,ImGui::GetFontSize()*zoom),{min.x+(width-size.x)*.5f,min.y+25*zoom},IM_COL32(111,128,145,255),label);
}
void open_selected_bracket_team(){const auto*e=current();if(!e||bracket_selected_tie<0||(size_t)bracket_selected_tie>=e->bracket_tie_count)return;
    const auto&tie=e->bracket_ties[bracket_selected_tie];int id=bracket_selected_side?tie.team_b:tie.team_a;if(id>0)clubs_browser_open_team(id);}
void draw_knockout(const ClubCompetitionEntry&e,const XINPUT_STATE&pad,bool active){
    std::vector<BracketColumn>columns=bracket_columns(e);if(columns.empty()){
        ImGui::TextUnformatted("MATA-MATA");ImGui::Separator();ImGui::Spacing();
        ImGui::TextDisabled("O chaveamento e os confrontos serão exibidos quando a competição chegar à fase eliminatória.");return;}
    int actual_count=0;for(const auto&column:columns)actual_count+=(int)column.ties.size();if(actual_count<=0){ImGui::TextDisabled("Ainda não há confrontos confirmados nesta fase.");return;}
    std::vector<int>navigable=bracket_navigation_indices(e);if(navigable.empty()){ImGui::TextDisabled("Ainda não há confrontos confirmados nesta fase.");return;}
    if(std::find(navigable.begin(),navigable.end(),bracket_selected_tie)==navigable.end())bracket_selected_tie=navigable.front();
    ImGui::TextUnformatted("CHAVEAMENTO");ImGui::SameLine();ImGui::TextDisabled("Clubes, jogos de ida e volta e agregado");
    ImGui::SameLine(ImGui::GetWindowWidth()-360);ImGui::TextUnformatted("Zoom");ImGui::SameLine();float zoom_percent=knockout_zoom*100.f;ImGui::SetNextItemWidth(150);
    if(ImGui::SliderFloat("##zoom-chaveamento",&zoom_percent,65.f,145.f,"%.0f%%",ImGuiSliderFlags_NoInput))knockout_zoom=zoom_percent/100.f;
    ImGui::SameLine();ImGui::TextDisabled("LT / RT");
    float view_h=std::max(200.f,ImGui::GetContentRegionAvail().y-2.f);ImGui::BeginChild("Chaveamento navegável",{0,view_h},true,ImGuiWindowFlags_HorizontalScrollbar);
    auto&io=ImGui::GetIO();if(ImGui::IsWindowHovered()){
        if(io.MouseWheel!=0){float old=knockout_zoom;knockout_zoom=std::clamp(knockout_zoom+io.MouseWheel*.08f,.65f,1.45f);
            float cx=ImGui::GetWindowWidth()*.5f,cy=ImGui::GetWindowHeight()*.5f;ImGui::SetScrollX((ImGui::GetScrollX()+cx)*knockout_zoom/old-cx);ImGui::SetScrollY((ImGui::GetScrollY()+cy)*knockout_zoom/old-cy);}
        if(ImGui::IsMouseDragging(ImGuiMouseButton_Middle)||ImGui::IsMouseDragging(ImGuiMouseButton_Right)){ImGui::SetScrollX(ImGui::GetScrollX()-io.MouseDelta.x);ImGui::SetScrollY(ImGui::GetScrollY()-io.MouseDelta.y);}
    }
    if(active&&focus==3){float speed=620.f*io.DeltaTime;
        if(abs(pad.Gamepad.sThumbRX)>8500)ImGui::SetScrollX(ImGui::GetScrollX()+((float)pad.Gamepad.sThumbRX/32767.f)*speed);
        if(abs(pad.Gamepad.sThumbRY)>8500)ImGui::SetScrollY(ImGui::GetScrollY()-((float)pad.Gamepad.sThumbRY/32767.f)*speed);
        if(io.KeyShift){if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow))ImGui::SetScrollX(ImGui::GetScrollX()-210.f);
            if(ImGui::IsKeyPressed(ImGuiKey_RightArrow))ImGui::SetScrollX(ImGui::GetScrollX()+210.f);
            if(ImGui::IsKeyPressed(ImGuiKey_UpArrow))ImGui::SetScrollY(ImGui::GetScrollY()-180.f);
            if(ImGui::IsKeyPressed(ImGuiKey_DownArrow))ImGui::SetScrollY(ImGui::GetScrollY()+180.f);}
        if(ImGui::IsKeyPressed(ImGuiKey_Home)){ImGui::SetScrollX(0);ImGui::SetScrollY(0);}
    }
    float base_h=std::max(440.f,64.f+columns.front().slots*96.f);float base_w=48.f+columns.size()*322.f;
    float canvas_w=base_w*knockout_zoom,canvas_h=base_h*knockout_zoom;ImVec2 origin=ImGui::GetCursorScreenPos();ImGui::InvisibleButton("##espaco-chaveamento",{canvas_w,canvas_h});
    ImDrawList*dl=ImGui::GetWindowDrawList();const float top=46.f,card_w=280.f;
    auto node_y=[&](int index,int slots){return top+(index+.5f)*(base_h-64.f)/std::max(1,slots);};
    for(size_t ci=0;ci<columns.size();++ci){const auto&column=columns[ci];float x=(24.f+ci*322.f)*knockout_zoom;
        ImVec2 label_pos={origin.x+x,origin.y+9.f*knockout_zoom};dl->AddText(ImGui::GetFont(),std::max(10.f,ImGui::GetFontSize()*knockout_zoom),label_pos,IM_COL32(55,83,108,255),bracket_stage_name(column.stage_kind));
        if(ci+1<columns.size()){const auto&next=columns[ci+1];float next_x=(24.f+(ci+1)*322.f)*knockout_zoom;
            for(int i=0;i<column.slots;++i){int next_index=std::min(next.slots-1,(int)((long long)i*next.slots/std::max(1,column.slots)));
                float y1=node_y(i,column.slots)*knockout_zoom,y2=node_y(next_index,next.slots)*knockout_zoom,join=x+card_w*knockout_zoom+18.f*knockout_zoom;
                dl->AddLine({origin.x+x+card_w*knockout_zoom,origin.y+y1},{origin.x+join,origin.y+y1},IM_COL32(178,194,208,255),1.5f*knockout_zoom);
                dl->AddLine({origin.x+join,origin.y+std::min(y1,y2)},{origin.x+join,origin.y+std::max(y1,y2)},IM_COL32(178,194,208,255),1.5f*knockout_zoom);
                dl->AddLine({origin.x+join,origin.y+y2},{origin.x+next_x,origin.y+y2},IM_COL32(178,194,208,255),1.5f*knockout_zoom);}}
        for(int slot=0;slot<column.slots;++slot){float y=(node_y(slot,column.slots)-38.f)*knockout_zoom;float card_x=x;
            if((size_t)slot<column.ties.size()){int tie_index=column.ties[slot];const auto&tie=e.bracket_ties[tie_index];bool is_selected=focus==3&&bracket_selected_tie==tie_index;
                draw_bracket_tie(dl,e,tie,tie_index,origin,card_x,y,knockout_zoom,is_selected,bracket_selected_side,active);
            }else draw_bracket_placeholder(dl,origin,card_x,y,knockout_zoom);
        }
    }
    ImGui::EndChild();ImGui::TextDisabled("A/D-pad: confronto  ·  ←/→: clube selecionado  ·  X: alternar clube  ·  A: abrir clube  ·  analógico direito / arrastar botão direito: mover  ·  roda / LT-RT: zoom  ·  Shift+setas: mover  ·  Home: início");
}
void open_selected_club(){auto*e=current();size_t count=0;const auto*rows=visible_rows(e,&count);if(rows&&count){selected_row=std::clamp(selected_row,0,(int)count-1);clubs_browser_open_team(rows[selected_row].team);}}
void change_competition(int delta){if(!visible.count)return;selected=(selected+delta+(int)visible.count)%(int)visible.count;selected_group=0;selected_row=0;
    bracket_selected_tie=0;bracket_selected_side=0;
    auto*e=current();if(e&&e->preferred_group>=0&&e->group_count)selected_group=std::clamp(e->preferred_group,0,(int)e->group_count-1);
    mode=e&&e->has_group_phase&&e->current_stage_kind>FCE_STAGE_GROUP?1:0;focus=0;request_assets();}
void change_group(int delta){auto*e=current();if(!e||!e->group_count)return;selected_group=(selected_group+delta+(int)e->group_count)%(int)e->group_count;selected_row=0;request_assets();}
void draw(void*){
    sync_snapshot();sync_assets();auto&io=ImGui::GetIO();DWORD now=GetTickCount();XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD press=pad.Gamepad.wButtons&~previous_buttons;previous_buttons=pad.Gamepad.wButtons;bool active=(LONG)(now-input_after)>=0;
    const ClubCompetitionEntry*input_entry=current();bool knockout_input=input_entry&&(mode==1||(!input_entry->has_group_phase&&!input_entry->table_available));
    if(active&&(ImGui::IsKeyPressed(ImGuiKey_Escape)||(press&XINPUT_GAMEPAD_B))){mod_screen_request_back();return;}
    if(active){int vertical=0,horizontal=0;if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)||(press&XINPUT_GAMEPAD_DPAD_UP))vertical=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)||(press&XINPUT_GAMEPAD_DPAD_DOWN))vertical=1;
        if((LONG)(now-repeat_at)>=0){if(!vertical&&abs(pad.Gamepad.sThumbLY)>16000)vertical=pad.Gamepad.sThumbLY>0?1:-1;
            if(!horizontal&&abs(pad.Gamepad.sThumbLX)>16000)horizontal=pad.Gamepad.sThumbLX>0?1:-1;if(vertical||horizontal)repeat_at=now+190;}
        if(vertical&&focus==3&&knockout_input){auto ties=bracket_navigation_indices(*input_entry);if(!ties.empty()){
                auto it=std::find(ties.begin(),ties.end(),bracket_selected_tie);int at=it==ties.end()?0:(int)(it-ties.begin());at=std::clamp(at+vertical,0,(int)ties.size()-1);bracket_selected_tie=ties[(size_t)at];}}
        else if(vertical&&focus==0&&visible.count)change_competition(vertical);
        else if(vertical&&focus==1)focus=vertical>0?2:0;
        else if(vertical&&focus==2){size_t count=0;visible_rows(current(),&count);if(vertical<0&&selected_row==0)focus=1;else if(count)selected_row=std::clamp(selected_row+vertical,0,(int)count-1);}
        if((ImGui::IsKeyPressed(ImGuiKey_LeftArrow)&&!ImGui::GetIO().KeyShift)||(press&XINPUT_GAMEPAD_DPAD_LEFT))horizontal=-1;
        if((ImGui::IsKeyPressed(ImGuiKey_RightArrow)&&!ImGui::GetIO().KeyShift)||(press&XINPUT_GAMEPAD_DPAD_RIGHT))horizontal=1;
        if(focus==3&&knockout_input&&horizontal)bracket_selected_side=horizontal>0?1:0;
        else if(focus==0&&horizontal)change_competition(horizontal);
        else if(focus==1&&horizontal){auto*e=current();if(e&&e->has_group_phase){mode=mode?0:1;selected_row=0;focus=1;request_assets();}}
        else if(focus==2&&horizontal){auto*e=current();if(e&&mode==0&&e->group_count>1)change_group(horizontal);}
        if(press&XINPUT_GAMEPAD_LEFT_SHOULDER)change_competition(-1);if(press&XINPUT_GAMEPAD_RIGHT_SHOULDER)change_competition(1);
        if(knockout_input&&focus==3){if(press&XINPUT_GAMEPAD_X)bracket_selected_side^=1;
            if(pad.Gamepad.bLeftTrigger>35)knockout_zoom=std::max(.65f,knockout_zoom-io.DeltaTime*.55f);
            if(pad.Gamepad.bRightTrigger>35)knockout_zoom=std::min(1.45f,knockout_zoom+io.DeltaTime*.55f);}
        if(ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space)||(press&XINPUT_GAMEPAD_A)){
            if(focus==0)focus=1;else if(focus==1){auto*e=current();if(knockout_input)focus=3;else focus=e&&mode==0&&(e->has_group_phase||e->table_available)?2:0;}
            else if(focus==3)open_selected_bracket_team();else open_selected_club();}
        if(knockout_input&&focus==3&&ImGui::IsKeyPressed(ImGuiKey_Tab))bracket_selected_side^=1;
    }
    screen_visuals::LightTheme theme;screen_visuals::begin_fullscreen("Competições do meu clube##ClubCompetitions",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.38f);ImGui::TextUnformatted("Competições do meu clube");ImGui::SetWindowFontScale(1);ImGui::SameLine();ImGui::TextDisabled("Temporada atual");ImGui::Separator();
    float content_h=ImGui::GetContentRegionAvail().y-38;float left_w=std::clamp(ImGui::GetContentRegionAvail().x*.24f,250.f,330.f);ImGui::BeginChild("Lista de competições",{left_w,content_h},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("COMPETIÇÕES");ImGui::Separator();
    if(!visible.count)ImGui::TextDisabled("Carregando as competições do clube...");
    for(size_t i=0;i<visible.count&&i<CLUB_COMPETITIONS_CAPACITY;++i){const auto&e=visible.entries[i];ImGui::PushID((int)i);
        bool chosen=selected==(int)i;if(chosen){ImGui::PushStyleColor(ImGuiCol_Button,{.82f,.91f,.96f,1});ImGui::PushStyleColor(ImGuiCol_Text,{.04f,.28f,.43f,1});}
        bool clicked=ImGui::Button("##competition",{-1,62});ImVec2 min=ImGui::GetItemRectMin(),max=ImGui::GetItemRectMax();if(clicked){selected=(int)i;selected_group=e.preferred_group>=0&&e.group_count?std::clamp(e.preferred_group,0,(int)e.group_count-1):0;bracket_selected_tie=0;bracket_selected_side=0;
            mode=e.has_group_phase&&e.current_stage_kind>FCE_STAGE_GROUP?1:0;focus=0;request_assets();}
        auto*dl=ImGui::GetWindowDrawList();if(competition_views[i])dl->AddImage((ImTextureID)(intptr_t)competition_views[i],{min.x+10,min.y+10},{min.x+50,min.y+50});
        auto label=shown&&i<shown->names.size()?shown->names[i]:std::string("Competição");dl->AddText({min.x+60,min.y+11},ImGui::GetColorU32(ImGuiCol_Text),label.c_str());
        const char*sub=e.has_group_phase?"COPA  ·  FASE DE GRUPOS":e.table_available?"LIGA  ·  CLASSIFICAÇÃO":"COPA  ·  MATA-MATA";
        dl->AddText({min.x+60,min.y+34},IM_COL32(103,119,128,255),sub);if(chosen)dl->AddRect({min.x,min.y},{max.x,max.y},IM_COL32(24,111,168,255),4,0,1.8f);
        if(chosen){ImGui::PopStyleColor(2);focus=focus;}
        if(active&&ImGui::IsItemHovered()&&ImGui::IsMouseClicked(0))focus=0;ImGui::PopID();}
    ImGui::EndChild();ImGui::SameLine(0,18);ImGui::BeginChild("Detalhes da competição",{0,content_h},false,ImGuiWindowFlags_NoNavInputs);
    const ClubCompetitionEntry*entry=current();if(entry){std::string name=shown&&selected>=0&&(size_t)selected<shown->names.size()?shown->names[selected]:"Competição";
        if(selected>=0&&(size_t)selected<competition_views.size()&&competition_views[selected])ImGui::Image((ImTextureID)(intptr_t)competition_views[selected],{48,48});
        if(selected>=0&&(size_t)selected<trophy_views.size()&&trophy_views[selected]){ImGui::SameLine(0,5);ImGui::Image((ImTextureID)(intptr_t)trophy_views[selected],{30,42});if(ImGui::IsItemHovered())ImGui::SetTooltip("Troféu desta competição");}
        ImGui::SameLine(0,10);
        ImGui::BeginGroup();ImGui::SetWindowFontScale(1.22f);ImGui::TextWrapped("%s",name.c_str());ImGui::SetWindowFontScale(1);
        const char*phase=entry->has_group_phase&&mode==0?"Fase de grupos":entry->has_group_phase&&mode==1?"Mata-mata":entry->table_available?"Liga":entry->current_stage_kind>FCE_STAGE_GROUP?"Mata-mata":"Competição";
        ImGui::TextDisabled("%s  ·  temporada em andamento",phase);ImGui::EndGroup();ImGui::Separator();
        if(entry->has_group_phase){if(ImGui::Button("Fase de grupos",{142,34})){mode=0;focus=1;}
            ImGui::SameLine();if(ImGui::Button("Mata-mata",{120,34})){mode=1;focus=1;}}
        if(entry->has_group_phase&&mode==0&&entry->group_count){int gi=selected_stage_index(entry);const auto&group=entry->groups[gi];
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()+8);ImGui::BeginGroup();if(ImGui::Button("<",{38,35}))change_group(-1);ImGui::SameLine();
            char group_label[64];sprintf_s(group_label,sizeof(group_label),"GRUPO %c",'A'+(gi%26));ImGui::Text("%s",group_label);ImGui::SameLine();
            if(group.current)ImGui::TextColored({.04f,.43f,.71f,1},"Grupo atual do clube");else ImGui::TextDisabled("%d de %u",gi+1,(unsigned)entry->group_count);
            ImGui::SameLine();if(ImGui::Button(">",{38,35}))change_group(1);ImGui::EndGroup();ImGui::Spacing();draw_table(*entry);
        }else if(entry->has_group_phase&&mode==1)draw_knockout(*entry,pad,active);
        else if(entry->table_available)draw_table(*entry);
        else draw_knockout(*entry,pad,active);
    }else ImGui::TextDisabled("Esta carreira ainda não publicou competições para o clube selecionado.");
    ImGui::EndChild();ImGui::SetCursorScreenPos({io.DisplaySize.x*.035f,io.DisplaySize.y*.93f-27});
    if(ImGui::Button("Voltar  (B / Esc)",{160,30}))mod_screen_request_back();ImGui::SameLine(0,18);
    if(knockout_input)ImGui::TextDisabled("D-pad / analógico esquerdo: confronto e clube  ·  X: alternar clube  ·  A: abrir clube  ·  analógico direito: mover  ·  LT/RT: zoom  ·  B/Esc: voltar");
    else ImGui::TextDisabled("Esquerda/direita: competições, fase ou grupos  ·  cima/baixo: tabela  ·  LB/RB: competições  ·  A: avançar / abrir clube  ·  B/Esc: voltar");ImGui::End();
}
void opened(void*){previous_buttons=0;input_after=GetTickCount()+320;selected=0;selected_group=0;focus=0;mode=0;bracket_selected_tie=0;bracket_selected_side=0;knockout_zoom=.68f;shown_revision=~0u;clubs_browser_request_native_refresh();request_assets();}
void closed(void*){std::lock_guard<std::mutex>lock(guard);++serial;ready.reset();release_views();}
BOOL back(void*){return FALSE;}
}
extern "C" void club_competitions_publish(const ClubCompetitionsSnapshot*data){std::lock_guard<std::mutex>lock(guard);published={};
    if(data&&data->club>0&&data->count<=CLUB_COMPETITIONS_CAPACITY){published=*data;published.count=std::min(data->count,(size_t)CLUB_COMPETITIONS_CAPACITY);
        for(size_t i=0;i<published.count;++i){auto&e=published.entries[i];if(e.table_count>CLUB_COMPETITION_TABLE_CAPACITY)e.table_count=CLUB_COMPETITION_TABLE_CAPACITY;
            if(e.group_count>CLUB_COMPETITION_GROUP_CAPACITY)e.group_count=CLUB_COMPETITION_GROUP_CAPACITY;
            if(e.bracket_tie_count>CLUB_COMPETITION_BRACKET_TIE_CAPACITY)e.bracket_tie_count=CLUB_COMPETITION_BRACKET_TIE_CAPACITY;
            if(e.bracket_team_count>CLUB_COMPETITION_BRACKET_TEAM_CAPACITY)e.bracket_team_count=CLUB_COMPETITION_BRACKET_TEAM_CAPACITY;
            e.title_key[sizeof(e.title_key)-1]=0;for(size_t g=0;g<e.group_count;++g){auto&group=e.groups[g];if(group.row_count>CLUB_COMPETITION_TABLE_CAPACITY)group.row_count=CLUB_COMPETITION_TABLE_CAPACITY;
                for(size_t r=0;r<group.row_count;++r)group.rows[r].name[sizeof(group.rows[r].name)-1]=0;}
            for(size_t r=0;r<e.table_count;++r)e.table[r].name[sizeof(e.table[r].name)-1]=0;
            for(size_t t=0;t<e.bracket_tie_count;++t){auto&tie=e.bracket_ties[t];if(tie.leg_count>2)tie.leg_count=2;}
            for(size_t t=0;t<e.bracket_team_count;++t)e.bracket_teams[t].name[sizeof(e.bracket_teams[t].name)-1]=0;}}
    ++revision;}
extern "C" size_t club_competitions_table_read(int club,int competition,ClubCompetitionTableRow*out,size_t capacity){
    if(!out||!capacity)return 0;std::lock_guard<std::mutex>lock(guard);if(published.club!=club)return 0;
    for(size_t i=0;i<published.count;++i){const auto&e=published.entries[i];if(e.competition!=competition)continue;const ClubCompetitionTableRow*rows=e.table;size_t count=e.table_count;
        if(e.has_group_phase&&e.group_count){size_t g=e.preferred_group>=0&&(size_t)e.preferred_group<e.group_count?(size_t)e.preferred_group:0;rows=e.groups[g].rows;count=e.groups[g].row_count;}
        count=std::min(count,capacity);std::copy(rows,rows+count,out);return count;}return 0;
}
extern "C" int club_competitions_social_read(int club,ClubCompetitionSocialSnapshot*out){
    if(!out)return 0;*out={};std::lock_guard<std::mutex>lock(guard);
    if(club<=0||published.club!=club)return 0;out->club=published.club;out->date=published.date;
    int cup_score=-1;for(size_t i=0;i<published.count;++i){const auto&e=published.entries[i];if(!e.has_group_phase||e.current_stage_kind<=FCE_STAGE_GROUP)continue;
        for(size_t g=0;g<e.group_count;++g){const auto&group=e.groups[g];if(group.classification_count<=0)continue;
            for(size_t r=0;r<group.row_count;++r)if(group.rows[r].team==club){int score=e.current_stage_kind*1000+group.rows[r].played;
                if(score>cup_score){cup_score=score;out->cup_competition=e.competition;out->cup_state=group.rows[r].rank<=group.classification_count?1:-1;}}}}
    const ClubCompetitionTableRow*best=nullptr;const ClubCompetitionEntry*best_entry=nullptr;int best_group=0,league_candidate=0;
    for(size_t i=0;i<published.count;++i){const auto&e=published.entries[i];
        if(e.table_available&&!e.is_cup){for(size_t r=0;r<e.table_count;++r)if(e.table[r].team==club){
            if(!best_entry||e.table[r].played>best->played){best=&e.table[r];best_entry=&e;best_group=0;}league_candidate=1;break;}}
    }
    if(!league_candidate){for(size_t i=0;i<published.count;++i){const auto&e=published.entries[i];if(!e.has_group_phase)continue;
        int gi=e.preferred_group>=0&&e.preferred_group<(int)e.group_count?e.preferred_group:0;
        for(size_t g=0;g<e.group_count;++g)for(size_t r=0;r<e.groups[g].row_count;++r)if(e.groups[g].rows[r].team==club){
            int played=e.groups[g].rows[r].played;if(!best_entry||played>best->played){best=&e.groups[g].rows[r];best_entry=&e;best_group=(int)g;}if((int)g==gi)league_candidate=1;}
    }}
    if(!best||!best_entry)return out->cup_state!=0;out->available=1;out->club=club;out->date=published.date;out->competition=best_entry->competition;out->rank=best->rank;
    out->played=best->played;out->won=best->won;out->drawn=best->drawn;out->lost=best->lost;out->goals_for=best->goals_for;out->goals_against=best->goals_against;out->points=best->points;
    if(best_group>=0&&best_entry->has_group_phase){out->is_group=1;out->team_count=(int)best_entry->groups[best_group].row_count;memcpy(out->form,best->form,sizeof(out->form));}
    else{out->team_count=(int)best_entry->table_count;memcpy(out->form,best->form,sizeof(out->form));}return 1;
}
bool club_competitions_screen_register(const char*root,void(*log)(const char*)){game_root=root?root:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE thread=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"club-competitions",FIFA16_CLUB_COMPETITIONS_ACTION,opened,draw,closed,nullptr,back};return mod_screen_register(&screen)!=FALSE;}
void club_competitions_screen_device(ID3D11Device*d){if(d==device)return;release_views();if(device)device->Release();device=d;if(d)d->AddRef();}
void club_competitions_screen_draw_office(float x,float y,float width,float height,
    int next_match_asset,int horizontal,int vertical,bool confirm,bool input_ready){
    static int preferred_asset=0,preferred_club=0;
    sync_snapshot();
    if(preferred_asset!=next_match_asset||preferred_club!=visible.club){
        preferred_asset=next_match_asset;preferred_club=visible.club;
        if(preferred_asset>0)for(size_t i=0;i<visible.count&&i<CLUB_COMPETITIONS_CAPACITY;++i){
            const auto&e=visible.entries[i];if(e.asset!=preferred_asset&&e.competition!=preferred_asset)continue;
            selected=(int)i;selected_group=e.preferred_group>=0&&e.group_count?
                std::clamp(e.preferred_group,0,(int)e.group_count-1):0;
            mode=e.has_group_phase&&e.current_stage_kind>FCE_STAGE_GROUP?1:0;
            selected_row=bracket_selected_tie=bracket_selected_side=0;focus=0;request_assets();break;
        }
    }
    sync_assets();
    const ClubCompetitionEntry*entry=current();
    bool knockout=entry&&(mode==1||(!entry->has_group_phase&&!entry->table_available));
    if(input_ready&&entry){
        if(vertical&&focus==3&&knockout){auto ties=bracket_navigation_indices(*entry);if(!ties.empty()){
                auto it=std::find(ties.begin(),ties.end(),bracket_selected_tie);int at=it==ties.end()?0:(int)(it-ties.begin());
                at=std::clamp(at+vertical,0,(int)ties.size()-1);bracket_selected_tie=ties[(size_t)at];}}
        else if(vertical&&focus==0&&visible.count)change_competition(vertical);
        else if(vertical&&focus==1)focus=vertical>0?2:0;
        else if(vertical&&focus==2){size_t count=0;visible_rows(current(),&count);
            if(vertical<0&&selected_row==0)focus=1;else if(count)selected_row=std::clamp(selected_row+vertical,0,(int)count-1);}
        if(horizontal&&focus==3&&knockout)bracket_selected_side=horizontal>0?1:0;
        else if(horizontal&&focus==0)change_competition(horizontal);
        else if(horizontal&&focus==1){auto*e=current();if(e&&e->has_group_phase){mode=mode?0:1;selected_row=0;request_assets();}}
        else if(horizontal&&focus==2){auto*e=current();if(e&&mode==0&&e->group_count>1)change_group(horizontal);}
        if(confirm){if(focus==0)focus=1;
            else if(focus==1){auto*e=current();focus=knockout?3:e&&mode==0&&(e->has_group_phase||e->table_available)?2:0;}
            else if(focus==3)open_selected_bracket_team();else if(focus==2)open_selected_club();}
    }

    screen_visuals::LightTheme theme;
    ImGui::SetCursorScreenPos({x,y});
    ImGui::BeginChild("Competições do escritório##OfficeCompetitions",{width,height},false,
        ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    ImGui::SetWindowFontScale(1.28f);ImGui::TextUnformatted("Competições da temporada");ImGui::SetWindowFontScale(1);
    ImGui::SameLine();ImGui::TextDisabled("Classificação, grupos e mata-mata");ImGui::Separator();
    float content_h=std::max(80.f,ImGui::GetContentRegionAvail().y-2.f);
    float left_w=std::clamp(ImGui::GetContentRegionAvail().x*.25f,240.f,340.f);
    ImGui::BeginChild("Competições disponíveis##OfficeList",{left_w,content_h},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::TextUnformatted("COMPETIÇÕES DO CLUBE");ImGui::Separator();
    if(!visible.count)ImGui::TextDisabled("Carregando competições da carreira...");
    for(size_t i=0;i<visible.count&&i<CLUB_COMPETITIONS_CAPACITY;++i){const auto&e=visible.entries[i];ImGui::PushID((int)i);
        bool chosen=selected==(int)i;ImVec2 min,max;
        if(chosen){ImGui::PushStyleColor(ImGuiCol_Button,{.84f,.92f,.97f,1});ImGui::PushStyleColor(ImGuiCol_Text,{.04f,.28f,.43f,1});}
        bool clicked=ImGui::Button("##competition-office",{-1,64});min=ImGui::GetItemRectMin();max=ImGui::GetItemRectMax();
        if(chosen)ImGui::PopStyleColor(2);
        if(clicked){selected=(int)i;selected_group=e.preferred_group>=0&&e.group_count?
                std::clamp(e.preferred_group,0,(int)e.group_count-1):0;
            selected_row=bracket_selected_tie=bracket_selected_side=0;
            mode=e.has_group_phase&&e.current_stage_kind>FCE_STAGE_GROUP?1:0;focus=0;request_assets();}
        auto*dl=ImGui::GetWindowDrawList();if(i<competition_views.size()&&competition_views[i])
            dl->AddImage((ImTextureID)(intptr_t)competition_views[i],{min.x+10,min.y+10},{min.x+50,min.y+50});
        std::string label=shown&&i<shown->names.size()?shown->names[i]:std::string("Competição");
        dl->AddText({min.x+60,min.y+10},ImGui::GetColorU32(chosen?ImGuiCol_Text:ImGuiCol_Text),label.c_str());
        const char*sub=e.has_group_phase?"COPA  ·  FASE DE GRUPOS":e.table_available?"LIGA  ·  CLASSIFICAÇÃO":"COPA  ·  MATA-MATA";
        dl->AddText({min.x+60,min.y+34},IM_COL32(103,119,128,255),sub);
        if(next_match_asset>0&&e.asset==next_match_asset)dl->AddText({min.x+60,min.y+49},IM_COL32(12,103,163,255),"PRÓXIMA PARTIDA");
        if(chosen)dl->AddRect({min.x,min.y},{max.x,max.y},IM_COL32(24,111,168,255),4,0,1.8f);
        if(input_ready&&ImGui::IsItemHovered())focus=0;ImGui::PopID();
    }
    ImGui::EndChild();ImGui::SameLine(0,16);
    ImGui::BeginChild("Detalhes da competição##OfficeDetail",{0,content_h},false,ImGuiWindowFlags_NoNavInputs);
    entry=current();
    if(entry){
        std::string name=shown&&selected>=0&&(size_t)selected<shown->names.size()?shown->names[selected]:"Competição";
        if(selected>=0&&(size_t)selected<competition_views.size()&&competition_views[selected])
            ImGui::Image((ImTextureID)(intptr_t)competition_views[selected],{44,44});
        if(selected>=0&&(size_t)selected<trophy_views.size()&&trophy_views[selected]){
            ImGui::SameLine(0,5);ImGui::Image((ImTextureID)(intptr_t)trophy_views[selected],{30,42});}
        ImGui::SameLine(0,10);ImGui::BeginGroup();ImGui::SetWindowFontScale(1.18f);ImGui::TextWrapped("%s",name.c_str());ImGui::SetWindowFontScale(1);
        const char*phase=entry->has_group_phase&&mode==0?"Fase de grupos":entry->has_group_phase&&mode==1?"Mata-mata":entry->table_available?"Liga · classificação":entry->current_stage_kind>FCE_STAGE_GROUP?"Mata-mata":"Competição";
        ImGui::TextDisabled("%s  ·  temporada atual",phase);ImGui::EndGroup();ImGui::Separator();
        if(entry->has_group_phase){if(ImGui::Button("Fase de grupos",{142,32})){mode=0;focus=1;selected_row=0;request_assets();}
            ImGui::SameLine();if(ImGui::Button("Mata-mata",{120,32})){mode=1;focus=1;selected_row=0;request_assets();}}
        if(entry->has_group_phase&&mode==0&&entry->group_count){int gi=selected_stage_index(entry);const auto&group=entry->groups[gi];
            ImGui::SetCursorPosY(ImGui::GetCursorPosY()+5);if(ImGui::Button("<",{34,30})){change_group(-1);focus=1;}ImGui::SameLine();
            char group_label[64];sprintf_s(group_label,sizeof(group_label),"GRUPO %c",'A'+(gi%26));ImGui::TextUnformatted(group_label);ImGui::SameLine();
            if(group.current)ImGui::TextColored({.04f,.43f,.71f,1},"Grupo atual do clube");else ImGui::TextDisabled("%d de %u",gi+1,(unsigned)entry->group_count);
            ImGui::SameLine();if(ImGui::Button(">",{34,30})){change_group(1);focus=1;}ImGui::Spacing();draw_table(*entry);
        }else if(entry->has_group_phase&&mode==1){XINPUT_STATE no_pad={};draw_knockout(*entry,no_pad,input_ready);}
        else if(entry->table_available)draw_table(*entry);
        else {XINPUT_STATE no_pad={};draw_knockout(*entry,no_pad,input_ready);}
    }else ImGui::TextDisabled("Esta carreira ainda não publicou competições para o clube.");
    ImGui::EndChild();ImGui::EndChild();
}
