/* Included in the club screen's private render namespace. It shares owned
 * roster snapshots and the asset worker, never native DB queries or pointers. */
int office_submenu_count(int index){switch(index){case 0:return 1;case 2:return 5;case 3:return 2;case 4:return 3;case 5:return 1;default:return 0;}}
bool office_has_submenu(int index){return office_submenu_count(index)>0;}
void office_close_submenu(){office_menu=-1;office_item=0;}
void office_select_slide(int target,DWORD now,int preferred_direction=0){
    const int count=1+CAREER_NEWS_CAPACITY;target=(target%count+count)%count;
    if(target==office_slide){office_last_advance=now;return;}
    int delta=(target-office_slide+count)%count;
    office_transition_direction=preferred_direction? (preferred_direction>0?1:-1):(delta>count/2?-1:1);
    office_transition_from=office_slide;office_slide=target;office_transition_started=now;office_last_advance=now;
}
ImVec4 office_blend(ImVec4 a,ImVec4 b,float amount){return {a.x+(b.x-a.x)*amount,a.y+(b.y-a.y)*amount,a.z+(b.z-a.z)*amount,a.w+(b.w-a.w)*amount};}
float office_luminance(ImVec4 c){return .2126f*c.x+.7152f*c.y+.0722f*c.z;}
float office_linear_channel(float value){return value<=.04045f?value/12.92f:powf((value+.055f)/1.055f,2.4f);}
bool office_header_uses_dark_text(unsigned rgb){float r=office_linear_channel(((rgb>>16)&255)/255.f),g=office_linear_channel(((rgb>>8)&255)/255.f),b=office_linear_channel((rgb&255)/255.f);
    float light=.2126f*r+.7152f*g+.0722f*b,white_contrast=1.05f/(light+.05f),dark_contrast=(light+.05f)/.064f;return dark_contrast>=white_contrast;}
ImVec4 office_club_color(){if(visible.empty()||!visible.front().club_colors_valid)return {.03f,.33f,.55f,1};
    unsigned rgb=visible.front().club_colors[0];return {((rgb>>16)&255)/255.f,((rgb>>8)&255)/255.f,(rgb&255)/255.f,1};}
void office_activate(int index){
    if(index==6){office_close_submenu();open_home_card(0);return;}
    if(index==7&&office_slide==0&&lineup_valid){office_close_submenu();open_home_card(2);return;}
    if(index==10){office_close_submenu();open_home_card(2);return;}
    if(index==8)return;
    if(index<0||index>=6)return;
    office_focus=index;
    if(office_has_submenu(index)){
        if(office_menu==index)office_close_submenu();
        else{office_menu=index;office_item=0;}
    }else office_close_submenu();
}
void office_menu_activate(){
    if(office_menu==0)mod_screen_push_action(FIFA16_CLUB_SQUAD_ACTION);
    else if(office_menu==2){const char*actions[]={"FifaModsOpenRanking","FifaModsOpenOtherClubs","FifaModsOpenLeagues",FIFA16_CLUB_COMPETITIONS_ACTION,FIFA16_PLAYER_SEARCH_ACTION};mod_screen_push_action(actions[std::clamp(office_item,0,4)]);}
    else if(office_menu==3){if(office_item==0)open_home_card(0);else mod_screen_push_action("FifaModsOpenTrophyRoom");}
    else if(office_menu==4){const char*actions[]={FIFA_TRANSFER_MARKET_ACTION,FIFA_MY_TRANSFERS_ACTION,FIFA_TRANSFER_LEAGUES_ACTION};mod_screen_push_action(actions[std::clamp(office_item,0,2)]);}
    else if(office_menu==5)mod_screen_push_action("FifaModsOpenLoans");
    office_close_submenu();
}
office_social::Signals office_social_signals(){office_social::Signals s;s.club=visible_club;s.club_name=utf8(visible_team.c_str());
    size_t suffix=s.club_name.find(" - ");if(suffix!=std::string::npos)s.club_name.resize(suffix);
    if(visible_icons){s.league_name=visible_icons->league_name;s.league_strength=visible_icons->league_strength;s.competition=visible_icons->league;}
    if(visible_icons&&visible_icons->card.context.valid){const auto&coach=visible_icons->card.context;s.coach_name=utf8(coach.name);
        s.coach_recent_valid=coach.recent_valid!=0;s.coach_recent_games=coach.recent_games;s.coach_recent_points=coach.recent_points;}
    double overall=0;size_t count=0;for(const auto&r:visible){if(r.overall>0&&r.overall<=99){overall+=r.overall;++count;}
        if(r.player_id>0&&s.players.size()<64&&std::none_of(s.players.begin(),s.players.end(),[&](const auto&p){return p.id==r.player_id;})){
            office_social::Player player;player.id=r.player_id;player.name=utf8(r.name);size_t suffix=player.name.find(" - ");if(suffix!=std::string::npos)player.name.resize(suffix);
            if(!player.name.empty())s.players.push_back(std::move(player));}}
    if(count)s.average_overall=(float)(overall/count);
    ClubCompetitionSocialSnapshot table={};if(club_competitions_social_read(s.club,&table)){s.cup_state=table.cup_state;if(table.available){s.table_valid=true;s.is_group=table.is_group!=0;s.competition=table.competition;s.rank=table.rank;s.teams=table.team_count;
            s.played=table.played;s.wins=table.won;s.draws=table.drawn;s.losses=table.lost;s.goals_for=table.goals_for;s.goals_against=table.goals_against;memcpy(s.form,table.form,sizeof(s.form));}}
    CareerNewsFacts news={};CareerNewsManagerFacts manager={};
    {std::lock_guard<std::mutex>guard(career_news_lock);if(career_news_facts.club_id==s.club)news=career_news_facts;
        if(career_news_manager.club_id==s.club)manager=career_news_manager;}
    if(news.club_id==s.club){s.last_valid=news.last_valid;s.last_home=news.last_home;s.last_goals_for=news.last_goals_for;s.last_goals_against=news.last_goals_against;
        s.last_opponent=utf8(news.last_opponent_name);s.next_valid=news.next_valid;s.next_home=news.next_home;s.next_knockout=news.next_knockout;s.next_rivalry=news.next_rivalry;
        s.next_opponent_rank=news.next_opponent_rank;s.next_date=news.next_date;s.next_opponent=utf8(news.next_opponent_name);
        s.recent_games=news.recent_games;s.recent_wins=news.recent_wins;s.recent_draws=news.recent_draws;s.recent_losses=news.recent_losses;
        s.recent_goals_for=news.recent_goals_for;s.recent_goals_against=news.recent_goals_against;
        if(news.table_valid){s.table_points=news.table_points;s.table_leader_points=news.table_leader_points;}
        s.goals_leader_valid=news.goals_leader_valid;s.goals_leader_goals=news.goals_leader_goals;s.goals_leader_name=utf8(news.goals_leader_name);
        s.assists_leader_valid=news.assists_leader_valid;s.assists_leader_assists=news.assists_leader_assists;s.assists_leader_name=utf8(news.assists_leader_name);
        for(std::string*name:{&s.last_opponent,&s.next_opponent,&s.goals_leader_name,&s.assists_leader_name}){size_t cut=name->find(" - ");if(cut!=std::string::npos)name->resize(cut);}}
    if(manager.club_id==s.club&&manager.valid){s.manager_record_valid=manager.season_record_valid;s.manager_games=manager.games;s.manager_wins=manager.wins;s.manager_draws=manager.draws;
        s.manager_losses=manager.losses;s.manager_confidence=manager.confidence;if(s.coach_name.empty())s.coach_name=utf8(manager.name);}
    return s;}
