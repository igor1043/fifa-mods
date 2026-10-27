#define NOMINMAX
#include "coach_profile_data.h"
#include "../../platform/mod_paths.h"
#include "../player/player_profile_view.h"
#include "../../ui/common/screen_visuals.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../../ui/common/native_loc_names.h"
#include <mutex>
#include <fstream>
#include <wincodec.h>
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"ole32.lib")
namespace {
struct Snapshot {CoachProfileContext context={};std::vector<CoachCareerRow>rows;};
std::mutex guard;Snapshot career,visible,pending;
std::unordered_map<int,CoachCareerRow>team_stats;
bool external=false,pending_external=false;
bool embedded=false;
unsigned revision=0,shown_revision=~0u,serial=0;
unsigned identity_revision=0;
volatile LONG refresh_requested=0;
std::string root;HANDLE event=nullptr;void(*logger)(const char*)=nullptr;
struct Request {unsigned serial=0;CoachProfileContext context={};std::vector<CoachCareerRow>rows;};
struct Batch {unsigned serial=0;CoachProfileContext context={};fifa_player::Texture crest,photo,flag,league_logo;
    std::string league_name,nationality_name;float league_strength=-1;std::shared_ptr<const fifa_player::Model>model;std::unordered_map<int,fifa_player::Texture>logos;};
Request request;std::shared_ptr<const Batch>ready,shown;
ID3D11Device*device=nullptr;ID3D11ShaderResourceView*crest=nullptr,*photo=nullptr,*flag=nullptr,*league_logo=nullptr;
std::unordered_map<int,ID3D11ShaderResourceView*>team_logos;
fifa_player::Renderer renderer;
int page=0;float yaw=0,zoom=1,pan=0,scroll=0;bool reset_scroll=true;
WORD held=0;DWORD input_after=0,repeat_at=0;
const char*const tabs[]={"Resumo","Desempenho","Clubes","Seleções","Títulos"};
#ifdef COACH_PROFILE_TEST
ImVec2 tab_centers[5]={};
#endif
void clear_views(){screen_visuals::release(crest);screen_visuals::release(photo);screen_visuals::release(flag);screen_visuals::release(league_logo);
    for(auto&entry:team_logos)screen_visuals::release(entry.second);team_logos.clear();renderer.clear();shown.reset();}
bool image_file(const std::string&path,fifa_player::Texture&out){
    int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,path.c_str(),-1,nullptr,0);if(!n)return false;
    std::vector<wchar_t>w(n);MultiByteToWideChar(CP_UTF8,0,path.c_str(),-1,w.data(),n);
    IWICImagingFactory*f=nullptr;IWICBitmapDecoder*d=nullptr;IWICBitmapFrameDecode*frame=nullptr;IWICFormatConverter*c=nullptr;
    HRESULT init=CoInitializeEx(nullptr,COINIT_MULTITHREADED);bool ok=false;
    do{if(FAILED(init)&&init!=RPC_E_CHANGED_MODE)break;
        if(FAILED(CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&f))))break;
        if(FAILED(f->CreateDecoderFromFilename(w.data(),nullptr,GENERIC_READ,WICDecodeMetadataCacheOnLoad,&d))||FAILED(d->GetFrame(0,&frame))||FAILED(f->CreateFormatConverter(&c)))break;
        UINT width=0,height=0;if(FAILED(frame->GetSize(&width,&height))||!width||!height||width>2048||height>2048)break;
        if(FAILED(c->Initialize(frame,GUID_WICPixelFormat32bppRGBA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom)))break;
        fifa_player::Texture t;t.width=width;t.height=height;t.format=3;t.bytes.resize(size_t(width)*height*4);
        if(FAILED(c->CopyPixels(nullptr,width*4,(UINT)t.bytes.size(),t.bytes.data())))break;out=std::move(t);ok=true;
    }while(false);
    if(c)c->Release();if(frame)frame->Release();if(d)d->Release();if(f)f->Release();if(SUCCEEDED(init))CoUninitialize();return ok;
}
bool photo_file(const CoachProfileContext&c,fifa_player::Texture&out){
    std::string key=c.kind==COACH_CAREER_USER?"user_":c.kind==COACH_CLUB_MANAGER?"club_":"national_";key+=std::to_string(c.id);
    for(const char*ext:{".png",".jpg",".jpeg",".dds"}){
        std::string path=root+"/ModCarrerMode/portraits/coaches/"+key+ext;
        if(!strcmp(ext,".dds")){std::ifstream f(path,std::ios::binary|std::ios::ate);auto size=f.tellg();
            if(f&&size>128&&size<32*1024*1024){std::vector<uint8_t>b((size_t)size);f.seekg(0);if(f.read((char*)b.data(),size)&&fifa_player::read_crest_dds(b,out))return true;}}
        else if(image_file(path,out))return true;
    }return false;
}
DWORD WINAPI worker(void*){
    fifa_player::Assets assets(root);thread_local std::unique_ptr<native_loc::Names>names;
    if(!names)names=std::make_unique<native_loc::Names>(root);
    for(;;){if(WaitForSingleObject(event,INFINITE)!=WAIT_OBJECT_0)return 0;Request r;{std::lock_guard<std::mutex>lock(guard);r=request;}
        if(!r.context.valid)continue;auto b=std::make_shared<Batch>();b->serial=r.serial;b->context=r.context;
        try{ClubPlayerRow club={};club.team_id=r.context.club?r.context.club:r.context.national_team;
            club.club_colors_valid=r.context.colors_valid;memcpy(club.club_colors,r.context.colors,sizeof(club.club_colors));
            assets.crest(club.team_id,b->crest);photo_file(r.context,b->photo);
            if(r.context.nationality>0){assets.nationality_flag(r.context.nationality,b->flag);b->nationality_name=names->nation(r.context.nationality);}
            for(const auto&row:r.rows)if(!b->logos.count(row.team)){fifa_player::Texture logo;if(assets.crest(row.team,logo))b->logos.emplace(row.team,std::move(logo));}
            int league=assets.league(r.context.club,b->league_name);assets.competition_icon(league,b->league_logo);
            b->league_strength=assets.league_strength(r.context.club);
            auto coach=assets.coach(club);
            /* The model belongs to the club, while name/history belong to the
             * career profile. Do not discard the club SLC when the career has
             * a custom manager name; keep unsupported native rigs static. */
            if(coach.model&&r.context.club>0&&
                (r.context.kind==COACH_CAREER_USER||r.context.kind==COACH_CLUB_MANAGER)){
                auto model=std::make_shared<fifa_player::Model>(*coach.model);
                if(model->skeleton&&!fifa_player::apply_coach_pose(*model,201))
                    model->diagnostic+="\ncoach profile: fixed native pose unavailable; original club model preserved";
                b->model=model;
            }
        }catch(...){if(logger)logger("CoachProfile: missing native asset; no model substituted");}
        {std::lock_guard<std::mutex>lock(guard);if(r.serial!=serial)continue;ready=b;}
        if(logger)logger(("CoachProfile: identity="+std::to_string(r.context.kind)+":"+std::to_string(r.context.id)+
            " club="+std::to_string(r.context.club)+" native_3d="+std::to_string(bool(b->model))+" photo="+std::to_string(!b->photo.bytes.empty())).c_str());
    }
}
DWORD WINAPI guarded_worker(void*p){try{return worker(p);}catch(...){if(logger)logger("CoachProfile: asset worker stopped safely");return 0;}}
void queue(){clear_views();std::lock_guard<std::mutex>lock(guard);++serial;ready.reset();request={serial,visible.context,visible.rows};if(visible.context.valid)SetEvent(event);}
void change_page(int next){page=(next+5)%5;reset_scroll=true;}
void opened(void*){
    {std::lock_guard<std::mutex>lock(guard);external=pending_external;visible=external?pending:career;pending_external=false;pending={};shown_revision=revision;}
    page=0;yaw=pan=scroll=0;zoom=1;held=0;repeat_at=0;reset_scroll=true;input_after=GetTickCount()+350;
    if(!external)InterlockedExchange(&refresh_requested,1);queue();
}
void closed(void*){clear_views();std::lock_guard<std::mutex>lock(guard);++serial;ready.reset();request={};visible={};external=false;}
void sync(){bool changed=false;std::shared_ptr<const Batch>b;unsigned current;
    {std::lock_guard<std::mutex>lock(guard);if(!external&&shown_revision!=revision){visible=career;shown_revision=revision;changed=true;}b=ready;current=serial;}
    if(changed){reset_scroll=true;queue();return;}
    if(device&&b&&b!=shown&&b->serial==current){clear_views();shown=b;crest=screen_visuals::upload(device,b->crest);photo=screen_visuals::upload(device,b->photo);
        flag=screen_visuals::upload(device,b->flag);league_logo=screen_visuals::upload(device,b->league_logo);
        for(const auto&entry:b->logos)if(auto*logo=screen_visuals::upload(device,entry.second))team_logos.emplace(entry.first,logo);}
}
float input(){XINPUT_STATE pad={};for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS)break;
    WORD pressed=pad.Gamepad.wButtons&~held;held=pad.Gamepad.wButtons;DWORD now=GetTickCount();if((LONG)(now-input_after)<0)return 0;
    auto&io=ImGui::GetIO();float dt=std::clamp(io.DeltaTime,0.f,.05f);int step=0;
    if(embedded&&((pressed&XINPUT_GAMEPAD_B)||ImGui::IsKeyPressed(ImGuiKey_Escape))){mod_screen_request_back();return 0;}
    if(!ImGui::IsAnyItemActive()){
        if((pressed&(XINPUT_GAMEPAD_LEFT_SHOULDER|XINPUT_GAMEPAD_DPAD_LEFT))||ImGui::IsKeyPressed(ImGuiKey_Q)||ImGui::IsKeyPressed(ImGuiKey_LeftArrow))step=-1;
        if((pressed&(XINPUT_GAMEPAD_RIGHT_SHOULDER|XINPUT_GAMEPAD_DPAD_RIGHT))||ImGui::IsKeyPressed(ImGuiKey_E)||ImGui::IsKeyPressed(ImGuiKey_RightArrow))step=1;
        if(!step&&abs(pad.Gamepad.sThumbLX)>16000&&(LONG)(now-repeat_at)>=0){step=pad.Gamepad.sThumbLX>0?1:-1;repeat_at=now+180;}
        if(step)change_page(page+step);
    }
    zoom=std::clamp(zoom+(std::max(0,int(pad.Gamepad.bRightTrigger)-30)-std::max(0,int(pad.Gamepad.bLeftTrigger)-30))/225.f*dt*.8f,.65f,2.f);
    yaw+=player_profile::stick(pad.Gamepad.sThumbRX)*dt*1.7f;pan=std::clamp(pan+player_profile::stick(pad.Gamepad.sThumbRY)*dt*.28f,-.35f,.35f);
    if((pressed&XINPUT_GAMEPAD_RIGHT_THUMB)||ImGui::IsKeyPressed(ImGuiKey_R)){yaw=pan=0;zoom=1;}
    float move=-player_profile::stick(pad.Gamepad.sThumbLY);
    if((pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_UP)||ImGui::IsKeyDown(ImGuiKey_UpArrow)||ImGui::IsKeyDown(ImGuiKey_PageUp))move=-1;
    if((pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_DOWN)||ImGui::IsKeyDown(ImGuiKey_DownArrow)||ImGui::IsKeyDown(ImGuiKey_PageDown))move=1;
    return move*dt*420;
}
void metric_card(const char*label,int n,float width,float height){
    auto at=ImGui::GetCursorScreenPos();ImGui::Dummy({width,height});auto*d=ImGui::GetWindowDrawList();
    d->AddRectFilled(at,{at.x+width,at.y+height},IM_COL32(233,242,249,255),7);
    d->AddRect(at,{at.x+width,at.y+height},IM_COL32(207,225,238,255),7);
    float fs=ImGui::GetFontSize()*.9f;auto text=ImGui::GetFont()->CalcTextSizeA(fs,FLT_MAX,0,label);
    d->AddText(ImGui::GetFont(),fs,{at.x+(width-text.x)*.5f,at.y+9},IM_COL32(55,101,137,255),label);
    char value[24];if(n>=0)sprintf_s(value,"%d",n);else strcpy_s(value,"-");
    fs=ImGui::GetFontSize()*1.55f;text=ImGui::GetFont()->CalcTextSizeA(fs,FLT_MAX,0,value);
    d->AddText(ImGui::GetFont(),fs,{at.x+(width-text.x)*.5f,at.y+height-35},IM_COL32(5,82,143,255),value);
}
void efficiency_ring(const char*id,const char*label,double value,int games,float width,bool large){
    const float height=large?176.f:142.f;
    ImGui::BeginChild(id,{width,height},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    ImGui::SetWindowFontScale(large?1.05f:.91f);
    const float label_width=ImGui::CalcTextSize(label).x;
    ImGui::SetCursorPosX(std::max(0.f,(width-label_width)*.5f));ImGui::TextUnformatted(label);
    ImGui::SetWindowFontScale(1);
    const ImVec2 origin=ImGui::GetCursorScreenPos();
    const float radius=large?std::min(61.f,width*.12f):std::min(43.f,width*.16f);
    const float ring_y=large?76.f:62.f;
    const float thickness=large?10.f:8.f;
    const ImVec2 center(origin.x+width*.5f,origin.y+ring_y);
    ImGui::Dummy({width,large?132.f:103.f});
    ImDrawList*draw=ImGui::GetWindowDrawList();
    draw->AddCircle(center,radius,IM_COL32(217,230,240,255),96,thickness);
    if(value>0){
        ImVec2 arc[97];
        const int count=std::max(2,(int)ceil(std::clamp(value,0.0,100.0)*.96)+1);
        for(int i=0;i<count;++i){
            const float angle=-1.5707963f+6.2831853f*(float)(std::clamp(value,0.0,100.0)/100.0)*(float)i/(float)(count-1);
            arc[i]={center.x+cosf(angle)*radius,center.y+sinf(angle)*radius};
        }
        draw->AddPolyline(arc,count,IM_COL32(10,108,180,255),0,thickness);
    }
    char text[24];if(value>=0)sprintf_s(text,"%.1f%%",value);else strcpy_s(text,"-");
    const float font_size=ImGui::GetFontSize()*(large?1.65f:1.22f);
    const ImVec2 text_size=ImGui::GetFont()->CalcTextSizeA(font_size,FLT_MAX,0,text);
    draw->AddText(ImGui::GetFont(),font_size,{center.x-text_size.x*.5f,center.y-text_size.y*.5f},IM_COL32(5,82,143,255),text);
    ImGui::SetCursorScreenPos({origin.x,origin.y+(large?139.f:109.f)});
    ImGui::SetWindowFontScale(.82f);
    if(games>=0){char count[40];sprintf_s(count,"%d jogos",games);const float count_width=ImGui::CalcTextSize(count).x;ImGui::SetCursorPosX(std::max(0.f,(width-count_width)*.5f));ImGui::TextUnformatted(count);}
    else {const char*unavailable="Dados indisponíveis";const float count_width=ImGui::CalcTextSize(unavailable).x;ImGui::SetCursorPosX(std::max(0.f,(width-count_width)*.5f));ImGui::TextUnformatted(unavailable);}
    ImGui::SetWindowFontScale(1);ImGui::EndChild();
}
void team_label(int team,const char*name){auto found=team_logos.find(team);
    player_profile::identity_line(found==team_logos.end()?nullptr:found->second,22,player_profile::utf8(name).c_str());}
void table_headers(){ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});ImGui::TableHeadersRow();ImGui::PopStyleColor();}
void percent(double p){if(p>=0)ImGui::Text("%.1f%%",p);else ImGui::TextUnformatted("-");}
void stats_table(const char*id,const std::vector<coach_profile::Passage>&rows,bool venues){
    if(rows.empty()){
        if(visible.context.stats_scope==COACH_STATS_CURRENT_CLUB)ImGui::TextWrapped("Não há histórico pessoal de passagens para este treinador. O desempenho do clube atual está na aba Desempenho.");
        else ImGui::TextWrapped(visible.context.history_valid?"Nenhuma passagem registrada neste grupo.":"Histórico indisponível para este treinador.");return;}
    ImGui::SetWindowFontScale(1.f);ImGui::PushStyleVar(ImGuiStyleVar_CellPadding,{8,8});
    const char*headers[]={"Equipe","Temporada","J","V","E","D","Gols +","Gols -","Taças","Aproveit. %","Casa J / %","Fora J / %"};
    const float weights[]={2.55f,1.1f,.48f,.48f,.48f,.48f,.72f,.72f,.65f,.95f,1.35f,1.35f};
    int columns=venues?12:10;
    if(ImGui::BeginTable(id,columns,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersOuter|ImGuiTableFlags_SizingStretchProp)){
        for(int i=0;i<columns;++i)ImGui::TableSetupColumn(headers[i],ImGuiTableColumnFlags_WidthStretch,weights[i]);table_headers();
        for(const auto&r:rows){ImGui::TableNextRow();ImGui::TableNextColumn();team_label(r.team,r.name.c_str());
            ImGui::TableNextColumn();if(!r.season_valid)ImGui::TextUnformatted("Atual");else if(r.first==r.last)ImGui::Text("%d",r.first+1);else ImGui::Text("%d-%d",r.first+1,r.last+1);
            for(int value:{r.total.games,r.total.wins,r.total.draws,r.total.losses,r.total.goals_for,r.total.goals_against}){ImGui::TableNextColumn();ImGui::Text("%d",value);}
            ImGui::TableNextColumn();if(visible.context.stats_scope==COACH_STATS_CURRENT_CLUB)ImGui::TextUnformatted("-");else ImGui::Text("%d",r.titles);
            ImGui::TableNextColumn();percent(coach_profile::efficiency(r.total));
            if(venues){for(const auto*s:{&r.home,&r.away}){ImGui::TableNextColumn();
                if(r.splits&&s->games>0)ImGui::Text("%d / %.1f%%",s->games,coach_profile::efficiency(*s));
                else if(r.splits)ImGui::TextUnformatted("0 / -");else ImGui::TextUnformatted("-");}}
        }ImGui::EndTable();}ImGui::PopStyleVar();ImGui::SetWindowFontScale(1);
}
void overview(){CoachMatchStats total={};for(const auto&r:visible.rows)coach_profile::add(total,r.total);
    bool valid=visible.context.history_valid!=0;float cell=(ImGui::GetContentRegionAvail().x-40)/6;
    const char*labels[]={"JOGOS","VITÓRIAS","EMPATES","DERROTAS","GOLS MARCADOS","GOLS SOFRIDOS"};
    int values[]={total.games,total.wins,total.draws,total.losses,total.goals_for,total.goals_against};
    for(int i=0;i<6;++i){if(i)ImGui::SameLine(0,8);metric_card(labels[i],valid?values[i]:-1,cell,68);}
    CoachMatchStats split_home={},split_away={};bool split_valid=false,split_current=false;
    for(auto it=visible.rows.rbegin();it!=visible.rows.rend();++it)if(it->splits_valid){
        if(visible.context.stats_scope!=COACH_STATS_CAREER||(it->team==visible.context.club&&it->season==visible.context.season)){
            split_home=it->home;split_away=it->away;split_valid=true;split_current=it->team==visible.context.club&&it->season==visible.context.season;break;}}
    ImGui::Spacing();float full_width=ImGui::GetContentRegionAvail().x;
    efficiency_ring("Aproveitamento geral","APROVEITAMENTO GERAL",valid?coach_profile::efficiency(total):-1,valid?total.games:-1,full_width,true);
    const char*home_label=visible.context.stats_scope==COACH_STATS_CAREER?(split_current?"EM CASA · TEMPORADA ATUAL":"EM CASA"):"EM CASA";
    const char*away_label=visible.context.stats_scope==COACH_STATS_CAREER?(split_current?"FORA DE CASA · TEMPORADA ATUAL":"FORA DE CASA"):"FORA DE CASA";
    float split_width=(ImGui::GetContentRegionAvail().x-10)/2;
    efficiency_ring("Aproveitamento em casa",home_label,split_valid?coach_profile::efficiency(split_home):-1,split_valid?split_home.games:-1,split_width,false);ImGui::SameLine(0,10);
    efficiency_ring("Aproveitamento fora",away_label,split_valid?coach_profile::efficiency(split_away):-1,split_valid?split_away.games:-1,split_width,false);
    ImGui::Spacing();ImGui::TextUnformatted("TAXA DE VITÓRIAS");ImGui::SameLine(0,12);percent(valid?coach_profile::win_rate(total):-1);
    ImGui::SameLine(0,8);ImGui::TextDisabled("(vitórias ÷ jogos)");ImGui::Spacing();
    if(visible.context.confidence>=0){ImGui::Text("Confiança da diretoria: %d%%",visible.context.confidence);ImGui::PushStyleColor(ImGuiCol_PlotHistogram,player_profile::ink());
        ImGui::ProgressBar(visible.context.confidence/100.f,{-1,6},"");ImGui::PopStyleColor();}
    ImGui::TextUnformatted("REPUTAÇÃO");auto rating=visible.context;
    if(!rating.league_strength_valid&&shown&&shown->league_strength>=0){rating.league_strength=shown->league_strength;rating.league_strength_valid=1;}
    player_profile::reputation_stars(coach_profile::reputation_score(rating),21);
    if(visible.context.national_team>0)ImGui::TextWrapped("Seleção atual: %s",player_profile::utf8(visible.context.national_name).c_str());
}
void trophies(){if(!visible.context.history_valid){ImGui::TextUnformatted("Histórico de títulos indisponível.");return;}
    if(visible.context.stats_scope==COACH_STATS_CURRENT_CLUB){ImGui::TextWrapped("O histórico de taças deste treinador não está disponível. Os números desta carreira são do clube atual, não um histórico individual de títulos.");return;}
    if(visible.rows.empty()){ImGui::TextUnformatted("Nenhum título registrado nesta carreira.");return;}
    if(ImGui::BeginTable("Taças por passagem",5,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersOuter|ImGuiTableFlags_SizingStretchProp)){
        ImGui::TableSetupColumn("Equipe",ImGuiTableColumnFlags_WidthStretch,2.5f);for(const char*name:{"Temp.","Ligas","Copas nacionais","Continentais"})ImGui::TableSetupColumn(name);table_headers();
        for(const auto&r:visible.rows){ImGui::TableNextRow();ImGui::TableNextColumn();team_label(r.team,r.team_name);
            for(int value:{r.season+1,r.league_titles,r.domestic_titles,r.continental_titles}){ImGui::TableNextColumn();ImGui::Text("%d",value);}}
        ImGui::EndTable();}
}
void draw(void*){
    sync();float scroll_step=input();screen_visuals::LightTheme theme;
    theme.color(ImGuiCol_TableHeaderBg,player_profile::ink());theme.color(ImGuiCol_TableRowBg,{.98f,.99f,1,1});
    theme.color(ImGuiCol_TableRowBgAlt,{.93f,.96f,.98f,1});theme.color(ImGuiCol_TableBorderStrong,{.64f,.76f,.85f,1});theme.color(ImGuiCol_TableBorderLight,{.78f,.86f,.91f,1});
    ImGui::PushStyleColor(ImGuiCol_Text,player_profile::ink());
    screen_visuals::begin_fullscreen("Perfil do técnico",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.25f);ImGui::TextUnformatted("Perfil do técnico");ImGui::SetWindowFontScale(1);
    if(!visible.context.valid){ImGui::TextUnformatted("Aguardando informações do treinador...");ImGui::End();ImGui::PopStyleColor();return;}
    ImGui::Spacing();auto area=ImGui::GetContentRegionAvail();float width=area.x*.35f,height=std::max(60.f,area.y-32);
    ImGui::BeginChild("Modelo do técnico",{width,height},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    auto at=ImGui::GetCursorScreenPos();auto stage=ImGui::GetContentRegionAvail();stage.y=std::max(40.f,stage.y-34);auto*d=ImGui::GetWindowDrawList();
    unsigned color=visible.context.colors_valid?visible.context.colors[0]:0x123d60;
    ImU32 tint=IM_COL32(233+((color>>16)&255)/16,233+((color>>8)&255)/16,233+(color&255)/16,255);
    d->AddRectFilledMultiColor(at,{at.x+stage.x,at.y+stage.y},IM_COL32(250,251,252,255),tint,tint,IM_COL32(239,245,249,255));
    if(crest){float s=stage.x*.65f;d->AddImage((ImTextureID)(intptr_t)crest,{at.x+(stage.x-s)/2,at.y+stage.y*.15f},{at.x+(stage.x+s)/2,at.y+stage.y*.15f+s},{0,0},{1,1},IM_COL32(255,255,255,24));}
    if(shown&&shown->model&&renderer.model(shown->model)&&renderer.render((UINT)stage.x,(UINT)stage.y,yaw,zoom,true,0,pan,true)){
        ImGui::Image((ImTextureID)(intptr_t)renderer.image(),stage);
        if(ImGui::IsItemHovered()){if(ImGui::IsMouseDragging(ImGuiMouseButton_Left)){yaw+=ImGui::GetIO().MouseDelta.x*.012f;pan=std::clamp(pan-ImGui::GetIO().MouseDelta.y*.0015f,-.35f,.35f);}zoom=std::clamp(zoom+ImGui::GetIO().MouseWheel*.08f,.65f,2.f);}
    }else{ImGui::Dummy(stage);d->AddText(nullptr,0,{at.x+20,at.y+stage.y*.45f},IM_COL32(60,99,127,255),shown?"Modelo 3D indisponível para este técnico.":"Carregando recursos do técnico...",nullptr,stage.x-40);}
    ImGui::SetWindowFontScale(.85f);ImGui::TextWrapped("Direito / arraste: girar e mover\nLT / RT / roda: zoom");ImGui::SetWindowFontScale(1);ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("Informações do técnico",{0,height},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar);
    if(photo){const auto&desc=shown->photo;float w=56,h=56;if(desc.width>desc.height)h=w*desc.height/desc.width;else w=h*desc.width/desc.height;ImGui::Image((ImTextureID)(intptr_t)photo,{w,h});}
    else{auto p=ImGui::GetCursorScreenPos();ImGui::Dummy({56,56});auto*dl=ImGui::GetWindowDrawList();dl->AddCircleFilled({p.x+28,p.y+16},10,IM_COL32(149,175,193,255));dl->AddRectFilled({p.x+10,p.y+30},{p.x+46,p.y+53},IM_COL32(149,175,193,255),11);}
    ImGui::SameLine();ImGui::BeginGroup();ImGui::SetWindowFontScale(1.25f);ImGui::TextWrapped("%s",player_profile::utf8(visible.context.name).c_str());ImGui::SetWindowFontScale(.9f);
    player_profile::identity_line(crest,18,visible.context.club_name[0]?player_profile::utf8(visible.context.club_name).c_str():visible.context.national_name);
    if(shown&&!shown->league_name.empty())player_profile::identity_line(league_logo,18,shown->league_name.c_str());
    if(flag&&shown&&!shown->nationality_name.empty())player_profile::identity_line(flag,20,shown->nationality_name.c_str());ImGui::SetWindowFontScale(1);ImGui::EndGroup();ImGui::Spacing();
    float tab_width=(ImGui::GetContentRegionAvail().x-32)/5;
    for(int i=0;i<5;++i){if(i)ImGui::SameLine();bool selected=i==page;if(selected){ImGui::PushStyleColor(ImGuiCol_Button,player_profile::ink());ImGui::PushStyleColor(ImGuiCol_Text,{1,1,1,1});}
#ifdef COACH_PROFILE_TEST
        auto t=ImGui::GetCursorScreenPos();tab_centers[i]={t.x+tab_width*.5f,t.y+15};
#endif
        if(ImGui::Button(tabs[i],{tab_width,30}))change_page(i);if(selected)ImGui::PopStyleColor(2);}
    ImGui::BeginChild("Dados do treinador",{0,0},false,ImGuiWindowFlags_NoNavInputs);
    if(reset_scroll){ImGui::SetScrollY(0);reset_scroll=false;}else if(scroll_step)ImGui::SetScrollY(std::clamp(ImGui::GetScrollY()+scroll_step,0.f,ImGui::GetScrollMaxY()));scroll=ImGui::GetScrollY();
    if(page==0)overview();
    else if(page==1){ImGui::TextUnformatted(visible.context.stats_scope==COACH_STATS_CURRENT_CLUB?"DESEMPENHO DO CLUBE ATUAL":"DESEMPENHO POR PASSAGEM");stats_table("Resultados",coach_profile::passages(visible.rows),true);}
    else if(page==2){ImGui::TextUnformatted("PASSAGENS POR CLUBES");
        if(visible.context.stats_scope==COACH_STATS_CURRENT_CLUB)ImGui::TextWrapped("O histórico pessoal de clubes não está disponível para este treinador.");
        else stats_table("Clubes",coach_profile::passages(visible.rows,COACH_TEAM_CLUB),true);}
    else if(page==3){ImGui::TextUnformatted("PASSAGENS POR SELEÇÕES");if(visible.context.national_team>0)ImGui::TextWrapped("Seleção atual: %s",player_profile::utf8(visible.context.national_name).c_str());stats_table("Seleções",coach_profile::passages(visible.rows,COACH_TEAM_NATIONAL),true);}
    else trophies();ImGui::EndChild();ImGui::EndChild();ImGui::SetWindowFontScale(.85f);
    ImGui::TextWrapped("Esquerdo / setas: abas e rolagem | LB/RB: abas | Direito: câmera | LT/RT: zoom | R/R3: centralizar | B/Esc: voltar");ImGui::SetWindowFontScale(1);
    ImGui::End();ImGui::PopStyleColor();
}
}
CoachCardData coach_profile_prepare_card(fifa_player::Assets&assets,const ClubPlayerRow&club,const char*club_name){
    CoachCardData out;auto assigned=assets.coach(club);auto&c=out.context;
    c.valid=club.team_id>0;c.kind=COACH_CLUB_MANAGER;c.id=c.club=club.team_id;
    c.confidence=c.reputation=c.wage=-1;c.stats_scope=COACH_STATS_NONE;
    strncpy_s(c.name,assigned.name.empty()?"Treinador":assigned.name.c_str(),_TRUNCATE);strncpy_s(c.club_name,club_name?club_name:"",_TRUNCATE);
    c.colors_valid=club.club_colors_valid;memcpy(c.colors,club.club_colors,sizeof(c.colors));
    assets.league(club.team_id,out.league_name);
    /* A club card always describes that club's assigned coach, not the
     * career-created manager. Reuse personal history only on an exact name
     * match; otherwise show the selected club's own fixture record. */
    {
        std::lock_guard<std::mutex>lock(guard);
        if(career.context.valid&&career.context.club==club.team_id&&career.context.history_valid&&!career.rows.empty()&&
            !_stricmp(career.context.name,c.name)){
            out.rows=career.rows;c.stats_scope=COACH_STATS_CAREER;c.history_valid=1;
        }else{
            auto found=team_stats.find(club.team_id);if(found!=team_stats.end()){
                out.rows.push_back(found->second);c.stats_scope=COACH_STATS_CURRENT_CLUB;c.history_valid=1;
            }
        }
    }
    // Optional exact-identity supplement; never infer nationality from the club.
    if(c.nationality<=0){std::ifstream f(career_paths::read(root+"/ModCarrerMode","data\\catalogs","coach_identity.tsv"));std::string line;
        while(std::getline(f,line)){if(line.size()>512)continue;size_t a=line.find('|'),b=line.find('|',a==line.npos?0:a+1);if(a==line.npos||b==line.npos)continue;
            std::string id_text=line.substr(0,a);char*end=nullptr;long id=strtol(id_text.c_str(),&end,10);if(!end||*end||id!=c.club)continue;
            auto name=player_profile::utf8(line.substr(a+1,b-a-1).c_str());if(_stricmp(name.c_str(),player_profile::utf8(c.name).c_str()))continue;
            std::string number=line.substr(b+1);long nation=strtol(number.c_str(),&end,10);while(end&&(*end=='\r'||*end==' '))++end;
            if(end&&!*end&&nation>0&&nation<=3000)c.nationality=(int)nation;break;}}
    if(c.nationality>0){thread_local std::unique_ptr<native_loc::Names>names;if(!names)names=std::make_unique<native_loc::Names>(root);
        out.nationality_name=names->nation(c.nationality);assets.nationality_flag(c.nationality,out.flag);}
    photo_file(c,out.photo);
    if(assigned.model&&c.club>0&&(c.kind==COACH_CAREER_USER||c.kind==COACH_CLUB_MANAGER)){
        auto m=std::make_shared<fifa_player::Model>(*assigned.model);
        if(m->skeleton&&!fifa_player::apply_coach_pose(*m,201))
            m->diagnostic+="\ncoach profile: fixed native pose unavailable; original club model preserved";
        out.model=m;
    }
    return out;
}
bool coach_profile_begin_embedded(const CoachCardData&card){
    if(!event||(!mod_screen_is_active("club_players")&&!mod_screen_is_active("other-clubs")&&!mod_screen_is_active("my-office")))return false;Snapshot next;
    if(!coach_profile::copy(&card.context,card.rows.data(),card.rows.size(),next.context,next.rows))return false;
    {std::lock_guard<std::mutex>lock(guard);
        if(next.context.kind==COACH_CLUB_MANAGER&&next.context.stats_scope!=COACH_STATS_CAREER){auto found=team_stats.find(next.context.club);
            if(found!=team_stats.end()){next.rows.assign(1,found->second);next.context.stats_scope=COACH_STATS_CURRENT_CLUB;next.context.history_valid=1;}}
        if(career.context.valid&&career.context.kind==next.context.kind&&career.context.id==next.context.id&&career.context.club==next.context.club&&!strcmp(career.context.name,next.context.name)){
            int nationality=next.context.nationality;next=career;if(next.context.nationality<=0)next.context.nationality=nationality;}
        pending=std::move(next);pending_external=true;}
    embedded=true;opened(nullptr);return true;
}
void coach_profile_draw_embedded(){if(embedded)draw(nullptr);}
void coach_profile_end_embedded(){if(embedded){closed(nullptr);embedded=false;}}
unsigned coach_profile_card_revision(){std::lock_guard<std::mutex>lock(guard);return identity_revision;}
extern "C" void coach_profile_publish_career(const CoachProfileContext*c,const CoachCareerRow*rows,size_t n){Snapshot next;
    if(!coach_profile::copy(c,rows,n,next.context,next.rows))next={};
    std::lock_guard<std::mutex>lock(guard);if(!memcmp(&next.context,&career.context,sizeof(next.context))&&next.rows.size()==career.rows.size()&&(next.rows.empty()||!memcmp(next.rows.data(),career.rows.data(),next.rows.size()*sizeof(CoachCareerRow))))return;
    const auto&a=next.context;const auto&b=career.context;
    if(a.valid!=b.valid||a.kind!=b.kind||a.id!=b.id||a.club!=b.club||a.nationality!=b.nationality||strcmp(a.name,b.name)||a.colors_valid!=b.colors_valid||memcmp(a.colors,b.colors,sizeof(a.colors)))++identity_revision;
    career=std::move(next);++revision;
}
extern "C" void coach_profile_publish_team_fixtures(int club,const char*name,const FceFixture*f,size_t count,int today){
    if(club<=0||club>200000)return;CoachCareerRow row={};
    if(!coach_profile::current_club_row(f,count,club,today,name,row)){std::lock_guard<std::mutex>lock(guard);team_stats.erase(club);return;}
    std::lock_guard<std::mutex>lock(guard);team_stats[club]=row;
    if(team_stats.size()>COACH_PROFILE_CAPACITY){auto victim=team_stats.begin();if(victim!=team_stats.end()&&victim->first==club&&team_stats.size()>1)++victim;if(victim!=team_stats.end()&&victim->first!=club)team_stats.erase(victim);}
}
extern "C" BOOL coach_profile_take_refresh(){return InterlockedExchange(&refresh_requested,0)!=0;}
extern "C" BOOL coach_profile_open(const CoachProfileContext*c,const CoachCareerRow*rows,size_t n){Snapshot next;if(mod_screen_is_open()||!coach_profile::copy(c,rows,n,next.context,next.rows))return FALSE;
    {std::lock_guard<std::mutex>lock(guard);pending=std::move(next);pending_external=true;}
    if(mod_screen_open_action(FIFA16_COACH_PROFILE_ACTION))return TRUE;
    std::lock_guard<std::mutex>lock(guard);pending_external=false;pending={};return FALSE;
}
extern "C" void coach_profile_bind_splits(CoachCareerRow*r,size_t n,const FceFixture*f,size_t count,int today,int club,int season){coach_profile::bind_splits(r,n,f,count,today,club,season);}
extern "C" void coach_profile_bind_form(CoachProfileContext*c,const FceFixture*f,size_t n,int today){if(c)coach_profile::recent_form(*c,f,n,today);}
bool coach_profile_register(const char*game_root,void(*log)(const char*)){
    root=game_root?game_root:"";logger=log;event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!event)return false;
    HANDLE thread=CreateThread(nullptr,0,guarded_worker,nullptr,0,nullptr);if(!thread){CloseHandle(event);event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"coach-profile",FIFA16_COACH_PROFILE_ACTION,opened,draw,closed,nullptr,nullptr};return mod_screen_register(&screen)!=FALSE;
}
void coach_profile_device(ID3D11Device*d){renderer.device(d);if(d==device)return;clear_views();if(device)device->Release();device=d;if(d)d->AddRef();}
#ifdef COACH_PROFILE_TEST
CoachProfileTestView coach_profile_test_view(){return {visible.context.kind,visible.context.id,visible.context.club,page,visible.rows.size(),shown&&bool(shown->model),photo!=nullptr,external,yaw,zoom,pan,scroll};}
bool coach_profile_test_tab_center(int i,float&x,float&y){if(i<0||i>=5)return false;x=tab_centers[i].x;y=tab_centers[i].y;return x>0&&y>0;}
#endif
