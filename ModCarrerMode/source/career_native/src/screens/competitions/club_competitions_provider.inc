/* Builds an owned, render-safe snapshot from the same career competition
 * list/table already backing FIFA's Competition tab. */
static int native_active_competition_trophy(int competition_id,int title_asset);
static int club_competition_row_precedes(const ClubCompetitionTableRow*a,const ClubCompetitionTableRow*b){
    int gd_a=a->goals_for-a->goals_against,gd_b=b->goals_for-b->goals_against;
    if(a->points!=b->points)return a->points>b->points;if(a->won!=b->won)return a->won>b->won;
    if(gd_a!=gd_b)return gd_a>gd_b;if(a->goals_for!=b->goals_for)return a->goals_for>b->goals_for;
    return a->team<b->team;
}
static int club_competition_fixture_precedes(const FceFixture*a,const FceFixture*b){
    if(a->date_raw!=b->date_raw)return a->date_raw<b->date_raw;
    if(a->time_raw!=b->time_raw)return a->time_raw<b->time_raw;return a->id<b->id;
}
typedef struct ClubCompetitionPriorRow {
    int source_row,current_rank,points,won,goals_for,goal_difference,removed_match;
} ClubCompetitionPriorRow;
static int club_competition_prior_precedes(const ClubCompetitionPriorRow*a,const ClubCompetitionPriorRow*b){
    if(a->points!=b->points)return a->points>b->points;if(a->won!=b->won)return a->won>b->won;
    if(a->goal_difference!=b->goal_difference)return a->goal_difference>b->goal_difference;
    if(a->goals_for!=b->goals_for)return a->goals_for>b->goals_for;return a->current_rank<b->current_rank;
}
/* Match FIFA Career's POSITION_UP/DOWN logic: reverse each club's latest
 * completed league match, rebuild the previous table, then compare ranks. */
