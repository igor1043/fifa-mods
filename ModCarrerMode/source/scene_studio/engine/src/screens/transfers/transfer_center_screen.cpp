#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "transfer_center_screen.h"
#include "../operations/career_operations.h"
#include "../club/club_player_screen.h"
#include "../../render/assets/fifa_player_assets.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../clubs/clubs_browser.h"
#include "../../render/renderer/fifa_player_card.h"
#include "../../ui/common/native_loc_names.h"
#include "../../ui/common/screen_visuals.h"
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <cmath>
#include <memory>
#include <mutex>
#include <string>
#include <unordered_map>
#include <vector>
#include <cstdio>

namespace {
constexpr size_t market_roster_limit=6;
struct RosterSnapshot {unsigned serial=0;int club=0;unsigned color=0;bool color_valid=false;std::string name;std::vector<ClubPlayerRow>rows;};
struct LeagueSourceRow {int league=0;std::string name;};
struct LeagueSource {unsigned serial=0;int club=0;std::vector<LeagueSourceRow>rows;};
struct LeagueView {int league=0;std::string name;ID3D11ShaderResourceView*texture=nullptr;};
struct ArtBatch {unsigned serial=0;int club=0;unsigned color=0;bool color_valid=false;std::string name;fifa_player::Texture crest;std::vector<ClubPlayerRow>rows;
    std::vector<fifa_player::Texture>portraits;int league_club=0;std::vector<LeagueView>leagues;std::vector<fifa_player::Texture>league_icons;};
struct PortraitView {ClubPlayerRow row={};ID3D11ShaderResourceView*texture=nullptr;};
std::mutex art_lock;
std::string game_root;
RosterSnapshot roster;
LeagueSource league_source;
std::shared_ptr<const ArtBatch>art_ready,art_shown;
HANDLE art_event=nullptr;
unsigned next_serial=0;
ID3D11Device*device=nullptr;
ID3D11ShaderResourceView*club_crest=nullptr;
std::vector<PortraitView>portrait_views;
std::vector<LeagueView>league_views;
int selected_league_competition=0,selected_league_index=0;
bool scroll_league_selection=true;
WORD previous_buttons=0;

bool leap_year(int year){return year%4==0&&(year%100!=0||year%400==0);}
int month_days(int year,int month){static const int days[]={0,31,28,31,30,31,30,31,31,30,31,30,31};
    return month<1||month>12?0:days[month]+(month==2&&leap_year(year));}
bool valid_date(uint32_t date){int year=(int)(date/10000),month=(int)(date/100%100),day=(int)(date%100);
    return year>=2008&&year<=2100&&month>=1&&month<=12&&day>=1&&day<=month_days(year,month);}
uint32_t next_day(uint32_t date){int year=(int)(date/10000),month=(int)(date/100%100),day=(int)(date%100);
    if(++day>month_days(year,month)){day=1;if(++month>12){month=1;++year;}}return (uint32_t)(year*10000+month*100+day);}
int days_to_close(uint32_t date,uint32_t mmdd){if(!valid_date(date)||mmdd<101||mmdd>1231)return -1;
    for(int i=0;i<=1465;++i){if(date%10000==mmdd)return i;date=next_day(date);}return -1;}
std::string date_text(uint32_t value){char text[24];sprintf_s(text,"%02u/%02u/%04u",value%100,value/100%100,value/10000);return text;}
std::string close_text(uint32_t date,uint32_t mmdd){int days=days_to_close(date,mmdd);if(days<0)return "Não registrada";
    while(days--)date=next_day(date);return date_text(date);}
std::string money(uint32_t value){std::string out=std::to_string(value);for(int i=(int)out.size()-3;i>0;i-=3)out.insert((size_t)i,".");return out;}
CareerTransferUiContext context(){CareerTransferUiContext value={};career_operations_get_transfer_context(&value);return value;}
std::string utf8(const char*text){if(!text)return {};if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,text,-1,nullptr,0))return text;
    int n=MultiByteToWideChar(CP_ACP,0,text,-1,nullptr,0);if(!n)return {};std::vector<wchar_t>w((size_t)n);MultiByteToWideChar(CP_ACP,0,text,-1,w.data(),n);
    int m=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);if(!m)return {};std::string result((size_t)m,'\0');
    WideCharToMultiByte(CP_UTF8,0,w.data(),-1,result.data(),m,nullptr,nullptr);result.pop_back();return result;}
