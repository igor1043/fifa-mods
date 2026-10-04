/* Existing native provider thread only. career_managerhistory has no userid:
 * require ONE coherent career user + matching managerinfo, never reuse it for
 * a club coach or an ambiguous multiplayer save. No native pointers escape. */
static void native_coach_profile_refresh(void) {
    static DWORD last_tick=0;static int last_club=-1,last_date=0;static LONG busy=0;
    CoachProfileContext context={0};CoachCareerRow rows[COACH_PROFILE_CAPACITY];
    unsigned __int64 query[7]={0},result=0;int q=0,r=0,ok=0,count=0,i=0;
    SIZE_T written=0;DWORD now=GetTickCount();void*backend=NULL;
    if(InterlockedCompareExchange(&busy,1,0))return;
    __try {
        int force=coach_profile_take_refresh();
        if(!force&&last_club==native_club&&last_date==native_view.date&&(DWORD)(now-last_tick)<10000)return;
        last_club=native_club;last_date=native_view.date;last_tick=now;
        if(native_club>0){char team_name[128]={0};native_team_name(native_club,team_name,sizeof(team_name));
            coach_profile_publish_team_fixtures(native_club,team_name,native_view.fixtures,native_view.fixture_count,native_view.date);}
        context.confidence=context.reputation=context.wage=-1;
        if(native_club<=0||!native_names||!is_readable_range(native_names,sizeof(void*))){career_news_publish_manager(NULL);coach_profile_publish_career(NULL,NULL,0);return;}
        native_name_db_bind();backend=*(void**)native_names;if(!backend||!is_readable_range(backend,sizeof(void*))){career_news_publish_manager(NULL);coach_profile_publish_career(NULL,NULL,0);return;}
        __try {__try {
            void(*execute)(void*,void*,void*)=(void(*)(void*,void*,void*))(*(void***)backend)[1];
            native_name_db.query_init(query,1,"career_users");q=1;
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);
            if(native_name_db.count(&result)!=1)__leave;
            context.id=native_name_db.integer(&result,0,"userid");
            context.club=native_name_db.integer(&result,0,"clubteamid");
            if(context.id<0||context.id>63||context.club!=native_club)__leave;
            context.national_team=native_name_db.integer(&result,0,"nationalteamid");if(context.national_team<0||context.national_team>200000)context.national_team=0;
            context.nationality=native_name_db.integer(&result,0,"nationalityid");
            context.season=native_name_db.integer(&result,0,"seasoncount");
            {char first[64]={0},surname[64]={0};const char*name=native_name_db.string(&result,0,"firstname");if(name)lstrcpynA(first,name,sizeof(first));
                name=native_name_db.string(&result,0,"surname");if(name)lstrcpynA(surname,name,sizeof(surname));
                snprintf(context.name,sizeof(context.name),"%s%s%s",first,first[0]&&surname[0]?" ":"",surname);}
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            native_name_db.query_init(query,1,"career_managerinfo");q=1;native_name_db.where_int(query,"userid",0,context.id);
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);
            if(native_name_db.count(&result)!=1||native_name_db.integer(&result,0,"clubteamid")!=native_club)__leave;
            context.confidence=native_name_db.integer(&result,0,"boardconfidence");if(context.confidence<0||context.confidence>100)context.confidence=-1;
            context.reputation=native_name_db.integer(&result,0,"managerreputation");if(context.reputation<0||context.reputation>1501)context.reputation=-1;
            context.wage=native_name_db.integer(&result,0,"wage");
            context.valid=1;context.kind=COACH_CAREER_USER;if(!context.name[0])lstrcpynA(context.name,"Treinador da carreira",sizeof(context.name));
            native_name_db.result_free(&result);r=0;native_name_db.query_free(query);q=0;
            native_name_db.query_init(query,1,"career_managerhistory");q=1;
            native_name_db.result_init(&result);r=1;execute(backend,query,&result);count=native_name_db.count(&result);
            if(count>=0&&count<=COACH_PROFILE_CAPACITY){ok=1;for(i=0;i<count;++i){CoachCareerRow*row=rows+written;memset(row,0,sizeof(*row));
                row->key=native_name_db.integer(&result,i,"artificialkey");row->team=native_name_db.integer(&result,i,"teamid");row->season_valid=1;
                row->season=native_name_db.integer(&result,i,"season");row->league=native_name_db.integer(&result,i,"leagueid");
                row->team_kind=context.national_team>0&&row->team==context.national_team?COACH_TEAM_NATIONAL:COACH_TEAM_CLUB;
                row->total.games=native_name_db.integer(&result,i,"games_played");row->total.wins=native_name_db.integer(&result,i,"wins");
                row->total.draws=native_name_db.integer(&result,i,"draws");row->total.losses=native_name_db.integer(&result,i,"losses");
                row->total.goals_for=native_name_db.integer(&result,i,"goals_for");row->total.goals_against=native_name_db.integer(&result,i,"goals_against");
                row->league_titles=native_name_db.integer(&result,i,"leaguetrophies");row->domestic_titles=native_name_db.integer(&result,i,"domesticcuptrophies");
                row->continental_titles=native_name_db.integer(&result,i,"continentalcuptrophies");
                if(row->team<=0||row->team>200000||row->season<0||row->season>15||row->key<0||row->league<0||row->league>3000||
                    row->total.games<0||row->total.games>250||row->total.wins<0||row->total.draws<0||row->total.losses<0||
                    row->total.wins+row->total.draws+row->total.losses!=row->total.games||row->total.goals_for<0||row->total.goals_against<0||
                    row->league_titles<0||row->domestic_titles<0||row->continental_titles<0){ok=0;break;}++written;}}
        }__finally {if(r)native_name_db.result_free(&result);if(q)native_name_db.query_free(query);}}
        __except(EXCEPTION_EXECUTE_HANDLER){ok=0;written=0;}
        if(!ok)written=0;context.history_valid=ok;context.stats_scope=ok?COACH_STATS_CAREER:COACH_STATS_NONE;
        if(context.valid){int captain=0;native_team_name(context.club,context.club_name,sizeof(context.club_name));
            if(context.national_team>0)native_team_name(context.national_team,context.national_name,sizeof(context.national_name));
            context.colors_valid=native_club_player_identity(context.club,context.colors,&captain);
            for(i=0;i<(int)written;++i)native_team_name(rows[i].team,rows[i].team_name,sizeof(rows[i].team_name));
            coach_profile_bind_splits(rows,written,native_view.fixtures,native_view.fixture_count,native_view.date,context.club,context.season);}
        if(context.valid&&context.history_valid)for(i=0;i<(int)written;++i)if(rows[i].team==context.club&&rows[i].season==context.season&&rows[i].splits_valid&&rows[i].total.games>0){
            coach_profile_bind_form(&context,native_view.fixtures,native_view.fixture_count,native_view.date);break;}
        {
            CareerNewsManagerFacts news={0};news.club_id=native_club;news.calendar_date=native_view.date;
            news.valid=context.valid;news.confidence=context.confidence;news.reputation=context.reputation;
            if(context.name[0])lstrcpynA(news.name,context.name,sizeof(news.name));
            if(context.valid&&context.history_valid)for(i=0;i<(int)written;++i)
                if(rows[i].team==native_club&&rows[i].season==context.season) {
                    const CoachCareerRow *row=rows+i;news.season_record_valid=1;news.games=row->total.games;
                    news.wins=row->total.wins;news.draws=row->total.draws;news.losses=row->total.losses;
                    news.goals_for=row->total.goals_for;news.goals_against=row->total.goals_against;
                    news.trophies=row->league_titles+row->domestic_titles+row->continental_titles;break;
                }
            career_news_publish_manager(context.valid?&news:NULL);
        }
        coach_profile_publish_career(&context,rows,written);
    } __finally {InterlockedExchange(&busy,0);}
}