static void club_competition_apply_movements(int root,int stage,int date,ClubCompetitionTableRow*rows,size_t count){
    ClubCompetitionPriorRow prior[CLUB_COMPETITION_TABLE_CAPACITY];int order[CLUB_COMPETITION_TABLE_CAPACITY],previous_rank[CLUB_COMPETITION_TABLE_CAPACITY]={0};
    size_t i,j;if(!rows)return;if(count>CLUB_COMPETITION_TABLE_CAPACITY)count=CLUB_COMPETITION_TABLE_CAPACITY;
    memset(prior,0,sizeof(prior));
    for(i=0;i<count;++i){ClubCompetitionTableRow*r=rows+i;const FceFixture*latest=NULL;int scored=0,conceded=0;
        r->movement=CLUB_COMPETITION_MOVEMENT_UNKNOWN;prior[i].source_row=(int)i;prior[i].current_rank=r->rank;
        prior[i].points=r->points;prior[i].won=r->won;prior[i].goals_for=r->goals_for;prior[i].goal_difference=r->goals_for-r->goals_against;order[i]=(int)i;
        if(r->played<=0)continue;
        for(j=0;j<native_view.fixture_count;++j){const FceFixture*f=native_view.fixtures+j;
            if(!f->played_raw||(fce_date_valid(date)&&f->date_raw>date)||(f->home!=r->team&&f->away!=r->team)||
               native_fixture_root(f)!=root||!native_fixture_stage_matches(f,stage))continue;
            if(!latest||club_competition_fixture_precedes(latest,f))latest=f;
        }
        if(!latest)continue;scored=latest->home==r->team?latest->home_score:latest->away_score;
        conceded=latest->home==r->team?latest->away_score:latest->home_score;
        prior[i].goals_for-=scored;prior[i].goal_difference-=scored-conceded;
        if(scored>conceded){prior[i].points-=3;--prior[i].won;}else if(scored==conceded)--prior[i].points;
        if(prior[i].points<0)prior[i].points=0;if(prior[i].won<0)prior[i].won=0;if(prior[i].goals_for<0)prior[i].goals_for=0;
        prior[i].removed_match=1;
    }
    for(i=0;i<count;++i)for(j=i+1;j<count;++j)if(club_competition_prior_precedes(prior+order[j],prior+order[i])){int swap=order[i];order[i]=order[j];order[j]=swap;}
    for(i=0;i<count;++i)previous_rank[prior[order[i]].source_row]=(int)i+1;
    for(i=0;i<count;++i){ClubCompetitionTableRow*r=rows+i;if(r->played<2||!prior[i].removed_match||!previous_rank[i])continue;
        if(r->rank<previous_rank[i])r->movement=1;else if(r->rank>previous_rank[i])r->movement=-1;else r->movement=0;}
}
static void club_competition_fill_row(int root,int stage,int team,int date,ClubCompetitionTableRow*out){
    const FceStanding*best=NULL;const FceFixture*recent[CLUB_COMPETITION_FORM_SIZE]={0};size_t i,count=0;
    memset(out,0,sizeof(*out));out->team=team;for(i=0;i<CLUB_COMPETITION_FORM_SIZE;++i)out->form[i]=2;
    for(i=0;i<native_view.standing_count;++i){const FceStanding*s=native_view.standings+i;
        if(s->team!=team||s->competition_object!=stage||fce_model_ancestor(&native_view,s->competition_object,3)!=root)continue;
        if(!best||s->played>best->played)best=s;}
    if(best){out->played=(int)best->played;out->won=(int)(best->home_wins+best->away_wins);
        out->drawn=(int)(best->home_draws+best->away_draws);out->lost=(int)(best->home_losses+best->away_losses);
        out->points=out->won*3+out->drawn;}
    native_team_name(team,out->name,sizeof(out->name));
    for(i=0;i<native_view.fixture_count;++i){const FceFixture*f=native_view.fixtures+i;size_t at;
        if(!f->played_raw||(fce_date_valid(date)&&f->date_raw>date)||(f->home!=team&&f->away!=team)||native_fixture_root(f)!=root||!native_fixture_stage_matches(f,stage))continue;
        if(f->home==team){out->goals_for+=f->home_score;out->goals_against+=f->away_score;}
        else{out->goals_for+=f->away_score;out->goals_against+=f->home_score;}
        for(at=0;at<count;++at)if(club_competition_fixture_precedes(recent[at],f))break;
        if(at>=CLUB_COMPETITION_FORM_SIZE)continue;size_t move=count<CLUB_COMPETITION_FORM_SIZE?count:CLUB_COMPETITION_FORM_SIZE-1;
        while(move>at){recent[move]=recent[move-1];--move;}recent[at]=f;if(count<CLUB_COMPETITION_FORM_SIZE)++count;
    }
    for(i=0;i<count;++i){const FceFixture*f=recent[count-1-i];int scored=f->home==team?f->home_score:f->away_score;
        int conceded=f->home==team?f->away_score:f->home_score;out->form[CLUB_COMPETITION_FORM_SIZE-count+i]=scored>conceded?1:scored<conceded?-1:0;}
    if(count){const FceFixture*f=recent[0];int scored=f->home==team?f->home_score:f->away_score;
        int conceded=f->home==team?f->away_score:f->home_score;out->last_match_valid=1;out->last_goals_for=scored;out->last_goals_against=conceded;
        out->last_match_result=scored>conceded?1:scored<conceded?-1:0;}
}
static void club_competition_apply_league_zones(ClubCompetitionTableRow*rows,size_t count){
    size_t i;int direct=0,preliminary=0,continental=0,relegated=0;if(!rows||count<8)return;
    if(count>=20){direct=4;preliminary=2;continental=6;relegated=4;}
    else if(count>=18){direct=4;preliminary=2;continental=4;relegated=3;}
    else if(count>=16){direct=3;preliminary=2;continental=3;relegated=3;}
    else if(count>=12){direct=2;preliminary=1;continental=3;relegated=2;}
    else{direct=2;preliminary=1;continental=2;relegated=2;}
    for(i=0;i<count;++i){int rank=rows[i].rank;if(rank<=direct)rows[i].zone=CLUB_COMPETITION_ZONE_PRIMARY;
        else if(rank<=direct+preliminary)rows[i].zone=CLUB_COMPETITION_ZONE_SECONDARY;
        else if(rank<=direct+preliminary+continental)rows[i].zone=CLUB_COMPETITION_ZONE_SAFE;
        else if(rank>(int)count-relegated)rows[i].zone=CLUB_COMPETITION_ZONE_RELEGATION;
        else rows[i].zone=CLUB_COMPETITION_ZONE_NONE;}
}
static size_t club_competition_fill_table(int root,int stage,int date,int club,ClubCompetitionTableRow*out){
    size_t i,j,count=0;for(i=0;i<native_view.standing_count&&count<CLUB_COMPETITION_TABLE_CAPACITY;++i){const FceStanding*s=native_view.standings+i;
        if(s->team<=0||s->competition_object!=stage||fce_model_ancestor(&native_view,s->competition_object,3)!=root)continue;
        for(j=0;j<count&&out[j].team!=s->team;++j){}if(j<count&&out[j].played>=(int)s->played)continue;
        club_competition_fill_row(root,stage,s->team,date,out+j);if(j==count)++count;}
    for(i=0;i<count;++i)for(j=i+1;j<count;++j)if(club_competition_row_precedes(out+j,out+i)){ClubCompetitionTableRow t=out[i];out[i]=out[j];out[j]=t;}
    for(i=0;i<count;++i){out[i].rank=(int)i+1;if(out[i].team==club)out[i].status=2;}
    return count;
}
static int club_competition_reached_later_stage(int root,int team){size_t i;
    for(i=0;i<native_view.fixture_count;++i){const FceFixture*f=native_view.fixtures+i;int kind;
        if((f->home!=team&&f->away!=team)||native_fixture_root(f)!=root)continue;kind=fce_model_stage_kind(&native_view,f->stage);
        if(kind>FCE_STAGE_GROUP)return 1;}
    for(i=0;i<native_view.standing_count;++i){const FceStanding*s=native_view.standings+i;int kind;
        if(s->team!=team||fce_model_ancestor(&native_view,s->competition_object,3)!=root)continue;kind=fce_model_stage_kind(&native_view,s->competition_object);
        if(kind>FCE_STAGE_GROUP)return 1;}
    return 0;
}
static void club_competition_set_fixture(ClubCompetitionMatch*out,const FceFixture*f){
    if(!out||!f)return;out->visible=1;out->stage=f->stage;out->round=f->round;out->home_team=f->home;out->away_team=f->away;
    out->date=f->date_raw;out->time=f->time_raw;out->played=f->played_raw;out->home_score=f->home_score;out->away_score=f->away_score;out->fixture_id=f->id;
}
static int club_competition_match_precedes(const ClubCompetitionMatch*a,const ClubCompetitionMatch*b){
    if(a->date!=b->date)return a->date<b->date;if(a->time!=b->time)return a->time<b->time;return a->fixture_id<b->fixture_id;
}
static void club_competition_remember_bracket_team(ClubCompetitionEntry*entry,int team){
    size_t i;if(!entry||team<=0)return;for(i=0;i<entry->bracket_team_count;++i)if(entry->bracket_teams[i].id==team)return;
    if(entry->bracket_team_count>=CLUB_COMPETITION_BRACKET_TEAM_CAPACITY)return;
    ClubCompetitionBracketTeam*out=entry->bracket_teams+entry->bracket_team_count++;out->id=team;native_team_name(team,out->name,sizeof(out->name));
}
static void club_competition_collect_bracket(ClubCompetitionEntry*entry,int root){
    size_t i,j;if(!entry||root<=0)return;
    for(i=0;i<native_view.fixture_count;++i){const FceFixture*f=native_view.fixtures+i;ClubCompetitionBracketTie*tie=NULL;ClubCompetitionMatch match={0};
        int kind;if(native_fixture_root(f)!=root||f->home<=0||f->away<=0)continue;kind=fce_model_stage_kind(&native_view,f->stage);
        if(kind<=FCE_STAGE_GROUP||kind==FCE_STAGE_UNKNOWN)continue;
        for(j=0;j<entry->bracket_tie_count;++j){ClubCompetitionBracketTie*candidate=entry->bracket_ties+j;
            if(candidate->stage==f->stage&&((candidate->team_a==f->home&&candidate->team_b==f->away)||(candidate->team_a==f->away&&candidate->team_b==f->home))){tie=candidate;break;}}
        if(!tie){if(entry->bracket_tie_count>=CLUB_COMPETITION_BRACKET_TIE_CAPACITY)continue;
            tie=entry->bracket_ties+entry->bracket_tie_count++;tie->stage=f->stage;tie->stage_kind=kind;tie->round=f->round;tie->team_a=f->home;tie->team_b=f->away;}
        club_competition_set_fixture(&match,f);
        if(!tie->leg_count){tie->legs[0]=match;tie->leg_count=1;}
        else if(club_competition_match_precedes(&match,tie->legs)){tie->legs[1]=tie->legs[0];tie->legs[0]=match;if(tie->leg_count<2)tie->leg_count=2;}
        else if(tie->leg_count<2){tie->legs[1]=match;tie->leg_count=2;}
        else if(club_competition_match_precedes(&match,tie->legs+1))tie->legs[1]=match;
        club_competition_remember_bracket_team(entry,f->home);club_competition_remember_bracket_team(entry,f->away);
    }
    for(i=0;i<entry->bracket_tie_count;++i)for(j=i+1;j<entry->bracket_tie_count;++j){ClubCompetitionBracketTie*a=entry->bracket_ties+i,*b=entry->bracket_ties+j;
        if(b->stage_kind<a->stage_kind||(b->stage_kind==a->stage_kind&&b->legs[0].visible&&(!a->legs[0].visible||club_competition_match_precedes(b->legs,a->legs)))){ClubCompetitionBracketTie temp=*a;*a=*b;*b=temp;}}
}
static void native_club_competitions_refresh(int club){
    ClubCompetitionsSnapshot*snapshot=(ClubCompetitionsSnapshot*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(*snapshot));
    size_t i,j,k;if(!snapshot){club_competitions_publish(NULL);return;}snapshot->club=club;snapshot->date=native_view.date;
    if(club<=0||!native_view.nodes||(!native_view.standings&&!native_view.fixture_count))goto done;
    for(i=0;i<g_competition_count&&i<CLUB_COMPETITIONS_CAPACITY;++i){const CompetitionSummary*summary=g_competition_rows+i;ClubCompetitionEntry*entry=snapshot->entries+snapshot->count++;
        int root=summary->competition_id,current=summary->stage,kind=fce_model_stage_kind(&native_view,current),club_group=-1;
        entry->competition=root;entry->asset=summary->league_id>0?summary->league_id:native_logo(root);
        entry->trophy_asset=native_active_competition_trophy(root,entry->asset);entry->current_stage=current;entry->current_stage_kind=kind;
        snprintf(entry->title_key,sizeof(entry->title_key),"TrophyName_%d",entry->asset>0?entry->asset:root);
        /* Each native group-stage node is one group. Preserve all groups and
         * remember the club's live group rather than freezing on the first. */
        {int stages[CLUB_COMPETITION_GROUP_CAPACITY];size_t stage_count=0;
            for(j=0;j<native_view.standing_count;++j){const FceStanding*standing=native_view.standings+j;int object=standing->competition_object;
                if(standing->team<=0||fce_model_ancestor(&native_view,object,3)!=root||fce_model_stage_kind(&native_view,object)!=FCE_STAGE_GROUP)continue;
                for(k=0;k<stage_count&&stages[k]!=object;++k){}if(k<stage_count)continue;
                if(stage_count<CLUB_COMPETITION_GROUP_CAPACITY)stages[stage_count++]=object;}
            for(j=0;j<stage_count;++j)for(k=j+1;k<stage_count;++k)if(stages[k]<stages[j]){int t=stages[j];stages[j]=stages[k];stages[k]=t;}
            for(j=0;j<stage_count;++j){ClubCompetitionGroup*g=entry->groups+entry->group_count;size_t n;
                g->stage=stages[j];n=club_competition_fill_table(root,g->stage,native_view.date,club,g->rows);g->row_count=n;if(n<3)continue;
                if(g->stage==current)club_group=(int)entry->group_count;
                /* Prefer the teams actually present in a later round; before
                 * the draw exists, use the saved group size's usual cut. */
                {int advanced=0;for(k=0;k<n;++k)if(club_competition_reached_later_stage(root,g->rows[k].team))++advanced;
                    g->classification_count=advanced?advanced:(n>=4?2:(int)(n/2));if(g->classification_count<1)g->classification_count=1;
                    for(k=0;k<n;++k){ClubCompetitionTableRow*r=g->rows+k;r->zone=r->rank<=g->classification_count?CLUB_COMPETITION_ZONE_ADVANCE:CLUB_COMPETITION_ZONE_OUTSIDE;
                        r->status=r->team==club?2:r->zone==CLUB_COMPETITION_ZONE_ADVANCE?1:-1;}}
                ++entry->group_count;
            }
        }
        entry->has_group_phase=entry->group_count>0;entry->is_cup=entry->has_group_phase||kind>FCE_STAGE_GROUP;
        if(club_group<0&&entry->group_count){int best=-1,best_played=-1;for(j=0;j<entry->group_count;++j)for(k=0;k<entry->groups[j].row_count;++k)
                if(entry->groups[j].rows[k].team==club&&entry->groups[j].rows[k].played>best_played){best=(int)j;best_played=entry->groups[j].rows[k].played;}
            club_group=best;}
        entry->preferred_group=club_group;
        if(!entry->has_group_phase&&summary->kind){entry->table_count=g_competition_tab_row_counts[i];if(entry->table_count>CLUB_COMPETITION_TABLE_CAPACITY)entry->table_count=CLUB_COMPETITION_TABLE_CAPACITY;
            for(j=0;j<entry->table_count;++j){const CompetitionTabRow*source=&g_competition_tab_rows[i][j];ClubCompetitionTableRow*row=entry->table+j;
                row->team=source->team_id;row->rank=source->rank;row->played=source->played;row->won=source->won;row->drawn=source->drawn;row->lost=source->lost;
                row->goals_for=source->goals_for;row->goals_against=source->goals_against;row->points=source->points;native_team_name(row->team,row->name,sizeof(row->name));
                for(k=0;k<CLUB_COMPETITION_FORM_SIZE;++k)row->form[k]=2;
                {ClubCompetitionTableRow recent;club_competition_fill_row(root,current,row->team,native_view.date,&recent);memcpy(row->form,recent.form,sizeof(row->form));
                    row->last_match_valid=recent.last_match_valid;row->last_match_result=recent.last_match_result;row->last_goals_for=recent.last_goals_for;row->last_goals_against=recent.last_goals_against;}
                if(row->team==club)row->status=2;}
            club_competition_apply_league_zones(entry->table,entry->table_count);
            club_competition_apply_movements(root,current,native_view.date,entry->table,entry->table_count);
            entry->table_available=entry->table_count>=3;
        }
        if(entry->has_group_phase){entry->table_count=0;entry->table_available=0;}
        {const FceFixture*previous=NULL,*next=NULL;for(j=0;j<native_view.fixture_count;++j){const FceFixture*f=native_view.fixtures+j;
                if((f->home!=club&&f->away!=club)||native_fixture_root(f)!=root)continue;
                if(f->played_raw&&(!fce_date_valid(native_view.date)||f->date_raw<=native_view.date)&&(!previous||club_competition_fixture_precedes(previous,f)))previous=f;
                if(!f->played_raw&&(!fce_date_valid(native_view.date)||f->date_raw>=native_view.date)&&(!next||club_competition_fixture_precedes(f,next)))next=f;}
            club_competition_set_fixture(&entry->previous,previous);club_competition_set_fixture(&entry->next,next);
            if(kind>FCE_STAGE_GROUP&&previous&&next&&previous->stage==next->stage&&
               (previous->home==next->home&&previous->away==next->away||previous->home==next->away&&previous->away==next->home)){
                int old_for=previous->home==club?previous->home_score:previous->away_score;
                int old_against=previous->home==club?previous->away_score:previous->home_score;
                entry->aggregate_visible=1;entry->aggregate_for=old_for;entry->aggregate_against=old_against;}}
        club_competition_collect_bracket(entry,root);
    }
done:
    club_competitions_publish(snapshot);HeapFree(GetProcessHeap(),0,snapshot);
}