void open(void*){previous_buttons=0;}
void open_leagues(void*){open(nullptr);scroll_league_selection=true;
#ifndef CLUB_PLAYER_SCREEN_TEST
    clubs_browser_request_catalog();
#endif
}
DWORD WINAPI art_worker(void*){fifa_player::Assets assets(game_root);
    native_loc::Names names(game_root);
    for(;;){if(WaitForSingleObject(art_event,INFINITE)!=WAIT_OBJECT_0)return 0;RosterSnapshot source;LeagueSource league_data;
        {std::lock_guard<std::mutex>lock(art_lock);source=roster;league_data=league_source;}
        auto batch=std::make_shared<ArtBatch>();batch->serial=source.serial;batch->club=source.club;batch->color=source.color;batch->color_valid=source.color_valid;batch->name=source.name;
        batch->league_club=league_data.club;
        if(source.club>0)assets.crest(source.club,batch->crest);
        for(const auto&row:source.rows){if(batch->rows.size()>=market_roster_limit)break;
            if(row.squad_position>=28)continue;fifa_player::Texture texture;
            if(!assets.portrait(row.player_id,texture))continue;batch->rows.push_back(row);batch->portraits.push_back(std::move(texture));}
        for(const auto&row:league_data.rows){LeagueView view;view.league=row.league;
            view.name=names.league(row.league);if(view.name.empty())view.name=row.name.empty()?"Liga":row.name;
            fifa_player::Texture icon;if(row.league>0)assets.competition_icon(row.league,icon);
            batch->leagues.push_back(std::move(view));batch->league_icons.push_back(std::move(icon));}
        std::lock_guard<std::mutex>lock(art_lock);if(batch->serial==roster.serial)art_ready=std::move(batch);
    }
}
void sync_art(){std::shared_ptr<const ArtBatch>batch;{std::lock_guard<std::mutex>lock(art_lock);batch=art_ready;}
    if(!batch||batch==art_shown)return;screen_visuals::release(club_crest);for(auto&v:portrait_views)screen_visuals::release(v.texture);portrait_views.clear();
    art_shown=batch;club_crest=screen_visuals::upload(device,batch->crest);
    for(size_t i=0;i<batch->rows.size()&&i<batch->portraits.size();++i){PortraitView view;view.row=batch->rows[i];view.texture=screen_visuals::upload(device,batch->portraits[i]);portrait_views.push_back(view);}
    for(auto&view:league_views)screen_visuals::release(view.texture);league_views.clear();
    for(size_t i=0;i<batch->leagues.size()&&i<batch->league_icons.size();++i){LeagueView view=batch->leagues[i];view.texture=screen_visuals::upload(device,batch->league_icons[i]);league_views.push_back(std::move(view));}
    scroll_league_selection=true;
}
ImU32 color_u32(unsigned rgb,int alpha=255){return IM_COL32((rgb>>16)&255,(rgb>>8)&255,rgb&255,alpha);}
unsigned primary_color(){if(art_shown&&art_shown->club==context().club&&art_shown->color_valid)return art_shown->color&0xffffff;return 0x09549a;}
float linear_channel(float x){return x<=.04045f?x/12.92f:powf((x+.055f)/1.055f,2.4f);}
bool use_dark_text(unsigned c){float r=linear_channel(((c>>16)&255)/255.f),g=linear_channel(((c>>8)&255)/255.f),b=linear_channel((c&255)/255.f);
    float lum=.2126f*r+.7152f*g+.0722f*b;return (lum+.05f)/.05f >= 1.05f/(lum+.05f);}
ImU32 theme_ink(unsigned c){return use_dark_text(c)?IM_COL32(25,35,43,255):IM_COL32(255,255,255,255);}
ImU32 blend(unsigned c,float amount,unsigned tint=0xffffff){int r=(int)((c>>16)&255),g=(int)((c>>8)&255),b=(int)(c&255);
    int tr=(int)((tint>>16)&255),tg=(int)((tint>>8)&255),tb=(int)(tint&255);
    return IM_COL32((int)(r+(tr-r)*amount),(int)(g+(tg-g)*amount),(int)(b+(tb-b)*amount),255);}
void text_fit(ImDrawList*d,ImVec2 pos,const char*text,ImU32 color,float max_width,float font_size=0){
    if(!text||!*text)return;ImFont*font=ImGui::GetFont();if(font_size<=0)font_size=ImGui::GetFontSize();std::string value=text;
    if(font->CalcTextSizeA(font_size,max_width,0,value.c_str()).x>max_width){while(value.size()>3&&font->CalcTextSizeA(font_size,max_width,0,(value+"…").c_str()).x>max_width)value.pop_back();value+="…";}
    d->AddText(font,font_size,pos,color,value.c_str());
}
void section_heading(ImDrawList*d,float x,float y,const char*title,const char*tag,float width,unsigned accent){
    d->AddText({x,y},IM_COL32(39,55,65,255),title);if(tag&&*tag){ImVec2 size=ImGui::CalcTextSize(tag);float bx=x+width-size.x-18;
        d->AddRectFilled({bx,y-3},{bx+size.x+18,y+size.y+5},blend(accent,.88f),8);d->AddText({bx+9,y-1},IM_COL32(74,86,91,255),tag);}}