struct OfficeSquadSummary {int players=0,average_age=-1,average_overall=-1;int positions[4]={};};
OfficeSquadSummary office_squad_summary(const ClubPlayerRow*rows,size_t count,const std::unordered_map<int,int>*ages=nullptr){
    OfficeSquadSummary summary;int age_sum=0,age_count=0,overall_sum=0,overall_count=0;int seen[CLUB_PLAYER_CAPACITY]={};size_t seen_count=0;
    if(!rows)return summary;count=std::min(count,(size_t)CLUB_PLAYER_CAPACITY);
    for(size_t i=0;i<count;++i){const auto&r=rows[i];if(r.player_id<=0)continue;bool duplicate=false;
        for(size_t j=0;j<seen_count;++j)if(seen[j]==r.player_id){duplicate=true;break;}if(duplicate)continue;
        seen[seen_count++]=r.player_id;++summary.players;
        int age=r.age;if((age<14||age>60)&&ages){auto found=ages->find(r.player_id);if(found!=ages->end())age=found->second;}
        if(age>=14&&age<=60){age_sum+=age;++age_count;}
        if(r.overall>0&&r.overall<=99){overall_sum+=r.overall;++overall_count;}
        if(r.position==0)++summary.positions[0];else if(r.position>=1&&r.position<=8)++summary.positions[1];
        else if(r.position>=9&&r.position<=22)++summary.positions[2];else if(r.position>=23&&r.position<=27)++summary.positions[3];
    }
    if(age_count)summary.average_age=(age_sum+age_count/2)/age_count;
    if(overall_count)summary.average_overall=(overall_sum+overall_count/2)/overall_count;
    return summary;
}
OfficeSquadSummary office_squad_summary(){return office_squad_summary(visible.data(),visible.size(),visible_icons?&visible_icons->ages:nullptr);}
void office_squad_summary_draw_card(float x,float y,float width,float height,const OfficeSquadSummary&summary,bool focused){
    auto*dl=ImGui::GetWindowDrawList();ImVec2 at={x,y},end={x+width,y+height};float scale=std::clamp(std::min(width/340.f,height/360.f),.64f,1.04f);
    ImU32 blue=IM_COL32(12,103,163,255),ink=IM_COL32(35,67,84,255),muted=IM_COL32(91,116,131,255),line=IM_COL32(204,219,229,255);
    dl->AddRectFilled(at,end,IM_COL32(255,255,255,255));dl->AddRectFilled({at.x,at.y},{end.x,at.y+4*scale},blue,5*scale);
    dl->AddText(nullptr,16*scale,{at.x+14*scale,at.y+13*scale},blue,"ELENCO");
    dl->AddText(nullptr,11*scale,{end.x-81*scale,at.y+16*scale},muted,"PLANTEL ATUAL");
    const char*labels[]={"JOGADORES","MÉDIA IDADE","NOTA MÉDIA"};int values[]={summary.players,summary.average_age,summary.average_overall};
    const float left=at.x+10*scale,stats_y=at.y+49*scale,stats_w=width-20*scale,col_w=stats_w/3.f;
    for(int i=0;i<3;++i){float col_x=left+i*col_w;ImVec2 label_size=ImGui::GetFont()->CalcTextSizeA(11*scale,FLT_MAX,0,labels[i]);
        dl->AddText(nullptr,11*scale,{col_x+(col_w-label_size.x)*.5f,stats_y},muted,labels[i]);
        char value[16]={};if(values[i]>=0)_snprintf_s(value,sizeof(value),_TRUNCATE,"%d",values[i]);else lstrcpynA(value,"—",sizeof(value));
        ImVec2 value_size=ImGui::GetFont()->CalcTextSizeA(28*scale,FLT_MAX,0,value);dl->AddText(nullptr,28*scale,{col_x+(col_w-value_size.x)*.5f,stats_y+16*scale},ink,value);
    }
    float divider_y=stats_y+55*scale;dl->AddLine({at.x+13*scale,divider_y},{end.x-13*scale,divider_y},line,1.f);
    const char*section="DIVISÃO POR POSIÇÃO";ImVec2 section_size=ImGui::GetFont()->CalcTextSizeA(12*scale,FLT_MAX,0,section);
    dl->AddText(nullptr,12*scale,{at.x+(width-section_size.x)*.5f,divider_y+11*scale},muted,section);
    const char*groups[]={"GOLEIROS","DEFENSORES","MEIAS","ATACANTES"};const float group_y=divider_y+37*scale,group_w=(width-16*scale)/4.f;
    for(int i=0;i<4;++i){float gx=at.x+8*scale+i*group_w;ImVec2 label_size=ImGui::GetFont()->CalcTextSizeA(10.5f*scale,FLT_MAX,0,groups[i]);
        dl->AddText(nullptr,10.5f*scale,{gx+(group_w-label_size.x)*.5f,group_y},muted,groups[i]);
        char value[16]={};_snprintf_s(value,sizeof(value),_TRUNCATE,"%d",summary.positions[i]);ImVec2 value_size=ImGui::GetFont()->CalcTextSizeA(22*scale,FLT_MAX,0,value);
        dl->AddText(nullptr,22*scale,{gx+(group_w-value_size.x)*.5f,group_y+15*scale},blue,value);
    }
    float action_y=end.y-43*scale;ImVec2 action_min={at.x+12*scale,action_y},action_max={end.x-12*scale,end.y-10*scale};
    dl->AddRectFilled(action_min,action_max,focused?IM_COL32(226,240,249,255):IM_COL32(241,247,251,255),5*scale);
    const char*action="ABRIR ELENCO";ImVec2 action_size=ImGui::GetFont()->CalcTextSizeA(13*scale,FLT_MAX,0,action);
    dl->AddText(nullptr,13*scale,{(action_min.x+action_max.x-action_size.x)*.5f,(action_min.y+action_max.y-13*scale)*.5f},blue,action);
}
void office_social_draw_card(const office_social::Signals&s,float x,float y,float width,float height,bool ready){
    auto*dl=ImGui::GetWindowDrawList();auto&io=ImGui::GetIO();ImVec2 at={x,y},end={x+width,y+height};office_centers[8]={(at.x+end.x)*.5f,(at.y+end.y)*.5f};
    bool hovered=ImGui::IsMouseHoveringRect(at,end,true),pointer_moved=io.MouseDelta.x||io.MouseDelta.y;if(ready&&hovered&&pointer_moved)office_focus=8;
    if(ready&&hovered&&ImGui::IsMouseClicked(0))office_focus=8;
    bool focused=office_focus==8||hovered;ImU32 blue=IM_COL32(12,103,163,255);
    dl->AddRectFilled(at,end,IM_COL32(250,252,254,255),8);
    dl->AddRect(at,end,focused?IM_COL32(20,112,172,255):IM_COL32(194,211,223,255),8,0,focused?2.4f:1.0f);
    auto text=[&](float tx,float ty,const char*value,ImU32 color=IM_COL32(36,78,105,255),float size=0){dl->AddText(nullptr,size,{tx,ty},color,value);};
    text(at.x+12,at.y+9,"SEGUIDORES",IM_COL32(67,106,130,255),14);
    if(crest_view)dl->AddImage((ImTextureID)(intptr_t)crest_view,{at.x+12,at.y+31},{at.x+46,at.y+65});
    else {dl->AddCircleFilled({at.x+29,at.y+48},17,IM_COL32(221,233,241,255));text(at.x+23,at.y+40,"FC",blue,12);}
    std::string club=utf8(s.club_name.c_str());if(club.empty())club="Clube";
    text(at.x+55,at.y+32,("#"+club).c_str(),IM_COL32(28,76,108,255),15);
    text(at.x+55,at.y+51,s.league_name.empty()?"Modo carreira":s.league_name.c_str(),IM_COL32(98,122,138,255),12);
    text(at.x+12,at.y+69,office_social::format_followers(office_social::followers(s)).c_str(),IM_COL32(13,81,130,255),28);
    text(at.x+14,at.y+101,"seguidores estimados",IM_COL32(105,126,139,255),11);
    dl->AddLine({at.x+12,at.y+116},{end.x-12,at.y+116},IM_COL32(216,226,233,255),1);
    const auto&post=office_social_runtime.posts[office_social_runtime.social_index%5];
    const char*source_label=post.source==office_social::PlayerVoice?"VOZ DO ELENCO":post.source==office_social::ClubVoice?"NOTA DO CLUBE":post.source==office_social::Press?"NO RADAR":"NA REDE";
    ImU32 source_color=post.source==office_social::PlayerVoice?IM_COL32(27,132,111,255):post.source==office_social::ClubVoice?IM_COL32(150,104,25,255):post.source==office_social::Press?IM_COL32(32,98,153,255):IM_COL32(58,98,124,255);
    text(at.x+12,at.y+123,source_label,source_color,12);
    auto draw_arrow=[&](bool next){ImVec2 center={end.x-40+(next?22:0),at.y+130};ImVec2 box0={center.x-10,center.y-10},box1={center.x+10,center.y+10};
        bool hot=ImGui::IsMouseHoveringRect(box0,box1,true);if(hot)ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
            if(ready&&hot&&ImGui::IsMouseClicked(0)){office_focus=8;office_social_runtime.social_index=(office_social_runtime.social_index+(next?1:4))%5;}
        ImU32 color=hot?blue:IM_COL32(101,132,151,255);if(next)dl->AddTriangleFilled({center.x-3,center.y-5},{center.x-3,center.y+5},{center.x+4,center.y},color);
        else dl->AddTriangleFilled({center.x+3,center.y-5},{center.x+3,center.y+5},{center.x-4,center.y},color);
        if(next)office_social_next=center;};
    draw_arrow(false);draw_arrow(true);
    float post_y=at.y+146;ImVec2 avatar={at.x+25,post_y+13};
    ImU32 avatar_color=post.source==office_social::PlayerVoice?IM_COL32(26,137,111,255):post.source==office_social::ClubVoice?IM_COL32(160,119,37,255):post.source==office_social::Press?IM_COL32(26,108,166,255):IM_COL32(91,128,151,255);
    dl->AddCircleFilled(avatar,13,avatar_color);char initial[2]={post.initial?post.initial:'?',0};
    ImVec2 initial_size=ImGui::CalcTextSize(initial);dl->AddText({avatar.x-initial_size.x*.5f,avatar.y-initial_size.y*.5f},IM_COL32(255,255,255,255),initial);
    float author_x=at.x+45;std::string author=post.name.empty()?"Torcida":post.name;dl->AddText(nullptr,13,{author_x,post_y},IM_COL32(35,68,87,255),author.c_str());
    float badge_x=author_x+ImGui::GetFont()->CalcTextSizeA(13,FLT_MAX,0,author.c_str()).x+8;
    if(post.verified){dl->AddCircleFilled({badge_x+6,post_y+8},6,IM_COL32(29,143,207,255));dl->AddLine({badge_x+3,post_y+8},{badge_x+5.5f,post_y+10.5f},IM_COL32(255,255,255,255),1.5f);dl->AddLine({badge_x+5.5f,post_y+10.5f},{badge_x+10,post_y+5},IM_COL32(255,255,255,255),1.5f);}
    std::string handle=post.handle;dl->AddText(nullptr,11,{author_x,post_y+16},IM_COL32(119,139,151,255),handle.c_str());
    float message_y=post_y+34;ImVec2 clip_min={at.x+13,message_y},clip_max={end.x-12,end.y-33};
    if(clip_max.y>clip_min.y){dl->PushClipRect(clip_min,clip_max,true);dl->AddText(nullptr,14,{clip_min.x,message_y},IM_COL32(44,65,77,255),post.text.c_str(),nullptr,width-26);dl->PopClipRect();}
    float dot_y=end.y-17,spacing=22.f,center_x=(at.x+end.x)*.5f;
    for(int i=0;i<5;++i){ImVec2 dot={center_x+(i-2)*spacing,dot_y};office_social_dots[i]=dot;ImVec2 hit_min={dot.x-9,dot.y-9},hit_max={dot.x+9,dot.y+9};
        bool hot=ImGui::IsMouseHoveringRect(hit_min,hit_max,true);if(hot)ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);
        if(ready&&hot&&pointer_moved)office_focus=8;
        if(ready&&hot&&ImGui::IsMouseClicked(0)){office_focus=8;office_social_runtime.social_index=i;}
        dl->AddCircleFilled(dot,i==office_social_runtime.social_index?5.f:3.5f,i==office_social_runtime.social_index?blue:IM_COL32(174,198,213,255));
        if(i==office_social_runtime.social_index)dl->AddCircle(dot,7.f,IM_COL32(12,103,163,100),0,1.2f);
    }
}
CareerNewsManagerFacts office_manager_facts(){CareerNewsManagerFacts manager={};std::lock_guard<std::mutex>guard(career_news_lock);
    if(career_news_manager.club_id==visible_club&&career_news_manager.valid)manager=career_news_manager;return manager;}
