#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include "club_player_screen.h"
#include "../player/player_search_screen.h"
#include "../player/club_player_profile.h"
#include "../player/player_profile_view.h"
#include "../../render/renderer/fifa_player_renderer.h"
#include "../../platform/overlay/mod_overlay_screens.h"
#include "../../platform/input/mod_xinput_gate.h"
#include "../operations/career_operations.h"
#include "../transfers/transfer_center_screen.h"
#include "../coach/coach_profile_screen.h"
#include "../coach/coach_profile_data.h"
#include "../office/office_social_feed.h"
#include "../office/career_news_feed.h"
#include "../competitions/club_competitions_screen.h"
#include "../../platform/overlay/webview2_overlay_host.h"
#include "../../render/scenes/new_experience_rooms.h"
#include "../../ui/common/native_loc_names.h"
#include "../../../third_party/imgui/imgui.h"
#include <algorithm>
#include <mutex>
#include <string>
#include <vector>
#include <memory>
#include <cmath>
#include <unordered_map>
#include <stdio.h>

namespace {
const char *fields[CLUB_PLAYER_ATTRIBUTE_COUNT]={
    "acceleration","sprintspeed","agility","reactions","balance","shotpower",
    "finishing","longshots","volleys","penalties","vision","crossing",
    "shortpassing","longpassing","curve","freekickaccuracy","ballcontrol",
    "dribbling","strength","stamina","jumping","aggression","interceptions",
    "positioning","marking","standingtackle","slidingtackle","headingaccuracy",
    "gkdiving","gkhandling","gkkicking","gkpositioning","gkreflexes","potential"};
std::mutex lock;
std::vector<ClubPlayerRow> published,visible;
std::vector<ClubPlayerRow> external_rows;
std::string external_team;
int external_club=0;
bool embedded_club=false;
bool database_profile_child=false;
std::string team,visible_team,root;
unsigned revision=0,visible_revision=~0u,request_serial=0,ready_serial=0;
unsigned request_coach_revision=~0u;
volatile LONG refresh_requested=0;
unsigned pose_id=1,request_pose_id=1;
unsigned group_pose_id=1,random_state=0;
unsigned press_pose_id=205,request_press_pose_id=205;
fifa_player::ClubRoomKind room_kind=fifa_player::RoomPhoto,request_room=fifa_player::RoomPhoto;
player_profile::State profile_state;
int &attribute_page=profile_state.page;
bool &portrait_mode=profile_state.portrait;
DWORD back_ready_at=0,input_ready_at=0;
int published_club=0,visible_club=0,selected=0,requested_player=0;
int press_player=0;
bool press_resample=false;
bool is_press_room(){return room_kind==fifa_player::RoomPress||room_kind==fifa_player::RoomPressPair;}
std::vector<ClubPlayerRow> request_rows;
std::vector<ClubPlayerRow> request_roster;
std::string request_team;
CareerNextMatchFacts request_office_match={},office_match_card={};
int request_kit_club=0;
bool request_kit_previews=false;
std::vector<int> lineup;
bool group_mode=true,request_group=false,request_coach=false;
bool request_office=false;
bool club_home=true,coach_child=false,from_home=false;
bool office_mode=false,office_home=false;
bool uniforms_open=false;
bool full_squad_mode=false;
volatile LONG web_room_requested=0,web_player_requested=0,web_pose_requested=0;
bool html_player_available=true;
int office_focus=0,office_menu=-1,office_item=0,office_slide=0,office_main_page=0,office_training_row=0;
DWORD office_repeat=0,office_last_advance=0,office_transition_started=0;
int office_transition_from=-1,office_transition_direction=1;
ImVec2 office_centers[11]={},office_menu_centers[5]={},office_dots[6]={},office_social_dots[5]={},office_social_next={};
office_social::Runtime office_social_runtime;
std::mutex career_news_lock;
CareerNewsFacts career_news_facts={};
CareerNewsManagerFacts career_news_manager={};
CareerWebDashboard career_web_dashboard={};
CareerNewsItem career_news_items[CAREER_NEWS_CAPACITY]={};
size_t career_news_item_count=0;
CareerNextMatchFacts career_next_match_facts={};
CareerClubStadiumFacts career_club_stadium_facts={};
fifa_player::Renderer office_coach_renderer,office_lineup_renderer;
std::shared_ptr<const fifa_player::Model>office_lineup_source,office_lineup_model;
std::shared_ptr<const fifa_player::Model>html_preview_source;
int card_focus=0;
float card_coach_yaw=0,card_coach_zoom=1,card_coach_pan=0;
DWORD card_repeat=0;
int mouse_card_press=-1;float mouse_card_travel=0;
ImVec2 card_centers[3]={};
fifa_player::Renderer coach_card_renderer;
bool lineup_valid=false;
WORD previous_buttons=0;
HANDLE work_event=nullptr;
std::shared_ptr<const fifa_player::Model> ready_model;
fifa_player::Renderer renderer;
void (*logger)(const char *)=nullptr;
bool scroll_selected=false,loading=false,render_failed_logged=false;
float &yaw=profile_state.yaw,&zoom=profile_state.zoom;
float photo_pan_x=0,photo_pan_y=0;
struct IconBatch {std::unordered_map<int,fifa_player::Texture>portraits,flags,competitions;std::vector<fifa_player::CompetitionIdentity>competition_names;std::vector<fifa_player::KitThumbnail>kits;std::unordered_map<int,int>nations,ages,feet;fifa_player::Texture crest,league_logo,office_next_home_crest,office_next_away_crest,office_next_competition;CareerNextMatchFacts office_next_match={};int club=0,league=0;float league_strength=-1;std::string league_name,office_next_competition_name;fifa_player::CoachAsset coach;CoachCardData card;std::shared_ptr<const fifa_player::Model>arrival;std::shared_ptr<const fifa_player::Texture>office_stadium;};
std::shared_ptr<const IconBatch>ready_icons,visible_icons;
bool has_coach(){return visible_icons&&visible_icons->club==visible_club&&visible_icons->coach.model;}
bool coach_poses_available(){return has_coach()&&visible_icons->coach.model->skeleton&&visible_icons->coach.model->skeleton->names.size()==31;}
bool coach_selected(){return has_coach()&&selected==(int)visible.size();}
int last_selection(){return (int)visible.size()-1+(has_coach()&&!from_home?1:0);}
ID3D11Device*icon_device=nullptr;
std::unordered_map<int,ID3D11ShaderResourceView*>portrait_views;
std::unordered_map<int,ID3D11ShaderResourceView*>flag_views;
std::unordered_map<int,ID3D11ShaderResourceView*>competition_views;
std::vector<ID3D11ShaderResourceView*>kit_views;
ID3D11ShaderResourceView*crest_view=nullptr,*league_view=nullptr,*office_stadium_view=nullptr;
ID3D11ShaderResourceView*office_next_home_crest_view=nullptr,*office_next_away_crest_view=nullptr,*office_next_competition_view=nullptr;
ID3D11ShaderResourceView*coach_card_photo=nullptr,*coach_card_flag=nullptr;
void clear_icon_views() {
    for(auto&i:portrait_views)if(i.second)i.second->Release();portrait_views.clear();
    for(auto&i:flag_views)if(i.second)i.second->Release();flag_views.clear();
    for(auto&i:competition_views)screen_visuals::release(i.second);competition_views.clear();
    for(auto*&view:kit_views)screen_visuals::release(view);kit_views.clear();
    if(crest_view){crest_view->Release();crest_view=nullptr;}visible_icons.reset();
    screen_visuals::release(league_view);
    screen_visuals::release(coach_card_photo);screen_visuals::release(coach_card_flag);coach_card_renderer.clear();
    office_coach_renderer.clear();office_lineup_renderer.clear();office_lineup_source.reset();office_lineup_model.reset();
    screen_visuals::release(office_stadium_view);
    screen_visuals::release(office_next_home_crest_view);screen_visuals::release(office_next_away_crest_view);screen_visuals::release(office_next_competition_view);
}
ID3D11ShaderResourceView*upload_icon(const fifa_player::Texture&t) {
    if(!icon_device||!t.width||!t.height||t.format>2||t.bytes.empty())return nullptr;
    D3D11_TEXTURE2D_DESC desc={};desc.Width=t.width;desc.Height=t.height;desc.MipLevels=desc.ArraySize=1;
    desc.Format=t.format==0?DXGI_FORMAT_BC1_UNORM:t.format==1?DXGI_FORMAT_BC2_UNORM:DXGI_FORMAT_BC3_UNORM;
    desc.SampleDesc.Count=1;desc.BindFlags=D3D11_BIND_SHADER_RESOURCE;desc.Usage=D3D11_USAGE_IMMUTABLE;
    D3D11_SUBRESOURCE_DATA data={t.bytes.data(),((t.width+3)/4)*(t.format?16:8),(UINT)t.bytes.size()};
    ID3D11Texture2D*texture=nullptr;ID3D11ShaderResourceView*view=nullptr;
    if(SUCCEEDED(icon_device->CreateTexture2D(&desc,&data,&texture))) {
        icon_device->CreateShaderResourceView(texture,nullptr,&view);texture->Release();
    }return view;
}
void sync_icons() {
    std::shared_ptr<const IconBatch>batch;
    {std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial)batch=ready_icons;}
    if(!icon_device||!batch||batch==visible_icons||batch->club!=visible_club)return;
    clear_icon_views();visible_icons=batch;
    for(const auto&i:batch->portraits)portrait_views[i.first]=upload_icon(i.second);
    for(const auto&i:batch->flags)flag_views[i.first]=upload_icon(i.second);
    for(const auto&i:batch->competitions)competition_views[i.first]=screen_visuals::upload(icon_device,i.second);
    for(const auto&kit:batch->kits)kit_views.push_back(screen_visuals::upload(icon_device,kit.image));
    crest_view=upload_icon(batch->crest);
    league_view=upload_icon(batch->league_logo);
    coach_card_photo=screen_visuals::upload(icon_device,batch->card.photo);coach_card_flag=screen_visuals::upload(icon_device,batch->card.flag);
    office_stadium_view=batch->office_stadium?screen_visuals::upload(icon_device,*batch->office_stadium):nullptr;
    office_next_home_crest_view=screen_visuals::upload(icon_device,batch->office_next_home_crest);
    office_next_away_crest_view=screen_visuals::upload(icon_device,batch->office_next_away_crest);
    office_next_competition_view=screen_visuals::upload(icon_device,batch->office_next_competition);
}
DWORD next_step=0;
std::string utf8(const char *value) {
    if(!value)return {};
    if(MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,value,-1,nullptr,0))return value;
    int count=MultiByteToWideChar(CP_ACP,0,value,-1,nullptr,0);if(!count)return value;
    std::vector<wchar_t>w(count);MultiByteToWideChar(CP_ACP,0,value,-1,w.data(),count);
    int bytes=WideCharToMultiByte(CP_UTF8,0,w.data(),-1,nullptr,0,nullptr,nullptr);
    std::string out(bytes,'\0');WideCharToMultiByte(CP_UTF8,0,w.data(),-1,&out[0],bytes,nullptr,nullptr);
    if(!out.empty())out.pop_back();return out;
}
void log_diagnostic(const std::string&value) {
    if(!logger)return;
    /* The existing host logger has a 384-byte record limit. Do not pass a
     * multi-kilobyte model diagnostic as one record or later actors disappear. */
    size_t start=0,lines=0;
    while(start<value.size()&&lines<80) {
        size_t end=value.find('\n',start);if(end==value.npos)end=value.size();
        if(end>start){logger(("Club3D asset: "+value.substr(start,std::min(size_t(340),end-start))).c_str());++lines;}
        start=end+1;
    }
    if(start<value.size())logger("Club3D asset: further diagnostic lines omitted; roster and formation logged separately");
}
DWORD WINAPI worker(void *) {
    fifa_player::Assets assets(root);
    std::shared_ptr<const fifa_player::Texture>office_background;
    bool office_background_attempted=false;
    struct Cached {ClubPlayerRow row;std::shared_ptr<const fifa_player::Model>model;};
    std::unordered_map<int,Cached>cache;
    fifa_player::CoachAsset coach_cache;ClubPlayerRow coach_club={};
    for(;;) {
        if(WaitForSingleObject(work_event,INFINITE)!=WAIT_OBJECT_0)return 0;
        std::vector<ClubPlayerRow>rows,roster;std::string club_name;CareerNextMatchFacts office_match={};unsigned serial,pose,press_pose;bool group,staff,office,kit_previews;int kit_club;fifa_player::ClubRoomKind room;
        {std::lock_guard<std::mutex>guard(lock);rows=request_rows;roster=request_roster;club_name=request_team;office_match=request_office_match;serial=request_serial;group=request_group;staff=request_coach;office=request_office;kit_previews=request_kit_previews;kit_club=request_kit_club;pose=request_pose_id;room=request_room;press_pose=request_press_pose_id;}
        const auto&source=roster.empty()?rows:roster;int current_club=source.empty()?kit_club:source.front().team_id;
        if(rows.empty()&&roster.empty()&&(!kit_previews||current_club<=0))continue;
        std::shared_ptr<const fifa_player::Model>model;
        auto icons=std::make_shared<IconBatch>();
        icons->office_next_match=office_match;
        if(office&&!office_background_attempted){
            office_background_attempted=true;auto image=std::make_shared<fifa_player::Texture>();std::string source;
            if(screen_visuals::load_image_file(root+"/ModCarrerMode/assets/ui/my_office/stadium_day_generic.png",*image))office_background=std::move(image);
            else if(logger)logger("Club3D: daytime office stadium backdrop unavailable; using neutral background");
        }
        icons->office_stadium=office_background;
        bool cancelled=false;
        try {
            icons->club=current_club;if(current_club<=0)continue;assets.crest(icons->club,icons->crest);
            icons->league=assets.league(icons->club,icons->league_name);assets.competition_icon(icons->league,icons->league_logo);
            icons->league_strength=assets.league_strength(icons->club);
            if(kit_previews)icons->kits=assets.kit_thumbnails(icons->club);
            if(office&&office_match.valid){
                assets.crest(office_match.home_team,icons->office_next_home_crest);
                assets.crest(office_match.away_team,icons->office_next_away_crest);
                if(office_match.competition_asset>0){assets.competition_icon(office_match.competition_asset,icons->office_next_competition);
                    native_loc::Names names(root);icons->office_next_competition_name=names.competition(office_match.competition_asset);}
            }
            ClubPlayerRow club={};if(!source.empty())club=source.front();else club.team_id=icons->club;
            if(club.player_id>0)icons->competition_names=assets.profile_competition_names(club.player_id,club.team_id);
            for(auto&i:icons->competition_names){fifa_player::Texture logo;if(assets.competition_icon(i.asset,logo))icons->competitions.emplace(i.root,std::move(logo));}
            icons->card=coach_profile_prepare_card(assets,club,club_name.c_str());
            if(club.team_id!=coach_club.team_id||club.club_colors_valid!=coach_club.club_colors_valid||memcmp(club.club_colors,coach_club.club_colors,sizeof(club.club_colors))) {
                coach_club=club;coach_cache=assets.coach(club);
                if(logger&&coach_cache.model)logger(coach_cache.model->diagnostic.c_str());
            }
            icons->coach=coach_cache;
            for(const auto&r:roster) {
                {std::lock_guard<std::mutex>guard(lock);if(serial!=request_serial){cancelled=true;break;}}
                fifa_player::Texture t;if(assets.portrait(r.player_id,t))icons->portraits.emplace(r.player_id,std::move(t));
                int nation=assets.nationality(r.player_id);icons->nations[r.player_id]=nation;
                icons->ages[r.player_id]=assets.player_age(r.player_id);
                icons->feet[r.player_id]=assets.preferred_foot(r.player_id);
                if(nation>0&&!icons->flags.count(nation)){fifa_player::Texture flag;if(assets.nationality_flag(nation,flag))icons->flags.emplace(nation,std::move(flag));}
            }
            if(cancelled)continue;
            std::vector<std::shared_ptr<const fifa_player::Model>>models;
            for(const auto&row:rows) {
                {std::lock_guard<std::mutex>guard(lock);if(serial!=request_serial){cancelled=true;break;}}
                auto found=cache.find(row.player_id);
                if(found==cache.end()||memcmp(&found->second.row,&row,sizeof(row))) {
                    if(cache.size()>=12)cache.erase(cache.begin());
                    auto loaded=std::make_shared<fifa_player::Model>(assets.load(row));
                    cache[row.player_id]={row,loaded};found=cache.find(row.player_id);
                }
                models.push_back(found->second.model);
            }
            if(cancelled)continue;
            // Office scene uses the club's assigned coach asset, as requested.
            // Career-manager identity/stats remain separate: a custom name
            // must not hide this visual or change which club supplies it.
            if(office&&group&&icons->coach.model){
                auto anchor=models.empty()?std::make_shared<fifa_player::Model>(assets.load(club)):models.front();
                auto arrival=std::make_shared<fifa_player::Model>(fifa_player::build_coach_arrival(*anchor,*icons->coach.model));
                if(arrival->press_coach_present)icons->arrival=std::move(arrival);
            }
            if(staff&&icons->coach.model) {
                auto coach=std::make_shared<fifa_player::Model>(*icons->coach.model);
                if(!fifa_player::apply_coach_pose(*coach,pose))coach->diagnostic+="\ncoach pose unavailable; preserved original model (no borrowed rig)";
                model=coach;
            }
            else if(group&&!models.empty()){
                if(room==fifa_player::RoomFullSquadPhoto){
                    model=std::make_shared<fifa_player::Model>(fifa_player::build_full_squad_photo(models,icons->coach.model));
                }else if(room==fifa_player::RoomPhoto){
                    model=std::make_shared<fifa_player::Model>(fifa_player::assemble_starting_eleven(models,pose));
                }else model=std::make_shared<fifa_player::Model>(fifa_player::build_new_experience_room(assets,root,models,roster,icons->coach,room));
            }
            else if(!models.empty()){auto individual=std::make_shared<fifa_player::Model>(*models.front());
                fifa_player::apply_presentation_pose(*individual,false,nullptr,pose);model=individual;}
        }
        catch(...){if(logger)logger("Club3D: asset load failed; preview unavailable");}
        {std::lock_guard<std::mutex>guard(lock);
            if(serial!=request_serial)continue;
            ready_model=model;ready_icons=icons;ready_serial=serial;
        }
        if(logger && model) {
            const auto&first=(rows.empty()?roster:rows).front();
            char message[256];sprintf_s(message,"Club3D: player=%d team=%d group=%d players=%zu parts=%zu textures=%zu specific_head=%d posed=%d colors=%d crest=%d pose=%u",
                first.player_id,first.team_id,group,model->player_count,model->parts.size(),model->textures.size(),model->specific_head,model->presentation_pose,model->club_colors_valid,model->crest_texture>=0,model->presentation_pose_id);
            if(staff){sprintf_s(message,"Club3D: coach details ready; own compact sideline rig; pose=%u",model->presentation_pose_id);logger(message);}
            else if(model->room!=fifa_player::RoomPhoto){sprintf_s(message,"Club3D: room ready; room=%d team=%d parts=%zu textures=%zu colors=%d crest=%d pose=%u",model->room,model->team_id,model->parts.size(),model->textures.size(),model->club_colors_valid,model->crest_texture>=0,model->presentation_pose_id);logger(message);}
            else logger(message);
            for(size_t i=0;i<model->formation.size();++i) {
                const auto&r=model->formation[i];
                sprintf_s(message,"Club3D photo slot=%zu player=%d height=%d keeper=%d row=%s pose=%u",
                    i+1,r.player_id,r.height_cm,r.goalkeeper,r.crouching?"front":"back",model->presentation_pose_id);
                logger(message);
            }
            log_diagnostic(model->diagnostic);
        }
    }
}
void queue_preview() {
    unsigned coach_revision=coach_profile_card_revision();
    std::vector<ClubPlayerRow>rows;
    CareerNextMatchFacts next_match={};
    if(office_mode)career_next_match_copy(visible_club,&next_match);
    bool staff=!group_mode&&coach_selected(),kit_previews=(club_home&&!office_mode)||uniforms_open;int kit_club=visible_club;
    if(group_mode) {
        if(room_kind==fifa_player::RoomPressPair) {
            auto at=std::find_if(visible.begin(),visible.end(),[](const auto&r){return r.player_id==press_player;});
            if(press_resample||at==visible.end()) {
                std::vector<const ClubPlayerRow*>eligible;
                for(const auto&r:visible)if(r.team_id==visible_club&&r.player_id>0&&r.height>=130&&r.height<=230&&
                    (visible.size()==1||r.player_id!=press_player))eligible.push_back(&r);
                if(eligible.empty())for(const auto&r:visible)if(r.team_id==visible_club&&r.player_id>0)eligible.push_back(&r);
                if(!random_state)random_state=GetTickCount()^GetCurrentProcessId()^0x9e3779b9u;
                random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;
                press_player=eligible.empty()?0:eligible[random_state%eligible.size()]->player_id;
                press_resample=false;
            }
            for(const auto&r:visible)if(r.player_id==press_player){rows.push_back(r);break;}
        }else if(full_squad_mode)rows=visible;
        else for(int id:lineup)for(const auto&r:visible)if(r.player_id==id){rows.push_back(r);break;}
    }else if(!staff&&selected>=0&&selected<(int)visible.size())rows.push_back(visible[selected]);
    {std::lock_guard<std::mutex>guard(lock);
        bool same=request_office==office_mode&&request_kit_previews==kit_previews&&request_kit_club==kit_club&&request_coach_revision==coach_revision&&request_group==group_mode && request_coach==staff && request_pose_id==pose_id && request_press_pose_id==press_pose_id && request_room==(group_mode?room_kind:fifa_player::RoomPhoto) &&
            request_office_match.valid==next_match.valid&&request_office_match.home_team==next_match.home_team&&request_office_match.away_team==next_match.away_team&&request_office_match.competition_asset==next_match.competition_asset&&request_rows.size()==rows.size() &&
            request_roster.size()==visible.size() && (visible.empty()||!memcmp(request_roster.data(),visible.data(),visible.size()*sizeof(ClubPlayerRow))) &&
            (rows.empty()||!memcmp(request_rows.data(),rows.data(),rows.size()*sizeof(ClubPlayerRow)));
        if(same)return;
        request_coach_revision=coach_revision;
        request_office=office_mode;
        request_kit_previews=kit_previews;request_kit_club=kit_club;
        request_office_match=next_match;
        request_rows=rows;request_roster=visible;request_team=visible_team;request_group=group_mode;request_coach=staff;request_pose_id=pose_id;request_room=group_mode?room_kind:fifa_player::RoomPhoto;++request_serial;ready_model.reset();ready_icons.reset();
        request_press_pose_id=press_pose_id;
        requested_player=rows.empty()?0:rows.front().player_id;
    }
    renderer.clear();loading=!rows.empty()||staff;render_failed_logged=false;
    yaw=0;zoom=1;photo_pan_x=photo_pan_y=0;SetEvent(work_event);
    profile_state.pan_y=0;
}
void select_player(int index) {
    if(visible.empty())return;selected=std::max(0,std::min(last_selection(),index));
    scroll_selected=true;if(!group_mode)queue_preview();
}
void random_individual_pose() {
    size_t count=fifa_player::presentation_pose_count(fifa_player::PoseIndividual);
    if(!count)return;
    if(!random_state)random_state=GetTickCount()^0x9e3779b9u;
    random_state^=random_state<<13;random_state^=random_state>>17;random_state^=random_state<<5;
    size_t index=random_state%count;
    if(count>1&&fifa_player::presentation_pose_at(index,fifa_player::PoseIndividual)->id==pose_id)index=(index+1)%count;
    pose_id=fifa_player::presentation_pose_at(index,fifa_player::PoseIndividual)->id;
}
void open_details(int index) {
    if(visible.empty())return;
    if(group_mode)group_pose_id=pose_id;
    selected=std::max(0,std::min(last_selection(),index));group_mode=false;
    profile_state=player_profile::State{};
    if(coach_selected())pose_id=coach_poses_available()?201:0;else random_individual_pose();queue_preview();
    yaw=-.12f;back_ready_at=input_ready_at=GetTickCount()+250;
    if(logger)logger(coach_selected()?"Club3D: coach detail view opened; read-only sideline model":"Club3D: player detail view opened; read-only attributes");
}
BOOL back(void*) {
    if((LONG)(GetTickCount()-back_ready_at)<0)return TRUE;
    if(database_profile_child)return FALSE;
    if(uniforms_open){uniforms_open=false;club_home=true;queue_preview();back_ready_at=input_ready_at=GetTickCount()+250;return TRUE;}
    if(office_home&&office_menu>=0){office_menu=-1;back_ready_at=input_ready_at=GetTickCount()+200;return TRUE;}
    if(coach_child){coach_profile_end_embedded();coach_child=false;club_home=true;office_home=office_mode;back_ready_at=input_ready_at=GetTickCount()+250;return TRUE;}
    if(club_home)return FALSE;
    if(group_mode&&from_home){club_home=true;office_home=office_mode;from_home=false;queue_preview();back_ready_at=input_ready_at=GetTickCount()+250;return TRUE;}
    if(group_mode)return FALSE;
    group_mode=true;pose_id=group_pose_id;queue_preview();
    back_ready_at=input_ready_at=GetTickCount()+250;
    if(logger)logger("Club3D: player details returned to team; modal capture retained");
    return TRUE;
}
const char *position(int p);
void draw_coach_details() {
    if(!coach_selected())return;
    const auto&coach=visible_icons->coach;
    float width=ImGui::GetContentRegionAvail().x,height=std::max(100.f,ImGui::GetContentRegionAvail().y-35);
    ImGui::BeginChild("Ficha do treinador",ImVec2(width*.4f,height),true,ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.35f);ImGui::TextUnformatted(utf8(coach.name.c_str()).c_str());ImGui::SetWindowFontScale(1);
    ImGui::TextUnformatted("TREINADOR");ImGui::Separator();
    ImGui::TextWrapped("Clube: %s",utf8(visible_team.c_str()).c_str());
    ImGui::TextWrapped("Modelo 3D do mod de beira de campo, associado ao ID deste clube.");
    ImGui::Spacing();ImGui::TextWrapped(coach.model->skeleton?"Poses próprias do técnico, com o rig deste modelo. Sem atributos de jogador ou alterações no save.":"Rig de técnico não reconhecido: modelo original preservado, sem poses.");
    ImGui::Spacing();ImGui::TextWrapped("A associação e o nome vêm dos arquivos instalados. O modelo não é uma reconstrução do técnico criado no modo carreira.");
    ImGui::EndChild();ImGui::SameLine();
    ImGui::BeginChild("Treinador 3D",ImVec2(0,height),true,ImGuiWindowFlags_NoNavInputs);
    std::shared_ptr<const fifa_player::Model>model;
    {std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial){model=ready_model;loading=false;}}
    ImGui::TextUnformatted("Arraste para girar / analógico direito");
    ImVec2 area=ImGui::GetContentRegionAvail();area.y=std::max(60.f,area.y-25);
    if(model&&renderer.model(model)&&renderer.render((UINT)area.x,(UINT)area.y,yaw,zoom,portrait_mode)) {
        ImGui::Image((ImTextureID)(intptr_t)renderer.image(),area);
        if(ImGui::IsItemHovered()) {
            if(ImGui::IsMouseDragging(ImGuiMouseButton_Left))yaw+=ImGui::GetIO().MouseDelta.x*.012f;
            zoom=std::max(.65f,std::min(1.5f,zoom+ImGui::GetIO().MouseWheel*.08f));
        }
    }else ImGui::TextWrapped(loading?"Carregando treinador 3D...":"Modelo do treinador indisponível.");
    ImGui::EndChild();ImGui::Separator();
    ImGui::TextUnformatted("Arraste / analógico direito: girar | LT/RT: zoom | X/P: pose | Y/F: enquadramento | B/Esc: equipe");
}
void draw_details(ImVec4) {
    if(visible.empty()){ImGui::TextUnformatted("Jogador indisponível.");return;}
    if(coach_selected()){draw_coach_details();return;}
    if(selected<0||selected>=(int)visible.size())return;
    const auto&r=visible[selected];
    player_profile::Visuals visuals;
    auto face=portrait_views.find(r.player_id);if(face!=portrait_views.end())visuals.face=face->second;
    visuals.crest=crest_view;visuals.loading=loading;
    visuals.competition_icons=competition_views;
    if(visible_icons)visuals.competitions=visible_icons->competition_names;
    if(visible_icons){auto nation=visible_icons->nations.find(r.player_id);
        visuals.league=visible_icons->league;visuals.league_name=visible_icons->league_name;visuals.league_logo=league_view;
        visuals.league_strength=visible_icons->league_strength;
        auto foot=visible_icons->feet.find(r.player_id);if(foot!=visible_icons->feet.end())visuals.foot=foot->second;
        auto age=visible_icons->ages.find(r.player_id);if(age!=visible_icons->ages.end())visuals.age=age->second;
        if(nation!=visible_icons->nations.end()){visuals.nationality=nation->second;auto flag=flag_views.find(nation->second);if(flag!=flag_views.end())visuals.flag=flag->second;}}
    {std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial){visuals.model=ready_model;loading=false;}}
    auto action=player_profile::draw(r,visible_team.c_str(),profile_state,visuals,renderer,pose_id);
    if(action.back)mod_screen_request_back();
    if(action.next_pose){random_individual_pose();queue_preview();}
    if(action.pose){pose_id=action.pose;queue_preview();}
}
void sync_rows() {
    bool changed=false;ClubPlayerRow previous={};
    bool was_coach=coach_selected();
    if(selected>=0&&selected<(int)visible.size())previous=visible[selected];
    int old=previous.player_id,previous_club=visible_club;
    {std::lock_guard<std::mutex>guard(lock);
        if(revision!=visible_revision) {
            changed=true;visible=embedded_club?external_rows:published;visible_team=embedded_club?external_team:team;
            visible_club=embedded_club?external_club:published_club;visible_revision=revision;
        }
    }
    if(!changed){if(request_coach_revision!=coach_profile_card_revision()){
            float z=zoom,px=photo_pan_x,py=photo_pan_y,y=yaw;queue_preview();clear_icon_views();zoom=z;photo_pan_x=px;photo_pan_y=py;yaw=y;}return;}
    int index=0;for(size_t i=0;i<visible.size();++i)if(visible[i].player_id==old)index=(int)i;
    selected=index;
    if(previous_club!=visible_club){clear_icon_views();scroll_selected=true;card_coach_yaw=card_coach_pan=0;card_coach_zoom=1;
        if(coach_child){coach_profile_end_embedded();coach_child=false;club_home=true;office_home=office_mode;}}
    else if(was_coach&&has_coach()&&!visible.empty())selected=(int)visible.size();
    if(!group_mode&&!coach_selected()) {
        const auto*info=fifa_player::presentation_pose_find(pose_id);
        if(!info||!(info->modes&fifa_player::PoseIndividual))random_individual_pose();
    }
    lineup.clear();int keepers=0;
    for(const auto&r:visible)if(r.squad_position>=0&&r.squad_position<28) {
        lineup.push_back(r.player_id);if(r.squad_position==0)++keepers;
    }
    lineup_valid=lineup.size()==11&&keepers==1;
    if(!lineup_valid)lineup.clear(); /* Do not substitute the first eleven or best-rated players. */
    if(logger) {
        char message[256];sprintf_s(message,"Club3D roster club=%d rows=%zu fieldRows=%zu keepers=%d validXI=%d source=live_teamplayerlinks",
            visible_club,visible.size(),lineup_valid?lineup.size():size_t(std::count_if(visible.begin(),visible.end(),[](const auto&r){return r.squad_position>=0&&r.squad_position<28;})),keepers,lineup_valid);
        logger(message);
        for(const auto&r:visible)if(r.squad_position>=0&&r.squad_position<28) {
            sprintf_s(message,"Club3D XI club=%d position=%d player=%d shirt=%d captain=%d",r.team_id,r.squad_position,r.player_id,r.number,r.captain);
            logger(message);
        }
    }
    queue_preview();
}
const char *position(int p) {
    static const char*names[]={"GOL","LIB","ALA D","LD","ZAG D","ZAG","ZAG E","LE","ALA E",
        "VOL D","VOL","VOL E","MD","MC D","MC","MC E","ME","MEI D","MEI","MEI E",
        "SA D","SA","SA E","PD","ATA D","ATA","ATA E","PE"};
    return p>=0&&p<28?names[p]:"-";
}
void opened(void *context) {
    if(!embedded_club)InterlockedExchange(&refresh_requested,1);
    visible_revision=~0u;requested_player=0;next_step=GetTickCount()+250;
    group_mode=!database_profile_child;previous_buttons=0;pose_id=group_pose_id=1;press_pose_id=205;
    office_mode=office_home=context==(void*)3;office_focus=0;office_menu=-1;office_item=office_slide=office_main_page=office_training_row=0;office_repeat=0;office_match_card={};
    office_last_advance=GetTickCount();office_transition_started=office_last_advance;office_transition_from=-1;office_transition_direction=1;
    club_home=!database_profile_child&&(context==nullptr||office_mode);coach_child=from_home=false;uniforms_open=false;full_squad_mode=context==(void*)4;card_focus=0;card_coach_yaw=card_coach_pan=0;card_coach_zoom=1;card_repeat=0;
    mouse_card_press=-1;mouse_card_travel=0;
    room_kind=context==(void*)1?fifa_player::RoomPressPair:full_squad_mode?fifa_player::RoomFullSquadPhoto:fifa_player::RoomPhoto;press_player=0;press_resample=context==(void*)1;
    int requested_room=(int)InterlockedExchange(&web_room_requested,0);
    if(context==(void*)1&&(requested_room==1||requested_room==2)){room_kind=requested_room==1?fifa_player::RoomPress:fifa_player::RoomDressing;press_resample=false;}
    back_ready_at=input_ready_at=GetTickCount()+250;
    sync_rows();if(database_profile_child){group_mode=false;selected=0;room_kind=fifa_player::RoomPhoto;random_individual_pose();queue_preview();yaw=-.12f;}
    if(logger)logger(database_profile_child?"Club3D: generic player profile opened from database search":office_mode?"Club3D: office opened; owned current-club scenes, fixed cameras":context==(void*)1?"Club3D: press conference opened; sample from current club only":"Club3D: opened by native Clube card action");
}
void closed(void *) {
    coach_profile_end_embedded();coach_child=false;
    full_squad_mode=false;uniforms_open=false;
    {std::lock_guard<std::mutex>guard(lock);request_rows.clear();request_roster.clear();++request_serial;ready_model.reset();ready_icons.reset();}
    clear_icon_views();
    requested_player=0;renderer.clear();visible.clear();lineup.clear();loading=false;
    html_preview_source.reset();
    if(database_profile_child){database_profile_child=false;embedded_club=false;external_rows.clear();external_team.clear();external_club=0;visible_revision=~0u;}
    if(logger)logger("Club3D: closed; shared modal input release delay active");
}
void html_office_open(void *) {
    opened((void*)3);
    html_preview_source.reset();
    fifa_webview::clear_scene_preview();
    fifa_webview::show();
}
std::string html_json_text(const char*text){std::string out="\"";if(text)for(auto*p=text;*p;++p){if(*p=='"'||*p=='\\')out+='\\';if((unsigned char)*p>=32)out+=*p;else out+=' ';}return out+"\"";}
void html_office_draw(void *) {
    static ULONGLONG last_web_context=0;
    const ULONGLONG web_now=GetTickCount64();
    if(fifa_webview::status()==1&&web_now-last_web_context<500
        &&!InterlockedCompareExchange(&web_room_requested,0,0)
        &&!InterlockedCompareExchange(&web_player_requested,0,0)
        &&!InterlockedCompareExchange(&web_pose_requested,0,0))return;
    last_web_context=web_now;
    int requested=(int)InterlockedExchange(&web_room_requested,0);
    if(requested>0){group_mode=true;room_kind=requested==1?fifa_player::RoomPress:requested==2?fifa_player::RoomDressing:requested==3?fifa_player::RoomGym:fifa_player::RoomTraining;html_preview_source.reset();fifa_webview::clear_scene_preview();}
    if(fifa_webview::page_is_home()&&(!group_mode||room_kind!=fifa_player::RoomPhoto)){group_mode=true;room_kind=fifa_player::RoomPhoto;queue_preview();html_preview_source.reset();fifa_webview::clear_scene_preview();}
    sync_rows();sync_icons();
    int wanted=(int)InterlockedExchange(&web_player_requested,0);
    if(wanted>0){html_player_available=false;auto found=std::find_if(visible.begin(),visible.end(),[&](const auto&r){return r.player_id==wanted;});if(found!=visible.end()){html_player_available=true;group_mode=false;selected=(int)(found-visible.begin());room_kind=fifa_player::RoomPhoto;random_individual_pose();html_preview_source.reset();fifa_webview::clear_scene_preview();}}
    int wanted_pose=(int)InterlockedExchange(&web_pose_requested,0);if(wanted_pose>=101&&wanted_pose<=114&&html_player_available&&!group_mode){pose_id=(unsigned)wanted_pose;html_preview_source.reset();}
    if(fifa_webview::status()!=1){
        screen_visuals::begin_fullscreen("Experiência Nova##WebViewStatus",ImGuiWindowFlags_NoDecoration);
        ImGui::TextUnformatted(fifa_webview::status()<0?"WebView2 indisponível. Confira o runtime e WebView2Loader.dll.":"Abrindo Experiência Nova...");
        ImGui::End();return;
    }
    std::string data="{\"players\":[";
    const char*positions[]={"GOL","LIB","ALA D","LD","ZAG D","ZAG","ZAG E","LE","ALA E","VOL D","VOL","VOL E","MD","MC D","MC","MC E","ME","MEI D","MEI","MEI E","SA D","SA","SA E","PD","ATA D","ATA","ATA E","PE"};
    for(size_t i=0;i<visible.size();++i){auto&r=visible[i];if(i)data+=",";data+="{\"id\":"+std::to_string(r.player_id)+",\"name\":"+html_json_text(utf8(r.name).c_str())+",\"overall\":"+std::to_string(r.overall)+",\"position\":"+html_json_text(r.position>=0&&r.position<28?positions[r.position]:"JOG")+",\"number\":"+std::to_string(r.number)+",\"height\":"+std::to_string(r.height)+",\"weight\":"+std::to_string(r.weight)+",\"potential\":"+std::to_string(r.attributes[33]);
        if(visible_icons&&visible_icons->club==visible_club){auto age=visible_icons->ages.find(r.player_id);if(age!=visible_icons->ages.end())data+=",\"age\":"+std::to_string(age->second);auto foot=visible_icons->feet.find(r.player_id);if(foot!=visible_icons->feet.end())data+=",\"foot\":"+std::to_string(foot->second);}
        data+=",\"positionId\":"+std::to_string(r.position)+",\"secondaryPositionIds\":[";if(r.secondary_positions_valid)for(int sp=0;sp<3;++sp){if(sp)data+=",";data+=std::to_string(r.secondary_positions[sp]);}data+="]";if(visible_icons){auto nation=visible_icons->nations.find(r.player_id);if(nation!=visible_icons->nations.end())data+=",\"nationId\":"+std::to_string(nation->second);}
        data+=",\"squadPosition\":"+std::to_string(r.squad_position);
        data+=",\"captain\":"+std::string(r.captain?"true":"false");
        if(r.career_data_valid){data+=",\"weeklyWage\":"+std::to_string(r.weekly_wage)+",\"retiring\":"+std::to_string(r.retiring)+",\"birthDate\":"+html_json_text(club_profile::raw_date_label(r.birthdate_raw).c_str())+",\"joinDate\":"+html_json_text(club_profile::raw_date_label(r.join_team_date_raw).c_str());}
        auto stats=fifa_player::profile_competitions(r.player_id,visible_club);if(stats.available){data+=",\"competitions\":[";for(size_t k=0;k<stats.rows.size();++k){auto&v=stats.rows[k];if(k)data+=",";std::string label; if(visible_icons)for(auto&identity:visible_icons->competition_names)if(identity.root==v.root){label=identity.name;break;}data+="{\"root\":"+std::to_string(v.root)+",\"asset\":"+std::to_string(v.asset)+",\"name\":"+html_json_text(label.c_str())+",\"games\":"+std::to_string(v.games)+",\"goals\":"+std::to_string(v.goals)+",\"assists\":"+std::to_string(v.assists)+",\"cleanSheets\":"+((v.valid&1)?std::to_string(v.clean_sheets):"null")+",\"average\":"+std::to_string(player_competitions::average(v))+"}";}data+="]";}
        data+=",\"attributes\":{";for(size_t j=0;j<CLUB_PLAYER_ATTRIBUTE_COUNT;++j){if(j)data+=",";data+=html_json_text(fields[j])+":"+std::to_string(r.attributes[j]);}data+="}}";}
    data+="],\"news\":[";CareerNewsItem items[CAREER_NEWS_CAPACITY]={};size_t count=career_news_copy(visible_club,items,CAREER_NEWS_CAPACITY);
    for(size_t i=0;i<count;++i){if(i)data+=",";data+="{\"title\":"+html_json_text(items[i].title)+",\"subtitle\":"+html_json_text(items[i].subtitle)+"}";}data+="]";
    if(visible_icons&&visible_icons->club==visible_club){auto&card=visible_icons->card;std::string name=card.context.name;{std::lock_guard<std::mutex>guard(career_news_lock);if(career_news_manager.valid&&career_news_manager.club_id==visible_club)name=career_news_manager.name;}data+=",\"coach\":{\"name\":"+html_json_text(name.c_str())+",\"country\":"+html_json_text(card.nationality_name.c_str())+",\"nationId\":"+std::to_string(card.context.nationality)+",\"reputation\":"+std::to_string(coach_profile::reputation_score(card.context))+",\"confidence\":"+std::to_string(card.context.confidence)+",\"weeklyWage\":"+std::to_string(card.context.wage)+",\"league\":"+html_json_text(card.league_name.c_str())+"}";}
    if(!visible.empty()){auto competitions=fifa_player::profile_competitions(visible.front().player_id,visible_club);if(competitions.available){data+=",\"competitions\":[";for(size_t k=0;k<competitions.rows.size();++k){auto&entry=competitions.rows[k];if(k)data+=",";std::string name; if(visible_icons)for(auto&identity:visible_icons->competition_names)if(identity.root==entry.root){name=identity.name;break;}data+="{\"root\":"+std::to_string(entry.root)+",\"asset\":"+std::to_string(entry.asset)+",\"name\":"+html_json_text(name.c_str())+",\"recorded\":false}";}data+="]";}}
    {CareerNewsManagerFacts manager={};{std::lock_guard<std::mutex>guard(career_news_lock);if(career_news_manager.club_id==visible_club)manager=career_news_manager;}
     if(manager.valid&&manager.season_record_valid)data+=" ,\"season\":{\"games\":"+std::to_string(manager.games)+",\"wins\":"+std::to_string(manager.wins)+",\"draws\":"+std::to_string(manager.draws)+",\"losses\":"+std::to_string(manager.losses)+",\"goalsFor\":"+std::to_string(manager.goals_for)+",\"goalsAgainst\":"+std::to_string(manager.goals_against)+"}";
     if(manager.valid&&manager.confidence>=0)data+=",\"boardConfidence\":"+std::to_string(manager.confidence);}
    auto identity=[&](int asset,int root_id){std::string name;if(visible_icons){for(const auto&item:visible_icons->competition_names)if(item.asset==asset||item.root==root_id){name=item.name;break;}if(name.empty()&&visible_icons->office_next_match.competition_asset==asset)name=utf8(visible_icons->office_next_competition_name.c_str());}return name.empty()?std::string("Competição ")+std::to_string(asset):name;};
    auto match_json=[&](const CareerWebMatch&m){return std::string("{\"home\":")+std::to_string(m.home)+",\"away\":"+std::to_string(m.away)+",\"asset\":"+std::to_string(m.asset)+",\"competition\":"+html_json_text(identity(m.asset,0).c_str())+",\"homeName\":"+html_json_text(utf8(m.home_name).c_str())+",\"awayName\":"+html_json_text(utf8(m.away_name).c_str())+",\"date\":"+html_json_text(m.date)+",\"time\":"+html_json_text(m.time)+",\"score\":"+html_json_text(m.score)+"}";};
    auto dashboard=std::make_unique<CareerWebDashboard>();if(career_web_dashboard_copy(visible_club,dashboard.get())){auto&w=*dashboard;CareerTransferUiContext calendar_context={};BOOL calendar_context_valid=career_operations_get_transfer_context(&calendar_context);data+=",\"webDashboard\":{\"current\":"+std::to_string(w.current)+",\"careerDate\":"+std::to_string(w.date)+",\"windowEndsValid\":"+std::string(calendar_context_valid&&calendar_context.window_ends_valid?"true":"false")+",\"windowStart1\":"+std::to_string(calendar_context.first_window_start_mmdd)+",\"windowEnd1\":"+std::to_string(calendar_context.first_window_end_mmdd)+",\"windowStart2\":"+std::to_string(calendar_context.second_window_start_mmdd)+",\"windowEnd2\":"+std::to_string(calendar_context.second_window_end_mmdd)+",\"competitions\":[";
      for(size_t i=0;i<std::min(w.count,size_t(5));++i){auto&e=w.competitions[i];if(i)data+=",";data+="{\"root\":"+std::to_string(e.root)+",\"asset\":"+std::to_string(e.asset)+",\"name\":"+html_json_text(identity(e.asset,e.root).c_str())+",\"table\":[";
       for(size_t j=0;j<std::min(e.row_count,size_t(20));++j){auto&r=e.rows[j];if(j)data+=",";data+="{\"team\":"+std::to_string(r.team)+",\"name\":"+html_json_text(utf8(r.name).c_str())+",\"rank\":"+std::to_string(r.rank)+",\"games\":"+std::to_string(r.games)+",\"wins\":"+std::to_string(r.wins)+",\"draws\":"+std::to_string(r.draws)+",\"losses\":"+std::to_string(r.losses)+",\"goalsFor\":"+std::to_string(r.goals_for)+",\"goalsAgainst\":"+std::to_string(r.goals_against)+",\"points\":"+std::to_string(r.points)+"}";}data+="]";
       for(int k=0;k<2;++k){data+=k?",\"assists\":[":",\"goals\":[";auto*rows=k?e.assists:e.goals;size_t count=k?e.assist_count:e.goal_count;for(size_t j=0;j<std::min(count,size_t(5));++j){auto&r=rows[j];if(j)data+=",";data+="{\"player\":"+std::to_string(r.player)+",\"club\":"+std::to_string(r.club)+",\"value\":"+std::to_string(r.value)+",\"name\":"+html_json_text(utf8(r.name).c_str())+"}";}data+="]";}data+="}";}data+="]";
      for(int k=0;k<2;++k){data+=k?",\"previous\":[":",\"upcoming\":[";auto*matches=k?w.previous:w.upcoming;size_t count=k?w.previous_count:w.upcoming_count;for(size_t j=0;j<std::min(count,size_t(10));++j){if(j)data+=",";data+=match_json(matches[j]);}data+="]";}
      if(w.season_valid){auto record_json=[](const CareerWebRecord&r){return std::string("{\"games\":")+std::to_string(r.games)+",\"wins\":"+std::to_string(r.wins)+",\"draws\":"+std::to_string(r.draws)+",\"losses\":"+std::to_string(r.losses)+",\"goalsFor\":"+std::to_string(r.goals_for)+",\"goalsAgainst\":"+std::to_string(r.goals_against)+",\"points\":"+std::to_string(r.points)+"}";};auto total=record_json(w.season);total.pop_back();data+=",\"season\":"+total+",\"home\":"+record_json(w.home_record)+",\"away\":"+record_json(w.away_record)+"}";}
      const char*metric_keys[]={"goals","assists","minutes","yellow","red"};data+=",\"clubStats\":{";for(int k=0;k<5;++k){if(k)data+=",";data+=html_json_text(metric_keys[k])+":"+"[";for(size_t j=0;j<std::min(w.metric_counts[k],size_t(5));++j){auto&r=w.metrics[k][j];if(j)data+=",";data+="{\"player\":"+std::to_string(r.player)+",\"club\":"+std::to_string(r.club)+",\"value\":"+std::to_string(r.value)+",\"name\":"+html_json_text(utf8(r.name).c_str())+"}";}data+="]";}data+="},\"injuries\":[";for(size_t j=0;j<std::min(w.injury_count,size_t(10));++j){auto&r=w.injuries[j];if(j)data+=",";data+="{\"player\":"+std::to_string(r.player)+",\"name\":"+html_json_text(utf8(r.name).c_str())+",\"injury\":"+html_json_text(utf8(r.injury).c_str())+",\"returnLabel\":"+html_json_text(utf8(r.return_label).c_str())+"}";}data+="]}";}
    {CareerNextMatchFacts next={};if(career_next_match_copy(visible_club,&next)&&next.valid){char date[24]={},time[12]={};sprintf_s(date,"%02d/%02d/%04d",next.match_date%100,next.match_date/100%100,next.match_date/10000);if(next.match_time>=0)sprintf_s(time,"%02d:%02d",next.match_time/100,next.match_time%100);
     data+=",\"nextMatch\":{\"home\":"+std::to_string(next.home_team)+",\"away\":"+std::to_string(next.away_team)+",\"homeName\":"+html_json_text(utf8(next.home_name).c_str())+",\"awayName\":"+html_json_text(utf8(next.away_name).c_str())+",\"date\":"+html_json_text(date)+",\"time\":"+html_json_text(time)+",\"asset\":"+std::to_string(next.competition_asset)+",\"competition\":"+html_json_text(identity(next.competition_asset,0).c_str())+",\"stadium\":"+html_json_text(utf8(next.stadium).c_str())+",\"capacity\":"+std::to_string(dashboard->next_fixture==next.fixture?dashboard->capacity:-1)+",\"attendance\":"+std::to_string(dashboard->next_fixture==next.fixture?dashboard->attendance:-1)+"}";}}
    data+="}";
    std::string current_name=utf8(visible_team.c_str());fifa_webview::set_career_context(visible_club,current_name.c_str(),(int)visible.size(),lineup_valid,data.c_str());
    if(!fifa_webview::page_is_home())return;
    if(fifa_webview::page_is_player()&&!html_player_available)return;
    if(!fifa_webview::page_is_player()&&!lineup_valid)return;
    std::shared_ptr<const fifa_player::Model>model;{std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial)model=ready_model;}
    if(!model||model==html_preview_source)return;
    auto scene=std::make_shared<fifa_player::Model>(*model);
    if(fifa_webview::page_is_home()){if(scene->player_count!=11)return;scene->room=fifa_player::RoomOfficeLineup;}
    if(!office_lineup_renderer.model(scene)||!office_lineup_renderer.render(fifa_webview::page_is_player()?900:1280,fifa_webview::page_is_player()?1100:720,0,1.f,false,0,0,fifa_webview::page_is_player()))return;
    if(fifa_webview::publish_scene(office_lineup_renderer.image()))html_preview_source=model;
}
void html_office_close(void *) {fifa_webview::hide();closed(nullptr);}
BOOL html_office_back(void *) {return FALSE;}
void open_home_card(int index){
    if(index==0){if(!visible_icons||!visible_icons->card.context.valid)return;
        if(coach_profile_begin_embedded(visible_icons->card)){coach_child=true;club_home=false;office_home=false;}}
    else if(index==1){club_home=false;office_home=false;uniforms_open=true;queue_preview();}
    else if(index==2){uniforms_open=false;club_home=false;office_home=false;from_home=true;full_squad_mode=false;group_mode=true;room_kind=fifa_player::RoomPhoto;selected=0;scroll_selected=true;queue_preview();}
    back_ready_at=input_ready_at=GetTickCount()+250;
}
std::vector<std::string> club_kit_labels(const std::vector<fifa_player::KitThumbnail>&kits){
    std::unordered_map<int,int>field_numbers,keeper_numbers;int fields=0,keepers=0;std::vector<std::string>labels;labels.reserve(kits.size());
    for(const auto&kit:kits){auto&numbers=kit.goalkeeper?keeper_numbers:field_numbers;auto found=numbers.find(kit.type);
        if(found==numbers.end())found=numbers.emplace(kit.type,kit.goalkeeper?++keepers:++fields).first;
        std::string label=(kit.goalkeeper?"Goleiro ":"Uniforme ")+std::to_string(found->second);
        if(kit.variant>0)label+=" · variação "+std::to_string(kit.variant);labels.push_back(std::move(label));}
    return labels;
}
void draw_uniforms(){
    screen_visuals::LightTheme theme;
    screen_visuals::begin_fullscreen("Uniformes##ClubKits",ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.35f);ImGui::TextUnformatted("Uniformes do clube");ImGui::SetWindowFontScale(1);
    if(crest_view)player_profile::identity_line(crest_view,24,utf8(visible_team.c_str()).c_str());else ImGui::TextUnformatted(utf8(visible_team.c_str()).c_str());
    ImGui::Spacing();
    const bool current=visible_icons&&visible_icons->club==visible_club;size_t count=current?visible_icons->kits.size():0;
    if(current)ImGui::Text("%zu modelos encontrados",count);else ImGui::TextUnformatted("Carregando uniformes...");
    ImGui::Separator();float footer=38.f,grid_height=std::max(160.f,ImGui::GetContentRegionAvail().y-footer);
    ImGui::BeginChild("Catálogo de uniformes",{0,grid_height},false,ImGuiWindowFlags_NoNavInputs);
    if(current&&count){
        auto labels=club_kit_labels(visible_icons->kits);float avail=ImGui::GetContentRegionAvail().x,gap=12.f;
        int columns=std::clamp((int)((avail+gap)/250.f),1,5);float tile_width=(avail-gap*(columns-1))/columns,tile_height=296.f;
        for(size_t i=0;i<count;++i){ImGui::PushID((int)i);
            ImGui::BeginChild("KitTile",{tile_width,tile_height},true,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse);
            ImGui::SetWindowFontScale(1.05f);ImGui::TextWrapped("%s",labels[i].c_str());ImGui::SetWindowFontScale(1);
            ImGui::TextDisabled(visible_icons->kits[i].goalkeeper?"GOLEIRO":"LINHA");ImGui::Spacing();
            ID3D11ShaderResourceView*view=i<kit_views.size()?kit_views[i]:nullptr;const auto&texture=visible_icons->kits[i].image;
            if(view&&texture.width&&texture.height){float scale=std::min((tile_width-32.f)/texture.width,184.f/texture.height);
                ImVec2 image_size={texture.width*scale,texture.height*scale};ImGui::SetCursorPosX(std::max(0.f,(ImGui::GetContentRegionAvail().x-image_size.x)*.5f));
                ImGui::Image((ImTextureID)(intptr_t)view,image_size);}
            else {float image_width=std::min(tile_width-32.f,184.f);auto*dl=ImGui::GetWindowDrawList();ImVec2 p=ImGui::GetCursorScreenPos();
                ImGui::Dummy({image_width,150});dl->AddText({p.x+8,p.y+64},IM_COL32(93,116,128,255),"Imagem indisponível");}
            if(visible_icons->kits[i].variant>0)ImGui::TextDisabled("Variação %d",visible_icons->kits[i].variant);
            ImGui::EndChild();ImGui::PopID();if((i+1)%columns)ImGui::SameLine(0,gap);
        }
    }else if(current)ImGui::TextWrapped("Nenhum arquivo de uniforme foi encontrado para este clube.");
    ImGui::EndChild();
    if(ImGui::Button("Voltar à tela do clube (B / Esc)")){uniforms_open=false;club_home=true;queue_preview();input_ready_at=GetTickCount()+150;}
    ImGui::End();
}
void draw_home(const XINPUT_STATE&pad,WORD pressed,bool ready){
    screen_visuals::LightTheme theme;theme.color(ImGuiCol_Text,player_profile::ink());auto&io=ImGui::GetIO();DWORD now=GetTickCount();
    int step=0,activate=-1;
    if(ready){
        if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(pressed&XINPUT_GAMEPAD_DPAD_LEFT))step=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(pressed&XINPUT_GAMEPAD_DPAD_RIGHT))step=1;
        if(ImGui::IsKeyPressed(ImGuiKey_Tab))step=1;
        if(!step&&abs(pad.Gamepad.sThumbLX)>16000&&(LONG)(now-card_repeat)>=0){step=pad.Gamepad.sThumbLX>0?1:-1;card_repeat=now+180;}
        if(step)card_focus=(card_focus+step+3)%3;
        if(ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space)||(pressed&XINPUT_GAMEPAD_A))activate=card_focus;
    }
    ImGui::SetNextWindowPos({io.DisplaySize.x*.035f,io.DisplaySize.y*.045f});ImGui::SetNextWindowSize({io.DisplaySize.x*.93f,io.DisplaySize.y*.91f});
    ImGui::Begin("Meu clube##ClubHome",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.4f);ImGui::TextUnformatted(embedded_club?"Informações do clube":"Meu clube");ImGui::SetWindowFontScale(1);
    if(crest_view)player_profile::identity_line(crest_view,24,utf8(visible_team.c_str()).c_str());else ImGui::TextUnformatted(utf8(visible_team.c_str()).c_str());
    ImGui::Spacing();float width=ImGui::GetContentRegionAvail().x,height=std::max(100.f,ImGui::GetContentRegionAvail().y-50);
    float card_gap=12.f,card_space=std::max(120.f,width-card_gap*3);
    float card_widths[3]={card_space*.23f,card_space*.28f,card_space*.49f};
    std::shared_ptr<const fifa_player::Model>team_model;{std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial)team_model=ready_model;}
    ImVec2 origin=ImGui::GetCursorScreenPos();
    float card_x=origin.x;
    for(int i=0;i<3;++i){ImGui::SetCursorScreenPos({card_x,origin.y});ImGui::PushID(i);ImVec2 at=ImGui::GetCursorScreenPos();
        card_centers[i]={at.x+card_widths[i]*.5f,at.y+height*.5f};
        ImGui::Dummy({card_widths[i],height});bool hovered=ImGui::IsMouseHoveringRect(at,{at.x+card_widths[i],at.y+height});
        // Children contain the images, so parent InvisibleButton cannot own
        // their hover. One explicit press/release gesture covers the full card.
        if(hovered&&ready&&ImGui::IsMouseClicked(0)){mouse_card_press=i;mouse_card_travel=0;card_focus=i;}
        if(mouse_card_press<0&&hovered&&ready&&(io.MouseDelta.x||io.MouseDelta.y||io.MouseWheel))card_focus=i;
        if(mouse_card_press==i&&ImGui::IsMouseDown(0)){mouse_card_travel+=fabsf(io.MouseDelta.x)+fabsf(io.MouseDelta.y);card_focus=i;}
        if(mouse_card_press==i&&ImGui::IsMouseReleased(0)){if(hovered&&ready&&mouse_card_travel<=6)activate=i;mouse_card_press=-1;}
        bool focused=card_focus==i;auto*d=ImGui::GetWindowDrawList();
        d->AddRectFilled(at,{at.x+card_widths[i],at.y+height},IM_COL32(250,252,254,255),8);
        d->AddRect(at,{at.x+card_widths[i],at.y+height},focused?IM_COL32(9,103,171,255):IM_COL32(190,210,224,255),8,0,focused?3.f:1.f);
        auto after=ImGui::GetCursorScreenPos();ImGui::SetCursorScreenPos({at.x+12,at.y+12});
        ImGui::BeginChild("Conteúdo",{card_widths[i]-24,height-24},false,ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse);
        if(i==1){
            bool current=visible_icons&&visible_icons->club==visible_club;size_t kit_count=current?visible_icons->kits.size():0;
            ImGui::SetWindowFontScale(1.12f);ImGui::TextUnformatted("Uniformes");ImGui::SetWindowFontScale(1);
            if(current)ImGui::TextDisabled("%zu modelos disponíveis",kit_count);else ImGui::TextDisabled("Carregando kits...");
            ImGui::Spacing();ImVec2 preview_at=ImGui::GetCursorScreenPos();float preview_width=ImGui::GetContentRegionAvail().x;
            float preview_height=std::clamp(ImGui::GetContentRegionAvail().y*.54f,150.f,235.f);ImGui::Dummy({preview_width,preview_height});
            auto*preview_dl=ImGui::GetWindowDrawList();preview_dl->AddRectFilled(preview_at,{preview_at.x+preview_width,preview_at.y+preview_height},IM_COL32(238,245,250,255),6);
            if(!current)preview_dl->AddText(nullptr,0,{preview_at.x+12,preview_at.y+preview_height*.48f},IM_COL32(57,100,133,255),"Carregando uniformes...");
            else if(!kit_count)preview_dl->AddText(nullptr,0,{preview_at.x+12,preview_at.y+preview_height*.48f},IM_COL32(57,100,133,255),"Nenhum kit encontrado para este clube.");
            else {
                auto labels=club_kit_labels(visible_icons->kits);std::vector<size_t>previews;std::vector<int>shown_field_types;bool keeper_added=false;
                for(size_t k=0;k<kit_count;++k){if(visible_icons->kits[k].goalkeeper){if(!keeper_added){previews.push_back(k);keeper_added=true;}}
                    else if(shown_field_types.size()<2&&std::find(shown_field_types.begin(),shown_field_types.end(),visible_icons->kits[k].type)==shown_field_types.end()){
                        previews.push_back(k);shown_field_types.push_back(visible_icons->kits[k].type);}}
                for(size_t k=0;k<kit_count&&previews.size()<3;++k)if(std::find(previews.begin(),previews.end(),k)==previews.end())previews.push_back(k);
                float tile_width=preview_width/std::max<size_t>(1,previews.size()),max_image_h=preview_height-48.f;
                for(size_t n=0;n<previews.size();++n){size_t k=previews[n];if(k>=kit_views.size()||!kit_views[k])continue;
                    const auto&texture=visible_icons->kits[k].image;if(!texture.width||!texture.height)continue;
                    float scale=std::min((tile_width-12.f)/texture.width,max_image_h/texture.height);ImVec2 image_size={texture.width*scale,texture.height*scale};
                    float image_x=preview_at.x+n*tile_width+(tile_width-image_size.x)*.5f,image_y=preview_at.y+8.f;
                    preview_dl->AddImage((ImTextureID)(intptr_t)kit_views[k],{image_x,image_y},{image_x+image_size.x,image_y+image_size.y});
                    float label_y=preview_at.y+preview_height-27.f;preview_dl->PushClipRect({preview_at.x+n*tile_width,label_y},{preview_at.x+(n+1)*tile_width,label_y+20},true);
                    ImVec2 text_size=ImGui::CalcTextSize(labels[k].c_str());preview_dl->AddText({preview_at.x+n*tile_width+(tile_width-text_size.x)*.5f,label_y},IM_COL32(47,75,93,255),labels[k].c_str());preview_dl->PopClipRect();}
            }
            ImGui::Spacing();ImGui::TextUnformatted("A / Enter: ver todos os uniformes");
            ImGui::EndChild();ImGui::SetCursorScreenPos(after);ImGui::PopID();card_x+=card_widths[i]+card_gap;continue;
        }
        if(i==0){
            if(coach_card_photo&&visible_icons){const auto&p=visible_icons->card.photo;float w=36,h=36;if(p.width>p.height)h=w*p.height/p.width;else if(p.height)w=h*p.width/p.height;
                ImGui::Image((ImTextureID)(intptr_t)coach_card_photo,{w,h});}
            else {auto p=ImGui::GetCursorScreenPos();ImGui::Dummy({36,36});auto*dl=ImGui::GetWindowDrawList();dl->AddCircleFilled({p.x+18,p.y+10},7,IM_COL32(155,181,199,255));dl->AddRectFilled({p.x+7,p.y+20},{p.x+29,p.y+35},IM_COL32(155,181,199,255),8);}
            ImGui::SameLine();ImGui::BeginGroup();ImGui::SetWindowFontScale(1.0f);
            ImGui::TextWrapped("%s",visible_icons?utf8(visible_icons->card.context.name).c_str():"Treinador");ImGui::SetWindowFontScale(.82f);
            if(coach_card_flag&&visible_icons&&!visible_icons->card.nationality_name.empty())
                player_profile::identity_line(coach_card_flag,20,visible_icons->card.nationality_name.c_str());
            else if(visible_icons&&!visible_icons->card.league_name.empty())ImGui::TextWrapped("Liga: %s",utf8(visible_icons->card.league_name.c_str()).c_str());
            else ImGui::TextWrapped("Clube: %s",utf8(visible_team.c_str()).c_str());
            ImGui::SetWindowFontScale(1);ImGui::EndGroup();
        }else{ImGui::SetWindowFontScale(1.25f);ImGui::TextUnformatted(embedded_club?"Elenco":"Meu elenco");ImGui::SetWindowFontScale(1);
            ImGui::TextUnformatted(lineup_valid?"Onze titulares":"Titulares indisponíveis");ImGui::Dummy({0,20});}
        ImGui::Spacing();auto stage_at=ImGui::GetCursorScreenPos();ImVec2 stage={ImGui::GetContentRegionAvail().x,std::max(50.f,ImGui::GetContentRegionAvail().y-36)};
        if(ready&&focused){float dt=std::clamp(io.DeltaTime,0.f,.05f),triggers=(std::max(0,int(pad.Gamepad.bRightTrigger)-30)-std::max(0,int(pad.Gamepad.bLeftTrigger)-30))/225.f;
            float wheel=hovered?io.MouseWheel:0;if(ImGui::IsKeyDown(ImGuiKey_Equal))wheel+=dt*5;if(ImGui::IsKeyDown(ImGuiKey_Minus))wheel-=dt*5;
            bool drag=hovered&&ImGui::IsMouseDragging(0)&&io.MousePos.y>=stage_at.y;
            if(i==0){card_coach_zoom=std::clamp(card_coach_zoom+triggers*dt*.7f+wheel*.08f,.65f,2.f);
                card_coach_yaw+=player_profile::stick(pad.Gamepad.sThumbRX)*dt*1.7f+(drag?io.MouseDelta.x*.012f:0);
                card_coach_pan=std::clamp(card_coach_pan+player_profile::stick(pad.Gamepad.sThumbRY)*dt*.18f-(drag?io.MouseDelta.y*.001f:0),-.20f,.20f);
                if(ImGui::IsKeyDown(ImGuiKey_Q))card_coach_yaw-=dt;if(ImGui::IsKeyDown(ImGuiKey_E))card_coach_yaw+=dt;
                if(ImGui::IsKeyPressed(ImGuiKey_R)||(pressed&XINPUT_GAMEPAD_RIGHT_THUMB)){card_coach_zoom=1;card_coach_yaw=card_coach_pan=0;}}
            else {zoom=std::clamp(zoom+triggers*dt*.7f+wheel*.08f,.65f,2.f);
                photo_pan_x=std::clamp(photo_pan_x+player_profile::stick(pad.Gamepad.sThumbRX)*dt*.28f+(drag?io.MouseDelta.x/stage.x:0),-.45f,.45f);
                photo_pan_y=std::clamp(photo_pan_y+player_profile::stick(pad.Gamepad.sThumbRY)*dt*.28f-(drag?io.MouseDelta.y/stage.y:0),-.35f,.35f);
                if(ImGui::IsKeyPressed(ImGuiKey_R)||(pressed&XINPUT_GAMEPAD_RIGHT_THUMB)){zoom=1;photo_pan_x=photo_pan_y=0;}}
        }
        bool rendered=false;
        if(i==0){auto model=visible_icons?visible_icons->card.model:nullptr;
            auto*dl=ImGui::GetWindowDrawList();dl->AddRectFilled(stage_at,{stage_at.x+stage.x,stage_at.y+stage.y},IM_COL32(238,245,250,255),6);
            rendered=model&&coach_card_renderer.model(model)&&coach_card_renderer.render((UINT)stage.x,(UINT)stage.y,card_coach_yaw,card_coach_zoom,true,0,card_coach_pan,true,.80f);
            if(rendered)ImGui::Image((ImTextureID)(intptr_t)coach_card_renderer.image(),stage);
        }else {rendered=lineup_valid&&team_model&&team_model->player_count==11&&renderer.model(team_model)&&renderer.render((UINT)stage.x,(UINT)stage.y,0,zoom,false,photo_pan_x,photo_pan_y);
            if(rendered)ImGui::Image((ImTextureID)(intptr_t)renderer.image(),stage);}
        if(!rendered){ImGui::Dummy(stage);auto*dl=ImGui::GetWindowDrawList();const char*message=!visible_icons?"Carregando...":i==0?"Modelo do técnico indisponível":lineup_valid?"Carregando elenco...":"Escalação indisponível";
            dl->AddText(nullptr,0,{stage_at.x+16,stage_at.y+stage.y*.45f},IM_COL32(57,100,133,255),message,nullptr,stage.x-32);}
        ImGui::Spacing();ImGui::TextUnformatted(i==0?"A / Enter: perfil do técnico":"A / Enter: elenco completo");
        ImGui::EndChild();ImGui::SetCursorScreenPos(after);ImGui::PopID();
        card_x+=card_widths[i]+card_gap;
    }
    ImGui::SetCursorScreenPos({origin.x,origin.y+height+8});
    ImGui::Spacing();ImGui::SetWindowFontScale(.85f);ImGui::TextUnformatted("Esquerdo / setas / Tab: navegar entre cards | A / Enter: abrir | Direito / arraste: câmera 3D | LT/RT / roda / +/-: zoom | B/Esc: voltar");ImGui::SetWindowFontScale(1);
    if(ImGui::Button("Voltar (B/Esc)"))mod_screen_request_back();ImGui::End();
    if(activate>=0&&ready)open_home_card(activate);
}
#include "../office/my_office_view.inc"
void draw(void *) {
    sync_rows();sync_icons();ImGuiIO &io=ImGui::GetIO();
    if(coach_child){coach_profile_draw_embedded();return;}
    XINPUT_STATE pad={};bool has_pad=false;
    for(DWORD i=0;i<4;++i)if(mod_xinput_read_raw(i,&pad)==ERROR_SUCCESS){has_pad=true;break;}
    WORD pressed=pad.Gamepad.wButtons&~previous_buttons;previous_buttons=pad.Gamepad.wButtons;
    bool input_ready=(LONG)(GetTickCount()-input_ready_at)>=0;
    if(!input_ready)pressed=0;
    if(input_ready&&(ImGui::IsKeyPressed(ImGuiKey_Escape)||(pressed&XINPUT_GAMEPAD_B))){
        if(uniforms_open){uniforms_open=false;club_home=true;queue_preview();input_ready_at=GetTickCount()+150;return;}
        if(office_home&&office_menu>=0){office_close_submenu();input_ready_at=GetTickCount()+150;return;}
        mod_screen_request_back();return;
    }
    if(uniforms_open){draw_uniforms();return;}
    if(office_home){draw_office(pad,pressed,input_ready);return;}
    if(club_home){draw_home(pad,pressed,input_ready);return;}
    if(input_ready && group_mode && (ImGui::IsKeyPressed(ImGuiKey_Tab)||ImGui::IsKeyPressed(ImGuiKey_Enter)||
        (pressed&(XINPUT_GAMEPAD_A|XINPUT_GAMEPAD_Y)))){open_details(selected);pressed=0;input_ready=false;}
    else if(input_ready && !group_mode && ImGui::IsKeyPressed(ImGuiKey_Tab)){profile_state.section=1-profile_state.section;}
    if(input_ready&&group_mode&&!from_home&&!full_squad_mode&&(ImGui::IsKeyPressed(ImGuiKey_V)||(pressed&XINPUT_GAMEPAD_X))){
        room_kind=(fifa_player::ClubRoomKind)(((int)room_kind+1)%3);queue_preview();
    }
    if(input_ready&&group_mode&&is_press_room()&&(ImGui::IsKeyPressed(ImGuiKey_Q)||ImGui::IsKeyPressed(ImGuiKey_E)||(pressed&(XINPUT_GAMEPAD_LEFT_SHOULDER|XINPUT_GAMEPAD_RIGHT_SHOULDER)))){
        press_pose_id=press_pose_id==205?206:205;queue_preview();
    }
    if(input_ready&&group_mode&&room_kind==fifa_player::RoomPressPair&&(ImGui::IsKeyPressed(ImGuiKey_N)||(pressed&XINPUT_GAMEPAD_LEFT_THUMB))) {
        press_resample=true;queue_preview();
    }
    if(input_ready&&group_mode&&room_kind==fifa_player::RoomPhoto&&fifa_player::presentation_pose_count(fifa_player::PoseGroup)>1) {
        int step=0;if(ImGui::IsKeyPressed(ImGuiKey_Q)||(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER))step=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_E)||(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER))step=1;
        if(step) {
            size_t count=fifa_player::presentation_pose_count(fifa_player::PoseGroup),index=0;
            while(index<count&&fifa_player::presentation_pose_at(index,fifa_player::PoseGroup)->id!=pose_id)++index;
            pose_id=fifa_player::presentation_pose_at((index+count+step)%count,fifa_player::PoseGroup)->id;queue_preview();
        }
    }
    if(input_ready && !group_mode) {
        if((!coach_selected()||coach_poses_available())&&(ImGui::IsKeyPressed(ImGuiKey_P)||(pressed&XINPUT_GAMEPAD_X))){
            if(coach_selected()){size_t count=fifa_player::presentation_pose_count(fifa_player::PoseStandingCoach),index=0;
                while(index<count&&fifa_player::presentation_pose_at(index,fifa_player::PoseStandingCoach)->id!=pose_id)++index;
                pose_id=fifa_player::presentation_pose_at((index+1)%count,fifa_player::PoseStandingCoach)->id;
            }else random_individual_pose();queue_preview();
        }
        if(ImGui::IsKeyPressed(ImGuiKey_F)||(pressed&XINPUT_GAMEPAD_Y))portrait_mode=!portrait_mode;
        if(coach_selected()){
            if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(pressed&XINPUT_GAMEPAD_DPAD_LEFT))open_details(selected-1);
            if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(pressed&XINPUT_GAMEPAD_DPAD_RIGHT))open_details(selected+1);
        }
    }
    if(input_ready&&group_mode&&(ImGui::IsKeyPressed(ImGuiKey_R)||(pressed&XINPUT_GAMEPAD_RIGHT_THUMB))) {
        zoom=1;photo_pan_x=photo_pan_y=0;
    }
    if(!visible.empty()) {
        int step=0;
        if(group_mode&&input_ready&&ImGui::IsKeyPressed(ImGuiKey_UpArrow))step=-1;
        if(group_mode&&input_ready&&ImGui::IsKeyPressed(ImGuiKey_DownArrow))step=1;
        DWORD now=GetTickCount();
        if(group_mode&&has_pad&&input_ready && (LONG)(now-next_step)>=0) {
            if(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_UP || pad.Gamepad.sThumbLY>16000)step=-1;
            if(pad.Gamepad.wButtons&XINPUT_GAMEPAD_DPAD_DOWN || pad.Gamepad.sThumbLY< -16000)step=1;
            if(step)next_step=now+150;
        }
        if(step)select_player(selected+step);
        if(!group_mode&&!coach_selected())player_profile::input(profile_state,pad,pressed,input_ready);
        if(has_pad&&input_ready) {
            auto stick=[](SHORT value){const float dead=9000.f;
                return abs(value)<=dead?0.f:(value>0?1.f:-1.f)*(abs(value)-dead)/(32768.f-dead);};
            if(group_mode) {
                float triggers=(std::max(0,int(pad.Gamepad.bRightTrigger)-30)-std::max(0,int(pad.Gamepad.bLeftTrigger)-30))/225.f;
                zoom=std::max(.65f,std::min(2.f,zoom+triggers*io.DeltaTime*.70f));
                photo_pan_x=std::max(-.45f,std::min(.45f,photo_pan_x+stick(pad.Gamepad.sThumbRX)*io.DeltaTime*.28f));
                photo_pan_y=std::max(-.35f,std::min(.35f,photo_pan_y+stick(pad.Gamepad.sThumbRY)*io.DeltaTime*.28f));
            }else if(coach_selected()) {
                yaw+=stick(pad.Gamepad.sThumbRX)*io.DeltaTime*1.7f;
                if(coach_selected())zoom=std::max(.65f,std::min(1.5f,zoom+(pad.Gamepad.bRightTrigger-pad.Gamepad.bLeftTrigger)/255.f*io.DeltaTime*.7f));
            }
        }
    }
    ImVec4 accent(.02f,.36f,.64f,1);
    if(!visible.empty()&&visible[0].club_colors_valid) {
        unsigned rgb=!group_mode&&!coach_selected()?club_profile::theme_color(visible[0]):visible[0].club_colors[0];accent=ImVec4(((rgb>>16)&255)/255.f,((rgb>>8)&255)/255.f,(rgb&255)/255.f,1);
    }
    bool profile=!group_mode&&!coach_selected();
    std::unique_ptr<screen_visuals::LightTheme>squad_theme;if(from_home&&group_mode)squad_theme=std::make_unique<screen_visuals::LightTheme>();
    ImGui::PushStyleColor(ImGuiCol_WindowBg,profile||from_home?ImVec4(.95f,.97f,.98f,1):group_mode?ImVec4(.79f,.82f,.83f,1):ImVec4(.035f+accent.x*.07f,.035f+accent.y*.07f,.045f+accent.z*.07f,1));
    ImGui::PushStyleColor(ImGuiCol_Text,group_mode||profile?ImVec4(.15f,.23f,.25f,1):ImVec4(.94f,.95f,.96f,1));
    ImGui::PushStyleColor(ImGuiCol_Header,ImVec4(.02f,.36f,.64f,1));
    ImGui::PushStyleColor(ImGuiCol_HeaderHovered,ImVec4(.1f,.49f,.69f,1));
    ImGui::PushStyleColor(ImGuiCol_HeaderActive,ImVec4(.02f,.36f,.64f,1));
    ImGui::PushStyleColor(ImGuiCol_TitleBg,ImVec4(.67f,.76f,.82f,1));
    ImGui::PushStyleColor(ImGuiCol_TitleBgActive,ImVec4(.67f,.76f,.82f,1));
    const char*window_name=group_mode?(full_squad_mode?"Time completo — foto oficial##FullSquad":from_home?"Elenco completo##ClubPlayers":room_kind==fifa_player::RoomPressPair?"Coletiva - treinador e jogador##ClubPlayers":"Clube - meus 11 jogadores##ClubPlayers"):coach_selected()?"Treinador - detalhes (somente leitura)##ClubPlayers":"Perfil de jogador##ClubPlayers";
    bool full_screen=profile||(group_mode&&(from_home||full_squad_mode));
    ImGuiWindowFlags flags=ImGuiWindowFlags_NoCollapse|ImGuiWindowFlags_NoNavInputs;
    if(profile||full_screen)flags|=ImGuiWindowFlags_NoTitleBar;
    bool open;
    if(full_screen)open=screen_visuals::begin_fullscreen(window_name,flags);
    else {
        ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x*.035f,io.DisplaySize.y*.045f));
        ImGui::SetNextWindowSize(ImVec2(io.DisplaySize.x*.93f,io.DisplaySize.y*.91f));
        open=ImGui::Begin(window_name,nullptr,flags|ImGuiWindowFlags_NoResize|
            ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings);
    }
    if(open) {
        if(profile){draw_details(accent);ImGui::End();ImGui::PopStyleColor(7);return;}
        ImGui::Text("%s  |  %zu jogadores",utf8(visible_team.c_str()).c_str(),visible.size());
        if(group_mode) {
            if(ImGui::Button("Abrir detalhes (A / Enter)"))open_details(selected);
            ImGui::SameLine();
            if(full_squad_mode)ImGui::TextUnformatted("Elenco inteiro + técnico do clube");
            else ImGui::TextUnformatted(lineup_valid?"Titulares e reservas":"Escalação indisponível");
            if(!from_home&&!full_squad_mode){
            const char*rooms[]={"Foto da equipe","Sala de coletiva (protótipo)","Vestiário (protótipo)","Coletiva: técnico e jogador"};
            const int kinds[]={0,1,2,4};ImGui::SetNextItemWidth(285);int choice=room_kind==fifa_player::RoomPressPair?3:(int)room_kind;
            if(ImGui::Combo("Ambiente (protótipo)",&choice,rooms,4)){room_kind=(fifa_player::ClubRoomKind)kinds[choice];if(choice==3)press_resample=true;queue_preview();}
            ImGui::SameLine();if(ImGui::Button("Próximo ambiente")){room_kind=(fifa_player::ClubRoomKind)(((int)room_kind+1)%3);queue_preview();}
            ImGui::SameLine();if(ImGui::Button("Coletiva: técnico + jogador")){room_kind=fifa_player::RoomPressPair;press_resample=true;queue_preview();}
            if(room_kind==fifa_player::RoomPressPair) {
                const auto at=std::find_if(visible.begin(),visible.end(),[](const auto&r){return r.player_id==press_player;});
                ImGui::Text("Convidado: %s",at!=visible.end()?utf8(at->name).c_str():"aguardando elenco");
                ImGui::SameLine();if(ImGui::Button("Sortear outro (N / L3)")){press_resample=true;queue_preview();}
            }
            }
        } else {
            if(ImGui::Button("Voltar à equipe (B / Esc)"))mod_screen_request_back();
            ImGui::SameLine();if(ImGui::Button(portrait_mode?"Corpo inteiro (Y / F)":"Retrato (Y / F)"))portrait_mode=!portrait_mode;
            if(!coach_selected()){ImGui::SameLine();if(ImGui::Button("Outra pose (X / P)")){random_individual_pose();queue_preview();}}
        }
        bool press=group_mode&&is_press_room();
        const auto*active_pose=fifa_player::presentation_pose_find(press?press_pose_id:pose_id);
        unsigned pose_mode=press?fifa_player::PosePressConferenceCoach:group_mode?fifa_player::PoseGroup:coach_selected()?fifa_player::PoseStandingCoach:fifa_player::PoseIndividual;
        if(full_squad_mode)ImGui::TextUnformatted("Pose exclusiva: retrato oficial do elenco completo");
        else if(!group_mode&&coach_selected()&&!coach_poses_available())ImGui::TextUnformatted("Pose original: rig do técnico não reconhecido");
        else if(group_mode&&room_kind==fifa_player::RoomDressing)ImGui::TextUnformatted("Ambiente 3D de estudo | Sem alteração na carreira");
        else if(fifa_player::presentation_pose_count(pose_mode)>1) {
            ImGui::SetNextItemWidth(260);
            if(ImGui::BeginCombo("Pose",active_pose?active_pose->name:"Pose indisponível")) {
                for(size_t i=0;i<fifa_player::presentation_pose_count(pose_mode);++i) {
                    const auto*p=fifa_player::presentation_pose_at(i,pose_mode);
                    if(ImGui::Selectable(p->name,p->id==(press?press_pose_id:pose_id))){if(press)press_pose_id=p->id;else pose_id=p->id;queue_preview();}
                }ImGui::EndCombo();
            }
        } else if(active_pose)ImGui::TextUnformatted(active_pose->name);
        ImGui::Separator();
        if(!group_mode){draw_details(accent);ImGui::End();ImGui::PopStyleColor(7);return;}
        float height=std::max(100.f,ImGui::GetContentRegionAvail().y-43),width=ImGui::GetContentRegionAvail().x;
        float left=width*.30f,center=width-left-10;
        ImGui::BeginChild("Elenco",ImVec2(left,height),true,ImGuiWindowFlags_NoNavInputs);
        int details_requested=-1;
        if(visible.empty())ImGui::TextWrapped("Elenco ainda indisponível. Volte ao Meu Time para atualizar os dados da carreira.");
        int section=-1;
        for(size_t i=0;i<visible.size();++i) {
            auto &r=visible[i];ImGui::PushID(r.player_id);
            int role=r.squad_position>=0&&r.squad_position<28?0:r.squad_position==28?1:r.squad_position==29?2:3;
            if(role!=section) {
                section=role;ImGui::Spacing();ImGui::Separator();
                ImGui::TextUnformatted(role==0?(lineup_valid?"TITULARES":"POSIÇÕES DE CAMPO (XI não confirmado)"):role==1?"BANCO DE RESERVAS":role==2?"DEMAIS RESERVAS":"ELENCO / POSIÇÃO NÃO DISPONÍVEL");
            }
            std::string name=utf8(r.name);
            if(r.captain==1)name+=" (C)";
            const ImVec2 at=ImGui::GetCursorScreenPos();float row_width=ImGui::GetContentRegionAvail().x,row_height=42;
            if(ImGui::Selectable("##Player",i==(size_t)selected,0,ImVec2(row_width,row_height))&&input_ready)details_requested=(int)i;
            if(i==(size_t)selected&&scroll_selected)ImGui::SetScrollHereY(.5f);
            ImDrawList*dl=ImGui::GetWindowDrawList();ImU32 text=i==(size_t)selected?IM_COL32(255,255,255,255):IM_COL32(39,59,64,255);
            auto portrait=portrait_views.find(r.player_id);
            if(portrait!=portrait_views.end()&&portrait->second)dl->AddImage((ImTextureID)(intptr_t)portrait->second,ImVec2(at.x,at.y),ImVec2(at.x+40,at.y+40));
            else {dl->AddCircleFilled(ImVec2(at.x+20,at.y+12),6,IM_COL32(119,136,143,255));dl->AddRectFilled(ImVec2(at.x+11,at.y+20),ImVec2(at.x+29,at.y+35),IM_COL32(119,136,143,255),5);}
            if(crest_view)dl->AddImage((ImTextureID)(intptr_t)crest_view,ImVec2(at.x+43,at.y+11),ImVec2(at.x+63,at.y+31));
            const float name_x=at.x+68,score_x=at.x+row_width-30;
            dl->PushClipRect(ImVec2(name_x,at.y),ImVec2(score_x-5,at.y+row_height),true);
            dl->AddText(ImVec2(name_x,at.y+2),text,name.c_str());
            int p=role==0?r.squad_position:r.position;
            std::string info=std::string(position(p))+"  |  #"+std::to_string(r.number);
            dl->AddText(ImVec2(name_x,at.y+22),text,info.c_str());dl->PopClipRect();
            char score[8];if(r.overall>=0&&r.overall<=99)sprintf_s(score,"%d",r.overall);else strcpy_s(score,"-");
            dl->AddText(ImVec2(score_x,at.y+12),text,score);
            ImGui::PopID();
        }
        if(has_coach()&&!from_home) {
            ImGui::Spacing();ImGui::Separator();ImGui::TextUnformatted("COMISSÃO TÉCNICA");
            ImVec2 at=ImGui::GetCursorScreenPos();float row_width=ImGui::GetContentRegionAvail().x;
            const int coach_index=(int)visible.size();bool highlighted=selected==coach_index;
            if(ImGui::Selectable("##Coach",highlighted,0,ImVec2(row_width,44))&&input_ready)details_requested=coach_index;
            if(highlighted&&scroll_selected)ImGui::SetScrollHereY(.5f);
            auto*dl=ImGui::GetWindowDrawList();ImU32 text=highlighted?IM_COL32(255,255,255,255):IM_COL32(39,59,64,255);
            if(crest_view)dl->AddImage((ImTextureID)(intptr_t)crest_view,at,ImVec2(at.x+36,at.y+36));
            dl->PushClipRect(ImVec2(at.x+43,at.y),ImVec2(at.x+row_width,at.y+44),true);
            dl->AddText(ImVec2(at.x+43,at.y+2),text,utf8(visible_icons->coach.name.c_str()).c_str());
            dl->AddText(ImVec2(at.x+43,at.y+23),text,"Treinador | Modelo 3D");dl->PopClipRect();
        }
        scroll_selected=false;ImGui::EndChild();ImGui::SameLine();
        ImGui::BeginChild("Modelo",ImVec2(center,height),true,ImGuiWindowFlags_NoNavInputs);
    if(!visible.empty()) {
            std::shared_ptr<const fifa_player::Model>model;
            {std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial){model=ready_model;loading=false;}}
            if(full_squad_mode)ImGui::Text("Foto do elenco: %zu jogadores + técnico",visible.size());
            else if(room_kind!=fifa_player::RoomPhoto)ImGui::TextUnformatted(is_press_room()?"Sala de coletiva - protótipo":"Vestiário - protótipo");
            else if(group_mode)ImGui::Text("Minha equipe: %zu titulares",lineup.size());
            else ImGui::TextUnformatted(utf8(visible[selected].name).c_str());
            ImGui::TextUnformatted(full_squad_mode?"Arraste / analógico direito: enquadrar | Roda / LT e RT: zoom":"Foto: arraste / analógico direito: mover | Roda / LT e RT: zoom (sem rotação)");
            ImVec2 area=ImGui::GetContentRegionAvail();area.y=std::max(60.f,area.y-44);
            bool rendered=model && renderer.model(model) && renderer.render((UINT)area.x,(UINT)area.y,0,zoom,false,photo_pan_x,photo_pan_y);
            if(rendered) {
                ImGui::Image((ImTextureID)(intptr_t)renderer.image(),area);
                if(ImGui::IsItemHovered()) {
                    if(ImGui::IsMouseDragging(ImGuiMouseButton_Left)) {
                        photo_pan_x=std::max(-.45f,std::min(.45f,photo_pan_x+io.MouseDelta.x/area.x));
                        photo_pan_y=std::max(-.35f,std::min(.35f,photo_pan_y-io.MouseDelta.y/area.y));
                    }
                    zoom=std::max(.65f,std::min(2.f,zoom+io.MouseWheel*.08f));
                }
                if(full_squad_mode)ImGui::TextWrapped("Foto oficial 3D: todos os jogadores disponíveis e o modelo SLC do técnico deste clube, em pose coletiva exclusiva.");
                else if(!from_home){
                if(model->room==fifa_player::RoomPhoto&&!model->specific_head)ImGui::TextWrapped("Algum atleta usa cabeça genérica: asset específico não encontrado.");
                ImGui::TextWrapped(model->room!=fifa_player::RoomPhoto?"Cores e escudo do clube | Camisas dos titulares | Protótipo estático":model->presentation_pose?group_mode?"Foto da equipe | Modelos, alturas, uniformes e detalhes do elenco":"Modelo RX3 | pose de apresentação do mod":
                    "Pose original: rig/weights indisponíveis; veja o log Club3D");
                if(model->room==fifa_player::RoomPressPair) {
                    if(!model->press_coach_present)ImGui::TextWrapped("Modelo de técnico não encontrado para este clube; não usamos o técnico de outro time.");
                    if(!model->press_player_id)ImGui::TextWrapped("Não foi possível posar o jogador com o rig instalado.");
                }
                }
            } else {
                ImGui::TextWrapped(loading?"Carregando os modelos 3D do elenco e do técnico...":full_squad_mode?"Não foi possível montar a foto completa; nenhum jogador foi omitido nem substituído por atleta de outro clube.":group_mode&&!lineup_valid?"Não há 11 titulares válidos na fonte do elenco. Nenhuma escalação é inventada; detalhes individuais continuam disponíveis.":"Prévia 3D indisponível; confira o log Club3D.");
                if(!loading&&full_squad_mode&&model&&model->player_count==0&&!model->diagnostic.empty())ImGui::TextWrapped("%s",utf8(model->diagnostic.c_str()).c_str());
                if(!loading&&lineup_valid&&room_kind==fifa_player::RoomPhoto&&model&&model->player_count!=11)
                    ImGui::TextWrapped("Não foi possível montar os 11 jogadores com esta pose. Não exibimos uma foto parcial como se fosse a equipe inteira; lista e detalhes individuais continuam disponíveis.");
                if(!loading && !render_failed_logged){if(logger)logger("Club3D: renderer/asset unavailable; attributes remain usable");render_failed_logged=true;}
            }
        }
        ImGui::EndChild();
        ImGui::Separator();
        ImGui::TextUnformatted(full_squad_mode?"Cima/baixo: jogador | A/Enter: perfil | analógico direito: enquadrar | LT/RT: zoom | B/Esc: voltar":from_home?"Cima/baixo: jogador | A/Enter: detalhes | LB/RB: pose | B/Esc: meu clube":"Cima/baixo: jogador | A/Enter: detalhes | LB/RB: pose | X/V: ambiente | B/Esc: voltar");
        ImGui::SameLine();if(ImGui::Button("Voltar"))mod_screen_request_back();
        if(details_requested>=0)open_details(details_requested);
    }
    ImGui::End();ImGui::PopStyleColor(7);
}
bool career_news_valid_date(int raw){int year=raw/10000,month=(raw/100)%100,day=raw%100;return year>=2008&&year<=2060&&month>=1&&month<=12&&day>=1&&day<=31;}
void career_news_date_text(int raw,char*out,size_t size){if(!size)return;out[0]=0;if(career_news_valid_date(raw))snprintf(out,size,"%02d/%02d/%04d",raw%100,(raw/100)%100,raw/10000);else snprintf(out,size,"Data da carreira indisponível");}
void career_news_make_item(CareerNewsItem&item,int category,int date,const std::string&title,const std::string&subtitle){
    memset(&item,0,sizeof(item));item.category=category;item.published_date=date;
    snprintf(item.title,sizeof(item.title),"%s",title.c_str());snprintf(item.subtitle,sizeof(item.subtitle),"%s",subtitle.c_str());
    career_news_date_text(date,item.posting_date,sizeof(item.posting_date));
}
std::vector<CareerNewsItem> career_news_build(const CareerNewsFacts&facts,const CareerNewsManagerFacts&manager){
    std::vector<CareerNewsItem>items;items.reserve(CAREER_NEWS_CAPACITY);
    const std::string club=utf8(facts.club_name),opponent=utf8(facts.next_opponent_name),last_opponent=utf8(facts.last_opponent_name);
    const std::string manager_name=utf8(manager.name),goals_name=utf8(facts.goals_leader_name),assists_name=utf8(facts.assists_leader_name);
    const char*club_name=club.empty()?"O clube":club.c_str();char date[24]={};
    auto add=[&](int category,const std::string&title,const std::string&subtitle){if(items.size()<CAREER_NEWS_CAPACITY){CareerNewsItem item;career_news_make_item(item,category,facts.calendar_date,title,subtitle);items.push_back(item);}};
    if(facts.next_valid){
        career_news_date_text(facts.next_date,date,sizeof(date));
        std::string rival=opponent.empty()?"adversário ainda não identificado":opponent;
        std::string title;
        if(facts.next_rivalry>=70)title="Clássico à vista: "+std::string(club_name)+" x "+rival;
        else if(facts.next_knockout)title="Jogo eliminatório no horizonte";
        else title="Próximo desafio: "+rival;
        std::string subtitle="Partida "+std::string(facts.next_home?"em casa":"fora de casa")+" em "+date+".";
        if(facts.next_knockout)subtitle+=" Confronto válido por fase eliminatória.";
        else if(facts.next_opponent_rank>0)subtitle+=" O adversário ocupa a "+std::to_string(facts.next_opponent_rank)+"ª posição na tabela consultada.";
        if(facts.next_rivalry>=70)subtitle+=" A base de rivalidades do jogo classifica o duelo como clássico.";
        else if(facts.next_rivalry>0)subtitle+=" Índice de rivalidade do jogo: "+std::to_string(facts.next_rivalry)+"/100.";
        if(facts.next_opponent_reputation>=0)subtitle+=" Reputação do adversário no jogo: "+std::to_string(facts.next_opponent_reputation)+"/100.";
        add(1,title,subtitle);
    } else add(1,"Agenda do clube", "O calendário da carreira ainda não publicou um próximo jogo para o clube.");
    if(facts.last_valid){
        std::string rival=last_opponent.empty()?"adversário":last_opponent;
        const char*verb=facts.last_goals_for>facts.last_goals_against?"Vitória":facts.last_goals_for<facts.last_goals_against?"Derrota":"Empate";
        career_news_date_text(facts.last_date,date,sizeof(date));
        char score[48]={};snprintf(score,sizeof(score),"%d x %d",facts.last_goals_for,facts.last_goals_against);
        std::string subtitle="Placar de "+std::string(date)+": "+score+" contra "+rival+".";
        if(facts.recent_games>0)subtitle+=" Recorte recente: "+std::to_string(facts.recent_wins)+"V, "+std::to_string(facts.recent_draws)+"E e "+std::to_string(facts.recent_losses)+"D.";
        add(2,std::string(verb)+" no último compromisso",subtitle);
    } else add(2,"Último apito", "Ainda não há resultado concluído no calendário desta carreira.");
    if(facts.table_valid){
        std::string subtitle=std::to_string(facts.table_points)+" pontos em "+std::to_string(facts.table_played)+" partidas.";
        if(facts.table_leader_points>=facts.table_points)subtitle+=" Distância para o líder: "+std::to_string(facts.table_leader_points-facts.table_points)+" ponto(s).";
        add(3,"Situação na tabela: "+std::to_string(facts.table_rank)+"º lugar",subtitle);
    } else if(facts.recent_games>0){
        int maximum=facts.recent_games*3,efficiency=maximum>0?(facts.recent_points*100+maximum/2)/maximum:0;
        std::string headline=facts.streak_result==1&&facts.streak_length>=2?std::to_string(facts.streak_length)+" vitórias consecutivas":
            facts.streak_result==2&&facts.streak_length>=2?"Sequência sem derrotas":
            facts.streak_result==-2&&facts.streak_length>=2?"Sequência sem vitórias":"Forma recente em análise";
        std::string subtitle=std::to_string(facts.recent_games)+" jogos: "+std::to_string(facts.recent_wins)+" vitórias, "+std::to_string(facts.recent_draws)+" empates e "+std::to_string(facts.recent_losses)+" derrotas. Aproveitamento de pontos: "+std::to_string(efficiency)+"%.";
        add(3,headline,subtitle);
    } else add(3,"Momento da equipe", "A tabela e os resultados recentes ainda estão sendo carregados pela carreira.");
    if(facts.goals_leader_valid||facts.assists_leader_valid){
        std::string title="Destaques ofensivos do clube",subtitle;
        if(facts.goals_leader_valid)subtitle+=goals_name+" lidera a artilharia do clube no recorte disponível, com "+std::to_string(facts.goals_leader_goals)+" gol(s).";
        if(facts.assists_leader_valid){if(!subtitle.empty())subtitle+=" ";subtitle+=assists_name+" lidera as assistências, com "+std::to_string(facts.assists_leader_assists)+" passe(s) para gol.";}
        add(4,title,subtitle);
    } else if(facts.squad_valid){
        add(4,"Raio-X do elenco",std::to_string(facts.squad_total)+" jogadores no grupo; média de idade de "+std::to_string(facts.squad_average_age)+" anos e overall médio "+std::to_string(facts.squad_average_overall)+".");
    } else add(4,"Nomes para acompanhar", "Os números de gols e assistências do elenco ainda não estão disponíveis neste momento da carreira.");
    if(manager.valid){
        std::string title="Comissão técnica sob os holofotes",subtitle=manager_name.empty()?"O treinador da carreira":"O trabalho de "+manager_name;
        if(manager.season_record_valid&&manager.games>0){int rate=(manager.wins*100+manager.games/2)/manager.games;
            subtitle+=" na temporada: "+std::to_string(manager.wins)+" vitórias, "+std::to_string(manager.draws)+" empates e "+std::to_string(manager.losses)+" derrotas ("+std::to_string(rate)+"% de vitórias).";
            if(manager.trophies>0)subtitle+=" Títulos registrados na temporada: "+std::to_string(manager.trophies)+".";
        } else subtitle+=" aguarda uma amostra completa de partidas na temporada atual.";
        if(manager.confidence>=0)subtitle+=" Confiança da diretoria: "+std::to_string(manager.confidence)+"/100.";
        if(facts.club_reputation>=0)subtitle+=" Reputação do clube no banco de dados do jogo: "+std::to_string(facts.club_reputation)+"/100.";
        add(5,title,subtitle);
    } else {
        std::string subtitle=facts.club_reputation>=0?"Reputação do clube no banco de dados do jogo: "+std::to_string(facts.club_reputation)+"/100.":"O perfil institucional do clube ainda está sendo carregado.";
        if(facts.squad_valid)subtitle+=" O elenco tem "+std::to_string(facts.squad_total)+" jogadores cadastrados.";
        add(5,"Perfil e reputação do clube",subtitle);
    }
    return items;
}
void career_news_rebuild_locked(){
    career_news_item_count=0;memset(career_news_items,0,sizeof(career_news_items));
    if(career_news_facts.club_id<=0)return;
    CareerNewsManagerFacts manager={};if(career_news_manager.club_id==career_news_facts.club_id)manager=career_news_manager;
    auto items=career_news_build(career_news_facts,manager);career_news_item_count=std::min(items.size(),size_t(CAREER_NEWS_CAPACITY));
    for(size_t i=0;i<career_news_item_count;++i)career_news_items[i]=items[i];
}
}
extern "C" void career_web_dashboard_publish(const CareerWebDashboard*value){std::lock_guard<std::mutex>guard(career_news_lock);career_web_dashboard=value?*value:CareerWebDashboard{};}
extern "C" int career_web_dashboard_copy(int club,CareerWebDashboard*out){if(!out)return 0;std::lock_guard<std::mutex>guard(career_news_lock);if(career_web_dashboard.club!=club){*out={};return 0;}*out=career_web_dashboard;return 1;}
extern "C" void career_news_publish_facts(const CareerNewsFacts*facts){std::lock_guard<std::mutex>guard(career_news_lock);if(!facts){memset(&career_news_facts,0,sizeof(career_news_facts));career_news_rebuild_locked();return;}career_news_facts=*facts;career_news_facts.club_name[sizeof(career_news_facts.club_name)-1]=0;career_news_facts.next_opponent_name[sizeof(career_news_facts.next_opponent_name)-1]=0;career_news_facts.last_opponent_name[sizeof(career_news_facts.last_opponent_name)-1]=0;career_news_facts.goals_leader_name[sizeof(career_news_facts.goals_leader_name)-1]=0;career_news_facts.assists_leader_name[sizeof(career_news_facts.assists_leader_name)-1]=0;career_news_rebuild_locked();}
extern "C" void career_news_publish_manager(const CareerNewsManagerFacts*manager){std::lock_guard<std::mutex>guard(career_news_lock);if(!manager)memset(&career_news_manager,0,sizeof(career_news_manager));else{career_news_manager=*manager;career_news_manager.name[sizeof(career_news_manager.name)-1]=0;}career_news_rebuild_locked();}
extern "C" size_t career_news_copy(int club,CareerNewsItem*out,size_t capacity){if(!out||!capacity||club<=0)return 0;std::lock_guard<std::mutex>guard(career_news_lock);if(career_news_facts.club_id!=club)return 0;size_t count=std::min(capacity,career_news_item_count);for(size_t i=0;i<count;++i)out[i]=career_news_items[i];return count;}
extern "C" void career_next_match_publish(const CareerNextMatchFacts*match){std::lock_guard<std::mutex>guard(career_news_lock);if(!match){memset(&career_next_match_facts,0,sizeof(career_next_match_facts));return;}career_next_match_facts=*match;career_next_match_facts.home_name[sizeof(career_next_match_facts.home_name)-1]=0;career_next_match_facts.away_name[sizeof(career_next_match_facts.away_name)-1]=0;career_next_match_facts.stadium[sizeof(career_next_match_facts.stadium)-1]=0;career_next_match_facts.location[sizeof(career_next_match_facts.location)-1]=0;career_next_match_facts.referee[sizeof(career_next_match_facts.referee)-1]=0;}
extern "C" int career_next_match_copy(int club,CareerNextMatchFacts*out){if(!out||club<=0)return 0;std::lock_guard<std::mutex>guard(career_news_lock);if(career_next_match_facts.club_id!=club){memset(out,0,sizeof(*out));return 0;}*out=career_next_match_facts;return 1;}
extern "C" void career_club_stadium_publish(const CareerClubStadiumFacts*stadium){std::lock_guard<std::mutex>guard(career_news_lock);if(!stadium){memset(&career_club_stadium_facts,0,sizeof(career_club_stadium_facts));return;}career_club_stadium_facts=*stadium;career_club_stadium_facts.name[sizeof(career_club_stadium_facts.name)-1]=0;career_club_stadium_facts.location[sizeof(career_club_stadium_facts.location)-1]=0;career_club_stadium_facts.image_key[sizeof(career_club_stadium_facts.image_key)-1]=0;}
extern "C" int career_club_stadium_copy(int club,CareerClubStadiumFacts*out){if(!out||club<=0)return 0;std::lock_guard<std::mutex>guard(career_news_lock);if(!career_club_stadium_facts.valid||career_club_stadium_facts.club_id!=club){memset(out,0,sizeof(*out));return 0;}*out=career_club_stadium_facts;return 1;}
extern "C" const char *club_player_attribute_field(size_t i){return i<CLUB_PLAYER_ATTRIBUTE_COUNT?fields[i]:nullptr;}
extern "C" BOOL club_player_screen_take_refresh_request(void){return InterlockedExchange(&refresh_requested,0)!=0;}
extern "C" void club_player_screen_publish(const ClubPlayerRow *rows,size_t count,int club,const char *name) {
    count=std::min(count,size_t(CLUB_PLAYER_CAPACITY));
    std::vector<ClubPlayerRow>transfer_rows;std::string transfer_name;
    {
        std::lock_guard<std::mutex>guard(lock);
        published.clear();
        if(rows&&count&&club>0)for(size_t i=0;i<count;++i) {
            const auto&r=rows[i];if(r.team_id!=club||r.player_id<=0||r.player_id>524287)continue;
            bool duplicate=false;for(const auto&old:published)if(old.player_id==r.player_id){duplicate=true;break;}
            if(!duplicate)published.push_back(r);
        }
        for(auto&r:published)r.name[sizeof(r.name)-1]=0;
        std::stable_sort(published.begin(),published.end(),[](const auto&a,const auto&b) {
            int pa=a.squad_position>=0&&a.squad_position<=29?a.squad_position:100;
            int pb=b.squad_position>=0&&b.squad_position<=29?b.squad_position:100;
            if(pa!=pb)return pa<pb;if(a.number!=b.number)return a.number<b.number;return a.player_id<b.player_id;
        });
        published_club=club;team=name?name:"";++revision;transfer_rows=published;transfer_name=team;
    }
    transfer_center_screen_publish_roster(transfer_rows.data(),transfer_rows.size(),club,transfer_name.c_str());
}
bool club_player_screen_register(const char *game_root,void (*log)(const char *)) {
    root=game_root?game_root:"";logger=log;
    work_event=CreateEventW(nullptr,FALSE,FALSE,nullptr);if(!work_event)return false;
    HANDLE thread=CreateThread(nullptr,0,worker,nullptr,0,nullptr);
    if(!thread){CloseHandle(work_event);work_event=nullptr;return false;}CloseHandle(thread);
    const ModOverlayScreen screen={"club_players",FIFA16_CLUB_PLAYER_ACTION,opened,draw,closed,nullptr,back};
    const ModOverlayScreen press_screen={"press_conference",FIFA16_PRESS_CONFERENCE_ACTION,opened,draw,closed,(void*)1,back};
    const ModOverlayScreen squad_screen={"club_squad",FIFA16_CLUB_SQUAD_ACTION,opened,draw,closed,(void*)2,back};
    const ModOverlayScreen full_squad_screen={"full-squad-photo",FIFA16_FULL_SQUAD_ACTION,opened,draw,closed,(void*)4,back};
    const ModOverlayScreen office_screen={"native-office","FifaModsOpenNativeOffice",opened,draw,closed,(void*)3,back};
    const ModOverlayScreen html_office_screen={"my-office",FIFA16_MY_OFFICE_ACTION,html_office_open,html_office_draw,html_office_close,nullptr,html_office_back};
    if(logger)logger("Club3D: renderer_revision=20261002_light_profile_complete_native_XI_guard");
    return mod_screen_register(&screen)!=FALSE&&mod_screen_register(&press_screen)!=FALSE&&mod_screen_register(&squad_screen)!=FALSE&&mod_screen_register(&office_screen)!=FALSE&&mod_screen_register(&html_office_screen)!=FALSE&&mod_screen_register(&full_squad_screen)!=FALSE;
}
void club_player_screen_request_web_pose(int id){InterlockedExchange(&web_pose_requested,id);}
void club_player_screen_request_web_player(int id){InterlockedExchange(&web_player_requested,id>0?id:0);}
void club_player_screen_request_web_room(int room){
    InterlockedExchange(&web_room_requested,room>=1&&room<=4?room:0);
}
bool club_player_begin_embedded(const ClubPlayerRow*rows,size_t count,int club,const char*name){
    if(!mod_screen_is_active("other-clubs")||!rows||!count||count>CLUB_PLAYER_CAPACITY||club<=0||club>200000)return false;
    std::vector<ClubPlayerRow>next;
    for(size_t i=0;i<count;++i){auto r=rows[i];if(r.team_id!=club||r.player_id<=0||r.player_id>524287)return false;
        if(std::any_of(next.begin(),next.end(),[&](const auto&p){return p.player_id==r.player_id;}))return false;
        r.name[sizeof(r.name)-1]=0;next.push_back(r);}
    std::stable_sort(next.begin(),next.end(),[](const auto&a,const auto&b){int pa=a.squad_position>=0&&a.squad_position<=29?a.squad_position:100,pb=b.squad_position>=0&&b.squad_position<=29?b.squad_position:100;
        if(pa!=pb)return pa<pb;return a.number!=b.number?a.number<b.number:a.player_id<b.player_id;});
    external_rows=std::move(next);external_team=name?name:"";external_club=club;embedded_club=true;opened(nullptr);return true;
}
bool club_player_screen_open_search_profile(const ClubPlayerRow*row,const char*name){
    if(!row||row->player_id<=0||row->player_id>524287||!mod_screen_is_active("player-search")||
       !mod_screen_has_action(FIFA16_CLUB_PLAYER_ACTION))return false;
    external_rows.assign(1,*row);external_rows[0].name[sizeof(external_rows[0].name)-1]=0;
    external_team=name?name:"";external_club=row->team_id;embedded_club=true;database_profile_child=true;visible_revision=~0u;
    if(mod_screen_push_action(FIFA16_CLUB_PLAYER_ACTION))return true;
    database_profile_child=false;embedded_club=false;external_rows.clear();external_team.clear();external_club=0;return false;
}
void club_player_draw_embedded(){if(embedded_club)draw(nullptr);}
bool club_player_back_embedded(){return embedded_club&&back(nullptr);}
void club_player_end_embedded(){if(embedded_club){closed(nullptr);embedded_club=false;external_rows.clear();external_team.clear();external_club=0;visible_revision=~0u;}}
void club_player_screen_set_device(ID3D11Device *device){
    office_coach_renderer.device(device);
    office_lineup_renderer.device(device);
    coach_card_renderer.device(device);
    renderer.device(device);if(device==icon_device)return;clear_icon_views();
    if(icon_device)icon_device->Release();icon_device=device;if(device)device->AddRef();
}
void club_player_screen_set_number_font(ImFont *font){
    player_profile::set_shirt_number_font(font);
}
#ifdef CLUB_PLAYER_SCREEN_TEST
ClubOfficeTestView club_office_test_view(){auto signals=office_social_signals();auto manager=office_manager_facts();return {office_home,office_focus,office_menu,office_item,office_slide,visible_icons&&bool(visible_icons->arrival),office_social_runtime.social_index,(int)office_social_runtime.posts.size(),(unsigned long long)office_social::followers(signals),signals.table_valid,
    manager.valid!=0,manager.games,manager.wins,manager.draws,manager.losses,manager.confidence,manager.reputation};}