void empty_moves(ImDrawList*d,float x,float y,float w,float h,unsigned accent){
    d->AddRectFilled({x,y},{x+w,y+h},IM_COL32(255,255,255,255),12);d->AddRect({x,y},{x+w,y+h},IM_COL32(212,220,223,255),12,0,1.f);
    const float cy=y+h*.52f;const float cx=x+w*.23f;float emblem=std::min(58.f,h*.43f);
    d->AddCircleFilled({cx,cy},emblem*.55f,blend(accent,.84f));
    if(club_crest)d->AddImage((ImTextureID)(intptr_t)club_crest,{cx-emblem*.40f,cy-emblem*.40f},{cx+emblem*.40f,cy+emblem*.40f});
    else {d->AddCircle({cx,cy},emblem*.4f,IM_COL32(255,255,255,220),0,2.f);d->AddLine({cx-emblem*.2f,cy},{cx+emblem*.2f,cy},IM_COL32(255,255,255,220),2.f);}
    float sx=x+w*.38f,ey=cy;d->AddCircle({sx,ey},10.f,IM_COL32(181,192,197,255),0,2.f);d->AddLine({sx+16,ey},{sx+w*.2f,ey},blend(accent,.12f),3.f);
    d->AddTriangleFilled({sx+w*.2f,ey},{sx+w*.2f-10,ey-7},{sx+w*.2f-10,ey+7},blend(accent,.12f));
    float tx=x+w*.63f;d->AddText({tx,y+h*.28f},IM_COL32(40,56,67,255),"Histórico não disponível");
    const char*detail="Esta carreira ainda não fornece os negócios da janela. Jogadores, clubes e taxas só aparecem quando houver registros verificáveis.";
    d->PushClipRect({tx,y+h*.45f},{x+w-16,y+h-8},true);d->AddText(ImGui::GetFont(),ImGui::GetFontSize()*.94f,{tx,y+h*.45f},IM_COL32(105,119,126,255),detail,nullptr,w*.34f);d->PopClipRect();
}
void draw_roster(ImDrawList*d,float x,float y,float width,float height,unsigned accent){
    d->AddText({x,y},IM_COL32(39,55,65,255),"ELENCO ATUAL");const char*note="Fotos reais do plantel · apenas referência visual, não são transferências";
    float title_width=ImGui::CalcTextSize("ELENCO ATUAL").x;d->AddText({x+title_width+12,y+1},IM_COL32(111,124,130,255),note);
    float top=y+27, gap=8, count=(float)std::max<size_t>(1,portrait_views.size());float cell=std::min(210.f,(width-gap*(count-1))/count);
    if(portrait_views.empty()){d->AddRectFilled({x,top},{x+width,top+height-30},IM_COL32(255,255,255,255),10);
        d->AddText({x+18,top+16},IM_COL32(105,119,126,255),"As fotos do elenco aparecem quando o plantel da carreira estiver carregado.");return;}
    for(size_t i=0;i<portrait_views.size();++i){const auto&view=portrait_views[i];float at=x+i*(cell+gap);float bottom=top+height-30;
        d->AddRectFilled({at,top},{at+cell,bottom},IM_COL32(255,255,255,255),9);d->AddRect({at,top},{at+cell,bottom},IM_COL32(215,222,224,255),9,0,1.f);
        float photo_w=cell*.42f,photo_h=bottom-top-14;
        d->AddRectFilled({at+7,top+7},{at+7+photo_w,top+7+photo_h},blend(accent,.87f),6);
        if(view.texture)d->AddImage((ImTextureID)(intptr_t)view.texture,{at+8,top+8},{at+7+photo_w,top+7+photo_h});
        else {float px=at+7+photo_w*.5f,py=top+photo_h*.4f;d->AddCircleFilled({px,py},photo_w*.17f,IM_COL32(178,190,195,255));d->AddEllipseFilled({px,py+photo_w*.40f},{photo_w*.28f,photo_h*.26f},IM_COL32(178,190,195,255));}
        float tx=at+photo_w+14,tw=cell-photo_w-21;char overall[16];if(view.row.overall>0)sprintf_s(overall,"%d OVR",view.row.overall);else strcpy_s(overall,"N/D");
        d->AddText({tx,top+12},blend(accent,.04f),overall);d->PushClipRect({tx,top+34},{at+cell-7,bottom-4},true);
        text_fit(d,{tx,top+36},utf8(view.row.name).c_str(),IM_COL32(47,61,69,255),tw,ImGui::GetFontSize()*.9f);
        char shirt[32];if(view.row.number>0)sprintf_s(shirt,"CAMISA %d",view.row.number);else strcpy_s(shirt,"ELENCO");
        d->AddText({tx,top+58},IM_COL32(121,133,138,255),shirt);d->PopClipRect();
        if(club_crest)d->AddImage((ImTextureID)(intptr_t)club_crest,{at+cell-24,bottom-27},{at+cell-8,bottom-11});
    }
}
void panel(ImDrawList*d,float x,float y,float w,float h,ImU32 fill=IM_COL32(255,255,255,255)){
    d->AddRectFilled({x,y},{x+w,y+h},fill,10);d->AddRect({x,y},{x+w,y+h},IM_COL32(218,225,229,255),10,0,1.f);
}
void draw_market_header(const CareerTransferUiContext&data,float x,float y,float w,float h,unsigned accent,bool show_leagues=true){
    ImDrawList*d=ImGui::GetWindowDrawList();panel(d,x,y,w,h);
    d->AddRectFilled({x,y},{x+6,y+h},color_u32(accent),3);
    if(club_crest)d->AddImage((ImTextureID)(intptr_t)club_crest,{x+17,y+12},{x+17+h-24,y+h-12});
    else {d->AddCircleFilled({x+17+h*.5f,y+h*.5f},h*.28f,blend(accent,.78f));d->AddLine({x+17+h*.34f,y+h*.5f},{x+17+h*.66f,y+h*.5f},theme_ink(accent),2.f);}
    float tx=x+h+8;d->AddText(nullptr,ImGui::GetFontSize()*1.35f,{tx,y+10},IM_COL32(32,52,65,255),"MERCADO DA BOLA");
    std::string subtitle="Temporada da carreira";if(valid_date(data.date))subtitle+="  ·  "+date_text(data.date);
    d->AddText({tx,y+36},IM_COL32(105,121,130,255),subtitle.c_str());
    if(show_leagues){float button_w=125.f,button_h=34.f,bx=x+w-button_w-16,by=y+(h-button_h)*.5f;
        ImGui::SetCursorScreenPos({bx,by});if(ImGui::Button("Ver ligas  >",{button_w,button_h}))mod_screen_push_action(FIFA_TRANSFER_LEAGUES_ACTION);}
}
void draw_top_transfer_slots(ImDrawList*d,float x,float y,float w,float h,unsigned accent){
    panel(d,x,y,w,h);d->AddText({x+14,y+10},IM_COL32(43,60,70,255),"TRANSFERÊNCIAS MAIS CARAS");
    d->AddText({x+w-116,y+11},blend(accent,.02f),"TOP 5 DA JANELA");
    float top=y+34.f,available_h=h-42.f,gap=7.f;float cw=(w-28.f-gap*4.f)/5.f,ch=std::max(78.f,available_h-5.f);
    for(int i=0;i<5;++i){float cx=x+14.f+i*(cw+gap);fifa_player_card::Data slot;slot.primary_color=accent;slot.overall=-1;slot.position="-";slot.name="Sem dados";
        fifa_player_card::draw(d,{cx,top},{cw,ch},slot,ImTextureID(0),ImTextureID(0));
    }
}
void draw_club_highlight(ImDrawList*d,float x,float y,float w,float h,unsigned accent,bool sellers){
    panel(d,x,y,w,h);unsigned color=sellers?0x39a978:0x188bc2;ImU32 icon=color_u32(color);
    ImVec2 center={x+34.f,y+h*.5f};d->AddCircleFilled(center,21.f,blend(accent,.85f));
    if(sellers){d->AddLine({center.x-8,center.y+5},{center.x+7,center.y-7},icon,3.f);d->AddTriangleFilled({center.x+8,center.y-8},{center.x+1,center.y-8},{center.x+8,center.y-1},icon);}
    else {d->AddLine({center.x-8,center.y-5},{center.x+7,center.y+7},icon,3.f);d->AddTriangleFilled({center.x+8,center.y+8},{center.x+1,center.y+8},{center.x+8,center.y+1},icon);}
    float tx=x+67.f;d->AddText({tx,y+10},IM_COL32(75,91,100,255),sellers?"TIMES QUE MAIS VENDERAM":"TIMES QUE MAIS COMPRARAM");
    d->AddText(nullptr,ImGui::GetFontSize()*1.18f,{tx,y+31},IM_COL32(44,62,71,255),sellers?"N/D arrecadado  ·  N/D lucro":"N/D gasto  ·  N/D negócios");
    d->AddText({tx,y+h-22},IM_COL32(118,130,136,255),"Sem histórico de janela no save");
}
void draw_recent_transfers(ImDrawList*d,float x,float y,float w,float h,unsigned accent){
    panel(d,x,y,w,h);d->AddText({x+15,y+11},IM_COL32(43,60,70,255),"ÚLTIMAS TRANSFERÊNCIAS");
    d->AddText({x+w-122,y+11},IM_COL32(112,126,133,255),"ATÉ 10 NEGÓCIOS");
    float mid=x+w*.5f,cy=y+h*.55f;ImU32 soft=blend(accent,.83f);d->AddCircleFilled({mid,cy-18},27.f,soft);
    d->AddCircle({mid-9,cy-18},7.f,blend(accent,.02f),0,2.f);d->AddCircle({mid+9,cy-18},7.f,blend(accent,.02f),0,2.f);
    d->AddLine({mid-2,cy-18},{mid+2,cy-18},blend(accent,.02f),2.f);
    d->AddLine({mid-14,cy+1},{mid-2,cy+1},blend(accent,.02f),2.f);d->AddLine({mid+2,cy+1},{mid+14,cy+1},blend(accent,.02f),2.f);
    const char*title="Ainda não há negócios confirmados para exibir";ImVec2 ts=ImGui::CalcTextSize(title);d->AddText({mid-ts.x*.5f,cy+18},IM_COL32(51,68,77,255),title);
    const char*note="Quando o save disponibilizar o histórico, cada linha mostrará jogador, overall, posição e clubes de origem e destino.";
    ImVec2 ns=ImGui::CalcTextSize(note);if(ns.x>w-36){d->PushClipRect({x+16,cy+42},{x+w-16,cy+64},true);d->AddText({x+18,cy+43},IM_COL32(112,126,133,255),note);d->PopClipRect();}
    else d->AddText({mid-ns.x*.5f,cy+43},IM_COL32(112,126,133,255),note);
}
void draw_market(const CareerTransferUiContext&data,float width,float height,unsigned accent){ImDrawList*d=ImGui::GetWindowDrawList();ImVec2 origin=ImGui::GetCursorScreenPos();float x=origin.x,y=origin.y;
    float gap=11.f,header_h=64.f,top_y=y+header_h+gap,top_h=std::clamp(height*.34f,180.f,230.f);
    draw_market_header(data,x,y,width,header_h,accent);
    float right_w=std::clamp(width*.32f,300.f,420.f),left_w=width-right_w-gap;
    draw_top_transfer_slots(d,x,top_y,left_w,top_h,accent);
    float rx=x+left_w+gap,rh=(top_h-gap)*.5f;
    draw_club_highlight(d,rx,top_y,right_w,rh,accent,true);draw_club_highlight(d,rx,top_y+rh+gap,right_w,rh,accent,false);
    float recent_y=top_y+top_h+gap;draw_recent_transfers(d,x,recent_y,width,std::max(105.f,y+height-recent_y-4.f),accent);
}
void draw_my_transfers(const CareerTransferUiContext&data,float width,float height,unsigned accent){ImDrawList*d=ImGui::GetWindowDrawList();ImVec2 origin=ImGui::GetCursorScreenPos();float x=origin.x,y=origin.y;
    float head=height*.135f;d->AddRectFilled({x,y},{x+width,y+head},color_u32(accent),10);ImU32 ink=theme_ink(accent);
    d->AddText(nullptr,ImGui::GetFontSize()*1.5f,{x+20,y+15},ink,"MINHAS TRANSFERÊNCIAS");
    if(valid_date(data.date)){std::string date="CARREIRA · "+date_text(data.date);d->AddText({x+22,y+head-27},ink,date.c_str());}
    if(club_crest){float size=head*.78f;d->AddImage((ImTextureID)(intptr_t)club_crest,{x+width-size-18,y+(head-size)*.5f},{x+width-18,y+(head+size)*.5f});}
    float row_y=y+head+12,gap=12,w=(width-gap*2)/3.f,h=height*.18f;
    struct Stat{const char*label;std::string value;const char*note;};Stat stats[]={{"VERBA DE TRANSFERÊNCIAS",data.save_valid?money(data.transfer_budget):"N/D","Saldo disponível atual"},
        {"ORÇAMENTO SALARIAL",data.save_valid?money(data.wage_budget):"N/D","Limite salarial, não salário individual"},{"NEGÓCIOS NO HISTÓRICO","N/D","A fonte atual não fornece eventos de compra/venda"}};
    for(int i=0;i<3;++i){float bx=x+i*(w+gap);d->AddRectFilled({bx,row_y},{bx+w,row_y+h},i==0?blend(accent,.84f):IM_COL32(255,255,255,255),10);
        d->AddRect({bx,row_y},{bx+w,row_y+h},i==0?blend(accent,.58f):IM_COL32(215,222,224,255),10);
        d->AddText({bx+14,row_y+13},IM_COL32(105,119,126,255),stats[i].label);d->AddText(nullptr,ImGui::GetFontSize()*1.28f,{bx+14,row_y+39},IM_COL32(37,53,62,255),stats[i].value.c_str());
        d->AddText({bx+14,row_y+h-24},IM_COL32(110,122,128,255),stats[i].note);}
    float list_y=row_y+h+16;section_heading(d,x,list_y,"CONTRATAÇÕES E VENDAS","Registros da sua carreira",width,accent);
    float list_h=height*.31f;empty_moves(d,x,list_y+ImGui::GetFontSize()+10,width,list_h,accent);
    draw_roster(d,x,list_y+ImGui::GetFontSize()+10+list_h+14,width,std::max(60.f,y+height-(list_y+ImGui::GetFontSize()+10+list_h+14)-5),accent);
}
void open_league_detail(){if(selected_league_index<0||(size_t)selected_league_index>=league_views.size())return;
    selected_league_competition=league_views[(size_t)selected_league_index].league;mod_screen_push_action(FIFA_TRANSFER_LEAGUE_DETAIL_ACTION);}