void office_manager_draw_card(const office_social::Signals&s,const CareerNewsManagerFacts&manager,float x,float y,float width,float height,bool ready){
    auto*dl=ImGui::GetWindowDrawList();auto&io=ImGui::GetIO();ImVec2 at={x,y},end={x+width,y+height};office_centers[9]={(at.x+end.x)*.5f,(at.y+end.y)*.5f};
    ImGui::SetCursorScreenPos(at);ImGui::PushID(9);ImGui::InvisibleButton("Manager performance card",{width,height});bool hovered=ImGui::IsItemHovered();
    if(ready&&hovered&&(io.MouseDelta.x||io.MouseDelta.y))office_focus=9;if(ready&&ImGui::IsItemClicked())office_focus=9;ImGui::PopID();
    bool focused=office_focus==9||hovered;ImU32 blue=IM_COL32(12,103,163,255),ink=IM_COL32(31,63,81,255),muted=IM_COL32(101,124,139,255);
    dl->AddRectFilled(at,end,IM_COL32(250,252,254,255),8);dl->AddRectFilled({at.x,at.y},{end.x,at.y+4},blue,8);
    dl->AddRect(at,end,focused?IM_COL32(20,112,172,255):IM_COL32(194,211,223,255),8,0,focused?2.4f:1.f);
    float scale=std::clamp(std::min(width/680.f,height/330.f),.78f,1.08f);
    auto text=[&](float tx,float ty,const char*value,ImU32 color,float size){dl->AddText(nullptr,size*scale,{tx,ty},color,value);};
    text(at.x+14*scale,at.y+11*scale,"TÉCNICO NO COMANDO",blue,12);
    std::string name=manager.valid&&manager.name[0]?utf8(manager.name):visible_icons&&visible_icons->card.context.valid?utf8(visible_icons->card.context.name):"Treinador";
    text(at.x+14*scale,at.y+30*scale,name.c_str(),ink,17);
    char games_label[48]={};if(manager.season_record_valid&&manager.games>=0)sprintf_s(games_label,"TEMPORADA ATUAL  •  %d JOGOS",manager.games);else lstrcpynA(games_label,"TEMPORADA ATUAL",sizeof(games_label));
    ImVec2 games_size=ImGui::GetFont()->CalcTextSizeA(10*scale,FLT_MAX,0,games_label);dl->AddText(nullptr,10*scale,{end.x-14*scale-games_size.x,at.y+15*scale},muted,games_label);

    CoachProfileContext rating_context={};if(visible_icons)rating_context=visible_icons->card.context;
    if(visible_icons&&visible_icons->league_strength>=0&&visible_icons->league_strength<=100){rating_context.league_strength=visible_icons->league_strength;rating_context.league_strength_valid=1;}
    if(manager.reputation>=0&&manager.reputation<=1501)rating_context.reputation=manager.reputation;
    int stars=coach_profile::reputation_stars(rating_context);
    text(at.x+14*scale,at.y+57*scale,"PRESTÍGIO",muted,10);
    if(stars<0)text(at.x+82*scale,at.y+52*scale,"—",muted,16);
    else{
        // Draw stars as vector shapes: the bundled game font has no reliable
        // star glyph, so UTF-8 symbols were rendered as question marks.
        const ImU32 filled=IM_COL32(17,113,173,255),empty=IM_COL32(166,190,205,255);
        const float outer=7.5f*scale,inner=outer*.43f,cy=at.y+62*scale,start_x=at.x+87*scale,step=19*scale;
        for(int i=0;i<5;++i){ImVec2 points[10];float cx=start_x+i*step;
            for(int j=0;j<10;++j){float radius=(j&1)?inner:outer,angle=-1.57079632679f+j*0.62831853072f;points[j]={cx+cosf(angle)*radius,cy+sinf(angle)*radius};}
            if(i<stars)dl->AddConvexPolyFilled(points,10,filled);
            else{dl->PathClear();for(const auto&p:points)dl->PathLineTo(p);dl->PathStroke(empty,ImDrawFlags_Closed,1.2f*scale);}
        }
    }
    float confidence_x=at.x+width*.48f,confidence_y=at.y+57*scale,confidence_w=std::max(80.f,width*.47f-16*scale);
    char confidence_label[40]={};if(manager.valid&&manager.confidence>=0&&manager.confidence<=100)sprintf_s(confidence_label,"DIRETORIA  %d%%",manager.confidence);else lstrcpynA(confidence_label,"DIRETORIA  —",sizeof(confidence_label));
    text(confidence_x,confidence_y,confidence_label,muted,10);float bar_y=at.y+74*scale;dl->AddRectFilled({confidence_x,bar_y},{confidence_x+confidence_w,bar_y+6*scale},IM_COL32(222,232,238,255),3*scale);
    if(manager.confidence>=0&&manager.confidence<=100)dl->AddRectFilled({confidence_x,bar_y},{confidence_x+confidence_w*manager.confidence/100.f,bar_y+6*scale},blue,3*scale);

    bool league_table=s.table_valid&&!s.is_group&&s.teams>1&&s.rank>0&&s.rank<=s.teams;
    const char*objective="AGUARDANDO DADOS";ImU32 objective_color=muted;
    if(manager.valid&&manager.confidence>=0){
        bool lower_third=league_table&&s.rank>s.teams*2/3;
        if(manager.confidence<40||lower_third){objective="SOB PRESSÃO";objective_color=IM_COL32(177,69,67,255);}
        else if(manager.confidence>=70&&(!league_table||s.rank<=(s.teams+1)/2)){objective="NO CAMINHO";objective_color=IM_COL32(30,132,92,255);}
        else {objective="EM AVALIAÇÃO";objective_color=IM_COL32(176,125,37,255);}}
    text(at.x+14*scale,at.y+88*scale,"OBJETIVOS • PROJEÇÃO",muted,9);
    ImVec2 objective_size=ImGui::GetFont()->CalcTextSizeA(10*scale,FLT_MAX,0,objective);ImVec2 chip_min={at.x+157*scale,at.y+84*scale};
    dl->AddRectFilled(chip_min,{chip_min.x+objective_size.x+14*scale,chip_min.y+20*scale},IM_COL32(232,241,246,255),10*scale);
    dl->AddText(nullptr,10*scale,{chip_min.x+7*scale,chip_min.y+4*scale},objective_color,objective);
    dl->AddLine({at.x+14*scale,at.y+113*scale},{end.x-14*scale,at.y+113*scale},IM_COL32(216,226,233,255),1);

    bool record=manager.valid&&manager.season_record_valid&&manager.games>0&&manager.games<=100000&&manager.wins>=0&&manager.draws>=0&&manager.losses>=0&&manager.wins+manager.draws+manager.losses==manager.games;
    double win=record?100.0*manager.wins/manager.games:0,draw=record?100.0*manager.draws/manager.games:0,loss=record?100.0*manager.losses/manager.games:0;
    double points=record?100.0*(manager.wins*3.0+manager.draws)/(manager.games*3.0):0;
    ImVec2 ring={at.x+70*scale,at.y+184*scale};float radius=37*scale;
    dl->AddCircle(ring,radius,IM_COL32(222,232,238,255),48,6*scale);
    if(record&&points>0){dl->PathClear();dl->PathArcTo(ring,radius,-1.5707963f,-1.5707963f+6.2831853f*(float)(points/100.0),48);dl->PathStroke(blue,0,6*scale);}
    char points_label[16]={};if(record)sprintf_s(points_label,"%.0f%%",points);else lstrcpynA(points_label,"—",sizeof(points_label));
    ImVec2 psize=ImGui::GetFont()->CalcTextSizeA(21*scale,FLT_MAX,0,points_label);dl->AddText(nullptr,21*scale,{ring.x-psize.x*.5f,ring.y-psize.y*.5f},ink,points_label);
    text(at.x+16*scale,at.y+230*scale,"APROVEITAMENTO",blue,9);text(at.x+37*scale,at.y+245*scale,"DE PONTOS",muted,8);
    if(!record){text(at.x+14*scale,at.y+264*scale,"Histórico da temporada indisponível",muted,9);}
    else {
        struct Rate{const char*label;int count;double pct;ImU32 color;};Rate rates[]={{"VITÓRIAS",manager.wins,win,IM_COL32(38,145,102,255)},
            {"EMPATES",manager.draws,draw,IM_COL32(207,153,56,255)},{"DERROTAS",manager.losses,loss,IM_COL32(191,86,83,255)}};
        float rx=at.x+158*scale,rw=std::max(100.f,width-176*scale),row_h=43*scale;
        for(int i=0;i<3;++i){float ry=at.y+(126.f+i*row_h)*scale;char value[48]={};sprintf_s(value,"%d   •   %.0f%%",rates[i].count,rates[i].pct);
            text(rx,ry,rates[i].label,muted,9);ImVec2 vs=ImGui::GetFont()->CalcTextSizeA(10*scale,FLT_MAX,0,value);dl->AddText(nullptr,10*scale,{rx+rw-vs.x,ry},ink,value);
            float by=ry+17*scale;dl->AddRectFilled({rx,by},{rx+rw,by+5*scale},IM_COL32(225,233,238,255),2*scale);
            if(rates[i].pct>0)dl->AddRectFilled({rx,by},{rx+rw*(float)(rates[i].pct/100.0),by+5*scale},rates[i].color,2*scale);}
    }
    text(at.x+14*scale,end.y-19*scale,"Indicador estimado: confiança da diretoria + posição na liga; metas por categoria não disponíveis.",muted,8);
}
int office_date_weekday(int date){
    int year=date/10000,month=date/100%100,day=date%100;if(year<2008||year>2100||month<1||month>12||day<1||day>31)return -1;
    int a=(14-month)/12,y=year+4800-a,m=month+12*a-3;
    int julian=day+(153*m+2)/5+365*y+y/4-y/100+y/400-32045;
    return (julian+1)%7;
}
void office_next_match_draw_card(float x,float y,float width,float height,const CareerNextMatchFacts&match,bool hovered){
    auto*dl=ImGui::GetWindowDrawList();ImVec2 at={x,y},end={x+width,y+height};
    float scale=std::clamp(std::min(width/440.f,height/330.f),.48f,1.f),pad=16.f*scale;
    ImU32 ink=IM_COL32(26,42,52,255),muted=IM_COL32(100,119,131,255),blue=IM_COL32(20,105,159,255),line=IM_COL32(215,225,232,255);
    dl->AddRectFilled({at.x+3,at.y+4},{end.x+3,end.y+4},IM_COL32(11,43,63,22),8*scale);
    dl->AddRectFilled(at,end,IM_COL32(249,251,252,255),8*scale);
    dl->AddRectFilled({at.x,at.y},{end.x,at.y+4*scale},blue,8*scale);
    dl->AddRect(at,end,hovered?IM_COL32(20,112,172,255):IM_COL32(194,211,223,255),8*scale,0,hovered?2.f:1.f);
    auto draw_text=[&](float tx,float ty,const std::string&value,ImU32 color,float size,float max_width){
        if(value.empty()||max_width<=0)return;dl->PushClipRect({tx,ty},{tx+max_width,ty+size*1.55f},true);dl->AddText(nullptr,size,{tx,ty},color,value.c_str());dl->PopClipRect();};
    auto draw_raw=[&](float tx,float ty,const char*value,ImU32 color,float size,float max_width){draw_text(tx,ty,value?std::string(value):std::string(),color,size,max_width);};
    draw_raw(at.x+pad,at.y+12*scale,"PRÓXIMA PARTIDA",blue,11*scale,width-2*pad);
    if(!match.valid){
        draw_raw(at.x+pad,at.y+62*scale,"Nenhuma partida agendada",ink,17*scale,width-2*pad);
        draw_raw(at.x+pad,at.y+91*scale,"A agenda da carreira ainda não informa o próximo jogo.",muted,12*scale,width-2*pad);
        return;
    }
    static const char*months[]={"janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"};
    static const char*weekdays[]={"domingo","segunda-feira","terça-feira","quarta-feira","quinta-feira","sexta-feira","sábado"};
    int year=match.match_date/10000,month=match.match_date/100%100,day=match.match_date%100;
    char date[96]={};if(month>=1&&month<=12&&day>=1&&day<=31){int weekday=office_date_weekday(match.match_date);
        if(weekday>=0&&weekday<7)_snprintf_s(date,sizeof(date),_TRUNCATE,"%s, %d de %s de %d",weekdays[weekday],day,months[month-1],year);
        else _snprintf_s(date,sizeof(date),_TRUNCATE,"%02d/%02d/%04d",day,month,year);}
    else lstrcpynA(date,"Data indisponível",sizeof(date));
    std::string date_text=utf8(date);for(char&c:date_text)if(c>='a'&&c<='z')c=(char)(c-'a'+'A');
    int days=-1;auto date_ordinal=[](int value){int yy=value/10000,mm=value/100%100,dd=value%100,a=(14-mm)/12,yy2=yy+4800-a,mm2=mm+12*a-3;return dd+(153*mm2+2)/5+365*yy2+yy2/4-yy2/100+yy2/400-32045;};
    if(office_date_weekday(match.calendar_date)>=0&&office_date_weekday(match.match_date)>=0)days=date_ordinal(match.match_date)-date_ordinal(match.calendar_date);
    char status[32]={};if(days==0)lstrcpynA(status,"HOJE",sizeof(status));else if(days==1)lstrcpynA(status,"AMANHÃ",sizeof(status));
    else if(days>1)sprintf_s(status,"EM %d DIAS",days);else lstrcpynA(status,"DATA",sizeof(status));
    ImVec2 pill_size=ImGui::GetFont()->CalcTextSizeA(10*scale,FLT_MAX,0,status);float pill_w=pill_size.x+18*scale,pill_h=21*scale;
    ImVec2 pill_min={end.x-pad-pill_w,at.y+29*scale},pill_max={end.x-pad,at.y+29*scale+pill_h};
    dl->AddRectFilled(pill_min,pill_max,IM_COL32(227,240,248,255),pill_h*.5f);
    dl->AddText(nullptr,10*scale,{pill_min.x+9*scale,pill_min.y+4*scale},blue,status);
    float date_max=std::max(30.f,pill_min.x-(at.x+pad)-10*scale);
    draw_text(at.x+pad,at.y+31*scale,date_text,ink,16*scale,date_max);
    dl->AddLine({at.x+pad,at.y+61*scale},{end.x-pad,at.y+61*scale},line,1.f);

    float comp_y=at.y+72*scale,icon_size=25*scale;bool icons_match=visible_icons&&visible_icons->office_next_match.valid&&
        visible_icons->office_next_match.fixture==match.fixture&&visible_icons->office_next_match.home_team==match.home_team&&visible_icons->office_next_match.away_team==match.away_team&&
        visible_icons->office_next_match.competition_asset==match.competition_asset;
    if(icons_match&&office_next_competition_view)dl->AddImage((ImTextureID)(intptr_t)office_next_competition_view,{at.x+pad,comp_y},{at.x+pad+icon_size,comp_y+icon_size});
    else {dl->AddCircleFilled({at.x+pad+icon_size*.5f,comp_y+icon_size*.5f},icon_size*.46f,IM_COL32(226,235,241,255));dl->AddText(nullptr,10*scale,{at.x+pad+icon_size*.27f,comp_y+icon_size*.27f},muted,"C");}
    std::string competition=icons_match?utf8(visible_icons->office_next_competition_name.c_str()):std::string();
    if(competition.empty())competition="Competição da carreira";
    draw_text(at.x+pad+icon_size+8*scale,comp_y+5*scale,competition,IM_COL32(58,83,99,255),12*scale,width-2*pad-icon_size-8*scale);
    dl->AddLine({at.x+pad,at.y+108*scale},{end.x-pad,at.y+108*scale},line,1.f);

    float crest_size=39*scale,crest_y=at.y+122*scale,crest_gap=7*scale;
    float crest_x=at.x+pad;
    if(icons_match&&office_next_home_crest_view)dl->AddImage((ImTextureID)(intptr_t)office_next_home_crest_view,{crest_x,crest_y},{crest_x+crest_size,crest_y+crest_size});
    else {dl->AddCircleFilled({crest_x+crest_size*.5f,crest_y+crest_size*.5f},crest_size*.47f,IM_COL32(230,237,242,255));}
    float away_x=crest_x+crest_size+crest_gap;
    if(icons_match&&office_next_away_crest_view)dl->AddImage((ImTextureID)(intptr_t)office_next_away_crest_view,{away_x,crest_y},{away_x+crest_size,crest_y+crest_size});
    else {dl->AddCircleFilled({away_x+crest_size*.5f,crest_y+crest_size*.5f},crest_size*.47f,IM_COL32(230,237,242,255));}
    float names_x=away_x+crest_size+10*scale,rank_w=34*scale,names_w=std::max(20.f,end.x-pad-rank_w-names_x);
    draw_raw(names_x,at.y+119*scale,"CASA",muted,9*scale,names_w);
    draw_text(names_x,at.y+131*scale,utf8(match.home_name),ink,13*scale,names_w);
    draw_raw(names_x,at.y+155*scale,"FORA",muted,9*scale,names_w);
    draw_text(names_x,at.y+167*scale,utf8(match.away_name),ink,13*scale,names_w);
    char home_rank[16]={},away_rank[16]={};if(match.home_rank>0)_snprintf_s(home_rank,sizeof(home_rank),_TRUNCATE,"%dº",match.home_rank);else lstrcpynA(home_rank,"—",sizeof(home_rank));
    if(match.away_rank>0)_snprintf_s(away_rank,sizeof(away_rank),_TRUNCATE,"%dº",match.away_rank);else lstrcpynA(away_rank,"—",sizeof(away_rank));
    float rank_x=end.x-pad-rank_w;
    draw_raw(rank_x,at.y+132*scale,home_rank,muted,12*scale,rank_w);
    draw_raw(rank_x,at.y+168*scale,away_rank,muted,12*scale,rank_w);
    dl->AddLine({at.x+pad,at.y+195*scale},{end.x-pad,at.y+195*scale},line,1.f);

    std::string stadium=match.venue_pending?"Estádio a definir":utf8(match.stadium);
    if(stadium.empty())stadium="Estádio indisponível";
    draw_text(at.x+pad,at.y+205*scale,stadium,ink,13*scale,width-2*pad);
    std::string location=match.venue_pending?"Localização pendente":utf8(match.location);
    if(location.empty())location="Localização indisponível";
    draw_text(at.x+pad,at.y+223*scale,location,muted,11*scale,width-2*pad);
    dl->AddLine({at.x+pad,at.y+246*scale},{end.x-pad,at.y+246*scale},line,1.f);
    char time[32]={};if(match.match_time>=0&&match.match_time<2400&&match.match_time%100<60)_snprintf_s(time,sizeof(time),_TRUNCATE,"%02d:%02d",match.match_time/100,match.match_time%100);
    else lstrcpynA(time,"Horário indisponível",sizeof(time));
    draw_raw(at.x+pad,at.y+256*scale,time,blue,12*scale,width-2*pad);
    std::string referee="Árbitro: ";referee+=match.referee[0]?utf8(match.referee):"informação indisponível";
    draw_text(at.x+pad,at.y+276*scale,referee,muted,10*scale,width-2*pad);
}
void office_training_draw(float x,float y,float width,float height,bool ready){
    ImGui::SetCursorScreenPos({x,y});ImGui::BeginChild("Treinamento do elenco##OfficeTraining",{width,height},false,ImGuiWindowFlags_NoNavInputs);
    ImGui::SetWindowFontScale(1.28f);ImGui::TextUnformatted("Treinamento do elenco");ImGui::SetWindowFontScale(1);
    ImGui::SameLine();ImGui::TextDisabled("Indicadores atuais do plantel");ImGui::Separator();
    int overall_sum=0,overall_count=0,stamina_sum=0,stamina_count=0;
    for(const auto&r:visible){if(r.overall>0&&r.overall<=99){overall_sum+=r.overall;++overall_count;}
        int stamina=r.attributes[19];if(stamina>=0&&stamina<=99){stamina_sum+=stamina;++stamina_count;}}
    float gap=10.f,card_w=(ImGui::GetContentRegionAvail().x-gap*2)/3.f;ImVec2 start=ImGui::GetCursorScreenPos();
    const char*labels[]={"JOGADORES NO ELENCO","OVERALL MÉDIO","RESISTÊNCIA MÉDIA"};
    char values[3][32]{};_snprintf_s(values[0],sizeof(values[0]),_TRUNCATE,"%zu",visible.size());
    if(overall_count)_snprintf_s(values[1],sizeof(values[1]),_TRUNCATE,"%d",overall_sum/overall_count);else lstrcpynA(values[1],"—",sizeof(values[1]));
    if(stamina_count)_snprintf_s(values[2],sizeof(values[2]),_TRUNCATE,"%d",stamina_sum/stamina_count);else lstrcpynA(values[2],"—",sizeof(values[2]));
    ImU32 blue=IM_COL32(10,91,145,255),ink=IM_COL32(35,65,82,255),muted=IM_COL32(101,123,137,255);
    for(int i=0;i<3;++i){ImVec2 a={start.x+i*(card_w+gap),start.y},b={a.x+card_w,a.y+84};
        ImGui::GetWindowDrawList()->AddRectFilled(a,b,IM_COL32(244,248,251,255),7);
        ImGui::GetWindowDrawList()->AddRect(a,b,IM_COL32(211,224,233,255),7,0,1);
        ImGui::GetWindowDrawList()->AddText({a.x+12,a.y+11},muted,labels[i]);
        ImGui::GetWindowDrawList()->AddText(nullptr,25,{a.x+12,a.y+34},blue,values[i]);}
    ImGui::Dummy({1,94});ImGui::TextUnformatted("ELENCO · ATRIBUTOS ATUAIS");
    ImGui::SameLine();ImGui::TextDisabled("Resistência é o atributo base do jogador, não energia ou fadiga.");
    float table_h=std::max(100.f,ImGui::GetContentRegionAvail().y-42.f);
    ImGui::BeginChild("Lista de treino do elenco",{0,table_h},true,ImGuiWindowFlags_NoNavInputs);
    if(visible.empty())ImGui::TextDisabled("Aguardando o elenco da carreira...");
    else if(ImGui::BeginTable("OfficeTrainingRoster",6,ImGuiTableFlags_RowBg|ImGuiTableFlags_BordersInnerH|ImGuiTableFlags_SizingStretchProp|ImGuiTableFlags_ScrollY)){
        ImGui::TableSetupColumn("JOGADOR",ImGuiTableColumnFlags_WidthStretch,2.8f);ImGui::TableSetupColumn("POS.",ImGuiTableColumnFlags_WidthFixed,72);
        ImGui::TableSetupColumn("IDADE",ImGuiTableColumnFlags_WidthFixed,72);ImGui::TableSetupColumn("GER",ImGuiTableColumnFlags_WidthFixed,72);
        ImGui::TableSetupColumn("RESIST.",ImGuiTableColumnFlags_WidthFixed,86);ImGui::TableSetupColumn("REFERÊNCIA",ImGuiTableColumnFlags_WidthStretch,1.1f);
        ImGui::TableHeadersRow();office_training_row=std::clamp(office_training_row,0,(int)visible.size()-1);
        for(size_t i=0;i<visible.size();++i){const auto&r=visible[i];ImGui::TableNextRow(ImGuiTableRowFlags_None,31);ImGui::TableSetColumnIndex(0);
            if(ImGui::Selectable(r.name[0]?r.name:"Jogador",office_training_row==(int)i,ImGuiSelectableFlags_SpanAllColumns|ImGuiSelectableFlags_AllowItemOverlap,{0,29})){
                office_training_row=(int)i;if(ready)office_focus=11;}
            ImGui::TableSetColumnIndex(1);ImGui::TextUnformatted(club_profile::position(r.position));
            ImGui::TableSetColumnIndex(2);if(r.age>=0&&r.age<=100)ImGui::Text("%d",r.age);else ImGui::TextUnformatted("—");
            ImGui::TableSetColumnIndex(3);if(r.overall>0&&r.overall<=99)ImGui::Text("%d",r.overall);else ImGui::TextUnformatted("—");
            int stamina=r.attributes[19];ImGui::TableSetColumnIndex(4);if(stamina>=0&&stamina<=99)ImGui::Text("%d",stamina);else ImGui::TextUnformatted("—");
            ImGui::TableSetColumnIndex(5);if(stamina<0||stamina>99)ImGui::TextDisabled("Sem dado");else if(stamina<60)ImGui::TextColored({.72f,.29f,.25f,1},"Atenção à resistência");
                else if(stamina>=80)ImGui::TextColored({.12f,.48f,.34f,1},"Boa resistência");else ImGui::TextDisabled("Faixa intermediária");
        }ImGui::EndTable();}
    ImGui::EndChild();ImGui::TextDisabled("O save ainda não fornece sessões, notas nem evolução de treino ao mod; esta página mostra somente os atributos confirmados.");
    ImGui::EndChild();
}
void draw_office(const XINPUT_STATE&pad,WORD pressed,bool ready){
    screen_visuals::LightTheme theme;theme.color(ImGuiCol_Text,player_profile::ink());theme.color(ImGuiCol_WindowBg,{1,1,1,1});
    auto&io=ImGui::GetIO();DWORD now=GetTickCount();int horizontal=0,vertical=0,office_comp_horizontal=0,office_comp_vertical=0;bool office_comp_confirm=false;
    if(!office_last_advance)office_last_advance=now;
    if(office_main_page==0&&(DWORD)(now-office_last_advance)>=40000)office_select_slide(office_slide+1,now,1);
    if(ready){
        if(ImGui::IsKeyPressed(ImGuiKey_LeftArrow)||(pressed&XINPUT_GAMEPAD_DPAD_LEFT))horizontal=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_RightArrow)||(pressed&XINPUT_GAMEPAD_DPAD_RIGHT))horizontal=1;
        if(ImGui::IsKeyPressed(ImGuiKey_UpArrow)||(pressed&XINPUT_GAMEPAD_DPAD_UP))vertical=-1;
        if(ImGui::IsKeyPressed(ImGuiKey_DownArrow)||(pressed&XINPUT_GAMEPAD_DPAD_DOWN))vertical=1;
        if((LONG)(now-office_repeat)>=0){
            if(!horizontal&&abs(pad.Gamepad.sThumbLX)>16000)horizontal=pad.Gamepad.sThumbLX>0?1:-1;
            if(!vertical&&abs(pad.Gamepad.sThumbLY)>16000)vertical=pad.Gamepad.sThumbLY<0?1:-1;
            if(horizontal||vertical)office_repeat=now+180;
        }
        int old_page=office_main_page;
        if(office_menu<0){
            if(office_main_page==0&&office_focus==8){
                if(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER)office_social_runtime.social_index=(office_social_runtime.social_index+4)%5;
                else if(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER)office_social_runtime.social_index=(office_social_runtime.social_index+1)%5;
            }else if(pressed&XINPUT_GAMEPAD_LEFT_SHOULDER)office_main_page=(office_main_page+1)%3;
            else if(pressed&XINPUT_GAMEPAD_RIGHT_SHOULDER)office_main_page=(office_main_page+2)%3;
        }
        if(old_page!=office_main_page){office_focus=office_main_page==0?7:office_main_page==1?10:11;office_transition_from=-1;}
        bool activate=ImGui::IsKeyPressed(ImGuiKey_Enter)||ImGui::IsKeyPressed(ImGuiKey_Space)||(pressed&XINPUT_GAMEPAD_A);
        if(office_menu>=0){
            if(horizontal){office_activate((office_focus+horizontal+6)%6);}
            else if(vertical)office_item=std::clamp(office_item+vertical,0,office_submenu_count(office_menu)-1);
            if(activate)office_menu_activate();
        }else if(office_main_page==0){
            if(horizontal){if(office_focus==8)office_social_runtime.social_index=(office_social_runtime.social_index+horizontal+5)%5;
                else if(office_focus<6)office_focus=(office_focus+horizontal+6)%6;
                else if(office_focus==6&&horizontal>0)office_focus=7;else if(office_focus==7)office_focus=horizontal<0?6:10;
                else if(office_focus==10&&horizontal<0)office_focus=7;
                else if(office_focus==9&&horizontal<0)office_focus=8;}
            if(vertical){if(vertical>0){if(office_focus<3)office_focus=6;else if(office_focus<6)office_focus=7;else if(office_focus==6)office_focus=8;else if(office_focus==7||office_focus==8||office_focus==10)office_focus=9;}
                else {if(office_focus==6)office_focus=0;else if(office_focus==7)office_focus=3;else if(office_focus==10)office_focus=5;else if(office_focus==8)office_focus=6;else if(office_focus==9)office_focus=7;}}
            if(ImGui::IsKeyPressed(ImGuiKey_Tab))office_focus=(office_focus+1)%11;
            if(office_focus==7){int slide=0;
                if(ImGui::IsKeyPressed(ImGuiKey_Q))slide=-1;
                if(ImGui::IsKeyPressed(ImGuiKey_E))slide=1;
                if(slide)office_select_slide(office_slide+slide,now,slide);
            }
            else if(office_focus==8){int slide=0;if(ImGui::IsKeyPressed(ImGuiKey_Q))slide=-1;
                if(ImGui::IsKeyPressed(ImGuiKey_E))slide=1;
                if(slide)office_social_runtime.social_index=(office_social_runtime.social_index+slide+5)%5;}
            if(activate)office_activate(office_focus);
        }else if(office_main_page==1){
            if(office_focus<6){if(horizontal)office_focus=(office_focus+horizontal+6)%6;if(vertical>0)office_focus=10;}
            else{office_comp_horizontal=horizontal;office_comp_vertical=vertical;office_comp_confirm=activate;}
        }else{
            if(office_focus<6){if(horizontal)office_focus=(office_focus+horizontal+6)%6;if(vertical>0)office_focus=11;}
            else{office_focus=11;if(vertical&&!visible.empty())office_training_row=std::clamp(office_training_row+vertical,0,(int)visible.size()-1);
                if(activate&&!visible.empty()){office_training_row=std::clamp(office_training_row,0,(int)visible.size()-1);club_home=false;office_home=false;from_home=true;group_mode=true;full_squad_mode=false;open_details(office_training_row);}}
        }
    }
    ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{0,0});ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,0);
    ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,0);ImGui::PushStyleVar(ImGuiStyleVar_FrameBorderSize,0);ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding,0);
    ImGui::SetNextWindowPos({0,0});ImGui::SetNextWindowSize(io.DisplaySize);
    ImGui::Begin("Meu escritório##MyOffice",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoMove|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoScrollbar|ImGuiWindowFlags_NoScrollWithMouse);
    ImVec2 top=ImGui::GetCursorScreenPos();float width=ImGui::GetContentRegionAvail().x,available=ImGui::GetContentRegionAvail().y;
    float header=66,crest_space=76,slot=(width-crest_space)/6;
    unsigned rgb=visible.empty()||!visible.front().club_colors_valid?0x07558d:visible.front().club_colors[0];
    const ImU32 focus_color=IM_COL32(255,255,255,255);
    const ImU32 normal_color=IM_COL32(255,255,255,220);
    auto*dl=ImGui::GetWindowDrawList();dl->AddRectFilled(top,{top.x+width,top.y+header},IM_COL32((rgb>>16)&255,(rgb>>8)&255,rgb&255,255));
    const char*headings[]={"Gerenciamento do time","Informações do time","Base de dados","Escritório do técnico","Transferências","Finanças"};
    ImVec2 menu_anchor={};float menu_width=0;bool toggled=false;
    for(int i=0;i<6;++i){float x=top.x+slot*i+(i>=3?crest_space:0);ImVec2 a={x,top.y},b={x+slot,top.y+header};office_centers[i]={(a.x+b.x)*.5f,top.y+header*.5f};
        ImGui::SetCursorScreenPos(a);ImGui::PushID(i);ImGui::InvisibleButton("Menu",{slot,header});bool hovered=ImGui::IsItemHovered();
        if(ready&&hovered&&(io.MouseDelta.x||io.MouseDelta.y))office_focus=i;
        if(ready&&ImGui::IsItemClicked()){office_focus=i;office_activate(i);toggled=true;}
        bool focus=office_focus==i||office_menu==i;
        ImFont*regular_font=io.Fonts->Fonts.Size>0?io.Fonts->Fonts[0]:ImGui::GetFont();
        ImFont*bold_font=io.Fonts->Fonts.Size>1?io.Fonts->Fonts[1]:regular_font;
        ImFont*header_font=focus?bold_font:regular_font;
        float font=focus?15.f:14.f,text_width=header_font->CalcTextSizeA(font,FLT_MAX,0,headings[i]).x;
        if(text_width>slot-12){font*=std::max(.6f,(slot-12)/text_width);text_width=header_font->CalcTextSizeA(font,FLT_MAX,0,headings[i]).x;}
        ImVec2 text={x+(slot-text_width)*.5f,top.y+(header-font)*.5f};ImU32 color=focus?focus_color:normal_color;
        // Keep every title white; focus is communicated only by a bolder, slightly larger label.
        dl->AddText(header_font,font,{text.x+1,text.y+1},IM_COL32(0,0,0,125),headings[i]);dl->AddText(header_font,font,text,color,headings[i]);
        if(office_menu==i){menu_anchor={x,top.y+header+2};menu_width=std::max(235.f,slot+36);}
        ImGui::PopID();
    }
    float emblem=78;ImVec2 logo={top.x+width*.5f-emblem*.5f,top.y-1};
    CareerNextMatchFacts latest_match={};career_next_match_copy(visible_club,&latest_match);
    if(memcmp(&latest_match,&office_match_card,sizeof(latest_match))!=0){office_match_card=latest_match;if(office_mode)queue_preview();}
    bool pointer_moved=io.MouseDelta.x||io.MouseDelta.y;
    if(office_main_page>0&&ready&&pointer_moved&&ImGui::IsMouseHoveringRect({top.x,top.y+header},{top.x+width,top.y+available-28},true))
        office_focus=office_main_page==1?10:11;
    const char*page_labels[]={"GERAL","COMPETIÇÃO","TREINAMENTO"};
    const float page_margin=std::clamp(width*.015f,14.f,30.f),page_gap=8.f;
    const float page_width=(width-page_margin*2-page_gap*2)/3.f;
    for(int page=0;page<3;++page){
        ImVec2 a={top.x+page_margin+page*(page_width+page_gap),top.y+header+5};
        ImVec2 b={a.x+page_width,a.y+32};
        ImGui::SetCursorScreenPos(a);ImGui::PushID(100+page);ImGui::InvisibleButton("Office page",{page_width,32});
        bool hovered=ImGui::IsItemHovered();
        if(ready&&office_menu<0&&hovered&&(io.MouseDelta.x||io.MouseDelta.y))office_focus=page==0?7:page==1?10:11;
        if(ready&&office_menu<0&&ImGui::IsItemClicked()){
            office_main_page=page;office_focus=page==0?7:page==1?10:11;office_transition_from=-1;
        }
        bool selected_page=office_main_page==page;ImU32 text_color=selected_page?IM_COL32(10,91,145,255):IM_COL32(91,111,124,255);
        if(selected_page)dl->AddRectFilled(a,b,IM_COL32(231,241,248,255),5);
        ImVec2 label_size=ImGui::CalcTextSize(page_labels[page]);
        dl->AddText({a.x+(page_width-label_size.x)*.5f,a.y+8},text_color,page_labels[page]);
        if(selected_page)dl->AddRectFilled({a.x+page_width*.28f,b.y-3},{a.x+page_width*.72f,b.y},IM_COL32(10,91,145,255),2);
        else if(hovered)dl->AddRect(a,b,IM_COL32(194,214,228,255),5,0,1);
        ImGui::PopID();
    }
    const float page_content_y=top.y+header+43;
    const float page_content_h=std::max(100.f,available-header-86);
    if(office_main_page==1){
        club_competitions_screen_draw_office(top.x+page_margin,page_content_y,width-page_margin*2,page_content_h,
            latest_match.valid?latest_match.competition_asset:0,office_comp_horizontal,office_comp_vertical,office_comp_confirm,ready&&office_menu<0);
    }else if(office_main_page==2){
        office_training_draw(top.x+page_margin,page_content_y,width-page_margin*2,page_content_h,ready&&office_menu<0);
    }else{
    // 1:2:1 cards use only the upper portion; the lower content area stays blank.
    float gap=8,side_margin=page_margin,inner_width=width-side_margin*2-gap*2;
    float row_y=page_content_y,row_h=std::clamp(page_content_h*.56f,220.f,400.f),unit=inner_width/4;
    float sizes[3]={unit,unit*2,unit},x=top.x+side_margin;
    std::shared_ptr<const fifa_player::Model>team_model;
    {std::lock_guard<std::mutex>guard(lock);if(ready_serial==request_serial)team_model=ready_model;}
    CareerNewsItem news[CAREER_NEWS_CAPACITY]={};size_t news_count=career_news_copy(visible_club,news,CAREER_NEWS_CAPACITY);
    OfficeSquadSummary squad_summary=office_squad_summary();
    for(int i=0;i<3;++i){ImVec2 at={x,row_y},end={x+sizes[i],row_y+row_h};bool selectable=true,blocked=office_menu>=0;
        bool card_hovered=false;
        int id=i==2?10:6+i;
        if(selectable){office_centers[id]={(at.x+end.x)*.5f,(at.y+end.y)*.5f};
            ImGui::SetCursorScreenPos(at);ImGui::PushID(id);ImGui::InvisibleButton("Cena",{sizes[i],row_h});
            card_hovered=ImGui::IsItemHovered();if(ready&&!blocked&&card_hovered&&pointer_moved)office_focus=id;
            bool dot_click=i==1&&io.MousePos.y>end.y-24&&fabsf(io.MousePos.x-(at.x+sizes[i]*.5f))<60;
            if(ready&&!blocked&&ImGui::IsItemClicked()&&!dot_click){office_focus=id;mouse_card_press=id;mouse_card_travel=0;}
            if(mouse_card_press==id&&ImGui::IsMouseDown(0))mouse_card_travel+=fabsf(io.MouseDelta.x)+fabsf(io.MouseDelta.y);
            if(mouse_card_press==id&&ImGui::IsMouseReleased(0)){if(ready&&!blocked&&ImGui::IsItemHovered()&&mouse_card_travel<=6)office_activate(id);mouse_card_press=-1;}
            ImGui::PopID();}
        else {card_hovered=ImGui::IsMouseHoveringRect(at,end,true);if(card_hovered&&pointer_moved)ImGui::SetMouseCursor(ImGuiMouseCursor_Hand);}
        dl->AddRectFilled(at,end,IM_COL32(255,255,255,255));
        if(i<2){
            ImVec2 stage={sizes[i],row_h-54};bool rendered=false;auto model=i==0?(visible_icons?visible_icons->arrival:nullptr):team_model;
            if(i==0&&model){float phase=(float)now*.0008f,walk_x=11.f*sinf(phase),walk_y=1.2f*fabsf(sinf(phase));
                rendered=office_coach_renderer.model(model)&&office_coach_renderer.render((UINT)stage.x,(UINT)stage.y,0,1.02f,false,0,0,false,.50f,nullptr,walk_x,walk_y);}
            if(i==1&&lineup_valid&&team_model&&team_model->player_count==11){
                if(office_lineup_source!=team_model){office_lineup_source=team_model;
                    auto menu_scene=std::make_shared<fifa_player::Model>(*team_model);menu_scene->room=fifa_player::RoomOfficeLineup;office_lineup_model=std::move(menu_scene);}
                rendered=office_lineup_model&&office_lineup_renderer.model(office_lineup_model)&&office_lineup_renderer.render((UINT)stage.x,(UINT)stage.y,0,1.08f);
            }
            if(i==0){
                ImVec2 image_at=at;auto*image=office_coach_renderer.image();
                if(rendered&&image)dl->AddImage((ImTextureID)(intptr_t)image,image_at,{image_at.x+stage.x,image_at.y+stage.y});
                else {const char*status=!visible_icons?"Carregando...":"Modelo do técnico indisponível";dl->AddText(nullptr,0,{at.x+12,at.y+stage.y*.5f},IM_COL32(62,103,132,255),status,nullptr,stage.x-24);}
                auto title=utf8(visible_icons?visible_icons->card.context.name:"Treinador");
                dl->AddText(nullptr,0,{at.x+12,at.y+stage.y+10},IM_COL32(7,79,133,255),title.c_str(),nullptr,sizes[i]-24);
            } else {
                float transition=1.f;bool animating=office_transition_from>=0;
                if(animating){float raw=std::clamp((float)(DWORD)(now-office_transition_started)/620.f,0.f,1.f);transition=raw*raw*(3.f-2.f*raw);if(raw>=1.f){office_transition_from=-1;animating=false;}}
                float card_width=sizes[i];auto category_name=[](int category)->const char*{switch(category){case 1:return "AGENDA";case 2:return "RESULTADO";case 3:return "CLASSIFICAÇÃO";case 4:return "DESTAQUES";case 5:return "COMISSÃO TÉCNICA";default:return "NOTÍCIA";}};
                auto draw_page=[&](int page,float shift,float opacity){
                    ImVec2 origin={at.x+shift,at.y};ImU32 ink=IM_COL32(35,67,84,(int)(255*opacity)),muted=IM_COL32(91,116,131,(int)(255*opacity));
                    if(page==0){
                        ImVec2 stage_origin=origin;bool xi=lineup_valid&&rendered;
                        if(xi&&office_stadium_view&&visible_icons&&visible_icons->office_stadium&&visible_icons->office_stadium->height){
                            float source_aspect=(float)visible_icons->office_stadium->width/visible_icons->office_stadium->height;
                            float view_height=std::min(1.f,source_aspect/(stage.x/stage.y)),uv_bottom=.92f,uv_top=std::max(0.f,uv_bottom-view_height);
                            dl->AddImage((ImTextureID)(intptr_t)office_stadium_view,stage_origin,{stage_origin.x+stage.x,stage_origin.y+stage.y},{0,uv_top},{1,uv_bottom},IM_COL32(255,255,255,(int)(255*opacity)));
                        }
                        auto*image=office_lineup_renderer.image();
                        if(xi&&image)dl->AddImage((ImTextureID)(intptr_t)image,stage_origin,{stage_origin.x+stage.x,stage_origin.y+stage.y},ImVec2(0,0),ImVec2(1,1),IM_COL32(255,255,255,(int)(255*opacity)));
                        else {const char*status=!visible_icons?"Carregando elenco...":lineup_valid?"Carregando titulares...":"Escalação indisponível";
                            dl->AddText(nullptr,0,{origin.x+18,origin.y+stage.y*.48f},muted,status,nullptr,stage.x-36);}
                        dl->AddText(nullptr,0,{origin.x+18,origin.y+stage.y+11},IM_COL32(7,79,133,(int)(255*opacity)),"Onze titulares");
                        return;
                    }
                    CareerNewsItem item={};
                    if((size_t)(page-1)<news_count)item=news[page-1];
                    else {snprintf(item.title,sizeof(item.title),"Notícia em atualização");snprintf(item.subtitle,sizeof(item.subtitle),"Aguardando dados confirmados do calendário e do elenco desta carreira.");snprintf(item.posting_date,sizeof(item.posting_date),"Data da carreira indisponível");}
                    ImU32 blue=IM_COL32(12,103,163,(int)(255*opacity)),pale=IM_COL32(235,244,249,(int)(255*opacity));
                    dl->AddRectFilled({origin.x+16,origin.y+18},{origin.x+card_width-16,origin.y+stage.y-10},pale,7);
                    dl->AddRectFilled({origin.x+16,origin.y+18},{origin.x+21,origin.y+stage.y-10},blue,2);
                    dl->AddText(nullptr,11,{origin.x+34,origin.y+31},blue,category_name(item.category));
                    char page_label[40]={};snprintf(page_label,sizeof(page_label),"NOTÍCIA %d DE 5",page);
                    ImVec2 label_size=ImGui::CalcTextSize(page_label);dl->AddText(nullptr,10,{origin.x+card_width-34-label_size.x,origin.y+31},muted,page_label);
                    dl->AddText(nullptr,0,{origin.x+34,origin.y+59},ink,item.title,nullptr,card_width-78);
                    float subtitle_y=std::min(113.f,stage.y*.48f);
                    ImVec2 subtitle_min={origin.x+34,origin.y+subtitle_y},subtitle_max={origin.x+card_width-32,origin.y+stage.y-48};
                    dl->PushClipRect(subtitle_min,subtitle_max,true);
                    dl->AddText(nullptr,0,subtitle_min,muted,item.subtitle,nullptr,card_width-68);
                    dl->PopClipRect();
                    dl->AddLine({origin.x+34,origin.y+stage.y-39},{origin.x+card_width-32,origin.y+stage.y-39},IM_COL32(195,213,224,(int)(255*opacity)),1);
                    std::string posted="PUBLICADO EM "+std::string(item.posting_date);
                    dl->AddText(nullptr,10,{origin.x+34,origin.y+stage.y-30},blue,posted.c_str());
                };
                ImVec2 clip_min=at,clip_max={end.x,end.y-25};dl->PushClipRect(clip_min,clip_max,true);
                if(animating){float shift=(1.f-transition)*card_width*office_transition_direction;float old_shift=-transition*card_width*office_transition_direction;
                    draw_page(office_transition_from,old_shift,1.f-transition*.18f);draw_page(office_slide,shift,.72f+.28f*transition);}
                else draw_page(office_slide,0,1.f);
                dl->PopClipRect();
                for(int n=0;n<1+CAREER_NEWS_CAPACITY;++n){float spacing=19.f;ImVec2 dot={at.x+sizes[i]*.5f+(n-(CAREER_NEWS_CAPACITY*.5f))*spacing,end.y-13};office_dots[n]=dot;
                    dl->AddCircleFilled(dot,n==office_slide?4.5f:3.5f,n==office_slide?IM_COL32(8,89,151,255):IM_COL32(187,207,222,255));
                    if(ready&&!blocked&&ImGui::IsMouseClicked(0)&&fabsf(io.MousePos.x-dot.x)<8&&fabsf(io.MousePos.y-dot.y)<8){office_select_slide(n,now);office_focus=7;}}
            }
        }else office_squad_summary_draw_card(at.x,at.y,sizes[i],row_h,squad_summary,office_focus==10||card_hovered);
        bool focus=office_focus==id||card_hovered;if(focus){dl->AddRectFilled({at.x-2,at.y-2},{end.x+2,end.y+3},IM_COL32(8,40,61,21),6);dl->AddRect({at.x-1,at.y-1},{end.x+1,end.y+1},IM_COL32(22,111,170,80),6,0,5);}
        dl->AddRect(at,end,focus?IM_COL32(12,100,159,255):IM_COL32(191,208,220,255),6,0,focus?2.2f:1.f);
        x+=sizes[i]+gap;
    }
    auto social=office_social_signals();office_social_runtime.update(social);
    float social_y=row_y+row_h+10,social_bottom=top.y+available-30,social_h=std::max(180.f,social_bottom-social_y);
    office_social_draw_card(social,top.x+side_margin,social_y,sizes[0],social_h,ready&&office_menu<0);
    CareerNewsManagerFacts manager=office_manager_facts();
    office_manager_draw_card(social,manager,top.x+side_margin+sizes[0]+gap,social_y,sizes[1],social_h,ready&&office_menu<0);
    office_next_match_draw_card(top.x+side_margin+sizes[0]+gap+sizes[1]+gap,social_y,sizes[2],social_h,office_match_card,false);
    }
    // Draw the floating crest LAST: its lower tip overlaps the central card,
    // not clipped to the bar and not hidden behind the scene's image.
    if(crest_view)dl->AddImage((ImTextureID)(intptr_t)crest_view,logo,{logo.x+emblem,logo.y+emblem});
    // Small game-style navigation hint, not development/provenance text.
    ImGui::SetCursorScreenPos({top.x+12,top.y+available-20});ImGui::SetWindowFontScale(.8f);
    if(ImGui::SmallButton("Voltar")){if(office_menu>=0)office_close_submenu();else mod_screen_request_back();}ImGui::SameLine(0,12);
    ImGui::TextUnformatted("L1: próxima aba  ·  R1: aba anterior  ·  Setas: navegar  ·  A: selecionar  ·  B/Esc: voltar");ImGui::SetWindowFontScale(1);
    ImGui::End();
    if(office_menu>=0&&office_home){
        int count=office_submenu_count(office_menu);ImGui::SetNextWindowPos(menu_anchor);ImGui::SetNextWindowSize({menu_width,12+count*38.f});
        ImVec4 club=office_club_color();bool light_club=office_header_uses_dark_text(visible.empty()||!visible.front().club_colors_valid?0x07558d:visible.front().club_colors[0]);
        ImVec4 panel=light_club?office_blend(club,{.035f,.17f,.29f,1},.58f):club;
        ImVec4 base_text={1,1,1,.82f},selected_text={1,1,1,1};
        ImVec4 outline=light_club?office_blend(club,{.18f,.25f,.30f,1},.38f):office_blend(club,{1,1,1,1},.38f);
        ImGui::PushStyleColor(ImGuiCol_WindowBg,panel);ImGui::PushStyleColor(ImGuiCol_Border,outline);ImGui::PushStyleColor(ImGuiCol_Text,base_text);
        // Hover/selection never paints a separate block: only the label changes weight and brightness.
        ImGui::PushStyleColor(ImGuiCol_Button,panel);ImGui::PushStyleColor(ImGuiCol_ButtonHovered,panel);ImGui::PushStyleColor(ImGuiCol_ButtonActive,panel);
        ImGui::PushStyleVar(ImGuiStyleVar_WindowBorderSize,1);ImGui::PushStyleVar(ImGuiStyleVar_WindowRounding,5);ImGui::PushStyleVar(ImGuiStyleVar_FrameRounding,3);
        ImGui::PushStyleVar(ImGuiStyleVar_WindowPadding,{6,6});
        ImGui::Begin("Opções##OfficeMenu",nullptr,ImGuiWindowFlags_NoDecoration|ImGuiWindowFlags_NoSavedSettings|ImGuiWindowFlags_NoNavInputs|ImGuiWindowFlags_NoMove);
        for(int i=0;i<count;++i){const char*name=office_menu==0?"Formação do time":office_menu==2?(i==0?"Ranking mundial":i==1?"Ver outros times":i==2?"Ver outras ligas":i==3?"Competições do meu clube":"Buscar jogador"):
                office_menu==3?(i==0?"Ver estatísticas do treinador":"Sala de troféus"):office_menu==4?(i==0?"Mercado da bola":i==1?"Minhas transferências":"Ligas") :"Empréstimos";
            bool focused=office_item==i;if(focused){ImGui::PushFont(io.Fonts->Fonts.Size>1?io.Fonts->Fonts[1]:ImGui::GetFont());ImGui::PushStyleColor(ImGuiCol_Text,selected_text);}
            bool clicked=ImGui::Button(name,{-1,34});auto a=ImGui::GetItemRectMin(),b=ImGui::GetItemRectMax();office_menu_centers[i]={(a.x+b.x)*.5f,(a.y+b.y)*.5f};
            if(focused){ImGui::PopStyleColor();ImGui::PopFont();}
            if(ready&&ImGui::IsItemHovered()&&(io.MouseDelta.x||io.MouseDelta.y))office_item=i;
            if(ready&&clicked){office_item=i;office_menu_activate();break;}}
        bool outside=ImGui::IsMouseClicked(0)&&!ImGui::IsWindowHovered(ImGuiHoveredFlags_AllowWhenBlockedByActiveItem)&&!toggled;
        ImGui::End();ImGui::PopStyleVar(4);ImGui::PopStyleColor(6);if(ready&&outside)office_close_submenu();
    }
    ImGui::PopStyleVar(5);
}