bool club_office_test_center(int i,float&x,float&y){if(i<0||i>=11)return false;x=office_centers[i].x;y=office_centers[i].y;return x>0&&y>0;}
ClubOfficeSquadTestSummary club_office_test_squad_summary(const ClubPlayerRow*rows,size_t count){auto s=office_squad_summary(rows,count);return {s.players,s.average_age,s.average_overall,s.positions[0],s.positions[1],s.positions[2],s.positions[3]};}
bool club_office_test_social_next_center(float&x,float&y){x=office_social_next.x;y=office_social_next.y;return x>0&&y>0;}
bool club_office_test_social_dot_center(int i,float&x,float&y){if(i<0||i>=5)return false;x=office_social_dots[i].x;y=office_social_dots[i].y;return x>0&&y>0;}
int club_office_test_social_source_count(int source){if(source<0||source>3)return 0;int n=0;for(const auto&p:office_social_runtime.posts)if((int)p.source==source)++n;return n;}
bool club_office_test_menu_center(int i,float&x,float&y){if(i<0||i>=5)return false;x=office_menu_centers[i].x;y=office_menu_centers[i].y;return x>0&&y>0;}
bool club_office_test_dot_center(int i,float&x,float&y){if(i<0||i>=6)return false;x=office_dots[i].x;y=office_dots[i].y;return x>0&&y>0;}
ClubPlayerScreenTestView club_player_screen_test_view(){return {group_mode,selected,attribute_page,pose_id,yaw,zoom,photo_pan_x,photo_pan_y,visible.size(),lineup.size(),portrait_views.size(),lineup_valid,selected>=0&&selected<(int)visible.size()?visible[selected].player_id:0,has_coach(),coach_selected(),(int)room_kind,profile_state.pan_y,profile_state.scroll_y,profile_state.scroll_max,flag_views.size(),club_home,coach_child,card_focus,card_coach_yaw,card_coach_zoom,visible_icons&&bool(visible_icons->card.model),visible_icons?visible_icons->card.context.club:0,visible_icons?visible_icons->card.context.nationality:0,profile_state.view_tab};}
bool club_player_screen_test_card_center(int i,float&x,float&y){if(i<0||i>2)return false;x=card_centers[i].x;y=card_centers[i].y;return x>0&&y>0;}
bool club_player_screen_test_starter(int player_id){return std::find(lineup.begin(),lineup.end(),player_id)!=lineup.end();}
bool club_player_screen_test_select_pose(unsigned id){
    const auto*info=fifa_player::presentation_pose_find(id);
    if(!info||!(info->modes&(group_mode?fifa_player::PoseGroup:coach_selected()?fifa_player::PoseStandingCoach:fifa_player::PoseIndividual)))return false;
    pose_id=id;queue_preview();return true;
}
bool club_player_screen_test_select_room(int kind){
    if(!group_mode||kind<0||(kind>2&&kind!=4))return false;room_kind=(fifa_player::ClubRoomKind)kind;queue_preview();return true;
}
int club_player_screen_test_press_player(){return press_player;}
int club_player_screen_test_press_rendered(){std::lock_guard<std::mutex>guard(lock);return ready_serial==request_serial&&ready_model?ready_model->press_player_id:0;}
bool club_player_screen_test_resample_press_player(){if(!group_mode||room_kind!=fifa_player::RoomPressPair)return false;press_resample=true;queue_preview();return true;}
#endif