void draw_league_list(const CareerTransferUiContext&data,float width,float height,unsigned accent){ImDrawList*d=ImGui::GetWindowDrawList();ImVec2 origin=ImGui::GetCursorScreenPos();float x=origin.x,y=origin.y;
    draw_market_header(data,x,y,width,64.f,accent,false);d->AddText({x,y+78},IM_COL32(43,60,70,255),"LIGAS DISPONÍVEIS");
    d->AddText({x,y+100},IM_COL32(112,126,133,255),"Selecione uma liga para abrir o mercado e as movimentações correspondentes.");
    float top=y+130.f,gap=12.f,card_h=82.f;int columns=std::min(3,(int)league_views.size());if(columns<1)columns=3;
    float card_w=league_views.empty()?std::min(430.f,width):std::min(430.f,(width-gap*(columns-1))/columns);
    if(!art_shown||art_shown->league_club!=static_cast<int>(data.club)||league_views.empty()){
        panel(d,x,top,width,std::max(128.f,height-134.f));float cx=x+width*.5f,cy=top+std::max(128.f,height-134.f)*.5f;
        d->AddCircleFilled({cx,cy-17},25.f,blend(accent,.83f));d->AddLine({cx-10,cy-17},{cx+10,cy-17},blend(accent,.05f),3.f);
        const char*title=art_shown&&art_shown->league_club==static_cast<int>(data.club)?"Nenhuma liga encontrada no catálogo":"Carregando as ligas disponíveis";
        ImVec2 ts=ImGui::CalcTextSize(title);d->AddText({cx-ts.x*.5f,cy+19},IM_COL32(48,65,74,255),title);
        const char*note="O catálogo completo de clubes e ligas aparecerá aqui com os escudos.";ImVec2 ns=ImGui::CalcTextSize(note);d->AddText({cx-ns.x*.5f,cy+42},IM_COL32(113,127,134,255),note);return;}
    selected_league_index=std::clamp(selected_league_index,0,(int)league_views.size()-1);
    float list_h=std::max(120.f,y+height-top);ImGui::SetCursorScreenPos({x,top});ImGui::PushStyleColor(ImGuiCol_ChildBg,{0,0,0,0});
    ImGui::BeginChild("##transfer-league-catalog",{width,list_h},false,ImGuiWindowFlags_NoNavInputs);
    float child_w=ImGui::GetContentRegionAvail().x;float contents_w=card_w*columns+gap*(columns-1),contents_x=(child_w-contents_w)*.5f;
    if(scroll_league_selection){float selected_row=(float)(selected_league_index/columns);ImGui::SetScrollY(std::max(0.f,selected_row*(card_h+gap)-list_h*.38f));scroll_league_selection=false;}
    for(size_t i=0;i<league_views.size();++i){int col=(int)(i%columns),row=(int)(i/columns);float bx=contents_x+col*(card_w+gap),by=8+row*(card_h+gap);
        ImGui::PushID((int)i);ImGui::SetCursorPos({bx,by});ImGui::InvisibleButton("##transfer-league",{card_w,card_h});ImVec2 a=ImGui::GetItemRectMin(),b=ImGui::GetItemRectMax();
        bool chosen=(int)i==selected_league_index,hover=ImGui::IsItemHovered();if(hover&&ImGui::IsMouseClicked(0)){selected_league_index=(int)i;selected_league_competition=league_views[i].league;mod_screen_push_action(FIFA_TRANSFER_LEAGUE_DETAIL_ACTION);}
        ImU32 fill=chosen?blend(accent,.85f):IM_COL32(255,255,255,255);d->AddRectFilled(a,b,fill,9);d->AddRect(a,b,chosen?blend(accent,.10f):IM_COL32(218,225,229,255),9,0,chosen?2.f:1.f);
        if(league_views[i].texture)d->AddImage((ImTextureID)(intptr_t)league_views[i].texture,{a.x+13,a.y+13},{a.x+56,a.y+56});
        else{d->AddCircleFilled({a.x+34,a.y+34},20.f,blend(accent,.84f));d->AddText({a.x+26,a.y+26},blend(accent,.02f),"L");}
        text_fit(d,{a.x+68,a.y+17},league_views[i].name.c_str(),IM_COL32(43,60,70,255),card_w-82.f,ImGui::GetFontSize());
        const char*kind="LIGA";d->AddText({a.x+68,a.y+43},IM_COL32(111,125,132,255),kind);
        float cy=a.y+card_h*.5f;if(chosen)d->AddTriangleFilled({b.x-17,cy},{b.x-26,cy-7},{b.x-26,cy+7},blend(accent,.04f));ImGui::PopID();
    }
    ImGui::EndChild();ImGui::PopStyleColor();
}
void draw_league_detail(const CareerTransferUiContext&data,float width,float height,unsigned accent){ImDrawList*d=ImGui::GetWindowDrawList();ImVec2 origin=ImGui::GetCursorScreenPos();float x=origin.x,y=origin.y;
    const LeagueView*league=nullptr;if(art_shown&&art_shown->league_club==static_cast<int>(data.club))for(const auto&item:league_views)if(item.league==selected_league_competition){league=&item;break;}
    draw_market_header(data,x,y,width,64.f,accent,false);float head_y=y+77.f;
    panel(d,x,head_y,width,78.f);
    if(league&&league->texture)d->AddImage((ImTextureID)(intptr_t)league->texture,{x+14,head_y+13},{x+62,head_y+61});
    else {d->AddCircleFilled({x+38,head_y+39},23.f,blend(accent,.83f));d->AddText({x+30,head_y+31},blend(accent,.03f),"L");}
    std::string title=league?league->name:"Liga selecionada";d->AddText(nullptr,ImGui::GetFontSize()*1.25f,{x+75,head_y+13},IM_COL32(43,60,70,255),title.c_str());
    d->AddText({x+76,head_y+43},IM_COL32(112,126,133,255),"MERCADO DA LIGA  ·  TEMPORADA ATUAL");
    float stat_y=head_y+91.f,gap=10.f,stat_w=(width-gap*2.f)/3.f,stat_h=70.f;
    const char*labels[]={"CONTRATAÇÕES","VENDAS","VALORES MOVIMENTADOS"};
    for(int i=0;i<3;++i){float sx=x+i*(stat_w+gap);panel(d,sx,stat_y,stat_w,stat_h);d->AddText({sx+14,stat_y+12},IM_COL32(112,126,133,255),labels[i]);
        d->AddText(nullptr,ImGui::GetFontSize()*1.15f,{sx+14,stat_y+36},IM_COL32(46,63,72,255),"N/D");}
    float list_y=stat_y+stat_h+gap;draw_recent_transfers(d,x,list_y,width,std::max(100.f,y+height-list_y-4.f),accent);
}
void draw(void*){screen_visuals::LightTheme theme;sync_art();auto&io=ImGui::GetIO();XINPUT_STATE pad={};
    bool have_pad=mod_xinput_read_raw(0,&pad)==ERROR_SUCCESS;WORD pressed=have_pad?(WORD)(pad.Gamepad.wButtons&~previous_buttons):0;previous_buttons=have_pad?pad.Gamepad.wButtons:0;
    bool league_list=mod_screen_is_active("transfer-leagues"),league_detail=mod_screen_is_active("transfer-league-detail");
    if(ImGui::IsKeyPressed(ImGuiKey_Escape)||(pressed&XINPUT_GAMEPAD_B)){mod_screen_request_back();return;}
    if(league_list&&!league_views.empty()){
        selected_league_index=std::clamp(selected_league_index,0,(int)league_views.size()-1);
        int delta=0;if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(pressed&XINPUT_GAMEPAD_DPAD_LEFT))delta=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(pressed&XINPUT_GAMEPAD_DPAD_RIGHT))delta=1;
        if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)||(pressed&XINPUT_GAMEPAD_DPAD_UP))delta=-3;
        if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)||(pressed&XINPUT_GAMEPAD_DPAD_DOWN))delta=3;
        if(delta){selected_league_index=std::clamp(selected_league_index+delta,0,(int)league_views.size()-1);scroll_league_selection=true;}
        if(ImGui::IsKeyPressed(ImGuiKey_Enter)||(pressed&XINPUT_GAMEPAD_A))open_league_detail();}
    if(!league_list&&!league_detail&&!mod_screen_is_active("my-transfers")&&(pressed&XINPUT_GAMEPAD_Y))mod_screen_push_action(FIFA_TRANSFER_LEAGUES_ACTION);
    ImGui::SetNextWindowPos({0,0},ImGuiCond_Always);ImGui::SetNextWindowSize(io.DisplaySize,ImGuiCond_Always);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,0.f);ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,0.f);ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{24,20});
    ImGui::Begin("Transferências da carreira##TransferCenter",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    bool own=mod_screen_is_active("my-transfers");CareerTransferUiContext data=context();
    if(art_shown&&art_shown->club!=static_cast<int>(data.club)){screen_visuals::release(club_crest);for(auto&view:portrait_views)screen_visuals::release(view.texture);portrait_views.clear();
        for(auto&view:league_views)screen_visuals::release(view.texture);league_views.clear();art_shown.reset();}
    unsigned accent=primary_color();
    float full_width=ImGui::GetContentRegionAvail().x,full_height=ImGui::GetContentRegionAvail().y;float footer=31.f;
    if(own)draw_my_transfers(data,full_width,full_height-footer,accent);
    else if(league_list)draw_league_list(data,full_width,full_height-footer,accent);
    else if(league_detail)draw_league_detail(data,full_width,full_height-footer,accent);
    else draw_market(data,full_width,full_height-footer,accent);
    ImGui::SetCursorPosY(std::max(ImGui::GetCursorPosY(),ImGui::GetWindowHeight()-56));
    if(ImGui::Button("Voltar (B / Esc)"))mod_screen_request_back();ImGui::SameLine();
    if(league_list)ImGui::TextDisabled("Setas: navegar  ·  A / clique: abrir liga  ·  B / Esc: voltar");
    else if(!own&&!league_detail)ImGui::TextDisabled("Y: ligas  ·  Valores e negociações só aparecem com registros confirmados do save.");
    else ImGui::TextDisabled("B / Esc: voltar  ·  Valores indisponíveis são marcados como N/D.");
    ImGui::End();ImGui::PopStyleVar(3);
}
BOOL back(void*){previous_buttons=0;return FALSE;}
}

void transfer_center_screen_publish_roster(const ClubPlayerRow*rows,size_t count,int club,const char*name){CareerTransferUiContext career=context();
    if(club>0&&career.club!=static_cast<uint32_t>(club))return;
    std::lock_guard<std::mutex>lock(art_lock);roster.rows.clear();roster.club=club;roster.name=name?name:"";roster.color=0;roster.color_valid=false;
    if(rows&&count&&club>0)for(size_t i=0;i<std::min(count,size_t(CLUB_PLAYER_CAPACITY));++i){const auto&row=rows[i];if(row.team_id!=club||row.player_id<=0||row.player_id>524287)continue;
        if(!roster.color_valid&&row.club_colors_valid){roster.color=row.club_colors[0];roster.color_valid=true;}
        if(std::none_of(roster.rows.begin(),roster.rows.end(),[&](const ClubPlayerRow&existing){return existing.player_id==row.player_id;}))roster.rows.push_back(row);}
    ++next_serial;roster.serial=next_serial;art_ready.reset();if(art_event)SetEvent(art_event);
}
void transfer_center_screen_publish_league_catalog(const ClubBrowserRow*rows,size_t count,int club){
    std::lock_guard<std::mutex>lock(art_lock);league_source.rows.clear();league_source.club=club>0?club:0;
    std::unordered_map<int,std::string>unique;
    if(rows&&count<=CLUB_BROWSER_CAPACITY)for(size_t i=0;i<count;++i){const auto&row=rows[i];if(row.league<=0||row.league>4096)continue;
        if(!unique.count(row.league))unique.emplace(row.league,row.league_name);}
    for(auto&item:unique)league_source.rows.push_back({item.first,std::move(item.second)});
    std::sort(league_source.rows.begin(),league_source.rows.end(),[](const LeagueSourceRow&a,const LeagueSourceRow&b){
        int name=_stricmp(a.name.c_str(),b.name.c_str());return name?name<0:a.league<b.league;});
    ++next_serial;roster.serial=next_serial;league_source.serial=next_serial;art_ready.reset();if(art_event)SetEvent(art_event);
}
void transfer_center_screen_device(ID3D11Device*next){if(device==next)return;screen_visuals::release(club_crest);for(auto&view:portrait_views)screen_visuals::release(view.texture);portrait_views.clear();
    for(auto&view:league_views)screen_visuals::release(view.texture);league_views.clear();art_shown.reset();device=next;}
bool transfer_center_screen_register(const char*root){game_root=root?root:"";if(!art_event){art_event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!art_event)return false;
        HANDLE worker=CreateThread(nullptr,0,art_worker,nullptr,0,nullptr);if(!worker){CloseHandle(art_event);art_event=nullptr;return false;}CloseHandle(worker);
        std::lock_guard<std::mutex>lock(art_lock);if(roster.serial)SetEvent(art_event);}
    const ModOverlayScreen market={"transfer-market",FIFA_TRANSFER_MARKET_ACTION,open,draw,nullptr,nullptr,back};
    const ModOverlayScreen own={"my-transfers",FIFA_MY_TRANSFERS_ACTION,open,draw,nullptr,nullptr,back};
    const ModOverlayScreen leagues={"transfer-leagues",FIFA_TRANSFER_LEAGUES_ACTION,open_leagues,draw,nullptr,nullptr,back};
    const ModOverlayScreen detail={"transfer-league-detail",FIFA_TRANSFER_LEAGUE_DETAIL_ACTION,open,draw,nullptr,nullptr,back};
    return mod_screen_register(&market)&&mod_screen_register(&own)&&mod_screen_register(&leagues)&&mod_screen_register(&detail);}
